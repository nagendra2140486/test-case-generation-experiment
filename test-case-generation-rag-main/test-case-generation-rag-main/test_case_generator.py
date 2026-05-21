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
    start_time = time.time()
    wall_start = datetime.utcnow().isoformat() + "Z"

    try:
        # ✅ RETRY HANDLING (fix 504 timeout)
        for attempt in range(2):
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
                    options={"temperature": 0.2, "num_predict": 700},
                )
                break
            except Exception:
                print(f"⚠️ Retry {attempt+1} for {user_story}")
                time.sleep(2)

        wall_end = datetime.utcnow().isoformat() + "Z"

        # ✅ FIXED RESPONSE EXTRACTION (critical)
        content = ""

        if hasattr(response, "message") and response.message:
            content = response.message.content
        elif hasattr(response, "response"):
            content = response.response
        elif isinstance(response, dict):
            content = response.get("message", {}).get("content", "") or response.get("response", "")

        if not content.strip():
            print(f"⚠️ EMPTY OUTPUT for {user_story}")

        # ✅ SAFE FALLBACK TOKENS
        input_tokens = max(len(context) // 4, 50)
        output_tokens = max(len(content) // 4, 20)

        total_tokens = input_tokens + output_tokens

        # ✅ SAFE TIME
        total_duration_ms = round((time.time() - start_time) * 1000, 2)

        # ✅ THROUGHPUT
        tokens_per_sec = round(total_tokens / (total_duration_ms / 1000), 2) if total_duration_ms > 0 else 0

        return {
            "content": content,
            "metrics": {
                "wall_start": wall_start,
                "wall_end": wall_end,
                "total_tokens": total_tokens,
                "prompt_tokens": input_tokens,
                "completion_tokens": output_tokens,
                "total_duration_ms": total_duration_ms,
                "tokens_per_sec": tokens_per_sec
            }
        }

    except Exception as e:
        return {
            "content": "error",
            "metrics": {
                "total_tokens": 0,
                "total_duration_ms": 0,
                "tokens_per_sec": 0
            },
            "error": str(e)
        }


# ── RUN EXPERIMENT ───────────────────────────────────
def run_analysis(model: str) -> list[dict]:

    results = []

    print(f"\n{'='*80}")
    print(f"  Model: {model}")
    print(f"{'='*80}")
    print(f"{'#':<4} {'Path':<6} {'Tokens':<10} {'Time(ms)':<10} {'Tok/s':<10} User Story")
    print("-" * 80)

    for i, story in enumerate(TEXTS, 1):

        # ✅ Path A
        result_a = generate_test_cases(story, model, FULL_BRD_CONTEXT)
        mA = result_a.get("metrics", {})

        # ✅ Path B
        chunk_context = get_chunk_context(story)
        result_b = generate_test_cases(story, model, chunk_context)
        mB = result_b.get("metrics", {})

        entry = {
            "user_story": story,
            "path_A": result_a,
            "path_B": result_b,
            "comparison": {
                "token_diff": mA.get("total_tokens", 0) - mB.get("total_tokens", 0),
                "latency_diff_ms": mA.get("total_duration_ms", 0) - mB.get("total_duration_ms", 0)
            }
        }

        results.append(entry)

        print(f"{i:<4} A {mA.get('total_tokens',0):<10} {mA.get('total_duration_ms',0):<10} {mA.get('tokens_per_sec',0):<10} {story[:40]}")
        print(f"{i:<4} B {mB.get('total_tokens',0):<10} {mB.get('total_duration_ms',0):<10} {mB.get('tokens_per_sec',0):<10}")

    return results


# ── SUMMARY ──────────────────────────────────────────
def print_summary(model: str, results: list[dict]):

    total_A = total_B = 0
    time_A = time_B = 0

    for r in results:
        mA = r["path_A"]["metrics"]
        mB = r["path_B"]["metrics"]

        total_A += mA["total_tokens"]
        total_B += mB["total_tokens"]

        time_A += mA["total_duration_ms"]
        time_B += mB["total_duration_ms"]

    print("\n" + "="*60)
    print(f" SUMMARY — {model}")
    print("="*60)

    print("\n📊 Tokens")
    print(f"Path A: {total_A}")
    print(f"Path B: {total_B}")
    print(f"Saved : {total_A - total_B} ✅")

    print("\n⏱ Time")
    print(f"A: {time_A}")
    print(f"B: {time_B}")

    energy_A = total_A * 0.00013
    energy_B = total_B * 0.00013

    print("\n🌱 Energy")
    print(f"A: {round(energy_A,6)} Wh")
    print(f"B: {round(energy_B,6)} Wh")


# ── MAIN ─────────────────────────────────────────────
def main():

    print("="*70)
    print(" RAG TEST CASE GENERATION EXPERIMENT")
    print("="*70)

    model = MODELS[0]

    results = run_analysis(model)

    print_summary(model, results)

    with open("outputs/experiment_results.json", "w") as f:
        json.dump(results, f, indent=2)

    print("\n✅ Results saved in outputs/experiment_results.json")


if __name__ == "__main__":
    main()
