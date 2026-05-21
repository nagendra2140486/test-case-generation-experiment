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
    "US-01: Register user",
    "US-02: Login user",
    "US-03: Link card",
    "US-04: Add money",
    "US-05: Send money"
]

FULL_BRD_CONTEXT = read_docx("data/01_BRD_SwiftPay_v2.docx")[:4000]

SYSTEM_PROMPT = "Generate detailed QA test cases"

# ── GENERATOR FUNCTION ✅ (THIS IS YOUR CORE)
def generate_test_cases(user_story, context):

    start_time = time.time()

    try:
        response = client.chat(
            model=MODELS[0],
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": context + "\n" + user_story}
            ],
            options={"temperature": 0.2, "num_predict": 700}
        )

        # ✅ SAFE CONTENT EXTRACTION
        content = ""
        if hasattr(response, "message") and response.message:
            content = response.message.content
        elif hasattr(response, "response"):
            content = response.response

        # ✅ TOKEN CALCULATION
        input_tokens = max(len(context)//4, 50)
        output_tokens = max(len(content)//4, 20)
        total_tokens = input_tokens + output_tokens

        # ✅ TIME
        total_duration_ms = (time.time() - start_time) * 1000

        # ✅ THROUGHPUT
        tokens_per_sec = round(total_tokens / (total_duration_ms / 1000), 2) if total_duration_ms > 0 else 0

        return {
            "content": content,
            "metrics": {
                "total_tokens": total_tokens,
                "prompt_tokens": input_tokens,
                "completion_tokens": output_tokens,
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

        result_a = generate_test_cases(story, FULL_BRD_CONTEXT)
        result_b = generate_test_cases(story, get_chunk_context(story))

        mA = result_a["metrics"]
        mB = result_b["metrics"]

        results.append({
            "user_story": story,
            "path_A": result_a,
            "path_B": result_b
        })

        print(f"{i} A Tokens: {mA['total_tokens']} Time: {round(mA['total_duration_ms'],2)} ms")
        print(f"{i} B Tokens: {mB['total_tokens']} Time: {round(mB['total_duration_ms'],2)} ms")

    return results

# ── MAIN ─────────────────────────────────────────────
def main():

    print("="*70)
    print(" RAG TEST CASE GENERATION EXPERIMENT")
    print("="*70)

    results = run_analysis(MODELS[0])

    with open("outputs/experiment_results.json", "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2)

    print("\n✅ Results saved")

if __name__ == "__main__":
    main()
