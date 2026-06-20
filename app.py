"""
SummaRise - AI Text Summarizer & Assistant
Streamlit app: ringkas teks, terjemahkan, dan tanya-jawab berbasis dokumen,
menggunakan Google Gemini API.
"""

import streamlit as st
from google import genai
from google.genai import types
from pypdf import PdfReader
from docx import Document

# ============================================================
# KONFIGURASI HALAMAN
# ============================================================
st.set_page_config(page_title="SummaRise", page_icon="📝", layout="centered")
st.title("📝 SummaRise")
st.caption("Ringkas, terjemahkan, dan tanya-jawab dengan teks/dokumen kamu menggunakan Gemini API")

MODEL_NAME = "gemini-2.5-flash-lite"


# ============================================================
# API KEY: ambil dari Secrets kalau ada, kalau tidak minta input manual
# ============================================================
def get_secret_api_key():
    try:
        return st.secrets["GEMINI_API_KEY"]
    except Exception:
        return None


secret_key = get_secret_api_key()

with st.sidebar:
    st.header("⚙️ Konfigurasi")
    if secret_key:
        api_key = secret_key
        st.success("✅ API Key aktif (dari Secrets)")
    else:
        api_key = st.text_input(
            "Google Gemini API Key",
            type="password",
            help="Belum punya API key? Daftar gratis di Google AI Studio.",
        )
        st.markdown("[➜ Daftar API Key di Google AI Studio](https://aistudio.google.com/apikey)")
        st.caption("💡 Tip: simpan key permanen lewat Secrets, lihat README.")
    st.divider()
    st.caption(f"Model: `{MODEL_NAME}`")


# ============================================================
# HELPER: panggil Gemini API
# ============================================================
def call_gemini(prompt, max_output_tokens=500, temperature=0.7):
    client = genai.Client(api_key=api_key)
    response = client.models.generate_content(
        model=MODEL_NAME,
        contents=prompt,
        config=types.GenerateContentConfig(
            temperature=temperature,
            max_output_tokens=max_output_tokens,
            stop_sequences=[],
        ),
    )
    return response


def show_token_usage(usage):
    col1, col2, col3 = st.columns(3)
    col1.metric("Input Tokens", usage.prompt_token_count)
    col2.metric("Output Tokens", usage.candidates_token_count)
    col3.metric("Total Tokens", usage.total_token_count)


# ============================================================
# HELPER: ekstrak teks dari file upload
# ============================================================
def extract_text(uploaded_file):
    uploaded_file.seek(0)
    name = uploaded_file.name.lower()
    if name.endswith(".pdf"):
        reader = PdfReader(uploaded_file)
        return "\n".join((page.extract_text() or "") for page in reader.pages)
    elif name.endswith(".docx"):
        doc = Document(uploaded_file)
        return "\n".join(p.text for p in doc.paragraphs)
    elif name.endswith(".txt"):
        return uploaded_file.read().decode("utf-8", errors="ignore")
    return ""


# ============================================================
# SUMBER TEKS (dipakai bersama oleh semua tab di bawah)
# ============================================================
st.subheader("📄 Sumber Teks")
source_mode = st.radio("Pilih sumber teks", ["Paste Teks", "Upload File"], horizontal=True)

source_text = ""
if source_mode == "Paste Teks":
    source_text = st.text_area(
        "Masukkan teks (artikel/berita)",
        height=200,
        placeholder="Paste teks panjang di sini...",
    )
else:
    uploaded_file = st.file_uploader("Upload file (PDF, DOCX, atau TXT)", type=["pdf", "docx", "txt"])
    if uploaded_file:
        with st.spinner("Mengekstrak teks dari file..."):
            source_text = extract_text(uploaded_file)
        if source_text.strip():
            with st.expander("👀 Lihat teks hasil ekstraksi"):
                preview = source_text[:3000] + ("..." if len(source_text) > 3000 else "")
                st.text(preview)
        else:
            st.warning("Tidak ada teks yang bisa diekstrak dari file ini.")

st.divider()

# ============================================================
# TABS: Ringkas | Terjemahkan | Tanya Jawab
# ============================================================
tab_ringkas, tab_translate, tab_qa = st.tabs(["📋 Ringkas", "🌐 Terjemahkan", "💬 Tanya Jawab"])

# ---------- TAB 1: RINGKAS ----------
with tab_ringkas:
    LENGTH_CONFIG = {
        "Pendek": {"max_tokens": 100, "poin": 3},
        "Sedang": {"max_tokens": 200, "poin": 5},
        "Panjang": {"max_tokens": 300, "poin": 7},
    }
    length_choice = st.radio(
        "Pilih panjang ringkasan", list(LENGTH_CONFIG.keys()), horizontal=True, index=1, key="length_choice"
    )

    if st.button("🔍 Rangkum Teks", type="primary", use_container_width=True, key="btn_summarize"):
        if not api_key:
            st.error("Masukkan API Key Gemini terlebih dahulu di sidebar.")
        elif not source_text.strip():
            st.warning("Masukkan/upload teks yang ingin diringkas terlebih dahulu.")
        else:
            cfg = LENGTH_CONFIG[length_choice]
            prompt = (
                f"Rangkum teks berikut ini menjadi maksimal {cfg['poin']} poin penting "
                f"dalam Bahasa Indonesia. Gunakan format bullet point yang jelas dan padat:\n\n{source_text}"
            )
            try:
                with st.spinner("Sedang merangkum teks..."):
                    response = call_gemini(prompt, max_output_tokens=cfg["max_tokens"])
                st.subheader("📋 Hasil Ringkasan")
                st.write(response.text)
                st.subheader("📊 Token Usage")
                show_token_usage(response.usage_metadata)
            except Exception as e:
                st.error(f"Terjadi kesalahan saat memanggil API: {e}")

# ---------- TAB 2: TERJEMAHKAN ----------
with tab_translate:
    LANGUAGES = ["Inggris", "Indonesia", "Mandarin", "Jepang", "Arab", "Prancis", "Spanyol", "Jerman", "Korea"]
    target_lang = st.selectbox("Terjemahkan ke bahasa", LANGUAGES, key="target_lang")

    if st.button("🌐 Terjemahkan Teks", type="primary", use_container_width=True, key="btn_translate"):
        if not api_key:
            st.error("Masukkan API Key Gemini terlebih dahulu di sidebar.")
        elif not source_text.strip():
            st.warning("Masukkan/upload teks yang ingin diterjemahkan terlebih dahulu.")
        else:
            prompt = (
                f"Terjemahkan teks berikut ke dalam Bahasa {target_lang}. "
                f"Pertahankan makna asli, gunakan gaya bahasa yang natural dan enak dibaca:\n\n{source_text}"
            )
            try:
                with st.spinner("Sedang menerjemahkan..."):
                    response = call_gemini(prompt, max_output_tokens=1024)
                st.subheader(f"🌐 Hasil Terjemahan ({target_lang})")
                st.write(response.text)
                st.subheader("📊 Token Usage")
                show_token_usage(response.usage_metadata)
            except Exception as e:
                st.error(f"Terjadi kesalahan saat memanggil API: {e}")

# ---------- TAB 3: TANYA JAWAB ----------
with tab_qa:
    st.caption("Tanya apa saja tentang isi teks/dokumen yang sudah kamu masukkan di atas.")

    if "chat_history" not in st.session_state:
        st.session_state.chat_history = []

    for msg in st.session_state.chat_history:
        with st.chat_message(msg["role"]):
            st.write(msg["content"])

    question = st.chat_input("Tulis pertanyaan kamu di sini...")

    if question:
        if not api_key:
            st.error("Masukkan API Key Gemini terlebih dahulu di sidebar.")
        elif not source_text.strip():
            st.warning("Masukkan/upload teks dulu sebelum bertanya.")
        else:
            st.session_state.chat_history.append({"role": "user", "content": question})
            with st.chat_message("user"):
                st.write(question)

            history_str = "\n".join(
                f"{m['role']}: {m['content']}" for m in st.session_state.chat_history[:-1]
            )
            prompt = (
                f"Berikut adalah teks/dokumen referensi:\n\"\"\"\n{source_text}\n\"\"\"\n\n"
                f"Jawab pertanyaan pengguna HANYA berdasarkan isi teks di atas, dalam Bahasa Indonesia. "
                f"Jika jawabannya tidak ada di teks, katakan dengan jujur bahwa informasi itu tidak tersedia.\n\n"
                f"Riwayat percakapan sebelumnya:\n{history_str}\n\n"
                f"Pertanyaan baru: {question}"
            )
            try:
                with st.chat_message("assistant"):
                    with st.spinner("Mencari jawaban..."):
                        response = call_gemini(prompt, max_output_tokens=400)
                    st.write(response.text)
                    with st.expander("📊 Token Usage"):
                        show_token_usage(response.usage_metadata)
                st.session_state.chat_history.append({"role": "assistant", "content": response.text})
            except Exception as e:
                st.error(f"Terjadi kesalahan saat memanggil API: {e}")
