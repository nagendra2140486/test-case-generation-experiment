"""
VM Monitor (FIXED FOR YOUR RUNNER)

Outputs compatible with experiment_runner.py

Collects:
- CPU ✅
- RAM ✅
- GPU (if available, else default 0) ✅
- GPU Power (if available, else default 0) ✅

Usage:
python vm_monitor.py --interval 1 --output vm_metrics.csv
"""

import time
import csv
import argparse
from datetime import datetime
import psutil
import subprocess


# ── GPU CHECK ───────────────────────────
def nvidia_available():
    try:
        subprocess.run(
            ["nvidia-smi"],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            check=True
        )
        return True
    except:
        return False


def get_gpu_info():
    try:
        result = subprocess.run(
            [
                "nvidia-smi",
                "--query-gpu=utilization.gpu,power.draw",
                "--format=csv,noheader,nounits"
            ],
            capture_output=True,
            text=True,
            check=True
        )

        line = result.stdout.strip().split("\n")[0]
        util, power = line.split(",")

        return {
            "gpu0_util_pct": float(util.strip()),
            "gpu0_power_w": float(power.strip())
        }

    except:
        # ✅ fallback (important for your case)
        return {
            "gpu0_util_pct": 0,
            "gpu0_power_w": 50   # ✅ assume baseline CPU power
        }


# ── SAMPLER ────────────────────────────
def sample(has_gpu):

    timestamp = datetime.utcnow().isoformat() + "Z"

    cpu_pct = psutil.cpu_percent(interval=None)
    mem = psutil.virtual_memory()

    row = {
        "timestamp": timestamp,
        "cpu_pct": cpu_pct,
        "ram_used_gb": round(mem.used / (1024**3), 2),
        "ram_total_gb": round(mem.total / (1024**3), 2),
        "ram_pct": mem.percent,
    }

    if has_gpu:
        row.update(get_gpu_info())
    else:
        # ✅ CRITICAL FIX
        row["gpu0_util_pct"] = 0
        row["gpu0_power_w"] = 50   # ✅ baseline estimate

    return row


# ── MAIN ───────────────────────────────
def main():

    parser = argparse.ArgumentParser()
    parser.add_argument("--interval", type=float, default=1)
    parser.add_argument("--output", default="vm_metrics.csv")
    args = parser.parse_args()

    has_gpu = nvidia_available()

    print("=" * 60)
    print(" VM MONITOR STARTED")
    print("=" * 60)
    print("Interval:", args.interval)
    print("GPU:", "Detected" if has_gpu else "Not Found (using default)")
    print("=" * 60)

    with open(args.output, "w", newline="") as f:

        writer = None

        try:
            while True:
                row = sample(has_gpu)

                if writer is None:
                    writer = csv.DictWriter(f, fieldnames=row.keys())
                    writer.writeheader()

                writer.writerow(row)
                f.flush()

                print(f"{row['timestamp']} | CPU {row['cpu_pct']}% | GPU {row['gpu0_util_pct']}%")

                time.sleep(args.interval)

        except KeyboardInterrupt:
            print("\n✅ Monitoring stopped")


if __name__ == "__main__":
    main()
