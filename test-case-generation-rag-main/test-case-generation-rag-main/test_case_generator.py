import json
import time
import ollama
from docx import Document

# ── CONFIG ───────────────────────────
OLLAMA_HOST = "http://10.120.100.16/ollama"
API_KEY = "sk-xxxxxxxxxxxxxxxx"   # ✅ PUT YOUR REAL KEY HERE

client = ollama.Client(
    host=OLLAMA_HOST,
    headers={"Authorization": f"Bearer {API_KEY}"}
)

# ── DOCX READER ─────────────────────
def read_docx(file_path):
    doc = Document(file_path)
    return "\n".join([p.text.strip() for p in doc.paragraphs if p.text.strip()])

# ── CHUNKING ─────────────────────────
def get_chunk_context(user_story: str):
    story = user_story.lower()

    if "register" in story:
        return read_docx("data/01_user_onboarding.docx") + read_docx("data/07_global_concerns.docx")
    elif "login" in story:
        return read_docx("data/02_authentication.docx") + read_docx("data/07_global_concerns.docx")
    elif "card" in story or "wallet" in story:
        return read_docx("data/03_wallet_and_cards.docx") + read_docx("data/07_global_concerns.docx")
    elif "send money" in story:
        return read_docx("data/04_p2p_transfers.docx") + read_docx("data/07_global_concerns.docx")
    elif "qr" in story:
        return read_docx("data/05_merchant_payments.docx") + read_docx("data/07_global_concerns.docx")
    else:
        return read_docx("data/07_global_concerns.docx")

# ── DATA ─────────────────────────────
TEXTS = [
    "US-01: Register using mobile number",
    "US-02: Login using PIN",
    "US-03: Link card",
    "US-04: Add money",
    "US-05: Send money",
]

FULL_BRD_CONTEXT = read_docx("data/01_BRD_SwiftPay_v2.docx")[:4000]

# ── CORE FUNCTION ───────────────────
def generate(user_story, context):

    start = time.time()

    try:
        response = client.chat(
            model="llama3.2:latest",
            messages=[
                {"role": "system", "content": "Generate test cases."},
                {"role": "user", "content": context + "\n" + user_story}
            ],
            options={"num_predict": 700}
        )

        content = response.message.content if response.message else ""

        input_tokens = max(len(context)//4, 50)
        output_tokens = max(len(content)//4, 20)

        total_tokens = input_tokens + output_tokens
        duration = (time.time() - start) * 1000

        return {
            "tokens": total_tokens,
            "time": duration
        }

    except Exception as e:
        print("Error:", e)
        return {"tokens": 0, "time": 0}

# ── MAIN ────────────────────────────
def main():

    results = []

    for story in TEXTS:
        A = generate(story, FULL_BRD_CONTEXT)
        B = generate(story, get_chunk_context(story))

        results.append({
            "user_story": story,
            "path_A": A,
            "path_B": B
        })

    with open("outputs/experiment_results.json", "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2)

    print("✅ Generator Done")

if __name__ == "__main__":
    main()
