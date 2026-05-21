"""
Sustainability Scorer — Path A vs Path B

Reads:
  experiment_results.json (from your test case generator)
  vm_metrics.csv (from vm_monitor)

Outputs:
  comparison_report.json
  terminal summary
"""

import csv
import json
import os
from datetime import datetime, timezone

# ── CONFIG ──────────────────────────────────────────
GRID_CARBON_INTENSITY = 713  # g CO2 per kWh (India approx)

# ── VM METRICS ───────────────────────────────────────
def load_vm_metrics(path):
    if not os.path.exists(path):
        return []

    with open(path) as f:
        return list(csv.DictReader(f))


def parse_ts(s):
    if not s:
        return None
    try:
        return datetime.fromisoformat(s.replace("Z", "+00:00"))
    except:
        return None


def resource_window(vm_rows, start, end):
    t0 = parse_ts(start)
    t1 = parse_ts(end)

    if not t0 or not t1:
        return {}

    window = []

    for row in vm_rows:
        ts = parse_ts(row.get("timestamp"))
        if ts and t0 <= ts <= t1:
            window.append(row)

    if not window:
        return {}

    def get_avg(key):
        vals = []
        for r in window:
            try:
                vals.append(float(r[key]))
            except:
                pass
        return round(sum(vals)/len(vals), 2) if vals else None

    return {
        "cpu_avg_pct": get_avg("cpu_pct"),
        "gpu_avg_pct": get_avg("gpu0_util_pct"),
        "gpu_avg_power_w": get_avg("gpu0_power_w"),
    }


# ── CORE METRICS ─────────────────────────────────────
def extract_experiment_metrics(data, vm_rows):

    total_A_tokens = total_B_tokens = 0
    total_A_time = total_B_time = 0

    cpu_A, cpu_B = [], []
    gpu_A, gpu_B = [], []

    energy_A = energy_B = 0

    for entry in data:

        mA = entry["path_A"]["metrics"]
        mB = entry["path_B"]["metrics"]

        # ── Tokens
        total_A_tokens += mA.get("total_tokens", 0)
        total_B_tokens += mB.get("total_tokens", 0)

        # ── Time
        total_A_time += mA.get("total_duration_ms", 0)
        total_B_time += mB.get("total_duration_ms", 0)

        # ── Resource usage
        rA = resource_window(vm_rows, mA.get("wall_start"), mA.get("wall_end"))
        rB = resource_window(vm_rows, mB.get("wall_start"), mB.get("wall_end"))

        if rA.get("cpu_avg_pct"):
            cpu_A.append(rA["cpu_avg_pct"])
        if rB.get("cpu_avg_pct"):
            cpu_B.append(rB["cpu_avg_pct"])

        if rA.get("gpu_avg_pct"):
            gpu_A.append(rA["gpu_avg_pct"])
        if rB.get("gpu_avg_pct"):
            gpu_B.append(rB["gpu_avg_pct"])

        # ── Energy calculation (GPU power based)
        power_A = rA.get("gpu_avg_power_w") or 0
        power_B = rB.get("gpu_avg_power_w") or 0

        time_A_sec = mA.get("total_duration_ms", 0) / 1000
        time_B_sec = mB.get("total_duration_ms", 0) / 1000

        energy_A += (power_A * time_A_sec) / 3600
        energy_B += (power_B * time_B_sec) / 3600

    return {
        "total_tokens_A": total_A_tokens,
        "total_tokens_B": total_B_tokens,

        "total_time_A": total_A_time,
        "total_time_B": total_B_time,

        "cpu_avg_A": round(sum(cpu_A)/len(cpu_A), 2) if cpu_A else None,
        "cpu_avg_B": round(sum(cpu_B)/len(cpu_B), 2) if cpu_B else None,

        "gpu_avg_A": round(sum(gpu_A)/len(gpu_A), 2) if gpu_A else None,
        "gpu_avg_B": round(sum(gpu_B)/len(gpu_B), 2) if gpu_B else None,

        "energy_A_wh": round(energy_A, 5),
        "energy_B_wh": round(energy_B, 5)
    }


# ── REPORT ──────────────────────────────────────────
def print_report(metrics):

    print("\n" + "="*70)
    print("  EXPERIMENT RESULTS — SUSTAINABILITY ANALYSIS")
    print("="*70)

    # ── Tokens
    print("\n📊 TOKEN USAGE")
    print(f"Path A: {metrics['total_tokens_A']}")
    print(f"Path B: {metrics['total_tokens_B']}")
    print(f"Saved : {metrics['total_tokens_A'] - metrics['total_tokens_B']} ✅")

    # ── Time
    print("\n⏱ EXECUTION TIME (ms)")
    print(f"A: {metrics['total_time_A']}")
    print(f"B: {metrics['total_time_B']}")

    # ── CPU
    print("\n💻 CPU USAGE")
    print(f"A avg: {metrics['cpu_avg_A']} %")
    print(f"B avg: {metrics['cpu_avg_B']} %")

    # ── GPU
    print("\n🎮 GPU USAGE")
    print(f"A avg: {metrics['gpu_avg_A']} %")
    print(f"B avg: {metrics['gpu_avg_B']} %")

    # ── Energy
    print("\n⚡ ENERGY (Wh)")
    print(f"A: {metrics['energy_A_wh']}")
    print(f"B: {metrics['energy_B_wh']}")
    print(f"Saved: {round(metrics['energy_A_wh'] - metrics['energy_B_wh'], 5)} ✅")

    # ── Carbon
    carbon_A = metrics["energy_A_wh"] / 1000 * GRID_CARBON_INTENSITY
    carbon_B = metrics["energy_B_wh"] / 1000 * GRID_CARBON_INTENSITY

    print("\n🌱 CO₂ EMISSIONS")
    print(f"A: {round(carbon_A,4)} g")
    print(f"B: {round(carbon_B,4)} g")

    # ── Conclusion
    print("\n✅ FINAL VERDICT")

    if metrics["total_tokens_B"] < metrics["total_tokens_A"]:
        print("✔ Chunked Retrieval (Path B) is more efficient ✅")

    if metrics["energy_B_wh"] < metrics["energy_A_wh"]:
        print("✔ Path B is more energy efficient ✅")

    print("="*70)


# ── MAIN ──────────────────────────────────────────
def main():

    results_file = "experiment_results.json"
    vm_file = "vm_metrics.csv"

    if not os.path.exists(results_file):
        print("❌ experiment_results.json not found")
        return

    with open(results_file) as f:
        data = json.load(f)

    vm_rows = load_vm_metrics(vm_file)

    print(f"Loaded {len(data)} user stories")
    print(f"VM samples: {len(vm_rows)}")

    # ── Extract metrics
    metrics = extract_experiment_metrics(data, vm_rows)

    # ── Print report
    print_report(metrics)

    # ── Save JSON
    with open("comparison_report.json", "w") as f:
        json.dump(metrics, f, indent=2)

    print("\n✅ Saved → comparison_report")