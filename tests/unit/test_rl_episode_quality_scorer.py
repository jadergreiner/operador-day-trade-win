import pytest

from src.application.rl_episode_quality_scorer import (
    BatchQualitySummary,
    EpisodeQualityInput,
    RLEpisodeQualityScorer,
)


def test_score_episode_nominal_and_serialization():
    scorer = RLEpisodeQualityScorer()
    episode = EpisodeQualityInput(
        episode_id="ep-001",
        requested_qty=10,
        filled_qty=10,
        slippage_points=0.5,
        latency_ms=120,
        confidence=0.8,
        status="FILLED",
        outcome="WIN",
        pnl_points=28.0,
    )

    score = scorer.score_episode(episode)

    assert score.episode_id == "ep-001"
    assert score.fill_rate == pytest.approx(1.0)
    assert score.quality_score > 80.0
    assert score.component_scores["fill_rate"] == pytest.approx(100.0)
    assert score.to_dict()["timestamp"] == episode.timestamp.isoformat()


def test_score_batch_aggregates_batch_metrics_and_failures():
    scorer = RLEpisodeQualityScorer()
    batch = [
        {
            "episode_id": "ep-good",
            "requested_qty": 10,
            "filled_qty": 10,
            "slippage_points": 0.2,
            "latency_ms": 80,
            "confidence": 0.9,
            "status": "FILLED",
            "outcome": "WIN",
            "pnl_points": 15.0,
        },
        {
            "episode_id": "ep-bad",
            "requested_qty": 10,
            "filled_qty": 6,
            "slippage_points": 5.5,
            "latency_ms": 700,
            "confidence": 0.3,
            "status": "REJECTED",
            "failure_reason": "timeout",
            "outcome": "LOSS",
            "pnl_points": -12.0,
        },
    ]

    summary = scorer.score_batch(batch)

    assert isinstance(summary, BatchQualitySummary)
    assert summary.batch_size == 2
    assert summary.scored_episodes == 2
    assert summary.average_score < 80.0
    assert summary.win_rate == pytest.approx(0.5)
    assert summary.loss_rate == pytest.approx(0.5)
    assert summary.failure_rate == pytest.approx(0.5)
    assert summary.average_fill_rate == pytest.approx(0.8)
    assert summary.top_failure_reasons == {"timeout": 1}
    assert len(summary.episode_scores) == 2
    assert summary.to_dict()["episode_scores"][0]["episode_id"] == "ep-good"


def test_score_batch_empty_returns_zero_summary():
    scorer = RLEpisodeQualityScorer()

    summary = scorer.score_batch([])

    assert summary.batch_size == 0
    assert summary.average_score == 0.0
    assert summary.quality_index == 0.0
    assert summary.top_failure_reasons == {}


def test_score_episode_rejects_invalid_values():
    scorer = RLEpisodeQualityScorer()

    with pytest.raises(ValueError):
        scorer.score_episode(
            {
                "episode_id": "bad-1",
                "requested_qty": 10,
                "filled_qty": 10,
                "latency_ms": -1,
            }
        )

    with pytest.raises(ValueError):
        scorer.score_episode(
            {
                "episode_id": "bad-2",
                "requested_qty": -10,
                "filled_qty": 10,
                "latency_ms": 1,
            }
        )


def test_score_episode_caps_outliers_without_breaking():
    scorer = RLEpisodeQualityScorer()
    score = scorer.score_episode(
        {
            "episode_id": "ep-outlier",
            "requested_qty": 10,
            "filled_qty": 10,
            "slippage_points": 120.0,
            "latency_ms": 5000.0,
            "confidence": 0.1,
            "status": "ERROR",
            "failure_reason": "liquidity timeout",
            "outcome": "LOSS",
        }
    )

    assert 0.0 <= score.quality_score <= 100.0
    assert "slippage_outlier" in score.flags
    assert "latency_outlier" in score.flags
    assert score.quality_score < 40.0
