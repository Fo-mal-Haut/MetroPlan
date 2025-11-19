
def check_columns(file_path):
    with open(file_path, 'r', encoding='utf-8') as f:
        lines = f.readlines()
    
    print(f"Checking {file_path}")
    header_pipes = 0
    for i, line in enumerate(lines):
        line = line.strip()
        if not line: continue
        pipe_count = line.count('|')
        
        if i == 1: # Line 2 is header (0-based index 1)
            header_pipes = pipe_count
            print(f"Header (Line {i+1}): {pipe_count} pipes")
            
        if "化龙南" in line or "广州莲花山" in line:
            print(f"Line {i+1} ({line.split('|')[1].strip()}): {pipe_count} pipes")


if __name__ == "__main__":
    check_columns(r"f:\Exploration\MetroPlan\车次信息\惠州北-飞霞.md")
