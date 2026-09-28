"""Loading and validation of simulator input JSON."""

from __future__ import annotations

import json
import math
from pathlib import Path
from typing import Any


class InputError(ValueError):
    """Raised when the input JSON is invalid."""


def _is_finite_number(value: Any) -> bool:
    return isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(value)


def _check_vector(
    data: dict[str, Any],
    key: str,
    length: int,
    *,
    min_value: float,
    max_value: float | None,
    inclusive: bool,
) -> list[float]:
    if key not in data:
        raise InputError(f"缺少顶层字段: {key}")
    vector = data[key]
    if not isinstance(vector, list):
        raise InputError(f"字段 {key} 必须是数组")
    if len(vector) != length:
        raise InputError(f"字段 {key} 长度为 {len(vector)}，应为 {length}（0 至 {length - 1} 龄）")
    result: list[float] = []
    for index, item in enumerate(vector):
        if not _is_finite_number(item):
            raise InputError(f"字段 {key}[{index}] 必须是有限数值")
        if inclusive:
            valid = item >= min_value and (max_value is None or item <= max_value)
        else:
            valid = item > min_value and (max_value is None or item < max_value)
        if not valid:
            upper = "" if max_value is None else f" 且不超过 {max_value}"
            relation = "大于" if not inclusive else "不小于"
            raise InputError(f"字段 {key}[{index}] = {item} 必须{relation} {min_value}{upper}")
        result.append(float(item))
    return result


def _parse_year_keys(mapping: Any, label: str, years: int) -> dict[int, Any]:
    if not isinstance(mapping, dict):
        raise InputError(f"{label} 必须是以年份为键的对象")
    parsed: dict[int, Any] = {}
    for raw_year, value in mapping.items():
        if not isinstance(raw_year, str) or not raw_year.isdigit():
            raise InputError(f"{label} 的年份键必须是正整数字符串，得到: {raw_year!r}")
        year = int(raw_year)
        if year < 1 or year > years:
            raise InputError(f"{label} 的年份 {year} 超出模拟范围 1..{years}")
        if year in parsed:
            raise InputError(f"{label} 的年份 {year} 重复")
        parsed[year] = value
    return parsed


def load_and_validate(path: str | Path) -> dict[str, Any]:
    """Read and validate a JSON configuration file."""
    config_path = Path(path)
    try:
        raw = config_path.read_text(encoding="utf-8")
    except OSError as exc:
        raise InputError(f"无法读取输入文件 {config_path}: {exc}") from exc
    try:
        data = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise InputError(f"输入文件不是合法 JSON: {exc}") from exc
    if not isinstance(data, dict):
        raise InputError("输入 JSON 顶层必须是对象")

    years = data.get("years")
    if not isinstance(years, int) or isinstance(years, bool) or years <= 0:
        raise InputError("字段 years 必须是正整数")

    max_age = data.get("max_age")
    if not isinstance(max_age, int) or isinstance(max_age, bool) or max_age <= 0:
        raise InputError("字段 max_age 必须是正整数（最大年龄及以上的末组）")

    length = max_age + 1
    initial = _check_vector(data, "initial_numbers", length, min_value=0.0, max_value=None, inclusive=True)
    survival = _check_vector(data, "survival", length, min_value=0.0, max_value=1.0, inclusive=True)
    fecundity = _check_vector(data, "fecundity", length, min_value=0.0, max_value=None, inclusive=True)
    weights = _check_vector(data, "weights", length, min_value=0.0, max_value=None, inclusive=True)

    capacity = data.get("carrying_capacity")
    if not _is_finite_number(capacity) or capacity <= 0:
        raise InputError("字段 carrying_capacity 必须是正数")

    scenarios_raw = data.get("scenarios")
    if not isinstance(scenarios_raw, list) or not scenarios_raw:
        raise InputError("字段 scenarios 必须是非空数组")

    scenarios: list[dict[str, Any]] = []
    seen_names: set[str] = set()
    for scenario_index, scenario in enumerate(scenarios_raw):
        label = f"scenarios[{scenario_index}]"
        if not isinstance(scenario, dict):
            raise InputError(f"{label} 必须是对象")
        name = scenario.get("name")
        if not isinstance(name, str) or not name.strip():
            raise InputError(f"{label}.name 必须是非空字符串")
        if name in seen_names:
            raise InputError(f"方案名重复: {name!r}")
        seen_names.add(name)

        releases_map = _parse_year_keys(scenario.get("releases", {}), f"{label}.releases", years)
        releases: dict[int, float] = {}
        for year, amount in releases_map.items():
            if not _is_finite_number(amount) or amount < 0:
                raise InputError(f"{label}.releases[{year}] = {amount} 必须是非负有限数值")
            releases[year] = float(amount)

        catches_map = _parse_year_keys(scenario.get("catches", {}), f"{label}.catches", years)
        catches: dict[int, list[float]] = {}
        for year, rates in catches_map.items():
            if not isinstance(rates, list) or len(rates) != length:
                raise InputError(
                    f"{label}.catches[{year}] 必须是长度 {length} 的数组（0 至 {max_age} 龄捕捞比例）"
                )
            parsed_rates: list[float] = []
            for age, rate in enumerate(rates):
                if not _is_finite_number(rate) or not (0.0 <= rate <= 1.0):
                    raise InputError(
                        f"{label}.catches[{year}][{age}] = {rate} 必须是 0 至 1 之间的数值"
                    )
                parsed_rates.append(float(rate))
            catches[year] = parsed_rates

        scenarios.append({"name": name, "releases": releases, "catches": catches})

    return {
        "years": years,
        "max_age": max_age,
        "initial_numbers": initial,
        "survival": survival,
        "fecundity": fecundity,
        "weights": weights,
        "carrying_capacity": float(capacity),
        "scenarios": scenarios,
    }
