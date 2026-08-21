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
from typing import Any, Dict, List, Optional

import numpy as np
import streamlit as st


st.set_page_config(
    page_title="SmartFiqh",
    page_icon="📚",
    layout="wide",
)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

DB_PATH = os.getenv("FIQH_DB_PATH", "fiqh.db")
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")
EMBED_MODEL = os.getenv("EMBED_MODEL", "gemini-embedding-001")


try:
    from google import genai
    from google.genai import types

    GENAI_AVAILABLE = True
except ImportError:
    genai = None
    types = None
    GENAI_AVAILABLE = False


def get_secret(name: str, default: str = "") -> str:
    try:
        value = st.secrets.get(name)
        if value:
            return str(value)
    except Exception:
        pass

    return os.getenv(name, default)


GEMINI_API_KEY = get_secret("GEMINI_API_KEY")
ADMIN_PASSWORD = get_secret("ADMIN_PASSWORD")

USE_GEMINI = bool(GEMINI_API_KEY and GENAI_AVAILABLE)

gemini_client = None

if USE_GEMINI:
    try:
        gemini_client = genai.Client(api_key=GEMINI_API_KEY)
    except Exception:
        USE_GEMINI = False
        logger.exception("Gemini initialization failed")


LANGS = {
    "ar": ("العربية", "🇪🇬", "rtl"),
    "en": ("English", "🇬🇧", "ltr"),
    "fr": ("Français", "🇫🇷", "ltr"),
    "fa": ("فارسی", "🇮🇷", "rtl"),
    "ms": ("Melayu", "🇲🇾", "ltr"),
    "ur": ("اردو", "🇵🇰", "rtl"),
}


UI = {
    "ar": {
        "title": "الجامع المختصر لآراء المذاهب",
        "subtitle": "منصة تعليمية للمقارنة الفقهية، وليست موقعًا للإفتاء.",
        "madhabs": "اختر مذهبًا واحدًا أو أكثر",
        "topic": "اختر الموضوع",
        "all": "كل الموضوعات",
        "level": "مستوى التفصيل",
        "very_short": "مختصرة جدًا",
        "short": "مختصرة",
        "full": "مفصلة",
        "question": "اكتب سؤالك",
        "placeholder": "مثال: ما حكم صلاة الجماعة؟",
        "search": "🔍 ابحث عن الإجابة",
        "no_question": "الرجاء كتابة السؤال أولًا.",
        "no_madhab": "الرجاء اختيار مذهب واحد على الأقل.",
        "no_result": "لم توجد نتيجة قابلة للعرض.",
        "loading": "جاري تحليل السؤال...",
        "ai_on": "Gemini AI: مفعّل",
        "ai_off": "Gemini AI: غير مفعّل",
        "ai_note": "هذه إجابة بحثية آلية وليست فتوى.",
        "glossary": "📚 المصطلحات الفقهية",
        "countries": "🗺️ الدول والمذاهب الغالبة",
        "sources": "📜 مصادر التشريع الفقهي",
        "rules": "📘 الأصول والقواعد الفقهية",
        "comments": "💬 ملاحظات الجلسة",
        "references": "📁 إدارة المراجع — للمشرفين",
        "definition": "التعريف",
        "example": "مثال",
        "admin_password": "كلمة مرور المشرف",
        "access_denied": "لا تملك الصلاحية.",
        "comment": "اكتب ملاحظتك",
        "rating": "تقييم الإجابة",
        "send": "إرسال",
        "saved": "تم حفظ الملاحظة.",
        "source_title": "عنوان المصدر",
        "source_madhab": "المذهب",
        "source_text": "نص المرجع",
        "add": "إضافة المرجع",
        "added": "تمت إضافة {} مقاطع.",
    },
    "en": {
        "title": "The Concise Compendium of Madhhab Opinions",
        "subtitle": "An educational fiqh comparison platform, not a fatwa service.",
        "madhabs": "Choose one or more schools",
        "topic": "Choose a topic",
        "all": "All topics",
        "level": "Answer detail",
        "very_short": "Very short",
        "short": "Short",
        "full": "Detailed",
        "question": "Write your question",
        "placeholder": "Example: What is the ruling on congregational prayer?",
        "search": "🔍 Search",
        "no_question": "Please enter a question first.",
        "no_madhab": "Please choose at least one school.",
        "no_result": "No usable result was found.",
        "loading": "Analyzing the question...",
        "ai_on": "Gemini AI: enabled",
        "ai_off": "Gemini AI: disabled",
        "ai_note": "This is an automated research answer, not a fatwa.",
        "glossary": "📚 Fiqh terminology",
        "countries": "🗺️ Countries and prevailing schools",
        "sources": "📜 Sources of Islamic jurisprudence",
        "rules": "📘 Fiqh principles and legal maxims",
        "comments": "💬 Session notes",
        "references": "📁 Reference management — admins",
        "definition": "Definition",
        "example": "Example",
        "admin_password": "Admin password",
        "access_denied": "Access denied.",
        "comment": "Write your note",
        "rating": "Rate the answer",
        "send": "Submit",
        "saved": "The note was saved.",
        "source_title": "Source title",
        "source_madhab": "Madhhab",
        "source_text": "Reference text",
        "add": "Add reference",
        "added": "{} chunks were added.",
    },
    "fr": {
        "title": "Recueil concis des avis des écoles juridiques",
        "subtitle": "Plateforme éducative de comparaison du fiqh.",
        "madhabs": "Choisissez une ou plusieurs écoles",
        "topic": "Choisir le sujet",
        "all": "Tous les sujets",
        "level": "Niveau de détail",
        "very_short": "Très bref",
        "short": "Bref",
        "full": "Détaillé",
        "question": "Écrivez votre question",
        "placeholder": "Exemple : Quel est le statut de la prière en congrégation ?",
        "search": "🔍 Rechercher",
        "no_question": "Veuillez écrire une question.",
        "no_madhab": "Veuillez choisir une école.",
        "no_result": "Aucun résultat utilisable.",
        "loading": "Analyse en cours...",
        "ai_on": "Gemini AI : activé",
        "ai_off": "Gemini AI : désactivé",
        "ai_note": "Ceci est une réponse de recherche, pas une fatwa.",
        "glossary": "📚 Terminologie du fiqh",
        "countries": "🗺️ Pays et écoles dominantes",
        "sources": "📜 Sources de la jurisprudence islamique",
        "rules": "📘 Principes et maximes du fiqh",
        "comments": "💬 Notes de session",
        "references": "📁 Gestion des références",
        "definition": "Définition",
        "example": "Exemple",
        "admin_password": "Mot de passe admin",
        "access_denied": "Accès refusé.",
        "comment": "Votre note",
        "rating": "Évaluation",
        "send": "Envoyer",
        "saved": "Note enregistrée.",
        "source_title": "Titre de la source",
        "source_madhab": "École",
        "source_text": "Texte de référence",
        "add": "Ajouter",
        "added": "{} segments ajoutés.",
    },
}


for code in ("fa", "ms", "ur"):
    UI[code] = UI["en"].copy()


UI["fa"].update({
    "title": "مجموعه مختصر دیدگاه‌های مذاهب فقهی",
    "subtitle": "سامانه‌ای آموزشی برای مقایسه دیدگاه‌های فقهی.",
    "madhabs": "یک یا چند مذهب را انتخاب کنید",
    "topic": "موضوع را انتخاب کنید",
    "all": "همه موضوعات",
    "level": "سطح جزئیات",
    "very_short": "بسیار کوتاه",
    "short": "کوتاه",
    "full": "کامل",
    "question": "پرسش خود را بنویسید",
    "placeholder": "مثال: حکم نماز جماعت چیست؟",
    "search": "🔍 جست‌وجو",
    "no_question": "لطفاً پرسش را بنویسید.",
    "no_madhab": "لطفاً یک مذهب را انتخاب کنید.",
    "no_result": "نتیجه‌ای پیدا نشد.",
    "loading": "در حال تحلیل پرسش...",
    "ai_on": "Gemini AI: فعال",
    "ai_off": "Gemini AI: غیرفعال",
    "glossary": "📚 اصطلاحات فقهی",
    "countries": "🗺️ کشورها و مذاهب رایج",
    "sources": "📜 منابع فقه اسلامی",
    "rules": "📘 اصول و قواعد فقهی",
    "comments": "💬 یادداشت‌های جلسه",
    "references": "📁 مدیریت منابع",
    "definition": "تعریف",
    "example": "مثال",
})

UI["ms"].update({
    "title": "Himpunan Ringkas Pandangan Mazhab",
    "subtitle": "Platform pendidikan untuk perbandingan pandangan fiqh.",
    "madhabs": "Pilih satu atau lebih mazhab",
    "topic": "Pilih topik",
    "all": "Semua topik",
    "level": "Tahap perincian",
    "very_short": "Sangat ringkas",
    "short": "Ringkas",
    "full": "Terperinci",
    "question": "Tulis soalan anda",
    "placeholder": "Contoh: Apakah hukum solat berjemaah?",
    "search": "🔍 Cari",
    "no_question": "Sila tulis soalan.",
    "no_madhab": "Sila pilih mazhab.",
    "no_result": "Tiada hasil yang sesuai.",
    "loading": "Menganalisis soalan...",
    "ai_on": "Gemini AI: diaktifkan",
    "ai_off": "Gemini AI: dinyahaktifkan",
    "glossary": "📚 Istilah fiqh",
    "countries": "🗺️ Negara dan mazhab utama",
    "sources": "📜 Sumber fiqh Islam",
    "rules": "📘 Prinsip dan kaedah fiqh",
    "comments": "💬 Nota sesi",
    "references": "📁 Pengurusan rujukan",
    "definition": "Takrif",
    "example": "Contoh",
})

UI["ur"].update({
    "title": "مذاہب فقہ کے مختصر آراء کا مجموعہ",
    "subtitle": "فقہی آراء کے تقابلی مطالعے کا تعلیمی پلیٹ فارم۔",
    "madhabs": "ایک یا زیادہ مسالک منتخب کریں",
    "topic": "موضوع منتخب کریں",
    "all": "تمام موضوعات",
    "level": "تفصیل کی سطح",
    "very_short": "نہایت مختصر",
    "short": "مختصر",
    "full": "تفصیلی",
    "question": "اپنا سوال لکھیں",
    "placeholder": "مثال: نماز باجماعت کا کیا حکم ہے؟",
    "search": "🔍 تلاش",
    "no_question": "براہ کرم سوال لکھیں۔",
    "no_madhab": "براہ کرم مسلک منتخب کریں۔",
    "no_result": "مناسب نتیجہ نہیں ملا۔",
    "loading": "سوال کا تجزیہ جاری ہے...",
    "ai_on": "Gemini AI: فعال",
    "ai_off": "Gemini AI: غیر فعال",
    "glossary": "📚 فقہی اصطلاحات",
    "countries": "🗺️ ممالک اور غالب مسالک",
    "sources": "📜 فقہی مصادرِ تشریع",
    "rules": "📘 فقہی اصول و قواعد",
    "comments": "💬 نشست کے نوٹس",
    "references": "📁 مراجع کا انتظام",
    "definition": "تعریف",
    "example": "مثال",
})


MADHABS = {
    "maliki": ("مالكي", "Maliki"),
    "shafii": ("شافعي", "Shafi'i"),
    "hanafi": ("حنفي", "Hanafi"),
    "hanbali": ("حنبلي", "Hanbali"),
    "zahiri": ("ظاهري", "Zahiri"),
    "jafari": ("جعفري", "Ja'fari"),
    "zaidi": ("زيدي", "Zaidi"),
    "ibadi": ("إباضي", "Ibadi"),
}

TOPICS = {
    "ibadat": ("العبادات", "Worship"),
    "muamalat": ("المعاملات", "Transactions"),
    "family": ("الأسرة", "Family"),
    "other": ("مواضيع أخرى", "Other topics"),
}


ISSUES = [
    {
        "topic": "ibadat",
        "title": "صلاة الجماعة",
        "keywords": "جماعة مسجد صلاة رجال فرض واجب سنة congregation prayer",
        "rulings": {
            "maliki": "فرض كفاية في الجملة.",
            "shafii": "فرض كفاية في الجملة.",
            "hanafi": "واجبة على القادر بلا عذر.",
            "hanbali": "فرض عين على القادر.",
            "zahiri": "فرض عين بظاهر الأمر.",
            "jafari": "مستحب مؤكد.",
            "zaidi": "فرض كفاية.",
            "ibadi": "سنة مؤكدة.",
        },
    },
    {
        "topic": "ibadat",
        "title": "العمرة",
        "keywords": (
            "عمرة العمرة عمره umrah umra omrah "
            "ihram tawaf sai pilgrimage"
        ),
        "rulings": {
            code: "تحتاج إلى تفصيل بحسب المذهب وشروط المسألة."
            for code in MADHABS
        },
    },
    {
        "topic": "ibadat",
        "title": "الوضوء",
        "keywords": "وضوء وضو طهارة صلاة حدث wudu ablution",
        "rulings": {
            code: "الوضوء شرط للصلاة عند وجود الحدث الأصغر."
            for code in MADHABS
        },
    },
    {
        "topic": "ibadat",
        "title": "صيام رمضان",
        "keywords": "صيام صوم رمضان فطر fasting ramadan",
        "rulings": {
            code: "صيام رمضان واجب على المسلم المكلف القادر."
            for code in MADHABS
        },
    },
    {
        "topic": "muamalat",
        "title": "البيع بالتقسيط",
        "keywords": "بيع تقسيط ثمن أجل دين sale installment",
        "rulings": {
            code: "يجوز عند ضبط الثمن والأجل وانتفاء الربا والغرر."
            for code in MADHABS
        },
    },
    {
        "topic": "muamalat",
        "title": "الربا",
        "keywords": "ربا فائدة قرض مال زيادة riba interest loan",
        "rulings": {
            code: "الربا محرم في الجملة، وتفصيل الصور يحتاج إلى دراسة العقد."
            for code in MADHABS
        },
    },
]


COUNTRIES = [
    ("🇪🇬", "مصر", "Egypt", "تنوع فقهي", "Juristic diversity", "نحو 120 مليون", "About 120 million"),
    ("🇲🇦", "المغرب", "Morocco", "مالكي", "Maliki", "نحو 38 مليون", "About 38 million"),
    ("🇸🇩", "السودان", "Sudan", "مالكي", "Maliki", "نحو 51 مليون", "About 51 million"),
    ("🇩زاد", "الجزائر", "Algeria", "مالكي", "Maliki", "نحو 47 مليون", "About 47 million"),
    ("🇹🇳", "تونس", "Tunisia", "مالكي", "Maliki", "نحو 12 مليون", "About 12 million"),
    ("🇸🇦", "السعودية", "Saudi Arabia", "حنبلي", "Hanbali", "نحو 35 مليون", "About 35 million"),
    ("🇹🇷", "تركيا", "Turkey", "حنفي", "Hanafi", "نحو 86 مليون", "About 86 million"),
    ("🇵🇰", "باكستان", "Pakistan", "حنفي", "Hanafi", "نحو 259 مليون", "About 259 million"),
    ("🇦🇫", "أفغانستان", "Afghanistan", "حنفي", "Hanafi", "نحو 44 مليون", "About 44 million"),
    ("🇮🇩", "إندونيسيا", "Indonesia", "شافعي", "Shafi'i", "نحو 288 مليون", "About 288 million"),
    ("🇲🇾", "ماليزيا", "Malaysia", "شافعي", "Shafi'i", "نحو 36 مليون", "About 36 million"),
    ("🇸🇴", "الصومال", "Somalia", "شافعي", "Shafi'i", "نحو 20 مليون", "About 20 million"),
    ("🇩🇯", "جيبوتي", "Djibouti", "شافعي", "Shafi'i", "نحو 1.2 مليون", "About 1.2 million"),
    ("🇮🇷", "إيران", "Iran", "جعفري", "Ja'fari", "نحو 93 مليون", "About 93 million"),
    ("🇴🇲", "عُمان", "Oman", "إباضي", "Ibadi", "نحو 5.5 مليون", "About 5.5 million"),
    ("🇱🇧", "لبنان", "Lebanon", "جعفري", "Ja'fari", "نحو 5.8 مليون", "About 5.8 million"),
    ("🇳🇬", "نيجيريا", "Nigeria", "مالكي", "Maliki", "نحو 242 مليون", "About 242 million"),
    ("🇹🇩", "تشاد", "Chad", "مالكي", "Maliki", "نحو 21 مليون", "About 21 million"),
    ("🇾🇪", "اليمن", "Yemen", "شافعي", "Shafi'i", "نحو 43 مليون", "About 43 million"),
]


LEGAL_SOURCES = [
    (
        "القرآن الكريم",
        "The Qur'an",
        "المصدر الأعلى والأصل الأول للتشريع الإسلامي.",
        "The highest and primary source of Islamic law.",
    ),
    (
        "السنة النبوية",
        "Prophetic Sunnah",
        "أقوال النبي ﷺ وأفعاله وتقريراته، وهي مبينة للقرآن.",
        "The Prophet's sayings, actions, and approvals explaining the Qur'an.",
    ),
    (
        "الإجماع",
        "Ijma' — scholarly consensus",
        "اتفاق المجتهدين على حكم شرعي في مسألة.",
        "Agreement of qualified scholars on a legal ruling.",
    ),
    (
        "القياس",
        "Qiyas — analogical reasoning",
        "إلحاق مسألة جديدة بمسألة منصوص عليها لعلة مشتركة.",
        "Applying a known ruling to a new case because of a shared cause.",
    ),
    (
        "الاجتهاد",
        "Ijtihad — qualified legal reasoning",
        "استفراغ الفقيه وسعه لاستنباط الحكم الشرعي.",
        "A qualified jurist's effort to derive a legal ruling.",
    ),
    (
        "العرف",
        "Custom — 'Urf",
        "ما اعتاده الناس مما لا يخالف نصًا أو أصلًا شرعيًا.",
        "A prevailing practice that does not conflict with Islamic law.",
    ),
]


GLOSSARY = [
    ("الحلال", "Halal", "ما أذن الشرع في فعله.", "What Islamic law permits."),
    ("المباح", "Permissible", "ما خيّر الشارع بين فعله وتركه.", "What is left to personal choice."),
    ("الحرام", "Haram", "ما طلب الشرع تركه طلبًا جازمًا.", "What Islamic law definitively prohibits."),
    ("المكروه", "Disliked", "ما طلب الشرع تركه دون إلزام.", "What is discouraged without strict prohibition."),
    ("الواجب", "Wajib", "ما طلب الشرع فعله طلبًا جازمًا.", "What Islamic law demands decisively."),
    ("الفرض", "Fard", "ما ثبت بدليل قطعي.", "An obligation established by definitive evidence."),
    ("فرض الكفاية", "Communal obligation", "واجب يسقط عن الباقين بقيام عدد كافٍ به.", "A communal obligation fulfilled by enough people."),
    ("المستحب", "Recommended", "ما يثاب فاعله ولا يعاقب تاركه.", "An act whose doer is rewarded."),
    ("المندوب", "Mandub", "ما رغب الشرع في فعله دون إلزام.", "An act encouraged without obligation."),
    ("السنة", "Sunnah", "ما نقل عن النبي ﷺ من قول أو فعل أو تقرير.", "A statement, action, or approval transmitted from the Prophet."),
    ("السنة المؤكدة", "Emphasized Sunnah", "سنة واظب عليها النبي ﷺ أو حث عليها.", "A sunnah consistently practiced or strongly encouraged."),
]


RULES = [
    (
        "الأمور بمقاصدها",
        "Actions are judged by intentions",
        "تعتبر المقاصد والنيات في فهم الأفعال.",
        "Intentions are considered when determining legal effects.",
    ),
    (
        "اليقين لا يزول بالشك",
        "Certainty is not removed by doubt",
        "الحكم الثابت بيقين لا يرفع بمجرد شك.",
        "An established certainty is not overturned by mere doubt.",
    ),
    (
        "المشقة تجلب التيسير",
        "Hardship brings facilitation",
        "المشقة غير المعتادة سبب للتخفيف الشرعي.",
        "Unusual hardship may justify a legal concession.",
    ),
    (
        "الضرر يزال",
        "Harm must be removed",
        "يجب رفع الضرر أو تقليله دون ضرر أكبر.",
        "Harm should be removed without causing greater harm.",
    ),
    (
        "العادة محكمة",
        "Custom is authoritative",
        "تعتبر العادة الصحيحة فيما لا تحديد فيه.",
        "Sound custom is considered where no specific rule exists.",
    ),
    (
        "الضرورات تبيح المحظورات",
        "Necessities permit prohibited matters",
        "الضرورة تبيح المحظور بقدر الحاجة.",
        "Necessity may permit a prohibited act only as needed.",
    ),
    (
        "الأصل في المعاملات الإباحة",
        "Transactions are presumed permissible",
        "الأصل في المعاملات الجديدة الجواز ما لم تتضمن محظورًا.",
        "New transactions are presumed permissible unless prohibited.",
    ),
]


@dataclass
class Issue:
    topic: str
    title: str
    keywords: str
    rulings: Dict[str, str]


def normalize(text: str) -> str:
    text = text.lower()

    for old, new in {
        "أ": "ا",
        "إ": "ا",
        "آ": "ا",
        "ى": "ي",
        "ة": "ه",
    }.items():
        text = text.replace(old, new)

    text = re.sub(r"[\u064B-\u065F\u0670]", "", text)
    text = re.sub(r"[^\w\s]", " ", text)
    return re.sub(r"\s+", " ", text).strip()


def timestamp() -> str:
    return dt.datetime.now(dt.timezone.utc).isoformat()


class Database:
    def __init__(self, path: str = DB_PATH):
        self.path = path
        self.setup()
        self.seed()

    def conn(self):
        connection = sqlite3.connect(
            self.path,
            timeout=30,
            check_same_thread=False,
        )
        connection.row_factory = sqlite3.Row
        return connection

    def setup(self):
        with self.conn() as db:
            db.execute("""
                CREATE TABLE IF NOT EXISTS issues (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    topic TEXT NOT NULL,
                    title TEXT NOT NULL UNIQUE,
                    keywords TEXT DEFAULT '',
                    rulings TEXT DEFAULT '{}'
                )
            """)

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

            db.execute("""
                CREATE TABLE IF NOT EXISTS feedback (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    comment TEXT,
                    rating INTEGER,
                    created_at TEXT NOT NULL
                )
            """)

            db.commit()

    def seed(self):
        with self.conn() as db:
            for item in ISSUES:
                db.execute(
                    """
                    INSERT OR IGNORE INTO issues
                    (topic, title, keywords, rulings)
                    VALUES (?, ?, ?, ?)
                    """,
                    (
                        item["topic"],
                        item["title"],
                        item["keywords"],
                        json.dumps(
                            item["rulings"],
                            ensure_ascii=False,
                        ),
                    ),
                )

            db.commit()

    def issues(
        self,
        topic: str = "all",
    ) -> List[Issue]:
        with self.conn() as db:
            if topic == "all":
                rows = db.execute(
                    "SELECT * FROM issues ORDER BY id"
                ).fetchall()
            else:
                rows = db.execute(
                    """
                    SELECT *
                    FROM issues
                    WHERE topic = ?
                    ORDER BY id
                    """,
                    (topic,),
                ).fetchall()

        return [
            Issue(
                topic=row["topic"],
                title=row["title"],
                keywords=row["keywords"],
                rulings=json.loads(row["rulings"]),
            )
            for row in rows
        ]

    def add_reference(
        self,
        title: str,
        madhab: str,
        text: str,
        embedding: List[float],
    ) -> bool:
        content_hash = hashlib.sha256(
            f"{title}|{madhab}|{text}".encode()
        ).hexdigest()

        with self.conn() as db:
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
                        title,
                        madhab,
                        text,
                        json.dumps(embedding),
                        content_hash,
                        timestamp(),
                    ),
                )

                db.commit()
                return True

            except sqlite3.IntegrityError:
                return False

    def reference_count(self) -> int:
        with self.conn() as db:
            return db.execute(
                """
                SELECT COUNT(*)
                FROM reference_chunks
                """
            ).fetchone()[0]

    def add_feedback(self, comment: str, rating: int):
        with self.conn() as db:
            db.execute(
                """
                INSERT INTO feedback (comment, rating, created_at)
                VALUES (?, ?, ?)
                """,
                (comment, rating, timestamp()),
            )
            db.commit()


class AI:
    def __init__(self):
        self.enabled = bool(USE_GEMINI and gemini_client)

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

            return (
                response.text.strip()
                if response.text
                else None
            )

        except Exception:
            logger.exception("Gemini generation failed")
            return None

    def answer(
        self,
        question: str,
        madhabs: List[str],
        level: str,
    ) -> Optional[Dict[str, str]]:
        if not self.enabled:
            return None

        detail = {
            "very_short": "one or two words",
            "short": "one line",
            "full": "three to five lines",
        }.get(level, "one line")

        newline = chr(10)

        labels = newline.join(
            f"{MADHABS[code][1]}: write the answer"
            for code in madhabs
        )

        prompt = f"""
You are an educational Islamic fiqh research assistant.
You are not issuing a personal fatwa.

Question:
{question}

Requested schools:
{", ".join(MADHABS[code][1] for code in madhabs)}

Detail level:
{detail}

Instructions:
- Answer the exact question.
- Mention meaningful disagreement.
- Do not invent sources.
- Use English for English questions and Arabic for Arabic questions.
- Do not use JSON.
- Do not add an introduction or conclusion.

Use exactly this format:
{labels}
"""

        raw = self.generate(prompt)

        if not raw:
            return None

        names = {}

        for code in madhabs:
            names[MADHABS[code][0]] = code
            names[MADHABS[code][1]] = code

        answers = {}
        current = None
        buffer = []

        for line in raw.splitlines():
            line = line.strip()

            if not line:
                continue

            found = None

            for name, code in names.items():
                if line.startswith(name + ":") or line.startswith(name + "："):
                    found = code
                    break

            if found:
                if current and buffer:
                    answers[current] = " ".join(buffer)

                current = found
                buffer = []

                if ":" in line:
                    buffer.append(line.split(":", 1)[1].strip())
                elif "：" in line:
                    buffer.append(line.split("：", 1)[1].strip())

            elif current:
                buffer.append(line)

        if current and buffer:
            answers[current] = " ".join(buffer)

        if answers:
            return answers

        if len(madhabs) == 1:
            return {madhabs[0]: raw}

        return None


class Search:
    def __init__(
        self,
        db: Database,
        ai: AI,
    ):
        self.db = db
        self.ai = ai
        self.cache = OrderedDict()

    def search(
        self,
        question: str,
        topic: str,
        madhabs: List[str],
    ):
        key = "|".join([
            question,
            topic,
            ",".join(madhabs),
        ])

        if key in self.cache:
            return self.cache[key]

        query = normalize(question)
        matches = []

        for issue in self.db.issues(topic):
            pool = normalize(
                " ".join([
                    issue.title,
                    issue.keywords,
                ])
            )

            score = sum(
                1
                for word in query.split()
                if len(word) > 2 and word in pool
            )

            if score:
                matches.append((score, issue))

        matches.sort(
            key=lambda item: item[0],
            reverse=True,
        )

        result = []

        for _, issue in matches[:5]:
            result.append({
                "title": issue.title,
                "topic": issue.topic,
                "cards": [
                    {
                        "code": code,
                        "answer": issue.rulings.get(
                            code,
                            "No detailed ruling available.",
                        ),
                    }
                    for code in madhabs
                ],
            })

        self.cache[key] = result

        while len(self.cache) > 200:
            self.cache.popitem(last=False)

        return result


def apply_css(lang: str):
    _, _, direction = LANGS[lang]
    align = "right" if direction == "rtl" else "left"

    st.markdown(
        f"""
        <style>
        [data-testid="stAppViewContainer"] .main,
        [data-testid="stSidebar"] {{
            direction: {direction};
            text-align: {align};
        }}

        [data-testid="stSidebar"] * {{
            text-align: {align};
        }}

        .header {{
            direction: {direction};
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
            direction: {direction} !important;
            text-align: {align} !important;
        }}

        div[data-testid="stExpander"] {{
            direction: {direction};
            text-align: {align};
        }}

        .card {{
            direction: {direction};
            text-align: {align};
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


def language_bar():
    if "lang" not in st.session_state:
        st.session_state.lang = "ar"

    columns = st.columns(len(LANGS))

    for column, code in zip(columns, LANGS):
        with column:
            label, flag, _ = LANGS[code]

            if st.button(
                f"{flag} {label}",
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


def render_search(
    db: Database,
    ai: AI,
    search: Search,
    madhabs: List[str],
    topic: str,
    level: str,
    lang: str,
    text: Dict[str, str],
):
    with st.form("question_form"):
        question = st.text_area(
            text["placeholder"],
            height=120,
        )

        submit = st.form_submit_button(
            text["search"],
            use_container_width=True,
        )

    if not submit:
        return

    if not question.strip():
        st.warning(text["no_question"])
        return

    if not madhabs:
        st.warning(text["no_madhab"])
        return

    with st.spinner(text["loading"]):
        results = search.search(
            question,
            topic,
            madhabs,
        )
        ai_answers = (
            ai.answer(question, madhabs, level)
            if ai.enabled
            else None
        )

    if ai_answers:
        st.info(text["ai_note"])
        st.markdown('<div class="card">', unsafe_allow_html=True)
        st.subheader(question)

        columns = st.columns(len(madhabs))
        for col, code in zip(columns, madhabs):
            with col:
                m_name = (
                    MADHABS[code][0]
                    if lang != "en"
                    else MADHABS[code][1]
                )
                st.markdown(f"**{m_name}**")
                st.write(
                    ai_answers.get(
                        code,
                        text["no_result"],
                    )
                )

        st.markdown("</div>", unsafe_allow_html=True)

    elif results:
        for result in results:
            topic_name = TOPICS[result["topic"]][
                0 if lang != "en" else 1
            ]

            st.markdown(
                '<div class="card">',
                unsafe_allow_html=True,
            )

            st.subheader(result["title"])
            st.caption(topic_name)

            columns = st.columns(len(result["cards"]))
            for col, card in zip(columns, result["cards"]):
                with col:
                    m_name = (
                        MADHABS[card["code"]][0]
                        if lang != "en"
                        else MADHABS[card["code"]][1]
                    )
                    st.markdown(f"**{m_name}**")
                    st.write(card["answer"])

            st.markdown("</div>", unsafe_allow_html=True)

    else:
        st.warning(text["no_result"])


def render_sidebar(
    db: Database,
    ai: AI,
    lang: str,
    text: Dict[str, str],
):
    with st.sidebar:
        st.subheader(text["madhabs"])
        selected_madhabs = []
        for code, (ar_name, en_name) in MADHABS.items():
            name = ar_name if lang != "en" else en_name
            if st.checkbox(name, value=(code in ("maliki", "shafii", "hanafi", "hanbali")), key=f"madhab_{code}"):
                selected_madhabs.append(code)

        st.divider()

        st.subheader(text["topic"])
        topic_options = {"all": text["all"]}
        for code, (ar_t, en_t) in TOPICS.items():
            topic_options[code] = ar_t if lang != "en" else en_t

        selected_topic = st.selectbox(
            text["topic"],
            options=list(topic_options.keys()),
            format_func=lambda x: topic_options[x],
            label_visibility="collapsed",
        )

        st.subheader(text["level"])
        level_options = {
            "very_short": text["very_short"],
            "short": text["short"],
            "full": text["full"],
        }
        selected_level = st.radio(
            text["level"],
            options=list(level_options.keys()),
            format_func=lambda x: level_options[x],
            label_visibility="collapsed",
        )

        st.divider()
        if ai.enabled:
            st.success(text["ai_on"])
        else:
            st.info(text["ai_off"])

    return selected_madhabs, selected_topic, selected_level


def render_auxiliary_tabs(
    db: Database,
    lang: str,
    text: Dict[str, str],
):
    tab1, tab2, tab3, tab4, tab5, tab6 = st.tabs([
        text["countries"],
        text["sources"],
        text["glossary"],
        text["rules"],
        text["comments"],
        text["references"],
    ])

    with tab1:
        for flag, ar_c, en_c, ar_m, en_m, ar_p, en_p in COUNTRIES:
            country = ar_c if lang != "en" else en_c
            madhab = ar_m if lang != "en" else en_m
            pop = ar_p if lang != "en" else en_p
            st.markdown(f"**{flag} {country}** — {madhab} ({pop})")

    with tab2:
        for ar_s, en_s, ar_d, en_d in LEGAL_SOURCES:
            src = ar_s if lang != "en" else en_s
            desc = ar_d if lang != "en" else en_d
            st.markdown(f"**{src}**: {desc}")

    with tab3:
        for ar_t, en_t, ar_d, en_d in GLOSSARY:
            term = ar_t if lang != "en" else en_t
            desc = ar_d if lang != "en" else en_d
            st.markdown(f"**{term}**: {desc}")

    with tab4:
        for ar_r, en_r, ar_d, en_d in RULES:
            rule = ar_r if lang != "en" else en_r
            desc = ar_d if lang != "en" else en_d
            st.markdown(f"**{rule}**: {desc}")

    with tab5:
        with st.form("feedback_form"):
            comment = st.text_area(text["comment"])
            rating = st.slider(text["rating"], 1, 5, 5)
            send = st.form_submit_button(text["send"])

            if send and comment.strip():
                db.add_feedback(comment, rating)
                st.success(text["saved"])

    with tab6:
        pwd = st.text_input(
            text["admin_password"], type="password"
        )
        if ADMIN_PASSWORD and pwd == ADMIN_PASSWORD:
            with st.form("ref_form"):
                ref_title = st.text_input(text["source_title"])
                ref_madhab = st.selectbox(
                    text["source_madhab"],
                    options=list(MADHABS.keys()),
                    format_func=lambda x: (
                        MADHABS[x][0]
                        if lang != "en"
                        else MADHABS[x][1]
                    ),
                )
                ref_text = st.text_area(text["source_text"])
                add_btn = st.form_submit_button(text["add"])

                if add_btn and ref_text.strip():
                    db.add_reference(
                        title=ref_title,
                        madhab=ref_madhab,
                        text=ref_text,
                        embedding=[0.0],
                    )
                    st.success(text["added"].format(1))
        elif pwd:
            st.error(text["access_denied"])


def main():
    db = Database()
    ai = AI()
    search = Search(db, ai)

    lang = language_bar()
    text = UI[lang]
    apply_css(lang)

    render_header(lang)

    madhabs, topic, level = render_sidebar(
        db, ai, lang, text
    )

    render_search(
        db, ai, search, madhabs, topic, level, lang, text
    )

    st.divider()

    render_auxiliary_tabs(db, lang, text)


if __name__ == "__main__":
    main()
