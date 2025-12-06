import dfspath from './find_paths_dfs';

let _cachedGraph: any = null;
let _cachedSchedule: any = null;

async function loadGraphAndSchedule() {
  if (_cachedGraph && _cachedSchedule) return { graph: _cachedGraph, schedule: _cachedSchedule };
  const graphUrl = '/static/data/fast_graph.json';
  const scheduleUrl = '/static/data/schedule_with_directionality.json';
  const [graphResp, scheduleResp] = await Promise.all([fetch(graphUrl), fetch(scheduleUrl)]);
  const graph = await graphResp.json();
  const schedule = await scheduleResp.json();
  _cachedGraph = graph;
  _cachedSchedule = schedule;
  return { graph, schedule };
}

export async function computePaths(start: string, end: string, maxTransfers: number = 2, windowMinutes: number = 90, allowSameStationConsecutiveTransfers: boolean = false) {
  const { graph, schedule } = await loadGraphAndSchedule();
  const nodes = graph.nodes as any;
  const edges = graph.edges as any;
  const adjacency = dfspath.buildAdjacency(nodes, edges);
  const trainInfo = dfspath.loadSchedule(schedule);
  const directionMap = dfspath.loadDirectionalityMap(schedule);

  const { paths, stats } = dfspath.findAllPaths(nodes, adjacency, start, end, trainInfo, directionMap, maxTransfers, allowSameStationConsecutiveTransfers);
  if (!paths || paths.length === 0) return { paths: [], stats };

  const fastestMinutes = Math.min(...paths.map((p: any) => p.total_minutes));
  const cutoff = fastestMinutes + (windowMinutes >= 0 ? windowMinutes : 0);
  const filtered = paths.filter((p: any) => p.total_minutes <= cutoff);
  const merged = dfspath.mergePathsByTrainSequence(filtered);
  merged.forEach((m: any, idx:number) => m.id = idx + 1);

  const summary = {
    raw_path_count: paths.length,
    window_minutes: windowMinutes,
    fastest_minutes: fastestMinutes,
    filtered_path_count: filtered.length,
    merged_path_count: merged.length,
    stats
  };

  return { paths: merged, raw_paths: paths, summary };
}

export async function listStations() {
  const { graph } = await loadGraphAndSchedule();
  const nodes = graph.nodes as any[];
  const set = new Set<string>();
  for (const n of nodes) {
    set.add(n[0]);
  }
  const arr = Array.from(set).sort();
  return arr;
}

async function demo() {
  const { graph, schedule } = await loadGraphAndSchedule();
  const nodes = graph.nodes as any;
  const edges = graph.edges as any;
  const adjacency = dfspath.buildAdjacency(nodes, edges);
  const trainInfo = dfspath.loadSchedule(schedule);
  const directionMap = dfspath.loadDirectionalityMap(schedule);

  const { paths, stats } = dfspath.findAllPaths(nodes, adjacency, '佛山西', '肇庆', trainInfo, directionMap, 2, false);
  if (!paths || paths.length === 0) {
    console.log('No paths');
    return;
  }
  const fastestMinutes = Math.min(...paths.map((p: any) => p.total_minutes));
  const windowMinutes = 90;
  const cutoff = fastestMinutes + windowMinutes;
  const filtered = paths.filter((p: any) => p.total_minutes <= cutoff);
  const merged = dfspath.mergePathsByTrainSequence(filtered);
  console.log(`Found ${paths.length} raw paths; fastest ${fastestMinutes} min; filtered ${filtered.length}; merged ${merged.length}`);
  console.log('sample paths (first 5):', merged.slice(0, 5));
  console.log('skipped consecutive transfers:', stats.skipped_same_station_transfers);
}

export {};
