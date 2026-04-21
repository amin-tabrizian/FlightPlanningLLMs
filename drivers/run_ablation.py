"""Ablation driver: 75 scenarios x 3 preferences x 3 conditions = 675 runs per model.

Assumes the DB has already been seeded by run_warmup.py. Uses --no_store so the DB
is read-only during ablation. Runs tasks in parallel; each task writes to a private
temp CSV that the driver merges into a single per-model aggregate CSV.
"""
import argparse
import csv
import os
import subprocess
import sys
import tempfile
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

_ROOT = Path(__file__).resolve().parent.parent

DEFAULT_POLYGONS = ["poly1", "poly4", "poly7"]
ORIGINS = [f"Origin{i}" for i in range(1, 6)]
DESTS = [f"Destination{i}" for i in range(1, 6)]

PREFERENCES = [
    ("distance", "Minimize total flight distance."),
    ("waypoints", "Minimize the number of waypoints — keep the path as simple as possible."),
    ("clearance", "Maximize clearance from hazardous polygons."),
]

CONDITIONS = [
    ("baseline", []),
    ("rag", ["--rag", "2"]),
    ("rag_coach", ["--rag_coach", "2"]),
]


def run_one(task):
    cmd = task["cmd"]
    tmp = tempfile.NamedTemporaryFile(mode="w", suffix=".csv", delete=False)
    tmp.close()
    cmd = cmd + ["--report_file", tmp.name]
    r = subprocess.run(cmd, capture_output=True, text=True)
    row = None
    try:
        if os.path.getsize(tmp.name) > 0:
            rows = list(csv.DictReader(open(tmp.name)))
            if rows:
                row = rows[0]
    except FileNotFoundError:
        pass
    finally:
        try:
            os.unlink(tmp.name)
        except OSError:
            pass
    if row is not None:
        row["_preference_key"] = task["pref_key"]
        row["_condition"] = task["condition"]
    err = r.stderr[-400:] if r.returncode != 0 else ""
    return task, r.returncode, row, err


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("model")
    ap.add_argument("--polygons", nargs="+", default=DEFAULT_POLYGONS)
    ap.add_argument("--kml_path", default="dataset.kml")
    ap.add_argument("--report_file", default=None, help="default: results/ablation_<model>.csv")
    ap.add_argument("--out_dir", default=None, help="default: runs_ablation/<model>")
    ap.add_argument("--workers", type=int, default=4)
    args = ap.parse_args()

    os.chdir(_ROOT)

    safe_model = args.model.replace("/", "_")
    report = args.report_file or f"results/ablation_{safe_model}.csv"
    out_dir = args.out_dir or f"runs_ablation/{safe_model}"
    prompt_log = f"results/prompts_ablation_{safe_model}.jsonl"
    os.makedirs(out_dir, exist_ok=True)
    os.makedirs(os.path.dirname(report), exist_ok=True)
    for stale in (report, prompt_log):
        if os.path.exists(stale):
            os.remove(stale)

    tasks = []
    for poly in args.polygons:
        for orig in ORIGINS:
            for dest in DESTS:
                for pref_key, pref_text in PREFERENCES:
                    for cond_name, cond_flags in CONDITIONS:
                        tag = f"{poly}_{orig}_{dest}_{pref_key}_{cond_name}"
                        img = f"{out_dir}/{tag}.png"
                        out = f"{out_dir}/{tag}.kml"
                        cmd = [
                            sys.executable, "main.py", args.model, args.kml_path,
                            poly, orig, dest,
                            "--image_path", img,
                            "--output_path", out,
                            "--prompt_log", prompt_log,
                            "--human_preference", pref_text,
                            "--no_store",
                        ] + cond_flags
                        tasks.append({
                            "cmd": cmd,
                            "tag": tag,
                            "pref_key": pref_key,
                            "condition": cond_name,
                        })

    total = len(tasks)
    print(f"Ablation: {total} tasks, workers={args.workers}")
    print(f"Report: {report}")

    t0 = time.time()
    failed = 0
    writer = None
    agg_fh = open(report, "w", newline="")
    try:
        with ThreadPoolExecutor(max_workers=args.workers) as ex:
            futures = [ex.submit(run_one, t) for t in tasks]
            for i, fut in enumerate(as_completed(futures), 1):
                task, code, row, err = fut.result()
                status = "OK " if code == 0 else "FAIL"
                if code != 0:
                    failed += 1
                    log_path = f"{out_dir}/{task['tag']}.err.log"
                    with open(log_path, "w") as lf:
                        lf.write(err)
                if row is not None:
                    if writer is None:
                        writer = csv.DictWriter(agg_fh, fieldnames=list(row.keys()))
                        writer.writeheader()
                    writer.writerow(row)
                    agg_fh.flush()
                elapsed = time.time() - t0
                eta = elapsed / i * (total - i)
                print(f"[{i:4d}/{total}] {status} {task['tag']}  (elapsed {elapsed:6.1f}s, ETA {eta:6.1f}s)")
    finally:
        agg_fh.close()

    print(f"\nAblation done. {total - failed}/{total} passed. Report: {report}")
    if failed:
        sys.exit(1)


if __name__ == "__main__":
    main()
