"""
FitAgent AI — Streamlit Application
"""

import streamlit as st
import sys, os, json, hashlib, time
from datetime import datetime, timedelta
from pathlib import Path

sys.path.append(os.path.dirname(__file__))

from memory.long_term import load_profile, save_profile
from memory.episodic import init_db, log_progress, get_recent_logs, get_weight_series
from agents.progress_agent import seed_test_data
from schemas import ProgressLog, UserProfile
from config import USERS_DIR

# ── Page config ───────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="FitAgent AI",
    page_icon="💪",
    layout="wide",
    initial_sidebar_state="expanded"
)

st.markdown("""
<style>
.metric-card {
    background: white;
    border-radius: 12px;
    padding: 1.2rem;
    text-align: center;
    border: 1px solid #E5E7EB;
    margin-bottom: 0.5rem;
}
.metric-value { font-size: 1.8rem; font-weight: 700; color: #1a1a2e; }
.metric-label { font-size: 0.75rem; color: #6B7280; text-transform: uppercase;
                letter-spacing: 0.05em; margin-top: 0.2rem; }
.agent-step { padding: 10px 16px; border-radius: 8px; margin: 4px 0;
              font-size: 0.9rem; font-weight: 500; }
.agent-done { background: #F0FDF4; color: #166534; border-left: 3px solid #22C55E; }
.agent-running { background: #EFF6FF; color: #1D4ED8; border-left: 3px solid #3B82F6; }
.agent-pending { background: #F9FAFB; color: #9CA3AF; border-left: 3px solid #E5E7EB; }
.signal-high { background: #FEE2E2; color: #991B1B; padding: 3px 10px;
               border-radius: 12px; font-size: 0.8rem; font-weight: 600; }
.signal-medium { background: #FEF3C7; color: #92400E; padding: 3px 10px;
                 border-radius: 12px; font-size: 0.8rem; font-weight: 600; }
.signal-low { background: #D1FAE5; color: #065F46; padding: 3px 10px;
              border-radius: 12px; font-size: 0.8rem; font-weight: 600; }
.info-card { background: white; border-radius: 12px; padding: 1.5rem;
             border: 1px solid #E5E7EB; margin-bottom: 1rem; }
#MainMenu { visibility: hidden; }
footer { visibility: hidden; }
</style>
""", unsafe_allow_html=True)

# ── Init ──────────────────────────────────────────────────────────────────────
if "db_initialized" not in st.session_state:
    init_db()
    st.session_state.db_initialized = True

AUTH_FILE = USERS_DIR / "auth.json"

def load_auth():
    USERS_DIR.mkdir(parents=True, exist_ok=True)
    if not AUTH_FILE.exists():
        return {}
    return json.loads(AUTH_FILE.read_text())

def save_auth(auth):
    AUTH_FILE.write_text(json.dumps(auth, indent=2))

def hash_pw(pw): return hashlib.sha256(pw.encode()).hexdigest()

def create_account(username, password):
    auth = load_auth()
    if username in auth: return False
    auth[username] = {
        "password": hash_pw(password),
        "user_id": f"user_{username.lower().replace(' ','_')}",
        "created_at": datetime.now().isoformat()
    }
    save_auth(auth)
    return True

def verify_login(username, password):
    auth = load_auth()
    if username not in auth: return None
    if auth[username]["password"] == hash_pw(password):
        return auth[username]["user_id"]
    return None

# ── Session defaults ──────────────────────────────────────────────────────────
for k, v in {
    "logged_in": False, "username": None, "user_id": None,
    "page": "dashboard", "prescription": None, "week_number": 1,
    "active_constraints": []
}.items():
    if k not in st.session_state:
        st.session_state[k] = v

# ── Auth page ─────────────────────────────────────────────────────────────────
def show_auth():
    _, col, _ = st.columns([1, 1.2, 1])
    with col:
        st.markdown("<br><br>", unsafe_allow_html=True)
        st.markdown("# 💪 FitAgent AI")
        st.markdown("*Your personal multi-agent fitness & nutrition coach*")
        st.markdown("<br>", unsafe_allow_html=True)

        tab1, tab2 = st.tabs(["Login", "Sign Up"])

        with tab1:
            u = st.text_input("Username", key="lu")
            p = st.text_input("Password", type="password", key="lp")
            if st.button("Login", type="primary", use_container_width=True):
                uid = verify_login(u, p)
                if uid:
                    st.session_state.update(logged_in=True, username=u, user_id=uid)
                    st.rerun()
                else:
                    st.error("Invalid credentials")

        with tab2:
            u2 = st.text_input("Username", key="su")
            p2 = st.text_input("Password", type="password", key="sp")
            p3 = st.text_input("Confirm password", type="password", key="sp2")
            if st.button("Create Account", type="primary", use_container_width=True):
                if len(p2) < 6:
                    st.error("Password must be at least 6 characters")
                elif p2 != p3:
                    st.error("Passwords don't match")
                elif create_account(u2, p2):
                    uid = verify_login(u2, p2)
                    st.session_state.update(logged_in=True, username=u2, user_id=uid)
                    st.rerun()
                else:
                    st.error("Username already taken")

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
    if st.button("🚀 Create My Profile", type="primary", use_container_width=True):
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

# ── Sidebar ───────────────────────────────────────────────────────────────────
def show_sidebar(profile):
    with st.sidebar:
        st.markdown("### 💪 FitAgent AI")
        st.markdown(f"**{profile.name}**  \n"
                    f"{profile.goal.replace('_', ' ').title()} · "
                    f"{profile.fitness_level.title()}")
        st.divider()

        nav = {
            "dashboard": "🏠 Dashboard",
            "plan":      "📋 My Plan",
            "checkin":   "✏️ Daily Check-in",
            "history":   "📊 History",
            "profile":   "👤 Profile Settings",
        }
        for key, label in nav.items():
            is_active = st.session_state.page == key
            if st.button(label, use_container_width=True,
                         type="primary" if is_active else "secondary"):
                st.session_state.page = key
                st.rerun()

        st.divider()
        if st.button("Logout", use_container_width=True):
            for k, v in {
                "logged_in": False, "username": None, "user_id": None,
                "page": "dashboard", "prescription": None,
                "week_number": 1, "active_constraints": []
            }.items():
                st.session_state[k] = v
            st.rerun()

# ── Dashboard ─────────────────────────────────────────────────────────────────
def show_dashboard(profile):
    st.markdown("## 🏠 Dashboard")
    greeting = ("morning" if datetime.now().hour < 12
                else "afternoon" if datetime.now().hour < 17
                else "evening")
    st.markdown(f"Good {greeting}, **{profile.name}**!")
    st.divider()

    import pandas as pd
    logs    = get_recent_logs(st.session_state.user_id, days=30)
    weights = get_weight_series(st.session_state.user_id, days=30)

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
        st.markdown("#### 📈 Weight Trend (last 30 days)")
        if weights:
            df = pd.DataFrame(weights)
            df["date"] = pd.to_datetime(df["date"])
            st.line_chart(df.set_index("date")["weight_kg"],
                          height=220, use_container_width=True)
        else:
            st.info("No weight data yet — log your first check-in to start tracking.")

    with col2:
        st.markdown("#### 🎯 Your Goal")
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
    st.markdown("#### ⚡ Quick Actions")
    c1, c2, c3 = st.columns(3)
    with c1:
        if st.button("📋 Generate This Week's Plan",
                     type="primary", use_container_width=True):
            st.session_state.page = "plan"
            st.rerun()
    with c2:
        if st.button("✏️ Log Today's Check-in", use_container_width=True):
            st.session_state.page = "checkin"
            st.rerun()
    with c3:
        if st.button("🧪 Seed 3 Weeks Test Data", use_container_width=True):
            seed_test_data(st.session_state.user_id, weeks=3)
            st.success("✓ Test data seeded — refresh to see charts")
            st.rerun()

    if logs:
        st.divider()
        st.markdown("#### 📅 Recent Activity")
        df2 = pd.DataFrame(logs[-7:])
        df2["Date"]       = pd.to_datetime(df2["date"]).dt.strftime("%b %d")
        df2["Workout"]    = df2["workout_completed"].apply(lambda x: "✅" if x else "—")
        df2["Difficulty"] = df2["workout_rating"].apply(
            lambda x: "⭐" * int(x) if x else "—")
        df2["Weight"]     = df2["weight_kg"].apply(lambda x: f"{x} kg" if x else "—")
        df2["Calories"]   = df2["calories_eaten"].apply(
            lambda x: f"{x:.0f}" if x else "—")
        st.dataframe(
            df2[["Date", "Workout", "Difficulty", "Weight", "Calories", "notes"]]
            .rename(columns={"notes": "Notes"}),
            use_container_width=True, hide_index=True
        )

# ── Plan page ─────────────────────────────────────────────────────────────────
def show_plan(profile):
    st.markdown("## 📋 My Weekly Plan")

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
                        use_container_width=True)

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

    st.markdown("### 🤖 Agent Pipeline")
    steps = [
        ("profile",   "👤 Profile Agent",     "Loading user profile"),
        ("progress",  "📊 Progress Agent",    "Analyzing progress history"),
        ("fitness",   "💪 Fitness Agent",     "Generating workout plan"),
        ("nutrition", "🥗 Nutrition Agent",   "Building nutrition plan"),
        ("conflicts", "⚡ Conflict Resolver", "Checking for conflicts"),
        ("synthesis", "🧠 Orchestrator",      "Synthesizing prescription"),
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

        rx = run_pipeline(
            st.session_state.user_id,
            week_number=week_num,
            constraint_context=constraint_context
        )

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

    if p.adaptation_signals:
        st.markdown("#### 📊 Adaptation Signals")
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
        st.markdown("#### ⚡ Conflicts Resolved")
        for c in p.conflicts_resolved:
            st.info(f"⚡ {c}")

    # Agent conversation log
    if p.agent_log:
        with st.expander("🤖 Agent Decision Log — see how each agent reasoned",
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
        st.markdown("#### 💪 Workout Plan")
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
        st.markdown("#### 🥗 Nutrition Plan")
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
    st.markdown("## ✏️ Daily Check-in")
    st.caption("Log your data daily — this is what the Progress Agent uses to detect trends.")
    st.divider()

    col1, col2 = st.columns(2)
    with col1:
        st.markdown("#### 📏 Body & Nutrition")
        log_date     = st.date_input("Date", datetime.now())
        log_weight   = st.number_input("Weight today (kg)",
                                        30.0, 300.0, float(profile.weight_kg), 0.1)
        log_calories = st.number_input("Calories eaten",
                                        0, 10000, int(profile.tdee_estimate))

    with col2:
        st.markdown("#### 🏋️ Workout")
        log_workout = st.checkbox("I completed my workout today ✅")
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
    st.markdown("#### 🩺 Any physical discomfort today?")
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

    if discomforts:
        st.session_state.active_constraints = discomforts
        st.info("✅ Constraints updated — your next plan will account for these.")

    st.divider()
    st.markdown("#### 🏋️ Log Today's Exercises")
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

    if st.button("➕ Add another exercise", type="secondary"):
        st.session_state.exercise_rows += 1
        st.rerun()

    st.divider()
    if st.button("💾 Save Check-in", type="primary", use_container_width=True):
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
        st.success("✅ Check-in saved! Your agents will use this data.")
        st.balloons()

# ── History ───────────────────────────────────────────────────────────────────
def show_history():
    st.markdown("## 📊 Progress History")
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
        st.markdown("#### ⚖️ Weight Over Time")
        if weights:
            df = pd.DataFrame(weights)
            df["date"] = pd.to_datetime(df["date"])
            st.line_chart(df.set_index("date")["weight_kg"],
                          height=200, use_container_width=True)

    with col2:
        st.markdown("#### 🔥 Daily Calories")
        df2 = pd.DataFrame(logs)
        df2 = df2[df2["calories_eaten"].notna()]
        if not df2.empty:
            df2["date"] = pd.to_datetime(df2["date"])
            st.bar_chart(df2.set_index("date")["calories_eaten"],
                         height=200, use_container_width=True)

    st.markdown("#### 📅 Full Log")
    df3 = pd.DataFrame(logs)
    df3["Date"]       = pd.to_datetime(df3["date"]).dt.strftime("%b %d, %Y")
    df3["Workout"]    = df3["workout_completed"].apply(lambda x: "✅" if x else "—")
    df3["Difficulty"] = df3["workout_rating"].apply(
        lambda x: f"{x}/5" if x else "—")
    df3["Weight"]     = df3["weight_kg"].apply(lambda x: f"{x} kg" if x else "—")
    df3["Calories"]   = df3["calories_eaten"].apply(
        lambda x: f"{x:.0f}" if x else "—")
    st.dataframe(
        df3[["Date", "Workout", "Difficulty", "Weight", "Calories", "notes"]]
        .rename(columns={"notes": "Notes"})
        .sort_values("Date", ascending=False),
        use_container_width=True, hide_index=True
    )
    st.divider()
    st.markdown("#### 💪 Exercise History")
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
                    use_container_width=True, hide_index=True
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
    st.markdown("## 👤 Profile Settings")
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
        st.success("✅ Profile updated!")

    st.divider()
    st.markdown("#### 🔬 Developer Tools")
    c1, c2 = st.columns(2)
    with c1:
        if st.button("🧪 Seed 3 Weeks Test Data", use_container_width=True):
            seed_test_data(st.session_state.user_id, weeks=3)
            st.success("✓ Done")
    with c2:
        from memory.episodic import clear_user_data
        if st.button("🗑️ Clear All My Data", use_container_width=True):
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


if __name__ == "__main__":
    main()