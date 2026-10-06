"""Phase 6.5 research helper: batched, cached retrieval and text extraction of public sources.

Used only to gather public legal and regulatory texts for evidence curation. Nothing here writes to
Snowflake, and no credentials are used or sent.

  fetch_all(urls)      parallel GET with retries; every response is cached under
                       data/raw/phase65_research/ (git-ignored) keyed by a hash of the URL and
                       reused on later runs
  extract_all()        one pass that turns every cached PDF/HTML file into plain text (*.txt)
  discover(queries)    site-restricted discovery queries against DuckDuckGo's HTML endpoint;
                       results are leads to official pages only, never evidence

Usage: imported by ad-hoc research runs, e.g.
    python -c "import scripts.research_fetch as r; r.fetch_all([...])"
"""

from __future__ import annotations

import hashlib
import html
import io
import json
import re
import time
import urllib.parse
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import requests

ROOT = Path(__file__).resolve().parents[1]
CACHE = ROOT / "data" / "raw" / "phase65_research"
INDEX = CACHE / "index.json"
UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) "
      "Chrome/126.0 Safari/537.36 (independent public-policy research)")


def _key(url: str) -> str:
    return hashlib.sha1(url.encode()).hexdigest()[:16]


def _load_index() -> dict:
    return json.loads(INDEX.read_text(encoding="utf-8")) if INDEX.exists() else {}


def _get(url: str, retries: int = 3) -> dict:
    last = ""
    for attempt in range(retries):
        try:
            r = requests.get(url, headers={"User-Agent": UA, "Accept": "*/*"}, timeout=60, allow_redirects=True)
            kind = "pdf" if (r.content[:4] == b"%PDF" or "pdf" in r.headers.get("content-type", "")) else "html"
            return {"url": url, "status": r.status_code, "final_url": r.url, "kind": kind, "content": r.content}
        except requests.RequestException as exc:
            last = str(exc)[:200]
            time.sleep(2 * (attempt + 1))
    return {"url": url, "status": -1, "final_url": url, "kind": "error", "content": last.encode()}


def fetch_all(urls: list[str], workers: int = 8, refresh: bool = False) -> dict:
    """Fetch URLs in parallel; cached successes are reused. Returns {url: meta}."""
    CACHE.mkdir(parents=True, exist_ok=True)
    idx = _load_index()
    todo = [u for u in dict.fromkeys(urls) if refresh or u not in idx or idx[u]["status"] != 200]
    with ThreadPoolExecutor(max_workers=workers) as ex:
        for res in ex.map(_get, todo):
            k = _key(res["url"])
            ext = {"pdf": ".pdf", "html": ".html"}.get(res["kind"], ".err")
            (CACHE / f"{k}{ext}").write_bytes(res["content"])
            idx[res["url"]] = {"key": k, "file": f"{k}{ext}", "status": res["status"],
                               "final_url": res["final_url"], "kind": res["kind"]}
    INDEX.write_text(json.dumps(idx, indent=1), encoding="utf-8")
    return {u: idx[u] for u in urls if u in idx}


def _html_text(raw: bytes) -> str:
    s = raw.decode("utf-8", errors="replace")
    s = re.sub(r"(?is)<(script|style|noscript)\b.*?</\1>", " ", s)
    s = re.sub(r"(?i)<br\s*/?>|</(p|div|li|tr|h\d)>", "\n", s)
    s = re.sub(r"<[^>]+>", " ", s)
    s = html.unescape(s)
    return re.sub(r"[ \t\r\f\v]+", " ", re.sub(r"\n\s*\n+", "\n", s)).strip()


def extract_all() -> dict:
    """One pass: every cached .pdf/.html without a .txt companion gets one. Returns {file: chars}."""
    from pypdf import PdfReader
    out = {}
    for f in sorted(CACHE.glob("*")):
        if f.suffix not in (".pdf", ".html"):
            continue
        txt = f.with_suffix(".txt")
        if txt.exists():
            out[f.name] = txt.stat().st_size
            continue
        try:
            if f.suffix == ".pdf":
                text = "\n".join((p.extract_text() or "") for p in PdfReader(io.BytesIO(f.read_bytes())).pages)
            else:
                text = _html_text(f.read_bytes())
        except Exception as exc:  # noqa: BLE001 - record and continue
            text = f"[EXTRACTION FAILED: {exc}]"
        txt.write_text(text, encoding="utf-8")
        out[f.name] = len(text)
    return out


def text_of(url: str) -> str:
    meta = _load_index().get(url)
    if not meta:
        return ""
    p = CACHE / (meta["key"] + ".txt")
    return p.read_text(encoding="utf-8") if p.exists() else ""


def links_of(url: str) -> list[str]:
    meta = _load_index().get(url)
    if not meta or meta["kind"] != "html":
        return []
    raw = (CACHE / meta["file"]).read_bytes().decode("utf-8", errors="replace")
    base = meta["final_url"]
    return sorted({urllib.parse.urljoin(base, html.unescape(h)) for h in re.findall(r'href="([^"#]+)"', raw)})


def discover(queries: list[str]) -> dict[str, list[str]]:
    """DuckDuckGo HTML results (discovery leads only). Returns {query: [result urls]}."""
    urls = {q: "https://html.duckduckgo.com/html/?q=" + urllib.parse.quote_plus(q) for q in queries}
    fetch_all(list(urls.values()), workers=4)
    res = {}
    for q, u in urls.items():
        meta = _load_index().get(u)
        raw = (CACHE / meta["file"]).read_bytes().decode("utf-8", errors="replace") if meta else ""
        hits = re.findall(r'uddg=([^"&]+)', raw)
        res[q] = list(dict.fromkeys(urllib.parse.unquote(h) for h in hits))[:8]
    return res
