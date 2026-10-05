"""Shared ingestion utilities: secret redaction, hashing, HTTP access, identifiers."""

from __future__ import annotations

import hashlib
import logging
import os
import re
import subprocess
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Iterator

import pandas as pd
import requests

REPO_ROOT = Path(__file__).resolve().parents[2]
RAW_CACHE = REPO_ROOT / "data" / "raw"

# Polite, descriptive User-Agent. No personal contact data is sent.
USER_AGENT = "autonomous-mobility-expansion/phase3 (independent portfolio research; python-requests)"

METADATA_COLUMNS = (
    "_INGEST_RUN_ID",
    "_INGESTED_AT",
    "_SOURCE_ID",
    "_SOURCE_VINTAGE",
    "_SOURCE_FILE",
    "_SOURCE_FILE_SHA256",
    "_SOURCE_ROW_NUMBER",
)

log = logging.getLogger("ingestion")


# --------------------------------------------------------------------------- #
# Exceptions
# --------------------------------------------------------------------------- #
class IngestionError(RuntimeError):
    """A source failed acquisition, validation or load (status FAILED)."""


class BlockedError(IngestionError):
    """Automated access was refused, or a pinned snapshot changed (status BLOCKED)."""


# --------------------------------------------------------------------------- #
# Secret redaction
# --------------------------------------------------------------------------- #
_KEY_PARAM = re.compile(r"(?i)([?&]key=)[^&\s'\"]+")


def sanitize(text: object) -> str:
    """Remove the Census API key (by value and by URL parameter) from text."""
    s = str(text)
    secret = os.getenv("CENSUS_API_KEY", "").strip()
    if secret:
        s = s.replace(secret, "<redacted>")
    return _KEY_PARAM.sub(r"\1<redacted>", s)


class RedactingFilter(logging.Filter):
    def filter(self, record: logging.LogRecord) -> bool:
        record.msg = sanitize(record.getMessage())
        record.args = ()
        return True


def configure_logging(level: int = logging.INFO) -> None:
    handler = logging.StreamHandler()
    handler.setFormatter(logging.Formatter("%(asctime)s %(levelname)-5s %(message)s", "%H:%M:%S"))
    handler.addFilter(RedactingFilter())
    root = logging.getLogger()
    root.handlers[:] = [handler]
    root.setLevel(level)
    # Third-party loggers can print full request URLs (with the API key) at DEBUG.
    for noisy in ("urllib3", "requests", "snowflake", "botocore"):
        logging.getLogger(noisy).setLevel(logging.WARNING)


# --------------------------------------------------------------------------- #
# Hashing and snapshots
# --------------------------------------------------------------------------- #
def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest().upper()


# Snapshots are held until the run outcome is known, so a drifted or failed
# retrieval can never overwrite the snapshot that was actually loaded.
_PENDING: dict[Path, bytes] = {}


def save_snapshot(source_id: str, name: str, data: bytes) -> Path:
    """Stage a snapshot for writing; finalize_snapshots() decides where it goes."""
    path = RAW_CACHE / source_id / name
    _PENDING[path] = data
    return path


def finalize_snapshots(status: str) -> list[str]:
    """Write staged snapshots once the outcome is known.

    SUCCEEDED / SKIPPED_IDENTICAL -> deterministic name (the loaded content).
    FAILED / BLOCKED              -> '<name>.rejected-<sha12>' beside it, so the
                                     loaded snapshot is never overwritten.
    """
    written = []
    for path, data in _PENDING.items():
        path.parent.mkdir(parents=True, exist_ok=True)
        if status not in ("SUCCEEDED", "SKIPPED_IDENTICAL"):
            path = path.with_name(f"{path.name}.rejected-{sha256_bytes(data)[:12]}")
        path.write_bytes(data)
        written.append(path.name)
    _PENDING.clear()
    return written


def git_commit() -> str:
    try:
        sha = subprocess.run(["git", "rev-parse", "--short", "HEAD"], cwd=REPO_ROOT,
                             capture_output=True, text=True, check=True).stdout.strip()
        dirty = subprocess.run(["git", "status", "--porcelain"], cwd=REPO_ROOT,
                               capture_output=True, text=True, check=True).stdout.strip()
        return sha + ("-dirty" if dirty else "")
    except Exception:  # noqa: BLE001 - informational only
        return "unknown"


# --------------------------------------------------------------------------- #
# HTTP
# --------------------------------------------------------------------------- #
_session = requests.Session()
_session.headers["User-Agent"] = USER_AGENT


def http_get(url: str, params: dict | None = None, timeout: int = 600,
             retries: int = 3) -> requests.Response:
    """GET with retries for transient failures.

    Access refusals (401/403/429) raise BlockedError immediately: they are
    not retried and never worked around.
    """
    last: Exception | None = None
    for attempt in range(1, retries + 1):
        try:
            resp = _session.get(url, params=params, timeout=timeout)
        except requests.RequestException as exc:
            last = exc
        else:
            if resp.status_code in (401, 403, 429):
                raise BlockedError(f"HTTP {resp.status_code} refused by {sanitize(url)}")
            if resp.status_code < 400:
                return resp
            if resp.status_code < 500:
                # Not resp.raise_for_status(): its message contains the full URL.
                raise IngestionError(f"HTTP {resp.status_code} from {sanitize(url)}: "
                                     f"{sanitize(resp.text[:200])}")
            last = IngestionError(f"HTTP {resp.status_code} from {sanitize(url)}")
        time.sleep(5 * attempt)
    raise IngestionError(sanitize(f"GET failed after {retries} attempts: {last}"))


def looks_like_html(data: bytes) -> bool:
    head = data[:512].lstrip().lower()
    return head.startswith(b"<!doctype html") or head.startswith(b"<html")


# --------------------------------------------------------------------------- #
# Identifiers
# --------------------------------------------------------------------------- #
def snowflake_column(name: str) -> str:
    """Map a source column name to a Snowflake-safe identifier.

    Uppercase; '%' -> 'PCT'; any other non-alphanumeric run -> '_'; a name that
    starts with a digit gets a 'C_' prefix. Leading underscores are reserved
    for ingestion metadata columns.
    """
    s = str(name).strip().replace("%", "PCT")
    s = re.sub(r"[^0-9A-Za-z]+", "_", s).strip("_").upper()
    if not s:
        s = "UNNAMED"
    if s[0].isdigit():
        s = "C_" + s
    return s


def column_mapping(columns: list[str]) -> dict[str, str]:
    """Source -> Snowflake column names; raise on collisions."""
    mapping = {c: snowflake_column(c) for c in columns}
    seen: dict[str, str] = {}
    for src, dst in mapping.items():
        if dst in seen:
            raise IngestionError(f"Column name collision: {seen[dst]!r} and {src!r} -> {dst}")
        seen[dst] = src
    return mapping


# --------------------------------------------------------------------------- #
# Extraction result
# --------------------------------------------------------------------------- #
@dataclass
class Check:
    name: str
    check_type: str
    status: str               # PASS / WARN / FAIL
    expected: object = None
    actual: object = None
    details: str = ""


@dataclass
class Reject:
    row_number: int | None
    reason: str
    record_text: str


@dataclass
class Extract:
    """Everything an extractor produces for one dataset.

    `frames` yields DataFrames of source columns only, with every value a
    string (or None) and a `_SOURCE_ROW_NUMBER` column. Frames are consumed
    once.
    """
    snapshot_name: str
    snapshot_bytes: int
    sha256: str
    url_sanitized: str
    frames: Iterator[pd.DataFrame] | None = None
    source_row_count: int | None = None   # known before parsing, if available
    columns: list[str] = field(default_factory=list)
    variant_columns: tuple[str, ...] = ()
    checks: list[Check] = field(default_factory=list)
    rejects: list[Reject] = field(default_factory=list)
    column_renames: dict[str, str] = field(default_factory=dict)
    # Re-iterable record source (row_no, values|None, raw); used for content
    # fingerprints when a re-baseline must prove the content is unchanged.
    record_factory: object = None
