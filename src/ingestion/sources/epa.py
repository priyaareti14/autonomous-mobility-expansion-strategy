"""EPA Smart Location Database v3.0 (S-21), which also carries the National
Walkability Index (S-22, field NatWalkInd).

Retrieved from EPA's official ArcGIS REST layer as attributes only (no
geometry). The 553 MB geodatabase download would need a GIS library that
Phase 3 does not otherwise require. The block-group CBSA field in this source
uses a pre-2023 delineation and is landed as-is, never used for mapping
(A-006).
"""

from __future__ import annotations

import json

from ..common import Check, Extract, IngestionError, http_get, log, save_snapshot, sha256_bytes
from ._tabular import build_extract, cell_to_str, is_number, make_row_check


def sld(ds: dict) -> Extract:
    endpoint, size = ds["endpoint"], ds["page_size"]
    count = http_get(endpoint, params={"where": "1=1", "returnCountOnly": "true", "f": "json"}).json()
    if "count" not in count:
        raise IngestionError(f"count query failed: {str(count)[:200]}")
    expected = int(count["count"])

    features: list[dict] = []
    offset = 0
    while offset < expected:
        # The EPA server returned transient HTTP 502s mid-paging in the first full
        # run, so pages get more retries with longer backoff (5..30 s).
        page = http_get(endpoint, retries=6, params={
            "where": "1=1", "outFields": "*", "returnGeometry": "false",
            "orderByFields": ds["order_by"], "resultOffset": offset,
            "resultRecordCount": size, "f": "json"}).json()
        if "error" in page:
            raise IngestionError(f"ArcGIS error at offset {offset}: {str(page['error'])[:200]}")
        batch = page.get("features", [])
        if not batch:
            raise IngestionError(f"empty page at offset {offset} before reaching {expected}")
        features.extend(f["attributes"] for f in batch)
        offset += len(batch)
        if offset % 50_000 < size:
            log.info("  SLD records fetched: %s / %s", f"{offset:,}", f"{expected:,}")

    header = list(features[0].keys())
    lines = []
    for f in features:
        if list(f.keys()) != header:
            raise IngestionError("inconsistent attribute set across records")
        lines.append(json.dumps(f, ensure_ascii=False))
    data = ("\n".join(lines) + "\n").encode("utf-8")
    sha = sha256_bytes(data)
    save_snapshot(ds["source_id"], ds["snapshot_name"], data)

    checks = [
        Check("service_count_reconciled", "RECONCILIATION", "PASS" if len(features) == expected else "FAIL",
              expected=expected, actual=len(features), details="returnCountOnly vs records paged"),
        Check("snapshot_serialization", "SCHEMA", "PASS",
              details="NDJSON of attributes ordered by OBJECTID; numbers rendered with Python "
                      "shortest round-trip repr"),
    ]
    if len(features) != expected:
        raise IngestionError("SLD record count does not match service count")

    def records():
        for i, f in enumerate(features, start=1):
            yield i, [cell_to_str(v) for v in f.values()], ""

    row_check = make_row_check(
        ("natwalkind_outside_1_to_20",
         lambda r: not (is_number(r["NatWalkInd"]) and 1 <= float(r["NatWalkInd"]) <= 20), "WARN"),
        ("totpop_negative", lambda r: is_number(r["TotPop"]) and float(r["TotPop"]) < 0),
    )
    return build_extract(ds, snapshot_name=ds["snapshot_name"], snapshot_bytes=len(data), sha256=sha,
                         url_sanitized=endpoint + "?where=1=1&outFields=*&returnGeometry=false"
                                                  f"&orderByFields={ds['order_by']}&resultRecordCount={size}",
                         header=header, records=records, row_check=row_check, extra_checks=checks)
