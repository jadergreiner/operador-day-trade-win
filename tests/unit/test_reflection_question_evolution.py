"""Testes unitarios para reflection_question_evolution."""

from __future__ import annotations

from src.application.reflection_question_evolution import (
    ReflectionLevel,
    ReflectionQuestionEvolution,
)


def test_returns_empty_when_limit_is_zero() -> None:
    evolution = ReflectionQuestionEvolution()

    questions = evolution.evolve_questions({}, [], limit=0)

    assert questions == []


def test_generates_default_categories_in_order() -> None:
    evolution = ReflectionQuestionEvolution()

    questions = evolution.evolve_questions({}, [], limit=3)

    assert len(questions) == 3
    assert questions[0].category == "execution"
    assert questions[1].category == "execution"
    assert questions[2].category == "execution"


def test_high_risk_prioritizes_risk_category() -> None:
    evolution = ReflectionQuestionEvolution()

    questions = evolution.evolve_questions({"high_risk": True}, [], limit=1)

    assert len(questions) == 1
    assert questions[0].category == "risk"


def test_emotional_instability_prioritizes_mindset() -> None:
    evolution = ReflectionQuestionEvolution()

    questions = evolution.evolve_questions(
        {"emotional_instability": True},
        [],
        limit=1,
    )

    assert len(questions) == 1
    assert questions[0].category == "mindset"


def test_level_is_basic_for_short_history() -> None:
    evolution = ReflectionQuestionEvolution()

    questions = evolution.evolve_questions({}, [{}] * 3, limit=1)

    assert questions[0].level == ReflectionLevel.BASICO
    assert "evidencias objetivas" not in questions[0].prompt.lower()


def test_level_is_intermediate_for_mid_history() -> None:
    evolution = ReflectionQuestionEvolution()

    questions = evolution.evolve_questions({}, [{}] * 10, limit=1)

    assert questions[0].level == ReflectionLevel.INTERMEDIARIO
    assert "evidencias objetivas" in questions[0].prompt.lower()
    assert "experimento pratico" not in questions[0].prompt.lower()


def test_level_is_advanced_for_long_history() -> None:
    evolution = ReflectionQuestionEvolution()

    questions = evolution.evolve_questions({}, [{}] * 25, limit=1)

    assert questions[0].level == ReflectionLevel.AVANCADO
    assert "experimento pratico" in questions[0].prompt.lower()


def test_avoids_used_prompts() -> None:
    evolution = ReflectionQuestionEvolution()
    initial = evolution.evolve_questions({}, [], limit=1)
    blocked_prompt = initial[0].prompt

    questions = evolution.evolve_questions({}, [], used_prompts=[blocked_prompt], limit=2)

    assert len(questions) == 2
    assert all(question.prompt != blocked_prompt for question in questions)


def test_question_to_dict_is_serializable_shape() -> None:
    evolution = ReflectionQuestionEvolution()
    question = evolution.evolve_questions({}, [], limit=1)[0]

    payload = question.to_dict()

    assert payload["prompt"]
    assert payload["level"] == "basico"
    assert payload["category"] in {"execution", "risk", "mindset"}
    assert "created_at" in payload
