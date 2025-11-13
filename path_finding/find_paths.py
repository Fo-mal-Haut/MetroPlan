#!/usr/bin/env python3
"""
基于时间的 BFS 路径搜索：
- 按时间顺序探索（优先队列）
- 时间剪枝：同日有效；可基于直达最短时间设置上限（T + 120min）
- 换乘限制：限制最大换乘次数；避免重复乘坐同一车次
- Dominance 检查：同站到达，若 A 比 B 更早且换乘不多，则剪枝 B

节点 = (station, train, departure_time)
边：同一车次内连续站点的行车边（weight = T2 - T1；包含站B停站）
输出：完整路径段列表（仅包含行车段，不单独记录换乘段）

使用方法：

# 进入路径查找目录
cd f:\Exploration\MetroPlan\path_finding

# 从 佛山西 到 肇庆，06:00 出发，最多 50 条方案，最多换乘 2 次，最小换乘 3 分钟，
# 默认时间窗口 12 小时，直达基础加时 120 分钟
python find_paths.py `
  --start "佛山西" `
  --end "肇庆" `
  --time "06:00" `
  --max_paths 50 `
  --max_transfers 2 `
  --min_transfer 3 `
  --default_limit_hours 12 `
  --extra_direct_limit 120 `
  --output paths.json
"""

import json
import argparse
import heapq
from pathlib import Path
from typing import Dict, List, Any, Tuple, Optional
from collections import defaultdict


def parse_time(time_str: str) -> int:
    """将 HH:MM 转为分钟。将 00:00 视为 1440（次日 0 点）。"""
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
    with graph_path.open(encoding="utf-8") as f:
        data = json.load(f)
    nodes = [tuple(n) for n in data["nodes"]]
    edges = data["edges"]
    return nodes, edges


def build_indices(nodes: List[Tuple[str, str, str]], edges: List[Dict[str, Any]]):
    """构建高效索引：
    - station_departures[station] = [(dep_min, node)]（按时间升序）
    - next_by_node[node] = [(next_node, edge)]
    - train_to_nodes[train] = [(dep_min, node)]（按时间升序）
    """
    station_departures: Dict[str, List[Tuple[int, Tuple[str, str, str]]]] = defaultdict(list)
    for node in nodes:
        station, train, time_str = node
        t = parse_time(time_str)
        station_departures[station].append((t, node))
    for st in station_departures:
        station_departures[st].sort(key=lambda x: x[0])

    next_by_node: Dict[Tuple[str, str, str], List[Tuple[Tuple[str, str, str], Dict[str, Any]]]] = defaultdict(list)
    for e in edges:
        f = tuple(e["from"])  # (station, train, time)
        t = tuple(e["to"])
        next_by_node[f].append((t, e))

    train_to_nodes: Dict[str, List[Tuple[int, Tuple[str, str, str]]]] = defaultdict(list)
    for node in nodes:
        station, train, time_str = node
        t = parse_time(time_str)
        train_to_nodes[train].append((t, node))
    for tr in train_to_nodes:
        train_to_nodes[tr].sort(key=lambda x: x[0])

    return station_departures, next_by_node, train_to_nodes


def find_fastest_direct(start_station: str, end_station: str, dep_time_min: int, train_to_nodes: Dict[str, List[Tuple[int, Tuple[str, str, str]]]]) -> Optional[int]:
    """估算最快直达时间（同一车次包含起终点，且起点时间 >= dep_time_min）。返回分钟数；无则 None。"""
    best = None
    for train, seq in train_to_nodes.items():
        # 构建 station -> (index, time) 映射
        station_index = {}
        for idx, (t, node) in enumerate(seq):
            st = node[0]
            station_index[st] = (idx, t)
        if start_station in station_index and end_station in station_index:
            i_s, t_s = station_index[start_station]
            i_e, t_e = station_index[end_station]
            if i_e > i_s and t_s >= dep_time_min and t_e >= t_s:
                dur = t_e - t_s
                if best is None or dur < best:
                    best = dur
    return best


def dominated(new_time: int, new_transfers: int, states: List[Tuple[int, int]]) -> bool:
    """判断新状态是否被已有状态支配（时间不早且换乘不小）。"""
    for t, k in states:
        if t <= new_time and k <= new_transfers:
            return True
    return False


def update_dominance(new_time: int, new_transfers: int, states: List[Tuple[int, int]]):
    """插入新状态并移除被其支配的旧状态。"""
    keep: List[Tuple[int, int]] = []
    for t, k in states:
        if not (t >= new_time and k >= new_transfers):
            keep.append((t, k))
    keep.append((new_time, new_transfers))
    keep.sort()
    return keep


def find_paths(
    start_station: str,
    end_station: str,
    dep_time_str: str,
    graph_path: Path,
    max_paths: int = 50,
    max_transfers: int = 2,
    min_transfer_min: int = 10,
    default_limit_hours: int = 12,
    extra_direct_limit_min: int = 120,
) -> List[Dict[str, Any]]:
    """时间优先 BFS 搜索所有可行路径。"""
    nodes, edges = load_graph(graph_path)
    station_departures, next_by_node, train_to_nodes = build_indices(nodes, edges)

    dep_time_min = parse_time(dep_time_str)
    latest_allowed = dep_time_min + default_limit_hours * 60

    # 直达最短作为时间上限（T + 120min）
    direct = find_fastest_direct(start_station, end_station, dep_time_min, train_to_nodes)
    if direct is not None:
        latest_allowed = min(latest_allowed, dep_time_min + direct + extra_direct_limit_min)

    # 初始出发节点（S 站 T0 之后）
    start_candidates = [(t, node) for (t, node) in station_departures.get(start_station, []) if t >= dep_time_min and t <= latest_allowed]
    if not start_candidates:
        return []

    # 优先队列：（当前时间，递增序号，当前节点，路径段列表，换乘数，已乘车次集合，首发时间字符串）
    heap: List[Tuple[int, int, Tuple[str, str, str], List[Dict[str, Any]], int, frozenset, str]] = []
    seq = 0
    for t, node in start_candidates:
        seq += 1
        heapq.heappush(heap, (t, seq, node, [], 0, frozenset({node[1]}), node[2]))

    results: List[Dict[str, Any]] = []
    # dominance[station] = [(best_time, transfers), ...]
    dominance: Dict[str, List[Tuple[int, int]]] = defaultdict(list)

    while heap and len(results) < max_paths:
        curr_time, _, curr_node, path, transfers, used_trains, first_dep_str = heapq.heappop(heap)

        if curr_time > latest_allowed:
            continue

        curr_station, curr_train, curr_time_str = curr_node

        # dominance 剪枝（按站点聚类）
        st_states = dominance[curr_station]
        if dominated(curr_time, transfers, st_states):
            continue
        dominance[curr_station] = update_dominance(curr_time, transfers, st_states)

        # 到达终点：保存方案
        if curr_station == end_station and path:
            total_dep = parse_time(first_dep_str)
            total_arr = curr_time
            total_time = total_arr - total_dep if total_arr >= total_dep else total_arr + 1440 - total_dep
            results.append({
                "segments": path,
                "total_dep_time": first_dep_str,
                "total_arr_time": curr_time_str,
                "total_time_minutes": total_time,
                "transfers": transfers
            })
            # 继续探索可能更早的其他方案
            continue

        # 1) 沿当前车次前进
        for next_node, edge in next_by_node.get(curr_node, []):
            next_time_str = next_node[2]
            next_time = parse_time(next_time_str)
            if next_time <= curr_time:
                continue  # 防止时间回退（理论不应发生）
            if next_time > latest_allowed:
                continue
            segment = {
                "train": curr_train,
                "from": curr_station,
                "to": next_node[0],
                "dep_time": curr_time_str,
                "arr_time": next_time_str,
                "weight": edge.get("weight"),
                "segment_travel_time": edge.get("segment_travel_time"),
            }
            seq += 1
            heapq.heappush(heap, (next_time, seq, next_node, path + [segment], transfers, used_trains, first_dep_str))

        # 2) 换乘（若未超限制）
        if transfers < max_transfers:
            # 在当前站查找满足最小换乘时间的其它车次
            departures = station_departures.get(curr_station, [])
            # 二分可优化，这里线性筛（数据量可接受）
            for t_dep, node in departures:
                if t_dep <= curr_time + min_transfer_min:
                    continue
                tr = node[1]
                if tr == curr_train or tr in used_trains:
                    continue
                if t_dep > latest_allowed:
                    break
                # 推入队列，不添加虚假段，下一步沿该车次前进时再添加段
                seq += 1
                heapq.heappush(heap, (t_dep, seq, node, path, transfers + 1, used_trains | {tr}, first_dep_str))

    # 后处理排序：先按出发时间，再按总耗时
    results.sort(key=lambda p: (parse_time(p["total_dep_time"]), p["total_time_minutes"]))
    return results[:max_paths]


def main():
    parser = argparse.ArgumentParser(description="基于时间的BFS查找所有可行路径。")
    parser.add_argument("--start", required=True, help="起点站")
    parser.add_argument("--end", required=True, help="终点站")
    parser.add_argument("--time", required=True, help="出发时间 (HH:MM)")
    parser.add_argument("--graph", default="../graph/timetable_graph.json", help="时刻表图文件")
    parser.add_argument("--output", default="paths.json", help="输出文件")
    parser.add_argument("--max_paths", type=int, default=50, help="最大路径数")
    parser.add_argument("--max_transfers", type=int, default=2, help="最大换乘次数")
    parser.add_argument("--min_transfer", type=int, default=3, help="最小换乘时间（分钟）")
    parser.add_argument("--default_limit_hours", type=int, default=12, help="默认时间窗口（小时）")
    parser.add_argument("--extra_direct_limit", type=int, default=120, help="直达最短基础上的额外上限（分钟）")
    args = parser.parse_args()

    graph_path = Path(args.graph)
    paths = find_paths(
        args.start,
        args.end,
        args.time,
        graph_path,
        args.max_paths,
        args.max_transfers,
        args.min_transfer,
        args.default_limit_hours,
        args.extra_direct_limit,
    )

    output_path = Path(args.output)
    with output_path.open("w", encoding="utf-8") as f:
        json.dump(paths, f, ensure_ascii=False, indent=2)
    print(f"[完成] 找到 {len(paths)} 条路径，输出到 {output_path}")


if __name__ == "__main__":
    main()