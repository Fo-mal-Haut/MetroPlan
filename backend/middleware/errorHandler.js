import config from '../config/config.js';

/**
 * Global error handling middleware
 */
export const errorHandler = (err, req, res, next) => {
  console.error('Error occurred:', {
    message: err.message,
    stack: err.stack,
    url: req.url,
    method: req.method,
    ip: req.ip,
    timestamp: new Date().toISOString()
  });

  // Default error
  let statusCode = 500;
  let message = 'Internal Server Error';
  let details = null;

  // Handle specific error types
  if (err.name === 'ValidationError') {
    statusCode = 400;
    message = 'Validation Error';
    details = err.message;
  } else if (err.name === 'SyntaxError' && err.type === 'entity.parse.failed') {
    statusCode = 400;
    message = 'Invalid JSON';
    details = 'The request body contains invalid JSON';
  } else if (err.code === 'ENOENT') {
    statusCode = 404;
    message = 'File Not Found';
    details = 'Required data file is missing';
  } else if (err.code === 'EACCES') {
    statusCode = 403;
    message = 'Permission Denied';
    details = 'Insufficient permissions to access resource';
  } else if (err.message.includes('timeout')) {
    statusCode = 408;
    message = 'Request Timeout';
    details = 'The request took too long to process';
  }

  const errorResponse = {
    error: message,
    timestamp: new Date().toISOString(),
    path: req.url
  };

  // Add details in development mode
  if (config.server.nodeEnv === 'development') {
    errorResponse.details = details || err.message;
    errorResponse.stack = err.stack;
  } else if (details) {
    errorResponse.details = details;
  }

  res.status(statusCode).json(errorResponse);
};

/**
 * 404 Not Found handler
 */
export const notFoundHandler = (req, res, next) => {
  res.status(404).json({
    error: 'Not Found',
    message: 'The requested resource was not found',
    path: req.url,
    timestamp: new Date().toISOString()
  });
};

/**
 * Async handler wrapper to catch errors in async routes
 */
export const asyncHandler = (fn) => (req, res, next) => {
  Promise.resolve(fn(req, res, next)).catch(next);
};

/**
 * Setup graceful shutdown for the server
 */
export const setupGracefulShutdown = (server) => {
  const gracefulShutdown = (signal) => {
    console.log(`\nReceived ${signal}. Starting graceful shutdown...`);

    server.close((err) => {
      if (err) {
        console.error('Error during server shutdown:', err);
        process.exit(1);
      }

      console.log('Server closed successfully');

      // Close database connections, clear timeouts, etc.
      setTimeout(() => {
        console.log('Graceful shutdown completed');
        process.exit(0);
      }, 1000);
    });
  };

  // Handle different shutdown signals
  process.on('SIGTERM', () => gracefulShutdown('SIGTERM'));
  process.on('SIGINT', () => gracefulShutdown('SIGINT'));

  // Handle uncaught exceptions
  process.on('uncaughtException', (err) => {
    console.error('Uncaught Exception:', err);
    gracefulShutdown('uncaughtException');
  });

  // Handle unhandled promise rejections
  process.on('unhandledRejection', (reason, promise) => {
    console.error('Unhandled Rejection at:', promise, 'reason:', reason);
    gracefulShutdown('unhandledRejection');
  });
};
