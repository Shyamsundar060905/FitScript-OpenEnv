"""
FitAgent FastAPI Backend
Thin wrapper over existing agents/utils — no logic changes.
Designed to be deployed on Render.
"""

from __future__ import annotations
import os, sys, json, time
from pathlib import Path
from typing import Optional, List
from datetime import datetime

# Add project root to sys.path (assumes api.py lives at <root>/backend/api.py)
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from fastapi import FastAPI, HTTPException, Depends, Header, Query, UploadFile, File, Form
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from pydantic import BaseModel
import uvicorn

# ── Project imports ──────────────────────────────────────────────────────────
from memory.long_term import load_profile, save_profile
from memory.episodic import (
    init_db, log_progress, get_recent_logs, get_weight_series,
    get_active_constraints, set_constraints,
    get_all_logged_exercises, get_exercise_history,
    log_exercise,
)
from utils.auth import create_account as auth_create, verify_login as auth_login, AuthError
from utils.session import create_session, lookup_session, destroy_session
from utils.prescription_store import rehydrate_latest_prescription
from utils.rate_limit import get_usage_stats
from utils.observability import summarize_recent_runs
from utils.export import export_prescription_to_pdf, export_prescription_to_ics
from utils.photos import save_photo, list_photos, remove_photo, PhotoUploadError
from agents.orchestrator import run_pipeline, RateLimitExceeded
from agents.progress_agent import seed_test_data
from schemas import ProgressLog, UserProfile
from config import USERS_DIR

# ── App setup ────────────────────────────────────────────────────────────────
app = FastAPI(title="FitAgent API", version="2.0")

# CORS — allow configured origins only. In dev defaults to localhost; in prod
# set ALLOWED_ORIGINS env var on Render to your Vercel URL.
_origins_env = os.getenv("ALLOWED_ORIGINS", "")
ALLOWED_ORIGINS = (
    [o.strip() for o in _origins_env.split(",") if o.strip()]
    if _origins_env
    else ["http://localhost:5173", "http://127.0.0.1:5173"]
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
@app.on_event("startup")
def startup():
    init_db()


# ── Auth dependencies ─────────────────────────────────────────────────────────

def _resolve_token(authorization: Optional[str], token: Optional[str]) -> dict:
    """Shared logic: resolve session from Bearer header or ?token= query param."""
    raw = token
    if not raw and authorization and authorization.startswith("Bearer "):
        raw = authorization.split(" ", 1)[1]
    if not raw:
        raise HTTPException(status_code=401, detail="Not authenticated")
    info = lookup_session(raw)
    if not info:
        raise HTTPException(status_code=401, detail="Session expired or invalid")
    return info


def require_user(authorization: Optional[str] = Header(None)) -> dict:
    """Standard dependency for all JSON API routes (Authorization: Bearer <token>)."""
    return _resolve_token(authorization, None)


def require_user_download(
    authorization: Optional[str] = Header(None),
    token: Optional[str] = Query(None),
) -> dict:
    """Dependency for file-download routes.
    Accepts both Authorization header AND ?token= query param because
    browser <a href> navigation cannot send custom headers."""
    return _resolve_token(authorization, token)


# ── Pydantic models ───────────────────────────────────────────────────────────

class LoginRequest(BaseModel):
    username: str
    password: str

class SignupRequest(BaseModel):
    username: str
    password: str

class AuthResponse(BaseModel):
    token: str
    user_id: str
    username: str

class ProfileCreate(BaseModel):
    name: str
    age: int
    weight_kg: float
    height_cm: float
    goal: str
    fitness_level: str
    dietary_restrictions: List[str] = []
    available_equipment: List[str] = ["bodyweight"]
    sessions_per_week: int = 4
    tdee_estimate: float = 2000.0

class ProfileUpdate(BaseModel):
    weight_kg: Optional[float] = None
    age: Optional[int] = None
    sessions_per_week: Optional[int] = None
    goal: Optional[str] = None
    fitness_level: Optional[str] = None
    dietary_restrictions: Optional[List[str]] = None
    available_equipment: Optional[List[str]] = None

class CheckinRequest(BaseModel):
    date: str
    weight_kg: float
    calories_eaten: float
    workout_completed: bool
    workout_rating: Optional[int] = None
    notes: str = ""
    discomforts: List[str] = []
    exercises: List[dict] = []

class ConstraintsRequest(BaseModel):
    constraints: List[str]

class RunPipelineRequest(BaseModel):
    week_number: int = 1


# ── Auth routes ───────────────────────────────────────────────────────────────

@app.post("/auth/login", response_model=AuthResponse)
def login(body: LoginRequest):
    uid = auth_login(body.username, body.password)
    if not uid:
        raise HTTPException(status_code=401, detail="Invalid username or password")
    token = create_session(body.username)
    return {"token": token, "user_id": uid, "username": body.username}


@app.post("/auth/signup", response_model=AuthResponse)
def signup(body: SignupRequest):
    try:
        auth_create(body.username, body.password)
    except AuthError as e:
        raise HTTPException(status_code=400, detail=str(e))
    uid = auth_login(body.username, body.password)
    token = create_session(body.username)
    return {"token": token, "user_id": uid, "username": body.username}


@app.post("/auth/logout")
def logout(authorization: Optional[str] = Header(None)):
    if authorization and authorization.startswith("Bearer "):
        destroy_session(authorization.split(" ", 1)[1])
    return {"ok": True}


# ── Profile routes ────────────────────────────────────────────────────────────

@app.get("/profile")
def get_profile(user: dict = Depends(require_user)):
    profile = load_profile(user["user_id"])
    if not profile:
        raise HTTPException(status_code=404, detail="Profile not found")
    return profile.model_dump()


@app.post("/profile")
def create_profile(body: ProfileCreate, user: dict = Depends(require_user)):
    profile = UserProfile(user_id=user["user_id"], **body.model_dump())
    save_profile(profile)
    return profile.model_dump()


@app.patch("/profile")
def update_profile(body: ProfileUpdate, user: dict = Depends(require_user)):
    profile = load_profile(user["user_id"])
    if not profile:
        raise HTTPException(status_code=404, detail="Profile not found")
    updates = {k: v for k, v in body.model_dump().items() if v is not None}
    # Ensure equipment list never becomes empty
    if "available_equipment" in updates and not updates["available_equipment"]:
        updates["available_equipment"] = ["bodyweight"]
    for k, v in updates.items():
        setattr(profile, k, v)
    save_profile(profile)
    return profile.model_dump()


# ── Constraints ───────────────────────────────────────────────────────────────

@app.get("/constraints")
def get_constraints(user: dict = Depends(require_user)):
    return {"constraints": get_active_constraints(user["user_id"])}


@app.post("/constraints")
def update_constraints(body: ConstraintsRequest, user: dict = Depends(require_user)):
    set_constraints(user["user_id"], body.constraints)
    return {"constraints": body.constraints}


# ── Agent pipeline ────────────────────────────────────────────────────────────

@app.post("/plan/run")
def run_plan(body: RunPipelineRequest, user: dict = Depends(require_user)):
    constraints = get_active_constraints(user["user_id"])
    constraint_context = ""
    if constraints:
        constraint_context = (
            "User has these physical constraints — avoid exercises that would aggravate: "
            + "; ".join(constraints)
        )
    try:
        rx = run_pipeline(
            user["user_id"],
            week_number=body.week_number,
            constraint_context=constraint_context,
        )
    except RateLimitExceeded as e:
        d = e.decision
        raise HTTPException(
            status_code=429,
            detail={
                "reason": d.reason,
                "retry_after_seconds": d.retry_after_seconds,
                "remaining_today": d.remaining_today,
            },
        )
    return _serialize_prescription(rx)


@app.get("/plan/latest")
def get_latest_plan(user: dict = Depends(require_user)):
    rx = rehydrate_latest_prescription(user["user_id"])
    if not rx:
        return None
    return _serialize_prescription(rx)


def _serialize_prescription(rx) -> dict:
    return {
        "user_id":            rx.user_id,
        "week_number":        rx.week_number,
        "orchestrator_notes": rx.orchestrator_notes,
        "workout_plan":       rx.workout_plan.model_dump(),
        "nutrition_plan":     rx.nutrition_plan.model_dump(),
        "adaptation_signals": [s.model_dump() for s in rx.adaptation_signals],
        "conflicts_resolved": rx.conflicts_resolved,
        "knowledge_used":     rx.knowledge_used,
        "agent_log":          rx.agent_log,
    }


# ── Export routes — use require_user_download so ?token= works in browser ────

@app.get("/plan/export/pdf/{week_number}")
def export_pdf(
    week_number: int,
    user: dict = Depends(require_user_download),
):
    rx = rehydrate_latest_prescription(user["user_id"])
    if not rx:
        raise HTTPException(status_code=404, detail="No plan found")
    profile = load_profile(user["user_id"])
    out = Path("data/exports") / f"{user['user_id']}_week{week_number}.pdf"
    out.parent.mkdir(parents=True, exist_ok=True)
    export_prescription_to_pdf(rx, out, user_name=profile.name)
    return FileResponse(
        str(out),
        media_type="application/pdf",
        filename=out.name,
        headers={"Content-Disposition": f"attachment; filename={out.name}"},
    )


@app.get("/plan/export/ics/{week_number}")
def export_ics(
    week_number: int,
    user: dict = Depends(require_user_download),
):
    rx = rehydrate_latest_prescription(user["user_id"])
    if not rx:
        raise HTTPException(status_code=404, detail="No plan found")
    profile = load_profile(user["user_id"])
    out = Path("data/exports") / f"{user['user_id']}_week{week_number}.ics"
    out.parent.mkdir(parents=True, exist_ok=True)
    export_prescription_to_ics(rx, out, user_name=profile.name)
    return FileResponse(
        str(out),
        media_type="text/calendar",
        filename=out.name,
        headers={"Content-Disposition": f"attachment; filename={out.name}"},
    )


# ── Check-in / progress ───────────────────────────────────────────────────────

@app.post("/checkin")
def save_checkin(body: CheckinRequest, user: dict = Depends(require_user)):
    note_full = body.notes
    if body.discomforts:
        note_full += " | Discomfort: " + ", ".join(
            d.split(" — ")[0] for d in body.discomforts
        )

    log_progress(ProgressLog(
        user_id=user["user_id"],
        date=body.date,
        weight_kg=body.weight_kg,
        workout_completed=body.workout_completed,
        workout_rating=body.workout_rating,
        calories_eaten=body.calories_eaten,
        notes=note_full,
    ))

    # Always sync constraints (even empty list clears them)
    set_constraints(user["user_id"], body.discomforts)

    # Log individual exercises for progressive overload tracking
    for ex in body.exercises:
        if ex.get("name") and ex.get("reps"):
            log_exercise(
                user_id=user["user_id"],
                date=body.date,
                exercise_name=ex["name"],
                sets=int(ex.get("sets", 3)),
                reps=str(ex["reps"]),
                weight_kg=float(ex.get("weight", 0)),
            )

    # Update profile weight to latest logged value
    profile = load_profile(user["user_id"])
    if profile:
        profile.weight_kg = body.weight_kg
        save_profile(profile)

    return {"ok": True}

# ── Progress photos ───────────────────────────────────────────────────────────

@app.get("/photos")
def photos_list(user: dict = Depends(require_user)):
    """Return the user's photo metadata, most recent first."""
    return list_photos(user["user_id"], limit=50)


@app.post("/photos")
async def photos_upload(
    file: UploadFile = File(...),
    date: Optional[str] = Form(None),
    weight_kg: Optional[float] = Form(None),
    note: str = Form(""),
    user: dict = Depends(require_user),
):
    """
    Upload a progress photo.

    Expects multipart/form-data with:
      - file:      the image (.jpg/.jpeg/.png/.webp/.heic, max 10MB)
      - date:      ISO date string (optional, defaults to today)
      - weight_kg: weight on this day (optional)
      - note:      freeform caption (optional)
    """
    try:
        file_bytes = await file.read()
        result = save_photo(
            user_id=user["user_id"],
            file_bytes=file_bytes,
            original_filename=file.filename or "upload.jpg",
            date=date,
            weight_kg=weight_kg,
            note=note,
        )
        return result
    except PhotoUploadError as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.delete("/photos/{photo_id}")
def photos_delete(photo_id: int, user: dict = Depends(require_user)):
    """Delete a photo (both the file and the DB row)."""
    removed = remove_photo(user["user_id"], photo_id)
    if not removed:
        raise HTTPException(status_code=404, detail="Photo not found")
    return {"ok": True}


@app.get("/photos/{photo_id}/file")
def photos_file(
    photo_id: int,
    user: dict = Depends(require_user_download),
):
    """
    Serve the raw photo bytes.
    Uses require_user_download so <img> tags can auth via ?token=<jwt>.
    Only returns photos owned by the authenticated user — prevents
    one user from viewing another user's photos via ID guessing.
    """
    # Find this photo in the user's gallery and confirm ownership
    photos = list_photos(user["user_id"], limit=500)
    match = next((p for p in photos if p.get("id") == photo_id), None)
    if not match:
        raise HTTPException(status_code=404, detail="Photo not found")

    photo_path = Path(match["photo_path"])
    if not photo_path.exists():
        raise HTTPException(status_code=404, detail="Photo file missing on disk")

    # Infer content type from extension
    ext = photo_path.suffix.lower()
    mime = {
        ".jpg": "image/jpeg", ".jpeg": "image/jpeg",
        ".png": "image/png", ".webp": "image/webp",
        ".heic": "image/heic",
    }.get(ext, "application/octet-stream")

    return FileResponse(str(photo_path), media_type=mime)
# ── History ───────────────────────────────────────────────────────────────────

@app.get("/history/logs")
def get_logs(days: int = 30, user: dict = Depends(require_user)):
    return get_recent_logs(user["user_id"], days=days)


@app.get("/history/weights")
def get_weights(days: int = 30, user: dict = Depends(require_user)):
    return get_weight_series(user["user_id"], days=days)


@app.get("/history/exercises")
def get_exercises(days: int = 60, user: dict = Depends(require_user)):
    return get_all_logged_exercises(user["user_id"], days=days)


@app.get("/history/exercise/{name}")
def get_exercise_detail(name: str, days: int = 60, user: dict = Depends(require_user)):
    return get_exercise_history(user["user_id"], name, days=days)


# ── Usage & diagnostics ───────────────────────────────────────────────────────

@app.get("/usage")
def usage(user: dict = Depends(require_user)):
    stats = get_usage_stats(user["user_id"])
    runs  = summarize_recent_runs(user["user_id"])
    return {"rate_limit": stats, "runs": runs}


# ── Dev tools ─────────────────────────────────────────────────────────────────

@app.post("/dev/seed")
def seed_data(weeks: int = 3, user: dict = Depends(require_user)):
    seed_test_data(user["user_id"], weeks=weeks)
    return {"ok": True}


@app.delete("/dev/clear")
def clear_data(user: dict = Depends(require_user)):
    from memory.episodic import clear_user_data
    clear_user_data(user["user_id"])
    return {"ok": True}


# ── Health ────────────────────────────────────────────────────────────────────

@app.get("/health")
def health():
    return {"status": "ok", "ts": time.time()}


if __name__ == "__main__":
    uvicorn.run("api:app", host="0.0.0.0", port=8000, reload=True)
