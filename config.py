import os
from pathlib import Path

# Try Streamlit secrets first, fall back to .env
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

import pathlib
BASE_DIR    = pathlib.Path(__file__).parent
DATA_DIR    = BASE_DIR / "data"
USERS_DIR   = DATA_DIR / "users"
KB_DIR      = DATA_DIR / "knowledge_base"
EPISODIC_DB = DATA_DIR / "episodic.db"
CHROMA_DIR  = DATA_DIR / "chroma"

PLATEAU_WINDOW_DAYS      = 14
PLATEAU_WEIGHT_THRESHOLD = 0.3
MAX_RETRIES              = 3