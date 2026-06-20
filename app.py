"""
SummaRise - AI Text Summarizer
Aplikasi web sederhana berbasis Streamlit untuk merangkum teks panjang
menggunakan Google Gemini API.
"""

import streamlit as st
from google import genai
from google.genai import types

# ============================================================
# KONFIGURASI HALAMAN
# ============================================================
st.set_page_config(page_title="SummaRise - AI Text Summarizer", page_icon="📝", layout="centered")

st.title("📝 SummaRise")
st.caption("Ringkas teks panjang (artikel/berita) jadi poin-poin penting menggunakan Gemini API")

# ============================================================
# SIDEBAR: API KEY & INFO MODEL
# ============================================================
with st.sidebar:
    st.header("⚙️ Konfigurasi")
    api_key = st.text_input(
        "Google Gemini API Key",
        type="password",
        help="Belum punya API key? Daftar gratis di Google AI Studio.",
    )
    st.markdown("[➜ Daftar API Key di Google AI Studio](https://aistudio.google.com/apikey)")
    st.divider()
    st.caption("Model yang dipakai: `gemini-2.5-flash-lite`")
    st.caption("(Gemini 1.5 sudah tidak aktif per 2026, jadi proyek ini sudah disesuaikan ke model terbaru)")

# ============================================================
# KONFIGURASI PANJANG RINGKASAN
# ============================================================
# Struktur Dictionary {} -- sesuai acuan koding di PRD
LENGTH_CONFIG = {
    "Pendek": {"max_tokens": 100, "poin": 3},
    "Sedang": {"max_tokens": 200, "poin": 5},
    "Panjang": {"max_tokens": 300, "poin": 7},
}

# ============================================================
# INPUT PENGGUNA
# ============================================================
text_input = st.text_area(
    "Masukkan teks (artikel/berita) yang ingin diringkas",
    height=250,
    placeholder="Paste teks panjang di sini...",
)

length_choice = st.radio(
    "Pilih panjang ringkasan",
    options=list(LENGTH_CONFIG.keys()),
    horizontal=True,
    index=1,
)

# ============================================================
# PROSES RANGKUM TEKS
# ============================================================
if st.button("🔍 Rangkum Teks", type="primary", use_container_width=True):
    if not api_key:
        st.error("Masukkan API Key Gemini terlebih dahulu di sidebar.")
    elif not text_input.strip():
        st.warning("Masukkan teks yang ingin diringkas terlebih dahulu.")
    else:
        config = LENGTH_CONFIG[length_choice]

        # Sistem prompt otomatis -- sesuai requirement 4.1
        system_prompt = (
            f"Rangkum teks berikut ini menjadi maksimal {config['poin']} poin penting "
            f"dalam Bahasa Indonesia. Gunakan format bullet point yang jelas dan padat:\n\n"
            f"{text_input}"
        )

        # Struktur generation_config -- Dictionary {} dan List []
        generation_config = {
            "temperature": 0.7,
            "max_output_tokens": config["max_tokens"],
            "stop_sequences": [],
        }

        try:
            with st.spinner("Sedang merangkum teks..."):
                client = genai.Client(api_key=api_key)
                response = client.models.generate_content(
                    model="gemini-2.5-flash-lite",
                    contents=system_prompt,
                    config=types.GenerateContentConfig(
                        temperature=generation_config["temperature"],
                        max_output_tokens=generation_config["max_output_tokens"],
                        stop_sequences=generation_config["stop_sequences"],
                    ),
                )

            st.subheader("📋 Hasil Ringkasan")
            st.write(response.text)

            # ---- Token & Cost Tracker -- requirement 4.2 ----
            usage = response.usage_metadata
            st.subheader("📊 Token Usage")
            col1, col2, col3 = st.columns(3)
            col1.metric("Input Tokens", usage.prompt_token_count)
            col2.metric("Output Tokens", usage.candidates_token_count)
            col3.metric("Total Tokens", usage.total_token_count)

        except Exception as e:
            st.error(f"Terjadi kesalahan saat memanggil API: {e}")
