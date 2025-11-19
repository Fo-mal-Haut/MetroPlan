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

def load_fast_stations(fast_station_file):
    """Load fast station list for transfer validation."""
    with open(fast_station_file, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    stations = set()
    for item in data:
        name = item['station_name']
        # Normalize name: remove "（城际）" suffix if present
        if "（城际）" in name:
            name = name.replace("（城际）", "")
        stations.add(name)
    return stations

def build_station_index(nodes):
    """
    Build an index for quick lookup of trains at each station.
    Returns: { station_name: [(time_minutes, node_index, train_id), ...] }
    """
    station_index = {}
    for i, node in enumerate(nodes):
        station = node[0]
        train_id = node[1]
        time_str = node[2]
        time_minutes = parse_time(time_str)
        
        if station not in station_index:
            station_index[station] = []
        station_index[station].append((time_minutes, i, train_id))
    
    # Sort by time for each station
    for station in station_index:
        station_index[station].sort(key=lambda x: x[0])
        
    return station_index

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

def get_travel_time(u_idx, v_idx, adj):
    """Get travel time between two nodes from adjacency list."""
    for neighbor, time in adj[u_idx]:
        if neighbor == v_idx:
            return time
    return 0

def analyze_path(path, nodes, adj, start_time):
    """Analyze path to extract transfer details and precise arrival time."""
    transfer_infos = []
    last_arrival_time = start_time
    
    for i in range(len(path) - 1):
        u = path[i]
        v = path[i+1]
        
        if nodes[u][0] == nodes[v][0]:
            # Transfer
            dep_time_minutes = parse_time(nodes[v][2])
            wait_time = dep_time_minutes - last_arrival_time
            transfer_infos.append({
                'station': nodes[u][0],
                'arrival_time': to_time(last_arrival_time),
                'departure_time': nodes[v][2],
                'wait_minutes': wait_time
            })
        else:
            # Physical travel
            t_time = get_travel_time(u, v, adj)
            # For physical travel, we depart at nodes[u][2]
            # But if we just transferred, nodes[u] is the new train node, so its time is departure time.
            # If we didn't transfer, nodes[u] is the arrival node from previous step? 
            # No, nodes in graph represent "Departure events" mostly, or "Stop events".
            # The time in node is the schedule time.
            
            dep_time = parse_time(nodes[u][2])
            last_arrival_time = dep_time + t_time
            
    return transfer_infos, last_arrival_time

def find_all_paths(nodes, adj, start_station, end_station, train_info, fast_stations):
    """Find all possible paths from start_station to end_station using DFS, including transfers."""
    paths = []
    
    # Build station index for transfers
    station_index = build_station_index(nodes)
    
    # Find all starting nodes at start_station
    start_nodes = [i for i, node in enumerate(nodes) if node[0] == start_station]
    
    def dfs(current_node, current_arrival, path, visited_nodes, current_trains, current_transfers, start_time, transfer_count):
        current_station = nodes[current_node][0]
        
        if current_station == end_station:
            # Found a path to end_station
            train_sequence = list(dict.fromkeys(current_trains))  # unique trains in order
            
            # Analyze path for precise details
            transfer_details, final_arrival_minutes = analyze_path(path, nodes, adj, start_time)
            
            total_minutes = final_arrival_minutes - start_time
            total_time_str = f"{total_minutes // 60}h {total_minutes % 60}m"
            
            is_fast = any(train_info.get(train, False) for train in train_sequence)
            
            paths.append({
                'id': len(paths) + 1,
                'type': 'Transfer' if transfer_details else 'Direct',
                'train_sequence': train_sequence,
                'transfer_details': transfer_details,
                'departure_time': to_time(start_time),
                'arrival_time': to_time(final_arrival_minutes),
                'total_time': total_time_str,
                'total_minutes': total_minutes,
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
        
        # Logic for transfers (Virtual Edges)
        if len(path) > 1 and current_station in fast_stations and transfer_count < 2:
            candidates = station_index.get(current_station, [])
            current_train_id = nodes[current_node][1]
            
            min_time = current_arrival + 15
            max_time = current_arrival + 90
            
            for cand_time, cand_idx, cand_train in candidates:
                # Since candidates are sorted by time, we can optimize
                if cand_time < min_time:
                    continue
                if cand_time > max_time:
                    break
                
                # Cannot transfer to the same train
                if cand_train == current_train_id:
                    continue
                
                # Execute transfer
                # Note: We treat this as a new step in the path
                new_transfers_transfer = current_transfers + [current_station]
                new_trains_transfer = current_trains + [cand_train]
                
                # Avoid cycles
                if cand_idx in visited_nodes:
                    continue

                dfs(cand_idx, cand_time, path + [cand_idx], visited_nodes | {cand_idx}, 
                    new_trains_transfer, new_transfers_transfer, start_time, transfer_count + 1)
    
    for start_node in start_nodes:
        start_time = parse_time(nodes[start_node][2])
        dfs(start_node, start_time, [start_node], {start_node}, [nodes[start_node][1]], [], start_time, 0)
    
    return paths

def main():
    parser = argparse.ArgumentParser(description='Find direct train paths using DFS.')
    parser.add_argument('--start', required=True, help='Start station ID')
    parser.add_argument('--end', required=True, help='End station ID')
    parser.add_argument('--schedule', default='schedule_list.json', help='Path to schedule JSON file')
    parser.add_argument('--fast_stations', default='fast_station_list.json', help='Path to fast station list JSON file')
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
    fast_stations = load_fast_stations(args.fast_stations)
    
    paths = find_all_paths(nodes, adj, args.start, args.end, train_info, fast_stations)
    
    # Generate output filename based on start and end stations
    output_filename = f"path_{args.start}_{args.end}.json"
    output_path = Path("Result_Finding") / output_filename
    
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(paths, f, ensure_ascii=False, indent=2)
    
    # Statistics for direct paths
    direct_paths = [p for p in paths if p['type'] == 'Direct']
    total_direct = len(direct_paths)
    fast_direct = len([p for p in direct_paths if p['is_fast']])
    slow_direct = total_direct - fast_direct
    
    print(f"Found {len(paths)} total paths. Results saved to {output_path}")
    print(f"Direct paths: Total {total_direct}, Fast {fast_direct}, Slow {slow_direct}")

if __name__ == '__main__':
    main()