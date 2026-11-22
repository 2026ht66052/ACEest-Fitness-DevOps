"""Pure business logic for ACEest Fitness & Gym.

This module intentionally contains no Flask or database code so that it can be
unit tested in isolation.  Every rule that was embedded inside the original
Tkinter versions (calorie factors, BMI banding, program generation) lives here.
"""

from __future__ import annotations

import random
from datetime import datetime, timezone
from typing import Any

#: Training programs offered by the gym.  ``factor`` is the kcal/kg multiplier
#: carried over from the Tkinter versions of the application.
PROGRAMS: dict[str, dict[str, Any]] = {
    "Fat Loss (FL) - 3 day": {
        "factor": 22,
        "focus": "Conditioning",
        "desc": "3-day full-body fat loss circuit",
        "diet": "Egg whites + oats, grilled chicken + brown rice, fish curry + millet roti",
    },
    "Fat Loss (FL) - 5 day": {
        "factor": 24,
        "focus": "Conditioning",
        "desc": "5-day split, higher volume fat loss",
        "diet": "High protein, moderate carb, ~2000 kcal target",
    },
    "Muscle Gain (MG) - PPL": {
        "factor": 35,
        "focus": "Hypertrophy",
        "desc": "Push / Pull / Legs hypertrophy split",
        "diet": "Eggs + peanut butter oats, chicken biryani, mutton curry + rice",
    },
    "Beginner (BG)": {
        "factor": 26,
        "focus": "Full Body",
        "desc": "3-day simple beginner full-body plan",
        "diet": "Balanced meals: idli-sambar, rice-dal, chapati. Protein 120 g/day",
    },
}

EXERCISE_POOL: dict[str, list[str]] = {
    "Strength": [
        "Back Squat",
        "Deadlift",
        "Bench Press",
        "Overhead Press",
        "Pull-Up",
        "Barbell Row",
    ],
    "Hypertrophy": [
        "Leg Press",
        "Incline Dumbbell Press",
        "Lat Pulldown",
        "Lateral Raise",
        "Bicep Curl",
        "Tricep Extension",
    ],
    "Conditioning": [
        "Assault Bike",
        "Rowing",
        "Burpees",
        "Jump Rope",
        "Kettlebell Swings",
        "Box Jumps",
    ],
    "Full Body": [
        "Air Squat",
        "Ring Row",
        "Push-Up",
        "Lunge",
        "Plank",
        "Dumbbell Press",
    ],
}

EXPERIENCE_LEVELS: dict[str, dict[str, Any]] = {
    "beginner": {"sets": (2, 3), "reps": (8, 12), "days": 3},
    "intermediate": {"sets": (3, 4), "reps": (8, 15), "days": 4},
    "advanced": {"sets": (4, 5), "reps": (6, 15), "days": 5},
}

WEEK_DAYS = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday"]

WORKOUT_TYPES = ["Strength", "Hypertrophy", "Conditioning", "Mixed", "Mobility"]


class ValidationError(ValueError):
    """Raised when client supplied data fails validation."""

    def __init__(self, errors: list[str]):
        self.errors = errors
        super().__init__("; ".join(errors))


def program_names() -> list[str]:
    """Return the available program names in a stable order."""
    return list(PROGRAMS.keys())


def calorie_factor(program: str) -> int:
    """Return the kcal/kg factor for ``program``.

    Raises:
        ValidationError: if the program is unknown.
    """
    if program not in PROGRAMS:
        raise ValidationError([f"Unknown program: {program!r}"])
    return int(PROGRAMS[program]["factor"])


def calculate_calories(weight_kg: float, program: str) -> int:
    """Estimate a daily calorie target from body weight and program."""
    if weight_kg is None or float(weight_kg) <= 0:
        raise ValidationError(["Weight must be greater than zero"])
    return int(round(float(weight_kg) * calorie_factor(program)))


def calculate_bmi(height_cm: float, weight_kg: float) -> float:
    """Return BMI rounded to one decimal place."""
    if height_cm is None or float(height_cm) <= 0:
        raise ValidationError(["Height must be greater than zero"])
    if weight_kg is None or float(weight_kg) <= 0:
        raise ValidationError(["Weight must be greater than zero"])
    metres = float(height_cm) / 100.0
    return round(float(weight_kg) / (metres * metres), 1)


def bmi_category(bmi: float) -> str:
    """Map a BMI value onto a WHO category label."""
    if bmi < 18.5:
        return "Underweight"
    if bmi < 25:
        return "Normal"
    if bmi < 30:
        return "Overweight"
    return "Obese"


def bmi_risk_note(bmi: float) -> str:
    """Return a coaching note matching the BMI category."""
    notes = {
        "Underweight": "Potential nutrient deficiency; prioritise a calorie surplus.",
        "Normal": "Low risk if active; maintain strength and conditioning work.",
        "Overweight": "Moderate risk; focus on adherence and progressive activity.",
        "Obese": "Higher risk; prioritise fat loss, consistency and supervision.",
    }
    return notes[bmi_category(bmi)]


def _coerce_number(
    payload: dict[str, Any],
    field: str,
    cast,
    errors: list[str],
    minimum: float = 0.0,
    required: bool = False,
):
    """Coerce ``payload[field]`` with ``cast``, appending problems to ``errors``."""
    raw = payload.get(field)
    if raw in (None, ""):
        if required:
            errors.append(f"{field} is required")
        return None
    try:
        value = cast(raw)
    except (TypeError, ValueError):
        errors.append(f"{field} must be a number")
        return None
    if value < minimum:
        errors.append(f"{field} must be >= {minimum}")
        return None
    return value


def _validate_name_and_program(payload: dict[str, Any], errors: list[str]) -> tuple[str, str]:
    """Validate the two mandatory text fields."""
    name = str(payload.get("name") or "").strip()
    if not name:
        errors.append("Name is required")

    program = str(payload.get("program") or "").strip()
    if not program:
        errors.append("Program is required")
    elif program not in PROGRAMS:
        errors.append(f"Unknown program: {program!r}")

    return name, program


def validate_client(payload: dict[str, Any]) -> dict[str, Any]:
    """Validate and normalise a client payload.

    Returns a dictionary with coerced types ready for persistence.

    Raises:
        ValidationError: with the list of all problems found.
    """
    errors: list[str] = []
    name, program = _validate_name_and_program(payload, errors)

    age = _coerce_number(payload, "age", int, errors)
    height = _coerce_number(payload, "height", float, errors)
    weight = _coerce_number(payload, "weight", float, errors, required=True)
    target_weight = _coerce_number(payload, "target_weight", float, errors)
    target_adherence = _coerce_number(payload, "target_adherence", int, errors)

    if age is not None and age > 120:
        errors.append("age must be <= 120")
    if target_adherence is not None and target_adherence > 100:
        errors.append("target_adherence must be between 0 and 100")

    if errors:
        raise ValidationError(errors)

    calories = calculate_calories(weight, program) if weight else None

    return {
        "name": name,
        "age": age,
        "height": height,
        "weight": weight,
        "program": program,
        "calories": calories,
        "target_weight": target_weight,
        "target_adherence": target_adherence,
    }


def validate_adherence(value: Any) -> int:
    """Validate a weekly adherence percentage."""
    try:
        adherence = int(value)
    except (TypeError, ValueError):
        raise ValidationError(["adherence must be an integer"]) from None
    if not 0 <= adherence <= 100:
        raise ValidationError(["adherence must be between 0 and 100"])
    return adherence


def week_label(moment: datetime | None = None) -> str:
    """Return the ISO-ish week label used to bucket weekly progress rows."""
    moment = moment or datetime.now(timezone.utc)
    return moment.strftime("Week %U - %Y")


def generate_program(
    program: str,
    experience: str,
    seed: int | None = None,
) -> list[dict[str, Any]]:
    """Generate a weekly training plan.

    The generator is deterministic when ``seed`` is supplied, which makes the
    behaviour straightforward to assert in the test suite.
    """
    if program not in PROGRAMS:
        raise ValidationError([f"Unknown program: {program!r}"])
    level = str(experience or "").lower().strip()
    if level not in EXPERIENCE_LEVELS:
        raise ValidationError(
            ["experience must be one of: " + ", ".join(EXPERIENCE_LEVELS)]
        )

    config = EXPERIENCE_LEVELS[level]
    focus = PROGRAMS[program]["focus"]
    pool = EXERCISE_POOL[focus]
    rng = random.Random(seed)
    per_day = 3 if config["days"] < 4 else 4

    plan: list[dict[str, Any]] = []
    for day in WEEK_DAYS[: config["days"]]:
        for exercise in rng.sample(pool, k=per_day):
            plan.append(
                {
                    "day": day,
                    "exercise": exercise,
                    "sets": rng.randint(*config["sets"]),
                    "reps": rng.randint(*config["reps"]),
                    "focus": focus,
                }
            )
    return plan


def summarise_progress(rows: list[dict[str, Any]]) -> dict[str, Any]:
    """Aggregate weekly adherence rows into summary statistics."""
    values = [int(row["adherence"]) for row in rows]
    if not values:
        return {
            "weeks_logged": 0,
            "average_adherence": 0.0,
            "best": 0,
            "worst": 0,
            "trend": "no-data",
        }
    average = round(sum(values) / len(values), 1)
    trend = "flat"
    if len(values) >= 2:
        if values[-1] > values[0]:
            trend = "improving"
        elif values[-1] < values[0]:
            trend = "declining"
    return {
        "weeks_logged": len(values),
        "average_adherence": average,
        "best": max(values),
        "worst": min(values),
        "trend": trend,
    }
