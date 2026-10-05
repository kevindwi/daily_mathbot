import os

import requests
from google import genai

# Ambil Environment Variables dari GitHub Secrets
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")
TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID")


def escape_markdown_v2(text: str) -> str:
    """
    Mengamankan karakter khusus untuk Telegram MarkdownV2,
    tanpa merusak sintaks spoiler ||...|| dan bold *...*
    """
    special_chars = r"\_[]()~`>#+-={}.!"
    for char in special_chars:
        text = text.replace(char, f"\\{char}")
    return text


def buat_soal() -> str:
    prompt = (
        "Buatkan 1 soal matematika tingkat menengah (SMA/Sederajat) beserta pembahasannya. "
        "Format output WAJIB persis seperti berikut:\n"
        "📐 *SOAL MATEMATIKA HARIAN*\n\n"
        "[Tuliskan isi soal di sini]\n\n"
        "---------------\n"
        "💡 *KUNCI JAWABAN & PEMBAHASAN*:\n"
        "||[Tuliskan kunci jawaban dan langkah singkat di sini]||"
    )

    # Membuka client menggunakan Context Manager sesuai dokumentasi
    with genai.Client(api_key=GEMINI_API_KEY) as client:
        response = client.models.generate_content(
            model="gemini-3.8-flash",
            contents=prompt,
        )
        return response.text


def kirim_notifikasi(pesan: str):
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"

    # Format Telegram menggunakan MarkdownV2 untuk mendukung ||spoiler||
    payload = {
        "chat_id": TELEGRAM_CHAT_ID,
        "text": escape_markdown_v2(pesan),
        "parse_mode": "MarkdownV2",
    }

    res = requests.post(url, json=payload)

    # Fallback jika ada kesalahan parsing Markdown dari teks AI
    if not res.ok:
        payload["parse_mode"] = ""
        payload["text"] = pesan
        requests.post(url, json=payload)


if __name__ == "__main__":
    soal = buat_soal()
    kirim_notifikasi(soal)
