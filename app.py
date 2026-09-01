"""Web UI for Sentence Autocomplete & Hybrid AI Search Engine with Voice Input."""

import os
import time
from types import SimpleNamespace
import streamlit as st

# Core imports (חלק א')
from core.indexer import DataManager
from core.models import AutoCompleteData
from core.normalizer import normalize_text
from core.scoring import rank_candidates
import core.search_engine as search_engine
from core.search_engine import typo_cache

# Services imports (חלק ב')
from services.gemini_completion_service import GeminiCompletionService
from services.gemini_service import GeminiService
from services.semantic_indexer import SemanticMatchResult, SemanticSearchEngine
from services.gemini_speech import GeminiSpeechTranscriber
from services.speech import VoiceInputError

st.set_page_config(
    page_title="Sentence Search Engine",
    page_icon="🔍",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.title("🔍 Sentence Autocomplete & Semantic Search")
st.caption("Hybrid Engine: Lexical + Semantic Vectors + Generative LLM + Voice Input")


@st.cache_resource(show_spinner="⏳ טוען את הארכיון והווקטורים לזיכרון...", max_entries=1)
def initialize_system():
    data_manager = DataManager()
    data_dir = "Archive"
    if os.path.exists(data_dir) or os.path.exists(data_manager.cache_file):
        data_manager.load_data(data_dir)

    gemini_svc = GeminiService()
    gemini_completion_svc = GeminiCompletionService()
    semantic_eng = SemanticSearchEngine(gemini_svc)
    speech_transcriber = GeminiSpeechTranscriber()

    semantic_eng._load_from_cache()

    return data_manager, gemini_svc, gemini_completion_svc, semantic_eng, speech_transcriber


manager, gemini_service, gemini_completion_service, semantic_engine, speech_transcriber = initialize_system()

# סרגל צדדי
with st.sidebar:
    st.header("📊 סטטוס מערכת")
    total_sentences = len(manager.sentences) if hasattr(manager, "sentences") else 0
    cached_vectors = (
        len(semantic_engine.sentences_metadata)
        if hasattr(semantic_engine, "sentences_metadata")
        else 0
    )
    learned_typos = len(typo_cache._entries) if hasattr(typo_cache, "_entries") else 0

    st.metric(label="משפטים בארכיון הלקסיקלי", value=f"{total_sentences:,}")
    st.metric(label="וקטורים במאגר הסמנטי", value=f"{cached_vectors:,}")
    st.metric(label="שגיאות הקלדה שנלמדו ב-Cache", value=f"{learned_typos:,}")

    st.markdown("---")
    st.subheader("💡 מצבי חיפוש")
    st.markdown("""
    - **⚡ השלמה לקסיקלית:** חיפוש מדויק/משוער מתוך קובצי הארכיון (עם תיעדוף TypoCache).
    - **🧠 חיפוש סמנטי:** חיפוש לפי כוונה ומשמעות ותרגום שפות אוטומטי.
    - **✨ השלמת AI:** יצירת המשך למשפט בזמן אמת ע"י Gemini.
    """)

# בחירת מצב החיפוש
search_mode = st.radio(
    "בחר סוג מנוע:",
    [
        "⚡ השלמה לקסיקלית מהירה (Part A)",
        "🧠 חיפוש סמנטי ורב-לשוני (Part B)",
        "✨ השלמת AI גנרטיבית (Gemini LLM)",
    ],
    horizontal=True,
)

# הגדרת הקשר רק במצב AI
ai_context = "General"
if "גנרטיבית" in search_mode:
    ai_context = st.selectbox(
        "בחר הקשר (Domain Context):",
        ["General", "Technical", "Academic", "Networking", "Database"],
        index=0,
    )

# קלט קולי (Speech-to-Text)
st.markdown("##### 🎙️ קלט קולי (אופציונלי)")
audio_val = st.audio_input("הקלט שאילתה בקולך:")

voice_query = ""
if audio_val is not None:
    try:
        temp_audio_path = "temp_recording.wav"
        with open(temp_audio_path, "wb") as f:
            f.write(audio_val.read())

        with st.spinner("🎙️ מתמלל את ההקלטה באמצעות Gemini..."):
            transcription = speech_transcriber.transcribe(temp_audio_path, language_code="en-US")
            voice_query = transcription.text
            st.success(f"תומלל בהצלחה: **{voice_query}** ({transcription.latency_seconds:.2f}s)")
    except VoiceInputError as e:
        st.error(f"שגיאת קלט קולי: {e}")
    except Exception as e:
        st.error(f"שגיאה בעיבוד השמע: {e}")

# תיבת חיפוש
query = st.text_input(
    "הזן טקסט לחיפוש ולחץ Enter:",
    value=voice_query,
    placeholder="לדוגמה: 'machine learning is', 'NGINX is a', או בעברית 'שרת אינטרנט מהיר'",
)

if query:
    start_time = time.perf_counter()

    # 1. השלמה לקסיקלית
    if "לקסיקלית" in search_mode:
        normalized_q = normalize_text(query)
        raw_matches = search_engine.search(query, manager) if hasattr(search_engine, "search") else []

        adapted_matches = [
            SimpleNamespace(
                sentence_id=m.sentence_id,
                error_type=None if m.edit_type == "exact" else m.edit_type,
                error_index=m.edit_position,
            )
            for m in raw_matches
        ]

        results = rank_candidates(normalized_q, adapted_matches, manager.get_sentence, top_k=5)
        elapsed_ms = (time.perf_counter() - start_time) * 1000

        st.markdown(f"### ⚡ תוצאות השלמה לקסיקלית <small>({elapsed_ms:.2f} ms)</small>", unsafe_allow_html=True)

        if not results:
            st.warning("לא נמצאו השלמות תואמות בארכיון.")
        else:
            for idx, r in enumerate(results, start=1):
                with st.container(border=True):
                    st.markdown(f"##### {idx}. {r.completed_sentence}")
                    c1, c2, c3 = st.columns(3)
                    with c1:
                        st.caption(f"📁 **קובץ:** `{r.source_text}`")
                    with c2:
                        st.caption(f"📍 **שורה/Offset:** `{r.offset}`")
                    with c3:
                        st.caption(f"⭐ **ציון התאמה:** `{r.score}`")

    # 2. חיפוש סמנטי
    elif "סמנטי" in search_mode:
        search_term = query.strip()
        if gemini_service.is_available() and not all(ord(c) < 128 for c in search_term):
            translated_term = gemini_service.translate_to_english(search_term)
            if translated_term != search_term:
                st.info(f"🌐 **תרגום אוטומטי לחיפוש בארכיון:** `{translated_term}`")

        results = semantic_engine.search(search_term, top_k=5)
        elapsed_ms = (time.perf_counter() - start_time) * 1000

        st.markdown(f"### 🧠 תוצאות סמנטיות מבוססות וקטורים <small>({elapsed_ms:.2f} ms)</small>", unsafe_allow_html=True)

        if not results:
            st.warning("לא נמצאו תוצאות סמנטיות במאגר.")
        else:
            for idx, r in enumerate(results, start=1):
                with st.container(border=True):
                    st.markdown(f"##### {idx}. {r.sentence}")
                    c1, c2, c3 = st.columns(3)
                    with c1:
                        st.caption(f"📁 **קובץ:** `{r.source_path}`")
                    with c2:
                        st.caption(f"📍 **שורה/Offset:** `{r.line_number}`")
                    with c3:
                        st.caption(f"📊 **דמיון סמנטי:** `{r.similarity_score:.4f}`")

    # 3. השלמת AI גנרטיבית
    elif "גנרטיבית" in search_mode:
        results = gemini_completion_service.generate_completions(
            query.strip(), domain_context=ai_context, top_k=5
        )
        elapsed_ms = (time.perf_counter() - start_time) * 1000

        st.markdown(f"### ✨ השלמות AI נוצרות <small>({elapsed_ms:.2f} ms)</small>", unsafe_allow_html=True)

        if not results:
            st.warning("לא נוצרו השלמות עבור קלט זה.")
        else:
            for idx, r in enumerate(results, start=1):
                with st.container(border=True):
                    st.markdown(f"##### {idx}. {r.completed_sentence}")
                    c1, c2 = st.columns(2)
                    with c1:
                        st.caption(f"🤖 **מקור:** `{r.source_text}`")
                    with c2:
                        st.caption(f"🎯 **הקשר:** `{ai_context}`")