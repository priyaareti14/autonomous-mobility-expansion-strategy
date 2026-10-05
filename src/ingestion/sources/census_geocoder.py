"""U.S. Census Bureau Geocoder, geographies-by-coordinates (S-40): the official county that
contains each FAA commercial-service airport's NASR reference point.

Phase 6 controlled source extension. It replaces the Phase 5 county-NAME match (A-032) with
an official coordinate-to-county relationship. NASR publishes no county FIPS code.

Inputs are not downloaded: they are the PINNED local snapshots already loaded in Phase 3:
- S-17 FAA CY2025 enplanements, for the 516 commercial-service airport codes;
- S-19 NASR APT_BASE 2026-09-03, for their LAT_DECIMAL / LONG_DECIMAL.
Both snapshots are verified against their registered SHA-256 before any request is sent. The
only data sent to the Census service is public airport coordinates.

Boundaries are pinned with vintage ACS2024_Current, the same county vintage as Gazetteer 2024.
The snapshot drops the service's internal object identifiers (OID, OBJECTID), which are not
attributes of the county, so an unchanged answer always reproduces the same checksum.
"""

from __future__ import annotations

import csv
import io
import json
import time
import zipfile

from ..common import RAW_CACHE, Check, Extract, IngestionError, http_get, log, save_snapshot, sha256_bytes
from ._tabular import bad_lat, bad_lon, build_extract, make_row_check
from .census import xlsx_records

COUNTY_FIELDS = ("GEOID", "STATE", "COUNTY", "NAME", "BASENAME", "COUNTYNS", "LSADC", "FUNCSTAT",
                 "MTFCC", "AREALAND", "AREAWATER", "INTPTLAT", "INTPTLON")
HEADER = ["AIRPORT_CODE", "INPUT_LATITUDE", "INPUT_LONGITUDE", "BENCHMARK_NAME", "VINTAGE_NAME",
          "COUNTY_MATCH_COUNT"] + [f"COUNTY_{f}" for f in COUNTY_FIELDS]


def _pinned(ds: dict, key: str) -> bytes:
    spec = ds["input_snapshots"][key]
    path = RAW_CACHE / spec["source_id"] / spec["snapshot_name"]
    if not path.exists():
        raise IngestionError(f"pinned input snapshot missing: {spec['snapshot_name']}")
    data = path.read_bytes()
    if sha256_bytes(data) != spec["sha256"]:
        raise IngestionError(f"pinned input snapshot changed: {spec['snapshot_name']}")
    return data


def _airport_points(ds: dict) -> list[tuple[str, str, str]]:
    """(airport_code, lat, lon) for every commercial-service airport, sorted by code."""
    def classify(values):
        if all(v is None for v in values):
            return "blank row"
        if values[0] is None and isinstance(values[3], (int, float)):
            return "summary row"
        return None
    header, records, _ = xlsx_records(_pinned(ds, "enplanements"), 1, classify)
    i = header.index("Locid")
    codes = sorted({str(v[i]).strip() for _, v, _ in records() if v is not None})

    with zipfile.ZipFile(io.BytesIO(_pinned(ds, "nasr"))) as z:
        text = z.read("APT_BASE.csv").decode("utf-8-sig")
    nasr = {r["ARPT_ID"].strip(): (r["LAT_DECIMAL"].strip(), r["LONG_DECIMAL"].strip())
            for r in csv.DictReader(io.StringIO(text))}
    missing = [c for c in codes if c not in nasr]
    if missing:
        raise IngestionError(f"airports without a NASR record: {missing[:10]}")
    return [(c, *nasr[c]) for c in codes]


def airport_counties(ds: dict) -> Extract:
    points = _airport_points(ds)
    if len(points) != ds["expected_airports"]:
        raise IngestionError(f"expected {ds['expected_airports']} airports, found {len(points)}")
    log.info("  geocoding %d airport reference points (vintage %s)", len(points), ds["vintage_name"])

    rows: list[dict] = []
    for n, (code, lat, lon) in enumerate(points, start=1):
        j = http_get(ds["endpoint"], retries=5, timeout=120, params={
            "x": lon, "y": lat, "benchmark": ds["benchmark_name"], "vintage": ds["vintage_name"],
            "layers": "Counties", "format": "json"}).json()
        result = j.get("result") or {}
        got = (result.get("input") or {}).get("vintage", {}).get("vintageName")
        if got != ds["vintage_name"]:
            raise IngestionError(f"{code}: service answered with vintage {got!r}")
        counties = (result.get("geographies") or {}).get("Counties", [])
        first = counties[0] if counties else {}
        rows.append({"AIRPORT_CODE": code, "INPUT_LATITUDE": lat, "INPUT_LONGITUDE": lon,
                     "BENCHMARK_NAME": ds["benchmark_name"], "VINTAGE_NAME": got,
                     "COUNTY_MATCH_COUNT": str(len(counties)),
                     **{f"COUNTY_{f}": (None if first.get(f) is None else str(first[f]))
                        for f in COUNTY_FIELDS}})
        if n % 100 == 0:
            log.info("  geocoded %d / %d", n, len(points))
        time.sleep(ds.get("pause_seconds", 0.2))     # polite pacing for a free public service

    data = ("\n".join(json.dumps(r, ensure_ascii=False) for r in rows) + "\n").encode("utf-8")
    sha = sha256_bytes(data)
    save_snapshot(ds["source_id"], ds["snapshot_name"], data)

    checks = [
        Check("pinned_inputs_verified", "ACQUISITION", "PASS",
              details="; ".join(f"{s['snapshot_name']} {s['sha256'][:12]}" for s in ds["input_snapshots"].values())),
        Check("one_response_per_airport", "RECONCILIATION", "PASS", expected=len(points), actual=len(rows)),
        Check("snapshot_serialization", "SCHEMA", "PASS",
              details="NDJSON ordered by airport code; service object identifiers (OID, OBJECTID) dropped"),
    ]

    def records():
        for i, r in enumerate(rows, start=1):
            yield i, [r[h] for h in HEADER], ""

    row_check = make_row_check(
        ("no_county_returned", lambda r: r["COUNTY_MATCH_COUNT"] != "1", "WARN"),
        ("input_latitude_out_of_range", lambda r: bad_lat(r["INPUT_LATITUDE"])),
        ("input_longitude_out_of_range", lambda r: bad_lon(r["INPUT_LONGITUDE"])),
    )
    url = (f"{ds['endpoint']}?x=<lon>&y=<lat>&benchmark={ds['benchmark_name']}"
           f"&vintage={ds['vintage_name']}&layers=Counties&format=json")
    return build_extract(ds, snapshot_name=ds["snapshot_name"], snapshot_bytes=len(data), sha256=sha,
                         url_sanitized=url, header=HEADER, records=records,
                         row_check=row_check, extra_checks=checks)
