"""
Testes para JsonFechamentoRepository.

Grupo 3 da estrategia TDD — ROADMAP-MICRO-03.

Testa:
- Persistencia de resultado WIN no JSON
- Persistencia de resultado LOSS no JSON
- Rejeicao de valor invalido
"""

import json
import pytest
from pathlib import Path

from src.infrastructure.repositories.fechamento_repository import (
    JsonFechamentoRepository,
    IFechamentoRepository,
)


@pytest.fixture
def repo_com_registro(tmp_path: Path) -> JsonFechamentoRepository:
    """Repositorio com um fechamento pre-existente sem resultado."""
    repo = JsonFechamentoRepository(agent_id="agente_5000", data_dir=tmp_path)
    arquivo = tmp_path / "historico_fechamentos_agente_5000.json"
    registro = [
        {
            "ticket": 1001,
            "agent_id": "agente_5000",
            "magic_number": 234500,
            "resultado": None,
            "pnl_reais": 25.0,
            "pnl_pct": 0.42,
        }
    ]
    arquivo.write_text(json.dumps(registro, ensure_ascii=False), encoding="utf-8")
    return repo


def test_atualizar_resultado_persiste_win_no_sqlite(repo_com_registro: JsonFechamentoRepository, tmp_path: Path):
    """Resultado WIN deve ser persistido corretamente no JSON."""
    sucesso = repo_com_registro.atualizar_resultado_fechamento(
        ticket=1001, resultado="WIN", pnl=25.0
    )

    assert sucesso is True

    arquivo = tmp_path / "historico_fechamentos_agente_5000.json"
    dados = json.loads(arquivo.read_text(encoding="utf-8"))
    assert dados[0]["resultado"] == "WIN"


def test_atualizar_resultado_persiste_loss_no_sqlite(repo_com_registro: JsonFechamentoRepository, tmp_path: Path):
    """Resultado LOSS deve ser persistido corretamente no JSON."""
    sucesso = repo_com_registro.atualizar_resultado_fechamento(
        ticket=1001, resultado="LOSS", pnl=-15.0
    )

    assert sucesso is True

    arquivo = tmp_path / "historico_fechamentos_agente_5000.json"
    dados = json.loads(arquivo.read_text(encoding="utf-8"))
    assert dados[0]["resultado"] == "LOSS"


def test_atualizar_resultado_rejeita_valor_invalido(tmp_path: Path):
    """Deve lancar ValueError para resultado fora do vocabulario."""
    repo = JsonFechamentoRepository(agent_id="agente_5000", data_dir=tmp_path)

    with pytest.raises(ValueError, match="resultado invalido"):
        repo.atualizar_resultado_fechamento(ticket=1001, resultado="UNKNOWN", pnl=0.0)


def test_atualizar_resultado_retorna_false_ticket_inexistente(tmp_path: Path):
    """Deve retornar False quando ticket nao existe no JSON."""
    repo = JsonFechamentoRepository(agent_id="agente_5000", data_dir=tmp_path)

    sucesso = repo.atualizar_resultado_fechamento(ticket=9999, resultado="WIN", pnl=0.0)

    assert sucesso is False


def test_listar_sem_resultado_filtra_pelo_magic_number(tmp_path: Path):
    """listar_sem_resultado deve filtrar por agent_id e magic_number."""
    repo = JsonFechamentoRepository(agent_id="agente_5000", data_dir=tmp_path)
    arquivo = tmp_path / "historico_fechamentos_agente_5000.json"
    registros = [
        {"ticket": 1001, "agent_id": "agente_5000", "magic_number": 234500, "resultado": None},
        {"ticket": 1002, "agent_id": "agente_5000", "magic_number": 234500, "resultado": "WIN"},
        {"ticket": 2001, "agent_id": "agente_5000", "magic_number": 234600, "resultado": None},
    ]
    arquivo.write_text(json.dumps(registros, ensure_ascii=False), encoding="utf-8")

    lacunas = repo.listar_sem_resultado(agent_id="agente_5000", magic_number=234500)

    tickets = [r["ticket"] for r in lacunas]
    assert 1001 in tickets
    assert 1002 not in tickets  # ja tem resultado
    assert 2001 not in tickets  # magic_number diferente


def test_obter_resultado_local_retorna_string_quando_preenchido(tmp_path: Path):
    """obter_resultado_local deve retornar a string de resultado do ticket."""
    repo = JsonFechamentoRepository(agent_id="agente_5000", data_dir=tmp_path)
    arquivo = tmp_path / "historico_fechamentos_agente_5000.json"
    arquivo.write_text(
        json.dumps([{"ticket": 1001, "resultado": "WIN", "pnl_pct": 0.42}]),
        encoding="utf-8"
    )

    resultado = repo.obter_resultado_local(1001)

    assert resultado == "WIN"


def test_obter_resultado_local_retorna_none_quando_nao_classificado(tmp_path: Path):
    """obter_resultado_local deve retornar None quando resultado e NULL."""
    repo = JsonFechamentoRepository(agent_id="agente_5000", data_dir=tmp_path)
    arquivo = tmp_path / "historico_fechamentos_agente_5000.json"
    arquivo.write_text(
        json.dumps([{"ticket": 1001, "resultado": None, "pnl_pct": 0.42}]),
        encoding="utf-8"
    )

    resultado = repo.obter_resultado_local(1001)

    assert resultado is None


def test_interface_abstrata_nao_instanciavel():
    """IFechamentoRepository nao pode ser instanciada diretamente."""
    with pytest.raises(TypeError):
        IFechamentoRepository()  # type: ignore[abstract]
