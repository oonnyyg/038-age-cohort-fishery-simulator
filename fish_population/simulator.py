"""Year-by-year age-cohort population simulation."""

from __future__ import annotations

from dataclasses import dataclass

from .config import Config, Scenario


@dataclass(frozen=True)
class YearResult:
    """State and flows recorded for one simulated year."""

    year: int
    stocking: float
    recruitment: float
    natural_mortality: float
    catch_numbers: list[float]
    catch_weight: float
    population: list[float]


@dataclass(frozen=True)
class ScenarioResult:
    name: str
    initial: list[float]
    years: list[YearResult]


def simulate(config: Config, scenario: Scenario) -> ScenarioResult:
    """Run one scenario independently from the shared initial population."""
    population = list(config.initial)
    ages = config.max_age + 1
    results: list[YearResult] = []

    for year in range(1, config.years + 1):
        plan = scenario.years.get(year)
        stocking = plan.stocking if plan is not None else 0.0
        fishing = plan.fishing if plan is not None else [0.0] * ages

        # 1. Add this year's releases to age 0.
        population[0] += stocking

        # 2. Remove catches using age-specific fishing proportions.
        catch_numbers = [
            population[age] * fishing[age] for age in range(ages)
        ]
        after_fishing = [
            population[age] - catch_numbers[age] for age in range(ages)
        ]

        # 3. Apply natural survival rates to the remaining stock.
        survivors = [
            after_fishing[age] * config.survival[age] for age in range(ages)
        ]
        natural_mortality = sum(
            after_fishing[age] - survivors[age] for age in range(ages)
        )

        # 4. Density-dependent recruitment from the surviving spawners.
        survivor_total = sum(survivors)
        raw_recruits = sum(
            survivors[age] * config.fecundity[age] for age in range(ages)
        )
        recruitment = raw_recruits / (1.0 + survivor_total / config.capacity)

        # 5. Age the survivors; the oldest group stays in the terminal group.
        aged = [0.0] * ages
        for age in range(ages):
            target = min(age + 1, config.max_age)
            aged[target] += survivors[age]
        aged[0] += recruitment

        catch_weight = sum(
            catch_numbers[age] * config.weights[age] for age in range(ages)
        )

        population = aged
        results.append(
            YearResult(
                year=year,
                stocking=stocking,
                recruitment=recruitment,
                natural_mortality=natural_mortality,
                catch_numbers=catch_numbers,
                catch_weight=catch_weight,
                population=list(population),
            )
        )

    return ScenarioResult(name=scenario.name, initial=list(config.initial), years=results)


def simulate_all(config: Config) -> list[ScenarioResult]:
    """Run every scenario independently; order never affects individual results."""
    return [simulate(config, scenario) for scenario in config.scenarios]
