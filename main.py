import os
import time

import requests
from google import genai
from google.genai import types
from google.genai.errors import APIError

GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")
TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID")

# Daftar model utama dan cadangan jika model utama sibuk (503)
AVAILABLE_MODELS = [
    "gemini-3.8-flash",
    "gemini-3.5-flash",
    "gemini-3.6-flash",
    "gemini-3.7-flash",
]


def escape_markdown_v2(text: str) -> str:
    """Mengamankan karakter khusus untuk Telegram MarkdownV2."""
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

    with genai.Client(api_key=GEMINI_API_KEY) as client:
        config = types.GenerateContentConfig(
            automatic_function_calling=types.AutomaticFunctionCallingConfig(
                disable=True
            )
        )

        # Mencoba setiap model yang ada di daftar jika terjadi error 503/server busy
        for model_name in AVAILABLE_MODELS:
            for attempt in range(2):  # Coba max 2x per model
                try:
                    print(f"Mencoba membuat soal dengan model: {model_name}...")
                    response = client.models.generate_content(
                        model=model_name,
                        contents=prompt,
                        config=config,
                    )
                    if response.text:
                        return response.text
                except APIError as e:
                    print(f"Gagal pada {model_name} (Percobaan {attempt + 1}): {e}")
                    time.sleep(3)  # Tunggu 3 detik sebelum coba lagi
                except Exception as e:
                    print(f"Error tidak terduga pada {model_name}: {e}")
                    break

    raise Exception(
        "Semua model Gemini sedang tidak tersedia atau mengalami high demand."
    )


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
    print("Berhasil membuat dan mengirim soal ke Telegram!")
