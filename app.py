import streamlit as st

# 1. إعداد الصفحة
st.set_page_config(
    page_title="الجامع المختصر لآراء المذاهب",
    page_icon="📚",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# 2. تصميم CSS المخصص
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Amiri:wght@400;700&family=Tajawal:wght@400;500;700&display=swap');

    .stApp {
        direction: rtl;
        font-family: 'Tajawal', sans-serif;
        background-color: #f8f9fa;
    }

    #MainMenu, footer, header {visibility: hidden;}

    .custom-header {
        text-align: center;
        padding: 35px 20px;
        background: linear-gradient(135deg, #1b4332, #2d6a4f);
        color: white;
        border-radius: 16px;
        margin-bottom: 25px;
        box-shadow: 0 4px 16px rgba(0,0,0,0.08);
    }
    .custom-header h1 {
        font-family: 'Amiri', serif;
        font-size: 2.5rem;
        margin-bottom: 8px;
        color: #d4af37;
    }
    .custom-header p {
        font-size: 1rem;
        opacity: 0.9;
        margin: 0;
    }

    /* بطاقة تفاصيل المذهب */
    .madhab-detail-card {
        background: #ffffff;
        border-right: 5px solid #d4af37;
        border-radius: 12px;
        padding: 20px 25px;
        margin-bottom: 25px;
        box-shadow: 0 2px 12px rgba(0,0,0,0.05);
    }
    .madhab-detail-title {
        font-family: 'Amiri', serif;
        font-size: 1.5rem;
        color: #1b4332;
        margin-bottom: 12px;
        font-weight: 700;
    }
    .sources-list {
        display: flex;
        flex-wrap: wrap;
        gap: 8px;
        margin-bottom: 15px;
    }
    .source-chip {
        background: #e8f5e9;
        color: #1b4332;
        padding: 4px 12px;
        border-radius: 16px;
        font-size: 0.88rem;
        font-weight: 500;
    }
    .principle-box {
        background: #fdfbf7;
        border: 1px dashed #d4af37;
        padding: 12px 16px;
        border-radius: 8px;
        font-size: 0.95rem;
        color: #333;
        line-height: 1.7;
    }

    /* شبكة بطاقات الدول */
    .countries-grid {
        display: grid;
        grid-template-columns: repeat(auto-fill, minmax(280px, 1fr));
        gap: 15px;
        margin-top: 15px;
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
        transform: translateY(-2px);
        box-shadow: 0 6px 16px rgba(0,0,0,0.08);
        border-color: #2d6a4f;
    }
    .country-info {
        display: flex;
        align-items: center;
        gap: 15px;
    }
    .country-flag {
        font-size: 2rem;
        line-height: 1;
    }
    .country-name {
        font-weight: 700;
        font-size: 1.05rem;
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
        padding: 5px 12px;
        border-radius: 20px;
        font-size: 0.85rem;
        font-weight: 700;
        white-space: nowrap;
    }
</style>
""", unsafe_allow_html=True)

# 3. الهيدر المخصص
st.markdown("""
<div class="custom-header">
    <h1>الجامع المختصر لآراء المذاهب 📚</h1>
    <p>منصة تعليمية للمقارنة الفقهية، وليست موقعًا للإفتاء</p>
</div>
""", unsafe_allow_html=True)

# 4. قواعد بيانات مصادر وتشريع المذاهب
MADHAB_INFO = {
    "مالكي": {
        "title": "المذهب المالكي (إمام دار الهجرة مالك بن أنس)",
        "sources": ["القرآن الكريم", "السنة النبوية", "عمل أهل المدينة", "إجماع الصحابة", "القياس", "قول الصحابي", "المصالح المرسلة", "سد الذرائع", "الاستحسان", "العرف"],
        "principles": "يمتاز المذهب بالتوسع في الأصول النقلية والاجتهادية، وإعطاء تقديم خاص لـ 'عمل أهل المدينة' باعتباره نقلاً متواتراً، مع اعتماد واسع على المقاصد الشرعية وسد الذرائع."
    },
    "شافعي": {
        "title": "المذهب الشافعي (الإمام محمد بن إدريس الشافعي)",
        "sources": ["القرآن الكريم", "السنة النبوية (الحديث الصحيح)", "الإجماع القطعي", "قول الصحابي (بشروط)", "القياس", "استصحاب الحال"],
        "principles": "صنع الإمام الشافعي ضبطاً دقيقاً لأصول الفقه في كتابه 'الرسالة'، ويرفض الاستحسان بغير نص أو قياس، وقاعدته الشهيرة: 'إذا صح الحديث فهو مذهبي'."
    },
    "حنفي": {
        "title": "المذهب الحنفي (الإمام أبو حنيفة النعمان)",
        "sources": ["القرآن الكريم", "السنة النبوية", "أقوال الصحابة", "الإجماع", "القياس", "الاستحسان", "العرف والعادة"],
        "principles": "يُعد مذهب أهل الرأي والتفريع، ويتوسع في القياس والاستحسان ومراعاة الأعراف التجارية والاجتماعية التي لا تخالف النص الشرعي."
    },
    "حنبلي": {
        "title": "المذهب الحنبلي (الإمام أحمد بن حنبل)",
        "sources": ["نصوص الكتاب والسنة", "فتاوى الصحابة", "تقديم الحديث المرسل/الضعيف على القياس", "القياس (عند الضرورة)", "الاستصحاب", "سد الذرائع"],
        "principles": "مذهب أثرِيّ يعتمد بشدة على النصوص والآثار المرفوعة، ويُقدّم الحديث ولو كان فيه ضعف يسير على الآراء والقياس الإنساني."
    },
    "ظاهري": {
        "title": "المذهب الظاهري (الإمام داود الظاهري وابن حزم)",
        "sources": ["ظاهر القرآن الكريم", "ظاهر السنة النبوية", "إجماع الصحابة القطعي فقط"],
        "principles": "يبطل المذهب القياس والاستحسان والتعليل بالرأي تماماً، ويلتزم بالدلالة اللفظية المباشرة (الظاهر) للنصوص الشرعية."
    },
    "جعفري": {
        "title": "المذهب الجعفري (الإمام جعفر الصادق - الشيعة الإمامية)",
        "sources": ["القرآن الكريم", "السنة المأثورة عن النبي والأئمة", "الإجماع الكاشف عن المعصوم", "دليل العقل"],
        "principles": "يعتمد فتح باب الاجتهاد المستمر، ويستند إلى العقل العملي (الملازمات العقلية) والاستصحاب والبراءة الأصلية في غياب النص."
    },
    "زيدي": {
        "title": "المذهب الزيدي (الإمام زيد بن علي)",
        "sources": ["القرآن الكريم", "السنة النبوية", "إجماع العترة (أهل البيت)", "القياس", "المصالح المرسلة", "دليل العقل"],
        "principles": "يجمع بين المدرسة الحديثية والأصول العقلية والاعتزالية، مع اعتماد مرن على القياس وفتح باب الاجتهاد لكل من استجمع شروطه."
    },
    "إباضي": {
        "title": "المذهب الإباضي (الإمام جابر بن زيد)",
        "sources": ["القرآن الكريم", "السنة النبوية المسندة", "الإجماع", "القياس", "الاستدلال والمصلحة"],
        "principles": "يعتمد على الأسانيد الحديثية المروية في مسند الربيع بن حبيب، ويأخذ بالقياس والمصلحة والعرف بما لا يناقض النص الصريح."
    }
}

# 5. قائمة الدول
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

# 6. عناصر التصفية
col1, col2 = st.columns([2, 1])

with col1:
    madhabs = ["الكل", "مالكي", "شافعي", "حنفي", "حنبلي", "ظاهري", "جعفري", "زيدي", "إباضي"]
    selected_madhab = st.radio("🏷️ اختر المذهب لإظهار أصوله والدول التابعة له:", madhabs, horizontal=True)

with col2:
    search_query = st.text_input("🔍 بحث عن دولة:", placeholder="أدخل اسم الدولة...")

st.markdown("<br>", unsafe_allow_html=True)

# 7. عرض قسم مصادر وقواعد المذهب المختار
if selected_madhab != "الكل" and selected_madhab in MADHAB_INFO:
    info = MADHAB_INFO[selected_madhab]
    chips_html = "".join([f'<span class="source-chip">{src}</span>' for src in info["sources"]])
    
    detail_card_html = (
        f'<div class="madhab-detail-card">'
        f'<div class="madhab-detail-title">📜 مصادر التشريع وأصول {info["title"]}</div>'
        f'<div style="margin-bottom: 8px; font-weight: bold; color: #555;">المصادر والأدلة الشرعية:</div>'
        f'<div class="sources-list">{chips_html}</div>'
        f'<div class="principle-box"><b>💡 أبرز الخصائص والقواعد:</b> {info["principles"]}</div>'
        f'</div>'
    )
    st.markdown(detail_card_html, unsafe_allow_html=True)

# 8. منطق التصفية وعرض البطاقات
filtered_countries = COUNTRIES
if selected_madhab != "الكل":
    filtered_countries = [c for c in filtered_countries if c["madhab"] == selected_madhab]

if search_query:
    filtered_countries = [c for c in filtered_countries if search_query.strip() in c["name"]]

st.subheader("🗺️ الدول والمذاهب الغالبة")

if filtered_countries:
    cards_list = []
    for c in filtered_countries:
        card_html = (
            f'<div class="country-card">'
            f'<div class="country-info">'
            f'<span class="country-flag">{c["flag"]}</span>'
            f'<div>'
            f'<p class="country-name">{c["name"]}</p>'
            f'<p class="country-pop">{c["pop"]}</p>'
            f'</div>'
            f'</div>'
            f'<span class="madhab-badge">{c["madhab"]}</span>'
            f'</div>'
        )
        cards_list.append(card_html)
    
    full_html = f'<div class="countries-grid">{"".join(cards_list)}</div>'
    st.markdown(full_html, unsafe_allow_html=True)
else:
    st.warning("لم يتم العثور على نتائج تطابق شروط البحث.")
