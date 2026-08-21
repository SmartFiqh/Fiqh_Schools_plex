import streamlit as st

# 1. إعداد الصفحة الأساسي
st.set_page_config(
    page_title="الجامع المختصر لآراء المذاهب",
    page_icon="📚",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# 2. حقن CSS مخصص لتجميل الواجهة وتحويلها إلى RTL
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Amiri:wght@400;700&family=Tajawal:wght@400;500;700&display=swap');

    /* توجيه الواجهة من اليمين لليسار والخطوط */
    .stApp {
        direction: rtl;
        font-family: 'Tajawal', sans-serif;
        background-color: #f8f9fa;
    }

    /* إخفاء عناصر Streamlit الافتراضية للحصول على مظهر نظيف */
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    header {visibility: hidden;}

    /* تصميم الهيدر المتدرج */
    .custom-header {
        text-align: center;
        padding: 40px 20px;
        background: linear-gradient(135deg, #1b4332, #2d6a4f);
        color: white;
        border-radius: 16px;
        margin-bottom: 30px;
        box-shadow: 0 4px 16px rgba(0,0,0,0.08);
    }
    .custom-header h1 {
        font-family: 'Amiri', serif;
        font-size: 2.8rem;
        margin-bottom: 10px;
        color: #d4af37;
    }
    .custom-header p {
        font-size: 1.1rem;
        opacity: 0.9;
        margin: 0;
    }

    /* تصميم شبكة البطاقات (Cards Grid) */
    .countries-grid {
        display: grid;
        grid-template-columns: repeat(auto-fill, minmax(280px, 1fr));
        gap: 15px;
        margin-top: 20px;
    }
    .country-card {
        background: #ffffff;
        padding: 16px 20px;
        border-radius: 12px;
        border: 1px solid #e9ecef;
        box-shadow: 0 2px 8px rgba(0,0,0,0.04);
        display: flex;
        align-items: center;
        justify-content: space-between;
        transition: transform 0.2s ease, box-shadow 0.2s ease;
    }
    .country-card:hover {
        transform: translateY(-3px);
        box-shadow: 0 6px 16px rgba(0,0,0,0.1);
        border-color: #2d6a4f;
    }
    .country-info {
        display: flex;
        align-items: center;
        gap: 15px;
    }
    .country-flag {
        font-size: 2.2rem;
        line-height: 1;
    }
    .country-name {
        font-weight: 700;
        font-size: 1.1rem;
        color: #212529;
        margin: 0;
    }
    .country-pop {
        font-size: 0.85rem;
        color: #6c757d;
        margin: 0;
    }
    .madhab-badge {
        background: #e8f5e9;
        color: #1b4332;
        padding: 6px 14px;
        border-radius: 20px;
        font-size: 0.9rem;
        font-weight: 700;
        white-space: nowrap;
    }
</style>
""", unsafe_allow_html=True)

# 3. عرض الهيدر المخصص
st.markdown("""
    <div class="custom-header">
        <h1>الجامع المختصر لآراء المذاهب 📚</h1>
        <p>منصة تعليمية للمقارنة الفقهية، وليست موقعًا للإفتاء</p>
    </div>
""", unsafe_allow_html=True)

# 4. البيانات
COUNTRIES = [
    {"flag": "🇪🇬", "name": "مصر", "madhab": "شافعي", "pop": "نحو 120 مليون"},
    {"flag": "🇲🇦", "name": "المغرب", "madhab": "مالكي", "pop": "نحو 38 مليون"},
    {"flag": "🇸🇩", "name": "السودان", "madhab": "مالكي", "pop": "نحو 51 مليون"},
    {"flag": "🇩🇿", "name": "الجزائر", "madhab": "مالكي", "pop": "نحو 47 مليون"},
    {"flag": "🇹🇳", "name": "تونس", "madhab": "مالكي", "pop": "نحو 12 مليون"},
    {"flag": "🇸🇦", "name": "السعودية", "madhab": "حنبلي", "pop": "نحو 35 مليون"},
    {"flag": "🇹🇷", "name": "تركيا", "madhab": "حنفي", "pop": "نحو 86 مليون"},
    {"flag": "🇵🇰", "name": "باكستان", "madhab": "حنفي", "pop": "نحو 259 مليون"},
    {"flag": "🇦🇫", "name": "أفغانستان", "madhab": "حنفي", "pop": "نحو 44 مليون"},
    {"flag": "🇮🇩", "name": "إندونيسيا", "madhab": "شافعي", "pop": "نحو 288 مليون"},
    {"flag": "🇲🇾", "name": "ماليزيا", "madhab": "شافعي", "pop": "نحو 36 مليون"},
    {"flag": "🇸🇴", "name": "الصومال", "madhab": "شافعي", "pop": "نحو 20 مليون"},
    {"flag": "🇩🇯", "name": "جيبوتي", "madhab": "شافعي", "pop": "نحو 1.2 مليون"},
    {"flag": "🇮🇷", "name": "إيران", "madhab": "جعفري", "pop": "نحو 93 مليون"},
    {"flag": "🇴🇲", "name": "عُمان", "madhab": "إباضي", "pop": "نحو 5.5 مليون"},
    {"flag": "🇱🇧", "name": "لبنان", "madhab": "جعفري", "pop": "نحو 5.8 مليون"},
    {"flag": "🇳🇬", "name": "نيجيريا", "madhab": "مالكي", "pop": "نحو 242 مليون"},
    {"flag": "🇹🇩", "name": "تشاد", "madhab": "مالكي", "pop": "نحو 21 مليون"},
    {"flag": "🇾🇪", "name": "اليمن", "madhab": "شافعي", "pop": "نحو 43 مليون"}
]

# 5. أدوات التصفية والبحث عبر Streamlit
col1, col2 = st.columns([2, 1])

with col1:
    madhabs = ["الكل", "مالكي", "شافعي", "حنفي", "حنبلي", "ظاهري", "جعفري", "زيدي", "إباضي"]
    selected_madhab = st.radio("🏷️ تصفية حسب المذهب الفقهي:", madhabs, horizontal=True)

with col2:
    search_query = st.text_input("🔍 بحث عن دولة:", placeholder="أدخل اسم الدولة هنا...")

st.markdown("<br>", unsafe_allow_html=True)

# 6. منطق الفلترة (Filtering)
filtered_countries = COUNTRIES
if selected_madhab != "الكل":
    filtered_countries = [c for c in filtered_countries if c["madhab"] == selected_madhab]

if search_query:
    filtered_countries = [c for c in filtered_countries if search_query.strip() in c["name"]]

# 7. بناء وعرض البطاقات باستخدام HTML ديناميكي
if filtered_countries:
    cards_html = '<div class="countries-grid">'
    for c in filtered_countries:
        cards_html += f'''
        <div class="country-card">
            <div class="country-info">
                <span class="country-flag">{c["flag"]}</span>
                <div>
                    <p class="country-name">{c["name"]}</p>
                    <p class="country-pop">{c["pop"]}</p>
                </div>
            </div>
            <span class="madhab-badge">{c["madhab"]}</span>
        </div>
        '''
    cards_html += '</div>'
    
    # عرض الـ HTML داخل تطبيق Streamlit
    st.markdown(cards_html, unsafe_allow_html=True)
else:
    st.warning("لم يتم العثور على نتائج تطابق شروط البحث.")
