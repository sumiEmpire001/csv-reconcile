# CSV Reconcile

A disk-backed reconciliation engine for two UTF-8 CSV files. Match composite keys, inspect changed or missing records and review duplicate-key groups without arbitrary row selection. Built for Lord_Sumi's portfolio.

## Run

Python 3.10+; standard library only.

```bash
git clone https://github.com/sumiEmpire001/csv-reconcile.git
cd csv-reconcile
python -m unittest discover -s tests -v
python -m csv_reconcile left.csv right.csv --keys account_id,period --decimals amount --exceptions-only
```

The CLI prints JSON Lines to stdout and a category summary to stderr. Exit 0 means all key groups matched; exit 1 means reconciliation exceptions were found; exit 2 means invalid input or an operational error. Summary counts describe **key groups**, not raw input rows.

```python
from csv_reconcile import reconcile

for group in reconcile("left.csv", "right.csv", ["id"], decimal_columns=["amount"]):
    print(group["key"], group["status"])
```

## Matching rules

| Status | Meaning |
|---|---|
| matched | Exactly one row on each side, equal compared fields |
| changed | Exactly one row on each side, with explicit field differences |
| left_only / right_only | Key occurs on only one side |
| duplicate | More than one row on either side; bounded samples and full counts are returned |

Composite keys are encoded as JSON arrays, preventing delimiter collisions. Keys are exact strings, including leading zeros and case. Column order and row order may differ, but both files must have the same column-name set. Comparisons use exact strings by default; `--trim` explicitly strips surrounding whitespace, including key values. Decimal columns use Python `Decimal` equality, so `0.10` equals `0.1` without binary floating-point rounding. Nonfinite and invalid decimal values are rejected.

## Architecture and ownership

Both inputs are validated and streamed into a temporary SQLite database. Indexed grouping reconciles one key at a time, and duplicate examples are bounded by `sample_limit` (default 3). Source files are opened read-only and never edited. Temporary storage is removed when iteration finishes or the generator is closed. Exhaust or explicitly close a partially consumed generator to release resources promptly.

The database needs disk space proportional to both inputs. Python holds the current CSV row and bounded result samples; SQLite manages its own cache and query working space. This is a disk-backed design, not a guarantee of constant total resource use or unlimited file size.

## Validation and evidence

Local validation on 30 October 2026: **12 tests passed**. Tests cover 4,000-row reordered files, reordered columns, missing rows, field changes, duplicate samples, composite-key delimiter collisions, exact high-precision decimals, quoted newlines/commas, Unicode, whitespace policy, malformed row widths, column drift and invalid input. The 4,000-row fixture is functional verification, not a large-scale memory or throughput benchmark. GitHub Actions is configured separately for Python 3.10, 3.12 and 3.13.

## Limits

UTF-8 CSV with unique nonempty headers; no Excel workbook parser or GUI. The standard CSV parser's default field-size limit applies. Both column sets must match. Empty key values are rejected, and duplicate keys are reported rather than paired. No fuzzy matching, automatic record merges or monetary aggregation is performed. Freeze input files during reconciliation; the engine does not take filesystem snapshots. Input data is temporarily persisted in local SQLite and is not encrypted or securely erased. Files from untrusted sources may still consume substantial disk, CPU or parsing resources.

MIT license; see [LICENSE](LICENSE).
