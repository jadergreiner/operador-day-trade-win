#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Auditoria do Modelo RL v5000 - Analisa viés de VENDA vs convicção real.

Verifica:
1. Distribuição de ações (BUY, SELL, HOLD)
2. Taxa de sucesso por ação
3. Comparação com recompensas reais
4. Detecção de viés comportamental
"""

import sqlite3
from pathlib import Path
from collections import Counter
import logging

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s'
)
logger = logging.getLogger(__name__)

ROOT_DIR = Path(__file__).parent.parent
DB_PATH = ROOT_DIR / "data" / "db" / "trading.db"


def conectar_banco():
    """Conecta ao banco de episódios RL."""
    try:
        conn = sqlite3.connect(str(DB_PATH))
        conn.row_factory = sqlite3.Row
        logger.info(f"Conectado ao banco: {DB_PATH}")
        return conn
    except Exception as e:
        logger.error(f"Erro ao conectar: {e}")
        return None


def analisar_distribuicao_acoes(conn):
    """Analisa distribuição de ações (BUY, SELL, HOLD)."""
    logger.info("\n" + "=" * 80)
    logger.info("1️⃣  DISTRIBUIÇÃO DE AÇÕES")
    logger.info("=" * 80)

    query = """
    SELECT
        action,
        COUNT(*) as total,
        ROUND(100.0 * COUNT(*) / (SELECT COUNT(*) FROM rl_episodes), 1) as percentual
    FROM rl_episodes
    WHERE action IS NOT NULL
    GROUP BY action
    ORDER BY total DESC
    """

    try:
        cursor = conn.cursor()
        cursor.execute(query)
        resultados = cursor.fetchall()

        if not resultados:
            logger.warning("Nenhum episódio encontrado!")
            return None

        total_episodios = sum(r['total'] for r in resultados)

        logger.info(f"\nTotal de episódios: {total_episodios}")
        logger.info("-" * 60)

        for row in resultados:
            acao = row['action'] or 'NULL'
            total = row['total']
            pct = row['percentual']

            # Visual bar
            barra = "█" * int(pct / 5)
            logger.info(f"{acao:10} | {barra:20} | {total:4} ({pct:5.1f}%)")

        logger.info("-" * 60)

        # Verificar viés
        vendas = next((r['total'] for r in resultados if r['action'] == 'SELL'), 0)
        compras = next((r['total'] for r in resultados if r['action'] == 'BUY'), 0)

        if vendas > 0 and compras > 0:
            razao = vendas / compras
            logger.info(f"\nRazão SELL/BUY: {razao:.2f}x")
            if razao > 1.5:
                logger.warning(f"⚠️  VIÉS DETECTADO: Modelo prefere VENDA {razao:.2f}x mais que COMPRA")
            elif razao < 0.67:
                logger.warning(f"⚠️  VIÉS DETECTADO: Modelo prefere COMPRA {1/razao:.2f}x mais que VENDA")
            else:
                logger.info(f"✅ Distribuição equilibrada (SELL/BUY = {razao:.2f}x)")

        return resultados

    except Exception as e:
        logger.error(f"Erro na análise: {e}")
        return None


def analisar_taxa_sucesso(conn):
    """Analisa taxa de sucesso por ação."""
    logger.info("\n" + "=" * 80)
    logger.info("2️⃣  TAXA DE SUCESSO POR AÇÃO (Dados de Episódios)")
    logger.info("=" * 80)

    query = """
    SELECT
        action,
        COUNT(*) as total_episodios,
        ROUND(AVG(overall_confidence), 2) as confianca_media
    FROM rl_episodes
    WHERE action IS NOT NULL
    GROUP BY action
    ORDER BY total_episodios DESC
    """

    try:
        cursor = conn.cursor()
        cursor.execute(query)
        resultados = cursor.fetchall()

        if not resultados:
            logger.warning("Nenhum dado de ação encontrado!")
            return None

        logger.info(f"\n{'Ação':<10} {'Total':<10} {'Confiança Média':<18}")
        logger.info("-" * 60)

        for row in resultados:
            acao = row['action'] or 'NULL'
            total = row['total_episodios']
            conf = row['confianca_media'] or 0

            logger.info(f"{acao:<10} {total:<10} {conf:<18.2f}")

        logger.info("-" * 60)

        # Análise de convicção
        logger.info("\n💡 ANÁLISE DE CONVICÇÃO:")
        for row in resultados:
            acao = row['action']
            conf = row['confianca_media'] or 0

            if conf >= 0.7:
                logger.info(f"✅ {acao}: Convicção FORTE (confiança {conf:.2f})")
            elif conf >= 0.5:
                logger.info(f"⚠️  {acao}: Moderado (confiança {conf:.2f})")
            else:
                logger.warning(f"❌ {acao}: FRACO (confiança {conf:.2f})")

        return resultados

    except Exception as e:
        logger.error(f"Erro na análise: {e}")
        return None


def analisar_correlacao_preco(conn):
    """Analisa se ação está correlacionada com movimento de preço."""
    logger.info("\n" + "=" * 80)
    logger.info("3️⃣  CORRELAÇÃO AÇÃO × MOVIMENTO DE PREÇO")
    logger.info("=" * 80)

    query = """
    SELECT
        action,
        COUNT(*) as total,
        ROUND(AVG(win_price_change_pct), 2) as media_movimento_pct,
        ROUND(MIN(win_price_change_pct), 2) as min_movimento_pct,
        ROUND(MAX(win_price_change_pct), 2) as max_movimento_pct
    FROM rl_episodes
    WHERE action IS NOT NULL AND win_price_change_pct IS NOT NULL
    GROUP BY action
    ORDER BY action
    """

    try:
        cursor = conn.cursor()
        cursor.execute(query)
        resultados = cursor.fetchall()

        if not resultados:
            logger.warning("Nenhum dado de preço encontrado!")
            return None

        logger.info(f"\n{'Ação':<10} {'Total':<8} {'Movimento Médio':<18} {'Min':<10} {'Max':<10}")
        logger.info("-" * 80)

        for row in resultados:
            acao = row['action']
            total = row['total']
            media = row['media_movimento_pct'] or 0
            min_mov = row['min_movimento_pct'] or 0
            max_mov = row['max_movimento_pct'] or 0

            movimento_str = f"{media:+.2f}%"
            logger.info(f"{acao:<10} {total:<8} {movimento_str:<18} {min_mov:+.2f}%   {max_mov:+.2f}%")

        logger.info("-" * 80)

        # Análise de alinhamento
        logger.info("\n🎯 ALINHAMENTO AÇÃO × MERCADO:")
        for row in resultados:
            acao = row['action']
            media = row['media_movimento_pct'] or 0

            if acao == 'BUY' and media > 0:
                logger.info(f"✅ {acao}: Modelo compra em alta correta! (movimento +{media:.2f}%)")
            elif acao == 'BUY' and media < 0:
                logger.warning(f"❌ {acao}: Modelo compra se ENGANANDO (movimento {media:.2f}%)")
            elif acao == 'SELL' and media < 0:
                logger.info(f"✅ {acao}: Modelo vende com RAZÃO! (movimento {media:.2f}%)")
            elif acao == 'SELL' and media > 0:
                logger.warning(f"❌ {acao}: Modelo VENDE ERRADO (movimento +{media:.2f}%)")

        return resultados

    except Exception as e:
        logger.error(f"Erro na análise: {e}")
        return None


def calcular_score_vicios(conn):
    """Calcula score indicando viço do modelo."""
    logger.info("\n" + "=" * 80)
    logger.info("4️⃣  SCORE DE VIÇO (BIAS DETECTION)")
    logger.info("=" * 80)

    # Método 1: Distribuição de ações
    query_dist = """
    SELECT action, COUNT(*) as cnt
    FROM rl_episodes
    WHERE action IS NOT NULL
    GROUP BY action
    """

    try:
        cursor = conn.cursor()
        cursor.execute(query_dist)
        dist = {row['action']: row['cnt'] for row in cursor.fetchall()}

        sell_pct = dist.get('SELL', 0) / sum(dist.values()) * 100 if dist else 0
        buy_pct = dist.get('BUY', 0) / sum(dist.values()) * 100 if dist else 0

        logger.info(f"\nDistribuição Observada:")
        logger.info(f"  - SELL: {sell_pct:.1f}%")
        logger.info(f"  - BUY:  {buy_pct:.1f}%")

        # Score de viço (0-100, onde 100 = totalmente viciado)
        vicios = []

        # Viço 1: Preferência extrema por VENDA
        if sell_pct > 70:
            vicios.append(("VENDA excessiva", sell_pct - 50))
        elif buy_pct > 70:
            vicios.append(("COMPRA excessiva", buy_pct - 50))

        # Viço 2: Taxa de sucesso muito baixa em uma ação
        query_wr = """
        SELECT action,
               ROUND(100.0 * SUM(CASE WHEN r.reward_normalized > 0 THEN 1 ELSE 0 END) /
                     NULLIF(COUNT(r.id), 0), 1) as win_rate
        FROM rl_episodes e
        LEFT JOIN rl_rewards r ON e.episode_id = r.episode_id AND r.is_evaluated = 1
        WHERE action IS NOT NULL
        GROUP BY action
        """
        cursor.execute(query_wr)
        wr_data = {row['action']: row['win_rate'] or 0 for row in cursor.fetchall()}

        if (wr := wr_data.get('SELL', 0)) < 40:
            vicios.append(("VENDA com win rate baixo", 40 - wr))
        if (wr := wr_data.get('BUY', 0)) < 40:
            vicios.append(("COMPRA com win rate baixo", 40 - wr))

        logger.info(f"\nVíços Detectados:")
        if vicios:
            for vicio, score in vicios:
                logger.warning(f"  ⚠️  {vicio} (gravidade: {score:.1f})")
        else:
            logger.info("  ✅ Nenhum viço crítico detectado")

        # Score final
        score_total = sum(s for _, s in vicios)
        if score_total > 50:
            logger.warning(f"\n🚨 SCORE TOTAL: {score_total:.1f}/100 - MODELO VICIADO")
        elif score_total > 20:
            logger.warning(f"\n⚠️  SCORE TOTAL: {score_total:.1f}/100 - Viço moderado")
        else:
            logger.info(f"\n✅ SCORE TOTAL: {score_total:.1f}/100 - Comportamento saudável")

        return score_total

    except Exception as e:
        logger.error(f"Erro no cálculo: {e}")
        return 0


def main():
    """Executa auditoria completa."""
    logger.info("\n" + "=" * 80)
    logger.info("🔍 AUDITORIA DO MODELO RL v5000")
    logger.info("Verificando: Viço vs Convicção")
    logger.info("=" * 80)

    conn = conectar_banco()
    if not conn:
        logger.error("Não foi possível conectar ao banco!")
        return

    try:
        # 1. Distribuição de ações
        dist = analisar_distribuicao_acoes(conn)

        # 2. Taxa de sucesso
        success = analisar_taxa_sucesso(conn)

        # 3. Correlação preço
        corr = analisar_correlacao_preco(conn)

        # 4. Score de viço
        score = calcular_score_vicios(conn)

        # Conclusão
        logger.info("\n" + "=" * 80)
        logger.info("📊 CONCLUSÃO")
        logger.info("=" * 80)

        if score > 50:
            logger.warning(
                "\n❌ MODELO ESTÁ VICIADO\n"
                "   Recomendação: Retreinar com dados balanceados ou ajustar reward function"
            )
        elif score > 20:
            logger.info(
                "\n⚠️  TENDÊNCIA MODERADA\n"
                "   Recomendação: Monitorar e coletar mais episódios para validação"
            )
        else:
            logger.info(
                "\n✅ MODELO COM CONVICÇÃO\n"
                "   O modelo está tomando decisões baseadas em análise, não vícios"
            )

    finally:
        conn.close()
        logger.info("\nBanco desconectado.")


if __name__ == "__main__":
    main()
