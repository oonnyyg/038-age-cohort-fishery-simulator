import csv
import io
import json
import os
import sys
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path

from fish_population.cli import main


ROOT = Path(__file__).resolve().parents[1]
SAMPLE = ROOT / "examples" / "sample_input.json"


class CliTest(unittest.TestCase):
    def test_sample_run_produces_sorted_outputs(self):
        with tempfile.TemporaryDirectory() as tmp:
            out_dir = os.path.join(tmp, "results")
            buf = io.StringIO()
            with redirect_stdout(buf):
                code = main(["--input", str(SAMPLE), "--output", out_dir])
            self.assertEqual(code, 0)

            csv_path = os.path.join(out_dir, "population.csv")
            json_path = os.path.join(out_dir, "summary.json")
            self.assertTrue(os.path.exists(csv_path))
            self.assertTrue(os.path.exists(json_path))

            with open(csv_path, newline="", encoding="utf-8") as handle:
                rows = list(csv.DictReader(handle))
            self.assertEqual(rows[0]["year"], "0")
            keys = [(r["scenario"], int(r["year"]), int(r["age"])) for r in rows]
            self.assertEqual(keys, sorted(keys))

            with open(json_path, encoding="utf-8") as handle:
                summary = json.load(handle)
            names = [item["scenario"] for item in summary["scenarios"]]
            self.assertEqual(names, sorted(names))
            baseline = summary["scenarios"][0]
            self.assertEqual(len(baseline["yearly"]), 5)
            self.assertIn("cumulative", baseline)
            self.assertIn("terminal", baseline)

    def test_invalid_input_writes_nothing(self):
        with tempfile.TemporaryDirectory() as tmp:
            bad_path = os.path.join(tmp, "bad.json")
            with open(bad_path, "w", encoding="utf-8") as handle:
                json.dump({"years": -1}, handle)
            out_dir = os.path.join(tmp, "out")
            os.makedirs(out_dir)
            sentinel = os.path.join(out_dir, "population.csv")
            with open(sentinel, "w", encoding="utf-8") as handle:
                handle.write("keep me")

            err = io.StringIO()
            with redirect_stderr(err):
                code = main(["--input", bad_path, "--output", out_dir])
            self.assertNotEqual(code, 0)
            self.assertIn("years", err.getvalue())
            with open(sentinel, encoding="utf-8") as handle:
                self.assertEqual(handle.read(), "keep me")
            self.assertFalse(os.path.exists(os.path.join(out_dir, "summary.json")))


if __name__ == "__main__":
    unittest.main()
