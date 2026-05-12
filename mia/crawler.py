#!/usr/bin/env python3
"""
Crawl raw HTML pages and PDF files from the Chinese section of marxists.org.

Extracted from crawl_mia_chinese.py with resume support.

Key functions:
  crawl, load_seen, save_seen, normalize_url, url_hash,
  build_session, ensure_dirs, in_scope, looks_like_binary_asset,
  content_type_of, detect_declared_encoding, decode_response_text,
  repair_mojibake_text, extract_links, append_jsonl
"""

from __future__ import annotations

import hashlib
import json
import re
import time
from collections import deque
from datetime import datetime
from pathlib import Path
from typing import Optional
from urllib.parse import urljoin, urlparse, urldefrag

import requests
from bs4 import BeautifulSoup
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry


# -----------------------------
# defaults (internal)
# -----------------------------

DEFAULT_SEEDS = [
    "https://www.marxists.org/chinese/",
    "https://www.marxists.org/chinese/pdf/marxism-library.htm",
]

DEFAULT_ALLOWED_HOST = "www.marxists.org"

DEFAULT_ALLOWED_PREFIXES = [
    "/chinese/",
]

DEFAULT_SKIP_PREFIXES = [
    "/chinese/update/",
]

DEFAULT_SKIP_EXTENSIONS = {
    ".jpg", ".jpeg", ".png", ".gif", ".svg", ".webp", ".ico",
    ".css", ".js", ".xml", ".zip", ".rar", ".7z", ".tar", ".gz",
    ".mp3", ".mp4", ".avi", ".mov", ".wmv", ".m4a", ".ogg",
    ".doc", ".docx", ".xls", ".xlsx", ".ppt", ".pptx",
    ".djvu", ".epub", ".mobi",
}

DEFAULT_USER_AGENT = "Mozilla/5.0 (compatible; mia-rag-crawler/0.1; internal research use)"

HTML_LIKE_TYPES = (
    "text/html",
    "application/xhtml+xml",
)

PDF_TYPES = (
    "application/pdf",
    "application/x-pdf",
)


# -----------------------------
# resume support
# -----------------------------

SEEN_SAVE_INTERVAL = 50


def load_seen(manifest_dir: Path) -> set[str]:
    """Load previously seen URLs from manifest/seen_urls.jsonl."""
    path = manifest_dir / "seen_urls.jsonl"
    seen: set[str] = set()
    if path.exists():
        with path.open("r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line:
                    try:
                        record = json.loads(line)
                        url = record.get("url", "")
                        if url:
                            seen.add(url)
                    except json.JSONDecodeError:
                        continue
    return seen


def save_seen(manifest_dir: Path, seen_set: set[str]) -> None:
    """Save seen URLs to manifest/seen_urls.jsonl (overwrite with current set)."""
    path = manifest_dir / "seen_urls.jsonl"
    path.parent.mkdir(parents=True, exist_ok=True)
    # Write all seen URLs atomically
    with path.open("w", encoding="utf-8") as f:
        for url in sorted(seen_set):
            f.write(json.dumps({"url": url}, ensure_ascii=False) + "\n")


# -----------------------------
# logging
# -----------------------------

def fmt_now() -> str:
    return datetime.now().strftime("%H:%M:%S")


def log_progress(
    stage: str,
    *,
    url: str | None = None,
    html_count: int | None = None,
    pdf_count: int | None = None,
    skipped_count: int | None = None,
    error_count: int | None = None,
    seen_count: int | None = None,
    queue_count: int | None = None,
) -> None:
    parts = [f"[{fmt_now()}]", stage]
    if url:
        parts.append(str(url))
    stats = []
    if html_count is not None:
        stats.append(f"html={html_count}")
    if pdf_count is not None:
        stats.append(f"pdf={pdf_count}")
    if skipped_count is not None:
        stats.append(f"skipped={skipped_count}")
    if error_count is not None:
        stats.append(f"errors={error_count}")
    if seen_count is not None:
        stats.append(f"seen={seen_count}")
    if queue_count is not None:
        stats.append(f"queue={queue_count}")
    if stats:
        parts.append("| " + " ".join(stats))
    print(" ".join(parts))


# -----------------------------
# core utilities
# -----------------------------

def build_session(user_agent: str = DEFAULT_USER_AGENT) -> requests.Session:
    session = requests.Session()
    retry = Retry(
        total=5,
        connect=5,
        read=5,
        backoff_factor=1.0,
        status_forcelist=[429, 500, 502, 503, 504],
        allowed_methods=["HEAD", "GET"],
        raise_on_status=False,
    )
    adapter = HTTPAdapter(max_retries=retry, pool_connections=20, pool_maxsize=20)
    session.mount("http://", adapter)
    session.mount("https://", adapter)
    session.headers.update({"User-Agent": user_agent})
    return session


def strip_fragment(url: str) -> str:
    return urldefrag(url)[0]


def normalize_url(url: str) -> str:
    url = strip_fragment(url)
    parsed = urlparse(url)
    scheme = parsed.scheme.lower() or "https"
    netloc = parsed.netloc.lower()
    path = re.sub(r"/{2,}", "/", parsed.path or "/")
    if not path.startswith("/"):
        path = "/" + path
    return parsed._replace(scheme=scheme, netloc=netloc, path=path, params="", fragment="").geturl()


def url_hash(url: str) -> str:
    return hashlib.md5(url.encode("utf-8")).hexdigest()


def ensure_dirs(out_dir: Path) -> dict[str, Path]:
    dirs = {
        "root": out_dir,
        "html": out_dir / "html",
        "html_utf8": out_dir / "html_utf8",
        "pdf": out_dir / "pdf",
        "manifest": out_dir / "manifest",
    }
    for p in dirs.values():
        p.mkdir(parents=True, exist_ok=True)
    return dirs


def in_scope(url: str, allowed_host: str, allowed_prefixes: list[str], skip_prefixes: list[str]) -> bool:
    parsed = urlparse(url)
    if parsed.netloc.lower() != allowed_host.lower():
        return False
    path = parsed.path or "/"
    if not any(path.startswith(prefix) for prefix in allowed_prefixes):
        return False
    if any(path.startswith(prefix) for prefix in skip_prefixes):
        return False
    return True


def looks_like_binary_asset(path: str, skip_extensions: set[str]) -> bool:
    lower = path.lower()
    return any(lower.endswith(ext) for ext in skip_extensions)


def safe_write_text(path: Path, text: str) -> None:
    path.write_text(text, encoding="utf-8", errors="ignore")


def append_jsonl(path: Path, record: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as f:
        f.write(json.dumps(record, ensure_ascii=False) + "\n")


def extract_links(base_url: str, html_text: str) -> list[str]:
    soup = BeautifulSoup(html_text, "lxml")
    links: list[str] = []
    for tag in soup.find_all("a", href=True):
        href = tag.get("href", "").strip()
        if not href:
            continue
        absolute = normalize_url(urljoin(base_url, href))
        links.append(absolute)
    return links


def content_type_of(resp: requests.Response) -> str:
    return (resp.headers.get("Content-Type") or "").split(";")[0].strip().lower()


def is_probably_pdf(url: str, content_type: str) -> bool:
    if url.lower().endswith(".pdf"):
        return True
    return content_type in PDF_TYPES


def is_probably_html(content_type: str) -> bool:
    return content_type in HTML_LIKE_TYPES


def fetch(session: requests.Session, url: str, timeout: int) -> requests.Response:
    return session.get(url, timeout=timeout)


def detect_declared_encoding(resp: requests.Response) -> str | None:
    """Detect encoding from HTTP header or HTML meta charset."""
    raw = resp.content

    # 1) HTTP header
    ct = resp.headers.get("Content-Type", "")
    m = re.search(r"charset=([^\s;]+)", ct, flags=re.I)
    if m:
        enc = m.group(1).strip("\"'").lower()
        if enc in {"gb2312", "gbk"}:
            enc = "gb18030"
        return enc

    # 2) HTML meta
    head_ascii = raw[:8192].decode("ascii", errors="ignore")
    m = re.search(r"charset=([a-zA-Z0-9_\-]+)", head_ascii, flags=re.I)
    if m:
        enc = m.group(1).lower()
        if enc in {"gb2312", "gbk"}:
            enc = "gb18030"
        return enc

    return None


def decode_response_text(resp: requests.Response) -> str:
    """Decode HTML more safely for older Chinese pages."""
    raw = resp.content

    candidates = []
    declared = detect_declared_encoding(resp)
    if declared:
        candidates.append(declared)

    if resp.encoding:
        candidates.append(resp.encoding.lower())
    if resp.apparent_encoding:
        candidates.append(resp.apparent_encoding.lower())

    candidates.extend(["gb18030", "big5", "utf-8", "latin-1"])

    seen = set()
    for enc in candidates:
        if not enc:
            continue
        enc = enc.lower()
        if enc in {"gb2312", "gbk"}:
            enc = "gb18030"
        if enc in seen:
            continue
        seen.add(enc)
        try:
            return raw.decode(enc, errors="ignore")
        except Exception:
            continue

    return raw.decode("utf-8", errors="ignore")


def repair_mojibake_text(text: str) -> str:
    """Try to repair common Chinese mojibake like 'Âí¿ËË¼...'."""
    try:
        repaired = text.encode("latin-1", errors="ignore").decode("gb18030", errors="ignore")
        cjk_orig = sum(1 for ch in text if "一" <= ch <= "鿿")
        cjk_new = sum(1 for ch in repaired if "一" <= ch <= "鿿")
        if cjk_new > cjk_orig:
            return repaired
    except Exception:
        pass
    return text


def guess_extension_from_content_type(content_type: str, default: str = "") -> str:
    ct = (content_type or "").lower()
    if "pdf" in ct:
        return ".pdf"
    if "html" in ct:
        return ".html"
    return default


# -----------------------------
# main crawl
# -----------------------------

def crawl(
    out_dir: Path,
    seeds: list[str] | None = None,
    max_pages: int | None = None,
    crawl_delay: float = 1.1,
    timeout: int = 30,
    user_agent: str = DEFAULT_USER_AGENT,
    progress_every: int = 25,
    resume: bool = False,
) -> dict:
    """BFS crawl starting from seeds.

    Parameters
    ----------
    out_dir : Path
        Output directory for crawled data.
    seeds : list[str] or None
        Seed URLs. Defaults to marxists.org Chinese homepage and PDF library.
    max_pages : int or None
        Maximum number of HTML+PDF resources to save before stopping.
    crawl_delay : float
        Seconds to delay between requests.
    timeout : int
        HTTP request timeout in seconds.
    user_agent : str
        User-Agent header value.
    progress_every : int
        Print summary every N saved resources.
    resume : bool
        If True, load previously seen URLs from manifest/seen_urls.jsonl
        and skip them.

    Returns
    -------
    dict
        Summary of crawl results.
    """
    if seeds is None:
        seeds = list(DEFAULT_SEEDS)

    allowed_host = DEFAULT_ALLOWED_HOST
    allowed_prefixes = list(DEFAULT_ALLOWED_PREFIXES)
    skip_prefixes = list(DEFAULT_SKIP_PREFIXES)
    skip_extensions = set(DEFAULT_SKIP_EXTENSIONS)

    dirs = ensure_dirs(out_dir)
    session = build_session(user_agent)

    pages_manifest = dirs["manifest"] / "pages.jsonl"
    pdfs_manifest = dirs["manifest"] / "pdfs.jsonl"
    errors_manifest = dirs["manifest"] / "errors.jsonl"
    summary_path = dirs["manifest"] / "summary.json"

    queue = deque(normalize_url(u) for u in seeds)
    seen: set[str] = set()
    queued: set[str] = set(queue)

    # Resume: load previously seen URLs and skip them
    if resume:
        previously_seen = load_seen(dirs["manifest"])
        seen.update(previously_seen)
        # Re-queue seeds if they weren't seen yet
        queue.clear()
        for s in seeds:
            u = normalize_url(s)
            if u not in seen:
                queue.append(u)
        queued = set(queue)
        log_progress(
            "RESUME",
            seen_count=len(seen),
            queue_count=len(queue),
        )

    html_count = 0
    pdf_count = 0
    skipped_count = 0
    error_count = 0
    save_count_since_checkpoint = 0

    last_request_at = 0.0
    last_progress_total = 0

    log_progress(
        "START",
        html_count=html_count,
        pdf_count=pdf_count,
        skipped_count=skipped_count,
        error_count=error_count,
        seen_count=len(seen),
        queue_count=len(queue),
    )

    while queue:
        if max_pages is not None and (html_count + pdf_count) >= max_pages:
            break

        url = queue.popleft()
        queued.discard(url)

        if url in seen:
            continue
        seen.add(url)

        parsed = urlparse(url)
        if not in_scope(url, allowed_host, allowed_prefixes, skip_prefixes):
            skipped_count += 1
            continue
        if looks_like_binary_asset(parsed.path, skip_extensions) and not parsed.path.lower().endswith(".pdf"):
            skipped_count += 1
            continue

        log_progress(
            "FETCH",
            url=url,
            html_count=html_count,
            pdf_count=pdf_count,
            skipped_count=skipped_count,
            error_count=error_count,
            seen_count=len(seen),
            queue_count=len(queue),
        )

        # Crawl-delay pacing
        wait = crawl_delay - (time.time() - last_request_at)
        if wait > 0:
            time.sleep(wait)

        try:
            resp = fetch(session, url, timeout=timeout)
            last_request_at = time.time()
            status = resp.status_code
            ct = content_type_of(resp)

            if status >= 400:
                error_count += 1
                append_jsonl(errors_manifest, {
                    "url": url,
                    "status_code": status,
                    "content_type": ct,
                    "error": f"HTTP {status}",
                    "ts": time.strftime("%Y-%m-%d %H:%M:%S"),
                })
                continue

            file_id = url_hash(url)
            total_saved_before = html_count + pdf_count

            if is_probably_pdf(url, ct):
                ext = guess_extension_from_content_type(ct, ".pdf") or ".pdf"
                raw_path = dirs["pdf"] / f"{file_id}{ext}"
                raw_path.write_bytes(resp.content)

                record = {
                    "id": file_id,
                    "url": url,
                    "status_code": status,
                    "content_type": ct,
                    "saved_path": str(raw_path),
                    "bytes": len(resp.content),
                    "ts": time.strftime("%Y-%m-%d %H:%M:%S"),
                }
                append_jsonl(pdfs_manifest, record)
                pdf_count += 1
                save_count_since_checkpoint += 1
                log_progress(
                    "SAVED PDF",
                    url=url,
                    html_count=html_count,
                    pdf_count=pdf_count,
                    skipped_count=skipped_count,
                    error_count=error_count,
                    seen_count=len(seen),
                    queue_count=len(queue),
                )
            elif is_probably_html(ct) or True:  # try even if content-type is ambiguous
                html_text = decode_response_text(resp)
                html_text = repair_mojibake_text(html_text)

                if is_probably_html(ct) or "<html" in html_text[:500].lower():
                    raw_path = dirs["html"] / f"{file_id}.html"
                    raw_path.write_bytes(resp.content)

                    utf8_path = dirs["html_utf8"] / f"{file_id}.html"
                    safe_write_text(utf8_path, html_text)

                    links = extract_links(url, html_text)
                    discovered = 0
                    for link in links:
                        lp = urlparse(link)
                        if not in_scope(link, allowed_host, allowed_prefixes, skip_prefixes):
                            continue
                        if looks_like_binary_asset(lp.path, skip_extensions) and not lp.path.lower().endswith(".pdf"):
                            continue
                        if link not in seen and link not in queued:
                            queue.append(link)
                            queued.add(link)
                            discovered += 1

                    title = ""
                    m = re.search(r"<title[^>]*>(.*?)</title>", html_text, flags=re.I | re.S)
                    if m:
                        title = re.sub(r"\s+", " ", m.group(1)).strip()

                    record = {
                        "id": file_id,
                        "url": url,
                        "status_code": status,
                        "content_type": ct,
                        "saved_path": str(raw_path),
                        "utf8_path": str(utf8_path),
                        "detected_encoding": detect_declared_encoding(resp),
                        "title": title,
                        "discovered_links": discovered,
                        "ts": time.strftime("%Y-%m-%d %H:%M:%S"),
                    }
                    append_jsonl(pages_manifest, record)
                    html_count += 1
                    save_count_since_checkpoint += 1
                    log_progress(
                        f"SAVED HTML (+{discovered} links)",
                        url=url,
                        html_count=html_count,
                        pdf_count=pdf_count,
                        skipped_count=skipped_count,
                        error_count=error_count,
                        seen_count=len(seen),
                        queue_count=len(queue),
                    )
                else:
                    skipped_count += 1
                    append_jsonl(errors_manifest, {
                        "url": url,
                        "status_code": status,
                        "content_type": ct,
                        "error": "Unsupported content type",
                        "ts": time.strftime("%Y-%m-%d %H:%M:%S"),
                    })
            else:
                skipped_count += 1
                append_jsonl(errors_manifest, {
                    "url": url,
                    "status_code": status,
                    "content_type": ct,
                    "error": "Unsupported content type",
                    "ts": time.strftime("%Y-%m-%d %H:%M:%S"),
                })

            # Periodic progress summary
            total_saved = html_count + pdf_count
            if progress_every > 0 and total_saved - last_progress_total >= progress_every:
                last_progress_total = total_saved
                log_progress(
                    "SUMMARY",
                    html_count=html_count,
                    pdf_count=pdf_count,
                    skipped_count=skipped_count,
                    error_count=error_count,
                    seen_count=len(seen),
                    queue_count=len(queue),
                )

            # Periodic seen_urls checkpoint (for resume)
            if save_count_since_checkpoint >= SEEN_SAVE_INTERVAL:
                save_seen(dirs["manifest"], seen)
                save_count_since_checkpoint = 0

        except KeyboardInterrupt:
            # Save progress on interrupt
            save_seen(dirs["manifest"], seen)
            raise
        except Exception as e:
            error_count += 1
            append_jsonl(errors_manifest, {
                "url": url,
                "error": repr(e),
                "ts": time.strftime("%Y-%m-%d %H:%M:%S"),
            })
            log_progress(
                f"ERROR {e!r}",
                url=url,
                html_count=html_count,
                pdf_count=pdf_count,
                skipped_count=skipped_count,
                error_count=error_count,
                seen_count=len(seen),
                queue_count=len(queue),
            )

    # Final save of seen URLs
    if resume:
        save_seen(dirs["manifest"], seen)

    summary = {
        "seeds": seeds,
        "allowed_host": allowed_host,
        "allowed_prefixes": allowed_prefixes,
        "skip_prefixes": skip_prefixes,
        "crawl_delay_seconds": crawl_delay,
        "html_count": html_count,
        "pdf_count": pdf_count,
        "skipped_count": skipped_count,
        "error_count": error_count,
        "seen_count": len(seen),
        "resumed": resume,
        "finished_at": time.strftime("%Y-%m-%d %H:%M:%S"),
        "html_note": "html/ stores original bytes; html_utf8/ stores normalized UTF-8 copies",
    }
    summary_path.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")

    return summary
