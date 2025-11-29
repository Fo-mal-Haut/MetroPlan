"""Enumerate intercity travel plans using fast_graph with explicit transfer edges.

功能：
    - 读取 `graph/fast_graph.json`（包含行车 + 换乘边）和 `schedule_list.json`；
    - 以车站名字为起终点，深度优先遍历所有满足换乘次数上限的路径；
    - 输出每条方案的车次序列、换乘细节、总时长等信息；
    - 多条方案车次序列一致时自动合并，并列出所有可选换乘站。

使用方法示例：
    python DFS_PathFinding/find_paths_dfs.py --start 琶洲 --end 西平西 \
        --graph graph/fast_graph.json --schedule schedule_list.json \
        --max_transfers 2 --window_minutes 120
    结果默认写入 `Result_Finding/path_起点_终点.json`。
"""

import json
import argparse
from copy import deepcopy
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Any


def load_graph(graph_file: Path):
    """Load graph JSON and return (nodes, edges)."""
    with open(graph_file, 'r', encoding='utf-8') as f:
        data = json.load(f)
    return data['nodes'], data['edges']


def load_schedule(schedule_file: Path) -> Dict[str, Any]:
    """Load schedule list and return a mapping train_id -> train info dict.
    The info will at least include 'is_fast'. It may include 'directionality' too.
    """
    with open(schedule_file, 'r', encoding='utf-8') as f:
        data = json.load(f)
    info = {}
    for train in data.get('train', []):
        info[train['id']] = {
            'is_fast': train.get('is_fast', False),
            'directionality': train.get('directionality')
        }
    return info


def load_directionality_map(schedule_file: Path) -> Dict[str, List[int]]:
    """Return a mapping train_id -> direction vector for trains that provide it.
    If schedule file does not contain 'directionality', the train will not be present in the result.
    """
    with open(schedule_file, 'r', encoding='utf-8') as f:
        data = json.load(f)
    out = {}
    for train in data.get('train', []):
        v = train.get('directionality')
        if isinstance(v, list):
            out[train['id']] = v
    return out


def parse_time(time_str: str) -> int:
    """Parse HH:MM into minutes since midnight. "00:00" maps to next-day 24:00."""
    if not time_str:
        return 0
    if time_str == "00:00":
        return 1440
    hours, minutes = map(int, time_str.split(':'))
    return hours * 60 + minutes


def to_time(total_minutes: int) -> str:
    """Convert minutes since midnight into HH:MM, wrapping every 24 hours."""
    total_minutes %= 1440
    hours = total_minutes // 60
    minutes = total_minutes % 60
    return f"{hours:02d}:{minutes:02d}"
def build_adjacency(nodes: List[List[str]], edges: List[Dict[str, Any]]):
    """Construct adjacency list with edge metadata."""
    node_lookup = {tuple(node): idx for idx, node in enumerate(nodes)}
    adjacency: Dict[int, List[Dict[str, Any]]] = {idx: [] for idx in range(len(nodes))}

    for edge in edges:
        from_idx = node_lookup.get(tuple(edge['from']))
        to_idx = node_lookup.get(tuple(edge['to']))
        if from_idx is None or to_idx is None:
            continue

        duration = edge.get('weight') or edge.get('segment_travel_time') or 0
        if duration <= 0:
            continue

        edge_info = {
            'to': to_idx,
            'type': edge.get('type', 'travel'),
            'duration': duration,
        }
        adjacency[from_idx].append(edge_info)

    return adjacency


def summarize_path(nodes: List[List[str]],
                   edge_history: List[Dict[str, Any]],
                   train_sequence: List[str],
                   start_time: int,
                   end_time: int,
                   train_info: Dict[str, bool]) -> Dict[str, Any]:
    """Create a summary object for a completed path."""
    timeline = start_time
    transfer_details: List[Dict[str, Any]] = []
    # 如多条方案车次序列相同，则合并为一条，并列出所有可选换乘站。

    for edge in edge_history:
        prev_time = timeline
        timeline += edge['duration']
        if edge['type'] == 'transfer':
            station_name = nodes[edge['from']][0]
            transfer_details.append({
                'station': station_name,
                'arrival_time': to_time(prev_time),
                'departure_time': to_time(timeline),
                'wait_minutes': edge['duration']
            })

    # Ensure final timeline matches recorded end time
    if timeline != end_time:
        timeline = end_time

    total_minutes = timeline - start_time
    if total_minutes < 0:
        total_minutes += 1440

    train_seq_copy = list(train_sequence)
    is_fast = any(train_info.get(train_id, False) for train_id in train_seq_copy)

    return {
        'type': 'Transfer' if transfer_details else 'Direct',
        'train_sequence': train_seq_copy,
        'transfer_details': transfer_details,
        'departure_time': to_time(start_time),
        'arrival_time': to_time(timeline),
        'total_time': f"{total_minutes // 60}h {total_minutes % 60}m",
        'total_minutes': total_minutes,
        'is_fast': is_fast,
        'transfer_count': len(transfer_details)
    }


def find_all_paths(nodes: List[List[str]],
                   adjacency: Dict[int, List[Dict[str, Any]]],
                   start_station: str,
                   end_station: str,
                   train_info: Dict[str, Any],
                   direction_map: Dict[str, List[int]] | None = None,
                   max_transfers: int = 2) -> List[Dict[str, Any]]:
    """Enumerate paths between stations using DFS over fast_graph."""
    paths: List[Dict[str, Any]] = []
    start_nodes = [idx for idx, node in enumerate(nodes) if node[0] == start_station]

    if not start_nodes:
        return []

    def dfs(current_idx: int,
            current_time: int,
            transfers_used: int,
            path: List[int],
            edge_history: List[Dict[str, Any]],
            train_sequence: List[str],
            start_time: int):
        station_name = nodes[current_idx][0]

        # Reached destination; require at least one edge in the journey
        if station_name == end_station and edge_history:
            path_summary = summarize_path(
                nodes,
                edge_history,
                train_sequence,
                start_time,
                current_time,
                train_info
            )
            # If this path contains transfers, check directionality consistency
            if direction_map and path_summary.get('transfer_count', 0) > 0:
                # For adjacent trains, ensure no opposite directions on any line
                seq = path_summary.get('train_sequence', [])
                invalid = False
                for i in range(len(seq) - 1):
                    a = direction_map.get(seq[i])
                    b = direction_map.get(seq[i+1])
                    if not a or not b:
                        # if either train lacks directionality info, skip consistency check
                        continue
                    # check for opposite direction on any line: a_j == -b_j
                    for j in range(min(len(a), len(b))):
                        if a[j] != 0 and b[j] != 0 and a[j] == -b[j]:
                            invalid = True
                            break
                    if invalid:
                        break
                if invalid:
                    # drop this path (do not append)
                    return
            paths.append(path_summary)
            return

        for edge in adjacency.get(current_idx, []):
            neighbor_idx = edge['to']
            if neighbor_idx in path:
                continue

            neighbor_train = nodes[neighbor_idx][1]
            current_train = nodes[current_idx][1]

            edge_duration = edge['duration']
            if edge_duration <= 0:
                continue

            next_time = current_time + edge_duration

            next_transfers = transfers_used
            if edge['type'] == 'transfer' or neighbor_train != current_train:
                next_transfers += 1
            if next_transfers > max_transfers:
                continue

            if train_sequence and neighbor_train == train_sequence[-1]:
                next_train_sequence = train_sequence
            else:
                next_train_sequence = train_sequence + [neighbor_train]

            path.append(neighbor_idx)
            edge_history.append({
                'from': current_idx,
                'to': neighbor_idx,
                'type': edge['type'],
                'duration': edge_duration
            })

            dfs(
                neighbor_idx,
                next_time,
                next_transfers,
                path,
                edge_history,
                next_train_sequence,
                start_time
            )

            edge_history.pop()
            path.pop()

    for start_idx in start_nodes:
        start_time = parse_time(nodes[start_idx][2])
        start_train = nodes[start_idx][1]
        dfs(
            current_idx=start_idx,
            current_time=start_time,
            transfers_used=0,
            path=[start_idx],
            edge_history=[],
            train_sequence=[start_train],
            start_time=start_time
        )

    # Assign identifiers and sort by total duration then departure
    paths.sort(key=lambda item: (item['total_minutes'], item['departure_time']))
    for idx, entry in enumerate(paths, start=1):
        entry['id'] = idx

    return paths


def merge_paths_by_train_sequence(paths: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Merge paths that share identical train sequences and timing while aggregating transfer options."""
    grouped: Dict[tuple, Dict[str, Any]] = {}
    ordered_keys: List[tuple] = []

    for entry in paths:
        transfer_count = entry.get('transfer_count', len(entry.get('transfer_details', [])))
        key = (
            tuple(entry.get('train_sequence', [])),
            entry.get('type'),
            transfer_count,
            entry.get('departure_time'),
            entry.get('arrival_time'),
            entry.get('total_minutes')
        )

        if key not in grouped:
            base = deepcopy(entry)
            if transfer_count > 0:
                option_lists: List[List[Dict[str, Any]]] = [[] for _ in range(transfer_count)]
                for idx, detail in enumerate(entry.get('transfer_details', [])):
                    option_lists[idx].append(deepcopy(detail))
                base['_transfer_option_lists'] = option_lists
            grouped[key] = base
            ordered_keys.append(key)
            continue

        base = grouped[key]
        if transfer_count == 0:
            continue
        option_lists = base.setdefault('_transfer_option_lists', [[] for _ in range(transfer_count)])
        details = entry.get('transfer_details', [])
        for idx, detail in enumerate(details):
            if idx >= len(option_lists):
                option_lists.append([])
            if not any(existing == detail for existing in option_lists[idx]):
                option_lists[idx].append(deepcopy(detail))

    merged: List[Dict[str, Any]] = []
    for key in ordered_keys:
        base = grouped[key]
        option_lists = base.pop('_transfer_option_lists', None)
        if option_lists:
            base['transfer_options'] = [
                {
                    'step': idx + 1,
                    'options': option_list
                }
                for idx, option_list in enumerate(option_lists)
                if option_list
            ]
            base['transfer_details'] = [opts[0] for opts in option_lists if opts]
        merged.append(base)

    return merged


def main():
    parser = argparse.ArgumentParser(description='Enumerate intercity paths with up to two transfers.')
    parser.add_argument('--start', required=True, help='Start station name')
    parser.add_argument('--end', required=True, help='End station name')
    parser.add_argument('--schedule', default='schedule_with_directionality.json', help='Path to schedule JSON file')
    parser.add_argument('--graph', default='graph/fast_graph.json', help='Path to fast graph JSON file')
    parser.add_argument('--output', default='Result_Finding/all_paths.json', help='Output JSON file')
    parser.add_argument('--max_transfers', type=int, default=2, help='Maximum number of transfers allowed')
    parser.add_argument('--window_minutes', type=int, default=120,
                        help='Keep paths whose total_minutes <= (fastest + window). Default: 120 (2h).')

    args = parser.parse_args()

    graph_path = Path(args.graph)
    if not graph_path.exists():
        print(f"Graph file {graph_path} not found.")
        return

    schedule_path = Path(args.schedule)
    if not schedule_path.exists():
        print(f"Schedule file {schedule_path} not found.")
        return

    nodes, edges = load_graph(graph_path)
    adjacency = build_adjacency(nodes, edges)
    train_info = load_schedule(schedule_path)
    # try to load directionality mapping from a schedule that contains directionality
    direction_map = {}
    try:
        direction_map = load_directionality_map(schedule_path)
    except Exception:
        # Not fatal; the provided schedule may not include directionality vectors
        direction_map = {}

    all_paths = find_all_paths(
        nodes,
        adjacency,
        args.start,
        args.end,
        train_info,
        direction_map=direction_map,
        max_transfers=args.max_transfers
    )

    if not all_paths:
        print("No feasible paths were found with the current constraints.")
        return

    fastest_minutes = min(p['total_minutes'] for p in all_paths)
    window_minutes = max(args.window_minutes, 0)
    cutoff_minutes = fastest_minutes + window_minutes
    filtered_paths = [p for p in all_paths if p['total_minutes'] <= cutoff_minutes]

    # Ensure deterministic order before merging
    filtered_paths.sort(key=lambda item: (item['total_minutes'], item['departure_time']))

    paths = merge_paths_by_train_sequence(filtered_paths)
    for idx, entry in enumerate(paths, start=1):
        entry['id'] = idx

    output_filename = f"path_{args.start}_{args.end}.json"
    output_path = Path('Result_Finding') / output_filename
    output_path.parent.mkdir(parents=True, exist_ok=True)

    output_payload = {
        'start_station': args.start,
        'end_station': args.end,
        'generated_at': datetime.now(timezone.utc).astimezone().isoformat(timespec='seconds'),
        'summary': {
            'raw_path_count': len(all_paths),
            'window_minutes': window_minutes,
            'fastest_minutes': fastest_minutes,
            'filtered_path_count': len(filtered_paths),
            'merged_path_count': len(paths)
        },
        'paths': paths
    }

    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(output_payload, f, ensure_ascii=False, indent=2)

    direct_paths = [p for p in paths if p['type'] == 'Direct']
    total_direct = len(direct_paths)
    fast_direct = len([p for p in direct_paths if p['is_fast']])
    slow_direct = total_direct - fast_direct

    transfer_breakdown = {0: 0, 1: 0, 2: 0}
    for p in paths:
        count = min(max(p.get('transfer_count', 0), 0), 2)
        transfer_breakdown[count] = transfer_breakdown.get(count, 0) + 1

    print(
    f"Found {len(all_paths)} raw paths. Fastest duration: {fastest_minutes} min. "
    f"Keeping {len(filtered_paths)} paths within +{window_minutes} min; "
    f"after merging identical train sequences, {len(paths)} remain."
    )
    print(f"Results saved to {output_path}")
    print(
        "Transfer breakdown: Direct={0}, One-transfer={1}, Two-transfer={2}".format(
            transfer_breakdown.get(0, 0),
            transfer_breakdown.get(1, 0),
            transfer_breakdown.get(2, 0)
        )
    )
    print(f"Direct paths: Total {total_direct}, Fast {fast_direct}, Slow {slow_direct}")


if __name__ == '__main__':
    # Entry point: enumerate intercity itineraries (0-2 transfers). Usage:
    # python DFS_PathFinding/find_paths_dfs.py --start <起点站> --end <终点站>
    # 通过命令行传入起终点/图/时刻表/换乘上限，生成所有可行方案
    main()