#!/usr/bin/env python3
"""
生成按车次的时间单元格数量对比 JSON 文件。

从 schedule_list.json 中提取每个车次的原始时间单元格数和 JSON 停靠数，
生成对比结果并输出到 train_comparison.json。
"""

import json
import argparse
from pathlib import Path
from typing import Dict, List, Any


def generate_train_comparison(schedule_path: Path, output_path: Path) -> None:
    """从 schedule_list.json 生成按车次对比。"""
    if not schedule_path.exists():
        raise FileNotFoundError(f"文件不存在: {schedule_path}")

    with schedule_path.open(encoding="utf-8") as f:
        data = json.load(f)

    trains = data.get("train", [])
    if not trains:
        print("[警告] schedule_list.json 中无车次数据")
        return

    comparisons: List[Dict[str, Any]] = []
    for tr in trains:
        train_id = tr.get("id", "")
        raw_count = tr.get("raw_time_count", 0)
        json_count = len(tr.get("stations", []))
        match = raw_count == json_count
        comparisons.append({
            "id": train_id,
            "raw_count": raw_count,
            "json_count": json_count,
            "match": match
        })

    out_obj = {
        "comparisons": comparisons,
        "summary": {
            "total_trains": len(comparisons),
            "matched_trains": sum(1 for c in comparisons if c["match"]),
            "mismatched_trains": sum(1 for c in comparisons if not c["match"])
        }
    }

    output_path.write_text(json.dumps(out_obj, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"[完成] 对比输出 -> {output_path} (车次数:{len(comparisons)})")


def main():
    parser = argparse.ArgumentParser(description="生成按车次的时间单元格数量对比 JSON 文件。")
    parser.add_argument("--schedule", default="schedule_list.json", help="schedule_list.json 文件路径（默认：schedule_list.json）")
    parser.add_argument("--output", default="train_comparison.json", help="输出文件路径（默认：train_comparison.json）")
    args = parser.parse_args()

    schedule_path = Path(args.schedule)
    output_path = Path(args.output)
    generate_train_comparison(schedule_path, output_path)


if __name__ == "__main__":
    main()