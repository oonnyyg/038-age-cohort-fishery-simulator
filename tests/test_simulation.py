import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from fish_population.output import build_summary, population_csv_text, write_outputs
from fish_population.simulation import simulate
from fish_population.validation import InputError, load_and_validate


def base_config(**overrides):
    config = {
        "years": 3,
        "max_age": 2,
        "initial_numbers": [100.0, 50.0, 20.0],
        "survival": [0.5, 0.5, 0.5],
        "fecundity": [0.0, 2.0, 4.0],
        "weights": [1.0, 2.0, 3.0],
        "carrying_capacity": 1000.0,
        "scenarios": [{"name": "s1", "releases": {}, "catches": {}}],
    }
    config.update(overrides)
    return config


class TerminalAgeGroupTests(unittest.TestCase):
    def test_max_age_group_accumulates(self):
        config = base_config(
            max_age=1,
            initial_numbers=[0.0, 10.0],
            survival=[1.0, 1.0],
            fecundity=[0.0, 0.0],
            weights=[1.0, 5.0],
        )
        results = simulate(config)
        year1 = results["s1"]["rows"][1]["numbers"]
        # 0 龄无新生，1 龄个体留在末组（自身增龄汇合后仍为 10）
        self.assertEqual(year1, [0.0, 10.0])
        year2 = results["s1"]["rows"][2]["numbers"]
        self.assertEqual(year2, [0.0, 10.0])

    def test_survivors_flow_into_terminal_group(self):
        config = base_config(
            max_age=2,
            initial_numbers=[8.0, 0.0, 0.0],
            survival=[0.5, 1.0, 1.0],
            fecundity=[0.0, 0.0, 0.0],
            weights=[1.0, 1.0, 1.0],
        )
        results = simulate(config)
        # 第1年末: 0龄存活4条增入1龄
        self.assertEqual(results["s1"]["rows"][1]["numbers"], [0.0, 4.0, 0.0])
        # 第2年末: 1龄4条增入2龄末组
        self.assertEqual(results["s1"]["rows"][2]["numbers"], [0.0, 0.0, 4.0])


class ZeroPopulationTests(unittest.TestCase):
    def test_all_zero_stays_zero(self):
        config = base_config(initial_numbers=[0.0, 0.0, 0.0])
        results = simulate(config)
        for row in results["s1"]["rows"]:
            self.assertEqual(sum(row["numbers"]), 0.0)
            self.assertEqual(row["newborns"], 0.0)
            self.assertEqual(row["natural_mortality"], 0.0)


class CatchWeightTests(unittest.TestCase):
    def test_catch_weight_uses_age_at_capture(self):
        config = base_config(
            years=1,
            initial_numbers=[10.0, 20.0, 30.0],
            survival=[1.0, 1.0, 1.0],
            fecundity=[0.0, 0.0, 0.0],
            weights=[1.0, 2.0, 5.0],
            scenarios=[{
                "name": "catch",
                "releases": {},
                "catches": {1: [0.5, 0.5, 0.2]},
            }],
        )
        results = simulate(config)
        row = results["catch"]["rows"][1]
        self.assertEqual(row["caught_numbers"], [5.0, 10.0, 6.0])
        self.assertEqual(row["caught_weight"], [5.0, 20.0, 30.0])
        summary = build_summary(results)["scenarios"][0]
        self.assertEqual(summary["total_caught_numbers"], 21.0)
        self.assertEqual(summary["total_caught_weight"], 55.0)
        self.assertEqual(row["natural_mortality"], 0.0)

    def test_release_precedes_catch_at_age_zero(self):
        config = base_config(
            years=1,
            initial_numbers=[0.0, 0.0, 0.0],
            survival=[1.0, 1.0, 1.0],
            fecundity=[0.0, 0.0, 0.0],
            weights=[1.0, 1.0, 1.0],
            scenarios=[{
                "name": "r",
                "releases": {1: 100.0},
                "catches": {1: [0.25, 0.0, 0.0]},
            }],
        )
        row = simulate(config)["r"]["rows"][1]
        self.assertEqual(row["released"], 100.0)
        self.assertEqual(row["caught_numbers"][0], 25.0)


class ScenarioIsolationTests(unittest.TestCase):
    def _two_scenarios(self):
        heavy = {
            "name": "heavy",
            "releases": {1: 1000.0},
            "catches": {1: [1.0, 1.0, 1.0], 2: [1.0, 1.0, 1.0]},
        }
        none = {"name": "none", "releases": {}, "catches": {}}
        return heavy, none

    def test_results_independent_of_order(self):
        heavy, none = self._two_scenarios()
        forward = simulate(base_config(scenarios=[heavy, none]))
        reversed_order = simulate(base_config(scenarios=[none, heavy]))
        for name in ("heavy", "none"):
            self.assertEqual(
                forward[name]["rows"], reversed_order[name]["rows"]
            )

    def test_scenarios_share_initial_state_only(self):
        heavy, none = self._two_scenarios()
        results = simulate(base_config(scenarios=[heavy, none]))
        # 重捕捞方案第1年把所有鱼捕光
        heavy_year1 = results["heavy"]["rows"][1]["numbers"]
        self.assertEqual(sum(heavy_year1), 0.0)
        # 无捕捞方案不受影响
        none_year1 = results["none"]["rows"][1]
        self.assertGreater(sum(none_year1["numbers"]), 0.0)


class ValidationTests(unittest.TestCase):
    def test_bad_vector_length(self):
        config = base_config(survival=[0.5, 0.5])
        with self.assertRaisesRegex(InputError, "survival"):
            self._load(config)

    def test_survival_out_of_range(self):
        config = base_config(survival=[1.5, 0.5, 0.5])
        with self.assertRaisesRegex(InputError, r"survival\[0\]"):
            self._load(config)

    def test_negative_numbers(self):
        config = base_config(initial_numbers=[-1.0, 0.0, 0.0])
        with self.assertRaisesRegex(InputError, r"initial_numbers\[0\]"):
            self._load(config)

    def test_non_positive_capacity(self):
        with self.assertRaisesRegex(InputError, "carrying_capacity"):
            self._load(base_config(carrying_capacity=0))

    def test_non_integer_years(self):
        with self.assertRaisesRegex(InputError, "years"):
            self._load(base_config(years=0))

    def test_duplicate_scenario_name(self):
        config = base_config(scenarios=[
            {"name": "x", "releases": {}, "catches": {}},
            {"name": "x", "releases": {}, "catches": {}},
        ])
        with self.assertRaisesRegex(InputError, "重复"):
            self._load(config)

    def test_year_out_of_range(self):
        config = base_config(scenarios=[
            {"name": "x", "releases": {9: 1.0}, "catches": {}}
        ])
        with self.assertRaisesRegex(InputError, "超出模拟范围"):
            self._load(config)

    def test_catch_rate_out_of_range(self):
        config = base_config(scenarios=[
            {"name": "x", "releases": {}, "catches": {1: [2.0, 0.0, 0.0]}}
        ])
        with self.assertRaisesRegex(InputError, r"catches\[1\]\[0\]"):
            self._load(config)

    def test_non_finite_value(self):
        config = base_config(weights=[float("inf"), 1.0, 1.0])
        with self.assertRaisesRegex(InputError, r"weights\[0\]"):
            self._load(config)

    def _load(self, config):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "in.json"
            path.write_text(json.dumps(config), encoding="utf-8")
            return load_and_validate(path)


class CliTests(unittest.TestCase):
    def test_cli_writes_outputs_and_sorted_csv(self):
        repo_root = Path(__file__).resolve().parents[1]
        with tempfile.TemporaryDirectory() as tmp:
            output_dir = Path(tmp) / "out"
            completed = subprocess.run(
                [
                    sys.executable, "-m", "fish_population",
                    "--input", str(repo_root / "examples" / "sample_input.json"),
                    "--output-dir", str(output_dir),
                ],
                cwd=repo_root,
                text=True,
                capture_output=True,
            )
            self.assertEqual(completed.returncode, 0, completed.stderr)
            csv_text = (output_dir / "population_by_age.csv").read_text(encoding="utf-8")
            lines = csv_text.strip().splitlines()
            self.assertEqual(lines[0], "scenario,year,age,numbers")
            self.assertIn("fishing_adult,0,0,1000.0", lines)
            self.assertTrue(
                any(line.startswith("no_fishing,5,3,") for line in lines)
            )
            summary = json.loads((output_dir / "summary.json").read_text(encoding="utf-8"))
            names = [item["name"] for item in summary["scenarios"]]
            self.assertEqual(names, sorted(names))

    def test_invalid_input_does_not_touch_output_dir(self):
        repo_root = Path(__file__).resolve().parents[1]
        with tempfile.TemporaryDirectory() as tmp:
            bad_input = Path(tmp) / "bad.json"
            bad_input.write_text(json.dumps(base_config(years=-1)), encoding="utf-8")
            output_dir = Path(tmp) / "out"
            output_dir.mkdir()
            marker = output_dir / "keep.txt"
            marker.write_text("untouched", encoding="utf-8")
            completed = subprocess.run(
                [
                    sys.executable, "-m", "fish_population",
                    "--input", str(bad_input), "--output-dir", str(output_dir),
                ],
                cwd=repo_root, text=True, capture_output=True,
            )
            self.assertNotEqual(completed.returncode, 0)
            self.assertFalse((output_dir / "summary.json").exists())
            self.assertEqual(marker.read_text(encoding="utf-8"), "untouched")


if __name__ == "__main__":
    unittest.main()
