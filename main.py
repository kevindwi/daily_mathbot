import json
import os

import requests
from groq import Groq

# Mengambil API key Groq dan Telegram dari Environment Variables
GROQ_API_KEY = os.environ.get("GROQ_API_KEY")
TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID")

SYSTEM_PROMPT = r"""Anda adalah pakar pembuat soal matematika SMA.
Tugasmu adalah membuat soal matematika beserta pembahasannya dalam format JSON valid.\n\nAturan Format JSON:\n1. Output HARUS berupa JSON valid dengan struktur: {\"soal_latex\": \"...\", \"pembahasan_latex\": \"...\"}.\n2. Jangan tambahkan teks pembuka atau penutup di luar JSON.\n\nAturan Penulisan LaTeX (QuickLaTeX Compatible):\n1. Setiap nilai/field JSON (`soal_latex` dan `pembahasan_latex`) HARUS ditulis dalam SATU BARIS UTUH (tanpa newlines/break lines nyata di dalam string JSON).\n2. Gunakan `\\[10pt]` untuk membuat jarak antar baris tampilan hasil render.\n3. Teks biasa di dalam math mode harus dibungkus dengan `\\text{...}`.\n4. Escape karakter khusus seperti `&` menjadi `\\&`.\n5. Gunakan `\\boxed{...}` untuk memperjelas jawaban akhir.
"""


def generate_quicklatex_url(latex_code: str) -> str:
    """
    Mengirimkan teks LaTeX ke QuickLaTeX API dan mengembalikan URL gambar PNG bersih.
    """
    url = "https://quicklatex.com/latex3.f"

    # Payload dikirimkan ke QuickLaTeX
    payload = {
        "formula": latex_code,
        "fsize": "17px",
        "fcolor": "000000",
        "mode": "0",
        "out": "1",
        "remhost": "quicklatex.com",
        "preamble": r"""\usepackage{amsmath}
\usepackage{amsfonts}
\usepackage{amssymb}
\usepackage[indonesian]{babel}""",
    }

    headers = {"User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36"}

    res = requests.post(url, data=payload, headers=headers)

    if res.status_code == 200:
        lines = res.text.strip().splitlines()
        if len(lines) >= 2 and lines[0].strip() == "0":
            # Ambil URL murni sebelum spasi
            raw_url = lines[1].strip().split()[0]
            return raw_url

    raise RuntimeError(f"Gagal generate QuickLaTeX: {res.text}")


def buat_soal() -> dict:
    """
    Membuat soal menggunakan Client SDK Groq dan model openai/gpt-oss-120b
    """
    client = Groq(api_key=GROQ_API_KEY)

    completion = client.chat.completions.create(
        model="openai/gpt-oss-120b",
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {
                "role": "user",
                "content": "Buatkan 1 soal matematika harian beserta pembahasannya.",
            },
        ],
        response_format={"type": "json_object"},
        temperature=0.6,
    )

    return json.loads(completion.choices[0].message.content)


def kirim_gambar_telegram(image_url: str, caption: str, has_spoiler: bool = False):
    """
    Mengunduh gambar dari QuickLaTeX lalu mengirimkannya sebagai file ke Telegram.
    """
    img_res = requests.get(image_url, headers={"User-Agent": "Mozilla/5.0"})

    if img_res.status_code != 200:
        print(f"Gagal mendownload gambar dari URL: {image_url}")
        return

    telegram_url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendPhoto"

    data_payload = {
        "chat_id": TELEGRAM_CHAT_ID,
        "caption": caption,
        "parse_mode": "Markdown",
        "has_spoiler": str(has_spoiler).lower(),
    }

    files_payload = {"photo": ("formula.png", img_res.content, "image/png")}

    res = requests.post(telegram_url, data=data_payload, files=files_payload)
    if not res.ok:
        print(f"Gagal mengirim foto ke Telegram: {res.text}")
    else:
        print("Berhasil terkirim!")


if __name__ == "__main__":
    print("1. Membuat soal matematika menggunakan Groq (openai/gpt-oss-120b)...")
    data = buat_soal()
    print(data)

    print("2. Render Soal ke QuickLaTeX...")
    url_soal = generate_quicklatex_url(data["soal_latex"])

    print("3. Render Pembahasan ke QuickLaTeX...")
    url_pembahasan = generate_quicklatex_url(data["pembahasan_latex"])

    print("4. Mengirim Gambar Soal ke Telegram...")
    kirim_gambar_telegram(url_soal, "📐 *SOAL MATEMATIKA HARIAN*", has_spoiler=False)

    print("5. Mengirim Gambar Pembahasan (Tersembunyi/Spoiler) ke Telegram...")
    kirim_gambar_telegram(
        url_pembahasan, "💡 *KUNCI JAWABAN & PEMBAHASAN*", has_spoiler=True
    )
