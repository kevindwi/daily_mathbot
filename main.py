import json
import os
from urllib.parse import quote

import requests
from groq import Groq

# Mengambil API key Groq dan Telegram dari Environment Variables
GROQ_API_KEY = os.environ.get("GROQ_API_KEY")
TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID")

SYSTEM_PROMPT = r"""
Anda adalah pakar pembuat soal matematika SMA.
Tugas Anda adalah membuat 1 soal matematika harian beserta pembahasannya dalam format JSON.

ATURAN LATEX UNTUK QUICKLATEX:
1. Anda BOLEH menggunakan $$ ... $$ atau \[ ... \] untuk rumus matematika terpisah (display math).
2. DILARANG meletakkan \\[10pt] di dalam atau tepat di samping $$ ... $$. Gunakan baris baru biasa di dalam string JSON jika menggunakan $$.
3. Teks narasi di luar $$ harus dibungkus dengan \text{...} atau \textbf{...} jika bercampur dengan baris LaTeX lainnya.
4. Karakter ampersand HARUS di-escape menjadi \&.

Format Output JSON:
{
  "soal_latex": "\\textbf{SOAL MATEMATIKA HARIAN} \\\\[10pt] \\text{Hitung nilai integral tentu berikut:} \\\\[10pt] \\int_{1}^{3} (2x^2-4x+3)\\,dx",
  "pembahasan_latex": "\\textbf{KUNCI JAWABAN \\& PEMBAHASAN} \\\\[10pt] \\text{Turunan pertama:} $$f'(x) = -4x + 8$$ \\text{Set } f'(x) = 0 \\text{ untuk titik kritis:} $$-4x + 8 = 0 \\Rightarrow x = 2$$ \\text{Hitung } f(2): $$f(2) = 13$$ \\textbf{Jawaban: } \\boxed{13}"
}
"""


def generate_quicklatex_url(latex_code: str) -> str:
    url = "https://quicklatex.com/latex3.f"

    # Encoding aman untuk LaTeX dan Preamble
    encoded_formula = quote(latex_code)
    preamble = quote(
        r"\usepackage{amsmath}\n\usepackage{amsfonts}\n\usepackage{amssymb}"
    )

    body_raw = (
        f"formula={encoded_formula}"
        f"&fsize=17px&fcolor=000000&mode=0&out=1&remhost=quicklatex.com"
        f"&preamble={preamble}&rnd=81.72740052257099"
    )

    headers = {
        "Accept": "*/*",
        "Accept-Language": "id-ID,id;q=0.9,en-US;q=0.8,en;q=0.7",
        "Content-Type": "application/x-www-form-urlencoded",
        "X-Requested-With": "XMLHttpRequest",
        "Referer": "https://quicklatex.com/",
    }

    res = requests.post(url, data=body_raw, headers=headers)

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
    print(data["soal_latex"])
    print(data["pembahasan_latex"])

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
