import json
import sys
from datetime import datetime
from pathlib import Path
from find_paths import find_paths


def log(msg: str):
    ts = datetime.now().strftime("%H:%M:%S")
    line = f"[{ts}] {msg}"
    print(line, flush=True)
    # 同时写到日志文件，便于排查环境下无 stdout 的情况
    (SCRIPT_DIR / "run_samples.log").write_text(
        ((SCRIPT_DIR / "run_samples.log").read_text(encoding="utf-8") if (SCRIPT_DIR / "run_samples.log").exists() else "")
        + line + "\n",
        encoding="utf-8",
    )


SCRIPT_DIR = Path(__file__).parent.resolve()
GRAPH_PATH = (SCRIPT_DIR / "../graph/timetable_graph.json").resolve()

# cases = [
#     ("飞霞", "惠州北", "06:00", SCRIPT_DIR / "paths_fx_hzb_0600.json"),
#     ("飞霞", "惠州北", "08:00", SCRIPT_DIR / "paths_fx_hzb_0800.json"),
#     ("肇庆", "惠州北", "06:00", SCRIPT_DIR / "paths_zq_hzb_0600.json"),
#     ("惠州北", "飞霞", "06:00", SCRIPT_DIR / "paths_hzb_fx_0600.json"),
# ]

cases = [
    ("西平西", "琶洲", "06:00", SCRIPT_DIR / "paths_xpx_pz_0600.json"),
]

def main():
    log(f"SCRIPT_DIR={SCRIPT_DIR}")
    log(f"GRAPH_PATH={GRAPH_PATH}")
    if not GRAPH_PATH.exists():
        log("ERROR: timetable_graph.json 不存在，请先生成图。")
        sys.exit(1)

    for s, t, dep, out_path in cases:
        try:
            log(f"开始案例: {s}->{t} 出发 {dep}")
            paths = find_paths(
                start_station=s,
                end_station=t,
                dep_time_str=dep,
                graph_path=GRAPH_PATH,
                max_paths=10,
                max_transfers=2,
                min_transfer_min=3,
            )
            Path(out_path).write_text(json.dumps(paths, ensure_ascii=False, indent=2), encoding="utf-8")
            log(f"完成: {s}->{t} {dep}: {len(paths)} paths -> {out_path}")
        except Exception as e:
            log(f"ERROR in case {s}->{t} {dep}: {e}")


if __name__ == "__main__":
    main()
