#!/usr/bin/env python3
"""CLI wrapper for mia.cleaner.process_corpus."""

import sys
from pathlib import Path as _Path
sys.path.insert(0, str(_Path(__file__).resolve().parent.parent))

import argparse
import json
from pathlib import Path

from mia.cleaner import process_corpus


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--root", type=Path, required=True)
    p.add_argument("--out", type=Path, default=Path("data/mia_clean"))
    p.add_argument("--html-limit", type=int, default=None)
    p.add_argument("--pdf-limit", type=int, default=None)
    p.add_argument("--incremental", action="store_true")
    args = p.parse_args()

    stats = process_corpus(
        root_dir=args.root,
        out_dir=args.out,
        html_limit=args.html_limit,
        pdf_limit=args.pdf_limit,
        incremental=args.incremental,
    )
    print("Done.", json.dumps(stats, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
