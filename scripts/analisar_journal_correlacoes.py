"""Script de analise e exportacao de correlacoes do diario de mercado.

BLID-022 / ROADMAP-DIARIOS-02.

Uso:
    python scripts/analisar_journal_correlacoes.py
    python scripts/analisar_journal_correlacoes.py --data 2026-04-02
    python scripts/analisar_journal_correlacoes.py \\
        --data 2026-04-02 \\
        --output-dir data/training \\
        --db-path data/db/trading_diarios.db

Saida:
    data/training/journal_features_YYYYMMDD.json
    (schema_version="1.0", magic_number_filtro=234800)
"""
from __future__ import annotations

import argparse
import json
import logging
import sqlite3
from datetime import date, datetime
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

# Versao do schema exportado — incrementar em breaking changes
_SCHEMA_VERSION = "1.0"
_MAGIC_NUMBER_DIARIOS = 234800


# ---------------------------------------------------------------------------
# Leitura do banco
# ---------------------------------------------------------------------------


def _buscar_entradas_journal(
    db_path: Path, data_referencia: str
) -> list[dict[str, Any]]:
    """Retorna entradas de trading_journal_logs para a data informada.

    Args:
        db_path: Caminho para o banco SQLite.
        data_referencia: Data no formato YYYY-MM-DD.

    Returns:
        Lista de dicionarios com os campos da tabela.
    """
    if not db_path.exists():
        return []

    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row
    try:
        tabela_existe = conn.execute(
            "SELECT name FROM sqlite_master "
            "WHERE type='table' AND name='trading_journal_logs'"
        ).fetchone()
        if not tabela_existe:
            return []

        cursor = conn.execute(
            """
            SELECT entry_id, timestamp, decision, confidence,
                   macro_bias, technical_bias, alignment_score,
                   market_feeling, outcome_trade
            FROM trading_journal_logs
            WHERE timestamp LIKE ?
            ORDER BY timestamp ASC
            """,
            (f"{data_referencia}%",),
        )
        return [dict(row) for row in cursor.fetchall()]
    finally:
        conn.close()


def _buscar_correlacoes(
    db_path: Path, entry_ids: list[str]
) -> list[dict[str, Any]]:
    """Retorna correlacoes de journal_trade_correlation para os entry_ids.

    Args:
        db_path: Caminho para o banco SQLite.
        entry_ids: Lista de entry_ids a consultar.

    Returns:
        Lista de dicionarios com os campos da tabela.
    """
    if not db_path.exists() or not entry_ids:
        return []

    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row
    try:
        tabela_existe = conn.execute(
            "SELECT name FROM sqlite_master "
            "WHERE type='table' AND name='journal_trade_correlation'"
        ).fetchone()
        if not tabela_existe:
            return []

        # Seguro: placeholders sao apenas '?' repetidos (sem interpolacao de dados)
        placeholders = ",".join("?" * len(entry_ids))
        cursor = conn.execute(
            f"""
            SELECT journal_entry_id, trade_ticket, outcome,
                   pnl_reais, narrativa_estava_alinhada
            FROM journal_trade_correlation
            WHERE journal_entry_id IN ({placeholders})
            """,
            entry_ids,
        )
        return [dict(row) for row in cursor.fetchall()]
    finally:
        conn.close()


# ---------------------------------------------------------------------------
# Helpers de metricas
# ---------------------------------------------------------------------------


def _calcular_alinhamento_medio(
    correlacoes: list[dict[str, Any]]
) -> float:
    """Calcula percentual medio de alinhamento narrativa x trade.

    Considera apenas correlacoes com narrativa_estava_alinhada nao nulo.

    Args:
        correlacoes: Lista de correlacoes com o campo
                     narrativa_estava_alinhada.

    Returns:
        Percentual de alinhamento (0.0–100.0) ou 0.0 se sem dados.
    """
    valores = [
        c["narrativa_estava_alinhada"]
        for c in correlacoes
        if c.get("narrativa_estava_alinhada") is not None
    ]
    if not valores:
        return 0.0
    return round(sum(valores) / len(valores) * 100, 2)


def _calcular_win_rate_alinhado(
    correlacoes: list[dict[str, Any]]
) -> float:
    """Calcula taxa de acerto nos trades em que a narrativa estava alinhada.

    Args:
        correlacoes: Lista de correlacoes.

    Returns:
        Win rate (0.0–100.0) ou 0.0 se sem dados.
    """
    alinhados = [c for c in correlacoes if c.get("narrativa_estava_alinhada") == 1]
    if not alinhados:
        return 0.0
    wins = sum(1 for c in alinhados if c.get("outcome") == "WIN")
    return round(wins / len(alinhados) * 100, 2)


def _calcular_sentimento_x_outcome(
    entradas: list[dict[str, Any]],
    correlacoes_por_entry: dict[str, dict[str, Any]],
) -> dict[str, dict[str, int]]:
    """Agrupa outcomes por sentimento de mercado (market_feeling).

    Utiliza o campo market_feeling das entradas de journal como chave
    e contabiliza WIN/LOSS/BREAKEVEN/SEM_TRADE por sentimento.

    Args:
        entradas: Entradas de trading_journal_logs.
        correlacoes_por_entry: Mapa entry_id -> correlacao.

    Returns:
        Dicionario {sentimento: {outcome: contagem}}.
    """
    resultado: dict[str, dict[str, int]] = {}
    for entrada in entradas:
        sentimento = str(entrada.get("market_feeling", "DESCONHECIDO"))
        corr = correlacoes_por_entry.get(str(entrada["entry_id"]))
        outcome = corr["outcome"] if corr else "SEM_TRADE"
        if sentimento not in resultado:
            resultado[sentimento] = {
                "WIN": 0, "LOSS": 0, "BREAKEVEN": 0, "SEM_TRADE": 0
            }
        resultado[sentimento][outcome] = resultado[sentimento].get(outcome, 0) + 1
    return resultado


# ---------------------------------------------------------------------------
# Exportador principal
# ---------------------------------------------------------------------------


def exportar_features(
    data_referencia: str,
    db_path: Path,
    output_dir: Path,
) -> Path:
    """Exporta features correlacionadas como JSON de treinamento.

    Gera arquivo journal_features_YYYYMMDD.json com schema_version="1.0",
    totais por outcome, metricas de correlacao e array features consumivel
    por pipelines ML/RL.

    Args:
        data_referencia: Data no formato YYYY-MM-DD.
        db_path: Caminho para o banco SQLite.
        output_dir: Diretorio de saida para o arquivo JSON.

    Returns:
        Path do arquivo gerado.
    """
    output_dir.mkdir(parents=True, exist_ok=True)
    data_sem_hifens = data_referencia.replace("-", "")
    caminho_saida = output_dir / f"journal_features_{data_sem_hifens}.json"

    entradas = _buscar_entradas_journal(db_path, data_referencia)
    entry_ids = [str(e["entry_id"]) for e in entradas]
    correlacoes = _buscar_correlacoes(db_path, entry_ids)

    correlacoes_por_entry: dict[str, dict[str, Any]] = {
        str(c["journal_entry_id"]): c for c in correlacoes
    }

    # Totais
    com_trade = sum(1 for c in correlacoes if c.get("outcome") != "SEM_TRADE")
    sem_trade = len(entradas) - com_trade
    wins = sum(1 for c in correlacoes if c.get("outcome") == "WIN")
    losses = sum(1 for c in correlacoes if c.get("outcome") == "LOSS")
    breakevens = sum(1 for c in correlacoes if c.get("outcome") == "BREAKEVEN")

    # Metricas
    alinhamento_medio = _calcular_alinhamento_medio(correlacoes)
    win_rate_alinhado = _calcular_win_rate_alinhado(correlacoes)
    sentimento_x_outcome = _calcular_sentimento_x_outcome(
        entradas, correlacoes_por_entry
    )

    # Features por entrada
    features: list[dict[str, Any]] = []
    for entrada in entradas:
        eid = str(entrada["entry_id"])
        corr = correlacoes_por_entry.get(eid)
        features.append(
            {
                "entry_id": eid,
                "timestamp": entrada.get("timestamp"),
                "decision": entrada.get("decision"),
                "confidence": entrada.get("confidence"),
                "macro_bias": entrada.get("macro_bias"),
                "technical_bias": entrada.get("technical_bias"),
                "alignment_score": entrada.get("alignment_score"),
                "outcome_trade": corr["outcome"] if corr else "SEM_TRADE",
                "narrativa_estava_alinhada": (
                    bool(corr["narrativa_estava_alinhada"])
                    if corr and corr.get("narrativa_estava_alinhada") is not None
                    else None
                ),
            }
        )

    payload: dict[str, Any] = {
        "schema_version": _SCHEMA_VERSION,
        "generated_at": datetime.utcnow().isoformat(),
        "data_referencia": data_referencia,
        "magic_number_filtro": _MAGIC_NUMBER_DIARIOS,
        "totais": {
            "entradas_journal": len(entradas),
            "com_trade": com_trade,
            "sem_trade": sem_trade,
            "win": wins,
            "loss": losses,
            "breakeven": breakevens,
        },
        "metricas": {
            "alinhamento_medio_pct": alinhamento_medio,
            "win_rate_quando_alinhado": win_rate_alinhado,
            "sentimento_x_outcome": sentimento_x_outcome,
        },
        "features": features,
    }

    caminho_saida.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    logger.info("Features exportadas: %s (%d entradas)", caminho_saida, len(features))
    return caminho_saida


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def _construir_argparser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Analisa e exporta correlacoes do Diario 1 (BLID-022)"
    )
    parser.add_argument(
        "--data",
        default=date.today().isoformat(),
        help="Data de referencia no formato YYYY-MM-DD (padrao: hoje)",
    )
    parser.add_argument(
        "--output-dir",
        default="data/training",
        help="Diretorio de saida do JSON (padrao: data/training)",
    )
    parser.add_argument(
        "--db-path",
        default="data/db/trading_diarios.db",
        help="Caminho para o banco SQLite (padrao: data/db/trading_diarios.db)",
    )
    return parser


def main() -> None:
    """Ponto de entrada da CLI."""
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    parser = _construir_argparser()
    args = parser.parse_args()

    caminho = exportar_features(
        data_referencia=args.data,
        db_path=Path(args.db_path),
        output_dir=Path(args.output_dir),
    )
    print(f"Exportado: {caminho}")


if __name__ == "__main__":
    main()
