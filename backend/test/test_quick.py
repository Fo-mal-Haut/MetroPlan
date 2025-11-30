#!/usr/bin/env python3
"""Quick API test"""
import urllib.request
import json
import time
import sys

BASE_URL = "http://localhost:5000"

print("Waiting 5 seconds for server to fully initialize...")
time.sleep(5)

# Test 1: Health check
print("\n" + "="*50)
print("TEST 1: /health endpoint")
print("="*50)
try:
    with urllib.request.urlopen(f"{BASE_URL}/health") as resp:
        result = json.loads(resp.read().decode())
        print(f"✅ Status: {resp.status}")
        print(json.dumps(result, indent=2, ensure_ascii=False))
except Exception as e:
    print(f"❌ Error: {e}")
    sys.exit(1)

# Test 2: Stations endpoint
print("\n" + "="*50)
print("TEST 2: /stations endpoint")
print("="*50)
try:
    with urllib.request.urlopen(f"{BASE_URL}/stations") as resp:
        result = json.loads(resp.read().decode())
        print(f"✅ Status: {resp.status}")
        print(f"Found {result['count']} stations")
        print(f"First 10 stations: {result['stations'][:10]}")
except Exception as e:
    print(f"❌ Error: {e}")
    sys.exit(1)

# Test 3: Path query
print("\n" + "="*50)
print("TEST 3: /path - Basic Query (琶洲 → 西平西)")
print("="*50)
try:
    payload = json.dumps({
        "start": "琶洲",
        "end": "西平西",
        "max_transfers": 2,
        "window_minutes": 120
    }).encode('utf-8')
    
    req = urllib.request.Request(
        f"{BASE_URL}/path",
        data=payload,
        headers={'Content-Type': 'application/json'}
    )
    
    with urllib.request.urlopen(req) as resp:
        result = json.loads(resp.read().decode())
        print(f"✅ Status: {resp.status}")
        print(f"Start: {result['start_station']}")
        print(f"End: {result['end_station']}")
        
        summary = result.get('summary', {})
        print(f"\nSummary:")
        print(f"  Raw paths: {summary['raw_path_count']}")
        print(f"  Filtered paths: {summary['filtered_path_count']}")
        print(f"  Merged paths: {summary['merged_path_count']}")
        print(f"  Fastest time: {summary['fastest_minutes']} minutes")
        print(f"  Window: {summary['window_minutes']} minutes")
        
        paths = result['paths']
        print(f"\nFound {len(paths)} paths (top 3):")
        for i, path in enumerate(paths[:3], 1):
            print(f"\n  Path {i}:")
            print(f"    Trains: {path['train_sequence']}")
            print(f"    Time: {path['departure_time']} → {path['arrival_time']} ({path['total_time']})")
            print(f"    Transfers: {path['transfer_count']}")
except Exception as e:
    print(f"❌ Error: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

# Test 4: Error handling
print("\n" + "="*50)
print("TEST 4: /path - Invalid Station")
print("="*50)
try:
    payload = json.dumps({
        "start": "InvalidStation",
        "end": "西平西"
    }).encode('utf-8')
    
    req = urllib.request.Request(
        f"{BASE_URL}/path",
        data=payload,
        headers={'Content-Type': 'application/json'}
    )
    
    try:
        with urllib.request.urlopen(req) as resp:
            print(f"❌ Should have returned 400, got {resp.status}")
    except urllib.error.HTTPError as e:
        result = json.loads(e.read().decode())
        print(f"✅ Status: {e.code} (expected)")
        print(f"Error: {result['error']}")
except Exception as e:
    print(f"❌ Error: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

print("\n" + "="*50)
print("🎉 All tests passed!")
print("="*50)
