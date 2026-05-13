#!/usr/bin/env python3
"""CLI wrapper for mia.crawler.crawl."""

import sys
from pathlib import Path as _Path
sys.path.insert(0, str(_Path(__file__).resolve().parent.parent))

import argparse
import json
from pathlib import Path

from mia.crawler import crawl


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--out", type=Path, default=Path("data/mia_raw"))
    p.add_argument("--max-pages", type=int, default=None)
    p.add_argument("--crawl-delay", type=float, default=1.1)
    p.add_argument("--timeout", type=int, default=30)
    p.add_argument("--progress-every", type=int, default=100)
    p.add_argument("--resume", action="store_true")
    p.add_argument("--seed", action="append", dest="seeds", default=None,
                   help="extra seed URL, use multiple times")
    args = p.parse_args()

    seeds = None
    if args.seeds:
        seeds = list(args.seeds)

    summary = crawl(
        out_dir=args.out,
        seeds=seeds,
        max_pages=args.max_pages,
        crawl_delay=args.crawl_delay,
        timeout=args.timeout,
        progress_every=args.progress_every,
        resume=args.resume,
    )
    print("Done.", json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
