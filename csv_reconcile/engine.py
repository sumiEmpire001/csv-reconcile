"""Disk-backed reconciliation with composite keys and explicit duplicate groups."""
import csv
import json
import sqlite3
import tempfile
from decimal import Decimal, InvalidOperation


def reconcile(left, right, keys, *, decimal_columns=(), trim=False, sample_limit=3):
    if not isinstance(keys, (list, tuple)) or not keys:
        raise ValueError("keys must be a nonempty list of unique column names")
    if not all(isinstance(key, str) and key for key in keys):
        raise ValueError("Key column names must be nonempty strings")
    if len(set(keys)) != len(keys):
        raise ValueError("Key column names must be unique")
    if type(trim) is not bool:
        raise ValueError("trim must be a boolean")
    if type(sample_limit) is not int or not 1 <= sample_limit <= 100:
        raise ValueError("sample_limit must be 1..100")
    decimals = set(decimal_columns)
    with tempfile.TemporaryDirectory(prefix="csv-reconcile-") as directory:
        db = sqlite3.connect(directory + "/rows.db")
        try:
            db.execute("CREATE TABLE rows(side TEXT NOT NULL,key TEXT NOT NULL,data TEXT NOT NULL)")
            columns = None
            for side, path in (("left", left), ("right", right)):
                with open(path, encoding="utf-8-sig", newline="") as file:
                    reader = csv.DictReader(file, strict=True)
                    fields = reader.fieldnames
                    if not fields or any(not field for field in fields) or len(set(fields)) != len(fields):
                        raise ValueError(side + ": CSV requires unique nonempty column names")
                    if not set(keys) <= set(fields) or not decimals <= set(fields):
                        raise ValueError(side + ": missing key or decimal columns")
                    if columns is None:
                        columns = fields
                    elif set(columns) != set(fields):
                        raise ValueError("CSV column sets differ")
                    for row in reader:
                        if None in row or any(value is None for value in row.values()):
                            raise ValueError(f"{side}: ragged row ending at line {reader.line_num}")
                        if trim:
                            row = {key: value.strip() for key, value in row.items()}
                        if any(not row[key] for key in keys):
                            raise ValueError(f"{side}: empty key at line {reader.line_num}")
                        for column in decimals:
                            try:
                                if not Decimal(row[column]).is_finite():
                                    raise InvalidOperation
                            except InvalidOperation as exc:
                                raise ValueError(f"{side}: invalid decimal in {column} at line {reader.line_num}") from exc
                        identity = json.dumps([row[key] for key in keys], ensure_ascii=False, separators=(",", ":"))
                        db.execute("INSERT INTO rows VALUES(?,?,?)", (side, identity, json.dumps(row, ensure_ascii=False)))
                db.commit()
            db.execute("CREATE INDEX by_identity ON rows(key,side)")
            db.commit()
            # A key is materialized one group at a time; duplicate examples are bounded.
            groups = db.execute("""SELECT key,SUM(side='left'),SUM(side='right')
                                   FROM rows GROUP BY key ORDER BY key""")
            for key, left_count, right_count in groups:
                def samples(side):
                    return [json.loads(row[0]) for row in db.execute("SELECT data FROM rows WHERE key=? AND side=? ORDER BY rowid LIMIT ?", (key, side, sample_limit))]
                left_rows, right_rows = samples("left"), samples("right")
                result = {"key": dict(zip(keys, json.loads(key))), "left_count": left_count, "right_count": right_count}
                if left_count > 1 or right_count > 1:
                    result |= {"status": "duplicate", "left_samples": left_rows, "right_samples": right_rows}
                elif not left_count:
                    result |= {"status": "right_only", "right": right_rows[0]}
                elif not right_count:
                    result |= {"status": "left_only", "left": left_rows[0]}
                else:
                    before, after = left_rows[0], right_rows[0]
                    differences = []
                    for column in columns:
                        if column in keys:
                            continue
                        a, b = before[column], after[column]
                        equal = Decimal(a) == Decimal(b) if column in decimals else a == b
                        if not equal:
                            differences.append({"column": column, "left": a, "right": b})
                    result |= {"status": "changed" if differences else "matched", "differences": differences}
                yield result
        finally:
            db.close()
