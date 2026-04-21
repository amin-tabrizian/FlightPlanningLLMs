"""Warmup driver: 75 scenarios x {no-coach, coach} = 150 runs per model.

Populates the RAG DB for one model. Run AFTER resetting the DB and BEFORE ablation.
"""
import argparse
import os
import subprocess
import sys
import time
from pathlib import Path

_ROOT = Path(__file__).resolve().parent.parent

WARMUP_PREF = "Propose the best flight plan from origin to destination avoiding hazardous polygons."

# 1 easy + 1 medium + 1 hard polygon set. Override with --polygons to change the picks.
DEFAULT_POLYGONS = ["poly1", "poly4", "poly7"]
ORIGINS = [f"Origin{i}" for i in range(1, 6)]
DESTS = [f"Destination{i}" for i in range(1, 6)]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("model")
    ap.add_argument("--polygons", nargs="+", default=DEFAULT_POLYGONS)
    ap.add_argument("--kml_path", default="dataset.kml")
    ap.add_argument("--report_file", default=None, help="default: results/warmup_<model>.csv")
    ap.add_argument("--out_dir", default=None, help="default: runs_warmup/<model>")
    args = ap.parse_args()

    os.chdir(_ROOT)

    safe_model = args.model.replace("/", "_")
    report = args.report_file or f"results/warmup_{safe_model}.csv"
    out_dir = args.out_dir or f"runs_warmup/{safe_model}"
    prompt_log = f"results/prompts_warmup_{safe_model}.jsonl"
    os.makedirs(out_dir, exist_ok=True)
    os.makedirs(os.path.dirname(report), exist_ok=True)
    for stale in (report, prompt_log):
        if os.path.exists(stale):
            os.remove(stale)

    tasks = []
    for poly in args.polygons:
        for orig in ORIGINS:
            for dest in DESTS:
                for coach_flag in (False, True):
                    tag = f"{poly}_{orig}_{dest}_{'coach' if coach_flag else 'nocoach'}"
                    tasks.append((poly, orig, dest, coach_flag, tag))

    total = len(tasks)
    failed = 0
    t0 = time.time()
    for i, (poly, orig, dest, coach_flag, tag) in enumerate(tasks, 1):
        img = f"{out_dir}/{tag}.png"
        out = f"{out_dir}/{tag}.kml"
        cmd = [
            sys.executable, "main.py", args.model, args.kml_path,
            poly, orig, dest,
            "--image_path", img,
            "--output_path", out,
            "--report_file", report,
            "--prompt_log", prompt_log,
            "--human_preference", WARMUP_PREF,
        ]
        if coach_flag:
            cmd.append("--coach")
        r = subprocess.run(cmd, capture_output=True, text=True)
        status = "OK " if r.returncode == 0 else "FAIL"
        if r.returncode != 0:
            failed += 1
            log_path = f"{out_dir}/{tag}.err.log"
            with open(log_path, "w") as f:
                f.write(r.stdout + "\n" + r.stderr)
        elapsed = time.time() - t0
        eta = elapsed / i * (total - i)
        print(f"[{i:3d}/{total}] {status} {tag}  (elapsed {elapsed:6.1f}s, ETA {eta:6.1f}s)")

    print(f"\nWarmup done. {total - failed}/{total} passed. Report: {report}")
    if failed:
        sys.exit(1)


if __name__ == "__main__":
    main()
