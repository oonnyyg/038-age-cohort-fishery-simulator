"""Command-line interface for the fishery simulator."""

from __future__ import annotations

import argparse
import os
import sys

from .config import load_config
from .errors import ConfigError
from .report import population_csv, summary_json
from .simulator import simulate_all


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="python -m fish_population",
        description="Age-cohort fishery population simulator (offline).",
    )
    parser.add_argument(
        "-i", "--input", required=True, help="Path to the input JSON file."
    )
    parser.add_argument(
        "-o",
        "--output",
        required=True,
        help="Directory where population.csv and summary.json are written.",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _build_parser().parse_args(argv)

    # Validate and simulate before touching the output directory so that an
    # invalid input never creates or overwrites any result files.
    try:
        config = load_config(args.input)
        results = simulate_all(config)
        csv_text = population_csv(config, results)
        json_text = summary_json(config, results)
    except ConfigError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2

    os.makedirs(args.output, exist_ok=True)
    with open(os.path.join(args.output, "population.csv"), "w", encoding="utf-8", newline="") as handle:
        handle.write(csv_text)
    with open(os.path.join(args.output, "summary.json"), "w", encoding="utf-8") as handle:
        handle.write(json_text)
        handle.write("\n")

    print(
        f"wrote population.csv and summary.json for {len(results)} scenario(s) "
        f"to {args.output}"
    )
    return 0
