# Metro Plan Backend API

基于Node.js和Express.js的城市交通路径规划后端API，使用深度优先搜索(DFS)算法实现地铁/城际铁路的换乘方案计算。

## 功能特性

- **深度优先搜索算法**: 实现高效的路径查找，支持最多2次换乘
- **多语言支持**: 支持中文站名和车次信息
- **智能合并**: 自动合并相同车次序列的路径方案
- **时间窗口过滤**: 基于最快路线的时间窗口过滤
- **方向性验证**: 确保换乘方案的方向性一致性
- **RESTful API**: 标准的REST API设计
- **错误处理**: 完善的错误处理和日志记录
- **配置管理**: 灵活的配置管理系统

## 快速开始

### 环境要求

- Node.js 14.0+
- npm 6.0+

### 安装依赖

```bash
cd backend
npm install
```

### 配置环境变量

复制环境变量模板文件：

```bash
cp .env.example .env
```

编辑 `.env` 文件：

```env
# 服务器配置
NODE_ENV=development
PORT=3000

# 数据文件路径
GRAPH_FILE_PATH=./fast_graph.json
SCHEDULE_FILE_PATH=./schedule_with_directionality.json
RESULTS_DIR=./results

# 算法参数
MAX_TRANSFERS=2
TIME_WINDOW_MINUTES=120
ALLOW_SAME_STATION_TRANSFERS=false
```

### 启动服务器

```bash
# 开发模式
npm run dev

# 生产模式
npm start
```

服务器启动后访问 http://localhost:3000

## API 文档

### 1. 路径查找

**POST** `/api/pathfinding/find`

查找两个站点之间的所有路径方案。

**请求体:**
```json
{
  "start_station": "佛山西",
  "end_station": "肇庆",
  "max_transfers": 2,
  "window_minutes": 120,
  "allow_same_station_consecutive_transfers": false
}
```

**响应:**
```json
{
  "start_station": "佛山西",
  "end_station": "肇庆",
  "generated_at": "2023-12-07T10:30:00.000Z",
  "summary": {
    "raw_path_count": 15,
    "window_minutes": 120,
    "fastest_minutes": 67,
    "filtered_path_count": 8,
    "merged_path_count": 5
  },
  "paths": [
    {
      "id": 1,
      "type": "Direct",
      "train_sequence": ["C4781"],
      "transfer_details": [],
      "departure_time": "06:00",
      "arrival_time": "07:07",
      "total_time": "1h 7m",
      "total_minutes": 67,
      "is_fast": false,
      "transfer_count": 0
    }
  ],
  "statistics": {
    "direct_paths": {
      "total": 2,
      "fast": 1,
      "slow": 1
    },
    "transfer_breakdown": {
      "0": 2,
      "1": 2,
      "2": 1
    }
  }
}
```

### 2. 获取站点列表

**GET** `/api/pathfinding/stations`

获取所有可用的站点列表。

**响应:**
```json
{
  "stations": ["佛山西", "狮山", "狮山北", "三水北"],
  "total_count": 4
}
```

### 3. 服务状态检查

**GET** `/api/pathfinding/status`

检查服务状态和数据加载情况。

**响应:**
```json
{
  "service": "pathfinding",
  "status": "healthy",
  "timestamp": "2023-12-07T10:30:00.000Z",
  "data_loaded": {
    "graph_data": true,
    "schedule_data": true,
    "adjacency_list": true,
    "train_info": true,
    "direction_map": true
  },
  "data_info": {
    "nodes_count": 1200,
    "edges_count": 2400,
    "trains_count": 45
  }
}
```

### 4. 重新加载数据

**POST** `/api/pathfinding/reload`

重新加载JSON数据文件。

**响应:**
```json
{
  "message": "Data files reloaded successfully",
  "timestamp": "2023-12-07T10:30:00.000Z"
}
```

### 5. 健康检查

**GET** `/health`

简单的健康检查端点。

## 数据格式

### 路径图数据格式 (fast_graph.json)

```json
{
  "nodes": [
    ["佛山西", "C4781", "06:00"],
    ["狮山", "C4781", "06:07"]
  ],
  "edges": [
    {
      "from": ["佛山西", "C4781", "06:00"],
      "to": ["狮山", "C4781", "06:07"],
      "weight": 7,
      "type": "travel"
    }
  ]
}
```

### 时刻表数据格式 (schedule_with_directionality.json)

```json
{
  "train": [
    {
      "id": "C4781",
      "start_station": "佛山西",
      "end_station": "肇庆",
      "is_fast": false,
      "directionality": [1, 0, 0, 0],
      "stations": [
        {
          "name": "佛山西",
          "time": "06:00"
        }
      ]
    }
  ]
}
```

## 项目结构

```
backend/
├── app.js                  # 主应用文件
├── package.json           # 项目配置和依赖
├── README.md             # 项目文档
├── .env.example          # 环境变量模板
├── config/
│   └── config.js         # 配置管理
├── middleware/
│   ├── validation.js     # 请求验证中间件
│   └── errorHandler.js   # 错误处理中间件
├── routes/
│   └── pathfinding.js    # API路由
├── services/
│   ├── dataService.js    # 数据处理服务
│   └── pathfindingService.js # 路径查找服务
├── utils/
│   └── timeUtils.js      # 时间工具函数
├── public/               # 静态文件
└── results/              # 结果输出目录
```

## 部署

### 使用 PM2 部署

1. 安装 PM2:
```bash
npm install -g pm2
```

2. 创建 PM2 配置文件 `ecosystem.config.js`:
```javascript
module.exports = {
  apps: [{
    name: 'metro-plan-backend',
    script: 'app.js',
    instances: 'max',
    exec_mode: 'cluster',
    env: {
      NODE_ENV: 'production',
      PORT: 3000
    },
    error_file: './logs/err.log',
    out_file: './logs/out.log',
    log_file: './logs/combined.log',
    time: true
  }]
};
```

3. 启动应用:
```bash
pm2 start ecosystem.config.js
pm2 save
pm2 startup
```

### 使用 Docker 部署

1. 创建 `Dockerfile`:
```dockerfile
FROM node:16-alpine

WORKDIR /app

COPY package*.json ./
RUN npm ci --only=production

COPY . .

EXPOSE 3000

USER node

CMD ["npm", "start"]
```

2. 构建和运行:
```bash
docker build -t metro-plan-backend .
docker run -p 3000:3000 --env-file .env metro-plan-backend
```

## 性能优化

- **数据预加载**: 应用启动时预加载JSON数据到内存
- **邻接表优化**: 使用邻接表提高图算法性能
- **路径缓存**: 相同请求的结果缓存
- **请求限制**: 实现请求频率限制防止滥用
- **集群模式**: 使用PM2集群模式提高并发性能

## 监控和日志

- 应用日志使用Morgan中间件
- 错误日志记录到控制台和文件
- 提供健康检查端点用于监控
- 支持日志级别配置

## 开发

### 运行测试
```bash
npm test
```

### 代码格式化
建议使用ESLint和Prettier进行代码格式化。

### 调试
开发模式下自动启用详细错误信息和调试日志。

## 许可证

MIT License

## 贡献

欢迎提交Issue和Pull Request来改进项目。