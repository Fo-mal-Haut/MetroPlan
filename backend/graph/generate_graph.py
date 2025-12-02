#!/usr/bin/env python3
"""
根据 schedule_list.json 生成时刻表图。

节点：(station_id, train_id, departure_time)
边：同一车次内连续站点间的行车边
权重：旅行时间 = T2 - T1
附加：segment_travel_time = 旅行时间 - 默认停站时间（3分钟）
"""

import json
import argparse
from pathlib import Path
from typing import Dict, List, Any, Tuple


def parse_time(time_str: str) -> int:
    """将 HH:MM 格式时间转换为分钟数（从午夜开始）。00:00 视为次日 0 点（1440 分钟）。"""
    if not time_str:
        return 0
    if time_str == "00:00":
        return 1440  # 次日 0 点
    try:
        h, m = map(int, time_str.split(":"))
        return h * 60 + m
    except ValueError:
        return 0


def build_graph(schedule_path: Path, output_path: Path, stop_time: int = 3) -> None:
    """从 schedule_list.json 构建时刻表图。"""
    if not schedule_path.exists():
        raise FileNotFoundError(f"文件不存在: {schedule_path}")

    with schedule_path.open(encoding="utf-8") as f:
        data = json.load(f)

    trains = data.get("train", [])
    if not trains:
        print("[警告] 无车次数据")
        return

    nodes: List[Tuple[str, str, str]] = []
    edges: List[Dict[str, Any]] = []

    for tr in trains:
        train_id = tr.get("id", "")
        stations = tr.get("stations", [])
        if len(stations) < 2:
            continue  # 至少两个站点才能有边

        for i in range(len(stations) - 1):
            st_a = stations[i]
            st_b = stations[i + 1]
            station_a = st_a.get("name", "")
            time_a_str = st_a.get("time", "")
            station_b = st_b.get("name", "")
            time_b_str = st_b.get("time", "")

            time_a = parse_time(time_a_str)
            time_b = parse_time(time_b_str)
            if time_a == 0 or time_b == 0:
                continue  # 跳过无效时间

            node_a = (station_a, train_id, time_a_str)
            node_b = (station_b, train_id, time_b_str)

            if node_a not in nodes:
                nodes.append(node_a)
            if node_b not in nodes:
                nodes.append(node_b)

            travel_time = time_b - time_a
            segment_travel_time = travel_time - stop_time

            edges.append({
                "from": node_a,
                "to": node_b,
                "weight": travel_time,
                "segment_travel_time": segment_travel_time
            })

    out_obj = {
        "nodes": nodes,
        "edges": edges,
        "summary": {
            "total_nodes": len(nodes),
            "total_edges": len(edges),
            "stop_time_minutes": stop_time
        }
    }

    output_path.write_text(json.dumps(out_obj, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"[完成] 图输出 -> {output_path} (节点:{len(nodes)}, 边:{len(edges)})")


def main():
    parser = argparse.ArgumentParser(description="根据 schedule_list.json 生成时刻表图。")
    parser.add_argument("--schedule", default="../schedule_list.json", help="schedule_list.json 文件路径（默认：../schedule_list.json）")
    parser.add_argument("--output", default="timetable_graph.json", help="输出文件路径（默认：timetable_graph.json）")
    parser.add_argument("--stop_time", type=int, default=3, help="默认停站时间（分钟，默认：3）")
    args = parser.parse_args()

    schedule_path = Path(args.schedule)
    output_path = Path(args.output)
    build_graph(schedule_path, output_path, args.stop_time)


if __name__ == "__main__":
    main()