"""NOAA NCEI Historical Observing Metadata Repository (HOMR): Enhanced Master Station History
Report, Lite edition (S-41). Phase 6 controlled source extension.

Why: the W5 station rule needs an authoritative station CLASS. The GHCN-Daily identifier prefix
'USW' only says the station is numbered by WBAN (GHCN-Daily readme, section IV); it does not
establish a network. EMSHR field TYPE lists the "station type and/or platforms station
participates in" for each history period, including PLCD = Primary Local Climatological Data
(Reference Table B of MSHR_Enhanced_Lite_Table.txt).

The file is fixed-width. Column positions are read from the dashed separator line under the
header, so the layout is taken from the file itself. Every record is landed as published; the
file has no unique record key (one station can hold several records for the same period), so
no natural key is enforced and _SOURCE_ROW_NUMBER identifies records.

NCEI republishes the file in place. The zip member name carries the edition (e.g.
emshr_lite_202609.txt), and the run fails unless it matches the pinned edition, so a newer edition
can never be landed silently.
"""

from __future__ import annotations

import io
import re
import zipfile

from ..common import Check, Extract, IngestionError, http_get, save_snapshot, sha256_bytes
from ._tabular import build_extract, make_row_check

_DATE = re.compile(r"^\d{8}$")


def emshr_lite(ds: dict) -> Extract:
    resp = http_get(ds["url"])
    data = resp.content
    if not data.startswith(b"PK"):
        raise IngestionError("expected a zip payload")
    sha = sha256_bytes(data)
    save_snapshot(ds["source_id"], ds["snapshot_name"], data)

    with zipfile.ZipFile(io.BytesIO(data)) as z:
        members = z.namelist()
        if members != [ds["zip_member"]]:
            raise IngestionError(f"edition changed: archive holds {members}, pinned {ds['zip_member']}")
        lines = z.read(ds["zip_member"]).decode(ds.get("encoding", "latin-1")).splitlines()

    header, dashes = lines[0], lines[1]
    spans = [(m.start(), m.end()) for m in re.finditer(r"-+", dashes)]
    names = [header[a:b].strip() for a, b in spans]
    spans[-1] = (spans[-1][0], None)                      # last field runs to end of line
    if names != ds["expected_header"]:
        raise IngestionError(f"layout changed: {names}")
    body = lines[2:]

    def records():
        for i, line in enumerate(body, start=1):
            if not line.strip():
                yield i, None, "blank line"
            else:
                yield i, [line[a:b].strip() or None for a, b in spans], ""

    checks = [
        Check("http_status", "ACQUISITION", "PASS", expected=200, actual=resp.status_code),
        Check("pinned_edition_member", "SOURCE_SPECIFIC", "PASS", expected=ds["zip_member"], actual=members[0]),
        Check("fixed_width_layout", "SCHEMA", "PASS", actual=len(names),
              details="column spans read from the dashed separator line"),
    ]
    row_check = make_row_check(
        ("beg_dt_not_yyyymmdd", lambda r: not _DATE.match(r["BEG_DT"] or ""), "WARN"),
        ("end_dt_not_yyyymmdd", lambda r: not _DATE.match(r["END_DT"] or ""), "WARN"),
        ("ncdc_id_missing", lambda r: not r["NCDC"]),
    )
    return build_extract(ds, snapshot_name=ds["snapshot_name"], snapshot_bytes=len(data), sha256=sha,
                         url_sanitized=ds["url"], header=names, records=records,
                         row_check=row_check, extra_checks=checks)
