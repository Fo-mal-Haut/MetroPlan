#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""将“车次信息”目录下多个 Markdown 时刻表聚合为一个 schedule_list.json。

使用方法：
        python md_to_json.py --dir "车次信息" --output schedule_list.json

输出：聚合后的单一 JSON 文件，结构：
{
    "train": [
        {
            "id": "车次ID",
            "start_station": "起点站",
            "end_station": "终点站",
            "is_fast": true,
            "stations": [
                {"name": "站名", "time": "HH:MM"},
                ...
            ]
        }, ...
    ]
}

说明：
1. 起点与终点站根据该车次首个和最后一个有时间的站确定。
2. is_fast 判断逻辑：在首末站之间存在未停靠（时间为空）站则为 True，否则 False。
3. 若不同文件出现相同车次 ID，后续重复将被忽略，不再重复统计。
"""
from __future__ import annotations

import argparse
import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import List, Tuple, Dict, Any


def _is_delim_cell(text: str) -> bool:
    """判断是否为表头对齐分隔行里的单元（例如 ---、:---、---:、:---:）。"""
    t = text.strip()
    return re.fullmatch(r':?-{3,}:?', t) is not None


def _split_md_row(line: str) -> List[str]:
    """将 Markdown 表格的一行按 | 切分，并去掉首尾可能的 |。"""
    s = line.strip()
    if not s:
        return []
    if s.startswith("|"):
        s = s[1:]
    if s.endswith("|"):
        s = s[:-1]
    return [c.strip() for c in s.split("|")]


def _is_empty_time(cell: str) -> bool:
    """判断一个单元格是否表示不停靠/无时间。"""
    if cell is None:
        return True
    c = cell.strip()
    if c == "":
        return True
    if c.lower() in {"x", "na", "n/a", "none"}:
        return True
    if all(ch in "-—–~·. " for ch in c):
        return True
    return False


def parse_markdown_table(md_text: str) -> Tuple[List[str], List[List[str]]]:
    """解析 Markdown 表格，返回 (表头列表, 数据行二维数组)。只解析第一张合法表。"""
    lines = md_text.splitlines()
    filtered = []
    in_fence = False
    for ln in lines:
        l = ln.rstrip("\n")
        if l.strip().startswith("```"):
            in_fence = not in_fence
            continue
        if not in_fence:
            filtered.append(l)
    filtered = [l.strip() for l in filtered if l.strip()]

    header_idx = None
    for i in range(len(filtered) - 1):
        if "|" not in filtered[i]:
            continue
        header_cells = _split_md_row(filtered[i])
        if not header_cells:
            continue
        delim_cells = _split_md_row(filtered[i + 1])
        if delim_cells and all(_is_delim_cell(c) for c in delim_cells):
            header_idx = i
            break

    if header_idx is None:
        return [], []

    headers = _split_md_row(filtered[header_idx])
    data_rows: List[List[str]] = []
    for j in range(header_idx + 2, len(filtered)):
        line = filtered[j]
        if "|" not in line:
            continue
        cells = _split_md_row(line)
        if not cells:
            continue
        if len(cells) < len(headers):
            cells += [""] * (len(headers) - len(cells))
        elif len(cells) > len(headers):
            cells = cells[: len(headers)]
        data_rows.append(cells)

    return headers, data_rows


def extract_trains_from_table(headers: List[str], rows: List[List[str]]) -> List[Dict[str, Any]]:
    """从单个 Markdown 表中抽取车次信息，转为统一结构列表。

    返回的列表元素结构：
    {
        "id": str,
        "start_station": str,
        "end_station": str,
        "is_fast": bool,
        "stations": [{"name": str, "time": str}, ...]
    }
    注意：按需求在读取 stations 过程中，忽视 .md 表格数据的第一行（常为“车站/车次”行）。
    """
    if not headers or not rows:
        return []

    station_col = 0
    # 顶部第一行通常包含各列的标识（车次号），按需求将 id 取自这一行
    top_row = rows[0] if len(rows) > 0 else []
    # 读取 stations 时跳过第一行
    data_rows = rows[1:] if len(rows) > 1 else []
    station_order = [r[station_col].strip() for r in data_rows]
    header_fallback_ids = headers[1:]
    result: List[Dict[str, Any]] = []

    for offset, header_id in enumerate(header_fallback_ids, start=1):
        # id 优先取第一行相应列的值；为空则回退到表头文字
        train_id = ""
        if offset < len(top_row):
            train_id = (top_row[offset] or "").strip()
        if not train_id:
            train_id = (header_id or "").strip()
        stops: List[Tuple[int, str, str]] = []  # (row_index, station_name, time)
        for r_index, r in enumerate(data_rows):
            station_name = station_order[r_index]
            cell = r[offset] if offset < len(r) else ""
            if not _is_empty_time(cell):
                stops.append((r_index, station_name, cell.strip()))
        if not stops:
            continue
        start_idx = stops[0][0]
        end_idx = stops[-1][0]
        # 在首末索引之间如果有任何站未出现时间则视为跳站
        full_span_count = end_idx - start_idx + 1
        is_fast = (len(stops) < full_span_count)
        result.append({
            "id": train_id,
            "start_station": station_order[start_idx],
            "end_station": station_order[end_idx],
            "is_fast": is_fast,
            "stations": [{"name": st, "time": t} for (_, st, t) in stops]
        })
    return result


def aggregate_folder(folder: Path, encoding: str, output_path: Path) -> None:
    """扫描目录中的 .md 文件，聚合所有车次为单一 JSON 文件。"""
    if not folder.exists() or not folder.is_dir():
        raise FileNotFoundError(f"目录不存在或不可用: {folder}")

    md_files = sorted(folder.glob("*.md"))
    if not md_files:
        print(f"[信息] 目录中未找到 .md 文件: {folder}")
        return

    print(f"[开始] 聚合 Markdown 时刻表：目录={folder}，文件数={len(md_files)}")
    trains: List[Dict[str, Any]] = []
    id_count: Dict[str, int] = {}
    processed, skipped = 0, 0

    for md_path in md_files:
        try:
            text = md_path.read_text(encoding=encoding)
            headers, data_rows = parse_markdown_table(text)
            if not headers or not data_rows:
                raise ValueError("未识别到有效的 Markdown 表格。")
            extracted = extract_trains_from_table(headers, data_rows)
            unique_added = 0
            for tr in extracted:
                orig_id = tr["id"]
                if orig_id in id_count:
                    # 重复出现：不再追加后缀，不统计，直接跳过
                    continue
                id_count[orig_id] = 1
                trains.append(tr)
                unique_added += 1
            print(f"[文件] {md_path.name} 车次提取 {len(extracted)} 条，新增唯一 {unique_added} 条，跳过重复 {len(extracted) - unique_added} 条")
            processed += 1
        except Exception as e:
            print(f"[跳过] {md_path.name}: {e}")
            skipped += 1

    out_obj = {"train": trains, "generated_at": datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")}
    output_path.write_text(json.dumps(out_obj, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"[完成] 聚合输出 -> {output_path} (总车次:{len(trains)}, 成功文件:{processed}, 跳过文件:{skipped})")


def main():
    parser = argparse.ArgumentParser(description="聚合“车次信息”目录内的 Markdown 时刻表为 schedule_list.json。")
    parser.add_argument("-d", "--dir", default="车次信息", help="包含 .md 时刻表的目录（默认：车次信息）")
    parser.add_argument("--output", default="schedule_list.json", help="输出文件路径（默认：schedule_list.json）")
    parser.add_argument("--encoding", default="utf-8-sig", help="读取 .md 的编码（默认：utf-8-sig，可兼容含 BOM 的文件）")
    args = parser.parse_args()

    folder = Path(args.dir)
    output_path = Path(args.output)
    aggregate_folder(folder, encoding=args.encoding, output_path=output_path)


if __name__ == "__main__":
    main()
