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
    Mengirimkan teks LaTeX ke QuickLaTeX API dan mengembalikan URL gambar PNG bersih.
    """
    url = "https://quicklatex.com/latex3.f"

    headers = {
        "Content-Type": "application/x-www-form-urlencoded",
        "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36",
    }

    payload = {
        "formula": latex_code,
        "fsize": "18px",
        "fcolor": "000000",
        "mode": "0",
        "out": "1",
        "remhost": "quicklatex.com",
        "preamble": "\\usepackage{amsmath}\n\\usepackage{amsfonts}\n\\usepackage{amssymb}",
    }

    res = requests.post(url, data=payload, headers=headers)

    if res.status_code == 200:
        lines = res.text.strip().splitlines()
        if len(lines) >= 2 and lines[0].strip() == "0":
            # Baris ke-2 biasanya berisi: "https://...png 0 632 96"
            # Kita split berdasarkan spasi dan ambil bagian pertamanya saja (URL asli)
            raw_url_line = lines[1].strip()
            clean_url = raw_url_line.split()[0]
            return clean_url

    raise RuntimeError(f"Gagal generate QuickLaTeX: {res.text}")


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
    Mengunduh gambar dari QuickLaTeX lalu mengunggah file-nya langsung ke Telegram.
    Metode ini mencegah error 'failed to get HTTP URL content'.
    """
    # 1. Unduh gambar dari QuickLaTeX ke memory/file sementara
    img_res = requests.get(image_url, headers={"User-Agent": "Mozilla/5.0"})

    if img_res.status_code != 200:
        print(f"Gagal mendownload gambar dari QuickLaTeX URL: {image_url}")
        return

    # 2. Kirim file gambar secara langsung ke API Telegram
    telegram_url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendPhoto"

    data_payload = {
        "chat_id": TELEGRAM_CHAT_ID,
        "caption": caption,
        "parse_mode": "Markdown",
        "has_spoiler": str(
            has_spoiler
        ).lower(),  # Telegram menerima boolean dalam format 'true'/'false'
    }

    # Upload sebagai bytes stream
    files_payload = {"photo": ("formula.png", img_res.content, "image/png")}

    res = requests.post(telegram_url, data=data_payload, files=files_payload)

    if not res.ok:
        print(f"Gagal mengirim foto ke Telegram: {res.text}")
    else:
        print(f"Berhasil terkirim!")


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
