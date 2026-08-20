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
# إعداد الصفحة
# ============================================================

st.set_page_config(
    page_title="الجامع المختصر لآراء المذاهب",
    page_icon="📚",
    layout="wide",
    initial_sidebar_state="expanded",
)


# ============================================================
# الإعدادات العامة
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
# اللغات والاتجاهات
# ============================================================

LANGUAGE_META = {
    "ar": {
        "label": "العربية",
        "flag": "🇪🇬",
        "direction": "rtl",
        "text_align": "right",
    },
    "en": {
        "label": "English",
        "flag": "🇬🇧",
        "direction": "ltr",
        "text_align": "left",
    },
    "fr": {
        "label": "Français",
        "flag": "🇫🇷",
        "direction": "ltr",
        "text_align": "left",
    },
    "fa": {
        "label": "فارسی",
        "flag": "🇮🇷",
        "direction": "rtl",
        "text_align": "right",
    },
    "ms": {
        "label": "Melayu",
        "flag": "🇲🇾",
        "direction": "ltr",
        "text_align": "left",
    },
    "ur": {
        "label": "اردو",
        "flag": "🇵🇰",
        "direction": "rtl",
        "text_align": "right",
    },
}


UI = {
    "ar": {
        "app_title": "الجامع المختصر لآراء المذاهب",
        "app_subtitle": (
            "منصة تعليمية لعرض ومقارنة الآراء الفقهية "
            "للفهم والتبصر، وليست موقعًا للإفتاء."
        ),
        "language": "اللغة",
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
        "ai_status_on": "Gemini AI: مفعّل",
        "ai_status_off": (
            "Gemini AI: غير مفعّل — "
            "سيعمل البحث المحلي فقط"
        ),
        "admin_missing": (
            "ADMIN_PASSWORD غير مضبوط في Secrets."
        ),
        "test_gemini": "اختبار اتصال Gemini",
        "test_success": "تم الاتصال بنجاح: {}",
        "test_failed": "تعذر الاتصال بـ Gemini.",
    },
    "en": {
        "app_title": "The Concise Compendium of Madhhab Opinions",
        "app_subtitle": (
            "An educational platform for comparing fiqh opinions. "
            "It is not a fatwa service."
        ),
        "language": "Language",
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
        "ai_generating": (
            "Analyzing the question and searching..."
        ),
        "ai_badge": "🤖 AI-generated research answer",
        "ai_disclaimer": (
            "This is an automated research answer, not a fatwa. "
            "Consult a qualified scholar."
        ),
        "rag_badge": "📖 Based on uploaded references: {}",
        "reference_management": (
            "📁 Reference management — admins"
        ),
        "reference_intro": (
            "Upload reference texts you have rights to use."
        ),
        "source_title": "Source title",
        "source_madhab": "Related school",
        "source_text": "Reference text",
        "source_file": "Or upload a TXT file",
        "add_reference": "Add and index reference",
        "reference_empty": (
            "Enter a title and text or upload a file."
        ),
        "reference_failed": (
            "Indexing failed. Check Gemini settings."
        ),
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
        "ai_status_on": "Gemini AI: enabled",
        "ai_status_off": (
            "Gemini AI: disabled — local search only"
        ),
        "admin_missing": (
            "ADMIN_PASSWORD is not configured in Secrets."
        ),
        "test_gemini": "Test Gemini connection",
        "test_success": "Connection successful: {}",
        "test_failed": "Gemini connection failed.",
    },
    "fr": {
        "app_title": (
            "Recueil concis des avis des écoles juridiques"
        ),
        "app_subtitle": (
            "Plateforme éducative de comparaison du fiqh. "
            "Ce service ne délivre pas de fatwas."
        ),
        "language": "Langue",
        "choose_madhab": "Choisir l’école",
        "choose_one_or_more": (
            "Choisissez une ou plusieurs écoles"
        ),
        "choose_topic": "Choisir le sujet",
        "all_topics": "Tous les sujets",
        "choose_level": "Niveau de détail",
        "very_short": "Très bref",
        "short": "Bref",
        "full": "Détaillé",
        "write_question": "Écrivez votre question",
        "question_placeholder": (
            "Exemple : Quel est le statut de la prière "
            "en congrégation ?"
        ),
        "search": "🔍 Rechercher",
        "no_question": "Veuillez écrire une question.",
        "no_madhab": "Veuillez choisir au moins une école.",
        "no_results": "Aucun résultat approprié.",
        "ai_generating": (
            "Analyse et recherche en cours..."
        ),
        "ai_badge": (
            "🤖 Réponse de recherche générée par IA"
        ),
        "ai_disclaimer": (
            "Ceci est une réponse de recherche, pas une fatwa."
        ),
        "rag_badge": "📖 Basé sur les références: {}",
        "reference_management": (
            "📁 Gestion des références"
        ),
        "reference_intro": (
            "Ajoutez des textes dont vous avez les droits."
        ),
        "source_title": "Titre de la source",
        "source_madhab": "École concernée",
        "source_text": "Texte de référence",
        "source_file": "Ou fichier TXT",
        "add_reference": "Ajouter et indexer",
        "reference_empty": (
            "Ajoutez un titre et un texte."
        ),
        "reference_failed": (
            "Échec de l’indexation."
        ),
        "reference_success": (
            "{} segments ajoutés de «{}»."
        ),
        "indexed_sources": "Sources indexées",
        "no_sources": "Aucune source indexée.",
        "glossary": "📚 Terminologie du fiqh",
        "countries": "🗺️ Pays et écoles dominantes",
        "rules": "📘 Principes et maximes du fiqh",
        "definition": "Définition",
        "example": "Exemple",
        "warning_terms": (
            "La terminologie peut varier selon les écoles."
        ),
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
        "ai_status_on": "Gemini AI : activé",
        "ai_status_off": "Gemini AI : désactivé",
        "admin_missing": (
            "ADMIN_PASSWORD n’est pas configuré."
        ),
        "test_gemini": "Tester Gemini",
        "test_success": "Connexion réussie : {}",
        "test_failed": "La connexion Gemini a échoué.",
    },
}

UI["fa"] = {
    **UI["en"],
    "app_title": "مجموعه مختصر دیدگاه‌های مذاهب فقهی",
    "app_subtitle": (
        "سامانه‌ای آموزشی برای مقایسه دیدگاه‌های فقهی؛ "
        "فتوا صادر نمی‌کند."
    ),
    "language": "زبان",
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
    "ai_disclaimer": (
        "این پاسخ فتوا نیست و باید توسط عالم متخصص بررسی شود."
    ),
    "rag_badge": "📖 مبتنی بر منابع بارگذاری‌شده: {}",
    "reference_management": "📁 مدیریت منابع — مدیران",
    "reference_intro": (
        "متون دارای مجوز استفاده را بارگذاری کنید."
    ),
    "source_title": "عنوان منبع",
    "source_madhab": "مذهب مرتبط",
    "source_text": "متن منبع",
    "source_file": "یا فایل TXT بارگذاری کنید",
    "add_reference": "افزودن و نمایه‌سازی منبع",
    "reference_empty": "عنوان و متن را وارد کنید.",
    "reference_failed": "نمایه‌سازی انجام نشد.",
    "reference_success": "{} بخش از منبع «{}» افزوده شد.",
    "indexed_sources": "منابع نمایه‌شده",
    "no_sources": "هنوز منبعی نمایه نشده است.",
    "glossary": "📚 اصطلاحات فقهی",
    "countries": "🗺️ کشورها و مذاهب رایج",
    "rules": "📘 اصول و قواعد فقهی",
    "definition": "تعریف",
    "example": "مثال",
    "warning_terms": (
        "کاربرد برخی اصطلاحات میان مذاهب متفاوت است."
    ),
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
    "country_note": (
        "این موارد گرایش‌های تاریخی یا غالب هستند."
    ),
    "ai_status_on": "Gemini AI: فعال",
    "ai_status_off": "Gemini AI: غیرفعال",
    "admin_missing": (
        "ADMIN_PASSWORD در Secrets تنظیم نشده است."
    ),
    "test_gemini": "آزمون اتصال Gemini",
    "test_success": "اتصال موفق بود: {}",
    "test_failed": "اتصال به Gemini ناموفق بود.",
}

UI["ms"] = {
    **UI["en"],
    "app_title": "Himpunan Ringkas Pandangan Mazhab",
    "app_subtitle": (
        "Platform pendidikan untuk membandingkan pandangan fiqh; "
        "bukan perkhidmatan fatwa."
    ),
    "language": "Bahasa",
    "choose_madhab": "Pilih mazhab",
    "choose_one_or_more": "Pilih satu atau lebih mazhab",
    "choose_topic": "Pilih topik",
    "all_topics": "Semua topik",
    "choose_level": "Tahap perincian",
    "very_short": "Sangat ringkas",
    "short": "Ringkas",
    "full": "Terperinci",
    "write_question": "Tulis soalan anda",
    "question_placeholder": (
        "Contoh: Apakah hukum solat berjemaah?"
    ),
    "search": "🔍 Cari jawapan",
    "no_question": "Sila tulis soalan dahulu.",
    "no_madhab": "Sila pilih sekurang-kurangnya satu mazhab.",
    "no_results": "Tiada hasil yang sesuai ditemui.",
    "ai_generating": (
        "Menganalisis soalan dan mencari jawapan..."
    ),
    "ai_badge": "🤖 Jawapan penyelidikan dijana AI",
    "ai_disclaimer": (
        "Ini bukan fatwa dan perlu disemak oleh ulama."
    ),
    "rag_badge": "📖 Berdasarkan rujukan yang dimuat naik: {}",
    "reference_management": (
        "📁 Pengurusan rujukan — pentadbir"
    ),
    "reference_intro": (
        "Muat naik teks yang anda mempunyai hak untuk menggunakannya."
    ),
    "source_title": "Tajuk sumber",
    "source_madhab": "Mazhab berkaitan",
    "source_text": "Teks rujukan",
    "source_file": "Atau muat naik fail TXT",
    "add_reference": "Tambah dan indeks rujukan",
    "reference_empty": "Masukkan tajuk dan teks.",
    "reference_failed": "Pengindeksan gagal.",
    "reference_success": (
        "{} bahagian daripada “{}” telah ditambah."
    ),
    "indexed_sources": "Sumber diindeks",
    "no_sources": "Tiada rujukan diindeks.",
    "glossary": "📚 Istilah fiqh",
    "countries": "🗺️ Negara dan mazhab utama",
    "rules": "📘 Prinsip dan kaedah fiqh",
    "definition": "Takrif",
    "example": "Contoh",
    "warning_terms": (
        "Istilah mungkin berbeza antara mazhab."
    ),
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
    "country_note": (
        "Ini ialah corak sejarah atau dominan."
    ),
    "ai_status_on": "Gemini AI: diaktifkan",
    "ai_status_off": "Gemini AI: dinyahaktifkan",
    "admin_missing": (
        "ADMIN_PASSWORD belum ditetapkan."
    ),
    "test_gemini": "Uji sambungan Gemini",
    "test_success": "Sambungan berjaya: {}",
    "test_failed": "Sambungan Gemini gagal.",
}

UI["ur"] = {
    **UI["en"],
    "app_title": "مذاہب فقہ کے مختصر آراء کا مجموعہ",
    "app_subtitle": (
        "فقہی آراء کے تقابلی مطالعے کا تعلیمی پلیٹ فارم؛ "
        "فتویٰ کی خدمت نہیں۔"
    ),
    "language": "زبان",
    "choose_madhab": "مسلک منتخب کریں",
    "choose_one_or_more": (
        "ایک یا زیادہ مسالک منتخب کریں"
    ),
    "choose_topic": "موضوع منتخب کریں",
    "all_topics": "تمام موضوعات",
    "choose_level": "تفصیل کی سطح",
    "very_short": "نہایت مختصر",
    "short": "مختصر",
    "full": "تفصیلی",
    "write_question": "اپنا سوال لکھیں",
    "question_placeholder": (
        "مثال: نماز باجماعت کا کیا حکم ہے؟"
    ),
    "search": "🔍 جواب تلاش کریں",
    "no_question": "براہ کرم پہلے سوال لکھیں۔",
    "no_madhab": (
        "براہ کرم کم از کم ایک مسلک منتخب کریں۔"
    ),
    "no_results": "مناسب نتیجہ نہیں ملا۔",
    "ai_generating": (
        "سوال کا تجزیہ اور تلاش جاری ہے..."
    ),
    "ai_badge": (
        "🤖 مصنوعی ذہانت سے تیار کردہ تحقیقی جواب"
    ),
    "ai_disclaimer": (
        "یہ فتویٰ نہیں ہے؛ مستند عالم سے رجوع کریں۔"
    ),
    "rag_badge": (
        "📖 اپ لوڈ کیے گئے مراجع پر مبنی: {}"
    ),
    "reference_management": (
        "📁 مراجع کا انتظام — منتظمین"
    ),
    "reference_intro": (
        "وہ متون اپ لوڈ کریں جن کے استعمال کا حق آپ کے پاس ہو۔"
    ),
    "source_title": "ماخذ کا عنوان",
    "source_madhab": "متعلقہ مسلک",
    "source_text": "حوالہ جاتی متن",
    "source_file": "یا TXT فائل اپ لوڈ کریں",
    "add_reference": (
        "ماخذ شامل اور فہرست کریں"
    ),
    "reference_empty": (
        "عنوان اور متن درج کریں۔"
    ),
    "reference_failed": (
        "فہرست سازی ناکام ہوئی۔"
    ),
    "reference_success": (
        "{} حصے “{}” سے شامل کیے گئے۔"
    ),
    "indexed_sources": (
        "فہرست شدہ مراجع"
    ),
    "no_sources": (
        "ابھی کوئی مرجع فہرست شدہ نہیں۔"
    ),
    "glossary": "📚 فقہی اصطلاحات",
    "countries": (
        "🗺️ ممالک اور غالب فقہی مسالک"
    ),
    "rules": "📘 فقہی اصول و قواعد",
    "definition": "تعریف",
    "example": "مثال",
    "warning_terms": (
        "بعض اصطلاحات کا استعمال مسالک کے درمیان مختلف ہو سکتا ہے۔"
    ),
    "comments": "💬 نشست کے نوٹس",
    "comment": "اپنا نوٹ لکھیں",
    "rating": "جواب کی درجہ بندی",
    "send_comment": "جمع کریں",
    "comment_saved": (
        "نوٹ محفوظ کر لیا گیا۔"
    ),
    "admin_password": (
        "منتظم کا پاس ورڈ"
    ),
    "admin_denied": (
        "آپ کو اجازت نہیں ہے۔"
    ),
    "normalization": (
        "سوال کی واضح صورت"
    ),
    "confidence": "اعتماد کی سطح",
    "general_source": "عمومی ماخذ",
    "country_note": (
        "یہ تاریخی یا غالب رجحانات ہیں۔"
    ),
    "ai_status_on": "Gemini AI: فعال",
    "ai_status_off": "Gemini AI: غیر فعال",
    "admin_missing": (
        "ADMIN_PASSWORD سیٹ نہیں کیا گیا۔"
    ),
    "test_gemini": "Gemini کنکشن ٹیسٹ",
    "test_success": "کنکشن کامیاب: {}",
    "test_failed": "Gemini کنکشن ناکام۔",
}


# ============================================================
# المذاهب والموضوعات
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
# المصطلحات
# ============================================================

GLOSSARY = {
    "الحلال": {
        "label": {
            "ar": "الحلال",
            "en": "Halal",
            "fr": "Halal",
            "fa": "حلال",
            "ms": "Halal",
            "ur": "حلال",
        },
        "definition": {
            "ar": "ما أذن الشرع في فعله، ولا يترتب على فعله إثم من حيث الأصل.",
            "en": "What Islamic law permits; doing it is not sinful in principle.",
            "fr": "Ce que la loi islamique permet en principe.",
            "fa": "آنچه شرع انجام آن را اجازه داده است.",
            "ms": "Perkara yang dibenarkan syarak.",
            "ur": "جسے شریعت نے جائز قرار دیا ہو۔",
        },
        "example": {
            "ar": "الأكل من الطعام الطيب المباح.",
            "en": "Eating permissible wholesome food.",
            "fr": "Manger une nourriture saine et permise.",
            "fa": "خوردن غذای پاک و مباح.",
            "ms": "Makan makanan yang baik dan halal.",
            "ur": "پاکیزہ اور حلال کھانا کھانا۔",
        },
    },
    "المباح": {
        "label": {
            "ar": "المباح",
            "en": "Permissible",
            "fr": "Permis",
            "fa": "مباح",
            "ms": "Harus",
            "ur": "مباح",
        },
        "definition": {
            "ar": "ما خيّر الشارع المكلّف بين فعله وتركه، فلا مدح ولا ذم لذاته.",
            "en": "An act left to the person's choice.",
            "fr": "Un acte laissé au libre choix de la personne.",
            "fa": "کاری که انجام یا ترک آن به اختیار مکلف گذاشته شده است.",
            "ms": "Perkara yang boleh dilakukan atau ditinggalkan.",
            "ur": "جس کے کرنے یا نہ کرنے میں اختیار ہو۔",
        },
        "example": {
            "ar": "اختيار لون الثوب المباح.",
            "en": "Choosing a permissible clothing color.",
            "fr": "Choisir une couleur de vêtement permise.",
            "fa": "انتخاب رنگ مباح لباس.",
            "ms": "Memilih warna pakaian yang dibenarkan.",
            "ur": "جائز لباس کا رنگ منتخب کرنا۔",
        },
    },
    "الحرام": {
        "label": {
            "ar": "الحرام",
            "en": "Haram",
            "fr": "Interdit",
            "fa": "حرام",
            "ms": "Haram",
            "ur": "حرام",
        },
        "definition": {
            "ar": "ما طلب الشرع تركه طلبًا جازمًا، ويأثم المكلّف بفعله مع العلم والقصد.",
            "en": "What Islamic law definitively prohibits.",
            "fr": "Ce que la loi islamique interdit catégoriquement.",
            "fa": "آنچه شرع به‌طور قطعی از آن نهی کرده است.",
            "ms": "Perkara yang dilarang secara tegas.",
            "ur": "جسے شریعت نے قطعی طور پر منع کیا ہو۔",
        },
        "example": {
            "ar": "السرقة وأكل أموال الناس بالباطل.",
            "en": "Theft and consuming people's wealth unjustly.",
            "fr": "Le vol et l’appropriation injuste des biens.",
            "fa": "دزدی و خوردن مال مردم به ناحق.",
            "ms": "Mencuri dan mengambil harta secara batil.",
            "ur": "چوری اور لوگوں کا مال ناحق کھانا۔",
        },
    },
    "المكروه": {
        "label": {
            "ar": "المكروه",
            "en": "Disliked",
            "fr": "Déconseillé",
            "fa": "مکروه",
            "ms": "Makruh",
            "ur": "مکروہ",
        },
        "definition": {
            "ar": "ما طلب الشرع تركه لا على سبيل الإلزام؛ فتركه أفضل.",
            "en": "What Islamic law discourages without strict prohibition.",
            "fr": "Ce que la loi déconseille sans l’interdire catégoriquement.",
            "fa": "آنچه شرع ترک آن را بدون الزام توصیه کرده است.",
            "ms": "Perkara yang tidak digalakkan tanpa larangan tegas.",
            "ur": "جسے شریعت نے ناپسند کیا مگر قطعی حرام نہ کیا ہو۔",
        },
        "example": {
            "ar": "فعل يكره في العبادة دون أن يبطلها.",
            "en": "An act disliked in worship without invalidating it.",
            "fr": "Un acte déconseillé qui n’annule pas l’adoration.",
            "fa": "کاری مکروه که عبادت را باطل نمی‌کند.",
            "ms": "Perbuatan makruh yang tidak membatalkan ibadah.",
            "ur": "عبادت میں ناپسندیدہ مگر غیر مبطل عمل۔",
        },
    },
    "الواجب": {
        "label": {
            "ar": "الواجب",
            "en": "Wajib",
            "fr": "Obligatoire",
            "fa": "واجب",
            "ms": "Wajib",
            "ur": "واجب",
        },
        "definition": {
            "ar": "ما طلب الشرع فعله طلبًا جازمًا، ويأثم المكلّف بتركه بلا عذر.",
            "en": "What Islamic law demands decisively.",
            "fr": "Ce que la loi exige de manière catégorique.",
            "fa": "آنچه شرع انجام آن را قطعی طلب کرده است.",
            "ms": "Perkara yang diwajibkan secara tegas.",
            "ur": "جسے شریعت نے لازم قرار دیا ہو۔",
        },
        "example": {
            "ar": "أداء الصلاة المفروضة في وقتها.",
            "en": "Performing the obligatory prayer on time.",
            "fr": "Accomplir la prière obligatoire à son heure.",
            "fa": "خواندن نماز واجب در وقت آن.",
            "ms": "Menunaikan solat fardu pada waktunya.",
            "ur": "فرض نماز وقت پر ادا کرنا۔",
        },
    },
    "الفرض": {
        "label": {
            "ar": "الفرض",
            "en": "Fard",
            "fr": "Fard",
            "fa": "فرض",
            "ms": "Fardu",
            "ur": "فرض",
        },
        "definition": {
            "ar": "ما ثبت طلبه بدليل قطعي عند من يفرّق بين الفرض والواجب.",
            "en": "An obligation established by definitive evidence.",
            "fr": "Une obligation établie par une preuve définitive.",
            "fa": "واجبی که با دلیل قطعی ثابت شده باشد.",
            "ms": "Kewajipan yang ditetapkan dengan dalil qat‘i.",
            "ur": "وہ واجب جو قطعی دلیل سے ثابت ہو۔",
        },
        "example": {
            "ar": "وجوب الصلوات الخمس بدليل قطعي.",
            "en": "The obligation of the five daily prayers.",
            "fr": "L’obligation des cinq prières quotidiennes.",
            "fa": "وجوب نمازهای پنج‌گانه.",
            "ms": "Kewajipan solat lima waktu.",
            "ur": "پانچ وقت کی نمازوں کا وجوب۔",
        },
    },
    "فرض الكفاية": {
        "label": {
            "ar": "فرض الكفاية",
            "en": "Communal obligation",
            "fr": "Obligation communautaire",
            "fa": "فرض کفایه",
            "ms": "Fardu kifayah",
            "ur": "فرض کفایہ",
        },
        "definition": {
            "ar": "واجب إذا قام به عدد كافٍ سقط الإثم عن الباقين.",
            "en": "A communal obligation fulfilled when enough people perform it.",
            "fr": "Une obligation communautaire accomplie par un nombre suffisant.",
            "fa": "واجبی که با انجام گروهی کافی از دیگران ساقط می‌شود.",
            "ms": "Kewajipan kolektif yang gugur apabila dilakukan oleh sebahagian yang mencukupi.",
            "ur": "ایسا اجتماعی فرض جسے کافی لوگ ادا کر دیں تو دوسروں سے ساقط ہو جائے۔",
        },
        "example": {
            "ar": "تجهيز الميت والصلاة عليه في الجملة.",
            "en": "Preparing and praying over the deceased.",
            "fr": "La préparation et la prière funéraire du défunt.",
            "fa": "تجهیز و نماز میت.",
            "ms": "Menguruskan jenazah dan solat jenazah.",
            "ur": "میت کو غسل دینا اور نماز جنازہ پڑھنا۔",
        },
    },
    "المستحب": {
        "label": {
            "ar": "المستحب",
            "en": "Recommended",
            "fr": "Recommandé",
            "fa": "مستحب",
            "ms": "Sunat",
            "ur": "مستحب",
        },
        "definition": {
            "ar": "ما طلب الشرع فعله طلبًا غير جازم؛ يثاب فاعله ولا يعاقب تاركه.",
            "en": "A recommended act whose doer is rewarded.",
            "fr": "Un acte recommandé dont l’accomplissement est récompensé.",
            "fa": "کاری که انجام آن مستحب است و ترک آن مجازات ندارد.",
            "ms": "Perkara sunat yang diberi pahala apabila dilakukan.",
            "ur": "جس کے کرنے پر ثواب ہو اور چھوڑنے پر گناہ نہ ہو۔",
        },
        "example": {
            "ar": "صدقة التطوع.",
            "en": "Voluntary charity.",
            "fr": "L’aumône volontaire.",
            "fa": "صدقه مستحبی.",
            "ms": "Sedekah sunat.",
            "ur": "نفلی صدقہ۔",
        },
    },
    "المندوب": {
        "label": {
            "ar": "المندوب",
            "en": "Mandub",
            "fr": "Mandub",
            "fa": "مندوب",
            "ms": "Mandub",
            "ur": "مندوب",
        },
        "definition": {
            "ar": "ما رغب الشرع في فعله دون إلزام.",
            "en": "An act encouraged without obligation.",
            "fr": "Un acte encouragé sans être obligatoire.",
            "fa": "کاری که شرع به انجام آن ترغیب کرده ولی الزام نکرده است.",
            "ms": "Perkara yang digalakkan tanpa kewajipan.",
            "ur": "جس کے کرنے کی شریعت نے ترغیب دی ہو مگر لازم نہ کیا ہو۔",
        },
        "example": {
            "ar": "صيام أيام نافلة.",
            "en": "Fasting voluntary days.",
            "fr": "Jeûner des jours surérogatoires.",
            "fa": "روزه گرفتن در روزهای مستحبی.",
            "ms": "Berpuasa pada hari-hari sunat.",
            "ur": "نفلی دنوں کے روزے رکھنا۔",
        },
    },
    "السنة": {
        "label": {
            "ar": "السنة",
            "en": "Sunnah",
            "fr": "Sunna",
            "fa": "سنت",
            "ms": "Sunnah",
            "ur": "سنت",
        },
        "definition": {
            "ar": "ما نقل عن النبي ﷺ من قول أو فعل أو تقرير.",
            "en": "A statement, action, or approval transmitted from the Prophet.",
            "fr": "Une parole, un acte ou une approbation attribuée au Prophète.",
            "fa": "گفتار، کردار یا تقریر پیامبر ﷺ.",
            "ms": "Perkataan, perbuatan atau pengakuan Nabi ﷺ.",
            "ur": "نبی ﷺ کا قول، فعل یا تقریر۔",
        },
        "example": {
            "ar": "بعض هيئات الصلاة وأذكارها.",
            "en": "Some prayer postures and remembrances.",
            "fr": "Certaines postures et invocations de la prière.",
            "fa": "برخی هیئت‌ها و اذکار نماز.",
            "ms": "Sebahagian perbuatan dan zikir dalam solat.",
            "ur": "نماز کی بعض سنتیں اور اذکار۔",
        },
    },
    "السنة المؤكدة": {
        "label": {
            "ar": "السنة المؤكدة",
            "en": "Emphasized Sunnah",
            "fr": "Sunna confirmée",
            "fa": "سنت مؤکده",
            "ms": "Sunnah muakkadah",
            "ur": "سنت مؤکدہ",
        },
        "definition": {
            "ar": "سنة واظب عليها النبي ﷺ أو حث عليها حثًا ظاهرًا.",
            "en": "A sunnah consistently practiced or strongly encouraged by the Prophet.",
            "fr": "Une pratique régulièrement accomplie ou fortement encouragée par le Prophète.",
            "fa": "سنتی که پیامبر ﷺ بر آن مداومت یا تأکید کرده است.",
            "ms": "Sunnah yang sentiasa dilakukan atau sangat ditekankan oleh Nabi ﷺ.",
            "ur": "وہ سنت جس پر نبی ﷺ نے ہمیشہ عمل کیا یا بہت تاکید فرمائی۔",
        },
        "example": {
            "ar": "صلاة الوتر عند من يعدّها سنة مؤكدة.",
            "en": "Witr prayer according to those who classify it as emphasized sunnah.",
            "fr": "La prière du witr selon ceux qui la classent comme sunna confirmée.",
            "fa": "نماز وتر نزد کسانی که آن را سنت مؤکده می‌دانند.",
            "ms": "Solat witir menurut ulama yang menganggapnya sunnah muakkadah.",
            "ur": "وتر کی نماز ان علماء کے نزدیک جو اسے سنت مؤکدہ کہتے ہیں۔",
        },
    },
}


# ============================================================
# القواعد
# ============================================================

FIQH_RULES = [
    {
        "title": {
            "ar": "الأمور بمقاصدها",
            "en": "Actions are judged by intentions",
            "fr": "Les actes sont jugés selon les intentions",
            "fa": "کارها بر اساس نیت‌ها سنجیده می‌شوند",
            "ms": "Amalan dinilai berdasarkan niat",
            "ur": "اعمال کا دارومدار نیتوں پر ہے",
        },
        "definition": {
            "ar": "تعتبر المقاصد والنيات في فهم الأفعال وترتيب آثارها الشرعية.",
            "en": "Intentions are considered when determining legal effects.",
            "fr": "Les intentions sont prises en compte pour déterminer les effets juridiques.",
            "fa": "نیت و هدف در تعیین آثار شرعی اعمال معتبر است.",
            "ms": "Niat dan tujuan diambil kira dalam menentukan hukum.",
            "ur": "اعمال کے شرعی اثرات میں نیتوں اور مقاصد کا اعتبار کیا جاتا ہے۔",
        },
        "example": {
            "ar": "يختلف دفع المال باختلاف كونه صدقة أو قرضًا أو هبة.",
            "en": "Giving money differs depending on whether it is charity, a loan, or a gift.",
            "fr": "Le don d’argent diffère selon qu’il s’agit d’une aumône, d’un prêt ou d’un don.",
            "fa": "دادن پول بر اساس صدقه، قرض یا هدیه بودن متفاوت است.",
            "ms": "Pemberian wang berbeza sama ada sedekah, pinjaman atau hadiah.",
            "ur": "مال دینے کا حکم صدقہ، قرض یا ہبہ ہونے کے لحاظ سے مختلف ہوتا ہے۔",
        },
    },
    {
        "title": {
            "ar": "اليقين لا يزول بالشك",
            "en": "Certainty is not removed by doubt",
            "fr": "La certitude n’est pas levée par le doute",
            "fa": "یقین با شک زائل نمی‌شود",
            "ms": "Keyakinan tidak dihilangkan oleh keraguan",
            "ur": "یقین شک سے زائل نہیں ہوتا",
        },
        "definition": {
            "ar": "الحكم الثابت بيقين لا يرفع بمجرد شك طارئ.",
            "en": "An established certainty is not overturned by a mere doubt.",
            "fr": "Une certitude établie n’est pas annulée par un simple doute.",
            "fa": "حکم ثابت با یقین با شک عارضی از بین نمی‌رود.",
            "ms": "Sesuatu yang pasti tidak gugur hanya kerana keraguan.",
            "ur": "یقینی حالت محض شک سے ختم نہیں ہوتی۔",
        },
        "example": {
            "ar": "من تيقن الطهارة وشك في الحدث يبقى على طهارته.",
            "en": "One certain of purity remains pure when merely doubting impurity.",
            "fr": "Celui qui est certain d’être pur le reste malgré un simple doute.",
            "fa": "کسی که به طهارت یقین دارد و در حدث شک می‌کند، پاک باقی می‌ماند.",
            "ms": "Orang yang yakin berwuduk kekal suci apabila hanya ragu-ragu.",
            "ur": "جسے طہارت کا یقین ہو وہ محض شک سے بے وضو نہیں ہوگا۔",
        },
    },
    {
        "title": {
            "ar": "المشقة تجلب التيسير",
            "en": "Hardship brings facilitation",
            "fr": "La difficulté entraîne la facilitation",
            "fa": "مشقت موجب آسانی است",
            "ms": "Kesukaran membawa kemudahan",
            "ur": "مشقت آسانی کا سبب بنتی ہے",
        },
        "definition": {
            "ar": "المشقة غير المعتادة سبب معتبر للتخفيف الشرعي وفق ضوابطه.",
            "en": "Unusual hardship may justify a legally recognized concession.",
            "fr": "Une difficulté inhabituelle peut justifier une facilité juridique.",
            "fa": "مشقت غیر عادی می‌تواند موجب تخفیف شرعی شود.",
            "ms": "Kesukaran luar biasa boleh membawa rukhsah syarak.",
            "ur": "غیر معمولی مشقت شرعی رخصت کا سبب بن سکتی ہے۔",
        },
        "example": {
            "ar": "الفطر للمريض الذي يضره الصوم.",
            "en": "Breaking the fast for a sick person harmed by fasting.",
            "fr": "Rompre le jeûne pour le malade que le jeûne nuit.",
            "fa": "افطار برای بیماری که روزه به او ضرر می‌زند.",
            "ms": "Berbuka bagi orang sakit yang terjejas oleh puasa.",
            "ur": "اس مریض کے لیے روزہ چھوڑنا جسے روزہ نقصان دے۔",
        },
    },
    {
        "title": {
            "ar": "الضرر يزال",
            "en": "Harm must be removed",
            "fr": "Le préjudice doit être supprimé",
            "fa": "ضرر باید برطرف شود",
            "ms": "Kemudaratan hendaklah dihilangkan",
            "ur": "ضرر کو دور کیا جائے گا",
        },
        "definition": {
            "ar": "يجب رفع الضرر أو تقليله بقدر الإمكان دون إحداث ضرر أكبر.",
            "en": "Harm should be removed or reduced without causing greater harm.",
            "fr": "Le préjudice doit être supprimé ou réduit sans causer un dommage plus grand.",
            "fa": "ضرر باید تا حد امکان بدون ایجاد ضرر بزرگ‌تر برطرف شود.",
            "ms": "Kemudaratan hendaklah dihapuskan tanpa menimbulkan mudarat yang lebih besar.",
            "ur": "ضرر کو اس طرح دور کیا جائے کہ اس سے بڑا ضرر پیدا نہ ہو۔",
        },
        "example": {
            "ar": "منع استعمال طريق يضر بالمارة.",
            "en": "Preventing use of a road that harms pedestrians.",
            "fr": "Interdire l’usage d’un passage dangereux pour les piétons.",
            "fa": "جلوگیری از استفاده از راهی که به عابران آسیب می‌زند.",
            "ms": "Melarang penggunaan jalan yang membahayakan pejalan kaki.",
            "ur": "ایسے راستے کے استعمال سے روکنا جو راہ گیروں کو نقصان دے۔",
        },
    },
    {
        "title": {
            "ar": "العادة محكمة",
            "en": "Custom is authoritative",
            "fr": "La coutume fait autorité",
            "fa": "عرف معتبر است",
            "ms": "Adat menjadi pertimbangan",
            "ur": "عرف معتبر ہے",
        },
        "definition": {
            "ar": "تعتبر العادة الصحيحة فيما لم يرد فيه تحديد شرعي خاص.",
            "en": "Sound custom is considered where no specific legal determination exists.",
            "fr": "La coutume saine est prise en compte en l’absence de règle précise.",
            "fa": "در مواردی که حکم خاصی نیست، عرف صحیح معتبر است.",
            "ms": "Adat yang sahih diambil kira apabila tiada penetapan khusus.",
            "ur": "جہاں شرعی تحدید نہ ہو وہاں صحیح عرف کا اعتبار کیا جاتا ہے۔",
        },
        "example": {
            "ar": "تحديد بعض صور النفقة بحسب عرف البلد.",
            "en": "Determining aspects of maintenance according to local custom.",
            "fr": "Déterminer certains aspects de la pension selon la coutume locale.",
            "fa": "تعیین برخی صور نفقه بر اساس عرف محل.",
            "ms": "Menentukan sebahagian nafkah berdasarkan adat setempat.",
            "ur": "نفقہ کی بعض صورتوں کا تعین مقامی عرف کے مطابق کرنا۔",
        },
    },
    {
        "title": {
            "ar": "الضرر لا يزال بالضرر",
            "en": "Harm is not removed by equivalent harm",
            "fr": "Le préjudice ne se supprime pas par un autre préjudice",
            "fa": "ضرر با ضرر برطرف نمی‌شود",
            "ms": "Kemudaratan tidak dihilangkan dengan kemudaratan",
            "ur": "ضرر کو دوسرے ضرر سے دور نہیں کیا جائے گا",
        },
        "definition": {
            "ar": "لا يجوز علاج ضرر بإحداث ضرر مساو أو أشد.",
            "en": "Harm cannot be remedied by causing equal or greater harm.",
            "fr": "Un préjudice ne peut être traité par un dommage équivalent ou supérieur.",
            "fa": "رفع ضرر با ایجاد ضرر مساوی یا بیشتر جایز نیست.",
            "ms": "Kemudaratan tidak boleh diatasi dengan kemudaratan yang sama atau lebih besar.",
            "ur": "ضرر کو برابر یا اس سے بڑے ضرر کے ذریعے دور نہیں کیا جا سکتا۔",
        },
        "example": {
            "ar": "لا يزال ضرر جار بإتلاف ملك جار آخر.",
            "en": "A neighbor's harm cannot be removed by destroying another neighbor's property.",
            "fr": "On ne supprime pas le tort d’un voisin en détruisant le bien d’un autre.",
            "fa": "ضرر همسایه با تخریب ملک همسایه دیگر رفع نمی‌شود.",
            "ms": "Mudarat jiran tidak boleh dihilangkan dengan merosakkan harta jiran lain.",
            "ur": "ایک پڑوسی کا ضرر دوسرے پڑوسی کی جائیداد تباہ کرکے دور نہیں کیا جا سکتا۔",
        },
    },
    {
        "title": {
            "ar": "درء المفاسد مقدم على جلب المصالح",
            "en": "Preventing harm takes precedence over gaining benefit",
            "fr": "Écarter les dommages prime sur les intérêts",
            "fa": "دفع مفسده بر جلب منفعت مقدم است",
            "ms": "Menolak kemudaratan didahulukan daripada menarik manfaat",
            "ur": "مفاسد کو دور کرنا مصالح حاصل کرنے پر مقدم ہے",
        },
        "definition": {
            "ar": "إذا تعارضت مفسدة ومصلحة معتبرتان قدم دفع المفسدة عند رجحانها.",
            "en": "When a harm and benefit conflict, the stronger harm may be given priority.",
            "fr": "En cas de conflit, écarter le dommage prépondérant peut primer.",
            "fa": "در تعارض مفسده و منفعت، دفع مفسده مهم‌تر مقدم می‌شود.",
            "ms": "Apabila manfaat dan mudarat bertembung, mudarat yang lebih besar hendaklah dielakkan.",
            "ur": "مصلحت اور مفسدت کے تعارض میں غالب مفسدت کو دور کرنا مقدم ہو سکتا ہے۔",
        },
        "example": {
            "ar": "منع معاملة فيها ربح ويترتب عليها ظلم واضح.",
            "en": "Preventing a profitable transaction that clearly causes injustice.",
            "fr": "Interdire une transaction rentable qui entraîne une injustice évidente.",
            "fa": "جلوگیری از معامله‌ای سودآور که ظلم آشکار دارد.",
            "ms": "Menghalang urus niaga yang menguntungkan tetapi jelas menzalimi.",
            "ur": "ایسے منافع بخش معاملے کو روکنا جس میں واضح ظلم ہو۔",
        },
    },
    {
        "title": {
            "ar": "الضرورات تبيح المحظورات",
            "en": "Necessities permit prohibited matters",
            "fr": "Les nécessités permettent les interdits",
            "fa": "ضرورت‌ها محرمات را مباح می‌کنند",
            "ms": "Darurat mengharuskan perkara terlarang",
            "ur": "ضرورتیں ممنوع چیزوں کو جائز کر دیتی ہیں",
        },
        "definition": {
            "ar": "الضرورة المنضبطة قد تبيح المحظور بقدر دفع الضرر.",
            "en": "A genuine necessity may permit a prohibited act only as needed.",
            "fr": "Une nécessité réelle peut permettre l’interdit dans la mesure nécessaire.",
            "fa": "ضرورت واقعی می‌تواند محظور را به اندازه نیاز مباح کند.",
            "ms": "Darurat sebenar boleh mengharuskan perkara terlarang sekadar keperluan.",
            "ur": "حقیقی ضرورت بقدر ضرورت ممنوع چیز کو جائز کر سکتی ہے۔",
        },
        "example": {
            "ar": "تناول المحرم عند خوف الهلاك بقدر الحاجة.",
            "en": "Consuming a prohibited item to avoid death, only as needed.",
            "fr": "Consommer un interdit pour éviter la mort, uniquement à hauteur du besoin.",
            "fa": "خوردن حرام هنگام ترس از مرگ به اندازه نیاز.",
            "ms": "Mengambil yang haram ketika takut maut sekadar keperluan.",
            "ur": "ہلاکت کے خوف میں بقدر ضرورت حرام چیز کھانا۔",
        },
    },
    {
        "title": {
            "ar": "الضرورة تقدر بقدرها",
            "en": "Necessity is measured by its extent",
            "fr": "La nécessité est limitée à son étendue",
            "fa": "ضرورت به اندازه خود سنجیده می‌شود",
            "ms": "Darurat diukur mengikut kadarnya",
            "ur": "ضرورت کا اندازہ بقدر ضرورت ہوگا",
        },
        "definition": {
            "ar": "الرخصة الناتجة عن الضرورة لا تتجاوز مقدار الحاجة.",
            "en": "A concession due to necessity does not exceed what is needed.",
            "fr": "La concession ne dépasse pas la mesure de la nécessité.",
            "fa": "رخصت ناشی از ضرورت از اندازه نیاز فراتر نمی‌رود.",
            "ms": "Rukhsah darurat tidak boleh melebihi kadar keperluan.",
            "ur": "ضرورت کی رخصت بقدر ضرورت سے زیادہ نہیں ہوگی۔",
        },
        "example": {
            "ar": "لا يتوسع المضطر بعد زوال الخطر.",
            "en": "The person in necessity does not exceed the need after danger ends.",
            "fr": "La personne en nécessité ne dépasse pas le besoin après la fin du danger.",
            "fa": "پس از رفع خطر، شخص مضطر نباید زیاده‌روی کند.",
            "ms": "Orang yang darurat tidak boleh berlebihan selepas bahaya hilang.",
            "ur": "خطر ختم ہونے کے بعد مضطر شخص ضرورت سے زیادہ نہیں لے گا۔",
        },
    },
    {
        "title": {
            "ar": "الأصل براءة الذمة",
            "en": "The basic assumption is freedom from liability",
            "fr": "La présomption est l’absence de responsabilité",
            "fa": "اصل برائت ذمه است",
            "ms": "Asal seseorang bebas daripada tanggungan",
            "ur": "اصل براءتِ ذمہ ہے",
        },
        "definition": {
            "ar": "الأصل عدم شغل ذمة الشخص بحق أو التزام حتى يثبت الدليل.",
            "en": "A person is presumed free of a claim or obligation until proven otherwise.",
            "fr": "Une personne est présumée libre de toute obligation jusqu’à preuve du contraire.",
            "fa": "اصل بر این است که ذمه شخص تا اثبات دلیل مشغول نیست.",
            "ms": "Asal seseorang tidak menanggung tuntutan sehingga dibuktikan.",
            "ur": "دلیل ثابت ہونے تک انسان کی ذمہ داری سے براءت اصل ہے۔",
        },
        "example": {
            "ar": "من ادعى دينًا فعليه إثباته.",
            "en": "Whoever claims a debt must prove it.",
            "fr": "Celui qui réclame une dette doit la prouver.",
            "fa": "مدعی بدهی باید آن را ثابت کند.",
            "ms": "Orang yang mendakwa hutang hendaklah membuktikannya.",
            "ur": "جو قرض کا دعویٰ کرے اس پر ثبوت لازم ہے۔",
        },
    },
    {
        "title": {
            "ar": "الأصل في العبادات التوقيف",
            "en": "Worship is based on textual authorization",
            "fr": "Les actes cultuels reposent sur une preuve",
            "fa": "اصل در عبادات توقیف است",
            "ms": "Ibadah berdasarkan dalil",
            "ur": "عبادات توقیفی ہیں",
        },
        "definition": {
            "ar": "لا تشرع عبادة مخصوصة بصفة أو وقت أو عدد إلا بدليل معتبر.",
            "en": "A specific form, time, or number of worship requires valid evidence.",
            "fr": "Une forme, un temps ou un nombre précis exige une preuve valable.",
            "fa": "عبادت مخصوص با کیفیت یا زمان و تعداد خاص نیازمند دلیل معتبر است.",
            "ms": "Bentuk, masa atau bilangan ibadah tertentu memerlukan dalil yang sah.",
            "ur": "کسی عبادت کی مخصوص کیفیت، وقت یا تعداد کے لیے معتبر دلیل لازم ہے۔",
        },
        "example": {
            "ar": "عدم تخصيص ذكر بعدد تعبدي بلا دليل.",
            "en": "Not assigning a specific devotional number without evidence.",
            "fr": "Ne pas fixer un nombre cultuel sans preuve.",
            "fa": "تعیین تعداد خاص برای ذکر بدون دلیل.",
            "ms": "Tidak menetapkan bilangan zikir tanpa dalil.",
            "ur": "بغیر دلیل کسی ذکر کے لیے خاص تعداد مقرر نہ کرنا۔",
        },
    },
    {
        "title": {
            "ar": "الأصل في المعاملات الإباحة",
            "en": "The default rule in transactions is permissibility",
            "fr": "Le principe des transactions est la permission",
            "fa": "اصل در معاملات اباحه است",
            "ms": "Asal muamalat ialah harus",
            "ur": "معاملات میں اصل اباحت ہے",
        },
        "definition": {
            "ar": "الأصل في المعاملات الجديدة الجواز ما لم تتضمن محظورًا.",
            "en": "New transactions are presumed permissible unless they contain a prohibition.",
            "fr": "Les nouvelles transactions sont permises sauf si elles comportent un interdit.",
            "fa": "معاملات جدید در اصل جایز هستند مگر اینکه محظوری داشته باشند.",
            "ms": "Urus niaga baharu asalnya harus kecuali mengandungi larangan.",
            "ur": "نئے معاملات اصلًا جائز ہیں جب تک ان میں کوئی ممانعت نہ ہو۔",
        },
        "example": {
            "ar": "جواز وسيلة بيع جديدة إذا خلت من الربا والغرر.",
            "en": "A new sales method is permissible if free from riba and excessive uncertainty.",
            "fr": "Une nouvelle méthode de vente est permise sans intérêt usuraire ni aléa excessif.",
            "fa": "روش فروش جدید اگر از ربا و غرر خالی باشد جایز است.",
            "ms": "Kaedah jual beli baharu harus jika bebas daripada riba dan gharar.",
            "ur": "نیا طریقۂ فروخت اگر سود اور غرر سے پاک ہو تو جائز ہے۔",
        },
    },
    {
        "title": {
            "ar": "العبرة في العقود للمقاصد والمعاني",
            "en": "Contracts are judged by purposes and meanings",
            "fr": "Les contrats sont jugés selon leurs finalités",
            "fa": "اعتبار در عقود با مقاصد و معانی است",
            "ms": "Kontrak dinilai berdasarkan tujuan dan makna",
            "ur": "عقود میں مقاصد اور معانی کا اعتبار ہے",
        },
        "definition": {
            "ar": "تعتبر حقيقة العقد وآثاره لا مجرد ألفاظه أو اسمه.",
            "en": "The substance and effects of a contract matter, not merely its label.",
            "fr": "La réalité et les effets du contrat comptent, non son simple nom.",
            "fa": "حقیقت و آثار عقد معتبر است نه فقط نام و الفاظ آن.",
            "ms": "Hakikat dan kesan kontrak diambil kira, bukan namanya sahaja.",
            "ur": "عقد کی حقیقت اور اثرات معتبر ہیں، صرف نام نہیں۔",
        },
        "example": {
            "ar": "لا يصبح القرض المحرم مباحًا بمجرد تغيير اسمه.",
            "en": "Renaming a prohibited loan does not make it permissible.",
            "fr": "Changer le nom d’un prêt interdit ne le rend pas permis.",
            "fa": "تغییر نام قرض حرام آن را حلال نمی‌کند.",
            "ms": "Menukar nama pinjaman yang haram tidak menjadikannya harus.",
            "ur": "حرام قرض کا نام بدلنے سے وہ جائز نہیں ہو جاتا۔",
        },
    },
    {
        "title": {
            "ar": "الخراج بالضمان",
            "en": "Benefit accompanies liability",
            "fr": "Le bénéfice accompagne la responsabilité",
            "fa": "خراج در برابر ضمان است",
            "ms": "Hasil datang bersama tanggungan",
            "ur": "خراج ضمان کے ساتھ ہے",
        },
        "definition": {
            "ar": "من تحمل ضمان الشيء وتبعاته استحق غلته في الجملة.",
            "en": "One who bears liability for an asset generally deserves its benefit.",
            "fr": "Celui qui assume la responsabilité d’un bien en mérite généralement le bénéfice.",
            "fa": "کسی که ضمان و مسئولیت مال را می‌پذیرد، در اصل مستحق منفعت آن است.",
            "ms": "Pihak yang menanggung risiko harta berhak mendapat hasilnya.",
            "ur": "جو شخص مال کی ذمہ داری اٹھائے وہ اصولاً اس کے نفع کا مستحق ہے۔",
        },
        "example": {
            "ar": "استحقاق غلة المبيع لمن كان ضامنًا له.",
            "en": "The liable owner is entitled to the yield of an asset.",
            "fr": "Le responsable du bien a droit à son rendement.",
            "fa": "مستحق بودن مالک ضامن نسبت به منفعت مال.",
            "ms": "Pemilik yang menanggung risiko berhak terhadap hasil harta.",
            "ur": "ضامن مالک مال کی پیداوار کا مستحق ہوتا ہے۔",
        },
    },
    {
        "title": {
            "ar": "الغنم بالغرم",
            "en": "Benefit accompanies burden",
            "fr": "Le gain accompagne la charge",
            "fa": "غنیمت در برابر غرامت است",
            "ms": "Keuntungan bersama tanggungan",
            "ur": "نفع ذمہ داری کے ساتھ ہے",
        },
        "definition": {
            "ar": "استحقاق المنفعة يقابله تحمل التبعة والضمان.",
            "en": "Entitlement to benefit accompanies bearing the associated risk.",
            "fr": "Le droit au bénéfice implique l’acceptation de la charge et du risque.",
            "fa": "استحقاق منفعت با تحمل مسئولیت و ریسک همراه است.",
            "ms": "Hak mendapat manfaat datang bersama tanggungan risiko.",
            "ur": "نفع کا استحقاق ذمہ داری اور خطرہ اٹھانے کے ساتھ ہے۔",
        },
        "example": {
            "ar": "من يستحق ربح الاستثمار يتحمل مخاطر الاستثمار.",
            "en": "One entitled to investment profit bears its investment risks.",
            "fr": "Celui qui reçoit le profit d’un investissement en assume les risques.",
            "fa": "کسی که سود سرمایه‌گذاری را می‌گیرد، ریسک آن را نیز می‌پذیرد.",
            "ms": "Pihak yang mendapat keuntungan pelaburan menanggung risikonya.",
            "ur": "سرمایہ کاری کے نفع کا مستحق اس کے خطرات بھی برداشت کرتا ہے۔",
        },
    },
    {
        "title": {
            "ar": "ما لا يتم الواجب إلا به فهو واجب",
            "en": "Whatever is necessary to fulfill an obligation is obligatory",
            "fr": "Ce qui est nécessaire à l’obligation devient obligatoire",
            "fa": "مقدمه واجب، واجب است",
            "ms": "Sesuatu yang diperlukan untuk kewajipan menjadi wajib",
            "ur": "جس کے بغیر واجب مکمل نہ ہو وہ بھی واجب ہے",
        },
        "definition": {
            "ar": "الوسيلة اللازمة لتحقيق واجب تأخذ حكم الوجوب بقدر لزومها.",
            "en": "A necessary means to fulfill an obligation takes its ruling.",
            "fr": "Le moyen nécessaire à l’accomplissement d’une obligation devient obligatoire.",
            "fa": "وسیله ضروری برای انجام واجب به اندازه ضرورت حکم وجوب می‌گیرد.",
            "ms": "Sarana yang diperlukan untuk melaksanakan kewajipan turut menjadi wajib.",
            "ur": "واجب کی تکمیل کے لیے ضروری ذریعہ بقدر ضرورت واجب ہو جاتا ہے۔",
        },
        "example": {
            "ar": "تعلم القدر اللازم لصحة الصلاة.",
            "en": "Learning what is necessary for a valid prayer.",
            "fr": "Apprendre ce qui est nécessaire à la validité de la prière.",
            "fa": "یادگیری مقدار لازم برای صحت نماز.",
            "ms": "Mempelajari perkara yang diperlukan untuk sah solat.",
            "ur": "نماز کی صحت کے لیے ضروری علم حاصل کرنا۔",
        },
    },
    {
        "title": {
            "ar": "الوسائل لها أحكام المقاصد",
            "en": "Means take the ruling of their ends",
            "fr": "Les moyens prennent le statut des finalités",
            "fa": "وسایل حکم مقاصد را دارند",
            "ms": "Sarana mengambil hukum tujuannya",
            "ur": "ذرائع مقاصد کا حکم رکھتے ہیں",
        },
        "definition": {
            "ar": "تأخذ الوسيلة حكم الغاية بحسب علاقتها بها ونتيجتها.",
            "en": "A means may take the ruling of its intended end according to its effect.",
            "fr": "Le moyen peut prendre le statut de sa finalité selon son effet.",
            "fa": "وسیله با توجه به ارتباط و نتیجه‌اش حکم مقصد را می‌گیرد.",
            "ms": "Sarana mengambil hukum tujuan berdasarkan hubungan dan kesannya.",
            "ur": "ذریعہ اپنے مقصد اور نتیجے کے لحاظ سے اس کا حکم لے سکتا ہے۔",
        },
        "example": {
            "ar": "تحريم وسيلة تؤدي غالبًا إلى محرم قطعي.",
            "en": "Prohibiting a means that normally leads to a definite prohibition.",
            "fr": "Interdire un moyen qui conduit généralement à un interdit certain.",
            "fa": "حرام کردن وسیله‌ای که غالباً به حرام قطعی می‌انجامد.",
            "ms": "Melarang sarana yang biasanya membawa kepada perkara haram.",
            "ur": "ایسے ذریعے کی ممانعت جو عموماً قطعی حرام تک پہنچاتا ہو۔",
        },
    },
    {
        "title": {
            "ar": "التابع تابع",
            "en": "The dependent follows the principal",
            "fr": "L’élément dépendant suit le principal",
            "fa": "تابع تابع است",
            "ms": "Perkara yang mengikut mengambil hukum asal",
            "ur": "تابع متبوع کے تابع ہوتا ہے",
        },
        "definition": {
            "ar": "الشيء التابع يأخذ حكم متبوعه ولا يفرد غالبًا بحكم مستقل.",
            "en": "A dependent matter generally follows the ruling of the principal matter.",
            "fr": "L’élément dépendant suit généralement le statut de l’élément principal.",
            "fa": "امر تابع معمولاً حکم متبوع خود را می‌گیرد.",
            "ms": "Perkara yang mengikut biasanya mengambil hukum perkara asal.",
            "ur": "تابع چیز عموماً متبوع کا حکم رکھتی ہے۔",
        },
        "example": {
            "ar": "دخول ملحقات العقار المعتادة في البيع.",
            "en": "Usual appurtenances are included in the sale of property.",
            "fr": "Les dépendances habituelles sont incluses dans la vente du bien.",
            "fa": "شامل شدن ملحقات معمول ملک در فروش آن.",
            "ms": "Kelengkapan biasa termasuk dalam jualan hartanah.",
            "ur": "جائیداد کی معمولی ملحقات کا فروخت میں شامل ہونا۔",
        },
    },
    {
        "title": {
            "ar": "يغتفر في التابع ما لا يغتفر في المتبوع",
            "en": "What is tolerated in a dependent matter is not tolerated independently",
            "fr": "Ce qui est toléré dans le dépendant ne l’est pas dans le principal",
            "fa": "در تابع چیزی بخشوده می‌شود که در متبوع بخشوده نمی‌شود",
            "ms": "Perkara kecil yang mengikut boleh dimaafkan",
            "ur": "تابع میں جو معاف ہے متبوع میں معاف نہیں",
        },
        "definition": {
            "ar": "قد يتسامح في أمر يسير تابع لا يتسامح فيه إذا كان مستقلًا.",
            "en": "A minor dependent matter may be tolerated when it would not be tolerated independently.",
            "fr": "Un élément mineur peut être toléré en tant que dépendant.",
            "fa": "امر جزئی در حالت تابع ممکن است بخشوده شود ولی مستقلًا نه.",
            "ms": "Perkara kecil yang mengikut mungkin dimaafkan tetapi tidak secara berasingan.",
            "ur": "معمولی تابع چیز میں گنجائش ہو سکتی ہے جو مستقل چیز میں نہ ہو۔",
        },
        "example": {
            "ar": "التسامح في غرر يسير تابع لعقد معلوم.",
            "en": "Tolerating minor uncertainty incidental to a known contract.",
            "fr": "Tolérer une incertitude mineure liée à un contrat connu.",
            "fa": "گذشت از غرر اندک تابع عقد معلوم.",
            "ms": "Memaafkan gharar kecil yang mengikut kontrak yang jelas.",
            "ur": "معلوم عقد کے تابع معمولی غرر سے درگزر کرنا۔",
        },
    },
    {
        "title": {
            "ar": "الاجتهاد لا ينقض بالاجتهاد",
            "en": "One ijtihad is not overturned by another",
            "fr": "Un ijtihad n’est pas annulé par un autre",
            "fa": "اجتهاد با اجتهاد نقض نمی‌شود",
            "ms": "Ijtihad tidak dibatalkan oleh ijtihad lain",
            "ur": "ایک اجتہاد دوسرے اجتہاد سے ختم نہیں ہوتا",
        },
        "definition": {
            "ar": "الحكم الاجتهادي لا ينقض لمجرد ظهور اجتهاد آخر.",
            "en": "A reasoned judgment is not overturned merely because another opinion appears.",
            "fr": "Un jugement raisonné n’est pas annulé par la seule apparition d’un autre avis.",
            "fa": "حکم اجتهادی صرف به سبب ظهور اجتهاد دیگر نقض نمی‌شود.",
            "ms": "Hukum ijtihad tidak terbatal hanya kerana muncul ijtihad lain.",
            "ur": "محض دوسرے اجتہاد کے ظاہر ہونے سے پہلا اجتہاد ختم نہیں ہوتا۔",
        },
        "example": {
            "ar": "عدم إبطال أحكام ماضية مبنية على اجتهاد معتبر.",
            "en": "Past judgments based on valid reasoning are not automatically invalidated.",
            "fr": "Les jugements passés fondés sur un ijtihad valide ne sont pas automatiquement annulés.",
            "fa": "احکام گذشته مبتنی بر اجتهاد معتبر خودبه‌خود باطل نمی‌شوند.",
            "ms": "Keputusan lama berdasarkan ijtihad sah tidak terbatal secara automatik.",
            "ur": "معتبر اجتہاد پر مبنی سابقہ فیصلے خود بخود باطل نہیں ہوتے۔",
        },
    },
    {
        "title": {
            "ar": "الحكم يدور مع علته وجودًا وعدمًا",
            "en": "A ruling follows its effective cause",
            "fr": "Le jugement suit sa cause effective",
            "fa": "حکم با علت خود وجوداً و عدماً می‌گردد",
            "ms": "Hukum beredar bersama illahnya",
            "ur": "حکم علت کے ساتھ وجود اور عدم میں ہوتا ہے",
        },
        "definition": {
            "ar": "إذا ثبتت العلة ثبت الحكم المرتبط بها وإذا انتفت انتفى.",
            "en": "When the effective cause exists, the related ruling applies; when it ends, it ends.",
            "fr": "Le jugement existe avec sa cause et cesse lorsque sa cause cesse.",
            "fa": "با وجود علت حکم وجود دارد و با نبود آن حکم مربوط نیز منتفی می‌شود.",
            "ms": "Apabila illah wujud, hukum berlaku; apabila tiada, hukum berakhir.",
            "ur": "علت موجود ہو تو حکم بھی موجود ہوتا ہے اور علت نہ ہو تو حکم بھی نہیں رہتا۔",
        },
        "example": {
            "ar": "ارتباط رخصة السفر بوصف السفر.",
            "en": "The travel concession is linked to the status of travel.",
            "fr": "La concession du voyage est liée au fait d’être voyageur.",
            "fa": "ارتباط رخصت سفر با وجود سفر.",
            "ms": "Rukhsah musafir berkaitan dengan keadaan musafir.",
            "ur": "سفر کی رخصت کا سفر کی حالت کے ساتھ تعلق۔",
        },
    },
]


# ============================================================
# الدول
# ============================================================

COUNTRIES = [
    {
        "country": {
            "ar": "السودان",
            "en": "Sudan",
            "fr": "Soudan",
            "fa": "سودان",
            "ms": "Sudan",
            "ur": "سوڈان",
        },
        "madhab": {
            "ar": "مالكي وشافعي",
            "en": "Maliki and Shafi'i",
            "fr": "Malikite et chaféite",
            "fa": "مالکی و شافعی",
            "ms": "Maliki dan Syafie",
            "ur": "مالکی اور شافعی",
        },
        "note": {
            "ar": "تنوع فقهي تاريخي",
            "en": "Historical juristic diversity",
            "fr": "Diversité juridique historique",
            "fa": "تنوع فقهی تاریخی",
            "ms": "Kepelbagaian fiqh sejarah",
            "ur": "تاریخی فقہی تنوع",
        },
    },
    {
        "country": {
            "ar": "المغرب",
            "en": "Morocco",
            "fr": "Maroc",
            "fa": "مراکش",
            "ms": "Maghribi",
            "ur": "مراکش",
        },
        "madhab": {
            "ar": "مالكي",
            "en": "Maliki",
            "fr": "Malikite",
            "fa": "مالکی",
            "ms": "Maliki",
            "ur": "مالکی",
        },
        "note": {
            "ar": "الغالب تاريخيًا",
            "en": "Historically predominant",
            "fr": "Historiquement dominant",
            "fa": "غالب تاریخی",
            "ms": "Dominan secara sejarah",
            "ur": "تاریخی طور پر غالب",
        },
    },
    {
        "country": {
            "ar": "سوريا",
            "en": "Syria",
            "fr": "Syrie",
            "fa": "سوریه",
            "ms": "Syria",
            "ur": "شام",
        },
        "madhab": {
            "ar": "حنفي وشافعي",
            "en": "Hanafi and Shafi'i",
            "fr": "Hanafite et chaféite",
            "fa": "حنفی و شافعی",
            "ms": "Hanafi dan Syafie",
            "ur": "حنفی اور شافعی",
        },
        "note": {
            "ar": "تنوع فقهي تاريخي",
            "en": "Historical juristic diversity",
            "fr": "Diversité juridique historique",
            "fa": "تنوع فقهی تاریخی",
            "ms": "Kepelbagaian fiqh sejarah",
            "ur": "تاریخی فقہی تنوع",
        },
    },
    {
        "country": {
            "ar": "العراق",
            "en": "Iraq",
            "fr": "Irak",
            "fa": "عراق",
            "ms": "Iraq",
            "ur": "عراق",
        },
        "madhab": {
            "ar": "حنفي وشافعي وحنبلي",
            "en": "Hanafi, Shafi'i, and Hanbali",
            "fr": "Hanafite, chaféite et hanbalite",
            "fa": "حنفی، شافعی و حنبلی",
            "ms": "Hanafi, Syafie dan Hanbali",
            "ur": "حنفی، شافعی اور حنبلی",
        },
        "note": {
            "ar": "تنوع فقهي واسع",
            "en": "Broad juristic diversity",
            "fr": "Grande diversité juridique",
            "fa": "تنوع فقهی گسترده",
            "ms": "Kepelbagaian fiqh yang luas",
            "ur": "وسیع فقہی تنوع",
        },
    },
    {
        "country": {
            "ar": "الإمارات",
            "en": "United Arab Emirates",
            "fr": "Émirats arabes unis",
            "fa": "امارات",
            "ms": "Emiriah Arab Bersatu",
            "ur": "متحدہ عرب امارات",
        },
        "madhab": {
            "ar": "تنوع سني",
            "en": "Sunni diversity",
            "fr": "Diversité sunnite",
            "fa": "تنوع اهل سنت",
            "ms": "Kepelbagaian Sunni",
            "ur": "اہل سنت کا تنوع",
        },
        "note": {
            "ar": "حضور مالكي وشافعي وحنبلي",
            "en": "Maliki, Shafi'i, and Hanbali influences",
            "fr": "Influences malikite, chaféite et hanbalite",
            "fa": "حضور دیدگاه‌های مالکی، شافعی و حنبلی",
            "ms": "Pengaruh Maliki, Syafie dan Hanbali",
            "ur": "مالکی، شافعی اور حنبلی اثرات",
        },
    },
    {
        "country": {
            "ar": "عُمان",
            "en": "Oman",
            "fr": "Oman",
            "fa": "عمان",
            "ms": "Oman",
            "ur": "عمان",
        },
        "madhab": {
            "ar": "إباضي",
            "en": "Ibadi",
            "fr": "Ibadite",
            "fa": "اباضی",
            "ms": "Ibadi",
            "ur": "اباضی",
        },
        "note": {
            "ar": "مع وجود مدارس أخرى",
            "en": "Alongside other schools",
            "fr": "Avec d’autres écoles",
            "fa": "در کنار مذاهب دیگر",
            "ms": "Bersama mazhab lain",
            "ur": "دیگر مسالک کے ساتھ",
        },
    },
    {
        "country": {
            "ar": "الأردن",
            "en": "Jordan",
            "fr": "Jordanie",
            "fa": "اردن",
            "ms": "Jordan",
            "ur": "اردن",
        },
        "madhab": {
            "ar": "شافعي وحنفي",
            "en": "Shafi'i and Hanafi",
            "fr": "Chaféite et hanafite",
            "fa": "شافعی و حنفی",
            "ms": "Syafie dan Hanafi",
            "ur": "شافعی اور حنفی",
        },
        "note": {
            "ar": "تنوع فقهي",
            "en": "Juristic diversity",
            "fr": "Diversité juridique",
            "fa": "تنوع فقهی",
            "ms": "Kepelbagaian fiqh",
            "ur": "فقہی تنوع",
        },
    },
    {
        "country": {
            "ar": "البحرين",
            "en": "Bahrain",
            "fr": "Bahreïn",
            "fa": "بحرین",
            "ms": "Bahrain",
            "ur": "بحرین",
        },
        "madhab": {
            "ar": "جعفري ومالكي وشافعي وحنبلي",
            "en": "Ja'fari, Maliki, Shafi'i, and Hanbali",
            "fr": "Jaafarite, malikite, chaféite et hanbalite",
            "fa": "جعفری، مالکی، شافعی و حنبلی",
            "ms": "Jaafari, Maliki, Syafie dan Hanbali",
            "ur": "جعفری، مالکی، شافعی اور حنبلی",
        },
        "note": {
            "ar": "تنوع مذهبي",
            "en": "Religious diversity",
            "fr": "Diversité religieuse",
            "fa": "تنوع مذهبی",
            "ms": "Kepelbagaian mazhab",
            "ur": "مذہبی تنوع",
        },
    },
    {
        "country": {
            "ar": "الكويت",
            "en": "Kuwait",
            "fr": "Koweït",
            "fa": "کویت",
            "ms": "Kuwait",
            "ur": "کویت",
        },
        "madhab": {
            "ar": "مالكي وحنبلي",
            "en": "Maliki and Hanbali",
            "fr": "Malikite et hanbalite",
            "fa": "مالکی و حنبلی",
            "ms": "Maliki dan Hanbali",
            "ur": "مالکی اور حنبلی",
        },
        "note": {
            "ar": "مع حضور مدارس أخرى",
            "en": "Alongside other schools",
            "fr": "Avec d’autres écoles",
            "fa": "در کنار مذاهب دیگر",
            "ms": "Bersama mazhab lain",
            "ur": "دیگر مسالک کے ساتھ",
        },
    },
    {
        "country": {
            "ar": "تونس",
            "en": "Tunisia",
            "fr": "Tunisie",
            "fa": "تونس",
            "ms": "Tunisia",
            "ur": "تیونس",
        },
        "madhab": {
            "ar": "مالكي",
            "en": "Maliki",
            "fr": "Malikite",
            "fa": "مالکی",
            "ms": "Maliki",
            "ur": "مالکی",
        },
        "note": {
            "ar": "الغالب تاريخيًا",
            "en": "Historically predominant",
            "fr": "Historiquement dominant",
            "fa": "غالب تاریخی",
            "ms": "Dominan secara sejarah",
            "ur": "تاریخی طور پر غالب",
        },
    },
    {
        "country": {
            "ar": "ليبيا",
            "en": "Libya",
            "fr": "Libye",
            "fa": "لیبی",
            "ms": "Libya",
            "ur": "لیبیا",
        },
        "madhab": {
            "ar": "مالكي",
            "en": "Maliki",
            "fr": "Malikite",
            "fa": "مالکی",
            "ms": "Maliki",
            "ur": "مالکی",
        },
        "note": {
            "ar": "الغالب تاريخيًا",
            "en": "Historically predominant",
            "fr": "Historiquement dominant",
            "fa": "غالب تاریخی",
            "ms": "Dominan secara sejarah",
            "ur": "تاریخی طور پر غالب",
        },
    },
    {
        "country": {
            "ar": "الجزائر",
            "en": "Algeria",
            "fr": "Algérie",
            "fa": "الجزایر",
            "ms": "Algeria",
            "ur": "الجیریا",
        },
        "madhab": {
            "ar": "مالكي",
            "en": "Maliki",
            "fr": "Malikite",
            "fa": "مالکی",
            "ms": "Maliki",
            "ur": "مالکی",
        },
        "note": {
            "ar": "الغالب تاريخيًا",
            "en": "Historically predominant",
            "fr": "Historiquement dominant",
            "fa": "غالب تاریخی",
            "ms": "Dominan secara sejarah",
            "ur": "تاریخی طور پر غالب",
        },
    },
    {
        "country": {
            "ar": "إندونيسيا",
            "en": "Indonesia",
            "fr": "Indonésie",
            "fa": "اندونزی",
            "ms": "Indonesia",
            "ur": "انڈونیشیا",
        },
        "madhab": {
            "ar": "شافعي",
            "en": "Shafi'i",
            "fr": "Chaféite",
            "fa": "شافعی",
            "ms": "Syafie",
            "ur": "شافعی",
        },
        "note": {
            "ar": "الغالب في المؤسسات التقليدية",
            "en": "Predominant in traditional institutions",
            "fr": "Dominant dans les institutions traditionnelles",
            "fa": "غالب در نهادهای سنتی",
            "ms": "Dominan dalam institusi tradisional",
            "ur": "روایتی اداروں میں غالب",
        },
    },
    {
        "country": {
            "ar": "ماليزيا",
            "en": "Malaysia",
            "fr": "Malaisie",
            "fa": "مالزی",
            "ms": "Malaysia",
            "ur": "ملائیشیا",
        },
        "madhab": {
            "ar": "شافعي",
            "en": "Shafi'i",
            "fr": "Chaféite",
            "fa": "شافعی",
            "ms": "Syafie",
            "ur": "شافعی",
        },
        "note": {
            "ar": "الغالب في المؤسسات الرسمية",
            "en": "Predominant in official institutions",
            "fr": "Dominant dans les institutions officielles",
            "fa": "غالب در نهادهای رسمی",
            "ms": "Dominan dalam institusi rasmi",
            "ur": "سرکاری اداروں میں غالب",
        },
    },
    {
        "country": {
            "ar": "باكستان",
            "en": "Pakistan",
            "fr": "Pakistan",
            "fa": "پاکستان",
            "ms": "Pakistan",
            "ur": "پاکستان",
        },
        "madhab": {
            "ar": "حنفي",
            "en": "Hanafi",
            "fr": "Hanafite",
            "fa": "حنفی",
            "ms": "Hanafi",
            "ur": "حنفی",
        },
        "note": {
            "ar": "مع وجود مدارس أخرى",
            "en": "Alongside other schools",
            "fr": "Avec d’autres écoles",
            "fa": "در کنار مذاهب دیگر",
            "ms": "Bersama mazhab lain",
            "ur": "دیگر مسالک کے ساتھ",
        },
    },
    {
        "country": {
            "ar": "أفغانستان",
            "en": "Afghanistan",
            "fr": "Afghanistan",
            "fa": "افغانستان",
            "ms": "Afghanistan",
            "ur": "افغانستان",
        },
        "madhab": {
            "ar": "حنفي",
            "en": "Hanafi",
            "fr": "Hanafite",
            "fa": "حنفی",
            "ms": "Hanafi",
            "ur": "حنفی",
        },
        "note": {
            "ar": "الغالب بين السنة",
            "en": "Predominant among Sunnis",
            "fr": "Dominant chez les sunnites",
            "fa": "غالب میان اهل سنت",
            "ms": "Dominan dalam kalangan Sunni",
            "ur": "اہل سنت میں غالب",
        },
    },
    {
        "country": {
            "ar": "إيران",
            "en": "Iran",
            "fr": "Iran",
            "fa": "ایران",
            "ms": "Iran",
            "ur": "ایران",
        },
        "madhab": {
            "ar": "جعفري",
            "en": "Ja'fari",
            "fr": "Jaafarite",
            "fa": "جعفری",
            "ms": "Jaafari",
            "ur": "جعفری",
        },
        "note": {
            "ar": "الغالب رسميًا",
            "en": "Officially predominant",
            "fr": "Officiellement dominant",
            "fa": "غالب رسمی",
            "ms": "Dominan secara rasmi",
            "ur": "سرکاری طور پر غالب",
        },
    },
    {
        "country": {
            "ar": "لبنان",
            "en": "Lebanon",
            "fr": "Liban",
            "fa": "لبنان",
            "ms": "Lubnan",
            "ur": "لبنان",
        },
        "madhab": {
            "ar": "جعفري وشافعي وحنفي ومالكي وحنبلي",
            "en": "Ja'fari, Shafi'i, Hanafi, Maliki, and Hanbali",
            "fr": "Jaafarite, chaféite, hanafite, malikite et hanbalite",
            "fa": "جعفری، شافعی، حنفی، مالکی و حنبلی",
            "ms": "Jaafari, Syafie, Hanafi, Maliki dan Hanbali",
            "ur": "جعفری، شافعی، حنفی، مالکی اور حنبلی",
        },
        "note": {
            "ar": "تنوع قانوني ومذهبي",
            "en": "Legal and religious diversity",
            "fr": "Diversité juridique et religieuse",
            "fa": "تنوع قانونی و مذهبی",
            "ms": "Kepelbagaian undang-undang dan mazhab",
            "ur": "قانونی اور مذہبی تنوع",
        },
    },
    {
        "country": {
            "ar": "فلسطين",
            "en": "Palestine",
            "fr": "Palestine",
            "fa": "فلسطین",
            "ms": "Palestin",
            "ur": "فلسطین",
        },
        "madhab": {
            "ar": "شافعي وحنفي",
            "en": "Shafi'i and Hanafi",
            "fr": "Chaféite et hanafite",
            "fa": "شافعی و حنفی",
            "ms": "Syafie dan Hanafi",
            "ur": "شافعی اور حنفی",
        },
        "note": {
            "ar": "تنوع تاريخي",
            "en": "Historical diversity",
            "fr": "Diversité historique",
            "fa": "تنوع تاریخی",
            "ms": "Kepelbagaian sejarah",
            "ur": "تاریخی تنوع",
        },
    },
    {
        "country": {
            "ar": "تشاد",
            "en": "Chad",
            "fr": "Tchad",
            "fa": "چاد",
            "ms": "Chad",
            "ur": "چاڈ",
        },
        "madhab": {
            "ar": "مالكي وشافعي",
            "en": "Maliki and Shafi'i",
            "fr": "Malikite et chaféite",
            "fa": "مالکی و شافعی",
            "ms": "Maliki dan Syafie",
            "ur": "مالکی اور شافعی",
        },
        "note": {
            "ar": "يختلف بحسب المناطق",
            "en": "Varies by region",
            "fr": "Varie selon les régions",
            "fa": "بر اساس مناطق متفاوت است",
            "ms": "Berbeza mengikut wilayah",
            "ur": "علاقوں کے لحاظ سے مختلف",
        },
    },
    {
        "country": {
            "ar": "نيجيريا",
            "en": "Nigeria",
            "fr": "Nigéria",
            "fa": "نیجریه",
            "ms": "Nigeria",
            "ur": "نائجیریا",
        },
        "madhab": {
            "ar": "مالكي",
            "en": "Maliki",
            "fr": "Malikite",
            "fa": "مالکی",
            "ms": "Maliki",
            "ur": "مالکی",
        },
        "note": {
            "ar": "الغالب في مناطق واسعة",
            "en": "Predominant in broad regions",
            "fr": "Dominant dans de vastes régions",
            "fa": "غالب در مناطق گسترده",
            "ms": "Dominan di kawasan luas",
            "ur": "وسیع علاقوں میں غالب",
        },
    },
    {
        "country": {
            "ar": "الصومال",
            "en": "Somalia",
            "fr": "Somalie",
            "fa": "سومالی",
            "ms": "Somalia",
            "ur": "صومالیہ",
        },
        "madhab": {
            "ar": "شافعي",
            "en": "Shafi'i",
            "fr": "Chaféite",
            "fa": "شافعی",
            "ms": "Syafie",
            "ur": "شافعی",
        },
        "note": {
            "ar": "الغالب تاريخيًا",
            "en": "Historically predominant",
            "fr": "Historiquement dominant",
            "fa": "غالب تاریخی",
            "ms": "Dominan secara sejarah",
            "ur": "تاریخی طور پر غالب",
        },
    },
    {
        "country": {
            "ar": "جيبوتي",
            "en": "Djibouti",
            "fr": "Djibouti",
            "fa": "جیبوتی",
            "ms": "Djibouti",
            "ur": "جبوتی",
        },
        "madhab": {
            "ar": "شافعي",
            "en": "Shafi'i",
            "fr": "Chaféite",
            "fa": "شافعی",
            "ms": "Syafie",
            "ur": "شافعی",
        },
        "note": {
            "ar": "الغالب تاريخيًا",
            "en": "Historically predominant",
            "fr": "Historiquement dominant",
            "fa": "غالب تاریخی",
            "ms": "Dominan secara sejarah",
            "ur": "تاریخی طور پر غالب",
        },
    },
    {
        "country": {
            "ar": "السعودية",
            "en": "Saudi Arabia",
            "fr": "Arabie saoudite",
            "fa": "عربستان سعودی",
            "ms": "Arab Saudi",
            "ur": "سعودی عرب",
        },
        "madhab": {
            "ar": "حنبلي",
            "en": "Hanbali",
            "fr": "Hanbalite",
            "fa": "حنبلی",
            "ms": "Hanbali",
            "ur": "حنبلی",
        },
        "note": {
            "ar": "مع تنوع فقهي اجتماعي",
            "en": "With social juristic diversity",
            "fr": "Avec une diversité juridique sociale",
            "fa": "با تنوع فقهی اجتماعی",
            "ms": "Dengan kepelbagaian fiqh sosial",
            "ur": "سماجی فقہی تنوع کے ساتھ",
        },
    },
    {
        "country": {
            "ar": "مصر",
            "en": "Egypt",
            "fr": "Égypte",
            "fa": "مصر",
            "ms": "Mesir",
            "ur": "مصر",
        },
        "madhab": {
            "ar": "تنوع فقهي",
            "en": "Juristic diversity",
            "fr": "Diversité juridique",
            "fa": "تنوع فقهی",
            "ms": "Kepelbagaian fiqh",
            "ur": "فقہی تنوع",
        },
        "note": {
            "ar": "حضور مدارس متعددة",
            "en": "Several schools are represented",
            "fr": "Plusieurs écoles sont représentées",
            "fa": "حضور مذاهب متعدد",
            "ms": "Beberapa mazhab diwakili",
            "ur": "متعدد مسالک کا وجود",
        },
    },
    {
        "country": {
            "ar": "اليمن",
            "en": "Yemen",
            "fr": "Yémen",
            "fa": "یمن",
            "ms": "Yaman",
            "ur": "یمن",
        },
        "madhab": {
            "ar": "شافعي وزيدي",
            "en": "Shafi'i and Zaidi",
            "fr": "Chaféite et zaydite",
            "fa": "شافعی و زیدی",
            "ms": "Syafie dan Zaidi",
            "ur": "شافعی اور زیدی",
        },
        "note": {
            "ar": "يختلف بحسب المناطق",
            "en": "Varies by region",
            "fr": "Varie selon les régions",
            "fa": "بر اساس مناطق متفاوت است",
            "ms": "Berbeza mengikut wilayah",
            "ur": "علاقوں کے لحاظ سے مختلف",
        },
    },
    {
        "country": {
            "ar": "تركيا",
            "en": "Turkey",
            "fr": "Turquie",
            "fa": "ترکیه",
            "ms": "Turki",
            "ur": "ترکی",
        },
        "madhab": {
            "ar": "حنفي",
            "en": "Hanafi",
            "fr": "Hanafite",
            "fa": "حنفی",
            "ms": "Hanafi",
            "ur": "حنفی",
        },
        "note": {
            "ar": "الغالب تاريخيًا بين السنة",
            "en": "Historically predominant among Sunnis",
            "fr": "Historiquement dominant chez les sunnites",
            "fa": "غالب تاریخی میان اهل سنت",
            "ms": "Dominan secara sejarah dalam kalangan Sunni",
            "ur": "اہل سنت میں تاریخی طور پر غالب",
        },
    },
]


# ============================================================
# النماذج
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
# أدوات مساعدة
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
        r"[\u064B-\u065F\u0670]",
        "",
        text,
    )

    text = re.sub(
        r"[^\w\s]",
        " ",
        text,
    )

    text = re.sub(
        r"\s+",
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
# قاعدة البيانات
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
# خدمة Gemini
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
  "needs_reference_search": true,
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
                "keywords": [
                    str(item).strip()
                    for item in data.get(
                        "keywords",
                        [],
                    )
                    if str(item).strip()
                ],
                "needs_reference_search": bool(
                    data.get(
                        "needs_reference_search",
                        True,
                    )
                ),
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

        output_format = "\n".join(
            f"{MADHHAB_NAMES[code]['ar']}: "
            "اكتب الإجابة هنا"
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

    def answer_from_references(
        self,
        question: str,
        madhabs: List[str],
        level: str,
        chunks: List[Dict[str, Any]],
    ) -> Optional[Dict[str, str]]:
        if not self.available or not chunks:
            return None

        newline = chr(10)
        double_newline = newline + newline

        context = double_newline.join(
            f"[{index}] {chunk['source_title']}"
            f"{newline}{chunk['chunk_text']}"
            for index, chunk in enumerate(
                chunks,
                start=1,
            )
        )

        detail = {
            "very_short": "كلمة أو كلمتين",
            "short": "سطر واحد",
            "full": "فقرة قصيرة",
        }.get(
            level,
            "سطر واحد",
        )

        labels = "\n".join(
            f"{MADHHAB_NAMES[code]['ar']}: "
            "اكتب الإجابة هنا"
            for code in madhabs
        )

        prompt = f"""
أنت مساعد بحثي في الفقه الإسلامي، ولست مفتيًا.

السؤال:
{question}

المراجع:
{context}

التعليمات:
- استخدم المراجع فقط.
- لا تضف معلومات غير موجودة فيها.
- اذكر رقم المرجع مثل [1].
- مستوى التفصيل: {detail}.
- اكتب بالعربية.
- لا تستخدم JSON.
- استخدم هذا الشكل:

{labels}
"""

        raw = self.generate(
            prompt,
            json_mode=False,
        )

        if not raw:
            return None

        answers = self.parse_text_answers(
            raw,
            madhabs,
        )

        return answers or None


# ============================================================
# إدارة المراجع
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
            r"\s+",
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
# البحث
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
# خدمات Streamlit
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
    text_align = meta["text_align"]

    st.markdown(
        f"""
        <style>
        :root {{
            --page-direction: {direction};
            --page-align: {text_align};
        }}

        [data-testid="stAppViewContainer"] {{
            background: #f8fafc;
        }}

        [data-testid="stAppViewContainer"] .main {{
            direction: {direction};
            text-align: {text_align};
        }}

        [data-testid="stSidebar"] {{
            direction: {direction};
            text-align: {text_align};
        }}

        [data-testid="stSidebar"] * {{
            text-align: {text_align};
        }}

        [data-testid="stHeader"] {{
            direction: {direction};
        }}

        .app-header {{
            direction: {direction};
            display: flex;
            align-items: center;
            justify-content: center;
            text-align: center;
            gap: 1rem;
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

        div[data-testid="stHorizontalBlock"] button {{
            border-radius: 999px;
            min-height: 2.3rem;
        }}

        div[data-baseweb="tag"] {{
            margin: 3px !important;
            padding: 4px 8px !important;
            border-radius: 999px !important;
            background: #dbeafe !important;
            color: #1e3a8a !important;
        }}

        .result-card {{
            direction: {direction};
            text-align: {text_align};
            padding: 1rem;
            margin: .7rem 0;
            border: 1px solid #e2e8f0;
            border-radius: 1rem;
            background: white;
            box-shadow: 0 4px 12px
                rgba(15, 23, 42, .05);
        }}

        .muted {{
            color: #64748b;
            font-size: .88rem;
        }}

        div[data-testid="stExpander"] {{
            direction: {direction};
            text-align: {text_align};
        }}

        div[data-testid="stExpander"] summary {{
            direction: {direction};
            text-align: {text_align};
        }}

        textarea, input {{
            direction: {direction} !important;
            text-align: {text_align} !important;
        }}

        [data-baseweb="select"] {{
            direction: {direction};
            text-align: {text_align};
        }}

        [data-baseweb="popover"] {{
            direction: {direction};
            text-align: {text_align};
        }}

        .section-title {{
            direction: {direction};
            text-align: {text_align};
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
    lang: str,
    text: Dict[str, str],
):
    with st.expander(
        text["glossary"],
        expanded=False,
    ):
        st.info(
            text["warning_terms"]
        )

        for data in GLOSSARY.values():
            label = data["label"].get(
                lang,
                data["label"]["ar"],
            )

            with st.expander(
                label,
                expanded=False,
            ):
                definition = data["definition"].get(
                    lang,
                    data["definition"]["ar"],
                )

                example = data["example"].get(
                    lang,
                    data["example"]["ar"],
                )

                st.markdown(
                    f"**{text['definition']}:** "
                    f"{definition}"
                )

                st.markdown(
                    f"**{text['example']}:** "
                    f"{example}"
                )


def render_countries(
    lang: str,
    text: Dict[str, str],
):
    with st.expander(
        text["countries"],
        expanded=False,
    ):
        st.caption(
            text["country_note"]
        )

        for item in COUNTRIES:
            country = item["country"].get(
                lang,
                item["country"]["ar"],
            )

            madhab = item["madhab"].get(
                lang,
                item["madhab"]["ar"],
            )

            note = item["note"].get(
                lang,
                item["note"]["ar"],
            )

            with st.expander(
                country,
                expanded=False,
            ):
                st.write(madhab)
                st.caption(note)


def render_rules(
    lang: str,
    text: Dict[str, str],
):
    with st.expander(
        text["rules"],
        expanded=False,
    ):
        for rule in FIQH_RULES:
            title = rule["title"].get(
                lang,
                rule["title"]["ar"],
            )

            with st.expander(
                title,
                expanded=False,
            ):
                definition = rule["definition"].get(
                    lang,
                    rule["definition"]["ar"],
                )

                example = rule["example"].get(
                    lang,
                    rule["example"]["ar"],
                )

                st.markdown(
                    f"**{text['definition']}:** "
                    f"{definition}"
                )

                st.markdown(
                    f"**{text['example']}:** "
                    f"{example}"
                )


def render_comments(
    lang: str,
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


def render_gemini_test(
    ai: AIService,
    text: Dict[str, str],
):
    with st.expander(
        text["test_gemini"],
        expanded=False,
    ):
        if not ai.available:
            st.warning(
                text["ai_status_off"]
            )
            return

        if st.button(
            text["test_gemini"],
            key="test_gemini_button",
        ):
            response = ai.generate(
                "Reply with exactly: GEMINI_OK",
                json_mode=False,
            )

            if response:
                st.success(
                    text["test_success"].format(
                        response
                    )
                )
            else:
                st.error(
                    text["test_failed"]
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
        with st.spinner(
            text["ai_generating"]
        ):
            answers = ai.answer_from_references(
                question=question,
                madhabs=madhabs,
                level=level,
                chunks=chunks,
            )

        if answers:
            st.warning(
                text["ai_disclaimer"]
            )

            source_names = sorted({
                chunk["source_title"]
                for chunk in chunks
            })

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
# التشغيل الرئيسي
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
                text["ai_status_on"]
            )
        else:
            st.warning(
                text["ai_status_off"]
            )

    st.markdown(
        f'<div class="section-title">'
        f"<h2>{text['write_question']}</h2>"
        f"</div>",
        unsafe_allow_html=True,
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

    render_glossary(
        lang,
        text,
    )

    render_countries(
        lang,
        text,
    )

    render_rules(
        lang,
        text,
    )

    render_comments(
        lang,
        text,
    )

    render_reference_admin(
        db=db,
        ai=ai,
        references=references,
        lang=lang,
        text=text,
    )

    render_gemini_test(
        ai,
        text,
    )


if __name__ == "__main__":
    main()
