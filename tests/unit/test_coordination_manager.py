"""Testes TDD para CoordinationManager (BLID-041).

Cenarios cobertos (AC1-AC10):
    AC1  - Inicializacao com config valida
    AC2  - Banco ausente retorna EstadoAgente zerado e sinal NORMAL
    AC3  - Drawdown individual >10% -> MODO_CONSERVADOR
    AC4  - Drawdown conjunto >15% -> MODO_DEFENSIVO
    AC5  - Capital <R$500 -> STOP_OPERACOES (prioridade sobre drawdown)
    AC6  - Sem threshold violado -> NORMAL e nenhum log de alerta
    AC7  - Persistencia atomica em coordination_signal_current.json
    AC8  - Callback registrado e invocado quando sinal != NORMAL
    AC9  - Thread daemon pode ser iniciada e parada
    AC10 - Config invalida (drawdown_individual >= drawdown_conjunto) -> ValueError

Formulas de referencia (especificacao BLID-041):
    drawdown_agente = max((peak - valley) / capital_inicial_sessao_reais)
                   onde peak e valley sao valores absolutos acumulados de PnL.
                   Se total_trades < 2: drawdown = 0.0.

    Prioridade dos thresholds (1 = maior prioridade):
        1. capital_estimado < capital_minimo_reais         -> STOP_OPERACOES
        2. drawdown_conjunto > drawdown_conjunto_pct       -> MODO_DEFENSIVO
        3. qualquer drawdown_individual > drawdown_individual_pct -> MODO_CONSERVADOR
        4. nenhum threshold violado                        -> NORMAL
"""

from __future__ import annotations

import json
import re
import threading
import time
from datetime import datetime
from typing import Any
from unittest.mock import MagicMock, call, patch

import pytest

from src.application.coordination_manager import (
    CoordinationManager,
    CoordinationSignal,
    ConfiguracaoCoordinacao,
    DecisaoCoordinacao,
    EstadoAgente,
)

# ---------------------------------------------------------------------------
# Constantes de apoio para dados de teste
# ---------------------------------------------------------------------------

_CAPITAL_INICIAL: float = 5_000.0
_CAPITAL_MINIMO: float = 500.0
_DRAWDOWN_INDIVIDUAL_PCT: float = 10.0
_DRAWDOWN_CONJUNTO_PCT: float = 15.0
_DB_PATH: str = "/tmp/test_trades.db"
_SINAL_PATH: str = "/tmp/coordination_signal_current.json"
_LOG_DIR: str = "/tmp/logs"


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def config_valida() -> ConfiguracaoCoordinacao:
    """Config valida para uso nos testes."""
    return ConfiguracaoCoordinacao(
        drawdown_individual_pct=_DRAWDOWN_INDIVIDUAL_PCT,
        drawdown_conjunto_pct=_DRAWDOWN_CONJUNTO_PCT,
        capital_minimo_reais=_CAPITAL_MINIMO,
        capital_inicial_sessao_reais=_CAPITAL_INICIAL,
        intervalo_polling_segundos=0.1,
        agentes_monitorados=["rl_5000", "rl_direto"],
        db_path=_DB_PATH,
        sinal_atual_path=_SINAL_PATH,
        log_dir=_LOG_DIR,
    )


@pytest.fixture
def _mock_sqlite_sem_banco() -> Any:
    """Mock que simula banco de dados ausente (OperationalError)."""
    import sqlite3
    with patch("src.application.coordination_manager.sqlite3.connect") as mock_conn:
        mock_conn.side_effect = sqlite3.OperationalError("unable to open database file")
        yield mock_conn


@pytest.fixture
def _mock_sqlite_com_trades() -> Any:
    """Mock que simula banco com trades para os dois agentes."""
    def _criar_mock_connect(pnl_5000: list[float], pnl_direto: list[float]) -> Any:
        # Retorna um contador de chamadas para rastrear qual magic_number foi usado
        chamada = {"indice": 0}
        # Ordem das chamadas: primeiro rl_5000 (magic=234500), depois rl_direto (magic=234600)
        sequencia_pnl = [pnl_5000, pnl_direto]

        def _side_effect(*args: Any, **kwargs: Any) -> Any:
            mock_conn = MagicMock()
            idx = chamada["indice"]
            pnl_atual = sequencia_pnl[idx] if idx < len(sequencia_pnl) else []
            chamada["indice"] += 1

            def _execute_side_effect(query: str, params: tuple[Any, ...] = ()) -> Any:
                mock_cursor_result = MagicMock()
                if "PRAGMA" in query:
                    mock_cursor_result.fetchall.return_value = []
                else:
                    mock_cursor_result.fetchall.return_value = [(p,) for p in pnl_atual]
                return mock_cursor_result

            mock_conn.__enter__ = MagicMock(return_value=mock_conn)
            mock_conn.__exit__ = MagicMock(return_value=False)
            mock_conn.execute = MagicMock(side_effect=_execute_side_effect)
            return mock_conn

        return _side_effect
    return _criar_mock_connect


# ---------------------------------------------------------------------------
# AC1 - Inicializacao com config valida
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestInicializacaoCoordinationManager:
    """AC1: CoordinationManager inicializa corretamente com config valida."""

    def test_inicializacao_com_config_valida_cria_instancia(
        self, config_valida: ConfiguracaoCoordinacao
    ) -> None:
        """Dado config valida, deve criar instancia sem erros."""
        manager = CoordinationManager(config=config_valida)
        assert manager is not None

    def test_sinal_inicial_eh_normal_antes_do_primeiro_ciclo(
        self, config_valida: ConfiguracaoCoordinacao
    ) -> None:
        """Antes do primeiro ciclo, o sinal inicial deve ser NORMAL."""
        manager = CoordinationManager(config=config_valida)
        assert manager.obter_ultimo_sinal() == CoordinationSignal.NORMAL

    def test_config_expoe_campos_obrigatorios(
        self, config_valida: ConfiguracaoCoordinacao
    ) -> None:
        """Config deve expor todos os campos obrigatorios."""
        assert config_valida.drawdown_individual_pct == _DRAWDOWN_INDIVIDUAL_PCT
        assert config_valida.drawdown_conjunto_pct == _DRAWDOWN_CONJUNTO_PCT
        assert config_valida.capital_minimo_reais == _CAPITAL_MINIMO
        assert config_valida.capital_inicial_sessao_reais == _CAPITAL_INICIAL
        assert "rl_5000" in config_valida.agentes_monitorados
        assert "rl_direto" in config_valida.agentes_monitorados

    def test_enum_coordination_signal_possui_todos_os_valores(self) -> None:
        """Enum CoordinationSignal deve ter todos os 4 valores especificados."""
        assert CoordinationSignal.NORMAL
        assert CoordinationSignal.MODO_CONSERVADOR
        assert CoordinationSignal.MODO_DEFENSIVO
        assert CoordinationSignal.STOP_OPERACOES


# ---------------------------------------------------------------------------
# AC2 - Banco ausente -> NORMAL zerado
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestBancoAusente:
    """AC2: Banco ausente deve retornar sinal NORMAL com drawdowns zerados."""

    def test_banco_ausente_retorna_sinal_normal(
        self, config_valida: ConfiguracaoCoordinacao, _mock_sqlite_sem_banco: Any
    ) -> None:
        """Dado banco inacessivel, sinal deve ser NORMAL."""
        manager = CoordinationManager(config=config_valida)
        decisao = manager.executar_ciclo()
        assert decisao.sinal == CoordinationSignal.NORMAL

    def test_banco_ausente_retorna_drawdown_zerado(
        self, config_valida: ConfiguracaoCoordinacao, _mock_sqlite_sem_banco: Any
    ) -> None:
        """Dado banco inacessivel, drawdowns devem ser zero."""
        manager = CoordinationManager(config=config_valida)
        decisao = manager.executar_ciclo()
        assert decisao.drawdown_rl_5000_pct == 0.0
        assert decisao.drawdown_rl_direto_pct == 0.0
        assert decisao.drawdown_conjunto_pct == 0.0

    def test_banco_ausente_threshold_nao_violado(
        self, config_valida: ConfiguracaoCoordinacao, _mock_sqlite_sem_banco: Any
    ) -> None:
        """Dado banco inacessivel, threshold_violado deve ser None."""
        manager = CoordinationManager(config=config_valida)
        decisao = manager.executar_ciclo()
        assert decisao.threshold_violado is None
        assert decisao.agente_gatilho is None


# ---------------------------------------------------------------------------
# AC3 - Drawdown individual >10% -> MODO_CONSERVADOR
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestDrawdownIndividualModoCons:
    """AC3: Drawdown individual acima do limiar deve emitir MODO_CONSERVADOR."""

    def test_drawdown_individual_acima_limiar_emite_modo_conservador(
        self, config_valida: ConfiguracaoCoordinacao, _mock_sqlite_com_trades: Any
    ) -> None:
        """Dado rl_5000 com drawdown >10%, deve emitir MODO_CONSERVADOR."""
        # rl_5000: 5000 -> 4400 (drawdown = 600/5000 = 12%) -> acima do limiar de 10%
        pnl_5000 = [-300.0, -300.0, 50.0]
        pnl_direto = [100.0, 50.0, 100.0]
        criar_mock = _mock_sqlite_com_trades(pnl_5000, pnl_direto)
        with patch("src.application.coordination_manager.sqlite3.connect", side_effect=criar_mock):
            manager = CoordinationManager(config=config_valida)
            decisao = manager.executar_ciclo()
        assert decisao.sinal == CoordinationSignal.MODO_CONSERVADOR

    def test_drawdown_individual_identifica_agente_gatilho(
        self, config_valida: ConfiguracaoCoordinacao, _mock_sqlite_com_trades: Any
    ) -> None:
        """Dado rl_5000 com drawdown >10%, agente_gatilho deve ser 'rl_5000'."""
        pnl_5000 = [-300.0, -300.0, 50.0]
        pnl_direto = [100.0, 50.0, 100.0]
        criar_mock = _mock_sqlite_com_trades(pnl_5000, pnl_direto)
        with patch("src.application.coordination_manager.sqlite3.connect", side_effect=criar_mock):
            manager = CoordinationManager(config=config_valida)
            decisao = manager.executar_ciclo()
        assert decisao.agente_gatilho == "rl_5000"

    def test_drawdown_individual_registra_threshold_violado(
        self, config_valida: ConfiguracaoCoordinacao, _mock_sqlite_com_trades: Any
    ) -> None:
        """Dado drawdown individual violado, threshold_violado deve ser 'drawdown_individual'."""
        pnl_5000 = [-300.0, -300.0, 50.0]
        pnl_direto = [100.0, 50.0, 100.0]
        criar_mock = _mock_sqlite_com_trades(pnl_5000, pnl_direto)
        with patch("src.application.coordination_manager.sqlite3.connect", side_effect=criar_mock):
            manager = CoordinationManager(config=config_valida)
            decisao = manager.executar_ciclo()
        assert decisao.threshold_violado == "drawdown_individual"

    def test_menos_de_dois_trades_drawdown_eh_zero(
        self, config_valida: ConfiguracaoCoordinacao, _mock_sqlite_com_trades: Any
    ) -> None:
        """Dado apenas 1 trade por agente, drawdown deve ser 0.0."""
        pnl_5000 = [-600.0]  # 12% de perda mas apenas 1 trade
        pnl_direto = [-600.0]  # idem
        criar_mock = _mock_sqlite_com_trades(pnl_5000, pnl_direto)
        with patch("src.application.coordination_manager.sqlite3.connect", side_effect=criar_mock):
            manager = CoordinationManager(config=config_valida)
            decisao = manager.executar_ciclo()
        # Com < 2 trades, drawdown = 0.0 e capital estimado = 5000 - 1200 = 3800 > 500
        assert decisao.drawdown_rl_5000_pct == 0.0
        assert decisao.drawdown_rl_direto_pct == 0.0


# ---------------------------------------------------------------------------
# AC4 - Drawdown conjunto >15% -> MODO_DEFENSIVO
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestDrawdownConjuntoModoDefensivo:
    """AC4: Drawdown conjunto acima do limiar deve emitir MODO_DEFENSIVO."""

    def test_drawdown_conjunto_acima_limiar_emite_modo_defensivo(
        self, config_valida: ConfiguracaoCoordinacao, _mock_sqlite_com_trades: Any
    ) -> None:
        """Dado drawdown conjunto >15% (ambos abaixo de 10% individual), deve ser MODO_DEFENSIVO."""
        # Ambos os agentes com drawdown individual em ~9% (abaixo do limiar de 10%)
        # mas conjunto deve passar de 15%
        # rl_5000: 5000 -> 4550 -> 4600, drawdown = 450/5000 = 9%
        pnl_5000 = [-450.0, 50.0]
        # rl_direto: 5000 -> 4600 -> 4650, drawdown = 400/5000 = 8%
        pnl_direto = [-400.0, 50.0]
        # Capital estimado = 5000 + (-400) + (-350) = 4250 > 500 (OK)
        # Drawdown conjunto: curva [5000, 4550, 4600, 4200, 4250]
        # pico = 5000, vale = 4200, dd = 800/5000 = 16% > 15%
        criar_mock = _mock_sqlite_com_trades(pnl_5000, pnl_direto)
        with patch("src.application.coordination_manager.sqlite3.connect", side_effect=criar_mock):
            manager = CoordinationManager(config=config_valida)
            decisao = manager.executar_ciclo()
        assert decisao.sinal == CoordinationSignal.MODO_DEFENSIVO

    def test_modo_defensivo_tem_prioridade_sobre_conservador(
        self, config_valida: ConfiguracaoCoordinacao, _mock_sqlite_com_trades: Any
    ) -> None:
        """Dado drawdown individual >10% E conjunto >15%, deve emitir MODO_DEFENSIVO (prioridade)."""
        # rl_5000 com drawdown individual alto (>10%) E drawdown conjunto >15%
        pnl_5000 = [-550.0, 50.0]   # drawdown_5000 = 550/5000 = 11% > 10%
        pnl_direto = [-400.0, 50.0]  # drawdown_direto = 400/5000 = 8%
        # conjunto: 800/5000 = 16% > 15% -> MODO_DEFENSIVO tem prioridade
        criar_mock = _mock_sqlite_com_trades(pnl_5000, pnl_direto)
        with patch("src.application.coordination_manager.sqlite3.connect", side_effect=criar_mock):
            manager = CoordinationManager(config=config_valida)
            decisao = manager.executar_ciclo()
        assert decisao.sinal == CoordinationSignal.MODO_DEFENSIVO


# ---------------------------------------------------------------------------
# AC5 - Capital <R$500 -> STOP_OPERACOES (prioridade maxima)
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestCapitalMinimoStopOperacoes:
    """AC5: Capital abaixo do minimo deve emitir STOP_OPERACOES com prioridade maxima."""

    def test_capital_abaixo_minimo_emite_stop_operacoes(
        self, config_valida: ConfiguracaoCoordinacao, _mock_sqlite_com_trades: Any
    ) -> None:
        """Dado capital estimado < R$500, deve emitir STOP_OPERACOES."""
        # Perda total que leva capital a menos de R$500
        # 5000 - 4600 = 400 < 500
        pnl_5000 = [-2300.0, 50.0]
        pnl_direto = [-2350.0, 50.0]
        # capital_estimado = 5000 + (-2250) + (-2300) = 450 < 500
        criar_mock = _mock_sqlite_com_trades(pnl_5000, pnl_direto)
        with patch("src.application.coordination_manager.sqlite3.connect", side_effect=criar_mock):
            manager = CoordinationManager(config=config_valida)
            decisao = manager.executar_ciclo()
        assert decisao.sinal == CoordinationSignal.STOP_OPERACOES
        assert decisao.capital_estimado_reais < _CAPITAL_MINIMO

    def test_stop_operacoes_tem_prioridade_maxima_sobre_drawdown(
        self, config_valida: ConfiguracaoCoordinacao, _mock_sqlite_com_trades: Any
    ) -> None:
        """Dado capital <500 E drawdown alto, STOP_OPERACOES deve prevalecer."""
        pnl_5000 = [-2300.0, 50.0]
        pnl_direto = [-2350.0, 50.0]
        criar_mock = _mock_sqlite_com_trades(pnl_5000, pnl_direto)
        with patch("src.application.coordination_manager.sqlite3.connect", side_effect=criar_mock):
            manager = CoordinationManager(config=config_valida)
            decisao = manager.executar_ciclo()
        # Independente do drawdown, capital baixo -> STOP
        assert decisao.sinal == CoordinationSignal.STOP_OPERACOES

    def test_stop_operacoes_registra_threshold_violado(
        self, config_valida: ConfiguracaoCoordinacao, _mock_sqlite_com_trades: Any
    ) -> None:
        """Dado STOP_OPERACOES, threshold_violado deve ser 'capital_minimo'."""
        pnl_5000 = [-2300.0, 50.0]
        pnl_direto = [-2350.0, 50.0]
        criar_mock = _mock_sqlite_com_trades(pnl_5000, pnl_direto)
        with patch("src.application.coordination_manager.sqlite3.connect", side_effect=criar_mock):
            manager = CoordinationManager(config=config_valida)
            decisao = manager.executar_ciclo()
        assert decisao.threshold_violado == "capital_minimo"


# ---------------------------------------------------------------------------
# AC6 - Sem threshold -> NORMAL sem log de alerta
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestSemThresholdNormal:
    """AC6: Sem threshold violado, sinal deve ser NORMAL sem log de alerta."""

    def test_todos_normais_emite_sinal_normal(
        self, config_valida: ConfiguracaoCoordinacao, _mock_sqlite_com_trades: Any
    ) -> None:
        """Dado todos os indicadores dentro dos limites, sinal deve ser NORMAL."""
        # Ganhos consistentes, sem violacao de drawdown ou capital
        pnl_5000 = [100.0, 150.0, 100.0]
        pnl_direto = [80.0, 120.0, 90.0]
        criar_mock = _mock_sqlite_com_trades(pnl_5000, pnl_direto)
        with patch("src.application.coordination_manager.sqlite3.connect", side_effect=criar_mock):
            manager = CoordinationManager(config=config_valida)
            decisao = manager.executar_ciclo()
        assert decisao.sinal == CoordinationSignal.NORMAL

    def test_normal_sem_threshold_violado(
        self, config_valida: ConfiguracaoCoordinacao, _mock_sqlite_com_trades: Any
    ) -> None:
        """Dado sinal NORMAL, threshold_violado e agente_gatilho devem ser None."""
        pnl_5000 = [100.0, 150.0, 100.0]
        pnl_direto = [80.0, 120.0, 90.0]
        criar_mock = _mock_sqlite_com_trades(pnl_5000, pnl_direto)
        with patch("src.application.coordination_manager.sqlite3.connect", side_effect=criar_mock):
            manager = CoordinationManager(config=config_valida)
            decisao = manager.executar_ciclo()
        assert decisao.threshold_violado is None
        assert decisao.agente_gatilho is None

    def test_normal_nao_emite_log_de_alerta(
        self, config_valida: ConfiguracaoCoordinacao, _mock_sqlite_com_trades: Any, caplog: Any
    ) -> None:
        """Dado sinal NORMAL, nao deve haver log de WARNING com 'threshold'."""
        import logging
        pnl_5000 = [100.0, 150.0]
        pnl_direto = [80.0, 90.0]
        criar_mock = _mock_sqlite_com_trades(pnl_5000, pnl_direto)
        with patch("src.application.coordination_manager.sqlite3.connect", side_effect=criar_mock):
            manager = CoordinationManager(config=config_valida)
            with caplog.at_level(logging.WARNING, logger="src.application.coordination_manager"):
                manager.executar_ciclo()
        alertas_threshold = [
            r for r in caplog.records
            if r.levelno >= logging.WARNING and "threshold" in r.message.lower()
        ]
        assert len(alertas_threshold) == 0


# ---------------------------------------------------------------------------
# AC7 - Persistencia atomica em coordination_signal_current.json
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestPersistenciaAtomicaJson:
    """AC7: Sinal atual deve ser persistido atomicamente em JSON."""

    def test_ciclo_escreve_arquivo_json_atomicamente(
        self, config_valida: ConfiguracaoCoordinacao, _mock_sqlite_sem_banco: Any
    ) -> None:
        """Dado um ciclo executado, deve escrever arquivo via .tmp + replace."""
        with patch("src.application.coordination_manager.Path") as mock_path_cls:
            mock_path_inst = MagicMock()
            mock_path_tmp = MagicMock()
            mock_path_inst.with_suffix.return_value = mock_path_tmp
            mock_path_inst.parent = MagicMock()
            mock_path_cls.return_value = mock_path_inst
            manager = CoordinationManager(config=config_valida)
            manager.executar_ciclo()
        # Deve ter chamado write_text no path tmp
        mock_path_tmp.write_text.assert_called_once()
        # Deve ter chamado replace para o path final
        mock_path_tmp.replace.assert_called_once_with(mock_path_inst)

    def test_json_de_sinal_contem_campos_obrigatorios(
        self, config_valida: ConfiguracaoCoordinacao, _mock_sqlite_sem_banco: Any
    ) -> None:
        """JSON escrito deve conter schema_version e campos obrigatorios."""
        conteudo_escrito: list[str] = []

        def _capturar_write(conteudo: str, encoding: str = "utf-8") -> None:
            conteudo_escrito.append(conteudo)

        with patch("src.application.coordination_manager.Path") as mock_path_cls:
            mock_path_inst = MagicMock()
            mock_path_tmp = MagicMock()
            mock_path_tmp.write_text.side_effect = _capturar_write
            mock_path_inst.with_suffix.return_value = mock_path_tmp
            mock_path_inst.parent = MagicMock()
            mock_path_cls.return_value = mock_path_inst
            manager = CoordinationManager(config=config_valida)
            manager.executar_ciclo()

        assert len(conteudo_escrito) == 1
        dados = json.loads(conteudo_escrito[0])
        assert dados.get("schema_version") == "1.0"
        assert "ciclo_id" in dados
        assert "timestamp_iso" in dados
        assert "sinal" in dados


# ---------------------------------------------------------------------------
# AC8 - Callback invocado quando sinal != NORMAL
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestCallbackQuandoSinalNaoNormal:
    """AC8: Callbacks registrados devem ser invocados quando sinal != NORMAL."""

    def test_callback_e_invocado_quando_sinal_modo_conservador(
        self, config_valida: ConfiguracaoCoordinacao, _mock_sqlite_com_trades: Any
    ) -> None:
        """Dado sinal MODO_CONSERVADOR, callback registrado deve ser chamado."""
        pnl_5000 = [-300.0, -300.0, 50.0]
        pnl_direto = [100.0, 50.0, 100.0]
        criar_mock = _mock_sqlite_com_trades(pnl_5000, pnl_direto)
        callback = MagicMock()
        with patch("src.application.coordination_manager.sqlite3.connect", side_effect=criar_mock):
            with patch("src.application.coordination_manager.Path") as mock_path_cls:
                mock_path_inst = MagicMock()
                mock_path_tmp = MagicMock()
                mock_path_inst.with_suffix.return_value = mock_path_tmp
                mock_path_inst.parent = MagicMock()
                mock_path_cls.return_value = mock_path_inst
                manager = CoordinationManager(config=config_valida)
                manager.registrar_callback(callback)
                decisao = manager.executar_ciclo()
        callback.assert_called_once_with(decisao)

    def test_callback_nao_e_invocado_quando_sinal_normal(
        self, config_valida: ConfiguracaoCoordinacao, _mock_sqlite_com_trades: Any
    ) -> None:
        """Dado sinal NORMAL, callback NAO deve ser chamado."""
        pnl_5000 = [100.0, 150.0]
        pnl_direto = [80.0, 90.0]
        criar_mock = _mock_sqlite_com_trades(pnl_5000, pnl_direto)
        callback = MagicMock()
        with patch("src.application.coordination_manager.sqlite3.connect", side_effect=criar_mock):
            with patch("src.application.coordination_manager.Path") as mock_path_cls:
                mock_path_inst = MagicMock()
                mock_path_tmp = MagicMock()
                mock_path_inst.with_suffix.return_value = mock_path_tmp
                mock_path_inst.parent = MagicMock()
                mock_path_cls.return_value = mock_path_inst
                manager = CoordinationManager(config=config_valida)
                manager.registrar_callback(callback)
                manager.executar_ciclo()
        callback.assert_not_called()

    def test_multiplos_callbacks_sao_todos_invocados(
        self, config_valida: ConfiguracaoCoordinacao, _mock_sqlite_com_trades: Any
    ) -> None:
        """Dado multiplos callbacks registrados, todos devem ser invocados."""
        pnl_5000 = [-300.0, -300.0, 50.0]
        pnl_direto = [100.0, 50.0, 100.0]
        criar_mock = _mock_sqlite_com_trades(pnl_5000, pnl_direto)
        callback_a = MagicMock()
        callback_b = MagicMock()
        with patch("src.application.coordination_manager.sqlite3.connect", side_effect=criar_mock):
            with patch("src.application.coordination_manager.Path") as mock_path_cls:
                mock_path_inst = MagicMock()
                mock_path_tmp = MagicMock()
                mock_path_inst.with_suffix.return_value = mock_path_tmp
                mock_path_inst.parent = MagicMock()
                mock_path_cls.return_value = mock_path_inst
                manager = CoordinationManager(config=config_valida)
                manager.registrar_callback(callback_a)
                manager.registrar_callback(callback_b)
                decisao = manager.executar_ciclo()
        callback_a.assert_called_once_with(decisao)
        callback_b.assert_called_once_with(decisao)

    def test_excecao_em_callback_nao_interrompe_outros_callbacks(
        self, config_valida: ConfiguracaoCoordinacao, _mock_sqlite_com_trades: Any
    ) -> None:
        """Dado callback A que levanta excecao, callback B deve ser chamado normalmente."""
        pnl_5000 = [-300.0, -300.0, 50.0]
        pnl_direto = [100.0, 50.0, 100.0]
        criar_mock = _mock_sqlite_com_trades(pnl_5000, pnl_direto)
        callback_erro = MagicMock(side_effect=RuntimeError("erro simulado"))
        callback_ok = MagicMock()
        with patch("src.application.coordination_manager.sqlite3.connect", side_effect=criar_mock):
            with patch("src.application.coordination_manager.Path") as mock_path_cls:
                mock_path_inst = MagicMock()
                mock_path_tmp = MagicMock()
                mock_path_inst.with_suffix.return_value = mock_path_tmp
                mock_path_inst.parent = MagicMock()
                mock_path_cls.return_value = mock_path_inst
                manager = CoordinationManager(config=config_valida)
                manager.registrar_callback(callback_erro)
                manager.registrar_callback(callback_ok)
                decisao = manager.executar_ciclo()
        # callback_ok deve ter sido chamado mesmo com callback_erro levantando excecao
        callback_ok.assert_called_once_with(decisao)


# ---------------------------------------------------------------------------
# AC9 - Thread daemon pode ser iniciada e parada
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestThreadDaemon:
    """AC9: Thread daemon do CoordinationManager deve ter ciclo de vida correto."""

    def test_iniciar_ativa_thread_daemon(
        self, config_valida: ConfiguracaoCoordinacao, _mock_sqlite_sem_banco: Any
    ) -> None:
        """Apos iniciar(), thread deve estar ativa e ser daemon."""
        with patch("src.application.coordination_manager.Path") as mock_path_cls:
            mock_path_inst = MagicMock()
            mock_path_tmp = MagicMock()
            mock_path_inst.with_suffix.return_value = mock_path_tmp
            mock_path_inst.parent = MagicMock()
            mock_path_cls.return_value = mock_path_inst
            manager = CoordinationManager(config=config_valida)
            manager.iniciar()
            try:
                assert manager.esta_ativo()
            finally:
                manager.parar()

    def test_parar_encerra_thread_com_sucesso(
        self, config_valida: ConfiguracaoCoordinacao, _mock_sqlite_sem_banco: Any
    ) -> None:
        """Apos parar(), thread deve estar inativa."""
        with patch("src.application.coordination_manager.Path") as mock_path_cls:
            mock_path_inst = MagicMock()
            mock_path_tmp = MagicMock()
            mock_path_inst.with_suffix.return_value = mock_path_tmp
            mock_path_inst.parent = MagicMock()
            mock_path_cls.return_value = mock_path_inst
            manager = CoordinationManager(config=config_valida)
            manager.iniciar()
            manager.parar()
            assert not manager.esta_ativo()

    def test_iniciar_idempotente_segunda_chamada_ignorada(
        self, config_valida: ConfiguracaoCoordinacao, _mock_sqlite_sem_banco: Any
    ) -> None:
        """Chamar iniciar() duas vezes nao deve criar segunda thread."""
        with patch("src.application.coordination_manager.Path") as mock_path_cls:
            mock_path_inst = MagicMock()
            mock_path_tmp = MagicMock()
            mock_path_inst.with_suffix.return_value = mock_path_tmp
            mock_path_inst.parent = MagicMock()
            mock_path_cls.return_value = mock_path_inst
            manager = CoordinationManager(config=config_valida)
            manager.iniciar()
            thread_original = manager._thread
            manager.iniciar()  # segunda chamada deve ser ignorada
            try:
                assert manager._thread is thread_original
            finally:
                manager.parar()

    def test_parar_idempotente_segunda_chamada_ignorada(
        self, config_valida: ConfiguracaoCoordinacao, _mock_sqlite_sem_banco: Any
    ) -> None:
        """Chamar parar() duas vezes nao deve levantar excecao."""
        with patch("src.application.coordination_manager.Path") as mock_path_cls:
            mock_path_inst = MagicMock()
            mock_path_tmp = MagicMock()
            mock_path_inst.with_suffix.return_value = mock_path_tmp
            mock_path_inst.parent = MagicMock()
            mock_path_cls.return_value = mock_path_inst
            manager = CoordinationManager(config=config_valida)
            manager.iniciar()
            manager.parar()
            manager.parar()  # segunda chamada nao deve falhar
            assert not manager.esta_ativo()

    def test_executar_ciclo_funciona_sem_thread_para_testes(
        self, config_valida: ConfiguracaoCoordinacao, _mock_sqlite_sem_banco: Any
    ) -> None:
        """executar_ciclo() deve funcionar diretamente sem iniciar thread daemon."""
        with patch("src.application.coordination_manager.Path") as mock_path_cls:
            mock_path_inst = MagicMock()
            mock_path_tmp = MagicMock()
            mock_path_inst.with_suffix.return_value = mock_path_tmp
            mock_path_inst.parent = MagicMock()
            mock_path_cls.return_value = mock_path_inst
            manager = CoordinationManager(config=config_valida)
            # Sem chamar iniciar()
            decisao = manager.executar_ciclo()
        assert isinstance(decisao, DecisaoCoordinacao)


# ---------------------------------------------------------------------------
# AC10 - Config invalida -> ValueError
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestValidacaoConfiguracao:
    """AC10: Configuracoes invalidas devem levantar ValueError."""

    def test_drawdown_individual_igual_conjunto_levanta_value_error(self) -> None:
        """drawdown_individual_pct == drawdown_conjunto_pct deve levantar ValueError."""
        with pytest.raises(ValueError):
            ConfiguracaoCoordinacao(
                drawdown_individual_pct=10.0,
                drawdown_conjunto_pct=10.0,  # igual -> invalido
                capital_minimo_reais=500.0,
                capital_inicial_sessao_reais=5000.0,
            )

    def test_drawdown_individual_maior_que_conjunto_levanta_value_error(self) -> None:
        """drawdown_individual_pct > drawdown_conjunto_pct deve levantar ValueError."""
        with pytest.raises(ValueError):
            ConfiguracaoCoordinacao(
                drawdown_individual_pct=20.0,
                drawdown_conjunto_pct=15.0,  # individual > conjunto -> invalido
                capital_minimo_reais=500.0,
                capital_inicial_sessao_reais=5000.0,
            )

    def test_drawdown_individual_menor_que_conjunto_eh_valido(self) -> None:
        """drawdown_individual_pct < drawdown_conjunto_pct deve ser valido."""
        config = ConfiguracaoCoordinacao(
            drawdown_individual_pct=10.0,
            drawdown_conjunto_pct=15.0,
            capital_minimo_reais=500.0,
            capital_inicial_sessao_reais=5000.0,
        )
        assert config.drawdown_individual_pct == 10.0

    def test_intervalo_polling_zero_levanta_value_error(self) -> None:
        """intervalo_polling_segundos <= 0 deve levantar ValueError."""
        with pytest.raises(ValueError):
            ConfiguracaoCoordinacao(
                drawdown_individual_pct=10.0,
                drawdown_conjunto_pct=15.0,
                capital_minimo_reais=500.0,
                capital_inicial_sessao_reais=5000.0,
                intervalo_polling_segundos=0.0,  # zero -> invalido
            )

    def test_capital_minimo_maior_que_capital_inicial_levanta_value_error(self) -> None:
        """capital_minimo_reais >= capital_inicial_sessao_reais deve levantar ValueError."""
        with pytest.raises(ValueError):
            ConfiguracaoCoordinacao(
                drawdown_individual_pct=10.0,
                drawdown_conjunto_pct=15.0,
                capital_minimo_reais=6000.0,   # maior que capital_inicial
                capital_inicial_sessao_reais=5000.0,
            )


# ---------------------------------------------------------------------------
# Contrato de DecisaoCoordinacao
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestContratoDecisaoCoordinacao:
    """Contrato estrutural de DecisaoCoordinacao."""

    def test_decisao_possui_ciclo_id_uuid4(
        self, config_valida: ConfiguracaoCoordinacao, _mock_sqlite_sem_banco: Any
    ) -> None:
        """DecisaoCoordinacao.ciclo_id deve ser UUID4 valido."""
        uuid4_regex = re.compile(
            r"^[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$"
        )
        with patch("src.application.coordination_manager.Path") as mock_path_cls:
            mock_path_inst = MagicMock()
            mock_path_tmp = MagicMock()
            mock_path_inst.with_suffix.return_value = mock_path_tmp
            mock_path_inst.parent = MagicMock()
            mock_path_cls.return_value = mock_path_inst
            manager = CoordinationManager(config=config_valida)
            decisao = manager.executar_ciclo()
        assert uuid4_regex.match(decisao.ciclo_id), f"ciclo_id invalido: {decisao.ciclo_id}"

    def test_decisao_possui_timestamp_iso_valido(
        self, config_valida: ConfiguracaoCoordinacao, _mock_sqlite_sem_banco: Any
    ) -> None:
        """DecisaoCoordinacao.timestamp_iso deve ser parseable como ISO 8601."""
        with patch("src.application.coordination_manager.Path") as mock_path_cls:
            mock_path_inst = MagicMock()
            mock_path_tmp = MagicMock()
            mock_path_inst.with_suffix.return_value = mock_path_tmp
            mock_path_inst.parent = MagicMock()
            mock_path_cls.return_value = mock_path_inst
            manager = CoordinationManager(config=config_valida)
            decisao = manager.executar_ciclo()
        # Nao deve levantar excecao
        parsed = datetime.fromisoformat(decisao.timestamp_iso)
        assert parsed is not None

    def test_ciclos_consecutivos_geram_ciclo_ids_distintos(
        self, config_valida: ConfiguracaoCoordinacao, _mock_sqlite_sem_banco: Any
    ) -> None:
        """Dois ciclos consecutivos devem gerar ciclo_ids distintos."""
        with patch("src.application.coordination_manager.Path") as mock_path_cls:
            mock_path_inst = MagicMock()
            mock_path_tmp = MagicMock()
            mock_path_inst.with_suffix.return_value = mock_path_tmp
            mock_path_inst.parent = MagicMock()
            mock_path_cls.return_value = mock_path_inst
            manager = CoordinationManager(config=config_valida)
            decisao_1 = manager.executar_ciclo()
            decisao_2 = manager.executar_ciclo()
        assert decisao_1.ciclo_id != decisao_2.ciclo_id
