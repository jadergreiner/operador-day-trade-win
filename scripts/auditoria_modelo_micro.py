"""
Script de auditoria do modelo LightGBM do Micro Tendencia.

Uso:
    python scripts/auditoria_modelo_micro.py [--db-path PATH]

Saida:
    - Versao atual em producao e data de treino
    - Win rate real dos rewards acumulados
    - Quantos episodios desde o ultimo treino
    - Recomendacao: retreinar agora? sim/nao com justificativa

Referencia: docs/BACKLOG.md (CALIBRACAO-MICRO-05)
Status: v1.0 (18/03/2026)
"""

from __future__ import annotations

import argparse
import json
import sqlite3
import sys
from datetime import datetime
from pathlib import Path

# Adiciona raiz do projeto no sys.path
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from src.application.retreino_micro_tendencia import (
    TriggerRetreino,
    THRESHOLD_REWARDS_NOVO_TREINO,
)

DB_PATH_PADRAO = str(ROOT / "data" / "db" / "trading.db")


def _conectar(db_path: str) -> sqlite3.Connection:
    """Abre conexao SQLite em modo read-only via URI.

    Args:
        db_path: Caminho para o banco.

    Returns:
        Conexao SQLite.
    """
    return sqlite3.connect(db_path)


def obter_versao_ativa(conn: sqlite3.Connection) -> dict[str, object] | None:
    """Retorna metadados da versao de modelo ativa.

    Args:
        conn: Conexao SQLite aberta.

    Returns:
        Dict com versao, data_treino, win_rate_validacao, n_episodios;
        ou None se tabela vazia.
    """
    try:
        cur = conn.cursor()
        cur.execute(
            "SELECT versao, data_treino, win_rate_validacao, n_episodios, notas "
            "FROM model_metadata WHERE ativo = 1 ORDER BY id DESC LIMIT 1"
        )
        row = cur.fetchone()
        if row is None:
            return None
        return {
            "versao": row[0],
            "data_treino": row[1],
            "win_rate_validacao": float(row[2]),
            "n_episodios": int(row[3]),
            "notas": row[4] or "",
        }
    except Exception:
        return None


def contar_episodios_banco(conn: sqlite3.Connection) -> int:
    """Conta episodios em micro_episodios.

    Args:
        conn: Conexao SQLite aberta.

    Returns:
        Total de registros em micro_episodios.
    """
    try:
        cur = conn.cursor()
        cur.execute("SELECT COUNT(*) FROM micro_episodios")
        row = cur.fetchone()
        return int(row[0]) if row else 0
    except Exception:
        return 0


def calcular_win_rate_real(conn: sqlite3.Connection, janela: int = 500) -> float:
    """Calcula win rate real dos ultimos N episodios.

    Args:
        conn: Conexao SQLite aberta.
        janela: Numero maximo de episodios a consultar.

    Returns:
        Win rate entre 0.0 e 1.0.
    """
    try:
        cur = conn.cursor()
        cur.execute(
            "SELECT outcome FROM micro_episodios "
            "WHERE outcome IS NOT NULL "
            "ORDER BY timestamp_entrada DESC LIMIT ?",
            (janela,),
        )
        rows = cur.fetchall()
        if not rows:
            return 0.0
        total = len(rows)
        wins = sum(1 for r in rows if r[0] == "WIN")
        return wins / total
    except Exception:
        return 0.0


def contar_rewards_total(conn: sqlite3.Connection) -> int:
    """Conta total de rewards avaliados.

    Args:
        conn: Conexao SQLite aberta.

    Returns:
        Total de registros avaliados em rl_rewards.
    """
    try:
        cur = conn.cursor()
        cur.execute("SELECT COUNT(*) FROM rl_rewards WHERE is_evaluated = 1")
        row = cur.fetchone()
        return int(row[0]) if row else 0
    except Exception:
        return 0


def contar_rewards_ultimo_treino(conn: sqlite3.Connection) -> int:
    """Retorna n_rewards_no_treino do ultimo registro em rl_training_metrics.

    Args:
        conn: Conexao SQLite aberta.

    Returns:
        n_rewards do ultimo treino, ou 0 se nunca treinou.
    """
    try:
        cur = conn.cursor()
        cur.execute(
            "SELECT n_rewards_no_treino FROM rl_training_metrics "
            "ORDER BY id DESC LIMIT 1"
        )
        row = cur.fetchone()
        return int(row[0]) if row else 0
    except Exception:
        return 0


def gerar_recomendacao(
    novos_rewards: int,
    win_rate_real: float,
    versao_ativa: dict[str, object] | None,
    threshold: int,
) -> str:
    """Gera recomendacao textual sobre necessidade de retreino.

    Args:
        novos_rewards: Rewards acumulados desde ultimo treino.
        win_rate_real: Win rate dos episodios recentes.
        versao_ativa: Metadados da versao ativa, ou None.
        threshold: Threshold minimo de rewards para retreinar.

    Returns:
        String com recomendacao clara.
    """
    if versao_ativa is None:
        return (
            "RETREINAR IMEDIATAMENTE — Nenhum modelo registrado em "
            "model_metadata. Primeiro retreino necessario."
        )

    win_rate_anterior = float(versao_ativa.get("win_rate_validacao") or 0.0)
    delta_pp = (win_rate_real - win_rate_anterior) * 100.0

    if novos_rewards >= threshold:
        if delta_pp < -5.0:
            return (
                f"RETREINAR IMEDIATAMENTE — {novos_rewards} novos rewards "
                f"(threshold: {threshold}) E degradacao de {abs(delta_pp):.1f}pp "
                f"vs versao anterior."
            )
        return (
            f"RETREINAR — {novos_rewards} novos rewards acumulados "
            f"(threshold: {threshold}). Delta win rate: {delta_pp:+.1f}pp."
        )

    if novos_rewards >= threshold // 2:
        return (
            f"MONITORAR — {novos_rewards} novos rewards ({threshold - novos_rewards} "
            f"faltando para threshold). Delta win rate: {delta_pp:+.1f}pp."
        )

    return (
        f"NAO RETREINAR — Apenas {novos_rewards} novos rewards "
        f"(threshold: {threshold}). Aguardar acumulo."
    )


def formatar_relatorio(
    versao_ativa: dict[str, object] | None,
    n_episodios_total: int,
    win_rate_real: float,
    rewards_total: int,
    rewards_ultimo_treino: int,
    novos_rewards: int,
    recomendacao: str,
    db_path: str,
) -> str:
    """Formata relatorio de auditoria em texto legivel.

    Args:
        versao_ativa: Metadados da versao ativa.
        n_episodios_total: Total de episodios no banco.
        win_rate_real: Win rate calculado dos episodios recentes.
        rewards_total: Total de rewards avaliados.
        rewards_ultimo_treino: Rewards no momento do ultimo treino.
        novos_rewards: Diferenca (novos desde ultimo treino).
        recomendacao: Texto da recomendacao gerada.
        db_path: Caminho do banco auditado.

    Returns:
        String formatada em texto com marcadores.
    """
    agora = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    linhas = [
        "=" * 60,
        "AUDITORIA MODELO MICRO TENDENCIA",
        f"Data/hora: {agora}",
        f"Banco:     {db_path}",
        "=" * 60,
        "",
        "[ VERSAO ATIVA ]",
    ]

    if versao_ativa:
        linhas += [
            f"  Versao:            {versao_ativa['versao']}",
            f"  Data treino:       {versao_ativa['data_treino']}",
            f"  Win rate validacao:{versao_ativa['win_rate_validacao']:.3f}",
            f"  Episodios usados:  {versao_ativa['n_episodios']}",
            f"  Notas:             {versao_ativa['notas']}",
        ]
    else:
        linhas.append("  NENHUM MODELO REGISTRADO (model_metadata vazia)")

    linhas += [
        "",
        "[ EPISODIOS E REWARDS ]",
        f"  Total micro_episodios:      {n_episodios_total}",
        f"  Win rate real (janela 500): {win_rate_real:.3f} "
        f"({win_rate_real * 100:.1f}%)",
        f"  Total rewards avaliados:    {rewards_total}",
        f"  Rewards no ultimo treino:   {rewards_ultimo_treino}",
        f"  Novos rewards acumulados:   {novos_rewards}",
        f"  Threshold retreino:         {THRESHOLD_REWARDS_NOVO_TREINO}",
        "",
        "[ RECOMENDACAO ]",
        f"  {recomendacao}",
        "",
        "=" * 60,
    ]
    return "\n".join(linhas)


def main() -> None:
    """Ponto de entrada do script de auditoria."""
    parser = argparse.ArgumentParser(
        description="Auditoria do modelo LightGBM do Micro Tendencia."
    )
    parser.add_argument(
        "--db-path",
        default=DB_PATH_PADRAO,
        help=f"Caminho para o banco SQLite (padrao: {DB_PATH_PADRAO})",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Saida em formato JSON",
    )
    args = parser.parse_args()

    db_path: str = args.db_path
    trigger = TriggerRetreino(db_path)

    try:
        conn = _conectar(db_path)
    except Exception as exc:
        print(f"ERRO: Nao foi possivel abrir o banco: {exc}", file=sys.stderr)
        sys.exit(1)

    versao_ativa = obter_versao_ativa(conn)
    n_episodios_total = contar_episodios_banco(conn)
    win_rate_real = calcular_win_rate_real(conn)
    rewards_total = contar_rewards_total(conn)
    rewards_ultimo_treino = contar_rewards_ultimo_treino(conn)
    conn.close()

    novos_rewards = trigger.novos_rewards_desde_ultimo_treino()
    recomendacao = gerar_recomendacao(
        novos_rewards=novos_rewards,
        win_rate_real=win_rate_real,
        versao_ativa=versao_ativa,
        threshold=THRESHOLD_REWARDS_NOVO_TREINO,
    )

    if args.json:
        dados: dict[str, object] = {
            "timestamp": datetime.now().isoformat(),
            "db_path": db_path,
            "versao_ativa": versao_ativa,
            "n_episodios_total": n_episodios_total,
            "win_rate_real": win_rate_real,
            "rewards_total": rewards_total,
            "rewards_ultimo_treino": rewards_ultimo_treino,
            "novos_rewards": novos_rewards,
            "threshold_retreino": THRESHOLD_REWARDS_NOVO_TREINO,
            "recomendacao": recomendacao,
        }
        print(json.dumps(dados, indent=2, ensure_ascii=False))
    else:
        relatorio = formatar_relatorio(
            versao_ativa=versao_ativa,
            n_episodios_total=n_episodios_total,
            win_rate_real=win_rate_real,
            rewards_total=rewards_total,
            rewards_ultimo_treino=rewards_ultimo_treino,
            novos_rewards=novos_rewards,
            recomendacao=recomendacao,
            db_path=db_path,
        )
        print(relatorio)


if __name__ == "__main__":
    main()
