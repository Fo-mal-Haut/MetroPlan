import json
import sys

def check_connectivity(graph_file, start_station, end_station):
    with open(graph_file, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    nodes = data['nodes']
    # nodes structure: [station_name, train_id, time]
    
    start_nodes = []
    end_nodes = []
    
    for i, node in enumerate(nodes):
        if node[0] == start_station:
            start_nodes.append(node)
        elif node[0] == end_station:
            end_nodes.append(node)
            
    print(f"Found {len(start_nodes)} nodes for {start_station}")
    print(f"Found {len(end_nodes)} nodes for {end_station}")
    
    # Check for direct trains
    start_trains = {node[1] for node in start_nodes}
    end_trains = {node[1] for node in end_nodes}
    
    common_trains = start_trains.intersection(end_trains)
    print(f"Common trains: {len(common_trains)}")
    
    edges = data['edges']

    # Check neighbors of end_station (incoming)
    print(f"\nTrains at {end_station}:")
    end_train_ids = end_trains
    print(f"Train IDs: {list(end_train_ids)[:10]}...")
    
    # Check where these trains stop
    end_train_routes = {}
    for edge in edges:
        t_id = edge['from'][1]
        if t_id in end_train_ids:
            if t_id not in end_train_routes:
                end_train_routes[t_id] = set()
            end_train_routes[t_id].add(edge['from'][0])
            end_train_routes[t_id].add(edge['to'][0])
            
    # Build pazhou_train_stops
    pazhou_train_stops = {}
    for edge in edges:
        t_id = edge['from'][1]
        if t_id in start_trains:
            if t_id not in pazhou_train_stops:
                pazhou_train_stops[t_id] = set()
            pazhou_train_stops[t_id].add(edge['from'][0])
            pazhou_train_stops[t_id].add(edge['to'][0])

    # Find reachable stations from Pazhou
    pazhou_reachable = set()
    for stops in pazhou_train_stops.values():
        pazhou_reachable.update(stops)
        
    print(f"\nReachable from Pazhou (1 hop): {len(pazhou_reachable)} stations")
    print(list(pazhou_reachable))
    
    # Find stations that can reach Xipingxi
    xipingxi_sources = set()
    for edge in edges:
        t_id = edge['from'][1]
        if t_id in end_train_ids:
            xipingxi_sources.add(edge['from'][0])
            xipingxi_sources.add(edge['to'][0])
            
    print(f"Can reach Xipingxi (1 hop): {len(xipingxi_sources)} stations")
    
    # Check incoming trains to Pazhou
    print("\nIncoming trains to Pazhou:")
    incoming_pazhou = set()
    for edge in edges:
        if edge['to'][0] == '琶洲':
            incoming_pazhou.add(edge['from'][0])
            
    print(f"Stations that have trains going TO Pazhou: {incoming_pazhou}")


if __name__ == "__main__":
    check_connectivity('graph/timetable_graph.json', '花都', '西平西')
