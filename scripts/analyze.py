from __future__ import annotations

import argparse
import json

from fffb.analysis import summarize_csv


def main():
    p = argparse.ArgumentParser()
    p.add_argument("csv")
    args = p.parse_args()
    summary = summarize_csv(args.csv)
    print(json.dumps(summary, ensure_ascii=False, indent=2, default=lambda x: list(x) if isinstance(x, tuple) else str(x)))


if __name__ == "__main__":
    main()
