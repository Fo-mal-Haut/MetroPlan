import sys
import os
import re

# Add parent directory to path to import md_to_json
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from data_processing.md_to_json import parse_markdown_table, _is_empty_time

def debug_parsing(file_path, train_id):
    with open(file_path, 'r', encoding='utf-8') as f:
        text = f.read()
    
    headers, data_rows = parse_markdown_table(text)
    print(f"Headers length: {len(headers)}")
    print(f"First data row length: {len(data_rows[0]) if data_rows else 0}")
    print(f"Parsed {len(data_rows)} data rows.")
    
    # Find train column
    # The first row of data_rows is usually the train ID row in this project's convention
    if not data_rows:
        print("No data rows found.")
        return

    train_row = data_rows[0]
    col_idx = -1
    for i, cell in enumerate(train_row):
        if train_id in cell:
            col_idx = i
            break
            
    if col_idx == -1:
        print(f"Train {train_id} not found in the first data row.")
        # Try headers just in case
        for i, cell in enumerate(headers):
            if train_id in cell:
                col_idx = i
                break
        if col_idx == -1:
            print("Train not found in headers either.")
            return

    print(f"Train {train_id} found at column index {col_idx}.")
    
    print("\n--- Row Data for Train ---")
    for i, row in enumerate(data_rows):
        station = row[0]
        if col_idx < len(row):
            time_val = row[col_idx]
            is_empty = _is_empty_time(time_val)
            print(f"Row {i}: {station} -> '{time_val}' (Empty: {is_empty})")
        else:
            print(f"Row {i}: {station} -> COLUMN MISSING (len={len(row)})")

if __name__ == "__main__":
    if len(sys.argv) > 2:
        debug_parsing(sys.argv[1], sys.argv[2])
    else:
        debug_parsing('车次信息/惠州北-飞霞.md', 'S4802')
