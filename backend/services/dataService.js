import fs from 'node:fs/promises';
import path from 'node:path';

export default class DataService {
  constructor() {
    this.graphData = null;
    this.scheduleData = null;
    this.adjacencyList = null;
  }

  /**
   * Load graph data from JSON file
   * @param {string} filePath - Path to graph JSON file
   * @returns {Promise<{nodes: Array, edges: Array}>}
   */
  async loadGraph(filePath) {
    try {
      const data = await fs.readFile(filePath, 'utf8');
      const graphData = JSON.parse(data);
      this.graphData = {
        nodes: graphData.nodes || [],
        edges: graphData.edges || []
      };
      return this.graphData;
    } catch (error) {
      throw new Error(`Failed to load graph data from ${filePath}: ${error.message}`);
    }
  }

  /**
   * Load schedule data from JSON file
   * @param {string} filePath - Path to schedule JSON file
   * @returns {Promise<Object>}
   */
  async loadSchedule(filePath) {
    try {
      const data = await fs.readFile(filePath, 'utf8');
      const scheduleData = JSON.parse(data);
      this.scheduleData = scheduleData;
      return scheduleData;
    } catch (error) {
      throw new Error(`Failed to load schedule data from ${filePath}: ${error.message}`);
    }
  }

  /**
   * Extract train information from schedule data
   * @param {Object} scheduleData - Schedule data object
   * @returns {Object} - Train info mapping (train_id -> info)
   */
  extractTrainInfo(scheduleData) {
    const trainInfo = {};
    const trains = scheduleData.train || [];

    trains.forEach(train => {
      trainInfo[train.id] = {
        is_fast: train.is_fast || false,
        directionality: train.directionality
      };
    });

    return trainInfo;
  }

  /**
   * Extract directionality mapping from schedule data
   * @param {Object} scheduleData - Schedule data object
   * @returns {Object} - Directionality mapping (train_id -> direction vector)
   */
  extractDirectionalityMap(scheduleData) {
    const directionMap = {};
    const trains = scheduleData.train || [];

    trains.forEach(train => {
      if (Array.isArray(train.directionality)) {
        directionMap[train.id] = train.directionality;
      }
    });

    return directionMap;
  }

  /**
   * Build adjacency list from nodes and edges
   * @param {Array} nodes - Array of nodes
   * @param {Array} edges - Array of edges
   * @returns {Object} - Adjacency list
   */
  buildAdjacencyList(nodes, edges) {
    const nodeLookup = new Map();

    // Create node lookup map
    nodes.forEach((node, idx) => {
      nodeLookup.set(JSON.stringify(node), idx);
    });

    const adjacency = {};

    // Initialize adjacency list
    for (let i = 0; i < nodes.length; i++) {
      adjacency[i] = [];
    }

    // Build adjacency list
    edges.forEach(edge => {
      const fromKey = JSON.stringify(edge.from);
      const toKey = JSON.stringify(edge.to);
      const fromIdx = nodeLookup.get(fromKey);
      const toIdx = nodeLookup.get(toKey);

      if (fromIdx === undefined || toIdx === undefined) {
        return; // Skip invalid edges
      }

      const duration = edge.weight || edge.segment_travel_time || 0;
      if (duration <= 0) {
        return; // Skip invalid duration
      }

      const edgeInfo = {
        to: toIdx,
        type: edge.type || 'travel',
        duration: duration
      };

      adjacency[fromIdx].push(edgeInfo);
    });

    this.adjacencyList = adjacency;
    return adjacency;
  }

  /**
   * Get loaded graph data
   * @returns {Object|null}
   */
  getGraphData() {
    return this.graphData;
  }

  /**
   * Get loaded schedule data
   * @returns {Object|null}
   */
  getScheduleData() {
    return this.scheduleData;
  }

  /**
   * Get adjacency list
   * @returns {Object|null}
   */
  getAdjacencyList() {
    return this.adjacencyList;
  }

  /**
   * Save results to JSON file
   * @param {Object} results - Results object
   * @param {string} filename - Output filename
   * @param {string} outputDir - Output directory
   * @returns {Promise<string>} - Path to saved file
   */
  async saveResults(results, filename, outputDir = './results') {
    try {
      // Create output directory if it doesn't exist
      await fs.mkdir(outputDir, { recursive: true });

      const outputPath = path.join(outputDir, filename);
      await fs.writeFile(outputPath, JSON.stringify(results, null, 2), 'utf8');

      return outputPath;
    } catch (error) {
      throw new Error(`Failed to save results to ${filename}: ${error.message}`);
    }
  }
}
