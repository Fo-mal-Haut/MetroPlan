# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

MetroPlan is a railway path finding system that provides optimal travel routes between stations in the Guangzhou metropolitan area. The system uses a graph-based approach with depth-first search (DFS) to find paths with up to 2 transfers, considering both travel time and train directionality constraints.

**Core Functionality:**
- Find optimal routes between stations with transfer constraints
- Support for both direct and transfer paths with timing details
- REST API for frontend integration
- Direction-aware path optimization using train direction vectors

## Architecture

### Core Components

1. **Graph System (`graph/`)**
   - `fast_graph.json`: Main graph with 4,018 nodes and 16,031 edges containing both train routes and transfer connections
   - `timetable_graph.json`: Alternative graph representation
   - `generate_fast_graph.py`: Graph generation utilities

2. **Path Finding Engine (`DFS_PathFinding/`)**
   - `find_paths_dfs.py`: Core DFS algorithm with directionality support and transfer optimization
   - Supports configurable transfer limits and time windows
   - Handles both same-station and cross-station transfers

3. **REST API (`backend/`)**
   - Flask application serving path finding as JSON API
   - CORS-enabled for frontend integration
   - Data caching in memory for performance

4. **Data Processing (`data_processing/`)**
   - Schedule and directionality processing utilities
   - Train service analysis and comparison tools

### Data Flow

```
Schedule JSON + Train Data → Graph Generation → Path Finding (DFS) → REST API Response
```

## Development Commands

### Backend API Development
```bash
# Setup and run Flask API
cd backend
pip install -r requirements.txt
python app.py

# Quick API testing
python ../test_quick.py

# Full test suite (comprehensive)
python backend/test_api.py
```

### Path Finding Algorithm Testing
```bash
# Direct path finding using DFS algorithm
python DFS_PathFinding/find_paths_dfs.py --start "琶洲" --end "西平西" \
  --graph graph/fast_graph.json --schedule schedule_with_directionality.json \
  --max_transfers 2 --window_minutes 120
```

### Data Validation
```bash
# Check connectivity between stations
python check_connectivity.py

# Validate schedule data consistency
python check/check_s4802.py
```

### Visualization
```bash
# Generate service visualizations
cd data_processing
python visualize_services.py
cd ../visualizations
python plot_transfer_histogram.py
```

## Key Data Files

**Required Data Files:**
- `graph/fast_graph.json`: Main graph with nodes and edges
- `schedule_with_directionality.json`: Train schedules with direction vectors
- `schedule_list.json`: Basic schedule information
- `line_list.json`: Railway line definitions

**Generated Results:**
- `Result_Finding/path_*.json`: Path finding results with detailed route information

## API Configuration

The Flask API uses these configurable paths (modify `backend/app.py`):
- `DATA_DIR`: Data directory location (defaults to project root)
- `GRAPH_FILE`: Path to fast_graph.json
- `SCHEDULE_FILE`: Path to schedule_with_directionality.json

## Algorithm Details

### Graph Structure
- **Nodes**: `[station_name, train_id, time]` tuples representing train arrivals/departures
- **Edges**: Two types of connections:
  - Train edges: Direct connections along train routes
  - Transfer edges: Walking connections between platforms at the same station

### Path Finding Strategy
- Uses depth-first search with backtracking
- Supports up to 2 transfers by default (configurable)
- Applies time window filtering (default: 120 minutes from fastest path)
- Considers train directionality to avoid invalid routing
- Merges duplicate train sequences with multiple transfer options

### Directionality Constraints
- Trains may have direction vectors indicating valid travel directions
- Prevents routing that would require a train to reverse direction
- Applied to transfer paths to ensure logical connectivity

## Performance Considerations

- Graph data (4,018 nodes) is loaded once and cached in memory
- API initialization may take 5-10 seconds due to data loading
- Path finding can take several seconds for distant stations with multiple transfer options
- Consider adding request timeouts for production deployment

## Data Processing Workflow

1. **Schedule Processing**: Convert raw schedule data to JSON format with directionality
2. **Graph Generation**: Create fast_graph.json with both train and transfer edges
3. **Path Finding**: Apply DFS algorithm with configurable constraints
4. **Result Processing**: Merge duplicate paths and format for API consumption

## Testing Strategy

- **Unit Testing**: Individual component testing via scripts in `check/` directory
- **Integration Testing**: Full API testing via `backend/test_api.py`
- **Algorithm Validation**: Path finding verification with known test cases
- **Data Integrity**: Connectivity checks and schedule validation

## Common Issues and Solutions

1. **Server Startup Timeout**: Allow 5+ seconds for data loading when starting Flask API
2. **Import Path Issues**: Use absolute paths relative to project root for cross-directory imports
3. **Cross-Platform Compatibility**: Avoid Unix-specific commands; use Python standard library for network requests
4. **Memory Usage**: Large graph data requires sufficient RAM; consider streaming for very large datasets