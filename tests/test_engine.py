import csv
import tempfile
import unittest
from pathlib import Path
from csv_reconcile import reconcile


class ReconcileTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.left = Path(self.temp.name) / "left.csv"
        self.right = Path(self.temp.name) / "right.csv"

    def write(self, path, rows, fields=("id", "value")):
        with path.open("w", encoding="utf-8", newline="") as file:
            writer = csv.writer(file)
            writer.writerow(fields)
            writer.writerows(rows)

    def run_rows(self, **options):
        return list(reconcile(self.left, self.right, ["id"], **options))

    def test_reordered_rows_and_columns_match(self):
        self.write(self.left, [("1", "one"), ("2", "two")])
        self.write(self.right, [("two", "2"), ("one", "1")], fields=("value", "id"))
        self.assertEqual([r["status"] for r in self.run_rows()], ["matched", "matched"])

    def test_changes_and_missing_keys_are_explicit(self):
        self.write(self.left, [("1", "old"), ("left", "only")])
        self.write(self.right, [("1", "new"), ("right", "only")])
        rows = {r["key"]["id"]: r for r in self.run_rows()}
        self.assertEqual(rows["1"]["differences"], [{"column": "value", "left": "old", "right": "new"}])
        self.assertEqual(rows["left"]["status"], "left_only")
        self.assertEqual(rows["right"]["status"], "right_only")

    def test_duplicate_keys_are_never_arbitrarily_matched(self):
        self.write(self.left, [("1", str(i)) for i in range(10)])
        self.write(self.right, [("1", "0")])
        result = self.run_rows(sample_limit=2)[0]
        self.assertEqual(result["status"], "duplicate")
        self.assertEqual(result["left_count"], 10)
        self.assertEqual(len(result["left_samples"]), 2)

    def test_composite_key_delimiters_do_not_collide(self):
        fields = ("a", "b", "value")
        rows = [("x|y", "z", "first"), ("x", "y|z", "second")]
        self.write(self.left, rows, fields)
        self.write(self.right, rows, fields)
        results = list(reconcile(self.left, self.right, ["a", "b"]))
        self.assertEqual(len(results), 2)
        self.assertTrue(all(r["status"] == "matched" for r in results))

    def test_decimal_comparison_avoids_binary_float_rounding(self):
        self.write(self.left, [("1", "0.10"), ("2", "9007199254740993.01")])
        self.write(self.right, [("1", "0.1"), ("2", "9007199254740993.02")])
        result = self.run_rows(decimal_columns=["value"])
        self.assertEqual(result[0]["status"], "matched")
        self.assertEqual(result[1]["status"], "changed")

    def test_nonfinite_and_invalid_decimals_are_rejected(self):
        self.write(self.left, [("1", "1")])
        for value in ("NaN", "Infinity", "no"):
            self.write(self.right, [("1", value)])
            with self.assertRaises(ValueError):
                self.run_rows(decimal_columns=["value"])

    def test_quoted_newlines_commas_and_unicode(self):
        rows = [("1", 'Café, "hello"\nsecond line')]
        self.write(self.left, rows)
        self.write(self.right, rows)
        self.assertEqual(self.run_rows()[0]["status"], "matched")

    def test_whitespace_normalization_is_opt_in(self):
        self.write(self.left, [("1", " value ")])
        self.write(self.right, [("1", "value")])
        self.assertEqual(self.run_rows()[0]["status"], "changed")
        self.assertEqual(self.run_rows(trim=True)[0]["status"], "matched")

    def test_ragged_rows_empty_keys_and_column_drift_fail(self):
        self.write(self.left, [("1", "value")])
        for text in ("id,value\n1,too,many\n", "id,value\n1\n", "id,value\n,value\n", "id,other\n1,value\n"):
            self.right.write_text(text)
            with self.assertRaises(ValueError):
                self.run_rows()

    def test_duplicate_headers_and_invalid_configuration_fail(self):
        self.write(self.left, [])
        self.right.write_text("id,id\n1,1\n")
        with self.assertRaises(ValueError):
            self.run_rows()
        with self.assertRaises(ValueError):
            list(reconcile(self.left, self.right, []))
        with self.assertRaises(ValueError):
            self.run_rows(sample_limit=0)

    def test_empty_files_with_headers_have_no_groups(self):
        self.write(self.left, [])
        self.write(self.right, [])
        self.assertEqual(self.run_rows(), [])

    def test_thousands_of_rows_are_streamed_through_disk_index(self):
        rows = [(str(n), str(n * n)) for n in range(4000)]
        self.write(self.left, rows)
        self.write(self.right, reversed(rows))
        results = self.run_rows()
        self.assertEqual(len(results), 4000)
        self.assertTrue(all(row["status"] == "matched" for row in results))


if __name__ == "__main__":
    unittest.main()
