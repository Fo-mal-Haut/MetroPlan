#!/usr/bin/env python3
"""
查找所有可行路径的功能。

基于时刻表图，使用 DFS 搜索从起点到终点的路径，包括换乘。
"""

import json
import argparse
from pathlib import Path
from typing import Dict, List, Any, Tuple, Optional
from collections import defaultdict


def parse_time(time_str: str) -> int:
    """将 HH:MM 格式时间转换为分钟数。00:00 视为 1440。"""
    if not time_str:
        return 0
    if time_str == "00:00":
        return 1440
    try:
        h, m = map(int, time_str.split(":"))
        return h * 60 + m
    except ValueError:
        return 0


def load_graph(graph_path: Path) -> Tuple[List[Tuple[str, str, str]], List[Dict[str, Any]]]:
    """加载时刻表图。"""
    with graph_path.open(encoding="utf-8") as f:
        data = json.load(f)
    nodes = [tuple(n) for n in data["nodes"]]
    edges = data["edges"]
    return nodes, edges


def build_indices(nodes: List[Tuple[str, str, str]], edges: List[Dict[str, Any]]) -> Tuple[Dict[str, List[Tuple[Tuple[str, str, str], int]]], Dict[str, List[Dict[str, Any]]]]:
    """构建索引：站点到节点（按时间排序），车次到边。"""
    station_to_nodes = defaultdict(list)
    for node in nodes:
        station, train, time_str = node
        time_min = parse_time(time_str)
        station_to_nodes[station].append((node, time_min))
    for station in station_to_nodes:
        station_to_nodes[station].sort(key=lambda x: x[1])  # 按时间排序

    train_to_edges = defaultdict(list)
    for edge in edges:
        train = edge["from"][1]
        train_to_edges[train].append(edge)

    return station_to_nodes, train_to_edges


def find_paths(start_station: str, end_station: str, dep_time_str: str, graph_path: Path, max_paths: int = 50, max_depth: int = 5) -> List[Dict[str, Any]]:
    """查找从起点到终点的所有可行路径。"""
    nodes, edges = load_graph(graph_path)
    station_to_nodes, train_to_edges = build_indices(nodes, edges)

    dep_time_min = parse_time(dep_time_str)
    start_nodes = [node for node, t in station_to_nodes.get(start_station, []) if t >= dep_time_min]
    if not start_nodes:
        return []

    all_paths = []

    def dfs(current_node: Tuple[str, str, str], path: List[Dict[str, Any]], visited_trains: set, current_time: int, depth: int):
        if len(all_paths) >= max_paths or depth > max_depth:
            return
        current_station, current_train, current_time_str = current_node
        if current_station == end_station:
            # 计算总时间
            total_dep_time = parse_time(path[0]["dep_time"])
            total_arr_time = current_time
            total_time = total_arr_time - total_dep_time if total_arr_time >= total_dep_time else total_arr_time + 1440 - total_dep_time
            all_paths.append({
                "segments": path,
                "total_dep_time": path[0]["dep_time"],
                "total_arr_time": current_time_str,
                "total_time_minutes": total_time
            })
            return

        # 沿当前车次前进
        next_edges = [e for e in train_to_edges[current_train] if e["from"] == list(current_node)]
        for edge in next_edges:
            next_node = tuple(edge["to"])
            next_station, next_train, next_time_str = next_node
            segment = {
                "train": current_train,
                "from": current_station,
                "to": next_station,
                "dep_time": current_time_str,
                "arr_time": next_time_str
            }
            dfs(next_node, path + [segment], visited_trains, parse_time(next_time_str), depth + 1)

        # 换乘：当前站后续出发车次
        transfer_nodes = [node for node, t in station_to_nodes.get(current_station, []) if t > current_time + 3 and node[1] not in visited_trains]  # 停站 3 分钟
        for transfer_node in transfer_nodes:
            transfer_station, transfer_train, transfer_time_str = transfer_node
            segment = {
                "train": transfer_train,
                "from": current_station,
                "to": transfer_station,  # 换乘到同一站
                "dep_time": transfer_time_str,
                "arr_time": transfer_time_str  # 出发时间
            }
            dfs(transfer_node, path + [segment], visited_trains | {transfer_train}, parse_time(transfer_time_str), depth + 1)

    for start_node in start_nodes:
        dfs(start_node, [], {start_node[1]}, parse_time(start_node[2]), 0)

    # 排序：先按出发时间，再按总耗时
    all_paths.sort(key=lambda p: (parse_time(p["total_dep_time"]), p["total_time_minutes"]))
    return all_paths[:max_paths]


def main():
    parser = argparse.ArgumentParser(description="查找从起点到终点的可行路径。")
    parser.add_argument("--start", required=True, help="起点站")
    parser.add_argument("--end", required=True, help="终点站")
    parser.add_argument("--time", required=True, help="出发时间 (HH:MM)")
    parser.add_argument("--graph", default="../graph/timetable_graph.json", help="时刻表图文件")
    parser.add_argument("--output", default="paths.json", help="输出文件")
    parser.add_argument("--max_paths", type=int, default=50, help="最大路径数")
    parser.add_argument("--max_depth", type=int, default=50, help="最大搜索深度")
    args = parser.parse_args()

    graph_path = Path(args.graph)
    paths = find_paths(args.start, args.end, args.time, graph_path, args.max_paths, args.max_depth)

    output_path = Path(args.output)
    with output_path.open("w", encoding="utf-8") as f:
        json.dump(paths, f, ensure_ascii=False, indent=2)
    print(f"[完成] 找到 {len(paths)} 条路径，输出到 {output_path}")


if __name__ == "__main__":
    main()