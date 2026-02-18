#!/usr/bin/env python3
"""
Gerador de HeadDirective a partir da análise do BDI B3.

Autor: Head Global de Finanças (IA)
Fonte: BDI_00_20260210.pdf - Boletim Diário de Informações da B3
Data de referência: 10/02/2026 (terça-feira)

Este script analisa os dados extraídos do BDI e gera uma diretiva
para o operador automático de WINFUT (mini-índice Bovespa).
"""

import sys
import os
from datetime import datetime

# Adiciona raiz do projeto ao path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.application.services.head_directives import (
    HeadDirective,
    save_directive,
    load_active_directive,
    create_directives_table,
)

# ────────────────────────────────────────────────────────────────
# ANÁLISE BDI 10/02/2026 - HEAD DE FINANÇAS
# ────────────────────────────────────────────────────────────────

ANALISE_BDI = """
═══════════════════════════════════════════════════════════════
  ANÁLISE BDI B3 - 10/02/2026 (Terça-feira) - Nº 28
  Head Global de Finanças - Mercado Brasileiro Futuro
═══════════════════════════════════════════════════════════════

1. IBOVESPA (Comportamento no Dia):
   - Abertura: 186.241 | Mínimo: 185.083 | Máximo: 186.959
   - Fechamento: 185.929 (-0,16%)
   - MÁXIMO DO ANO atingido em 09/FEV (186.241) - DIA ANTERIOR!
   - Mínimo do ano: 160.538 (02/JAN) → Rally de +15,39% no ano
   - Dia anterior: +1,80% (forte alta)
   - Na semana: +1,63% | No mês: +2,52% | Em 1 mês: +13,81%

2. EVOLUÇÃO SETORIAL (sinais de rotação):
   - IBOV S HBETA: -0,82% (HIGH BETA UNDERPERFORMING forte)
   - IMAT BASICOS: -0,61% (materiais básicos fracos)
   - IFINANCEIRO: -0,30% (bancos recuando)
   - IBOV S LVOL: -0,09% (defensivos resilientes)
   - IMOBILIARIO: +0,55% (imóveis na contramão - positivo)
   - IDIVERSA: +0,19% (diversificado positivo)
   → CONCLUSÃO: Rotação de high beta para defensivos = cautela

3. DI OVER / TAXAS DE JUROS:
   - CDI/Selic: 14,90% | Fator diário: 1,00055131
   - Taxa referência 3 meses: 14,62% | 6 meses: 14,10%
   - CURVA DI INVERTIDA → Mercado precifica CORTES futuros
   - IPCA prévia: 0,33% (mês) | 0,45% (próximo mês)
   → Positivo para equities no médio prazo

4. CÂMBIO:
   - USD/BRL PTAX: 5,2021 | D+1: 5,2031
   - EUR/USD: 1,1890 | BTC: US$ 68.748,96
   → Dólar estável, sem pressão cambial

5. MAIORES OSCILAÇÕES IBOVESPA:
   Altas: BRKM5 +8,27% | MRVE3 +4,17% | RAIL3 +2,77%
   Baixas: ENEV3 -9,66% | RAIZ4 -8,33% | CSNA3 -4,67%
   → ENEV3 foi 2º mais negociado (R$ 2,09B) com queda -9,66%
   → Indica estresse vendedor pontual significativo

6. OPÇÕES (Puts dominantes):
   - ENEVN205 put FEV@20,50: R$ 13,4M volume
   - IBOVO184 put MAR@185.000: R$ 12,6M (proteção no nível atual!)
   - IBOVO189 put MAR@190.000: R$ 8,3M volume
   - ENEVO220 put MAR@22,00: R$ 11,9M
   → Hedging institucional forte no nível 185.000 pontos

7. PARTICIPAÇÃO DOS INVESTIDORES (acumulado Fevereiro):
   - Estrangeiro: Compras R$ 105,4B vs Vendas R$ 102,4B
     → COMPRADOR LÍQUIDO +R$ 2,98B (flow positivo)
   - Institucional: Compras R$ 34,9B vs Vendas R$ 39,4B
     → VENDEDOR LÍQUIDO -R$ 4,52B (realizando lucros)
   - Pessoa Física: neutro (compras ≈ vendas)

8. DERIVATIVOS WIN (Mini-Índice):
   - Volume: 5.651.328 negócios | 18.084.815 contratos
   - Volume financeiro: R$ 673,77 BILHÕES
   - IND (cheio): 9.688 negócios | 54.230 contratos | R$ 10,1B
   - Preço liquidação WIN: 185.742

9. POSIÇÕES EM ABERTO WING26:
   - WING26: 1.176.088 contratos | Variação: -12.345
   - WINJ26: 28.726 contratos | Variação: +3.391
   → OI REDUZINDO no vencimento ativo = posições sendo desfeitas
   → Migração inicial para WINJ26 (+3.391)

═══════════════════════════════════════════════════════════════
  VEREDITO DO HEAD DE FINANÇAS
═══════════════════════════════════════════════════════════════

DIREÇÃO: BULLISH (com cautela)
CONFIANÇA: 62/100

FATORES BULLISH (peso 65%):
  ✓ Flow estrangeiro comprador (+R$ 2,98B)
  ✓ Curva DI invertida → expectativa de cortes de juros
  ✓ Rally sustentado: +15,39% YTD, +13,81% em 1 mês
  ✓ IBOVESPA em máxima do ano (tendência clara de alta)
  ✓ Câmbio estável (sem pressão)
  ✓ IMOBILIARIO e IDIVERSA positivos (setores cíclicos)

FATORES BEARISH (peso 35%):
  ✗ Consolidação após máxima histórica (-0,16% hoje)
  ✗ High beta -0,82% (rotação para defensivos)
  ✗ Institucionais vendedores líquidos (-R$ 4,52B)
  ✗ OI WING26 reduzindo (-12.345 contratos)
  ✗ Heavy put buying em 185.000 (hedging institucional)
  ✗ ENEV3 -9,66% pode contaminar sentimento

ZONAS DE OPERAÇÃO WINFUT:
  - Suporte principal: 185.000-185.100 (mínima do dia + puts)
  - Resistência: 186.900-187.000 (máxima do dia)
  - Zona ideal de compra: 185.000-185.500
  - Zona ideal de venda: 186.500-187.000
  - BUY proibido acima: 187.200 (extensão além da máxima)
  - SELL proibido abaixo: 184.500 (abaixo do suporte forte)

GESTÃO DE RISCO:
  - Aggressividade: MODERATE (mercado em consolidação)
  - Stop loss: 250 pontos (mercado volátil mas com tendência)
  - Max trades/dia: 5 (preservar capital em consolidação)
  - Posição: 100% (confiança razoável no setup)
  - RSI buy max: 72 (evitar comprar sobrecomprado)
  - RSI sell min: 28 (evitar vender sobrevendido)

═══════════════════════════════════════════════════════════════
"""


def gerar_diretiva_bdi_20260210() -> HeadDirective:
    """Gera a HeadDirective baseada na análise do BDI 10/02/2026."""

    directive = HeadDirective(
        # Identificação
        date="2026-02-10",
        created_at=datetime.now().isoformat(),
        source="BDI_B3_20260210_analise_completa",
        analyst="Head Global de Finanças (IA) - Análise BDI",

        # Direção e confiança
        direction="BULLISH",
        confidence_market=62,
        aggressiveness="MODERATE",

        # Gestão de posição
        position_size_pct=100,
        stop_loss_pts=250,
        max_daily_trades=5,

        # Filtros técnicos
        max_rsi_for_buy=72,       # Não comprar com RSI > 72
        min_rsi_for_sell=28,      # Não vender com RSI < 28
        min_adx_for_entry=0,      # Sem filtro ADX

        # Zonas de preço (em pontos WINFUT)
        forbidden_zone_above=187200.0,  # BUY proibido acima (extensão além da máxima)
        forbidden_zone_below=184500.0,  # SELL proibido abaixo (abaixo do suporte forte)
        ideal_buy_zone_low=185000.0,    # Zona ideal compra - inferior (suporte + puts)
        ideal_buy_zone_high=185500.0,   # Zona ideal compra - superior
        ideal_sell_zone_low=186500.0,   # Zona ideal venda - inferior
        ideal_sell_zone_high=187000.0,  # Zona ideal venda - superior (resistência)

        # Eventos macro
        reduce_before_event=False,
        event_description="Sem eventos macro relevantes identificados no BDI. Monitorar agenda BCB/FED.",
        event_time="",

        # Análise e notas
        notes=(
            "ANÁLISE BDI B3 10/02/2026 | IBOV: 185.929 (-0,16%) | "
            "Máxima do ano 186.241 atingida ontem (09/FEV) | "
            "Flow estrangeiro comprador líquido +R$2,98B | "
            "Institucionais vendedores -R$4,52B (realizando lucros) | "
            "DI invertida (14,90% vs 3m 14,62% vs 6m 14,10%) → espera cortes | "
            "High beta -0,82% (rotação defensiva) | "
            "WING26 OI: 1.176.088 (-12.345) → desalavancagem | "
            "WIN volume: 18M contratos / R$673,7B | "
            "Puts IBOV 185k R$12,6M + 190k R$8,3M (hedging) | "
            "ENEV3 -9,66% stress pontual (2º mais negociado R$2,09B) | "
            "Suporte: 185.000-185.100 | Resistência: 186.900-187.000"
        ),
        risk_scenario=(
            "RISCO PRINCIPAL: Consolidação/correção após máximas históricas. "
            "Institucionais realizando lucros (-R$4,52B líquido). "
            "OI WING26 em queda (-12.345) indica desalavancagem. "
            "Puts concentrados em 185.000 podem virar suporte firme. "
            "Se perder 185.000, próximo suporte em 184.500. "
            "RISCO SECUNDÁRIO: ENEV3 -9,66% pode contaminar sentimento "
            "do IBOVESPA na próxima sessão."
        ),

        active=True,
    )

    return directive


def main():
    """Executa a geração e persistência da diretiva BDI."""

    # Resolve caminho do banco
    project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    db_path = os.path.join(project_root, "data", "db", "trading.db")

    print(ANALISE_BDI)
    print("=" * 60)
    print("  GERANDO DIRETIVA PARA O OPERADOR AUTOMÁTICO WINFUT")
    print("=" * 60)

    # Gera a diretiva
    directive = gerar_diretiva_bdi_20260210()

    # Exibe resumo
    print(f"\n  Data: {directive.date}")
    print(f"  Fonte: {directive.source}")
    print(f"  Direção: {directive.direction}")
    print(f"  Confiança: {directive.confidence_market}/100")
    print(f"  Agressividade: {directive.aggressiveness}")
    print(f"  Stop Loss: {directive.stop_loss_pts} pts")
    print(f"  Max Trades/dia: {directive.max_daily_trades}")
    print(f"  RSI Buy Max: {directive.max_rsi_for_buy}")
    print(f"  RSI Sell Min: {directive.min_rsi_for_sell}")
    print(f"  Buy Zone: {directive.ideal_buy_zone_low:.0f}-{directive.ideal_buy_zone_high:.0f}")
    print(f"  Sell Zone: {directive.ideal_sell_zone_low:.0f}-{directive.ideal_sell_zone_high:.0f}")
    print(f"  Forbidden BUY acima: {directive.forbidden_zone_above:.0f}")
    print(f"  Forbidden SELL abaixo: {directive.forbidden_zone_below:.0f}")
    print(f"  Posição: {directive.position_size_pct}%")

    # Persiste no banco
    print(f"\n  DB Path: {db_path}")
    create_directives_table(db_path)
    row_id = save_directive(db_path, directive)
    print(f"  ✓ Diretiva salva com ID: {row_id}")

    # Valida leitura
    loaded = load_active_directive(db_path, directive.date)
    if loaded and loaded.direction == directive.direction:
        print(f"  ✓ Validação OK: load_active_directive retorna direction={loaded.direction}")
        print(f"  ✓ Confiança carregada: {loaded.confidence_market}")
        print(f"  ✓ Notas carregadas: {loaded.notes[:80]}...")
    else:
        print("  ✗ ERRO: Validação falhou!")
        return 1

    print("\n" + "=" * 60)
    print("  DIRETIVA ATIVA - PRONTA PARA USO PELO AGENTE WINFUT")
    print("=" * 60)
    print(f"\n  O agente '{os.path.basename(project_root)}/scripts/agente_micro_tendencia_winfut.py'")
    print(f"  carregará esta diretiva automaticamente via load_active_directive()")
    print(f"  a cada ciclo de análise.\n")

    return 0


if __name__ == "__main__":
    sys.exit(main())
