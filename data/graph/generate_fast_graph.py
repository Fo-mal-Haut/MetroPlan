#!/usr/bin/env python3
"""基于现有时刻表图，为快车站生成换乘边并输出新的图文件。"""

import json
import argparse
import re
from pathlib import Path
from typing import Dict, List, Tuple, Any, Set


def parse_time(time_str: str) -> int:
    """将 HH:MM 转换为从午夜开始的分钟数，"00:00" 视为次日。"""
    if not time_str:
        return -1
    time_str = time_str.strip()
    if time_str == "00:00":
        return 24 * 60
    try:
        hour, minute = map(int, time_str.split(":"))
    except ValueError:
        return -1
    return hour * 60 + minute


def normalize_station_name(name: str) -> str:
    """统一站名，移除括号内容与多余空白。"""
    if not name:
        return ""
    # 先去除中文全角/半角括号内说明
    cleaned = re.sub(r"[（(].*?[）)]", "", name)
    cleaned = cleaned.replace("（城际）", "").replace("(Intercity)", "")
    return cleaned.strip()


def load_fast_station_names(fast_station_path: Path) -> Set[str]:
    """读取快车站列表，返回规范化后的站名集合。"""
    with fast_station_path.open(encoding="utf-8") as f:
        data = json.load(f)

    names: Set[str] = set()
    for item in data:
        station_name = item.get("station_name", "")
        normalized = normalize_station_name(station_name)
        if normalized:
            names.add(normalized)
    return names


def build_station_time_index(nodes: List[List[str]]) -> Dict[str, List[Tuple[int, int, str]]]:
    """按站名建立时间索引，元素为(分钟值, 节点索引, 车次)。"""
    index: Dict[str, List[Tuple[int, int, str]]] = {}
    for idx, node in enumerate(nodes):
        if len(node) != 3:
            continue
        station, train_id, time_str = node
        time_minutes = parse_time(time_str)
        if time_minutes < 0:
            continue
        normalized = normalize_station_name(station)
        if not normalized:
            continue
        if normalized not in index:
            index[normalized] = []
        index[normalized].append((time_minutes, idx, train_id))

    for normalized_name in index:
        index[normalized_name].sort(key=lambda item: item[0])
    return index


def add_transfer_edges(nodes: List[List[str]],
                       base_edges: List[Dict[str, Any]],
                       fast_stations: Set[str],
                       min_wait: int,
                       max_wait: int) -> Tuple[List[Dict[str, Any]], int]:
    """在快车站添加换乘边，返回新边列表与新增数量。"""
    station_index = build_station_time_index(nodes)
    new_edges: List[Dict[str, Any]] = []
    seen_pairs: Set[Tuple[int, int]] = set()

    for station_name, entries in station_index.items():
        if station_name not in fast_stations:
            continue

        # 对同站点按时间滑窗，生成满足等待区间的换乘边
        for i, (time_a, idx_a, train_a) in enumerate(entries):
            for j in range(i + 1, len(entries)):
                time_b, idx_b, train_b = entries[j]
                wait_minutes = time_b - time_a
                if wait_minutes < min_wait:
                    continue
                if wait_minutes > max_wait:
                    break  # 后续时间只会更大
                if train_a == train_b:
                    continue

                pair = (idx_a, idx_b)
                if pair in seen_pairs:
                    continue
                seen_pairs.add(pair)

                edge = {
                    "from": nodes[idx_a],
                    "to": nodes[idx_b],
                    "weight": wait_minutes,
                    "segment_travel_time": wait_minutes,
                    "type": "transfer",
                    "station": nodes[idx_a][0]
                }
                new_edges.append(edge)

    combined_edges = base_edges + new_edges
    return combined_edges, len(new_edges)


def build_fast_graph(base_graph_path: Path,
                     fast_station_path: Path,
                     output_path: Path,
                     min_wait: int = 15,
                     max_wait: int = 90) -> None:
    """读取基础图，添加换乘边，并输出 fast_graph。"""
    if not base_graph_path.exists():
        raise FileNotFoundError(f"图文件不存在: {base_graph_path}")
    if not fast_station_path.exists():
        raise FileNotFoundError(f"快车站文件不存在: {fast_station_path}")

    with base_graph_path.open(encoding="utf-8") as f:
        graph_data = json.load(f)

    nodes = graph_data.get("nodes", [])
    base_edges = graph_data.get("edges", [])

    fast_stations = load_fast_station_names(fast_station_path)
    combined_edges, added_count = add_transfer_edges(
        nodes, base_edges, fast_stations, min_wait, max_wait
    )

    out_obj: Dict[str, Any] = {
        "nodes": nodes,
        "edges": combined_edges,
        "summary": {
            "total_nodes": len(nodes),
            "total_edges": len(combined_edges),
            "transfer_edges_added": added_count,
            "min_transfer_wait": min_wait,
            "max_transfer_wait": max_wait,
            "source_graph": str(base_graph_path)
        }
    }

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(out_obj, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"[完成] 快车站换乘图输出 -> {output_path} (新增换乘边:{added_count})")


def main() -> None:
    parser = argparse.ArgumentParser(description="为快车站添加换乘边，生成 fast_graph。")
    parser.add_argument("--base", default="graph/timetable_graph.json", help="基础图文件路径")
    parser.add_argument("--fast", default="fast_station_list.json", help="快车站列表文件路径")
    parser.add_argument("--output", default="graph/fast_graph.json", help="输出图文件路径")
    parser.add_argument("--min_wait", type=int, default=15, help="最小换乘等待时间")
    parser.add_argument("--max_wait", type=int, default=90, help="最大换乘等待时间")
    args = parser.parse_args()

    base_path = Path(args.base)
    fast_path = Path(args.fast)
    output_path = Path(args.output)

    build_fast_graph(base_path, fast_path, output_path, args.min_wait, args.max_wait)


if __name__ == "__main__":
    main()
