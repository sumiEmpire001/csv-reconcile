import argparse
import csv
import json
import sys
from collections import Counter
from .engine import reconcile


def main():
    parser = argparse.ArgumentParser(description="Reconcile two UTF-8 CSV files using a temporary SQLite index")
    parser.add_argument("left")
    parser.add_argument("right")
    parser.add_argument("--keys", required=True, help="Comma-separated composite key columns")
    parser.add_argument("--decimals", default="", help="Comma-separated columns compared with Decimal")
    parser.add_argument("--trim", action="store_true")
    parser.add_argument("--exceptions-only", action="store_true")
    args = parser.parse_args()
    counts = Counter()
    try:
        for result in reconcile(args.left, args.right, args.keys.split(","), decimal_columns=[c for c in args.decimals.split(",") if c], trim=args.trim):
            counts[result["status"]] += 1
            if not args.exceptions_only or result["status"] != "matched":
                print(json.dumps(result, ensure_ascii=False))
        print(json.dumps({"summary": dict(counts)}), file=sys.stderr)
        if any(counts[status] for status in ("changed", "duplicate", "left_only", "right_only")):
            raise SystemExit(1)
    except (ValueError, OSError, csv.Error) as exc:
        parser.error(str(exc))


if __name__ == "__main__":
    main()
