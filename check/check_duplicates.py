import os
import sys
from pathlib import Path

# Add parent directory to path to import md_to_json
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from data_processing.md_to_json import parse_markdown_table, _is_empty_time

def check_duplicates_and_length(folder_path):
    folder = Path(folder_path)
    md_files = sorted(folder.glob("*.md"))
    
    print(f"Scanning {len(md_files)} files in '{folder_path}'...\n")
    
    first_occurrence = True
    
    for md_path in md_files:
        print(f"Checking file: {md_path.name}")
        try:
            text = md_path.read_text(encoding='utf-8')
        except Exception as e:
            print(f"  Error reading file: {e}")
            continue
            
        headers, data_rows = parse_markdown_table(text)
        if not headers:
            print("  No headers found.")
            continue
            
        # Find all columns with S4802
        train_id = "S4802"
        
        # Check first row (often contains IDs)
        first_row = data_rows[0] if data_rows else []
        
        found_indices = []
        
        # Check in first data row
        for i, cell in enumerate(first_row):
            if train_id in cell:
                found_indices.append(('row0', i))
                
        # Check in headers if not found (fallback logic in md_to_json)
        # But md_to_json iterates over ALL columns and checks both.
        # Let's simulate md_to_json's extraction loop to see what it finds.
        
        header_fallback_ids = headers[1:]
        top_row = data_rows[0] if len(data_rows) > 0 else []
        data_rows_body = data_rows[1:] if len(data_rows) > 1 else []
        station_order = [r[0].strip() for r in data_rows_body]
        
        for offset, header_id in enumerate(header_fallback_ids, start=1):
            tid = ""
            if offset < len(top_row):
                tid = (top_row[offset] or "").strip()
            if not tid:
                tid = (header_id or "").strip()
            
            if tid == train_id:
                # Found S4802
                stops = []
                for r_index, r in enumerate(data_rows_body):
                    cell = r[offset] if offset < len(r) else ""
                    if not _is_empty_time(cell):
                        stops.append((r_index, station_order[r_index], cell.strip()))
                
                start_st = stops[0][1] if stops else "None"
                end_st = stops[-1][1] if stops else "None"
                print(f"  FOUND {train_id} at column {offset}: {len(stops)} stops. ({start_st} -> {end_st})")
                
                if first_occurrence:
                    print("  ^^^ THIS IS THE ONE KEPT BY md_to_json.py ^^^")
                    first_occurrence = False

if __name__ == "__main__":
    check_duplicates_and_length("车次信息")
