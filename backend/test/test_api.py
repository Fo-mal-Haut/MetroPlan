"""
MetroPlan Flask API 测试用例

测试Flask API的各个端点：
- /health 健康检查
- /stations 车站列表
- /path 路径查询

运行方式：
cd backend && python -m pytest test/test_api.py -v
或直接运行：
cd backend && python test/test_api.py
"""

import sys
import json
import time
from pathlib import Path

# 添加backend目录到Python路径
backend_path = Path(__file__).parent.parent
sys.path.insert(0, str(backend_path))

# Flask应用导入
from app import app

# 测试客户端
import requests


def test_health_endpoint():
    """测试健康检查端点"""
    print("\n=== 测试 /health 端点 ===")

    try:
        response = requests.get('http://localhost:5000/health', timeout=10)
        print(f"状态码: {response.status_code}")

        if response.status_code == 200:
            data = response.json()
            print(f"健康状态: {data.get('status')}")
            print(f"数据加载状态: {data.get('data_loaded')}")
            print("✅ /health 端点测试通过")
            return True
        else:
            print(f"❌ /health 端点返回错误: {response.text}")
            return False

    except requests.exceptions.ConnectionError:
        print("❌ 无法连接到Flask服务器，请先启动: python app.py")
        return False
    except Exception as e:
        print(f"❌ /health 端点测试失败: {e}")
        return False


def test_stations_endpoint():
    """测试车站列表端点"""
    print("\n=== 测试 /stations 端点 ===")

    try:
        response = requests.get('http://localhost:5000/stations', timeout=10)
        print(f"状态码: {response.status_code}")

        if response.status_code == 200:
            data = response.json()
            stations = data.get('stations', [])
            count = data.get('count', 0)

            print(f"车站总数: {count}")
            print(f"前10个车站: {stations[:10]}")

            if count > 0 and len(stations) == count:
                print("✅ /stations 端点测试通过")
                return True, stations
            else:
                print("❌ 车站数据不完整")
                return False, []
        else:
            print(f"❌ /stations 端点返回错误: {response.text}")
            return False, []

    except Exception as e:
        print(f"❌ /stations 端点测试失败: {e}")
        return False, []


def test_path_endpoint(start_station, end_station, max_transfers=2, window_minutes=120):
    """测试路径查询端点"""
    print(f"\n=== 测试 /path 端点: {start_station} → {end_station} ===")

    try:
        payload = {
            'start_station': start_station,
            'end_station': end_station,
            'max_transfers': max_transfers,
            'window_minutes': window_minutes
        }

        response = requests.post(
            'http://localhost:5000/path',
            json=payload,
            headers={'Content-Type': 'application/json'},
            timeout=30
        )

        print(f"状态码: {response.status_code}")

        if response.status_code == 200:
            data = response.json()
            paths = data.get('paths', [])
            summary = data.get('summary', {})

            print(f"路径总数: {summary.get('total_paths', 0)}")
            print(f"最短时间: {summary.get('fastest_minutes', 0)} 分钟")
            print(f"过滤后路径: {summary.get('filtered_paths', 0)}")
            print(f"合并后路径: {summary.get('merged_paths', 0)}")

            # 显示前3个路径方案
            for i, path in enumerate(paths[:3]):
                print(f"  路径 {i+1}: {path.get('train_sequence', [])} "
                      f"({path.get('departure_time', '')} → {path.get('arrival_time', '')}, "
                      f"{path.get('total_time', '')}, "
                      f"换乘{path.get('transfer_count', 0)}次)")

            print("✅ /path 端点测试通过")
            return True, data
        else:
            print(f"❌ /path 端点返回错误: {response.text}")
            return False, {}

    except Exception as e:
        print(f"❌ /path 端点测试失败: {e}")
        return False, {}


def test_path_error_cases():
    """测试路径查询的错误情况"""
    print("\n=== 测试 /path 错误情况 ===")

    error_cases = [
        # 缺少参数
        ({}, "缺少start_station和end_station"),
        # 起点为空
        ({'start_station': '', 'end_station': '广州南'}, "起点站为空"),
        # 终点为空
        ({'start_station': '广州南', 'end_station': ''}, "终点站为空"),
        # 起终点相同
        ({'start_station': '广州南', 'end_station': '广州南'}, "起终点相同"),
        # 换乘次数超出范围
        ({'start_station': '广州南', 'end_station': '深圳北', 'max_transfers': 3}, "换乘次数超出范围"),
        # 不存在的车站
        ({'start_station': '不存在的站', 'end_station': '深圳北'}, "起点站不存在"),
        ({'start_station': '广州南', 'end_station': '不存在的站'}, "终点站不存在"),
    ]

    success_count = 0

    for payload, description in error_cases:
        print(f"\n测试错误情况: {description}")
        try:
            response = requests.post(
                'http://localhost:5000/path',
                json=payload,
                headers={'Content-Type': 'application/json'},
                timeout=10
            )

            if response.status_code in [400, 404, 500]:
                print(f"✅ 正确返回错误状态码 {response.status_code}")
                success_count += 1
            else:
                print(f"❌ 应该返回错误但返回了 {response.status_code}")

        except Exception as e:
            print(f"❌ 请求失败: {e}")

    print(f"\n错误情况测试: {success_count}/{len(error_cases)} 通过")
    return success_count == len(error_cases)


def run_performance_test():
    """运行性能测试"""
    print("\n=== 性能测试 ===")

    test_cases = [
        ('广州南', '深圳北'),
        ('广州东', '珠海'),
        ('花都', '肇庆')
    ]

    for start, end in test_cases:
        payload = {
            'start_station': start,
            'end_station': end,
            'max_transfers': 2,
            'window_minutes': 120
        }

        start_time = time.time()
        try:
            response = requests.post(
                'http://localhost:5000/path',
                json=payload,
                headers={'Content-Type': 'application/json'},
                timeout=30
            )
            end_time = time.time()
            duration = end_time - start_time

            if response.status_code == 200:
                data = response.json()
                paths_count = len(data.get('paths', []))
                print(f"{start} → {end}: {duration:.2f}秒, {paths_count}条路径")
            else:
                print(f"{start} → {end}: 请求失败 ({response.status_code})")

        except Exception as e:
            print(f"{start} → {end}: 测试失败: {e}")


def main():
    """主测试函数"""
    print("MetroPlan Flask API 测试开始")
    print("=" * 50)

    # 检查服务器是否启动
    print("检查Flask服务器连接...")
    try:
        response = requests.get('http://localhost:5000/health', timeout=5)
        if response.status_code != 200:
            print("❌ Flask服务器响应异常")
            return
        print("✅ Flask服务器连接正常")
    except requests.exceptions.ConnectionError:
        print("❌ 无法连接到Flask服务器")
        print("请先启动Flask应用: cd backend && python app.py")
        return
    except Exception as e:
        print(f"❌ 连接检查失败: {e}")
        return

    # 运行基础测试
    results = []

    # 1. 健康检查
    results.append(test_health_endpoint())

    # 2. 车站列表
    stations_success, stations = test_stations_endpoint()
    results.append(stations_success)

    # 3. 路径查询 (使用一些实际存在的车站)
    if stations and len(stations) >= 4:
        # 选择几个测试车站
        test_stations = stations[:4]
        for i in range(len(test_stations) - 1):
            success, _ = test_path_endpoint(test_stations[i], test_stations[i + 1])
            results.append(success)

        # 测试长距离路径
        if len(stations) >= 10:
            success, _ = test_path_endpoint(stations[0], stations[9])
            results.append(success)

    # 4. 错误情况测试
    error_test_success = test_path_error_cases()
    results.append(error_test_success)

    # 5. 性能测试
    run_performance_test()

    # 总结
    print("\n" + "=" * 50)
    passed_tests = sum(results)
    total_tests = len(results)
    print(f"测试结果: {passed_tests}/{total_tests} 通过")

    if passed_tests == total_tests:
        print("🎉 所有测试通过！Flask API工作正常")
    else:
        print("⚠️  部分测试失败，请检查Flask应用")


if __name__ == '__main__':
    main()