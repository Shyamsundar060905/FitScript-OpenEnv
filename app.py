"""
FitAgent AI — Streamlit Application
"""

import streamlit as st
import sys, os, json, hashlib, time
from datetime import datetime, timedelta
from pathlib import Path

sys.path.append(os.path.dirname(__file__))

from memory.long_term import load_profile, save_profile
# v2 imports
from memory.episodic import (
    get_active_constraints, set_constraints,
    save_photo_metadata, get_photos, delete_photo,
)
from utils.auth import (
    create_account as auth_create_account,
    verify_login as auth_verify_login,
    AuthError,
)
from utils.session import (
    create_session, lookup_session, destroy_session,
)
from utils.prescription_store import rehydrate_latest_prescription
from utils.rate_limit import check_and_record, get_usage_stats, RateLimitDecision
from utils.observability import summarize_recent_runs
from utils.export import export_prescription_to_pdf, export_prescription_to_ics
from utils.photos import save_photo, list_photos, remove_photo, PhotoUploadError
from agents.orchestrator import RateLimitExceeded
from memory.episodic import init_db, log_progress, get_recent_logs, get_weight_series
from agents.progress_agent import seed_test_data
from schemas import ProgressLog, UserProfile
from config import USERS_DIR

# ── Page config ───────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="FitAgent",
    page_icon="",
    layout="wide",
    initial_sidebar_state="expanded"
)

st.markdown("""
<style>
/* ── Typography ──────────────────────────────────────────────────────────── */
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap');

html, body, [class*="css"], button, input, textarea, select {
    font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif !important;
    -webkit-font-smoothing: antialiased;
    -moz-osx-font-smoothing: grayscale;
}

/* ── Background — soft cream throughout ──────────────────────────────────── */
.stApp {
    background-color: #FAF8F1;
}

/* Sidebar surface */
[data-testid="stSidebar"] {
    background-color: #F5F2E8;
    border-right: 1px solid #E8E3D5;
}

/* ── Headings — restrained, no orange accents ────────────────────────────── */
h1, h2, h3, h4 {
    color: #1F2937 !important;
    font-weight: 600 !important;
    letter-spacing: -0.015em;
}
h1 { font-size: 2rem !important; }
h2 { font-size: 1.5rem !important; margin-top: 0.5rem !important; }
h3 { font-size: 1.15rem !important; }

/* Caption / muted text */
.stCaption, [data-testid="stCaptionContainer"] {
    color: #6B7280 !important;
    font-size: 0.85rem !important;
}

/* ── Metric cards — cleaner, less shouty ─────────────────────────────────── */
.metric-card {
    background: #FFFFFF;
    border-radius: 14px;
    padding: 1.1rem 1rem;
    text-align: center;
    border: 1px solid #E8E3D5;
    margin-bottom: 0.5rem;
    box-shadow: 0 1px 3px rgba(0,0,0,0.02);
    transition: box-shadow 0.15s ease;
}
.metric-card:hover {
    box-shadow: 0 4px 12px rgba(0,0,0,0.04);
}
.metric-value {
    font-size: 1.75rem;
    font-weight: 600;
    color: #1F2937;
    letter-spacing: -0.02em;
    line-height: 1.2;
}
.metric-label {
    font-size: 0.7rem;
    color: #9CA3AF;
    text-transform: uppercase;
    letter-spacing: 0.08em;
    margin-top: 0.4rem;
    font-weight: 500;
}

/* ── Agent pipeline rows ─────────────────────────────────────────────────── */
.agent-step {
    padding: 12px 16px;
    border-radius: 10px;
    margin: 6px 0;
    font-size: 0.9rem;
    font-weight: 500;
    transition: all 0.2s ease;
}
.agent-done {
    background: #F0F9E8;
    color: #3F6B1F;
    border-left: 3px solid #7CB342;
}
.agent-running {
    background: #FFFFFF;
    color: #1F2937;
    border-left: 3px solid #6B7280;
    animation: subtle-pulse 1.5s ease-in-out infinite;
}
.agent-pending {
    background: #FAF8F1;
    color: #9CA3AF;
    border-left: 3px solid #E8E3D5;
}
@keyframes subtle-pulse {
    0%, 100% { opacity: 1; }
    50% { opacity: 0.7; }
}

/* ── Severity pills ──────────────────────────────────────────────────────── */
.signal-high {
    background: #FEF2F2;
    color: #991B1B;
    padding: 4px 12px;
    border-radius: 12px;
    font-size: 0.75rem;
    font-weight: 600;
    border: 1px solid #FECACA;
}
.signal-medium {
    background: #FFFBEB;
    color: #92400E;
    padding: 4px 12px;
    border-radius: 12px;
    font-size: 0.75rem;
    font-weight: 600;
    border: 1px solid #FDE68A;
}
.signal-low {
    background: #F0F9E8;
    color: #3F6B1F;
    padding: 4px 12px;
    border-radius: 12px;
    font-size: 0.75rem;
    font-weight: 600;
    border: 1px solid #C5E1A5;
}

/* ── Generic info card ───────────────────────────────────────────────────── */
.info-card {
    background: #FFFFFF;
    border-radius: 14px;
    padding: 1.5rem;
    border: 1px solid #E8E3D5;
    margin-bottom: 1rem;
    box-shadow: 0 1px 3px rgba(0,0,0,0.02);
}

/* ── Buttons ─────────────────────────────────────────────────────────────── */
.stButton > button {
    border-radius: 10px !important;
    font-weight: 500 !important;
    transition: all 0.15s ease !important;
    border: 1px solid #E8E3D5 !important;
    box-shadow: none !important;
}
.stButton > button:hover {
    transform: translateY(-1px);
    box-shadow: 0 2px 6px rgba(0,0,0,0.06) !important;
}
/* Primary button */
.stButton > button[kind="primary"] {
    background: #7CB342 !important;
    color: white !important;
    border: 1px solid #7CB342 !important;
}
.stButton > button[kind="primary"]:hover {
    background: #689F38 !important;
    border-color: #689F38 !important;
}
/* Secondary button */
.stButton > button[kind="secondary"] {
    background: #FFFFFF !important;
    color: #1F2937 !important;
}

/* ── Sidebar navigation buttons ──────────────────────────────────────────── */
[data-testid="stSidebar"] .stButton > button {
    text-align: left !important;
    justify-content: flex-start !important;
}

/* ── Inputs ──────────────────────────────────────────────────────────────── */
.stTextInput > div > div > input,
.stNumberInput > div > div > input,
.stTextArea > div > div > textarea,
.stDateInput > div > div > input,
.stSelectbox > div > div {
    border-radius: 8px !important;
    border-color: #E8E3D5 !important;
    background-color: #FFFFFF !important;
}
.stTextInput > div > div > input:focus,
.stNumberInput > div > div > input:focus,
.stTextArea > div > div > textarea:focus {
    border-color: #7CB342 !important;
    box-shadow: 0 0 0 1px #7CB342 !important;
}

/* ── Tabs ────────────────────────────────────────────────────────────────── */
.stTabs [data-baseweb="tab-list"] {
    gap: 4px;
    background: transparent;
    border-bottom: 1px solid #E8E3D5;
}
.stTabs [data-baseweb="tab"] {
    background: transparent !important;
    color: #6B7280 !important;
    font-weight: 500 !important;
    border-radius: 6px 6px 0 0 !important;
    padding: 8px 14px !important;
}
.stTabs [aria-selected="true"] {
    color: #7CB342 !important;
    border-bottom: 2px solid #7CB342 !important;
}

/* ── Expanders ───────────────────────────────────────────────────────────── */
.streamlit-expanderHeader, [data-testid="stExpander"] > div:first-child {
    background: #FFFFFF !important;
    border-radius: 10px !important;
    border: 1px solid #E8E3D5 !important;
    font-weight: 500 !important;
}
[data-testid="stExpander"] {
    border: none !important;
    margin-bottom: 0.5rem;
}

/* ── Dataframes ──────────────────────────────────────────────────────────── */
[data-testid="stDataFrame"] {
    border-radius: 10px;
    overflow: hidden;
    border: 1px solid #E8E3D5;
}

/* ── Alerts (st.success / st.warning / st.error / st.info) ───────────────── */
[data-testid="stAlert"] {
    border-radius: 10px !important;
    border: 1px solid transparent !important;
}
[data-testid="stAlert"][kind="info"] {
    background: #FFFFFF !important;
    border-color: #E8E3D5 !important;
}

/* ── Dividers — softer ───────────────────────────────────────────────────── */
hr {
    border-color: #E8E3D5 !important;
    opacity: 0.6;
    margin: 1.5rem 0 !important;
}

/* ── Sliders / progress ──────────────────────────────────────────────────── */
.stSlider > div > div > div > div {
    background: #7CB342 !important;
}

/* ── Hide streamlit chrome ───────────────────────────────────────────────── */
#MainMenu { visibility: hidden; }
footer { visibility: hidden; }
header[data-testid="stHeader"] { background: transparent; }

/* ── Labels — softer ─────────────────────────────────────────────────────── */
.stTextInput label, .stNumberInput label, .stSelectbox label,
.stTextArea label, .stDateInput label, .stSlider label,
.stCheckbox label, .stMultiSelect label, .stFileUploader label {
    color: #4B5563 !important;
    font-weight: 500 !important;
    font-size: 0.85rem !important;
}

/* ── Streamlit's "running man" / spinner ─────────────────────────────────── */
.stSpinner > div {
    border-top-color: #7CB342 !important;
}

</style>
""", unsafe_allow_html=True)

# ── Init ──────────────────────────────────────────────────────────────────────
if "db_initialized" not in st.session_state:
    init_db()
    st.session_state.db_initialized = True

def create_account(username, password):
    """v2: uses bcrypt via utils.auth"""
    try:
        auth_create_account(username, password)
        return True
    except AuthError:
        return False


def verify_login(username, password):
    """v2: uses bcrypt via utils.auth"""
    return auth_verify_login(username, password)

# ── Session defaults ──────────────────────────────────────────────────────────
for k, v in {
    "logged_in": False, "username": None, "user_id": None,
    "page": "dashboard", "prescription": None, "week_number": 1,
    "active_constraints": []
}.items():
    if k not in st.session_state:
        st.session_state[k] = v

# ── Refresh-survival: rehydrate session from URL token if present ────────────
if not st.session_state.logged_in:
    url_token = st.query_params.get("session")
    if url_token:
        info = lookup_session(url_token)
        if info:
            st.session_state.logged_in = True
            st.session_state.username  = info["username"]
            st.session_state.user_id   = info["user_id"]
        else:
            # Stale or invalid token — clear it from URL
            try:
                del st.query_params["session"]
            except KeyError:
                pass
# ── Refresh-survival: rehydrate the most recent prescription ─────────────────
# After login is restored, also try to restore the last generated plan so
# the Plan page isn't empty after a browser refresh.
if (st.session_state.logged_in
        and st.session_state.prescription is None
        and st.session_state.user_id):
    restored = rehydrate_latest_prescription(st.session_state.user_id)
    if restored:
        st.session_state.prescription = restored
        st.session_state.week_number  = restored.week_number + 1
        
# ── Auth page ─────────────────────────────────────────────────────────────────
def show_auth():
    """Polished two-pane auth: value-prop hero on left, form on right.
    Constrained to a max-width so it doesn't stretch on ultra-wide monitors."""

    # Open a centered constrained container. We use an HTML wrapper because
    # Streamlit's columns alone don't give us a max-width control.
    st.markdown(
        '<div style="max-width: 1080px; margin: 4rem auto 0;">',
        unsafe_allow_html=True,
    )

    hero_html = (
        '<div style="padding: 2.5rem 1.75rem 1.5rem; '
        'background: linear-gradient(180deg, #F5F2E8 0%, #EFEBDB 100%); '
        'border-radius: 16px; border: 1px solid #E8E3D5; min-height: 540px; '
        'display: flex; flex-direction: column; justify-content: space-between;">'

          '<div>'

            # Logo + wordmark
            '<div style="display: flex; align-items: center; gap: 10px; margin-bottom: 2rem;">'
              '<svg width="32" height="32" viewBox="0 0 32 32" xmlns="http://www.w3.org/2000/svg">'
                '<circle cx="16" cy="16" r="15" fill="#7CB342"/>'
                '<path d="M10 16 L14 20 L22 12" stroke="white" stroke-width="2.5" '
                'fill="none" stroke-linecap="round" stroke-linejoin="round"/>'
              '</svg>'
              '<span style="font-size: 18px; font-weight: 600; color: #1F2937; '
              'letter-spacing: -0.01em;">FitAgent</span>'
            '</div>'

            # Headline + tagline
            '<h1 style="font-size: 26px; font-weight: 600; color: #1F2937; '
            'line-height: 1.25; margin: 0 0 0.75rem; letter-spacing: -0.02em;">'
            'Personalized fitness,<br/>grounded in evidence.'
            '</h1>'
            '<p style="font-size: 13px; color: #6B7280; line-height: 1.6; margin: 0 0 2rem;">'
            'A multi-agent AI system that adapts your training and nutrition to your '
            'goals, your equipment, and your progress &mdash; with every recommendation '
            'backed by the IFCT 2017 nutrition database and peer-reviewed sports science.'
            '</p>'

            # Three feature bullets
            '<div style="display: flex; flex-direction: column; gap: 14px;">'

              '<div style="display: flex; align-items: flex-start; gap: 10px;">'
                '<div style="width: 18px; height: 18px; border-radius: 50%; '
                'background: #7CB342; flex-shrink: 0; margin-top: 2px; '
                'display: flex; align-items: center; justify-content: center;">'
                  '<svg width="10" height="10" viewBox="0 0 10 10">'
                  '<path d="M2 5 L4 7 L8 3" stroke="white" stroke-width="1.5" '
                  'fill="none" stroke-linecap="round" stroke-linejoin="round"/>'
                  '</svg>'
                '</div>'
                '<div>'
                  '<div style="font-size: 13px; font-weight: 500; color: #1F2937;">'
                  'Statistical plateau detection</div>'
                  '<div style="font-size: 12px; color: #6B7280;">'
                  '7-day rolling regression on body weight</div>'
                '</div>'
              '</div>'

              '<div style="display: flex; align-items: flex-start; gap: 10px;">'
                '<div style="width: 18px; height: 18px; border-radius: 50%; '
                'background: #7CB342; flex-shrink: 0; margin-top: 2px; '
                'display: flex; align-items: center; justify-content: center;">'
                  '<svg width="10" height="10" viewBox="0 0 10 10">'
                  '<path d="M2 5 L4 7 L8 3" stroke="white" stroke-width="1.5" '
                  'fill="none" stroke-linecap="round" stroke-linejoin="round"/>'
                  '</svg>'
                '</div>'
                '<div>'
                  '<div style="font-size: 13px; font-weight: 500; color: #1F2937;">'
                  'Verified Indian nutrition</div>'
                  '<div style="font-size: 12px; color: #6B7280;">'
                  'Macros sourced from IFCT 2017 &amp; USDA</div>'
                '</div>'
              '</div>'

              '<div style="display: flex; align-items: flex-start; gap: 10px;">'
                '<div style="width: 18px; height: 18px; border-radius: 50%; '
                'background: #7CB342; flex-shrink: 0; margin-top: 2px; '
                'display: flex; align-items: center; justify-content: center;">'
                  '<svg width="10" height="10" viewBox="0 0 10 10">'
                  '<path d="M2 5 L4 7 L8 3" stroke="white" stroke-width="1.5" '
                  'fill="none" stroke-linecap="round" stroke-linejoin="round"/>'
                  '</svg>'
                '</div>'
                '<div>'
                  '<div style="font-size: 13px; font-weight: 500; color: #1F2937;">'
                  'Deterministic progressive overload</div>'
                  '<div style="font-size: 12px; color: #6B7280;">'
                  'Coaching rules, not LLM guesswork</div>'
                '</div>'
              '</div>'

            '</div>'
          '</div>'

          '<div style="font-size: 11px; color: #9CA3AF; padding-top: 1.5rem; '
          'border-top: 1px solid #E8E3D5; margin-top: 1.5rem;">'
          'Final-year B.Tech research project &middot; Multi-agent systems &middot; 2026'
          '</div>'

        '</div>'
    )

    # Two columns within the constrained wrapper. The gap parameter gives
    # comfortable breathing room between hero and form.
    left, right = st.columns([1.05, 1], gap="large")

    with left:
        st.markdown(hero_html, unsafe_allow_html=True)

    with right:
        st.markdown(
            '<div style="padding: 1.5rem 0 0; max-width: 420px;">'
            '<h2 style="font-size: 22px; font-weight: 600; color: #1F2937; '
            'margin: 0 0 6px; letter-spacing: -0.01em;">Welcome back</h2>'
            '<p style="font-size: 13px; color: #6B7280; margin: 0 0 1.5rem;">'
            'Sign in to continue your training plan</p>'
            '</div>',
            unsafe_allow_html=True,
        )

        # Constrain the form column to a sensible width within the right pane
        # by nesting another column.
        form_col, _ = st.columns([1, 0.05])

        with form_col:
            tab1, tab2 = st.tabs(["Sign in", "Create account"])

            with tab1:
                u = st.text_input("Username", key="lu",
                                  placeholder="your username")
                p = st.text_input("Password", type="password", key="lp",
                                  placeholder="your password")
                if st.button("Sign in", type="primary",
                             width="stretch", key="login_btn"):
                    uid = verify_login(u, p)
                    if uid:
                        st.session_state.update(
                            logged_in=True, username=u, user_id=uid
                        )
                        token = create_session(u)
                        st.query_params["session"] = token
                        st.rerun()
                    else:
                        st.error("Invalid username or password.")

            with tab2:
                u2 = st.text_input("Username", key="su",
                                    placeholder="choose a username")
                p2 = st.text_input(
                    "Password", type="password", key="sp",
                    placeholder="at least 8 characters",
                    help="At least 8 chars with 2 of: lowercase, uppercase, digit, symbol"
                )
                p3 = st.text_input("Confirm password", type="password", key="sp2",
                                    placeholder="re-enter password")
                if st.button("Create account", type="primary",
                             width="stretch", key="signup_btn"):
                    if p2 != p3:
                        st.error("Passwords don't match.")
                    else:
                        try:
                            auth_create_account(u2, p2)
                            uid = auth_verify_login(u2, p2)
                            st.session_state.update(
                                logged_in=True, username=u2, user_id=uid
                            )
                            token = create_session(u2)
                            st.query_params["session"] = token
                            st.rerun()
                        except AuthError as e:
                            st.error(str(e))

            st.markdown(
                '<p style="font-size: 11px; color: #9CA3AF; text-align: center; '
                'margin: 1.5rem 0 0;">'
                'By signing in you agree to use this research prototype responsibly. '
                'Not medical advice.'
                '</p>',
                unsafe_allow_html=True,
            )

    # Close the centered wrapper
    st.markdown('</div>', unsafe_allow_html=True)

# ── Onboarding ────────────────────────────────────────────────────────────────
def show_onboarding():
    st.markdown("## 👋 Welcome! Let's set up your profile")
    st.caption("This takes 2 minutes and helps our AI agents personalize everything for you.")
    st.divider()

    col1, col2 = st.columns(2)
    with col1:
        name     = st.text_input("Your name *", placeholder="e.g. Arjun")
        age      = st.number_input("Age", 16, 80, 22)
        weight   = st.number_input("Weight (kg)", 30.0, 250.0, 70.0, 0.5)
        height   = st.number_input("Height (cm)", 100.0, 250.0, 170.0, 0.5)
        sessions = st.slider("How many days/week can you train?", 2, 6, 4)

    with col2:
        goal = st.selectbox("Primary goal", [
            "muscle_gain", "weight_loss", "endurance", "maintenance"
        ], format_func=lambda x: x.replace("_", " ").title())

        level = st.selectbox("Current fitness level", [
            "beginner", "intermediate", "advanced"
        ], format_func=str.title)

        diet = st.multiselect("Dietary restrictions (optional)", [
            "vegetarian", "vegan", "gluten_free", "dairy_free", "halal"
        ])

        equipment = st.multiselect("Available equipment *", [
            "bodyweight", "dumbbells", "barbell", "pull_up_bar",
            "resistance_bands", "kettlebell", "gym_machines", "bench"
        ], default=["bodyweight"])

    st.divider()
    st.markdown("#### Any existing injuries or areas to avoid?")
    st.caption("This helps the Fitness Agent skip exercises that could aggravate your condition.")

    col_a, col_b, col_c = st.columns(3)
    injuries = []
    with col_a:
        if st.checkbox("🦵 Knee issues"):
            injuries.append("knee pain — avoid squats, lunges, leg press")
        if st.checkbox("🔙 Lower back"):
            injuries.append("lower back pain — avoid deadlifts, heavy squats")
    with col_b:
        if st.checkbox("💪 Shoulder"):
            injuries.append("shoulder injury — avoid overhead press, dips")
        if st.checkbox("🤝 Wrist"):
            injuries.append("wrist pain — avoid push-ups on palms, barbell curls")
    with col_c:
        if st.checkbox("🦶 Ankle"):
            injuries.append("ankle injury — avoid jumping, running")
        if st.checkbox("🏃 Hip"):
            injuries.append("hip pain — avoid hip hinge movements")

    st.divider()
    if st.button("🚀 Create My Profile", type="primary", width="stretch"):
        if not name:
            st.error("Please enter your name")
            return
        if not equipment:
            st.error("Please select at least one equipment option")
            return

        af = {"beginner": 1.4, "intermediate": 1.6, "advanced": 1.8}[level]
        tdee_base = weight * 22 * af
        tdee = {"weight_loss": tdee_base - 400, "muscle_gain": tdee_base + 300,
                "endurance": tdee_base + 100, "maintenance": tdee_base}[goal]

        profile = UserProfile(
            user_id=st.session_state.user_id,
            name=name, age=int(age),
            weight_kg=float(weight), height_cm=float(height),
            goal=goal, fitness_level=level,
            dietary_restrictions=diet,
            available_equipment=equipment,
            sessions_per_week=int(sessions),
            tdee_estimate=round(float(tdee))
        )
        save_profile(profile)
        if injuries:
            st.session_state.active_constraints = injuries
        st.success(f"✅ Profile created! Welcome, {name}!")
        time.sleep(1)
        st.rerun()

def show_photos(profile):
    st.markdown("## Progress Photos")
    st.caption("Upload photos to visually track your progress over time. "
                "Photos are stored privately on this server, not shared.")
    st.divider()

    # Upload
    st.markdown("### Upload a new photo")
    col1, col2 = st.columns([2, 1])
    with col1:
        uploaded = st.file_uploader(
            "Choose a photo",
            type=["jpg", "jpeg", "png", "webp"],
            help=f"Max 10MB. Accepted: JPG, PNG, WebP",
        )
    with col2:
        photo_weight = st.number_input(
            "Weight on this day (kg)",
            0.0, 300.0, float(profile.weight_kg), 0.1,
        )
    photo_note = st.text_input("Note (optional)",
                                placeholder="e.g. Front, 4 weeks in")
    photo_date = st.date_input("Date", datetime.now())

    if uploaded is not None and st.button("💾 Save photo", type="primary"):
        try:
            result = save_photo(
                user_id=st.session_state.user_id,
                file_bytes=uploaded.getvalue(),
                original_filename=uploaded.name,
                date=photo_date.strftime("%Y-%m-%d"),
                weight_kg=photo_weight,
                note=photo_note,
            )
            st.success(f"✅ Saved as {result['filename']}")
            st.rerun()
        except PhotoUploadError as e:
            st.error(f"Upload failed: {e}")

    st.divider()
    st.markdown("### Gallery")
    photos = list_photos(st.session_state.user_id, limit=24)
    if not photos:
        st.info("No photos yet. Upload one above to start tracking visually.")
        return

    # Render 3-column grid
    cols = st.columns(3)
    for idx, photo in enumerate(photos):
        col = cols[idx % 3]
        with col:
            from pathlib import Path
            p = Path(photo["photo_path"])
            if p.exists():
                st.image(str(p), width="stretch")
            else:
                st.warning("Photo file missing")
            st.caption(
                f"**{photo['date']}**  \n"
                f"Weight: {photo['weight_kg']} kg" if photo['weight_kg'] else photo['date']
            )
            if photo.get("note"):
                st.caption(f"_{photo['note']}_")
            if st.button("🗑️ Delete", key=f"del_{photo['id']}"):
                remove_photo(st.session_state.user_id, photo["id"])
                st.rerun()

# ── Sidebar ───────────────────────────────────────────────────────────────────
def show_sidebar(profile):
    with st.sidebar:
        st.markdown("### FitAgent AI")
        st.markdown(f"**{profile.name}**  \n"
                    f"{profile.goal.replace('_', ' ').title()} · "
                    f"{profile.fitness_level.title()}")
        st.divider()

        nav = {
            "dashboard": "Dashboard",
            "plan":      "My Plan",
            "checkin":   "Check-in",
            "history":   "History",
            "photos":    "Progress Photos",
            "profile":   "Settings",
        }
        for key, label in nav.items():
            is_active = st.session_state.page == key
            if st.button(label, width="stretch",
                         type="primary" if is_active else "secondary"):
                st.session_state.page = key
                st.rerun()

        st.divider()
        if st.button("Logout", width="stretch"):
            # Destroy server-side session and clear URL token
            url_token = st.query_params.get("session")
            if url_token:
                destroy_session(url_token)
                try:
                    del st.query_params["session"]
                except KeyError:
                    pass
            for k, v in {
                "logged_in": False, "username": None, "user_id": None,
                "page": "dashboard", "prescription": None,
                "week_number": 1, "active_constraints": [],
                "_constraints_hydrated": False,
            }.items():
                st.session_state[k] = v
            st.rerun()

        st.divider()
        with st.expander("📊 Usage & diagnostics", expanded=False):
            stats = get_usage_stats(st.session_state.user_id)
            st.caption(
                f"Plans today: {stats['used_today']} / {stats['daily_limit']}  \n"
                f"Last hour: {stats['used_this_hour']}"
            )
            runs = summarize_recent_runs(st.session_state.user_id)
            if runs["successful_runs"]:
                st.caption(f"Total successful agent runs: {runs['successful_runs']}")
                for agent, s in runs["by_agent"].items():
                    st.caption(f"  • {agent}: {s['count']} runs, avg {s['avg_ms']}ms")
# ── Dashboard ─────────────────────────────────────────────────────────────────
def show_dashboard(profile):
    st.markdown("## Dashboard")
    greeting = ("morning" if datetime.now().hour < 12
                else "afternoon" if datetime.now().hour < 17
                else "evening")
    st.markdown(f"Good {greeting}, **{profile.name}**!")
    st.divider()

    import pandas as pd
    logs    = get_recent_logs(st.session_state.user_id, days=30)
    weights = get_weight_series(st.session_state.user_id, days=30)
    # v2: hydrate active constraints from the DB on first load of this session
    if not st.session_state.get("_constraints_hydrated"):
        st.session_state.active_constraints = get_active_constraints(
            st.session_state.user_id
        )
        st.session_state._constraints_hydrated = True
    completed  = sum(1 for l in logs if l["workout_completed"])
    adherence  = round(completed / len(logs) * 100) if logs else 0
    weight_chg = (round(weights[-1]["weight_kg"] - weights[0]["weight_kg"], 1)
                  if len(weights) >= 2 else 0.0)

    c1, c2, c3, c4, c5 = st.columns(5)
    for col, val, unit, label in [
        (c1, profile.weight_kg,  "kg", "Current Weight"),
        (c2, profile.bmi(),      "",   "BMI"),
        (c3, f"{adherence}%",   "",   "30-day Adherence"),
        (c4, completed,          "",   "Workouts Done"),
        (c5, f"{'+' if weight_chg > 0 else ''}{weight_chg}", "kg", "Weight Change"),
    ]:
        col.markdown(
            f"<div class='metric-card'>"
            f"<div class='metric-value'>{val}"
            f"<span style='font-size:1rem;color:#6B7280'>{unit}</span></div>"
            f"<div class='metric-label'>{label}</div></div>",
            unsafe_allow_html=True
        )

    st.markdown("<br>", unsafe_allow_html=True)
    col1, col2 = st.columns([2, 1])

    with col1:
        st.markdown("#### Weight Trend (last 30 days)")
        if weights:
            import altair as alt
            df = pd.DataFrame(weights)
            df["date"] = pd.to_datetime(df["date"])
            
            # Auto-scale Y axis to ±2kg around the data range
            min_w = df["weight_kg"].min()
            max_w = df["weight_kg"].max()
            padding = max(2.0, (max_w - min_w) * 0.3)
            y_min = round(min_w - padding, 1)
            y_max = round(max_w + padding, 1)
            
            chart = (
                alt.Chart(df)
                .mark_line(
                    point=alt.OverlayMarkDef(size=60, fill="#7CB342"),
                    color="#7CB342",
                    strokeWidth=2.5,
                )
                .encode(
                    x=alt.X(
                        "date:T",
                        axis=alt.Axis(
                            format="%b %d",
                            labelAngle=0,
                            title=None,
                            tickCount="day",
                        ),
                    ),
                    y=alt.Y(
                        "weight_kg:Q",
                        scale=alt.Scale(domain=[y_min, y_max]),
                        axis=alt.Axis(title="kg", titlePadding=10),
                    ),
                    tooltip=[
                        alt.Tooltip("date:T", title="Date", format="%b %d, %Y"),
                        alt.Tooltip("weight_kg:Q", title="Weight (kg)", format=".1f"),
                    ],
                )
                .properties(height=240)
                .configure_view(strokeWidth=0)
                .configure_axis(
                    grid=True,
                    gridColor="#E8E3D5",
                    domainColor="#E8E3D5",
                    tickColor="#E8E3D5",
                    labelColor="#6B7280",
                    titleColor="#6B7280",
                    labelFontSize=11,
                )
            )
            st.altair_chart(chart, width="stretch")
        else:
            st.info("No weight data yet — log your first check-in to start tracking.")

    with col2:
        st.markdown("#### Your Goal")
        goal_emoji = {"muscle_gain": "🏋️", "weight_loss": "🔥",
                      "endurance": "🏃", "maintenance": "⚖️"}
        diet_html = (
            f"<div style='margin-top:0.5rem;color:#92400E;font-size:0.8rem'>"
            f"⚠️ {' · '.join(profile.dietary_restrictions)}</div>"
            if profile.dietary_restrictions else ""
        )
        st.markdown(
            f"<div class='info-card' style='text-align:center'>"
            f"<div style='font-size:2.5rem'>{goal_emoji.get(profile.goal, '🎯')}</div>"
            f"<div style='font-size:1.2rem;font-weight:700;margin-top:0.5rem'>"
            f"{profile.goal.replace('_', ' ').title()}</div>"
            f"<div style='color:#6B7280;font-size:0.9rem;margin-top:0.3rem'>"
            f"{profile.fitness_level.title()} · {profile.sessions_per_week}x/week</div>"
            f"<div style='color:#6B7280;font-size:0.85rem;margin-top:0.3rem'>"
            f"Target: {profile.tdee_estimate:.0f} kcal/day</div>"
            f"{diet_html}</div>",
            unsafe_allow_html=True
        )

    if st.session_state.active_constraints:
        st.warning(
            "**Active constraints:** " +
            " · ".join(f"⚠️ {c.split(' — ')[0]}"
                       for c in st.session_state.active_constraints) +
            " — these will be passed to the Fitness Agent when generating your plan."
        )

    st.divider()
    st.markdown("#### Quick Actions")
    c1, c2, c3 = st.columns(3)
    with c1:
        if st.button("📋 Generate This Week's Plan",
                     type="primary", width="stretch"):
            st.session_state.page = "plan"
            st.rerun()
    with c2:
        if st.button("✏️ Log Today's Check-in", width="stretch"):
            st.session_state.page = "checkin"
            st.rerun()
    with c3:
        if st.button("🧪 Seed 3 Weeks Test Data", width="stretch"):
            seed_test_data(st.session_state.user_id, weeks=3)
            st.success("✓ Test data seeded — refresh to see charts")
            st.rerun()

    if logs:
        st.divider()
        st.markdown("#### Recent Activity")
        df2 = pd.DataFrame(logs[-7:])
        df2["Date"]       = pd.to_datetime(df2["date"]).dt.strftime("%b %d")
        df2["Workout"]    = df2["workout_completed"].apply(lambda x: "✅" if x else "—")
        df2["Difficulty"] = df2["workout_rating"].apply(
            lambda x: "⭐" * int(x) if pd.notna(x) and x else "—")
        df2["Weight"]     = df2["weight_kg"].apply(lambda x: f"{x} kg" if pd.notna(x) and x else "—")
        df2["Calories"]   = df2["calories_eaten"].apply(
            lambda x: f"{x:.0f}" if pd.notna(x) and x else "—")
        st.dataframe(
            df2[["Date", "Workout", "Difficulty", "Weight", "Calories", "notes"]]
            .rename(columns={"notes": "Notes"}),
            width="stretch", hide_index=True
        )

# ── Plan page ─────────────────────────────────────────────────────────────────
def show_plan(profile):
    st.markdown("## My Weekly Plan")

    if st.session_state.active_constraints:
        st.warning(
            "**Active constraints today:** " +
            " · ".join(f"⚠️ {c.split(' — ')[0]}"
                       for c in st.session_state.active_constraints) +
            "\n\nThe Fitness Agent will avoid related exercises."
        )

    col1, col2 = st.columns([3, 1])
    with col1:
        week_num = st.number_input("Week number", 1, 52,
                                    st.session_state.week_number)
    with col2:
        st.markdown("<br>", unsafe_allow_html=True)
        go = st.button("🚀 Run All Agents", type="primary",
                        width="stretch")

    if go:
        _run_agents(profile, week_num)

    if st.session_state.prescription:
        _show_prescription(st.session_state.prescription)


def _run_agents(profile, week_num):
    from agents.orchestrator import run_pipeline

    constraint_context = ""
    if st.session_state.active_constraints:
        constraint_context = (
            "User has these physical constraints today — "
            "avoid exercises that would aggravate: " +
            "; ".join(st.session_state.active_constraints)
        )

    st.markdown("### Agent Pipeline")
    steps = [
        ("profile",   "Profile",          "Loading user profile"),
        ("progress",  "Progress",         "Analyzing progress history"),
        ("fitness",   "Fitness",          "Generating workout plan"),
        ("nutrition", "Nutrition",        "Building nutrition plan"),
        ("conflicts", "Conflict resolver", "Checking for conflicts"),
        ("synthesis", "Orchestrator",     "Synthesizing prescription"),
    ]

    placeholders = {k: st.empty() for k, _, _ in steps}

    def render(key, label, status, msg=""):
        icon = {"done": "✅", "running": "⟳", "pending": "⏳", "error": "❌"}[status]
        css  = {"done": "agent-done", "running": "agent-running",
                "pending": "agent-pending", "error": "agent-pending"}[status]
        placeholders[key].markdown(
            f"<div class='agent-step {css}'>{icon} {label}"
            f"{'  —  <span style=opacity:.7>' + msg + '</span>' if msg else ''}"
            f"</div>",
            unsafe_allow_html=True
        )

    for k, label, _ in steps:
        render(k, label, "pending")

    try:
        render("profile", "👤 Profile Agent", "running", "Loading...")
        time.sleep(0.2)
        render("profile", "👤 Profile Agent", "done",
               f"{profile.name} · {profile.goal.replace('_', ' ')}")

        render("progress", "📊 Progress Agent", "running", "Querying memory...")

        # v2: rate limit check happens inside run_pipeline; surface the error
        try:
            rx = run_pipeline(
                st.session_state.user_id,
                week_number=week_num,
                constraint_context=constraint_context,
            )
        except RateLimitExceeded as rle:
            d = rle.decision
            mins = d.retry_after_seconds // 60
            if d.reason == "cooldown":
                st.warning(f"⏳ Please wait {d.retry_after_seconds}s before generating another plan.")
            else:
                st.warning(f"📅 Daily plan limit reached. Resets in {mins} minutes.")
            return

        sigs = rx.adaptation_signals
        render("progress", "📊 Progress Agent", "done",
               ", ".join(f"{s.signal_type}({s.severity})" for s in sigs)
               or "No issues detected")
        render("fitness",  "💪 Fitness Agent",  "done",
               f"{rx.workout_plan.weekly_volume_sets} sets/week")
        render("nutrition", "🥗 Nutrition Agent", "done",
               f"{rx.nutrition_plan.target_calories:.0f} kcal/day")
        render("conflicts", "⚡ Conflict Resolver", "done",
               f"{len(rx.conflicts_resolved)} resolved"
               if rx.conflicts_resolved else "No conflicts")
        render("synthesis", "🧠 Orchestrator", "done", "Prescription ready ✓")

        st.session_state.prescription = rx
        st.session_state.week_number  = week_num + 1
        st.success("✅ Your personalized prescription is ready!")

    except Exception as e:
        render("synthesis", "🧠 Orchestrator", "error", str(e)[:80])
        st.error(f"Error: {e}")


def _show_prescription(p):
    st.divider()
    st.markdown(
        f"<div class='info-card' style='border-left:4px solid #3B82F6'>"
        f"<div style='font-size:0.75rem;color:#6B7280;font-weight:600;"
        f"text-transform:uppercase;letter-spacing:.05em'>"
        f"Orchestrator Summary — Week {p.week_number}</div>"
        f"<div style='font-size:1rem;color:#1a1a2e;margin-top:.5rem;"
        f"line-height:1.7'>{p.orchestrator_notes}</div></div>",
        unsafe_allow_html=True
    )

    # v2: Export buttons
    col1, col2, _ = st.columns([1, 1, 3])
    with col1:
        if st.button("📄 Download PDF", width="stretch"):
            from pathlib import Path
            out_path = Path("data/exports") / f"{st.session_state.user_id}_week{p.week_number}.pdf"
            profile = load_profile(st.session_state.user_id)
            try:
                export_prescription_to_pdf(p, out_path, user_name=profile.name)
                with open(out_path, "rb") as f:
                    st.download_button(
                        "Click to download PDF",
                        f.read(),
                        file_name=out_path.name,
                        mime="application/pdf",
                        key=f"dl_pdf_{p.week_number}",
                    )
            except ImportError:
                st.error("PDF export requires reportlab. Run: pip install reportlab")
    with col2:
        if st.button("📅 Export to calendar", width="stretch"):
            from pathlib import Path
            out_path = Path("data/exports") / f"{st.session_state.user_id}_week{p.week_number}.ics"
            profile = load_profile(st.session_state.user_id)
            export_prescription_to_ics(p, out_path, user_name=profile.name)
            with open(out_path, "rb") as f:
                st.download_button(
                    "⬇️ Click to download .ics",
                    f.read(),
                    file_name=out_path.name,
                    mime="text/calendar",
                    key=f"dl_ics_{p.week_number}",
                )

    if p.adaptation_signals:
        st.markdown("#### Adaptation Signals")
        for s in p.adaptation_signals:
            cls = f"signal-{s.severity}"
            st.markdown(
                f"<span class='{cls}'>{s.signal_type.replace('_', ' ').title()}"
                f" · {s.severity}</span> &nbsp; {s.description}"
                f"<br><span style='color:#6B7280;font-size:.85rem'>"
                f"→ {s.recommended_action}</span>",
                unsafe_allow_html=True
            )
            st.markdown("")

    if p.conflicts_resolved:
        st.markdown("#### Conflicts Resolved")
        for c in p.conflicts_resolved:
            st.info(f"{c}")

    # Agent conversation log
    if p.agent_log:
        with st.expander(" Agent Decision Log — see how each agent reasoned",
                          expanded=False):
            for entry in p.agent_log:
                st.markdown(
                    f"**{entry['icon']} {entry['agent']}** "
                    f"<span style='color:#6B7280;font-size:.85rem'>"
                    f"{entry['timestamp']}</span>",
                    unsafe_allow_html=True
                )
                st.markdown(
                    f"&nbsp;&nbsp;&nbsp;✦ **{entry['decision']}**"
                )
                if entry.get("detail"):
                    st.caption(f"&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;{entry['detail'][:200]}")
                st.markdown("---")

    # Knowledge used panel
    if p.knowledge_used:
        with st.expander(
            f"📚 Knowledge Base Used — {len(p.knowledge_used)} evidence-based sources",
            expanded=False
        ):
            st.caption(
                "These are the fitness science and nutrition guidelines "
                "the AI agents retrieved to inform your plan."
            )
            for i, chunk in enumerate(p.knowledge_used[:6], 1):
                relevance = chunk.get("relevance", 0)
                content   = chunk.get("content", "")
                tags      = chunk.get("tags", [])

                # Color by relevance
                color = ("#166534" if relevance > 0.7
                         else "#92400E" if relevance > 0.5
                         else "#374151")
                bar   = "█" * int(relevance * 10) + "░" * (10 - int(relevance * 10))

                st.markdown(
                    f"**Source {i}** &nbsp; "
                    f"<span style='color:{color};font-family:monospace'>"
                    f"{bar}</span> &nbsp; "
                    f"<span style='color:#6B7280;font-size:.8rem'>"
                    f"relevance: {relevance:.2f}</span>",
                    unsafe_allow_html=True
                )
                st.markdown(
                    f"<div style='background:#F9FAFB;padding:.8rem 1rem;"
                    f"border-radius:8px;border-left:3px solid #E5E7EB;"
                    f"font-size:.9rem;color:#374151;margin:.3rem 0 .8rem'>"
                    f"{content}</div>",
                    unsafe_allow_html=True
                )
                if tags:
                    tag_html = " ".join(
                        f"<span style='background:#EFF6FF;color:#1D4ED8;"
                        f"padding:2px 8px;border-radius:10px;font-size:.75rem'>"
                        f"{t}</span>"
                        for t in tags[:4]
                    )
                    st.markdown(tag_html, unsafe_allow_html=True)
                st.markdown("")

    col1, col2 = st.columns(2)

    with col1:
        st.markdown("#### Workout Plan")
        st.caption(f"{p.workout_plan.weekly_volume_sets} sets/week · "
                   f"{p.workout_plan.notes}")
        for day in p.workout_plan.days:
            with st.expander(
                f"**{day.day_name}** · {day.focus} · "
                f"~{day.estimated_duration_minutes} min"
            ):
                for ex in day.exercises:
                    reps = (str(ex.reps).lstrip("-").replace(".0", "")
                            if ex.reps else "?")
                    if ex.duration_minutes:
                        st.markdown(f"**{ex.name}** — {ex.duration_minutes} min")
                    else:
                        st.markdown(
                            f"**{ex.name}** — "
                            f"{ex.sets} × {reps} reps | "
                            f"rest {ex.rest_seconds}s"
                        )
                    if ex.notes:
                        st.caption(f"↳ {ex.notes}")

    with col2:
        st.markdown("#### Nutrition Plan")
        st.caption(
            f"{p.nutrition_plan.target_calories:.0f} kcal · "
            f"{p.nutrition_plan.target_protein_g:.0f}g protein/day"
        )
        for day in p.nutrition_plan.daily_plans:
            actual_cal  = sum(m.calories  for m in day.meals)
            actual_pro  = sum(m.protein_g for m in day.meals)
            actual_carb = sum(m.carbs_g   for m in day.meals)
            actual_fat  = sum(m.fats_g    for m in day.meals)
            with st.expander(
                f"**{day.day_name}** · {actual_cal:.0f} kcal · "
                f"P:{actual_pro:.0f}g "
                f"C:{actual_carb:.0f}g "
                f"F:{actual_fat:.0f}g"
            ):
                for meal in day.meals:
                    st.markdown(
                        f"**{meal.meal_name}** "
                        f"({meal.calories:.0f} kcal · P:{meal.protein_g:.0f}g)"
                    )
                    for food in meal.foods:
                        st.markdown(f"  • {food}")

# ── Check-in ──────────────────────────────────────────────────────────────────
def show_checkin(profile):
    st.markdown("## Daily Check-in")
    st.caption("Log your data daily — this is what the Progress Agent uses to detect trends.")
    st.divider()

    col1, col2 = st.columns(2)
    with col1:
        st.markdown("#### Body & Nutrition")
        log_date     = st.date_input("Date", datetime.now())
        log_weight   = st.number_input("Weight today (kg)",
                                        30.0, 300.0, float(profile.weight_kg), 0.1)
        log_calories = st.number_input("Calories eaten",
                                        0, 10000, int(profile.tdee_estimate))

    with col2:
        st.markdown("#### Workout")
        log_workout = st.checkbox("I completed my workout today")
        log_rating  = None
        if log_workout:
            log_rating = st.select_slider(
                "How hard was today's workout?",
                ["1 - Very Easy", "2 - Easy", "3 - Moderate",
                 "4 - Hard", "5 - Very Hard"],
                value="3 - Moderate"
            )
        log_notes = st.text_area(
            "Notes (optional)",
            placeholder="e.g. Felt great, slightly sore knees, hit a new PR...",
            height=100
        )

    st.divider()
    st.markdown("#### Any physical discomfort today?")
    st.caption("Selecting these will automatically update your constraints "
               "and the Fitness Agent will avoid related exercises next time.")

    col_a, col_b, col_c = st.columns(3)
    discomforts = []
    with col_a:
        if st.checkbox("🦵 Knee pain"):
            discomforts.append("knee pain — avoid squats, lunges, leg press")
        if st.checkbox("🔙 Lower back pain"):
            discomforts.append("lower back pain — avoid deadlifts, heavy squats")
    with col_b:
        if st.checkbox("💪 Shoulder pain"):
            discomforts.append("shoulder injury — avoid overhead press, dips")
        if st.checkbox("🤝 Wrist pain"):
            discomforts.append("wrist pain — avoid push-ups on palms, barbell curls")
    with col_c:
        if st.checkbox("🦶 Ankle pain"):
            discomforts.append("ankle injury — avoid jumping, running")
        if st.checkbox("😴 General fatigue"):
            discomforts.append("general fatigue — reduce intensity by 30%")

    # Always sync, even when the list is empty (user clearing old constraints)
    st.session_state.active_constraints = discomforts
    set_constraints(st.session_state.user_id, discomforts)
    if discomforts:
        st.info("Constraints saved — your next plan will account for these.")
    else:
        st.caption("_No active constraints — your plan will include all exercises._")
   
    st.divider()
    st.markdown("#### Log Today's Exercises")
    st.caption("Track weights and reps for progressive overload. "
               "The Fitness Agent will use this next week.")

    if "exercise_rows" not in st.session_state:
        st.session_state.exercise_rows = 1

    exercise_logs = []
    for i in range(st.session_state.exercise_rows):
        col_a, col_b, col_c, col_d = st.columns([3, 1, 1, 1])
        with col_a:
            ex_name = st.text_input(f"Exercise", key=f"ex_name_{i}",
                                     placeholder="e.g. Push-ups")
        with col_b:
            ex_sets = st.number_input("Sets", 1, 10, 3, key=f"ex_sets_{i}")
        with col_c:
            ex_reps = st.text_input("Reps", key=f"ex_reps_{i}",
                                     placeholder="8-12")
        with col_d:
            ex_weight = st.number_input("kg", 0.0, 500.0, 0.0,
                                         key=f"ex_weight_{i}",
                                         help="0 for bodyweight")
        if ex_name:
            exercise_logs.append({
                "name": ex_name, "sets": ex_sets,
                "reps": ex_reps, "weight": ex_weight
            })

    if st.button(" Add another exercise", type="secondary"):
        st.session_state.exercise_rows += 1
        st.rerun()

    st.divider()
    if st.button("💾 Save Check-in", type="primary", width="stretch"):
        rating_num = int(log_rating[0]) if log_workout and log_rating else None
        note_full  = log_notes
        if discomforts:
            note_full += " | Discomfort: " + \
                         ", ".join(d.split(" — ")[0] for d in discomforts)

        log_progress(ProgressLog(
            user_id=st.session_state.user_id,
            date=log_date.strftime("%Y-%m-%d"),
            weight_kg=float(log_weight),
            workout_completed=log_workout,
            workout_rating=rating_num,
            calories_eaten=float(log_calories),
            notes=note_full
        ))
        # Log exercises for progressive overload tracking
        from memory.episodic import log_exercise
        for ex in exercise_logs:
            if ex["name"] and ex["reps"]:
                log_exercise(
                    user_id=st.session_state.user_id,
                    date=log_date.strftime("%Y-%m-%d"),
                    exercise_name=ex["name"],
                    sets=int(ex["sets"]),
                    reps=ex["reps"],
                    weight_kg=float(ex["weight"]),
                )
        if exercise_logs:
            st.session_state.exercise_rows = 1

        profile.weight_kg = float(log_weight)
        save_profile(profile)
        st.success("Check-in saved! Your agents will use this data.")
        st.balloons()

# ── History ───────────────────────────────────────────────────────────────────
def show_history():
    st.markdown("## Progress History")
    st.divider()
    import pandas as pd

    days    = st.select_slider("Show last", [7, 14, 30, 60, 90], value=30,
                                format_func=lambda x: f"{x} days")
    logs    = get_recent_logs(st.session_state.user_id, days=days)
    weights = get_weight_series(st.session_state.user_id, days=days)

    if not logs:
        st.info("No history yet. Log your first check-in to start tracking!")
        return

    col1, col2 = st.columns(2)
    with col1:
        st.markdown("#### Weight Trend (last 30 days)")
        if weights:
            import altair as alt
            df = pd.DataFrame(weights)
            df["date"] = pd.to_datetime(df["date"])
            
            # Auto-scale Y axis to ±2kg around the data range
            min_w = df["weight_kg"].min()
            max_w = df["weight_kg"].max()
            padding = max(2.0, (max_w - min_w) * 0.3)
            y_min = round(min_w - padding, 1)
            y_max = round(max_w + padding, 1)
            
            chart = (
                alt.Chart(df)
                .mark_line(
                    point=alt.OverlayMarkDef(size=60, fill="#7CB342"),
                    color="#7CB342",
                    strokeWidth=2.5,
                )
                .encode(
                    x=alt.X(
                        "date:T",
                        axis=alt.Axis(
                            format="%b %d",
                            labelAngle=0,
                            title=None,
                            tickCount="day",
                        ),
                    ),
                    y=alt.Y(
                        "weight_kg:Q",
                        scale=alt.Scale(domain=[y_min, y_max]),
                        axis=alt.Axis(title="kg", titlePadding=10),
                    ),
                    tooltip=[
                        alt.Tooltip("date:T", title="Date", format="%b %d, %Y"),
                        alt.Tooltip("weight_kg:Q", title="Weight (kg)", format=".1f"),
                    ],
                )
                .properties(height=240)
                .configure_view(strokeWidth=0)
                .configure_axis(
                    grid=True,
                    gridColor="#E8E3D5",
                    domainColor="#E8E3D5",
                    tickColor="#E8E3D5",
                    labelColor="#6B7280",
                    titleColor="#6B7280",
                    labelFontSize=11,
                )
            )
            st.altair_chart(chart, width="stretch")
        else:
            st.info("No weight data yet — log your first check-in to start tracking.")
    with col2:
        st.markdown("#### Daily Calories")
        df2 = pd.DataFrame(logs)
        df2 = df2[df2["calories_eaten"].notna()]
        if not df2.empty:
            import altair as alt
            df2["date"] = pd.to_datetime(df2["date"])
            chart = (
                alt.Chart(df2)
                .mark_bar(color="#7CB342", size=12)
                .encode(
                    x=alt.X(
                        "date:T",
                        axis=alt.Axis(format="%b %d", labelAngle=0, title=None, tickCount="day"),
                    ),
                    y=alt.Y("calories_eaten:Q", axis=alt.Axis(title="kcal", titlePadding=10)),
                    tooltip=[
                        alt.Tooltip("date:T", title="Date", format="%b %d"),
                        alt.Tooltip("calories_eaten:Q", title="Calories", format=".0f"),
                    ],
                )
                .properties(height=240)
                .configure_view(strokeWidth=0)
                .configure_axis(
                    grid=True, gridColor="#E8E3D5",
                    domainColor="#E8E3D5", tickColor="#E8E3D5",
                    labelColor="#6B7280", titleColor="#6B7280", labelFontSize=11,
                )
            )
            st.altair_chart(chart, width="stretch")

    st.markdown("#### Full Log")
    df3 = pd.DataFrame(logs)
    df3["Date"]       = pd.to_datetime(df3["date"]).dt.strftime("%b %d, %Y")
    df3["Workout"]    = df3["workout_completed"].apply(lambda x: "✅" if x else "—")
    df3["Difficulty"] = df3["workout_rating"].apply(
        lambda x: f"{int(x)}/5" if pd.notna(x) and x else "—")
    df3["Weight"]     = df3["weight_kg"].apply(lambda x: f"{x} kg" if pd.notna(x) and x else "—")
    df3["Calories"]   = df3["calories_eaten"].apply(
        lambda x: f"{x:.0f}" if pd.notna(x) and x else "—")
    st.dataframe(
        df3[["Date", "Workout", "Difficulty", "Weight", "Calories", "notes"]]
        .rename(columns={"notes": "Notes"})
        .sort_values("Date", ascending=False),
        width="stretch", hide_index=True
    )
    st.divider()
    st.markdown("#### Exercise History")
    from memory.episodic import get_all_logged_exercises, get_exercise_history
    exercises = get_all_logged_exercises(st.session_state.user_id, days=60)
    if exercises:
        selected_ex = st.selectbox("Select exercise to view progression",
                                    exercises)
        if selected_ex:
            history = get_exercise_history(
                st.session_state.user_id, selected_ex, days=60)
            if history:
                df_ex = pd.DataFrame(history)
                df_ex["Date"] = pd.to_datetime(df_ex["date"]).dt.strftime("%b %d")
                df_ex["Performance"] = df_ex.apply(
                    lambda r: f"{r['sets_completed']}×{r['reps_completed']}"
                              f"{' @ ' + str(r['weight_kg']) + 'kg' if r['weight_kg'] > 0 else ' (BW)'}",
                    axis=1
                )
                st.dataframe(
                    df_ex[["Date", "Performance", "notes"]]
                    .rename(columns={"notes": "Notes"}),
                    width="stretch", hide_index=True
                )
                if len(history) >= 2 and all(
                    r["weight_kg"] > 0 for r in history[:2]):
                    st.line_chart(
                        pd.DataFrame(history).set_index("date")["weight_kg"],
                        height=150
                    )
    else:
        st.info("No exercise history yet. Log exercises in the Check-in tab.")

# ── Profile settings ──────────────────────────────────────────────────────────
def show_profile(profile):
    st.markdown("## Profile Settings")
    st.divider()

    col1, col2 = st.columns(2)
    with col1:
        st.markdown("#### Basic Info")
        new_weight   = st.number_input("Weight (kg)", value=profile.weight_kg,
                                        step=0.5)
        new_age      = st.number_input("Age", value=profile.age,
                                        min_value=16, max_value=80)
        new_sessions = st.slider("Sessions per week", 2, 6,
                                  profile.sessions_per_week)

    with col2:
        st.markdown("#### Goals")
        goals    = ["muscle_gain", "weight_loss", "endurance", "maintenance"]
        new_goal = st.selectbox(
            "Goal", goals,
            index=goals.index(profile.goal),
            format_func=lambda x: x.replace("_", " ").title()
        )
        levels   = ["beginner", "intermediate", "advanced"]
        new_lvl  = st.selectbox(
            "Fitness level", levels,
            index=levels.index(profile.fitness_level),
            format_func=str.title
        )
        new_diet = st.multiselect("Dietary restrictions", [
            "vegetarian", "vegan", "gluten_free", "dairy_free", "halal"
        ], default=profile.dietary_restrictions)

    new_equip = st.multiselect("Available equipment", [
        "bodyweight", "dumbbells", "barbell", "pull_up_bar",
        "resistance_bands", "kettlebell", "gym_machines", "bench"
    ], default=profile.available_equipment)

    st.divider()
    if st.button("💾 Save Changes", type="primary"):
        profile.weight_kg            = float(new_weight)
        profile.age                  = int(new_age)
        profile.sessions_per_week    = int(new_sessions)
        profile.goal                 = new_goal
        profile.fitness_level        = new_lvl
        profile.dietary_restrictions = new_diet
        profile.available_equipment  = new_equip or ["bodyweight"]
        save_profile(profile)
        st.success("Profile updated!")

    st.divider()
    st.markdown("#### Developer Tools")
    c1, c2 = st.columns(2)
    with c1:
        if st.button("Seed 3 Weeks Test Data", width="stretch"):
            seed_test_data(st.session_state.user_id, weeks=3)
            st.success("✓ Done")
    with c2:
        from memory.episodic import clear_user_data
        if st.button("Clear All My Data", width="stretch"):
            clear_user_data(st.session_state.user_id)
            st.success("✓ Cleared")

# ── Main ──────────────────────────────────────────────────────────────────────
def main():
    if not st.session_state.logged_in:
        show_auth()
        return

    profile = load_profile(st.session_state.user_id)
    if profile is None:
        show_onboarding()
        return

    show_sidebar(profile)

    page = st.session_state.page
    if page == "dashboard":
        show_dashboard(profile)
    elif page == "plan":
        show_plan(profile)
    elif page == "checkin":
        show_checkin(profile)
    elif page == "history":
        show_history()
    elif page == "profile":
        show_profile(profile)
    elif page == "photos":
        show_photos(profile)

if __name__ == "__main__":
    main()