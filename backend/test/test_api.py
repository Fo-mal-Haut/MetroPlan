#!/usr/bin/env python3
"""Test script for Railway Path Finding API"""

import json
import time
import sys
import urllib.request
import urllib.error

BASE_URL = "http://localhost:5000"

def http_get(url, timeout=5):
    """Simple HTTP GET helper"""
    try:
        req = urllib.request.Request(url)
        with urllib.request.urlopen(req, timeout=timeout) as response:
            return response.status, json.loads(response.read().decode('utf-8'))
    except urllib.error.HTTPError as e:
        body = json.loads(e.read().decode('utf-8'))
        return e.code, body
    except Exception as e:
        raise e

def http_post(url, data, timeout=30):
    """Simple HTTP POST helper"""
    try:
        json_data = json.dumps(data).encode('utf-8')
        req = urllib.request.Request(
            url, 
            data=json_data,
            headers={'Content-Type': 'application/json'}
        )
        with urllib.request.urlopen(req, timeout=timeout) as response:
            return response.status, json.loads(response.read().decode('utf-8'))
    except urllib.error.HTTPError as e:
        body = json.loads(e.read().decode('utf-8'))
        return e.code, body
    except Exception as e:
        raise e

def test_health():
    """Test /health endpoint"""
    print("\n" + "="*60)
    print("TEST 1: /health endpoint")
    print("="*60)
    try:
        status, result = http_get(f"{BASE_URL}/health")
        print(f"Status: {status}")
        print(json.dumps(result, indent=2, ensure_ascii=False))
        return status == 200
    except Exception as e:
        print(f"❌ Error: {e}")
        return False


def test_stations():
    """Test /stations endpoint"""
    print("\n" + "="*60)
    print("TEST 2: /stations endpoint")
    print("="*60)
    try:
        status, result = http_get(f"{BASE_URL}/stations")
        print(f"Status: {status}")
        print(f"Total stations: {result.get('count', 0)}")
        stations = result.get('stations', [])
        print(f"Stations (first 20): {stations[:20]}")
        return status == 200
    except Exception as e:
        print(f"❌ Error: {e}")
        return False


def test_path_basic():
    """Test /path endpoint with basic query"""
    print("\n" + "="*60)
    print("TEST 3: /path endpoint - Basic Query (琶洲 → 西平西)")
    print("="*60)
    try:
        payload = {
            "start": "琶洲",
            "end": "西平西",
            "max_transfers": 2,
            "window_minutes": 120
        }
        print(f"Request: {json.dumps(payload, ensure_ascii=False, indent=2)}")
        status, result = http_post(f"{BASE_URL}/path", payload)
        print(f"Status: {status}")
        
        print(f"\nStart: {result.get('start_station')}")
        print(f"End: {result.get('end_station')}")
        
        summary = result.get('summary', {})
        print(f"\nSummary:")
        print(f"  Raw paths: {summary.get('raw_path_count')}")
        print(f"  Filtered paths: {summary.get('filtered_path_count')}")
        print(f"  Merged paths: {summary.get('merged_path_count')}")
        print(f"  Fastest time: {summary.get('fastest_minutes')} minutes")
        print(f"  Window: {summary.get('window_minutes')} minutes")
        print(f"  Skipped same-station transfers: {summary.get('skipped_same_station_transfers')}")
        
        paths = result.get('paths', [])
        print(f"\nFound {len(paths)} paths:")
        for i, path in enumerate(paths[:5], 1):
            print(f"\n  Path {i}:")
            print(f"    Type: {path.get('type')}")
            print(f"    Trains: {path.get('train_sequence')}")
            print(f"    Departure: {path.get('departure_time')}")
            print(f"    Arrival: {path.get('arrival_time')}")
            print(f"    Duration: {path.get('total_time')}")
            print(f"    Transfers: {path.get('transfer_count')}")
        
        if len(paths) > 5:
            print(f"\n  ... and {len(paths) - 5} more paths")
        
        return status == 200 and len(paths) > 0
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_path_invalid_station():
    """Test /path endpoint with invalid station"""
    print("\n" + "="*60)
    print("TEST 4: /path endpoint - Invalid Station")
    print("="*60)
    try:
        payload = {
            "start": "InvalidStation",
            "end": "西平西"
        }
        print(f"Request: {json.dumps(payload, ensure_ascii=False, indent=2)}")
        status, result = http_post(f"{BASE_URL}/path", payload)
        print(f"Status: {status}")
        print(json.dumps(result, indent=2, ensure_ascii=False))
        return status == 400
    except Exception as e:
        print(f"❌ Error: {e}")
        return False


def test_path_missing_params():
    """Test /path endpoint with missing parameters"""
    print("\n" + "="*60)
    print("TEST 5: /path endpoint - Missing Parameters")
    print("="*60)
    try:
        payload = {
            "start": "琶洲"
        }
        print(f"Request: {json.dumps(payload, ensure_ascii=False, indent=2)}")
        status, result = http_post(f"{BASE_URL}/path", payload)
        print(f"Status: {status}")
        print(json.dumps(result, indent=2, ensure_ascii=False))
        return status == 400
    except Exception as e:
        print(f"❌ Error: {e}")
        return False


def test_path_different_route():
    """Test /path endpoint with different route"""
    print("\n" + "="*60)
    print("TEST 6: /path endpoint - Different Route (飞霞 → 肇庆)")
    print("="*60)
    try:
        payload = {
            "start": "飞霞",
            "end": "肇庆",
            "max_transfers": 2,
            "window_minutes": 180
        }
        print(f"Request: {json.dumps(payload, ensure_ascii=False, indent=2)}")
        status, result = http_post(f"{BASE_URL}/path", payload)
        print(f"Status: {status}")
        
        print(f"\nStart: {result.get('start_station')}")
        print(f"End: {result.get('end_station')}")
        
        summary = result.get('summary', {})
        print(f"\nSummary:")
        print(f"  Raw paths: {summary.get('raw_path_count')}")
        print(f"  Filtered paths: {summary.get('filtered_path_count')}")
        print(f"  Merged paths: {summary.get('merged_path_count')}")
        print(f"  Fastest time: {summary.get('fastest_minutes')} minutes")
        
        paths = result.get('paths', [])
        print(f"\nFound {len(paths)} paths (showing first 5):")
        for i, path in enumerate(paths[:5], 1):
            print(f"\n  Path {i}:")
            print(f"    Trains: {path.get('train_sequence')}")
            print(f"    Time: {path.get('departure_time')} - {path.get('arrival_time')}")
            print(f"    Duration: {path.get('total_time')}")
        
        return status == 200
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """Run all tests"""
    print("\n" + "="*60)
    print("Railway Path Finding API - Test Suite")
    print("="*60)
    print(f"Base URL: {BASE_URL}")
    
    # Wait for server to be ready
    print("\nWaiting for server to be ready...")
    for i in range(10):
        try:
            status, _ = http_get(f"{BASE_URL}/health")
            print("✓ Server is ready!")
            break
        except:
            if i < 9:
                time.sleep(1)
                print(".", end="", flush=True)
            else:
                print("\n❌ Server not responding after 10 seconds!")
                sys.exit(1)
    
    results = {}
    
    results['health'] = test_health()
    results['stations'] = test_stations()
    results['path_basic'] = test_path_basic()
    results['path_invalid'] = test_path_invalid_station()
    results['path_missing'] = test_path_missing_params()
    results['path_different'] = test_path_different_route()
    
    # Summary
    print("\n" + "="*60)
    print("Test Summary")
    print("="*60)
    passed = sum(1 for v in results.values() if v)
    total = len(results)
    
    for test_name, passed_flag in results.items():
        status = "✅ PASS" if passed_flag else "❌ FAIL"
        print(f"{status}: {test_name}")
    
    print(f"\nTotal: {passed}/{total} tests passed")
    
    if passed == total:
        print("\n🎉 All tests passed!")
        return 0
    else:
        print(f"\n⚠️ {total - passed} test(s) failed")
        return 1


if __name__ == '__main__':
    sys.exit(main())
