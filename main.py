import os
import time

import requests
from google import genai
from google.genai import types
from groq import Groq

GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")
GROQ_API_KEY = os.environ.get("GROQ_API_KEY")
TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID")

PROMPT = (
    "Buatkan 1 soal matematika tingkat menengah (SMA/Sederajat) beserta pembahasannya. "
    "Format output WAJIB persis seperti berikut:\n"
    "📐 *SOAL MATEMATIKA HARIAN*\n\n"
    "[Tuliskan isi soal di sini]\n\n"
    "---------------\n"
    "💡 *KUNCI JAWABAN & PEMBAHASAN*:\n"
    "||[Tuliskan kunci jawaban dan langkah singkat di sini]||"
)


def escape_markdown_v2(text: str) -> str:
    """Mengamankan karakter khusus untuk Telegram MarkdownV2."""
    special_chars = r"\_[]()~`>#+-={}.!"
    for char in special_chars:
        text = text.replace(char, f"\\{char}")
    return text


def generate_with_gemini() -> str:
    """Mencoba membuat soal menggunakan Gemini API."""
    if not GEMINI_API_KEY:
        raise ValueError("GEMINI_API_KEY tidak ditemukan")

    models = ["gemini-2.0-flash", "gemini-1.5-flash"]
    with genai.Client(api_key=GEMINI_API_KEY) as client:
        config = types.GenerateContentConfig(
            automatic_function_calling=types.AutomaticFunctionCallingConfig(
                disable=True
            )
        )
        for model in models:
            try:
                print(f"Mencoba Gemini ({model})...")
                response = client.models.generate_content(
                    model=model, contents=PROMPT, config=config
                )
                if response.text:
                    return response.text
            except Exception as e:
                print(f"Gemini ({model}) gagal: {e}")
    raise RuntimeError("Semua model Gemini gagal.")


def generate_with_groq() -> str:
    """Mencoba membuat soal menggunakan Groq API (Fallback Gratis)."""
    if not GROQ_API_KEY:
        raise ValueError("GROQ_API_KEY tidak ditemukan")

    print("Mencoba Groq API (Llama 3.3 70B)...")
    client = Groq(api_key=GROQ_API_KEY)

    completion = client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=[
            {
                "role": "system",
                "content": "Anda adalah pembuat soal matematika profesional.",
            },
            {"role": "user", "content": PROMPT},
        ],
        temperature=0.7,
    )
    return completion.choices[0].message.content


def buat_soal() -> str:
    # # 1. Coba Gemini dulu
    # try:
    #     return generate_with_gemini()
    # except Exception as e:
    #     print(f"Beralih ke Groq karena Gemini error: {e}")

    # 2. Fallback ke Groq jika Gemini gagal
    try:
        return generate_with_groq()
    except Exception as e:
        print(f"Groq juga gagal: {e}")

    raise Exception("Gagal membuat soal dari seluruh provider (Gemini & Groq).")


def kirim_notifikasi(pesan: str):
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"

    payload = {
        "chat_id": TELEGRAM_CHAT_ID,
        "text": escape_markdown_v2(pesan),
        "parse_mode": "MarkdownV2",
    }

    res = requests.post(url, json=payload)

    # Fallback ke plain text jika parsing MarkdownV2 gagal
    if not res.ok:
        payload["parse_mode"] = ""
        payload["text"] = pesan
        requests.post(url, json=payload)


if __name__ == "__main__":
    soal = buat_soal()
    kirim_notifikasi(soal)
    print("Berhasil mengirim soal ke Telegram!")
