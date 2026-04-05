"""
Testes unitarios para bdi_processor_v2 — ENG-202 (BLID-037)

Cobre:
- RegistroAuditFiltro: criacao e campos
- MetricasPipelineBDI: contadores, precision, recall, f1_score, exportar()
- FiltroConfiancaBDI: avaliar(), exportar_metricas(), registrar_resultado_real()
"""

from dataclasses import fields
from datetime import datetime
from decimal import Decimal

import pytest

from src.domain.bdi_processor_v2 import (
    LIMIAR_CONFIANCA_PADRAO,
    FiltroConfiancaBDI,
    MetricasPipelineBDI,
    RegistroAuditFiltro,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _alerta_fake(confianca: float, padrao: str = "engulfing_bullish"):
    """Cria mock de AlertaOportunidade com confianca e padrao fornecidos."""
    from unittest.mock import MagicMock

    alerta = MagicMock()
    alerta.confianca = Decimal(str(confianca))
    alerta.ativo = "WIN$N"
    alerta.padrao.value = padrao
    return alerta


# ---------------------------------------------------------------------------
# RegistroAuditFiltro
# ---------------------------------------------------------------------------

class TestRegistroAuditFiltro:
    """Testes para dataclass RegistroAuditFiltro."""

    def test_criacao_com_todos_campos(self):
        """RegistroAuditFiltro deve aceitar todos os campos obrigatorios."""
        registro = RegistroAuditFiltro(
            timestamp=datetime.now(),
            ativo="WIN$N",
            padrao="engulfing_bullish",
            confianca=Decimal("0.80"),
            decisao="APROVADO",
            motivo="confianca=0.800 > limiar=0.75",
            latencia_ms=0.12,
        )
        assert registro.ativo == "WIN$N"
        assert registro.decisao == "APROVADO"
        assert registro.latencia_ms == pytest.approx(0.12, abs=1e-9)

    def test_campos_esperados(self):
        """RegistroAuditFiltro deve ter 7 campos definidos."""
        nomes = {f.name for f in fields(RegistroAuditFiltro)}
        esperados = {
            "timestamp", "ativo", "padrao", "confianca",
            "decisao", "motivo", "latencia_ms",
        }
        assert nomes == esperados


# ---------------------------------------------------------------------------
# MetricasPipelineBDI
# ---------------------------------------------------------------------------

class TestMetricasPipelineBDI:
    """Testes para MetricasPipelineBDI."""

    def test_estado_inicial(self):
        """Metricas iniciam zeradas."""
        m = MetricasPipelineBDI()
        assert m.total_processados == 0
        assert m.aprovados == 0
        assert m.rejeitados == 0
        assert m.precision == 0.0
        assert m.recall == 0.0
        assert m.f1_score == 0.0

    def test_precision_sem_feedback_usa_razao_aprovacao(self):
        """Sem feedback real, precision = aprovados / total_processados."""
        m = MetricasPipelineBDI(total_processados=10, aprovados=8, rejeitados=2)
        assert m.precision == pytest.approx(0.8, abs=1e-4)

    def test_recall_sem_feedback_retorna_1_quando_ha_aprovados(self):
        """Sem feedback real e com aprovados, recall = 1.0."""
        m = MetricasPipelineBDI(total_processados=10, aprovados=8, rejeitados=2)
        assert m.recall == pytest.approx(1.0)

    def test_recall_sem_feedback_retorna_0_quando_zero_aprovados(self):
        """Sem aprovados, recall = 0.0."""
        m = MetricasPipelineBDI(total_processados=5, aprovados=0, rejeitados=5)
        assert m.recall == pytest.approx(0.0)

    def test_f1_score_calculado_corretamente(self):
        """F1 = 2 * p * r / (p + r)."""
        m = MetricasPipelineBDI(total_processados=10, aprovados=8, rejeitados=2)
        p = 0.8
        r = 1.0
        esperado = round(2 * p * r / (p + r), 4)
        assert m.f1_score == pytest.approx(esperado, abs=1e-4)

    def test_precision_com_feedback_real(self):
        """Com feedback real, precision = VP / (VP + FP)."""
        m = MetricasPipelineBDI(
            total_processados=10,
            aprovados=8,
            rejeitados=2,
            verdadeiros_positivos=6,
            falsos_positivos=2,
        )
        assert m.precision == pytest.approx(6 / 8, abs=1e-4)

    def test_recall_com_feedback_real(self):
        """Com feedback real, recall = VP / (VP + FN)."""
        m = MetricasPipelineBDI(
            total_processados=10,
            aprovados=8,
            rejeitados=2,
            verdadeiros_positivos=6,
            falsos_negativos=1,
        )
        assert m.recall == pytest.approx(6 / 7, abs=1e-4)

    def test_exportar_retorna_chaves_esperadas(self):
        """exportar() deve retornar dict com todas as chaves esperadas."""
        m = MetricasPipelineBDI(total_processados=4, aprovados=3, rejeitados=1)
        resultado = m.exportar()
        chaves_esperadas = {
            "total_processados", "aprovados", "rejeitados",
            "taxa_aprovacao", "precision", "recall", "f1_score",
        }
        assert set(resultado.keys()) == chaves_esperadas

    def test_exportar_taxa_aprovacao(self):
        """taxa_aprovacao = aprovados / total_processados."""
        m = MetricasPipelineBDI(total_processados=10, aprovados=7, rejeitados=3)
        resultado = m.exportar()
        assert resultado["taxa_aprovacao"] == pytest.approx(0.7, abs=1e-4)

    def test_exportar_total_zero_nao_levanta_divisao(self):
        """exportar() com total=0 nao levanta ZeroDivisionError."""
        m = MetricasPipelineBDI()
        resultado = m.exportar()
        assert resultado["taxa_aprovacao"] == 0.0
        assert resultado["precision"] == 0.0


# ---------------------------------------------------------------------------
# FiltroConfiancaBDI
# ---------------------------------------------------------------------------

class TestFiltroConfiancaBDI:
    """Testes para FiltroConfiancaBDI."""

    def test_limiar_padrao_e_0_75(self):
        """Limiar padrao deve ser 0.75."""
        filtro = FiltroConfiancaBDI()
        assert filtro.limiar == LIMIAR_CONFIANCA_PADRAO
        assert filtro.limiar == Decimal("0.75")

    def test_limiar_customizavel(self):
        """Limiar deve ser configuravel no construtor."""
        filtro = FiltroConfiancaBDI(limiar=Decimal("0.90"))
        assert filtro.limiar == Decimal("0.90")

    def test_avaliar_aprovado_confianca_acima_limiar(self):
        """Alerta com confianca > 0.75 deve ser aprovado."""
        filtro = FiltroConfiancaBDI()
        alerta = _alerta_fake(0.85)
        assert filtro.avaliar(alerta) is True

    def test_avaliar_aprovado_exatamente_acima_limiar(self):
        """Alerta com confianca = 0.76 deve ser aprovado."""
        filtro = FiltroConfiancaBDI()
        alerta = _alerta_fake(0.76)
        assert filtro.avaliar(alerta) is True

    def test_avaliar_rejeitado_confianca_igual_limiar(self):
        """Alerta com confianca = 0.75 deve ser REJEITADO (limiar estrito)."""
        filtro = FiltroConfiancaBDI()
        alerta = _alerta_fake(0.75)
        assert filtro.avaliar(alerta) is False

    def test_avaliar_rejeitado_confianca_abaixo_limiar(self):
        """Alerta com confianca < 0.75 deve ser rejeitado."""
        filtro = FiltroConfiancaBDI()
        alerta = _alerta_fake(0.65)
        assert filtro.avaliar(alerta) is False

    def test_historico_audit_cresce_por_avaliacao(self):
        """Cada chamada a avaliar() deve gerar um RegistroAuditFiltro."""
        filtro = FiltroConfiancaBDI()
        assert len(filtro.historico_audit) == 0
        filtro.avaliar(_alerta_fake(0.80))
        filtro.avaliar(_alerta_fake(0.60))
        assert len(filtro.historico_audit) == 2

    def test_registro_audit_decisao_aprovado(self):
        """Registro de alerta aprovado deve ter decisao='APROVADO'."""
        filtro = FiltroConfiancaBDI()
        filtro.avaliar(_alerta_fake(0.90))
        assert filtro.historico_audit[-1].decisao == "APROVADO"

    def test_registro_audit_decisao_rejeitado(self):
        """Registro de alerta rejeitado deve ter decisao='REJEITADO'."""
        filtro = FiltroConfiancaBDI()
        filtro.avaliar(_alerta_fake(0.60))
        assert filtro.historico_audit[-1].decisao == "REJEITADO"

    def test_registro_audit_confianca_preservada(self):
        """Registro deve preservar confianca original do alerta."""
        filtro = FiltroConfiancaBDI()
        filtro.avaliar(_alerta_fake(0.82))
        assert filtro.historico_audit[-1].confianca == Decimal("0.82")

    def test_registro_audit_latencia_positiva(self):
        """Latencia de avaliacao deve ser positiva (em ms)."""
        filtro = FiltroConfiancaBDI()
        filtro.avaliar(_alerta_fake(0.80))
        assert filtro.historico_audit[-1].latencia_ms >= 0.0

    def test_metricas_contadores_aprovados(self):
        """Contadores de aprovados devem ser incrementados corretamente."""
        filtro = FiltroConfiancaBDI()
        filtro.avaliar(_alerta_fake(0.80))
        filtro.avaliar(_alerta_fake(0.90))
        filtro.avaliar(_alerta_fake(0.60))
        assert filtro.metricas.total_processados == 3
        assert filtro.metricas.aprovados == 2
        assert filtro.metricas.rejeitados == 1

    def test_exportar_metricas_retorna_dict(self):
        """exportar_metricas() deve retornar dict com chaves esperadas."""
        filtro = FiltroConfiancaBDI()
        filtro.avaliar(_alerta_fake(0.80))
        resultado = filtro.exportar_metricas()
        assert isinstance(resultado, dict)
        assert "precision" in resultado
        assert "recall" in resultado
        assert "f1_score" in resultado

    def test_exportar_metricas_valores_entre_0_e_1(self):
        """precision, recall e f1_score devem estar entre 0 e 1."""
        filtro = FiltroConfiancaBDI()
        for confianca in [0.80, 0.85, 0.60, 0.70, 0.95]:
            filtro.avaliar(_alerta_fake(confianca))
        m = filtro.exportar_metricas()
        assert 0.0 <= m["precision"] <= 1.0
        assert 0.0 <= m["recall"] <= 1.0
        assert 0.0 <= m["f1_score"] <= 1.0

    def test_registrar_resultado_real_verdadeiro_positivo(self):
        """VP incrementado quando aprovado e correto."""
        filtro = FiltroConfiancaBDI()
        filtro.registrar_resultado_real(foi_aprovado=True, foi_correto=True)
        assert filtro.metricas.verdadeiros_positivos == 1
        assert filtro.metricas.falsos_positivos == 0

    def test_registrar_resultado_real_falso_positivo(self):
        """FP incrementado quando aprovado mas incorreto."""
        filtro = FiltroConfiancaBDI()
        filtro.registrar_resultado_real(foi_aprovado=True, foi_correto=False)
        assert filtro.metricas.falsos_positivos == 1
        assert filtro.metricas.verdadeiros_positivos == 0

    def test_registrar_resultado_real_falso_negativo(self):
        """FN incrementado quando rejeitado mas deveria ter sido aprovado."""
        filtro = FiltroConfiancaBDI()
        filtro.registrar_resultado_real(foi_aprovado=False, foi_correto=False)
        assert filtro.metricas.falsos_negativos == 1

    def test_precision_com_feedback_real_precisa(self):
        """Precision com feedback real = VP / (VP + FP)."""
        filtro = FiltroConfiancaBDI()
        # 6 VP + 2 FP → precision = 0.75
        for _ in range(6):
            filtro.registrar_resultado_real(foi_aprovado=True, foi_correto=True)
        for _ in range(2):
            filtro.registrar_resultado_real(foi_aprovado=True, foi_correto=False)
        assert filtro.metricas.precision == pytest.approx(0.75, abs=1e-4)
