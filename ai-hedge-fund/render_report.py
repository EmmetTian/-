"""把 aihf 输出的运行记录 JSON 转成一份易读的 Markdown 报告。

用法：python render_report.py record.json report.md
只依赖标准库；按字段名遍历 JSON，兼容正常结果和 Pending 结果两种结构。
"""

from __future__ import annotations

import json
import sys
from collections import defaultdict

INVESTOR_NAMES = {
    "buffett": "巴菲特 Warren Buffett",
    "munger": "芒格 Charlie Munger",
    "graham": "格雷厄姆 Benjamin Graham",
    "lynch": "彼得·林奇 Peter Lynch",
    "druckenmiller": "德鲁肯米勒 Stanley Druckenmiller",
}


def walk(node):
    if isinstance(node, dict):
        yield node
        for value in node.values():
            yield from walk(value)
    elif isinstance(node, list):
        for item in node:
            yield from walk(item)


def label(value: float) -> str:
    if value >= 0.3:
        return "看多"
    if value <= -0.3:
        return "看空"
    return "中性"


def main(record_path: str, out_path: str) -> None:
    with open(record_path, encoding="utf-8") as f:
        record = json.load(f)

    signals = defaultdict(dict)
    final_weights = None
    as_of = record.get("as_of", "")
    for node in walk(record):
        if {"model_name", "ticker", "value"} <= node.keys():
            signals[node["ticker"]][node["model_name"]] = node
        if final_weights is None and isinstance(node.get("final_weights"), dict):
            final_weights = node["final_weights"]

    lines = [f"# 投资大师会诊报告（数据截至 {as_of}）", ""]
    lines.append("评分范围 -1（强烈看空）到 +1（强烈看多）。理由为模型原文（英文）。")
    lines.append("")
    for ticker, by_model in sorted(signals.items()):
        values = [s["value"] for s in by_model.values() if not s.get("metadata", {}).get("abstained")]
        avg = sum(values) / len(values) if values else 0.0
        lines += [f"## {ticker}：平均 {avg:+.2f}（{label(avg)}）", ""]
        lines += ["| 投资人 | 评分 | 观点 |", "|---|---|---|"]
        for name, s in by_model.items():
            abstained = s.get("metadata", {}).get("abstained")
            view = "弃权" if abstained else label(s["value"])
            lines.append(f"| {INVESTOR_NAMES.get(name, name)} | {s['value']:+.2f} | {view} |")
        lines.append("")
        for name, s in by_model.items():
            reasoning = (s.get("reasoning") or "（无说明）").strip()
            lines += [f"### {INVESTOR_NAMES.get(name, name)}", "", reasoning, ""]

    if final_weights:
        lines += ["## 模拟组合建议仓位（仅供参考，不是投资建议）", ""]
        for ticker, weight in final_weights.items():
            lines.append(f"- {ticker}: {weight:+.1%}")
        lines.append("")

    if not signals:
        lines.append("没有解析到任何投资人观点，请查看同目录下的 record.json 和运行日志。")

    with open(out_path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2])
