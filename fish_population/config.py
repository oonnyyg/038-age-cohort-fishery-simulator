"""Loading and validation of simulation input configuration."""

from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any

from .errors import ConfigError


def _is_finite_number(value: Any) -> bool:
    return (
        isinstance(value, (int, float))
        and not isinstance(value, bool)
        and value == value
        and value not in (float("inf"), float("-inf"))
    )


def _require_vector(
    data: dict[str, Any],
    key: str,
    length: int,
    *,
    minimum: float,
    allow_zero: bool,
) -> list[float]:
    if key not in data:
        raise ConfigError(f"{key}: missing field")
    raw = data[key]
    if not isinstance(raw, list):
        raise ConfigError(f"{key}: expected an array, got {type(raw).__name__}")
    if len(raw) != length:
        raise ConfigError(
            f"{key}: array length {len(raw)} does not match required length {length}"
        )
    result: list[float] = []
    bound_text = "non-negative" if allow_zero else "positive"
    for index, item in enumerate(raw):
        if not _is_finite_number(item):
            raise ConfigError(f"{key}[{index}]: expected a finite number")
        value = float(item)
        if value < minimum or (not allow_zero and value <= 0):
            raise ConfigError(f"{key}[{index}]: expected a {bound_text} number")
        result.append(value)
    return result


def _require_rates(
    data: dict[str, Any], key: str, length: int, prefix: str | None = None
) -> list[float]:
    label = f"{prefix}.{key}" if prefix is not None else key
    raw = data.get(key)
    if not isinstance(raw, list):
        raise ConfigError(f"{label}: expected an array, got {type(raw).__name__}")
    if len(raw) != length:
        raise ConfigError(
            f"{label}: array length {len(raw)} does not match required length {length}"
        )
    result: list[float] = []
    for index, item in enumerate(raw):
        if not _is_finite_number(item):
            raise ConfigError(f"{label}[{index}]: expected a finite number")
        value = float(item)
        if not 0.0 <= value <= 1.0:
            raise ConfigError(f"{label}[{index}]: expected a rate between 0 and 1")
        result.append(value)
    return result


@dataclass(frozen=True)
class YearPlan:
    """Stocking and age-specific fishing rates for one simulation year."""

    year: int
    stocking: float
    fishing: list[float]


@dataclass(frozen=True)
class Scenario:
    name: str
    years: dict[int, YearPlan]


@dataclass(frozen=True)
class Config:
    years: int
    max_age: int
    initial: list[float]
    survival: list[float]
    fecundity: list[float]
    weights: list[float]
    capacity: float
    scenarios: list[Scenario]


def _parse_scenario(raw: Any, index: int, years: int, ages: int) -> Scenario:
    location = f"scenarios[{index}]"
    if not isinstance(raw, dict):
        raise ConfigError(f"{location}: expected an object")
    name = raw.get("name")
    if not isinstance(name, str) or not name:
        raise ConfigError(f"{location}.name: expected a non-empty string")
    yearly = raw.get("yearly")
    if not isinstance(yearly, list):
        raise ConfigError(f"{location}.yearly: expected an array")
    plans: dict[int, YearPlan] = {}
    for entry_index, entry in enumerate(yearly):
        entry_loc = f"{location}.yearly[{entry_index}]"
        if not isinstance(entry, dict):
            raise ConfigError(f"{entry_loc}: expected an object")
        year = entry.get("year")
        if not isinstance(year, int) or isinstance(year, bool):
            raise ConfigError(f"{entry_loc}.year: expected an integer")
        if not 1 <= year <= years:
            raise ConfigError(
                f"{entry_loc}.year: year {year} is outside range 1..{years}"
            )
        if year in plans:
            raise ConfigError(f"{entry_loc}.year: duplicate year {year} in scenario")
        stocking = entry.get("stocking", 0.0)
        if not _is_finite_number(stocking) or stocking < 0:
            raise ConfigError(f"{entry_loc}.stocking: expected a non-negative number")
        fishing = (
            _require_rates(entry, "fishing", ages, prefix=entry_loc)
            if "fishing" in entry
            else [0.0] * ages
        )
        plans[year] = YearPlan(year=year, stocking=float(stocking), fishing=fishing)
    return Scenario(name=name, years=plans)


def parse_config(data: Any) -> Config:
    """Validate decoded JSON data and return a structured :class:`Config`."""
    if not isinstance(data, dict):
        raise ConfigError("root: expected a JSON object")

    years = data.get("years")
    if not isinstance(years, int) or isinstance(years, bool) or years <= 0:
        raise ConfigError("years: expected a positive integer")

    max_age = data.get("max_age")
    if not isinstance(max_age, int) or isinstance(max_age, bool) or max_age <= 0:
        raise ConfigError("max_age: expected a positive integer")

    ages = max_age + 1
    initial = _require_vector(data, "initial_numbers", ages, minimum=0.0, allow_zero=True)
    survival = _require_rates(data, "survival", ages)
    fecundity = _require_vector(data, "fecundity", ages, minimum=0.0, allow_zero=True)
    weights = _require_vector(data, "weights", ages, minimum=0.0, allow_zero=False)

    capacity = data.get("capacity")
    if not _is_finite_number(capacity) or capacity <= 0:
        raise ConfigError("capacity: expected a positive number")

    scenarios_raw = data.get("scenarios")
    if not isinstance(scenarios_raw, list) or not scenarios_raw:
        raise ConfigError("scenarios: expected a non-empty array")

    scenarios = [
        _parse_scenario(raw, index, years, ages)
        for index, raw in enumerate(scenarios_raw)
    ]
    seen: set[str] = set()
    for index, scenario in enumerate(scenarios):
        if scenario.name in seen:
            raise ConfigError(f"scenarios[{index}].name: duplicate name {scenario.name!r}")
        seen.add(scenario.name)

    return Config(
        years=years,
        max_age=max_age,
        initial=initial,
        survival=survival,
        fecundity=fecundity,
        weights=weights,
        capacity=float(capacity),
        scenarios=scenarios,
    )


def load_config(path: str) -> Config:
    """Read and validate a JSON configuration file."""
    try:
        with open(path, "r", encoding="utf-8-sig") as handle:
            data = json.load(handle)
    except FileNotFoundError:
        raise ConfigError(f"input file not found: {path}") from None
    except json.JSONDecodeError as exc:
        raise ConfigError(f"invalid JSON at line {exc.lineno} column {exc.colno}: {exc.msg}") from None
    return parse_config(data)
