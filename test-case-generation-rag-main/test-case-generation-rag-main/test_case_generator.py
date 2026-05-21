import json
import time
from datetime import datetime
import ollama
from docx import Document

# ── CONFIG ───────────────────────────────────────────
OLLAMA_HOST = "http://10.120.100.16/ollama"
API_KEY = "sk-your-real-key"   # ✅ PUT YOUR REAL KEY

client = ollama.Client(
    host=OLLAMA_HOST,
    headers={"Authorization": f"Bearer {API_KEY}"}   # ✅ FIXED
)

# ── DOCX READER ─────────────────────────────────────
def read_docx(file_path):
    doc = Document(file_path)
    return "\n".join([p.text.strip() for p in doc.paragraphs if p.text.strip()])

# ── CHUNKING ─────────────────────────────────────────
def get_chunk_context(user_story: str):
    story = user_story.lower()

    if "register" in story:
        return read_docx("data/01_user_onboarding.docx") + "\n\n" + read_docx("data/07_global_concerns.docx")
    elif "login" in story:
        return read_docx("data/02_authentication.docx") + "\n\n" + read_docx("data/07_global_concerns.docx")
    elif "card" in story or "wallet" in story:
        return read_docx("data/03_wallet_and_cards.docx") + "\n\n" + read_docx("data/07_global_concerns.docx")
    elif "send money" in story:
        return read_docx("data/04_p2p_transfers.docx") + "\n\n" + read_docx("data/07_global_concerns.docx")
    elif "qr" in story:
        return read_docx("data/05_merchant_payments.docx") + "\n\n" + read_docx("data/07_global_concerns.docx")
    else:
        return read_docx("data/07_global_concerns.docx")

# ── DATA ─────────────────────────────────────────────
MODELS = ["llama3.2:latest"]

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

FULL_BRD_CONTEXT = read_docx("data/01_BRD_SwiftPay_v2.docx")[:4000]

SYSTEM_PROMPT = (
    "You are a Senior QA Engineer.\n\n"
    "Your task is to generate detailed and structured test cases based on the given requirements context and user story.\n\n"

    "STRICT INSTRUCTIONS:\n"
    "1. Always generate test cases in a structured and consistent format.\n"
    "2. Do NOT add explanations, comments, or extra text.\n"
    "3. Use clear, concise, and professional language.\n\n"

    "Each test case MUST include:\n"
    "- Test Case ID\n"
    "- Title\n"
    "- Preconditions\n"
    "- Test Steps (numbered)\n"
    "- Expected Result\n"
    "- Priority (High/Medium/Low)\n"
    "- Test Type (Positive / Negative / Edge / NFR)\n\n"

    "Coverage requirements:\n"
    "- Include Positive scenarios\n"
    "- Include Negative scenarios\n"
    "- Include Edge cases\n"
    "- Include Non-functional scenarios (performance, security, validation)\n\n"

    "Constraints:\n"
    "- Follow the given requirements context strictly\n"
    "- Do not assume missing data\n"
    "- Do not hallucinate features\n"
    "- Keep output precise and structured\n"
)


def generate_test_cases(user_story, model, context):

    start_time = time.time()

    try:
        response = client.chat(
            model=model,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": context + "\n" + user_story}
            ],
            options={"temperature": 0.2, "num_predict": 700}
        )

        content = ""
        if hasattr(response, "message") and response.message:
            content = response.message.content
        elif hasattr(response, "response"):
            content = response.response

        # ✅ token calc
        input_tokens = max(len(context)//4, 50)
        output_tokens = max(len(content)//4, 20)
        total_tokens = input_tokens + output_tokens

        # ✅ time
        total_duration_ms = (time.time() - start_time) * 1000

        # ✅ throughput
        tokens_per_sec = round(total_tokens / (total_duration_ms / 1000), 2) if total_duration_ms > 0 else 0

        return {
            "content": content,
            "metrics": {
                "total_tokens": total_tokens,
                "total_duration_ms": total_duration_ms,
                "tokens_per_sec": tokens_per_sec
            }
        }

    except Exception as e:
        print("ERROR:", e)
        return {
            "content": "error",
            "metrics": {
                "total_tokens": 0,
                "total_duration_ms": 0,
                "tokens_per_sec": 0
            }
        }

# ── RUN EXPERIMENT ───────────────────────────────────
def run_analysis(model):

    results = []

    print("\n" + "="*80)
    print(f"MODEL: {model}")
    print("="*80)

    for i, story in enumerate(TEXTS, 1):

        result_a = generate_test_cases(story, model, FULL_BRD_CONTEXT)
        result_b = generate_test_cases(story, model, get_chunk_context(story))

        mA = result_a["metrics"]
        mB = result_b["metrics"]

        results.append({
            "user_story": story,
            "path_A": result_a,
            "path_B": result_b
        })

        # ✅ BRD vs Chunking labels
        print(f"{i} BRD → Tokens: {mA['total_tokens']} Time: {round(mA['total_duration_ms'],2)} ms")
        print(f"{i} Chunking → Tokens: {mB['total_tokens']} Time: {round(mB['total_duration_ms'],2)} ms")

    return results

# ── SUMMARY ✅ (YOU WANTED THIS BACK)
def print_summary(model, results):

    total_A = total_B = 0
    time_A = time_B = 0

    for r in results:
        mA = r["path_A"]["metrics"]
        mB = r["path_B"]["metrics"]

        total_A += mA.get("total_tokens", 0)
        total_B += mB.get("total_tokens", 0)

        time_A += mA.get("total_duration_ms", 0)
        time_B += mB.get("total_duration_ms", 0)

    print("\n" + "="*60)
    print(" FINAL SUMMARY")
    print("="*60)

    print("\n📊 Tokens")
    print(f"BRD: {total_A}")
    print(f"Chunking: {total_B}")
    print(f"Saved: {total_A - total_B} ✅")

    print("\n⏱ Time")
    print(f"BRD: {round(time_A,2)} ms")
    print(f"Chunking: {round(time_B,2)} ms")

    energy_A = total_A * 0.00013
    energy_B = total_B * 0.00013

    print("\n⚡ Energy")
    print(f"BRD: {round(energy_A,6)} Wh")
    print(f"Chunking: {round(energy_B,6)} Wh")

# ── MAIN ─────────────────────────────────────────────
def main():

    print("="*70)
    print(" RAG TEST CASE GENERATION EXPERIMENT")
    print("="*70)

    results = run_analysis(MODELS[0])

    print_summary(MODELS[0], results)   # ✅ BACK AGAIN

    with open("outputs/experiment_results.json", "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2)

    print("\n✅ Results saved → outputs/experiment_results.json")


if __name__ == "__main__":
    main()

