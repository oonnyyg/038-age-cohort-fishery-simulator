import unittest

from fish_population.config import parse_config
from fish_population.errors import ConfigError


VALID = {
    "years": 2,
    "max_age": 1,
    "initial_numbers": [1.0, 2.0],
    "survival": [0.5, 0.5],
    "fecundity": [0.0, 1.0],
    "weights": [1.0, 2.0],
    "capacity": 100.0,
    "scenarios": [{"name": "a", "yearly": []}],
}


class ValidationTest(unittest.TestCase):
    def assert_invalid(self, data, location_fragment):
        with self.assertRaises(ConfigError) as ctx:
            parse_config(data)
        self.assertIn(location_fragment, str(ctx.exception))

    def test_valid_input(self):
        config = parse_config(VALID)
        self.assertEqual(config.years, 2)
        self.assertEqual(len(config.initial), 2)

    def test_years_must_be_positive_integer(self):
        self.assert_invalid({**VALID, "years": 0}, "years")
        self.assert_invalid({**VALID, "years": 1.5}, "years")

    def test_max_age_positive_integer(self):
        self.assert_invalid({**VALID, "max_age": 0}, "max_age")

    def test_array_length_must_match(self):
        self.assert_invalid(
            {**VALID, "survival": [0.5]}, "survival"
        )

    def test_finite_and_non_negative_numbers(self):
        self.assert_invalid(
            {**VALID, "initial_numbers": [float("nan"), 2.0]}, "initial_numbers[0]"
        )
        self.assert_invalid(
            {**VALID, "initial_numbers": [-1.0, 2.0]}, "initial_numbers[0]"
        )

    def test_rates_between_zero_and_one(self):
        self.assert_invalid(
            {**VALID, "survival": [1.2, 0.5]}, "survival[0]"
        )

    def test_weights_and_capacity_positive(self):
        self.assert_invalid({**VALID, "weights": [0.0, 2.0]}, "weights[0]")
        self.assert_invalid({**VALID, "capacity": 0.0}, "capacity")

    def test_scenario_name_non_empty_and_unique(self):
        data = {
            **VALID,
            "scenarios": [
                {"name": "a", "yearly": []},
                {"name": "a", "yearly": []},
            ],
        }
        self.assert_invalid(data, "scenarios[1].name")
        self.assert_invalid(
            {**VALID, "scenarios": []}, "scenarios"
        )

    def test_year_in_range_and_unique(self):
        data = {
            **VALID,
            "scenarios": [
                {
                    "name": "a",
                    "yearly": [
                        {"year": 3, "fishing": [0.1, 0.1]},
                    ],
                }
            ],
        }
        self.assert_invalid(data, "yearly[0].year")
        dup = {
            **VALID,
            "scenarios": [
                {
                    "name": "a",
                    "yearly": [
                        {"year": 1},
                        {"year": 1},
                    ],
                }
            ],
        }
        self.assert_invalid(dup, "yearly[1].year")

    def test_fishing_rate_range_reports_location(self):
        data = {
            **VALID,
            "scenarios": [
                {
                    "name": "a",
                    "yearly": [{"year": 1, "fishing": [0.1, 1.5]}],
                }
            ],
        }
        self.assert_invalid(data, "scenarios[0].yearly[0].fishing[1]")

    def test_fishing_array_length(self):
        data = {
            **VALID,
            "scenarios": [
                {"name": "a", "yearly": [{"year": 1, "fishing": [0.1]}]}
            ],
        }
        self.assert_invalid(data, "fishing")


if __name__ == "__main__":
    unittest.main()
