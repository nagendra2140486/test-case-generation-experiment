"""
Sustainability Scorer — Path A vs Path B

Reads:
  experiment_results.json
  vm_metrics.csv (optional)

Outputs:
  comparison_report.json
  terminal summary
"""

import csv
import json
import os
from datetime import datetime

# ── CONFIG ───────────────────────────────
GRID_CARBON_INTENSITY = 713  # gCO2/kWh

# ── VM METRICS ───────────────────────────
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

    def avg(key):
        vals = []
        for r in window:
            try:
                vals.append(float(r[key]))
            except:
                pass
        return round(sum(vals)/len(vals), 2) if vals else None

    return {
        "cpu": avg("cpu_pct"),
        "gpu": avg("gpu0_util_pct"),
        "power": avg("gpu0_power_w"),
    }


# ── CORE METRICS ─────────────────────────
def extract_metrics(data, vm_rows):

    total_A_tokens = total_B_tokens = 0
    total_A_time = total_B_time = 0

    cpu_A, cpu_B = [], []
    gpu_A, gpu_B = [], []

    energy_A = energy_B = 0

    for entry in data:

        mA = entry["path_A"]["metrics"]
        mB = entry["path_B"]["metrics"]

        # ✅ Tokens
        total_A_tokens += mA.get("total_tokens", 0)
        total_B_tokens += mB.get("total_tokens", 0)

        # ✅ Time
        total_A_time += mA.get("total_duration_ms", 0)
        total_B_time += mB.get("total_duration_ms", 0)

        # ✅ VM resource usage
        rA = resource_window(vm_rows, mA.get("wall_start"), mA.get("wall_end"))
        rB = resource_window(vm_rows, mB.get("wall_start"), mB.get("wall_end"))

        if rA.get("cpu"): cpu_A.append(rA["cpu"])
        if rB.get("cpu"): cpu_B.append(rB["cpu"])

        if rA.get("gpu"): gpu_A.append(rA["gpu"])
        if rB.get("gpu"): gpu_B.append(rB["gpu"])

        # ✅ Energy calculation
        power_A = rA.get("power") or 0
        power_B = rB.get("power") or 0

        time_A = mA.get("total_duration_ms", 0) / 1000
        time_B = mB.get("total_duration_ms", 0) / 1000

        energy_A += (power_A * time_A) / 3600
        energy_B += (power_B * time_B) / 3600

    return {
        "tokens_A": total_A_tokens,
        "tokens_B": total_B_tokens,

        "time_A": total_A_time,
        "time_B": total_B_time,

        "cpu_A": round(sum(cpu_A)/len(cpu_A),2) if cpu_A else None,
        "cpu_B": round(sum(cpu_B)/len(cpu_B),2) if cpu_B else None,

        "gpu_A": round(sum(gpu_A)/len(gpu_A),2) if gpu_A else None,
        "gpu_B": round(sum(gpu_B)/len(gpu_B),2) if gpu_B else None,

        "energy_A": round(energy_A,4),
        "energy_B": round(energy_B,4),
    }


# ── REPORT ───────────────────────────────
def print_report(m):

    print("\n" + "="*70)
    print(" EXPERIMENT REPORT — PATH A vs PATH B")
    print("="*70)

    # ✅ Tokens
    print("\n📊 TOKENS")
    print(f"A: {m['tokens_A']}")
    print(f"B: {m['tokens_B']}")
    print(f"Saved: {m['tokens_A'] - m['tokens_B']} ✅")

    # ✅ Time
    print("\n⏱ TIME (ms)")
    print(f"A: {m['time_A']}")
    print(f"B: {m['time_B']}")

    # ✅ CPU
    print("\n💻 CPU")
    print(f"A avg: {m['cpu_A']}")
    print(f"B avg: {m['cpu_B']}")

    # ✅ GPU
    print("\n🎮 GPU")
    print(f"A avg: {m['gpu_A']}")
    print(f"B avg: {m['gpu_B']}")

    # ✅ Energy
    print("\n⚡ ENERGY (Wh)")
    print(f"A: {m['energy_A']}")
    print(f"B: {m['energy_B']}")
    print(f"Saved: {round(m['energy_A'] - m['energy_B'],4)} ✅")

    # ✅ CO2
    co2_A = m["energy_A"]/1000 * GRID_CARBON_INTENSITY
    co2_B = m["energy_B"]/1000 * GRID_CARBON_INTENSITY

    print("\n🌱 CO₂")
    print(f"A: {round(co2_A,4)} g")
    print(f"B: {round(co2_B,4)} g")

    # ✅ Verdict
    print("\n✅ FINAL VERDICT")

    if m["tokens_B"] < m["tokens_A"]:
        print("✔ Chunking (Path B) reduces tokens ✅")

    if m["energy_B"] < m["energy_A"]:
        print("✔ Path B is more energy efficient ✅")

    print("="*70)


# ── MAIN ───────────────────────────────
def main():

    results_file = "experiment_results.json"
    vm_file = "vm_metrics.csv"

    if not os.path.exists(results_file):
        print("❌ No experiment_results.json found")
        return

    with open(results_file) as f:
        data = json.load(f)

    vm_rows = load_vm_metrics(vm_file)

    print(f"Loaded {len(data)} user stories")
    print(f"VM samples: {len(vm_rows)}")

    metrics = extract_metrics(data, vm_rows)

    print_report(metrics)

    with open("outputs/comparison_report.json","w") as f:
        json.dump(metrics, f, indent=2)

    print("\n✅ comparison_report.json saved")


if __name__ == "__main__":
    main()
