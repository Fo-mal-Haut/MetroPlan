import json
import argparse
from pathlib import Path

def load_graph(graph_file):
    """Load the timetable graph from JSON file."""
    with open(graph_file, 'r', encoding='utf-8') as f:
        data = json.load(f)
    nodes = data['nodes']
    edges = data['edges']
    return nodes, edges

def load_schedule(schedule_file):
    """Load schedule list to get train types."""
    with open(schedule_file, 'r', encoding='utf-8') as f:
        data = json.load(f)
    train_info = {train['id']: train['is_fast'] for train in data['train']}
    return train_info

def build_adjacency_list(nodes, edges):
    """Build adjacency list from nodes and edges."""
    node_to_index = {tuple(node): i for i, node in enumerate(nodes)}
    adj = {i: [] for i in range(len(nodes))}
    for edge in edges:
        from_node = tuple(edge['from'])
        to_node = tuple(edge['to'])
        if from_node in node_to_index and to_node in node_to_index:
            from_idx = node_to_index[from_node]
            to_idx = node_to_index[to_node]
            travel_time = edge.get('segment_travel_time', 1)
            adj[from_idx].append((to_idx, travel_time))
    return adj

def parse_time(time_str):
    """Parse time string HH:MM to minutes since midnight."""
    if time_str == "00:00":
        return 1440  # Next day
    h, m = map(int, time_str.split(':'))
    return h * 60 + m

def to_time(minutes):
    """Convert minutes to HH:MM format."""
    if minutes >= 1440:
        minutes -= 1440
    h = minutes // 60
    m = minutes % 60
    return f"{h:02d}:{m:02d}"

def find_all_paths(nodes, adj, start_station, end_station, train_info):
    """Find all possible paths from start_station to end_station using DFS, including transfers."""
    paths = []
    
    # Find all starting nodes at start_station
    start_nodes = [i for i, node in enumerate(nodes) if node[0] == start_station]
    
    def dfs(current_node, current_arrival, path, visited_nodes, current_trains, current_transfers, start_time, transfer_count):
        current_station = nodes[current_node][0]
        
        if current_station == end_station:
            # Found a path to end_station
            train_sequence = list(dict.fromkeys(current_trains))  # unique trains in order
            transfer_stations = current_transfers
            total_minutes = current_arrival - start_time
            total_time = to_time(total_minutes)
            is_fast = any(train_info.get(train, False) for train in train_sequence)
            paths.append({
                'train_sequence': train_sequence,
                'transfer_stations': transfer_stations,
                'departure_time': to_time(start_time),
                'arrival_time': to_time(current_arrival),
                'total_time': total_time,
                'is_fast': is_fast
            })
            return
        
        # Explore neighbors
        for neighbor, travel_time in adj[current_node]:
            # if neighbor in visited_nodes:  # Temporarily remove to check for cycles
            #     continue
            neighbor_station = nodes[neighbor][0]
            neighbor_train = nodes[neighbor][1]
            neighbor_time = parse_time(nodes[neighbor][2])
            
            arrival_time = current_arrival + travel_time
            transfer_time = -20  # More flexibility
            if neighbor_time <= arrival_time + transfer_time:
                continue
            
            new_trains = current_trains + [neighbor_train]
            new_transfers = current_transfers[:]
            new_transfer_count = transfer_count
            if neighbor_train != nodes[current_node][1]:
                # Transfer at current_station
                if current_station not in new_transfers:
                    new_transfers.append(current_station)
                    new_transfer_count += 1
                if new_transfer_count > 2:
                    continue
            
            dfs(neighbor, neighbor_time, path + [neighbor], visited_nodes | {neighbor}, new_trains, new_transfers, start_time, new_transfer_count)
        
        # Try transfers at current station if not end
        # Removed due to recursion depth
    
    for start_node in start_nodes:
        start_time = parse_time(nodes[start_node][2])
        dfs(start_node, start_time, [start_node], {start_node}, [nodes[start_node][1]], [], start_time, 0)
    
    return paths

def main():
    parser = argparse.ArgumentParser(description='Find direct train paths using DFS.')
    parser.add_argument('--start', required=True, help='Start station ID')
    parser.add_argument('--end', required=True, help='End station ID')
    parser.add_argument('--schedule', default='schedule_list.json', help='Path to schedule JSON file')
    parser.add_argument('--graph', default='graph/timetable_graph.json', help='Path to graph JSON file')
    parser.add_argument('--output', default='Result_Finding/all_paths.json', help='Output JSON file')
    
    args = parser.parse_args()
    
    graph_path = Path(args.graph)
    if not graph_path.exists():
        print(f"Graph file {graph_path} not found.")
        return
    
    nodes, edges = load_graph(graph_path)
    adj = build_adjacency_list(nodes, edges)
    train_info = load_schedule(args.schedule)
    
    paths = find_all_paths(nodes, adj, args.start, args.end, train_info)
    
    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(paths, f, ensure_ascii=False, indent=2)
    
    # Statistics for direct paths
    direct_paths = [p for p in paths if not p['transfer_stations']]
    total_direct = len(direct_paths)
    fast_direct = len([p for p in direct_paths if p['is_fast']])
    slow_direct = total_direct - fast_direct
    
    print(f"Found {len(paths)} total paths. Results saved to {output_path}")
    print(f"Direct paths: Total {total_direct}, Fast {fast_direct}, Slow {slow_direct}")

if __name__ == '__main__':
    main()