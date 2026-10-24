# app.py - UniPath AI | Multi-Agent University Admission System

import streamlit as st
import sqlite3
from datetime import datetime
import time
import os
from dotenv import load_dotenv

load_dotenv()

from config import UNIVERSITIES, get_eligibility_color, get_deadline_color
from chatbot import get_chatbot_response
from scraper import get_data_source_label

# ─────────────────────────────────────────────
# PAGE CONFIG
# ─────────────────────────────────────────────
st.set_page_config(
    page_title="UniPath AI",
    page_icon="🎓",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ─────────────────────────────────────────────
# CSS
# ─────────────────────────────────────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;600;700&display=swap');

html, body, [class*="css"] { font-family: 'Inter', sans-serif; }

.header {
    background: linear-gradient(135deg, #0f2027, #203a43, #2c5364);
    padding: 2rem 2.5rem;
    border-radius: 16px;
    color: white;
    margin-bottom: 1.5rem;
    text-align: center;
}
.header h1 { font-size: 2.4rem; margin: 0; font-weight: 700; }
.header p  { font-size: 1rem; margin: 0.3rem 0 0; opacity: 0.85; }

.uni-card {
    background: white;
    border-radius: 14px;
    padding: 1.2rem 1.4rem;
    margin-bottom: 1rem;
    border-left: 5px solid #2c5364;
    box-shadow: 0 2px 12px rgba(0,0,0,0.08);
}
.badge {
    display: inline-block;
    padding: 2px 10px;
    border-radius: 20px;
    font-size: 0.72rem;
    font-weight: 600;
    margin-left: 6px;
}
.agent-box {
    background: #f8f9fa;
    border-radius: 10px;
    padding: 0.6rem 1rem;
    margin-bottom: 0.5rem;
    font-size: 0.85rem;
}
.deadline-row {
    display: flex;
    align-items: center;
    justify-content: space-between;
    padding: 0.5rem 0.8rem;
    border-radius: 8px;
    margin-bottom: 0.4rem;
    background: #f8f9fa;
    font-size: 0.85rem;
}
.footer {
    text-align: center;
    color: #888;
    font-size: 0.72rem;
    margin-top: 2rem;
    padding-top: 1rem;
    border-top: 1px solid #eee;
}
</style>
""", unsafe_allow_html=True)

# ─────────────────────────────────────────────
# DATABASE
# ─────────────────────────────────────────────
def init_db():
    conn = sqlite3.connect("unipath.db")
    c = conn.cursor()
    c.execute("""CREATE TABLE IF NOT EXISTS students (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT UNIQUE,
        ssc1 REAL, ssc2 REAL, hssc1 REAL, hssc2 REAL,
        field TEXT, budget INTEGER, category TEXT,
        date TEXT
    )""")
    conn.commit()
    conn.close()

def save_student(name, ssc1, ssc2, hssc1, hssc2, field, budget, category):
    conn = sqlite3.connect("unipath.db")
    c = conn.cursor()
    c.execute("""INSERT INTO students (name,ssc1,ssc2,hssc1,hssc2,field,budget,category,date)
                 VALUES (?,?,?,?,?,?,?,?,?)
                 ON CONFLICT(name) DO UPDATE SET
                 ssc1=excluded.ssc1, ssc2=excluded.ssc2,
                 hssc1=excluded.hssc1, hssc2=excluded.hssc2,
                 field=excluded.field, budget=excluded.budget,
                 category=excluded.category, date=excluded.date""",
              (name, ssc1, ssc2, hssc1, hssc2, field, budget, category,
               datetime.now().isoformat()))
    conn.commit()
    conn.close()

def load_student(name):
    conn = sqlite3.connect("unipath.db")
    c = conn.cursor()
    c.execute("SELECT * FROM students WHERE name=? ORDER BY id DESC LIMIT 1", (name,))
    row = c.fetchone()
    conn.close()
    return row

init_db()

# ─────────────────────────────────────────────
# AGENTS
# ─────────────────────────────────────────────
def agent_search(category, field, budget):
    results = []
    field_map = {
        "Computer Science": ["Computer Science", "Software Engineering", "Artificial Intelligence",
                             "Data Science", "Cyber Security", "Information Technology"],
        "Engineering":      ["Electrical Engineering", "Mechanical Engineering", "Civil Engineering",
                             "Chemical Engineering", "Mechatronics", "Petroleum Engineering"],
        "Medical":          ["MBBS", "BDS", "Nursing", "Pharmacy", "Bioinformatics"],
        "Business":         ["Business Administration", "BBA", "Economics", "Accounting", "Finance",
                             "Management Sciences"],
        "Law":              ["Law", "LLB"],
        "Arts & Design":    ["Architecture", "Textile Design", "Fashion Design", "Mass Communication",
                             "Media Studies", "Psychology", "Education"],
        "All Fields":       None,
    }
    keywords = field_map.get(field)

    for uni_name, uni_data in UNIVERSITIES.items():
        if category != "All" and uni_data["category"] != category:
            continue
        for prog_name, prog_data in uni_data["programs"].items():
            if keywords is not None:
                if not any(k.lower() in prog_name.lower() for k in keywords):
                    continue
            if prog_data["fee"] > budget:
                continue
            results.append({
                "university": uni_name,
                "program": prog_name,
                "category": uni_data["category"],
                "merit": prog_data["merit"],
                "fee": prog_data["fee"],
                "test": uni_data["test"],
                "test_date": uni_data["test_date"],
                "deadline": uni_data["deadline"],
                "scholarships": uni_data["scholarships"],
                "hostel": uni_data["hostel"],
                "ranking": uni_data["ranking"],
            })
    return results


def agent_filter(results, student_pct):
    for r in results:
        status, color = get_eligibility_color(student_pct, r["merit"])
        r["eligibility_status"] = status
        r["eligibility_color"] = color
        r["gap"] = round(student_pct - r["merit"], 1)
    return results


def agent_rank(results, student_pct, budget):
    for r in results:
        score = 0
        if student_pct >= r["merit"]:          score += 50
        elif student_pct >= r["merit"] - 5:    score += 30
        else:                                   score += 10
        if budget >= r["fee"]:                  score += 30
        elif budget >= r["fee"] * 0.7:          score += 15
        else:                                   score += 5
        if r["scholarships"]:                   score += 10
        if r["hostel"]:                         score += 10
        r["match_score"] = min(score, 100)
    return sorted(results, key=lambda x: (
        0 if "Eligible" in x["eligibility_status"] else
        1 if "Borderline" in x["eligibility_status"] else 2,
        x["deadline"]
    ))


def agent_counsel(top, name, pct):
    if not top:
        return "No matching universities found. Try adjusting your filters."
    t = top[0]
    return f"""
### 🎯 Personalized Roadmap for **{name}**

**Your Score:** {pct:.1f}%

#### 🥇 Top Match: {t['university']}
- **Program:** {t['program']}
- **Match Score:** {t['match_score']}%
- **Eligibility:** {t['eligibility_status']}

#### 📋 Action Plan
1. **Register for:** {t['test']} — test date: {t['test_date']}
2. **Apply before:** {t['deadline']}
3. **Fee per semester:** PKR {t['fee']:,}
4. **Scholarship:** {'Available ✅' if t['scholarships'] else 'Not available ❌'}
5. **Documents:** SSC & HSSC certificates, CNIC/B-Form, passport photos, domicile

#### 🏛️ Backup Options
{"**2nd choice:** " + top[1]['university'] + " — " + top[1]['program'] if len(top) > 1 else ""}
{"**3rd choice:** " + top[2]['university'] + " — " + top[2]['program'] if len(top) > 2 else ""}
"""

# ─────────────────────────────────────────────
# HEADER
# ─────────────────────────────────────────────
st.markdown("""
<div class="header">
    <h1>🎓 UniPath AI</h1>
    <p>Multi-Agent University Admission System &nbsp;·&nbsp; Lahore, Pakistan &nbsp;·&nbsp; 15 Universities &nbsp;·&nbsp; 60+ Programs</p>
    <p style="font-size:0.82rem;opacity:0.7;">4 AI Agents &nbsp;|&nbsp; Live Scraping &nbsp;|&nbsp; Gemini Chatbot &nbsp;|&nbsp; SQLite Memory</p>
</div>
""", unsafe_allow_html=True)

# ─────────────────────────────────────────────
# SIDEBAR
# ─────────────────────────────────────────────
with st.sidebar:
    st.markdown("## 📝 Student Profile")

    name = st.text_input("Full Name", placeholder="Enter your name")

    # Returning student detection
    if name:
        existing = load_student(name)
        if existing:
            st.success(f"👋 Welcome back, {name}! Profile loaded.")
            default_ssc1  = existing[2]
            default_ssc2  = existing[3]
            default_hssc1 = existing[4]
            default_hssc2 = existing[5]
            default_field  = existing[6]
            default_budget = existing[7]
            default_cat    = existing[8]
        else:
            default_ssc1 = default_ssc2 = default_hssc1 = default_hssc2 = 70.0
            default_field  = "Computer Science"
            default_budget = 150000
            default_cat    = "All"
    else:
        default_ssc1 = default_ssc2 = default_hssc1 = default_hssc2 = 70.0
        default_field  = "Computer Science"
        default_budget = 150000
        default_cat    = "All"

    st.markdown("### 📚 Academic Marks")
    col1, col2 = st.columns(2)
    with col1:
        ssc1  = st.number_input("SSC Part 1 (9th)",  0.0, 100.0, float(default_ssc1),  step=0.5)
        hssc1 = st.number_input("HSSC Part 1 (11th)", 0.0, 100.0, float(default_hssc1), step=0.5)
    with col2:
        ssc2  = st.number_input("SSC Part 2 (10th)", 0.0, 100.0, float(default_ssc2),  step=0.5)
        hssc2 = st.number_input("HSSC Part 2 (12th)", 0.0, 100.0, float(default_hssc2), step=0.5)

    ssc_avg   = (ssc1 + ssc2) / 2
    hssc_avg  = (hssc1 + hssc2) / 2
    overall   = round((ssc_avg * 0.4 + hssc_avg * 0.6), 2)

    st.info(f"📊 SSC: **{ssc_avg:.1f}%** | HSSC: **{hssc_avg:.1f}%** | Overall: **{overall:.1f}%**")

    st.markdown("### 💰 Budget")
    budget = st.number_input("Per Semester (PKR)", 10000, 1000000,
                              int(default_budget), step=10000)

    if budget < 50000:
        st.warning("💡 Budget < PKR 50,000 — Highlighting **Public** universities for you!")

    st.markdown("### 🎯 Preferences")
    field = st.selectbox("Preferred Field", [
        "Computer Science", "Engineering", "Medical",
        "Business", "Law", "Arts & Design", "All Fields"
    ], index=["Computer Science","Engineering","Medical","Business","Law","Arts & Design","All Fields"].index(
        default_field if default_field in ["Computer Science","Engineering","Medical","Business","Law","Arts & Design","All Fields"] else "Computer Science"
    ))

    category = st.selectbox("University Type",
        ["All", "Public", "Private", "Semi-Govt"],
        index=["All","Public","Private","Semi-Govt"].index(
            default_cat if default_cat in ["All","Public","Private","Semi-Govt"] else "All"
        )
    )

    st.markdown("---")
    st.markdown("### 🤖 AI Agents")
    st.markdown("1️⃣ **Search** — scans all universities")
    st.markdown("2️⃣ **Filter** — checks eligibility")
    st.markdown("3️⃣ **Ranking** — scores each match")
    st.markdown("4️⃣ **Counselor** — builds your roadmap")

    go = st.button("🚀 Find My Universities", type="primary", use_container_width=True)

# ─────────────────────────────────────────────
# MAIN RESULTS
# ─────────────────────────────────────────────
if go and name:
    save_student(name, ssc1, ssc2, hssc1, hssc2, field, budget, category)

    # ── Agent progress bars ──────────────────
    st.markdown("### 🤖 Multi-Agent Progress")
    agents_ui = [
        ("🔍 Agent 1: Search", "Scanning 15 universities..."),
        ("⚙️ Agent 2: Filter", "Checking eligibility..."),
        ("📊 Agent 3: Ranking", "Calculating match scores..."),
        ("💬 Agent 4: Counselor", "Building your roadmap..."),
    ]
    bars = []
    for label, msg in agents_ui:
        col_l, col_b = st.columns([1, 3])
        with col_l:
            st.markdown(f"**{label}**")
        with col_b:
            bars.append(st.progress(0, text=msg))

    # Run agents with animated bars
    time.sleep(0.3); bars[0].progress(100, text="✅ Search complete")
    results = agent_search(category, field, budget)

    time.sleep(0.3); bars[1].progress(100, text="✅ Eligibility checked")
    results = agent_filter(results, overall)

    time.sleep(0.3); bars[2].progress(100, text="✅ Ranking done")
    results = agent_rank(results, overall, budget)

    time.sleep(0.3); bars[3].progress(100, text="✅ Roadmap ready")
    roadmap = agent_counsel(results, name, overall)

    st.markdown("---")

    if not results:
        st.warning("⚠️ No universities found. Try changing your field, category, or budget.")
    else:
        # ── Summary metrics ──────────────────
        eligible   = sum(1 for r in results if "Eligible" in r["eligibility_status"] and "Not" not in r["eligibility_status"])
        borderline = sum(1 for r in results if "Borderline" in r["eligibility_status"])
        not_elig   = sum(1 for r in results if "Not Eligible" in r["eligibility_status"])
        avg_fee    = sum(r["fee"] for r in results) // len(results)

        c1, c2, c3, c4 = st.columns(4)
        c1.metric("🎯 Programs Found", len(results))
        c2.metric("✅ Eligible",       eligible)
        c3.metric("⚠️ Borderline",    borderline)
        c4.metric("💰 Avg Fee/Sem",   f"PKR {avg_fee:,}")

        # ── Tabs ─────────────────────────────
        tab1, tab2, tab3 = st.tabs(["🏛️ University Results", "📅 Deadline Tracker", "🗺️ AI Roadmap"])

        # TAB 1 — Results
        with tab1:
            st.markdown(f"**Showing {len(results)} programs for {name} ({overall:.1f}%)**")

            # Per-university progress bars
            seen_unis = []
            uni_progress = {}
            for r in results:
                if r["university"] not in seen_unis:
                    seen_unis.append(r["university"])

            st.markdown("#### 📡 Live Data Status")
            prog_cols = st.columns(min(len(seen_unis), 5))
            for i, uni in enumerate(seen_unis[:10]):
                with prog_cols[i % 5]:
                    label = get_data_source_label(uni)
                    st.markdown(f"<small>{uni.split()[0]}<br><b>{label}</b></small>", unsafe_allow_html=True)

            st.markdown("---")

            for r in results:
                deadline_text, deadline_color = get_deadline_color(r["deadline"])
                gap_str = f"+{r['gap']}%" if r["gap"] >= 0 else f"{r['gap']}%"
                gap_color = "#28a745" if r["gap"] >= 0 else "#dc3545"

                cat_colors = {"Public": "#007bff", "Private": "#6f42c1", "Semi-Govt": "#fd7e14"}
                cat_color  = cat_colors.get(r["category"], "#6c757d")

                st.markdown(f"""
                <div class="uni-card">
                    <div style="display:flex;justify-content:space-between;align-items:center;flex-wrap:wrap;gap:0.5rem;">
                        <div>
                            <strong style="font-size:1.05rem;">{r['university']}</strong>
                            <span class="badge" style="background:{cat_color};color:white;">{r['category']}</span>
                            <span class="badge" style="background:#e9ecef;color:#333;">Rank #{r['ranking']}</span>
                        </div>
                        <div style="background:{r['eligibility_color']};color:{'white' if r['eligibility_color']!='#ffc107' else '#333'};
                                    padding:4px 14px;border-radius:20px;font-weight:700;font-size:0.85rem;">
                            {r['eligibility_status']}
                        </div>
                    </div>

                    <div style="margin-top:0.5rem;font-size:0.95rem;color:#444;">
                        📘 <strong>{r['program']}</strong>
                    </div>

                    <div style="display:flex;flex-wrap:wrap;gap:1.2rem;margin-top:0.8rem;font-size:0.82rem;">
                        <div>🎯 Merit<br><strong>{r['merit']}%</strong></div>
                        <div>📈 Your Score<br><strong style="color:{gap_color};">{overall:.1f}% ({gap_str})</strong></div>
                        <div>💰 Fee/Sem<br><strong>PKR {r['fee']:,}</strong></div>
                        <div>📝 Entry Test<br><strong>{r['test']}</strong></div>
                        <div>📅 Deadline<br><strong style="color:{deadline_color};">{deadline_text}</strong></div>
                        <div>🏆 Match<br><strong style="font-size:1.1rem;color:#2c5364;">{r['match_score']}%</strong></div>
                    </div>

                    <div style="margin-top:0.8rem;background:#e9ecef;border-radius:10px;height:7px;">
                        <div style="background:linear-gradient(90deg,#0f2027,#2c5364);
                                    width:{r['match_score']}%;height:7px;border-radius:10px;"></div>
                    </div>

                    <div style="margin-top:0.5rem;font-size:0.72rem;color:#888;">
                        🏠 Hostel: {'Yes' if r['hostel'] else 'No'} &nbsp;|&nbsp;
                        🎓 Scholarship: {'Available' if r['scholarships'] else 'None'} &nbsp;|&nbsp;
                        📆 Test Date: {r['test_date']}
                    </div>
                </div>
                """, unsafe_allow_html=True)

        # TAB 2 — Deadline Tracker
        with tab2:
            st.markdown("### 📅 Deadline Tracker — Sorted by Urgency")

            # Get unique universities sorted by deadline
            seen = set()
            deadline_list = []
            for r in sorted(results, key=lambda x: x["deadline"]):
                if r["university"] not in seen:
                    seen.add(r["university"])
                    deadline_list.append(r)

            for r in deadline_list:
                deadline_text, deadline_color = get_deadline_color(r["deadline"])
                elig_icon = "✅" if "Eligible" in r["eligibility_status"] and "Not" not in r["eligibility_status"] else \
                            "⚠️" if "Borderline" in r["eligibility_status"] else "❌"
                st.markdown(f"""
                <div class="deadline-row" style="border-left:4px solid {deadline_color};">
                    <div>
                        <strong>{r['university']}</strong>
                        <span style="color:#888;font-size:0.78rem;margin-left:8px;">{r['deadline']}</span>
                    </div>
                    <div style="display:flex;gap:1.5rem;align-items:center;">
                        <span>{elig_icon} {r['eligibility_status']}</span>
                        <span style="color:{deadline_color};font-weight:700;">{deadline_text}</span>
                    </div>
                </div>
                """, unsafe_allow_html=True)

        # TAB 3 — Roadmap
        with tab3:
            st.markdown(roadmap)

elif go and not name:
    st.error("⚠️ Please enter your name in the sidebar first.")

# ─────────────────────────────────────────────
# CHATBOT
# ─────────────────────────────────────────────
st.markdown("---")
st.markdown("## 💬 Ask UniPath AI (GIRIGO)")

# Quick question buttons
qc1, qc2, qc3, qc4 = st.columns(4)
with qc1:
    if st.button("💰 Lowest Fee"):
        st.session_state.chat_q = "Which university has the lowest fee?"
with qc2:
    if st.button("📅 Nearest Deadline"):
        st.session_state.chat_q = "Which deadline is closest?"
with qc3:
    if st.button("📝 FAST Requirements"):
        st.session_state.chat_q = "What are the requirements for FAST Lahore?"
with qc4:
    if st.button("🎓 LUMS Info"):
        st.session_state.chat_q = "Tell me about LUMS admissions."

user_q = st.text_input("Type your question:", placeholder="e.g. Am I eligible for UET? What is ECAT?",
                        value=st.session_state.get("chat_q", ""))

if user_q:
    context = "\n".join([
        f"{u}: programs={list(d['programs'].keys())}, test={d['test']}, deadline={d['deadline']}, "
        f"category={d['category']}, scholarships={d['scholarships']}"
        for u, d in UNIVERSITIES.items()
    ])
    with st.spinner("🤖 Thinking..."):
        reply = get_chatbot_response(user_q, context)

    st.markdown(f"""
    <div style="background:#f0f7ff;border-left:4px solid #2c5364;
                border-radius:12px;padding:1rem 1.2rem;margin-top:0.5rem;">
        <strong>🤖 UniPath AI:</strong><br>{reply}
    </div>
    """, unsafe_allow_html=True)

    if "chat_q" in st.session_state:
        del st.session_state["chat_q"]

# ─────────────────────────────────────────────
# FOOTER
# ─────────────────────────────────────────────
st.markdown("""
<div class="footer">
    🎓 UniPath AI &nbsp;|&nbsp; 4 AI Agents &nbsp;|&nbsp; 15 Universities &nbsp;|&nbsp; 60+ Programs &nbsp;|&nbsp; Lahore, Pakistan<br>
    Powered by Streamlit · SQLite · Gemini 1.5 Flash · BeautifulSoup
</div>
""", unsafe_allow_html=True)
