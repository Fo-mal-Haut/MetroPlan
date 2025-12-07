const express = require('express');
const helmet = require('helmet');
const morgan = require('morgan');
const path = require('path');

const config = require('./config/config');
const { configureCORS, createRateLimiter, createRequestTimeout } = require('./middleware/validation');
const { errorHandler, notFoundHandler, setupGracefulShutdown } = require('./middleware/errorHandler');
const pathfindingRoutes = require('./routes/pathfinding');

const app = express();

// Trust proxy for proper IP detection
app.set('trust proxy', 1);

// Security middleware
app.use(helmet({
  contentSecurityPolicy: {
    directives: {
      defaultSrc: ["'self'"],
      styleSrc: ["'self'", "'unsafe-inline'"],
      scriptSrc: ["'self'"],
      imgSrc: ["'self'", "data:", "https:"],
    },
  },
}));

// CORS configuration
app.use(configureCORS);

// Rate limiting
const rateLimiter = createRateLimiter(100, 60000); // 100 requests per minute
app.use(rateLimiter);

// Request timeout
app.use(createRequestTimeout(config.api.requestTimeout));

// Logging
if (config.server.nodeEnv === 'production') {
  app.use(morgan('combined'));
} else {
  app.use(morgan('dev'));
}

// Body parsing
app.use(express.json({ limit: config.api.maxRequestSize }));
app.use(express.urlencoded({ extended: true, limit: config.api.maxRequestSize }));

// Serve static files
app.use(express.static(path.join(__dirname, 'public')));

// API Routes
app.use('/api/pathfinding', pathfindingRoutes);

// Health check endpoint
app.get('/health', (req, res) => {
  res.status(200).json({
    status: 'OK',
    timestamp: new Date().toISOString(),
    service: 'metro-plan-backend'
  });
});

// Root endpoint
app.get('/', (req, res) => {
  res.json({
    message: 'Metro Plan Backend API',
    version: '1.0.0',
    endpoints: {
      health: '/health',
      pathfinding: '/api/pathfinding'
    }
  });
});

// Error handling middleware (must be after all routes)
app.use(notFoundHandler);
app.use(errorHandler);

// Start server
const server = app.listen(config.server.port, () => {
  console.log(`Metro Plan Backend server running on port ${config.server.port}`);
  console.log(`Environment: ${config.server.nodeEnv}`);
  console.log(`CORS Origin: ${config.server.corsOrigin}`);
});

// Setup graceful shutdown
setupGracefulShutdown(server);

module.exports = app;