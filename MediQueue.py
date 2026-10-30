import sqlite3
import heapq
import subprocess
import sys
from datetime import datetime
from pathlib import Path

try:
    import streamlit as st
    import pandas as pd
except ModuleNotFoundError as exc:
    missing = exc.name or "a required package"
    print(
        f"Missing dependency: {missing}\n\n"
        "Open PowerShell in this file's folder and run:\n"
        "  python -m pip install --upgrade streamlit pandas\n\n"
        "Then launch with either:\n"
        "  python -m streamlit run MediQueue.py\n"
        "or simply:\n"
        "  python MediQueue.py"
    )
    raise SystemExit(1)

# If launched with `python MediQueue.py`, hand off to Streamlit automatically.
# A light theme is forced so text is never white-on-white when the OS/browser is in dark mode.
try:
    from streamlit.runtime.scriptrunner import get_script_run_ctx
    _streamlit_context = get_script_run_ctx(suppress_warning=True)
except (ImportError, TypeError):
    _streamlit_context = None

if _streamlit_context is None and __name__ == "__main__":
    raise SystemExit(
        subprocess.call([
            sys.executable, "-m", "streamlit", "run", str(Path(__file__).resolve()),
            "--theme.base", "light",
            "--theme.primaryColor", "#176b87",
            "--theme.backgroundColor", "#f5f7fb",
            "--theme.secondaryBackgroundColor", "#ffffff",
            "--theme.textColor", "#10243a",
        ])
    )

APP_DIR = Path(__file__).parent
DB_PATH = APP_DIR / "hospital.db"

st.set_page_config(
    page_title="MediQueue | Emergency Management",
    page_icon="🏥",
    layout="wide",
    initial_sidebar_state="expanded",
)


# ---------- Streamlit version compatibility ----------
def _rerun():
    if hasattr(st, "rerun"):
        st.rerun()
    else:
        st.experimental_rerun()


def show_df(df):
    """Full-width dataframe that works on old and new Streamlit versions."""
    try:
        st.dataframe(df, width="stretch", hide_index=True)
    except (TypeError, st.errors.StreamlitAPIException):
        st.dataframe(df, use_container_width=True, hide_index=True)


def wide_button(label, **kwargs):
    try:
        return st.button(label, width="stretch", **kwargs)
    except (TypeError, st.errors.StreamlitAPIException):
        return st.button(label, use_container_width=True, **kwargs)


# ---------- Database ----------
def get_connection():
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    conn = get_connection()
    try:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS patients (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                age INTEGER NOT NULL,
                gender TEXT NOT NULL,
                phone TEXT,
                symptoms TEXT NOT NULL,
                category TEXT NOT NULL,
                priority INTEGER NOT NULL,
                status TEXT NOT NULL DEFAULT 'Waiting',
                registered_at TEXT NOT NULL,
                called_at TEXT,
                notes TEXT
            )
        """)
        conn.commit()
    finally:
        conn.close()


def run_query(query, params=(), fetch=False):
    """Run a query and always close the connection (sqlite3's `with` does not close it)."""
    conn = get_connection()
    try:
        cur = conn.execute(query, params)
        rows = cur.fetchall() if fetch else None
        conn.commit()
        return rows
    finally:
        conn.close()


init_db()

PRIORITIES = {"Critical": 1, "Serious": 2, "Moderate": 3, "Minor": 4}
STATUS_OPTIONS = ["Waiting", "In Treatment", "Completed"]
PAGES = ["Dashboard", "Register Patient", "Live Queue", "Patient Records", "Analytics", "About Project"]


def now_str():
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def get_all_patients():
    rows = run_query("SELECT * FROM patients ORDER BY id DESC", fetch=True)
    return [dict(r) for r in rows]


def get_waiting_heap():
    rows = run_query(
        "SELECT id, name, category, priority, registered_at FROM patients WHERE status='Waiting'",
        fetch=True,
    )
    heap = []
    for row in rows:
        # Registration time and ID provide stable ordering for equal priorities.
        heapq.heappush(heap, (row["priority"], row["registered_at"], row["id"], row["name"], row["category"]))
    return heap


def metric_count(query):
    result = run_query(query, fetch=True)
    return result[0][0] if result else 0


def add_patient(data):
    conn = get_connection()
    try:
        cur = conn.execute(
            """INSERT INTO patients
            (name, age, gender, phone, symptoms, category, priority, status, registered_at, notes)
            VALUES (?, ?, ?, ?, ?, ?, ?, 'Waiting', ?, ?)""",
            (
                data["name"], data["age"], data["gender"], data["phone"],
                data["symptoms"], data["category"], PRIORITIES[data["category"]],
                now_str(), data["notes"],
            ),
        )
        conn.commit()
        return cur.lastrowid  # exact ID of the row just inserted
    finally:
        conn.close()


def next_waiting_patient():
    heap = get_waiting_heap()
    if not heap:
        return None
    _, _, patient_id, _, _ = heapq.heappop(heap)
    run_query("UPDATE patients SET status='In Treatment', called_at=? WHERE id=?", (now_str(), patient_id))
    return run_query("SELECT * FROM patients WHERE id=?", (patient_id,), fetch=True)[0]


def flash(kind, message):
    st.session_state["flash"] = (kind, message)


def show_flash():
    item = st.session_state.pop("flash", None)
    if item:
        kind, message = item
        getattr(st, kind)(message)


def go_to(page_name):
    """Callback used by the quick-action buttons to switch pages."""
    st.session_state["page"] = page_name


if "page" not in st.session_state:
    st.session_state["page"] = "Dashboard"

# ---------- Styling ----------
# Colours are set explicitly for every text element so nothing depends on the
# user's light/dark theme (this is what caused the invisible white-on-white text).
st.markdown("""
<style>
    .stApp, [data-testid="stAppViewContainer"] { background: #f5f7fb; }
    [data-testid="stHeader"] { background: transparent; }

    /* ----- Main area: dark text on light background ----- */
    .block-container, .block-container p, .block-container li, .block-container span,
    .block-container label, .block-container h1, .block-container h2, .block-container h3,
    .block-container h4, .block-container h5, .block-container h6,
    .block-container [data-testid="stMarkdownContainer"],
    .block-container [data-testid="stWidgetLabel"] p,
    .block-container [data-testid="stCaptionContainer"] {
        color: #10243a;
    }
    .block-container [data-testid="stCaptionContainer"],
    .block-container [data-testid="stCaptionContainer"] p { color: #5a6b80; }

    /* ----- Hero banner: white text on dark gradient (higher specificity) ----- */
    .block-container .hero {
        background: linear-gradient(115deg, #10243a 0%, #176b87 100%);
        padding: 1.4rem 1.6rem; border-radius: 18px; margin-bottom: 1rem;
    }
    .block-container .hero h1 { color: #ffffff !important; margin: 0; font-size: 2rem; padding: 0; }
    .block-container .hero p  { color: #e0f2fe !important; margin: .45rem 0 0 0; }

    .small-muted { color: #5a6b80 !important; font-size: .9rem; }

    /* ----- Sidebar: light text on dark navy ----- */
    [data-testid="stSidebar"], [data-testid="stSidebar"] > div:first-child { background: #10243a; }
    [data-testid="stSidebar"] *, [data-testid="stSidebar"] p, [data-testid="stSidebar"] label,
    [data-testid="stSidebar"] span, [data-testid="stSidebar"] h1, [data-testid="stSidebar"] h2,
    [data-testid="stSidebar"] h3 { color: #f3f7fb !important; }
    [data-testid="stSidebar"] hr { border-color: rgba(255,255,255,.18); }

    /* ----- Metric cards ----- */
    div[data-testid="stMetric"] {
        background: #ffffff; padding: 1rem; border-radius: 14px;
        border: 1px solid #e3eaf2; box-shadow: 0 2px 8px rgba(16,36,58,.06);
    }
    div[data-testid="stMetric"] *,
    div[data-testid="stMetricLabel"] *, div[data-testid="stMetricValue"] * { color: #10243a !important; }

    /* ----- Inputs: readable text on white fields ----- */
    .block-container input, .block-container textarea {
        color: #10243a !important; background: #ffffff !important;
    }
    .block-container ::placeholder { color: #8a97a8 !important; opacity: 1; }
    .block-container [data-baseweb="select"] > div { background: #ffffff; }
    .block-container [data-baseweb="select"] * { color: #10243a; }
    [data-baseweb="popover"] li, [data-baseweb="popover"] li * { color: #10243a !important; }
    [data-baseweb="popover"] ul { background: #ffffff !important; }

    /* ----- Forms ----- */
    [data-testid="stForm"] { background: #ffffff; border: 1px solid #e3eaf2; border-radius: 14px; }

    /* ----- Buttons ----- */
    .block-container button[kind="primary"], .block-container button[kind="primary"] * {
        color: #ffffff !important;
    }
    .block-container button[kind="primary"] { background: #176b87; border-color: #176b87; }
    .block-container button[kind="primary"]:hover { background: #10243a; border-color: #10243a; }
    .block-container button[kind="secondary"], .block-container button[kind="secondary"] * {
        color: #10243a !important;
    }
    .block-container button[kind="secondary"] { background: #ffffff; border: 1px solid #c9d5e3; }
    .block-container [data-testid="stDownloadButton"] button,
    .block-container [data-testid="stDownloadButton"] button * { color: #10243a !important; background: #ffffff; }

    /* ----- Alerts keep their own readable dark text ----- */
    .block-container [data-testid="stAlert"] * { color: #10243a !important; }

    .tag {
        display:inline-block; padding: .25rem .6rem; border-radius: 999px;
        font-weight: 600; font-size: .8rem;
    }
</style>
""", unsafe_allow_html=True)

# ---------- Sidebar ----------
with st.sidebar:
    st.markdown("## 🏥 MediQueue")
    st.caption("Emergency Patient Management")
    st.markdown("---")
    page = st.radio("NAVIGATION", PAGES, key="page")
    st.markdown("---")
    st.caption("DSA focus")
    st.markdown("**Priority Queue · Heap**")
    st.markdown("Searching · Sorting · Database")
    st.markdown("---")
    st.caption("Demo application — not for real clinical triage.")

# ---------- Header ----------
st.markdown("""
<div class="hero">
  <h1>🏥 MediQueue Emergency Desk</h1>
  <p>A priority-based patient queue and hospital emergency workflow dashboard.</p>
</div>
""", unsafe_allow_html=True)

show_flash()

# ---------- Dashboard ----------
if page == "Dashboard":
    total = metric_count("SELECT COUNT(*) FROM patients")
    waiting = metric_count("SELECT COUNT(*) FROM patients WHERE status='Waiting'")
    treating = metric_count("SELECT COUNT(*) FROM patients WHERE status='In Treatment'")
    completed = metric_count("SELECT COUNT(*) FROM patients WHERE status='Completed'")

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Total Patients", total, help="All registered patient records")
    c2.metric("Waiting Queue", waiting, help="Patients waiting to be called")
    c3.metric("In Treatment", treating)
    c4.metric("Completed", completed)

    st.markdown("### 🚦 Emergency overview")
    left, right = st.columns([1.25, 1])
    with left:
        st.subheader("Next patients in queue")
        heap = get_waiting_heap()
        if heap:
            preview = []
            for priority, registered, pid, name, category in sorted(heap)[:7]:
                preview.append({
                    "Queue": len(preview) + 1,
                    "Patient ID": f"MQ-{pid:04d}",
                    "Patient": name,
                    "Triage Level": category,
                    "Priority": priority,
                    "Registered": registered,
                })
            show_df(pd.DataFrame(preview))
        else:
            st.info("The waiting queue is empty. Register a patient to get started.")

    with right:
        st.subheader("Patient status")
        status_df = pd.DataFrame({
            "Status": ["Waiting", "In Treatment", "Completed"],
            "Patients": [waiting, treating, completed],
        })
        if total:
            st.bar_chart(status_df.set_index("Status"))
        else:
            st.caption("Charts appear after patients are added.")

    st.markdown("### ⚡ Quick actions")
    qa1, qa2, qa3 = st.columns(3)
    with qa1:
        wide_button("➕ Register a patient", on_click=go_to, args=("Register Patient",))
    with qa2:
        wide_button("📋 View live queue", on_click=go_to, args=("Live Queue",))
    with qa3:
        wide_button("📊 Open analytics", on_click=go_to, args=("Analytics",))

# ---------- Register ----------
elif page == "Register Patient":
    st.subheader("➕ New patient registration")
    st.write("Enter the patient's basic details and select a triage category.")
    with st.form("register_form", clear_on_submit=True):
        col1, col2 = st.columns(2)
        with col1:
            name = st.text_input("Full name *", placeholder="e.g., Arun Kumar")
            age = st.number_input("Age *", min_value=0, max_value=120, value=20, step=1)
            gender = st.selectbox("Gender", ["Prefer not to say", "Female", "Male", "Other"])
            phone = st.text_input("Contact number", placeholder="Optional")
        with col2:
            category = st.selectbox(
                "Triage category *",
                ["Critical", "Serious", "Moderate", "Minor"],
                help="For this academic demo only. Real triage must be performed by trained medical staff.",
            )
            symptoms = st.text_area("Symptoms / reason for visit *", placeholder="Brief description")
            notes = st.text_area("Additional notes", placeholder="Optional")
        st.markdown("**Priority guide**")
        st.caption("1 — Critical · 2 — Serious · 3 — Moderate · 4 — Minor")
        submitted = st.form_submit_button("Register Patient", type="primary")
        if submitted:
            if not name.strip() or not symptoms.strip():
                st.error("Please enter the patient's name and symptoms.")
            else:
                new_id = add_patient({
                    "name": name.strip(), "age": int(age), "gender": gender,
                    "phone": phone.strip(), "symptoms": symptoms.strip(),
                    "category": category, "notes": notes.strip(),
                })
                st.success(f"Patient registered successfully! Patient ID: MQ-{new_id:04d}")
                st.balloons()

# ---------- Live Queue ----------
elif page == "Live Queue":
    st.subheader("📋 Live priority queue")
    st.write(
        "The queue uses a **min-heap priority queue**: lower priority number is served first. "
        "Patients with equal priority are ordered by registration time."
    )
    heap = get_waiting_heap()
    if heap:
        queue_data = []
        for i, (priority, registered, pid, name, category) in enumerate(sorted(heap), 1):
            queue_data.append({
                "Queue Position": i,
                "Patient ID": f"MQ-{pid:04d}",
                "Patient Name": name,
                "Category": category,
                "Priority": priority,
                "Registered At": registered,
            })
        show_df(pd.DataFrame(queue_data))
        st.warning("Priority categories in this demo are illustrative. In actual emergency care, follow approved triage protocols.")
        if wide_button("🩺 Call next patient", type="primary"):
            patient = next_waiting_patient()
            if patient:
                flash("success", f"Now calling {patient['name']} (MQ-{patient['id']:04d}) — {patient['category']}.")
                _rerun()
    else:
        st.info("No patients are waiting right now.")

    st.markdown("### Update patient status")
    records = run_query(
        "SELECT id, name, status FROM patients WHERE status != 'Completed' ORDER BY id DESC", fetch=True
    )
    if records:
        labels = {f"MQ-{r['id']:04d} — {r['name']} ({r['status']})": r["id"] for r in records}
        selected_label = st.selectbox("Select patient", list(labels.keys()))
        action = st.selectbox("New status", ["In Treatment", "Completed"])
        if st.button("Update status"):
            pid = labels[selected_label]
            if action == "In Treatment":
                run_query("UPDATE patients SET status='In Treatment', called_at=? WHERE id=?", (now_str(), pid))
            else:
                # Keep called_at if already set; otherwise record the time now.
                run_query(
                    "UPDATE patients SET status='Completed', called_at=COALESCE(called_at, ?) WHERE id=?",
                    (now_str(), pid),
                )
            flash("success", "Patient status updated.")
            _rerun()
    else:
        st.caption("No active patients to update.")

# ---------- Records ----------
elif page == "Patient Records":
    st.subheader("🗂️ Patient records")
    records = get_all_patients()
    if not records:
        st.info("No patient records yet. Register a patient to populate this table.")
    else:
        df = pd.DataFrame(records)
        search = st.text_input("🔎 Search by patient name, ID (e.g. 3 or MQ-0003), symptoms, or category")
        status_filter = st.multiselect("Filter by status", STATUS_OPTIONS, default=STATUS_OPTIONS)
        filtered = df[df["status"].isin(status_filter)]
        if search.strip():
            term = search.strip().lower()
            id_term = term.replace("mq-", "").lstrip("0") or "0"
            mask = (
                filtered["name"].astype(str).str.lower().str.contains(term, na=False, regex=False)
                | filtered["id"].astype(str).str.contains(id_term, na=False, regex=False)
                | filtered["symptoms"].astype(str).str.lower().str.contains(term, na=False, regex=False)
                | filtered["category"].astype(str).str.lower().str.contains(term, na=False, regex=False)
            )
            filtered = filtered[mask]
        show = filtered.rename(columns={
            "id": "ID", "name": "Name", "age": "Age", "gender": "Gender",
            "phone": "Phone", "symptoms": "Symptoms", "category": "Category",
            "priority": "Priority", "status": "Status", "registered_at": "Registered At",
            "called_at": "Called At", "notes": "Notes",
        })
        show_df(show)
        csv = filtered.to_csv(index=False).encode("utf-8")
        st.download_button("⬇️ Export filtered records as CSV", csv, "patient_records.csv", "text/csv")
        st.caption(f"Showing {len(filtered)} of {len(df)} records.")

        st.markdown("### Patient details")
        max_id = int(df["id"].max())
        selected_id = st.number_input("Enter numeric patient ID", min_value=1, step=1, value=max_id)
        detail = run_query("SELECT * FROM patients WHERE id=?", (int(selected_id),), fetch=True)
        if detail:
            p = dict(detail[0])
            d1, d2, d3 = st.columns(3)
            d1.metric("Patient ID", f"MQ-{p['id']:04d}")
            d2.metric("Priority", p["priority"])
            d3.metric("Status", p["status"])
            st.write(f"**Name:** {p['name']} · **Age:** {p['age']} · **Gender:** {p['gender']}")
            st.write(f"**Phone:** {p['phone'] or '—'}")
            st.write(f"**Symptoms:** {p['symptoms']}")
            st.write(f"**Notes:** {p['notes'] or '—'}")
            st.write(f"**Registered:** {p['registered_at']} · **Called:** {p['called_at'] or 'Not called'}")
        else:
            st.caption("Enter an existing numeric ID to view details.")

# ---------- Analytics ----------
elif page == "Analytics":
    st.subheader("📊 Hospital analytics")
    records = get_all_patients()
    if not records:
        st.info("Register sample patients to view analytics.")
    else:
        df = pd.DataFrame(records)
        a, b = st.columns(2)
        with a:
            st.markdown("#### Patients by triage category")
            triage = df.groupby("category").size().reindex(["Critical", "Serious", "Moderate", "Minor"], fill_value=0)
            st.bar_chart(triage)
        with b:
            st.markdown("#### Patients by status")
            status = df.groupby("status").size().reindex(STATUS_OPTIONS, fill_value=0)
            st.bar_chart(status)
        st.markdown("#### Registration trend")
        df["registration_date"] = pd.to_datetime(df["registered_at"], errors="coerce").dt.date
        trend = df.groupby("registration_date").size()
        st.line_chart(trend)
        st.markdown("#### Summary")
        x1, x2, x3 = st.columns(3)
        x1.metric("Average patient age", f"{df['age'].mean():.1f} years")
        x2.metric("Critical cases", int((df["category"] == "Critical").sum()))
        x3.metric("Completion rate", f"{(df['status'].eq('Completed').mean() * 100):.1f}%")
        st.caption("Analytics are calculated from the records currently stored in the local SQLite database.")

# ---------- About ----------
elif page == "About Project":
    st.subheader("📘 Project documentation")
    st.markdown("""
### Project title
**MediQueue: Emergency Patient Management System Using Priority Queue**

### Abstract
MediQueue is a Python-based academic prototype that demonstrates how a hospital emergency desk can organize waiting patients using priority-based scheduling. It stores patient details in an SQLite database, places waiting patients in a heap-based priority queue, and provides a dashboard for managing status and viewing basic statistics.

### Problem statement
A simple first-come-first-served list does not demonstrate how priority scheduling works when cases have different urgency levels. This project models a priority-based queue and offers a structured way to register, search, track, and review patient records.

### Objectives
1. Register and maintain patient records.
2. Use a min-heap to select the next patient by priority.
3. Track waiting, in-treatment, and completed statuses.
4. Search and filter patient records.
5. Export records to CSV and visualize summary statistics.

### Data structures and technologies
- **Priority Queue / Min-Heap:** chooses the smallest priority value first.
- **List / DataFrame:** displays and analyzes records.
- **SQLite database:** persists data between app restarts.
- **Searching and sorting:** supports record lookup and queue display.
- **Python, Streamlit, Pandas:** application and dashboard.

### Algorithm: Call next patient
1. Read all records whose status is `Waiting`.
2. Insert each record into a min-heap using `(priority, registration time, patient ID)`.
3. Remove the smallest heap item.
4. Update that patient's status to `In Treatment`.
5. Display the patient selected for treatment.

### Limitations
This is a classroom demonstration, not a real hospital system. It does not provide medical advice, clinical triage, authentication, multi-user access controls, or integration with hospital software. Priority levels must never be used to make real clinical decisions.
""")
    st.info("For a project report, include screenshots of Dashboard, Register Patient, Live Queue, Patient Records, and Analytics.")

st.markdown("---")
st.markdown(
    "<div class='small-muted'>MediQueue · Academic DSA Mini Project · Python + Streamlit + SQLite</div>",
    unsafe_allow_html=True,
)
