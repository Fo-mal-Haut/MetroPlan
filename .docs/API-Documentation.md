# MetroPlan API 文档

## 概述

MetroPlan 是一个综合性的城际轨道交通规划系统，提供广东省区域内的列车路径查询服务。本文档详细描述了 MetroPlan Flask API 的所有端点、请求/响应格式以及使用示例。

**API 版本**: 1.3 (Flask MVP)
**基础URL**: `http://localhost:5000`
**数据更新时间**: 动态加载（启动时）
**支持车站数量**: 65个车站
**支持列车数量**: 242辆列车

## 认证

当前版本为 MVP 版本，无需认证即可访问所有 API 端点。

## 数据格式

所有 API 端点使用 JSON 格式进行数据交换：

- **Content-Type**: `application/json`
- **字符编码**: UTF-8
- **时区**: 本地时间（自动转换）

## API 端点

### 1. 健康检查

检查 API 服务状态和数据加载情况。

#### 端点信息
- **URL**: `GET /health`
- **描述**: 服务健康状态检查
- **参数**: 无

#### 响应示例

**成功响应 (200 OK)**:
```json
{
  "status": "healthy",
  "data_loaded": {
    "graph": true,
    "schedule": true,
    "train_info": true,
    "directionality_map": true,
    "adjacency": true,
    "nodes": true,
    "stations_list": true
  },
  "timestamp": "2024-12-01T10:30:00+08:00"
}
```

**响应字段说明**:
- `status`: 服务状态 (`healthy` | `unhealthy`)
- `data_loaded`: 各类数据的加载状态
- `timestamp`: 响应生成时间（本地时间）

### 2. 车站列表

获取系统中所有可用的车站信息。

#### 端点信息
- **URL**: `GET /stations`
- **描述**: 获取所有车站名称列表
- **参数**: 无

#### 响应示例

**成功响应 (200 OK)**:
```json
{
  "stations": [
    "广州南",
    "广州东",
    "花都",
    "肇庆",
    "珠海",
    "深圳北",
    "西平西",
    "琶洲",
    ...
  ],
  "count": 65,
  "timestamp": "2024-12-01T10:30:00+08:00"
}
```

**响应字段说明**:
- `stations`: 车站名称数组（按字母顺序排序）
- `count`: 车站总数
- `timestamp`: 响应生成时间

### 3. 路径查询

查询两个车站之间的最优路径，支持最多2次换乘。

#### 端点信息
- **URL**: `POST /path`
- **描述**: 车站间路径规划查询
- **参数**: JSON 请求体

#### 请求参数

```json
{
  "start_station": "广州南",
  "end_station": "深圳北",
  "max_transfers": 2,
  "window_minutes": 120,
  "allow_same_station_consecutive_transfers": false
}
```

**参数说明**:
- `start_station` (必需): 起始车站名称
- `end_station` (必需): 目标车站名称
- `max_transfers` (可选, 默认2): 最大换乘次数 (0-2)
- `window_minutes` (可选, 默认120): 时间窗口（分钟），超过最短路径时间的限制
- `allow_same_station_consecutive_transfers` (可选, 默认false): 是否允许同一车站连续换乘

#### 响应示例

**成功响应 (200 OK)**:
```json
{
  "start_station": "广州南",
  "end_station": "深圳北",
  "paths": [
    {
      "id": 1,
      "type": "Direct",
      "train_sequence": ["C7711"],
      "departure_time": "07:00",
      "arrival_time": "07:29",
      "total_time": "0h 29m",
      "total_minutes": 29,
      "is_fast": true,
      "transfer_count": 0,
      "transfer_details": [],
      "transfer_options": []
    },
    {
      "id": 2,
      "type": "Transfer",
      "train_sequence": ["C6801", "C7045"],
      "departure_time": "06:30",
      "arrival_time": "08:15",
      "total_time": "1h 45m",
      "total_minutes": 105,
      "is_fast": false,
      "transfer_count": 1,
      "transfer_details": [
        {
          "station": "广州东",
          "arrival_time": "07:15",
          "departure_time": "07:20",
          "wait_minutes": 5
        }
      ],
      "transfer_options": [
        {
          "step": 1,
          "options": [
            {
              "station": "广州东",
              "arrival_time": "07:15",
              "departure_time": "07:20",
              "wait_minutes": 5
            },
            {
              "station": "广州",
              "arrival_time": "07:00",
              "departure_time": "07:10",
              "wait_minutes": 10
            }
          ]
        }
      ]
    }
  ],
  "summary": {
    "total_paths": 25,
    "fastest_minutes": 29,
    "window_minutes": 120,
    "filtered_paths": 12,
    "merged_paths": 5
  },
  "metadata": {
    "max_transfers": 2,
    "generated_at": "2024-12-01T10:30:00+08:00"
  }
}
```

**响应字段说明**:

**根级别字段**:
- `start_station`: 起始车站名称
- `end_station`: 目标车站名称
- `paths`: 路径方案数组
- `summary`: 查询统计信息
- `metadata`: 查询元数据

**路径方案字段 (`paths[].*`)**:
- `id`: 路径方案唯一标识
- `type`: 路径类型 (`Direct` | `Transfer`)
- `train_sequence`: 使用的列车车次序列
- `departure_time`: 出发时间 (HH:MM)
- `arrival_time`: 到达时间 (HH:MM)
- `total_time`: 总时长字符串
- `total_minutes`: 总时长分钟数
- `is_fast`: 是否包含快速列车
- `transfer_count`: 换乘次数
- `transfer_details`: 具体换乘信息数组
- `transfer_options`: 换乘选项数组（合并相同列车序列的多种换乘方案）

**换乘信息字段 (`transfer_details[].*` 和 `transfer_options[].options[].*`)**:
- `station`: 换乘车站名称
- `arrival_time`: 到达换乘站时间
- `departure_time`: 从换乘站出发时间
- `wait_minutes`: 等待时间（分钟）

**统计信息字段 (`summary.*`)**:
- `total_paths`: 找到的原始路径总数
- `fastest_minutes`: 最短路径时间（分钟）
- `window_minutes`: 使用的时间窗口
- `filtered_paths`: 时间窗口过滤后的路径数
- `merged_paths`: 合并相同列车序列后的最终路径数

**元数据字段 (`metadata.*`)**:
- `max_transfers`: 使用的最大换乘次数
- `generated_at`: 响应生成时间

## 使用示例

### Python 示例

```python
import requests
import json

# API 基础URL
BASE_URL = "http://localhost:5000"

def get_stations():
    """获取车站列表"""
    response = requests.get(f"{BASE_URL}/stations")
    return response.json() if response.status_code == 200 else None

def find_path(start, end, max_transfers=2):
    """查询路径"""
    payload = {
        "start_station": start,
        "end_station": end,
        "max_transfers": max_transfers
    }

    response = requests.post(
        f"{BASE_URL}/path",
        json=payload,
        headers={"Content-Type": "application/json"}
    )

    return response.json() if response.status_code == 200 else None

# 使用示例
stations = get_stations()
print(f"共有 {stations['count']} 个车站")

# 查询广州南到深圳北的路径
paths = find_path("广州南", "深圳北")
if paths:
    print(f"找到 {len(paths['paths'])} 条路径方案")
    for path in paths['paths']:
        print(f"路径 {path['id']}: {path['departure_time']} → {path['arrival_time']}, "
              f"耗时 {path['total_time']}, 换乘 {path['transfer_count']} 次")
```

### JavaScript 示例

```javascript
// API 基础URL
const BASE_URL = 'http://localhost:5000';

// 获取车站列表
async function getStations() {
  try {
    const response = await fetch(`${BASE_URL}/stations`);
    return await response.json();
  } catch (error) {
    console.error('获取车站列表失败:', error);
    return null;
  }
}

// 查询路径
async function findPath(start, end, maxTransfers = 2) {
  try {
    const payload = {
      start_station: start,
      end_station: end,
      max_transfers: maxTransfers
    };

    const response = await fetch(`${BASE_URL}/path`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json'
      },
      body: JSON.stringify(payload)
    });

    return await response.json();
  } catch (error) {
    console.error('路径查询失败:', error);
    return null;
  }
}

// 使用示例
(async () => {
  const stations = await getStations();
  console.log(`共有 ${stations.count} 个车站`);

  const paths = await findPath('广州南', '深圳北');
  if (paths && paths.paths) {
    console.log(`找到 ${paths.paths.length} 条路径方案`);
    paths.paths.forEach(path => {
      console.log(`路径 ${path.id}: ${path.departure_time} → ${path.arrival_time}, ` +
                  `耗时 ${path.total_time}, 换乘 ${path.transfer_count} 次`);
    });
  }
})();
```

### cURL 示例

```bash
# 健康检查
curl -X GET http://localhost:5000/health

# 获取车站列表
curl -X GET http://localhost:5000/stations

# 路径查询
curl -X POST http://localhost:5000/path \
  -H "Content-Type: application/json" \
  -d '{
    "start_station": "广州南",
    "end_station": "深圳北",
    "max_transfers": 2,
    "window_minutes": 120
  }'
```

## 错误处理

### HTTP 状态码

| 状态码 | 说明 | 处理建议 |
|--------|------|----------|
| 200 | 请求成功 | 正常处理响应数据 |
| 400 | 请求参数错误 | 检查请求体格式和参数值 |
| 404 | 资源不存在 | 检查 URL 端点或车站名称 |
| 500 | 服务器内部错误 | 检查服务器日志 |
| 503 | 服务不可用 | 检查数据加载状态 |

### 错误响应格式

```json
{
  "error": "错误描述信息",
  "detail": "详细错误说明（可选）"
}
```

### 常见错误情况

1. **参数缺失** (400 Bad Request):
   ```json
   {
     "error": "起点和终点站不能为空"
   }
   ```

2. **车站不存在** (404 Not Found):
   ```json
   {
     "error": "起点站 \"不存在的站\" 不存在"
   }
   ```

3. **数据未加载** (503 Service Unavailable):
   ```json
   {
     "error": "数据未完全加载"
   }
   ```

## 性能考虑

- **响应时间**: 一般查询 < 2秒，复杂查询 < 5秒
- **并发支持**: 开发环境支持约50个并发请求
- **内存使用**: 服务启动时约占用200MB内存
- **数据缓存**: 所有数据在启动时加载到内存中

## 限制说明

1. **换乘次数**: 最多支持2次换乘
2. **时间窗口**: 默认2小时内的路径方案
3. **车站范围**: 仅支持广东省城际铁路网络内的65个车站
4. **数据更新**: 需要重启服务才能加载更新的时刻表数据
5. **查询限制**: 单次查询返回最多100条路径方案（合并后）

## 版本信息

- **当前版本**: 1.3 (Flask MVP)
- **最后更新**: 2024-12-01
- **兼容性**: Python 3.8+, Flask 2.3+
- **支持协议**: HTTP/1.1

## 技术支持

如有技术问题或建议，请联系：

- **项目维护者**: Fomalhuat
- **邮箱**: leizicung@163.com
- **文档更新**: 定期更新以反映 API 变更

---

*本文档最后更新时间: 2024-12-01*