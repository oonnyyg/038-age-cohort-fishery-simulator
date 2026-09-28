"""CSV and JSON output writing."""

from __future__ import annotations

import csv
import io
import json
from pathlib import Path
from typing import Any


def _num(value: float) -> float:
    return round(float(value), 10)


def build_summary(results: dict[str, dict[str, Any]]) -> dict[str, Any]:
    summary: list[dict[str, Any]] = []
    for name in sorted(results):
        result = results[name]
        weights = result["weights"]
        yearly: list[dict[str, Any]] = []
        total_caught_numbers = 0.0
        total_caught_weight = 0.0
        total_released = 0.0
        total_newborns = 0.0
        total_natural_mortality = 0.0
        for row in result["rows"]:
            caught_numbers = sum(row["caught_numbers"])
            caught_weight = sum(row["caught_weight"])
            yearly.append({
                "year": row["year"],
                "released": _num(row["released"]),
                "newborns": _num(row["newborns"]),
                "natural_mortality": _num(row["natural_mortality"]),
                "caught_numbers": _num(caught_numbers),
                "caught_weight": _num(caught_weight),
            })
            if row["year"] >= 1:
                total_caught_numbers += caught_numbers
                total_caught_weight += caught_weight
                total_released += row["released"]
                total_newborns += row["newborns"]
                total_natural_mortality += row["natural_mortality"]

        final = result["rows"][-1]
        final_numbers = sum(final["numbers"])
        final_weight = sum(
            final["numbers"][age] * weights[age] for age in range(result["max_age"] + 1)
        )
        summary.append({
            "name": name,
            "total_released": _num(total_released),
            "total_newborns": _num(total_newborns),
            "total_natural_mortality": _num(total_natural_mortality),
            "total_caught_numbers": _num(total_caught_numbers),
            "total_caught_weight": _num(total_caught_weight),
            "final_year": final["year"],
            "final_numbers": _num(final_numbers),
            "final_weight": _num(final_weight),
            "final_numbers_by_age": [_num(value) for value in final["numbers"]],
            "yearly": yearly,
        })
    return {"scenarios": summary}


def population_csv_text(results: dict[str, dict[str, Any]]) -> str:
    buffer = io.StringIO()
    writer = csv.writer(buffer, lineterminator="\n")
    writer.writerow(["scenario", "year", "age", "numbers"])
    for name in sorted(results):
        result = results[name]
        for row in sorted(result["rows"], key=lambda item: item["year"]):
            for age in range(result["max_age"] + 1):
                writer.writerow([name, row["year"], age, repr(_num(row["numbers"][age]))])
    return buffer.getvalue()


def yearly_csv_text(results: dict[str, dict[str, Any]]) -> str:
    buffer = io.StringIO()
    writer = csv.writer(buffer, lineterminator="\n")
    writer.writerow([
        "scenario", "year", "released", "newborns", "natural_mortality",
        "caught_numbers", "caught_weight",
    ])
    for name in sorted(results):
        result = results[name]
        for row in sorted(result["rows"], key=lambda item: item["year"]):
            writer.writerow([
                name, row["year"], repr(_num(row["released"])), repr(_num(row["newborns"])),
                repr(_num(row["natural_mortality"])), repr(_num(sum(row["caught_numbers"]))),
                repr(_num(sum(row["caught_weight"]))),
            ])
    return buffer.getvalue()


def write_outputs(results: dict[str, dict[str, Any]], output_dir: str | Path) -> list[Path]:
    """Write all output files; the directory must not contain stale results."""
    target = Path(output_dir)
    target.mkdir(parents=True, exist_ok=True)
    summary = build_summary(results)
    files = {
        "population_by_age.csv": population_csv_text(results),
        "yearly_flows.csv": yearly_csv_text(results),
        "summary.json": json.dumps(summary, ensure_ascii=False, indent=2, sort_keys=False) + "\n",
    }
    written: list[Path] = []
    for filename, content in files.items():
        path = target / filename
        path.write_text(content, encoding="utf-8", newline="")
        written.append(path)
    return written
