import json
import os

import requests
from groq import Groq

# Mengambil API key Groq dan Telegram dari Environment Variables
GROQ_API_KEY = os.environ.get("GROQ_API_KEY")
TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID")

SYSTEM_PROMPT = r"""Anda adalah pakar pembuat soal matematika SMA.
Tugas Anda adalah membuat 1 soal matematika harian beserta pembahasannya dalam format JSON.

ATURAN STRUKTUR LATEX (SANGAT PENTING):
1. PISAHKAN teks penjelasan dan rumus matematika!
   - Gunakan teks biasa untuk narasi/penjelasan (Gunakan \textbf{...} untuk judul/penekanan).
   - Gunakan blok $$ ... $$ untuk rumus matematika yang berdiri sendiri (display math).
   - Gunakan \( ... \) untuk variabel/angka tipis di dalam kalimat.
2. DILARANG BUKANNYA MEMASUKKAN KALIMAT PANJANG KE DALAM \text{...} DI DALAM RUMUS!
3. DILARANG menggunakan tanda '+' di antara kata-kata teks biasa.

Format Output JSON HARUS persis seperti contoh berikut:
{
  "soal_latex": "\textbf{SOAL MATEMATIKA HARIAN} \\[10pt] \text{Hitung nilai integral tentu berikut:} \\[10pt] \int_{1}^{3} (2x^2-4x+3)\,dx",
  "pembahasan_latex": "\textbf{KUNCI JAWABAN \& PEMBAHASAN} \\[10pt] \int (2x^2-4x+3)\,dx = \frac{2}{3}x^3-2x^2+3x \\[10pt] \text{Substitusikan batas } 1 \text{ dan } 3: \\[10pt] \left[\frac{2}{3}x^3-2x^2+3x\right]_1^3 \\[10pt] \text{Untuk } x=3: \\[10pt] \frac{2}{3}(27)-2(9)+3(3)=9 \\[10pt] \text{Untuk } x=1: \\[10pt] \frac{2}{3}-2+3=\frac{5}{3} \\[10pt] \text{Maka:} \\[10pt] 9-\frac{5}{3}=\frac{22}{3} \\[10pt] \textbf{Jawaban: } \boxed{\frac{22}{3}}"
}
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
