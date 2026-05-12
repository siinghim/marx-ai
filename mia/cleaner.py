#!/usr/bin/env python3
"""
Clean crawled marxists.org Chinese corpus into a reviewable document corpus.

Extracted from clean_mia_corpus.py with incremental mode support.

Key functions:
  load_manifest, process_one_html, process_one_pdf, process_corpus,
  load_processed_files, load_text_hashes, save_text_hashes,
  normalize_text, is_index_like, extract_author_hint, extract_date_hint,
  extract_html_main_text, extract_pdf_text
"""

from __future__ import annotations

import hashlib
import json
import random
import re
from collections import Counter
from pathlib import Path

import fitz  # PyMuPDF
from bs4 import BeautifulSoup
from tqdm import tqdm


# -----------------------------
# io helpers
# -----------------------------

def load_jsonl(path: Path) -> list[dict]:
    rows = []
    if not path.exists():
        return rows
    with path.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                rows.append(json.loads(line))
    return rows


def write_jsonl(path: Path, rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        for row in rows:
            f.write(json.dumps(row, ensure_ascii=False) + "\n")


def append_jsonl(path: Path, row: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as f:
        f.write(json.dumps(row, ensure_ascii=False) + "\n")


def md5_text(text: str) -> str:
    return hashlib.md5(text.encode("utf-8")).hexdigest()


# -----------------------------
# manifest loading
# -----------------------------

def load_manifest(manifest_dir: Path) -> tuple[dict, dict]:
    """Load page and pdf manifests from manifest_dir."""
    pages = load_jsonl(manifest_dir / "pages.jsonl")
    pdfs = load_jsonl(manifest_dir / "pdfs.jsonl")

    page_map = {}
    for x in pages:
        key = Path(x.get("utf8_path", x.get("saved_path", ""))).name
        if key:
            page_map[key] = x

    pdf_map = {}
    for x in pdfs:
        key = Path(x.get("saved_path", "")).name
        if key:
            pdf_map[key] = x

    return page_map, pdf_map


# -----------------------------
# incremental support
# -----------------------------

def load_processed_files(out_dir: Path) -> set[str]:
    """Load set of raw_file paths already processed from docs_clean.jsonl."""
    docs = load_jsonl(out_dir / "docs_clean.jsonl")
    return {d.get("raw_file", "") for d in docs if d.get("raw_file")}


def load_text_hashes(out_dir: Path) -> dict[str, str]:
    """Load dict of text_hash -> doc_id from text_hashes.jsonl."""
    rows = load_jsonl(out_dir / "text_hashes.jsonl")
    return {r["text_hash"]: r["doc_id"] for r in rows if "text_hash" in r and "doc_id" in r}


def save_text_hashes(out_dir: Path, mapping: dict[str, str]) -> None:
    """Save text_hashes mapping to text_hashes.jsonl."""
    rows = [{"text_hash": k, "doc_id": v} for k, v in mapping.items()]
    path = out_dir / "text_hashes.jsonl"
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        for row in rows:
            f.write(json.dumps(row, ensure_ascii=False) + "\n")


# -----------------------------
# normalization / extraction
# -----------------------------

DROP_EXACT_LINES = {
    "中文马克思主义文库",
    "PDF文库",
    "->",
    "说明",
    "参考",
    "返回",
    "上一页",
    "下一页",
}

DROP_REGEXES = [
    re.compile(r"^\s*中文马克思主义文库\s*$"),
    re.compile(r"^\s*PDF文库\s*$", re.I),
    re.compile(r"^\s*返回(目录|首页)?\s*$"),
    re.compile(r"^\s*上一页\s*$"),
    re.compile(r"^\s*下一页\s*$"),
]

AUTHOR_HINTS = [
    "马克思", "恩格斯", "列宁", "斯大林", "毛泽东", "托洛茨基", "罗莎·卢森堡",
    "王明", "陈独秀", "杜波依斯", "W. E. B. Du Bois", "Du Bois",
]

DATE_PATTERNS = [
    re.compile(r"\d{4}年\d{1,2}月\d{1,2}日"),
    re.compile(r"\d{4}年\d{1,2}月"),
    re.compile(r"\d{4}年"),
]


def clean_url(url: str) -> str:
    if not url:
        return ""
    return re.sub(r"\s+", "", url)


def looks_like_noise_line(line: str) -> bool:
    if not line:
        return True
    if line in DROP_EXACT_LINES:
        return True
    for pat in DROP_REGEXES:
        if pat.search(line):
            return True
    return False


def normalize_whitespace(text: str) -> str:
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"　+", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def normalize_text(text: str, title: str = "") -> str:
    lines = [x.strip() for x in text.splitlines() if x.strip()]

    kept = []
    seen_title = False
    for i, line in enumerate(lines):
        if looks_like_noise_line(line):
            continue

        # drop title if duplicated as first body line
        if title and i < 3 and line == title and not seen_title:
            seen_title = True
            continue

        # drop breadcrumb-ish tiny arrows / separators
        if line in {"-", "--", "—", ">>", "›", ":"}:
            continue

        kept.append(line)

    text = "\n".join(kept)
    text = normalize_whitespace(text)

    # fix obvious line-break artifacts
    text = re.sub(r"(\d)\n([年月日号页])", r"\1\2", text)
    text = re.sub(r"([一-龥])\n([一-龥])", r"\1\2", text)
    text = re.sub(r"([a-zA-Z])\n([a-zA-Z])", r"\1\2", text)

    # keep paragraph boundaries, but merge isolated short numeric lines into neighbors
    lines = [x.strip() for x in text.splitlines() if x.strip()]
    merged = []
    i = 0
    while i < len(lines):
        cur = lines[i]
        if (
            i + 1 < len(lines)
            and len(cur) <= 6
            and re.fullmatch(r"[0-9一二三四五六七八九十百千万〇○\-—]+", cur)
        ):
            merged.append(cur + lines[i + 1])
            i += 2
            continue
        merged.append(cur)
        i += 1

    text = "\n".join(merged)
    text = normalize_whitespace(text)
    return text


def extract_date_hint(text: str) -> str:
    head = text[:1200]
    for pat in DATE_PATTERNS:
        m = pat.search(head)
        if m:
            return m.group(0)
    return ""


def extract_author_hint(title: str, text: str) -> str:
    sample = f"{title}\n{text[:500]}"
    for name in AUTHOR_HINTS:
        if name in sample:
            return name
    # heuristic: title prefix like "列宁：..."
    m = re.match(r"^([^：:]{1,12})[：:]", title)
    if m:
        return m.group(1).strip()
    return ""


def is_index_like(url: str, title: str, text: str, soup: BeautifulSoup | None = None) -> tuple[bool, dict]:
    """
    Transparent heuristic classifier.
    Returns (is_index_like, feature_debug)
    """
    features = {
        "url_index_suffix": False,
        "title_library_prefix": False,
        "avg_line_len": 0.0,
        "short_line_ratio": 0.0,
        "link_count": 0,
        "text_len": len(text),
        "title_list_ratio": 0.0,
    }

    score_index = 0
    score_article = 0

    url_low = clean_url(url).lower()
    if url_low.endswith("/index.htm") or url_low.endswith("/index.html"):
        features["url_index_suffix"] = True
        score_index += 3

    if "中文马克思主义文库·" in title or title.endswith("作品目录"):
        features["title_library_prefix"] = True
        score_index += 2

    lines = [x.strip() for x in text.splitlines() if x.strip()]
    if lines:
        avg_line_len = sum(len(x) for x in lines) / len(lines)
        short_line_ratio = sum(1 for x in lines if len(x) < 30) / len(lines)
        # lines that look like titles / list items rather than prose
        titleish_ratio = sum(
            1 for x in lines
            if len(x) < 45 and ("（" in x or "《" in x or re.search(r"\d{4}年", x))
        ) / len(lines)

        features["avg_line_len"] = round(avg_line_len, 2)
        features["short_line_ratio"] = round(short_line_ratio, 3)
        features["title_list_ratio"] = round(titleish_ratio, 3)

        if avg_line_len < 28:
            score_index += 2
        if short_line_ratio > 0.65:
            score_index += 2
        if titleish_ratio > 0.35:
            score_index += 1

        if len(text) > 1500 and avg_line_len > 40:
            score_article += 2
        if short_line_ratio < 0.45:
            score_article += 1

    if soup is not None:
        link_count = len(soup.find_all("a"))
        features["link_count"] = link_count
        if link_count > 40:
            score_index += 1

    # article clues
    if re.search(r"（\d{4}年|\d{4}年\d+月", title + "\n" + text[:800]):
        score_article += 1
    if re.search(r"[。！？；]\n", text[:2000]) or "无产者" in text[:1000]:
        score_article += 1

    is_index = score_index >= score_article + 2
    features["score_index"] = score_index
    features["score_article"] = score_article
    return is_index, features


def extract_html_main_text(html: str) -> tuple[str, str, BeautifulSoup]:
    soup = BeautifulSoup(html, "lxml")

    for tag in soup(["script", "style", "noscript"]):
        tag.decompose()

    title = ""
    if soup.title:
        title = soup.title.get_text(" ", strip=True)

    # Try body first
    container = soup.body if soup.body else soup
    text = container.get_text("\n", strip=True)
    text = normalize_whitespace(text)
    return title, text, soup


def extract_pdf_text(pdf_path: Path) -> tuple[str, str]:
    doc = fitz.open(pdf_path)
    pages = []
    title = ""

    # sometimes metadata title is useful
    meta_title = ""
    try:
        meta_title = (doc.metadata or {}).get("title", "") or ""
    except Exception:
        meta_title = ""
    if meta_title:
        title = meta_title.strip()

    for i, page in enumerate(doc):
        txt = page.get_text("text", sort=True)
        if txt and txt.strip():
            pages.append(txt.strip())

    text = "\n\n".join(pages)
    text = normalize_whitespace(text)

    # if metadata title missing, try first meaningful line
    if not title:
        for line in text.splitlines()[:10]:
            line = line.strip()
            if line and 4 <= len(line) <= 80:
                title = line
                break

    return title, text


# -----------------------------
# processors
# -----------------------------

def process_one_html(fp: Path, meta: dict) -> tuple[dict | None, dict | None]:
    html = fp.read_text(encoding="utf-8", errors="ignore")
    title, raw_text, soup = extract_html_main_text(html)
    url = clean_url(meta.get("url", ""))

    text = normalize_text(raw_text, title=title)
    is_index, feature_debug = is_index_like(url, title, text, soup=soup)

    record = {
        "doc_id": md5_text(f"html:{url or fp.name}"),
        "source_type": "html",
        "page_type": "index" if is_index else "article",
        "title": title or meta.get("title", ""),
        "url": url,
        "author_hint": extract_author_hint(title or meta.get("title", ""), text),
        "date_hint": extract_date_hint(text),
        "text": text,
        "raw_file": str(fp),
        "text_hash": md5_text(text),
        "char_count": len(text),
        "feature_debug": feature_debug,
    }

    # drop obvious non-content / too short pages
    if len(text) < 180:
        drop = dict(record)
        drop["drop_reason"] = "too_short"
        return None, drop

    if is_index:
        drop = dict(record)
        drop["drop_reason"] = "index_like_page"
        return None, drop

    return record, None


def process_one_pdf(fp: Path, meta: dict) -> tuple[dict | None, dict | None]:
    try:
        title, text = extract_pdf_text(fp)
    except Exception as e:
        return None, {
            "doc_id": md5_text(f"pdf:{fp.name}"),
            "source_type": "pdf",
            "page_type": "unknown",
            "title": fp.name,
            "url": clean_url(meta.get("url", "")),
            "raw_file": str(fp),
            "drop_reason": f"pdf_extract_failed:{type(e).__name__}",
            "char_count": 0,
        }

    text = normalize_text(text, title=title)

    record = {
        "doc_id": md5_text(f"pdf:{meta.get('url', fp.name)}"),
        "source_type": "pdf",
        "page_type": "article",
        "title": title or fp.name,
        "url": clean_url(meta.get("url", "")),
        "author_hint": extract_author_hint(title or fp.name, text),
        "date_hint": extract_date_hint(text),
        "text": text,
        "raw_file": str(fp),
        "text_hash": md5_text(text),
        "char_count": len(text),
    }

    if len(text) < 180:
        drop = dict(record)
        drop["drop_reason"] = "too_short"
        return None, drop

    return record, None


# -----------------------------
# corpus processing (with incremental support)
# -----------------------------

def _deduplicate_docs(docs: list[dict], existing_text_hashes: dict[str, str]) -> tuple[list[dict], list[dict]]:
    """Deduplicate docs against existing hashes and among themselves.

    Returns (kept, dropped).
    """
    kept = []
    dropped = []
    seen_hash = dict(existing_text_hashes)  # copy so we can add new ones

    for doc in docs:
        h = doc["text_hash"]
        if h in seen_hash:
            drop = dict(doc)
            drop["drop_reason"] = "duplicate_text"
            drop["kept_doc_id"] = seen_hash[h]
            dropped.append(drop)
        else:
            seen_hash[h] = doc["doc_id"]
            kept.append(doc)

    return kept, dropped


def process_corpus(
    root_dir: Path,
    out_dir: Path,
    html_limit: int | None = None,
    pdf_limit: int | None = None,
    incremental: bool = False,
) -> dict:
    """Process crawled corpus: extract, classify, deduplicate, and save.

    Parameters
    ----------
    root_dir : Path
        Crawl root directory (e.g. data/mia_raw) containing html_utf8/,
        pdf/, manifest/.
    out_dir : Path
        Clean output directory.
    html_limit : int or None
        Limit number of HTML files to process.
    pdf_limit : int or None
        Limit number of PDF files to process.
    incremental : bool
        If True, skip already-processed raw files and append new docs
        without overwriting existing output.

    Returns
    -------
    dict
        Statistics about the processing run.
    """
    html_dir = root_dir / "html_utf8"
    pdf_dir = root_dir / "pdf"
    manifest_dir = root_dir / "manifest"

    out_dir.mkdir(parents=True, exist_ok=True)

    page_map, pdf_map = load_manifest(manifest_dir)

    # --- incremental setup ---
    processed_files: set[str] = set()
    text_hashes: dict[str, str] = {}
    if incremental:
        processed_files = load_processed_files(out_dir)
        text_hashes = load_text_hashes(out_dir)

    # --- collect and filter HTML files ---
    html_files = sorted(html_dir.glob("*.html")) if html_dir.exists() else []
    if html_limit is not None:
        html_files = html_files[:html_limit]
    if incremental and processed_files:
        html_files = [fp for fp in html_files if str(fp) not in processed_files]

    # --- collect and filter PDF files ---
    pdf_files = sorted(pdf_dir.glob("*.pdf")) if pdf_dir.exists() else []
    if pdf_limit is not None:
        pdf_files = pdf_files[:pdf_limit]
    if incremental and processed_files:
        pdf_files = [fp for fp in pdf_files if str(fp) not in processed_files]

    # --- process HTML ---
    html_docs: list[dict] = []
    html_drops: list[dict] = []
    for fp in tqdm(html_files, desc="clean HTML"):
        meta = page_map.get(fp.name, {})
        doc, drop = process_one_html(fp, meta)
        if doc:
            html_docs.append(doc)
        if drop:
            html_drops.append(drop)

    # --- process PDF ---
    pdf_docs: list[dict] = []
    pdf_drops: list[dict] = []
    for fp in tqdm(pdf_files, desc="clean PDF"):
        meta = pdf_map.get(fp.name, {})
        doc, drop = process_one_pdf(fp, meta)
        if doc:
            pdf_docs.append(doc)
        if drop:
            pdf_drops.append(drop)

    docs = html_docs + pdf_docs
    pre_dedup_count = len(docs)

    # --- dedup ---
    docs, dedup_drops = _deduplicate_docs(docs, text_hashes)
    drops = html_drops + pdf_drops + dedup_drops

    # --- write output ---
    docs_path = out_dir / "docs_clean.jsonl"
    dropped_path = out_dir / "dropped_docs.jsonl"
    stats_path = out_dir / "stats.json"

    if incremental and docs_path.exists():
        # Append new docs
        for doc in docs:
            append_jsonl(docs_path, doc)
        for drop in drops:
            append_jsonl(dropped_path, drop)
        # Update text_hashes with newly seen ones
        for doc in docs:
            text_hashes[doc["text_hash"]] = doc["doc_id"]
        save_text_hashes(out_dir, text_hashes)
    else:
        write_jsonl(docs_path, docs)
        write_jsonl(dropped_path, drops)
        # Save text hashes from this run
        new_hashes = {doc["text_hash"]: doc["doc_id"] for doc in docs}
        save_text_hashes(out_dir, new_hashes)

    # --- stats ---
    total_html_input = len(sorted(html_dir.glob("*.html"))) if html_dir.exists() else 0
    total_pdf_input = len(sorted(pdf_dir.glob("*.pdf"))) if pdf_dir.exists() else 0

    stats = _summarize_stats(
        docs,
        drops,
        html_total=html_limit if html_limit is not None else total_html_input,
        pdf_total=pdf_limit if pdf_limit is not None else total_pdf_input,
    )
    stats["pre_dedup_doc_count"] = pre_dedup_count
    stats["final_output_path"] = str(docs_path)

    with stats_path.open("w", encoding="utf-8") as f:
        json.dump(stats, f, ensure_ascii=False, indent=2)

    # --- review samples ---
    _export_review_samples(out_dir, docs, drops, n=20)

    return stats


# -----------------------------
# reporting
# -----------------------------

def _summarize_stats(kept_docs: list[dict], dropped_docs: list[dict], html_total: int, pdf_total: int) -> dict:
    kept_counter = Counter((x["source_type"], x.get("page_type", "unknown")) for x in kept_docs)
    drop_reasons = Counter(x.get("drop_reason", "unknown") for x in dropped_docs)

    avg_char = round(sum(x["char_count"] for x in kept_docs) / max(1, len(kept_docs)), 2) if kept_docs else 0
    median_char = sorted(x["char_count"] for x in kept_docs)[len(kept_docs) // 2] if kept_docs else 0

    stats = {
        "html_total_input": html_total,
        "pdf_total_input": pdf_total,
        "final_docs": len(kept_docs),
        "dropped_docs": len(dropped_docs),
        "kept_by_type": {
            "html_article": kept_counter.get(("html", "article"), 0),
            "html_mixed": kept_counter.get(("html", "mixed"), 0),
            "html_unknown": kept_counter.get(("html", "unknown"), 0),
            "pdf_article": kept_counter.get(("pdf", "article"), 0),
        },
        "drop_reasons": dict(drop_reasons),
        "avg_char_count": avg_char,
        "median_char_count_approx": median_char,
    }
    return stats


def _export_review_samples(out_dir: Path, kept_docs: list[dict], dropped_docs: list[dict], n: int = 20) -> None:
    review_dir = out_dir / "review_samples"
    review_dir.mkdir(parents=True, exist_ok=True)

    kept_articles = [x for x in kept_docs if x["source_type"] == "html" and x.get("page_type") == "article"]
    dropped_indexes = [x for x in dropped_docs if x.get("drop_reason") == "index_like_page"]

    random.seed(42)
    write_jsonl(review_dir / "kept_article_samples.jsonl", random.sample(kept_articles, min(n, len(kept_articles))))
    write_jsonl(review_dir / "dropped_index_samples.jsonl", random.sample(dropped_indexes, min(n, len(dropped_indexes))))
