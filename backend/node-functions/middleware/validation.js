import config from '../../config/config.js';
import cors from 'cors';

export const configureCORS = cors({
  origin: [
    'http://localhost:8080',
    'http://10.193.2.241:8080',
    // 如果以后有正式域名，也加在这里
  ],
  methods: ['GET', 'POST', 'PUT', 'DELETE', 'OPTIONS'],
  allowedHeaders: ['Content-Type', 'Authorization'],
  credentials: true
});

/**
 * Validation middleware for pathfinding requests
 */
export const validatePathfindingRequest = (req, res, next) => {
  try {
    const { start_station, end_station, max_transfers, window_minutes } = req.body;

    // Required fields validation
    if (!start_station || typeof start_station !== 'string') {
      return res.status(400).json({
        error: 'Bad Request',
        message: 'start_station is required and must be a string',
        field: 'start_station'
      });
    }

    if (!end_station || typeof end_station !== 'string') {
      return res.status(400).json({
        error: 'Bad Request',
        message: 'end_station is required and must be a string',
        field: 'end_station'
      });
    }

    // Station name validation
    if (start_station.length < config.validation.minStationNameLength ||
        start_station.length > config.validation.maxStationNameLength) {
      return res.status(400).json({
        error: 'Bad Request',
        message: `start_station length must be between ${config.validation.minStationNameLength} and ${config.validation.maxStationNameLength} characters`,
        field: 'start_station'
      });
    }

    if (end_station.length < config.validation.minStationNameLength ||
        end_station.length > config.validation.maxStationNameLength) {
      return res.status(400).json({
        error: 'Bad Request',
        message: `end_station length must be between ${config.validation.minStationNameLength} and ${config.validation.maxStationNameLength} characters`,
        field: 'end_station'
      });
    }

    // Different stations validation
    if (start_station.trim() === end_station.trim()) {
      return res.status(400).json({
        error: 'Bad Request',
        message: 'start_station and end_station must be different',
        field: 'end_station'
      });
    }

    // Optional parameters validation
    if (max_transfers !== undefined) {
      const maxTransfersNum = parseInt(max_transfers);
      if (isNaN(maxTransfersNum) || maxTransfersNum < 0 || maxTransfersNum > config.validation.maxTransfers) {
        return res.status(400).json({
          error: 'Bad Request',
          message: `max_transfers must be a number between 0 and ${config.validation.maxTransfers}`,
          field: 'max_transfers'
        });
      }
    }

    if (window_minutes !== undefined) {
      const windowMinutesNum = parseInt(window_minutes);
      if (isNaN(windowMinutesNum) || windowMinutesNum < 0 || windowMinutesNum > config.validation.maxTimeWindowMinutes) {
        return res.status(400).json({
          error: 'Bad Request',
          message: `window_minutes must be a number between 0 and ${config.validation.maxTimeWindowMinutes}`,
          field: 'window_minutes'
        });
      }
    }

    // Sanitize input
    req.body.start_station = start_station.trim();
    req.body.end_station = end_station.trim();

    next();
  } catch (error) {
    console.error('Validation error:', error);
    res.status(500).json({
      error: 'Internal Server Error',
      message: 'Validation failed'
    });
  }
};

/**
 * Rate limiting middleware (simple implementation)
 */
export const createRateLimiter = (maxRequests = 100, windowMs = 60000) => {
  const requests = new Map();

  return (req, res, next) => {
    const clientId = req.ip || req.headers['x-forwarded-for'] || 'unknown';
    const now = Date.now();

    // Clean old entries
    if (requests.size > 10000) {
      const cutoff = now - windowMs;
      for (const [key, timestamps] of requests.entries()) {
        requests.set(key, timestamps.filter(timestamp => timestamp > cutoff));
        if (requests.get(key).length === 0) {
          requests.delete(key);
        }
      }
    }

    // Get client requests
    const clientRequests = requests.get(clientId) || [];
    const recentRequests = clientRequests.filter(timestamp => now - timestamp < windowMs);

    if (recentRequests.length >= maxRequests) {
      return res.status(429).json({
        error: 'Too Many Requests',
        message: `Rate limit exceeded. Maximum ${maxRequests} requests per ${windowMs / 1000} seconds.`,
        retry_after: Math.ceil(windowMs / 1000)
      });
    }

    // Add current request
    recentRequests.push(now);
    requests.set(clientId, recentRequests);

    next();
  };
};

/**
 * Request timeout middleware
 */
export const createRequestTimeout = (timeoutMs = config.api.requestTimeout) => {
  return (req, res, next) => {
    const timeout = setTimeout(() => {
      if (!res.headersSent) {
        res.status(408).json({
          error: 'Request Timeout',
          message: 'Request took too long to process'
        });
      }
    }, timeoutMs);

    res.on('finish', () => clearTimeout(timeout));
    res.on('close', () => clearTimeout(timeout));

    next();
  };
};
