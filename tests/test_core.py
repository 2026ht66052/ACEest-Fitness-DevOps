"""Unit tests for the pure business logic in ``app.core``."""

from __future__ import annotations

from datetime import datetime

import pytest

from app import core


# --------------------------------------------------------------------------- #
# Programs and calories
# --------------------------------------------------------------------------- #
def test_program_catalogue_is_not_empty():
    assert core.program_names()
    for name, meta in core.PROGRAMS.items():
        assert meta["factor"] > 0, name
        assert meta["focus"] in core.EXERCISE_POOL, name


@pytest.mark.parametrize(
    "program,expected_factor",
    [
        ("Fat Loss (FL) - 3 day", 22),
        ("Fat Loss (FL) - 5 day", 24),
        ("Muscle Gain (MG) - PPL", 35),
        ("Beginner (BG)", 26),
    ],
)
def test_calorie_factors_match_specification(program, expected_factor):
    assert core.calorie_factor(program) == expected_factor


def test_calorie_factor_rejects_unknown_program():
    with pytest.raises(core.ValidationError):
        core.calorie_factor("Powerlifting")


@pytest.mark.parametrize(
    "weight,program,expected",
    [
        (80, "Muscle Gain (MG) - PPL", 2800),
        (70, "Fat Loss (FL) - 3 day", 1540),
        (60.5, "Beginner (BG)", 1573),
    ],
)
def test_calculate_calories(weight, program, expected):
    assert core.calculate_calories(weight, program) == expected


@pytest.mark.parametrize("weight", [0, -1, None])
def test_calculate_calories_rejects_bad_weight(weight):
    with pytest.raises(core.ValidationError):
        core.calculate_calories(weight, "Beginner (BG)")


# --------------------------------------------------------------------------- #
# BMI
# --------------------------------------------------------------------------- #
@pytest.mark.parametrize(
    "height,weight,expected",
    [
        (175, 80, 26.1),
        (180, 60, 18.5),
        (160, 95, 37.1),
    ],
)
def test_calculate_bmi(height, weight, expected):
    assert core.calculate_bmi(height, weight) == expected


@pytest.mark.parametrize(
    "bmi,category",
    [(17.0, "Underweight"), (22.0, "Normal"), (27.5, "Overweight"), (33.0, "Obese")],
)
def test_bmi_category_boundaries(bmi, category):
    assert core.bmi_category(bmi) == category


def test_bmi_category_exact_boundaries():
    assert core.bmi_category(18.5) == "Normal"
    assert core.bmi_category(25.0) == "Overweight"
    assert core.bmi_category(30.0) == "Obese"


def test_bmi_risk_note_present_for_every_category():
    for bmi in (17.0, 22.0, 27.0, 35.0):
        assert core.bmi_risk_note(bmi)


@pytest.mark.parametrize("height,weight", [(0, 70), (-5, 70), (175, 0), (175, -2)])
def test_calculate_bmi_rejects_non_positive_values(height, weight):
    with pytest.raises(core.ValidationError):
        core.calculate_bmi(height, weight)


# --------------------------------------------------------------------------- #
# Client validation
# --------------------------------------------------------------------------- #
def test_validate_client_normalises_and_derives_calories():
    data = core.validate_client(
        {
            "name": "  Priya  ",
            "age": "31",
            "height": "165",
            "weight": "62.5",
            "program": "Fat Loss (FL) - 3 day",
        }
    )
    assert data["name"] == "Priya"
    assert data["age"] == 31
    assert data["weight"] == pytest.approx(62.5)
    assert data["calories"] == 1375
    assert data["target_weight"] is None


def test_validate_client_collects_all_errors():
    with pytest.raises(core.ValidationError) as excinfo:
        core.validate_client({"name": "", "program": "Nope", "weight": "abc"})
    errors = excinfo.value.errors
    assert any("Name is required" in e for e in errors)
    assert any("Unknown program" in e for e in errors)
    assert any("weight" in e for e in errors)


def test_validate_client_requires_weight():
    with pytest.raises(core.ValidationError):
        core.validate_client({"name": "X", "program": "Beginner (BG)"})


def test_validate_client_rejects_impossible_age():
    with pytest.raises(core.ValidationError):
        core.validate_client(
            {"name": "X", "program": "Beginner (BG)", "weight": 70, "age": 500}
        )


def test_validate_client_rejects_adherence_above_100():
    with pytest.raises(core.ValidationError):
        core.validate_client(
            {
                "name": "X",
                "program": "Beginner (BG)",
                "weight": 70,
                "target_adherence": 150,
            }
        )


@pytest.mark.parametrize("value,expected", [(0, 0), ("55", 55), (100, 100)])
def test_validate_adherence_accepts_valid_range(value, expected):
    assert core.validate_adherence(value) == expected


@pytest.mark.parametrize("value", [-1, 101, "high", None])
def test_validate_adherence_rejects_invalid(value):
    with pytest.raises(core.ValidationError):
        core.validate_adherence(value)


# --------------------------------------------------------------------------- #
# Program generation
# --------------------------------------------------------------------------- #
def test_generate_program_is_deterministic_with_seed():
    first = core.generate_program("Muscle Gain (MG) - PPL", "intermediate", seed=7)
    second = core.generate_program("Muscle Gain (MG) - PPL", "intermediate", seed=7)
    assert first == second


@pytest.mark.parametrize(
    "experience,days,per_day",
    [("beginner", 3, 3), ("intermediate", 4, 4), ("advanced", 5, 4)],
)
def test_generate_program_shape_matches_experience(experience, days, per_day):
    plan = core.generate_program("Beginner (BG)", experience, seed=1)
    assert len({row["day"] for row in plan}) == days
    assert len(plan) == days * per_day


def test_generate_program_respects_program_focus():
    plan = core.generate_program("Fat Loss (FL) - 3 day", "beginner", seed=3)
    assert all(row["focus"] == "Conditioning" for row in plan)
    assert all(row["exercise"] in core.EXERCISE_POOL["Conditioning"] for row in plan)


def test_generate_program_sets_and_reps_within_bounds():
    plan = core.generate_program("Muscle Gain (MG) - PPL", "advanced", seed=11)
    low_sets, high_sets = core.EXPERIENCE_LEVELS["advanced"]["sets"]
    low_reps, high_reps = core.EXPERIENCE_LEVELS["advanced"]["reps"]
    for row in plan:
        assert low_sets <= row["sets"] <= high_sets
        assert low_reps <= row["reps"] <= high_reps


def test_generate_program_rejects_bad_experience():
    with pytest.raises(core.ValidationError):
        core.generate_program("Beginner (BG)", "olympian")


def test_generate_program_rejects_bad_program():
    with pytest.raises(core.ValidationError):
        core.generate_program("CrossFit Open", "beginner")


# --------------------------------------------------------------------------- #
# Progress aggregation and week labels
# --------------------------------------------------------------------------- #
def test_summarise_progress_with_no_rows():
    summary = core.summarise_progress([])
    assert summary == {
        "weeks_logged": 0,
        "average_adherence": 0.0,
        "best": 0,
        "worst": 0,
        "trend": "no-data",
    }


def test_summarise_progress_detects_improving_trend():
    rows = [{"adherence": 50}, {"adherence": 70}, {"adherence": 90}]
    summary = core.summarise_progress(rows)
    assert summary["weeks_logged"] == 3
    assert summary["average_adherence"] == 70.0
    assert summary["best"] == 90
    assert summary["worst"] == 50
    assert summary["trend"] == "improving"


def test_summarise_progress_detects_declining_and_flat_trends():
    assert core.summarise_progress([{"adherence": 90}, {"adherence": 40}])["trend"] == "declining"
    assert core.summarise_progress([{"adherence": 60}, {"adherence": 60}])["trend"] == "flat"


def test_week_label_format():
    label = core.week_label(datetime(2026, 1, 15))
    assert label.startswith("Week ")
    assert label.endswith("2026")
