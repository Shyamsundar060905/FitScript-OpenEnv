import os
import pathlib

try:
    import streamlit as st
    GROQ_API_KEY   = st.secrets.get("GROQ_API_KEY", os.getenv("GROQ_API_KEY", ""))
    GEMINI_API_KEY = st.secrets.get("GEMINI_API_KEY", os.getenv("GEMINI_API_KEY", ""))
except Exception:
    from dotenv import load_dotenv
    load_dotenv()
    GROQ_API_KEY   = os.getenv("GROQ_API_KEY", "")
    GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")

GROQ_MODEL   = "llama-3.3-70b-versatile"
GEMINI_MODEL = "gemini-2.0-flash"
OLLAMA_MODEL = "llama3"
LLM_TIMEOUT  = 30

BASE_DIR    = pathlib.Path(__file__).parent
DATA_DIR    = BASE_DIR / "data"
USERS_DIR   = DATA_DIR / "users"
KB_DIR      = DATA_DIR / "knowledge_base"
EPISODIC_DB = DATA_DIR / "episodic.db"
AUTH_DB     = DATA_DIR / "auth.db"
CHROMA_DIR  = DATA_DIR / "chroma"
PHOTOS_DIR  = DATA_DIR / "photos"

PLATEAU_WINDOW_DAYS      = 14
PLATEAU_WEIGHT_THRESHOLD = 0.3
MAX_RETRIES              = 3

# Rate limiting
AGENT_RUN_COOLDOWN_SECONDS = 30
MAX_AGENT_RUNS_PER_DAY     = 20