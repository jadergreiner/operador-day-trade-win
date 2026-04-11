"""Backfill histórico de `rl_rewards` a partir de `rl_episodes`.

Reconstrói recompensas multi-horizonte (5m, 15m, 30m, 60m, 120m)
para episódios RL já persistidos, usando preços históricos da tabela
`market_data`.

Uso:
    python scripts/backfill_rl_rewards.py \
        --target-db data/db/trading_rl_direto.db \
        --market-db data/db/trading.db
"""

from __future__ import annotations

import argparse
import sqlite3
from dataclasses import dataclass
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional

ROOT_DIR = Path(__file__).resolve().parents[1]
DEFAULT_TARGET_DB = ROOT_DIR / "data" / "db" / "trading_rl_direto.db"
DEFAULT_MARKET_DB = ROOT_DIR / "data" / "db" / "trading.db"
REWARD_HORIZONS = [5, 15, 30, 60, 120]
HOLD_TOLERANCE_PTS = 100.0


@dataclass(frozen=True)
class PontoMercado:
    """Snapshot de mercado usado para inferência de reward."""

    timestamp: datetime
    symbol: str
    open_price: float
    high_price: float
    low_price: float
    close_price: float


def normalizar_acao_rl(
    acao: Optional[str],
    acao_original: Optional[str] = None,
) -> str:
    """Converte rótulos operacionais para o padrão canônico do RL."""
    mapa = {
        "AGUARDAR": "HOLD",
        "HOLD": "HOLD",
        "COMPRAR": "BUY",
        "BUY": "BUY",
        "VENDER": "SELL",
        "SELL": "SELL",
    }
    for valor in (acao, acao_original):
        chave = (valor or "").strip().upper()
        if chave in mapa:
            return mapa[chave]
    return "HOLD"


def _parse_dt(valor: str) -> datetime:
    texto = str(valor).replace("T", " ")
    return datetime.fromisoformat(texto)


def _to_ponto(row: sqlite3.Row) -> PontoMercado:
    return PontoMercado(
        timestamp=_parse_dt(row["timestamp"]),
        symbol=str(row["symbol"]),
        open_price=float(row["open"]),
        high_price=float(row["high"]),
        low_price=float(row["low"]),
        close_price=float(row["close"]),
    )


def _buscar_referencia_mercado(
    cur: sqlite3.Cursor,
    timestamp_decisao: datetime,
    preco_decisao: float,
    janela_minutos: int = 20,
) -> Optional[PontoMercado]:
    """Localiza o candle WIN mais próximo do episódio.

    Estratégia:
    1. procura candles WIN dentro de uma janela curta em torno do episódio;
    2. ordena por proximidade temporal e depois por proximidade de preço;
    3. amplia a janela caso o banco esteja mais esparso.
    """
    inicio = (timestamp_decisao - timedelta(minutes=janela_minutos)).strftime(
        "%Y-%m-%d %H:%M:%S"
    )
    fim = (timestamp_decisao + timedelta(minutes=janela_minutos)).strftime(
        "%Y-%m-%d %H:%M:%S"
    )
    cur.execute(
        """
        SELECT timestamp, symbol, open, high, low, close
        FROM market_data
        WHERE symbol LIKE 'WIN%'
          AND timestamp BETWEEN ? AND ?
        """,
        (inicio, fim),
    )
    rows = cur.fetchall()
    if not rows and janela_minutos < 180:
        return _buscar_referencia_mercado(
            cur,
            timestamp_decisao,
            preco_decisao,
            janela_minutos=180,
        )
    if not rows:
        return None

    candidatos = [_to_ponto(row) for row in rows]
    candidatos.sort(
        key=lambda item: (
            abs((item.timestamp - timestamp_decisao).total_seconds()),
            abs(item.close_price - preco_decisao),
        )
    )
    return candidatos[0]


def _buscar_ponto_avaliacao(
    cur: sqlite3.Cursor,
    symbol: str,
    timestamp_decisao: datetime,
    timestamp_alvo: datetime,
) -> Optional[PontoMercado]:
    """Busca o melhor candle para avaliar um horizonte histórico."""
    alvo = timestamp_alvo.strftime("%Y-%m-%d %H:%M:%S")
    limite_superior = (timestamp_alvo + timedelta(days=1)).strftime(
        "%Y-%m-%d %H:%M:%S"
    )
    inicio = timestamp_decisao.strftime("%Y-%m-%d %H:%M:%S")

    cur.execute(
        """
        SELECT timestamp, symbol, open, high, low, close
        FROM market_data
        WHERE symbol = ?
          AND timestamp >= ?
          AND timestamp <= ?
        ORDER BY timestamp ASC
        LIMIT 1
        """,
        (symbol, alvo, limite_superior),
    )
    row = cur.fetchone()
    if row is not None:
        return _to_ponto(row)

    cur.execute(
        """
        SELECT timestamp, symbol, open, high, low, close
        FROM market_data
        WHERE symbol = ?
          AND timestamp >= ?
          AND timestamp <= ?
        ORDER BY timestamp DESC
        LIMIT 1
        """,
        (symbol, inicio, alvo),
    )
    row = cur.fetchone()
    return _to_ponto(row) if row is not None else None


def _buscar_mfe_mae(
    cur: sqlite3.Cursor,
    symbol: str,
    timestamp_inicio: datetime,
    timestamp_fim: datetime,
) -> tuple[Optional[float], Optional[float], Optional[float]]:
    """Calcula máxima favorável, máxima adversa e volatilidade do range."""
    inicio = timestamp_inicio.strftime("%Y-%m-%d %H:%M:%S")
    fim = timestamp_fim.strftime("%Y-%m-%d %H:%M:%S")
    cur.execute(
        """
        SELECT MAX(high) AS max_high, MIN(low) AS min_low
        FROM market_data
        WHERE symbol = ?
          AND timestamp BETWEEN ? AND ?
        """,
        (symbol, inicio, fim),
    )
    row = cur.fetchone()
    if row is None or row[0] is None or row[1] is None:
        return None, None, None
    max_high = float(row[0])
    min_low = float(row[1])
    return max_high, min_low, max_high - min_low


def calcular_reward_historico(
    *,
    acao: str,
    preco_decisao: float,
    preco_avaliacao: float,
    max_high: Optional[float],
    min_low: Optional[float],
) -> dict[str, object]:
    """Replica a semântica do reward multi-horizonte do runtime RL."""
    price_change = preco_avaliacao - preco_decisao
    price_change_pct = (price_change / preco_decisao * 100.0) if preco_decisao else 0.0

    if price_change > 0:
        direction = "UP"
    elif price_change < 0:
        direction = "DOWN"
    else:
        direction = "FLAT"

    was_correct = 0
    decision_verdict = None
    reward_continuous = 0.0

    if acao == "BUY":
        reward_continuous = price_change
        if direction == "UP":
            was_correct = 1
            decision_verdict = "BUY_CONFIRMADO"
    elif acao == "SELL":
        reward_continuous = -price_change
        if direction == "DOWN":
            was_correct = 1
            decision_verdict = "SELL_CONFIRMADO"
    else:
        excesso = abs(price_change) - HOLD_TOLERANCE_PTS
        reward_continuous = -excesso if excesso > 0 else 0.0
        if abs(price_change) <= HOLD_TOLERANCE_PTS:
            was_correct = 1
            decision_verdict = "HOLD_CORRECT"
        elif price_change > 0:
            decision_verdict = "HOLD_PERDEU_ALTA"
        else:
            decision_verdict = "HOLD_PERDEU_BAIXA"

    reward_normalized = max(-1.0, min(1.0, reward_continuous / 200.0))

    mfe = None
    mae = None
    if max_high is not None and min_low is not None:
        if acao == "BUY":
            mfe = max_high - preco_decisao
            mae = preco_decisao - min_low
        elif acao == "SELL":
            mfe = preco_decisao - min_low
            mae = max_high - preco_decisao
        else:
            mfe = max_high - preco_decisao
            mae = preco_decisao - min_low

    return {
        "price_change_points": round(price_change, 2),
        "price_change_pct": price_change_pct,
        "reward_direction": direction,
        "was_correct": was_correct,
        "reward_normalized": reward_normalized,
        "reward_continuous": reward_continuous,
        "decision_verdict": decision_verdict,
        "max_favorable_points": None if mfe is None else round(mfe, 2),
        "max_adverse_points": None if mae is None else round(mae, 2),
    }


def _garantir_reward_base(
    cur: sqlite3.Cursor,
    *,
    episode_id: str,
    timestamp_decisao: datetime,
    preco_decisao: float,
    acao: str,
    horizon: int,
) -> None:
    """Cria a linha-base do reward caso ainda não exista."""
    cur.execute(
        """
        INSERT OR IGNORE INTO rl_rewards (
            episode_id,
            timestamp_decision,
            win_price_at_decision,
            action_at_decision,
            horizon_minutes,
            is_evaluated,
            created_at,
            updated_at
        )
        VALUES (?, ?, ?, ?, ?, 0, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
        """,
        (
            episode_id,
            timestamp_decisao.strftime("%Y-%m-%d %H:%M:%S"),
            preco_decisao,
            acao,
            horizon,
        ),
    )


def _atualizar_reward_avaliado(
    cur: sqlite3.Cursor,
    *,
    episode_id: str,
    horizon: int,
    evaluated_at: datetime,
    preco_avaliacao: float,
    dados_reward: dict[str, object],
    volatilidade: Optional[float],
) -> None:
    cur.execute(
        """
        UPDATE rl_rewards
        SET evaluated_at = ?,
            win_price_at_evaluation = ?,
            price_change_points = ?,
            price_change_pct = ?,
            reward_direction = ?,
            was_correct = ?,
            reward_normalized = ?,
            reward_continuous = ?,
            decision_verdict = ?,
            max_favorable_points = ?,
            max_adverse_points = ?,
            volatility_in_horizon = ?,
            is_evaluated = 1,
            updated_at = CURRENT_TIMESTAMP
        WHERE episode_id = ?
          AND horizon_minutes = ?
        """,
        (
            evaluated_at.strftime("%Y-%m-%d %H:%M:%S"),
            preco_avaliacao,
            dados_reward["price_change_points"],
            dados_reward["price_change_pct"],
            dados_reward["reward_direction"],
            dados_reward["was_correct"],
            dados_reward["reward_normalized"],
            dados_reward["reward_continuous"],
            dados_reward["decision_verdict"],
            dados_reward["max_favorable_points"],
            dados_reward["max_adverse_points"],
            volatilidade,
            episode_id,
            horizon,
        ),
    )


def backfill_rl_rewards(
    *,
    target_db: Path,
    market_db: Optional[Path] = None,
    limit: Optional[int] = None,
) -> dict[str, int]:
    """Executa o backfill histórico de rewards em um banco RL."""
    market_db = market_db or target_db

    target_conn = sqlite3.connect(target_db)
    target_conn.row_factory = sqlite3.Row
    market_conn = target_conn if market_db == target_db else sqlite3.connect(market_db)
    market_conn.row_factory = sqlite3.Row

    try:
        target_cur = target_conn.cursor()
        market_cur = market_conn.cursor()

        query = """
        SELECT episode_id, timestamp, win_price, action, original_action
        FROM rl_episodes
        WHERE win_price IS NOT NULL
        ORDER BY timestamp ASC
        """
        if limit is not None:
            query += f" LIMIT {int(limit)}"

        episodes = target_cur.execute(query).fetchall()

        resumo = {
            "episodes_total": len(episodes),
            "episodes_com_referencia": 0,
            "rewards_criados_ou_atualizados": 0,
            "rewards_avaliados": 0,
            "episodes_sem_match_mercado": 0,
        }

        for episode in episodes:
            episode_id = str(episode["episode_id"])
            timestamp_decisao = _parse_dt(str(episode["timestamp"]))
            preco_decisao = float(episode["win_price"])
            acao_rl = normalizar_acao_rl(
                episode["action"],
                episode["original_action"],
            )

            referencia = _buscar_referencia_mercado(
                market_cur,
                timestamp_decisao,
                preco_decisao,
            )
            if referencia is None:
                resumo["episodes_sem_match_mercado"] += 1
                continue

            resumo["episodes_com_referencia"] += 1

            for horizon in REWARD_HORIZONS:
                _garantir_reward_base(
                    target_cur,
                    episode_id=episode_id,
                    timestamp_decisao=timestamp_decisao,
                    preco_decisao=preco_decisao,
                    acao=acao_rl,
                    horizon=horizon,
                )
                resumo["rewards_criados_ou_atualizados"] += 1

                timestamp_alvo = timestamp_decisao + timedelta(minutes=horizon)
                ponto_avaliacao = _buscar_ponto_avaliacao(
                    market_cur,
                    referencia.symbol,
                    timestamp_decisao,
                    timestamp_alvo,
                )
                if ponto_avaliacao is None:
                    continue

                max_high, min_low, volatilidade = _buscar_mfe_mae(
                    market_cur,
                    referencia.symbol,
                    timestamp_decisao,
                    ponto_avaliacao.timestamp,
                )
                dados_reward = calcular_reward_historico(
                    acao=acao_rl,
                    preco_decisao=preco_decisao,
                    preco_avaliacao=ponto_avaliacao.close_price,
                    max_high=max_high,
                    min_low=min_low,
                )
                _atualizar_reward_avaliado(
                    target_cur,
                    episode_id=episode_id,
                    horizon=horizon,
                    evaluated_at=ponto_avaliacao.timestamp,
                    preco_avaliacao=ponto_avaliacao.close_price,
                    dados_reward=dados_reward,
                    volatilidade=volatilidade,
                )
                resumo["rewards_avaliados"] += 1

        target_conn.commit()
        return resumo
    finally:
        target_conn.close()
        if market_conn is not target_conn:
            market_conn.close()


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Reconstrói rl_rewards avaliados usando market_data histórico.",
    )
    parser.add_argument(
        "--target-db",
        type=Path,
        default=DEFAULT_TARGET_DB,
        help="Banco RL que receberá o backfill.",
    )
    parser.add_argument(
        "--market-db",
        type=Path,
        default=DEFAULT_MARKET_DB,
        help="Banco fonte com market_data histórico.",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=None,
        help="Limita a quantidade de episódios processados.",
    )
    return parser


def main() -> int:
    parser = _build_parser()
    args = parser.parse_args()

    resumo = backfill_rl_rewards(
        target_db=args.target_db,
        market_db=args.market_db,
        limit=args.limit,
    )

    print("\n=== BACKFILL RL REWARDS ===")
    print(f"Banco alvo: {args.target_db}")
    print(f"Banco mercado: {args.market_db}")
    for chave, valor in resumo.items():
        print(f"- {chave}: {valor}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
