"""CSV and JSON output writers."""

from __future__ import annotations

import csv
import io
import json

from .config import Config
from .simulator import ScenarioResult


def population_csv(config: Config, results: list[ScenarioResult]) -> str:
    """Build the per-year, per-age population CSV text."""
    buffer = io.StringIO()
    writer = csv.writer(buffer, lineterminator="\n")
    writer.writerow(["scenario", "year", "age", "number"])
    for result in sorted(results, key=lambda item: item.name):
        for age, number in enumerate(result.initial):
            writer.writerow([result.name, 0, age, repr(number)])
        for year_result in result.years:
            for age, number in enumerate(year_result.population):
                writer.writerow(
                    [result.name, year_result.year, age, repr(number)]
                )
    return buffer.getvalue()


def summary_json(config: Config, results: list[ScenarioResult]) -> str:
    """Build the summary JSON text with cumulative and terminal statistics."""
    summary: list[dict[str, object]] = []
    for result in sorted(results, key=lambda item: item.name):
        yearly = []
        total_stocking = 0.0
        total_recruitment = 0.0
        total_natural_mortality = 0.0
        total_catch_number = 0.0
        total_catch_weight = 0.0
        for year_result in result.years:
            catch_number = sum(year_result.catch_numbers)
            total_stocking += year_result.stocking
            total_recruitment += year_result.recruitment
            total_natural_mortality += year_result.natural_mortality
            total_catch_number += catch_number
            total_catch_weight += year_result.catch_weight
            yearly.append(
                {
                    "year": year_result.year,
                    "stocking": year_result.stocking,
                    "recruitment": year_result.recruitment,
                    "natural_mortality": year_result.natural_mortality,
                    "catch_numbers": year_result.catch_numbers,
                    "catch_number_total": catch_number,
                    "catch_weight": year_result.catch_weight,
                }
            )
        terminal = result.years[-1].population if result.years else result.initial
        terminal_weight = sum(
            number * config.weights[age] for age, number in enumerate(terminal)
        )
        summary.append(
            {
                "scenario": result.name,
                "yearly": yearly,
                "cumulative": {
                    "stocking": total_stocking,
                    "recruitment": total_recruitment,
                    "natural_mortality": total_natural_mortality,
                    "catch_number": total_catch_number,
                    "catch_weight": total_catch_weight,
                },
                "terminal": {
                    "year": config.years,
                    "numbers": list(terminal),
                    "number_total": sum(terminal),
                    "weight": terminal_weight,
                },
            }
        )
    return json.dumps({"scenarios": summary}, indent=2, ensure_ascii=False, sort_keys=False)
