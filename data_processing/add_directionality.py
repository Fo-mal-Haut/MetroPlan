#!/usr/bin/env python3
"""Add directionality vector to schedule JSON using line definitions.

This script reads a line definition file (line_list.json) and a schedule file
(schedule_list.json or similar) and outputs a new schedule file where each
train/service has a `directionality` vector. Each element corresponds to the
line order in line_list.json and has values:
    0 = does not pass through the line
    1 = travels in the same direction as the line (index ascending)
 -1 = travels in the reverse direction (index descending)

Usage:
    py -3 data_processing/add_directionality.py \
        --line line_list.json --schedule schedule_list.json --output schedule_with_dir.json

Options:
  --ambiguous_strategy: how to resolve mixed directions on a line:
      0 = mark as 0 (ambiguous)
      1 = majority vote (default)
      2 = use first segment direction (first non-zero delta)
  --dry-run: do not write output, just print a summary/log
"""
from __future__ import annotations

import argparse
import json
import re
from collections import defaultdict
from copy import deepcopy
from pathlib import Path
from typing import Dict, List, Tuple, Any


def normalize_station_name(name: str) -> str:
    if not name:
        return ""
    # Remove parentheses content like (城际) (& variances), and day notes
    s = re.sub(r"\(.*?\)|（.*?）", "", name)
    # Remove extra whitespace and unusual characters
    s = s.strip()
    s = s.replace('\u00A0', ' ')
    return s


def build_line_index(line_file: Path) -> Tuple[List[Dict[str, Any]], Dict[str, List[Tuple[int,int]]]]:
    with line_file.open('r', encoding='utf-8') as f:
        data = json.load(f)
    lines = data.get('lines', [])

    # station_name_normalized -> list of (line_index, pos)
    station_to_positions: Dict[str, List[Tuple[int,int]]] = defaultdict(list)
    for li, line in enumerate(lines):
        for pos, st in enumerate(line.get('stations', [])):
            name = st.get('station_name') or st.get('name') or ''
            key = normalize_station_name(name)
            if key:
                station_to_positions[key].append((li, pos))
    return lines, station_to_positions


def compute_direction_for_line(indices: List[int], strategy: int) -> int:
    # indices is the list of positions on this line in sequence of service stops
    if not indices or len(indices) < 2:
        return 0
    deltas = [indices[i+1] - indices[i] for i in range(len(indices)-1) if indices[i+1] != indices[i]]
    if not deltas:
        return 0
    pos = sum(1 for d in deltas if d > 0)
    neg = sum(1 for d in deltas if d < 0)
    if pos > 0 and neg == 0:
        return 1
    if neg > 0 and pos == 0:
        return -1
    # Mixed directions
    if strategy == 0:
        return 0
    if strategy == 1:
        if pos > neg:
            return 1
        if neg > pos:
            return -1
        return 0
    if strategy == 2:
        for d in deltas:
            if d > 0:
                return 1
            if d < 0:
                return -1
        return 0
    # default fallback
    return 0


def add_directionality_to_schedule(lines: List[Dict[str, Any]], station_index: Dict[str, List[Tuple[int,int]]], schedule_file: Path, out_file: Path, strategy: int=1, dry_run: bool=False) -> Dict[str, Any]:
    with schedule_file.open('r', encoding='utf-8') as f:
        data = json.load(f)

    trains = data.get('train', [])
    lines_count = len(lines)
    unmatched_total = 0
    ambiguous_counts = 0

    for tr in trains:
        # Build station normalized list
        st_list = [normalize_station_name(s.get('name') or '') for s in tr.get('stations', [])]
        # Per line, gather indices seen in service order
        line_indices: Dict[int, List[int]] = {i: [] for i in range(lines_count)}

        for st in st_list:
            if not st:
                continue
            pos_pairs = station_index.get(st, [])
            if not pos_pairs:
                unmatched_total += 1
                continue
            for (li, pos) in pos_pairs:
                line_indices[li].append(pos)

        dir_vector = [0] * lines_count
        notes = {}
        for li in range(lines_count):
            indices = line_indices.get(li, [])
            if len(indices) == 0:
                dir_vector[li] = 0
                continue
            # Collapse consecutive duplicates (service may include same pos twice if round trip), but don't reorder
            clean_indices: List[int] = [indices[0]]
            for v in indices[1:]:
                if v != clean_indices[-1]:
                    clean_indices.append(v)
            dir_val = compute_direction_for_line(clean_indices, strategy)
            dir_vector[li] = dir_val
            if dir_val == 0 and len(clean_indices) >= 2:
                notes[str(li)] = {
                    'status': 'ambiguous',
                    'indices': clean_indices
                }
                ambiguous_counts += 1

        tr['directionality'] = dir_vector
        if notes:
            tr.setdefault('_direction_notes', {})
            tr['_direction_notes'].update(notes)

    out = deepcopy(data)
    out['_direction_meta'] = {
        'lines_count': lines_count,
        'lines': [(li.get('line_id'), li.get('line_name')) for li in lines],
        'unmatched_total': unmatched_total,
        'ambiguous_counts': ambiguous_counts
    }

    if dry_run:
        return out

    out_file.write_text(json.dumps(out, ensure_ascii=False, indent=2), encoding='utf-8')
    return out


def main():
    parser = argparse.ArgumentParser(description='Add directionality vector to schedule JSON using line definitions.')
    parser.add_argument('--line', default='line_list.json', help='Path to line_list.json')
    parser.add_argument('--schedule', default='schedule_list.json', help='Path to schedule JSON file to modify')
    parser.add_argument('--output', default='schedule_with_directionality.json', help='Output file path')
    parser.add_argument('--ambiguous_strategy', type=int, default=1, choices=[0,1,2], help='0: mark ambiguous as 0; 1: majority vote; 2: use first non-zero delta')
    parser.add_argument('--dry-run', action='store_true', help='Do not write output, only return data')

    args = parser.parse_args()

    line_file = Path(args.line)
    schedule_file = Path(args.schedule)
    out_file = Path(args.output)

    print(f"Reading line file {line_file} and schedule {schedule_file}")
    lines, station_index = build_line_index(line_file)
    res = add_directionality_to_schedule(lines, station_index, schedule_file, out_file, strategy=args.ambiguous_strategy, dry_run=args.dry_run)

    print(f"Processed {len(res.get('train', []))} trains. Lines: {len(lines)}")
    print(f"Unmatched station occurrences: {res.get('_direction_meta',{}).get('unmatched_total')}")
    print(f"Ambiguous determinations: {res.get('_direction_meta',{}).get('ambiguous_counts')}")


if __name__ == '__main__':
    main()
