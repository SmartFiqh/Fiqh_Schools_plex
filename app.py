from flask import Flask, render_template_string, request, jsonify

app = Flask(__name__)

# قائمة الدول مع تحديد مذهب سائد واحد لكل دولة
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

HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="ar" dir="rtl">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>الجامع المختصر لآراء المذاهب</title>
    <link href="https://fonts.googleapis.com/css2?family=Amiri:wght@400;700&family=Tajawal:wght@400;500;700&display=swap" rel="stylesheet">
    <style>
        :root {
            --primary-color: #1b4332;
            --primary-light: #2d6a4f;
            --accent-color: #d4af37;
            --bg-color: #f8f9fa;
            --card-bg: #ffffff;
            --text-main: #212529;
            --text-muted: #6c757d;
            --border-color: #e9ecef;
            --radius-lg: 16px;
            --radius-md: 10px;
            --shadow-sm: 0 2px 8px rgba(0,0,0,0.04);
            --shadow-md: 0 4px 16px rgba(0,0,0,0.08);
        }

        * { box-sizing: border-box; margin: 0; padding: 0; }

        body {
            font-family: 'Tajawal', sans-serif;
            background-color: var(--bg-color);
            color: var(--text-main);
            line-height: 1.6;
            padding: 20px;
        }

        .container { max-width: 1100px; margin: 0 auto; }

        .app-header {
            text-align: center;
            padding: 30px 20px;
            background: linear-gradient(135deg, var(--primary-color), var(--primary-light));
            color: white;
            border-radius: var(--radius-lg);
            margin-bottom: 25px;
            box-shadow: var(--shadow-md);
        }

        .app-header h1 {
            font-family: 'Amiri', serif;
            font-size: 2.2rem;
            margin-bottom: 8px;
            color: var(--accent-color);
        }

        .controls-card {
            background: var(--card-bg);
            padding: 20px;
            border-radius: var(--radius-lg);
            box-shadow: var(--shadow-sm);
            border: 1px solid var(--border-color);
            margin-bottom: 25px;
        }

        .section-title {
            font-size: 1rem;
            font-weight: 700;
            margin-bottom: 12px;
            color: var(--primary-color);
        }

        .madhab-grid {
            display: grid;
            grid-template-columns: repeat(auto-fill, minmax(110px, 1fr));
            gap: 10px;
            margin-bottom: 20px;
        }

        .madhab-chip {
            background: #f1f3f5;
            border: 1px solid var(--border-color);
            border-radius: var(--radius-md);
            padding: 8px 12px;
            text-align: center;
            cursor: pointer;
            font-size: 0.9rem;
            transition: all 0.2s ease;
            user-select: none;
        }

        .madhab-chip:hover { background: #e9ecef; }

        .madhab-chip.active {
            background: var(--primary-color);
            color: white;
            border-color: var(--primary-color);
            font-weight: bold;
        }

        .search-input {
            width: 100%;
            padding: 12px 16px;
            border: 1px solid var(--border-color);
            border-radius: var(--radius-md);
            font-size: 1rem;
            font-family: inherit;
            outline: none;
        }

        .nav-pills {
            display: flex;
            gap: 10px;
            overflow-x: auto;
            padding-bottom: 10px;
            margin-bottom: 20px;
        }

        .nav-pill {
            padding: 8px 16px;
            background: var(--card-bg);
            border: 1px solid var(--border-color);
            border-radius: 20px;
            font-size: 0.85rem;
            white-space: nowrap;
            cursor: pointer;
        }

        .nav-pill.active {
            background: var(--accent-color);
            color: #000;
            font-weight: bold;
            border-color: var(--accent-color);
        }

        .countries-grid {
            display: grid;
            grid-template-columns: repeat(auto-fill, minmax(260px, 1fr));
            gap: 15px;
        }

        .country-card {
            background: var(--card-bg);
            padding: 16px;
            border-radius: var(--radius-md);
            border: 1px solid var(--border-color);
            box-shadow: var(--shadow-sm);
            display: flex;
            align-items: center;
            justify-content: space-between;
        }

        .country-info { display: flex; align-items: center; gap: 12px; }
        .country-flag { font-size: 1.8rem; }
        .country-name { font-weight: 700; font-size: 1rem; }
        .country-pop { font-size: 0.8rem; color: var(--text-muted); }

        .madhab-badge {
            background: #e8f5e9;
            color: var(--primary-color);
            padding: 4px 10px;
            border-radius: 12px;
            font-size: 0.8rem;
            font-weight: 700;
        }
    </style>
</head>
<body>

<div class="container">
    <header class="app-header">
        <h1>الجامع المختصر لآراء المذاهب 📚</h1>
        <p>منصة تعليمية للمقارنة الفقهية، وليست موقعًا للإفتاء</p>
    </header>

    <div class="controls-card">
        <div class="section-title">اختر المذهب الفقهي:</div>
        <div class="madhab-grid" id="madhabGrid">
            {% for m in ['مالكي', 'شافعي', 'حنفي', 'حنبلي', 'ظاهري', 'جعفري', 'زيدي', 'إباضي'] %}
                <div class="madhab-chip" onclick="filterByMadhab('{{ m }}', this)">{{ m }}</div>
            {% endfor %}
        </div>

        <input type="text" id="searchInput" oninput="filterCountries()" class="search-input" placeholder="بحث عن دولة...">
    </div>

    <div class="nav-pills">
        <div class="nav-pill active">🗺️ الدول والمذاهب الغالبة</div>
        <div class="nav-pill">📜 مصادر التشريع الفقهي</div>
        <div class="nav-pill">📚 المصطلحات الفقهية</div>
        <div class="nav-pill">📘 الأصول والقواعد الفقهية</div>
        <div class="nav-pill">💬 ملاحظات الجلسة</div>
    </div>

    <div class="countries-grid" id="countriesGrid">
        {% for c in countries %}
        <div class="country-card" data-madhab="{{ c.madhab }}" data-name="{{ c.name }}">
            <div class="country-info">
                <span class="country-flag">{{ c.flag }}</span>
                <div>
                    <div class="country-name">{{ c.name }}</div>
                    <div class="country-pop">{{ c.pop }}</div>
                </div>
            </div>
            <span class="madhab-badge">{{ c.madhab }}</span>
        </div>
        {% endfor %}
    </div>
</div>

<script>
    let activeMadhab = null;

    function filterByMadhab(madhab, element) {
        const chips = document.querySelectorAll('.madhab-chip');
        if (activeMadhab === madhab) {
            activeMadhab = null;
            element.classList.remove('active');
        } else {
            chips.forEach(c => c.classList.remove('active'));
            activeMadhab = madhab;
            element.classList.add('active');
        }
        filterCountries();
    }

    function filterCountries() {
        const query = document.getElementById('searchInput').value.toLowerCase();
        const cards = document.querySelectorAll('.country-card');

        cards.forEach(card => {
            const name = card.getAttribute('data-name');
            const madhab = card.getAttribute('data-madhab');

            const matchesSearch = name.includes(query);
            const matchesMadhab = !activeMadhab || madhab === activeMadhab;

            if (matchesSearch && matchesMadhab) {
                card.style.display = 'flex';
            } else {
                card.style.display = 'none';
            }
        });
    }
</script>

</body>
</html>
"""

@app.route('/')
def home():
    return render_template_string(HTML_TEMPLATE, countries=COUNTRIES)

@app.route('/api/countries', methods=['GET'])
def get_countries():
    return jsonify(COUNTRIES)

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)
