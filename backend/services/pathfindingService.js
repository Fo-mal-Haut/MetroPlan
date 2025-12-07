const { parseTime, toTime, formatDuration } = require('../utils/timeUtils');

class PathfindingService {
  constructor() {
    this.paths = [];
    this.stats = {
      skipped_same_station_transfers: 0
    };
  }

  /**
   * Find all paths between stations using DFS algorithm
   * @param {Array} nodes - Array of nodes
   * @param {Object} adjacency - Adjacency list
   * @param {string} startStation - Start station name
   * @param {string} endStation - End station name
   * @param {Object} trainInfo - Train information mapping
   * @param {Object} directionMap - Directionality mapping (optional)
   * @param {Object} options - Additional options
   * @returns {Array} - Array of found paths
   */
  findAllPaths(nodes, adjacency, startStation, endStation, trainInfo, directionMap = null, options = {}) {
    const {
      maxTransfers = 2,
      allowSameStationConsecutiveTransfers = false
    } = options;

    this.paths = [];
    this.stats = { skipped_same_station_transfers: 0 };

    // Find starting nodes
    const startNodes = nodes
      .map((node, idx) => ({ node, idx }))
      .filter(({ node }) => node[0] === startStation)
      .map(({ idx }) => idx);

    if (startNodes.length === 0) {
      return [];
    }

    // DFS function
    const dfs = (currentIdx, currentTime, transfersUsed, path, edgeHistory, trainSequence, startTime, lastTransferStation = null) => {
      const stationName = nodes[currentIdx][0];

      // Check if we reached destination
      if (stationName === endStation && edgeHistory.length > 0) {
        const pathSummary = this.summarizePath(
          nodes,
          edgeHistory,
          trainSequence,
          startTime,
          currentTime,
          trainInfo
        );

        // Check directionality consistency if required
        if (directionMap && pathSummary.transfer_count > 0) {
          const seq = pathSummary.train_sequence;
          let invalid = false;

          for (let i = 0; i < seq.length - 1; i++) {
            const a = directionMap[seq[i]];
            const b = directionMap[seq[i + 1]];

            if (!a || !b) continue;

            // Check for opposite direction on any line
            for (let j = 0; j < Math.min(a.length, b.length); j++) {
              if (a[j] !== 0 && b[j] !== 0 && a[j] === -b[j]) {
                invalid = true;
                break;
              }
            }
            if (invalid) break;
          }

          if (invalid) return; // Skip this path
        }

        this.paths.push(pathSummary);
        return;
      }

      // Explore neighbors
      const neighbors = adjacency[currentIdx] || [];
      for (const edge of neighbors) {
        const neighborIdx = edge.to;

        // Skip if already visited
        if (path.includes(neighborIdx)) continue;

        const neighborTrain = nodes[neighborIdx][1];
        const currentTrain = nodes[currentIdx][1];
        const edgeDuration = edge.duration;

        if (edgeDuration <= 0) continue;

        const nextTime = currentTime + edgeDuration;
        let nextTransfers = transfersUsed;
        const isTransferNow = edge.type === 'transfer' || neighborTrain !== currentTrain;
        const transferStation = isTransferNow ? nodes[currentIdx][0] : null;

        // Check consecutive transfers at same station
        if (isTransferNow && !allowSameStationConsecutiveTransfers && lastTransferStation) {
          if (transferStation === lastTransferStation) {
            this.stats.skipped_same_station_transfers++;
            continue;
          }
        }

        if (isTransferNow) nextTransfers++;
        if (nextTransfers > maxTransfers) continue;

        // Update train sequence
        const nextTrainSequence = trainSequence && neighborTrain === trainSequence[trainSequence.length - 1]
          ? trainSequence
          : [...trainSequence, neighborTrain];

        // Recurse
        path.push(neighborIdx);
        edgeHistory.push({
          from: currentIdx,
          to: neighborIdx,
          type: edge.type,
          duration: edgeDuration
        });

        dfs(
          neighborIdx,
          nextTime,
          nextTransfers,
          path,
          edgeHistory,
          nextTrainSequence,
          startTime,
          isTransferNow ? transferStation : lastTransferStation
        );

        // Backtrack
        edgeHistory.pop();
        path.pop();
      }
    };

    // Start DFS from each starting node
    for (const startIdx of startNodes) {
      const startTime = parseTime(nodes[startIdx][2]);
      const startTrain = nodes[startIdx][1];

      dfs(
        startIdx,
        startTime,
        0,
        [startIdx],
        [],
        [startTrain],
        startTime
      );
    }

    // Sort paths by total duration and departure time
    this.paths.sort((a, b) => {
      if (a.total_minutes !== b.total_minutes) {
        return a.total_minutes - b.total_minutes;
      }
      return a.departure_time.localeCompare(b.departure_time);
    });

    // Add IDs
    this.paths.forEach((path, idx) => {
      path.id = idx + 1;
    });

    return this.paths;
  }

  /**
   * Create a summary object for a completed path
   * @param {Array} nodes - Array of nodes
   * @param {Array} edgeHistory - Edge history
   * @param {Array} trainSequence - Train sequence
   * @param {number} startTime - Start time in minutes
   * @param {number} endTime - End time in minutes
   * @param {Object} trainInfo - Train information mapping
   * @returns {Object} - Path summary
   */
  summarizePath(nodes, edgeHistory, trainSequence, startTime, endTime, trainInfo) {
    let timeline = startTime;
    const transferDetails = [];

    for (const edge of edgeHistory) {
      const prevTime = timeline;
      timeline += edge.duration;

      if (edge.type === 'transfer') {
        const stationName = nodes[edge.from][0];
        transferDetails.push({
          station: stationName,
          arrival_time: toTime(prevTime),
          departure_time: toTime(timeline),
          wait_minutes: edge.duration
        });
      }
    }

    // Ensure final timeline matches recorded end time
    if (timeline !== endTime) {
      timeline = endTime;
    }

    let totalMinutes = timeline - startTime;
    if (totalMinutes < 0) totalMinutes += 1440;

    const trainSeqCopy = [...trainSequence];
    const isFast = trainSeqCopy.some(trainId => trainInfo[trainId]?.is_fast);

    return {
      type: transferDetails.length > 0 ? 'Transfer' : 'Direct',
      train_sequence: trainSeqCopy,
      transfer_details: transferDetails,
      departure_time: toTime(startTime),
      arrival_time: toTime(timeline),
      total_time: formatDuration(totalMinutes),
      total_minutes: totalMinutes,
      is_fast: isFast,
      transfer_count: transferDetails.length
    };
  }

  /**
   * Merge paths that share identical train sequences
   * @param {Array} paths - Array of paths
   * @returns {Array} - Merged paths
   */
  mergePathsByTrainSequence(paths) {
    const grouped = new Map();
    const orderedKeys = [];

    for (const entry of paths) {
      const transferCount = entry.transfer_count || (entry.transfer_details || []).length;
      const key = JSON.stringify([
        entry.train_sequence || [],
        entry.type,
        transferCount,
        entry.departure_time,
        entry.arrival_time,
        entry.total_minutes
      ]);

      if (!grouped.has(key)) {
        const base = JSON.parse(JSON.stringify(entry));

        if (transferCount > 0) {
          const optionLists = Array.from({ length: transferCount }, () => []);

          for (const [idx, detail] of (entry.transfer_details || []).entries()) {
            optionLists[idx].push(JSON.parse(JSON.stringify(detail)));
          }

          base._transfer_option_lists = optionLists;
        }

        grouped.set(key, base);
        orderedKeys.push(key);
        continue;
      }

      const base = grouped.get(key);
      if (transferCount === 0) continue;

      const optionLists = base._transfer_option_lists || Array.from({ length: transferCount }, () => []);
      base._transfer_option_lists = optionLists;

      for (const [idx, detail] of (entry.transfer_details || []).entries()) {
        if (idx >= optionLists.length) {
          optionLists.push([]);
        }

        const exists = optionLists[idx].some(existing =>
          JSON.stringify(existing) === JSON.stringify(detail)
        );

        if (!exists) {
          optionLists[idx].push(JSON.parse(JSON.stringify(detail)));
        }
      }
    }

    const merged = [];
    for (const key of orderedKeys) {
      const base = grouped.get(key);
      const optionLists = base._transfer_option_lists;

      if (optionLists) {
        delete base._transfer_option_lists;

        base.transfer_options = optionLists
          .map((optionList, idx) => ({
            step: idx + 1,
            options: optionList
          }))
          .filter(option => option.options.length > 0);

        base.transfer_details = optionLists
          .filter(optionList => optionList.length > 0)
          .map(optionList => optionList[0]);
      }

      merged.push(base);
    }

    return merged;
  }

  /**
   * Filter paths by time window
   * @param {Array} paths - Array of paths
   * @param {number} windowMinutes - Time window in minutes
   * @returns {Object} - Filtered paths and summary
   */
  filterPathsByTimeWindow(paths, windowMinutes) {
    if (paths.length === 0) {
      return { paths: [], fastestMinutes: 0 };
    }

    const fastestMinutes = Math.min(...paths.map(p => p.total_minutes));
    const cutoffMinutes = fastestMinutes + Math.max(windowMinutes, 0);
    const filteredPaths = paths.filter(p => p.total_minutes <= cutoffMinutes);

    return { paths: filteredPaths, fastestMinutes };
  }

  /**
   * Get statistics
   * @returns {Object} - Statistics
   */
  getStats() {
    return { ...this.stats };
  }
}

module.exports = PathfindingService;