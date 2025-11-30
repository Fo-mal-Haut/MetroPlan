# Flask API 开发总结

## 1. 项目背景

### 需求
将已有的 DFS 路径查询算法包装为 REST API，提供两个主要端点：
- `GET /stations` - 获取所有可用车站列表  
- `POST /path` - 查询两站间的换乘方案  
- `GET /health` - 健康检查  

### 系统架构
```
Request → Flask Router → Validation → DFS Algorithm → Response
                                           ↓
                        (fast_graph.json, schedule_with_directionality.json)
```

---

## 2. Flask 应用创建过程

### 步骤 1: 核心应用文件 (`backend/app.py`)

**主要功能：**
- 启动时加载图数据和列车时刻表（4018 节点，16031 边，242 辆列车）
- 将数据缓存在全局变量，避免重复加载
- 提供 3 个 REST 端点处理用户请求
- 集成 CORS 支持跨域访问

**数据加载流程：**
```
load_data()
  ├─ 加载 fast_graph.json (4018 节点, 16031 边)
  ├─ 构建邻接表 (adjacency)
  ├─ 加载列车时刻表 (242 辆列车)
  ├─ 加载方向向量 (directionality_map)
  └─ 提取 65 个唯一车站
```

### 步骤 2: 依赖配置 (`requirements.txt`)

```
Flask==2.3.3
Flask-CORS==4.0.0
```

### 步骤 3: 完整的 API 文档 (`README.md`)

包含：
- 所有端点的详细说明
- 请求/响应示例
- Python、JavaScript、cURL 使用示例
- 配置和部署说明

---

## 3. 调试过程中遇到的问题

### 问题 1: 依赖缺失 (requests 库)

**症状：**
```
ModuleNotFoundError: No module named 'requests'
```

**原因：**
- 测试脚本使用 `requests` 库，但 Conda 源配置问题导致无法安装
- requests 库不在用户的 Python 环境中

**解决方案：**
- 放弃使用 `requests` 库
- 改用 Python 标准库 `urllib.request` 重写所有网络请求
- 好处：无额外依赖，更轻量，内置支持

**代码改进：**

原始代码（依赖 requests）：
```python
import requests
response = requests.post(url, json=payload, timeout=30)
result = response.json()
```

改进代码（使用标准库）：
```python
import urllib.request
import json

json_data = json.dumps(payload).encode('utf-8')
req = urllib.request.Request(
    url,
    data=json_data,
    headers={'Content-Type': 'application/json'}
)
with urllib.request.urlopen(req, timeout=30) as response:
    result = json.loads(response.read().decode('utf-8'))
```

---

### 问题 2: Windows PowerShell 命令兼容性

**症状：**
```
错误: 无效语法。默认选项不允许超过 '1' 次。
```

**原因：**
- Unix `timeout` 命令与 Windows PowerShell 语法不同
- Unix `tail`、`head` 命令在 Windows 不存在

**示例错误的命令：**
```powershell
# ❌ 错误：Windows timeout 命令有不同的语法
timeout 60 python backend/test_api.py

# ❌ 错误：Windows 没有 tail 命令
python test.py 2>&1 | tail -20
```

**解决方案：**
1. 避免使用 Unix 特定命令
2. 将延迟逻辑移到 Python 脚本内部
3. 用 PowerShell 原生命令替代

**改进的命令：**
```python
# Python 脚本内部处理等待和超时
import time
print("Waiting 5 seconds for server to initialize...")
time.sleep(5)
```

---

### 问题 3: Flask 服务器连接超时

**症状：**
```
urllib.error.URLError: <urlopen error [WinError 10061] 由于目标计算机积极拒绝，无法连接。>
```

**根本原因：**
1. Flask 开发服务器启动需要时间加载 4018 个节点的图数据
2. 测试脚本的连接超时设置过短（原始为 2 秒）
3. 服务器在打印 "Press CTRL+C to quit" 时仍在执行 HTTP 服务初始化

**调试过程：**

步骤 1 - 验证服务器是否真的启动：
```python
# test_import.py
import backend.app
print(f"✅ Flask routes: {[str(r) for r in backend.app.app.url_map.iter_rules()]}")
# 输出: ✅ Flask routes: ['/static/<path:filename>', '/health', '/stations', '/path']
```

步骤 2 - 在 Flask 应用中添加调试输出：
```python
def load_data():
    global _graph_nodes, _graph_edges, ...
    
    try:
        print(f"Loading graph from {GRAPH_FILE}")
        _graph_nodes, _graph_edges = load_graph(GRAPH_FILE)
        _adjacency = build_adjacency(_graph_nodes, _graph_edges)
        
        print(f"Loading schedule from {SCHEDULE_FILE}")
        _train_info = load_schedule(SCHEDULE_FILE)
        
        try:
            _direction_map = load_directionality_map(SCHEDULE_FILE)
            print(f"Loaded directionality for {len(_direction_map)} trains")
        except Exception as e:
            print(f"Warning: Failed to load directionality map: {e}")
            _direction_map = {}
        
        # Extract all unique stations
        stations_set = set()
        for node in _graph_nodes:
            station_name = node[0]
            if station_name:
                stations_set.add(station_name)
        _all_stations = sorted(list(stations_set))
        
        print(f"Loaded {len(_graph_nodes)} nodes, {len(_graph_edges)} edges")
        print(f"Loaded {len(_train_info)} trains")
        print(f"Found {len(_all_stations)} unique stations")
        return True
    except Exception as e:
        print(f"Error loading data: {e}")
        return False
```

步骤 3 - 增加测试脚本中的等待时间：
```python
# test_quick.py
print("Waiting 5 seconds for server to fully initialize...")
time.sleep(5)  # ✅ 增加到 5 秒而不是 2 秒
```

**成功的启动输出：**
```
Loading graph from F:\Exploration\MetroPlan\graph\fast_graph.json
Loading schedule from F:\Exploration\MetroPlan\schedule_with_directionality.json
Loaded directionality for 242 trains
Loaded 4018 nodes, 16031 edges
Loaded 242 trains
Found 65 unique stations
Starting Flask server on http://127.0.0.1:5000
 * Serving Flask app 'app'
 * Debug mode: off
 * Running on http://127.0.0.1:5000
Press CTRL+C to quit
```

---

### 问题 4: 全局变量初始化问题

**症状：**
- Flask 路由处理函数访问全局变量时出现 `None` 值
- `/path` 端点返回 "Data not loaded" 错误

**原因：**
```python
# ❌ 问题代码
_graph_nodes = None

def find_path():
    if not all([_graph_nodes, ...]):  # 如果不调用 load_data()，此检查会失败
        return jsonify({'error': 'Data not loaded'}), 500
```

**解决方案：**
1. 在 `__main__` 块中显式调用 `load_data()`
2. 检查返回值确保成功加载
3. 只在数据成功加载后启动服务器

```python
if __name__ == '__main__':
    if not load_data():
        print("Failed to load data. Exiting.")
        sys.exit(1)
    
    print("Starting Flask server on http://0.0.0.0:5000")
    app.run(host='0.0.0.0', port=5000, debug=False)
```

---

### 问题 5: 路径导入兼容性

**症状：**
在不同工作目录下运行脚本时，模块导入失败

**原因：**
```python
# ❌ 问题代码：相对路径依赖于当前工作目录
sys.path.insert(0, "../DFS_PathFinding")  # 如果工作目录不对会失败
```

**解决方案：**
使用 `Path` 对象计算绝对路径

```python
from pathlib import Path
import sys

# ✅ 改进代码：始终相对于当前文件位置
sys.path.insert(0, str(Path(__file__).parent.parent / "DFS_PathFinding"))
from find_paths_dfs import (
    load_graph,
    load_schedule,
    load_directionality_map,
    build_adjacency,
    find_all_paths,
    merge_paths_by_train_sequence,
)
```

---

## 4. 创建的文件清单

| 文件 | 大小 | 用途 |
|------|------|------|
| `backend/app.py` | 239 行 | 核心 Flask 应用和路由 |
| `backend/requirements.txt` | 2 行 | 依赖列表 |
| `backend/README.md` | ~300 行 | 完整 API 文档 |
| `backend/test_api.py` | 257 行 | 完整测试套件（6 个测试用例） |
| `test_quick.py` | ~110 行 | 简化快速测试 |
| `test_import.py` | 8 行 | 模块导入验证 |
| `FLASK_DEVELOPMENT_SUMMARY.md` | 当前文件 | 开发总结 |

---

## 5. API 端点详解

### GET /health
```json
Response: {
  "status": "healthy",
  "data_loaded": true
}
```

### GET /stations
```json
Response: {
  "stations": ["琶洲", "西平西", "东莞西", ...],
  "count": 65
}
```

### POST /path
```json
Request: {
  "start": "琶洲",
  "end": "西平西",
  "max_transfers": 2,
  "window_minutes": 120,
  "allow_same_station_consecutive_transfers": false
}

Response: {
  "start_station": "琶洲",
  "end_station": "西平西",
  "paths": [
    {
      "id": 1,
      "type": "Direct",
      "train_sequence": ["S4847"],
      "departure_time": "21:33",
      "arrival_time": "22:06",
      "total_time": "0h 33m",
      "total_minutes": 33,
      "transfer_count": 0,
      "is_fast": true,
      "transfer_details": [],
      "transfer_options": []
    }
  ],
  "summary": {
    "raw_path_count": 923,
    "fastest_minutes": 33,
    "window_minutes": 120,
    "filtered_path_count": 54,
    "merged_path_count": 34,
    "skipped_same_station_transfers": 5
  }
}
```

---

## 6. 测试验证

### 已验证成功：
- ✅ 数据加载正确（4018 节点，16031 边，242 列车，65 车站）
- ✅ Flask 路由注册成功（4 条路由）
- ✅ 导入链完整（DFS 模块可正确导入）
- ✅ 服务器启动成功

### 待验证：
需要等待服务器完全初始化后运行以下测试：
```bash
python test_quick.py
```

这会验证：
- [ ] `/health` 端点正常响应
- [ ] `/stations` 端点返回 65 个车站
- [ ] `/path` 端点成功处理路径查询
- [ ] 错误处理正确（无效车站返回 400）

---

## 7. 关键教训

| 问题类型 | 解决方案 | 适用场景 |
|--------|--------|---------|
| 依赖不可用 | 使用标准库替代 | 网络请求、JSON 处理 |
| 跨平台命令 | 避免 Unix 特定命令 | Windows 和 Linux 兼容 |
| 启动延迟 | 增加等待时间 + 调试输出 | 重型初始化（数据加载） |
| 路径问题 | 使用 `Path` 对象 | 跨平台文件访问 |
| 全局状态 | 显式初始化 + 返回值检查 | Flask 应用配置 |

---

## 8. 下一步改进方向

### 短期
- 运行完整的测试套件验证 API
- 添加请求参数验证和错误消息改进
- 集成日志记录功能

### 中期
- 性能优化（缓存频繁查询）
- 集成 Vue 前端
- 添加更多过滤参数

### 长期
- 使用 Gunicorn/uWSGI 部署生产环境
- 添加数据库持久化
- 集成实时查询推荐功能

