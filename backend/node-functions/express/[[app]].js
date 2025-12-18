import express from 'express';
import helmet from 'helmet';
import morgan from 'morgan';
import path from 'path';
import { fileURLToPath } from 'url'; // 新增

// 修复 ESM 下没有 __dirname 的问题
const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

import config from '../../config/config.js';
import { configureCORS, createRateLimiter, createRequestTimeout } from '../../middleware/validation.js';
import { errorHandler, notFoundHandler } from '../../middleware/errorHandler.js';
import pathfindingRoutes from '../../routes/pathfinding.js';

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
app.use(express.static(path.join(__dirname, '../../public')));

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

// 重要：必须导出实例，且不能有 app.listen()
export default app;