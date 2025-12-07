"""
MetroPlan Flask API Backend

最小可用版本的Flask应用，提供路径规划API服务。
根据架构规范，启动时加载数据到全局变量缓存。

API端点：
- GET /health: 健康检查和数据加载状态
- GET /stations: 获取所有车站列表
- POST /path: 路径查询（支持0-2次换乘）

作者：Fomalhuat
版本：1.3 (Flask MVP)
"""

import json
import os
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime, timezone
import sys

from flask import Flask, request, jsonify
from flask_cors import CORS

# 添加backend目录到Python路径
current_dir = Path(__file__).parent
sys.path.insert(0, str(current_dir))

# 导入路径规划算法
try:
    from DFS_PathFinding.find_paths_dfs import (
        load_graph, load_schedule, load_directionality_map,
        build_adjacency, find_all_paths, merge_paths_by_train_sequence
    )
    print("✅ 成功导入路径规划算法模块")
except ImportError as e:
    print(f"❌ 导入路径规划算法失败: {e}")
    print(f"当前Python路径: {sys.path}")
    sys.exit(1)

# 全局变量缓存数据
graph_data = None
schedule_data = None
train_info = None
directionality_map = None
adjacency = None
nodes = None
stations_list = None

app = Flask(__name__)
CORS(app)  # 启用跨域支持

# 数据文件路径配置
DATA_DIR = Path(__file__).parent
FAST_GRAPH_PATH = DATA_DIR / "graph" / "fast_graph.json"
SCHEDULE_PATH = DATA_DIR / "schedule_with_directionality.json"


def load_data():
    """启动时加载所有必要的数据到全局变量"""
    global graph_data, schedule_data, train_info, directionality_map, adjacency, nodes, stations_list

    try:
        print(f"开始加载数据文件...")

        # 1. 加载fast_graph.json (4018 节点, 16031 边)
        if not FAST_GRAPH_PATH.exists():
            raise FileNotFoundError(f"Fast graph file not found: {FAST_GRAPH_PATH}")

        nodes, edges = load_graph(FAST_GRAPH_PATH)
        adjacency = build_adjacency(nodes, edges)
        print(f"已加载fast_graph: {len(nodes)} 节点, {len(edges)} 边")

        # 2. 加载schedule_with_directionality.json (242 辆列车)
        if not SCHEDULE_PATH.exists():
            raise FileNotFoundError(f"Schedule file not found: {SCHEDULE_PATH}")

        train_info = load_schedule(SCHEDULE_PATH)
        print(f"已加载schedule: {len(train_info)} 辆列车")

        # 3. 加载directionality_map (方向向量)
        try:
            directionality_map = load_directionality_map(SCHEDULE_PATH)
            print(f"已加载directionality_map: {len(directionality_map)} 辆列车有方向信息")
        except Exception as e:
            print(f"警告：无法加载directionality_map: {e}")
            directionality_map = {}

        # 4. 提取全部车站列表 (65 个车站)
        stations_set = set()
        for node in nodes:
            stations_set.add(node[0])  # node[0] 是车站名
        stations_list = sorted(list(stations_set))
        print(f"已提取车站列表: {len(stations_list)} 个车站")

        # 保存原始数据
        graph_data = {'nodes': nodes, 'edges': edges}
        with open(SCHEDULE_PATH, 'r', encoding='utf-8') as f:
            schedule_data = json.load(f)

        print("所有数据加载完成！")
        return True

    except Exception as e:
        print(f"数据加载失败: {e}")
        return False


@app.route('/health', methods=['GET'])
def health_check():
    """健康检查端点"""
    return jsonify({
        'status': 'healthy' if all([
            graph_data, schedule_data, train_info,
            directionality_map is not None, adjacency, nodes, stations_list
        ]) else 'unhealthy',
        'data_loaded': {
            'graph': graph_data is not None,
            'schedule': schedule_data is not None,
            'train_info': train_info is not None,
            'directionality_map': directionality_map is not None,
            'adjacency': adjacency is not None,
            'nodes': nodes is not None,
            'stations_list': stations_list is not None
        },
        'timestamp': datetime.now(timezone.utc).astimezone().isoformat()
    })


@app.route('/stations', methods=['GET'])
def get_stations():
    """获取所有车站列表"""
    if stations_list is None:
        return jsonify({'error': '车站数据未加载'}), 503

    return jsonify({
        'stations': stations_list,
        'count': len(stations_list),
        'timestamp': datetime.now(timezone.utc).astimezone().isoformat()
    })


@app.route('/path', methods=['POST'])
def find_path():
    """路径查询端点"""
    if not all([graph_data, schedule_data, train_info, adjacency, nodes]):
        return jsonify({'error': '数据未完全加载'}), 503

    try:
        # 解析请求参数
        data = request.get_json()
        if not data:
            return jsonify({'error': '请求体格式错误'}), 400

        start_station = data.get('start_station')
        end_station = data.get('end_station')
        max_transfers = data.get('max_transfers', 2)
        window_minutes = data.get('window_minutes', 120)
        allow_same_station_transfers = data.get('allow_same_station_transfers', False)

        # 验证必需参数
        if not start_station or not end_station:
            return jsonify({'error': '起点和终点站不能为空'}), 400

        if start_station == end_station:
            return jsonify({'error': '起点和终点站不能相同'}), 400

        if max_transfers < 0 or max_transfers > 2:
            return jsonify({'error': '换乘次数限制为0-2次'}), 400

        # 验证车站是否存在
        if start_station not in stations_list:
            return jsonify({'error': f'起点站 "{start_station}" 不存在'}), 404
        if end_station not in stations_list:
            return jsonify({'error': f'终点站 "{end_station}" 不存在'}), 404

        # 调用路径规划算法
        all_paths, stats = find_all_paths(
            nodes=nodes,
            adjacency=adjacency,
            start_station=start_station,
            end_station=end_station,
            train_info=train_info,
            direction_map=directionality_map,
            max_transfers=max_transfers,
            allow_same_station_consecutive_transfers=allow_same_station_transfers
        )

        if not all_paths:
            return jsonify({
                'start_station': start_station,
                'end_station': end_station,
                'paths': [],
                'summary': {
                    'total_paths': 0,
                    'message': '在当前约束条件下未找到可行路径'
                },
                'timestamp': datetime.now(timezone.utc).astimezone().isoformat()
            })

        # 过滤和合并路径
        fastest_minutes = min(p['total_minutes'] for p in all_paths)
        cutoff_minutes = fastest_minutes + max(window_minutes, 0)
        filtered_paths = [p for p in all_paths if p['total_minutes'] <= cutoff_minutes]

        # 确保顺序一致后合并
        filtered_paths.sort(key=lambda item: (item['total_minutes'], item['departure_time']))
        merged_paths = merge_paths_by_train_sequence(filtered_paths)

        # 添加路径ID
        for idx, entry in enumerate(merged_paths, start=1):
            entry['id'] = idx

        # 构建返回结果
        result = {
            'start_station': start_station,
            'end_station': end_station,
            'paths': merged_paths,
            'summary': {
                'total_paths': len(all_paths),
                'fastest_minutes': fastest_minutes,
                'window_minutes': window_minutes,
                'filtered_paths': len(filtered_paths),
                'merged_paths': len(merged_paths)
            },
            'metadata': {
                'max_transfers': max_transfers,
                'generated_at': datetime.now(timezone.utc).astimezone().isoformat()
            }
        }

        # 添加统计信息
        if isinstance(stats, dict):
            result['summary'].update(stats)

        return jsonify(result)

    except Exception as e:
        print(f"路径查询错误: {e}")
        return jsonify({
            'error': '路径查询失败',
            'detail': str(e)
        }), 500


@app.errorhandler(404)
def not_found(error):
    return jsonify({'error': '端点不存在'}), 404


@app.errorhandler(500)
def internal_error(error):
    return jsonify({'error': '内部服务器错误'}), 500


if __name__ == '__main__':
    print("MetroPlan Flask API 启动中...")

    # 加载数据
    if load_data():
        print("数据加载成功，启动Flask开发服务器...")
        app.run(host='0.0.0.0', port=5000, debug=True)
    else:
        print("数据加载失败，服务器启动终止")
        sys.exit(1)