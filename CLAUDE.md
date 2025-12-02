# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

MetroPlan is a comprehensive metro transportation planning system designed for analyzing intercity rail routes in the Guangdong region of China. The system processes train schedules, generates transportation networks, and calculates optimal paths between stations with support for transfers.

**Current Version**: 1.3 (Flask-based API)

### Key Features
- **Schedule Processing**: Aggregates Markdown timetables into structured JSON data
- **Network Graph Generation**: Creates transportation networks from schedule data
- **Path Finding**: Implements DFS-based pathfinding with transfer constraints
- **Direction Analysis**: Adds directionality vectors to train services
- **Web API**: Flask-based REST API for querying stations and paths
- **Data Validation**: Comprehensive checking and debugging tools

## Architecture

### Core Components

#### 1. Data Processing Pipeline
- **Input**: Markdown timetables in `backend/车次信息/` directory
- **Processing**: `backend/data_processing/md_to_json.py`
- **Output**: `schedule_list.json` (aggregated train schedules)

#### 2. Graph Generation
- **Input**: `schedule_list.json`
- **Processing**: `backend/graph/generate_graph.py`
- **Output**: `timetable_graph.json` (network graph with nodes and edges)

#### 3. Enhanced Graph with Directionality
- **Input**: `schedule_list.json` + `line_list.json`
- **Processing**: `backend/data_processing/add_directionality.py`
- **Output**: `schedule_with_directionality.json`

#### 4. Fast Graph Generation
- **Input**: Enhanced schedule data
- **Processing**: `backend/graph/generate_fast_graph.py`
- **Output**: `fast_graph.json` (includes transfer edges)

#### 5. Path Finding Engine
- **Input**: `fast_graph.json` + schedule data
- **Processing**: `backend/DFS_PathFinding/find_paths_dfs.py`
- **Output**: Route options in `Result_Finding/` directory

## Project Structure

```
MetroPlan/
├── backend/                          # Core backend processing
│   ├── 车次信息/                     # Markdown timetable files
│   ├── check/                        # Data validation scripts
│   ├── data_processing/              # Data transformation tools
│   ├── DFS_PathFinding/              # Pathfinding algorithms
│   ├── graph/                        # Graph generation utilities
│   ├── visualizations/               # Chart and visualization tools
│   ├── *.json                        # Data files (schedules, graphs, etc.)
│   └── test/                         # Test files (currently deleted)
├── frontend/                         # Frontend application (empty)
├── docs/                            # Documentation directory
├── .spec/                           # Architecture specifications
├── .chat/                           # AI conversation archives
├── .gitignore                       # Git ignore rules
└── CLAUDE.md                        # This file
```

## Data Files

### Core Data Files
- **`schedule_list.json`**: Aggregated train schedules (373KB, 242 trains)
- **`schedule_with_directionality.json`**: Schedules with direction vectors
- **`line_list.json`**: Line definitions and station mappings (19KB, multiple lines)
- **`fast_graph.json`**: Transportation network with transfer edges
- **`timetable_graph.json`**: Basic timetable graph

### Supporting Data Files
- **`fast_station_list.json`**: Fast station information
- **`service_list.json`**: Service definitions
- **`service_metrics.json`**: Service performance metrics
- **`transfer_list.json`**: Transfer station information
- **`train_comparison.json`**: Train comparison data

## Setup and Installation

### Prerequisites
- Python 3.8+
- pip package manager
- (Optional) Node.js for frontend development

### Backend Setup
1. **Navigate to backend directory**:
   ```bash
   cd backend
   ```

2. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

3. **Create virtual environment (recommended)**:
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

### Data Preparation
1. **Generate schedule data from Markdown**:
   ```bash
   python data_processing/md_to_json.py --dir "车次信息" --output schedule_list.json
   ```

2. **Add directionality information**:
   ```bash
   python data_processing/add_directionality.py --line line_list.json --schedule schedule_list.json --output schedule_with_directionality.json
   ```

3. **Generate transportation graphs**:
   ```bash
   python graph/generate_graph.py --schedule schedule_list.json --output timetable_graph.json
   python graph/generate_fast_graph.py --schedule schedule_with_directionality.json --output fast_graph.json
   ```

## Development Workflow

### Step-by-step Data Processing
1. **Process Markdown timetables**:
   ```bash
   python data_processing/md_to_json.py
   ```

2. **Add directionality vectors**:
   ```bash
   python data_processing/add_directionality.py
   ```

3. **Generate network graphs**:
   ```bash
   python graph/generate_fast_graph.py
   ```

4. **Test pathfinding**:
   ```bash
   python DFS_PathFinding/find_paths_dfs.py --start 琶洲 --end 西平西 --max_transfers 2
   ```

### Common Development Commands

#### Data Processing
```bash
# Aggregate markdown schedules
python data_processing/md_to_json.py --dir "车次信息" --output schedule_list.json

# Add directionality analysis
python data_processing/add_directionality.py --line line_list.json --schedule schedule_list.json

# Generate transportation network
python graph/generate_fast_graph.py --schedule schedule_with_directionality.json
```

#### Pathfinding Analysis
```bash
# Find paths between stations (max 2 transfers)
python DFS_PathFinding/find_paths_dfs.py --start 琶洲 --end 西平西 --max_transfers 2

# Find paths with time window constraint
python DFS_PathFinding/find_paths_dfs.py --start 花都 --end 肇庆 --max_transfers 2 --window_minutes 120
```

#### Data Validation
```bash
# Check network connectivity
python check/check_connectivity.py graph/fast_graph.json

# Validate data integrity
python check/check_duplicates.py
python check/check_md_cols.py
python check/check_s4802.py
```

## Core Algorithms

### Pathfinding Algorithm
- **Algorithm**: Depth-First Search (DFS) with transfer constraints
- **Features**:
  - Supports 0-2 transfers
  - Time window filtering
  - Directionality consistency checking
  - Path merging for identical train sequences
  - Fast/slow train differentiation

### Directionality Analysis
- **Method**: Vector-based direction tracking per line
- **Output**: Each train gets a direction vector (0=not used, 1=forward, -1=reverse)
- **Strategies**: Majority vote, first segment, or ambiguous marking

### Graph Representation
- **Nodes**: (station_name, train_id, departure_time)
- **Edges**: Travel edges between consecutive stations + transfer edges
- **Weights**: Travel time in minutes

## Testing and Quality Assurance

### Validation Scripts
- **Connectivity Check**: Validates network connectivity between stations
- **Duplicate Detection**: Identifies duplicate trains or stations
- **Data Integrity**: Validates markdown column structure
- **S4802 Compliance**: Specific data format validation

## Configuration

### Key Configuration Files
- **`.gitignore`**: Ignores JSON files, Markdown files, Python caches
- **`line_list.json`**: Line definitions with station order and metadata
- **Schedule processing**: Configurable stop time (default: 3 minutes)

### Environment Variables
- **Python path**: Backend modules in `backend/` directory
- **Data directory**: JSON files located in `backend/` directory
- **Output directory**: Results written to `Result_Finding/`

## Troubleshooting

### Common Issues
1. **Missing JSON files**: Run data processing scripts first
2. **Import errors**: Ensure working directory is project root
3. **Path finding no results**: Check station names and network connectivity
4. **Directionality errors**: Verify line definitions and station names

### Debug Commands
```bash
# Check network connectivity
python check/check_connectivity.py

# Validate schedule data
python data_processing/md_to_json.py --dry-run

# Test directionality processing
python data_processing/add_directionality.py --dry-run
```