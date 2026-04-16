"""
Data schemas for the fitness agent framework.
All data exchanged between agents uses these models.
"""

from pydantic import BaseModel, Field
from typing import Optional, List, Literal
from datetime import datetime, date


# ── Core user model ───────────────────────────────────────────────────────────

class UserProfile(BaseModel):
    user_id: str
    name: str
    age: int
    weight_kg: float
    height_cm: float
    goal: Literal["weight_loss", "muscle_gain", "endurance", "maintenance"]
    fitness_level: Literal["beginner", "intermediate", "advanced"]
    dietary_restrictions: List[str] = []           # e.g. ["vegetarian", "gluten_free"]
    available_equipment: List[str] = ["bodyweight"] # e.g. ["dumbbells", "barbell"]
    sessions_per_week: int = 3
    tdee_estimate: float = 2000.0                  # total daily energy expenditure
    created_at: str = Field(default_factory=lambda: datetime.now().isoformat())
    updated_at: str = Field(default_factory=lambda: datetime.now().isoformat())

    def bmi(self) -> float:
        return round(self.weight_kg / ((self.height_cm / 100) ** 2), 1)

    def to_summary(self) -> str:
        """Plain text summary for LLM prompts."""
        return (
            f"Name: {self.name}, Age: {self.age}, Weight: {self.weight_kg}kg, "
            f"Height: {self.height_cm}cm, BMI: {self.bmi()}, "
            f"Goal: {self.goal}, Fitness level: {self.fitness_level}, "
            f"Equipment: {', '.join(self.available_equipment)}, "
            f"Dietary restrictions: {', '.join(self.dietary_restrictions) or 'none'}, "
            f"Sessions/week: {self.sessions_per_week}, "
            f"Estimated TDEE: {self.tdee_estimate} kcal/day"
        )


# ── Progress tracking ─────────────────────────────────────────────────────────

class ProgressLog(BaseModel):
    user_id: str
    date: str                           # ISO date string YYYY-MM-DD
    weight_kg: Optional[float] = None
    workout_completed: bool = False
    workout_rating: Optional[int] = None  # 1-5, subjective difficulty
    calories_eaten: Optional[float] = None
    notes: str = ""


# ── Inter-agent message protocol ──────────────────────────────────────────────

class AgentMessage(BaseModel):
    from_agent: Literal["fitness", "nutrition", "progress", "profile", "orchestrator"]
    to_agent: Literal["fitness", "nutrition", "progress", "profile", "orchestrator"]
    message_type: Literal["plan", "conflict", "signal", "query", "response"]
    payload: dict                       # the actual content
    confidence: float = 1.0            # 0.0 - 1.0
    conflicts_with: List[str] = []     # list of agent names this conflicts with
    reasoning: str = ""                # why this agent produced this output


# ── Exercise + workout plan ───────────────────────────────────────────────────

class Exercise(BaseModel):
    name: str
    sets: Optional[int] = None
    reps: Optional[str] = None          # "8-12" or "to failure"
    duration_minutes: Optional[int] = None
    rest_seconds: int = 60
    notes: str = ""


class WorkoutDay(BaseModel):
    day_name: str                       # e.g. "Monday", "Day 1"
    focus: str                          # e.g. "Push", "Lower body", "Cardio"
    exercises: List[Exercise]
    estimated_duration_minutes: int = 45


class WorkoutPlan(BaseModel):
    user_id: str
    week_number: int = 1
    days: List[WorkoutDay]
    weekly_volume_sets: int = 0
    notes: str = ""
    generated_at: str = Field(default_factory=lambda: datetime.now().isoformat())


# ── Nutrition plan ────────────────────────────────────────────────────────────

class Meal(BaseModel):
    meal_name: str                      # "Breakfast", "Lunch", etc.
    foods: List[str]
    calories: float
    protein_g: float
    carbs_g: float
    fats_g: float


class DailyNutritionPlan(BaseModel):
    day_name: str
    meals: List[Meal]
    total_calories: float
    total_protein_g: float
    total_carbs_g: float
    total_fats_g: float


class NutritionPlan(BaseModel):
    user_id: str
    week_number: int = 1
    daily_plans: List[DailyNutritionPlan]
    target_calories: float
    target_protein_g: float
    notes: str = ""
    generated_at: str = Field(default_factory=lambda: datetime.now().isoformat())


# ── Adaptation signal ─────────────────────────────────────────────────────────

class AdaptationSignal(BaseModel):
    user_id: str
    signal_type: Literal["plateau", "overtraining", "goal_change", "progress", "schedule_change"]
    severity: Literal["low", "medium", "high"]
    description: str
    recommended_action: str
    data_points: dict = {}              # the numbers that triggered this signal


# ── Full prescription output ──────────────────────────────────────────────────

class WeeklyPrescription(BaseModel):
    user_id: str
    week_number: int
    workout_plan: WorkoutPlan
    nutrition_plan: NutritionPlan
    adaptation_signals: List[AdaptationSignal] = []
    orchestrator_notes: str = ""
    conflicts_resolved: List[str] = []
    knowledge_used: List[dict] = []        # RAG chunks used by agents
    agent_log: List[dict] = []             # timeline of agent decisions
    generated_at: str = Field(default_factory=lambda: datetime.now().isoformat())