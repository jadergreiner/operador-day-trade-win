"""
Serviço de Diretivas do Head Financeiro.

Permite que análises pré-mercado (diários overnight, BDI, etc.)
influenciem as decisões do agente de micro tendências em tempo real.

As diretivas são armazenadas em SQLite e lidas pelo agente a cada ciclo.
O Head Financeiro (humano ou IA) gera diretivas via script ou manualmente.

Campos da diretiva:
  - direction: BULLISH, BEARISH, NEUTRAL
  - confidence_market: 0-100 (confiança do Head no mercado)
  - aggressiveness: LOW, MODERATE, HIGH
  - position_size_pct: 0-100 (% do tamanho normal de posição)
  - stop_loss_pts: stop em pontos (0 = usar padrão do agente)
  - max_rsi_for_buy: RSI máximo para permitir BUY (0 = sem filtro)
  - max_rsi_for_sell: RSI mínimo para permitir SELL (100 = sem filtro)
  - forbidden_zone_above: preço acima do qual BUY é proibido (0 = sem zona)
  - forbidden_zone_below: preço abaixo do qual SELL é proibido (0 = sem zona)
  - ideal_buy_zone_low: limite inferior da zona ideal de compra
  - ideal_buy_zone_high: limite superior da zona ideal de compra
  - reduce_before_event: True = reduzir exposição antes de evento macro
  - event_description: descrição do evento macro do dia
  - notes: observações livres do Head
"""

from __future__ import annotations

import json
import os
import sqlite3
from dataclasses import dataclass, field, asdict
from datetime import datetime, date
from decimal import Decimal
from typing import Optional


@dataclass
class HeadDirective:
    """Diretiva do Head Financeiro para o agente."""

    # Identificação
    date: str = ""                          # YYYY-MM-DD
    created_at: str = ""                    # ISO timestamp
    source: str = ""                        # ex: "diario_overnight_20260211"
    analyst: str = "Head Global de Finanças"

    # Direção e confiança
    direction: str = "NEUTRAL"              # BULLISH, BEARISH, NEUTRAL
    confidence_market: int = 50             # 0-100
    aggressiveness: str = "MODERATE"        # LOW, MODERATE, HIGH

    # Gestão de posição
    position_size_pct: int = 100            # % do tamanho normal
    stop_loss_pts: int = 0                  # 0 = usar padrão do agente
    max_daily_trades: int = 0               # 0 = usar padrão do agente

    # Filtros técnicos
    max_rsi_for_buy: int = 0                # 0 = sem filtro (ex: 72)
    min_rsi_for_sell: int = 100             # 100 = sem filtro (ex: 28)
    min_adx_for_entry: int = 0              # 0 = sem filtro

    # Zonas de preço
    forbidden_zone_above: float = 0.0       # BUY proibido acima deste preço
    forbidden_zone_below: float = 0.0       # SELL proibido abaixo deste preço
    ideal_buy_zone_low: float = 0.0         # Zona ideal de compra (low)
    ideal_buy_zone_high: float = 0.0        # Zona ideal de compra (high)
    ideal_sell_zone_low: float = 0.0        # Zona ideal de venda (low)
    ideal_sell_zone_high: float = 0.0       # Zona ideal de venda (high)

    # Eventos macro
    reduce_before_event: bool = False       # Reduzir exposição antes de evento
    event_description: str = ""             # Ex: "Payroll americano 10:30"
    event_time: str = ""                    # HH:MM (horário do evento)

    # Notas
    notes: str = ""                         # Observações livres
    risk_scenario: str = ""                 # Cenário de risco principal

    # Estado
    active: bool = True                     # Diretiva ativa?

    def to_dict(self) -> dict:
        """Converte para dicionário."""
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict) -> HeadDirective:
        """Cria a partir de dicionário."""
        valid_fields = {f.name for f in cls.__dataclass_fields__.values()}
        filtered = {k: v for k, v in data.items() if k in valid_fields}
        return cls(**filtered)


# ────────────────────────────────────────────────────────────────
# Persistência SQLite
# ────────────────────────────────────────────────────────────────

_CREATE_TABLE_SQL = """
CREATE TABLE IF NOT EXISTS head_directives (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    date TEXT NOT NULL,
    created_at TEXT NOT NULL,
    source TEXT NOT NULL,
    analyst TEXT NOT NULL DEFAULT 'Head Global de Finanças',
    direction TEXT NOT NULL DEFAULT 'NEUTRAL',
    confidence_market INTEGER NOT NULL DEFAULT 50,
    aggressiveness TEXT NOT NULL DEFAULT 'MODERATE',
    position_size_pct INTEGER NOT NULL DEFAULT 100,
    stop_loss_pts INTEGER NOT NULL DEFAULT 0,
    max_daily_trades INTEGER NOT NULL DEFAULT 0,
    max_rsi_for_buy INTEGER NOT NULL DEFAULT 0,
    min_rsi_for_sell INTEGER NOT NULL DEFAULT 100,
    min_adx_for_entry INTEGER NOT NULL DEFAULT 0,
    forbidden_zone_above REAL NOT NULL DEFAULT 0.0,
    forbidden_zone_below REAL NOT NULL DEFAULT 0.0,
    ideal_buy_zone_low REAL NOT NULL DEFAULT 0.0,
    ideal_buy_zone_high REAL NOT NULL DEFAULT 0.0,
    ideal_sell_zone_low REAL NOT NULL DEFAULT 0.0,
    ideal_sell_zone_high REAL NOT NULL DEFAULT 0.0,
    reduce_before_event INTEGER NOT NULL DEFAULT 0,
    event_description TEXT NOT NULL DEFAULT '',
    event_time TEXT NOT NULL DEFAULT '',
    notes TEXT NOT NULL DEFAULT '',
    risk_scenario TEXT NOT NULL DEFAULT '',
    active INTEGER NOT NULL DEFAULT 1
)
"""

_INSERT_SQL = """
INSERT INTO head_directives (
    date, created_at, source, analyst,
    direction, confidence_market, aggressiveness,
    position_size_pct, stop_loss_pts, max_daily_trades,
    max_rsi_for_buy, min_rsi_for_sell, min_adx_for_entry,
    forbidden_zone_above, forbidden_zone_below,
    ideal_buy_zone_low, ideal_buy_zone_high,
    ideal_sell_zone_low, ideal_sell_zone_high,
    reduce_before_event, event_description, event_time,
    notes, risk_scenario, active
) VALUES (
    ?, ?, ?, ?,
    ?, ?, ?,
    ?, ?, ?,
    ?, ?, ?,
    ?, ?,
    ?, ?,
    ?, ?,
    ?, ?, ?,
    ?, ?, ?
)
"""


def create_directives_table(db_path: str) -> None:
    """Cria a tabela de diretivas se não existir."""
    conn = sqlite3.connect(db_path)
    conn.execute(_CREATE_TABLE_SQL)
    conn.commit()
    conn.close()


def save_directive(db_path: str, directive: HeadDirective) -> int:
    """Salva uma diretiva no banco. Retorna o ID."""
    create_directives_table(db_path)

    # Desativa diretivas anteriores do mesmo dia
    conn = sqlite3.connect(db_path)
    conn.execute(
        "UPDATE head_directives SET active = 0 WHERE date = ? AND active = 1",
        (directive.date,),
    )

    cursor = conn.execute(_INSERT_SQL, (
        directive.date,
        directive.created_at or datetime.now().isoformat(),
        directive.source,
        directive.analyst,
        directive.direction,
        directive.confidence_market,
        directive.aggressiveness,
        directive.position_size_pct,
        directive.stop_loss_pts,
        directive.max_daily_trades,
        directive.max_rsi_for_buy,
        directive.min_rsi_for_sell,
        directive.min_adx_for_entry,
        directive.forbidden_zone_above,
        directive.forbidden_zone_below,
        directive.ideal_buy_zone_low,
        directive.ideal_buy_zone_high,
        directive.ideal_sell_zone_low,
        directive.ideal_sell_zone_high,
        1 if directive.reduce_before_event else 0,
        directive.event_description,
        directive.event_time,
        directive.notes,
        directive.risk_scenario,
        1 if directive.active else 0,
    ))

    conn.commit()
    row_id = cursor.lastrowid
    conn.close()
    return row_id


def load_active_directive(db_path: str, target_date: str = "") -> Optional[HeadDirective]:
    """
    Carrega a diretiva ativa para a data.
    Se target_date vazio, usa a data de hoje.
    Retorna None se não houver diretiva ativa.
    """
    if not os.path.exists(db_path):
        return None

    if not target_date:
        target_date = date.today().isoformat()

    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row

    # Tenta diretiva do dia
    row = conn.execute(
        "SELECT * FROM head_directives WHERE date = ? AND active = 1 "
        "ORDER BY id DESC LIMIT 1",
        (target_date,),
    ).fetchone()

    conn.close()

    if row is None:
        return None

    return HeadDirective(
        date=row["date"],
        created_at=row["created_at"],
        source=row["source"],
        analyst=row["analyst"],
        direction=row["direction"],
        confidence_market=row["confidence_market"],
        aggressiveness=row["aggressiveness"],
        position_size_pct=row["position_size_pct"],
        stop_loss_pts=row["stop_loss_pts"],
        max_daily_trades=row["max_daily_trades"],
        max_rsi_for_buy=row["max_rsi_for_buy"],
        min_rsi_for_sell=row["min_rsi_for_sell"],
        min_adx_for_entry=row["min_adx_for_entry"],
        forbidden_zone_above=row["forbidden_zone_above"],
        forbidden_zone_below=row["forbidden_zone_below"],
        ideal_buy_zone_low=row["ideal_buy_zone_low"],
        ideal_buy_zone_high=row["ideal_buy_zone_high"],
        ideal_sell_zone_low=row["ideal_sell_zone_low"],
        ideal_sell_zone_high=row["ideal_sell_zone_high"],
        reduce_before_event=bool(row["reduce_before_event"]),
        event_description=row["event_description"],
        event_time=row["event_time"],
        notes=row["notes"],
        risk_scenario=row["risk_scenario"],
        active=bool(row["active"]),
    )


def list_directives(db_path: str, limit: int = 10) -> list[HeadDirective]:
    """Lista as últimas diretivas."""
    if not os.path.exists(db_path):
        return []

    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    rows = conn.execute(
        "SELECT * FROM head_directives ORDER BY id DESC LIMIT ?",
        (limit,),
    ).fetchall()
    conn.close()

    return [HeadDirective(
        date=r["date"],
        created_at=r["created_at"],
        source=r["source"],
        analyst=r["analyst"],
        direction=r["direction"],
        confidence_market=r["confidence_market"],
        aggressiveness=r["aggressiveness"],
        position_size_pct=r["position_size_pct"],
        stop_loss_pts=r["stop_loss_pts"],
        max_daily_trades=r["max_daily_trades"],
        max_rsi_for_buy=r["max_rsi_for_buy"],
        min_rsi_for_sell=r["min_rsi_for_sell"],
        min_adx_for_entry=r["min_adx_for_entry"],
        forbidden_zone_above=r["forbidden_zone_above"],
        forbidden_zone_below=r["forbidden_zone_below"],
        ideal_buy_zone_low=r["ideal_buy_zone_low"],
        ideal_buy_zone_high=r["ideal_buy_zone_high"],
        ideal_sell_zone_low=r["ideal_sell_zone_low"],
        ideal_sell_zone_high=r["ideal_sell_zone_high"],
        reduce_before_event=bool(r["reduce_before_event"]),
        event_description=r["event_description"],
        event_time=r["event_time"],
        notes=r["notes"],
        risk_scenario=r["risk_scenario"],
        active=bool(r["active"]),
    ) for r in rows]
