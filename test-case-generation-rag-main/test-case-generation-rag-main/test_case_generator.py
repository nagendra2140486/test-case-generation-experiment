"""
Sentiment analysis using Ollama SLMs via Open WebUI proxy.
Scores 50 text samples across multiple models and saves results to JSON.
"""

import json
import time
from datetime import datetime
import ollama
from docx import Document

# reading the docx file
def read_docx(file_path):
    doc = Document(file_path)
    full_text = []

    for para in doc.paragraphs:
        text = para.text.strip()
        if text:
            full_text.append(text)

    return "\n".join(full_text)
## chunking document reading only necessary for the userstory
def get_chunk_context(user_story: str):
    try:
        story = str(user_story).lower()
    except:
        story = ""

    # ────────── USER ONBOARDING ──────────
    if "register" in story or "onboard" in story:
        return read_docx("data/01_user_onboarding.docx") + "\n\n" + \
               read_docx("data/07_global_concerns.docx")

    # ────────── AUTHENTICATION ──────────
    elif "login" in story or "secure" in story:
        return read_docx("data/02_authentication.docx") + "\n\n" + \
               read_docx("data/07_global_concerns.docx")

    # ────────── WALLET / CARDS ──────────
    elif "card" in story or "wallet" in story or "add money" in story:
        return read_docx("data/03_wallet_and_cards.docx") + "\n\n" + \
               read_docx("data/07_global_concerns.docx")

    # ────────── P2P TRANSFERS ──────────
    elif "send money" in story or "transfer" in story or "receive money" in story:
        return read_docx("data/04_p2p_transfers.docx") + "\n\n" + \
               read_docx("data/07_global_concerns.docx")

    # ────────── MERCHANT PAYMENTS ──────────
    elif "qr" in story or "merchant" in story or "payment" in story:
        return read_docx("data/05_merchant_payments.docx") + "\n\n" + \
               read_docx("data/07_global_concerns.docx")

    # ────────── HISTORY / NOTIFICATIONS ──────────
    elif "history" in story or "notification" in story or "export" in story:
        return read_docx("data/06_history_and_notifications.docx") + "\n\n" + \
               read_docx("data/07_global_concerns.docx")

    # ────────── DEFAULT (fallback) ──────────
    else:
        return read_docx("data/07_global_concerns.docx")
# ── CONFIG ────────────────────────────────────────────────────────────────────
OLLAMA_HOST = "http://10.120.100.16/ollama"
API_KEY     = "sk-your-key-here"   # Open WebUI: Settings → Account → API Keys

# SLM vs LLM comparison pair — change these to try different combos
MODELS = [
    "llama3.2:latest",   # SLM — 3.2B parameters
    "llama3.3:70b",      # LLM — 70.6B parameters
]

# ── 50 SAMPLE TEXTS ──────────────────────────────────────────────────────────

TEXTS = [
    "US-01: As a new user, I want to register using my mobile number so that I can create an account.",
    "US-02: As a user, I want to login using PIN so that I can access my wallet.",
    "US-03: As a user, I want to link a card so that I can add funds.",
    "US-04: As a user, I want to add money to wallet so that I can use it.",
    "US-05: As a user, I want to send money to another user so that I can transfer funds.",
    "US-06: As a user, I want to receive money so that I can accept transfers.",
    "US-07: As a user, I want to scan QR code so that I can pay merchants.",
    "US-08: As a user, I want to view transaction history so that I can track spending.",
    "US-09: As a user, I want to get notifications so that I am aware of activities.",
    "US-10: As a user, I want to withdraw money so that I can move funds to bank.",
    "US-11: As a user, I want secure authentication so that my account is protected.",
    "US-12: As a user, I want export data so that I can download statements.",
]

# ── CONTEXTS ──────────────────────────────────────────────────────────────────

# ✅ Path A → FULL BRD
FULL_BRD_CONTEXT = read_docx("data/01_BRD_SwiftPay_v2.docx")


SYSTEM_PROMPT = (
    "You are a senior Quality Engineer.\n"
    "Based on the requirements context and user story, generate detailed test cases.\n\n"
    "You must cover:\n"
    "- Positive scenarios\n"
    "- Negative scenarios\n"
    "- Edge cases\n"
    "- Non-functional scenarios (security, performance, compliance)\n\n"
    "Each test case must include:\n"
    "- Test ID\n"
    "- Title\n"
    "- Preconditions\n"
    "- Test Steps (numbered)\n"
    "- Expected Result\n"
    "- Priority (High/Medium/Low)\n"
    "- Type (Positive/Negative/Edge/NFR)\n\n"
    "Important:\n"
    "- Always consider cross-cutting rules like KYC limits, authentication rules, security and transaction rules.\n"
    "- Return ONLY the test cases (no extra explanation).\n"
)

# ── CLIENT ────────────────────────────────────────────────────────────────────
client = ollama.Client(
    host=OLLAMA_HOST,
    headers={"Authorization": f"Bearer {API_KEY}"},
)


def list_available_models() -> list[str]:
    """Return model names from Ollama via SDK."""
    response = client.list()
    return [m.model for m in response.models]


def generate_test_cases(user_story: str, model: str, context: str) -> dict:
    wall_start = datetime.utcnow().isoformat() + "Z"

    try:
        response = client.chat(
            model=model,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {
                    "role": "user",
                    "content": f"""
REQUIREMENTS CONTEXT:
{context}

USER STORY:
{user_story}
"""
                }
            ],
            options={"temperature": 0.2, "num_predict": 2000},
        )

        wall_end = datetime.utcnow().isoformat() + "Z"

        content = response.message.content

        # ✅ Metrics extraction from Ollama
        eval_count     = response.eval_count or 0
        eval_dur_ns    = response.eval_duration or 0
        prompt_count   = response.prompt_eval_count or 0
        prompt_dur_ns  = response.prompt_eval_duration or 0
        total_dur_ns   = response.total_duration or 0

        # ✅ Token calculations
        total_tokens = prompt_count + eval_count

        tokens_per_sec = (
            eval_count / (eval_dur_ns / 1e9)
            if eval_dur_ns > 0 else 0
        )

        return {
            "content": content,
            "metrics": {
                "wall_start": wall_start,
                "wall_end": wall_end,

                "total_tokens": total_tokens,
                "prompt_tokens": prompt_count,
                "completion_tokens": eval_count,

                "total_duration_ms": round(total_dur_ns / 1e6, 2),
                "prompt_duration_ms": round(prompt_dur_ns / 1e6, 2),
                "completion_duration_ms": round(eval_dur_ns / 1e6, 2),

                "tokens_per_sec": round(tokens_per_sec, 2)
            }
        }

    except Exception as e:
        return {
            "content": "error",
            "metrics": {},
            "error": str(e)
        }


def run_analysis(model: str) -> list[dict]:
    """
    Runs experiment for all user stories:
    - Path A (Full BRD)
    - Path B (Chunked context)
    - Captures metrics for comparison
    """

    results = []

    print(f"\n{'='*80}")
    print(f"  Model: {model}")
    print(f"{'='*80}")
    print(f"{'#':<4} {'Path':<6} {'Tokens':<10} {'Time(ms)':<10} {'Tok/s':<10} User Story")
    print("-" * 80)

    for i, story in enumerate(TEXTS, 1):

        # ─────────────── PATH A ───────────────
        result_a = generate_test_cases(story, model, FULL_BRD_CONTEXT)
        mA = result_a.get("metrics", {})

        # ─────────────── PATH B ───────────────
        CHUNK_CONTEXT = get_chunk_context(story)

        result_b = generate_test_cases(story, model, CHUNK_CONTEXT)
        mB = result_b.get("metrics", {})

        # ✅ Comparison
        comparison = {
            "token_diff": mA.get("total_tokens", 0) - mB.get("total_tokens", 0),
            "latency_diff_ms": mA.get("total_duration_ms", 0) - mB.get("total_duration_ms", 0)
        }

        entry = {
            "user_story": story,
            "path_A": result_a,
            "path_B": result_b,
            "comparison": comparison
        }

        results.append(entry)

        # ✅ PRINT TABLE (LIVE)
        print(f"{i:<4} A      {mA.get('total_tokens',0):<10} {mA.get('total_duration_ms',0):<10} {mA.get('tokens_per_sec',0):<10} {story[:40]}")
        print(f"{i:<4} B      {mB.get('total_tokens',0):<10} {mB.get('total_duration_ms',0):<10} {mB.get('tokens_per_sec',0):<10} {'-'}")

    return results


def print_summary(model: str, results: list[dict]):
    """
    Summarizes experiment results across all user stories
    """

    total_A_tokens = 0
    total_B_tokens = 0

    total_A_time = 0
    total_B_time = 0

    total_A_tps = []
    total_B_tps = []

    for r in results:
        mA = r["path_A"].get("metrics", {})
        mB = r["path_B"].get("metrics", {})

        total_A_tokens += mA.get("total_tokens", 0)
        total_B_tokens += mB.get("total_tokens", 0)

        total_A_time += mA.get("total_duration_ms", 0)
        total_B_time += mB.get("total_duration_ms", 0)

        if mA.get("tokens_per_sec", 0) > 0:
            total_A_tps.append(mA["tokens_per_sec"])

        if mB.get("tokens_per_sec", 0) > 0:
            total_B_tps.append(mB["tokens_per_sec"])

    avg_A_tps = sum(total_A_tps) / len(total_A_tps) if total_A_tps else 0
    avg_B_tps = sum(total_B_tps) / len(total_B_tps) if total_B_tps else 0

    print(f"\n{'='*60}")
    print(f" SUMMARY — {model}")
    print(f"{'='*60}")

    print("\n📊 Token Usage:")
    print(f"  Path A (Full BRD)   : {total_A_tokens}")
    print(f"  Path B (Chunked)   : {total_B_tokens}")
    print(f"  🔻 Reduction       : {total_A_tokens - total_B_tokens}")

    print("\n⏱️ Execution Time:")
    print(f"  Path A total (ms)  : {round(total_A_time,2)}")
    print(f"  Path B total (ms)  : {round(total_B_time,2)}")
    print(f"  🔻 Time saved      : {round(total_A_time - total_B_time,2)} ms")

    print("\n⚡ Throughput:")
    print(f"  Path A avg tok/s   : {round(avg_A_tps,2)}")
    print(f"  Path B avg tok/s   : {round(avg_B_tps,2)}")

    # ✅ Optional Energy Estimate (VERY IMPORTANT FOR YOUR EXPERIMENT)
    energy_A = total_A_tokens * 0.00013
    energy_B = total_B_tokens * 0.00013

    print("\n🌱 Estimated Energy (Wh):")
    print(f"  Path A              : {round(energy_A,6)} Wh")
    print(f"  Path B              : {round(energy_B,6)} Wh")


def main():
    print("=" * 70)
    print(f"  Ollama Sentiment Scorer")
    print(f"  Host : {OLLAMA_HOST}")
    print("=" * 70)

    # Verify connection and list models
    try:
        available = list_available_models()
        print(f"\nModels on this Ollama instance ({len(available)} total):")
        for m in available:
            print(f"  • {m}")
    except Exception as e:
        print(f"\nCould not connect to {OLLAMA_HOST}: {e}")
        print("Check that the VM is reachable and OLLAMA_HOST is correct.")
        return

    # Confirm which models we'll run
    models_to_run = [m for m in MODELS if m in available]
    missing = [m for m in MODELS if m not in available]
    if missing:
        print(f"\nNot found (skipping): {missing}")
    if not models_to_run:
        print("None of the MODELS list are available. Update MODELS in the script.")
        return
    print(f"\nRunning analysis with: {models_to_run}")

    all_results = {}
    for model in models_to_run:
        t0         = time.time()
        wall_start = datetime.utcnow().isoformat() + "Z"
        results = run_analysis(model)
        print_summary(model, results)
        wall_end   = datetime.utcnow().isoformat() + "Z"
        elapsed    = time.time() - t0

        valid = [r for r in results if r.get("meta", {}).get("tokens_per_sec", 0) > 0]
        avg_tps = sum(r["meta"]["tokens_per_sec"] for r in valid) / len(valid) if valid else 0
        total_tokens = sum(
            r.get("meta", {}).get("prompt_tokens", 0) + r.get("meta", {}).get("completion_tokens", 0)
            for r in results
        )

        all_results[model] = {
            "wall_start":    wall_start,
            "wall_end":      wall_end,
            "elapsed_sec":   round(elapsed, 2),
            "total_tokens":  total_tokens,
            "avg_tokens_per_sec": round(avg_tps, 2),
            "results":       results,
        }
        print_summary(model, results)
        print(f"  time : {elapsed:.1f}s  avg {avg_tps:.1f} tok/s  total tokens: {total_tokens}")

    # Save to JSON
    output_file = "sentiment_results.json"
    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(all_results, f, indent=2, ensure_ascii=False)
    print(f"\nResults saved → {output_file}")


if __name__ == "__main__":
    main()
