# Flask API 创建和调试总结

## 📋 项目背景
这个项目是为一个**铁路换乘查询系统**开发的 REST API 后端。

### 核心需求
- 将已有的 DFS 路径查询算法包装为 REST API
- 提供两个主要端点：
  - `GET /stations` - 获取所有可用车站列表
  - `POST /path` - 查询两站间的换乘方案
  - `GET /health` - 健康检查

---

## ✅ Flask 应用创建过程

### 1. **架构设计** (`backend/app.py`)

#### 核心特性：
```
启动时加载数据 → 缓存到全局变量 → 处理 API 请求
```

#### 数据加载流程：
```python
load_data()
├── 加载 fast_graph.json (4018 节点, 16031 边)
├── 加载 schedule_with_directionality.json (242 辆列车)
├── 加载 directionality_map (方向向量)
└── 提取全部车站列表 (65 个车站)
```

#### 三个 API 端点：

| 端点 | 方法 | 功能 | 返回值 |
|------|------|------|--------|
| `/health` | GET | 健康检查 | `{status, data_loaded}` |
| `/stations` | GET | 车站列表 | `{stations[], count}` |
| `/path` | POST | 路径查询 | `{paths[], summary, metadata}` |

---

### 2. **核心端点实现**

#### `/path` 端点的处理流程：

```
POST /path
  ↓
验证请求 JSON (start, end)
  ↓
检查车站是否存在
  ↓
调用 find_all_paths() DFS 算法
  ↓
按 time_window 过滤 (最快时间 + window_minutes)
  ↓
按总时间排序
  ↓
按列车序列合并相同路径
  ↓
返回 JSON 结果
```

#### 响应格式示例：
```json
{
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
      "is_fast": true
    }
  ],
  "summary": {
    "raw_path_count": 923,
    "fastest_minutes": 33,
    "filtered_path_count": 54,
    "merged_path_count": 34,
    "skipped_same_station_transfers": 5
  }
}
```

---

## 🐛 调试过程中遇到的问题

### 问题 1：**依赖缺失 - requests 库**
**症状：** 
```
ModuleNotFoundError: No module named 'requests'
```

**原因：** 
- 原始测试脚本使用了 `requests` 库，但该库未在 Conda 环境中安装
- Conda 源配置问题导致无法安装

**解决方案：**
- 使用 Python 标准库 `urllib.request` 重写所有网络请求
- 避免第三方依赖，提高可靠性

**改进代码：**
```python
# ❌ 原始（依赖 requests）
response = requests.post(url, json=payload)

# ✅ 改进（使用标准库）
import urllib.request
req = urllib.request.Request(
    url, 
    data=json.dumps(payload).encode('utf-8'),
    headers={'Content-Type': 'application/json'}
)
with urllib.request.urlopen(req) as response:
    result = json.loads(response.read().decode('utf-8'))
```

---

### 问题 2：**Flask 应用导入错误**

**症状：** 
```python
sys.path.insert(0, str(Path(__file__).parent.parent / "DFS_PathFinding"))
from find_paths_dfs import (...)
```
这样的相对路径导入在不同工作目录下可能失败

**原因：**
- Windows 路径分隔符问题
- 工作目录不同导致相对路径解析差异

**解决方案：**
- 使用 `Path` 对象确保跨平台兼容性
- 添加调试输出查看实际加载的文件路径

**改进代码：**
```python
from pathlib import Path
import sys

# 明确指定父目录路径
sys.path.insert(0, str(Path(__file__).parent.parent / "DFS_PathFinding"))

# 在 load_data() 中添加调试信息
print(f"Loading graph from {GRAPH_FILE}")  # 显示实际路径
print(f"Loaded {len(_graph_nodes)} nodes, {len(_graph_edges)} edges")
```

---

### 问题 3：**PowerShell 命令兼容性**

**症状：**
```
错误: 无效语法。默认选项不允许超过 '1' 次。
```

**原因：**
- Windows PowerShell 中 `timeout` 命令语法与 Unix 不同
- `tail` 命令在 Windows 上不存在

**解决方案：**
- 避免使用 Unix 特定命令（`timeout`, `tail`, `head`）
- 改用 PowerShell 原生命令或 Python 内置功能

**错误示例：**
```powershell
# ❌ 错误：Windows timeout 命令语法不同
timeout 60 python backend/test_api.py

# ✅ 正确：使用 Python 时间延迟
python test_quick.py  # 脚本内部用 time.sleep()
```

---

### 问题 4：**Flask 服务器连接超时**

**症状：**
```
urllib.error.URLError: <urlopen error [WinError 10061] 由于目标计算机积极拒绝，无法连接。>
```

**原因：**
- Flask 开发服务器启动时的初始化延迟（数据加载耗时）
- 测试脚本连接超时时间设置过短（2秒）
- localhost vs 127.0.0.1 绑定问题

**调试过程：**
1. **第一次启动：** 应用似乎在 `Press CTRL+C to quit` 处卡住
   - 实际上是在加载数据，需要等待更长时间

2. **添加调试信息：**
```python
def load_data():
    global _graph_nodes, _graph_edges, ...
    
    try:
        print(f"Loading graph from {GRAPH_FILE}")
        _graph_nodes, _graph_edges = load_graph(GRAPH_FILE)
        _adjacency = build_adjacency(_graph_nodes, _graph_edges)
        
        print(f"Loading schedule from {SCHEDULE_FILE}")
        _train_info = load_schedule(SCHEDULE_FILE)
        
        # ... 更多加载步骤 ...
        
        print(f"Loaded {len(_graph_nodes)} nodes, {len(_graph_edges)} edges")
        print(f"Found {len(_all_stations)} unique stations")
        return True
    except Exception as e:
        print(f"Error loading data: {e}")
        return False
```

3. **延长测试脚本的等待时间：**
```python
print("Waiting 5 seconds for server to fully initialize...")
time.sleep(5)  # ✅ 增加初始化时间
```

---

### 问题 5：**全局变量缓存陷阱**

**症状：**
测试脚本创建多个版本时，需要确保全局变量正确初始化

**解决方案：**
```python
# 全局变量声明和初始化
_graph_nodes = None
_graph_edges = None
_adjacency = None
_train_info = None
_direction_map = None
_all_stations = None

def load_data():
    """Load graph and schedule data into memory."""
    global _graph_nodes, _graph_edges, _adjacency, _train_info, _direction_map, _all_stations
    
    try:
        # ... 加载逻辑 ...
        return True
    except Exception as e:
        print(f"Error loading data: {e}")
        return False

# 启动时必须调用
if __name__ == '__main__':
    if not load_data():
        print("Failed to load data. Exiting.")
        sys.exit(1)
```

---

## 📊 创建的文件总结

### 1. **`backend/app.py`** (239 行)
- 核心 Flask 应用
- 包含所有路由处理
- 数据加载和缓存逻辑

### 2. **`backend/requirements.txt`**
```
Flask==2.3.3
Flask-CORS==4.0.0
```

### 3. **`backend/README.md`** (完整文档)
- API 端点说明
- 请求/响应示例
- 使用 Python/JavaScript/cURL 的示例
- 配置说明

### 4. **`backend/test_api.py`** (257 行)
- 完整的测试套件
- 6 个测试用例：
  1. `/health` 端点
  2. `/stations` 端点
  3. `/path` 基础查询
  4. 无效车站错误处理
  5. 缺少参数错误处理
  6. 不同路线查询

### 5. **`test_quick.py`** (快速测试)
- 简化版本
- 使用标准库 `urllib`
- 4 个核心测试用例

---

## 🎯 最终状态验证

✅ **成功验证的部分：**
```
Loading graph from F:\Exploration\MetroPlan\graph\fast_graph.json
Loaded directionality for 242 trains
Loaded 4018 nodes, 16031 edges
Loaded 242 trains
Found 65 unique stations
Starting Flask server on http://127.0.0.1:5000
✅ Flask routes: ['/static/<path:filename>', '/health', '/stations', '/path']
```

**服务器启动参数：**
```python
if __name__ == '__main__':
    if not load_data():
        print("Failed to load data. Exiting.")
        sys.exit(1)
    
    print("Starting Flask server on http://0.0.0.0:5000")
    app.run(host='0.0.0.0', port=5000, debug=False)
```

---

## 🚀 使用方式

### 启动服务器
```bash
cd f:\Exploration\MetroPlan
python backend\app.py
```

### 运行测试
```bash
# 完整测试
python backend\test_api.py

# 快速测试
python test_quick.py
```

### 示例 API 调用
```bash
# 健康检查
curl http://localhost:5000/health

# 获取车站列表
curl http://localhost:5000/stations

# 查询路径
curl -X POST http://localhost:5000/path \
  -H "Content-Type: application/json" \
  -d '{"start": "琶洲", "end": "西平西", "max_transfers": 2, "window_minutes": 120}'
```

---

## 📈 下一步改进方向

### 1. **性能优化**
- 添加请求缓存（Redis）
- 异步处理长查询（Celery）
- 数据库持久化而非内存加载

### 2. **生产部署**
- 使用 Gunicorn/uWSGI 替代开发服务器
- 添加 Nginx 反向代理
- 配置 SSL/HTTPS

### 3. **监控和日志**
- 整合 logging 模块
- 添加性能指标（响应时间）
- 请求日志记录

### 4. **前端集成**
- 添加 CORS 预检请求支持
- WebSocket 支持（实时更新）
- Vue.js 前端集成

### 5. **文档自动化**
- 集成 Swagger/OpenAPI
- 自动生成 API 文档
- 交互式 API 测试界面

---

## 🎓 关键学习点

| 问题 | 解决方案 | 适用场景 |
|------|--------|---------|
| 第三方库依赖 | 使用标准库实现 | 简单网络请求 |
| 路径兼容性 | 使用 `Path` 对象 | 跨平台开发 |
| 命令行兼容性 | 避免 Unix 特定命令 | Windows 环境 |
| 数据加载延迟 | 增加等待时间 + 调试输出 | 重型初始化 |
| 全局状态管理 | 显式声明 global + 返回值验证 | Flask 应用 |

