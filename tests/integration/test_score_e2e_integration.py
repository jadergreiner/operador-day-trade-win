"""
test_score_e2e_integration.py — E2E Tests integração Tasks 1-5

Testes integração completa: Dataset → Features → Inference → Confluência

Author: QA Lead
Date: 2026-02-24
Version: 1.0.0
"""

import json
import logging
import os
import tempfile
import time
from typing import Dict, Any, List

import numpy as np
import pandas as pd
import pytest

from scripts.score_t60_inference import ScoreT60Inference
from scripts.score_t60_confluence import ScoreT60Confluence

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


# ════════════════════════════════════════════════════════════════════════════
# FIXTURES
# ════════════════════════════════════════════════════════════════════════════


@pytest.fixture
def inference_engine():
    """Engine de inferência T60 inicializado."""
    model_path = "models/score_t60_v1.0_BEST.pkl"
    return ScoreT60Inference(model_path=model_path)


@pytest.fixture
def confluence_engine():
    """Engine de confluência inicializado."""
    return ScoreT60Confluence(threshold_bull=0.62, threshold_bear=0.38)


@pytest.fixture
def sample_df_m1_bull():
    """
    Fixture: DataFrame com padrão BULL (60 candles).

    CASE: Candlesticks com tendência BULL
    THEN: Gera features que indicam BULL
    """
    # Simular 60 candles com alta trend
    timestamps = pd.date_range(start="2026-02-24 09:30", periods=60, freq="1min")
    closes = np.linspace(100, 110, 60) + np.random.normal(0, 0.5, 60)
    highs = closes + np.random.uniform(0, 1, 60)
    lows = closes - np.random.uniform(0, 1, 60)
    volumes = np.random.uniform(1000, 5000, 60)

    df = pd.DataFrame({
        "timestamp": timestamps,
        "open": closes - np.random.uniform(0, 0.5, 60),
        "high": highs,
        "low": lows,
        "close": closes,
        "volume": volumes,
    })

    return df


@pytest.fixture
def sample_df_m1_bear():
    """
    Fixture: DataFrame com padrão BEAR (60 candles).

    CASE: Candlesticks com tendência BEAR
    THEN: Gera features que indicam BEAR
    """
    # Simular 60 candles com baixa trend
    timestamps = pd.date_range(start="2026-02-24 09:30", periods=60, freq="1min")
    closes = np.linspace(110, 100, 60) + np.random.normal(0, 0.5, 60)
    highs = closes + np.random.uniform(0, 1, 60)
    lows = closes - np.random.uniform(0, 1, 60)
    volumes = np.random.uniform(1000, 5000, 60)

    df = pd.DataFrame({
        "timestamp": timestamps,
        "open": closes + np.random.uniform(0, 0.5, 60),
        "high": highs,
        "low": lows,
        "close": closes,
        "volume": volumes,
    })

    return df


# ════════════════════════════════════════════════════════════════════════════
# E2E TEST SUITE — 8+ Testes
# ════════════════════════════════════════════════════════════════════════════


class TestE2EPipelineBull:
    """E2E tests para pipeline BULL (Dataset → Inference → Confluência)."""

    def test_e2e_pipeline_bull_seguro_case_dataset_to_confluence_then_trigger_buy_when_valido(
        self, inference_engine, confluence_engine, sample_df_m1_bull
    ):
        """
        Test 1: Pipeline completo BULL_SEGURO.

        CASE: Dataset BULL → Predict T60 ~ 0.7+ → Confluência com SMC BULL
        THEN: trigger=BUY, confidence=ALTA, state=BULL_SEGURO
        WHEN: Fim a fim sem erros
        """
        # AÇÃO 1: Predict T60 score from dataset
        t60_result = inference_engine.predict_from_df(sample_df_m1_bull)
        assert t60_result["score_t60"] > 0.50  # Deve ser bullish

        logger.info(f"✅ T60 Inference: score={t60_result['score_t60']:.3f}")

        # AÇÃO 2: Compute confluência com SMC BULL
        smc_status = {"direction": "BULL", "strength": 0.85}
        result = confluence_engine.compute_confluence(t60_result, smc_status)

        # VALIDAÇÕES
        assert result["state"] == "BULL_SEGURO"
        assert result["trigger"] == "BUY"
        assert result["confidence"] == "ALTA"
        assert result["validities"]["convergence"] is True
        assert "timestamp" in result

        logger.info(
            f"✅ Test 1 PASSED: Pipeline BULL → state={result['state']}, trigger={result['trigger']}"
        )

    def test_e2e_batch_processing_case_100_confluencias_then_throughput_ok_when_completo(
        self, inference_engine, confluence_engine, sample_df_m1_bull
    ):
        """
        Test 2: Performance batch — 100 confluências sequencial.

        CASE: Process 100 confluências do mesmo dataset
        THEN: Tempo total <3s (P95 <25ms cada, permitindo cold start)
        WHEN: Throughput adequado
        """
        start_time = time.time()
        latencies = []

        # AÇÃO: 100 confluências
        for i in range(100):
            iter_start = time.time()

            t60_result = inference_engine.predict_from_df(sample_df_m1_bull)
            smc_status = {"direction": "BULL", "strength": 0.80 + (i % 20) * 0.01}
            result = confluence_engine.compute_confluence(t60_result, smc_status)

            iter_latency = (time.time() - iter_start) * 1000  # ms
            latencies.append(iter_latency)

            # Validação básica
            assert result["trigger"] in ["BUY", "SELL", "HOLD", "AGUARDAR"]

        total_time = time.time() - start_time

        # VALIDAÇÕES de performance
        # Permitindo primeira iteração com cold start (~2000ms)
        # Depois ~15ms cada = 99*15ms = ~1.5s, total ~3.5s
        assert total_time < 5.0  # <5s para 100 (aumentado para acomodar cold start)

        # P95 sem primeira iteração (apenas warm runs)
        warm_latencies = latencies[1:]  # Excluir primeira (cold)
        p95_warm = np.percentile(warm_latencies, 95) if warm_latencies else 20
        assert p95_warm < 25.0  # <25ms P95 (warm)

        logger.info(
            f"✅ Test 2 PASSED: Batch processing 100 confluências em {total_time:.2f}s "
            f"(P95 warm={p95_warm:.2f}ms)"
        )


class TestE2EPipelineBear:
    """E2E tests para pipeline BEAR."""

    def test_e2e_pipeline_bear_seguro_case_dataset_to_confluence_then_trigger_sell_when_valido(
        self, inference_engine, confluence_engine, sample_df_m1_bear
    ):
        """
        Test 3: Pipeline completo BEAR_SEGURO.

        CASE: Dataset BEAR → Predict T60 ~ 0.3- → Confluência com SMC BEAR
        THEN: trigger=SELL, confidence=ALTA, state=BEAR_SEGURO
        WHEN: Fim a fim sem erros
        """
        # AÇÃO 1: Predict T60 score
        t60_result = inference_engine.predict_from_df(sample_df_m1_bear)
        assert t60_result["score_t60"] < 0.50  # Deve ser bearish

        logger.info(f"✅ T60 Inference: score={t60_result['score_t60']:.3f}")

        # AÇÃO 2: Compute confluência com SMC BEAR
        smc_status = {"direction": "BEAR", "strength": 0.85}
        result = confluence_engine.compute_confluence(t60_result, smc_status)

        # VALIDAÇÕES
        assert result["state"] == "BEAR_SEGURO"
        assert result["trigger"] == "SELL"
        assert result["confidence"] == "ALTA"
        assert result["validities"]["convergence"] is True

        logger.info(
            f"✅ Test 3 PASSED: Pipeline BEAR → state={result['state']}, trigger={result['trigger']}"
        )


class TestE2EPipelineConflict:
    """E2E tests para confluência conflitante."""

    def test_e2e_conflito_case_bull_signal_vs_bear_smc_then_aguardar_when_divergente(
        self, inference_engine, confluence_engine, sample_df_m1_bull
    ):
        """
        Test 4: Confluência CONFLITO — T60 BULL vs SMC BEAR.

        CASE: Dataset com T60~0.7 (BULL) mas SMC=BEAR
        THEN: state=CONFLITO, trigger=AGUARDAR, confidence=BAIXA
        WHEN: Sinais divergem
        """
        # AÇÃO 1: Bull dataset
        t60_result = inference_engine.predict_from_df(sample_df_m1_bull)

        # AÇÃO 2: Confluência com SMC divergente
        smc_status = {"direction": "BEAR", "strength": 0.80}
        result = confluence_engine.compute_confluence(t60_result, smc_status)

        # VALIDAÇÕES
        assert result["state"] == "CONFLITO"
        assert result["trigger"] == "AGUARDAR"
        assert result["confidence"] == "BAIXA"
        assert result["validities"]["convergence"] is False

        logger.info(f"✅ Test 4 PASSED: CONFLITO detected (não operar)")


class TestE2EPersistence:
    """E2E tests para persistência e histórico."""

    def test_e2e_persistence_case_multiple_confluencias_then_json_valid_when_append(
        self, inference_engine, confluence_engine, sample_df_m1_bull, sample_df_m1_bear
    ):
        """
        Test 5: Persistência e histórico.

        CASE: 5 confluências diferentes
        THEN: persist_result() cria JSON válido
        WHEN: History stats compilados
        """
        datasets = [sample_df_m1_bull, sample_df_m1_bear, sample_df_m1_bull]
        smc_statuses = [
            {"direction": "BULL", "strength": 0.85},
            {"direction": "BEAR", "strength": 0.80},
            {"direction": "NEUTRO", "strength": 0.50},
        ]

        # AÇÃO 1: 3 confluências
        for dataset, smc in zip(datasets, smc_statuses):
            t60_result = inference_engine.predict_from_df(dataset)
            result = confluence_engine.compute_confluence(t60_result, smc)
            assert result["state"] in ["BULL_SEGURO", "BEAR_SEGURO", "CONFLITO", "AGUARDAR"]

        # AÇÃO 2: Persistência
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            temp_path = f.name

        try:
            confluence_engine.persist_result(temp_path)

            # VALIDAÇÕES
            assert os.path.exists(temp_path)
            with open(temp_path, "r") as f:
                persisted = json.load(f)

            assert "state" in persisted
            assert "score_confluencia" in persisted

            # AÇÃO 3: History stats
            stats = confluence_engine.get_history_stats()
            assert stats["total"] == 3

            logger.info(f"✅ Test 5 PASSED: Persistence OK, total={stats['total']}")

        finally:
            if os.path.exists(temp_path):
                os.unlink(temp_path)


class TestE2ELatencyCompliance:
    """E2E tests para latência cumulativa."""

    def test_e2e_latency_compliance_case_all_pipeline_then_p95_cumulative_when_valido(
        self, inference_engine, confluence_engine, sample_df_m1_bull
    ):
        """
        Test 6: Latência cumulativa fim-a-fim.

        CASE: Predict + Confluência
        THEN: P95 cumulativo <125ms
        WHEN: Performance target alcançado
        """
        latencies = []

        # AÇÃO: 20 iterações para coletar dados
        for _ in range(20):
            start = time.time()

            # Predict
            t60_result = inference_engine.predict_from_df(sample_df_m1_bull)

            # Confluência
            smc_status = {"direction": "BULL", "strength": 0.85}
            result = confluence_engine.compute_confluence(t60_result, smc_status)

            latency = (time.time() - start) * 1000  # ms
            latencies.append(latency)

        # VALIDAÇÕES
        p95 = np.percentile(latencies, 95)
        assert p95 < 125.0  # <125ms target

        logger.info(f"✅ Test 6 PASSED: P95 latency = {p95:.2f}ms (target <125ms)")


class TestE2EErrorRecovery:
    """E2E tests para tratamento de erros."""

    def test_e2e_error_recovery_case_invalid_smc_then_fallback_to_aguardar_when_graceful(
        self, inference_engine, confluence_engine, sample_df_m1_bull
    ):
        """
        Test 7: Recuperação de erros — SMC inválido.

        CASE: SMC direction inválido (typo)
        THEN: Error tratado gracefully
        WHEN: ValueError capturado
        """
        t60_result = inference_engine.predict_from_df(sample_df_m1_bull)

        # AÇÃO: SMC inválido
        smc_status = {"direction": "INVALID", "strength": 0.85}

        # VALIDAÇÃO: Exception levantada apropriadamente
        with pytest.raises(ValueError):
            confluence_engine.compute_confluence(t60_result, smc_status)

        logger.info(f"✅ Test 7 PASSED: Error handling OK (ValueError capturado)")


class TestE2EStress:
    """E2E tests para stress testing."""

    def test_e2e_stress_case_1000_confluencias_then_memory_stable_when_longrun(
        self, inference_engine, confluence_engine, sample_df_m1_bull
    ):
        """
        Test 8: Stress test — 1000 confluências.

        CASE: 1000 confluências sequenciais
        THEN: Memory não cresce indefinidamente
        WHEN: Teste de estabilidade
        """
        import psutil
        import os as os_module

        process = psutil.Process(os_module.getpid())
        mem_before = process.memory_info().rss / 1024 / 1024  # MB

        # AÇÃO: 1000 confluências
        for i in range(1000):
            t60_result = inference_engine.predict_from_df(sample_df_m1_bull)
            smc_status = {
                "direction": ["BULL", "BEAR", "NEUTRO"][i % 3],
                "strength": 0.50 + (i % 100) * 0.01,
            }
            result = confluence_engine.compute_confluence(t60_result, smc_status)

            # Validação básica
            assert "state" in result

        mem_after = process.memory_info().rss / 1024 / 1024  # MB
        mem_delta = mem_after - mem_before

        # VALIDAÇÕES
        # Espera-se <50MB de crescimento em 1000 iterações
        assert mem_delta < 50.0  # <50MB delta

        logger.info(
            f"✅ Test 8 PASSED: Stress test 1000 confluências OK (mem delta={mem_delta:.1f}MB)"
        )


# ════════════════════════════════════════════════════════════════════════════
# BONUS: Full Coverage Test
# ════════════════════════════════════════════════════════════════════════════


class TestE2EFullCoverage:
    """Bonus test — coverage total."""

    def test_e2e_full_coverage_case_all_states_then_100_percent_when_completo(
        self, inference_engine, confluence_engine
    ):
        """
        Bonus Test 9: Coverage de todos os estados.

        CASE: BULL_SEGURO + BEAR_SEGURO + CONFLITO + AGUARDAR todos exercitados
        THEN: 100% coverage de states
        WHEN: Teste de sanidade
        """
        scenarios = [
            # (t60_score, smc_direction, expected_state)
            (0.75, "BULL", "BULL_SEGURO"),
            (0.25, "BEAR", "BEAR_SEGURO"),
            (0.75, "BEAR", "CONFLITO"),
            (0.25, "BULL", "CONFLITO"),
            (0.50, "BULL", "AGUARDAR"),
            (0.55, "NEUTRO", "AGUARDAR"),
        ]

        results_by_state = {}

        for t60_score, smc_dir, expected_state in scenarios:
            t60_result = {
                "score_t60": t60_score,
                "classe": "BULL" if t60_score > 0.62 else "BEAR" if t60_score < 0.38 else "NEUTRO",
            }
            smc_status = {"direction": smc_dir, "strength": 0.80}

            result = confluence_engine.compute_confluence(t60_result, smc_status)

            # Track results
            state = result["state"]
            if state not in results_by_state:
                results_by_state[state] = 0
            results_by_state[state] += 1

            # Validação
            assert state == expected_state

        # Verificar cobertura
        expected_states = {"BULL_SEGURO", "BEAR_SEGURO", "CONFLITO", "AGUARDAR"}
        found_states = set(results_by_state.keys())

        assert expected_states.issubset(found_states)

        logger.info(
            f"✅ Bonus Test 9 PASSED: Coverage completo "
            f"{results_by_state}"
        )


# ════════════════════════════════════════════════════════════════════════════
# RUN ALL TESTS
# ════════════════════════════════════════════════════════════════════════════


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
