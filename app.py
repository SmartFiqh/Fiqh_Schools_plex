from __future__ import annotations

import datetime as dt
import hashlib
import json
import logging
import os
import re
import sqlite3
from pathlib import Path
from typing import Any, Dict, List, Optional

import numpy as np
import streamlit as st


# ============================================================
# إعداد الصفحة
# ============================================================

st.set_page_config(
    page_title="SmartFiqh",
    page_icon="📚",
    layout="wide",
    initial_sidebar_state="expanded",
)


# ============================================================
# الإعدادات والمسارات
# ============================================================

ROOT = Path(__file__).resolve().parent
DATA_DIR = ROOT / "data"
DB_PATH = ROOT / "fiqh.db"

GEMINI_MODEL = os.getenv(
    "GEMINI_MODEL",
    "gemini-2.5-flash",
)

EMBED_MODEL = os.getenv(
    "EMBED_MODEL",
    "gemini-embedding-001",
)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


# ============================================================
# Gemini initialization
# ============================================================

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


GEMINI_API_KEY = get_secret(
    "GEMINI_API_KEY"
)

ADMIN_PASSWORD = get_secret(
    "ADMIN_PASSWORD"
)

USE_GEMINI = bool(
    GEMINI_API_KEY
    and GENAI_AVAILABLE
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
# اللغات
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
        "madhab_filter": "تصفية المذاهب",
        "sunni": "مذاهب السنة",
        "shia": "مذاهب الشيعة",
        "ibadi": "المذهب الإباضي",
        "select_sunni": "اختر المذاهب السنية",
        "select_shia": "اختر المذاهب الشيعية",
        "select_ibadi": "اختر المذهب الإباضي",
        "topic": "اختر الموضوع",
        "all_topics": "كل الموضوعات",
        "answer_type": "نوع الإجابة",
        "brief": "مختصرة",
        "detailed": "مفصلة",
        "questions": "❓ أسئلة واستفسارات",
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
        "countries": "🗺️ دول منظمة التعاون الإسلامي",
        "scholars": "📜 الأئمة والعلماء",
        "glossary": "📚 المصطلحات الفقهية",
        "sources": "📜 مصادر التشريع الفقهي",
        "rules": "⚖️ الأصول والقواعد الفقهية",
        "usul": "📚 أصول الاستدلال الفقهي",
        "references": "📁 إدارة المراجع",
        "definition": "التعريف",
        "example": "مثال",
        "note": "ملاحظة",
        "population_note": (
            "أعداد المسلمين تقريبية، والمذهب المذكور هو السائد "
            "أو الأبرز، وليس بالضرورة رسميًا حصريًا."
        ),
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
        "madhab_filter": "Madhhab filter",
        "sunni": "Sunni schools",
        "shia": "Shia schools",
        "ibadi": "Ibadi school",
        "select_sunni": "Choose Sunni schools",
        "select_shia": "Choose Shia schools",
        "select_ibadi": "Choose the Ibadi school",
        "topic": "Choose a topic",
        "all_topics": "All topics",
        "answer_type": "Answer type",
        "brief": "Brief",
        "detailed": "Detailed",
        "questions": "❓ Questions and answers",
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
        "countries": "🗺️ OIC member states",
        "scholars": "📜 Imams and scholars",
        "glossary": "📚 Fiqh terminology",
        "sources": "📜 Sources of Islamic jurisprudence",
        "rules": "⚖️ Fiqh principles and legal maxims",
        "usul": "📚 Principles of legal reasoning",
        "references": "📁 Reference management",
        "definition": "Definition",
        "example": "Example",
        "note": "Note",
        "population_note": (
            "Muslim population figures are approximate. "
            "The listed school is predominant or prominent, "
            "not necessarily exclusive or official."
        ),
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


# ============================================================
# أسماء المذاهب الرئيسية
# ============================================================

CANONICAL_MADHABS = {
    "maliki": {
        "group": "sunni",
        "names": {
            "ar": "مالكي",
            "en": "Maliki",
            "fr": "Malikite",
            "fa": "مالکی",
            "ms": "Maliki",
            "ur": "مالکی",
        },
    },
    "shafii": {
        "group": "sunni",
        "names": {
            "ar": "شافعي",
            "en": "Shafi'i",
            "fr": "Chaféite",
            "fa": "شافعی",
            "ms": "Syafie",
            "ur": "شافعی",
        },
    },
    "hanafi": {
        "group": "sunni",
        "names": {
            "ar": "حنفي",
            "en": "Hanafi",
            "fr": "Hanafite",
            "fa": "حنفی",
            "ms": "Hanafi",
            "ur": "حنفی",
        },
    },
    "hanbali": {
        "group": "sunni",
        "names": {
            "ar": "حنبلي",
            "en": "Hanbali",
            "fr": "Hanbalite",
            "fa": "حنبلی",
            "ms": "Hanbali",
            "ur": "حنبلی",
        },
    },
    "zahiri": {
        "group": "sunni",
        "names": {
            "ar": "ظاهري",
            "en": "Zahiri",
            "fr": "Zahirite",
            "fa": "ظاهری",
            "ms": "Zahiri",
            "ur": "ظاہری",
        },
    },
    "jafari": {
        "group": "shia",
        "names": {
            "ar": "جعفري",
            "en": "Ja'fari",
            "fr": "Jaafarite",
            "fa": "جعفری",
            "ms": "Jaafari",
            "ur": "جعفری",
        },
    },
    "zaidi": {
        "group": "shia",
        "names": {
            "ar": "زيدي",
            "en": "Zaidi",
            "fr": "Zaydite",
            "fa": "زیدی",
            "ms": "Zaidi",
            "ur": "زیدی",
        },
    },
    "ibadi": {
        "group": "ibadi",
        "names": {
            "ar": "إباضي",
            "en": "Ibadi",
            "fr": "Ibadite",
            "fa": "اباضی",
            "ms": "Ibadi",
            "ur": "اباضی",
        },
    },
}


GROUP_CODES = {
    "sunni": [
        "maliki",
        "shafii",
        "hanafi",
        "hanbali",
        "zahiri",
    ],
    "shia": [
        "jafari",
        "zaidi",
    ],
    "ibadi": [
        "ibadi",
    ],
}


# ============================================================
# تحميل الملفات
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
            "Could not load %s: %s",
            path,
            error,
        )
        return default


MadhhabFile = load_json(
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

USUL = load_json(
    "usul.json",
    [],
)


# ============================================================
# مسائل البحث المحلية
# ============================================================

DEFAULT_ISSUES = [
    {
        "topic": "ibadat",
        "title": {
            "ar": "صلاة الجماعة",
            "en": "Congregational prayer",
            "fr": "Prière en congrégation",
            "fa": "نماز جماعت",
            "ms": "Solat berjemaah",
            "ur": "نماز باجماعت",
        },
        "keywords": (
            "جماعة جماعه مسجد صلاة صلاه "
            "congregational prayer jamaah"
        ),
        "rulings": {
            "maliki": {
                "ar": "فرض كفاية في الجملة.",
                "en": "Generally treated as a communal obligation.",
            },
            "shafii": {
                "ar": "فرض كفاية في الجملة.",
                "en": "Generally treated as a communal obligation.",
            },
            "hanafi": {
                "ar": "واجبة على القادر بلا عذر.",
                "en": "Obligatory for an able person without a valid excuse.",
            },
            "hanbali": {
                "ar": "فرض عين على القادر.",
                "en": "An individual obligation for an able person.",
            },
            "zahiri": {
                "ar": "يميل إلى الوجوب بظاهر النصوص.",
                "en": "Tends toward obligation based on the apparent texts.",
            },
            "jafari": {
                "ar": "مستحب مؤكد.",
                "en": "Strongly recommended.",
            },
            "zaidi": {
                "ar": "فرض كفاية.",
                "en": "A communal obligation.",
            },
            "ibadi": {
                "ar": "سنة مؤكدة.",
                "en": "An emphasized Sunnah.",
            },
        },
    },
    {
        "topic": "ibadat",
        "title": {
            "ar": "العمرة",
            "en": "Umrah",
            "fr": "Omra",
            "fa": "عمره",
            "ms": "Umrah",
            "ur": "عمرہ",
        },
        "keywords": (
            "عمرة العمره عمره umrah umra omrah "
            "ihram tawaf sai pilgrimage"
        ),
        "rulings": {},
    },
    {
        "topic": "ibadat",
        "title": {
            "ar": "الوضوء",
            "en": "Ablution",
            "fr": "Ablution",
            "fa": "وضو",
            "ms": "Wuduk",
            "ur": "وضو",
        },
        "keywords": (
            "وضوء وضو طهارة صلاة حدث "
            "wudu ablution purification"
        ),
        "rulings": {},
    },
    {
        "topic": "ibadat",
        "title": {
            "ar": "صيام رمضان",
            "en": "Ramadan fasting",
            "fr": "Jeûne du Ramadan",
            "fa": "روزه رمضان",
            "ms": "Puasa Ramadan",
            "ur": "رمضان کے روزے",
        },
        "keywords": (
            "صيام صوم رمضان فطر "
            "fasting ramadan"
        ),
        "rulings": {},
    },
    {
        "topic": "muamalat",
        "title": {
            "ar": "البيع بالتقسيط",
            "en": "Installment sales",
            "fr": "Vente à tempérament",
            "fa": "فروش اقساطی",
            "ms": "Jualan ansuran",
            "ur": "قسطوں پر فروخت",
        },
        "keywords": (
            "بيع تقسيط ثمن أجل دين "
            "sale installment credit"
        ),
        "rulings": {},
    },
    {
        "topic": "muamalat",
        "title": {
            "ar": "الربا",
            "en": "Riba",
            "fr": "Riba",
            "fa": "ربا",
            "ms": "Riba",
            "ur": "سود",
        },
        "keywords": (
            "ربا فائدة قرض مال زيادة "
            "riba interest loan"
        ),
        "rulings": {},
    },
]


# ============================================================
# Helpers
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
                value.get(
                    "ar",
                    default,
                ),
            )
        )

    return default


def normalize_text(
    text: str,
) -> str:
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


def get_madhab_name(
    code: str,
    lang: str,
) -> str:
    if code in CANONICAL_MADHABS:
        return CANONICAL_MADHABS[code]["names"].get(
            lang,
            CANONICAL_MADHABS[code]["names"]["ar"],
        )

    return text_for(
        MadhhabFile.get(
            code,
            {},
        ).get(
            "name",
            code,
        ),
        lang,
        code,
    )


def get_topic_name(
    code: str,
    lang: str,
) -> str:
    topics = {
        "ibadat": {
            "ar": "العبادات",
            "en": "Worship",
            "fr": "Actes d’adoration",
            "fa": "عبادات",
            "ms": "Ibadah",
            "ur": "عبادات",
        },
        "muamalat": {
            "ar": "المعاملات",
            "en": "Transactions",
            "fr": "Transactions",
            "fa": "معاملات",
            "ms": "Muamalat",
            "ur": "معاملات",
        },
        "family": {
            "ar": "الأسرة",
            "en": "Family",
            "fr": "Famille",
            "fa": "خانواده",
            "ms": "Keluarga",
            "ur": "خاندان",
        },
        "other": {
            "ar": "مواضيع أخرى",
            "en": "Other topics",
            "fr": "Autres sujets",
            "fa": "موضوعات دیگر",
            "ms": "Topik lain",
            "ur": "دیگر موضوعات",
        },
    }

    return topics.get(
        code,
        {},
    ).get(
        lang,
        topics.get(
            code,
            {},
        ).get(
            "ar",
            code,
        ),
    )


def get_madhab_data(
    code: str,
) -> Dict[str, Any]:
    value = MadhhabFile.get(
        code,
        {},
    )

    return value if isinstance(value, dict) else {}


def issue_title(
    issue: Dict[str, Any],
    lang: str,
) -> str:
    return text_for(
        issue.get("title", ""),
        lang,
    )


def issue_ruling(
    issue: Dict[str, Any],
    code: str,
    lang: str,
) -> str:
    value = issue.get(
        "rulings",
        {},
    ).get(
        code,
        "",
    )

    return text_for(
        value,
        lang,
    )


def issue_search_text(
    issue: Dict[str, Any],
    lang: str,
) -> str:
    values = [
        issue_title(
            issue,
            lang,
        ),
        issue.get(
            "keywords",
            "",
        ),
    ]

    for value in issue.get(
        "rulings",
        {},
    ).values():
        if isinstance(value, dict):
            values.extend(
                str(item)
                for item in value.values()
            )
        else:
            values.append(str(value))

    return normalize_text(
        " ".join(values)
    )


# ============================================================
# SQLite
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
            f"{title}|{madhab}|{text}".encode(
                "utf-8"
            )
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
# Gemini
# ============================================================

class GeminiService:
    def __init__(self):
        self.enabled = bool(
            USE_GEMINI and gemini_client
        )

    def generate(
        self,
        prompt: str,
    ) -> Optional[str]:
        if not self.enabled:
            return None

        try:
            config = types.GenerateContentConfig(
                temperature=0.2,
            )

            response = gemini_client.models.generate_content(
                model=GEMINI_MODEL,
                contents=prompt,
                config=config,
            )

            if not response.text:
                return None

            return response.text.strip()

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
            config = types.EmbedContentConfig(
                task_type=task_type,
                output_dimensionality=768,
            )

            response = gemini_client.models.embed_content(
                model=EMBED_MODEL,
                contents=text,
                config=config,
            )

            return response.embeddings[0].values

        except Exception:
            logger.exception(
                "Gemini embedding failed"
            )
            return None

    def answer(
        self,
        question: str,
        madhabs: List[str],
        level: str,
        lang: str,
        context: str = "",
    ) -> Optional[str]:
        selected_names = ", ".join(
            get_madhab_name(
                code,
                lang,
            )
            for code in madhabs
        )

        style = {
            "brief": {
                "ar": "إجابة مختصرة",
                "en": "Brief answer",
                "fr": "Réponse brève",
                "fa": "پاسخ کوتاه",
                "ms": "Jawapan ringkas",
                "ur": "مختصر جواب",
            },
            "detailed": {
                "ar": "إجابة مفصلة",
                "en": "Detailed answer",
                "fr": "Réponse détaillée",
                "fa": "پاسخ مفصل",
                "ms": "Jawapan terperinci",
                "ur": "تفصیلی جواب",
            },
        }

        answer_style = text_for(
            style.get(
                level,
                {},
            ),
            lang,
            "Brief answer",
        )

        prompt = f"""
You are an educational Islamic fiqh research assistant.
You are not issuing a personal fatwa.

Question:
{question}

Selected madhhabs only:
{selected_names}

Answer style:
{answer_style}

Reference context:
{context}

Instructions:
- Answer the exact question.
- Discuss only the selected madhhabs.
- Do not add unselected schools.
- Mention meaningful disagreement.
- Do not invent citations.
- Clearly state when specialist review is needed.
- Write in the selected language.
"""

        return self.generate(
            prompt
        )


# ============================================================
# البحث في المراجع
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

        query_embedding = self.ai.embed(
            query,
            "RETRIEVAL_QUERY",
        )

        if not query_embedding:
            return []

        query_vector = np.array(
            query_embedding,
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
                    json.loads(
                        item["embedding"]
                    ),
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
# البحث المحلي
# ============================================================

class LocalSearch:
    def search(
        self,
        question: str,
        topic: str,
        madhabs: List[str],
        lang: str,
    ):
        query = normalize_text(
            question
        )

        matches = []

        for issue in DEFAULT_ISSUES:
            if (
                topic != "all"
                and issue["topic"] != topic
            ):
                continue

            searchable = issue_search_text(
                issue,
                lang,
            )

            score = sum(
                1
                for word in query.split()
                if len(word) > 2
                and word in searchable
            )

            if score:
                matches.append(
                    (
                        score,
                        issue,
                    )
                )

        matches.sort(
            key=lambda value: value[0],
            reverse=True,
        )

        results = []

        for _, issue in matches[:5]:
            cards = []

            for code in madhabs:
                answer = issue_ruling(
                    issue,
                    code,
                    lang,
                )

                if not answer:
                    answer = (
                        "تحتاج هذه المسألة إلى "
                        "بحث تفصيلي في مصادر المذهب."
                        if lang == "ar"
                        else "This issue requires detailed "
                        "research in the school's sources."
                    )

                cards.append({
                    "code": code,
                    "answer": answer,
                })

            results.append({
                "title": issue_title(
                    issue,
                    lang,
                ),
                "topic": issue["topic"],
                "cards": cards,
            })

        return results


# ============================================================
# CSS
# ============================================================

def apply_css(
    lang: str,
):
    metadata = LANGUAGES[lang]

    st.markdown(
        f"""
        <style>
        [data-testid="stAppViewContainer"] .main,
        [data-testid="stSidebar"] {{
            direction: {metadata["direction"]};
            text-align: {metadata["align"]};
        }}

        [data-testid="stSidebar"] * {{
            text-align: {metadata["align"]};
        }}

        .header {{
            direction: {metadata["direction"]};
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
            box-shadow: 0 12px 30px
                rgba(15, 23, 42, .15);
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
            direction: {metadata["direction"]} !important;
            text-align: {metadata["align"]} !important;
        }}

        div[data-testid="stExpander"] {{
            direction: {metadata["direction"]};
            text-align: {metadata["align"]};
        }}

        .card {{
            direction: {metadata["direction"]};
            text-align: {metadata["align"]};
            background: white;
            border: 1px solid #e2e8f0;
            border-radius: 1rem;
            padding: 1rem;
            margin: .75rem 0;
            box-shadow: 0 4px 12px
                rgba(15, 23, 42, .05);
        }}
        </style>
        """,
        unsafe_allow_html=True,
    )


# ============================================================
# شريط اللغة والترويسة
# ============================================================

def render_language_bar() -> str:
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
            item = LANGUAGES[code]

            if st.button(
                f"{item['flag']} {item['name']}",
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


def render_header(
    lang: str,
):
    text = UI[lang]

    st.markdown(
        f"""
        <div class="header">
            <div class="logo">📚</div>
            <div class="title">
                {text["title"]}
            </div>
            <div class="subtitle">
                {text["subtitle"]}
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


# ============================================================
# تصفية المذاهب بثلاثة فروع
# ============================================================

def render_madhab_filter(
    lang: str,
    text: Dict[str, str],
) -> List[str]:
    previous = st.session_state.get(
        "selected_madhabs",
        [
            "maliki",
            "shafii",
            "hanafi",
            "hanbali",
        ],
    )

    with st.expander(
        text["madhab_filter"],
        expanded=False,
    ):
        with st.expander(
            text["sunni"],
            expanded=False,
        ):
            sunni_options = [
                code
                for code in GROUP_CODES["sunni"]
                if code in CANONICAL_MADHABS
            ]

            sunni_defaults = [
                code
                for code in previous
                if code in sunni_options
            ]

            sunni_selected = st.multiselect(
                text["select_sunni"],
                options=sunni_options,
                default=sunni_defaults,
                format_func=lambda code: get_madhab_name(
                    code,
                    lang,
                ),
                key="sunni_madhabs",
            )

        with st.expander(
            text["shia"],
            expanded=False,
        ):
            shia_options = [
                code
                for code in GROUP_CODES["shia"]
                if code in CANONICAL_MADHABS
            ]

            shia_defaults = [
                code
                for code in previous
                if code in shia_options
            ]

            shia_selected = st.multiselect(
                text["select_shia"],
                options=shia_options,
                default=shia_defaults,
                format_func=lambda code: get_madhab_name(
                    code,
                    lang,
                ),
                key="shia_madhabs",
            )

        with st.expander(
            text["ibadi"],
            expanded=False,
        ):
            ibadi_options = [
                code
                for code in GROUP_CODES["ibadi"]
                if code in CANONICAL_MADHABS
            ]

            ibadi_defaults = [
                code
                for code in previous
                if code in ibadi_options
            ]

            ibadi_selected = st.multiselect(
                text["select_ibadi"],
                options=ibadi_options,
                default=ibadi_defaults,
                format_func=lambda code: get_madhab_name(
                    code,
                    lang,
                ),
                key="ibadi_madhabs",
            )

    selected = list(dict.fromkeys(
        sunni_selected
        + shia_selected
        + ibadi_selected
    ))

    st.session_state.selected_madhabs = selected

    return selected


# ============================================================
# الأسئلة
# ============================================================

def render_questions(
    ai: GeminiService,
    references: ReferenceSearch,
    local_search: LocalSearch,
    lang: str,
    text: Dict[str, str],
    madhabs: List[str],
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
            key="search_question",
            use_container_width=True,
        ):
            if not question.strip():
                st.warning(
                    text["no_question"]
                )
                return

            if not madhabs:
                st.warning(
                    text["no_madhab"]
                )
                return

            local_results = local_search.search(
                question,
                topic,
                madhabs,
                lang,
            )

            if local_results:
                for result in local_results:
                    st.markdown(
                        '<div class="card">',
                        unsafe_allow_html=True,
                    )

                    st.subheader(
                        result["title"]
                    )

                    st.caption(
                        get_topic_name(
                            result["topic"],
                            lang,
                        )
                    )

                    columns = st.columns(
                        len(result["cards"])
                    )

                    for column, card in zip(
                        columns,
                        result["cards"],
                    ):
                        with column:
                            label = get_madhab_name(
                                card["code"],
                                lang,
                            )

                            st.markdown(
                                f"### {label}"
                            )

                            st.write(
                                card["answer"]
                            )

                    st.markdown(
                        "</div>",
                        unsafe_allow_html=True,
                    )

                return

            with st.spinner(
                text["loading"]
            ):
                chunks = references.retrieve(
                    question,
                    madhabs,
                )

                context = "\n\n".join(
                    chunk["text"]
                    for chunk in chunks
                )

                answer = ai.answer(
                    question=question,
                    madhabs=madhabs,
                    level=level,
                    lang=lang,
                    context=context,
                )

            if answer:
                st.warning(
                    text["ai_note"]
                )
                st.markdown(answer)
            else:
                st.error(
                    text["no_result"]
                )


# ============================================================
# الدول
# ============================================================

def render_countries(
    lang: str,
    text: Dict[str, str],
):
    with st.expander(
        text["countries"],
        expanded=False,
    ):
        st.caption(
            text["population_note"]
        )

        for item in COUNTRIES:
            name = text_for(
                item.get("name", ""),
                lang,
            )

            flag = item.get(
                "flag",
                "🌍",
            )

            muslims = text_for(
                item.get("muslims", ""),
                lang,
            )

            madhab = text_for(
                item.get("madhab", ""),
                lang,
            )

            st.markdown(
                f"{flag} **{name}** — "
                f"{muslims} — {madhab}"
            )


# ============================================================
# العلماء
# ============================================================

def render_scholars(
    lang: str,
    text: Dict[str, str],
):
    with st.expander(
        text["scholars"],
        expanded=False,
    ):
        for code in CANONICAL_MADHABS:
            name = get_madhab_name(
                code,
                lang,
            )

            data = get_madhab_data(
                code
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

                for field, label in fields:
                    value = text_for(
                        data.get(field, ""),
                        lang,
                    )

                    if value:
                        st.markdown(
                            f"**{label}:** {value}"
                        )


# ============================================================
# المصطلحات
# ============================================================

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


# ============================================================
# مصادر التشريع
# ============================================================

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
                st.write(
                    description
                )


# ============================================================
# القواعد
# ============================================================

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


# ============================================================
# أصول الفقه
# ============================================================

def render_usul(
    lang: str,
    text: Dict[str, str],
):
    with st.expander(
        text["usul"],
        expanded=False,
    ):
        for item in USUL:
            name = text_for(
                item.get("name", ""),
                lang,
            )

            definition = text_for(
                item.get("definition", ""),
                lang,
            )

            note = text_for(
                item.get("note", ""),
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

                if note:
                    st.markdown(
                        f"**{text['note']}:** "
                        f"{note}"
                    )


# ============================================================
# إدارة المراجع
# ============================================================

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
            st.info(
                text["access_denied"]
            )
            return

        password = st.text_input(
            text["admin_password"],
            type="password",
            key="admin_password",
        )

        if password != ADMIN_PASSWORD:
            st.info(
                text["access_denied"]
            )
            return

        title = st.text_input(
            text["source_title"],
            key="reference_title",
        )

        source = st.text_area(
            text["source_text"],
            height=220,
            key="reference_text",
        )

        if st.button(
            text["add_reference"],
            key="add_reference_button",
        ):
            if not title.strip() or not source.strip():
                st.warning(
                    text["source_text"]
                )
                return

            if not ai.enabled:
                st.error(
                    text["ai_off"]
                )
                return

            chunks = [
                source[i:i + 700]
                for i in range(
                    0,
                    len(source),
                    600,
                )
                if len(
                    source[i:i + 700]
                ) > 30
            ]

            added = 0

            with st.spinner(
                text["loading"]
            ):
                for chunk in chunks:
                    vector = ai.embed(
                        chunk,
                        "RETRIEVAL_DOCUMENT",
                    )

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
# الخدمات
# ============================================================

@st.cache_resource
def get_services():
    db = Database()
    ai = GeminiService()
    references = ReferenceSearch(
        db,
        ai,
    )
    local_search = LocalSearch()

    return (
        db,
        ai,
        references,
        local_search,
    )


# ============================================================
# التشغيل الرئيسي
# ============================================================

def main():
    lang = render_language_bar()
    text = UI[lang]

    apply_css(lang)
    render_header(lang)

    (
        db,
        ai,
        references,
        local_search,
    ) = get_services()

    with st.sidebar:
        selected_madhabs = render_madhab_filter(
            lang,
            text,
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
                else get_topic_name(
                    value,
                    lang,
                )
            ),
            key="topic_selector",
        )

        level = st.radio(
            text["answer_type"],
            options=[
                "brief",
                "detailed",
            ],
            format_func=lambda value: text[value],
            horizontal=True,
            key="answer_level",
        )

        st.divider()

        st.success(
            text["ai_on"]
            if ai.enabled
            else text["ai_off"]
        )

    render_questions(
        ai=ai,
        references=references,
        local_search=local_search,
        lang=lang,
        text=text,
        madhabs=selected_madhabs,
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

    render_usul(
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
