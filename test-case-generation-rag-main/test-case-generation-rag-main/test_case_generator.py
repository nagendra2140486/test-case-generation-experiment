import json
import time
from datetime import datetime
import ollama
from docx import Document

# ── DOCX READER ─────────────────────────────────────
def read_docx(file_path):
    doc = Document(file_path)
    return "\n".join([p.text.strip() for p in doc.paragraphs if p.text.strip()])

# ── CHUNK RETRIEVAL ─────────────────────────────────
def get_chunk_context(user_story: str):
    story = str(user_story).lower()

    if "register" in story:
        return read_docx("data/01_user_onboarding.docx") + "\n\n" + read_docx("data/07_global_concerns.docx")

    elif "login" in story or "secure" in story:
        return read_docx("data/02_authentication.docx") + "\n\n" + read_docx("data/07_global_concerns.docx")

    elif "card" in story or "wallet" in story:
        return read_docx("data/03_wallet_and_cards.docx") + "\n\n" + read_docx("data/07_global_concerns.docx")

    elif "send money" in story or "transfer" in story:
        return read_docx("data/04_p2p_transfers.docx") + "\n\n" + read_docx("data/07_global_concerns.docx")

    elif "qr" in story or "merchant" in story:
        return read_docx("data/05_merchant_payments.docx") + "\n\n" + read_docx("data/07_global_concerns.docx")

    elif "history" in story or "notification" in story or "export" in story:
        return read_docx("data/06_history_and_notifications.docx") + "\n\n" + read_docx("data/07_global_concerns.docx")

    else:
        return read_docx("data/07_global_concerns.docx")

# ── CONFIG ──────────────────────────────────────────
OLLAMA_HOST = "http://10.120.100.16/ollama"
API_KEY = "sk-your-key-here"

MODELS = ["llama3.2:latest"]

TEXTS = [
    "US-01: Register user",
    "US-02: Login user",
    "US-03: Link card",
    "US-04: Add money",
    "US-05: Send money",
    "US-06: Receive money",
    "US-07: Pay via QR",
    "US-08: View history",
    "US-09: Notifications",
    "US-10: Withdraw money",
    "US-11: Secure auth",
    "US-12: Export data",
]

FULL_BRD_CONTEXT = read_docx("data/01_BRD_SwiftPay_v2.docx")

SYSTEM_PROMPT = """
You are a QA Engineer. Generate test cases with:
- Positive
- Negative
- Edge cases
- NFR scenarios

Each test should include:
Test ID, Title, Steps, Expected Result.
"""

client = ollama.Client(host=OLLAMA_HOST, headers={"Authorization": f"Bearer {API_KEY}"})

# ── CORE FUNCTION ───────────────────────────────────
def generate_test_cases(user_story, model, context):
    start_time = time.time()
    wall_start = datetime.utcnow().isoformat() + "Z"

    response = client.chat(
        model=model,
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": f"{context}\n\n{user_story}"},
        ]
    )

    content = response.message.content
    wall_end = datetime.utcnow().isoformat() + "Z"

    # ✅ fallback tokens
    input_tokens = len(context) // 4
    output_tokens = len(content) // 4
    total_tokens = input_tokens + output_tokens

    # ✅ fallback time
    total_duration_ms = round((time.time() - start_time) * 1000, 2)

    tokens_per_sec = round(total_tokens / (total_duration_ms / 1000), 2)

    return {
        "content": content,
        "metrics": {
            "wall_start": wall_start,
            "wall_end": wall_end,
            "total_tokens": total_tokens,
            "total_duration_ms": total_duration_ms,
            "tokens_per_sec": tokens_per_sec
        }
    }

# ── RUN EXPERIMENT ──────────────────────────────────
def main():
    all_results = []

    for model in MODELS:
        print(f"\nMODEL: {model}")

        for i, story in enumerate(TEXTS, 1):

            # Path A
            res_A = generate_test_cases(story, model, FULL_BRD_CONTEXT)

            # Path B
            chunk_context = get_chunk_context(story)
            res_B = generate_test_cases(story, model, chunk_context)

            entry = {
                "user_story": story,
                "path_A": res_A,
                "path_B": res_B,
                "comparison": {
                    "token_diff": res_A["metrics"]["total_tokens"] - res_B["metrics"]["total_tokens"]
                }
            }

            all_results.append(entry)

            print(f"{i} A {res_A['metrics']['total_tokens']} tokens")
            print(f"{i} B {res_B['metrics']['total_tokens']} tokens")

    # ✅ save output
    with open("outputs/experiment_results.json", "w") as f:
        json.dump(all_results, f, indent=2)

    print("\n✅ Experiment complete")

if __name__ == "__main__":
    main()
