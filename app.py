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

MODEL_NAME = "gemini-2.5-flash-lite"
APP_VERSION = "v1.1"

# Harga gemini-2.5-flash-lite per 1 juta token (USD) -- untuk estimasi biaya saja
PRICE_INPUT_PER_M = 0.10
PRICE_OUTPUT_PER_M = 0.40


# ============================================================
# PROTEKSI PASSWORD (opsional -- aktif otomatis kalau APP_PASSWORD diisi di Secrets)
# ============================================================
def get_app_password():
    try:
        return st.secrets["APP_PASSWORD"]
    except Exception:
        return None


_app_password = get_app_password()
if _app_password:
    if "authenticated" not in st.session_state:
        st.session_state.authenticated = False

    if not st.session_state.authenticated:
        st.title("📝 SummaRise")
        st.caption("🔒 Aplikasi ini dilindungi password.")
        pwd_input = st.text_input("Masukkan password", type="password", key="app_password_gate")
        if st.button("Masuk", type="primary"):
            if pwd_input == _app_password:
                st.session_state.authenticated = True
                st.rerun()
            else:
                st.error("Password salah, coba lagi.")
        st.stop()


# ============================================================
# HEADER
# ============================================================
st.title("📝 SummaRise")
st.caption("Ringkas, terjemahkan, dan tanya-jawab dengan teks/dokumen kamu — didukung Google Gemini API")

badge_col1, badge_col2, badge_col3 = st.columns(3)
with badge_col1:
    st.badge("Gemini 2.5 Flash-Lite", icon="✨", color="violet")
with badge_col2:
    st.badge("Tier Gratis", icon="💚", color="green")
with badge_col3:
    st.badge(APP_VERSION, icon="🚀", color="blue")

st.divider()


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
        "last_sentiment": None,
        "last_keywords": None,
        "last_quiz": None,
        "last_style": None,
    }
    for k, v in defaults.items():
        if k not in st.session_state:
            st.session_state[k] = v


init_session_state()


def reset_all():
    """Hapus semua input & riwayat untuk mulai dari awal lagi."""
    keys_to_clear = [
        "source_text_input", "file_uploader", "source_mode_radio",
        "length_choice", "target_lang", "quiz_count", "style_choice",
        "chat_history", "session_history",
        "total_input_tokens", "total_output_tokens",
        "last_summary", "last_translation",
        "last_sentiment", "last_keywords", "last_quiz", "last_style",
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


IMAGE_MIME_MAP = {
    "jpg": "image/jpeg", "jpeg": "image/jpeg", "png": "image/png", "webp": "image/webp",
}


def extract_text_from_image(image_bytes, mime_type):
    """Baca teks dari foto memakai kemampuan vision Gemini (tanpa OCR lokal)."""
    client = genai.Client(api_key=api_key)
    image_part = types.Part.from_bytes(data=image_bytes, mime_type=mime_type)
    response = client.models.generate_content(
        model=MODEL_NAME,
        contents=[
            image_part,
            "Transkrip semua teks yang terlihat di foto ini secara lengkap dan akurat, "
            "sesuai bahasa aslinya. Jangan menambahkan komentar, penjelasan, atau karakter "
            "lain selain teks yang benar-benar ada di foto.",
        ],
        config=types.GenerateContentConfig(temperature=0.1, max_output_tokens=2048),
    )
    return response


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
    st.markdown("### 📝 SummaRise")
    st.caption("AI Text Summarizer & Assistant")
    st.divider()

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

with st.container(border=True):
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
            "Upload file (PDF, DOCX, TXT, atau Foto)",
            type=["pdf", "docx", "txt", "jpg", "jpeg", "png", "webp"],
            key="file_uploader",
        )
        if uploaded_file:
            ext = uploaded_file.name.lower().split(".")[-1]

            if ext in IMAGE_MIME_MAP:
                st.image(uploaded_file, caption="Pratinjau foto", use_container_width=True)
                if not api_key:
                    st.warning("Masukkan API Key Gemini di sidebar dulu untuk membaca teks dari foto.")
                else:
                    try:
                        with st.spinner("Membaca teks dari foto..."):
                            image_bytes = uploaded_file.getvalue()
                            ocr_response = extract_text_from_image(image_bytes, IMAGE_MIME_MAP[ext])
                        source_text = ocr_response.text
                        ocr_cost = estimate_cost(
                            ocr_response.usage_metadata.prompt_token_count,
                            ocr_response.usage_metadata.candidates_token_count,
                        )
                        show_usage(ocr_response.usage_metadata, ocr_cost)
                        add_to_history("Baca Foto", uploaded_file.name, source_text, ocr_response.usage_metadata, ocr_cost)
                    except Exception as e:
                        handle_api_error(e)
            else:
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
# PILIH FITUR (dropdown -- lebih ringkas di layar HP dibanding tabs)
# ============================================================
FEATURE_OPTIONS = [
    "📋 Ringkas", "🌐 Terjemahkan", "🎭 Sentimen", "🔑 Kata Kunci",
    "🧠 Kuis", "✍️ Gaya", "💬 Tanya Jawab", "🕘 Riwayat",
]
selected_feature = st.selectbox("🧭 Pilih fitur", FEATURE_OPTIONS, key="feature_select")
st.divider()

# ---------- FITUR: RINGKAS ----------
if selected_feature == "📋 Ringkas":
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
        with st.container(border=True):
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

# ---------- FITUR: TERJEMAHKAN ----------
elif selected_feature == "🌐 Terjemahkan":
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
        with st.container(border=True):
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

# ---------- FITUR: ANALISIS SENTIMEN ----------
elif selected_feature == "🎭 Sentimen":
    st.caption("Deteksi nada/sentimen dari teks: positif, negatif, netral, atau campuran.")

    if st.button("🎭 Analisis Sentimen", type="primary", use_container_width=True, key="btn_sentiment"):
        if not api_key:
            st.error("Masukkan API Key Gemini terlebih dahulu di sidebar.")
        elif not source_text.strip():
            st.warning("Masukkan/upload teks yang ingin dianalisis terlebih dahulu.")
        else:
            prompt = (
                "Analisis sentimen/nada dari teks berikut, jawab dalam Bahasa Indonesia. Sertakan:\n"
                "1. Label sentimen keseluruhan (Positif / Negatif / Netral / Campuran)\n"
                "2. Tingkat keyakinan (Rendah/Sedang/Tinggi)\n"
                "3. Penjelasan singkat alasannya\n"
                "4. Satu kutipan singkat dari teks yang paling mendukung penilaian ini\n\n"
                f"Teks:\n{source_text}"
            )
            try:
                with st.spinner("Menganalisis sentimen..."):
                    response = call_gemini(prompt, max_output_tokens=400)
                cost = estimate_cost(response.usage_metadata.prompt_token_count, response.usage_metadata.candidates_token_count)
                st.session_state.last_sentiment = {"text": response.text, "usage": response.usage_metadata, "cost": cost}
                add_to_history("Analisis Sentimen", source_text, response.text, response.usage_metadata, cost)
            except Exception as e:
                handle_api_error(e)

    if st.session_state.last_sentiment:
        result = st.session_state.last_sentiment
        with st.container(border=True):
            st.subheader("🎭 Hasil Analisis Sentimen")
            st.write(result["text"])
            show_usage(result["usage"], result["cost"])
            st.download_button(
                "📥 Download Hasil (.txt)",
                data=result["text"],
                file_name=f"sentimen_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt",
                mime="text/plain",
                key="dl_sentiment",
            )

# ---------- FITUR: EKSTRAK KATA KUNCI & TOPIK ----------
elif selected_feature == "🔑 Kata Kunci":
    st.caption("Ambil kata kunci dan topik utama dari teks, cocok buat tag artikel atau SEO.")

    if st.button("🔑 Ekstrak Kata Kunci", type="primary", use_container_width=True, key="btn_keywords"):
        if not api_key:
            st.error("Masukkan API Key Gemini terlebih dahulu di sidebar.")
        elif not source_text.strip():
            st.warning("Masukkan/upload teks yang ingin diekstrak terlebih dahulu.")
        else:
            prompt = (
                "Dari teks berikut, jawab dalam Bahasa Indonesia dengan format ini:\n"
                "1. **Topik Utama**: satu kalimat singkat tentang topik keseluruhan teks\n"
                "2. **Kata Kunci** (5-10 kata/frasa, format bullet, urutkan dari paling relevan)\n"
                "3. **Kategori**: 1-2 kata kategori umum yang paling cocok (misal: Teknologi, Kesehatan, Politik, dll)\n\n"
                f"Teks:\n{source_text}"
            )
            try:
                with st.spinner("Mengekstrak kata kunci..."):
                    response = call_gemini(prompt, max_output_tokens=300)
                cost = estimate_cost(response.usage_metadata.prompt_token_count, response.usage_metadata.candidates_token_count)
                st.session_state.last_keywords = {"text": response.text, "usage": response.usage_metadata, "cost": cost}
                add_to_history("Ekstrak Kata Kunci", source_text, response.text, response.usage_metadata, cost)
            except Exception as e:
                handle_api_error(e)

    if st.session_state.last_keywords:
        result = st.session_state.last_keywords
        with st.container(border=True):
            st.subheader("🔑 Kata Kunci & Topik")
            st.write(result["text"])
            show_usage(result["usage"], result["cost"])
            st.download_button(
                "📥 Download Hasil (.txt)",
                data=result["text"],
                file_name=f"kata_kunci_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt",
                mime="text/plain",
                key="dl_keywords",
            )

# ---------- FITUR: BUAT KUIS DARI TEKS ----------
elif selected_feature == "🧠 Kuis":
    st.caption("Buat soal pilihan ganda otomatis dari isi teks, cocok untuk belajar/latihan.")
    quiz_count = st.radio("Jumlah soal", [3, 5, 10], horizontal=True, index=1, key="quiz_count")

    if st.button("🧠 Buat Kuis", type="primary", use_container_width=True, key="btn_quiz"):
        if not api_key:
            st.error("Masukkan API Key Gemini terlebih dahulu di sidebar.")
        elif not source_text.strip():
            st.warning("Masukkan/upload teks yang ingin dijadikan kuis terlebih dahulu.")
        else:
            prompt = (
                f"Buat {quiz_count} soal pilihan ganda (4 opsi A-D) berdasarkan teks berikut, "
                f"dalam Bahasa Indonesia. Variasikan tingkat kesulitan. Untuk setiap soal, tulis "
                f"pertanyaan, lalu 4 opsi jawaban, lalu baris terakhir berisi 'Jawaban: X' "
                f"(huruf opsi yang benar). Beri jarak antar soal.\n\nTeks:\n{source_text}"
            )
            try:
                with st.spinner("Membuat soal kuis..."):
                    response = call_gemini(prompt, max_output_tokens=int(quiz_count) * 150)
                cost = estimate_cost(response.usage_metadata.prompt_token_count, response.usage_metadata.candidates_token_count)
                st.session_state.last_quiz = {"text": response.text, "usage": response.usage_metadata, "cost": cost}
                add_to_history("Buat Kuis", source_text, response.text, response.usage_metadata, cost)
            except Exception as e:
                handle_api_error(e)

    if st.session_state.last_quiz:
        result = st.session_state.last_quiz
        with st.container(border=True):
            st.subheader("🧠 Kuis dari Teks")
            st.write(result["text"])
            show_usage(result["usage"], result["cost"])
            st.download_button(
                "📥 Download Kuis (.txt)",
                data=result["text"],
                file_name=f"kuis_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt",
                mime="text/plain",
                key="dl_quiz",
            )

# ---------- FITUR: UBAH GAYA PENULISAN ----------
elif selected_feature == "✍️ Gaya":
    st.caption("Tulis ulang teks dengan gaya bahasa yang berbeda, isi tetap sama.")
    STYLE_OPTIONS = ["Formal", "Santai/Kasual", "Persuasif", "Naratif/Storytelling", "Akademis", "Jurnalistik"]
    style_choice = st.selectbox("Pilih gaya penulisan", STYLE_OPTIONS, key="style_choice")

    if st.button("✍️ Ubah Gaya Penulisan", type="primary", use_container_width=True, key="btn_style"):
        if not api_key:
            st.error("Masukkan API Key Gemini terlebih dahulu di sidebar.")
        elif not source_text.strip():
            st.warning("Masukkan/upload teks yang ingin ditulis ulang terlebih dahulu.")
        else:
            prompt = (
                f"Tulis ulang teks berikut dengan gaya bahasa {style_choice}, dalam Bahasa Indonesia. "
                f"Pertahankan semua informasi dan makna inti, hanya ubah gaya penyampaiannya:\n\n{source_text}"
            )
            try:
                with st.spinner("Menulis ulang teks..."):
                    response = call_gemini(prompt, max_output_tokens=1024)
                cost = estimate_cost(response.usage_metadata.prompt_token_count, response.usage_metadata.candidates_token_count)
                st.session_state.last_style = {
                    "text": response.text, "usage": response.usage_metadata, "cost": cost, "style": style_choice,
                }
                add_to_history(f"Gaya: {style_choice}", source_text, response.text, response.usage_metadata, cost)
            except Exception as e:
                handle_api_error(e)

    if st.session_state.last_style:
        result = st.session_state.last_style
        with st.container(border=True):
            st.subheader(f"✍️ Hasil Gaya {result['style']}")
            st.write(result["text"])
            show_usage(result["usage"], result["cost"])
            st.download_button(
                "📥 Download Hasil (.txt)",
                data=result["text"],
                file_name=f"gaya_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt",
                mime="text/plain",
                key="dl_style",
            )

# ---------- FITUR: TANYA JAWAB ----------
elif selected_feature == "💬 Tanya Jawab":
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

# ---------- FITUR: RIWAYAT ----------
elif selected_feature == "🕘 Riwayat":
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
                    file_name=f"{''.join(c for c in item['kind'].split(' ')[0] if c.isalnum()).lower() or 'riwayat'}_{i}.txt",
                    mime="text/plain",
                    key=f"dl_hist_{i}",
                )

# ============================================================
# FOOTER
# ============================================================
st.divider()
st.caption(f"📝 SummaRise {APP_VERSION} · Dibangun dengan Streamlit & Google Gemini API · Proyek pembelajaran AI API")
