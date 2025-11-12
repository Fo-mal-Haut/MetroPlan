#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""交路可视化与统计：
读取 service_list.json 与 schedule_list.json：
- 为每条交路统计：首班(first_departure)、末班(last_departure)、平均间隔(avg_interval)、车次数量(train_count)
- 生成 metrics JSON: service_metrics.json
- 可选生成图表：train_count 柱状图与平均间隔柱状图（若 matplotlib 可用）

用法：
  python visualize_services.py \
      --services ../service_list.json \
      --schedule ../schedule_list.json \
      --out-json ../service_metrics.json \
      --out-dir ../visualizations
"""
from __future__ import annotations

import argparse
import json
import re
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional

_TIME_RE = re.compile(r"^\d{1,2}:\d{2}$")


def parse_time_to_minutes(t: str) -> Optional[int]:
    if not isinstance(t, str):
        return None
    t = t.strip()
    if not _TIME_RE.match(t):
        return None
    h, m = t.split(":")
    return int(h) * 60 + int(m)


def minutes_to_str(mins: float) -> str:
    if mins is None:
        return ""
    mins_int = int(round(mins))
    h = mins_int // 60
    m = mins_int % 60
    return f"{h:02d}:{m:02d}" if h < 24 else f">=24h({mins_int}m)"


def load_trains(schedule: Dict[str, Any]) -> Dict[str, Dict[str, Any]]:
    trains = schedule.get("train")
    if not isinstance(trains, list):
        raise ValueError("schedule_list.json 缺少 'train' 列表")
    mapping: Dict[str, Dict[str, Any]] = {}
    for tr in trains:
        if not isinstance(tr, dict):
            continue
        tid = (tr.get("id") or "").strip()
        if not tid:
            continue
        mapping[tid] = tr
    return mapping


def get_departure_time(train_obj: Dict[str, Any]) -> Optional[str]:
    # stations 列表第一个元素的时间即起点发车时间（已在前面处理过忽略首行逻辑）
    stations = train_obj.get("stations") or train_obj.get("station")
    if not isinstance(stations, list) or not stations:
        return None
    first = stations[0]
    if not isinstance(first, dict):
        return None
    t = first.get("time")
    if isinstance(t, str) and _TIME_RE.match(t.strip()):
        return t.strip()
    return None


def compute_metrics(services: List[Dict[str, Any]], train_map: Dict[str, Dict[str, Any]]) -> List[Dict[str, Any]]:
    results: List[Dict[str, Any]] = []
    for svc in services:
        train_ids = svc.get("train")
        if not isinstance(train_ids, list):
            continue
        times: List[int] = []
        raw_times: List[str] = []
        for tid in train_ids:
            tr = train_map.get(tid)
            if not tr:
                continue
            dep = get_departure_time(tr)
            if dep:
                mm = parse_time_to_minutes(dep)
                if mm is not None:
                    times.append(mm)
                    raw_times.append(dep)
        times_sorted = sorted(times)
        first_dep = minutes_to_str(times_sorted[0]) if times_sorted else ""
        last_dep = minutes_to_str(times_sorted[-1]) if times_sorted else ""
        avg_interval_min: Optional[float] = None
        if len(times_sorted) >= 2:
            span = times_sorted[-1] - times_sorted[0]
            avg_interval_min = span / (len(times_sorted) - 1) if span >= 0 else None
        metrics = {
            "id": svc.get("id"),
            "start_station": svc.get("start_station"),
            "end_station": svc.get("end_station"),
            "is_fast": svc.get("is_fast"),
            "train_count": len(train_ids),
            "first_departure": first_dep,
            "last_departure": last_dep,
            "avg_interval_minutes": round(avg_interval_min, 2) if avg_interval_min is not None else None,
            "avg_interval_str": minutes_to_str(avg_interval_min) if avg_interval_min is not None else "",
        }
        results.append(metrics)
    return results


def try_plot(metrics: List[Dict[str, Any]], out_dir: Path) -> None:
    try:
        import matplotlib.pyplot as plt  # type: ignore
        plt.rcParams['font.family'] = 'Microsoft YaHei'  # 替换为你选择的字体
    except Exception:
        print("[图表] matplotlib 不可用，跳过可视化生成。可使用 'pip install matplotlib' 安装后重试。")
        return

    out_dir.mkdir(parents=True, exist_ok=True)

    # 柱状图：车次数量
    labels = [m["id"] for m in metrics]
    counts = [m["train_count"] for m in metrics]
    fig, ax = plt.subplots(figsize=(max(8, len(labels)*0.2), 6))
    ax.bar(range(len(labels)), counts, color="#4e79a7")
    ax.set_ylabel("Train Count")
    ax.set_title("Train Count per Service")
    ax.set_xticks(range(len(labels)))
    ax.set_xticklabels(labels, rotation=90, fontsize=6)
    fig.tight_layout()
    fig.savefig(out_dir / "service_train_count.png", dpi=150)
    plt.close(fig)

    # 柱状图：平均间隔
    intervals = [m["avg_interval_minutes"] if m["avg_interval_minutes"] is not None else 0 for m in metrics]
    fig, ax = plt.subplots(figsize=(max(8, len(labels)*0.2), 6))
    ax.bar(range(len(labels)), intervals, color="#f28e2b")
    ax.set_ylabel("Avg Interval (min)")
    ax.set_title("Average Interval per Service")
    ax.set_xticks(range(len(labels)))
    ax.set_xticklabels(labels, rotation=90, fontsize=6)
    fig.tight_layout()
    fig.savefig(out_dir / "service_avg_interval.png", dpi=150)
    plt.close(fig)

    print(f"[图表] 已生成图像文件于 {out_dir}")


def main():
    parser = argparse.ArgumentParser(description="交路可视化与统计脚本")
    parser.add_argument("--services", default="service_list.json", help="交路文件路径 (默认: service_list.json)")
    parser.add_argument("--schedule", default="schedule_list.json", help="完整车次文件路径 (默认: schedule_list.json)")
    parser.add_argument("--out-json", default="service_metrics.json", help="输出统计 JSON 路径 (默认: service_metrics.json)")
    parser.add_argument("--out-dir", default="visualizations", help="图表输出目录 (默认: visualizations)")
    args = parser.parse_args()

    services_path = Path(args.services)
    schedule_path = Path(args.schedule)
    if not services_path.exists() or not schedule_path.exists():
        raise FileNotFoundError("services 或 schedule 文件不存在")

    services_data = json.loads(services_path.read_text(encoding="utf-8"))
    schedule_data = json.loads(schedule_path.read_text(encoding="utf-8"))

    services_list = services_data.get("service")
    if not isinstance(services_list, list):
        raise ValueError("service_list.json 缺少 'service' 列表")

    train_map = load_trains(schedule_data)
    metrics = compute_metrics(services_list, train_map)

    out_json_path = Path(args.out_json)
    out_json_path.write_text(json.dumps({"service_metrics": metrics}, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"[统计] 已写出统计 JSON: {out_json_path} (服务数: {len(metrics)})")

    try_plot(metrics, Path(args.out_dir))


if __name__ == "__main__":
    main()
