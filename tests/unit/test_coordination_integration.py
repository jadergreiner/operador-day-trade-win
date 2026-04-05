"""Testes de integracao do CoordinationSignalReader nos agentes RL (BLID-043).

Testa o modulo ``src.application.coordination_integration`` que encapsula a
verificacao de sinal de coordenacao. Os scripts dos agentes delegam para este
modulo, permitindo testes sem dependencias pesadas (MT5, SQLAlchemy, pandas).

Cenarios cobertos:
    T01 - STOP_OPERACOES -> verificar_pode_abrir_posicao() retorna False
    T02 - NORMAL -> verificar_pode_abrir_posicao() retorna True
    T03 - MODO_CONSERVADOR -> verificar_pode_abrir_posicao() retorna True
    T04 - MODO_DEFENSIVO -> verificar_pode_abrir_posicao() retorna True
    T05 - STOP_OPERACOES -> log WARNING emitido com prefixo [COORDINATION]
    T06 - NORMAL -> sem log WARNING de coordination
    T07 - MODO_CONSERVADOR -> sem log WARNING de coordination
    T08 - MODO_DEFENSIVO -> sem log WARNING de coordination
    T09 - Log WARNING contem o valor do sinal (STOP_OPERACOES)
    T10 - reader injetavel: MagicMock e aceito como parametro (AC5)
    T11 - reader injetavel: False com mock retornando pode_abrir=False (AC5)
    T12 - reader injetavel: True com mock retornando pode_abrir=True (AC5)
    T13 - Fallback: arquivo ausente -> pode_abrir_posicao True (ADR-023)
    T14 - Fallback: JSON malformado -> pode_abrir_posicao True (ADR-023)
    T15 - _reader_padrao modulo-level e CoordinationSignalReader
    T16 - Multiplas chamadas com STOP_OPERACOES -> todas retornam False
    T17 - Multiplas chamadas com NORMAL -> todas retornam True
    T18 - Leitura fresca: muda sinal entre chamadas
    T19 - reader injetavel: mock.pode_abrir_posicao chamado exatamente uma vez
    T20 - reader injetavel: mock.obter_sinal_atual chamado quando bloqueado
"""

from __future__ import annotations

import json
import logging
from pathlib import Path
from unittest.mock import MagicMock, call

import pytest

from src.application.coordination_manager import CoordinationSignal
from src.application.coordination_signal_reader import CoordinationSignalReader
import src.application.coordination_integration as ci_mod
from src.application.coordination_integration import verificar_pode_abrir_posicao


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _criar_reader_com_sinal(
    sinal: CoordinationSignal, tmp_path: Path
) -> CoordinationSignalReader:
    """Cria CoordinationSignalReader apontando para arquivo temporario."""
    arquivo = tmp_path / "sinal_test.json"
    payload = {
        "schema_version": "1.0",
        "sinal": sinal.value,
        "ciclo_id": "00000000-0000-0000-0000-000000000001",
        "timestamp_iso": "2026-04-06T10:00:00",
        "drawdown_rl_5000_pct": 0.0,
        "drawdown_rl_direto_pct": 0.0,
        "drawdown_conjunto_pct": 0.0,
        "capital_estimado_reais": 10000.0,
        "threshold_violado": None,
        "agente_gatilho": None,
        "total_trades_rl_5000": 0,
        "total_trades_rl_direto": 0,
    }
    arquivo.write_text(json.dumps(payload), encoding="utf-8")
    return CoordinationSignalReader(sinal_path=str(arquivo))


# ---------------------------------------------------------------------------
# T01-T04: Retorno booleano por sinal
# ---------------------------------------------------------------------------


class TestRetornoBooleano:
    """Verifica retorno bool para cada sinal possivel."""

    def test_T01_stop_operacoes_retorna_false(self, tmp_path: Path) -> None:
        """T01 - STOP_OPERACOES -> False (bloqueia abertura)."""
        reader = _criar_reader_com_sinal(CoordinationSignal.STOP_OPERACOES, tmp_path)
        assert verificar_pode_abrir_posicao(reader=reader) is False

    def test_T02_normal_retorna_true(self, tmp_path: Path) -> None:
        """T02 - NORMAL -> True (permite abertura)."""
        reader = _criar_reader_com_sinal(CoordinationSignal.NORMAL, tmp_path)
        assert verificar_pode_abrir_posicao(reader=reader) is True

    def test_T03_modo_conservador_retorna_true(self, tmp_path: Path) -> None:
        """T03 - MODO_CONSERVADOR -> True (nao bloqueia)."""
        reader = _criar_reader_com_sinal(CoordinationSignal.MODO_CONSERVADOR, tmp_path)
        assert verificar_pode_abrir_posicao(reader=reader) is True

    def test_T04_modo_defensivo_retorna_true(self, tmp_path: Path) -> None:
        """T04 - MODO_DEFENSIVO -> True (nao bloqueia)."""
        reader = _criar_reader_com_sinal(CoordinationSignal.MODO_DEFENSIVO, tmp_path)
        assert verificar_pode_abrir_posicao(reader=reader) is True


# ---------------------------------------------------------------------------
# T05-T09: Log WARNING
# ---------------------------------------------------------------------------


class TestLogWarning:
    """Verifica emissao de log WARNING quando bloqueado."""

    def test_T05_stop_operacoes_emite_log_warning(
        self, tmp_path: Path, caplog: pytest.LogCaptureFixture
    ) -> None:
        """T05 - STOP_OPERACOES -> log WARNING com prefixo [COORDINATION] emitido."""
        reader = _criar_reader_com_sinal(CoordinationSignal.STOP_OPERACOES, tmp_path)
        with caplog.at_level(logging.WARNING):
            verificar_pode_abrir_posicao(reader=reader)
        assert any("[COORDINATION]" in m for m in caplog.messages)

    def test_T06_normal_nao_emite_log_warning(
        self, tmp_path: Path, caplog: pytest.LogCaptureFixture
    ) -> None:
        """T06 - NORMAL -> nenhum log WARNING de coordination."""
        reader = _criar_reader_com_sinal(CoordinationSignal.NORMAL, tmp_path)
        with caplog.at_level(logging.WARNING):
            verificar_pode_abrir_posicao(reader=reader)
        assert not any("[COORDINATION]" in m for m in caplog.messages)

    def test_T07_modo_conservador_nao_emite_log_warning(
        self, tmp_path: Path, caplog: pytest.LogCaptureFixture
    ) -> None:
        """T07 - MODO_CONSERVADOR -> nenhum log WARNING de coordination."""
        reader = _criar_reader_com_sinal(CoordinationSignal.MODO_CONSERVADOR, tmp_path)
        with caplog.at_level(logging.WARNING):
            verificar_pode_abrir_posicao(reader=reader)
        assert not any("[COORDINATION]" in m for m in caplog.messages)

    def test_T08_modo_defensivo_nao_emite_log_warning(
        self, tmp_path: Path, caplog: pytest.LogCaptureFixture
    ) -> None:
        """T08 - MODO_DEFENSIVO -> nenhum log WARNING de coordination."""
        reader = _criar_reader_com_sinal(CoordinationSignal.MODO_DEFENSIVO, tmp_path)
        with caplog.at_level(logging.WARNING):
            verificar_pode_abrir_posicao(reader=reader)
        assert not any("[COORDINATION]" in m for m in caplog.messages)

    def test_T09_log_warning_contem_valor_sinal(
        self, tmp_path: Path, caplog: pytest.LogCaptureFixture
    ) -> None:
        """T09 - Log WARNING contem o valor do sinal STOP_OPERACOES."""
        reader = _criar_reader_com_sinal(CoordinationSignal.STOP_OPERACOES, tmp_path)
        with caplog.at_level(logging.WARNING):
            verificar_pode_abrir_posicao(reader=reader)
        coordination_msgs = [m for m in caplog.messages if "[COORDINATION]" in m]
        assert len(coordination_msgs) >= 1
        assert CoordinationSignal.STOP_OPERACOES.value in coordination_msgs[0]


# ---------------------------------------------------------------------------
# T10-T12: Injetabilidade (AC5)
# ---------------------------------------------------------------------------


class TestInjetabilidade:
    """Testa injetabilidade do reader externo (AC5)."""

    def test_T10_mock_pode_abrir_true_aceito(self) -> None:
        """T10 - reader injetavel: MagicMock com pode_abrir=True e aceito."""
        mock_reader = MagicMock(spec=CoordinationSignalReader)
        mock_reader.pode_abrir_posicao.return_value = True
        resultado = verificar_pode_abrir_posicao(reader=mock_reader)
        assert resultado is True

    def test_T11_mock_pode_abrir_false_retorna_false(self) -> None:
        """T11 - reader injetavel: mock retornando pode_abrir=False -> False (AC5)."""
        mock_reader = MagicMock(spec=CoordinationSignalReader)
        mock_reader.pode_abrir_posicao.return_value = False
        mock_reader.obter_sinal_atual.return_value = CoordinationSignal.STOP_OPERACOES
        resultado = verificar_pode_abrir_posicao(reader=mock_reader)
        assert resultado is False

    def test_T12_mock_pode_abrir_true_retorna_true(self) -> None:
        """T12 - reader injetavel: mock retornando pode_abrir=True -> True (AC5)."""
        mock_reader = MagicMock(spec=CoordinationSignalReader)
        mock_reader.pode_abrir_posicao.return_value = True
        resultado = verificar_pode_abrir_posicao(reader=mock_reader)
        assert resultado is True


# ---------------------------------------------------------------------------
# T13-T14: Fallback (ADR-023)
# ---------------------------------------------------------------------------


class TestFallback:
    """Testa fallback seguro quando arquivo ausente ou invalido (ADR-023)."""

    def test_T13_arquivo_ausente_permite_abertura(self, tmp_path: Path) -> None:
        """T13 - Arquivo ausente -> True (ADR-023 fallback seguro)."""
        reader = CoordinationSignalReader(
            sinal_path=str(tmp_path / "inexistente.json")
        )
        assert verificar_pode_abrir_posicao(reader=reader) is True

    def test_T14_json_malformado_permite_abertura(self, tmp_path: Path) -> None:
        """T14 - JSON malformado -> True (ADR-023 fallback seguro)."""
        arquivo = tmp_path / "malformado.json"
        arquivo.write_text("{ nao_e_json: abc", encoding="utf-8")
        reader = CoordinationSignalReader(sinal_path=str(arquivo))
        assert verificar_pode_abrir_posicao(reader=reader) is True


# ---------------------------------------------------------------------------
# T15: Modulo-level reader
# ---------------------------------------------------------------------------


class TestModuleLevelReader:
    """Testa existencia e tipo do reader padrao modulo-level."""

    def test_T15_reader_padrao_e_coordination_signal_reader(self) -> None:
        """T15 - _reader_padrao e instancia de CoordinationSignalReader."""
        assert isinstance(ci_mod._reader_padrao, CoordinationSignalReader)


# ---------------------------------------------------------------------------
# T16-T17: Multiplas chamadas
# ---------------------------------------------------------------------------


class TestMultiplasChamadas:
    """Testa consistencia em multiplas chamadas."""

    def test_T16_stop_operacoes_multiplas_chamadas_sempre_false(
        self, tmp_path: Path
    ) -> None:
        """T16 - Multiplas chamadas com STOP_OPERACOES -> sempre False."""
        reader = _criar_reader_com_sinal(CoordinationSignal.STOP_OPERACOES, tmp_path)
        resultados = [verificar_pode_abrir_posicao(reader=reader) for _ in range(3)]
        assert all(r is False for r in resultados)

    def test_T17_normal_multiplas_chamadas_sempre_true(
        self, tmp_path: Path
    ) -> None:
        """T17 - Multiplas chamadas com NORMAL -> sempre True."""
        reader = _criar_reader_com_sinal(CoordinationSignal.NORMAL, tmp_path)
        resultados = [verificar_pode_abrir_posicao(reader=reader) for _ in range(3)]
        assert all(r is True for r in resultados)


# ---------------------------------------------------------------------------
# T18: Leitura fresca
# ---------------------------------------------------------------------------


class TestLeituraFresca:
    """Testa que cada chamada faz leitura fresca do sinal."""

    def test_T18_muda_sinal_entre_chamadas(self, tmp_path: Path) -> None:
        """T18 - Leitura fresca: mudar arquivo muda resultado na proxima chamada."""
        arquivo = tmp_path / "sinal.json"

        # Primeiro: NORMAL
        payload_normal = {
            "schema_version": "1.0",
            "sinal": CoordinationSignal.NORMAL.value,
            "ciclo_id": "00000000-0000-0000-0000-000000000001",
            "timestamp_iso": "2026-04-06T10:00:00",
            "drawdown_rl_5000_pct": 0.0,
            "drawdown_rl_direto_pct": 0.0,
            "drawdown_conjunto_pct": 0.0,
            "capital_estimado_reais": 10000.0,
            "threshold_violado": None,
            "agente_gatilho": None,
            "total_trades_rl_5000": 0,
            "total_trades_rl_direto": 0,
        }
        arquivo.write_text(json.dumps(payload_normal), encoding="utf-8")
        reader = CoordinationSignalReader(sinal_path=str(arquivo))
        assert verificar_pode_abrir_posicao(reader=reader) is True

        # Agora: STOP_OPERACOES
        payload_stop = dict(payload_normal)
        payload_stop["sinal"] = CoordinationSignal.STOP_OPERACOES.value
        arquivo.write_text(json.dumps(payload_stop), encoding="utf-8")
        assert verificar_pode_abrir_posicao(reader=reader) is False


# ---------------------------------------------------------------------------
# T19-T20: Chamadas ao mock
# ---------------------------------------------------------------------------


class TestChamadasMock:
    """Testa quantidade de chamadas ao mock reader."""

    def test_T19_pode_abrir_posicao_chamado_uma_vez_true(self) -> None:
        """T19 - pode_abrir_posicao chamado exatamente uma vez quando True."""
        mock_reader = MagicMock(spec=CoordinationSignalReader)
        mock_reader.pode_abrir_posicao.return_value = True
        verificar_pode_abrir_posicao(reader=mock_reader)
        mock_reader.pode_abrir_posicao.assert_called_once()

    def test_T20_obter_sinal_atual_chamado_quando_bloqueado(self) -> None:
        """T20 - obter_sinal_atual chamado quando pode_abrir=False."""
        mock_reader = MagicMock(spec=CoordinationSignalReader)
        mock_reader.pode_abrir_posicao.return_value = False
        mock_reader.obter_sinal_atual.return_value = CoordinationSignal.STOP_OPERACOES
        verificar_pode_abrir_posicao(reader=mock_reader)
        mock_reader.obter_sinal_atual.assert_called_once()

