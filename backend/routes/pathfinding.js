import express from 'express';
import DataService from '../services/dataService.js';
import PathfindingService from '../services/pathfindingService.js';
import { validatePathfindingRequest } from '../middleware/validation.js';
import { asyncHandler } from '../middleware/errorHandler.js';
import path from 'node:path';

const router = express.Router();

// Initialize services
const dataService = new DataService();
const pathfindingService = new PathfindingService();

// Load data on startup
let graphData = null;
let scheduleData = null;
let adjacencyList = null;
let trainInfo = null;
let directionMap = null;

const loadInitialData = async () => {
  try {
    const graphPath = process.env.GRAPH_FILE_PATH || './fast_graph.json';
    const schedulePath = process.env.SCHEDULE_FILE_PATH || './schedule_with_directionality.json';

    console.log('Loading initial data...');
    graphData = await dataService.loadGraph(graphPath);
    scheduleData = await dataService.loadSchedule(schedulePath);
    adjacencyList = dataService.buildAdjacencyList(graphData.nodes, graphData.edges);
    trainInfo = dataService.extractTrainInfo(scheduleData);
    directionMap = dataService.extractDirectionalityMap(scheduleData);

    console.log('Initial data loaded successfully');
    return true;
  } catch (error) {
    console.error('Failed to load initial data:', error);
    return false;
  }
};

// Load data on startup
loadInitialData();

/**
 * POST /api/pathfinding/find
 * Find paths between start and end stations
 * Body: {
 *   start_station: string,
 *   end_station: string,
 *   max_transfers?: number,
 *   window_minutes?: number,
 *   allow_same_station_consecutive_transfers?: boolean
 * }
 */
router.post('/find', validatePathfindingRequest, asyncHandler(async (req, res) => {
  const {
    start_station: startStation,
    end_station: endStation,
    max_transfers: maxTransfers,
    window_minutes: windowMinutes,
    allow_same_station_consecutive_transfers: allowSameStationTransfers
  } = req.body;

  const config = require('../config/config');

  // Use provided values or defaults from config
  const finalMaxTransfers = maxTransfers !== undefined ? maxTransfers : config.algorithm.maxTransfers;
  const finalWindowMinutes = windowMinutes !== undefined ? windowMinutes : config.algorithm.timeWindowMinutes;
  const finalAllowSameStationTransfers = allowSameStationTransfers !== undefined
    ? allowSameStationTransfers
    : config.algorithm.allowSameStationTransfers;

  // Check if data is loaded
  if (!graphData || !scheduleData || !adjacencyList) {
      // Try to reload data
      const loaded = await loadInitialData();
      if (!loaded) {
        return res.status(503).json({
          error: 'Service Unavailable',
          message: 'Data files are not available'
        });
      }
    }

    // Find all paths
    console.log(`Finding paths from ${startStation} to ${endStation}`);
    const allPaths = pathfindingService.findAllPaths(
      graphData.nodes,
      adjacencyList,
      startStation,
      endStation,
      trainInfo,
      directionMap,
      {
        maxTransfers: finalMaxTransfers,
        allowSameStationConsecutiveTransfers: finalAllowSameStationTransfers
      }
    );

    if (allPaths.length === 0) {
      return res.json({
        start_station: startStation,
        end_station: endStation,
        generated_at: new Date().toISOString(),
        summary: {
          raw_path_count: 0,
          window_minutes: finalWindowMinutes,
          fastest_minutes: 0,
          filtered_path_count: 0,
          merged_path_count: 0
        },
        paths: []
      });
    }

    // Filter by time window
    const { paths: filteredPaths, fastestMinutes } = pathfindingService.filterPathsByTimeWindow(
      allPaths,
      finalWindowMinutes
    );

    // Merge identical train sequences
    const mergedPaths = pathfindingService.mergePathsByTrainSequence(filteredPaths);

    // Reassign IDs after merging
    mergedPaths.forEach((entry, idx) => {
      entry.id = idx + 1;
    });

    // Generate statistics
    const stats = pathfindingService.getStats();
    const directPaths = mergedPaths.filter(p => p.type === 'Direct');
    const fastDirect = directPaths.filter(p => p.is_fast);
    const slowDirect = directPaths.filter(p => !p.is_fast);

    const transferBreakdown = { 0: 0, 1: 0, 2: 0 };
    mergedPaths.forEach(p => {
      const count = Math.min(Math.max(p.transfer_count || 0, 0), 2);
      transferBreakdown[count] = (transferBreakdown[count] || 0) + 1;
    });

    const response = {
      start_station: startStation,
      end_station: endStation,
      generated_at: new Date().toISOString(),
      summary: {
        raw_path_count: allPaths.length,
        window_minutes: finalWindowMinutes,
        fastest_minutes: fastestMinutes,
        filtered_path_count: filteredPaths.length,
        merged_path_count: mergedPaths.length,
        ...stats
      },
      paths: mergedPaths,
      statistics: {
        direct_paths: {
          total: directPaths.length,
          fast: fastDirect.length,
          slow: slowDirect.length
        },
        transfer_breakdown: transferBreakdown
      }
    };

    console.log(
      `Found ${allPaths.length} raw paths. Fastest duration: ${fastestMinutes} min. ` +
      `Keeping ${filteredPaths.length} paths within +${finalWindowMinutes} min; ` +
      `after merging identical train sequences, ${mergedPaths.length} remain.`
    );

    res.json(response);
}));

/**
 * GET /api/pathfinding/stations
 * Get list of all available stations
 */
router.get('/stations', (req, res) => {
  try {
    if (!graphData) {
      return res.status(503).json({
        error: 'Service Unavailable',
        message: 'Data not loaded'
      });
    }

    const stations = new Set();
    graphData.nodes.forEach(node => {
      stations.add(node[0]); // Station name is the first element
    });

    const stationList = Array.from(stations).sort();

    res.json({
      stations: stationList,
      total_count: stationList.length
    });
  } catch (error) {
    console.error('Error getting stations:', error);
    res.status(500).json({
      error: 'Internal Server Error',
      message: 'Failed to get stations'
    });
  }
});

/**
 * POST /api/pathfinding/reload
 * Reload data files
 */
router.post('/reload', async (req, res) => {
  try {
    console.log('Reloading data files...');
    const loaded = await loadInitialData();

    if (loaded) {
      res.json({
        message: 'Data files reloaded successfully',
        timestamp: new Date().toISOString()
      });
    } else {
      res.status(503).json({
        error: 'Service Unavailable',
        message: 'Failed to reload data files'
      });
    }
  } catch (error) {
    console.error('Error reloading data:', error);
    res.status(500).json({
      error: 'Internal Server Error',
      message: 'Failed to reload data files',
      details: process.env.NODE_ENV === 'development' ? error.message : undefined
    });
  }
});

/**
 * GET /api/pathfinding/status
 * Get service status and data information
 */
router.get('/status', (req, res) => {
  try {
    const status = {
      service: 'pathfinding',
      status: 'healthy',
      timestamp: new Date().toISOString(),
      data_loaded: {
        graph_data: !!graphData,
        schedule_data: !!scheduleData,
        adjacency_list: !!adjacencyList,
        train_info: !!trainInfo,
        direction_map: !!directionMap
      }
    };

    if (graphData) {
      status.data_info = {
        nodes_count: graphData.nodes?.length || 0,
        edges_count: graphData.edges?.length || 0,
        trains_count: scheduleData?.train?.length || 0
      };
    }

    res.json(status);
  } catch (error) {
    console.error('Error getting status:', error);
    res.status(500).json({
      error: 'Internal Server Error',
      message: 'Failed to get status'
    });
  }
});

export default router;