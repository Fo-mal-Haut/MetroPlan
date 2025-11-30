#!/usr/bin/env python3
"""Flask API for intercity railway path finding.

Exposes endpoints:
  - GET /stations: List all available stations
  - POST /path: Find paths between two stations with optional parameters
  - GET /health: Health check
"""

import sys
import json
from pathlib import Path
from typing import List, Dict, Any, Tuple

from flask import Flask, request, jsonify
from flask_cors import CORS

# Add parent directory to path to import find_paths_dfs
sys.path.insert(0, str(Path(__file__).parent.parent / "DFS_PathFinding"))
from find_paths_dfs import (
    load_graph,
    load_schedule,
    load_directionality_map,
    build_adjacency,
    find_all_paths,
    merge_paths_by_train_sequence,
)

app = Flask(__name__)
CORS(app)

# Load data on startup
DATA_DIR = Path(__file__).parent.parent
GRAPH_FILE = DATA_DIR / "graph" / "fast_graph.json"
SCHEDULE_FILE = DATA_DIR / "schedule_with_directionality.json"

# Global variables to cache loaded data
_graph_nodes = None
_graph_edges = None
_adjacency = None
_train_info = None
_direction_map = None
_all_stations = None


def load_data():
    """Load graph and schedule data into memory."""
    global _graph_nodes, _graph_edges, _adjacency, _train_info, _direction_map, _all_stations
    
    try:
        print(f"Loading graph from {GRAPH_FILE}")
        _graph_nodes, _graph_edges = load_graph(GRAPH_FILE)
        _adjacency = build_adjacency(_graph_nodes, _graph_edges)
        
        print(f"Loading schedule from {SCHEDULE_FILE}")
        _train_info = load_schedule(SCHEDULE_FILE)
        
        try:
            _direction_map = load_directionality_map(SCHEDULE_FILE)
            print(f"Loaded directionality for {len(_direction_map)} trains")
        except Exception as e:
            print(f"Warning: Failed to load directionality map: {e}")
            _direction_map = {}
        
        # Extract all unique stations from graph nodes
        stations_set = set()
        for node in _graph_nodes:
            station_name = node[0]
            if station_name:
                stations_set.add(station_name)
        _all_stations = sorted(list(stations_set))
        
        print(f"Loaded {len(_graph_nodes)} nodes, {len(_graph_edges)} edges")
        print(f"Loaded {len(_train_info)} trains")
        print(f"Found {len(_all_stations)} unique stations")
        return True
    except Exception as e:
        print(f"Error loading data: {e}")
        return False


@app.route('/health', methods=['GET'])
def health():
    """Health check endpoint."""
    return jsonify({
        'status': 'healthy',
        'data_loaded': all([_graph_nodes, _adjacency, _train_info, _all_stations])
    }), 200


@app.route('/stations', methods=['GET'])
def stations():
    """Get list of all available stations."""
    if not _all_stations:
        return jsonify({'error': 'Stations data not loaded'}), 500
    
    return jsonify({
        'stations': _all_stations,
        'count': len(_all_stations)
    }), 200


@app.route('/path', methods=['POST'])
def find_path():
    """Find paths between two stations.
    
    Request JSON:
    {
        "start": "琶洲",
        "end": "西平西",
        "max_transfers": 2,
        "window_minutes": 120,
        "allow_same_station_consecutive_transfers": false
    }
    
    Response:
    {
        "start_station": "琶洲",
        "end_station": "西平西",
        "paths": [
            {
                "type": "Direct" | "Transfer",
                "train_sequence": ["S4847"],
                "transfer_details": [...],
                "transfer_options": [...],
                "departure_time": "21:33",
                "arrival_time": "22:06",
                "total_time": "0h 33m",
                "total_minutes": 33,
                "is_fast": true,
                "transfer_count": 0,
                "id": 1
            }
        ],
        "summary": {
            "raw_path_count": 923,
            "fastest_minutes": 33,
            "filtered_path_count": 54,
            "merged_path_count": 34
        }
    }
    """
    if not all([_graph_nodes, _adjacency, _train_info, _all_stations]):
        return jsonify({'error': 'Data not loaded'}), 500
    
    data = request.get_json()
    if not data:
        return jsonify({'error': 'Request body must be JSON'}), 400
    
    start = data.get('start')
    end = data.get('end')
    
    if not start or not end:
        return jsonify({'error': 'Missing "start" or "end" station'}), 400
    
    if start not in _all_stations:
        return jsonify({'error': f'Start station "{start}" not found'}), 400
    if end not in _all_stations:
        return jsonify({'error': f'End station "{end}" not found'}), 400
    
    # Get optional parameters
    max_transfers = data.get('max_transfers', 2)
    window_minutes = data.get('window_minutes', 120)
    allow_same_station = data.get('allow_same_station_consecutive_transfers', False)
    
    try:
        # Run path finding
        all_paths, stats = find_all_paths(
            _graph_nodes,
            _adjacency,
            start,
            end,
            _train_info,
            direction_map=_direction_map if _direction_map else None,
            max_transfers=max_transfers,
            allow_same_station_consecutive_transfers=allow_same_station
        )
        
        if not all_paths:
            return jsonify({
                'start_station': start,
                'end_station': end,
                'paths': [],
                'summary': {
                    'raw_path_count': 0,
                    'fastest_minutes': None,
                    'filtered_path_count': 0,
                    'merged_path_count': 0
                },
                'message': 'No feasible paths found'
            }), 200
        
        # Filter by window
        fastest_minutes = min(p['total_minutes'] for p in all_paths)
        cutoff_minutes = fastest_minutes + window_minutes
        filtered_paths = [p for p in all_paths if p['total_minutes'] <= cutoff_minutes]
        
        # Sort and merge
        filtered_paths.sort(key=lambda item: (item['total_minutes'], item['departure_time']))
        paths = merge_paths_by_train_sequence(filtered_paths)
        
        # Assign IDs
        for idx, entry in enumerate(paths, start=1):
            entry['id'] = idx
        
        return jsonify({
            'start_station': start,
            'end_station': end,
            'paths': paths,
            'summary': {
                'raw_path_count': len(all_paths),
                'fastest_minutes': fastest_minutes,
                'window_minutes': window_minutes,
                'filtered_path_count': len(filtered_paths),
                'merged_path_count': len(paths),
                'skipped_same_station_transfers': stats.get('skipped_same_station_transfers', 0)
            }
        }), 200
    
    except Exception as e:
        return jsonify({'error': f'Path finding failed: {str(e)}'}), 500


if __name__ == '__main__':
    if not load_data():
        print("Failed to load data. Exiting.")
        sys.exit(1)
    
    print("Starting Flask server on http://127.0.0.1:5000")
    app.run(host='127.0.0.1', port=5000, debug=False)
