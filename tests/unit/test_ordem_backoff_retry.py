"""
Testes para BUG-3: Backoff Exponencial e Deteccao de Rollover WINFUT.

Cobertura:
- StatusRetry enum
- ResultadoRetry dataclass
- calcular_terceira_quarta_do_mes()
- detectar_rollover_winfut()
- obter_proximo_simbolo_winfut()
- GerenciadorRetryOrdem: falhas, backoff, encerramento, rollover, simbolo

Status: BUG-3 (18/03/2026)
Referencia: docs/BACKLOG.md (BUG-3 / CRITICO)
"""

from __future__ import annotations

from datetime import date
from unittest.mock import MagicMock

import pytest

from src.application.ordem_backoff_retry import (
    GerenciadorRetryOrdem,
    ResultadoRetry,
    StatusRetry,
    calcular_terceira_quarta_do_mes,
    detectar_rollover_winfut,
    obter_proximo_simbolo_winfut,
)

RETCODE_10006 = 10006


# ─────────────────────────────────────────────────────────────────────────────
# StatusRetry e ResultadoRetry
# ─────────────────────────────────────────────────────────────────────────────

class TestStatusRetry:
    """Valida enum StatusRetry."""

    def test_valores_esperados(self) -> None:
        assert StatusRetry.PERMITIDO.value == "PERMITIDO"
        assert StatusRetry.EM_BACKOFF.value == "EM_BACKOFF"
        assert StatusRetry.ENCERRAR_SESSAO.value == "ENCERRAR_SESSAO"
        assert StatusRetry.ROLLOVER_DETECTADO.value == "ROLLOVER_DETECTADO"
        assert StatusRetry.SIMBOLO_INATIVO.value == "SIMBOLO_INATIVO"

    def test_contagem(self) -> None:
        assert len(StatusRetry) == 5


class TestResultadoRetry:
    """Valida dataclass ResultadoRetry."""

    def test_permitido_retorna_true(self) -> None:
        r = ResultadoRetry(
            status=StatusRetry.PERMITIDO,
            aguardar_segundos=0.0,
            mensagem="ok",
            falhas_consecutivas=0,
        )
        assert r.permitido() is True
        assert r.deve_encerrar() is False

    def test_em_backoff_nao_encerra(self) -> None:
        r = ResultadoRetry(
            status=StatusRetry.EM_BACKOFF,
            aguardar_segundos=5.0,
            mensagem="aguardando",
            falhas_consecutivas=1,
        )
        assert r.permitido() is False
        assert r.deve_encerrar() is False

    def test_encerrar_sessao_retorna_true(self) -> None:
        r = ResultadoRetry(
            status=StatusRetry.ENCERRAR_SESSAO,
            aguardar_segundos=0.0,
            mensagem="limite",
            falhas_consecutivas=5,
        )
        assert r.deve_encerrar() is True

    def test_rollover_detectado_encerra(self) -> None:
        r = ResultadoRetry(
            status=StatusRetry.ROLLOVER_DETECTADO,
            aguardar_segundos=0.0,
            mensagem="rollover",
            falhas_consecutivas=1,
        )
        assert r.deve_encerrar() is True


# ─────────────────────────────────────────────────────────────────────────────
# Calculos de data de rollover
# ─────────────────────────────────────────────────────────────────────────────

class TestCalcularTerceiraQuartaDomes:
    """Valida calculo da terceira quarta-feira."""

    def test_marco_2026(self) -> None:
        # Março 2026: 1/3 é domingo (6), primeira qua = 4/3, terceira = 18/3
        resultado = calcular_terceira_quarta_do_mes(2026, 3)
        assert resultado == date(2026, 3, 18)

    def test_junho_2026(self) -> None:
        # Junho 2026: 1/6 é segunda (0), primeira qua = 3/6, terceira = 17/6
        resultado = calcular_terceira_quarta_do_mes(2026, 6)
        assert resultado == date(2026, 6, 17)

    def test_janeiro_2026(self) -> None:
        # Janeiro 2026: 1/1 é quinta (3), primeira qua = 7/1, terceira = 21/1
        resultado = calcular_terceira_quarta_do_mes(2026, 1)
        assert resultado == date(2026, 1, 21)

    def test_resultado_e_quarta_feira(self) -> None:
        for mes in range(1, 13):
            resultado = calcular_terceira_quarta_do_mes(2026, mes)
            # weekday() == 2 para quarta-feira
            assert resultado.weekday() == 2, (
                f"Mes {mes}/2026: {resultado} nao e quarta-feira"
            )


class TestDetectarRolloverWinfut:
    """Valida deteccao de dia de rollover."""

    def test_dia_de_rollover_marco_2026(self) -> None:
        # 18/03/2026 e a terceira quarta-feira de marco
        assert detectar_rollover_winfut(date(2026, 3, 18)) is True

    def test_dia_diferente_nao_e_rollover(self) -> None:
        assert detectar_rollover_winfut(date(2026, 3, 17)) is False
        assert detectar_rollover_winfut(date(2026, 3, 19)) is False

    def test_dia_de_rollover_junho_2026(self) -> None:
        assert detectar_rollover_winfut(date(2026, 6, 17)) is True


class TestObterProximoSimboloWinfut:
    """Valida sugestao de proximo simbolo apos rollover."""

    def test_winj26_aponta_para_winm26(self) -> None:
        # WINJ26 = abril/2026, proximo vencimento = junho = WINM26
        assert obter_proximo_simbolo_winfut("WINJ26") == "WINM26"

    def test_winm26_aponta_para_winq26(self) -> None:
        # WINM26 = junho/2026, proximo = agosto = WINQ26
        assert obter_proximo_simbolo_winfut("WINM26") == "WINQ26"

    def test_winz26_aponta_para_wing27(self) -> None:
        # WINZ26 = dezembro/2026, proximo = fevereiro/2027 = WING27
        assert obter_proximo_simbolo_winfut("WINZ26") == "WING27"

    def test_simbolo_invalido_retorna_none(self) -> None:
        assert obter_proximo_simbolo_winfut("INVALID") is None
        assert obter_proximo_simbolo_winfut("") is None
        assert obter_proximo_simbolo_winfut("WIN") is None

    def test_letra_mes_invalida_retorna_none(self) -> None:
        # A nao e mes valido de WINFUT
        assert obter_proximo_simbolo_winfut("WINA26") is None


# ─────────────────────────────────────────────────────────────────────────────
# GerenciadorRetryOrdem
# ─────────────────────────────────────────────────────────────────────────────

class TestGerenciadorRetryOrdem:
    """Valida logica de backoff e encerramento de sessao."""

    @pytest.fixture
    def mgr(self) -> GerenciadorRetryOrdem:
        """Gerenciador sem verificacao de rollover para testes unitarios."""
        return GerenciadorRetryOrdem(
            simbolo="WINJ26",
            limite_encerrar=5,
            verificar_rollover=False,
        )

    def test_inicializa_zerado(self, mgr: GerenciadorRetryOrdem) -> None:
        assert mgr.falhas_consecutivas == 0
        assert mgr.historico_falhas == []

    def test_primeira_falha_aplica_backoff(self, mgr: GerenciadorRetryOrdem) -> None:
        resultado = mgr.registrar_falha_10006(RETCODE_10006)
        assert resultado.status == StatusRetry.EM_BACKOFF
        assert resultado.aguardar_segundos == 5.0
        assert resultado.falhas_consecutivas == 1

    def test_terceira_falha_aguarda_60s(self, mgr: GerenciadorRetryOrdem) -> None:
        mgr.registrar_falha_10006(RETCODE_10006)
        mgr.registrar_falha_10006(RETCODE_10006)
        resultado = mgr.registrar_falha_10006(RETCODE_10006)
        assert resultado.status == StatusRetry.EM_BACKOFF
        assert resultado.aguardar_segundos == 60.0
        assert resultado.falhas_consecutivas == 3

    def test_quinta_falha_encerra_sessao(self, mgr: GerenciadorRetryOrdem) -> None:
        for _ in range(4):
            mgr.registrar_falha_10006(RETCODE_10006)
        resultado = mgr.registrar_falha_10006(RETCODE_10006)
        assert resultado.status == StatusRetry.ENCERRAR_SESSAO
        assert resultado.deve_encerrar() is True
        assert resultado.falhas_consecutivas == 5

    def test_sucesso_reseta_contador(self, mgr: GerenciadorRetryOrdem) -> None:
        mgr.registrar_falha_10006(RETCODE_10006)
        mgr.registrar_falha_10006(RETCODE_10006)
        assert mgr.falhas_consecutivas == 2
        mgr.registrar_sucesso()
        assert mgr.falhas_consecutivas == 0

    def test_sucesso_sem_falhas_nao_quebra(self, mgr: GerenciadorRetryOrdem) -> None:
        # Nao deve levantar excecao
        mgr.registrar_sucesso()
        assert mgr.falhas_consecutivas == 0

    def test_historico_acumula_falhas(self, mgr: GerenciadorRetryOrdem) -> None:
        mgr.registrar_falha_10006(RETCODE_10006)
        mgr.registrar_falha_10006(RETCODE_10006)
        assert len(mgr.historico_falhas) == 2
        assert mgr.historico_falhas[0]["retcode"] == RETCODE_10006

    def test_historico_nao_reseta_com_sucesso(self, mgr: GerenciadorRetryOrdem) -> None:
        mgr.registrar_falha_10006(RETCODE_10006)
        mgr.registrar_sucesso()
        # Historico preservado mesmo apos sucesso
        assert len(mgr.historico_falhas) == 1

    def test_resumo_retorna_dict(self, mgr: GerenciadorRetryOrdem) -> None:
        resumo = mgr.resumo()
        assert "simbolo" in resumo
        assert "falhas_consecutivas" in resumo
        assert "limite_encerrar" in resumo
        assert resumo["simbolo"] == "WINJ26"
        assert resumo["falhas_consecutivas"] == 0


class TestGerenciadorRetryRollover:
    """Valida deteccao de rollover integrada ao gerenciador."""

    def test_rollover_ativo_encerra_sessao(self) -> None:
        # Criar gerenciador com verificacao de rollover ativada
        # e simular que hoje e dia de rollover (18/03/2026)
        mgr = GerenciadorRetryOrdem(
            simbolo="WINH26",
            limite_encerrar=5,
            verificar_rollover=True,
        )
        # Forcar dia de rollover: 18/03/2026 e terceira quarta de marco
        # Precisamos mockar detectar_rollover_winfut via patch
        import unittest.mock as mock
        with mock.patch(
            "src.application.ordem_backoff_retry.detectar_rollover_winfut",
            return_value=True,
        ):
            resultado = mgr.registrar_falha_10006(RETCODE_10006)

        assert resultado.status == StatusRetry.ROLLOVER_DETECTADO
        assert resultado.deve_encerrar() is True

    def test_sem_rollover_aplica_backoff_normal(self) -> None:
        mgr = GerenciadorRetryOrdem(
            simbolo="WINJ26",
            limite_encerrar=5,
            verificar_rollover=True,
        )
        import unittest.mock as mock
        with mock.patch(
            "src.application.ordem_backoff_retry.detectar_rollover_winfut",
            return_value=False,
        ):
            resultado = mgr.registrar_falha_10006(RETCODE_10006)

        assert resultado.status == StatusRetry.EM_BACKOFF


class TestVerificarSimboloAtivo:
    """Valida verificacao de disponibilidade do simbolo."""

    def test_simbolo_ativo_retorna_true(self) -> None:
        mt5_mock = MagicMock()
        info_mock = MagicMock()
        info_mock.trade_mode = 4  # TRADE_MODE_FULL
        mt5_mock.symbol_info.return_value = info_mock

        mgr = GerenciadorRetryOrdem("WINJ26", verificar_rollover=False)
        assert mgr.verificar_simbolo_ativo(mt5_mock) is True

    def test_simbolo_desativado_retorna_false(self) -> None:
        mt5_mock = MagicMock()
        info_mock = MagicMock()
        info_mock.trade_mode = 0  # TRADE_MODE_DISABLED
        mt5_mock.symbol_info.return_value = info_mock

        mgr = GerenciadorRetryOrdem("WINJ26", verificar_rollover=False)
        assert mgr.verificar_simbolo_ativo(mt5_mock) is False

    def test_simbolo_inexistente_retorna_false(self) -> None:
        mt5_mock = MagicMock()
        mt5_mock.symbol_info.return_value = None

        mgr = GerenciadorRetryOrdem("WINZZ26", verificar_rollover=False)
        assert mgr.verificar_simbolo_ativo(mt5_mock) is False

    def test_excecao_na_consulta_retorna_false(self) -> None:
        mt5_mock = MagicMock()
        mt5_mock.symbol_info.side_effect = Exception("Sem conexao MT5")

        mgr = GerenciadorRetryOrdem("WINJ26", verificar_rollover=False)
        assert mgr.verificar_simbolo_ativo(mt5_mock) is False


class TestTypeHints:
    """Valida que type hints estao corretos no modulo."""

    def test_importa_sem_erros(self) -> None:
        from src.application.ordem_backoff_retry import (
            GerenciadorRetryOrdem,
            ResultadoRetry,
            StatusRetry,
            calcular_terceira_quarta_do_mes,
            detectar_rollover_winfut,
            obter_proximo_simbolo_winfut,
        )
        assert GerenciadorRetryOrdem is not None
        assert ResultadoRetry is not None
        assert StatusRetry is not None
        assert calcular_terceira_quarta_do_mes is not None
        assert detectar_rollover_winfut is not None
        assert obter_proximo_simbolo_winfut is not None
