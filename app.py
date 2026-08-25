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

try:
    import numpy as np
    NUMPY_AVAILABLE = True
except ImportError:
    np = None
    NUMPY_AVAILABLE = False

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
# المسارات والإعدادات
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

logging.basicConfig(
    level=logging.INFO
)

logger = logging.getLogger(__name__)


# ============================================================
# الاتصال بخدمة Gemini اختياري
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

    return os.getenv(
        name,
        default,
    )


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


# ============================================================
# نصوص الواجهة
# ============================================================

def build_ui() -> Dict[str, Dict[str, str]]:
    base = {
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
        "combined_sources": (
            "📜 مصادر التشريع وأصول الاستدلال الفقهي"
        ),
        "rules": "⚖️ القواعد الفقهية",
        "references": "📁 إدارة المراجع",
        "definition": "التعريف",
        "example": "مثال",
        "note": "ملاحظة",
        "population_note": (
            "أعداد المسلمين تقريبية، والمذهب المذكور "
            "هو السائد أو الأبرز."
        ),
        "admin_password": "كلمة مرور المشرف",
        "access_denied": "لا تملك الصلاحية.",
        "source_title": "عنوان المصدر",
        "source_text": "نص المرجع",
        "madhab": "المذهب",
        "add_reference": "إضافة المرجع",
        "reference_added": "تمت إضافة {} مقاطع.",
        "legal_sources": "مصادر التشريع",
        "usul": "أصول الاستدلال",
    }

    ui = {
        "ar": dict(base),
        "en": dict(base),
        "fr": dict(base),
        "fa": dict(base),
        "ms": dict(base),
        "ur": dict(base),
    }

    ui["en"].update({
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
        "combined_sources": (
            "📜 Legal sources and principles of reasoning"
        ),
        "rules": "⚖️ Fiqh principles",
        "references": "📁 Reference management",
        "definition": "Definition",
        "example": "Example",
        "note": "Note",
        "population_note": (
            "Muslim population figures are approximate."
        ),
        "admin_password": "Admin password",
        "access_denied": "Access denied.",
        "source_title": "Source title",
        "source_text": "Reference text",
        "madhab": "Madhhab",
        "add_reference": "Add reference",
        "reference_added": "{} chunks were added.",
        "legal_sources": "Legal sources",
        "usul": "Principles of legal reasoning",
    })

    ui["fr"].update({
        "title": "Recueil concis des avis des écoles juridiques",
        "subtitle": "Plateforme éducative de comparaison du fiqh.",
        "madhab_filter": "Filtre des écoles",
        "sunni": "Écoles sunnites",
        "shia": "Écoles chiites",
        "ibadi": "École ibadite",
        "select_sunni": "Choisir les écoles sunnites",
        "select_shia": "Choisir les écoles chiites",
        "select_ibadi": "Choisir l’école ibadite",
        "topic": "Choisir le sujet",
        "all_topics": "Tous les sujets",
        "answer_type": "Type de réponse",
        "brief": "Bref",
        "detailed": "Détaillé",
        "questions": "❓ Questions et réponses",
        "placeholder": "Exemple : Quel est le statut de la Omra ?",
        "search": "🔍 Rechercher",
        "loading": "Recherche et analyse en cours...",
        "no_question": "Veuillez écrire une question.",
        "no_madhab": "Veuillez choisir une école.",
        "no_result": "Aucune réponse utilisable.",
        "ai_on": "Gemini AI : activé",
        "ai_off": "Gemini AI : désactivé",
        "ai_note": "Ceci est une réponse de recherche, pas une fatwa.",
        "countries": "🗺️ États membres de l’OCI",
        "scholars": "📜 Imams et savants",
        "glossary": "📚 Terminologie du fiqh",
        "combined_sources": (
            "📜 Sources et principes du raisonnement juridique"
        ),
        "rules": "⚖️ Principes du fiqh",
        "references": "📁 Gestion des références",
        "definition": "Définition",
        "example": "Exemple",
        "note": "Note",
        "population_note": (
            "Les populations musulmanes sont approximatives."
        ),
        "admin_password": "Mot de passe admin",
        "access_denied": "Accès refusé.",
        "source_title": "Titre de la source",
        "source_text": "Texte de référence",
        "madhab": "École juridique",
        "add_reference": "Ajouter la référence",
        "reference_added": "{} segments ajoutés.",
        "legal_sources": "Sources juridiques",
        "usul": "Principes du raisonnement",
    })

    ui["fa"].update({
        "title": "مجموعه مختصر دیدگاه‌های مذاهب فقهی",
        "subtitle": "سامانه‌ای آموزشی برای مقایسه دیدگاه‌های فقهی.",
        "madhab_filter": "فیلتر مذاهب",
        "sunni": "مذاهب اهل سنت",
        "shia": "مذاهب شیعه",
        "ibadi": "مذهب اباضی",
        "select_sunni": "مذاهب اهل سنت را انتخاب کنید",
        "select_shia": "مذاهب شیعه را انتخاب کنید",
        "select_ibadi": "مذهب اباضی را انتخاب کنید",
        "topic": "موضوع را انتخاب کنید",
        "all_topics": "همه موضوعات",
        "answer_type": "نوع پاسخ",
        "brief": "کوتاه",
        "detailed": "کامل",
        "questions": "❓ پرسش‌ها و پاسخ‌ها",
        "placeholder": "مثال: حکم عمره چیست؟",
        "search": "🔍 جست‌وجو",
        "loading": "در حال جست‌وجو و تحلیل...",
        "no_question": "لطفاً پرسش را وارد کنید.",
        "no_madhab": "لطفاً یک مذهب را انتخاب کنید.",
        "no_result": "پاسخ قابل استفاده‌ای پیدا نشد.",
        "ai_on": "Gemini AI: فعال",
        "ai_off": "Gemini AI: غیرفعال",
        "ai_note": "این پاسخ پژوهشی است، نه فتوا.",
        "countries": "🗺️ کشورهای عضو سازمان همکاری اسلامی",
        "scholars": "📜 امامان و دانشمندان",
        "glossary": "📚 اصطلاحات فقهی",
        "combined_sources": "📜 منابع و اصول استنباط فقهی",
        "rules": "⚖️ اصول و قواعد فقهی",
        "references": "📁 مدیریت منابع",
        "definition": "تعریف",
        "example": "مثال",
        "note": "یادداشت",
        "legal_sources": "منابع تشریع",
        "usul": "اصول استنباط",
    })

    ui["ms"].update({
        "title": "Himpunan Ringkas Pandangan Mazhab",
        "subtitle": "Platform pendidikan perbandingan fiqh.",
        "madhab_filter": "Tapis mazhab",
        "sunni": "Mazhab Sunni",
        "shia": "Mazhab Syiah",
        "ibadi": "Mazhab Ibadi",
        "select_sunni": "Pilih mazhab Sunni",
        "select_shia": "Pilih mazhab Syiah",
        "select_ibadi": "Pilih mazhab Ibadi",
        "topic": "Pilih topik",
        "all_topics": "Semua topik",
        "answer_type": "Jenis jawapan",
        "brief": "Ringkas",
        "detailed": "Terperinci",
        "questions": "❓ Soalan dan jawapan",
        "placeholder": "Contoh: Apakah hukum Umrah?",
        "search": "🔍 Cari",
        "loading": "Mencari dan menganalisis...",
        "no_question": "Sila masukkan soalan.",
        "no_madhab": "Sila pilih sekurang-kurangnya satu mazhab.",
        "no_result": "Tiada jawapan yang sesuai.",
        "ai_on": "Gemini AI: diaktifkan",
        "ai_off": "Gemini AI: dinyahaktifkan",
        "ai_note": "Ini jawapan penyelidikan, bukan fatwa.",
        "countries": "🗺️ Negara anggota OIC",
        "scholars": "📜 Imam dan ulama",
        "glossary": "📚 Istilah fiqh",
        "combined_sources": "📜 Sumber dan prinsip fiqh",
        "rules": "⚖️ Prinsip fiqh",
        "references": "📁 Pengurusan rujukan",
        "definition": "Takrif",
        "example": "Contoh",
        "note": "Nota",
        "legal_sources": "Sumber hukum",
        "usul": "Prinsip istinbat",
    })

    ui["ur"].update({
        "title": "مذاہب فقہ کے مختصر آراء کا مجموعہ",
        "subtitle": "فقہی آراء کے تقابلی مطالعے کا تعلیمی پلیٹ فارم۔",
        "madhab_filter": "مسلک کا انتخاب",
        "sunni": "اہل سنت کے مسالک",
        "shia": "شیعہ مسالک",
        "ibadi": "اباضی مسلک",
        "select_sunni": "اہل سنت کے مسالک منتخب کریں",
        "select_shia": "شیعہ مسالک منتخب کریں",
        "select_ibadi": "اباضی مسلک منتخب کریں",
        "topic": "موضوع منتخب کریں",
        "all_topics": "تمام موضوعات",
        "answer_type": "جواب کی نوعیت",
        "brief": "مختصر",
        "detailed": "تفصیلی",
        "questions": "❓ سوالات و جوابات",
        "placeholder": "مثال: عمرہ کا کیا حکم ہے؟",
        "search": "🔍 تلاش",
        "loading": "تلاش اور تجزیہ جاری ہے...",
        "no_question": "براہ کرم سوال درج کریں۔",
        "no_madhab": "براہ کرم کم از کم ایک مسلک منتخب کریں۔",
        "no_result": "قابل استعمال جواب نہیں ملا۔",
        "ai_on": "Gemini AI: فعال",
        "ai_off": "Gemini AI: غیر فعال",
        "ai_note": "یہ تحقیقی جواب ہے، فتویٰ نہیں۔",
        "countries": "🗺️ اسلامی تعاون تنظیم کے رکن ممالک",
        "scholars": "📜 ائمہ اور علماء",
        "glossary": "📚 فقہی اصطلاحات",
        "combined_sources": "📜 فقہی مصادر اور اصولِ استدلال",
        "rules": "⚖️ فقہی اصول و قواعد",
        "references": "📁 مراجع کا انتظام",
        "definition": "تعریف",
        "example": "مثال",
        "note": "نوٹ",
        "legal_sources": "مصادرِ تشریع",
        "usul": "اصولِ استدلال",
    })

    return ui


UI = build_ui()


# ============================================================
# المذاهب
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
# تحميل ملفات JSON
# ============================================================

def load_json(
    filename: str,
    default: Any,
) -> Any:
    path = DATA_DIR / filename

    if not path.exists():
        logger.warning(
            "Missing data file: %s",
            path,
        )
        return default

    try:
        with path.open(
            "r",
            encoding="utf-8",
        ) as file:
            return json.load(file)
    except Exception:
        logger.exception(
            "Invalid JSON file: %s",
            path,
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
# بيانات افتراضية للأصول والمصادر
# ============================================================

if not LEGAL_SOURCES:
    LEGAL_SOURCES = [
        {
            "name": {
                "ar": "القرآن الكريم",
                "en": "The Qur'an",
                "fr": "Le Coran",
            },
            "description": {
                "ar": "المصدر الأعلى والأول للتشريع الإسلامي.",
                "en": "The primary and highest source of Islamic law.",
                "fr": "La première et la plus haute source du droit islamique.",
            },
        },
        {
            "name": {
                "ar": "السنة النبوية",
                "en": "Prophetic Sunnah",
                "fr": "La Sunna prophétique",
            },
            "description": {
                "ar": "أقوال النبي ﷺ وأفعاله وتقريراته.",
                "en": "The sayings, actions, and approvals of the Prophet.",
                "fr": "Les paroles, actes et approbations du Prophète.",
            },
        },
        {
            "name": {
                "ar": "الإجماع",
                "en": "Ijma'",
                "fr": "Ijma'",
            },
            "description": {
                "ar": "اتفاق المجتهدين من أمة محمد ﷺ في عصر من العصور على حكم شرعي.",
                "en": "The agreement of qualified jurists on a legal ruling.",
                "fr": "L’accord des juristes qualifiés sur une règle juridique.",
            },
        },
        {
            "name": {
                "ar": "القياس",
                "en": "Qiyas",
                "fr": "Qiyas",
            },
            "description": {
                "ar": "إلحاق مسألة جديدة بمسألة منصوص عليها لاشتراكهما في العلة.",
                "en": "Applying an established ruling to a new case due to a shared effective cause.",
                "fr": "L’application d’une règle connue à un cas nouveau par une cause commune.",
            },
        },
    ]


if not USUL:
    USUL = [
        {
            "name": {
                "ar": "الأمر والنهي",
                "en": "Commands and prohibitions",
                "fr": "Commandements et interdictions",
            },
            "definition": {
                "ar": "بحث دلالات صيغ الأمر والنهي وآثارها في الحكم الشرعي.",
                "en": "Analysis of commands and prohibitions and their legal effects.",
                "fr": "Analyse des commandements et interdictions et de leurs effets juridiques.",
            },
            "note": {
                "ar": "تختلف بعض تطبيقاته بحسب القرائن والسياق.",
                "en": "Applications may vary according to context and indications.",
                "fr": "Les applications peuvent varier selon le contexte.",
            },
        },
        {
            "name": {
                "ar": "العام والخاص",
                "en": "General and specific texts",
                "fr": "Textes généraux et spécifiques",
            },
            "definition": {
                "ar": "دراسة النصوص العامة وما يرد عليها من تخصيص.",
                "en": "Study of general texts and possible specification.",
                "fr": "Étude des textes généraux et de leur éventuelle spécification.",
            },
            "note": {
                "ar": "يبحث الأصولي في دلالة اللفظ وحدود شموله.",
                "en": "The jurist examines the scope and meaning of the wording.",
                "fr": "Le juriste examine la portée et le sens de la formulation.",
            },
        },
        {
            "name": {
                "ar": "المطلق والمقيد",
                "en": "Unrestricted and restricted texts",
                "fr": "Textes absolus et restreints",
            },
            "definition": {
                "ar": "الموازنة بين النص المطلق والنص الذي قيده وصف أو شرط.",
                "en": "Reconciling unrestricted texts with texts limited by a condition or description.",
                "fr": "La conciliation entre les textes absolus et ceux limités par une condition.",
            },
            "note": {
                "ar": "يُنظر في اتحاد الحكم والسبب والسياق.",
                "en": "The legal ruling, cause, and context are considered.",
                "fr": "La règle, la cause et le contexte sont pris en compte.",
            },
        },
        {
            "name": {
                "ar": "المصلحة والاستصحاب",
                "en": "Maslahah and presumption of continuity",
                "fr": "Maslaha et présomption de continuité",
            },
            "definition": {
                "ar": "منهج للنظر في المصلحة المعتبرة واستمرار الحكم السابق عند غياب الناقل.",
                "en": "Considering recognized benefit and continuity of an earlier state when no contrary evidence exists.",
                "fr": "Prise en compte de l’intérêt reconnu et de la continuité d’un état antérieur.",
            },
            "note": {
                "ar": "تختلف حدود الاعتماد عليهما بين المدارس الفقهية.",
                "en": "Schools differ in the extent to which they rely on these principles.",
                "fr": "Les écoles divergent quant à leur utilisation.",
            },
        },
    ]


# ============================================================
# موضوعات افتراضية للبحث المحلي
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
                "fr": "Considérée généralement comme une obligation collective.",
            },
            "shafii": {
                "ar": "فرض كفاية في الجملة.",
                "en": "Generally treated as a communal obligation.",
                "fr": "Considérée généralement comme une obligation collective.",
            },
            "hanafi": {
                "ar": "واجبة على القادر بلا عذر.",
                "en": "Obligatory for an able person without a valid excuse.",
                "fr": "Obligatoire pour celui qui en est capable sans excuse valable.",
            },
            "hanbali": {
                "ar": "فرض عين على القادر.",
                "en": "An individual obligation for an able person.",
                "fr": "Une obligation individuelle pour celui qui en est capable.",
            },
            "zahiri": {
                "ar": "يميل إلى الوجوب بظاهر النصوص.",
                "en": "Tends toward obligation based on the apparent texts.",
                "fr": "Tend vers l’obligation selon le sens apparent des textes.",
            },
            "jafari": {
                "ar": "مستحب مؤكد.",
                "en": "Strongly recommended.",
                "fr": "Fortement recommandée.",
            },
            "zaidi": {
                "ar": "فرض كفاية.",
                "en": "A communal obligation.",
                "fr": "Une obligation collective.",
            },
            "ibadi": {
                "ar": "سنة مؤكدة.",
                "en": "An emphasized Sunnah.",
                "fr": "Une Sunna fortement recommandée.",
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
            "عمرة العمرة عمره umrah umra omrah "
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
            "صيام صوم رمضان فطر fasting ramadan"
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
# أدوات عامة
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
    value: str,
) -> str:
    replacements = {
        "أ": "ا",
        "إ": "ا",
        "آ": "ا",
        "ى": "ي",
        "ة": "ه",
    }

    value = value.lower()

    for old, new in replacements.items():
        value = value.replace(
            old,
            new,
        )

    value = re.sub(
        r"[\u064B-\u065F\u0670]",
        "",
        value,
    )

    value = re.sub(
        r"[^\w\s]",
        " ",
        value,
    )

    return re.sub(
        r"\s+",
        " ",
        value,
    ).strip()


def now_iso() -> str:
    return dt.datetime.now(
        dt.timezone.utc
    ).isoformat()


def get_madhab_name(
    code: str,
    lang: str,
) -> str:
    canonical = CANONICAL_MADHABS.get(
        code
    )

    if canonical:
        return canonical["names"].get(
            lang,
            canonical["names"]["ar"],
        )

    data = MadhhabFile.get(
        code,
        {},
    )

    return text_for(
        data.get(
            "name",
            code,
        ),
        lang,
        code,
    )


def get_madhab_data(
    code: str,
) -> Dict[str, Any]:
    data = MadhhabFile.get(
        code,
        {},
    )

    if isinstance(data, dict):
        return data

    return {}


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
        code,
    )


def issue_title(
    issue: Dict[str, Any],
    lang: str,
) -> str:
    return text_for(
        issue.get(
            "title",
            "",
        ),
        lang,
    )


def issue_ruling(
    issue: Dict[str, Any],
    madhab: str,
    lang: str,
) -> str:
    rulings = issue.get(
        "rulings",
        {},
    )

    value = rulings.get(
        madhab,
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
        str(
            issue.get(
                "keywords",
                "",
            )
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
            values.append(
                str(value)
            )

    return normalize_text(
        " ".join(values)
    )


# ============================================================
# قاعدة البيانات
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
            rows = db.execute(
                """
                SELECT *
                FROM reference_chunks
                ORDER BY id
                """
            ).fetchall()

        return [
            dict(row)
            for row in rows
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
                    INSERT INTO reference_chunks
                    (
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
                        json.dumps(
                            embedding
                        ),
                        content_hash,
                        now_iso(),
                    ),
                )

                db.commit()
                return True

            except sqlite3.IntegrityError:
                return False


# ============================================================
# خدمة Gemini
# ============================================================

class GeminiService:
    def __init__(self):
        self.enabled = bool(
            USE_GEMINI
            and gemini_client
        )

    def generate(
        self,
        prompt: str,
    ) -> Optional[str]:
        if not self.enabled:
            return None

        try:
            response = gemini_client.models.generate_content(
                model=GEMINI_MODEL,
                contents=prompt,
                config=types.GenerateContentConfig(
                    temperature=0.2,
                ),
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
        task_type: str,
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

    def answer(
        self,
        question: str,
        madhabs: List[str],
        level: str,
        lang: str,
        context: str,
    ) -> Optional[str]:
        selected = ", ".join(
            get_madhab_name(
                code,
                lang,
            )
            for code in madhabs
        )

        style = (
            "brief"
            if level == "brief"
            else "detailed"
        )

        prompt = f"""
You are an educational Islamic fiqh research assistant.
You are not issuing a personal fatwa.

Question:
{question}

Selected schools:
{selected}

Answer style:
{style}

Reference context:
{context}

Instructions:
- Answer the exact question.
- Discuss only the selected schools.
- Do not add unselected schools.
- Explain meaningful differences.
- Do not invent references.
- Clearly state that specialist review may be needed.
- Answer in the selected language.
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
    ) -> List[Dict[str, Any]]:
        if not NUMPY_AVAILABLE:
            return []

        if self.db.count_chunks() == 0:
            return []

        vector = self.ai.embed(
            query,
            "RETRIEVAL_QUERY",
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
                    json.loads(
                        item["embedding"]
                    ),
                    dtype=np.float32,
                )

                denominator = (
                    np.linalg.norm(query_vector)
                    * np.linalg.norm(item_vector)
                )

                if not denominator:
                    score = 0.0
                else:
                    score = float(
                        np.dot(
                            query_vector,
                            item_vector,
                        )
                        / denominator
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
            key=lambda item: item[0],
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
    ) -> List[Dict[str, Any]]:
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

            content = issue_search_text(
                issue,
                lang,
            )

            score = sum(
                1
                for word in query.split()
                if len(word) > 2
                and word in content
            )

            if score:
                matches.append(
                    (
                        score,
                        issue,
                    )
                )

        matches.sort(
            key=lambda item: item[0],
            reverse=True,
        )

        results = []

        for _, issue in matches[:5]:
            cards = []

            for madhab in madhabs:
                answer = issue_ruling(
                    issue,
                    madhab,
                    lang,
                )

                if not answer:
                    fallback_texts = {
                        "ar": "تحتاج هذه المسألة إلى بحث تفصيلي في مصادر المذهب.",
                        "en": "This issue requires detailed research in the school's sources.",
                        "fr": "Cette question nécessite une recherche détaillée dans les sources de l'école.",
                        "fa": "این مسئله نیاز به بررسی تفصیلی در منابع مذهب دارد.",
                        "ms": "Isu ini memerlukan penyelidikan terperinci dalam sumber mazhab.",
                        "ur": "اس مسئلے کے لیے مذہب کے مصادر میں تفصیلی تحقیق درکار ہے۔",
                    }
                    answer = fallback_texts.get(lang, fallback_texts["en"])

                cards.append({
                    "madhab": madhab,
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
# التصميم
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

        .answer-card {{
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
# شريط اللغات
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
                key=f"lang_{code}",
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
# تصفية المذاهب
# ============================================================

def render_madhab_filter(
    lang: str,
    text: Dict[str, str],
) -> List[str]:
    old_selection = st.session_state.get(
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
        st.markdown(f"**{text['sunni']}**")
        options = GROUP_CODES["sunni"]

        defaults = [
            code
            for code in old_selection
            if code in options
        ]

        sunni = st.multiselect(
            text["select_sunni"],
            options=options,
            default=defaults,
            format_func=lambda code: (
                get_madhab_name(
                    code,
                    lang,
                )
            ),
            key="sunni_selector",
        )

        st.divider()
        st.markdown(f"**{text['shia']}**")
        options = GROUP_CODES["shia"]

        defaults = [
            code
            for code in old_selection
            if code in options
        ]

        shia = st.multiselect(
            text["select_shia"],
            options=options,
            default=defaults,
            format_func=lambda code: (
                get_madhab_name(
                    code,
                    lang,
                )
            ),
            key="shia_selector",
        )

        st.divider()
        st.markdown(f"**{text['ibadi']}**")
        options = GROUP_CODES["ibadi"]

        defaults = [
            code
            for code in old_selection
            if code in options
        ]

        ibadi = st.multiselect(
            text["select_ibadi"],
            options=options,
            default=defaults,
            format_func=lambda code: (
                get_madhab_name(
                    code,
                    lang,
                )
            ),
            key="ibadi_selector",
        )

    selected = list(
        dict.fromkeys(
            sunni + shia + ibadi
        )
    )

    st.session_state.selected_madhabs = selected

    return selected


# ============================================================
# قسم الأسئلة
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

        if not st.button(
            text["search"],
            key="search_button",
            use_container_width=True,
        ):
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

        local_results = local_search.search(
            question,
            topic,
            madhabs,
            lang,
        )

        if local_results:
            for result in local_results:
                st.markdown(
                    '<div class="answer-card">',
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
                        st.markdown(
                            f"### {get_madhab_name(
                                card['madhab'],
                                lang,
                            )}"
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
        if not COUNTRIES:
            st.info(
                "ملف countries.json غير موجود أو فارغ."
                if lang == "ar"
                else
                "countries.json is missing or empty."
            )
            return

        st.caption(
            text["population_note"]
        )

        for item in COUNTRIES:
            name = text_for(
                item.get(
                    "name",
                    "",
                ),
                lang,
            )

            flag = item.get(
                "flag",
                "🌍",
            )

            muslims = text_for(
                item.get(
                    "muslims",
                    "",
                ),
                lang,
            )

            madhab = text_for(
                item.get(
                    "madhab",
                    "",
                ),
                lang,
            )

            if item.get(
                "diverse",
                False,
            ):
                suffix = {
                    "ar": "(مع تنوع مذهبي)",
                    "en": "(with religious diversity)",
                    "fr": "(avec diversité religieuse)",
                    "fa": "(با تنوع مذهبی)",
                    "ms": "(dengan kepelbagaian mazhab)",
                    "ur": "(مذہبی تنوع کے ساتھ)",
                }.get(
                    lang,
                    "(with religious diversity)",
                )

                madhab = (
                    f"{madhab} {suffix}"
                )

            details = " — ".join(
                value
                for value in [
                    muslims,
                    madhab,
                ]
                if value
            )

            st.markdown(
                f"{flag} **{name}**"
                + (
                    f" — {details}"
                    if details
                    else ""
                )
            )


# ============================================================
# الأئمة والعلماء
# ============================================================

def render_scholars(
    lang: str,
    text: Dict[str, str],
):
    field_labels = {
        "founder": {
            "ar": "الإمام المؤسس", "en": "Founding imam", "fr": "Imam fondateur",
            "fa": "امام مؤسس", "ms": "Imam pengasas", "ur": "بانی امام",
        },
        "life": {
            "ar": "فترة الحياة", "en": "Lifespan", "fr": "Période de vie",
            "fa": "دوره زندگی", "ms": "Tempoh hidup", "ur": "دورِ حیات",
        },
        "birthplace": {
            "ar": "مكان الميلاد", "en": "Birthplace", "fr": "Lieu de naissance",
            "fa": "محل تولد", "ms": "Tempat lahir", "ur": "جائے پیدائش",
        },
        "origin": {
            "ar": "مكان النشأة والانتشار", "en": "Origin & spread", "fr": "Origine et diffusion",
            "fa": "خاستگاه و گسترش", "ms": "Asal usul & penyebaran", "ur": "ماخذ و پھیلاؤ",
        },
        "scholars": {
            "ar": "أشهر العلماء", "en": "Prominent scholars", "fr": "Savants marquants",
            "fa": "دانشمندان برجسته", "ms": "Ulama terkemuka", "ur": "نمایاں علماء",
        },
        "summary": {
            "ar": "نبذة", "en": "Summary", "fr": "Résumé",
            "fa": "خلاصه", "ms": "Ringkasan", "ur": "خلاصہ",
        },
    }

    with st.expander(
        text["scholars"],
        expanded=False,
    ):
        codes = list(CANONICAL_MADHABS)

        for index, code in enumerate(codes):
            name = get_madhab_name(
                code,
                lang,
            )

            data = get_madhab_data(
                code
            )

            if index > 0:
                st.divider()

            st.markdown(f"#### {name}")

            displayed = False

            for field, labels in field_labels.items():
                value = text_for(
                    data.get(
                        field,
                        "",
                    ),
                    lang,
                )

                if value:
                    displayed = True
                    label = labels.get(lang, labels["en"])

                    st.markdown(
                        f"**{label}:** {value}"
                    )

            if not displayed:
                st.info(
                    (
                        "لا توجد بيانات تفصيلية لهذا "
                        "المذهب في madhabs.json."
                        if lang == "ar"
                        else
                        "No detailed data was found "
                        "for this school in madhabs.json."
                    )
                )


# ============================================================
# المصادر وأصول الاستدلال في قسم واحد
# ============================================================

def render_sources_and_usul(
    lang: str,
    text: Dict[str, str],
):
    with st.expander(
        text["combined_sources"],
        expanded=False,
    ):
        st.markdown(f"### {text['legal_sources']}")

        if not LEGAL_SOURCES:
            st.info(
                "لا توجد مصادر تشريع."
                if lang == "ar"
                else
                "No legal sources were found."
            )
        else:
            for item in LEGAL_SOURCES:
                name = text_for(
                    item.get(
                        "name",
                        "",
                    ),
                    lang,
                )

                description = text_for(
                    item.get(
                        "description",
                        "",
                    ),
                    lang,
                )

                st.markdown(f"**{name}**")
                st.markdown(
                    f"{text['definition']}: "
                    f"{description}"
                )

        st.divider()
        st.markdown(f"### {text['usul']}")

        if not USUL:
            st.info(
                "لا توجد أصول استدلال."
                if lang == "ar"
                else
                "No principles of reasoning were found."
            )
        else:
            for index, item in enumerate(USUL):
                name = text_for(
                    item.get(
                        "name",
                        "",
                    ),
                    lang,
                )

                definition = text_for(
                    item.get(
                        "definition",
                        "",
                    ),
                    lang,
                )

                note = text_for(
                    item.get(
                        "note",
                        "",
                    ),
                    lang,
                )

                if index > 0:
                    st.markdown("---")

                st.markdown(f"**{name}**")
                st.markdown(
                    f"{text['definition']}: "
                    f"{definition}"
                )

                if note:
                    st.markdown(
                        f"{text['note']}: "
                        f"{note}"
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
        if not GLOSSARY:
            st.info(
                "لا توجد مصطلحات في ملف glossary.json."
                if lang == "ar"
                else
                "No glossary entries were found."
            )
            return

        glossary_cols = st.columns(2)

        for index, item in enumerate(GLOSSARY):
            name = text_for(
                item.get(
                    "name",
                    "",
                ),
                lang,
            )

            definition = text_for(
                item.get(
                    "definition",
                    "",
                ),
                lang,
            )

            example = text_for(
                item.get(
                    "example",
                    "",
                ),
                lang,
            )

            with glossary_cols[index % 2]:
                st.markdown(f"**{name}**")
                st.markdown(
                    f"{text['definition']}: "
                    f"{definition}"
                )

                if example:
                    st.markdown(
                        f"{text['example']}: "
                        f"{example}"
                    )

                st.markdown("")


# ============================================================
# القواعد الفقهية
# ============================================================

def render_rules(
    lang: str,
    text: Dict[str, str],
):
    with st.expander(
        text["rules"],
        expanded=False,
    ):
        if not RULES:
            st.info(
                "لا توجد قواعد في ملف rules.json."
                if lang == "ar"
                else
                "No rules were found."
            )
            return

        for index, item in enumerate(RULES):
            name = text_for(
                item.get(
                    "name",
                    "",
                ),
                lang,
            )

            definition = text_for(
                item.get(
                    "definition",
                    "",
                ),
                lang,
            )

            example = text_for(
                item.get(
                    "example",
                    "",
                ),
                lang,
            )

            if index > 0:
                st.markdown("---")

            st.markdown(f"**📌 {name}**")
            st.markdown(
                f"{text['definition']}: "
                f"{definition}"
            )

            if example:
                st.markdown(
                    f"{text['example']}: "
                    f"{example}"
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
            key="admin_password_input",
        )

        if password != ADMIN_PASSWORD:
            st.info(
                text["access_denied"]
            )
            return

        title = st.text_input(
            text["source_title"],
            key="source_title_input",
        )

        madhab_options = [
            "",
            *CANONICAL_MADHABS.keys(),
        ]

        madhab = st.selectbox(
            text["madhab"],
            options=madhab_options,
            format_func=lambda code: (
                "عام"
                if code == ""
                else get_madhab_name(
                    code,
                    lang,
                )
            ),
            key="reference_madhab",
        )

        source = st.text_area(
            text["source_text"],
            height=220,
            key="source_text_input",
        )

        if st.button(
            text["add_reference"],
            key="add_reference_button",
        ):
            if not title.strip():
                st.warning(
                    text["source_title"]
                )
                return

            if not source.strip():
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
                source[index:index + 700]
                for index in range(
                    0,
                    len(source),
                    600,
                )
                if len(
                    source[index:index + 700]
                ) > 30
            ]

            added = 0

            with st.spinner(
                text["loading"]
            ):
                for chunk in chunks:
                    embedding = ai.embed(
                        chunk,
                        "RETRIEVAL_DOCUMENT",
                    )

                    if embedding and db.add_chunk(
                        title,
                        madhab,
                        chunk,
                        embedding,
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
# الدالة الرئيسية
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
            format_func=lambda value: (
                text[value]
            ),
            horizontal=True,
            key="answer_level",
        )

        st.divider()

        if ai.enabled:
            st.success(
                text["ai_on"]
            )
        else:
            st.warning(
                text["ai_off"]
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

    render_sources_and_usul(
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
