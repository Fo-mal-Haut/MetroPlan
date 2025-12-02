#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
根据 service_list.json 中的交路快慢属性，更新 line_list.json 中站点的 is_fast。
规则：凡是出现在任意 is_fast=true 的交路的 station 列表里的站点，都标记为 fast 站点（is_fast=true）。
注意：为提升匹配鲁棒性，比较站名时会去除括号内容（支持中英文括号）。

用法：
  python update_line_fast_stations.py \
    --services ../service_list.json \
    --line ../line_list.json \
    --inplace

若未指定 --inplace，则默认输出到同目录的 line_list.updated.json。
"""
from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Any, Dict, List, Set

PAREN_RE = re.compile(r"[（(].*?[）)]")

def normalize_name(name: str) -> str:
    if not isinstance(name, str):
        return ""
    s = PAREN_RE.sub("", name).strip()
    return s


def collect_fast_stations(services: Dict[str, Any]) -> Set[str]:
    fast_names: Set[str] = set()
    svc_list = services.get("service")
    if not isinstance(svc_list, list):
        raise ValueError("service_list.json 缺少 'service' 列表")
    for svc in svc_list:
        if not isinstance(svc, dict):
            continue
        if not bool(svc.get("is_fast", False)):
            continue
        stations = svc.get("station")
        if not isinstance(stations, list):
            continue
        for name in stations:
            if isinstance(name, str):
                fast_names.add(normalize_name(name))
    return fast_names


def update_line_file(line_data: Dict[str, Any], fast_names: Set[str]) -> Dict[str, Any]:
    lines = line_data.get("lines")
    if not isinstance(lines, list):
        raise ValueError("line_list.json 缺少 'lines' 列表")
    changed = 0
    for line in lines:
        stations = line.get("stations")
        if not isinstance(stations, list):
            continue
        for st in stations:
            if not isinstance(st, dict):
                continue
            name = st.get("station_name")
            norm = normalize_name(name or "")
            if norm in fast_names:
                if st.get("is_fast") is not True:
                    st["is_fast"] = True
                    changed += 1
    line_data.setdefault("_fast_update_info", {})
    line_data["_fast_update_info"]["updated_count"] = changed
    return line_data


def main():
    parser = argparse.ArgumentParser(description="根据交路快慢属性更新线路站点 is_fast")
    parser.add_argument("--services", default="service_list.json", help="service_list.json 路径")
    parser.add_argument("--line", default="line_list.json", help="line_list.json 路径")
    parser.add_argument("--inplace", action="store_true", help="原地覆盖 line_list.json")
    args = parser.parse_args()

    services_path = Path(args.services)
    line_path = Path(args.line)
    if not services_path.exists() or not line_path.exists():
        raise FileNotFoundError("services 或 line 文件不存在")

    services_data = json.loads(services_path.read_text(encoding="utf-8"))
    fast_names = collect_fast_stations(services_data)

    line_data = json.loads(line_path.read_text(encoding="utf-8"))
    updated = update_line_file(line_data, fast_names)

    if args.inplace:
        out_path = line_path
    else:
        out_path = line_path.with_name(line_path.stem + ".updated.json")
    out_path.write_text(json.dumps(updated, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"已更新 is_fast 站点，输出: {out_path}，共修改 {updated.get('_fast_update_info',{}).get('updated_count',0)} 处")


if __name__ == "__main__":
    main()
