"""
MetroPlan Flask API 快速测试

简化的API测试，用于快速验证基本功能
运行方式：cd backend && python test/test_quick.py
"""

import sys
import json
import time
from pathlib import Path

# 添加backend目录到Python路径
backend_path = Path(__file__).parent.parent
sys.path.insert(0, str(backend_path))

# 直接测试app函数，不需要启动服务器
from app import load_data, app
from DFS_PathFinding.find_paths_dfs import load_graph, load_schedule, find_all_paths

# Flask测试客户端
from flask.testing import FlaskClient


def test_data_loading():
    """测试数据加载功能"""
    print("=== 测试数据加载 ===")

    try:
        success = load_data()
        if success:
            print("✅ 数据加载成功")

            # 检查全局变量
            from app import graph_data, schedule_data, train_info, stations_list, adjacency, nodes

            print(f"  - 图数据: {len(graph_data.get('nodes', []))} 节点, {len(graph_data.get('edges', []))} 边")
            print(f"  - 列车信息: {len(train_info)} 辆列车")
            print(f"  - 车站列表: {len(stations_list)} 个车站")
            print(f"  - 邻接表: {len(adjacency)} 个节点")

            return True
        else:
            print("❌ 数据加载失败")
            return False

    except Exception as e:
        print(f"❌ 数据加载异常: {e}")
        return False


def test_algorithm_directly():
    """直接测试路径规划算法"""
    print("\n=== 直接测试路径规划算法 ===")

    try:
        # 加载必要数据
        from app import FAST_GRAPH_PATH, SCHEDULE_PATH

        nodes, edges = load_graph(FAST_GRAPH_PATH)
        train_info = load_schedule(SCHEDULE_PATH)

        from DFS_PathFinding.find_paths_dfs import build_adjacency, load_directionality_map
        adjacency = build_adjacency(nodes, edges)

        try:
            direction_map = load_directionality_map(SCHEDULE_PATH)
        except:
            direction_map = {}

        # 选择一些车站进行测试
        stations = list(set(node[0] for node in nodes))
        if len(stations) < 2:
            print("❌ 车站数量不足")
            return False

        start_station = stations[0]
        end_station = stations[1] if len(stations) > 1 else stations[0]

        print(f"测试路径: {start_station} → {end_station}")

        # 调用路径查找算法
        all_paths, stats = find_all_paths(
            nodes=nodes,
            adjacency=adjacency,
            start_station=start_station,
            end_station=end_station,
            train_info=train_info,
            direction_map=direction_map,
            max_transfers=2
        )

        print(f"找到 {len(all_paths)} 条路径")

        if all_paths:
            # 显示第一个路径
            first_path = all_paths[0]
            print(f"  最短路径: {first_path.get('departure_time')} → {first_path.get('arrival_time')}")
            print(f"  总时长: {first_path.get('total_time')}")
            print(f"  换乘次数: {first_path.get('transfer_count', 0)}")
            print(f"  车次: {first_path.get('train_sequence', [])}")
            print("✅ 路径规划算法正常")
            return True
        else:
            print("⚠️  未找到路径，但算法执行正常")
            return True

    except Exception as e:
        print(f"❌ 算法测试异常: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_flask_endpoints():
    """测试Flask端点"""
    print("\n=== 测试Flask端点 ===")

    try:
        # 创建测试客户端
        with app.test_client() as client:
            # 测试健康检查
            response = client.get('/health')
            print(f"GET /health: {response.status_code}")

            if response.status_code == 200:
                data = response.get_json()
                print(f"  状态: {data.get('status')}")
                print("✅ /health 端点正常")
                health_success = True
            else:
                print("❌ /health 端点异常")
                health_success = False

            # 测试车站列表
            response = client.get('/stations')
            print(f"GET /stations: {response.status_code}")

            if response.status_code == 200:
                data = response.get_json()
                stations = data.get('stations', [])
                count = data.get('count', 0)
                print(f"  车站数量: {count}")
                print(f"  前5个车站: {stations[:5]}")
                print("✅ /stations 端点正常")
                stations_success = True
            else:
                print("❌ /stations 端点异常")
                stations_success = False

            # 测试路径查询（如果有车站数据）
            path_success = False
            if stations and len(stations) >= 2:
                payload = {
                    'start_station': stations[0],
                    'end_station': stations[1],
                    'max_transfers': 2,
                    'window_minutes': 120
                }

                response = client.post(
                    '/path',
                    data=json.dumps(payload),
                    content_type='application/json'
                )

                print(f"POST /path: {response.status_code}")

                if response.status_code == 200:
                    data = response.get_json()
                    paths = data.get('paths', [])
                    summary = data.get('summary', {})
                    print(f"  路径数量: {summary.get('total_paths', 0)}")
                    print(f"  合并后: {summary.get('merged_paths', 0)}")

                    if paths:
                        print(f"  第一条路径: {paths[0].get('departure_time')} → {paths[0].get('arrival_time')}")

                    print("✅ /path 端点正常")
                    path_success = True
                else:
                    print(f"❌ /path 端点异常: {response.get_data(as_text=True)}")

            return health_success and stations_success and path_success

    except Exception as e:
        print(f"❌ Flask端点测试异常: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_error_cases():
    """测试错误情况"""
    print("\n=== 测试错误情况 ===")

    try:
        with app.test_client() as client:
            error_cases = [
                # 空请求体
                ({}, "空请求体"),
                # 缺少参数
                ({'start_station': '广州'}, "缺少end_station"),
                # 起终点相同
                ({'start_station': '广州', 'end_station': '广州'}, "起终点相同"),
                # 换乘次数过多
                ({'start_station': '广州', 'end_station': '深圳', 'max_transfers': 3}, "换乘次数过多"),
            ]

            success_count = 0

            for payload, description in error_cases:
                response = client.post(
                    '/path',
                    data=json.dumps(payload),
                    content_type='application/json'
                )

                if response.status_code in [400, 404, 500]:
                    print(f"✅ {description}: 正确返回错误 {response.status_code}")
                    success_count += 1
                else:
                    print(f"❌ {description}: 应该返回错误但得到 {response.status_code}")

            print(f"错误测试: {success_count}/{len(error_cases)} 通过")
            return success_count == len(error_cases)

    except Exception as e:
        print(f"❌ 错误测试异常: {e}")
        return False


def main():
    """主测试函数"""
    print("MetroPlan Flask API 快速测试")
    print("=" * 40)

    # 确保数据已加载
    print("1. 测试数据加载...")
    data_ok = test_data_loading()

    if not data_ok:
        print("❌ 数据加载失败，停止后续测试")
        return

    print("2. 测试路径规划算法...")
    algorithm_ok = test_algorithm_directly()

    print("3. 测试Flask端点...")
    endpoints_ok = test_flask_endpoints()

    print("4. 测试错误情况...")
    error_ok = test_error_cases()

    # 总结
    print("\n" + "=" * 40)
    results = [data_ok, algorithm_ok, endpoints_ok, error_ok]
    passed = sum(results)
    total = len(results)

    print(f"测试结果: {passed}/{total} 通过")

    if passed == total:
        print("🎉 所有测试通过！")
        print("Flask API可以启动使用:")
        print("  cd backend && python app.py")
    else:
        print("⚠️  部分测试失败，请检查问题")

    print("\nAPI使用示例:")
    print("- 健康检查: GET http://localhost:5000/health")
    print("- 车站列表: GET http://localhost:5000/stations")
    print("- 路径查询: POST http://localhost:5000/path")
    print("  请求体: {'start_station': '广州南', 'end_station': '深圳北', 'max_transfers': 2}")


if __name__ == '__main__':
    main()