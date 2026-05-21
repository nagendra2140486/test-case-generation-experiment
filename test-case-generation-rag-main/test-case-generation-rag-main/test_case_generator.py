import json
import time
from datetime import datetime
import ollama
from docx import Document

OLLAMA_HOST = "http://10.120.100.16/ollama"
# ── DOCX READER ─────────────────────────
def read_docx(file_path):
    doc = Document(file_path)
    return "\n".join([p.text.strip() for p in doc.paragraphs if p.text.strip()])

# ── CHUNKING ───────────────────────────
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

# ── CONFIG ───────────────────────────
client = ollama.Client(
    host=OLLAMA_HOST,
    headers={"Authorization": f"Bearer {API_KEY}"}
)


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

SYSTEM_PROMPT = "Generate test cases."

# ── CORE FUNCTION ─────────────────────
def generate(user_story, context):

    start = time.time()

    try:
        response = client.chat(
            model=MODELS[0],
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
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

    except:
        return {"tokens": 0, "time": 0}

# ── RUN ───────────────────────────────
def main():

    results = []

    for story in TEXTS:

        A = generate(story, FULL_BRD_CONTEXT)
        B = generate(story, get_chunk_context(story))

        results.append({
            "path_A": A,
            "path_B": B
        })

    with open("outputs/experiment_results.json", "w") as f:
        json.dump(results, f, indent=2)

    print("✅ Generator Done")

if __name__ == "__main__":
    main()
