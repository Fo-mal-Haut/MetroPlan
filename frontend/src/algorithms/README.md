find_paths_dfs.ts
=================

This module is a TypeScript port of the backend DFS pathfinding algorithm. It provides:

- buildAdjacency(nodes, edges)
- loadSchedule(schedule)
- loadDirectionalityMap(schedule)
- findAllPaths(nodes, adjacency, start, end, trainInfo, directionMap, maxTransfers?, allowSameStationConsecutiveTransfers?)
- mergePathsByTrainSequence(paths)

Usage from a Vue component or plain front-end JS:

1) Use the demo script for a quick run: `src/algorithms/run_find_paths_demo.ts` (it fetches `/static/data/*`)

2) Or import the module and call functions with in-memory data:

  import { buildAdjacency, loadSchedule, loadDirectionalityMap, findAllPaths, mergePathsByTrainSequence } from '@/algorithms';

  const nodes = graph.nodes;
  const adjacency = buildAdjacency(nodes, graph.edges);
  const trainInfo = loadSchedule(scheduleJson);
  const directionMap = loadDirectionalityMap(scheduleJson);
  const { paths, stats } = findAllPaths(nodes, adjacency, '佛山西', '肇庆', trainInfo, directionMap, 2, false);

3. The module returns data structures similar to the backend. You can merge and sort results using mergePathsByTrainSequence.

Notes
-----
- The demo uses `fetch('/static/data/...')` at runtime. Ensure the development server serves `src/static/data` at `/static/data/`.
- If your setup allows importing JSON modules, you can import JSON directly.
