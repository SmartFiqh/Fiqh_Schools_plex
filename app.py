from __future__ import annotations

import datetime as dt
import hashlib
import json
import logging
import os
import re
import sqlite3
from collections import OrderedDict
from pathlib import Path
from typing import Any, Dict, List, Optional

import numpy as np
import streamlit as st


# ============================================================
# Page and configuration
# ============================================================

st.set_page_config(
    page_title="SmartFiqh",
    page_icon="📚",
    layout="wide",
    initial_sidebar_state="expanded",
)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

ROOT = Path(__file__).resolve().parent
DATA_DIR = ROOT / "data"
REFERENCES_DIR = ROOT / "references"
DB_PATH = ROOT / "fiqh.db"

GEMINI_MODEL = os.getenv(
    "GEMINI_MODEL",
    "gemini-2.5-flash",
)

EMBED_MODEL = os.getenv(
    "EMBED_MODEL",
    "gemini-embedding-001",
)


try:
    from google import genai
    from google.genai import types

    GENAI_AVAILABLE = True
except ImportError:
    genai = None
    types = None
    GENAI_AVAILABLE = False


def get_secret(
    name: str,
    default: str = "",
) -> str:
    try:
        value = st.secrets.get(name)

        if value:
            return str(value)
    except Exception:
        pass

    return os.getenv(name, default)


GEMINI_API_KEY = get_secret("GEMINI_API_KEY")
ADMIN_PASSWORD = get_secret("ADMIN_PASSWORD")

USE_GEMINI = bool(
    GEMINI_API_KEY and GENAI_AVAILABLE
)

gemini_client = None

if USE_GEMINI:
    try:
        gemini_client = genai.Client(
            api_key=GEMINI_API_KEY
        )
    except Exception:
        USE_GEMINI = False
        logger.exception(
            "Gemini initialization failed"
        )


# ============================================================
# UI languages
# ============================================================

LANGUAGES = {
    "ar": {
        "name": "العربية",
        "flag": "🇪🇬",
        "direction": "rtl",
        "align": "right",
    },
    "en": {
        "name": "English",
        "flag": "🇬🇧",
        "direction": "ltr",
        "align": "left",
    },
    "fr": {
        "name": "Français",
        "flag": "🇫🇷",
        "direction": "ltr",
        "align": "left",
    },
    "fa": {
        "name": "فارسی",
        "flag": "🇮🇷",
        "direction": "rtl",
        "align": "right",
    },
    "ms": {
        "name": "Melayu",
        "flag": "🇲🇾",
        "direction": "ltr",
        "align": "left",
    },
    "ur": {
        "name": "اردو",
        "flag": "🇵🇰",
        "direction": "rtl",
        "align": "right",
    },
}


UI = {
    "ar": {
        "title": "الجامع المختصر لآراء المذاهب",
        "subtitle": (
            "منصة تعليمية للمقارنة الفقهية، "
            "وليست موقعًا للإفتاء."
        ),
        "language": "اللغة",
        "madhab": "تصفية المذهب",
        "all_madhabs": "كل المذاهب",
        "topic": "اختر الموضوع",
        "all_topics": "كل الموضوعات",
        "answer_type": "نوع الإجابة",
        "brief": "مختصرة",
        "detailed": "مفصلة",
        "question": "اكتب سؤالك",
        "placeholder": "مثال: ما حكم العمرة؟",
        "search": "🔍 بحث",
        "loading": "جاري البحث وتحليل السؤال...",
        "no_question": "الرجاء كتابة السؤال.",
        "no_madhab": "الرجاء اختيار مذهب واحد على الأقل.",
        "no_result": "لم يتم العثور على إجابة قابلة للعرض.",
        "ai_on": "Gemini AI: مفعّل",
        "ai_off": "Gemini AI: غير مفعّل",
        "ai_note": (
            "هذه إجابة بحثية آلية وليست فتوى، "
            "وينبغي مراجعتها لدى متخصص."
        ),
        "countries": "🗺️ تصفح الدول والمذاهب",
        "scholars": "📜 الأئمة والعلماء",
        "glossary": "📚 المصطلحات الفقهية",
        "sources": "📜 مصادر التشريع الفقهي",
        "rules": "⚖️ الأصول والقواعد الفقهية",
        "questions": "❓ أسئلة واستفسارات",
        "references": "📁 إدارة المراجع",
        "definition": "التعريف",
        "example": "مثال",
        "population_note": "أعداد السكان تقريبية.",
        "admin_password": "كلمة مرور المشرف",
        "access_denied": "لا تملك الصلاحية.",
        "source_title": "عنوان المصدر",
        "source_text": "نص المرجع",
        "add_reference": "إضافة المرجع",
        "reference_added": "تمت إضافة {} مقاطع.",
    },
    "en": {
        "title": "The Concise Compendium of Madhhab Opinions",
        "subtitle": (
            "An educational fiqh comparison platform, "
            "not a fatwa service."
        ),
        "language": "Language",
        "madhab": "Madhhab filter",
        "all_madhabs": "All schools",
        "topic": "Choose a topic",
        "all_topics": "All topics",
        "answer_type": "Answer type",
        "brief": "Brief",
        "detailed": "Detailed",
        "question": "Ask a question",
        "placeholder": "Example: What is the ruling on Umrah?",
        "search": "🔍 Search",
        "loading": "Searching and analyzing...",
        "no_question": "Please enter a question.",
        "no_madhab": "Please choose at least one school.",
        "no_result": "No usable answer was found.",
        "ai_on": "Gemini AI: enabled",
        "ai_off": "Gemini AI: disabled",
        "ai_note": (
            "This is an automated research answer, "
            "not a fatwa. Consult a qualified specialist."
        ),
        "countries": "🗺️ Countries and schools",
        "scholars": "📜 Imams and scholars",
        "glossary": "📚 Fiqh terminology",
        "sources": "📜 Sources of Islamic jurisprudence",
        "rules": "⚖️ Fiqh principles and legal maxims",
        "questions": "❓ Questions and answers",
        "references": "📁 Reference management",
        "definition": "Definition",
        "example": "Example",
        "population_note": "Population figures are approximate.",
        "admin_password": "Admin password",
        "access_denied": "Access denied.",
        "source_title": "Source title",
        "source_text": "Reference text",
        "add_reference": "Add reference",
        "reference_added": "{} chunks were added.",
    },
}


for code in ("fr", "fa", "ms", "ur"):
    UI[code] = UI["en"].copy()


UI["fa"].update({
    "title": "مجموعه مختصر دیدگاه‌های مذاهب فقهی",
    "subtitle": "سامانه‌ای آموزشی برای مقایسه دیدگاه‌های فقهی.",
    "language": "زبان",
    "madhab": "مذهب را انتخاب کنید",
    "all_madhabs": "همه مذاهب",
    "topic": "موضوع را انتخاب کنید",
    "all_topics": "همه موضوعات",
    "answer_type": "نوع پاسخ",
    "brief": "کوتاه",
    "detailed": "کامل",
    "question": "پرسش خود را بنویسید",
    "placeholder": "مثال: حکم عمره چیست؟",
    "search": "🔍 جست‌وجو",
    "loading": "در حال جست‌وجو و تحلیل...",
    "no_question": "لطفاً پرسش را وارد کنید.",
    "no_madhab": "لطفاً یک مذهب را انتخاب کنید.",
    "no_result": "پاسخ قابل استفاده‌ای پیدا نشد.",
    "ai_on": "Gemini AI: فعال",
    "ai_off": "Gemini AI: غیرفعال",
    "ai_note": "این پاسخ پژوهشی است، نه فتوا.",
    "countries": "🗺️ کشورها و مذاهب",
    "scholars": "📜 امامان و دانشمندان",
    "glossary": "📚 اصطلاحات فقهی",
    "sources": "📜 منابع فقه اسلامی",
    "rules": "⚖️ اصول و قواعد فقهی",
    "questions": "❓ پرسش‌ها و پاسخ‌ها",
    "references": "📁 مدیریت منابع",
    "definition": "تعریف",
    "example": "مثال",
    "population_note": "آمار جمعیت تقریبی است.",
})


UI["ms"].update({
    "title": "Himpunan Ringkas Pandangan Mazhab",
    "subtitle": "Platform pendidikan untuk perbandingan pandangan fiqh.",
    "language": "Bahasa",
    "madhab": "Pilih mazhab",
    "all_madhabs": "Semua mazhab",
    "topic": "Pilih topik",
    "all_topics": "Semua topik",
    "answer_type": "Jenis jawapan",
    "brief": "Ringkas",
    "detailed": "Terperinci",
    "question": "Tulis soalan anda",
    "placeholder": "Contoh: Apakah hukum Umrah?",
    "search": "🔍 Cari",
    "loading": "Mencari dan menganalisis...",
    "no_question": "Sila masukkan soalan.",
    "no_madhab": "Sila pilih sekurang-kurangnya satu mazhab.",
    "no_result": "Tiada jawapan yang sesuai.",
    "ai_on": "Gemini AI: diaktifkan",
    "ai_off": "Gemini AI: dinyahaktifkan",
    "ai_note": "Ini jawapan penyelidikan, bukan fatwa.",
    "countries": "🗺️ Negara dan mazhab",
    "scholars": "📜 Imam dan ulama",
    "glossary": "📚 Istilah fiqh",
    "sources": "📜 Sumber fiqh Islam",
    "rules": "⚖️ Prinsip dan kaedah fiqh",
    "questions": "❓ Soalan dan jawapan",
    "references": "📁 Pengurusan rujukan",
    "definition": "Takrif",
    "example": "Contoh",
    "population_note": "Angka penduduk adalah anggaran.",
})


UI["ur"].update({
    "title": "مذاہب فقہ کے مختصر آراء کا مجموعہ",
    "subtitle": "فقہی آراء کے تقابلی مطالعے کا تعلیمی پلیٹ فارم۔",
    "language": "زبان",
    "madhab": "مسلک منتخب کریں",
    "all_madhabs": "تمام مسالک",
    "topic": "موضوع منتخب کریں",
    "all_topics": "تمام موضوعات",
    "answer_type": "جواب کی نوعیت",
    "brief": "مختصر",
    "detailed": "تفصیلی",
    "question": "اپنا سوال لکھیں",
    "placeholder": "مثال: عمرہ کا کیا حکم ہے؟",
    "search": "🔍 تلاش",
    "loading": "تلاش اور تجزیہ جاری ہے...",
    "no_question": "براہ کرم سوال درج کریں۔",
    "no_madhab": "براہ کرم کم از کم ایک مسلک منتخب کریں۔",
    "no_result": "قابل استعمال جواب نہیں ملا۔",
    "ai_on": "Gemini AI: فعال",
    "ai_off": "Gemini AI: غیر فعال",
    "ai_note": "یہ تحقیقی جواب ہے، فتویٰ نہیں۔",
    "countries": "🗺️ ممالک اور مسالک",
    "scholars": "📜 ائمہ اور علماء",
    "glossary": "📚 فقہی اصطلاحات",
    "sources": "📜 فقہی مصادر",
    "rules": "⚖️ فقہی اصول و قواعد",
    "questions": "❓ سوالات و جوابات",
    "references": "📁 مراجع کا انتظام",
    "definition": "تعریف",
    "example": "مثال",
    "population_note": "آبادی کے اعداد تقریباً ہیں۔",
})


# ============================================================
# External data
# ============================================================

def load_json(
    filename: str,
    default: Any,
) -> Any:
    path = DATA_DIR / filename

    try:
        with path.open(
            "r",
            encoding="utf-8",
        ) as file:
            return json.load(file)
    except Exception as error:
        logger.warning(
            "Unable to load %s: %s",
            path,
            error,
        )
        return default


MADHABS = load_json(
    "madhabs.json",
    {},
)

COUNTRIES = load_json(
    "countries.json",
    [],
)

GLOSSARY = load_json(
    "glossary.json",
    [],
)

RULES = load_json(
    "rules.json",
    [],
)

LEGAL_SOURCES = load_json(
    "legal_sources.json",
    [],
)


# ============================================================
# Utility functions
# ============================================================

def text_for(
    value: Any,
    lang: str,
    default: str = "",
) -> str:
    if isinstance(value, str):
        return value

    if isinstance(value, dict):
        return str(
            value.get(
                lang,
                value.get("ar", default),
            )
        )

    return default


def normalize(text: str) -> str:
    replacements = {
        "أ": "ا",
        "إ": "ا",
        "آ": "ا",
        "ى": "ي",
        "ة": "ه",
    }

    text = text.lower()

    for old, new in replacements.items():
        text = text.replace(old, new)

    text = re.sub(
        r"[\u064B-\u065F\u0670]",
        "",
        text,
    )

    text = re.sub(
        r"[^\w\s]",
        " ",
        text,
    )

    return re.sub(
        r"\s+",
        " ",
        text,
    ).strip()


def now_iso() -> str:
    return dt.datetime.now(
        dt.timezone.utc
    ).isoformat()


def madhab_name(
    code: str,
    lang: str,
) -> str:
    data = MADHABS.get(code, {})

    return text_for(
        data.get("name", code),
        lang,
        code,
    )


def topic_name(
    code: str,
    lang: str,
) -> str:
    names = {
        "ibadat": {
            "ar": "العبادات",
            "en": "Worship",
        },
        "muamalat": {
            "ar": "المعاملات",
            "en": "Transactions",
        },
        "family": {
            "ar": "الأسرة",
            "en": "Family",
        },
        "other": {
            "ar": "مواضيع أخرى",
            "en": "Other topics",
        },
    }

    return text_for(
        names.get(code, {}),
        lang,
        code,
    )


# ============================================================
# SQLite database
# ============================================================

class Database:
    def __init__(
        self,
        path: Path = DB_PATH,
    ):
        self.path = path
        self.setup()

    def connection(self):
        connection = sqlite3.connect(
            self.path,
            timeout=30,
            check_same_thread=False,
        )

        connection.row_factory = sqlite3.Row
        return connection

    def setup(self):
        with self.connection() as db:
            db.execute("""
                CREATE TABLE IF NOT EXISTS reference_chunks (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    title TEXT NOT NULL,
                    madhab TEXT DEFAULT '',
                    text TEXT NOT NULL,
                    embedding TEXT NOT NULL,
                    content_hash TEXT UNIQUE NOT NULL,
                    created_at TEXT NOT NULL
                )
            """)

            db.commit()

    def count_chunks(self) -> int:
        with self.connection() as db:
            return db.execute(
                """
                SELECT COUNT(*)
                FROM reference_chunks
                """
            ).fetchone()[0]

    def chunks(self):
        with self.connection() as db:
            return [
                dict(row)
                for row in db.execute(
                    """
                    SELECT *
                    FROM reference_chunks
                    ORDER BY id
                    """
                ).fetchall()
            ]

    def add_chunk(
        self,
        title: str,
        madhab: str,
        text: str,
        embedding: List[float],
    ) -> bool:
        content_hash = hashlib.sha256(
            f"{title}|{madhab}|{text}".encode()
        ).hexdigest()

        with self.connection() as db:
            try:
                db.execute(
                    """
                    INSERT INTO reference_chunks (
                        title,
                        madhab,
                        text,
                        embedding,
                        content_hash,
                        created_at
                    )
                    VALUES (?, ?, ?, ?, ?, ?)
                    """,
                    (
                        title.strip(),
                        madhab or "",
                        text.strip(),
                        json.dumps(embedding),
                        content_hash,
                        now_iso(),
                    ),
                )

                db.commit()
                return True

            except sqlite3.IntegrityError:
                return False


# ============================================================
# Gemini service
# ============================================================

class GeminiService:
    def __init__(self):
        self.enabled = bool(
            USE_GEMINI and gemini_client
        )

    def generate(
        self,
        prompt: str,
        use_search: bool = True,
    ) -> Optional[str]:
        if not self.enabled:
            return None

        try:
            config_args = {
                "temperature": 0.2,
            }

            if use_search:
                config_args["tools"] = [
                    types.Tool(
                        google_search=types.GoogleSearch()
                    )
                ]

            config = types.GenerateContentConfig(
                **config_args
            )

            response = gemini_client.models.generate_content(
                model=GEMINI_MODEL,
                contents=prompt,
                config=config,
            )

            return (
                response.text.strip()
                if response.text
                else None
            )

        except Exception:
            logger.exception(
                "Gemini generation failed"
            )
            return None

    def embed(
        self,
        text: str,
        task_type: str = "RETRIEVAL_DOCUMENT",
    ) -> Optional[List[float]]:
        if not self.enabled:
            return None

        try:
            response = gemini_client.models.embed_content(
                model=EMBED_MODEL,
                contents=text,
                config=types.EmbedContentConfig(
                    task_type=task_type,
                    output_dimensionality=768,
                ),
            )

            return response.embeddings[0].values

        except Exception:
            logger.exception(
                "Gemini embedding failed"
            )
            return None


# ============================================================
# Reference retrieval
# ============================================================

class ReferenceSearch:
    def __init__(
        self,
        db: Database,
        ai: GeminiService,
    ):
        self.db = db
        self.ai = ai

    def retrieve(
        self,
        query: str,
        madhabs: List[str],
        limit: int = 5,
    ):
        if self.db.count_chunks() == 0:
            return []

        vector = self.ai.embed(
            query,
            task_type="RETRIEVAL_QUERY",
        )

        if not vector:
            return []

        query_vector = np.array(
            vector,
            dtype=np.float32,
        )

        allowed = set(madhabs)
        allowed.add("")

        scored = []

        for item in self.db.chunks():
            if item["madhab"] not in allowed:
                continue

            try:
                item_vector = np.array(
                    json.loads(item["embedding"]),
                    dtype=np.float32,
                )

                denominator = (
                    np.linalg.norm(query_vector)
                    * np.linalg.norm(item_vector)
                )

                score = (
                    float(
                        np.dot(
                            query_vector,
                            item_vector,
                        )
                        / denominator
                    )
                    if denominator
                    else 0.0
                )

                scored.append(
                    (
                        score,
                        item,
                    )
                )

            except Exception:
                logger.exception(
                    "Invalid reference embedding"
                )

        scored.sort(
            key=lambda value: value[0],
            reverse=True,
        )

        return [
            item
            for score, item in scored[:limit]
            if score >= 0.4
        ]


# ============================================================
# User interface
# ============================================================

def apply_css(lang: str):
    meta = LANGUAGES[lang]

    st.markdown(
        f"""
        <style>
        [data-testid="stAppViewContainer"] .main,
        [data-testid="stSidebar"] {{
            direction: {meta["direction"]};
            text-align: {meta["align"]};
        }}

        [data-testid="stSidebar"] * {{
            text-align: {meta["align"]};
        }}

        .header {{
            direction: {meta["direction"]};
            text-align: center;
            padding: 2rem 1rem;
            margin-bottom: 1.5rem;
            border-radius: 1.25rem;
            color: white;
            background: linear-gradient(
                135deg,
                #0f766e,
                #1d4ed8
            );
        }}

        .logo {{
            font-size: 3rem;
        }}

        .title {{
            margin-top: .5rem;
            font-size: clamp(1.4rem, 3vw, 2.3rem);
            font-weight: 800;
        }}

        .subtitle {{
            margin-top: .5rem;
            line-height: 1.8;
        }}

        textarea,
        input {{
            direction: {meta["direction"]} !important;
            text-align: {meta["align"]} !important;
        }}

        div[data-testid="stExpander"] {{
            direction: {meta["direction"]};
            text-align: {meta["align"]};
        }}

        .card {{
            direction: {meta["direction"]};
            text-align: {meta["align"]};
            background: white;
            border: 1px solid #e2e8f0;
            border-radius: 1rem;
            padding: 1rem;
            margin: .75rem 0;
        }}
        </style>
        """,
        unsafe_allow_html=True,
    )


def language_bar() -> str:
    if "lang" not in st.session_state:
        st.session_state.lang = "ar"

    columns = st.columns(
        len(LANGUAGES)
    )

    for column, code in zip(
        columns,
        LANGUAGES,
    ):
        with column:
            meta = LANGUAGES[code]

            if st.button(
                f"{meta['flag']} {meta['name']}",
                key=f"language_{code}",
                use_container_width=True,
                type=(
                    "primary"
                    if code == st.session_state.lang
                    else "secondary"
                ),
            ):
                st.session_state.lang = code
                st.rerun()

    return st.session_state.lang


def render_header(lang: str):
    text = UI[lang]

    st.markdown(
        f"""
        <div class="header">
            <div class="logo">📚</div>
            <div class="title">{text["title"]}</div>
            <div class="subtitle">{text["subtitle"]}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_countries(
    lang: str,
    text: Dict[str, str],
):
    with st.expander(
        text["countries"],
        expanded=False,
    ):
        for item in COUNTRIES:
            flag = item.get("flag", "🌍")
            name = text_for(
                item.get("name", ""),
                lang,
            )

            madhab = text_for(
                item.get("madhab", ""),
                lang,
            )

            population = text_for(
                item.get("population", ""),
                lang,
            )

            st.markdown(
                f"{flag} **{name}** — "
                f"{madhab} — {population}"
            )

            summary = text_for(
                item.get("madhab_summary", ""),
                lang,
            )

            if summary:
                with st.expander(
                    madhab,
                    expanded=False,
                ):
                    st.write(summary)


def render_scholars(
    lang: str,
    text: Dict[str, str],
):
    with st.expander(
        text["scholars"],
        expanded=False,
    ):
        for code, item in MADHABS.items():
            name = text_for(
                item.get("name", code),
                lang,
                code,
            )

            with st.expander(
                name,
                expanded=False,
            ):
                fields = [
                    ("founder", "الإمام المؤسس"),
                    ("life", "فترة الحياة"),
                    ("birthplace", "مكان الميلاد"),
                    ("origin", "مكان النشأة والانتشار"),
                    ("scholars", "أشهر العلماء"),
                    ("summary", "نبذة"),
                ]

                for key, label in fields:
                    value = text_for(
                        item.get(key, ""),
                        lang,
                    )

                    if value:
                        st.markdown(
                            f"**{label}:** {value}"
                        )


def render_sources(
    lang: str,
    text: Dict[str, str],
):
    with st.expander(
        text["sources"],
        expanded=False,
    ):
        for item in LEGAL_SOURCES:
            name = text_for(
                item.get("name", ""),
                lang,
            )

            description = text_for(
                item.get("description", ""),
                lang,
            )

            with st.expander(
                name,
                expanded=False,
            ):
                st.write(description)


def render_glossary(
    lang: str,
    text: Dict[str, str],
):
    with st.expander(
        text["glossary"],
        expanded=False,
    ):
        for item in GLOSSARY:
            name = text_for(
                item.get("name", ""),
                lang,
            )

            definition = text_for(
                item.get("definition", ""),
                lang,
            )

            example = text_for(
                item.get("example", ""),
                lang,
            )

            with st.expander(
                name,
                expanded=False,
            ):
                st.markdown(
                    f"**{text['definition']}:** "
                    f"{definition}"
                )

                st.markdown(
                    f"**{text['example']}:** "
                    f"{example}"
                )


def render_rules(
    lang: str,
    text: Dict[str, str],
):
    with st.expander(
        text["rules"],
        expanded=False,
    ):
        for item in RULES:
            name = text_for(
                item.get("name", ""),
                lang,
            )

            description = text_for(
                item.get("description", ""),
                lang,
            )

            example = text_for(
                item.get("example", ""),
                lang,
            )

            with st.expander(
                name,
                expanded=False,
            ):
                st.markdown(
                    f"**{text['definition']}:** "
                    f"{description}"
                )

                st.markdown(
                    f"**{text['example']}:** "
                    f"{example}"
                )


def render_question_panel(
    ai: GeminiService,
    references: ReferenceSearch,
    lang: str,
    text: Dict[str, str],
    selected_madhabs: List[str],
    topic: str,
    level: str,
):
    with st.expander(
        text["questions"],
        expanded=True,
    ):
        question = st.text_area(
            text["placeholder"],
            height=130,
            key="question_input",
        )

        if st.button(
            text["search"],
            key="question_button",
            use_container_width=True,
        ):
            if not question.strip():
                st.warning(text["no_question"])
                return

            if not selected_madhabs:
                st.warning(text["no_madhab"])
                return

            with st.spinner(text["loading"]):
                chunks = references.retrieve(
                    question,
                    selected_madhabs,
                )

                context = "\n\n".join(
                    chunk["text"]
                    for chunk in chunks
                )

                selected_names = ", ".join(
                    madhab_name(
                        code,
                        lang,
                    )
                    for code in selected_madhabs
                )

                prompt = f"""
You are an educational Islamic fiqh research assistant.
You do not issue a personal fatwa.

Question:
{question}

Selected schools:
{selected_names}

Answer style:
{"brief" if level == "brief" else "detailed"}

Uploaded reference context:
{context}

Instructions:
- Answer the exact question.
- Compare only the selected schools.
- Use the uploaded context when relevant.
- If current or externally verifiable information is needed,
  use Google Search grounding.
- Clearly mention disagreement.
- Do not invent citations.
- Write in the selected language.
"""

                answer = ai.generate(
                    prompt,
                    use_search=True,
                )

            if answer:
                st.warning(text["ai_note"])
                st.markdown(answer)
            else:
                st.error(text["no_result"])


def render_references(
    db: Database,
    ai: GeminiService,
    lang: str,
    text: Dict[str, str],
):
    with st.expander(
        text["references"],
        expanded=False,
    ):
        if not ADMIN_PASSWORD:
            st.info(text["access_denied"])
            return

        password = st.text_input(
            text["admin_password"],
            type="password",
        )

        if password != ADMIN_PASSWORD:
            st.info(text["access_denied"])
            return

        title = st.text_input(
            text["source_title"],
        )

        source = st.text_area(
            text["source_text"],
            height=220,
        )

        if st.button(
            text["add_reference"],
        ):
            if not title.strip() or not source.strip():
                st.warning(text["source_text"])
                return

            chunks = [
                source[i:i + 700]
                for i in range(
                    0,
                    len(source),
                    600,
                )
                if len(source[i:i + 700]) > 30
            ]

            added = 0

            for chunk in chunks:
                vector = ai.embed(chunk)

                if vector and db.add_chunk(
                    title,
                    "",
                    chunk,
                    vector,
                ):
                    added += 1

            st.success(
                text["reference_added"].format(
                    added
                )
            )


# ============================================================
# Services and main
# ============================================================

@st.cache_resource
def get_services():
    db = Database()
    ai = GeminiService()
    references = ReferenceSearch(
        db,
        ai,
    )

    return db, ai, references


def main():
    lang = language_bar()
    text = UI[lang]

    apply_css(lang)
    render_header(lang)

    db, ai, references = get_services()

    with st.sidebar:
        st.header(text["madhab"])

        codes = [
            code
            for code in MADHABS
            if not code.startswith("_")
        ]

        selected_madhabs = st.multiselect(
            text["madhab"],
            options=codes,
            default=[
                "maliki",
                "shafii",
                "hanafi",
                "hanbali",
            ],
            format_func=lambda code: madhab_name(
                code,
                lang,
            ),
        )

        topic = st.selectbox(
            text["topic"],
            options=[
                "all",
                "ibadat",
                "muamalat",
                "family",
                "other",
            ],
            format_func=lambda value: (
                text["all_topics"]
                if value == "all"
                else text_for(
                    {
                        "ibadat": {
                            "ar": "العبادات",
                            "en": "Worship",
                        },
                        "muamalat": {
                            "ar": "المعاملات",
                            "en": "Transactions",
                        },
                        "family": {
                            "ar": "الأسرة",
                            "en": "Family",
                        },
                        "other": {
                            "ar": "مواضيع أخرى",
                            "en": "Other topics",
                        },
                    }[value],
                    lang,
                )
            ),
        )

        level = st.radio(
            text["answer_type"],
            options=[
                "brief",
                "detailed",
            ],
            format_func=lambda value: text[value],
            horizontal=True,
        )

        st.divider()

        st.success(
            text["ai_on"]
            if ai.enabled
            else text["ai_off"]
        )

    render_question_panel(
        ai=ai,
        references=references,
        lang=lang,
        text=text,
        selected_madhabs=selected_madhabs,
        topic=topic,
        level=level,
    )

    render_countries(
        lang,
        text,
    )

    render_scholars(
        lang,
        text,
    )

    render_sources(
        lang,
        text,
    )

    render_glossary(
        lang,
        text,
    )

    render_rules(
        lang,
        text,
    )

    render_references(
        db=db,
        ai=ai,
        lang=lang,
        text=text,
    )


if __name__ == "__main__":
    main()
