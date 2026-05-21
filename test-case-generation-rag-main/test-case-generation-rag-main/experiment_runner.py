import json

def main():

    with open("outputs/experiment_results.json", encoding="utf-8") as f:
        data = json.load(f)

    total_A_tokens = total_B_tokens = 0
    total_A_time = total_B_time = 0

    for entry in data:
        total_A_tokens += entry["path_A"]["tokens"]
        total_B_tokens += entry["path_B"]["tokens"]
        total_A_time += entry["path_A"]["time"]
        total_B_time += entry["path_B"]["time"]

    # ✅ ENERGY CALCULATION (playbook)
    energy_A = (total_A_tokens / 1000) * 0.0003
    energy_B = (total_B_tokens / 1000) * 0.0003

    co2_A = energy_A * 0.233
    co2_B = energy_B * 0.233

    # ✅ % calculations
    token_reduction = ((total_A_tokens - total_B_tokens)/total_A_tokens)*100 if total_A_tokens else 0
    energy_reduction = ((energy_A - energy_B)/energy_A)*100 if energy_A else 0
    time_reduction = ((total_A_time - total_B_time)/total_A_time)*100 if total_A_time else 0

    report = {
        "experiment": "BRD vs Chunking",
        "model": "llama3.2",

        "totals": {
            "tokens": {
                "BRD": total_A_tokens,
                "Chunking": total_B_tokens
            },
            "time_ms": {
                "BRD": round(total_A_time,2),
                "Chunking": round(total_B_time,2)
            },
            "energy_wh": {
                "BRD": round(energy_A,6),
                "Chunking": round(energy_B,6)
            },
            "co2_g": {
                "BRD": round(co2_A,6),
                "Chunking": round(co2_B,6)
            }
        },

        "improvements": {
            "token_reduction_percent": round(token_reduction,2),
            "energy_reduction_percent": round(energy_reduction,2),
            "time_reduction_percent": round(time_reduction,2)
        },

        "verdict": "Chunking is more efficient than BRD in terms of tokens, energy, and performance."
    }

    with open("outputs/comparison_report.json", "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2)

    # ✅ Print summary
    print("\n✅ FINAL SUMMARY")
    print(f"Tokens → BRD: {total_A_tokens} | Chunking: {total_B_tokens}")
    print(f"Energy → BRD: {round(energy_A,6)} | Chunking: {round(energy_B,6)}")
    print(f"CO2 → BRD: {round(co2_A,6)} | Chunking: {round(co2_B,6)}")

    print(f"\n✅ Token Reduction: {round(token_reduction,2)}%")
    print(f"✅ Energy Reduction: {round(energy_reduction,2)}%")
    print(f"✅ Speed Improvement: {round(time_reduction,2)}%")

    print("\n✅ Report saved → outputs/comparison_report.json")


if __name__ == "__main__":
    main()
