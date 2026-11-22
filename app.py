import streamlit as st
import pandas as pd
import datetime
from groq import Groq
import json
import os

# ============================================================
# PAGE CONFIG
# ============================================================
st.set_page_config(
    page_title="Smart Hospital Staff Manager",
    page_icon="🏥",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ============================================================
# CUSTOM CSS
# ============================================================
st.markdown("""
<style>
    .main-header {
        font-size: 2.2rem;
        font-weight: 800;
        color: #0A5C8A;
        text-align: center;
        padding-bottom: 0.5rem;
    }
    .sub-header {
        font-size: 1rem;
        color: #555;
        text-align: center;
        margin-bottom: 2rem;
    }
    .metric-card {
        background: linear-gradient(135deg, #e8f4fd 0%, #d1ecf9 100%);
        padding: 1rem;
        border-radius: 12px;
        border-left: 5px solid #0A5C8A;
    }
    .ai-box {
        background: #f4f8fb;
        border: 1px solid #b8d8ea;
        border-radius: 10px;
        padding: 1rem;
        margin-top: 1rem;
    }
    .badge-present { color: #1e7e34; font-weight: bold; }
    .badge-absent  { color: #c82333; font-weight: bold; }
    .badge-onleave { color: #e0a800; font-weight: bold; }
</style>
""", unsafe_allow_html=True)

# ============================================================
# GROQ CLIENT
# ============================================================
GROQ_API_KEY = st.secrets.get("GROQ_API_KEY", os.getenv("GROQ_API_KEY", ""))

@st.cache_resource
def get_groq_client(api_key: str):
    if not api_key:
        return None
    return Groq(api_key=api_key)

client = get_groq_client(GROQ_API_KEY)

# Model selection — Groq-supported models
GROQ_MODELS = [
    "llama-3.3-70b-versatile",
    "llama-3.1-8b-instant",
    "mixtral-8x7b-32768",
    "gemma2-9b-it",
]

# ============================================================
# MOCK DATA (replace with DB/API in production)
# ============================================================
def load_staff_data() -> pd.DataFrame:
    data = [
        # ID, Name, Role, Department, Shift, Duty Start, Duty End, Status, Assigned Surgery
        ("D001", "Dr. Arjun Mehta",   "Doctor", "Cardiology",      "Morning", "08:00", "16:00", "Present", "CABG-101"),
        ("D002", "Dr. Priya Nair",    "Doctor", "Neurology",       "Morning", "09:00", "17:00", "Present", "Craniotomy-204"),
        ("D003", "Dr. Rohan Verma",   "Doctor", "Orthopedics",     "Evening", "14:00", "22:00", "Present", "Knee-Replacement-310"),
        ("D004", "Dr. Sneha Kapoor",  "Doctor", "General Surgery", "Night",   "22:00", "06:00", "On Leave", "-"),
        ("D005", "Dr. Vikram Rao",    "Doctor", "Anesthesiology",  "Morning", "07:00", "15:00", "Present", "CABG-101"),
        ("N001", "Nurse Anjali Singh", "Nurse",  "ICU",             "Morning", "08:00", "16:00", "Present", "CABG-101"),
        ("N002", "Nurse Meera Joshi",  "Nurse",  "OT",              "Morning", "08:00", "16:00", "Present", "Craniotomy-204"),
        ("N003", "Nurse Kavita Desai", "Nurse",  "Post-Op",         "Evening", "14:00", "22:00", "Present", "Knee-Replacement-310"),
        ("N004", "Nurse Rahul Patel",  "Nurse",  "Emergency",       "Night",   "22:00", "06:00", "Absent",  "-"),
        ("N005", "Nurse Pooja Reddy",  "Nurse",  "ICU",             "Evening", "14:00", "22:00", "Present", "CABG-101"),
        ("N006", "Nurse Suresh Kumar", "Nurse",  "Ward",            "Morning", "08:00", "16:00", "Present", "-"),
    ]
    cols = ["ID", "Name", "Role", "Department", "Shift",
            "Duty Start", "Duty End", "Status", "Assigned Surgery"]
    return pd.DataFrame(data, columns=cols)

# ============================================================
# SESSION STATE
# ============================================================
if "staff_df" not in st.session_state:
    st.session_state.staff_df = load_staff_data()
if "ai_response" not in st.session_state:
    st.session_state.ai_response = ""

# ============================================================
# HEADER
# ============================================================
st.markdown('<div class="main-header">🏥 Smart Hospital Staff Management</div>', unsafe_allow_html=True)
st.markdown('<div class="sub-header">AI-powered duty tracking, staff presence & surgery dispatch</div>', unsafe_allow_html=True)

if client is None:
    st.error(
        "⚠️ **GROQ_API_KEY not configured.**  \n"
        "Add it in Streamlit Cloud → Settings → Secrets as:  \n"
        "```toml\nGROQ_API_KEY = \"gsk_...\"\n```"
    )

# ============================================================
# SIDEBAR — CONTROLS
# ============================================================
with st.sidebar:
    st.header("⚙️ Controls")
    model_choice = st.selectbox("AI Model (Groq)", GROQ_MODELS, index=0)

    st.subheader("➕ Add / Update Staff")
    with st.form("add_staff"):
        c1, c2 = st.columns(2)
        s_id   = c1.text_input("ID", "D006")
        s_name = c2.text_input("Name", "Dr. New Staff")
        c3, c4 = st.columns(2)
        s_role = c3.selectbox("Role", ["Doctor", "Nurse"])
        s_dept = c4.text_input("Department", "General")
        c5, c6 = st.columns(2)
        s_shift = c5.selectbox("Shift", ["Morning", "Evening", "Night"])
        s_status = c6.selectbox("Status", ["Present", "Absent", "On Leave"])
        c7, c8 = st.columns(2)
        s_start = c7.time_input("Duty Start", datetime.time(8, 0))
        s_end   = c8.time_input("Duty End", datetime.time(16, 0))
        s_surg  = st.text_input("Assigned Surgery", "-")
        submitted = st.form_submit_button("💾 Save Staff")

        if submitted:
            new_row = {
                "ID": s_id, "Name": s_name, "Role": s_role, "Department": s_dept,
                "Shift": s_shift, "Duty Start": s_start.strftime("%H:%M"),
                "Duty End": s_end.strftime("%H:%M"), "Status": s_status,
                "Assigned Surgery": s_surg,
            }
            df = st.session_state.staff_df
            df = df[df["ID"] != s_id]
            st.session_state.staff_df = pd.concat([df, pd.DataFrame([new_row])], ignore_index=True)
            st.success(f"Saved {s_name}")

    st.divider()
    if st.button("🔄 Reset Demo Data"):
        st.session_state.staff_df = load_staff_data()
        st.session_state.ai_response = ""
        st.success("Demo data reloaded")

# ============================================================
# MAIN — METRICS
# ============================================================
df = st.session_state.staff_df
total     = len(df)
doctors   = (df["Role"] == "Doctor").sum()
nurses    = (df["Role"] == "Nurse").sum()
present   = (df["Status"] == "Present").sum()
absent    = (df["Status"] == "Absent").sum()
on_leave  = (df["Status"] == "On Leave").sum()
presence_rate = round((present / total) * 100, 1) if total else 0

m1, m2, m3, m4, m5 = st.columns(5)
m1.metric("👥 Total Staff", total)
m2.metric("👨‍⚕️ Doctors", doctors)
m3.metric("👩‍⚕️ Nurses", nurses)
m4.metric("✅ Present", present, f"{presence_rate}%")
m5.metric("🚫 Absent / Leave", absent + on_leave)

# ============================================================
# MAIN — STAFF TABLE
# ============================================================
st.subheader("📋 Staff Directory & Duty Timings")

def color_status(val):
    return {
        "Present":  "background-color:#d4edda; color:#155724",
        "Absent":   "background-color:#f8d7da; color:#721c24",
        "On Leave": "background-color:#fff3cd; color:#856404",
    }.get(val, "")

filter_role = st.multiselect("Filter by Role", ["Doctor", "Nurse"], default=["Doctor", "Nurse"])
filter_status = st.multiselect("Filter by Status", ["Present", "Absent", "On Leave"],
                               default=["Present", "Absent", "On Leave"])
view = df[df["Role"].isin(filter_role) & df["Status"].isin(filter_status)]

st.dataframe(
    view.style.applymap(color_status, subset=["Status"]),
    use_container_width=True,
    height=420,
)

# ============================================================
# MAIN — SURGERY DISPATCH
# ============================================================
st.subheader("🩺 Surgery Dispatch Board")
surgeries = df[df["Assigned Surgery"] != "-"][["Assigned Surgery", "Name", "Role", "Shift", "Status"]]
if surgeries.empty:
    st.info("No surgeries assigned currently.")
else:
    pivoted = surgeries.groupby("Assigned Surgery")["Name"].apply(lambda x: ", ".join(x)).reset_index()
    pivoted.columns = ["Surgery ID", "Assigned Staff"]
    st.dataframe(pivoted, use_container_width=True)

# ============================================================
# AI SMART MANAGER
# ============================================================
st.subheader("🤖 AI Smart Manager (Groq)")
st.caption(f"Powered by `{model_choice}` — analyzes staff data & recommends dispatch actions.")

col_a, col_b = st.columns([3, 1])
with col_a:
    user_query = st.text_area(
        "Ask the AI manager",
        value="Analyze current staff presence and recommend which staff to dispatch to pending surgeries. "
              "Highlight risks and suggest replacements for absent staff.",
        height=110,
    )
with col_b:
    st.write("")
    st.write("")
    run_ai = st.button("🚀 Run AI Analysis", type="primary", use_container_width=True)

def build_context(df: pd.DataFrame) -> str:
    return f"""
HOSPITAL STAFF DATA (as of {datetime.datetime.now().strftime('%Y-%m-%d %H:%M')}):
{df.to_markdown(index=False)}

SUMMARY:
- Total staff: {len(df)}
- Doctors: {(df['Role']=='Doctor').sum()}
- Nurses: {(df['Role']=='Nurse').sum()}
- Present: {(df['Status']=='Present').sum()}
- Absent: {(df['Status']=='Absent').sum()}
- On Leave: {(df['Status']=='On Leave').sum()}
"""

SYSTEM_PROMPT = """You are a senior hospital operations AI assistant.
You receive live staff roster data and must:
1. Summarize current staff presence & duty coverage.
2. Identify gaps (absent staff, under-covered surgeries, shift overlaps).
3. Recommend concrete staff dispatch decisions for surgeries.
4. Flag risks and suggest contingency actions.
Respond in crisp bullet points with a short 'Recommended Dispatch Plan' table.
Be precise, avoid hallucination, and base every claim strictly on the provided data."""

if run_ai:
    if client is None:
        st.error("Groq client not initialized — set GROQ_API_KEY in secrets.")
    elif not user_query.strip():
        st.warning("Please enter a query.")
    else:
        with st.spinner("AI is analyzing the roster..."):
            try:
                context = build_context(df)
                completion = client.chat.completions.create(
                    model=model_choice,
                    messages=[
                        {"role": "system", "content": SYSTEM_PROMPT},
                        {"role": "user",   "content": f"{context}\n\nREQUEST:\n{user_query}"},
                    ],
                    temperature=0.3,
                    max_tokens=1200,
                )
                st.session_state.ai_response = completion.choices[0].message.content
            except Exception as e:
                st.error(f"Groq API error: {e}")

if st.session_state.ai_response:
    st.markdown('<div class="ai-box">', unsafe_allow_html=True)
    st.markdown("### 🧠 AI Recommendations")
    st.markdown(st.session_state.ai_response)
    st.markdown("</div>", unsafe_allow_html=True)

    st.download_button(
        "⬇️ Download AI Report",
        st.session_state.ai_response,
        file_name=f"hospital_ai_report_{datetime.date.today()}.md",
        mime="text/markdown",
    )

# ============================================================
# FOOTER
# ============================================================
st.divider()
st.caption("🏥 Smart Hospital Staff Manager · Built with Streamlit + Groq · Deployable on Streamlit Cloud")
