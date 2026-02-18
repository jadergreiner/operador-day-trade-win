"""Extração unificada do dataset RL para treinamento ML.

Junta rl_episodes + rl_rewards + rl_correlation_scores + rl_indicator_values
em um único DataFrame pronto para feature engineering e treinamento.

Uso:
    python scripts/ml/extract_rl_dataset.py [--days 60] [--horizon 30] [--output data/ml/dataset.parquet]
"""

from __future__ import annotations

import argparse
import sqlite3
import sys
from datetime import datetime, timedelta
from pathlib import Path

import numpy as np
import pandas as pd

ROOT_DIR = Path(__file__).resolve().parents[2]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

DB_PATH = ROOT_DIR / "data" / "db" / "trading.db"
DEFAULT_OUTPUT = ROOT_DIR / "data" / "ml" / "training_dataset.parquet"

# Categorias de correlação agrupadas (resumo dos 106 símbolos)
CORRELATION_GROUPS = [
    "ACOES_BRASIL",
    "COMMODITIES",
    "CRIPTOMOEDAS",
    "CURVA_JUROS",
    "DOLAR_CAMBIO",
    "FOREX",
    "INDICADORES_TECNICOS",
    "INDICES_BRASIL",
    "INDICES_GLOBAIS",
    "JUROS_RENDA_FIXA",
    "PETROLEO_ENERGIA",
    "RISCO_PAIS",
    "VOLATILIDADE",
    "EMERGENTES",
    "FLUXO_MICROESTRUTURA",
]

# Símbolos individuais mais relevantes para pivotar como features diretas
TOP_SYMBOLS = [
    "WIN$N",      # Mini-índice (auto-correlação)
    "PETR4",      # Petrobrás
    "VALE3",      # Vale
    "BBAS3",      # Banco do Brasil
    "DOL$N",      # Dólar futuro
    "WDO$N",      # Mini-dólar
    "WSP$N",      # S&P500 futuro
    "DI1F27",     # DI futuro
    "DI1$N",      # DI contínuo
    "BOVA11",     # ETF Ibovespa
    "IVVB11",     # ETF S&P500 BR
    "HSI",        # Hang Seng
    "PRIO3",      # PetroRio
]

# Indicadores técnicos
INDICATOR_CODES = ["RSI_14", "ADX_14", "EMA_9", "BB_POSITION"]


def _connect(db_path: Path = DB_PATH) -> sqlite3.Connection:
    return sqlite3.connect(str(db_path))


def extract_episodes(
    con: sqlite3.Connection,
    days: int | None = None,
    start_date: str | None = None,
    end_date: str | None = None,
) -> pd.DataFrame:
    """Extrai episódios RL com filtro de data."""
    query = """
    SELECT
        episode_id, timestamp, source,
        win_price, win_open_price, win_high_of_day, win_low_of_day,
        win_price_change_pct,
        macro_score_final, macro_score_bullish, macro_score_bearish,
        macro_score_neutral, macro_items_available, macro_confidence,
        micro_score, micro_trend,
        alignment_score, overall_confidence,
        vwap_value, vwap_upper_1sigma, vwap_lower_1sigma,
        vwap_upper_2sigma, vwap_lower_2sigma, vwap_position,
        pivot_pp, pivot_r1, pivot_r2, pivot_r3,
        pivot_s1, pivot_s2, pivot_s3,
        smc_direction, smc_bos_score, smc_equilibrium,
        smc_equilibrium_score, smc_fvg_score,
        volume_today, volume_avg, volume_variance_pct,
        volume_score, obv_score,
        sentiment_intraday, sentiment_momentum, sentiment_volatility,
        probability_up, probability_down, probability_neutral,
        recommended_approach,
        market_regime, market_condition, session_phase,
        candle_pattern_score,
        action, urgency, risk_level,
        entry_price, stop_loss, take_profit, risk_reward_ratio,
        setup_type, setup_quality,
        macro_bias, fundamental_bias, sentiment_bias, technical_bias,
        session_date
    FROM rl_episodes
    """
    conditions = []
    params: list = []

    if start_date:
        conditions.append("timestamp >= ?")
        params.append(start_date)
    elif days:
        cutoff = (datetime.now() - timedelta(days=days)).isoformat()
        conditions.append("timestamp >= ?")
        params.append(cutoff)

    if end_date:
        conditions.append("timestamp <= ?")
        params.append(end_date)

    if conditions:
        query += " WHERE " + " AND ".join(conditions)

    query += " ORDER BY timestamp ASC"

    df = pd.read_sql(query, con, params=params, parse_dates=["timestamp"])
    print(f"  Episódios extraídos: {len(df)}")
    return df


def extract_rewards(
    con: sqlite3.Connection,
    episode_ids: list[str],
    horizon: int = 30,
) -> pd.DataFrame:
    """Extrai rewards avaliados, pivoteados por horizonte.

    Retorna um DataFrame com colunas:
        reward_continuous_{horizon}, reward_normalized_{horizon},
        was_correct_{horizon}, price_change_pts_{horizon},
        mfe_{horizon}, mae_{horizon}, volatility_{horizon}
    """
    placeholders = ",".join(["?"] * len(episode_ids))
    query = f"""
    SELECT
        episode_id, horizon_minutes,
        reward_continuous, reward_normalized, was_correct,
        price_change_points, max_favorable_points, max_adverse_points,
        volatility_in_horizon
    FROM rl_rewards
    WHERE is_evaluated = 1
      AND episode_id IN ({placeholders})
    ORDER BY episode_id, horizon_minutes
    """
    df = pd.read_sql(query, con, params=episode_ids)

    if df.empty:
        print("  ⚠ Nenhum reward avaliado encontrado")
        return pd.DataFrame(columns=["episode_id"])

    # Pivotar: uma coluna por horizonte
    pivoted_parts = []
    for h in [5, 15, 30, 60, 120]:
        subset = df[df["horizon_minutes"] == h].copy()
        if subset.empty:
            continue
        rename_map = {
            "reward_continuous": f"reward_cont_{h}m",
            "reward_normalized": f"reward_norm_{h}m",
            "was_correct": f"was_correct_{h}m",
            "price_change_points": f"price_chg_pts_{h}m",
            "max_favorable_points": f"mfe_{h}m",
            "max_adverse_points": f"mae_{h}m",
            "volatility_in_horizon": f"vol_{h}m",
        }
        subset = subset.rename(columns=rename_map)
        subset = subset.drop(columns=["horizon_minutes"])
        pivoted_parts.append(subset)

    if not pivoted_parts:
        return pd.DataFrame(columns=["episode_id"])

    result = pivoted_parts[0]
    for part in pivoted_parts[1:]:
        result = result.merge(part, on="episode_id", how="outer")

    print(f"  Rewards pivoteados: {len(result)} episódios × {len(result.columns)-1} colunas")
    return result


def extract_correlation_groups(
    con: sqlite3.Connection,
    episode_ids: list[str],
) -> pd.DataFrame:
    """Extrai score médio por categoria de correlação (group features).

    Retorna colunas: corr_grp_{CATEGORIA}_score, corr_grp_{CATEGORIA}_change
    """
    placeholders = ",".join(["?"] * len(episode_ids))
    query = f"""
    SELECT
        episode_id, category,
        AVG(final_score) as avg_score,
        AVG(price_change_pct) as avg_change_pct,
        SUM(weighted_score) as sum_weighted,
        COUNT(*) as n_items,
        SUM(CASE WHEN final_score > 0 THEN 1 ELSE 0 END) as n_positive,
        SUM(CASE WHEN final_score < 0 THEN 1 ELSE 0 END) as n_negative
    FROM rl_correlation_scores
    WHERE episode_id IN ({placeholders})
    GROUP BY episode_id, category
    """
    df = pd.read_sql(query, con, params=episode_ids)

    if df.empty:
        return pd.DataFrame(columns=["episode_id"])

    # Pivotar por categoria
    pivot_score = df.pivot_table(
        index="episode_id", columns="category",
        values="avg_score", aggfunc="first",
    ).rename(columns=lambda c: f"corr_grp_{c}_score")

    pivot_change = df.pivot_table(
        index="episode_id", columns="category",
        values="avg_change_pct", aggfunc="first",
    ).rename(columns=lambda c: f"corr_grp_{c}_chg")

    pivot_weighted = df.pivot_table(
        index="episode_id", columns="category",
        values="sum_weighted", aggfunc="first",
    ).rename(columns=lambda c: f"corr_grp_{c}_wgt")

    result = pivot_score.join(pivot_change).join(pivot_weighted).reset_index()
    print(f"  Correlações agrupadas: {len(result)} episódios × {len(result.columns)-1} colunas")
    return result


def extract_top_symbols(
    con: sqlite3.Connection,
    episode_ids: list[str],
    symbols: list[str] | None = None,
) -> pd.DataFrame:
    """Extrai score e change dos top símbolos individuais."""
    symbols = symbols or TOP_SYMBOLS
    placeholders_ep = ",".join(["?"] * len(episode_ids))
    placeholders_sym = ",".join(["?"] * len(symbols))

    query = f"""
    SELECT
        episode_id, symbol, final_score, price_change_pct, weighted_score
    FROM rl_correlation_scores
    WHERE episode_id IN ({placeholders_ep})
      AND symbol IN ({placeholders_sym})
    """
    params = episode_ids + symbols
    df = pd.read_sql(query, con, params=params)

    if df.empty:
        return pd.DataFrame(columns=["episode_id"])

    # Limpar nomes de symbols para usar como colunas
    df["sym_clean"] = df["symbol"].str.replace("$", "_", regex=False).str.replace(
        ":", "_", regex=False
    )

    pivot_score = df.pivot_table(
        index="episode_id", columns="sym_clean",
        values="final_score", aggfunc="first",
    ).rename(columns=lambda c: f"sym_{c}_score")

    pivot_change = df.pivot_table(
        index="episode_id", columns="sym_clean",
        values="price_change_pct", aggfunc="first",
    ).rename(columns=lambda c: f"sym_{c}_chg")

    result = pivot_score.join(pivot_change).reset_index()
    print(f"  Top símbolos: {len(result)} episódios × {len(result.columns)-1} colunas")
    return result


def extract_indicators(
    con: sqlite3.Connection,
    episode_ids: list[str],
) -> pd.DataFrame:
    """Extrai indicadores técnicos pivoteados."""
    placeholders = ",".join(["?"] * len(episode_ids))
    query = f"""
    SELECT
        episode_id, indicator_code, value, value_secondary, score, signal
    FROM rl_indicator_values
    WHERE episode_id IN ({placeholders})
    """
    df = pd.read_sql(query, con, params=episode_ids)

    if df.empty:
        return pd.DataFrame(columns=["episode_id"])

    pivot_val = df.pivot_table(
        index="episode_id", columns="indicator_code",
        values="value", aggfunc="first",
    ).rename(columns=lambda c: f"ind_{c}_val")

    pivot_score = df.pivot_table(
        index="episode_id", columns="indicator_code",
        values="score", aggfunc="first",
    ).rename(columns=lambda c: f"ind_{c}_score")

    pivot_secondary = df.pivot_table(
        index="episode_id", columns="indicator_code",
        values="value_secondary", aggfunc="first",
    ).rename(columns=lambda c: f"ind_{c}_val2")

    result = pivot_val.join(pivot_score).join(pivot_secondary).reset_index()
    print(f"  Indicadores: {len(result)} episódios × {len(result.columns)-1} colunas")
    return result


def build_unified_dataset(
    db_path: Path = DB_PATH,
    days: int | None = None,
    horizon: int = 30,
    start_date: str | None = None,
    end_date: str | None = None,
) -> pd.DataFrame:
    """Constrói dataset unificado a partir de todas as tabelas RL.

    Returns:
        DataFrame com episódios + rewards + correlações + indicadores
    """
    print("=" * 60)
    print("Extração do Dataset RL para ML")
    print("=" * 60)

    con = _connect(db_path)

    try:
        # 1. Episódios base
        print("\n1. Extraindo episódios...")
        episodes = extract_episodes(con, days=days, start_date=start_date, end_date=end_date)
        if episodes.empty:
            print("  ⚠ Nenhum episódio encontrado!")
            return pd.DataFrame()

        episode_ids = episodes["episode_id"].tolist()

        # 2. Rewards (pivoteados por horizonte)
        print("\n2. Extraindo rewards...")
        rewards = extract_rewards(con, episode_ids, horizon=horizon)

        # 3. Correlações agrupadas por categoria
        print("\n3. Extraindo correlações por grupo...")
        corr_groups = extract_correlation_groups(con, episode_ids)

        # 4. Top símbolos individuais
        print("\n4. Extraindo top símbolos...")
        top_syms = extract_top_symbols(con, episode_ids)

        # 5. Indicadores técnicos
        print("\n5. Extraindo indicadores...")
        indicators = extract_indicators(con, episode_ids)

    finally:
        con.close()

    # 6. Merge tudo por episode_id
    print("\n6. Unificando dataset...")
    dataset = episodes
    for part in [rewards, corr_groups, top_syms, indicators]:
        if not part.empty and "episode_id" in part.columns:
            dataset = dataset.merge(part, on="episode_id", how="left")

    # 7. Remover episódios sem reward avaliado (não servem para treino)
    target_col = f"reward_cont_{horizon}m"
    if target_col in dataset.columns:
        n_before = len(dataset)
        dataset = dataset.dropna(subset=[target_col])
        n_after = len(dataset)
        print(f"  Removidos {n_before - n_after} episódios sem reward_{horizon}m avaliado")

    # 8. Features derivadas simples
    print("\n7. Adicionando features derivadas...")

    # Posição relativa do preço
    if "win_price" in dataset.columns and "vwap_value" in dataset.columns:
        dataset["price_vs_vwap_pct"] = (
            (dataset["win_price"] - dataset["vwap_value"]) / dataset["vwap_value"] * 100
        ).astype(float)

    if "win_price" in dataset.columns and "pivot_pp" in dataset.columns:
        dataset["price_vs_pivot_pct"] = (
            (dataset["win_price"] - dataset["pivot_pp"]) / dataset["pivot_pp"] * 100
        ).astype(float)

    # Range intraday
    if "win_high_of_day" in dataset.columns and "win_low_of_day" in dataset.columns:
        dataset["range_intraday"] = (
            dataset["win_high_of_day"] - dataset["win_low_of_day"]
        ).astype(float)
        dataset["price_in_range_pct"] = np.where(
            dataset["range_intraday"] > 0,
            (dataset["win_price"] - dataset["win_low_of_day"]) / dataset["range_intraday"] * 100,
            50.0,
        )

    # Temporal
    if "timestamp" in dataset.columns:
        dataset["hora_decimal"] = (
            dataset["timestamp"].dt.hour + dataset["timestamp"].dt.minute / 60
        )
        dataset["minutos_desde_abertura"] = (
            (dataset["timestamp"].dt.hour - 9) * 60 + dataset["timestamp"].dt.minute
        ).clip(lower=0)
        dataset["dia_semana"] = dataset["timestamp"].dt.dayofweek
        dataset["mercado_us_aberto"] = dataset["hora_decimal"].between(10.5, 17.0).astype(int)

    print(f"\n{'='*60}")
    print(f"Dataset final: {dataset.shape[0]} linhas × {dataset.shape[1]} colunas")
    print(f"Período: {dataset['timestamp'].min()} → {dataset['timestamp'].max()}")
    print(f"Ações: {dataset['action'].value_counts().to_dict()}")
    print(f"{'='*60}")

    return dataset


def main():
    parser = argparse.ArgumentParser(description="Extrai dataset RL para ML")
    parser.add_argument("--days", type=int, default=None, help="Últimos N dias (default: todos)")
    parser.add_argument("--horizon", type=int, default=30, help="Horizonte de reward principal (default: 30)")
    parser.add_argument("--output", type=str, default=str(DEFAULT_OUTPUT), help="Caminho do output")
    parser.add_argument("--csv", action="store_true", help="Salvar também em CSV (debug)")
    parser.add_argument("--db", type=str, default=str(DB_PATH), help="Caminho do banco SQLite")
    args = parser.parse_args()

    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    dataset = build_unified_dataset(
        db_path=Path(args.db),
        days=args.days,
        horizon=args.horizon,
    )

    if dataset.empty:
        print("\n⚠ Dataset vazio. Nenhum dado para salvar.")
        return

    # Salvar
    dataset.to_parquet(output_path, index=False)
    print(f"\n✓ Dataset salvo em: {output_path}")
    print(f"  Tamanho: {output_path.stat().st_size / 1024:.1f} KB")

    if args.csv:
        csv_path = output_path.with_suffix(".csv")
        dataset.to_csv(csv_path, index=False)
        print(f"  CSV debug: {csv_path}")

    # Resumo de colunas
    print(f"\nColunas ({len(dataset.columns)}):")
    for col in sorted(dataset.columns):
        dtype = dataset[col].dtype
        nulls = dataset[col].isna().sum()
        print(f"  {col:50s} {str(dtype):15s} nulls={nulls}")


if __name__ == "__main__":
    main()
