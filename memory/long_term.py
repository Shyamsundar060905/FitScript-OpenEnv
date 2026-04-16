"""
Long-term memory — stores and retrieves user profiles as JSON files.
Each user gets their own file: data/users/{user_id}.json
"""

import json
from pathlib import Path
from datetime import datetime
from typing import Optional
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(__file__)))
from config import USERS_DIR
from schemas import UserProfile


def save_profile(profile: UserProfile):
    """Save or update a user profile."""
    USERS_DIR.mkdir(parents=True, exist_ok=True)
    profile.updated_at = datetime.now().isoformat()
    path = USERS_DIR / f"{profile.user_id}.json"
    path.write_text(profile.model_dump_json(indent=2))
    print(f"  [Profile] ✓ Saved profile for {profile.name} ({profile.user_id})")


def load_profile(user_id: str) -> Optional[UserProfile]:
    """Load a user profile. Returns None if not found."""
    path = USERS_DIR / f"{user_id}.json"
    if not path.exists():
        return None
    data = json.loads(path.read_text())
    return UserProfile(**data)


def list_users() -> list:
    """Return list of all user IDs."""
    USERS_DIR.mkdir(parents=True, exist_ok=True)
    return [f.stem for f in USERS_DIR.glob("*.json")]


def create_sample_user() -> UserProfile:
    """Create a sample user for testing."""
    profile = UserProfile(
        user_id="user_001",
        name="Arjun Sharma",
        age=22,
        weight_kg=78.0,
        height_cm=175.0,
        goal="muscle_gain",
        fitness_level="intermediate",
        dietary_restrictions=["vegetarian"],
        available_equipment=["dumbbells", "pull_up_bar", "resistance_bands"],
        sessions_per_week=4,
        tdee_estimate=2600.0
    )
    save_profile(profile)
    return profile


if __name__ == "__main__":
    profile = create_sample_user()
    print(f"  Created: {profile.to_summary()}")

    loaded = load_profile("user_001")
    print(f"  Loaded BMI: {loaded.bmi()}")
    print("  [Profile] ✓ Long-term memory test passed")
