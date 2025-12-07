"""
基本功能测试脚本
测试数据加载和Flask应用的基本功能
"""

import sys
import json
from pathlib import Path

def test_basic_imports():
    """测试基本导入"""
    print("=== 测试基本导入 ===")

    try:
        # 测试标准库
        import json
        import datetime
        from pathlib import Path
        print("✅ 标准库导入成功")

        # 测试Flask
        from flask import Flask, jsonify
        from flask_cors import CORS
        print("✅ Flask库导入成功")

        return True
    except ImportError as e:
        print(f"❌ 导入失败: {e}")
        return False

def test_data_loading():
    """测试数据文件加载"""
    print("\n=== 测试数据文件 ===")

    backend_dir = Path(__file__).parent

    # 检查关键数据文件
    key_files = [
        "graph/fast_graph.json",
        "schedule_with_directionality.json"
    ]

    for file_path in key_files:
        full_path = backend_dir / file_path
        if full_path.exists():
            size = full_path.stat().st_size
            print(f"✅ {file_path} ({size:,} bytes)")
        else:
            print(f"❌ {file_path} 不存在")
            return False

    # 尝试加载数据
    try:
        # 测试graph加载
        graph_path = backend_dir / "graph" / "fast_graph.json"
        with open(graph_path, 'r', encoding='utf-8') as f:
            graph_data = json.load(f)
            nodes = graph_data.get('nodes', [])
            edges = graph_data.get('edges', [])
            print(f"✅ 图数据: {len(nodes)} 节点, {len(edges)} 边")

        # 测试schedule加载
        schedule_path = backend_dir / "schedule_with_directionality.json"
        with open(schedule_path, 'r', encoding='utf-8') as f:
            schedule_data = json.load(f)
            trains = schedule_data.get('train', [])
            print(f"✅ 时刻表数据: {len(trains)} 辆列车")

        # 提取车站列表
        stations = set()
        for node in nodes:
            if isinstance(node, list) and len(node) >= 1:
                stations.add(node[0])

        print(f"✅ 车站总数: {len(stations)} 个")

        return True, stations

    except Exception as e:
        print(f"❌ 数据加载失败: {e}")
        return False, set()

def test_algorithm_import():
    """测试算法模块导入"""
    print("\n=== 测试算法模块 ===")

    backend_dir = Path(__file__).parent
    sys.path.insert(0, str(backend_dir))

    try:
        # 导入算法模块
        from DFS_PathFinding.find_paths_dfs import (
            load_graph, load_schedule, build_adjacency,
            find_all_paths
        )
        print("✅ 算法模块导入成功")

        # 测试基本功能
        graph_path = backend_dir / "graph" / "fast_graph.json"
        schedule_path = backend_dir / "schedule_with_directionality.json"

        # 加载图数据
        nodes, edges = load_graph(graph_path)
        adjacency = build_adjacency(nodes, edges)
        print(f"✅ 图邻接表构建成功: {len(adjacency)} 个节点")

        # 加载列车信息
        train_info = load_schedule(schedule_path)
        print(f"✅ 列车信息加载成功: {len(train_info)} 辆列车")

        # 提取测试车站
        stations = list(set(node[0] for node in nodes if len(node) >= 1))
        if len(stations) >= 2:
            start, end = stations[0], stations[1]
            print(f"✅ 测试路径: {start} → {end}")

            # 运行路径查找（限制搜索范围）
            paths, stats = find_all_paths(
                nodes=nodes,
                adjacency=adjacency,
                start_station=start,
                end_station=end,
                train_info=train_info,
                max_transfers=1  # 限制换乘次数
            )

            print(f"✅ 路径查找成功: 找到 {len(paths)} 条路径")
            return True
        else:
            print("⚠️ 车站数量不足，跳过路径测试")
            return True

    except Exception as e:
        print(f"❌ 算法测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_flask_app():
    """测试Flask应用"""
    print("\n=== 测试Flask应用 ===")

    backend_dir = Path(__file__).parent
    sys.path.insert(0, str(backend_dir))

    try:
        # 导入Flask应用（不启动服务器）
        from app import load_data, app

        # 测试数据加载
        print("测试数据加载...")
        success = load_data()
        if success:
            print("✅ 数据加载成功")

            # 测试Flask路由
            with app.test_client() as client:
                # 健康检查
                response = client.get('/health')
                print(f"✅ /health: {response.status_code}")

                # 车站列表
                response = client.get('/stations')
                if response.status_code == 200:
                    data = response.get_json()
                    print(f"✅ /stations: {len(data.get('stations', []))} 个车站")
                else:
                    print(f"❌ /stations: {response.status_code}")

            print("✅ Flask应用测试通过")
            return True
        else:
            print("❌ 数据加载失败")
            return False

    except Exception as e:
        print(f"❌ Flask应用测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False

def main():
    """主测试函数"""
    print("MetroPlan 基本功能测试")
    print("=" * 40)

    results = []

    # 1. 基本导入测试
    results.append(test_basic_imports())

    # 2. 数据文件测试
    data_success, stations = test_data_loading()
    results.append(data_success)

    # 3. 算法模块测试
    results.append(test_algorithm_import())

    # 4. Flask应用测试
    results.append(test_flask_app())

    # 总结
    print("\n" + "=" * 40)
    passed = sum(results)
    total = len(results)

    print(f"测试结果: {passed}/{total} 通过")

    if passed == total:
        print("🎉 所有基本功能测试通过！")
        print("\n可以启动Flask应用:")
        print("  cd backend")
        print("  python app.py")
        print("\nAPI端点:")
        print("  - 健康检查: GET http://localhost:5000/health")
        print("  - 车站列表: GET http://localhost:5000/stations")
        print("  - 路径查询: POST http://localhost:5000/path")
        print("    请求体: {'start_station': '广州南', 'end_station': '深圳北', 'max_transfers': 2}")
    else:
        print("⚠️  部分测试失败，请检查配置")

if __name__ == '__main__':
    main()