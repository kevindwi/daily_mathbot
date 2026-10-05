import os

import requests
from google import genai

# Konfigurasi Environment Variables
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")
TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID")

# Inisialisasi Client SDK Baru
client = genai.Client(api_key=GEMINI_API_KEY)


def buat_soal():
    prompt = (
        "Buatkan 1 soal matematika tingkat menengah (SMA/Sederajat) beserta jawabannya. "
        "Format output harus:\n"
        "📐 *SOAL MATEMATIKA HARIAN*\n\n"
        "[Isi Soal]\n\n"
        "---------------\n"
        "💡 *KUNCI JAWABAN & PEMBAHASAN* (Disembunyikan):\n"
        "||[Kunci Jawaban Singkat & Pembahasan Ringkas]||"
    )
    # Menggunakan model gemini-2.5-flash terbaru
    response = client.models.generate_content(
        model="gemini-2.5-flash",
        contents=prompt,
    )
    return response.text


def kirim_notifikasi(pesan):
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {"chat_id": TELEGRAM_CHAT_ID, "text": pesan, "parse_mode": "Markdown"}
    requests.post(url, json=payload)


if __name__ == "__main__":
    soal = buat_soal()
    kirim_notifikasi(soal)
