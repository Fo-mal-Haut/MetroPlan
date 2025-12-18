import 'dotenv/config';

const config = {
  // Server configuration
  server: {
    port: process.env.PORT || 3000,
    nodeEnv: process.env.NODE_ENV || 'development',
    corsOrigin: process.env.CORS_ORIGIN || '*'
  },

  // File paths
  paths: {
    graphFile: process.env.GRAPH_FILE_PATH || './fast_graph.json',
    scheduleFile: process.env.SCHEDULE_FILE_PATH || './schedule_with_directionality.json',
    resultsDir: process.env.RESULTS_DIR || './results'
  },

  // Algorithm parameters
  algorithm: {
    maxTransfers: parseInt(process.env.MAX_TRANSFERS) || 2,
    timeWindowMinutes: parseInt(process.env.TIME_WINDOW_MINUTES) || 90,
    allowSameStationTransfers: process.env.ALLOW_SAME_STATION_TRANSFERS === 'true'
  },

  // API configuration
  api: {
    requestTimeout: parseInt(process.env.REQUEST_TIMEOUT) || 30000,
    maxRequestSize: process.env.MAX_REQUEST_SIZE || '10mb'
  },

  // Logging configuration
  logging: {
    level: process.env.LOG_LEVEL || 'info',
    enableFileLogging: process.env.ENABLE_FILE_LOGGING === 'true',
    logFile: process.env.LOG_FILE || './logs/app.log'
  },

  // Validation rules
  validation: {
    maxStationNameLength: 50,
    minStationNameLength: 1,
    maxTransfers: 5,
    maxTimeWindowMinutes: 480 // 8 hours max
  }
};

// Validate configuration
const validateConfig = () => {
  const errors = [];

  // Validate paths
  if (!config.paths.graphFile) {
    errors.push('Graph file path is required');
  }

  if (!config.paths.scheduleFile) {
    errors.push('Schedule file path is required');
  }

  // Validate algorithm parameters
  if (config.algorithm.maxTransfers < 0 || config.algorithm.maxTransfers > config.validation.maxTransfers) {
    errors.push(`Max transfers must be between 0 and ${config.validation.maxTransfers}`);
  }

  if (config.algorithm.timeWindowMinutes < 0 || config.algorithm.timeWindowMinutes > config.validation.maxTimeWindowMinutes) {
    errors.push(`Time window must be between 0 and ${config.validation.maxTimeWindowMinutes} minutes`);
  }

  // Validate server configuration
  if (config.server.port < 1 || config.server.port > 65535) {
    errors.push('Server port must be between 1 and 65535');
  }

  if (errors.length > 0) {
    throw new Error(`Configuration validation failed: ${errors.join(', ')}`);
  }
};

// Configuration validation on startup
try {
  validateConfig();
  console.log('Configuration validation passed');
} catch (error) {
  console.error('Configuration validation failed:', error.message);
  process.exit(1);
}

export default config;