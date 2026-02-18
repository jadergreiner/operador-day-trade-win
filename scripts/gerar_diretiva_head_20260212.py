#!/usr/bin/env python3
"""
Gera e salva HeadDirective para 12/02/2026.

Análise completa:
- Sessão Asiática: MISTA-POSITIVA (KOSPI +3.13%, Nikkei flat em ATH, HSI -0.86%)
- Sessão Europeia: POSITIVA FORTE (DAX +1.34%, FTSE recorde, CAC +0.93%)
- EUA: S&P -0.33% ontem, Dow futuros subem, VIX +3.57% (payroll)
- Brasil: IBOV 189.699 (+2.03%), WING26 gap down ~1.290 pts

Lições incorporadas:
1. Agente ficou em HOLD perpetuo em dia de +4.5% — confiança nunca passou 0.4
2. Compra em RSI 83-85 custou -215 pts → filtro RSI ≤ 72
3. Zonas desatualizadas (185k-187k) → atualizar para 188.5k-191k
4. Payroll 10:30 → reduce_before_event = True
5. Stop mais apertado (350 pts) para limitar dano
"""

import sys
import os
from datetime import datetime

# Adiciona root do projeto ao path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.application.services.head_directives import (
    HeadDirective,
    save_directive,
    load_active_directive,
    create_directives_table,
)

DB_PATH = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "data", "db", "trading.db"
)


def main():
    directive = HeadDirective(
        # Identificação
        date="2026-02-12",
        created_at=datetime.now().isoformat(),
        source="diario_head_20260212_sessoes_globais",
        analyst="Head Global de Finanças (IA)",

        # Direção e confiança
        direction="BULLISH",
        confidence_market=58,
        aggressiveness="MODERATE",

        # Gestão de posição
        position_size_pct=80,        # Reduzido de 100% por risco Payroll
        stop_loss_pts=350,           # Stop firme — lição de 10/02
        max_daily_trades=4,          # Conservar capital para pós-Payroll

        # Filtros técnicos
        max_rsi_for_buy=72,          # LIÇÃO CRÍTICA: compra em RSI 83 custou -215 pts
        min_rsi_for_sell=28,         # Não vender em oversold extremo
        min_adx_for_entry=0,         # Sem filtro ADX

        # Zonas de preço (ATUALIZADAS para range atual)
        forbidden_zone_above=191500, # Não perseguir ATH — lição de 10/02
        forbidden_zone_below=188000, # Piso de suporte — não vender abaixo
        ideal_buy_zone_low=188500,   # Gap fill de hoje, suporte intraday
        ideal_buy_zone_high=189500,  # Topo da zona de valor
        ideal_sell_zone_low=190800,  # Base da resistência (pico ontem 190.870)
        ideal_sell_zone_high=191300, # Topo da zona de resistência

        # Eventos macro
        reduce_before_event=True,
        event_description="Non-Farm Payroll (EUA) — risco binário alto; VIX +3.57%",
        event_time="10:30",

        # Notas estratégicas
        notes=(
            "LIÇÕES 11/02: Agente ficou em HOLD a 0.4 conf durante +4.5% rally. "
            "Zero trades. Momentum não foi capturado. "
            "HOJE: (1) BUY permitido somente em zona 188.5k-189.5k com RSI<72. "
            "(2) SELL em 190.8k-191.3k. (3) ZERAR posição até 10:00 BRT — Payroll 10:30. "
            "(4) Pós-payroll reavaliar trend e reentrar. "
            "(5) Europa FORTE (DAX +1.34%, FTSE ATH) suporta viés bull. "
            "(6) Asia mista, China fraca. "
            "CONFIANÇA 58% reflete desconto pelo Payroll — sem o evento seria 68%."
        ),
        risk_scenario=(
            "CENÁRIO DE RISCO: Payroll muito forte → Fed hawkish → USD sobe → "
            "emergentes caem. WING26 pode testar 187.500. "
            "MITIGAÇÃO: position 80%, stop 350 pts, fechar pré-10:00, max 4 trades. "
            "SE payroll em linha/fraco → rally retoma → target 191.000+."
        ),

        # Estado
        active=True,
    )

    # Salva no banco
    directive_id = save_directive(DB_PATH, directive)
    print(f"\n{'='*65}")
    print(f"  ✅ HeadDirective salva com sucesso!")
    print(f"  ID: {directive_id}")
    print(f"  Data: {directive.date}")
    print(f"  Direção: {directive.direction}")
    print(f"  Confiança: {directive.confidence_market}%")
    print(f"  Agressividade: {directive.aggressiveness}")
    print(f"  Tamanho Posição: {directive.position_size_pct}%")
    print(f"  Stop Loss: {directive.stop_loss_pts} pts")
    print(f"  Max Trades: {directive.max_daily_trades}")
    print(f"  RSI máx BUY: {directive.max_rsi_for_buy}")
    print(f"  RSI mín SELL: {directive.min_rsi_for_sell}")
    print(f"  🚫 BUY proibido acima: {directive.forbidden_zone_above:.0f}")
    print(f"  🚫 SELL proibido abaixo: {directive.forbidden_zone_below:.0f}")
    print(f"  ✅ Zona ideal BUY: {directive.ideal_buy_zone_low:.0f} - {directive.ideal_buy_zone_high:.0f}")
    print(f"  ✅ Zona ideal SELL: {directive.ideal_sell_zone_low:.0f} - {directive.ideal_sell_zone_high:.0f}")
    print(f"  ⚠️  Evento: {directive.event_description}")
    print(f"  ⚠️  Horário: {directive.event_time}")
    print(f"  📝 Reduce Pre-Event: {directive.reduce_before_event}")
    print(f"{'='*65}")

    # Valida carregamento
    loaded = load_active_directive(DB_PATH, "2026-02-12")
    if loaded and loaded.direction == "BULLISH" and loaded.confidence_market == 58:
        print(f"\n  ✅ Validação OK — Diretiva carregada corretamente do banco.")
        print(f"     Direction: {loaded.direction}, Conf: {loaded.confidence_market}%")
        print(f"     Zones: BUY {loaded.ideal_buy_zone_low:.0f}-{loaded.ideal_buy_zone_high:.0f}, "
              f"SELL {loaded.ideal_sell_zone_low:.0f}-{loaded.ideal_sell_zone_high:.0f}")
        print(f"     Evento: {loaded.event_description} ({loaded.event_time})")
    else:
        print(f"\n  ❌ ERRO: Diretiva não carregou corretamente!")


if __name__ == "__main__":
    main()
