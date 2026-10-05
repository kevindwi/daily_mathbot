import json
import os
import urllib.parse

import requests

GROQ_API_KEY = os.environ.get("GROQ_API_KEY")
TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID")

SYSTEM_PROMPT = """Anda adalah pembuat soal matematika profesional.
Tugas Anda adalah membuat 1 soal matematika tingkat menengah (SMA/Sederajat) beserta pembahasannya.

Aturan Penulisan LaTeX QuickLaTeX:
1. Bungkus persamaan matematika dengan sintaks LaTeX standar ($...$ untuk inline, \\[...\\] untuk display).
2. Gunakan \\text{...} untuk teks penjelasan di dalam rumus.
3. Untuk ganti baris pada teks penjelasan, gunakan \\\\

Format Output HARUS dalam format JSON murni persis seperti berikut:
{
  "soal_latex": "\\\\textbf{Sebuah segitiga siku-siku} memiliki panjang sisi $a$ dan $b$.\\\\\\\\[1ex] Diketahui $a:b = 3:4$ dan kelilingnya $30\\text{ cm}$.\\\\\\\\[1ex] \\\\textbf{Tentukan:} panjang sisi $a$, $b$, dan sisi miring $c$!",
  "pembahasan_latex": "Misalkan $a = 3k$ dan $b = 4k$\\\\\\\[1ex] Sisi miring $c = \\\\sqrt{a^2 + b^2} = \\\\sqrt{(3k)^2 + (4k)^2} = 5k$\\\\\\\[1ex] \\\\text{Keliling } = a + b + c = 30\\\\\\\\[1ex] 3k + 4k + 5k = 30 \\\\Rightarrow 12k = 30 \\\\Rightarrow k = 2.5\\\\\\\\[1ex] a = 3(2.5) = 7.5\\text{ cm}\\\\\\\[1ex] b = 4(2.5) = 10\\text{ cm}\\\\\\\[1ex] c = 5(2.5) = 12.5\\text{ cm}"
}
"""


def generate_quicklatex_image_url(latex_code: str) -> str:
    """
    Mengirimkan kode LaTeX ke QuickLaTeX API dan mengembalikan URL gambar PNG.
    """
    url = "https://quicklatex.com/latex3.im"

    # Menambahkan konfigurasi QuickLaTeX (fontsize 18px, warna teks gelap, resolusi tinggi)
    full_latex = (
        r"\documentclass{article}"
        "\n"
        r"\usepackage{amsmath,amsfonts,amssymb}"
        "\n"
        r"\begin{document}"
        "\n"
        r"\thispagestyle{empty}"
        "\n"
        f"{latex_code}"
        "\n"
        r"\end{document}"
    )

    payload = {
        "formula": full_latex,
        "fsize": "18px",
        "fcolor": "000000",
        "mode": "0",
        "out": "1",
        "removespaces": "1",
    }

    # API QuickLaTeX membutuhkan format x-www-form-urlencoded
    response = requests.post(url, data=payload)
    if response.status_code == 200:
        # Response QuickLaTeX mengembalikan teks: "0\n<image_url>\n<width>\n<height>"
        lines = response.text.splitlines()
        if len(lines) >= 2 and lines[0] == "0":
            return lines[1].strip()

    raise RuntimeError(f"Gagal generate QuickLaTeX: {response.text}")


def buat_soal() -> dict:
    if not GROQ_API_KEY:
        raise ValueError("GROQ_API_KEY tidak ditemukan!")

    from groq import Groq

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
    Mengirimkan URL gambar ke Telegram.
    Jika has_spoiler=True, gambarnya otomatis diburamkan oleh Telegram.
    """
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendPhoto"

    payload = {
        "chat_id": TELEGRAM_CHAT_ID,
        "photo": image_url,
        "caption": caption,
        "parse_mode": "Markdown",
        "has_spoiler": has_spoiler,  # Menyembunyikan gambar dengan efek buram/spoiler
    }

    res = requests.post(url, data=payload)
    if not res.ok:
        print(f"Gagal mengirim foto ke Telegram: {res.text}")


if __name__ == "__main__":
    print("1. Membuat soal matematika menggunakan Groq...")
    data = buat_soal()

    print("2. Render LaTeX ke Gambar via QuickLaTeX API...")
    url_soal = generate_quicklatex_image_url(data["soal_latex"])
    url_pembahasan = generate_quicklatex_image_url(data["pembahasan_latex"])

    print("3. Mengirim Gambar Soal ke Telegram...")
    kirim_gambar_telegram(
        image_url=url_soal, caption="📐 *SOAL MATEMATIKA HARIAN*", has_spoiler=False
    )

    print("4. Mengirim Gambar Pembahasan (Tersebunyi/Spoiler)...")
    kirim_gambar_telegram(
        image_url=url_pembahasan,
        caption="💡 *KUNCI JAWABAN & PEMBAHASAN* (Ketuk gambar untuk melihat)",
        has_spoiler=True,
    )

    print("Selesai! Berhasil terkirim ke Telegram.")
