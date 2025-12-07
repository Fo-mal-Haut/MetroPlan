#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
根据 schedule_list.json 统计交路（service）：
- 按 (start_station, end_station, is_fast) 分组
- 聚合同组内所有车次 id
- 统计每个交路经过的站点 station（按各车次中的平均相对顺序排序）
- 生成输出 service_list.json

用法：
    python generate_service_list.py --input ../schedule_list.json --output ../service_list.json
"""
from __future__ import annotations

import argparse
import json
from collections import defaultdict
from pathlib import Path
from typing import Any, Dict, List, Tuple


def build_services(trains: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    groups: Dict[Tuple[str, str, bool], List[str]] = defaultdict(list)
    # 预构建：车次ID -> 站名列表（保持顺序）
    id_to_stations: Dict[str, List[str]] = {}
    for tr in trains:
        if not isinstance(tr, dict):
            continue
        sid = (tr.get("start_station") or "").strip()
        eid = (tr.get("end_station") or "").strip()
        is_fast = bool(tr.get("is_fast", False))
        tid = (tr.get("id") or "").strip()
        if not sid or not eid:
            continue
        if not tid:
            # 忽略没有 id 的条目
            continue
        groups[(sid, eid, is_fast)].append(tid)
        # 提取站名序列
        stations_list = tr.get("stations") or tr.get("station") or []
        names: List[str] = []
        if isinstance(stations_list, list):
            for s in stations_list:
                if isinstance(s, dict):
                    name = (s.get("name") or "").strip()
                    if name:
                        names.append(name)
        if tid and names:
            id_to_stations[tid] = names

    services: List[Dict[str, Any]] = []
    for (sid, eid, is_fast), ids in groups.items():
        # 去重且保持出现顺序
        seen = set()
        ordered_ids = []
        for x in ids:
            if x not in seen:
                seen.add(x)
                ordered_ids.append(x)
        # 统计交路经过的站点（按平均相对位置排序）
        pos_sum: Dict[str, float] = {}
        pos_cnt: Dict[str, int] = {}
        for tid in ordered_ids:
            seq = id_to_stations.get(tid) or []
            for idx, name in enumerate(seq):
                pos_sum[name] = pos_sum.get(name, 0.0) + idx
                pos_cnt[name] = pos_cnt.get(name, 0) + 1
        # 计算平均位置并排序
        stations_ordered = sorted(pos_sum.keys(), key=lambda n: (pos_sum[n] / max(1, pos_cnt.get(n, 1))))
        services.append({
            "id": f"{sid}__{eid}__{'fast' if is_fast else 'slow'}",
            "start_station": sid,
            "end_station": eid,
            "is_fast": is_fast,
            "train": ordered_ids,
            "station": stations_ordered,
        })

    # 可按 id 或起终点排序，便于稳定输出
    services.sort(key=lambda x: (x["start_station"], x["end_station"], not x["is_fast"], x["id"]))
    return services


def main():
    parser = argparse.ArgumentParser(description="从 schedule_list.json 生成 service_list.json（交路统计）。")
    parser.add_argument("--input", "-i", default="schedule_list.json", help="输入文件（默认：schedule_list.json）")
    parser.add_argument("--output", "-o", default="service_list.json", help="输出文件（默认：service_list.json）")
    args = parser.parse_args()

    in_path = Path(args.input)
    if not in_path.exists():
        raise FileNotFoundError(f"找不到输入文件: {in_path}")

    data = json.loads(in_path.read_text(encoding="utf-8"))
    trains = data.get("train") or []
    if not isinstance(trains, list):
        raise ValueError("输入 JSON 顶层缺少 'train' 列表")

    services = build_services(trains)
    out_obj = {"service": services}

    out_path = Path(args.output)
    out_path.write_text(json.dumps(out_obj, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"已生成: {out_path}（交路数: {len(services)}）")


if __name__ == "__main__":
    main()
