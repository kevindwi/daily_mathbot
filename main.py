import os

import requests
from groq import Groq

# Ambil Environment Variables dari GitHub Secrets
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


def buat_soal() -> str:
    if not GROQ_API_KEY:
        raise ValueError("GROQ_API_KEY tidak ditemukan pada Environment Variables.")

    client = Groq(api_key=GROQ_API_KEY)

    # Menggunakan Llama 3.3 70B Versatile (Gratis & Sangat Cepat)
    completion = client.chat.completions.create(
        model="openai/gpt-oss-120b",
        messages=[
            {
                "role": "system",
                "content": "Anda adalah guru matematika profesional yang membuat soal berkualitas.",
            },
            {"role": "user", "content": PROMPT},
        ],
        temperature=0.7,
    )

    return completion.choices[0].message.content


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
    print("Membuat soal menggunakan Groq API...")
    soal = buat_soal()
    kirim_notifikasi(soal)
    print("Berhasil membuat dan mengirim soal ke Telegram!")
