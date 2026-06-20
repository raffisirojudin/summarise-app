"""
SummaRise - AI Text Summarizer & Assistant
Streamlit app: ringkas teks, terjemahkan, dan tanya-jawab berbasis dokumen,
menggunakan Google Gemini API.
"""

from datetime import datetime

import streamlit as st
from google import genai
from google.genai import types
from pypdf import PdfReader
from docx import Document

# ============================================================
# KONFIGURASI HALAMAN & KONSTANTA
# ============================================================
st.set_page_config(page_title="SummaRise", page_icon="📝", layout="centered")
st.title("📝 SummaRise")
st.caption("Ringkas, terjemahkan, dan tanya-jawab dengan teks/dokumen kamu menggunakan Gemini API")

MODEL_NAME = "gemini-2.5-flash-lite"

# Harga gemini-2.5-flash-lite per 1 juta token (USD) -- untuk estimasi biaya saja
PRICE_INPUT_PER_M = 0.10
PRICE_OUTPUT_PER_M = 0.40


# ============================================================
# SESSION STATE
# ============================================================
def init_session_state():
    defaults = {
        "session_history": [],
        "chat_history": [],
        "total_input_tokens": 0,
        "total_output_tokens": 0,
        "last_summary": None,
        "last_translation": None,
    }
    for k, v in defaults.items():
        if k not in st.session_state:
            st.session_state[k] = v


init_session_state()


def reset_all():
    """Hapus semua input & riwayat untuk mulai dari awal lagi."""
    keys_to_clear = [
        "source_text_input", "file_uploader", "source_mode_radio",
        "length_choice", "target_lang",
        "chat_history", "session_history",
        "total_input_tokens", "total_output_tokens",
        "last_summary", "last_translation",
    ]
    for k in keys_to_clear:
        st.session_state.pop(k, None)


# ============================================================
# HELPER: biaya, panggilan API, error, ekstraksi file
# ============================================================
def estimate_cost(input_tokens, output_tokens):
    return (input_tokens / 1_000_000) * PRICE_INPUT_PER_M + (output_tokens / 1_000_000) * PRICE_OUTPUT_PER_M


def get_secret_api_key():
    try:
        return st.secrets["GEMINI_API_KEY"]
    except Exception:
        return None


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


def show_usage(usage, cost):
    st.session_state.total_input_tokens += usage.prompt_token_count
    st.session_state.total_output_tokens += usage.candidates_token_count
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Input Tokens", usage.prompt_token_count)
    col2.metric("Output Tokens", usage.candidates_token_count)
    col3.metric("Total Tokens", usage.total_token_count)
    col4.metric("Estimasi Biaya", f"${cost:.5f}")
    st.caption(
        "💡 Estimasi berdasarkan harga gemini-2.5-flash-lite "
        "($0.10/1M token input, $0.40/1M token output). Bisa berbeda dari billing asli Google."
    )


def handle_api_error(e):
    """Tampilkan pesan error yang ramah berdasarkan jenis kesalahannya."""
    msg = str(e)
    msg_lower = msg.lower()

    if "resource_exhausted" in msg_lower or "429" in msg or "quota" in msg_lower:
        st.error(
            "⏳ **Kuota API habis untuk saat ini.** Tier gratis Gemini punya limit "
            "jumlah request per menit dan per hari. Coba lagi setelah beberapa menit, "
            "atau besok kalau limit hariannya yang habis (biasanya reset tengah malam "
            "waktu Pacific). Cek sisa kuota di [Google AI Studio](https://aistudio.google.com)."
        )
    elif "unavailable" in msg_lower or "503" in msg:
        st.error(
            "🔄 **Server Gemini sedang sibuk** (overload sementara, bukan masalah di kode kamu). "
            "Coba klik tombolnya lagi setelah beberapa detik."
        )
    elif "api_key_invalid" in msg_lower or "permission_denied" in msg_lower or "401" in msg or "403" in msg:
        st.error(
            "🔑 **API Key tidak valid atau tidak punya izin.** Cek kembali API Key di "
            "sidebar atau di Secrets, pastikan disalin lengkap tanpa spasi tambahan."
        )
    else:
        st.error(f"Terjadi kesalahan saat memanggil API: {msg}")


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


def add_to_history(kind, input_text, output_text, usage, cost):
    preview = input_text.strip().replace("\n", " ")
    preview = preview[:150] + ("..." if len(preview) > 150 else "")
    st.session_state.session_history.insert(0, {
        "time": datetime.now().strftime("%H:%M:%S"),
        "kind": kind,
        "input_preview": preview,
        "output": output_text,
        "usage": usage,
        "cost": cost,
    })


# ============================================================
# SIDEBAR: API KEY, RINGKASAN PEMAKAIAN, RESET
# ============================================================
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

    st.divider()
    st.subheader("📊 Pemakaian Sesi Ini")
    total_tokens = st.session_state.total_input_tokens + st.session_state.total_output_tokens
    total_cost = estimate_cost(st.session_state.total_input_tokens, st.session_state.total_output_tokens)
    c1, c2 = st.columns(2)
    c1.metric("Total Token", f"{total_tokens:,}")
    c2.metric("Estimasi Biaya", f"${total_cost:.5f}")

    st.divider()
    st.button("🧹 Reset Semua", on_click=reset_all, use_container_width=True)


# ============================================================
# SUMBER TEKS (dipakai bersama oleh semua tab di bawah)
# ============================================================
st.subheader("📄 Sumber Teks")
source_mode = st.radio(
    "Pilih sumber teks", ["Paste Teks", "Upload File"], horizontal=True, key="source_mode_radio"
)

source_text = ""
if source_mode == "Paste Teks":
    source_text = st.text_area(
        "Masukkan teks (artikel/berita)",
        height=200,
        placeholder="Paste teks panjang di sini...",
        key="source_text_input",
    )
else:
    uploaded_file = st.file_uploader(
        "Upload file (PDF, DOCX, atau TXT)", type=["pdf", "docx", "txt"], key="file_uploader"
    )
    if uploaded_file:
        with st.spinner("Mengekstrak teks dari file..."):
            source_text = extract_text(uploaded_file)
        if source_text.strip():
            with st.expander("👀 Lihat teks hasil ekstraksi"):
                preview_text = source_text[:3000] + ("..." if len(source_text) > 3000 else "")
                st.text(preview_text)
        else:
            st.warning("Tidak ada teks yang bisa diekstrak dari file ini.")

if source_text.strip():
    word_count = len(source_text.split())
    char_count = len(source_text)
    st.caption(f"📝 {word_count:,} kata · {char_count:,} karakter")

st.divider()

# ============================================================
# TABS: Ringkas | Terjemahkan | Tanya Jawab | Riwayat
# ============================================================
tab_ringkas, tab_translate, tab_qa, tab_history = st.tabs(
    ["📋 Ringkas", "🌐 Terjemahkan", "💬 Tanya Jawab", "🕘 Riwayat"]
)

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
                cost = estimate_cost(response.usage_metadata.prompt_token_count, response.usage_metadata.candidates_token_count)
                st.session_state.last_summary = {"text": response.text, "usage": response.usage_metadata, "cost": cost}
                add_to_history("Ringkas", source_text, response.text, response.usage_metadata, cost)
            except Exception as e:
                handle_api_error(e)

    if st.session_state.last_summary:
        result = st.session_state.last_summary
        st.subheader("📋 Hasil Ringkasan")
        st.write(result["text"])
        show_usage(result["usage"], result["cost"])
        st.download_button(
            "📥 Download Ringkasan (.txt)",
            data=result["text"],
            file_name=f"ringkasan_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt",
            mime="text/plain",
            key="dl_ringkas",
        )

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
                cost = estimate_cost(response.usage_metadata.prompt_token_count, response.usage_metadata.candidates_token_count)
                st.session_state.last_translation = {
                    "text": response.text, "usage": response.usage_metadata, "cost": cost, "lang": target_lang,
                }
                add_to_history(f"Terjemahkan ({target_lang})", source_text, response.text, response.usage_metadata, cost)
            except Exception as e:
                handle_api_error(e)

    if st.session_state.last_translation:
        result = st.session_state.last_translation
        st.subheader(f"🌐 Hasil Terjemahan ({result['lang']})")
        st.write(result["text"])
        show_usage(result["usage"], result["cost"])
        st.download_button(
            "📥 Download Terjemahan (.txt)",
            data=result["text"],
            file_name=f"terjemahan_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt",
            mime="text/plain",
            key="dl_translate",
        )

# ---------- TAB 3: TANYA JAWAB ----------
with tab_qa:
    st.caption("Tanya apa saja tentang isi teks/dokumen yang sudah kamu masukkan di atas.")

    if st.session_state.chat_history:
        chat_export = "\n\n".join(
            f"{'Kamu' if m['role'] == 'user' else 'AI'}: {m['content']}" for m in st.session_state.chat_history
        )
        st.download_button(
            "📥 Download Riwayat Chat (.txt)",
            data=chat_export,
            file_name=f"chat_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt",
            mime="text/plain",
            key="dl_chat",
        )

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
                    cost = estimate_cost(
                        response.usage_metadata.prompt_token_count, response.usage_metadata.candidates_token_count
                    )
                    with st.expander("📊 Token Usage"):
                        show_usage(response.usage_metadata, cost)
                st.session_state.chat_history.append({"role": "assistant", "content": response.text})
                add_to_history("Tanya Jawab", question, response.text, response.usage_metadata, cost)
            except Exception as e:
                handle_api_error(e)

# ---------- TAB 4: RIWAYAT ----------
with tab_history:
    st.caption("Semua hasil yang sudah dibuat di sesi ini (hilang kalau halaman di-refresh atau ditutup).")

    if not st.session_state.session_history:
        st.info("Belum ada riwayat. Coba pakai salah satu fitur Ringkas / Terjemahkan / Tanya Jawab dulu.")
    else:
        if st.button("🗑️ Hapus Semua Riwayat", key="btn_clear_history"):
            st.session_state.session_history = []
            st.rerun()

        for i, item in enumerate(st.session_state.session_history):
            with st.expander(f"**{item['kind']}** · {item['time']} — _{item['input_preview']}_"):
                st.write(item["output"])
                u = item["usage"]
                st.caption(
                    f"Token: {u.prompt_token_count} in / {u.candidates_token_count} out / {u.total_token_count} total "
                    f"· Estimasi biaya: ${item['cost']:.5f}"
                )
                st.download_button(
                    "📥 Download",
                    data=item["output"],
                    file_name=f"{item['kind'].split(' ')[0].lower()}_{i}.txt",
                    mime="text/plain",
                    key=f"dl_hist_{i}",
                )
