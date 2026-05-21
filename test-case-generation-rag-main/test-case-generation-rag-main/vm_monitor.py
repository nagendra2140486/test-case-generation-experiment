"""
VM Monitor (Windows + Linux compatible)

Collects:
- CPU
- RAM
- GPU utilization (if NVIDIA available)
- GPU power

Output:
    python vm_monitor.py --interval 2 --output vm_metrics.csv
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
                "--query-gpu=utilization.gpu,memory.used,memory.total,temperature.gpu,power.draw",
                "--format=csv,noheader,nounits"
            ],
            capture_output=True,
            text=True,
            check=True
        )

        line = result.stdout.strip().split("\n")[0]
        parts = [p.strip() for p in line.split(",")]

        return {
            "gpu_util_pct": float(parts[0]),
            "gpu_mem_used_mb": float(parts[1]),
            "gpu_mem_total_mb": float(parts[2]),
            "gpu_temp_c": float(parts[3]),
            "gpu_power_w": float(parts[4]),
        }

    except:
        return {
            "gpu_util_pct": "",
            "gpu_mem_used_mb": "",
            "gpu_mem_total_mb": "",
            "gpu_temp_c": "",
            "gpu_power_w": "",
        }


# ── SAMPLER ────────────────────────────
def sample(has_gpu):

    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

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
        gpu = get_gpu_info()
        row.update(gpu)

    return row


# ── SUMMARY ────────────────────────────
def print_summary(rows):

    if not rows:
        return

    def avg(key):
        vals = [float(r[key]) for r in rows if r[key] != ""]
        return round(sum(vals)/len(vals), 2) if vals else 0

    def peak(key):
        vals = [float(r[key]) for r in rows if r[key] != ""]
        return max(vals) if vals else 0

    print("\n" + "="*60)
    print(" VM MONITOR SUMMARY")
    print("="*60)

    print(f"CPU Avg: {avg('cpu_pct')}%   Peak: {peak('cpu_pct')}%")
    print(f"RAM Avg: {avg('ram_pct')}%   Peak: {peak('ram_pct')}%")

    if "gpu_util_pct" in rows[0]:
        print(f"GPU Avg: {avg('gpu_util_pct')}%   Peak: {peak('gpu_util_pct')}%")
        print(f"GPU Power Avg: {avg('gpu_power_w')} W")

    print("="*60)


# ── MAIN ───────────────────────────────
# ── MAIN ───────────────────────────────
def main():

    parser = argparse.ArgumentParser()
    parser.add_argument("--interval", type=float, default=2)
    parser.add_argument("--output", default="vm_metrics.csv")

    args = parser.parse_args()

    has_gpu = nvidia_available()

    print("=" * 60)
    print("  VM Monitor Started")
    print("=" * 60)
    print(f"  Interval : {args.interval}s")
    print(f"  Output   : {args.output}")
    print(f"  GPU      : {'Detected' if has_gpu else 'Not found'}")
    print("=" * 60)

    rows = []

    try:
        with open(args.output, "w", newline="") as f:
            writer = None

            while True:
                row = sample(has_gpu)
                rows.append(row)

                # ✅ initialize CSV writer once
                if writer is None:
                    writer = csv.DictWriter(f, fieldnames=row.keys())
                    writer.writeheader()

                writer.writerow(row)
                f.flush()

                # ✅ console log
                msg = f"{row['timestamp']} | CPU {row['cpu_pct']}% | RAM {row['ram_pct']}%"

                if has_gpu and row.get("gpu_util_pct") not in ("", None):
                    msg += f" | GPU {row['gpu_util_pct']}% | Power {row['gpu_power_w']}W"

                print(msg)

                time.sleep(args.interval)

    except KeyboardInterrupt:
        print("\n✅ Monitoring stopped by user")

    # ✅ summary after stop
    print_summary(rows)


if __name__ == "__main__":
    main()

