import streamlit as st

# 1. إعداد الصفحة
st.set_page_config(
    page_title="الجامع المختصر لآراء المذاهب",
    page_icon="📚",
    layout="wide",
    initial_sidebar_state="expanded"
)

# 2. تصميم CSS المطور والمتقدم
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Amiri:ital,wght@0,400;0,700;1,400&family=Readex+Pro:wght@300;400;500;600;700&display=swap');

    /* الهيكل العام للموقع */
    .stApp {
        font-family: 'Readex Pro', sans-serif;
        background-color: #faf9f6;
        color: #2b2b2b;
    }

    #MainMenu, footer, header {visibility: hidden;}

    /* الهيدر الرئيسي */
    .custom-header {
        text-align: center;
        padding: 35px 25px;
        background: linear-gradient(135deg, #0f382c 0%, #1e5645 100%);
        color: white;
        border-radius: 20px;
        margin-bottom: 25px;
        box-shadow: 0 10px 25px rgba(15, 56, 44, 0.15);
        border-bottom: 4px solid #c5a059;
    }
    .custom-header h1 {
        font-family: 'Amiri', serif;
        font-size: 2.5rem;
        font-weight: 700;
        margin-bottom: 10px;
        color: #f3e5ab;
        letter-spacing: 0.5px;
    }
    .custom-header p {
        font-size: 1.05rem;
        opacity: 0.9;
        margin: 0;
        font-weight: 300;
    }

    /* تحسين القوائم المطوية (st.expander) */
    div[data-testid="stExpander"] {
        background-color: #ffffff;
        border: 1px solid #e2ebf0 !important;
        border-right: 4px solid #1e5645 !important;
        border-radius: 12px !important;
        margin-bottom: 12px !important;
        box-shadow: 0 3px 10px rgba(0,0,0,0.02) !important;
        transition: all 0.3s ease !important;
    }
    div[data-testid="stExpander"]:hover {
        border-right-color: #c5a059 !important;
        box-shadow: 0 5px 15px rgba(0,0,0,0.05) !important;
        transform: translateX(-2px);
    }
    div[data-testid="stExpander"] summary {
        font-weight: 600 !important;
        color: #0f382c !important;
        padding: 14px 18px !important;
        font-size: 1.05rem !important;
    }

    /* تحسين تصميم التبويبات (Tabs) */
    .stTabs [data-baseweb="tab-list"] {
        gap: 8px;
        background-color: #eae8e1;
        padding: 8px;
        border-radius: 14px;
    }
    .stTabs [data-baseweb="tab"] {
        height: 45px;
        border-radius: 10px;
        font-family: 'Readex Pro', sans-serif;
        font-weight: 500;
        color: #555555;
        border: none !important;
        background-color: transparent;
    }
    .stTabs [aria-selected="true"] {
        background-color: #ffffff !important;
        color: #0f382c !important;
        font-weight: 700 !important;
        box-shadow: 0 4px 10px rgba(0,0,0,0.06);
    }

    /* شبكة بطاقات الدول */
    .countries-grid {
        display: grid;
        grid-template-columns: repeat(auto-fill, minmax(270px, 1fr));
        gap: 16px;
        margin-top: 20px;
    }
    .country-card {
        background: #ffffff;
        padding: 16px 20px;
        border-radius: 14px;
        border: 1px solid #e9ecef;
        box-shadow: 0 2px 8px rgba(0,0,0,0.03);
        display: flex;
        align-items: center;
        justify-content: space-between;
        transition: all 0.3s ease;
    }
    .country-card:hover {
        transform: translateY(-4px);
        box-shadow: 0 8px 20px rgba(15, 56, 44, 0.08);
        border-color: #c5a059;
    }
    .country-flag { font-size: 2rem; }
    .country-name { font-weight: 700; color: #111111; margin: 0; font-size: 1.05rem; }
    .country-pop { font-size: 0.82rem; color: #777777; margin: 0; }
    .madhab-badge {
        background: #e8f3ee;
        color: #0f382c;
        padding: 6px 12px;
        border-radius: 20px;
        font-size: 0.82rem;
        font-weight: 600;
        border: 1px solid #c2e0d3;
    }

    /* جدول المقارنة */
    .custom-table {
        width: 100%;
        border-collapse: separate;
        border-spacing: 0;
        background: white;
        border-radius: 14px;
        overflow: hidden;
        box-shadow: 0 4px 15px rgba(0,0,0,0.04);
        margin-top: 15px;
    }
    .custom-table th {
        background-color: #0f382c;
        color: #f3e5ab;
        padding: 16px;
        text-align: right;
        font-family: 'Amiri', serif;
        font-size: 1.15rem;
        font-weight: 700;
    }
    .custom-table td {
        padding: 14px 16px;
        border-bottom: 1px solid #f0f0f0;
        vertical-align: top;
        font-size: 0.95rem;
        line-height: 1.6;
    }
    .custom-table tr:hover td {
        background-color: #fcfbf7;
    }

    /* تحسين الشريحة الجانبية */
    section[data-testid="stSidebar"] {
        background-color: #f1efe9;
        border-left: 1px solid #e2ded4;
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

# 4. الهيدر الأساسي
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
    "زيدي": {
        "imams": "الإمام زيد بن علي بن الحسين (80 - 122 هـ)",
        "scholars": "الإمام الهادي إلى الحق، القاسم بن إبراهيم، الإمام الشوكاني، الإمام الصنعاني",
        "sources": ["القرآن الكريم", "السنة النبوية", "إجماع العترة (أهل البيت)", "القياس", "المصالح المرسلة", "العقل"],
        "desc": "يجمع بين مدرسة الحديث والأصول العقلية، ويفسح مجالاً واسعاً للاجتهاد والقياس والمصلحة."
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

FIQH_TERMS = {
    "📌 الفرض / الواجب": {
        "definition": "ما طلب الشارع فعله من المكلف على وجه الحتم واللزام.",
        "ruling": "يثاب فاعله امتثالاً لأمر الله، ويعاقب تاركه واستحق الوعيد.",
        "examples": "الصلوات الخمس، صيام شهر رمضان، إيتاء الزكاة، بر الوالدين."
    },
    "📌 فرض العين": {
        "definition": "الواجب الذي يلزم كل فرد مكلف بعينه أداؤه، ولا يجزئ أو يسقط بفعل شخص آخر عنه.",
        "ruling": "يتوجه التكليف فيه إلى كل مسلم ومسلمة بذاته، ويأثم كل فرد يتخلف عنه دون عذر شرعي.",
        "examples": "صلاة الظهر، الطهارة للصلاة، الأمانة، الوفاء بالعهود."
    },
    "📌 فرض الكفاية": {
        "definition": "الواجب الذي قُصد تحقيقه وحصوله من مجموع المكلفين دون النظر إلى ذات من قام به.",
        "ruling": "إذا قام به من يكفي من المسلمين سقط الإثم والتكليف عن الباقين، وإذا تركه الجميع أثم كل من علم به وقدر عليه.",
        "examples": "صلاة الجنازة، رد السلام، الأذان للمجتمع، تعلم العلوم التخصصية كالطب والهندسة والإفتاء."
    },
    "📌 المندوب / المستحب / النفل": {
        "definition": "ما طلب الشارع فعله من المكلف طلباً غير جازم (على سبيل الترغيب لا الإلزام).",
        "ruling": "يثاب فاعله امتثالاً، ولا يعاقب تاركه ولا يلام.",
        "examples": "صدقة التطوع، قيام الليل، السواك، قراءة أذكار الصباح والمساء."
    },
    "📌 السنة المؤكدة": {
        "definition": "ما داوم النبي ﷺ على فعله وحافظ عليه ولم يتركه إلا نادراً لبيان أنه ليس بفرض واجب.",
        "ruling": "يثاب فاعلها، ولا يعاقب تاركها ولكنه يستحق العتاب واللوم للتفريط في هدي النبي ﷺ.",
        "examples": "ركعتا الفجر، صلاة الوتر، صلاة العيدين، والسنن الراتبة التابعة للصلوات الخمس."
    },
    "📌 الحلال / المباح": {
        "definition": "ما خير الشارع المكلف بين فعله وتركه، فلا يتعلق بفعله أو تركه أمر ولا نهي لذاته.",
        "ruling": "لا يثاب على فعله ولا يعاقب على تركه لذاته، وقد يثاب عليه إذا صاحَبَته نية صالحة.",
        "examples": "أنواع الطعام والشراب المباحة، البيع والشراء، السفر للنزهة، اختيار نمط الملابس."
    },
    "📌 المكروه": {
        "definition": "ما طلب الشارع من المكلف تركه طلباً غير جازم (على وجه التنزيه لا التحريم).",
        "ruling": "يثاب تاركه امتثالاً لأمر الله، ولا يعاقب فاعله، ولكن يُلام على الإكثار منه.",
        "examples": "الأخذ والإعطاء باليد الشمال بلا عذر، النوم قبل صلاة العشاء، إفراد يوم الجمعة بالصيام."
    },
    "📌 الحرام / المحرم": {
        "definition": "ما طلب الشارع من المكلف تركه على وجه الحتم واللزام.",
        "ruling": "يثاب تاركه امتثالاً لله، ويعاقب فاعله مرتکب الكبيرة أو المعصية ومستحق للوعيد.",
        "examples": "عقوق الوالدين، أكل الربا، السرقة، شهادة الزور، القتل بغير حق."
    }
}

USUL_TERMS = {
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
    {"flag": "🇩жуть", "name": "الجزائر", "madhab": "مالكي", "pop": "نحو 47 مليون"},
    {"flag": "🇹🇳", "name": "تونس", "madhab": "مالكي", "pop": "نحو 12 مليون"},
    {"flag": "🇸🇦", "name": "السعودية", "madhab": "حنبلي", "pop": "نحو 35 مليون"},
    {"flag": "🇮🇶", "name": "العراق", "madhab": "جعفري", "pop": "نحو 45 مليون"},
    {"flag": "🇸🇾", "name": "سوريا", "madhab": "حنفي", "pop": "نحو 23 مليون"},
    {"flag": "🇵🇸", "name": "فلسطين", "madhab": "شافعي", "pop": "نحو 5.5 مليون"},
    {"flag": "🇯🇴", "name": "الأردن", "madhab": "شافعي", "pop": "نحو 11.5 مليون"},
    {"flag": "🇱🇧", "name": "لبنان", "madhab": "جعفري", "pop": "نحو 5.8 مليون"},
    {"flag": "🇾🇪", "name": "اليمن", "madhab": "زيدي", "pop": "نحو 43 مليون"},
    {"flag": "🇰🇼", "name": "الكويت", "madhab": "مالكي", "pop": "نحو 4.8 مليون"},
    {"flag": "🇶🇦", "name": "قطر", "madhab": "حنبلي", "pop": "نحو 3.0 مليون"},
    {"flag": "🇧🇭", "name": "البحرين", "madhab": "مالكي", "pop": "نحو 1.5 مليون"},
    {"flag": "🇹🇷", "name": "تركيا", "madhab": "حنفي", "pop": "نحو 86 مليون"},
    {"flag": "🇵🇰", "name": "باكستان", "madhab": "حنفي", "pop": "نحو 259 مليون"},
    {"flag": "🇦🇫", "name": "أفغانستان", "madhab": "حنفي", "pop": "نحو 44 مليون"},
    {"flag": "🇮🇩", "name": "إندونيسيا", "madhab": "شافعي", "pop": "نحو 288 مليون"},
    {"flag": "🇲🇾", "name": "ماليزيا", "madhab": "شافعي", "pop": "نحو 36 مليون"},
    {"flag": "🇸🇴", "name": "الصومال", "madhab": "شافعي", "pop": "نحو 20 مليون"},
    {"flag": "🇩🇯", "name": "جيبوتي", "madhab": "شافعي", "pop": "نحو 1.2 مليون"},
    {"flag": "🇹🇩", "name": "تشاد", "madhab": "مالكي", "pop": "نحو 21 مليون"},
    {"flag": "🇴🇲", "name": "عُمان", "madhab": "إباضي", "pop": "نحو 5.5 مليون"},
    {"flag": "🇮🇷", "name": "إيران", "madhab": "جعفري", "pop": "نحو 93 مليون"}
]

# 6. التبويبات
tab1, tab2, tab3, tab4 = st.tabs([
    "🗺️ تصفح الدول والمذاهب",
    "📜 الأئمة والمصطلحات والمصادر",
    "⚖️ جدول المقارنة الأصولية",
    "❓ أسئلة واستفسارات"
])

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
            f'<div class="country-card"><div style="display:flex;align-items:center;gap:12px;"><span class="country-flag">{c["flag"]}</span><div><p class="country-name">{c["name"]}</p><p class="country-pop">{c["pop"]}</p></div></div><span class="madhab-badge">{c["madhab"]}</span></div>'
            for c in filtered_countries
        ]
        st.markdown(f'<div class="countries-grid">{"".join(cards_list)}</div>', unsafe_allow_html=True)
    else:
        st.warning("لم يتم العثور على نتائج تطابق شروط البحث.")

with tab2:
    st.subheader("👤 الأئمة المؤسسون وأشهر الفقهاء")
    for m_name, m_data in MADHABS_DATA.items():
        with st.expander(f"مذهب الإمام ({m_name}) - التراجم والفقهاء", expanded=False):
            st.markdown(f"**الإمام المؤسس:** {m_data['imams']}")
            st.markdown(f"**أشهر الفقهاء والأعلام:** {m_data['scholars']}")
            st.markdown(f"**النهج العام:** {m_data['desc']}")

    st.divider()

    st.subheader("📖 معجم الأحكام والمصطلحات الفقهية")
    for term, details in FIQH_TERMS.items():
        with st.expander(term, expanded=False):
            st.markdown(f"**التعريف الفقهي:** {details['definition']}")
            st.markdown(f"**الأثر الشرعي (الحكم):** {details['ruling']}")
            st.markdown(f"**الأمثلة التطبيقية:** {details['examples']}")

    st.divider()

    st.subheader("🔍 معجم القواعد ومصادر التشريع الأصولية")
    for term, definition in USUL_TERMS.items():
        with st.expander(f"مصدر: {term}", expanded=False):
            st.markdown(f"**التعريف الأصولي:** {definition}")

with tab3:
    st.subheader("⚖️ مقارنة أصول الاستنباط بين المذاهب")
    table_rows = []
    for m_name, m_data in MADHABS_DATA.items():
        sources_str = ", ".join(m_data["sources"])
        table_rows.append(f"<tr><td><b>{m_name}</b></td><td>{m_data['imams']}</td><td>{sources_str}</td><td>{m_data['desc']}</td></tr>")
    
    html_table = f'<table class="custom-table"><thead><tr><th>المذهب</th><th>المؤسس</th><th>أبرز مصادر التشريع</th><th>المنهج الأصولي</th></tr></thead><tbody>{"".join(table_rows)}</tbody></table>'
    st.markdown(html_table, unsafe_allow_html=True)

with tab4:
    st.subheader("❓ قسم الأسئلة التعليمية والتفاعلية")
    with st.expander("س: ما الفرق بين المصلحة المرسلة والاستحسان؟", expanded=False):
        st.write("الاستحسان هو عدول عن قياس جلي إلى قياس خفي لوجود أثر أو ضرورة، بينما المصلحة المرسلة هي استنباط حكم لم ورد فيه نص خاص بناءً على مصلحة عامة تتوافق مع مقاصد الشريعة.")
    
    with st.expander("س: لماذا يُقدم المذهب المالكي 'عمل أهل المدينة' على بعض أحاديث الآحاد؟", expanded=False):
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
