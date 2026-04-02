"""
Testes para UnknownResultDetector — ROADMAP-MICRO-03.

Grupo 4 da estrategia TDD.

Cobre:
- detectar_lacunas filtra por magic_number
- detectar_lacunas ignora ticket de outro agente
- detectar_lacunas retorna vazio quando todos tem resultado
- detectar_por_db filtra resultado NULL no SQLite
- detectar_por_db nao retorna posicoes abertas
- agent_id invalido levanta ValueError
- Compatibilidade retroativa: validar_integridade_resultado
"""

import sqlite3
import pytest
from pathlib import Path

from src.application.reconciliadores.unknown_result_detector import UnknownResultDetector


# ------------------------------------------------------------------
# Grupo 4 — detectar_lacunas com magic_number
# ------------------------------------------------------------------

def test_detectar_lacunas_filtra_por_magic_number():
    """So tickets do magic_number do agente devem aparecer."""
    detector = UnknownResultDetector()
    ordens_locais = [
        {"ticket": "1001", "magic_number": 234500, "resultado": None},
        {"ticket": "2001", "magic_number": 234600, "resultado": None},
    ]

    lacunas = detector.detectar_lacunas(
        agent_id="agente_5000",
        magic_number=234500,
        ordens_locais=ordens_locais,
        ordens_mt5=[],
    )

    assert "1001" in lacunas
    assert "2001" not in lacunas


def test_detectar_lacunas_ignora_ticket_de_outro_agente():
    """Ticket com magic_number diferente nunca aparece na lista."""
    detector = UnknownResultDetector()
    ordens_locais = [
        {"ticket": "1001", "magic_number": 234500, "resultado": None},
        {"ticket": "2001", "magic_number": 234600, "resultado": None},
    ]

    lacunas = detector.detectar_lacunas(
        agent_id="agente_5000",
        magic_number=234500,
        ordens_locais=ordens_locais,
        ordens_mt5=[],
    )

    assert "2001" not in lacunas


def test_detectar_lacunas_retorna_vazio_quando_todos_tem_resultado():
    """Nenhuma lacuna quando todos os tickets ja tem resultado."""
    detector = UnknownResultDetector()
    ordens_locais = [
        {"ticket": "1001", "magic_number": 234500, "resultado": "WIN"},
        {"ticket": "1002", "magic_number": 234500, "resultado": "LOSS"},
    ]

    lacunas = detector.detectar_lacunas(
        agent_id="agente_5000",
        magic_number=234500,
        ordens_locais=ordens_locais,
        ordens_mt5=[],
    )

    assert lacunas == []


def test_detectar_por_db_filtra_resultado_null_no_sqlite(sqlite_em_memoria):
    """detectar_por_db deve retornar apenas registros sem resultado."""
    db_path, conn = sqlite_em_memoria
    conn.execute(
        "INSERT INTO historico_fechamentos (ticket, agent_id, magic_number, resultado) "
        "VALUES (?, ?, ?, ?)",
        (1001, "agente_5000", 234500, None),
    )
    conn.execute(
        "INSERT INTO historico_fechamentos (ticket, agent_id, magic_number, resultado) "
        "VALUES (?, ?, ?, ?)",
        (1002, "agente_5000", 234500, "WIN"),
    )
    conn.commit()
    conn.close()

    detector = UnknownResultDetector()
    registros = detector.detectar_por_db(db_path, agent_id="agente_5000", magic_number=234500)

    tickets = [r["ticket"] for r in registros]
    assert 1001 in tickets
    assert 1002 not in tickets


def test_detectar_por_db_nao_retorna_posicoes_abertas(sqlite_em_memoria):
    """detectar_por_db deve ignorar registros com status ABERTA."""
    db_path, conn = sqlite_em_memoria
    conn.execute(
        "INSERT INTO historico_fechamentos "
        "(ticket, agent_id, magic_number, resultado, status) "
        "VALUES (?, ?, ?, ?, ?)",
        (3001, "agente_5000", 234500, None, "ABERTA"),
    )
    conn.execute(
        "INSERT INTO historico_fechamentos "
        "(ticket, agent_id, magic_number, resultado, status) "
        "VALUES (?, ?, ?, ?, ?)",
        (3002, "agente_5000", 234500, None, "FECHADA"),
    )
    conn.commit()
    conn.close()

    detector = UnknownResultDetector()
    registros = detector.detectar_por_db(db_path)

    tickets = [r["ticket"] for r in registros]
    assert 3001 not in tickets
    assert 3002 in tickets


def test_detectar_lacunas_agent_id_invalido_levanta_value_error():
    """agent_id vazio deve levantar ValueError."""
    detector = UnknownResultDetector()

    with pytest.raises(ValueError, match="agent_id"):
        detector.detectar_lacunas(
            agent_id="",
            magic_number=234500,
            ordens_locais=[],
            ordens_mt5=[],
        )


# ------------------------------------------------------------------
# Compatibilidade retroativa
# ------------------------------------------------------------------

def test_validar_integridade_resultado_sucesso():
    detector = UnknownResultDetector()
    resultado_valido = {"price": 120500, "volume": 1, "profit": 50.0}

    assert detector.validar_integridade_resultado(resultado_valido) is True


def test_validar_integridade_resultado_sucesso_com_valores_texto():
    detector = UnknownResultDetector()
    resultado_valido = {"price": "120500", "volume": "1", "profit": "50.0"}

    assert detector.validar_integridade_resultado(resultado_valido) is True


def test_validar_integridade_resultado_falha_campo_ausente():
    detector = UnknownResultDetector()
    resultado_invalido = {"price": 120500}

    assert detector.validar_integridade_resultado(resultado_invalido) is False


def test_validar_integridade_resultado_falha_valor_nulo():
    detector = UnknownResultDetector()
    resultado_invalido = {"price": 120500, "volume": None, "profit": 50.0}

    assert detector.validar_integridade_resultado(resultado_invalido) is False

