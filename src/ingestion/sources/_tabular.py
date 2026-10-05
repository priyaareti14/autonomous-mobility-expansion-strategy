"""Shared two-pass tabular extraction.

Pass 1 (validation) streams every record once: counts records, rejects
malformed ones with a reason, checks required columns, null and duplicate
natural keys, and runs per-record source-specific checks. Nothing is loaded.

Pass 2 (load) streams again and yields string-typed DataFrame chunks,
skipping exactly the rows rejected in pass 1.
"""

from __future__ import annotations

import csv
import io
import re
from collections.abc import Callable, Iterable, Iterator
from datetime import date, datetime

from ..common import Check, Extract, IngestionError, Reject, column_mapping
from ..loaders import frame_from_rows

CHUNK_ROWS = 100_000

# A record source returns an iterator of (source_row_number, values or None, raw_text).
# values is None when the record is malformed; raw_text explains or reproduces it.
RecordIter = Callable[[], Iterator[tuple[int, list | None, str]]]


def cell_to_str(v) -> str | None:
    """Conservative text form of a parsed cell (XLSX/JSON) for VARCHAR RAW columns."""
    if v is None:
        return None
    if isinstance(v, bool):
        return str(v)
    if isinstance(v, int):
        return str(v)
    if isinstance(v, float):
        return repr(v)            # shortest round-trip representation
    if isinstance(v, (datetime, date)):
        return v.isoformat()
    return str(v)


def delimited_records(text: str, delimiter: str, n_cols: int) -> RecordIter:
    """Records after the header line. Row numbers are 1-based data-record numbers."""
    def it():
        reader = csv.reader(io.StringIO(text), delimiter=delimiter)
        next(reader)  # header
        for i, row in enumerate(reader, start=1):
            if len(row) != n_cols:
                reason = "blank line" if not row else f"field count {len(row)} != header {n_cols}"
                yield i, None, f"{reason}: {delimiter.join(row)[:500]}"
            else:
                yield i, row, ""
    return it


def build_extract(ds: dict, *, snapshot_name: str, snapshot_bytes: int, sha256: str,
                  url_sanitized: str, header: list[str], records: RecordIter,
                  row_check: Callable[[dict[str, str | None]], Iterable[str]] | None = None,
                  extra_checks: list[Check] | None = None,
                  extra_rejects: list[Reject] | None = None) -> Extract:
    """Validate (pass 1) and return an Extract whose frames run pass 2."""
    mapping = column_mapping(header)
    sf_cols = [mapping[c] for c in header]
    checks: list[Check] = list(extra_checks or [])
    rejects: list[Reject] = list(extra_rejects or [])

    # Required columns are named in source form in the registry.
    missing = [c for c in ds["required_columns"] if c not in header]
    checks.append(Check("required_columns_present", "SCHEMA", "FAIL" if missing else "PASS",
                        expected=", ".join(ds["required_columns"]), actual=f"missing: {missing}"))
    if missing:
        raise IngestionError(f"required columns missing: {missing}")

    key_idx = [header.index(k) for k in ds.get("natural_key", [])]
    # Components that must never be blank. Defaults to the whole key; composite
    # keys whose parts are blank by design (e.g. PEP MDIV/STCOU on metro rows)
    # name the mandatory parts in "key_not_null".
    nn_idx = [header.index(k) for k in ds.get("key_not_null", ds.get("natural_key", []))]
    seen_keys: set[int] = set()   # hash of each key tuple: bounded memory for multi-million-row sources
    dup_keys = null_keys = 0
    dup_examples: list[str] = []
    # Identifiers expected to be unique but known to repeat in the source:
    # duplicates are recorded as WARN (source anomaly), never altered.
    warn_idx = {c: header.index(c) for c in ds.get("warn_unique", [])}
    warn_seen: dict[str, set] = {c: set() for c in warn_idx}
    warn_dups: dict[str, list] = {c: [] for c in warn_idx}
    issues: dict[str, int] = {}
    issue_examples: dict[str, str] = {}
    total = valid = 0
    rejected_rows: set[int] = {r.row_number for r in rejects if r.row_number is not None}

    for row_no, values, raw in records():
        total += 1
        if values is None:
            rejects.append(Reject(row_no, raw.split(":")[0], raw))
            rejected_rows.add(row_no)
            continue
        valid += 1
        if key_idx:
            key = tuple(values[i] for i in key_idx)
            if any(values[i] in (None, "") for i in nn_idx):
                null_keys += 1
            elif (h := hash(key)) in seen_keys:
                dup_keys += 1
                if len(dup_examples) < 5:
                    dup_examples.append(str(key))
            else:
                seen_keys.add(h)
        for c, i in warn_idx.items():
            if values[i] in warn_seen[c]:
                warn_dups[c].append(f"{values[i]} (row {row_no})")
            else:
                warn_seen[c].add(values[i])
        if row_check:
            for issue in row_check(dict(zip(header, values))):
                issues[issue] = issues.get(issue, 0) + 1
                issue_examples.setdefault(issue, f"row {row_no}")

    if valid == 0:
        raise IngestionError("source contains no data records")
    checks.append(Check("non_empty_source", "INTEGRITY", "PASS", actual=valid))
    if key_idx:
        k = "+".join(ds["natural_key"])
        nn = "+".join(ds.get("key_not_null", ds["natural_key"]))
        checks.append(Check(f"key_not_null[{nn}]", "INTEGRITY",
                            "FAIL" if null_keys else "PASS", expected=0, actual=null_keys))
        checks.append(Check(f"natural_key_unique[{k}]", "INTEGRITY",
                            "FAIL" if dup_keys else "PASS", expected=0, actual=dup_keys,
                            details="; ".join(dup_examples)))
    for c, dups in warn_dups.items():
        checks.append(Check(f"source_identifier_repeats[{c}]", "INTEGRITY", "WARN" if dups else "PASS",
                            expected=0, actual=len(dups),
                            details="known source anomaly, landed as-is: " + "; ".join(dups[:5])))
    severity = row_check.__dict__.get("severity", {}) if row_check else {}
    for issue, count in sorted(issues.items()):
        checks.append(Check(issue, "SOURCE_SPECIFIC", severity.get(issue, "FAIL"), expected=0,
                            actual=count, details=f"first at {issue_examples[issue]}"))
    for issue in (row_check.__dict__.get("check_names", []) if row_check else []):
        if issue not in issues:
            checks.append(Check(issue, "SOURCE_SPECIFIC", "PASS", expected=0, actual=0))

    renamed = {s: t for s, t in mapping.items() if s != t}
    if renamed:
        checks.append(Check("column_names_normalized", "SCHEMA", "PASS", actual=len(renamed),
                            details="; ".join(f"{s!r}->{t}" for s, t in list(renamed.items())[:40])))

    def frames() -> Iterator:
        buf, nums = [], []
        for row_no, values, _ in records():
            if values is None or row_no in rejected_rows:
                continue
            buf.append(values)
            nums.append(row_no)
            if len(buf) >= CHUNK_ROWS:
                yield frame_from_rows(sf_cols, buf, nums)
                buf, nums = [], []
        if buf:
            yield frame_from_rows(sf_cols, buf, nums)

    return Extract(snapshot_name=snapshot_name, snapshot_bytes=snapshot_bytes, sha256=sha256,
                   url_sanitized=url_sanitized, frames=frames(), source_row_count=total,
                   columns=sf_cols, checks=checks, rejects=rejects, column_renames=renamed,
                   record_factory=records)


# --------------------------------------------------------------------------- #
# Reusable per-record checks
# --------------------------------------------------------------------------- #
_NUM = re.compile(r"^[+-]?\d+(\.\d+)?$")   # Gazetteer writes positive longitudes as '+179.62'


def make_row_check(*rules: tuple):
    """Build a row_check from (issue_name, predicate_true_when_bad[, 'FAIL'|'WARN']).

    FAIL rules block the load; WARN rules are recorded but allow it.
    """
    def check(rec: dict) -> Iterable[str]:
        return [r[0] for r in rules if r[1](rec)]
    check.check_names = [r[0] for r in rules]
    check.severity = {r[0]: (r[2] if len(r) > 2 else "FAIL") for r in rules}
    return check


def is_number(v) -> bool:
    return v is not None and bool(_NUM.match(str(v).strip()))


def bad_lat(v) -> bool:
    return not (is_number(v) and -90 <= float(v) <= 90)


def bad_lon(v) -> bool:
    return not (is_number(v) and -180 <= float(v) <= 180)
