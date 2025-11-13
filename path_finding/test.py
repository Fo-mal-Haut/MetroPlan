from pathlib import Path
from find_paths import find_paths

paths = find_paths(
	start_station="佛山西",
	end_station="肇庆",
	dep_time_str="06:00",
	graph_path=Path("../graph/timetable_graph.json"),
	max_paths=5,
	max_transfers=2,
	min_transfer_min=3,
)

print("paths count:", len(paths))
for p in paths:
	print(p["total_dep_time"], p["total_arr_time"], p["total_time_minutes"], p["transfers"]) 
