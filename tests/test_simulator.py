import math
import unittest

from fish_population.config import parse_config
from fish_population.simulator import simulate, simulate_all


def base_config(**overrides):
    data = {
        "years": 3,
        "max_age": 2,
        "initial_numbers": [100.0, 50.0, 20.0],
        "survival": [0.5, 0.8, 0.6],
        "fecundity": [0.0, 2.0, 3.0],
        "weights": [1.0, 2.0, 4.0],
        "capacity": 1000.0,
        "scenarios": [{"name": "s", "yearly": []}],
    }
    data.update(overrides)
    return parse_config(data)


class SimulatorTest(unittest.TestCase):
    def test_terminal_age_conflation(self):
        config = base_config(
            initial_numbers=[0.0, 0.0, 100.0],
            survival=[1.0, 1.0, 0.5],
            fecundity=[0.0, 0.0, 0.0],
        )
        result = simulate(config, config.scenarios[0])
        year1 = result.years[0].population
        # 100 survivors at max age remain in the terminal group; none age out.
        self.assertEqual(year1, [0.0, 0.0, 50.0])
        year2 = result.years[1].population
        self.assertEqual(year2, [0.0, 0.0, 25.0])

    def test_all_zero_population_stays_zero(self):
        config = base_config(initial_numbers=[0.0, 0.0, 0.0])
        result = simulate(config, config.scenarios[0])
        for year_result in result.years:
            self.assertEqual(year_result.population, [0.0, 0.0, 0.0])
            self.assertEqual(year_result.recruitment, 0.0)
            self.assertEqual(year_result.natural_mortality, 0.0)
            self.assertEqual(year_result.catch_weight, 0.0)

    def test_stocking_and_aging_order(self):
        config = base_config(
            initial_numbers=[0.0, 0.0, 0.0],
            survival=[0.5, 1.0, 1.0],
            fecundity=[0.0, 0.0, 0.0],
            scenarios=[
                {
                    "name": "s",
                    "yearly": [{"year": 1, "stocking": 100.0, "fishing": [0.0, 0.0, 0.0]}],
                }
            ],
        )
        result = simulate(config, config.scenarios[0])
        # 100 age-0 fish are stocked, 50 survive and move to age 1.
        self.assertEqual(result.years[0].population, [0.0, 50.0, 0.0])
        self.assertEqual(result.years[0].stocking, 100.0)

    def test_catch_weight_uses_age_at_capture(self):
        data = {
            "years": 1,
            "max_age": 2,
            "initial_numbers": [10.0, 20.0, 30.0],
            "survival": [1.0, 1.0, 1.0],
            "fecundity": [0.0, 0.0, 0.0],
            "weights": [1.0, 2.0, 5.0],
            "capacity": 1000.0,
            "scenarios": [
                {
                    "name": "s",
                    "yearly": [
                        {"year": 1, "stocking": 0.0, "fishing": [0.5, 0.25, 0.1]}
                    ],
                }
            ],
        }
        config = parse_config(data)
        result = simulate(config, config.scenarios[0])
        year1 = result.years[0]
        self.assertEqual(year1.catch_numbers, [5.0, 5.0, 3.0])
        # 5*1 + 5*2 + 3*5 = 30
        self.assertAlmostEqual(year1.catch_weight, 30.0)
        self.assertEqual(year1.natural_mortality, 0.0)

    def test_recruitment_density_dependence(self):
        config = base_config(
            initial_numbers=[0.0, 100.0, 0.0],
            survival=[1.0, 1.0, 1.0],
            fecundity=[0.0, 2.0, 0.0],
            capacity=100.0,
        )
        result = simulate(config, config.scenarios[0])
        # 100 age-1 survivors produce 200 raw recruits limited by capacity.
        expected = 200.0 / (1.0 + 100.0 / 100.0)
        self.assertTrue(math.isclose(result.years[0].recruitment, expected))
        self.assertTrue(math.isclose(result.years[0].population[0], expected))

    def test_scenario_isolation_and_order(self):
        data = {
            "years": 2,
            "max_age": 1,
            "initial_numbers": [10.0, 10.0],
            "survival": [0.5, 0.5],
            "fecundity": [1.0, 1.0],
            "weights": [1.0, 1.0],
            "capacity": 100.0,
            "scenarios": [
                {"name": "heavy", "yearly": [{"year": 1, "fishing": [0.9, 0.9]}]},
                {"name": "light", "yearly": [{"year": 2, "fishing": [0.1, 0.1]}]},
            ],
        }
        config_a = parse_config(data)
        results_a = simulate_all(config_a)

        reversed_data = dict(data)
        reversed_data["scenarios"] = list(reversed(data["scenarios"]))
        config_b = parse_config(reversed_data)
        results_b = simulate_all(config_b)

        by_name_a = {r.name: r for r in results_a}
        by_name_b = {r.name: r for r in results_b}
        for name in ("heavy", "light"):
            for ya, yb in zip(by_name_a[name].years, by_name_b[name].years):
                self.assertEqual(ya.population, yb.population)
                self.assertEqual(ya.catch_numbers, yb.catch_numbers)

        # Heavy fishing must reduce the stock relative to light fishing.
        heavy_end = sum(by_name_a["heavy"].years[-1].population)
        light_end = sum(by_name_a["light"].years[-1].population)
        self.assertLess(heavy_end, light_end)


if __name__ == "__main__":
    unittest.main()
