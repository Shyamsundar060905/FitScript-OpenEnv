# FitAgent AI

A multi-agent framework for personalized fitness and nutrition prescription
with adaptive memory and progress reasoning.

## Setup

```bash
pip install -r requirements.txt
cp .env.example .env  # add your API keys
streamlit run app.py
```

## Architecture

- **Orchestrator** — coordinates agents, resolves conflicts
- **Fitness Agent** — workout programming with RAG
- **Nutrition Agent** — meal planning with Indian food database  
- **Progress Agent** — plateau detection and adaptation
- **Profile Agent** — user model management