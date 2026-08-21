import streamlit as st

# 1. إعداد الصفحة
st.set_page_config(
    page_title="الجامع المختصر لآراء المذاهب",
    page_icon="📚",
    layout="wide",
    initial_sidebar_state="expanded"
)

# 2. تصميم CSS المخصص
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Amiri:wght@400;700&family=Tajawal:wght@400;500;700&display=swap');

    .stApp {
        font-family: 'Tajawal', sans-serif;
        background-color: #f8f9fa;
    }

    #MainMenu, footer, header {visibility: hidden;}

    .custom-header {
        text-align: center;
        padding: 25px 20px;
        background: linear-gradient(135deg, #1b4332, #2d6a4f);
        color: white;
        border-radius: 16px;
        margin-bottom: 20px;
        box-shadow: 0 4px 16px rgba(0,0,0,0.08);
    }
    .custom-header h1 {
        font-family: 'Amiri', serif;
        font-size: 2.2rem;
        margin-bottom: 6px;
        color: #d4af37;
    }
    .custom-header p {
        font-size: 0.95rem;
        opacity: 0.9;
        margin: 0;
    }

    /* البطاقات التفاعلية */
    .info-card {
        background: #ffffff;
        border-right: 4px solid #1b4332;
        border-radius: 10px;
        padding: 18px 20px;
        margin-bottom: 15px;
        box-shadow: 0 2px 8px rgba(0,0,0,0.04);
    }
    .info-card-title {
        font-family: 'Amiri', serif;
        font-size: 1.3rem;
        color: #1b4332;
        font-weight: 700;
        margin-bottom: 8px;
    }

    /* شبكة بطاقات الدول */
    .countries-grid {
        display: grid;
        grid-template-columns: repeat(auto-fill, minmax(260px, 1fr));
        gap: 15px;
        margin-top: 15px;
    }
    .country-card {
        background: #ffffff;
        padding: 14px 18px;
        border-radius: 10px;
        border: 1px solid #e9ecef;
        box-shadow: 0 2px 6px rgba(0,0,0,0.03);
        display: flex;
        align-items: center;
        justify-content: space-between;
    }
    .country-flag { font-size: 1.8rem; }
    .country-name { font-weight: 700; color: #212529; margin: 0; }
    .country-pop { font-size: 0.8rem; color: #6c757d; margin: 0; }
    .madhab-badge {
        background: #e8f5e9;
        color: #1b4332;
        padding: 4px 10px;
        border-radius: 15px;
        font-size: 0.8rem;
        font-weight: 700;
    }

    /* جداول المقارنة */
    .custom-table {
        width: 100%;
        border-collapse: collapse;
        background: white;
        border-radius: 10px;
        overflow: hidden;
        box-shadow: 0 2px 8px rgba(0,0,0,0.04);
    }
    .custom-table th {
        background-color: #1b4332;
        color: white;
        padding: 12px;
        text-align: right;
    }
    .custom-table td {
        padding: 12px;
        border-bottom: 1px solid #eee;
        vertical-align: top;
    }
</style>
""", unsafe_allow_html=True)

# 3. محدد اللغات في الشريط الجانبي
with st.sidebar:
    st.title("🌐 اللغة / Language")
    selected_lang = st.selectbox(
        "اختر لغة الواجهة:",
        ["العربية", "English", "Français", "فارسی", "اردو", "Bahasa Melayu"]
    )
    st.divider()
    st.info("💡 المنصة تهدف لتسهيل المدارسة الفقهية المقارنة للأكاديميين والباحثين.")

# 4. ترجمة الهيدر الأساسي بناءً على اللغة
headers = {
    "العربية": ("الجامع المختصر لآراء المذاهب 📚", "منصة تعليمية للمقارنة الفقهية، وليست موقعًا للإفتاء"),
    "English": ("Concise Compendium of Jurisprudential Schools 📚", "Educational Platform for Comparative Fiqh, Not a Fatwa Site"),
    "Français": ("Compendium des Écoles de Jurisprudence 📚", "Plateforme Éducative de Fiqh Comparé (Non-Fatwa)"),
    "فارسی": ("جامع مختصر آراء مذاهب فقهی 📚", "پلتفرم آموزشی فقه مقارن، نه پایگاه استفتاء"),
    "اردو": ("جامع مختصر آراء مذاہب 📚", "تقابلی فقہ کا تعلیمی پلیٹ فارم، فتویٰ ویب سائٹ نہیں"),
    "Bahasa Melayu": ("Kompendium Ringkas Mazhab Fiqh 📚", "Platform Pendidikan Fiqh Perbandingan, Bukan Laman Fatwa")
}

title_txt, subtitle_txt = headers.get(selected_lang, headers["العربية"])

st.markdown(f"""
<div class="custom-header">
    <h1>{title_txt}</h1>
    <p>{subtitle_txt}</p>
</div>
""", unsafe_allow_html=True)

# 5. البيانات الأساسية
MADHABS_DATA = {
    "مالكي": {
        "imams": "الإمام مالك بن أنس (93 - 179 هـ)",
        "scholars": "ابن رشد الحفيد، القاضي عياض، الإمام الشاطبي، خليل بن إسحاق",
        "sources": ["القرآن", "السنة", "عمل أهل المدينة", "المصالح المرسلة", "سد الذرائع", "الاستحسان"],
        "desc": "يعتمد على الأثر المتواتر وتطبيق أهل المدينة المنورة كدليل عملي مع مراعاة المقاصد الشرعية."
    },
    "شافعي": {
        "imams": "الإمام محمد بن إدريس الشافعي (150 - 204 هـ)",
        "scholars": "الإمام النووي، الإمام الغزالي، العز بن عبد السلام، الإمام الماوردي",
        "sources": ["القرآن", "السنة الصحيحة", "الإجماع", "القياس", "استصحاب الحال"],
        "desc": "تمتاز بالدقة الأصولية والصياغة المحكمة واستبعاد الاستحسان الذي لا يستند إلى نص."
    },
    "حنفي": {
        "imams": "الإمام أبو حنيفة النعمان (80 - 150 هـ)",
        "scholars": "أبو يوسف، محمد بن الحسن الشيباني، الكاساني، ابن عابدين",
        "sources": ["القرآن", "السنة", "أقوال الصحابة", "القياس", "الاستحسان", "العرف"],
        "desc": "مدرسة أهل الرأي والتفريع الفقهي والتوسع في القياس والحلول العرفية الاستحسانية."
    },
    "حنبلي": {
        "imams": "الإمام أحمد بن حنبل (164 - 241 هـ)",
        "scholars": "ابن قدامة المقدسي، شيخ الإسلام ابن تيمية، ابن القيم، ابن رجب",
        "sources": ["الكتاب والسنة", "فتاوى الصحابة", "تقديم الحديث الضعيف/المرسل على القياس", "القياس"],
        "desc": "مذهب أثري يعتمد التمسك بالنصوص المرفوعة والآثار وتجنب الرأي ما وجد الأثر."
    },
    "إباضي": {
        "imams": "الإمام جابر بن زيد الأزدي (21 - 93 هـ)",
        "scholars": "أبو عبيدة مسلم بن أبي كريمة، الإمام السالمي، الشيخ أطفيش",
        "sources": ["القرآن", "السنة المسندة", "الإجماع", "القياس", "المصلحة"],
        "desc": "يعتمد على الأسانيد المروية في مسند الربيع بن حبيب والأصول الاستدلالية العقلية والمصلحية."
    },
    "جعفري": {
        "imams": "الإمام جعفر بن محمد الصادق (83 - 148 هـ)",
        "scholars": "الشيخ الطوسي، الشيخ المفيد، المحقق الحلي، العلامة الحلي",
        "sources": ["القرآن", "السنة النبوية وآل البيت", "الإجماع الكاشف", "دليل العقل"],
        "desc": "استمرار الاجتهاد والاعتماد على أدلة العقل والأحاديث المروية عبر أئمة أهل البيت."
    }
}

TERMS_GLOSSARY = {
    "عمل أهل المدينة": "المنقول المتواتر من الممارسات والعبادات التي توارثها أهل المدينة المنورة جيلًا عن جيل عن النبي ﷺ.",
    "القياس": "إلحاق واقعة لا نص على حكمها بواقعة ورد نص بحكمها لإتحادهما في العلة.",
    "الاستحسان": "عدول المجتهد عن مقتضى قياس جلي إلى قياس خفي أو استثناء لضرورة أو مصلحة راجحة.",
    "المصالح المرسلة": "جلب منفعة أو دفع مضرة لم ينص الشارع على اعتبارها ولا على إلغائها.",
    "سد الذرائع": "منع الوسائل والمباحات التي تؤدي غالباً إلى مفاسد أو محرمات.",
    "استصحاب الحال": "الحكم ببقاء الأمر على ما كان عليه في الماضي حتى يقوم الدليل على تغيره."
}

COUNTRIES = [
    {"flag": "🇪🇬", "name": "مصر", "madhab": "شافعي", "pop": "نحو 120 مليون"},
    {"flag": "🇲🇦", "name": "المغرب", "madhab": "مالكي", "pop": "نحو 38 مليون"},
    {"flag": "🇸🇩", "name": "السودان", "madhab": "مالكي", "pop": "نحو 51 مليون"},
    {"flag": "🇸🇦", "name": "السعودية", "madhab": "حنبلي", "pop": "نحو 35 مليون"},
    {"flag": "🇹🇷", "name": "تركيا", "madhab": "حنفي", "pop": "نحو 86 مليون"},
    {"flag": "🇮🇩", "name": "إندونيسيا", "madhab": "شافعي", "pop": "نحو 288 مليون"},
    {"flag": "🇴🇲", "name": "عُمان", "madhab": "إباضي", "pop": "نحو 5.5 مليون"},
    {"flag": "🇮🇷", "name": "إيران", "madhab": "جعفري", "pop": "نحو 93 مليون"}
]

# 6. التبويبات الرئيسية
tab1, tab2, tab3, tab4 = st.tabs([
    "🗺️ تصفح الدول والمذاهب",
    "📜 الأئمة والمصطلحات والمصادر",
    "⚖️ جدول المقارنة الأصولية",
    "❓ أسئلة واستفسارات المستخدمين"
])

# --- التبويب الأول: الدول والمذاهب ---
with tab1:
    col1, col2 = st.columns([2, 1])
    with col1:
        selected_madhab = st.radio("🏷️ تصفية المذهب:", ["الكل"] + list(MADHABS_DATA.keys()), horizontal=True)
    with col2:
        search_query = st.text_input("🔍 بحث عن دولة:", placeholder="أدخل اسم الدولة...")

    filtered_countries = COUNTRIES
    if selected_madhab != "الكل":
        filtered_countries = [c for c in filtered_countries if c["madhab"] == selected_madhab]
    if search_query:
        filtered_countries = [c for c in filtered_countries if search_query.strip() in c["name"]]

    if filtered_countries:
        cards_list = [
            f'<div class="country-card"><div style="display:flex;align-items:center;gap:10px;"><span class="country-flag">{c["flag"]}</span><div><p class="country-name">{c["name"]}</p><p class="country-pop">{c["pop"]}</p></div></div><span class="madhab-badge">{c["madhab"]}</span></div>'
            for c in filtered_countries
        ]
        st.markdown(f'<div class="countries-grid">{"".join(cards_list)}</div>', unsafe_allow_html=True)
    else:
        st.warning("لم يتم العثور على نتائج تطابق شروط البحث.")

# --- التبويب الثاني: الأئمة والمصطلحات والمصادر ---
with tab2:
    st.subheader("👤 الأئمة المؤسسون وأشهر الفقهاء")
    for m_name, m_data in MADHABS_DATA.items():
        with st.expander(f"مذهب الإمام ({m_name}) - التراجم والفقهاء"):
            st.markdown(f"**الإمام المؤسس:** {m_data['imams']}")
            st.markdown(f"**أشهر الفقهاء والأعلام:** {m_data['scholars']}")
            st.markdown(f"**النهج العام:** {m_data['desc']}")

    st.divider()
    st.subheader("📖 معجم المصطلحات الأصولية ومصادر التشريع")
    for term, definition in TERMS_GLOSSARY.items():
        st.markdown(f"**• {term}:** {definition}")

# --- التبويب الثالث: جدول المقارنة الأصولية ---
with tab3:
    st.subheader("⚖️ مقارنة أصول الاستنباط بين المذاهب")
    table_rows = []
    for m_name, m_data in MADHABS_DATA.items():
        sources_str = ", ".join(m_data["sources"])
        table_rows.append(f"<tr><td><b>{m_name}</b></td><td>{m_data['imams']}</td><td>{sources_str}</td><td>{m_data['desc']}</td></tr>")
    
    html_table = f'<table class="custom-table"><thead><tr><th>المذهب</th><th>المؤسس</th><th>أبرز مصادر التشريع</th><th>المنهج الأصولي</th></tr></thead><tbody>{"".join(table_rows)}</tbody></table>'
    st.markdown(html_table, unsafe_allow_html=True)

# --- التبويب الرابع: أسئلة واستفسارات المستخدمين ---
with tab4:
    st.subheader("❓ قسم الأسئلة التعليمية والتفاعلية")
    st.caption("يتيح هذا القسم تقديم الاستفسارات العلمية والمقارنات الفقهية لمراجعتها من الباحثين.")

    # أسئلة شائعة
    with st.expander("س: ما الفرق بين المصلحة المرسلة والاستحسان؟"):
        st.write("الاستحسان هو عدول عن قياس جلي إلى قياس خفي لوجود أثر أو ضرورة، بينما المصلحة المرسلة هي استنباط حكم لم يرد فيه نص خاص بناءً على مصلحة عامة تتوافق مع مقاصد الشريعة.")
    
    with st.expander("س: لماذا يُقدم المذهب المالكي 'عمل أهل المدينة' على بعض أحاديث الآحاد؟"):
        st.write("لأن الإمام مالك يرى أن تطبيق أهل المدينة ينقل السُّنّة نقلًا عمليًا متواترًا كابرًا عن كابر، والتواتر العملي أقدم وأقوى من خبر الفرد.")

    st.divider()
    st.write("💬 **إرسال سؤال جديد:**")
    with st.form("user_question_form"):
        user_name = st.text_input("الاسم / اللقب الأكاديمي:")
        user_email = st.text_input("البريد الإلكتروني (اختياري):")
        question_text = st.text_area("أدخل سؤالك المفهومي أو الاستفسار عن المقارنات الفقهية:")
        submitted = st.form_submit_button("إرسال السؤال")
        
        if submitted:
            if question_text.strip():
                st.success("تم إرسال سؤالك بنجاح! سيتم مراجعته وإضافته لقسم الإجابات التعليمية قريبًا.")
            else:
                st.error("يرجى كتابة نص السؤال قبل الإرسال.")
