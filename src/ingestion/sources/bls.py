"""BLS OEWS May 2025 metropolitan-area estimates (S-09).

Phase 1 and the early Phase 3 probes got HTTP 403, but those used a
browser-style User-Agent. The pipeline's descriptive User-Agent was accepted
on 2026-10-04. The layout was inspected before this parser was written: the
zip holds MSA_M2025_dl.xlsx (metro areas, landed here), BOS_M2025_dl.xlsx
(nonmetropolitan balance-of-state areas, out of scope) and
file_descriptions.xlsx.

Wage cells keep BLS's documented markers ('*' wage not available,
'#' top-coded) exactly as published; interpretation belongs to dbt STAGING.
"""

from __future__ import annotations

import io
import zipfile

from ..common import Check, Extract, IngestionError, http_get, save_snapshot, sha256_bytes
from ._tabular import build_extract, make_row_check
from .census import frozen_market_ids, xlsx_records


def oews(ds: dict) -> Extract:
    resp = http_get(ds["url"])  # raises BlockedError on HTTP 401/403/429
    data = resp.content
    if not data.startswith(b"PK"):
        raise IngestionError("expected a zip payload")
    sha = sha256_bytes(data)
    save_snapshot(ds["source_id"], ds["snapshot_name"], data)
    z = zipfile.ZipFile(io.BytesIO(data))
    names = z.namelist()
    if ds["zip_member"] not in names:
        raise IngestionError(f"{ds['zip_member']} not in archive: {names}")
    book = z.read(ds["zip_member"])

    def classify(values):
        return "blank row" if all(v is None for v in values) else None

    header, records, _ = xlsx_records(book, ds["xlsx_header_row"], classify, sheet=ds["xlsx_sheet"])
    checks = [
        Check("http_status", "ACQUISITION", "PASS", expected=200, actual=resp.status_code),
        Check("zip_member", "ACQUISITION", "PASS", actual=ds["zip_member"],
              details=f"members: {', '.join(names)}; only the MSA workbook is landed"),
    ]
    row_check = make_row_check(
        ("area_type_not_msa", lambda r: r["AREA_TYPE"] != "4"),
        ("occ_code_malformed", lambda r: not (r["OCC_CODE"] or "").count("-") == 1),
    )
    ex = build_extract(ds, snapshot_name=ds["snapshot_name"], snapshot_bytes=len(data), sha256=sha,
                       url_sanitized=ds["url"], header=header, records=records,
                       row_check=row_check, extra_checks=checks)
    ai = header.index("AREA")
    areas = {v[ai] for _, v, _ in records() if v}
    missing = frozen_market_ids() - areas
    ex.checks.append(Check("frozen_markets_present", "SOURCE_SPECIFIC", "FAIL" if missing else "PASS",
                           expected=35, actual=35 - len(missing), details=f"missing {sorted(missing)}"))
    ex.checks.append(Check("metro_area_count", "SOURCE_SPECIFIC", "PASS", actual=len(areas),
                           details="OEWS publishes metropolitan areas only in this workbook "
                                   "(includes Puerto Rico metros)"))
    return ex
