"""Year-by-year age-cohort population simulation."""

from __future__ import annotations

from typing import Any


def simulate(config: dict[str, Any]) -> dict[str, Any]:
    """Run every scenario independently from the same initial population.

    Returns a dict keyed by scenario name; each scenario contains the
    population table (year 0 plus every simulated year-end state) and
    yearly flow records.
    """
    years: int = config["years"]
    max_age: int = config["max_age"]
    initial: list[float] = list(config["initial_numbers"])
    survival: list[float] = config["survival"]
    fecundity: list[float] = config["fecundity"]
    weights: list[float] = config["weights"]
    capacity: float = config["carrying_capacity"]

    results: dict[str, dict[str, Any]] = {}
    for scenario in config["scenarios"]:
        population = list(initial)
        rows: list[dict[str, Any]] = [
            {"year": 0, "numbers": list(population), "released": 0.0, "newborns": 0.0,
             "natural_mortality": 0.0, "caught_numbers": [0.0] * (max_age + 1),
             "caught_weight": [0.0] * (max_age + 1)}
        ]
        for year in range(1, years + 1):
            released = scenario["releases"].get(year, 0.0)
            catch_rates = scenario["catches"].get(year, [0.0] * (max_age + 1))

            stocked = list(population)
            stocked[0] += released

            caught_numbers = [stocked[age] * catch_rates[age] for age in range(max_age + 1)]
            after_catch = [stocked[age] - caught_numbers[age] for age in range(max_age + 1)]
            survivors = [after_catch[age] * survival[age] for age in range(max_age + 1)]
            natural_mortality = sum(
                after_catch[age] - survivors[age] for age in range(max_age + 1)
            )

            total_survivors = sum(survivors)
            newborns = (
                sum(survivors[age] * fecundity[age] for age in range(max_age + 1))
                / (1.0 + total_survivors / capacity)
            )

            aged = [0.0] * (max_age + 1)
            aged[0] = newborns
            for age in range(1, max_age + 1):
                aged[age] = survivors[age - 1]
            aged[max_age] += survivors[max_age]

            caught_weight = [
                caught_numbers[age] * weights[age] for age in range(max_age + 1)
            ]
            population = aged
            rows.append({
                "year": year,
                "numbers": list(population),
                "released": released,
                "newborns": newborns,
                "natural_mortality": natural_mortality,
                "caught_numbers": caught_numbers,
                "caught_weight": caught_weight,
            })

        results[scenario["name"]] = {
            "name": scenario["name"],
            "years": years,
            "max_age": max_age,
            "weights": weights,
            "rows": rows,
        }
    return results
