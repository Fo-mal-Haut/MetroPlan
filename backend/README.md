# Railway Path Finding API

Flask REST API for finding intercity railway paths with transfer optimization.

## Setup

```bash
# Install dependencies
pip install -r requirements.txt

# Run the server
python app.py
```

Server will start on `http://localhost:5000`

## API Endpoints

### GET /health
Health check endpoint.

**Response:**
```json
{
  "status": "healthy",
  "data_loaded": true
}
```

### GET /stations
List all available stations.

**Response:**
```json
{
  "stations": ["琶洲", "西平西", "东莞西", ...],
  "count": 128
}
```

### POST /path
Find paths between two stations.

**Request:**
```json
{
  "start": "琶洲",
  "end": "西平西",
  "max_transfers": 2,
  "window_minutes": 120,
  "allow_same_station_consecutive_transfers": false
}
```

**Parameters:**
- `start` (required): Starting station name
- `end` (required): Ending station name
- `max_transfers` (optional, default: 2): Maximum number of transfers allowed
- `window_minutes` (optional, default: 120): Time window in minutes from fastest path
- `allow_same_station_consecutive_transfers` (optional, default: false): Allow two consecutive transfers at the same station

**Response:**
```json
{
  "start_station": "琶洲",
  "end_station": "西平西",
  "paths": [
    {
      "id": 1,
      "type": "Direct",
      "train_sequence": ["S4847"],
      "departure_time": "21:33",
      "arrival_time": "22:06",
      "total_time": "0h 33m",
      "total_minutes": 33,
      "transfer_count": 0,
      "is_fast": true,
      "transfer_details": [],
      "transfer_options": []
    },
    {
      "id": 2,
      "type": "Transfer",
      "train_sequence": ["S4805", "S4757"],
      "departure_time": "21:00",
      "arrival_time": "22:24",
      "total_time": "1h 24m",
      "total_minutes": 84,
      "transfer_count": 1,
      "is_fast": true,
      "transfer_details": [
        {
          "from_train": "S4805",
          "to_train": "S4757",
          "transfer_station": "某站",
          "arrival_time": "21:45",
          "departure_time": "22:00",
          "wait_time_minutes": 15
        }
      ],
      "transfer_options": [
        {
          "from_train": "S4805",
          "to_train": "S4759",
          "transfer_station": "某站",
          "arrival_time": "21:45",
          "departure_time": "22:05",
          "wait_time_minutes": 20
        }
      ]
    }
  ],
  "summary": {
    "raw_path_count": 923,
    "fastest_minutes": 33,
    "window_minutes": 120,
    "filtered_path_count": 54,
    "merged_path_count": 34,
    "skipped_same_station_transfers": 5
  }
}
```

**Response Fields:**
- `paths`: Array of path objects, sorted by total time
- `id`: Unique identifier for the path
- `type`: "Direct" (no transfers) or "Transfer" (one or more transfers)
- `train_sequence`: Array of train IDs for this path
- `departure_time`: Time of first train departure
- `arrival_time`: Time of last train arrival
- `total_time`: Human-readable duration (e.g., "1h 24m")
- `total_minutes`: Total duration in minutes
- `transfer_count`: Number of transfers (0, 1, or 2)
- `is_fast`: Whether all trains in sequence are fast trains
- `transfer_details`: Details of each transfer point
- `transfer_options`: Alternative trains available at the same transfer point
- `summary`: Statistics about the path finding operation

## Error Responses

### 400 Bad Request
```json
{
  "error": "Missing \"start\" or \"end\" station"
}
```

### 404 Not Found
```json
{
  "error": "Start station \"InvalidStation\" not found"
}
```

### 500 Internal Server Error
```json
{
  "error": "Data not loaded"
}
```

## Example Usage

### Python
```python
import requests

response = requests.post('http://localhost:5000/path', json={
    'start': '琶洲',
    'end': '西平西',
    'max_transfers': 2,
    'window_minutes': 120
})

result = response.json()
print(f"Found {len(result['paths'])} paths")
for path in result['paths'][:5]:
    print(f"  {path['departure_time']} - {path['arrival_time']} ({path['total_time']})")
```

### JavaScript/Fetch
```javascript
const response = await fetch('http://localhost:5000/path', {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({
    start: '琶洲',
    end: '西平西',
    max_transfers: 2,
    window_minutes: 120
  })
});

const result = await response.json();
console.log(`Found ${result.paths.length} paths`);
result.paths.slice(0, 5).forEach(path => {
  console.log(`  ${path.departure_time} - ${path.arrival_time} (${path.total_time})`);
});
```

### cURL
```bash
curl -X POST http://localhost:5000/path \
  -H "Content-Type: application/json" \
  -d '{
    "start": "琶洲",
    "end": "西平西",
    "max_transfers": 2,
    "window_minutes": 120
  }'
```

## Configuration

Edit `app.py` to modify:
- `DATA_DIR`: Path to data directory (default: parent of backend folder)
- `GRAPH_FILE`: Path to fast_graph.json (default: `graph/fast_graph.json`)
- `SCHEDULE_FILE`: Path to schedule JSON (default: `schedule_with_directionality.json`)

## Data Requirements

The following files must exist relative to the backend folder:
- `../graph/fast_graph.json`: Graph with nodes and edges
- `../schedule_with_directionality.json`: Train schedule with directionality vectors

## Development

### Enable Debug Mode
```python
app.run(host='0.0.0.0', port=5000, debug=True)
```

### Test Endpoints
```bash
# Health check
curl http://localhost:5000/health

# List stations
curl http://localhost:5000/stations

# Find path
curl -X POST http://localhost:5000/path \
  -H "Content-Type: application/json" \
  -d '{"start": "琶洲", "end": "西平西"}'
```

## Performance Notes

- Data is loaded once at startup and cached in memory
- Path finding may take several seconds for distant stations with many transfers
- Consider adding a timeout for long-running queries in production
- CORS is enabled by default for all origins (modify `CORS(app)` if needed)

## Frontend Integration

The API is CORS-enabled and returns JSON, making it easy to integrate with:
- Vue.js
- React
- Angular
- Plain JavaScript fetch API

See example usage above.
