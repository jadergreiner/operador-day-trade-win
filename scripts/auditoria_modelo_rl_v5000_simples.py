#!/usr/bin/env python3
"""
Auditoria simplificada do modelo RL v5000
Verifica se o modelo está viciado em VENDA ou tem convicção real
"""

import sqlite3
import logging
from pathlib import Path
from collections import Counter
from typing import Optional, Dict, List

# Logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger(__name__)

DB_PATH = Path("data/db/trading_analise.db")  # Usar cópia para evitar lock


def analisar_distribuicao_acoes(conn) -> Dict:
    """Analisa a distribuição de ações (BUY/SELL/HOLD)."""
    logger.info("\n" + "=" * 80)
    logger.info("1️⃣  DISTRIBUIÇÃO DE AÇÕES")
    logger.info("=" * 80)

    cursor = conn.cursor()
    cursor.execute("SELECT action FROM rl_episodes WHERE action IS NOT NULL")
    acoes = [row[0] for row in cursor.fetchall()]

    if not acoes:
        logger.warning("Nenhuma ação encontrada!")
        return {}

    counter = Counter(acoes)
    total = len(acoes)

    logger.info(f"\nTotal de episódios: {total}\n")

    for acao, count in counter.most_common():
        pct = 100 * count / total
        bar = "█" * int(pct / 5)
        logger.info(f"{acao:>10}: {count:>4} ({pct:>6.1f}%) {bar}")

    # Análise da razão SELL/BUY
    sell_count = counter.get('SELL', 0)
    buy_count = counter.get('BUY', 0)
    razao = sell_count / buy_count if buy_count > 0 else 0

    logger.info(f"\n{'─' * 60}")
    logger.info(f"Razão SELL/BUY: {razao:.2f}x")

    if 0.9 <= razao <= 1.1:
        logger.info("✅ Distribuição EQUILIBRADA (sem viço evidente)")
    elif razao > 1.1:
        logger.warning(f"⚠️  TENDÊNCIA A VENDA elevada (razão {razao:.2f}x)")
    else:
        logger.info(f"📌 Tendência a COMPRA (razão {razao:.2f}x)")

    return {
        'total': total,
        'distribuicao': dict(counter),
        'razao_sell_buy': razao
    }


def analisar_confianca(conn) -> Dict:
    """Analisa confiança média por ação."""
    logger.info("\n" + "=" * 80)
    logger.info("2️⃣  CONFIANÇA MÉDIA POR AÇÃO")
    logger.info("=" * 80)

    cursor = conn.cursor()
    query = """
    SELECT
        action,
        COUNT(*) as total,
        ROUND(AVG(overall_confidence), 3) as confianca_media,
        ROUND(MIN(overall_confidence), 3) as confianca_min,
        ROUND(MAX(overall_confidence), 3) as confianca_max
    FROM rl_episodes
    WHERE action IS NOT NULL AND overall_confidence IS NOT NULL
    GROUP BY action
    ORDER BY confianca_media DESC
    """

    cursor.execute(query)
    resultados = cursor.fetchall()

    if not resultados:
        logger.warning("Nenhum dado de confiança encontrado!")
        return {}

    logger.info(f"\n{'Ação':<10} {'Total':<8} {'Média':<10} {'Min':<10} {'Max':<10}")
    logger.info("─" * 60)

    dados = {}
    for row in resultados:
        acao = row[0] or 'NULL'
        total = row[1]
        media = row[2] or 0
        minimo = row[3] or 0
        maximo = row[4] or 0

        logger.info(f"{acao:<10} {total:<8} {media:<10.3f} {minimo:<10.3f} {maximo:<10.3f}")
        dados[acao] = {
            'total': total,
            'media': media,
            'min': minimo,
            'max': maximo
        }

    logger.info("─" * 60)
    logger.info("\n💡 ANÁLISE DE CONVICÇÃO:")

    for acao in ['BUY', 'SELL', 'HOLD']:
        if acao in dados:
            conf = dados[acao]['media']
            if conf >= 0.7:
                logger.info(f"✅ {acao}: Convicção FORTE (confiança {conf:.3f})")
            elif conf >= 0.5:
                logger.info(f"⚠️  {acao}: MODERADA (confiança {conf:.3f})")
            else:
                logger.info(f"📌 {acao}: FRACA (confiança {conf:.3f})")

    return dados


def analisar_preco_mudanca(conn) -> Dict:
    """Analisa movimento de preço associado a cada ação."""
    logger.info("\n" + "=" * 80)
    logger.info("3️⃣  MOVIMENTO DE PREÇO POR AÇÃO")
    logger.info("=" * 80)

    cursor = conn.cursor()
    query = """
    SELECT
        action,
        COUNT(*) as total,
        ROUND(AVG(ABS(CAST(win_price_change_pct AS FLOAT))), 4) as volatilidade,
        ROUND(AVG(CAST(win_price_change_pct AS FLOAT)), 4) as movimento_medio
    FROM rl_episodes
    WHERE action IS NOT NULL AND win_price_change_pct IS NOT NULL
    GROUP BY action
    ORDER BY volatilidade DESC
    """

    cursor.execute(query)
    resultados = cursor.fetchall()

    if not resultados:
        logger.warning("Nenhum dado de preço encontrado!")
        return {}

    logger.info(f"\n{'Ação':<10} {'Total':<8} {'Volatilidade':<15} {'Movimento Médio':<15}")
    logger.info("─" * 60)

    dados = {}
    for row in resultados:
        acao = row[0] or 'NULL'
        total = row[1]
        vol = row[2] or 0
        mov = row[3] or 0

        logger.info(f"{acao:<10} {total:<8} {vol:<15.4f} {mov:<15.4f}")
        dados[acao] = {
            'total': total,
            'volatilidade': vol,
            'movimento_medio': mov
        }

    logger.info("─" * 60)
    logger.info("\n📊 ANÁLISE DE MERCADO:")

    for acao in ['BUY', 'SELL', 'HOLD']:
        if acao in dados:
            vol = dados[acao]['volatilidade']
            mov = dados[acao]['movimento_medio']

            if vol < 0.005:
                logger.info(f"✅ {acao}: Ambiente ESTÁVEL (volatilidade {vol:.4f})")
            elif vol < 0.01:
                logger.info(f"📌 {acao}: Ambiente NORMAL (volatilidade {vol:.4f})")
            else:
                logger.warning(f"⚠️  {acao}: Ambiente VOLÁTIL (volatilidade {vol:.4f})")

    return dados


def calcular_score_vicios(distribuicao: Dict, confianca: Dict, preco: Dict) -> float:
    """Calcula score de viço (0-100, onde 100 = completamente viciado)."""
    logger.info("\n" + "=" * 80)
    logger.info("4️⃣  SCORE DE VIÇO (Bias Score)")
    logger.info("=" * 80)

    score = 0
    razaos = []

    # Fator 1: Desequilíbrio de distribuição (0-30 pontos)
    razao = distribuicao.get('razao_sell_buy', 1)
    desvio = abs(razao - 1.0)

    if desvio > 0.3:  # Mais de 30% desequilibrado
        fator1 = 30
    elif desvio > 0.15:  # Mais de 15% desequilibrado
        fator1 = 15
    else:
        fator1 = 0

    razaos.append(f"Desequilíbrio distribuição: +{fator1:.0f} pontos (razão SELL/BUY: {razao:.2f}x)")
    score += fator1

    # Fator 2: Diferença de confiança entre SELL e BUY (0-20 pontos)
    sell_conf = confianca.get('SELL', {}).get('media', 0.5)
    buy_conf = confianca.get('BUY', {}).get('media', 0.5)
    diff_conf = abs(sell_conf - buy_conf)

    if diff_conf > 0.15:
        fator2 = 20
    elif diff_conf > 0.08:
        fator2 = 10
    else:
        fator2 = 0

    razaos.append(f"Diferença confiança SELL vs BUY: +{fator2:.0f} pontos (diff: {diff_conf:.3f})")
    score += fator2

    # Fator 3: Padrão de preço favorecendo uma ação (0-20 pontos)
    sell_vol = preco.get('SELL', {}).get('volatilidade', 0)
    buy_vol = preco.get('BUY', {}).get('volatilidade', 0)
    diff_vol = abs(sell_vol - buy_vol)

    if diff_vol > 0.005:
        fator3 = 20
    elif diff_vol > 0.002:
        fator3 = 10
    else:
        fator3 = 0

    razaos.append(f"Diferença volatilidade: +{fator3:.0f} pontos (diff: {diff_vol:.4f})")
    score += fator3

    # Fator 4: Distribuição HOLD muito alta (0-20 pontos)
    dist = distribuicao.get('distribuicao', {})
    hold_pct = 100 * dist.get('HOLD', 0) / sum(dist.values()) if dist else 0

    if hold_pct > 60:
        fator4 = 20
    elif hold_pct > 50:
        fator4 = 10
    else:
        fator4 = 0

    razaos.append(f"HOLD muito alto: +{fator4:.0f} pontos (HOLD: {hold_pct:.1f}%)")
    score += fator4

    logger.info(f"\nScore Total: {score:.0f}/100\n")
    for razao in razaos:
        logger.info(f"  • {razao}")

    logger.info("\n" + "─" * 60)
    logger.info("\n🎯 CONCLUSÃO:")

    if score >= 70:
        logger.error(f"🚨 MODELO VICIADO ({score:.0f}/100)")
        logger.error("   → Diagnóstico: Viço CONFIRMADO em VENDA")
        logger.error("   → Recomendação: Ajustar pesos do modelo ou retraining")
    elif score >= 40:
        logger.warning(f"⚠️  SUSPEITA DE VIÇO ({score:.0f}/100)")
        logger.warning("   → Monitorar performance em próximas operações")
    else:
        logger.info(f"✅ MODELO EQUILIBRADO ({score:.0f}/100)")
        logger.info("   → Distribuição natural, sem sinais de viço")
        logger.info("   → Modelo tem CONVICÇÃO REAL, não viço")

    return score


def main():
    """Main execution."""
    logger.info("\n" + "=" * 80)
    logger.info("🔍 AUDITORIA DO MODELO RL v5000")
    logger.info("Pergunta: O modelo está viciado em VENDA ou tem convicção?")
    logger.info("=" * 80)

    if not DB_PATH.exists():
        logger.error(f"❌ Banco de dados não encontrado: {DB_PATH}")
        return

    # Retry logic para banco travado
    import time
    max_retries = 5
    for retry in range(max_retries):
        try:
            # Use read-only mode (URI) para evitar locks
            conn = sqlite3.connect(f'file:{DB_PATH}?mode=ro', uri=True, timeout=10)
            conn.row_factory = sqlite3.Row
            logger.info(f"✅ Conectado (read-only): {DB_PATH}\n")
            break
        except sqlite3.OperationalError as e:
            if "locked" in str(e).lower() and retry < max_retries - 1:
                logger.warning(f"⏳ Banco travado, tentando novamente... (tentativa {retry + 1}/{max_retries})")
                time.sleep(3)
            else:
                logger.error(f"❌ Erro ao conectar: {e}")
                return

    try:

        # Executar análises em ordem
        dist = analisar_distribuicao_acoes(conn)
        conf = analisar_confianca(conn)
        preco = analisar_preco_mudanca(conn)

        # Calcular score final
        score = calcular_score_vicios(dist, conf, preco)

        logger.info("\n" + "=" * 80)
        logger.info("📝 RESUMO FINAL")
        logger.info("=" * 80)
        logger.info(f"\nScore de Viço: {score:.0f}/100")
        logger.info(f"Total de Episódios Analisados: {dist.get('total', 0)}\n")

        conn.close()
        logger.info("✅ Auditoria concluída!\n")

    except Exception as e:
        logger.error(f"❌ Erro durante auditoria: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
