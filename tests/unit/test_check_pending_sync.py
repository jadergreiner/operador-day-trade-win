"""Testes para cálculo da janela de recuperação do P50-CHECK."""

from __future__ import annotations

import sqlite3
from datetime import date

from scripts.check_pending_sync import (
    _calcular_days_back_para_pendencias,
    _check_posicoes_abertas,
)


def test_calcular_days_back_para_pendencias_usa_padrao_sem_datas() -> None:
    assert _calcular_days_back_para_pendencias([], [], hoje=date(2026, 4, 9)) == 2


def test_calcular_days_back_para_pendencias_expande_janela_para_pendencias_antigas() -> None:
    orphans = [
        {"criado_em": "2026-03-17T10:15:00"},
        {"criado_em": "2026-03-19T14:30:00"},
    ]
    trades_antigos = [
        {"entry_time": "2026-03-25T11:00:00"},
    ]

    resultado = _calcular_days_back_para_pendencias(
        orphans,
        trades_antigos,
        hoje=date(2026, 4, 9),
    )

    assert resultado >= 23


def test_check_posicoes_abertas_ignora_registros_encerrados() -> None:
    conn = sqlite3.connect(":memory:")
    cur = conn.cursor()
    cur.execute(
        """
        CREATE TABLE posicoes_abertas (
            posicao_id TEXT,
            trade_id TEXT,
            symbol TEXT,
            direcao TEXT,
            preco_entrada REAL,
            criado_em TEXT,
            status TEXT
        )
        """
    )
    cur.executemany(
        "INSERT INTO posicoes_abertas VALUES (?, ?, ?, ?, ?, ?, ?)",
        [
            ("POS_1", "1", "WIN$N", "BUY", 100.0, "2026-03-17T10:00:00", "ABERTA"),
            ("POS_2", "2", "WIN$N", "SELL", 101.0, "2026-03-17T11:00:00", "ENCERRADA"),
        ],
    )

    resultado = _check_posicoes_abertas(cur, "2026-04-09")

    conn.close()
    assert [item["trade_id"] for item in resultado] == ["1"]
