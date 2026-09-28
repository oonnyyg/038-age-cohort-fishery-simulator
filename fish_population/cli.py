"""Command-line entry point: python -m fish_population"""

from __future__ import annotations

import argparse
import sys

from .output import write_outputs
from .simulation import simulate
from .validation import InputError, load_and_validate


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="python -m fish_population",
        description="按年龄队列逐年推进的渔业种群模拟工具（自足模型，不接入在线数据）",
    )
    parser.add_argument("--input", "-i", required=True, help="本地输入 JSON 文件路径")
    parser.add_argument("--output-dir", "-o", required=True, help="结果输出目录")
    args = parser.parse_args(argv)

    try:
        config = load_and_validate(args.input)
        results = simulate(config)
        written = write_outputs(results, args.output_dir)
    except InputError as exc:
        print(f"输入错误: {exc}", file=sys.stderr)
        return 1

    for path in written:
        print(f"已写出: {path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
