"""FAA sources: CY2025 commercial-service enplanements (S-17) and NASR APT_BASE (S-19).

Airports are landed with their native identifiers and coordinates only. No
airport is assigned to a market here: airport-to-CBSA rules are an open
Phase 4+ decision (A-009).
"""

from __future__ import annotations

from ..common import Check, Extract, IngestionError, http_get, looks_like_html, save_snapshot, sha256_bytes
from ._tabular import bad_lat, bad_lon, build_extract, delimited_records, is_number, make_row_check
from .census import xlsx_records, zip_delimited


def enplanements(ds: dict) -> Extract:
    resp = http_get(ds["url"])
    data = resp.content
    if not data or looks_like_html(data) or not data.startswith(b"PK"):
        raise IngestionError("expected an XLSX (zip) payload")
    sha = sha256_bytes(data)
    save_snapshot(ds["source_id"], ds["snapshot_name"], data)

    def classify(values):
        if all(v is None for v in values):
            return "blank row"
        # The sheet ends with summary counts: Rank empty, a count in the Locid column.
        if values[0] is None and isinstance(values[3], (int, float)):
            return "summary row (not an airport record)"
        return None

    header, records, _ = xlsx_records(data, ds["xlsx_header_row"], classify)
    checks = [Check("http_status", "ACQUISITION", "PASS", expected=200, actual=resp.status_code),
              Check("payload_is_xlsx", "ACQUISITION", "PASS", actual=f"{len(data):,} bytes")]
    has_cy25 = "CY 25 Enplanements" in header
    checks.append(Check("vintage_column_cy25_present", "SOURCE_SPECIFIC", "PASS" if has_cy25 else "FAIL",
                        expected="CY 25 Enplanements", actual=", ".join(h for h in header if h)))
    row_check = make_row_check(
        ("cy25_enplanements_not_non_negative_number",
         lambda r: not (is_number(r["CY 25 Enplanements"]) and float(r["CY 25 Enplanements"]) >= 0)),
        ("locid_missing", lambda r: not (r["Locid"] or "").strip()),
    )
    return build_extract(ds, snapshot_name=ds["snapshot_name"], snapshot_bytes=len(data), sha256=sha,
                         url_sanitized=ds["url"], header=header, records=records,
                         row_check=row_check, extra_checks=checks)


def nasr_apt_base(ds: dict) -> Extract:
    text, header, checks, nbytes, sha = zip_delimited(ds)
    expected_eff = ds["expected_values"]["EFF_DATE"]
    row_check = make_row_check(
        ("eff_date_not_pinned_edition", lambda r: r["EFF_DATE"] != expected_eff),
        ("latitude_out_of_range", lambda r: bad_lat(r["LAT_DECIMAL"]), "WARN"),
        ("longitude_out_of_range", lambda r: bad_lon(r["LONG_DECIMAL"]), "WARN"),
    )
    return build_extract(ds, snapshot_name=ds["snapshot_name"], snapshot_bytes=nbytes, sha256=sha,
                         url_sanitized=ds["url"], header=header,
                         records=delimited_records(text, ds["delimiter"], len(header)),
                         row_check=row_check, extra_checks=checks)
