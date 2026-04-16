"""
Profile Agent — responsible for:
1. Onboarding new users (collecting their info via LLM conversation)
2. Loading and updating existing user profiles
3. Providing a clean user summary to other agents
"""

import json
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(__file__)))

from llm.router import llm_call, parse_json_response
from memory.long_term import save_profile, load_profile, create_sample_user
from schemas import UserProfile, AgentMessage


SYSTEM_PROMPT = """You are the Profile Agent in a fitness AI system.
Your job is to extract structured user information from a conversation or description.
You always respond with valid JSON matching the UserProfile schema exactly.
Be practical and make reasonable assumptions if some details are missing.
"""


def create_profile_from_description(description: str) -> UserProfile:
    prompt = f"""Extract a complete user profile from this description:

"{description}"

Return a JSON object with EXACTLY these fields:
{{
  "user_id": "user_<3 random digits>",
  "name": "extract or use 'User'",
  "age": <integer>,
  "weight_kg": <float>,
  "height_cm": <float>,
  "goal": "<one of: weight_loss, muscle_gain, endurance, maintenance>",
  "fitness_level": "<one of: beginner, intermediate, advanced>",
  "dietary_restrictions": ["list", "of", "restrictions"],
  "available_equipment": ["list", "of", "equipment"],
  "sessions_per_week": <integer 3-5>,
  "tdee_estimate": <a single computed number like 2690.0, NOT a formula>
}}

For TDEE estimation use: 
  weight_loss -> TDEE = weight_kg * 22 * activity_factor - 300
  muscle_gain -> TDEE = weight_kg * 22 * activity_factor + 300
  maintenance/endurance -> TDEE = weight_kg * 22 * activity_factor
  activity_factor: beginner=1.4, intermediate=1.6, advanced=1.8

Return ONLY the JSON object, nothing else."""

    response = llm_call(SYSTEM_PROMPT, prompt, json_mode=True)
    data = parse_json_response(response)
    data.setdefault("dietary_restrictions", [])
    data.setdefault("available_equipment", ["bodyweight"])
    data.setdefault("sessions_per_week", 3)
    profile = UserProfile(**data)
    save_profile(profile)
    return profile


def update_profile_field(user_id: str, field: str, value) -> UserProfile:
    profile = load_profile(user_id)
    if not profile:
        raise ValueError(f"No profile found for user_id: {user_id}")
    profile_dict = profile.model_dump()
    profile_dict[field] = value
    updated = UserProfile(**profile_dict)
    save_profile(updated)
    return updated


def get_profile_summary(user_id: str) -> str:
    profile = load_profile(user_id)
    if not profile:
        return f"No profile found for user {user_id}"
    return profile.to_summary()


def run(user_id: str, task: str = "load") -> AgentMessage:
    if task == "create":
        profile = create_sample_user()
    else:
        profile = load_profile(user_id)
        if not profile:
            profile = create_sample_user()

    return AgentMessage(
        from_agent="profile",
        to_agent="orchestrator",
        message_type="response",
        payload=profile.model_dump(),
        confidence=1.0,
        reasoning="Profile loaded successfully"
    )


if __name__ == "__main__":
    print("\n── Test 1: Create profile from natural language ──")
    profile = create_profile_from_description(
        "My name is Rahul, I'm 23 years old, 68kg, 170cm tall. "
        "I want to build muscle. I work out at home with dumbbells. "
        "I'm vegetarian and have been training for about a year."
    )
    print(f"  Created: {profile.to_summary()}")
    print(f"  BMI: {profile.bmi()}")
    print(f"  TDEE: {profile.tdee_estimate} kcal")

    print("\n── Test 2: Load existing profile ──")
    loaded = load_profile(profile.user_id)
    print(f"  Loaded: {loaded.name}, goal: {loaded.goal}")

    print("\n── Test 3: Agent message output ──")
    msg = run(profile.user_id)
    print(f"  From: {msg.from_agent}, confidence: {msg.confidence}")
    print("\n  [Profile Agent] ✓ All tests passed")