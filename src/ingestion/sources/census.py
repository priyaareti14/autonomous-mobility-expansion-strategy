"""Census Bureau sources: PEP (S-01), delineation (S-02), ACS (S-03/S-04),
Gazetteer (S-05) and County Business Patterns (S-08)."""

from __future__ import annotations

import csv
import io
import json
import os
import re
import zipfile

import openpyxl

from ..common import (REPO_ROOT, BlockedError, Check, Extract, IngestionError, http_get, log,
                      looks_like_html, sanitize, save_snapshot, sha256_bytes)
from ._tabular import (bad_lat, bad_lon, build_extract, cell_to_str, delimited_records,
                       is_number, make_row_check)

SCOPE_DOC = REPO_ROOT / "docs" / "project_scope.md"
CBSA_GEO = "metropolitan statistical area/micropolitan statistical area"


# --------------------------------------------------------------------------- #
# Frozen market universe (authority: docs/project_scope.md section 6)
# --------------------------------------------------------------------------- #
def frozen_markets() -> list[tuple[int, str, str, int]]:
    """(rank, cbsa, name, population) parsed from the scope document table."""
    rows = []
    pattern = re.compile(r"^\|\s*(\d+)\s*\|\s*(\d{5})\s*\|\s*(.+?)\s*\|\s*([\d,]+)\s*\|\s*$")
    for line in SCOPE_DOC.read_text(encoding="utf-8").splitlines():
        m = pattern.match(line)
        if m:
            rows.append((int(m[1]), m[2], m[3], int(m[4].replace(",", ""))))
    if len(rows) != 35:
        raise IngestionError(f"expected 35 frozen markets in project_scope.md, parsed {len(rows)}")
    return rows


def frozen_market_ids() -> set[str]:
    return {r[1] for r in frozen_markets()}


def _require_payload(data: bytes, what: str) -> None:
    if not data:
        raise IngestionError(f"{what}: empty payload")
    if looks_like_html(data):
        raise IngestionError(f"{what}: received an HTML page instead of data")


def _acquisition_checks(resp, data: bytes) -> list[Check]:
    return [
        Check("http_status", "ACQUISITION", "PASS", expected=200, actual=resp.status_code),
        Check("payload_non_empty_not_html", "ACQUISITION", "PASS", actual=f"{len(data)} bytes",
              details=f"content-type {resp.headers.get('Content-Type')}"),
    ]


# --------------------------------------------------------------------------- #
# S-01 PEP
# --------------------------------------------------------------------------- #
def pep(ds: dict) -> Extract:
    resp = http_get(ds["url"])
    data = resp.content
    _require_payload(data, ds["dataset_id"])
    sha = sha256_bytes(data)
    save_snapshot(ds["source_id"], ds["snapshot_name"], data)
    checks = _acquisition_checks(resp, data)

    expected_sha = ds.get("expected_sha256")
    if expected_sha and sha != expected_sha:
        raise BlockedError(f"PEP checksum {sha} differs from the Phase 1 pinned {expected_sha}")
    checks.append(Check("matches_phase1_checksum", "IDEMPOTENCY", "PASS", expected=expected_sha, actual=sha))

    text = data.decode("latin-1")
    header = next(csv.reader(io.StringIO(text)))
    checks += _pep_universe_checks(text, header)
    row_check = make_row_check(
        ("pop2025_not_non_negative_integer",
         lambda r: not (r["POPESTIMATE2025"] or "").isdigit()),
        ("cbsa_not_5_digits", lambda r: not re.fullmatch(r"\d{5}", r["CBSA"] or "")),
    )
    return build_extract(ds, snapshot_name=ds["snapshot_name"], snapshot_bytes=len(data), sha256=sha,
                         url_sanitized=ds["url"], header=header,
                         records=delimited_records(text, ",", len(header)),
                         row_check=row_check, extra_checks=checks)


def _pep_universe_checks(text: str, header: list[str]) -> list[Check]:
    rows = [dict(zip(header, r)) for r in csv.reader(io.StringIO(text))][1:]
    msas = [r for r in rows if r["LSAD"] == "Metropolitan Statistical Area"]
    checks = [Check("metro_universe_count", "SOURCE_SPECIFIC",
                    "PASS" if len(msas) == 387 else "FAIL", expected=387, actual=len(msas))]
    ranked = sorted(msas, key=lambda r: int(r["POPESTIMATE2025"]), reverse=True)[:35]
    frozen = frozen_markets()
    mismatches = []
    for (rank, cbsa, name, pop), src in zip(frozen, ranked):
        if (cbsa, name, pop) != (src["CBSA"], src["NAME"], int(src["POPESTIMATE2025"])):
            mismatches.append(f"rank {rank}: doc {cbsa}/{name}/{pop} vs source "
                              f"{src['CBSA']}/{src['NAME']}/{src['POPESTIMATE2025']}")
    status = "PASS" if not mismatches else "FAIL"
    checks.append(Check("frozen_top35_matches_project_scope", "SOURCE_SPECIFIC", status,
                        expected="35 markets: code, name, population and rank as in project_scope.md section 6",
                        actual=f"{35 - len(mismatches)}/35 identical",
                        details="; ".join(mismatches[:5])))
    if mismatches:
        raise IngestionError("PEP top-35 universe differs from project_scope.md; stopping for review")
    return checks


# --------------------------------------------------------------------------- #
# XLSX helper (S-02 here; reused by FAA)
# --------------------------------------------------------------------------- #
def xlsx_records(data: bytes, header_row: int, classify, sheet: str | None = None):
    """Read one sheet (default: the first). `classify(values) -> None | reject reason`."""
    wb = openpyxl.load_workbook(io.BytesIO(data), read_only=True, data_only=True)
    ws = wb[sheet] if sheet else wb.worksheets[0]
    all_rows = [list(r) for r in ws.iter_rows(values_only=True)]
    wb.close()
    header = [cell_to_str(v) for v in all_rows[header_row - 1]]
    body = all_rows[header_row:]

    def it():
        for offset, values in enumerate(body, start=1):
            reason = classify(values)
            text = " | ".join("" if v is None else str(v) for v in values)
            if reason:
                yield offset, None, f"{reason}: {text}"
            else:
                yield offset, [cell_to_str(v) for v in values], ""
    pre_header = [" | ".join(str(v) for v in r if v is not None) for r in all_rows[:header_row - 1]]
    return header, it, pre_header


def delineation(ds: dict) -> Extract:
    resp = http_get(ds["url"])
    data = resp.content
    _require_payload(data, ds["dataset_id"])
    sha = sha256_bytes(data)
    save_snapshot(ds["source_id"], ds["snapshot_name"], data)

    def classify(values):
        if all(v is None for v in values):
            return "blank row"
        if values[0] and not str(values[0]).isdigit() and all(v is None for v in values[1:]):
            return "non-tabular note row"
        return None

    header, records, pre = xlsx_records(data, ds["xlsx_header_row"], classify)
    checks = _acquisition_checks(resp, data)
    checks.append(Check("title_identifies_july_2023", "SOURCE_SPECIFIC",
                        "PASS" if any("JULY 2023" in p.upper() for p in pre) else "FAIL",
                        expected="title contains 'JULY 2023'", actual=pre[-1][:200] if pre else None,
                        details=f"{len(pre)} title row(s) above the header are not data"))
    row_check = make_row_check(
        ("cbsa_code_not_5_digits", lambda r: not re.fullmatch(r"\d{5}", r["CBSA Code"] or "")),
        ("state_fips_not_2_digits", lambda r: not re.fullmatch(r"\d{2}", r["FIPS State Code"] or "")),
        ("county_fips_not_3_digits", lambda r: not re.fullmatch(r"\d{3}", r["FIPS County Code"] or "")),
    )
    ex = build_extract(ds, snapshot_name=ds["snapshot_name"], snapshot_bytes=len(data), sha256=sha,
                       url_sanitized=ds["url"], header=header, records=records,
                       row_check=row_check, extra_checks=checks)
    # Source-specific: county rows of the 35 frozen markets are all present.
    present = set()
    for _, values, _ in records():
        if values:
            present.add(cell_to_str(values[0]))
    missing = frozen_market_ids() - present
    ex.checks.append(Check("frozen_markets_present", "SOURCE_SPECIFIC", "FAIL" if missing else "PASS",
                           expected=35, actual=35 - len(missing), details=f"missing {sorted(missing)}"))
    if missing:
        raise IngestionError(f"delineation lacks frozen markets {sorted(missing)}")
    return ex


# --------------------------------------------------------------------------- #
# Census Data API (S-03, S-04)
# --------------------------------------------------------------------------- #
def _api_key() -> str:
    key = os.getenv("CENSUS_API_KEY", "").strip()
    if not key:
        raise BlockedError("CENSUS_API_KEY is not set")
    return key


def _census_call(endpoint: str, params: dict) -> list[list]:
    resp = http_get(endpoint, params={**params, "key": _api_key()})
    text = resp.text
    if looks_like_html(resp.content) or not text.lstrip().startswith("["):
        raise IngestionError(f"Census API returned non-JSON content: {sanitize(text[:200])}")
    return json.loads(text)


def _sanitized_query(endpoint: str, params: dict) -> str:
    q = "&".join(f"{k}={v}" for k, v in params.items())
    return f"{endpoint}?{q}"   # key deliberately not included


def _canonical(header: list[str], body: list[list]) -> list[list]:
    """Sort API records by GEO_ID.

    The Census API does not guarantee row order: an identical S-04 response
    came back reordered within Alaska on 2026-10-05. Sorting by the source's
    own unique identifier makes the snapshot checksum depend on content only.
    """
    gi = header.index("GEO_ID")
    return sorted(body, key=lambda r: str(r[gi]))


CANONICAL_CHECK = Check("api_rows_canonical_order", "IDEMPOTENCY", "PASS",
                        details="records sorted by GEO_ID before hashing; the API's row order is "
                                "not guaranteed (S-04 reorder observed 2026-10-05)")


def _json_records(rows: list[list]):
    def it():
        for i, r in enumerate(rows[1:], start=1):
            yield i, [None if v is None else str(v) for v in r], ""
    return it


def _cbsa_presence_check(header: list[str], rows: list[list], geo_col: str) -> Check:
    idx = header.index(geo_col)
    present = {str(r[idx]) for r in rows[1:]}
    missing = frozen_market_ids() - present
    return Check("frozen_markets_present", "SOURCE_SPECIFIC", "FAIL" if missing else "PASS",
                 expected=35, actual=35 - len(missing), details=f"missing {sorted(missing)}")


def acs_cbsa(ds: dict) -> Extract:
    if ds["access_method"] == "census_api_group":
        params = {"get": f"group({ds['group']})", "for": ds["geography"]}
    else:
        params = {"get": ",".join(ds["variables"]), "for": ds["geography"]}
    rows = _census_call(ds["endpoint"], params)
    header = [str(h) for h in rows[0]]
    rows = [rows[0]] + _canonical(header, rows[1:])
    data = json.dumps(rows, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
    sha = sha256_bytes(data)
    save_snapshot(ds["source_id"], ds["snapshot_name"], data)
    checks = [
        CANONICAL_CHECK,
        Check("api_response_json_array", "ACQUISITION", "PASS", actual=f"{len(rows) - 1} records"),
        Check("cbsa_universe_count", "SOURCE_SPECIFIC", "PASS" if len(rows) - 1 == 935 else "WARN",
              expected="935 (387 metro + 538 micro, July 2023 delineation)", actual=len(rows) - 1),
        _cbsa_presence_check(header, rows, CBSA_GEO),
    ]
    if ds["access_method"] == "census_api_group":
        expected_prefix = ds["group"] + "_"
        n_vars = sum(1 for h in header if h.startswith(expected_prefix))
        checks.append(Check("group_variables_returned", "SCHEMA", "PASS" if n_vars else "FAIL",
                            actual=n_vars, details=f"columns starting with {expected_prefix}"))
    if any(c.status == "FAIL" for c in checks):
        raise IngestionError("ACS acquisition checks failed")
    return build_extract(ds, snapshot_name=ds["snapshot_name"], snapshot_bytes=len(data), sha256=sha,
                         url_sanitized=_sanitized_query(ds["endpoint"], params), header=header,
                         records=_json_records(rows), extra_checks=checks)


def acs_tract(ds: dict) -> Extract:
    states = _census_call(ds["endpoint"], {"get": "NAME", "for": "state:*"})
    state_codes = sorted(str(r[1]) for r in states[1:])
    header, all_rows = None, []
    for code in state_codes:
        rows = _census_call(ds["endpoint"], {"get": f"group({ds['group']})", "for": "tract:*",
                                             "in": f"state:{code}"})
        if header is None:
            header = [str(h) for h in rows[0]]
        elif [str(h) for h in rows[0]] != header:
            raise IngestionError(f"tract response header changed for state {code}")
        all_rows.extend(rows[1:])
        log.info("  tracts state %s: %s", code, f"{len(rows) - 1:,}")
    rows = [header] + _canonical(header, all_rows)
    snapshot = {"state_codes": state_codes, "rows": rows}
    data = json.dumps(snapshot, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
    sha = sha256_bytes(data)
    save_snapshot(ds["source_id"], ds["snapshot_name"], data)
    params = {"get": f"group({ds['group']})", "for": "tract:*", "in": "state:<each state code>"}
    checks = [CANONICAL_CHECK,
              Check("states_queried", "ACQUISITION", "PASS", actual=len(state_codes),
                    details=",".join(state_codes))]
    return build_extract(ds, snapshot_name=ds["snapshot_name"], snapshot_bytes=len(data), sha256=sha,
                         url_sanitized=_sanitized_query(ds["endpoint"], params), header=header,
                         records=_json_records(rows), extra_checks=checks,
                         row_check=make_row_check(
                             ("population_not_non_negative_integer",
                              lambda r: not (r["B01003_001E"] or "").isdigit())))


# --------------------------------------------------------------------------- #
# Zipped delimited text (S-05 Gazetteer, S-08 CBP; reused by FAA NASR)
# --------------------------------------------------------------------------- #
def zip_delimited(ds: dict, encoding: str = "latin-1") -> tuple[str, list[str], list[Check], int, str]:
    """Download a zip, return (member text, trimmed header, checks, zip bytes, zip SHA-256)."""
    resp = http_get(ds["url"])
    data = resp.content
    _require_payload(data, ds["dataset_id"])
    sha = sha256_bytes(data)
    save_snapshot(ds["source_id"], ds["snapshot_name"], data)
    z = zipfile.ZipFile(io.BytesIO(data))
    member = ds.get("zip_member")
    names = z.namelist()
    if member is None:
        data_files = [n for n in names if not n.endswith("/")]
        if len(data_files) != 1:
            raise IngestionError(f"expected one file in zip, found {data_files}")
        member = data_files[0]
    elif member not in names:
        raise IngestionError(f"zip member {member} not found; members: {names}")
    text = z.read(member).decode(encoding)
    raw_header = next(csv.reader(io.StringIO(text), delimiter=ds["delimiter"]))
    header = [h.strip() for h in raw_header]
    checks = _acquisition_checks(resp, data)
    checks.append(Check("zip_member", "ACQUISITION", "PASS", actual=member,
                        details=f"members: {', '.join(names)[:500]}"))
    if header != raw_header:
        checks.append(Check("header_whitespace_trimmed", "SCHEMA", "WARN",
                            details="surrounding whitespace removed from source column names"))
    return text, header, checks, len(data), sha


def gazetteer(ds: dict) -> Extract:
    text, header, checks, nbytes, sha = zip_delimited(ds)
    rules = [("aland_not_numeric", lambda r: not is_number(r["ALAND"]))]
    if "INTPTLAT" in header:
        rules += [("latitude_out_of_range", lambda r: bad_lat(r["INTPTLAT"])),
                  ("longitude_out_of_range", lambda r: bad_lon(r["INTPTLONG"]))]
    ex = build_extract(ds, snapshot_name=ds["snapshot_name"], snapshot_bytes=nbytes, sha256=sha,
                       url_sanitized=ds["url"], header=header,
                       records=_trimmed_delimited(text, ds["delimiter"], len(header)),
                       row_check=make_row_check(*rules), extra_checks=checks)
    ex.checks.append(Check("values_outer_whitespace_trimmed", "SCHEMA", "WARN",
                           details="Gazetteer pads the last field with spaces; leading/trailing "
                                   "whitespace removed from every value (technical normalization)"))
    if ds["dataset_id"].endswith("_cbsa"):
        gi = header.index("GEOID")
        present = {v[gi] for _, v, _ in _trimmed_delimited(text, ds["delimiter"], len(header))() if v}
        missing = frozen_market_ids() - present
        ex.checks.append(Check("frozen_markets_present", "SOURCE_SPECIFIC", "FAIL" if missing else "PASS",
                               expected=35, actual=35 - len(missing), details=f"missing {sorted(missing)}"))
    return ex


def _trimmed_delimited(text: str, delimiter: str, n_cols: int):
    """Gazetteer lines carry trailing padding on the last field; trim each value's outer whitespace."""
    base = delimited_records(text, delimiter, n_cols)

    def it():
        for row_no, values, raw in base():
            yield row_no, (None if values is None else [v.strip() for v in values]), raw
    return it


def cbp(ds: dict) -> Extract:
    text, header, checks, nbytes, sha = zip_delimited(ds)
    row_check = make_row_check(
        ("est_not_non_negative_integer", lambda r: not (r["est"] or "").isdigit()),
        ("msa_not_5_digits", lambda r: not re.fullmatch(r"\d{5}", r["msa"] or "")),
    )
    ex = build_extract(ds, snapshot_name=ds["snapshot_name"], snapshot_bytes=nbytes, sha256=sha,
                       url_sanitized=ds["url"], header=header,
                       records=delimited_records(text, ds["delimiter"], len(header)),
                       row_check=row_check, extra_checks=checks)
    present = {v[0] for _, v, _ in delimited_records(text, ds["delimiter"], len(header))() if v}
    missing = frozen_market_ids() - present
    ex.checks.append(Check("frozen_markets_present", "SOURCE_SPECIFIC", "FAIL" if missing else "PASS",
                           expected=35, actual=35 - len(missing), details=f"missing {sorted(missing)}"))
    ex.checks.append(Check("cbsa_universe_count", "SOURCE_SPECIFIC",
                           "PASS" if len(present) == 925 else "WARN",
                           expected="925 (387 metro + 538 micro per Phase 1)", actual=len(present)))
    return ex
