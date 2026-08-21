from __future__ import annotations

import datetime as dt
import hashlib
import json
import logging
import os
import re
import sqlite3
from collections import OrderedDict
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Tuple

import numpy as np
import streamlit as st


# ============================================================
# Page setup
# ============================================================

st.set_page_config(
    page_title="الجامع المختصر لآراء المذاهب",
    page_icon="📚",
    layout="wide",
    initial_sidebar_state="expanded",
)


# ============================================================
# Configuration
# ============================================================

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

DB_PATH = os.getenv("FIQH_DB_PATH", "fiqh.db")
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")
EMBED_MODEL = os.getenv("EMBED_MODEL", "gemini-embedding-001")


try:
    from dotenv import load_dotenv

    load_dotenv()
except ImportError:
    pass


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
# Language metadata
# ============================================================

LANGUAGE_META = {
    "ar": {
        "label": "العربية",
        "flag": "🇪🇬",
        "direction": "rtl",
        "align": "right",
    },
    "en": {
        "label": "English",
        "flag": "🇬🇧",
        "direction": "ltr",
        "align": "left",
    },
    "fr": {
        "label": "Français",
        "flag": "🇫🇷",
        "direction": "ltr",
        "align": "left",
    },
    "fa": {
        "label": "فارسی",
        "flag": "🇮🇷",
        "direction": "rtl",
        "align": "right",
    },
    "ms": {
        "label": "Melayu",
        "flag": "🇲🇾",
        "direction": "ltr",
        "align": "left",
    },
    "ur": {
        "label": "اردو",
        "flag": "🇵🇰",
        "direction": "rtl",
        "align": "right",
    },
}


UI = {
    "ar": {
        "app_title": "الجامع المختصر لآراء المذاهب",
        "app_subtitle": (
            "منصة تعليمية لعرض ومقارنة الآراء الفقهية "
            "للفهم والتبصر، وليست موقعًا للإفتاء."
        ),
        "choose_madhab": "اختر المذهب",
        "choose_one_or_more": "اختر مذهبًا واحدًا أو أكثر",
        "choose_topic": "اختر الموضوع",
        "all_topics": "كل الموضوعات",
        "choose_level": "مستوى التفصيل",
        "very_short": "مختصرة جدًا",
        "short": "مختصرة",
        "full": "مفصلة",
        "write_question": "اكتب سؤالك",
        "question_placeholder": "مثال: ما حكم صلاة الجماعة؟",
        "search": "🔍 ابحث عن الإجابة",
        "no_question": "الرجاء كتابة السؤال أولًا.",
        "no_madhab": "الرجاء اختيار مذهب واحد على الأقل.",
        "no_results": (
            "لم توجد مسألة مطابقة، ولم تُنتج خدمة Gemini إجابة "
            "قابلة للعرض. جرّب صياغة السؤال بطريقة أخرى."
        ),
        "ai_generating": "جاري تحليل السؤال والبحث عن الإجابة...",
        "ai_badge": "🤖 إجابة بحثية مولدة بالذكاء الاصطناعي",
        "ai_disclaimer": (
            "هذه إجابة بحثية آلية وليست فتوى، "
            "ويجب مراجعتها لدى عالم مؤهل."
        ),
        "rag_badge": "📖 مبني على المراجع المرفوعة: {}",
        "reference_management": "📁 إدارة المراجع — للمشرفين",
        "reference_intro": (
            "ارفع نصوصًا تملك حقوق استخدامها. "
            "سيتم تقسيمها وفهرستها للبحث الدلالي."
        ),
        "source_title": "عنوان المصدر",
        "source_madhab": "المذهب المرتبط بالمصدر",
        "source_text": "نص المرجع",
        "source_file": "أو ارفع ملف TXT",
        "add_reference": "إضافة وفهرسة المرجع",
        "reference_empty": "الرجاء إدخال عنوان ونص أو رفع ملف.",
        "reference_failed": "تعذرت الفهرسة. تحقق من إعداد Gemini.",
        "reference_success": "تمت إضافة {} مقاطع من المصدر «{}».",
        "indexed_sources": "المصادر المفهرسة",
        "no_sources": "لا توجد مراجع مفهرسة.",
        "glossary": "📚 المصطلحات الفقهية",
        "countries": "🗺️ الدول والمذاهب الفقهية الغالبة",
        "rules": "📘 الأصول والقواعد الفقهية",
        "definition": "التعريف",
        "example": "مثال",
        "warning_terms": (
            "تنبيه: قد يختلف استعمال بعض المصطلحات بين المذاهب، "
            "خصوصًا الفرض والواجب والمكروه."
        ),
        "comments": "💬 ملاحظات الجلسة",
        "comment": "اكتب ملاحظتك",
        "rating": "تقييم الإجابة",
        "send_comment": "إرسال",
        "comment_saved": "تم حفظ الملاحظة لهذه الجلسة.",
        "admin_password": "كلمة مرور المشرف",
        "admin_denied": "لا تملك صلاحية إدارة المراجع.",
        "normalization": "صياغة السؤال المفهومة",
        "confidence": "درجة الثقة",
        "general_source": "مصدر عام",
        "country_note": (
            "المذكور هو الغالب أو الأبرز تاريخيًا، "
            "وليس بالضرورة نظامًا قانونيًا حصريًا."
        ),
        "ai_on": "Gemini AI: مفعّل",
        "ai_off": "Gemini AI: غير مفعّل — البحث المحلي فقط",
        "admin_missing": "ADMIN_PASSWORD غير مضبوط في Secrets.",
    },
    "en": {
        "app_title": "The Concise Compendium of Madhhab Opinions",
        "app_subtitle": (
            "An educational platform for comparing fiqh opinions. "
            "It is not a fatwa service."
        ),
        "choose_madhab": "Choose a madhhab",
        "choose_one_or_more": "Choose one or more schools",
        "choose_topic": "Choose a topic",
        "all_topics": "All topics",
        "choose_level": "Answer detail",
        "very_short": "Very short",
        "short": "Short",
        "full": "Detailed",
        "write_question": "Write your question",
        "question_placeholder": (
            "Example: What is the ruling on congregational prayer?"
        ),
        "search": "🔍 Search",
        "no_question": "Please enter a question first.",
        "no_madhab": "Please choose at least one school.",
        "no_results": (
            "No matching issue was found, and Gemini did not return "
            "a usable answer. Try rephrasing the question."
        ),
        "ai_generating": "Analyzing the question and searching...",
        "ai_badge": "🤖 AI-generated research answer",
        "ai_disclaimer": (
            "This is an automated research answer, not a fatwa. "
            "Consult a qualified scholar."
        ),
        "rag_badge": "📖 Based on uploaded references: {}",
        "reference_management": "📁 Reference management — admins",
        "reference_intro": (
            "Upload reference texts you have rights to use."
        ),
        "source_title": "Source title",
        "source_madhab": "Related school",
        "source_text": "Reference text",
        "source_file": "Or upload a TXT file",
        "add_reference": "Add and index reference",
        "reference_empty": "Enter a title and text or upload a file.",
        "reference_failed": "Indexing failed. Check Gemini settings.",
        "reference_success": "Added {} chunks from “{}”.",
        "indexed_sources": "Indexed sources",
        "no_sources": "No indexed references.",
        "glossary": "📚 Fiqh terminology",
        "countries": "🗺️ Countries and prevailing schools",
        "rules": "📘 Fiqh principles and legal maxims",
        "definition": "Definition",
        "example": "Example",
        "warning_terms": (
            "Terminology may differ between schools, especially "
            "fard, wajib, and makruh."
        ),
        "comments": "💬 Session notes",
        "comment": "Write your note",
        "rating": "Rate the answer",
        "send_comment": "Submit",
        "comment_saved": "The note was saved for this session.",
        "admin_password": "Admin password",
        "admin_denied": "You do not have permission.",
        "normalization": "Normalized question",
        "confidence": "Confidence",
        "general_source": "General source",
        "country_note": (
            "These are historical or prevailing patterns, "
            "not necessarily exclusive legal systems."
        ),
        "ai_on": "Gemini AI: enabled",
        "ai_off": "Gemini AI: disabled — local search only",
        "admin_missing": "ADMIN_PASSWORD is not configured.",
    },
    "fr": {
        "app_title": "Recueil concis des avis des écoles juridiques",
        "app_subtitle": (
            "Plateforme éducative de comparaison du fiqh. "
            "Ce service ne délivre pas de fatwas."
        ),
        "choose_madhab": "Choisir l’école",
        "choose_one_or_more": "Choisissez une ou plusieurs écoles",
        "choose_topic": "Choisir le sujet",
        "all_topics": "Tous les sujets",
        "choose_level": "Niveau de détail",
        "very_short": "Très bref",
        "short": "Bref",
        "full": "Détaillé",
        "write_question": "Écrivez votre question",
        "question_placeholder": (
            "Exemple : Quel est le statut de la prière en congrégation ?"
        ),
        "search": "🔍 Rechercher",
        "no_question": "Veuillez écrire une question.",
        "no_madhab": "Veuillez choisir au moins une école.",
        "no_results": "Aucun résultat approprié.",
        "ai_generating": "Analyse et recherche en cours...",
        "ai_badge": "🤖 Réponse de recherche générée par IA",
        "ai_disclaimer": "Ceci est une réponse de recherche, pas une fatwa.",
        "rag_badge": "📖 Basé sur les références: {}",
        "reference_management": "📁 Gestion des références",
        "reference_intro": "Ajoutez des textes dont vous avez les droits.",
        "source_title": "Titre de la source",
        "source_madhab": "École concernée",
        "source_text": "Texte de référence",
        "source_file": "Ou fichier TXT",
        "add_reference": "Ajouter et indexer",
        "reference_empty": "Ajoutez un titre et un texte.",
        "reference_failed": "Échec de l’indexation.",
        "reference_success": "{} segments ajoutés de «{}».",
        "indexed_sources": "Sources indexées",
        "no_sources": "Aucune source indexée.",
        "glossary": "📚 Terminologie du fiqh",
        "countries": "🗺️ Pays et écoles dominantes",
        "rules": "📘 Principes et maximes du fiqh",
        "definition": "Définition",
        "example": "Exemple",
        "warning_terms": "La terminologie peut varier selon les écoles.",
        "comments": "💬 Notes de session",
        "comment": "Votre note",
        "rating": "Évaluation",
        "send_comment": "Envoyer",
        "comment_saved": "Note enregistrée.",
        "admin_password": "Mot de passe admin",
        "admin_denied": "Accès refusé.",
        "normalization": "Question normalisée",
        "confidence": "Confiance",
        "general_source": "Source générale",
        "country_note": (
            "Tendances historiques ou dominantes, "
            "pas nécessairement des systèmes exclusifs."
        ),
        "ai_on": "Gemini AI : activé",
        "ai_off": "Gemini AI : désactivé",
        "admin_missing": "ADMIN_PASSWORD n’est pas configuré.",
    },
}


UI["fa"] = {**UI["en"]}
UI["fa"].update({
    "app_title": "مجموعه مختصر دیدگاه‌های مذاهب فقهی",
    "app_subtitle": "سامانه‌ای آموزشی برای مقایسه دیدگاه‌های فقهی؛ فتوا صادر نمی‌کند.",
    "choose_madhab": "مذهب را انتخاب کنید",
    "choose_one_or_more": "یک یا چند مذهب را انتخاب کنید",
    "choose_topic": "موضوع را انتخاب کنید",
    "all_topics": "همه موضوعات",
    "choose_level": "سطح جزئیات",
    "very_short": "بسیار کوتاه",
    "short": "کوتاه",
    "full": "کامل",
    "write_question": "پرسش خود را بنویسید",
    "question_placeholder": "مثال: حکم نماز جماعت چیست؟",
    "search": "🔍 جست‌وجو",
    "no_question": "لطفاً ابتدا پرسش را بنویسید.",
    "no_madhab": "لطفاً حداقل یک مذهب را انتخاب کنید.",
    "no_results": "نتیجه مناسبی پیدا نشد.",
    "ai_generating": "در حال تحلیل پرسش و جست‌وجو...",
    "ai_badge": "🤖 پاسخ پژوهشی تولیدشده با هوش مصنوعی",
    "ai_disclaimer": "این پاسخ فتوا نیست و باید توسط عالم متخصص بررسی شود.",
    "glossary": "📚 اصطلاحات فقهی",
    "countries": "🗺️ کشورها و مذاهب رایج",
    "rules": "📘 اصول و قواعد فقهی",
    "definition": "تعریف",
    "example": "مثال",
    "comments": "💬 یادداشت‌های جلسه",
    "comment": "یادداشت خود را بنویسید",
    "rating": "ارزیابی پاسخ",
    "send_comment": "ارسال",
    "comment_saved": "یادداشت ذخیره شد.",
    "admin_password": "رمز مدیر",
    "admin_denied": "دسترسی ندارید.",
    "normalization": "بازنویسی پرسش",
    "confidence": "میزان اطمینان",
    "general_source": "منبع عمومی",
    "country_note": "این موارد گرایش‌های تاریخی یا غالب هستند.",
    "ai_on": "Gemini AI: فعال",
    "ai_off": "Gemini AI: غیرفعال",
    "admin_missing": "ADMIN_PASSWORD در Secrets تنظیم نشده است.",
})

UI["ms"] = {**UI["en"]}
UI["ms"].update({
    "app_title": "Himpunan Ringkas Pandangan Mazhab",
    "app_subtitle": (
        "Platform pendidikan untuk membandingkan pandangan fiqh; "
        "bukan perkhidmatan fatwa."
    ),
    "choose_madhab": "Pilih mazhab",
    "choose_one_or_more": "Pilih satu atau lebih mazhab",
    "choose_topic": "Pilih topik",
    "all_topics": "Semua topik",
    "choose_level": "Tahap perincian",
    "very_short": "Sangat ringkas",
    "short": "Ringkas",
    "full": "Terperinci",
    "write_question": "Tulis soalan anda",
    "question_placeholder": "Contoh: Apakah hukum solat berjemaah?",
    "search": "🔍 Cari jawapan",
    "no_question": "Sila tulis soalan dahulu.",
    "no_madhab": "Sila pilih sekurang-kurangnya satu mazhab.",
    "no_results": "Tiada hasil yang sesuai ditemui.",
    "ai_generating": "Menganalisis soalan dan mencari jawapan...",
    "ai_badge": "🤖 Jawapan penyelidikan dijana AI",
    "ai_disclaimer": "Ini bukan fatwa dan perlu disemak oleh ulama.",
    "glossary": "📚 Istilah fiqh",
    "countries": "🗺️ Negara dan mazhab utama",
    "rules": "📘 Prinsip dan kaedah fiqh",
    "definition": "Takrif",
    "example": "Contoh",
    "comments": "💬 Nota sesi",
    "comment": "Tulis nota anda",
    "rating": "Nilai jawapan",
    "send_comment": "Hantar",
    "comment_saved": "Nota telah disimpan.",
    "admin_password": "Kata laluan pentadbir",
    "admin_denied": "Anda tidak mempunyai akses.",
    "normalization": "Soalan yang dinormalisasi",
    "confidence": "Tahap keyakinan",
    "general_source": "Sumber umum",
    "country_note": "Ini ialah corak sejarah atau dominan.",
    "ai_on": "Gemini AI: diaktifkan",
    "ai_off": "Gemini AI: dinyahaktifkan",
    "admin_missing": "ADMIN_PASSWORD belum ditetapkan.",
})

UI["ur"] = {**UI["en"]}
UI["ur"].update({
    "app_title": "مذاہب فقہ کے مختصر آراء کا مجموعہ",
    "app_subtitle": (
        "فقہی آراء کے تقابلی مطالعے کا تعلیمی پلیٹ فارم؛ "
        "فتویٰ کی خدمت نہیں۔"
    ),
    "choose_madhab": "مسلک منتخب کریں",
    "choose_one_or_more": "ایک یا زیادہ مسالک منتخب کریں",
    "choose_topic": "موضوع منتخب کریں",
    "all_topics": "تمام موضوعات",
    "choose_level": "تفصیل کی سطح",
    "very_short": "نہایت مختصر",
    "short": "مختصر",
    "full": "تفصیلی",
    "write_question": "اپنا سوال لکھیں",
    "question_placeholder": "مثال: نماز باجماعت کا کیا حکم ہے؟",
    "search": "🔍 جواب تلاش کریں",
    "no_question": "براہ کرم پہلے سوال لکھیں۔",
    "no_madhab": "براہ کرم کم از کم ایک مسلک منتخب کریں۔",
    "no_results": "مناسب نتیجہ نہیں ملا۔",
    "ai_generating": "سوال کا تجزیہ اور تلاش جاری ہے...",
    "ai_badge": "🤖 مصنوعی ذہانت سے تیار کردہ تحقیقی جواب",
    "ai_disclaimer": "یہ فتویٰ نہیں ہے؛ مستند عالم سے رجوع کریں۔",
    "glossary": "📚 فقہی اصطلاحات",
    "countries": "🗺️ ممالک اور غالب فقہی مسالک",
    "rules": "📘 فقہی اصول و قواعد",
    "definition": "تعریف",
    "example": "مثال",
    "comments": "💬 نشست کے نوٹس",
    "comment": "اپنا نوٹ لکھیں",
    "rating": "جواب کی درجہ بندی",
    "send_comment": "جمع کریں",
    "comment_saved": "نوٹ محفوظ کر لیا گیا۔",
    "admin_password": "منتظم کا پاس ورڈ",
    "admin_denied": "آپ کو اجازت نہیں ہے۔",
    "normalization": "سوال کی واضح صورت",
    "confidence": "اعتماد کی سطح",
    "general_source": "عمومی ماخذ",
    "country_note": "یہ تاریخی یا غالب رجحانات ہیں۔",
    "ai_on": "Gemini AI: فعال",
    "ai_off": "Gemini AI: غیر فعال",
    "admin_missing": "ADMIN_PASSWORD سیٹ نہیں کیا گیا۔",
})


# ============================================================
# Madhhabs and topics
# ============================================================

MADHHAB_NAMES = {
    "maliki": {
        "ar": "مالكي",
        "en": "Maliki",
        "fr": "Malikite",
        "fa": "مالکی",
        "ms": "Maliki",
        "ur": "مالکی",
    },
    "shafii": {
        "ar": "شافعي",
        "en": "Shafi'i",
        "fr": "Chaféite",
        "fa": "شافعی",
        "ms": "Syafie",
        "ur": "شافعی",
    },
    "hanafi": {
        "ar": "حنفي",
        "en": "Hanafi",
        "fr": "Hanafite",
        "fa": "حنفی",
        "ms": "Hanafi",
        "ur": "حنفی",
    },
    "hanbali": {
        "ar": "حنبلي",
        "en": "Hanbali",
        "fr": "Hanbalite",
        "fa": "حنبلی",
        "ms": "Hanbali",
        "ur": "حنبلی",
    },
    "zahiri": {
        "ar": "ظاهري",
        "en": "Zahiri",
        "fr": "Zahirite",
        "fa": "ظاهری",
        "ms": "Zahiri",
        "ur": "ظاہری",
    },
    "jafari": {
        "ar": "جعفري",
        "en": "Ja'fari",
        "fr": "Jaafarite",
        "fa": "جعفری",
        "ms": "Jaafari",
        "ur": "جعفری",
    },
    "zaidi": {
        "ar": "زيدي",
        "en": "Zaidi",
        "fr": "Zaydite",
        "fa": "زیدی",
        "ms": "Zaidi",
        "ur": "زیدی",
    },
    "ibadi": {
        "ar": "إباضي",
        "en": "Ibadi",
        "fr": "Ibadite",
        "fa": "اباضی",
        "ms": "Ibadi",
        "ur": "اباضی",
    },
}


TOPICS = {
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


# ============================================================
# Dataclasses
# ============================================================

@dataclass
class Issue:
    id: int
    topic: str
    title: str
    keywords: List[str]
    rulings: Dict[str, str]
    rulings_by_madhab: Dict[str, Dict[str, str]]


@dataclass
class SearchResult:
    title: str
    topic: str
    cards: List[Dict[str, str]]


# ============================================================
# Utilities
# ============================================================

def utc_now_iso() -> str:
    return dt.datetime.now(
        dt.timezone.utc
    ).isoformat()


def normalize_arabic(text: str) -> str:
    replacements = {
        "أ": "ا",
        "إ": "ا",
        "آ": "ا",
        "ى": "ي",
        "ة": "ه",
        "ؤ": "و",
        "ئ": "ي",
    }

    for old, new in replacements.items():
        text = text.replace(old, new)

    text = re.sub(
        r"[ً-ٰٟ]",
        "",
        text,
    )

    text = re.sub(
        r"[^ws]",
        " ",
        text,
    )

    text = re.sub(
        r"s+",
        " ",
        text,
    )

    return text.strip().lower()


def safe_json_loads(
    value: Any,
    default: Any,
) -> Any:
    if not value:
        return default

    try:
        return json.loads(value)
    except Exception:
        return default


# ============================================================
# Database
# ============================================================

class DatabaseManager:
    def __init__(
        self,
        db_path: str = DB_PATH,
    ):
        self.db_path = db_path
        self.initialize_database()
        self.seed_initial_issue()
        self.seed_more_issues()

    def connection(self) -> sqlite3.Connection:
        conn = sqlite3.connect(
            self.db_path,
            timeout=30,
            check_same_thread=False,
        )

        conn.row_factory = sqlite3.Row
        return conn

    def initialize_database(self):
        with self.connection() as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS issues (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    topic TEXT NOT NULL,
                    title_ar TEXT NOT NULL,
                    keywords_ar TEXT DEFAULT '',
                    ruling_vs_ar TEXT DEFAULT '',
                    ruling_s_ar TEXT DEFAULT '',
                    ruling_f_ar TEXT DEFAULT '',
                    rulings_by_madhab_ar TEXT DEFAULT '{}',
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                    updated_at TEXT DEFAULT CURRENT_TIMESTAMP
                )
            """)

            conn.execute("""
                CREATE TABLE IF NOT EXISTS reference_chunks (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    source_title TEXT NOT NULL,
                    madhab_tag TEXT DEFAULT '',
                    chunk_text TEXT NOT NULL,
                    embedding TEXT NOT NULL,
                    added_at TEXT NOT NULL,
                    chunk_hash TEXT UNIQUE NOT NULL
                )
            """)

            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_issues_topic
                ON issues(topic)
            """)

            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_reference_madhab
                ON reference_chunks(madhab_tag)
            """)

            conn.commit()

    def seed_initial_issue(self):
        with self.connection() as conn:
            count = conn.execute(
                "SELECT COUNT(*) FROM issues"
            ).fetchone()[0]

            if count:
                return

            rulings = {
                "maliki": {
                    "very_short": "فرض كفاية",
                    "short": "فرض كفاية في الجملة",
                    "full": (
                        "المشهور عند المالكية أنها فرض كفاية على أهل الحي، "
                        "مع تأكيد المحافظة عليها."
                    ),
                },
                "shafii": {
                    "very_short": "فرض كفاية",
                    "short": "فرض كفاية في الجملة",
                    "full": (
                        "المعتمد عند الشافعية أنها فرض كفاية، "
                        "وتتأكد في حق الرجال القادرين."
                    ),
                },
                "hanafi": {
                    "very_short": "واجب",
                    "short": "واجبة على القادر بلا عذر",
                    "full": (
                        "صلاة الجماعة واجبة عند الحنفية على الرجل القادر "
                        "بلا عذر، مع اختلاف التفصيل."
                    ),
                },
                "hanbali": {
                    "very_short": "فرض عين",
                    "short": "فرض عين على القادر",
                    "full": (
                        "المشهور عند الحنابلة وجوب صلاة الجماعة "
                        "على الرجل القادر بلا عذر."
                    ),
                },
                "zahiri": {
                    "very_short": "فرض عين",
                    "short": "فرض عين بظاهر الأمر",
                    "full": (
                        "يميل الظاهرية إلى الأخذ بظاهر النصوص "
                        "في وجوب صلاة الجماعة."
                    ),
                },
                "jafari": {
                    "very_short": "مستحب مؤكد",
                    "short": "مستحب مؤكد",
                    "full": (
                        "صلاة الجماعة مستحبة استحبابًا مؤكدًا "
                        "بحسب العرض العام للمذهب الجعفري."
                    ),
                },
                "zaidi": {
                    "very_short": "فرض كفاية",
                    "short": "فرض كفاية",
                    "full": (
                        "تذكر المصادر العامة أن صلاة الجماعة "
                        "من شعائر الدين وفرض كفاية."
                    ),
                },
                "ibadi": {
                    "very_short": "سنة مؤكدة",
                    "short": "سنة مؤكدة",
                    "full": (
                        "صلاة الجماعة من شعائر الدين والسنة المؤكدة "
                        "مع اختلاف التفصيل."
                    ),
                },
            }

            conn.execute("""
                INSERT INTO issues (
                    topic,
                    title_ar,
                    keywords_ar,
                    ruling_vs_ar,
                    ruling_s_ar,
                    ruling_f_ar,
                    rulings_by_madhab_ar
                )
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (
                "ibadat",
                "صلاة الجماعة",
                "جماعة,مسجد,صلاة,رجال,فرض,واجب,سنة",
                "تختلف باختلاف المذهب",
                (
                    "تتراوح أقوال الفقهاء بين فرض العين "
                    "وفرض الكفاية والسنة المؤكدة."
                ),
                (
                    "تختلف درجة حكم صلاة الجماعة باختلاف المذهب؛ "
                    "فمن الفقهاء من يعدها فرض كفاية، ومنهم من يعدها "
                    "واجبة أو سنة مؤكدة."
                ),
                json.dumps(
                    rulings,
                    ensure_ascii=False,
                ),
            ))

            conn.commit()

    def seed_more_issues(self):
        more_issues = [
            {
                "topic": "ibadat",
                "title": "الوضوء",
                "keywords": "وضوء,وضو,طهارة,صلاة,حدث",
                "short": (
                    "الوضوء شرط لصحة الصلاة عند وجود الحدث الأصغر."
                ),
            },
            {
                "topic": "ibadat",
                "title": "صيام رمضان",
                "keywords": "صيام,صوم,رمضان,فطر",
                "short": (
                    "صيام رمضان واجب على المسلم المكلف القادر."
                ),
            },
            {
                "topic": "ibadat",
                "title": "صلاة المسافر",
                "keywords": "سفر,مسافر,قصر,جمع,صلاة",
                "short": (
                    "تختلف أحكام القصر والجمع بحسب شروط السفر والمذهب."
                ),
            },
            {
                "topic": "muamalat",
                "title": "البيع بالتقسيط",
                "keywords": "بيع,تقسيط,ثمن,أجل,دين",
                "short": (
                    "يجوز عند ضبط الثمن والأجل وانتفاء الربا والغرر."
                ),
            },
            {
                "topic": "muamalat",
                "title": "الربا",
                "keywords": "ربا,فائدة,قرض,مال,زيادة",
                "short": (
                    "الربا محرم في الجملة، وتفصيل صوره يحتاج إلى دراسة العقد."
                ),
            },
            {
                "topic": "family",
                "title": "النفقة",
                "keywords": "نفقة,زوجة,أولاد,أسرة",
                "short": (
                    "تجب النفقة بحسب الاستطاعة والعرف والحاجة والقرابة."
                ),
            },
            {
                "topic": "family",
                "title": "الزواج",
                "keywords": "زواج,نكاح,زوج,زوجة,مهر",
                "short": (
                    "الزواج عقد له أركان وشروط تختلف بعض تفاصيلها بين المذاهب."
                ),
            },
        ]

        with self.connection() as conn:
            existing = {
                row["title_ar"]
                for row in conn.execute(
                    "SELECT title_ar FROM issues"
                ).fetchall()
            }

            for item in more_issues:
                if item["title"] in existing:
                    continue

                rulings = {}

                for madhab in MADHHAB_NAMES:
                    rulings[madhab] = {
                        "very_short": "يحتاج تفصيلًا",
                        "short": item["short"],
                        "full": item["short"],
                    }

                conn.execute("""
                    INSERT INTO issues (
                        topic,
                        title_ar,
                        keywords_ar,
                        ruling_vs_ar,
                        ruling_s_ar,
                        ruling_f_ar,
                        rulings_by_madhab_ar
                    )
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                """, (
                    item["topic"],
                    item["title"],
                    item["keywords"],
                    "يحتاج تفصيلًا",
                    item["short"],
                    item["short"],
                    json.dumps(
                        rulings,
                        ensure_ascii=False,
                    ),
                ))

            conn.commit()

    def load_issues(
        self,
        topic_filter: str = "all",
    ) -> List[Issue]:
        with self.connection() as conn:
            if topic_filter == "all":
                rows = conn.execute("""
                    SELECT *
                    FROM issues
                    ORDER BY id
                """).fetchall()
            else:
                rows = conn.execute("""
                    SELECT *
                    FROM issues
                    WHERE topic = ?
                    ORDER BY id
                """, (
                    topic_filter,
                )).fetchall()

        issues = []

        for row in rows:
            keywords = [
                item.strip()
                for item in (
                    row["keywords_ar"] or ""
                ).split(",")
                if item.strip()
            ]

            issues.append(Issue(
                id=row["id"],
                topic=row["topic"],
                title=row["title_ar"],
                keywords=keywords,
                rulings={
                    "very_short": row["ruling_vs_ar"],
                    "short": row["ruling_s_ar"],
                    "full": row["ruling_f_ar"],
                },
                rulings_by_madhab=safe_json_loads(
                    row["rulings_by_madhab_ar"],
                    {},
                ),
            ))

        return issues

    def add_reference_chunk(
        self,
        title: str,
        madhab_tag: str,
        chunk_text: str,
        embedding: List[float],
    ) -> bool:
        chunk_hash = hashlib.sha256(
            f"{title}|{madhab_tag}|{chunk_text}".encode(
                "utf-8"
            )
        ).hexdigest()

        with self.connection() as conn:
            try:
                conn.execute("""
                    INSERT INTO reference_chunks (
                        source_title,
                        madhab_tag,
                        chunk_text,
                        embedding,
                        added_at,
                        chunk_hash
                    )
                    VALUES (?, ?, ?, ?, ?, ?)
                """, (
                    title.strip(),
                    madhab_tag or "",
                    chunk_text.strip(),
                    json.dumps(embedding),
                    utc_now_iso(),
                    chunk_hash,
                ))

                conn.commit()
                return True

            except sqlite3.IntegrityError:
                return False

    def get_reference_chunks(self) -> List[Dict[str, Any]]:
        with self.connection() as conn:
            rows = conn.execute("""
                SELECT
                    id,
                    source_title,
                    madhab_tag,
                    chunk_text,
                    embedding
                FROM reference_chunks
                ORDER BY id
            """).fetchall()

        return [
            dict(row)
            for row in rows
        ]

    def count_reference_chunks(self) -> int:
        with self.connection() as conn:
            return conn.execute(
                "SELECT COUNT(*) FROM reference_chunks"
            ).fetchone()[0]

    def list_reference_sources(
        self,
    ) -> List[Tuple[str, int]]:
        with self.connection() as conn:
            rows = conn.execute("""
                SELECT source_title, COUNT(*) AS total
                FROM reference_chunks
                GROUP BY source_title
                ORDER BY source_title
            """).fetchall()

        return [
            (
                row["source_title"],
                row["total"],
            )
            for row in rows
        ]


# ============================================================
# AI service
# ============================================================

class AIService:
    def __init__(self):
        self.available = (
            USE_GEMINI
            and gemini_client is not None
        )

    def generate(
        self,
        prompt: str,
        json_mode: bool = False,
    ) -> Optional[str]:
        if not self.available:
            return None

        try:
            if json_mode:
                config = types.GenerateContentConfig(
                    temperature=0.15,
                    response_mime_type="application/json",
                )
            else:
                config = types.GenerateContentConfig(
                    temperature=0.25,
                )

            response = gemini_client.models.generate_content(
                model=GEMINI_MODEL,
                contents=prompt,
                config=config,
            )

            if not response.text:
                return None

            return response.text.strip()

        except Exception as error:
            logger.exception(
                "Gemini request failed: %s",
                error,
            )
            return None

    def embed_text(
        self,
        text: str,
        task_type: str = "RETRIEVAL_DOCUMENT",
    ) -> Optional[List[float]]:
        if not self.available or not text:
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

    def understand_question(
        self,
        question: str,
        issues: List[Issue],
    ) -> Optional[Dict[str, Any]]:
        if not self.available:
            return None

        newline = chr(10)

        issue_list = newline.join(
            f"{issue.id}: {issue.title}; "
            f"الكلمات: {', '.join(issue.keywords)}"
            for issue in issues
        )

        topic_list = newline.join(
            f"{key}: {value['ar']}"
            for key, value in TOPICS.items()
        )

        prompt = f"""
أنت محلل أسئلة فقهية. لا تصدر فتوى ولا تخترع حكمًا.

السؤال:
{question}

الموضوعات:
{topic_list}

المسائل الموجودة:
{issue_list}

أعد JSON فقط:
{{
  "normalized_question": "صياغة عربية مختصرة دقيقة",
  "topic": "رمز موضوع من القائمة",
  "matched_issue_ids": [1],
  "keywords": ["كلمات مهمة"],
  "confidence": 0.0
}}

القواعد:
- matched_issue_ids أرقام موجودة فقط.
- confidence رقم بين 0 و1.
- إذا لم توجد مسألة مناسبة اجعل القائمة فارغة.
"""

        raw = self.generate(
            prompt,
            json_mode=True,
        )

        if not raw:
            return None

        try:
            data = json.loads(raw)

            valid_ids = {
                issue.id
                for issue in issues
            }

            matched_ids = []

            for item in data.get(
                "matched_issue_ids",
                [],
            ):
                try:
                    number = int(item)

                    if number in valid_ids:
                        matched_ids.append(number)
                except (TypeError, ValueError):
                    continue

            confidence = float(
                data.get(
                    "confidence",
                    0.0,
                )
            )

            return {
                "normalized_question": str(
                    data.get(
                        "normalized_question",
                        question,
                    )
                ),
                "topic": (
                    data.get("topic")
                    if data.get("topic") in TOPICS
                    else "all"
                ),
                "matched_issue_ids": matched_ids,
                "confidence": max(
                    0.0,
                    min(
                        1.0,
                        confidence,
                    ),
                ),
            }

        except Exception:
            logger.exception(
                "Question understanding failed"
            )
            return None

    def parse_text_answers(
        self,
        raw: str,
        madhabs: List[str],
    ) -> Dict[str, str]:
        answers = {}

        if not raw:
            return answers

        current_code = None
        buffer = []

        name_to_code = {}

        for code in madhabs:
            name_to_code[
                MADHHAB_NAMES[code]["ar"]
            ] = code

            name_to_code[
                MADHHAB_NAMES[code]["en"]
            ] = code

        for line in raw.splitlines():
            line = line.strip()

            if not line:
                continue

            detected_code = None

            for name, code in name_to_code.items():
                if (
                    line.startswith(f"{name}:")
                    or line.startswith(f"{name}：")
                    or line.startswith(f"## {name}")
                    or line.startswith(f"### {name}")
                ):
                    detected_code = code
                    break

            if detected_code:
                if current_code and buffer:
                    answers[current_code] = (
                        " ".join(buffer).strip()
                    )

                current_code = detected_code
                buffer = []

                if ":" in line:
                    buffer.append(
                        line.split(
                            ":",
                            1,
                        )[1].strip()
                    )
                elif "：" in line:
                    buffer.append(
                        line.split(
                            "：",
                            1,
                        )[1].strip()
                    )

            elif current_code:
                buffer.append(line)

        if current_code and buffer:
            answers[current_code] = (
                " ".join(buffer).strip()
            )

        return {
            code: answer
            for code, answer in answers.items()
            if answer
        }

    def generate_fallback_answer(
        self,
        question: str,
        madhabs: List[str],
        level: str,
    ) -> Optional[Dict[str, str]]:
        if not self.available:
            return None

        if not question.strip():
            return None

        detail = {
            "very_short": "كلمة أو كلمتين",
            "short": "سطر واحد",
            "full": "فقرة قصيرة من ثلاثة إلى خمسة أسطر",
        }.get(
            level,
            "سطر واحد",
        )

        madhab_names = ", ".join(
            f"{code}: "
            f"{MADHHAB_NAMES[code]['ar']}"
            for code in madhabs
        )

        newline = chr(10)

        output_format = newline.join(
            f"{MADHHAB_NAMES[code]['ar']}: اكتب الإجابة هنا"
            for code in madhabs
        )

        prompt = f"""
أنت مساعد بحثي في الفقه الإسلامي، ولست مفتيًا.

السؤال:
{question}

المذاهب المطلوبة:
{madhab_names}

التعليمات:
- أجب عن السؤال نفسه.
- اذكر الرأي الفقهي المعروف باختصار.
- إذا وجد اختلاف معتبر، اذكره بوضوح.
- لا تخترع مصادر أو نصوصًا.
- لا تقدم الإجابة كفتوى شخصية.
- مستوى التفصيل: {detail}.
- اكتب بالعربية.
- لا تستخدم JSON.
- لا تستخدم Markdown.
- لا تضف مقدمة أو خاتمة.

استخدم هذا الشكل:
{output_format}
"""

        raw = self.generate(
            prompt,
            json_mode=False,
        )

        if not raw:
            logger.warning(
                "Gemini returned empty text answer"
            )
            return None

        answers = self.parse_text_answers(
            raw,
            madhabs,
        )

        if answers:
            return answers

        if len(madhabs) == 1:
            return {
                madhabs[0]: raw.strip()
            }

        return None


# ============================================================
# Reference manager
# ============================================================

class ReferenceManager:
    def __init__(
        self,
        db: DatabaseManager,
        ai: AIService,
    ):
        self.db = db
        self.ai = ai

    def chunk_text(
        self,
        text: str,
        max_chars: int = 700,
        overlap: int = 100,
    ) -> List[str]:
        if overlap >= max_chars:
            raise ValueError(
                "overlap must be smaller than max_chars"
            )

        text = re.sub(
            r"s+",
            " ",
            text,
        ).strip()

        if not text:
            return []

        step = max_chars - overlap
        chunks = []

        for start in range(
            0,
            len(text),
            step,
        ):
            chunk = text[
                start:start + max_chars
            ].strip()

            if len(chunk) > 30:
                chunks.append(chunk)

            if start + max_chars >= len(text):
                break

        return chunks

    def add_document(
        self,
        title: str,
        madhab_tag: str,
        raw_text: str,
    ) -> int:
        if not self.ai.available:
            return -1

        chunks = self.chunk_text(raw_text)

        if not chunks:
            return 0

        embeddings = []

        for chunk in chunks:
            embedding = self.ai.embed_text(
                chunk,
                task_type="RETRIEVAL_DOCUMENT",
            )

            if embedding is None:
                return -1

            embeddings.append(embedding)

        added = 0

        for chunk, embedding in zip(
            chunks,
            embeddings,
        ):
            if self.db.add_reference_chunk(
                title,
                madhab_tag,
                chunk,
                embedding,
            ):
                added += 1

        return added

    def retrieve_relevant_chunks(
        self,
        query: str,
        madhabs: Optional[List[str]] = None,
        top_k: int = 6,
        min_similarity: float = 0.45,
    ) -> List[Dict[str, Any]]:
        if not self.ai.available:
            return []

        if self.db.count_reference_chunks() == 0:
            return []

        query_embedding = self.ai.embed_text(
            query,
            task_type="RETRIEVAL_QUERY",
        )

        if not query_embedding:
            return []

        query_vector = np.array(
            query_embedding,
            dtype=np.float32,
        )

        allowed = set(madhabs or [])
        allowed.add("")

        scored = []

        for chunk in self.db.get_reference_chunks():
            tag = chunk.get(
                "madhab_tag",
                "",
            ) or ""

            if madhabs and tag not in allowed:
                continue

            try:
                vector = np.array(
                    json.loads(
                        chunk["embedding"]
                    ),
                    dtype=np.float32,
                )

                denominator = (
                    np.linalg.norm(query_vector)
                    * np.linalg.norm(vector)
                )

                similarity = (
                    float(
                        np.dot(
                            query_vector,
                            vector,
                        )
                        / denominator
                    )
                    if denominator
                    else 0.0
                )

                if similarity >= min_similarity:
                    scored.append({
                        "source_title": (
                            chunk["source_title"]
                        ),
                        "madhab_tag": tag,
                        "chunk_text": (
                            chunk["chunk_text"]
                        ),
                        "score": similarity,
                    })

            except Exception:
                logger.exception(
                    "Invalid stored embedding"
                )

        scored.sort(
            key=lambda item: item["score"],
            reverse=True,
        )

        return scored[:top_k]


# ============================================================
# Search service
# ============================================================

class SearchService:
    def __init__(
        self,
        db: DatabaseManager,
        ai: AIService,
        cache_size: int = 200,
    ):
        self.db = db
        self.ai = ai
        self.cache_size = cache_size
        self.cache = OrderedDict()

    def get_cached(self, key: str):
        if key not in self.cache:
            return None

        value = self.cache.pop(key)
        self.cache[key] = value
        return value

    def save_cached(
        self,
        key: str,
        value: Any,
    ):
        if key in self.cache:
            self.cache.pop(key)

        self.cache[key] = value

        while len(self.cache) > self.cache_size:
            self.cache.popitem(
                last=False
            )

    def search(
        self,
        query: str,
        topic_filter: str,
        madhabs: List[str],
        level: str,
    ) -> Tuple[
        List[SearchResult],
        Optional[Dict[str, Any]],
    ]:
        if not query.strip():
            return [], None

        cache_key = "|".join([
            query.strip(),
            topic_filter,
            ",".join(sorted(madhabs)),
            level,
        ])

        cached = self.get_cached(cache_key)

        if cached is not None:
            return cached

        issues = self.db.load_issues(
            topic_filter
        )

        if not issues:
            return [], None

        understanding = None
        candidates = []

        if self.ai.available:
            understanding = (
                self.ai.understand_question(
                    query,
                    issues,
                )
            )

        if understanding:
            candidate_ids = set(
                understanding.get(
                    "matched_issue_ids",
                    [],
                )
            )

            candidates = [
                issue
                for issue in issues
                if issue.id in candidate_ids
            ]

        normalized_query = normalize_arabic(
            query
        )

        synonyms = {
            "جماعة": [
                "جماعه",
                "جماعة",
                "الجماعه",
                "الجماعة",
                "مسجد",
            ],
            "صلاة": [
                "صلاه",
                "صلاة",
                "الصلاه",
                "الصلاة",
            ],
            "وضوء": [
                "وضوء",
                "وضو",
                "طهاره",
                "الطهاره",
            ],
            "صيام": [
                "صيام",
                "صوم",
                "رمضان",
            ],
            "بيع": [
                "بيع",
                "تقسيط",
                "شراء",
                "ثمن",
            ],
        }

        expanded_terms = set(
            normalized_query.split()
        )

        for word in normalized_query.split():
            for values in synonyms.values():
                normalized_values = [
                    normalize_arabic(value)
                    for value in values
                ]

                if word in normalized_values:
                    expanded_terms.update(
                        normalized_values
                    )

        scored_candidates = []

        for issue in issues:
            searchable_text = normalize_arabic(
                " ".join([
                    issue.title,
                    *issue.keywords,
                    issue.rulings.get(
                        "very_short",
                        "",
                    ),
                    issue.rulings.get(
                        "short",
                        "",
                    ),
                    issue.rulings.get(
                        "full",
                        "",
                    ),
                ])
            )

            title_text = normalize_arabic(
                issue.title
            )

            score = 0

            if title_text in normalized_query:
                score += 100

            if normalized_query in searchable_text:
                score += 80

            for term in expanded_terms:
                if term and term in searchable_text:
                    score += 10

            for word in normalized_query.split():
                if len(word) > 2 and word in searchable_text:
                    score += 5

            if score > 0:
                scored_candidates.append(
                    (
                        score,
                        issue,
                    )
                )

        scored_candidates.sort(
            key=lambda item: item[0],
            reverse=True,
        )

        seen_ids = set()

        for _, issue in scored_candidates:
            if issue.id in seen_ids:
                continue

            candidates.append(issue)
            seen_ids.add(issue.id)

        results = []

        for issue in candidates[:5]:
            cards = []

            for madhab in madhabs:
                ruling = issue.rulings_by_madhab.get(
                    madhab
                )

                if not ruling:
                    continue

                cards.append({
                    "code": madhab,
                    "label": MADHHAB_NAMES[madhab]["ar"],
                    "answer": ruling.get(
                        level,
                        ruling.get(
                            "full",
                            "",
                        ),
                    ),
                    "note": (
                        f"رأي المذهب "
                        f"{MADHHAB_NAMES[madhab]['ar']}"
                    ),
                })

            if cards:
                results.append(
                    SearchResult(
                        title=issue.title,
                        topic=issue.topic,
                        cards=cards,
                    )
                )

        final_value = (
            results,
            understanding,
        )

        self.save_cached(
            cache_key,
            final_value,
        )

        return final_value


# ============================================================
# Streamlit UI
# ============================================================

@st.cache_resource
def get_services():
    db = DatabaseManager(DB_PATH)
    ai = AIService()
    search = SearchService(db, ai)
    references = ReferenceManager(db, ai)

    return (
        db,
        ai,
        search,
        references,
    )


def inject_css(lang: str):
    meta = LANGUAGE_META[lang]
    direction = meta["direction"]
    align = meta["align"]

    st.markdown(
        f"""
        <style>
        [data-testid="stAppViewContainer"] {{
            background: #f8fafc;
        }}

        [data-testid="stAppViewContainer"] .main {{
            direction: {direction};
            text-align: {align};
        }}

        [data-testid="stSidebar"] {{
            direction: {direction};
            text-align: {align};
        }}

        [data-testid="stSidebar"] * {{
            text-align: {align};
        }}

        .app-header {{
            direction: {direction};
            display: flex;
            align-items: center;
            justify-content: center;
            text-align: center;
            padding: 1.8rem 1.5rem;
            margin: .5rem 0 1.2rem;
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

        .app-header-content {{
            display: flex;
            flex-direction: column;
            align-items: center;
            justify-content: center;
            width: 100%;
            text-align: center;
        }}

        .brand-mark {{
            width: 4.5rem;
            height: 4.5rem;
            display: flex;
            align-items: center;
            justify-content: center;
            border-radius: 1.2rem;
            background: rgba(255, 255, 255, .18);
            font-size: 2.5rem;
        }}

        .brand-title {{
            margin-top: .8rem;
            font-size: clamp(1.35rem, 3vw, 2.2rem);
            font-weight: 800;
            line-height: 1.35;
            text-align: center;
        }}

        .brand-subtitle {{
            max-width: 850px;
            margin-top: .45rem;
            opacity: .92;
            line-height: 1.8;
            text-align: center;
        }}

        .language-title {{
            direction: ltr;
            text-align: center;
            color: #64748b;
            font-size: .85rem;
            margin-bottom: .35rem;
        }}

        .result-card {{
            direction: {direction};
            text-align: {align};
            padding: 1rem;
            margin: .7rem 0;
            border: 1px solid #e2e8f0;
            border-radius: 1rem;
            background: white;
            box-shadow: 0 4px 12px
                rgba(15, 23, 42, .05);
        }}

        div[data-testid="stExpander"] {{
            direction: {direction};
            text-align: {align};
        }}

        div[data-testid="stExpander"] summary {{
            direction: {direction};
            text-align: {align};
        }}

        textarea,
        input {{
            direction: {direction} !important;
            text-align: {align} !important;
        }}

        [data-baseweb="select"] {{
            direction: {direction};
            text-align: {align};
        }}

        div[data-baseweb="tag"] {{
            margin: 3px !important;
            padding: 4px 8px !important;
            border-radius: 999px !important;
            background: #dbeafe !important;
            color: #1e3a8a !important;
        }}

        .muted {{
            color: #64748b;
            font-size: .88rem;
        }}
        </style>
        """,
        unsafe_allow_html=True,
    )


def render_language_bar() -> str:
    if "lang" not in st.session_state:
        st.session_state.lang = "ar"

    st.markdown(
        '<div class="language-title">'
        "🌐 اللغة / Language / Langue"
        "</div>",
        unsafe_allow_html=True,
    )

    codes = list(
        LANGUAGE_META.keys()
    )

    columns = st.columns(
        len(codes)
    )

    for column, code in zip(
        columns,
        codes,
    ):
        with column:
            meta = LANGUAGE_META[code]

            if st.button(
                f"{meta['flag']} "
                f"{meta['label']}",
                key=f"language_{code}",
                use_container_width=True,
                type=(
                    "primary"
                    if st.session_state.lang == code
                    else "secondary"
                ),
            ):
                st.session_state.lang = code
                st.rerun()

    return st.session_state.lang


def render_header(lang: str):
    meta = LANGUAGE_META[lang]
    text = UI[lang]

    st.markdown(
        f"""
        <div class="app-header"
             dir="{meta['direction']}">
            <div class="app-header-content">
                <div class="brand-mark">📚</div>
                <div class="brand-title">
                    {text["app_title"]}
                </div>
                <div class="brand-subtitle">
                    {text["app_subtitle"]}
                </div>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_madhab_selector(
    lang: str,
    text: Dict[str, str],
) -> List[str]:
    options = [
        "maliki",
        "shafii",
        "hanafi",
        "hanbali",
        "zahiri",
        "jafari",
        "zaidi",
        "ibadi",
    ]

    labels = {
        code: MADHHAB_NAMES[code].get(
            lang,
            MADHHAB_NAMES[code]["ar"],
        )
        for code in options
    }

    if hasattr(st, "pills"):
        selected = st.pills(
            text["choose_one_or_more"],
            options=options,
            selection_mode="multi",
            default=[
                "maliki",
                "shafii",
                "hanafi",
                "hanbali",
            ],
            format_func=lambda code: labels[code],
        )

        return list(selected or [])

    return st.multiselect(
        text["choose_one_or_more"],
        options=options,
        default=[
            "maliki",
            "shafii",
            "hanafi",
            "hanbali",
        ],
        format_func=lambda code: labels[code],
    )


def render_topic_selector(
    lang: str,
    text: Dict[str, str],
) -> str:
    options = [
        "all",
        *TOPICS.keys(),
    ]

    return st.selectbox(
        text["choose_topic"],
        options=options,
        format_func=lambda code: (
            text["all_topics"]
            if code == "all"
            else TOPICS[code].get(
                lang,
                TOPICS[code]["ar"],
            )
        ),
        key="selected_topic",
    )


def render_level_selector(
    text: Dict[str, str],
) -> str:
    labels = {
        "very_short": text["very_short"],
        "short": text["short"],
        "full": text["full"],
    }

    return st.radio(
        text["choose_level"],
        options=list(
            labels.keys()
        ),
        format_func=lambda code: labels[code],
        horizontal=True,
        key="selected_level",
    )


def render_results(
    results: List[SearchResult],
    understanding: Optional[Dict[str, Any]],
    lang: str,
    text: Dict[str, str],
):
    if understanding:
        with st.expander(
            text["normalization"],
            expanded=False,
        ):
            st.write(
                understanding[
                    "normalized_question"
                ]
            )

            st.caption(
                f"{text['confidence']}: "
                f"{understanding['confidence']:.0%}"
            )

    for result in results:
        topic_label = TOPICS.get(
            result.topic,
            TOPICS["other"],
        ).get(
            lang,
            TOPICS["other"]["ar"],
        )

        st.markdown(
            '<div class="result-card">',
            unsafe_allow_html=True,
        )

        st.subheader(result.title)
        st.caption(topic_label)

        columns = st.columns(
            len(result.cards)
        )

        for column, card in zip(
            columns,
            result.cards,
        ):
            with column:
                label = MADHHAB_NAMES.get(
                    card.get("code", ""),
                    {},
                ).get(
                    lang,
                    card.get("label", ""),
                )

                st.markdown(
                    f"### {label or card['label']}"
                )

                st.write(
                    card["answer"]
                )

                st.caption(
                    card["note"]
                )

        st.markdown(
            "</div>",
            unsafe_allow_html=True,
        )


def render_glossary(
    text: Dict[str, str],
):
    with st.expander(
        text["glossary"],
        expanded=False,
    ):
        st.info(
            text["warning_terms"]
        )

        terms = {
            "ar": [
                ("الحلال", "ما أذن الشرع في فعله.", "الأكل من الطعام المباح."),
                ("المباح", "ما خيّر الشارع بين فعله وتركه.", "اختيار لون الثوب."),
                ("الحرام", "ما طلب الشرع تركه طلبًا جازمًا.", "السرقة."),
                ("المكروه", "ما طلب الشرع تركه دون إلزام.", "فعل مكروه لا يبطل العبادة."),
                ("الواجب", "ما طلب الشرع فعله طلبًا جازمًا.", "الصلاة المفروضة."),
                ("الفرض", "ما ثبت بدليل قطعي عند من يفرق بينه وبين الواجب.", "الصلوات الخمس."),
                ("فرض الكفاية", "واجب يسقط عن الباقين بقيام عدد كافٍ به.", "تجهيز الميت."),
                ("المستحب", "ما يثاب فاعله ولا يعاقب تاركه.", "صدقة التطوع."),
                ("المندوب", "ما رغب الشرع في فعله دون إلزام.", "صيام النافلة."),
                ("السنة", "ما نقل عن النبي ﷺ من قول أو فعل أو تقرير.", "بعض هيئات الصلاة."),
                ("السنة المؤكدة", "سنة واظب عليها النبي ﷺ أو حث عليها.", "صلاة الوتر عند من يعدها سنة مؤكدة."),
            ],
            "en": [
                ("Halal", "What Islamic law permits.", "Eating permissible food."),
                ("Permissible", "What is left to personal choice.", "Choosing a clothing color."),
                ("Haram", "What Islamic law definitively prohibits.", "Theft."),
                ("Disliked", "What is discouraged without strict prohibition.", "A disliked act that does not invalidate worship."),
                ("Wajib", "What Islamic law demands decisively.", "The obligatory prayer."),
                ("Fard", "An obligation established by definitive evidence.", "The five daily prayers."),
                ("Communal obligation", "An obligation fulfilled by enough members of the community.", "Preparing the deceased."),
                ("Recommended", "An act whose doer is rewarded and non-doer is not punished.", "Voluntary charity."),
                ("Mandub", "An act encouraged without obligation.", "Voluntary fasting."),
                ("Sunnah", "A statement, action, or approval transmitted from the Prophet.", "Some prayer postures."),
                ("Emphasized Sunnah", "A sunnah consistently practiced or strongly encouraged.", "Witr according to those who classify it as emphasized sunnah."),
            ],
        }

        language = (
            "en"
            if text["app_title"].startswith("The")
            else "ar"
        )

        for label, definition, example in terms[language]:
            with st.expander(
                label,
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


def render_countries(
    text: Dict[str, str],
):
    with st.expander(
        text["countries"],
        expanded=False,
    ):
        st.caption(
            text["country_note"]
        )

        countries = [
            ("Sudan", "Maliki and Shafi'i"),
            ("Morocco", "Maliki"),
            ("Syria", "Hanafi and Shafi'i"),
            ("Iraq", "Hanafi, Shafi'i, and Hanbali"),
            ("United Arab Emirates", "Sunni diversity"),
            ("Oman", "Ibadi"),
            ("Jordan", "Shafi'i and Hanafi"),
            ("Bahrain", "Ja'fari, Maliki, Shafi'i, and Hanbali"),
            ("Kuwait", "Maliki and Hanbali"),
            ("Tunisia", "Maliki"),
            ("Libya", "Maliki"),
            ("Algeria", "Maliki"),
            ("Indonesia", "Shafi'i"),
            ("Malaysia", "Shafi'i"),
            ("Pakistan", "Hanafi"),
            ("Afghanistan", "Hanafi"),
            ("Iran", "Ja'fari"),
            ("Lebanon", "Jafari, Shafi'i, Hanafi, Maliki, and Hanbali"),
            ("Palestine", "Shafi'i and Hanafi"),
            ("Chad", "Maliki and Shafi'i"),
            ("Nigeria", "Maliki"),
            ("Somalia", "Shafi'i"),
            ("Djibouti", "Shafi'i"),
            ("Saudi Arabia", "Hanbali"),
            ("Egypt", "Juristic diversity"),
            ("Yemen", "Shafi'i and Zaidi"),
            ("Turkey", "Hanafi"),
        ]

        for country, madhab in countries:
            st.markdown(
                f"**{country}** — {madhab}"
            )


def render_rules(
    text: Dict[str, str],
):
    with st.expander(
        text["rules"],
        expanded=False,
    ):
        rules = [
            (
                "Actions are judged by intentions",
                "Intentions are considered when determining legal effects.",
                "Giving money differs depending on whether it is charity, a loan, or a gift.",
            ),
            (
                "Certainty is not removed by doubt",
                "An established certainty is not overturned by a mere doubt.",
                "One certain of purity remains pure when merely doubting impurity.",
            ),
            (
                "Hardship brings facilitation",
                "Unusual hardship may justify a legally recognized concession.",
                "Breaking the fast for a sick person harmed by fasting.",
            ),
            (
                "Harm must be removed",
                "Harm should be removed or reduced without causing greater harm.",
                "Preventing use of a road that harms pedestrians.",
            ),
            (
                "Custom is authoritative",
                "Sound custom is considered where no specific legal determination exists.",
                "Determining aspects of maintenance according to local custom.",
            ),
            (
                "Necessities permit prohibited matters",
                "A genuine necessity may permit a prohibited act only as needed.",
                "Consuming a prohibited item to avoid death, only as needed.",
            ),
            (
                "The default rule in transactions is permissibility",
                "New transactions are presumed permissible unless prohibited.",
                "A new sales method is permissible if free from riba and excessive uncertainty.",
            ),
            (
                "The dependent follows the principal",
                "A dependent matter generally follows the ruling of the principal matter.",
                "Usual appurtenances are included in the sale of property.",
            ),
        ]

        is_english = text["app_title"].startswith("The")

        for title, definition, example in rules:
            display_title = title

            if not is_english:
                display_title = {
                    "Actions are judged by intentions": "الأمور بمقاصدها",
                    "Certainty is not removed by doubt": "اليقين لا يزول بالشك",
                    "Hardship brings facilitation": "المشقة تجلب التيسير",
                    "Harm must be removed": "الضرر يزال",
                    "Custom is authoritative": "العادة محكمة",
                    "Necessities permit prohibited matters": "الضرورات تبيح المحظورات",
                    "The default rule in transactions is permissibility": "الأصل في المعاملات الإباحة",
                    "The dependent follows the principal": "التابع تابع",
                }.get(
                    title,
                    title,
                )

            with st.expander(
                display_title,
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


def render_comments(
    text: Dict[str, str],
):
    if "comments" not in st.session_state:
        st.session_state.comments = []

    with st.expander(
        text["comments"],
        expanded=False,
    ):
        rating = st.slider(
            text["rating"],
            min_value=1,
            max_value=5,
            value=4,
            key="answer_rating",
        )

        comment = st.text_area(
            text["comment"],
            key="session_comment",
        )

        if st.button(
            text["send_comment"],
            key="submit_comment",
        ):
            if comment.strip():
                st.session_state.comments.append({
                    "rating": rating,
                    "comment": comment.strip(),
                    "time": utc_now_iso(),
                })

                st.success(
                    text["comment_saved"]
                )
            else:
                st.warning(
                    text["no_question"]
                )

        for item in reversed(
            st.session_state.comments
        ):
            st.markdown(
                f"⭐ {item['rating']}/5 — "
                f"{item['comment']}"
            )


def is_admin(
    text: Dict[str, str],
) -> bool:
    if not ADMIN_PASSWORD:
        st.warning(
            text["admin_missing"]
        )
        return False

    entered = st.text_input(
        text["admin_password"],
        type="password",
        key="admin_password_input",
    )

    return entered == ADMIN_PASSWORD


def render_reference_admin(
    db: DatabaseManager,
    ai: AIService,
    references: ReferenceManager,
    lang: str,
    text: Dict[str, str],
):
    with st.expander(
        text["reference_management"],
        expanded=False,
    ):
        if not is_admin(text):
            st.info(
                text["admin_denied"]
            )
            return

        st.write(
            text["reference_intro"]
        )

        title = st.text_input(
            text["source_title"],
            key="reference_title",
        )

        madhab_options = [
            "",
            *MADHHAB_NAMES.keys(),
        ]

        madhab_tag = st.selectbox(
            text["source_madhab"],
            options=madhab_options,
            format_func=lambda code: (
                text["general_source"]
                if not code
                else MADHHAB_NAMES[code].get(
                    lang,
                    MADHHAB_NAMES[code]["ar"],
                )
            ),
            key="reference_madhab",
        )

        raw_text = st.text_area(
            text["source_text"],
            height=250,
            key="reference_text",
        )

        uploaded = st.file_uploader(
            text["source_file"],
            type=["txt"],
            key="reference_file",
        )

        if uploaded is not None:
            raw_text = uploaded.getvalue().decode(
                "utf-8",
                errors="ignore",
            )

        if st.button(
            text["add_reference"],
            use_container_width=True,
            key="add_reference_button",
        ):
            if not title.strip() or not raw_text.strip():
                st.warning(
                    text["reference_empty"]
                )
                return

            if not ai.available:
                st.error(
                    text["reference_failed"]
                )
                return

            with st.spinner(
                text["ai_generating"]
            ):
                added = references.add_document(
                    title,
                    madhab_tag,
                    raw_text,
                )

            if added >= 0:
                st.success(
                    text["reference_success"].format(
                        added,
                        title,
                    )
                )
            else:
                st.error(
                    text["reference_failed"]
                )

        st.markdown(
            f"### {text['indexed_sources']}"
        )

        sources = db.list_reference_sources()

        if not sources:
            st.info(
                text["no_sources"]
            )
        else:
            for source, count in sources:
                st.write(
                    f"📖 {source}: {count}"
                )


def render_search(
    db: DatabaseManager,
    ai: AIService,
    search: SearchService,
    references: ReferenceManager,
    madhabs: List[str],
    topic: str,
    level: str,
    lang: str,
    text: Dict[str, str],
):
    with st.form("search_form"):
        question = st.text_area(
            text["question_placeholder"],
            height=130,
            key="question_input",
        )

        submitted = st.form_submit_button(
            text["search"],
            use_container_width=True,
        )

    if not submitted:
        return

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

    with st.spinner(
        text["ai_generating"]
    ):
        results, understanding = search.search(
            query=question,
            topic_filter=topic,
            madhabs=madhabs,
            level=level,
        )

    if results:
        render_results(
            results,
            understanding,
            lang,
            text,
        )
        return

    chunks = []

    if db.count_reference_chunks() > 0:
        chunks = references.retrieve_relevant_chunks(
            query=question,
            madhabs=madhabs,
        )

    if chunks and ai.available:
        st.warning(
            text["ai_disclaimer"]
        )

        source_names = sorted({
            chunk["source_title"]
            for chunk in chunks
        })

        answers = ai.answer_from_references(
            question=question,
            madhabs=madhabs,
            level=level,
            chunks=chunks,
        )

        if answers:
            for code, answer in answers.items():
                st.markdown(
                    '<div class="result-card">',
                    unsafe_allow_html=True,
                )

                label = MADHHAB_NAMES[code].get(
                    lang,
                    MADHHAB_NAMES[code]["ar"],
                )

                st.subheader(label)
                st.write(answer)

                st.caption(
                    text["rag_badge"].format(
                        ", ".join(source_names)
                    )
                )

                st.markdown(
                    "</div>",
                    unsafe_allow_html=True,
                )

            return

    if ai.available:
        with st.spinner(
            text["ai_generating"]
        ):
            fallback_answers = (
                ai.generate_fallback_answer(
                    question=question,
                    madhabs=madhabs,
                    level=level,
                )
            )

        if fallback_answers:
            st.warning(
                text["ai_disclaimer"]
            )

            for code, answer in fallback_answers.items():
                st.markdown(
                    '<div class="result-card">',
                    unsafe_allow_html=True,
                )

                label = MADHHAB_NAMES[code].get(
                    lang,
                    MADHHAB_NAMES[code]["ar"],
                )

                st.subheader(label)
                st.write(answer)
                st.caption(
                    text["ai_badge"]
                )

                st.markdown(
                    "</div>",
                    unsafe_allow_html=True,
                )

            return

    st.warning(
        text["no_results"]
    )


# ============================================================
# Main
# ============================================================

def main():
    lang = render_language_bar()

    inject_css(lang)

    text = UI[lang]

    render_header(lang)

    db, ai, search, references = get_services()

    with st.sidebar:
        st.header(
            text["choose_madhab"]
        )

        madhabs = render_madhab_selector(
            lang,
            text,
        )

        st.divider()

        topic = render_topic_selector(
            lang,
            text,
        )

        st.divider()

        level = render_level_selector(
            text,
        )

        st.divider()

        if ai.available:
            st.success(
                text["ai_on"]
            )
        else:
            st.warning(
                text["ai_off"]
            )

    st.markdown(
        f"## {text['write_question']}"
    )

    render_search(
        db=db,
        ai=ai,
        search=search,
        references=references,
        madhabs=madhabs,
        topic=topic,
        level=level,
        lang=lang,
        text=text,
    )

    render_glossary(text)
    render_countries(text)
    render_rules(text)
    render_comments(text)

    render_reference_admin(
        db=db,
        ai=ai,
        references=references,
        lang=lang,
        text=text,
    )


if __name__ == "__main__":
    main()
