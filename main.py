import json
import os
import re

import requests
from groq import Groq

# Mengambil API key Groq dan Telegram dari Environment Variables
GROQ_API_KEY = os.environ.get("GROQ_API_KEY")
TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID")

SYSTEM_PROMPT = r"""Anda adalah pakar pembuat soal matematika.
Tugas Anda adalah membuat 1 soal matematika SMA beserta pembahasannya dalam format JSON.

PENTING DAN WAJIB DIPATUHI:
1. DILARANG HARDCODE TANDA '+' DI ANTARA KATA ATAU DI AWAL/AKHIR BARIS! Gunakan spasi biasa untuk memisahkan kata.
2. Gunakan tanda '+' HANYA untuk operasi penjumlahan matematika (contoh: x + 2).
3. Jangan gunakan emoji atau markdown Telegram (*, _) di dalam nilai JSON.

Contoh Output JSON yang BENAR:
{
  "soal_latex": "\\textbf{Soal:}\\\\[1ex]\nDiberikan fungsi $f(x) = x^3 - 6x^2 + 9x + 1$.\n\\begin{enumerate}\n  \\item Tentukan semua nilai $x$ yang memenuhi $f'(x) = 0$.\n  \\item Klasifikasikan masing-masing titik kritis tersebut.\n\\end{enumerate}",
  "pembahasan_latex": "\\textbf{Pembahasan:}\\\\[1ex]\nTurunan pertama:\n\\begin{align*}\nf'(x) &= 3x^2 - 12x + 9 \\\\[1ex]\n&= 3(x^2 - 4x + 3) \\\\[1ex]\n&= 3(x - 1)(x - 3)\n\\end{align*}\\\\[1ex]\nJadi $f'(x) = 0 \\implies x = 1$ atau $x = 3$."
}
"""


def clean_latex_string(code: str) -> str:
    """
    Membersihkan tanda '+' liar yang sering dihasilkan oleh model LLM tertentu.
    """
    # 1. Hapus tanda '+' yang menempel di awal kata/kalimat (misal: '+Diberikan' -> 'Diberikan')
    code = re.sub(r"(?<=[\s\\\[\]\(\)\{\}])\+(?=\w)", "", code)
    code = re.sub(r"^\s*\+", "", code, flags=re.MULTILINE)

    # 2. Hapus tanda '+' di akhir baris (misal: '9+ \\' atau 'lokal.+' -> '9 \\' atau 'lokal.')
    code = re.sub(r"\+\s*(\\\\|\n|$)", r"\1", code)

    # 3. Ubah tanda '+' terisolasi di antara kata teks biasa menjadi spasi
    # (misal: 'maksimum+lokal' -> 'maksimum lokal')
    code = re.sub(r"([a-zA-Z0-9.,])\+([a-zA-Z0-9.,])", r"\1 \2", code)

    return code


def generate_quicklatex_url(latex_code: str) -> str:
    """
    Mengirimkan teks LaTeX ke QuickLaTeX API dan mengembalikan URL gambar PNG bersih.
    """
    url = "https://quicklatex.com/latex3.f"

    # Bersihkan kode LaTeX dari tanda '+' liar sebelum dikirim ke QuickLaTeX
    cleaned_code = clean_latex_string(latex_code)

    payload = {
        "formula": cleaned_code,
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
