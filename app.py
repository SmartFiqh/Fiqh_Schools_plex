from __future__ import annotations

import csv
import datetime as dt
import hashlib
import io
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
# Page configuration
# ============================================================

st.set_page_config(
    page_title="الجامع المختصر لآراء المذاهب",
    page_icon="📚",
    layout="wide",
    initial_sidebar_state="expanded",
)


# ============================================================
# Logging and environment
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
        logger.info("Gemini initialized successfully")
    except Exception:
        USE_GEMINI = False
        logger.exception("Gemini initialization failed")


# ============================================================
# Language data
# ============================================================

LANGUAGE_META = {
    "ar": {
        "label": "العربية",
        "flag": "🇪🇬",
        "direction": "rtl",
    },
    "en": {
        "label": "English",
        "flag": "🇬🇧",
        "direction": "ltr",
    },
    "fr": {
        "label": "Français",
        "flag": "🇫🇷",
        "direction": "ltr",
    },
    "fa": {
        "label": "فارسی",
        "flag": "🇮🇷",
        "direction": "rtl",
    },
    "ms": {
        "label": "Melayu",
        "flag": "🇲🇾",
        "direction": "ltr",
    },
    "ur": {
        "label": "اردو",
        "flag": "🇵🇰",
        "direction": "rtl",
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
            "لم نجد نتيجة مناسبة في قاعدة البيانات "
            "أو المراجع المرفوعة."
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
        "reference_empty": "الرجاء إدخال نص أو رفع ملف.",
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
        "no_results": "No suitable result was found.",
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
        "reference_empty": "Enter text or upload a file.",
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
    },
    "fr": {
        "app_title": "Recueil concis des avis des écoles juridiques",
        "app_subtitle": (
            "Plateforme éducative de comparaison du fiqh. "
            "Ce service ne délivre pas de fatwas."
        ),
        "language": "Langue",
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
        "ai_disclaimer": "Ceci n’est pas une fatwa.",
        "rag_badge": "📖 Basé sur les références: {}",
        "reference_management": "📁 Gestion des références",
        "reference_intro": (
            "Ajoutez des textes dont vous avez les droits."
        ),
        "source_title": "Titre de la source",
        "source_madhab": "École concernée",
        "source_text": "Texte de référence",
        "source_file": "Ou fichier TXT",
        "add_reference": "Ajouter et indexer",
        "reference_empty": "Ajoutez un texte ou un fichier.",
        "reference_failed": "Échec de l’indexation.",
        "reference_success": "{} segments ajoutés de «{}».",
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
    },
}


# Fill untranslated UI languages safely
for language_code in ("fa", "ms", "ur"):
    UI[language_code] = UI["ar"].copy()


# ============================================================
# Madhhab and topic data
# ============================================================

MADHHAB_NAMES = {
    "maliki": {
        "ar": "مالكي",
        "en": "Maliki",
        "fr": "Malikite",
    },
    "shafii": {
        "ar": "شافعي",
        "en": "Shafi'i",
        "fr": "Chaféite",
    },
    "hanafi": {
        "ar": "حنفي",
        "en": "Hanafi",
        "fr": "Hanafite",
    },
    "hanbali": {
        "ar": "حنبلي",
        "en": "Hanbali",
        "fr": "Hanbalite",
    },
    "zahiri": {
        "ar": "ظاهري",
        "en": "Zahiri",
        "fr": "Zahirite",
    },
    "jafari": {
        "ar": "جعفري",
        "en": "Ja'fari",
        "fr": "Jaafarite",
    },
    "zaidi": {
        "ar": "زيدي",
        "en": "Zaidi",
        "fr": "Zaydite",
    },
    "ibadi": {
        "ar": "إباضي",
        "en": "Ibadi",
        "fr": "Ibadite",
    },
}


GROUPS = {
    "sunni": {
        "ar": "مذاهب السنة",
        "en": "Sunni schools",
        "fr": "Écoles sunnites",
        "members": [
            "maliki",
            "shafii",
            "hanafi",
            "hanbali",
            "zahiri",
        ],
    },
    "shia": {
        "ar": "مذاهب الشيعة",
        "en": "Shia schools",
        "fr": "Écoles chiites",
        "members": ["jafari", "zaidi"],
    },
    "ibadi": {
        "ar": "المذهب الإباضي",
        "en": "Ibadi school",
        "fr": "École ibadite",
        "members": ["ibadi"],
    },
}


TOPICS = {
    "ibadat": {
        "ar": "العبادات",
        "en": "Worship",
        "fr": "Actes d’adoration",
    },
    "muamalat": {
        "ar": "المعاملات",
        "en": "Transactions",
        "fr": "Transactions",
    },
    "family": {
        "ar": "الأسرة",
        "en": "Family",
        "fr": "Famille",
    },
    "other": {
        "ar": "مواضيع أخرى",
        "en": "Other",
        "fr": "Autres sujets",
    },
}


# ============================================================
# Fiqh glossary
# ============================================================

GLOSSARY = {
    "الحلال": {
        "definition": (
            "ما أذن الشرع في فعله، ولا يترتب على فعله إثم "
            "من حيث الأصل."
        ),
        "example": "الأكل من الطعام الطيب المباح.",
    },
    "المباح": {
        "definition": (
            "ما خيّر الشارع المكلّف بين فعله وتركه، "
            "فلا مدح ولا ذم لذاته."
        ),
        "example": "اختيار لون الثوب المباح.",
    },
    "الحرام": {
        "definition": (
            "ما طلب الشرع تركه طلبًا جازمًا، ويأثم المكلّف "
            "بفعله مع العلم والقصد."
        ),
        "example": "السرقة وأكل أموال الناس بالباطل.",
    },
    "المكروه": {
        "definition": (
            "ما طلب الشرع تركه لا على سبيل الإلزام؛ فتركه أفضل، "
            "وفعله لا يوجب الإثم في الأصل."
        ),
        "example": "فعل يكره في العبادة دون أن يبطلها.",
    },
    "الواجب": {
        "definition": (
            "ما طلب الشرع فعله طلبًا جازمًا، ويأثم المكلّف "
            "بتركه بلا عذر."
        ),
        "example": "أداء الصلاة المفروضة في وقتها.",
    },
    "الفرض": {
        "definition": (
            "ما ثبت طلبه بدليل قطعي عند الاصطلاح الذي يفرّق "
            "بين الفرض والواجب."
        ),
        "example": "وجوب الصلوات الخمس بدليل قطعي.",
    },
    "فرض الكفاية": {
        "definition": (
            "واجب إذا قام به عدد كافٍ سقط الإثم عن الباقين، "
            "وإذا تركه الجميع أثم القادرون."
        ),
        "example": "تجهيز الميت والصلاة عليه في الجملة.",
    },
    "المستحب": {
        "definition": (
            "ما طلب الشرع فعله طلبًا غير جازم؛ يثاب فاعله "
            "ولا يعاقب تاركه."
        ),
        "example": "صدقة التطوع.",
    },
    "المندوب": {
        "definition": (
            "ما رغب الشرع في فعله دون إلزام، وهو من ألفاظ "
            "الترغيب في الاصطلاح العام."
        ),
        "example": "صيام أيام نافلة.",
    },
    "السنة": {
        "definition": (
            "ما نقل عن النبي ﷺ من قول أو فعل أو تقرير، "
            "وقد يطلق فقهيًا على ما يثاب فاعله."
        ),
        "example": "بعض هيئات الصلاة وأذكارها.",
    },
    "السنة المؤكدة": {
        "definition": (
            "سنة واظب عليها النبي ﷺ أو حث عليها حثًا ظاهرًا، "
            "ويُلام عند بعض الفقهاء من يتركها دائمًا."
        ),
        "example": "صلاة الوتر عند من يعدّها سنة مؤكدة.",
    },
}


# ============================================================
# Fiqh principles and legal maxims
# ============================================================

FIQH_RULES = [
    {
        "title": "الأمور بمقاصدها",
        "definition": (
            "تعتبر المقاصد والنيات في فهم الأفعال وترتيب آثارها الشرعية."
        ),
        "example": "يختلف دفع المال باختلاف كونه صدقة أو قرضًا أو هبة.",
    },
    {
        "title": "اليقين لا يزول بالشك",
        "definition": (
            "الحكم الثابت بيقين لا يرفع بمجرد شك طارئ."
        ),
        "example": "من تيقن الطهارة وشك في الحدث يبقى على طهارته.",
    },
    {
        "title": "المشقة تجلب التيسير",
        "definition": (
            "المشقة غير المعتادة سبب معتبر للتخفيف الشرعي وفق ضوابطه."
        ),
        "example": "الفطر للمريض الذي يضره الصوم.",
    },
    {
        "title": "الضرر يزال",
        "definition": (
            "يجب رفع الضرر أو تقليله بقدر الإمكان دون إحداث ضرر أكبر."
        ),
        "example": "منع استعمال طريق يضر بالمارة.",
    },
    {
        "title": "العادة محكمة",
        "definition": (
            "تعتبر العادة الصحيحة فيما لم يرد فيه تحديد شرعي خاص."
        ),
        "example": "تحديد بعض صور النفقة بحسب عرف البلد.",
    },
    {
        "title": "الضرر لا يزال بالضرر",
        "definition": (
            "لا يجوز علاج ضرر بإحداث ضرر مساو أو أشد."
        ),
        "example": "لا يزال ضرر جار بإتلاف ملك جار آخر.",
    },
    {
        "title": "درء المفاسد مقدم على جلب المصالح",
        "definition": (
            "إذا تعارضت مفسدة ومصلحة معتبرتان قدم دفع المفسدة "
            "عند رجحانها."
        ),
        "example": "منع معاملة فيها ربح ويترتب عليها ظلم واضح.",
    },
    {
        "title": "الضرورات تبيح المحظورات",
        "definition": (
            "الضرورة المنضبطة قد تبيح المحظور بقدر دفع الضرر."
        ),
        "example": "تناول المحرم عند خوف الهلاك بقدر الحاجة.",
    },
    {
        "title": "الضرورة تقدر بقدرها",
        "definition": (
            "الرخصة الناتجة عن الضرورة لا تتجاوز مقدار الحاجة."
        ),
        "example": "لا يتوسع المضطر بعد زوال الخطر.",
    },
    {
        "title": "الأصل براءة الذمة",
        "definition": (
            "الأصل عدم شغل ذمة الشخص بحق أو التزام حتى يثبت الدليل."
        ),
        "example": "من ادعى دينًا فعليه إثباته.",
    },
    {
        "title": "الأصل في العبادات التوقيف",
        "definition": (
            "لا تشرع عبادة مخصوصة بصفة أو وقت أو عدد إلا بدليل معتبر."
        ),
        "example": "عدم تخصيص ذكر بعدد تعبدي بلا دليل.",
    },
    {
        "title": "الأصل في المعاملات الإباحة",
        "definition": (
            "الأصل في المعاملات الجديدة الجواز ما لم تتضمن محظورًا."
        ),
        "example": "جواز وسيلة بيع جديدة إذا خلت من الربا والغرر.",
    },
    {
        "title": "العبرة في العقود للمقاصد والمعاني",
        "definition": (
            "تعتبر حقيقة العقد وآثاره لا مجرد ألفاظه أو اسمه."
        ),
        "example": "لا يصبح القرض المحرم مباحًا بمجرد تغيير اسمه.",
    },
    {
        "title": "الخراج بالضمان",
        "definition": (
            "من تحمل ضمان الشيء وتبعاته استحق غلته في الجملة."
        ),
        "example": "استحقاق غلة المبيع لمن كان ضامنًا له.",
    },
    {
        "title": "الغنم بالغرم",
        "definition": (
            "استحقاق المنفعة يقابله تحمل التبعة والضمان."
        ),
        "example": "من يستحق ربح الاستثمار يتحمل مخاطر الاستثمار.",
    },
    {
        "title": "ما لا يتم الواجب إلا به فهو واجب",
        "definition": (
            "الوسيلة اللازمة لتحقيق واجب تأخذ حكم الوجوب بقدر لزومها."
        ),
        "example": "تعلم القدر اللازم لصحة الصلاة.",
    },
    {
        "title": "الوسائل لها أحكام المقاصد",
        "definition": (
            "تأخذ الوسيلة حكم الغاية بحسب علاقتها بها ونتيجتها."
        ),
        "example": "تحريم وسيلة تؤدي غالبًا إلى محرم قطعي.",
    },
    {
        "title": "التابع تابع",
        "definition": (
            "الشيء التابع يأخذ حكم متبوعه ولا يفرد غالبًا بحكم مستقل."
        ),
        "example": "دخول ملحقات العقار المعتادة في البيع.",
    },
    {
        "title": "يغتفر في التابع ما لا يغتفر في المتبوع",
        "definition": (
            "قد يتسامح في أمر يسير تابع لا يتسامح فيه إذا كان مستقلًا."
        ),
        "example": "التسامح في غرر يسير تابع لعقد معلوم.",
    },
    {
        "title": "الاجتهاد لا ينقض بالاجتهاد",
        "definition": (
            "الحكم الاجتهادي لا ينقض لمجرد ظهور اجتهاد آخر."
        ),
        "example": "عدم إبطال أحكام ماضية مبنية على اجتهاد معتبر.",
    },
    {
        "title": "الحكم يدور مع علته وجودًا وعدمًا",
        "definition": (
            "إذا ثبتت العلة ثبت الحكم المرتبط بها وإذا انتفت انتفى."
        ),
        "example": "ارتباط رخصة السفر بوصف السفر.",
    },
]


# ============================================================
# Countries
# ============================================================

COUNTRIES = [
    ("السودان", "مالكي وشافعي", "تنوع فقهي تاريخي"),
    ("المغرب", "مالكي", "الغالب تاريخيًا"),
    ("سوريا", "حنفي وشافعي", "تنوع فقهي تاريخي"),
    ("العراق", "حنفي وشافعي وحنبلي", "تنوع فقهي واسع"),
    ("الإمارات", "تنوع سني", "حضور مالكي وشافعي وحنبلي"),
    ("عُمان", "إباضي", "مع وجود مدارس أخرى"),
    ("الأردن", "شافعي وحنفي", "تنوع فقهي"),
    ("البحرين", "جعفري ومالكي وشافعي وحنبلي", "تنوع مذهبي"),
    ("الكويت", "مالكي وحنبلي", "مع حضور مدارس أخرى"),
    ("تونس", "مالكي", "الغالب تاريخيًا"),
    ("ليبيا", "مالكي", "الغالب تاريخيًا"),
    ("الجزائر", "مالكي", "الغالب تاريخيًا"),
    ("إندونيسيا", "شافعي", "الغالب في المؤسسات التقليدية"),
    ("ماليزيا", "شافعي", "الغالب في المؤسسات الرسمية"),
    ("باكستان", "حنفي", "مع وجود مدارس أخرى"),
    ("أفغانستان", "حنفي", "الغالب بين السنة"),
    ("إيران", "جعفري", "الغالب رسميًا"),
    ("لبنان", "جعفري وشافعي وحنفي ومالكي وحنبلي", "تنوع قانوني ومذهبي"),
    ("فلسطين", "شافعي وحنفي", "تنوع تاريخي"),
    ("تشاد", "مالكي وشافعي", "يختلف بحسب المناطق"),
    ("نيجيريا", "مالكي", "الغالب في مناطق واسعة"),
    ("الصومال", "شافعي", "الغالب تاريخيًا"),
    ("جيبوتي", "شافعي", "الغالب تاريخيًا"),
    ("السعودية", "حنبلي", "مع تنوع فقهي اجتماعي"),
    ("مصر", "تنوع فقهي", "حضور مدارس متعددة"),
    ("اليمن", "شافعي وزيدي", "يختلف بحسب المناطق"),
    ("تركيا", "حنفي", "الغالب تاريخيًا بين السنة"),
]


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
# Utility functions
# ============================================================

def utc_now_iso() -> str:
    return dt.datetime.now(dt.timezone.utc).isoformat()


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

    text = re.sub(r"[\u064B-\u065F\u0670]", "", text)
    text = re.sub(r"[^\w\s]", " ", text)
    text = re.sub(r"\s+", " ", text)

    return text.strip().lower()


def safe_json_loads(value: Any, default: Any) -> Any:
    if not value:
        return default

    try:
        return json.loads(value)
    except Exception:
        return default


# ============================================================
# Database manager
# ============================================================

class DatabaseManager:
    def __init__(self, db_path: str = DB_PATH):
        self.db_path = db_path
        self.initialize_database()
        self.seed_initial_issue()

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
                json.dumps(rulings, ensure_ascii=False),
            ))

            conn.commit()

    def load_issues(self, topic_filter: str = "all") -> List[Issue]:
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
                """, (topic_filter,)).fetchall()

        issues = []

        for row in rows:
            keywords = [
                item.strip()
                for item in (row["keywords_ar"] or "").split(",")
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

    def import_from_csv(self, content: bytes) -> int:
        text = content.decode("utf-8-sig")
        reader = csv.DictReader(io.StringIO(text))
        count = 0

        with self.connection() as conn:
            for row in reader:
                title = row.get("title_ar", "").strip()

                if not title:
                    continue

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
                    row.get("topic", "other"),
                    title,
                    row.get("keywords_ar", ""),
                    row.get("ruling_vs_ar", ""),
                    row.get("ruling_s_ar", ""),
                    row.get("ruling_f_ar", ""),
                    row.get("rulings_by_madhab_ar", "{}"),
                ))

                count += 1

            conn.commit()

        return count

    def add_reference_chunk(
        self,
        title: str,
        madhab_tag: str,
        chunk_text: str,
        embedding: List[float],
    ) -> bool:
        chunk_hash = hashlib.sha256(
            f"{title}|{madhab_tag}|{chunk_text}".encode("utf-8")
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

        return [dict(row) for row in rows]

    def count_reference_chunks(self) -> int:
        with self.connection() as conn:
            return conn.execute(
                "SELECT COUNT(*) FROM reference_chunks"
            ).fetchone()[0]

    def list_reference_sources(self) -> List[Tuple[str, int]]:
        with self.connection() as conn:
            rows = conn.execute("""
                SELECT source_title, COUNT(*) AS total
                FROM reference_chunks
                GROUP BY source_title
                ORDER BY source_title
            """).fetchall()

        return [
            (row["source_title"], row["total"])
            for row in rows
        ]


# ============================================================
# AI service
# ============================================================

class AIService:
    def __init__(self):
        self.available = (
            USE_GEMINI and gemini_client is not None
        )

    def generate(
        self,
        prompt: str,
        json_mode: bool = False,
    ) -> Optional[str]:
        if not self.available:
            return None

        try:
            config = types.GenerateContentConfig(
                temperature=0.15 if json_mode else 0.25,
                response_mime_type=(
                    "application/json"
                    if json_mode
                    else "text/plain"
                ),
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
            logger.exception("Generation failed")
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
            logger.exception("Embedding failed")
            return None

    def embed_texts(
        self,
        texts: List[str],
        task_type: str = "RETRIEVAL_DOCUMENT",
    ) -> Optional[List[List[float]]]:
        vectors = []

        for text in texts:
            vector = self.embed_text(text, task_type)

            if vector is None:
                return None

            vectors.append(vector)

        return vectors

    def understand_question(
        self,
        question: str,
        issues: List[Issue],
    ) -> Optional[Dict[str, Any]]:
        if not self.available:
            return None

        # Important: chr(10) avoids broken multiline string literals.
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

        raw = self.generate(prompt, json_mode=True)

        if not raw:
            return None

        try:
            data = json.loads(raw)
            valid_ids = {issue.id for issue in issues}

            matched_ids = []

            for item in data.get("matched_issue_ids", []):
                try:
                    number = int(item)

                    if number in valid_ids:
                        matched_ids.append(number)
                except (TypeError, ValueError):
                    continue

            confidence = float(
                data.get("confidence", 0.0)
            )

            return {
                "normalized_question": str(
                    data.get("normalized_question", question)
                ),
                "topic": (
                    data.get("topic")
                    if data.get("topic") in TOPICS
                    else "all"
                ),
                "matched_issue_ids": matched_ids,
                "keywords": [
                    str(item).strip()
                    for item in data.get("keywords", [])
                    if str(item).strip()
                ],
                "needs_reference_search": bool(
                    data.get("needs_reference_search", True)
                ),
                "confidence": max(
                    0.0,
                    min(1.0, confidence),
                ),
            }

        except Exception:
            logger.exception("Question understanding failed")
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
            f"[{index}] المصدر: {chunk['source_title']}"
            f"{newline}{chunk['chunk_text']}"
            for index, chunk in enumerate(chunks, start=1)
        )

        madhab_names = ", ".join(
            f"{code}: {MADHHAB_NAMES[code]['ar']}"
            for code in madhabs
        )

        detail = {
            "very_short": "كلمة أو كلمتين",
            "short": "سطر واحد",
            "full": "فقرة قصيرة",
        }.get(level, "سطر واحد")

        prompt = f"""
أنت مساعد بحثي في الفقه الإسلامي، ولست مفتيًا.

السؤال:
{question}

المذاهب:
{madhab_names}

النصوص المرجعية:
{context}

التعليمات:
- استخدم النصوص المرجعية فقط.
- لا تضف حكمًا غير موجود في النصوص.
- اذكر رقم المقطع مثل [1].
- مستوى الإجابة: {detail}.
- أعد قيمة فارغة للمذهب الذي لا يوجد عنه نص.

أعد JSON فقط:
{{
  "maliki": "",
  "shafii": "",
  "hanafi": "",
  "hanbali": "",
  "zahiri": "",
  "jafari": "",
  "zaidi": "",
  "ibadi": ""
}}
"""

        raw = self.generate(prompt, json_mode=True)

        if not raw:
            return None

        try:
            data = json.loads(raw)

            answers = {}

            for code in madhabs:
                answer = str(data.get(code, "")).strip()

                if answer:
                    answers[code] = answer

            return answers or None

        except Exception:
            logger.exception("Reference answer parsing failed")
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

        text = re.sub(r"\s+", " ", text).strip()

        if not text:
            return []

        step = max_chars - overlap
        chunks = []

        for start in range(0, len(text), step):
            chunk = text[start:start + max_chars].strip()

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

        embeddings = self.ai.embed_texts(
            chunks,
            task_type="RETRIEVAL_DOCUMENT",
        )

        if embeddings is None:
            return -1

        added = 0

        for chunk, embedding in zip(chunks, embeddings):
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
            tag = chunk.get("madhab_tag") or ""

            if madhabs and tag not in allowed:
                continue

            try:
                vector = np.array(
                    json.loads(chunk["embedding"]),
                    dtype=np.float32,
                )

                denominator = (
                    np.linalg.norm(query_vector)
                    * np.linalg.norm(vector)
                )

                similarity = (
                    float(
                        np.dot(query_vector, vector)
                        / denominator
                    )
                    if denominator
                    else 0.0
                )

                if similarity >= min_similarity:
                    scored.append({
                        "source_title": chunk["source_title"],
                        "madhab_tag": tag,
                        "chunk_text": chunk["chunk_text"],
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

    def save_cached(self, key: str, value: Any):
        if key in self.cache:
            self.cache.pop(key)

        self.cache[key] = value

        while len(self.cache) > self.cache_size:
            self.cache.popitem(last=False)

    def search(
        self,
        query: str,
        topic_filter: str,
        madhabs: List[str],
        level: str,
    ) -> Tuple[List[SearchResult], Optional[Dict[str, Any]]]:
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

        issues = self.db.load_issues(topic_filter)
        understanding = None
        candidates = []

        if self.ai.available:
            understanding = self.ai.understand_question(
                query,
                issues,
            )

        if understanding:
            candidate_ids = set(
                understanding["matched_issue_ids"]
            )

            candidates = [
                issue
                for issue in issues
                if issue.id in candidate_ids
            ]

        if not candidates:
            normalized = normalize_arabic(
                understanding["normalized_question"]
                if understanding
                else query
            )

            words = [
                word
                for word in normalized.split()
                if len(word) > 2
            ]

            for issue in issues:
                pool = normalize_arabic(" ".join([
                    issue.title,
                    *issue.keywords,
                    issue.rulings.get("full", ""),
                ]))

                if normalized in pool or any(
                    word in pool for word in words
                ):
                    candidates.append(issue)

        results = []

        for issue in candidates[:5]:
            cards = []

            for madhab in madhabs:
                ruling = issue.rulings_by_madhab.get(madhab)

                if not ruling:
                    continue

                cards.append({
                    "label": MADHHAB_NAMES[madhab]["ar"],
                    "answer": ruling.get(
                        level,
                        ruling.get("full", ""),
                    ),
                    "note": (
                        f"رأي المذهب "
                        f"{MADHHAB_NAMES[madhab]['ar']}"
                    ),
                })

            if cards:
                results.append(SearchResult(
                    title=issue.title,
                    topic=TOPICS.get(
                        issue.topic,
                        TOPICS["other"],
                    )["ar"],
                    cards=cards,
                ))

        final_value = (results, understanding)
        self.save_cached(cache_key, final_value)

        return final_value


# ============================================================
# Streamlit services
# ============================================================

@st.cache_resource
def get_services():
    db = DatabaseManager(DB_PATH)
    ai = AIService()
    search = SearchService(db, ai)
    references = ReferenceManager(db, ai)

    return db, ai, search, references


def inject_css():
    st.markdown(
        """
        <style>
        [data-testid="stAppViewContainer"] {
            background: #f8fafc;
        }

        .app-header {
            display: flex;
            align-items: center;
            gap: 1rem;
            padding: 1.5rem;
            margin: .5rem 0 1.2rem;
            border-radius: 1.25rem;
            color: white;
            background: linear-gradient(
                135deg,
                #0f766e,
                #1d4ed8
            );
            box-shadow: 0 12px 30px rgba(15, 23, 42, .15);
        }

        .brand-mark {
            width: 4.2rem;
            height: 4.2rem;
            display: flex;
            align-items: center;
            justify-content: center;
            border-radius: 1.1rem;
            background: rgba(255, 255, 255, .17);
            font-size: 2.3rem;
        }

        .brand-title {
            font-size: clamp(1.35rem, 3vw, 2.15rem);
            font-weight: 800;
            line-height: 1.3;
        }

        .brand-subtitle {
            margin-top: .35rem;
            opacity: .92;
            line-height: 1.7;
        }

        .language-title {
            text-align: center;
            color: #64748b;
            font-size: .85rem;
            margin-bottom: .35rem;
        }

        div[data-testid="stHorizontalBlock"] button {
            border-radius: 999px;
            min-height: 2.3rem;
        }

        .result-card {
            padding: 1rem;
            margin: .7rem 0;
            border: 1px solid #e2e8f0;
            border-radius: 1rem;
            background: white;
            box-shadow: 0 4px 12px rgba(15, 23, 42, .05);
        }

        .muted {
            color: #64748b;
            font-size: .88rem;
        }
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

    codes = list(LANGUAGE_META.keys())
    columns = st.columns(len(codes))

    for column, code in zip(columns, codes):
        with column:
            meta = LANGUAGE_META[code]

            if st.button(
                f"{meta['flag']} {meta['label']}",
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
        <div class="app-header" dir="{meta['direction']}">
            <div class="brand-mark">📚</div>
            <div>
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
    options = []
    labels = {}

    for group in GROUPS.values():
        for member in group["members"]:
            options.append(member)
            labels[member] = (
                f"{MADHHAB_NAMES[member].get(lang, member)}"
            )

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
        key="selected_madhabs",
    )


def render_topic_selector(
    lang: str,
    text: Dict[str, str],
) -> str:
    options = ["all", *TOPICS.keys()]

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


def render_level_selector(text: Dict[str, str]) -> str:
    labels = {
        "very_short": text["very_short"],
        "short": text["short"],
        "full": text["full"],
    }

    return st.radio(
        text["choose_level"],
        options=list(labels.keys()),
        format_func=lambda code: labels[code],
        horizontal=True,
        key="selected_level",
    )


def render_results(
    results: List[SearchResult],
    understanding: Optional[Dict[str, Any]],
    text: Dict[str, str],
):
    if understanding:
        with st.expander(
            text["normalization"],
            expanded=False,
        ):
            st.write(
                understanding["normalized_question"]
            )
            st.caption(
                f"{text['confidence']}: "
                f"{understanding['confidence']:.0%}"
            )

    for result in results:
        st.markdown(
            '<div class="result-card" dir="rtl">',
            unsafe_allow_html=True,
        )

        st.subheader(result.title)
        st.caption(result.topic)

        columns = st.columns(len(result.cards))

        for column, card in zip(columns, result.cards):
            with column:
                st.markdown(f"### {card['label']}")
                st.write(card["answer"])
                st.caption(card["note"])

        st.markdown(
            "</div>",
            unsafe_allow_html=True,
        )


def render_glossary(text: Dict[str, str]):
    with st.expander(text["glossary"]):
        st.info(text["warning_terms"])

        for term, data in GLOSSARY.items():
            st.markdown(f"### {term}")
            st.markdown(
                f"**{text['definition']}:** "
                f"{data['definition']}"
            )
            st.markdown(
                f"**{text['example']}:** "
                f"{data['example']}"
            )


def render_countries(text: Dict[str, str]):
    with st.expander(text["countries"]):
        st.caption(
            "المذكور هو الغالب أو الأبرز تاريخيًا، "
            "وليس بالضرورة نظامًا قانونيًا حصريًا."
        )

        for country, madhab, note in COUNTRIES:
            st.markdown(
                f"**{country}** — {madhab}  \n"
                f"<span class='muted'>{note}</span>",
                unsafe_allow_html=True,
            )


def render_rules(text: Dict[str, str]):
    with st.expander(text["rules"]):
        for rule in FIQH_RULES:
            with st.expander(rule["title"]):
                st.markdown(
                    f"**{text['definition']}:** "
                    f"{rule['definition']}"
                )
                st.markdown(
                    f"**{text['example']}:** "
                    f"{rule['example']}"
                )


def render_comments(text: Dict[str, str]):
    if "comments" not in st.session_state:
        st.session_state.comments = []

    with st.expander(text["comments"]):
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
                st.success(text["comment_saved"])
            else:
                st.warning(text["no_question"])

        for item in reversed(st.session_state.comments):
            st.markdown(
                f"⭐ {item['rating']}/5 — {item['comment']}"
            )


def is_admin(text: Dict[str, str]) -> bool:
    if not ADMIN_PASSWORD:
        st.warning(
            "ADMIN_PASSWORD غير مضبوط في secrets.toml"
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
    text: Dict[str, str],
):
    with st.expander(text["reference_management"]):
        if not is_admin(text):
            st.info(text["admin_denied"])
            return

        st.write(text["reference_intro"])

        title = st.text_input(
            text["source_title"],
            key="reference_title",
        )

        madhab_options = [""] + list(MADHHAB_NAMES.keys())

        madhab_tag = st.selectbox(
            text["source_madhab"],
            options=madhab_options,
            format_func=lambda code: (
                "عام"
                if not code
                else MADHHAB_NAMES[code]["ar"]
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
                st.warning(text["reference_empty"])
                return

            if not ai.available:
                st.error(text["reference_failed"])
                return

            with st.spinner(text["ai_generating"]):
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
                st.error(text["reference_failed"])

        st.markdown(f"### {text['indexed_sources']}")

        sources = db.list_reference_sources()

        if not sources:
            st.info(text["no_sources"])
        else:
            for source, count in sources:
                st.write(f"📖 {source}: {count}")


def render_search(
    db: DatabaseManager,
    ai: AIService,
    search: SearchService,
    references: ReferenceManager,
    madhabs: List[str],
    topic: str,
    level: str,
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
        st.warning(text["no_question"])
        return

    if not madhabs:
        st.warning(text["no_madhab"])
        return

    with st.spinner(text["ai_generating"]):
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
            text,
        )
        return

    chunks = references.retrieve_relevant_chunks(
        query=question,
        madhabs=madhabs,
    )

    if chunks and ai.available:
        with st.spinner(text["ai_generating"]):
            answers = ai.answer_from_references(
                question=question,
                madhabs=madhabs,
                level=level,
                chunks=chunks,
            )

        if answers:
            st.warning(text["ai_disclaimer"])

            source_names = sorted({
                chunk["source_title"]
                for chunk in chunks
            })

            for code, answer in answers.items():
                st.markdown(
                    '<div class="result-card" dir="rtl">',
                    unsafe_allow_html=True,
                )

                st.subheader(MADHHAB_NAMES[code]["ar"])
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

    st.warning(text["no_results"])


# ============================================================
# Main
# ============================================================

def main():
    inject_css()

    language = render_language_bar()
    text = UI[language]

    render_header(language)

    db, ai, search, references = get_services()

    with st.sidebar:
        st.header(text["choose_madhab"])

        madhabs = render_madhab_selector(
            language,
            text,
        )

        st.divider()

        topic = render_topic_selector(
            language,
            text,
        )

        st.divider()

        level = render_level_selector(text)

        st.divider()

        if ai.available:
            st.success("Gemini AI: مفعّل")
        else:
            st.warning(
                "Gemini AI: غير مفعّل — "
                "سيعمل البحث المحلي فقط"
            )

    st.markdown(f"## {text['write_question']}")

    render_search(
        db=db,
        ai=ai,
        search=search,
        references=references,
        madhabs=madhabs,
        topic=topic,
        level=level,
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
        text=text,
    )


if __name__ == "__main__":
    main()
