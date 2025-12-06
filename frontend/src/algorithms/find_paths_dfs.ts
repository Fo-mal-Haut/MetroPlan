// TypeScript port of backend/DFS_PathFinding/find_paths_dfs.py
// Provides pure front-end functions to find intercity paths from a fast_graph + schedule.

export type NodeEntry = [string, string, string];

export interface EdgeEntry {
  from: NodeEntry;
  to: NodeEntry;
  weight?: number;
  segment_travel_time?: number;
  type?: string;
}

export type Graph = { nodes: NodeEntry[]; edges: EdgeEntry[] };

export interface TrainInfoEntry {
  is_fast?: boolean;
  directionality?: number[] | null;
}

export type TrainInfoMap = Record<string, TrainInfoEntry>;
export type DirectionMap = Record<string, number[]>;

export interface PathSummary {
  id?: number;
  type: 'Direct' | 'Transfer';
  train_sequence: string[];
  transfer_details: Array<{ station: string; arrival_time: string; departure_time: string; wait_minutes: number }>;
  departure_time: string;
  arrival_time: string;
  total_time: string;
  total_minutes: number;
  is_fast: boolean;
  transfer_count: number;
  // optional merged transfer options
  transfer_options?: Array<{ step: number; options: any[] }>;
}

function parseTime(timeStr: string | undefined | null): number {
  if (!timeStr) return 0;
  if (timeStr === '00:00') return 1440;
  const [h, m] = timeStr.split(':').map((x) => parseInt(x, 10));
  return h * 60 + m;
}

function toTime(totalMinutes: number): string {
  totalMinutes = ((totalMinutes % 1440) + 1440) % 1440;
  const hours = Math.floor(totalMinutes / 60);
  const minutes = totalMinutes % 60;
  return `${hours.toString().padStart(2, '0')}:${minutes.toString().padStart(2, '0')}`;
}

export function buildAdjacency(nodes: NodeEntry[], edges: EdgeEntry[]) {
  const nodeKey = (n: NodeEntry) => `${n[0]}|||${n[1]}|||${n[2]}`;
  const nodeLookup = new Map<string, number>();
  nodes.forEach((n, i) => nodeLookup.set(nodeKey(n), i));
  const adjacency = new Map<number, Array<{ to: number; type: string; duration: number }>>();
  for (let i = 0; i < nodes.length; i++) adjacency.set(i, []);

  for (const e of edges) {
    const fromIdx = nodeLookup.get(nodeKey(e.from));
    const toIdx = nodeLookup.get(nodeKey(e.to));
    if (fromIdx === undefined || toIdx === undefined) continue;
    const duration = (e.weight ?? e.segment_travel_time ?? 0) as number;
    if (typeof duration !== 'number' || duration <= 0) continue;
    const type = e.type ?? 'travel';
    adjacency.get(fromIdx)!.push({ to: toIdx, type, duration });
  }
  return adjacency;
}

function summarizePath(
  nodes: NodeEntry[],
  edgeHistory: Array<{ from: number; to: number; type: string; duration: number }> ,
  trainSequence: string[],
  startTime: number,
  endTime: number,
  trainInfo: TrainInfoMap
) {
  let timeline = startTime;
  const transferDetails: Array<{ station: string; arrival_time: string; departure_time: string; wait_minutes: number }> = [];
  for (const edge of edgeHistory) {
    const prev = timeline;
    timeline += edge.duration;
    if (edge.type === 'transfer') {
      const station = nodes[edge.from][0];
      transferDetails.push({ station, arrival_time: toTime(prev), departure_time: toTime(timeline), wait_minutes: edge.duration });
    }
  }
  if (timeline !== endTime) timeline = endTime;
  let totalMinutes = timeline - startTime;
  if (totalMinutes < 0) totalMinutes += 1440;
  const isFast = trainSequence.some((tid) => !!trainInfo[tid]?.is_fast);
  return {
    type: transferDetails.length ? 'Transfer' : 'Direct',
    train_sequence: [...trainSequence],
    transfer_details: transferDetails,
    departure_time: toTime(startTime),
    arrival_time: toTime(timeline),
    total_time: `${Math.floor(totalMinutes / 60)}h ${totalMinutes % 60}m`,
    total_minutes: totalMinutes,
    is_fast: isFast,
    transfer_count: transferDetails.length,
  } as PathSummary;
}

export function loadSchedule(schedule: any): TrainInfoMap {
  const map: TrainInfoMap = {};
  if (!schedule?.train) return map;
  for (const tr of schedule.train) {
    map[tr.id] = { is_fast: !!tr.is_fast, directionality: tr.directionality ?? null };
  }
  return map;
}

export function loadDirectionalityMap(schedule: any): DirectionMap {
  const out: DirectionMap = {};
  if (!schedule?.train) return out;
  for (const tr of schedule.train) {
    if (Array.isArray(tr.directionality)) out[tr.id] = tr.directionality;
  }
  return out;
}

export function mergePathsByTrainSequence(paths: PathSummary[]): PathSummary[] {
  const grouped: Record<string, PathSummary> = {};
  const order: string[] = [];
  for (const entry of paths) {
    const transferCount = entry.transfer_count ?? entry.transfer_details.length;
    const key = JSON.stringify([entry.train_sequence, entry.type, transferCount, entry.departure_time, entry.arrival_time, entry.total_minutes]);
    if (!grouped[key]) {
      const base = JSON.parse(JSON.stringify(entry)) as PathSummary;
      if (transferCount > 0) {
        const optionLists: Array<Array<any>> = [];
        for (let idx = 0; idx < transferCount; idx++) optionLists.push([]);
        for (let idx = 0; idx < (entry.transfer_details || []).length; idx++) optionLists[idx].push(JSON.parse(JSON.stringify(entry.transfer_details[idx])));
        (base as any)['_transfer_option_lists'] = optionLists;
      }
      grouped[key] = base;
      order.push(key);
      continue;
    }
    const base = grouped[key];
    if (transferCount === 0) continue;
    const optionLists = (base as any)['_transfer_option_lists'] as Array<Array<any>>;
    const details = entry.transfer_details || [];
    for (let idx = 0; idx < details.length; idx++) {
      if (!optionLists[idx]) optionLists[idx] = [];
      const detail = details[idx];
      if (!optionLists[idx].some((d) => JSON.stringify(d) === JSON.stringify(detail))) optionLists[idx].push(JSON.parse(JSON.stringify(detail)));
    }
  }
  const merged: PathSummary[] = [];
  for (const key of order) {
    const base = grouped[key];
    const optionLists = (base as any)['_transfer_option_lists'];
    if (optionLists) {
      base.transfer_options = optionLists.map((opts: any[], idx: number) => ({ step: idx + 1, options: opts }));
      base.transfer_details = optionLists.map((opts: any[]) => (opts[0] as any));
      delete (base as any)['_transfer_option_lists'];
    }
    merged.push(base);
  }
  return merged;
}

export function findAllPaths(
  nodes: NodeEntry[],
  adjacency: Map<number, Array<{ to: number; type: string; duration: number }>>,
  startStation: string,
  endStation: string,
  trainInfo: TrainInfoMap,
  directionMap?: DirectionMap,
  maxTransfers: number = 2,
  allowSameStationConsecutiveTransfers: boolean = false
) {
  const paths: PathSummary[] = [];
  const stats = { skipped_same_station_transfers: 0 };
  const startNodes: number[] = [];
  for (let i = 0; i < nodes.length; i++) if (nodes[i][0] === startStation) startNodes.push(i);
  if (!startNodes.length) return { paths: [], stats };

  function dfs(
    currentIdx: number,
    currentTime: number,
    transfersUsed: number,
    path: number[],
    edgeHistory: Array<{ from: number; to: number; type: string; duration: number }>,
    trainSequence: string[],
    startTime: number,
    lastTransferStation: string | null = null
  ) {
    const stationName = nodes[currentIdx][0];
    if (stationName === endStation && edgeHistory.length > 0) {
      const summary = summarizePath(nodes, edgeHistory, trainSequence, startTime, currentTime, trainInfo);
      if (directionMap && (summary.transfer_count ?? 0) > 0) {
        const seq = summary.train_sequence || [];
        let invalid = false;
        for (let i = 0; i < seq.length - 1; i++) {
          const a = directionMap[seq[i]];
          const b = directionMap[seq[i + 1]];
          if (!a || !b) continue;
          for (let j = 0; j < Math.min(a.length, b.length); j++) {
            if (a[j] !== 0 && b[j] !== 0 && a[j] === -b[j]) {
              invalid = true;
              break;
            }
          }
          if (invalid) break;
        }
        if (invalid) return;
      }
      paths.push(summary);
      return;
    }

    const neighbors = adjacency.get(currentIdx) || [];
    for (const edge of neighbors) {
      const neighborIdx = edge.to;
      if (path.includes(neighborIdx)) continue;
      const neighborTrain = nodes[neighborIdx][1];
      const currentTrain = nodes[currentIdx][1];
      const edgeDuration = edge.duration;
      if (edgeDuration <= 0) continue;
      const nextTime = currentTime + edgeDuration;
      let nextTransfers = transfersUsed;
      const isTransferNow = edge.type === 'transfer' || neighborTrain !== currentTrain;
      const transferStation = isTransferNow ? nodes[currentIdx][0] : null;
      if (isTransferNow && !allowSameStationConsecutiveTransfers && lastTransferStation !== null && transferStation === lastTransferStation) {
        stats.skipped_same_station_transfers++;
        continue;
      }
      if (isTransferNow) nextTransfers++;
      if (nextTransfers > maxTransfers) continue;
      const lastTrain = trainSequence.length ? trainSequence[trainSequence.length - 1] : null;
      let nextTrainSequence = trainSequence;
      if (!lastTrain || neighborTrain !== lastTrain) nextTrainSequence = [...trainSequence, neighborTrain];

      path.push(neighborIdx);
      edgeHistory.push({ from: currentIdx, to: neighborIdx, duration: edgeDuration, type: edge.type });
      dfs(neighborIdx, nextTime, nextTransfers, path, edgeHistory, nextTrainSequence, startTime, isTransferNow ? transferStation : lastTransferStation);
      edgeHistory.pop();
      path.pop();
    }
  }

  for (const startIdx of startNodes) {
    const startTime = parseTime(nodes[startIdx][2]);
    const startTrain = nodes[startIdx][1];
    dfs(startIdx, startTime, 0, [startIdx], [], [startTrain], startTime, null);
  }
  paths.sort((a, b) => (a.total_minutes - b.total_minutes) || a.departure_time.localeCompare(b.departure_time));
  paths.forEach((p, i) => p.id = i + 1);
  return { paths, stats };
}

// Example usage; consumers should import JSON and call findAllPaths with buildAdjacency
export default {
  parseTime,
  toTime,
  buildAdjacency,
  loadSchedule,
  loadDirectionalityMap,
  findAllPaths,
  mergePathsByTrainSequence
};
