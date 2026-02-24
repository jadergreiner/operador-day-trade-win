"""
test_score_t60_confluence.py — Testes do módulo de Confluência SMC + T60

8 Testes CASE-THEN-WHEN para validar lógica de integração dupla.

Author: QA Lead
Date: 2026-02-24
Version: 1.0.0
"""

import json
import logging
import os
import tempfile
from typing import Dict, Any

import pytest

from scripts.score_t60_confluence import ScoreT60Confluence, STATES, TRIGGERS

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


# ════════════════════════════════════════════════════════════════════════════
# FIXTURES
# ════════════════════════════════════════════════════════════════════════════


@pytest.fixture
def confluence_engine():
    """
    Fixture: Engine de confluência inicializado.

    CASE: Tests precisam de engine configurado
    THEN: Retorna engine com thresholds padrão
    """
    return ScoreT60Confluence(threshold_bull=0.62, threshold_bear=0.38)


# ════════════════════════════════════════════════════════════════════════════
# TEST SUITE — 8 TESTES
# ════════════════════════════════════════════════════════════════════════════


class TestConfluenceBullSeguro:
    """Tests para confluência BULL_SEGURO."""

    def test_confluence_bull_seguro_case_ambos_bull_then_trigger_buy_when_score_alto(
        self, confluence_engine
    ):
        """
        Test 1: BULL SEGURO (dupla validação positiva).

        CASE: T60=0.725 (BULL) AND SMC=BULL (strength 0.85)
        THEN: State=BULL_SEGURO, trigger=BUY, confidence=ALTA
        WHEN: Score confluência = (0.725 + 0.85) / 2 = 0.7875
        """
        # AÇÃO
        t60_result = {"score_t60": 0.725, "classe": "BULL"}
        smc_status = {"direction": "BULL", "strength": 0.85}

        result = confluence_engine.compute_confluence(t60_result, smc_status)

        # VALIDAÇÕES
        assert result["state"] == "BULL_SEGURO"
        assert result["trigger"] == "BUY"
        assert result["confidence"] == "ALTA"
        assert 0.70 < result["score_confluencia"] < 0.80
        assert result["validities"]["convergence"] is True

        logger.info(f"✅ Test 1 PASSED: BULL_SEGURO with score {result['score_confluencia']:.3f}")


class TestConfluenceBearSeguro:
    """Tests para confluência BEAR_SEGURO."""

    def test_confluence_bear_seguro_case_ambos_bear_then_trigger_sell_when_score_baixo(
        self, confluence_engine
    ):
        """
        Test 2: BEAR SEGURO (dupla validação negativa).

        CASE: T60=0.25 (BEAR) AND SMC=BEAR (strength 0.80)
        THEN: State=BEAR_SEGURO, trigger=SELL, confidence=ALTA
        WHEN: Score confluência = média invertida ≈ 0.725
        """
        # AÇÃO
        t60_result = {"score_t60": 0.25, "classe": "BEAR"}
        smc_status = {"direction": "BEAR", "strength": 0.80}

        result = confluence_engine.compute_confluence(t60_result, smc_status)

        # VALIDAÇÕES
        assert result["state"] == "BEAR_SEGURO"
        assert result["trigger"] == "SELL"
        assert result["confidence"] == "ALTA"
        assert 0.70 < result["score_confluencia"] < 0.80
        assert result["validities"]["convergence"] is True

        logger.info(f"✅ Test 2 PASSED: BEAR_SEGURO with score {result['score_confluencia']:.3f}")


class TestConfluenceConflito:
    """Tests para confluência CONFLITO."""

    def test_confluence_conflito_case_divergentes_bull_then_trigger_aguardar_when_ambiguo(
        self, confluence_engine
    ):
        """
        Test 3: CONFLITO (Divergência - T60 BULL, SMC BEAR).

        CASE: T60=0.72 (BULL) AND SMC=BEAR (strength 0.75)
        THEN: State=CONFLITO, trigger=AGUARDAR, confidence=BAIXA
        WHEN: Score confluência = 0.50 (neutra)
        """
        # AÇÃO
        t60_result = {"score_t60": 0.72, "classe": "BULL"}
        smc_status = {"direction": "BEAR", "strength": 0.75}

        result = confluence_engine.compute_confluence(t60_result, smc_status)

        # VALIDAÇÕES
        assert result["state"] == "CONFLITO"
        assert result["trigger"] == "AGUARDAR"
        assert result["confidence"] == "BAIXA"
        assert result["score_confluencia"] == 0.50  # Neutro em conflito
        assert result["validities"]["convergence"] is False

        logger.info(f"✅ Test 3 PASSED: CONFLITO (não operar)")

    def test_confluence_conflito_case_divergentes_bear_then_aguardar_when_sinal_oposto(
        self, confluence_engine
    ):
        """
        Test 4: CONFLITO (Divergência oposta - T60 BEAR, SMC BULL).

        CASE: T60=0.35 (BEAR) AND SMC=BULL (strength 0.90)
        THEN: State=CONFLITO, trigger=AGUARDAR, confidence=BAIXA
        WHEN: Score confluência = 0.50 (neutra)
        """
        # AÇÃO
        t60_result = {"score_t60": 0.35, "classe": "BEAR"}
        smc_status = {"direction": "BULL", "strength": 0.90}

        result = confluence_engine.compute_confluence(t60_result, smc_status)

        # VALIDAÇÕES
        assert result["state"] == "CONFLITO"
        assert result["trigger"] == "AGUARDAR"
        assert result["confidence"] == "BAIXA"
        assert result["score_confluencia"] == 0.50
        assert result["validities"]["convergence"] is False

        logger.info(f"✅ Test 4 PASSED: CONFLITO oposto (BEAR vs BULL)")


class TestConfluenceAguardar:
    """Tests para confluência AGUARDAR."""

    def test_confluence_aguardar_case_sinal_fraco_t60_then_hold_when_indeciso(
        self, confluence_engine
    ):
        """
        Test 5: AGUARDAR (Score T60 fraco/indeciso).

        CASE: T60=0.50 (NEUTRO) AND SMC=BULL
        THEN: State=AGUARDAR, trigger=HOLD, confidence=BAIXA
        WHEN: Score confluência = 0.50 (sem convergência clara)
        """
        # AÇÃO
        t60_result = {"score_t60": 0.50, "classe": "NEUTRO"}
        smc_status = {"direction": "BULL", "strength": 0.80}

        result = confluence_engine.compute_confluence(t60_result, smc_status)

        # VALIDAÇÕES
        assert result["state"] == "AGUARDAR"
        assert result["trigger"] == "HOLD"
        assert result["confidence"] == "BAIXA"
        assert result["score_confluencia"] == 0.50

        logger.info(f"✅ Test 5 PASSED: AGUARDAR (sinal fraco T60)")

    def test_confluence_aguardar_case_smc_neutro_then_hold_when_smc_ambiguo(
        self, confluence_engine
    ):
        """
        Test 6: AGUARDAR (SMC NEUTRO).

        CASE: T60=0.70 (BULL) AND SMC=NEUTRO
        THEN: State=AGUARDAR, trigger=HOLD, confidence=BAIXA
        WHEN: SMC sem direção clara
        """
        # AÇÃO
        t60_result = {"score_t60": 0.70, "classe": "BULL"}
        smc_status = {"direction": "NEUTRO", "strength": 0.50}

        result = confluence_engine.compute_confluence(t60_result, smc_status)

        # VALIDAÇÕES
        assert result["state"] == "AGUARDAR"
        assert result["trigger"] == "HOLD"
        assert result["confidence"] == "BAIXA"
        assert result["validities"]["convergence"] is True  # NEUTRO não é divergência

        logger.info(f"✅ Test 6 PASSED: AGUARDAR (SMC NEUTRO)")


class TestConfluencePersistence:
    """Tests para persistência de resultados."""

    def test_persistence_json_case_resultado_then_arquivo_criado_when_valido(
        self, confluence_engine
    ):
        """
        Test 7: Persistência em JSON.

        CASE: compute_confluence() com resultado válido
        THEN: persist_result() cria arquivo JSON
        WHEN: Arquivo contém 4 campos obrigatórios
        """
        # AÇÃO 1: Compute
        t60_result = {"score_t60": 0.725, "classe": "BULL"}
        smc_status = {"direction": "BULL", "strength": 0.85}
        result = confluence_engine.compute_confluence(t60_result, smc_status)

        # AÇÃO 2: Persist em temp file
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".json", delete=False
        ) as f:
            temp_path = f.name

        try:
            confluence_engine.persist_result(temp_path)

            # VALIDAÇÕES
            assert os.path.exists(temp_path)

            with open(temp_path, "r") as f:
                loaded = json.load(f)

            # 4 campos obrigatórios
            assert "state" in loaded
            assert "score_confluencia" in loaded
            assert "confidence" in loaded
            assert "trigger" in loaded
            assert loaded["state"] == "BULL_SEGURO"

            logger.info(f"✅ Test 7 PASSED: JSON persistence OK")

        finally:
            if os.path.exists(temp_path):
                os.unlink(temp_path)


class TestConfluenceErrorHandling:
    """Tests para tratamento de erros."""

    def test_error_handling_case_inputs_invalidos_then_excecao_when_score_fora_range(
        self, confluence_engine
    ):
        """
        Test 8: Tratamento de erros com validação.

        CASE: compute_confluence(score_t60=1.5) — fora [0, 1]
        THEN: ValueError levantado
        WHEN: "_validate_inputs" detecta erro
        """
        # AÇÃO
        t60_result = {"score_t60": 1.5}  # Inválido!
        smc_status = {"direction": "BULL", "strength": 0.80}

        # VALIDAÇÃO: Exception levantada
        with pytest.raises(ValueError, match="score_t60"):
            confluence_engine.compute_confluence(t60_result, smc_status)

        logger.info(f"✅ Test 8 PASSED: Error handling (invalid score)")


class TestConfluenceHistoryStats:
    """Tests para estatísticas de histórico."""

    def test_history_stats_case_multiplas_confluencias_then_counts_acumulados(
        self, confluence_engine
    ):
        """
        Test de bonus: Histórico e estatísticas.

        CASE: 3 confluências (BULL_SEGURO, BEAR_SEGURO, CONFLITO)
        THEN: get_history_stats() retorna counts corretos
        """
        # AÇÃO: 3 confluências
        confluence_engine.compute_confluence(
            {"score_t60": 0.725, "classe": "BULL"},
            {"direction": "BULL", "strength": 0.85},
        )
        confluence_engine.compute_confluence(
            {"score_t60": 0.25, "classe": "BEAR"},
            {"direction": "BEAR", "strength": 0.80},
        )
        confluence_engine.compute_confluence(
            {"score_t60": 0.72, "classe": "BULL"},
            {"direction": "BEAR", "strength": 0.75},
        )

        # VALIDAÇÕES
        stats = confluence_engine.get_history_stats()
        assert stats["total"] == 3
        assert stats["bull_seguro_count"] == 1
        assert stats["bear_seguro_count"] == 1
        assert stats["conflito_count"] == 1
        assert stats["avg_score"] > 0.0

        logger.info(f"✅ Bonus Test PASSED: History stats {stats}")


# ════════════════════════════════════════════════════════════════════════════
# RUN ALL TESTS
# ════════════════════════════════════════════════════════════════════════════


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
