# 年龄队列渔业种群模拟器

纯 Python 3.12 标准库实现，按年龄队列（age cohort）逐年推进，比较不同
放流与捕捞方案对种群存量和产出的影响。模型完全自足，不接入任何在线数据。

## 运行

```sh
python -m fish_population --input examples/sample_input.json --output-dir out
```

仅依赖标准库，无需安装第三方包。输入非法时向标准错误打印错误位置，
以非零状态退出，且不会生成或覆盖任何结果文件。

## 输入格式

输入为本地 JSON 文件（见 `examples/sample_input.json`）：

| 字段 | 说明 |
| --- | --- |
| `years` | 正整数，模拟年数 |
| `max_age` | 正整数，最大年龄；年龄从 0 开始，末组（`max_age`）表示该年龄及以上 |
| `initial_numbers` | 长度 `max_age + 1` 的数组，各龄初始数量，非负实数 |
| `survival` | 同长度数组，各龄存活率，取值 0 至 1 |
| `fecundity` | 同长度数组，各龄繁殖系数，非负 |
| `weights` | 同长度数组，各龄个体重量，非负 |
| `carrying_capacity` | 正数，环境容量 |
| `scenarios` | 至少一个具名方案；`name` 非空且全局唯一 |

每个方案含：

- `releases`：以年份字符串为键的放流量（0 龄个体数，非负）。
- `catches`：以年份字符串为键的数组，长度 `max_age + 1`，各龄捕捞比例
  （0 至 1）。

年份键在方案内不可重复，且必须落在 `1..years`。未设置的年份，放流量与
各龄捕捞比例均视为 0。所有方案从同一份初始种群独立运行，方案顺序不影响
各自结果。

## 年内顺序

每一年依次执行：

1. **放流**：当年放流量加入 0 龄数量。
2. **捕捞**：按各龄捕捞比例扣除捕获数量，即
   `caught = number_after_release * catch_rate`。
3. **自然存活**：捕捞后剩余数量乘该龄存活率得到存活数量；自然死亡 =
   捕捞后数量 − 存活数量。
4. **繁殖**：新生数量
   `newborns = sum(survivors[a] * fecundity[a]) / (1 + sum(survivors) / carrying_capacity)`。
5. **增龄**：存活个体增龄，最高龄个体留在末组（与新进入末组的个体汇合），
   新生进入 0 龄。数量全程按实数计算，不取整。

捕获重量按捕捞时的年龄计算（捕获数量乘该龄个体重量）。

## 输出

输出目录下生成：

- `population_by_age.csv`：逐年（含初始第 0 年）各龄年末数量，列为
  `scenario, year, age, numbers`。
- `yearly_flows.csv`：逐年放流、新生、自然死亡、捕获数量、捕获重量，
  第 0 年流量均为 0。
- `summary.json`：每个方案的累计放流、累计新生、累计自然死亡、累计捕获
  数量与重量，以及末年（年末）种群数量、重量和各龄数量。

所有输出按方案名、年份、年龄稳定排序。

## 测试

```sh
python -m unittest discover -s tests -v
```
