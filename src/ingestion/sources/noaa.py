"""NOAA NCEI U.S. Climate Normals 1991-2020: annual/seasonal (S-12) and hourly wind (S-13).

Both arrive as by-station tarballs (one CSV per station). No station is mapped
to a market here: station-to-CBSA rules are an open Phase 4+ decision (A-007).
"""

from __future__ import annotations

import csv
import io
import json
import tarfile

from ..common import Check, Extract, IngestionError, http_get, log, save_snapshot, sha256_bytes
from ._tabular import bad_lat, bad_lon, build_extract, make_row_check


def _download(ds: dict) -> tuple[bytes, str, list[Check]]:
    resp = http_get(ds["url"], timeout=1800)
    data = resp.content
    if not data.startswith(b"\x1f\x8b"):
        raise IngestionError("expected a gzip archive")
    sha = sha256_bytes(data)
    save_snapshot(ds["source_id"], ds["snapshot_name"], data)
    checks = [Check("http_status", "ACQUISITION", "PASS", expected=200, actual=resp.status_code),
              Check("payload_is_gzip", "ACQUISITION", "PASS", actual=f"{len(data):,} bytes")]
    return data, sha, checks


def _members(data: bytes):
    """Yield (name, text) for every CSV member, in sorted name order (deterministic)."""
    with tarfile.open(fileobj=io.BytesIO(data), mode="r:gz") as tf:
        files = sorted((m for m in tf.getmembers() if m.isfile() and m.name.endswith(".csv")),
                       key=lambda m: m.name)
        for m in files:
            yield m.name, tf.extractfile(m).read().decode("utf-8")


# --------------------------------------------------------------------------- #
# S-12 annual/seasonal: one record per station, heterogeneous columns -> VARIANT
# --------------------------------------------------------------------------- #
def annual_seasonal(ds: dict) -> Extract:
    data, sha, checks = _download(ds)
    required = ds["required_columns"]

    def records():
        for i, (name, text) in enumerate(_members(data), start=1):
            rows = list(csv.reader(io.StringIO(text)))
            header, body = rows[0], [r for r in rows[1:] if r]
            if len(body) != 1 or len(body[0]) != len(header):
                yield i, None, f"station file {name}: expected 1 record matching header, got {len(body)}"
                continue
            rec = dict(zip(header, body[0]))
            missing = [c for c in required if c not in rec]
            if missing:
                yield i, None, f"station file {name}: missing {missing}"
                continue
            # Every source field and value kept exactly, as a JSON object.
            yield i, [rec["STATION"], json.dumps(rec, ensure_ascii=False)], ""

    def _field(r, key):
        return json.loads(r["RECORD"]).get(key)

    row_check = make_row_check(
        ("latitude_out_of_range", lambda r: bad_lat(_field(r, "LATITUDE"))),
        ("longitude_out_of_range", lambda r: bad_lon(_field(r, "LONGITUDE"))),
    )
    station_files = sum(1 for _ in _members(data))
    checks.append(Check("station_files_in_archive", "ACQUISITION", "PASS", actual=station_files,
                        details="one CSV per station; each must hold exactly one record"))
    checks.append(Check("heterogeneous_columns_as_variant", "SCHEMA", "PASS",
                        details="stations publish different element sets; each station record is "
                                "landed whole in RECORD (VARIANT) keyed by STATION"))
    ex = build_extract({**ds, "required_columns": ["STATION"]}, snapshot_name=ds["snapshot_name"],
                       snapshot_bytes=len(data), sha256=sha, url_sanitized=ds["url"],
                       header=["STATION", "RECORD"], records=records, row_check=row_check,
                       extra_checks=checks)
    ex.variant_columns = ("RECORD",)
    return ex


# --------------------------------------------------------------------------- #
# S-13 hourly: wind columns only (documented projection), every row kept
# --------------------------------------------------------------------------- #
def hourly_wind(ds: dict) -> Extract:
    data, sha, checks = _download(ds)
    ident = ds["projection"]["identifier_columns"]
    needle = ds["projection"]["column_contains"]

    # Pass 0: union of projected columns across stations (in first-seen order).
    projected: list[str] = []
    all_cols: set[str] = set()
    stations = 0
    no_wind = []
    for name, text in _members(data):
        stations += 1
        header = next(csv.reader(io.StringIO(text)))
        all_cols.update(header)
        wind = [c for c in header if needle in c]
        if not wind:
            no_wind.append(name)
        for c in [c for c in header if c in ident] + wind:
            if c not in projected:
                projected.append(c)
    projected = [c for c in ident if c in projected] + [c for c in projected if c not in ident]
    log.info("  hourly normals: %d stations, %d projected of %d source columns",
             stations, len(projected), len(all_cols))
    checks.append(Check("column_projection", "SCHEMA", "WARN", actual=f"{len(projected)} of {len(all_cols)}",
                        details=f"kept identifier columns + columns containing '{needle}'; every row kept. "
                                f"Dropped non-wind hourly variables (no approved feature uses them)."))
    checks.append(Check("stations_without_wind_columns", "SOURCE_SPECIFIC",
                        "WARN" if no_wind else "PASS", actual=len(no_wind),
                        details=", ".join(no_wind[:10])))

    def records():
        n = 0
        for name, text in _members(data):
            reader = csv.reader(io.StringIO(text))
            header = next(reader)
            idx = {c: i for i, c in enumerate(header)}
            for row in reader:
                if not row:
                    continue
                n += 1
                if len(row) != len(header):
                    yield n, None, f"{name}: field count {len(row)} != header {len(header)}"
                    continue
                yield n, [row[idx[c]] if c in idx else None for c in projected], ""

    return build_extract(ds, snapshot_name=ds["snapshot_name"], snapshot_bytes=len(data), sha256=sha,
                         url_sanitized=ds["url"], header=projected, records=records,
                         extra_checks=checks)
