"""Testes TDD para CoordinationSignalReader (BLID-042).

Cenarios cobertos:
    T01 - Arquivo ausente -> obter_sinal_atual() retorna NORMAL (ADR-023)
    T02 - Arquivo ausente -> pode_abrir_posicao() retorna True (fallback seguro)
    T03 - Arquivo ausente -> obter_decisao_completa() retorna None
    T04 - JSON malformado -> obter_sinal_atual() retorna NORMAL
    T05 - JSON malformado -> pode_abrir_posicao() retorna True
    T06 - JSON malformado -> obter_decisao_completa() retorna None
    T07 - schema_version ausente -> retorna NORMAL + loga WARNING (ADR-019)
    T08 - schema_version diferente de "1.0" -> retorna NORMAL + loga WARNING
    T09 - Sinal NORMAL -> obter_sinal_atual() retorna CoordinationSignal.NORMAL
    T10 - Sinal NORMAL -> pode_abrir_posicao() retorna True
    T11 - Sinal MODO_CONSERVADOR -> pode_abrir_posicao() retorna True
    T12 - Sinal MODO_DEFENSIVO -> pode_abrir_posicao() retorna True
    T13 - Sinal STOP_OPERACOES -> pode_abrir_posicao() retorna False
    T14 - Sinal STOP_OPERACOES -> obter_sinal_atual() retorna STOP_OPERACOES
    T15 - DecisaoCoordinacao reconstruida com todos os campos corretos
    T16 - ciclo_id deve ser UUID4 valido
    T17 - timestamp_iso deve ser parseable como datetime
    T18 - threshold_violado None preservado corretamente
    T19 - agente_gatilho None preservado corretamente
    T20 - threshold_violado preenchido preservado corretamente
    T21 - agente_gatilho preenchido preservado corretamente
    T22 - Campo sinal invalido no JSON -> obter_sinal_atual() retorna NORMAL
    T23 - Campo sinal invalido -> obter_decisao_completa() retorna None
    T24 - Campo obrigatorio ausente no JSON -> obter_decisao_completa() retorna None
    T25 - sinal_path customizado via construtor
    T26 - Leitura fresca: dois arquivos diferentes produzem sinais diferentes
    T27 - Sinal MODO_CONSERVADOR -> obter_sinal_atual() retorna MODO_CONSERVADOR
    T28 - Sinal MODO_DEFENSIVO -> obter_sinal_atual() retorna MODO_DEFENSIVO
    T29 - Arquivo vazio -> obter_sinal_atual() retorna NORMAL
    T30 - Valores numericos preservados em DecisaoCoordinacao
"""

from __future__ import annotations

import json
import logging
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any

import pytest

from src.application.coordination_manager import (
    CoordinationSignal,
    DecisaoCoordinacao,
)
from src.application.coordination_signal_reader import CoordinationSignalReader


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


def _payload_valido(
    sinal: str = "NORMAL",
    threshold_violado: Any = None,
    agente_gatilho: Any = None,
) -> dict[str, Any]:
    """Retorna payload JSON valido conforme schema_version 1.0."""
    return {
        "schema_version": "1.0",
        "ciclo_id": str(uuid.uuid4()),
        "timestamp_iso": datetime.utcnow().isoformat(),
        "sinal": sinal,
        "drawdown_rl_5000_pct": 3.5,
        "drawdown_rl_direto_pct": 2.1,
        "drawdown_conjunto_pct": 4.8,
        "capital_estimado_reais": 4800.0,
        "threshold_violado": threshold_violado,
        "agente_gatilho": agente_gatilho,
        "total_trades_rl_5000": 5,
        "total_trades_rl_direto": 3,
    }


def _escrever_json(path: Path, conteudo: dict[str, Any]) -> None:
    """Escreve dicionario como JSON no arquivo especificado."""
    path.write_text(json.dumps(conteudo), encoding="utf-8")


# ---------------------------------------------------------------------------
# T01-T03: Arquivo ausente
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_t01_arquivo_ausente_obter_sinal_retorna_normal(tmp_path: Path) -> None:
    """T01: Arquivo ausente -> obter_sinal_atual() retorna NORMAL (ADR-023)."""
    reader = CoordinationSignalReader(
        sinal_path=str(tmp_path / "inexistente.json")
    )
    assert reader.obter_sinal_atual() == CoordinationSignal.NORMAL


@pytest.mark.unit
def test_t02_arquivo_ausente_pode_abrir_posicao_true(tmp_path: Path) -> None:
    """T02: Arquivo ausente -> pode_abrir_posicao() retorna True (fallback seguro)."""
    reader = CoordinationSignalReader(
        sinal_path=str(tmp_path / "inexistente.json")
    )
    assert reader.pode_abrir_posicao() is True


@pytest.mark.unit
def test_t03_arquivo_ausente_decisao_completa_none(tmp_path: Path) -> None:
    """T03: Arquivo ausente -> obter_decisao_completa() retorna None."""
    reader = CoordinationSignalReader(
        sinal_path=str(tmp_path / "inexistente.json")
    )
    assert reader.obter_decisao_completa() is None


# ---------------------------------------------------------------------------
# T04-T06: JSON malformado
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_t04_json_malformado_obter_sinal_retorna_normal(tmp_path: Path) -> None:
    """T04: JSON malformado -> obter_sinal_atual() retorna NORMAL."""
    sinal_file = tmp_path / "sinal.json"
    sinal_file.write_text("nao_e_json{{{", encoding="utf-8")

    reader = CoordinationSignalReader(sinal_path=str(sinal_file))
    assert reader.obter_sinal_atual() == CoordinationSignal.NORMAL


@pytest.mark.unit
def test_t05_json_malformado_pode_abrir_posicao_true(tmp_path: Path) -> None:
    """T05: JSON malformado -> pode_abrir_posicao() retorna True."""
    sinal_file = tmp_path / "sinal.json"
    sinal_file.write_text("{invalido", encoding="utf-8")

    reader = CoordinationSignalReader(sinal_path=str(sinal_file))
    assert reader.pode_abrir_posicao() is True


@pytest.mark.unit
def test_t06_json_malformado_decisao_completa_none(tmp_path: Path) -> None:
    """T06: JSON malformado -> obter_decisao_completa() retorna None."""
    sinal_file = tmp_path / "sinal.json"
    sinal_file.write_text("[[[[", encoding="utf-8")

    reader = CoordinationSignalReader(sinal_path=str(sinal_file))
    assert reader.obter_decisao_completa() is None


# ---------------------------------------------------------------------------
# T07-T08: schema_version invalida
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_t07_schema_version_ausente_retorna_normal_com_warning(
    tmp_path: Path, caplog: pytest.LogCaptureFixture
) -> None:
    """T07: schema_version ausente -> retorna NORMAL + loga WARNING (ADR-019)."""
    sinal_file = tmp_path / "sinal.json"
    payload = _payload_valido()
    del payload["schema_version"]
    _escrever_json(sinal_file, payload)

    reader = CoordinationSignalReader(sinal_path=str(sinal_file))
    with caplog.at_level(logging.WARNING):
        sinal = reader.obter_sinal_atual()

    assert sinal == CoordinationSignal.NORMAL
    assert "schema_version" in caplog.text


@pytest.mark.unit
def test_t08_schema_version_diferente_retorna_normal_com_warning(
    tmp_path: Path, caplog: pytest.LogCaptureFixture
) -> None:
    """T08: schema_version diferente de '1.0' -> retorna NORMAL + loga WARNING."""
    sinal_file = tmp_path / "sinal.json"
    payload = _payload_valido()
    payload["schema_version"] = "2.0"
    _escrever_json(sinal_file, payload)

    reader = CoordinationSignalReader(sinal_path=str(sinal_file))
    with caplog.at_level(logging.WARNING):
        sinal = reader.obter_sinal_atual()

    assert sinal == CoordinationSignal.NORMAL
    assert "schema_version" in caplog.text


# ---------------------------------------------------------------------------
# T09-T14: Sinais validos e pode_abrir_posicao
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_t09_sinal_normal_obter_sinal_atual(tmp_path: Path) -> None:
    """T09: Sinal NORMAL -> obter_sinal_atual() retorna CoordinationSignal.NORMAL."""
    sinal_file = tmp_path / "sinal.json"
    _escrever_json(sinal_file, _payload_valido(sinal="NORMAL"))

    reader = CoordinationSignalReader(sinal_path=str(sinal_file))
    assert reader.obter_sinal_atual() == CoordinationSignal.NORMAL


@pytest.mark.unit
def test_t10_sinal_normal_pode_abrir_posicao_true(tmp_path: Path) -> None:
    """T10: Sinal NORMAL -> pode_abrir_posicao() retorna True."""
    sinal_file = tmp_path / "sinal.json"
    _escrever_json(sinal_file, _payload_valido(sinal="NORMAL"))

    reader = CoordinationSignalReader(sinal_path=str(sinal_file))
    assert reader.pode_abrir_posicao() is True


@pytest.mark.unit
def test_t11_sinal_modo_conservador_pode_abrir_posicao_true(tmp_path: Path) -> None:
    """T11: Sinal MODO_CONSERVADOR -> pode_abrir_posicao() retorna True (nao bloqueia)."""
    sinal_file = tmp_path / "sinal.json"
    _escrever_json(sinal_file, _payload_valido(sinal="MODO_CONSERVADOR"))

    reader = CoordinationSignalReader(sinal_path=str(sinal_file))
    assert reader.pode_abrir_posicao() is True


@pytest.mark.unit
def test_t12_sinal_modo_defensivo_pode_abrir_posicao_true(tmp_path: Path) -> None:
    """T12: Sinal MODO_DEFENSIVO -> pode_abrir_posicao() retorna True (nao bloqueia)."""
    sinal_file = tmp_path / "sinal.json"
    _escrever_json(sinal_file, _payload_valido(sinal="MODO_DEFENSIVO"))

    reader = CoordinationSignalReader(sinal_path=str(sinal_file))
    assert reader.pode_abrir_posicao() is True


@pytest.mark.unit
def test_t13_sinal_stop_operacoes_pode_abrir_posicao_false(tmp_path: Path) -> None:
    """T13: Sinal STOP_OPERACOES -> pode_abrir_posicao() retorna False (bloqueia)."""
    sinal_file = tmp_path / "sinal.json"
    _escrever_json(sinal_file, _payload_valido(sinal="STOP_OPERACOES"))

    reader = CoordinationSignalReader(sinal_path=str(sinal_file))
    assert reader.pode_abrir_posicao() is False


@pytest.mark.unit
def test_t14_sinal_stop_operacoes_obter_sinal_atual(tmp_path: Path) -> None:
    """T14: Sinal STOP_OPERACOES -> obter_sinal_atual() retorna STOP_OPERACOES."""
    sinal_file = tmp_path / "sinal.json"
    _escrever_json(sinal_file, _payload_valido(sinal="STOP_OPERACOES"))

    reader = CoordinationSignalReader(sinal_path=str(sinal_file))
    assert reader.obter_sinal_atual() == CoordinationSignal.STOP_OPERACOES


# ---------------------------------------------------------------------------
# T15-T17: DecisaoCoordinacao reconstruida
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_t15_decisao_completa_campos_corretos(tmp_path: Path) -> None:
    """T15: DecisaoCoordinacao reconstruida com todos os campos corretos."""
    ciclo_id = str(uuid.uuid4())
    ts = datetime.utcnow().isoformat()
    sinal_file = tmp_path / "sinal.json"
    payload: dict[str, Any] = {
        "schema_version": "1.0",
        "ciclo_id": ciclo_id,
        "timestamp_iso": ts,
        "sinal": "NORMAL",
        "drawdown_rl_5000_pct": 1.5,
        "drawdown_rl_direto_pct": 2.3,
        "drawdown_conjunto_pct": 3.8,
        "capital_estimado_reais": 4950.0,
        "threshold_violado": None,
        "agente_gatilho": None,
        "total_trades_rl_5000": 7,
        "total_trades_rl_direto": 4,
    }
    _escrever_json(sinal_file, payload)

    reader = CoordinationSignalReader(sinal_path=str(sinal_file))
    decisao = reader.obter_decisao_completa()

    assert decisao is not None
    assert decisao.ciclo_id == ciclo_id
    assert decisao.timestamp_iso == ts
    assert decisao.sinal == CoordinationSignal.NORMAL
    assert decisao.drawdown_rl_5000_pct == pytest.approx(1.5)
    assert decisao.drawdown_rl_direto_pct == pytest.approx(2.3)
    assert decisao.drawdown_conjunto_pct == pytest.approx(3.8)
    assert decisao.capital_estimado_reais == pytest.approx(4950.0)
    assert decisao.threshold_violado is None
    assert decisao.agente_gatilho is None
    assert decisao.total_trades_rl_5000 == 7
    assert decisao.total_trades_rl_direto == 4


@pytest.mark.unit
def test_t16_ciclo_id_uuid4_valido(tmp_path: Path) -> None:
    """T16: ciclo_id do payload deve ser UUID4 valido."""
    sinal_file = tmp_path / "sinal.json"
    _escrever_json(sinal_file, _payload_valido())

    reader = CoordinationSignalReader(sinal_path=str(sinal_file))
    decisao = reader.obter_decisao_completa()

    assert decisao is not None
    parsed = uuid.UUID(decisao.ciclo_id, version=4)
    assert str(parsed) == decisao.ciclo_id


@pytest.mark.unit
def test_t17_timestamp_iso_parseable(tmp_path: Path) -> None:
    """T17: timestamp_iso deve ser parseable como datetime ISO 8601."""
    sinal_file = tmp_path / "sinal.json"
    _escrever_json(sinal_file, _payload_valido())

    reader = CoordinationSignalReader(sinal_path=str(sinal_file))
    decisao = reader.obter_decisao_completa()

    assert decisao is not None
    parsed_dt = datetime.fromisoformat(decisao.timestamp_iso)
    assert isinstance(parsed_dt, datetime)


# ---------------------------------------------------------------------------
# T18-T21: threshold_violado e agente_gatilho
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_t18_threshold_violado_none_preservado(tmp_path: Path) -> None:
    """T18: threshold_violado None preservado corretamente."""
    sinal_file = tmp_path / "sinal.json"
    _escrever_json(sinal_file, _payload_valido(threshold_violado=None))

    reader = CoordinationSignalReader(sinal_path=str(sinal_file))
    decisao = reader.obter_decisao_completa()

    assert decisao is not None
    assert decisao.threshold_violado is None


@pytest.mark.unit
def test_t19_agente_gatilho_none_preservado(tmp_path: Path) -> None:
    """T19: agente_gatilho None preservado corretamente."""
    sinal_file = tmp_path / "sinal.json"
    _escrever_json(sinal_file, _payload_valido(agente_gatilho=None))

    reader = CoordinationSignalReader(sinal_path=str(sinal_file))
    decisao = reader.obter_decisao_completa()

    assert decisao is not None
    assert decisao.agente_gatilho is None


@pytest.mark.unit
def test_t20_threshold_violado_preenchido(tmp_path: Path) -> None:
    """T20: threshold_violado preenchido preservado corretamente."""
    sinal_file = tmp_path / "sinal.json"
    _escrever_json(
        sinal_file,
        _payload_valido(
            sinal="MODO_CONSERVADOR",
            threshold_violado="drawdown_individual",
            agente_gatilho="rl_5000",
        ),
    )

    reader = CoordinationSignalReader(sinal_path=str(sinal_file))
    decisao = reader.obter_decisao_completa()

    assert decisao is not None
    assert decisao.threshold_violado == "drawdown_individual"


@pytest.mark.unit
def test_t21_agente_gatilho_preenchido(tmp_path: Path) -> None:
    """T21: agente_gatilho preenchido preservado corretamente."""
    sinal_file = tmp_path / "sinal.json"
    _escrever_json(
        sinal_file,
        _payload_valido(
            sinal="MODO_CONSERVADOR",
            threshold_violado="drawdown_individual",
            agente_gatilho="rl_direto",
        ),
    )

    reader = CoordinationSignalReader(sinal_path=str(sinal_file))
    decisao = reader.obter_decisao_completa()

    assert decisao is not None
    assert decisao.agente_gatilho == "rl_direto"


# ---------------------------------------------------------------------------
# T22-T24: Campos invalidos
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_t22_sinal_invalido_obter_sinal_retorna_normal(
    tmp_path: Path, caplog: pytest.LogCaptureFixture
) -> None:
    """T22: Campo sinal invalido no JSON -> obter_sinal_atual() retorna NORMAL."""
    sinal_file = tmp_path / "sinal.json"
    payload = _payload_valido()
    payload["sinal"] = "SINAL_INEXISTENTE"
    _escrever_json(sinal_file, payload)

    reader = CoordinationSignalReader(sinal_path=str(sinal_file))
    with caplog.at_level(logging.WARNING):
        sinal = reader.obter_sinal_atual()

    assert sinal == CoordinationSignal.NORMAL


@pytest.mark.unit
def test_t23_sinal_invalido_decisao_completa_none(tmp_path: Path) -> None:
    """T23: Campo sinal invalido -> obter_decisao_completa() retorna None."""
    sinal_file = tmp_path / "sinal.json"
    payload = _payload_valido()
    payload["sinal"] = "SINAL_INVALIDO_XYZ"
    _escrever_json(sinal_file, payload)

    reader = CoordinationSignalReader(sinal_path=str(sinal_file))
    assert reader.obter_decisao_completa() is None


@pytest.mark.unit
def test_t24_campo_obrigatorio_ausente_decisao_none(tmp_path: Path) -> None:
    """T24: Campo obrigatorio ausente no JSON -> obter_decisao_completa() retorna None."""
    sinal_file = tmp_path / "sinal.json"
    payload = _payload_valido()
    del payload["drawdown_rl_5000_pct"]
    _escrever_json(sinal_file, payload)

    reader = CoordinationSignalReader(sinal_path=str(sinal_file))
    assert reader.obter_decisao_completa() is None


# ---------------------------------------------------------------------------
# T25-T26: Comportamento do construtor e leitura fresca
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_t25_sinal_path_customizado(tmp_path: Path) -> None:
    """T25: sinal_path customizado via construtor e respeitado."""
    sinal_file = tmp_path / "subdir" / "meu_sinal.json"
    sinal_file.parent.mkdir(parents=True)
    _escrever_json(sinal_file, _payload_valido(sinal="STOP_OPERACOES"))

    reader = CoordinationSignalReader(sinal_path=str(sinal_file))
    assert reader.obter_sinal_atual() == CoordinationSignal.STOP_OPERACOES
    assert reader.pode_abrir_posicao() is False


@pytest.mark.unit
def test_t26_leitura_fresca_dois_arquivos_diferentes(tmp_path: Path) -> None:
    """T26: Leitura fresca — dois arquivos com sinais diferentes produzem resultados corretos."""
    arquivo_normal = tmp_path / "normal.json"
    arquivo_stop = tmp_path / "stop.json"
    _escrever_json(arquivo_normal, _payload_valido(sinal="NORMAL"))
    _escrever_json(arquivo_stop, _payload_valido(sinal="STOP_OPERACOES"))

    reader_normal = CoordinationSignalReader(sinal_path=str(arquivo_normal))
    reader_stop = CoordinationSignalReader(sinal_path=str(arquivo_stop))

    assert reader_normal.obter_sinal_atual() == CoordinationSignal.NORMAL
    assert reader_stop.obter_sinal_atual() == CoordinationSignal.STOP_OPERACOES


# ---------------------------------------------------------------------------
# T27-T28: Sinais intermediarios
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_t27_sinal_modo_conservador_obter_sinal_atual(tmp_path: Path) -> None:
    """T27: Sinal MODO_CONSERVADOR -> obter_sinal_atual() retorna MODO_CONSERVADOR."""
    sinal_file = tmp_path / "sinal.json"
    _escrever_json(sinal_file, _payload_valido(sinal="MODO_CONSERVADOR"))

    reader = CoordinationSignalReader(sinal_path=str(sinal_file))
    assert reader.obter_sinal_atual() == CoordinationSignal.MODO_CONSERVADOR


@pytest.mark.unit
def test_t28_sinal_modo_defensivo_obter_sinal_atual(tmp_path: Path) -> None:
    """T28: Sinal MODO_DEFENSIVO -> obter_sinal_atual() retorna MODO_DEFENSIVO."""
    sinal_file = tmp_path / "sinal.json"
    _escrever_json(sinal_file, _payload_valido(sinal="MODO_DEFENSIVO"))

    reader = CoordinationSignalReader(sinal_path=str(sinal_file))
    assert reader.obter_sinal_atual() == CoordinationSignal.MODO_DEFENSIVO


# ---------------------------------------------------------------------------
# T29-T30: Arquivo vazio e valores numericos
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_t29_arquivo_vazio_retorna_normal(tmp_path: Path) -> None:
    """T29: Arquivo vazio (0 bytes) -> obter_sinal_atual() retorna NORMAL."""
    sinal_file = tmp_path / "sinal.json"
    sinal_file.write_text("", encoding="utf-8")

    reader = CoordinationSignalReader(sinal_path=str(sinal_file))
    assert reader.obter_sinal_atual() == CoordinationSignal.NORMAL


@pytest.mark.unit
def test_t30_valores_numericos_preservados(tmp_path: Path) -> None:
    """T30: Valores numericos de drawdown e capital preservados com precisao."""
    sinal_file = tmp_path / "sinal.json"
    payload: dict[str, Any] = {
        "schema_version": "1.0",
        "ciclo_id": str(uuid.uuid4()),
        "timestamp_iso": datetime.utcnow().isoformat(),
        "sinal": "MODO_DEFENSIVO",
        "drawdown_rl_5000_pct": 11.25,
        "drawdown_rl_direto_pct": 8.75,
        "drawdown_conjunto_pct": 16.33,
        "capital_estimado_reais": 3456.78,
        "threshold_violado": "drawdown_conjunto",
        "agente_gatilho": None,
        "total_trades_rl_5000": 12,
        "total_trades_rl_direto": 9,
    }
    _escrever_json(sinal_file, payload)

    reader = CoordinationSignalReader(sinal_path=str(sinal_file))
    decisao = reader.obter_decisao_completa()

    assert decisao is not None
    assert decisao.sinal == CoordinationSignal.MODO_DEFENSIVO
    assert decisao.drawdown_rl_5000_pct == pytest.approx(11.25)
    assert decisao.drawdown_rl_direto_pct == pytest.approx(8.75)
    assert decisao.drawdown_conjunto_pct == pytest.approx(16.33)
    assert decisao.capital_estimado_reais == pytest.approx(3456.78)
    assert decisao.threshold_violado == "drawdown_conjunto"
    assert decisao.total_trades_rl_5000 == 12
    assert decisao.total_trades_rl_direto == 9
