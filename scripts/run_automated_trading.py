"""
Run Automated Trading - Executa trading automatico 24/7.

Sistema completo:
- Analisa mercado continuamente
- Executa ordens automaticamente
- Gerencia posicoes abertas
- Stop loss e take profit automaticos
- Trailing stop
- Logs detalhados
"""

import sys
from pathlib import Path

project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

import time
from decimal import Decimal
from datetime import datetime, time as dt_time
from config import get_config
from src.application.services.automated_trading import AutomatedTradingEngine
from src.application.services.quantum_operator import QuantumOperatorEngine
from src.domain.value_objects import Symbol, Price, Quantity
from src.domain.enums.trading_enums import OrderSide, TradeSignal
from src.infrastructure.adapters.mt5_adapter import MT5Adapter, TimeFrame


def display_banner():
    """Display startup banner."""
    print("=" * 80)
    print("OPERADOR QUANTICO - TRADING AUTOMATIZADO")
    print("=" * 80)
    print()
    print("Sistema de execucao automatica de trades no MetaTrader 5")
    print()
    print("IMPORTANTE:")
    print("  - Este sistema executa ordens REAIS")
    print("  - Dinheiro REAL esta em risco")
    print("  - Monitore constantemente")
    print("  - Pare imediatamente se houver problemas")
    print()
    print("=" * 80)
    print()


def display_config(
    symbol: Symbol,
    max_positions: int,
    risk_per_trade: Decimal,
    min_confidence: Decimal,
    min_alignment: Decimal,
):
    """Display trading configuration."""
    print("CONFIGURACAO:")
    print(f"  Simbolo:           {symbol}")
    print(f"  Max Posicoes:      {max_positions}")
    print(f"  Risco por Trade:   {risk_per_trade:.1%}")
    print(f"  Confianca Minima:  {min_confidence:.0%}")
    print(f"  Alinhamento Min:   {min_alignment:.0%}")
    print()


def display_market_analysis(
    current_price: Price,
    signal,
    confidence: Decimal,
    alignment: Decimal,
    reasoning: str,
    correlations: dict = None,
    symbol: str = "WING26",
    biases: dict = None
):
    """Display market analysis."""
    now = datetime.now()

    # Mapas de Traducao
    TRADUCAO = {
        "BUY": "COMPRA",
        "SELL": "VENDA",
        "HOLD": "AGUARDAR",
        "BULLISH": "ALTISTA",
        "BEARISH": "BAIXISTA",
        "NEUTRAL": "NEUTRO",
        "Macro": "MACRO",
        "Sent": "SENTIM.",
        "Fund": "FUNDAM.",
        "Tecn": "TECNICO"
    }

    print("-" * 60)
    print(f"[{now.strftime('%H:%M:%S')}] {symbol} | Preco: R$ {current_price.value:,.2f}")

    if correlations:
        corr_parts = []
        if correlations.get("wdo"): corr_parts.append(f"WDO: {correlations['wdo']:,.2f}")
        if correlations.get("wsp"): corr_parts.append(f"WSP: {correlations['wsp']:,.0f}")
        print(f"  Correlacoes: {' | '.join(corr_parts)}")

    # Detalha a confluencia (Biases)
    if biases:
        b_str = []
        # Traducao explicita de chaves e valores
        key_map = {"Macro": "MACRO", "Sent": "SENTIM.", "Fund": "FUNDAM.", "Tecn": "TECNICO"}
        val_map = {"BULLISH": "ALTISTA", "BEARISH": "BAIXISTA", "NEUTRAL": "NEUTRO", "HOLD": "AGUARDAR", "BUY": "COMPRA", "SELL": "VENDA"}

        for k, v in biases.items():
            label = key_map.get(k, k.upper())
            raw_val = v.value if hasattr(v, 'value') else str(v)
            val = val_map.get(raw_val.upper(), raw_val)
            b_str.append(f"{label}: {val}")
        print(f"  Dimensoes  : {' | '.join(b_str)}")

    val_map = {"BULLISH": "ALTISTA", "BEARISH": "BAIXISTA", "NEUTRAL": "NEUTRO", "HOLD": "AGUARDAR", "BUY": "COMPRA", "SELL": "VENDA"}
    raw_signal = signal.value if hasattr(signal, 'value') else str(signal)
    signal_traduzido = val_map.get(raw_signal.upper(), raw_signal)

    print(f"  Sinal      : {signal_traduzido} (Confianca: {confidence:.0%})")
    print(f"  Confluencia: {alignment:.0%}")

    # Motivacao formatada
    safe_reasoning = str(reasoning) if reasoning else "Aguardando alinhamento institucional"
    print(f"  Motivacao  : {safe_reasoning[:120]}")
    print("-" * 60)


def display_positions(positions: list, mt5_positions=None, current_price=None):
    """Display active position management with detailed point/tick data."""
    if not positions and not mt5_positions:
        print("\n  [INFO] Nenhuma posicao aberta no momento.")
        return

    print("\n" + " " + "=" * 62)
    print(" GESTAO ESTRATEGICA DE POSICOES (Dashboard Head Financeiro)")
    print(" " + "=" * 62)

    # Prioriza posicoes reais do MT5 se fornecidas
    if mt5_positions:
        for pos in mt5_positions:
            side_str = "COMPRA" if pos.type == 0 else "VENDA" # 0=BUY, 1=SELL no MT5
            profit = pos.profit

            # Calculo de pontos (Inves de apenas R$)
            # No WIN, cada ponto = R$ 0.20 por contrato.
            points = (profit / (pos.volume * 0.2)) if pos.volume > 0 else 0

            # Progresso ate o Alvo
            dist_to_tp = abs(pos.tp - pos.price_open) if pos.tp > 0 else 0
            current_dist = abs(pos.price_current - pos.price_open)
            progress = (current_dist / dist_to_tp * 100) if dist_to_tp > 0 else 0

            print(f"  TICKET: {pos.ticket} | {side_str} | Lote: {pos.volume}")
            print(f"  PRECO ENTRADA: {pos.price_open:,.0f} | PRECO ATUAL: {pos.price_current:,.0f}")
            print(f"  RESULTADO    : {points:+.0f} PONTOS | R$ {profit:,.2f} ({progress:.1f}% do alvo)")
            print(f"  GESTOES SL/TP: SL {pos.sl:,.0f} | TP {pos.tp:,.0f}")
            print("-" * 62)
    else:
        for pos in positions:
            side_str = "COMPRA" if pos.side == OrderSide.BUY else "VENDA"
            pnl_str = f"R$ {pos.unrealized_pnl:,.2f}"
            print(f"  TICKET: {pos.ticket} | {side_str} ({pos.quantity.value})")
            print(f"  ENTRADA: {pos.entry_price.value:,.2f} | PnL: {pnl_str}")
            print(f"  ALVOS: SL {pos.stop_loss.value:,.2f} | TP {pos.take_profit.value:,.2f}")
            print("-" * 62)

    print(" " + "=" * 62 + "\n")


def display_entry(
    ticket: str,
    side,
    entry_price: Price,
    stop_loss: Price,
    take_profit: Price,
    quantity: Quantity,
):
    """Display trade entry."""
    print("=" * 80)
    print("[ENTRADA] ORDEM EXECUTADA COM SUCESSO")
    print("=" * 80)
    print(f"  Ticket:       {ticket}")
    print(f"  Direcao:      {side.value}")
    print(f"  Entrada:      R$ {entry_price.value:,.2f}")
    print(f"  Stop Loss:    R$ {stop_loss.value:,.2f}")
    print(f"  Take Profit:  R$ {take_profit.value:,.2f}")
    print(f"  Quantidade:   {quantity.value} contrato(s)")
    risk = abs(entry_price.value - stop_loss.value)
    reward = abs(take_profit.value - entry_price.value)
    rr_ratio = reward / risk if risk > 0 else 0
    print(f"  R/R Ratio:    {rr_ratio:.2f}")
    print("=" * 80)
    print()


def display_exit(result):
    """Display trade exit."""
    print("=" * 80)
    print("[SAIDA] POSICAO FECHADA")
    print("=" * 80)
    print(f"  Ticket:       {result.ticket}")
    print(f"  Direcao:      {result.side.value}")
    print(f"  Entrada:      R$ {result.entry_price.value:,.2f}")
    print(f"  Saida:        R$ {result.exit_price.value:,.2f}")
    print(f"  PnL:          R$ {result.pnl:,.2f} ({result.pnl_percent:+.2f}%)")
    print(f"  Duracao:      {result.duration_seconds}s")
    print(f"  Razao:        {result.exit_reason}")
    print("=" * 80)
    print()


def display_statistics(stats: dict, daily_pnl: Decimal):
    """Display trading statistics."""
    print("-" * 80)
    print("ESTATISTICAS DO DIA")
    print("-" * 80)
    print(f"  Total Trades:     {stats['total_trades']}")
    print(f"  Ganhos:           {stats['winners']}")
    print(f"  Perdas:           {stats['losers']}")
    print(f"  Win Rate:         {stats['win_rate']:.1f}%")
    print(f"  PnL Total:        R$ {daily_pnl:,.2f}")
    print(f"  Media Ganho:      R$ {stats['avg_win']:,.2f}")
    print(f"  Media Perda:      R$ {stats['avg_loss']:,.2f}")
    print(f"  Posicoes Abertas: {stats['open_positions']}")
    print("-" * 80)
    print()


def is_market_open() -> bool:
    """Check if market is open."""
    now = datetime.now().time()
    market_open = dt_time(9, 0)
    market_close = dt_time(17, 30)
    return market_open <= now <= market_close


def run_automated_trading():
    """Main trading loop."""

    display_banner()

    # Configuration
    config = get_config()
    symbol = Symbol(config.trading_symbol)

    # ========================================================================
    # CONFIGURACOES DE TRADING - AJUSTE AQUI
    # ========================================================================

    # POSICOES E CONTRATOS
    MAX_POSITIONS = 5000  # Rumo aos 5k contratos
    CONTRACTS_PER_TRADE = 1  # Abrindo 1 por vez para manter granularidade e esconder o player

    # GESTAO DE RISCO
    RISK_PER_TRADE = Decimal("0.0001")  # Risco ínfimo por tique individual (1 contrato)

    # FILTROS DE QUALIDADE (DAY TRADE AMBIÇÃO HEAD)
    MIN_CONFIDENCE = Decimal("0.20")  # Aumentando agressividade para escalar lote
    MIN_ALIGNMENT = Decimal("0.10")   # Reduzindo exigência de alinhamento para o plano de 5k

    # PERFORMANCE
    ANALYSIS_INTERVAL = 10  # Análise mais rápida (10s) para escalar rápido

    # TRAILING STOP
    USE_TRAILING_STOP = True
    TRAILING_DISTANCE_PERCENT = Decimal("0.5")  # 0.5% de distancia

    # ========================================================================

    print("CONFIGURACAO ATUAL:")
    print(f"  Max Operacoes Simultaneas: {MAX_POSITIONS}")
    print(f"  Contratos por Operacao:    {CONTRACTS_PER_TRADE}")
    print(f"  Total Potencial:           {MAX_POSITIONS * CONTRACTS_PER_TRADE} contratos")
    print(f"  Risco por Trade:           {RISK_PER_TRADE:.1%}")
    print(f"  Confianca Minima:          {MIN_CONFIDENCE:.0%}")
    print(f"  Alinhamento Minimo:        {MIN_ALIGNMENT:.0%}")
    print(f"  Trailing Stop:             {'SIM' if USE_TRAILING_STOP else 'NAO'} ({TRAILING_DISTANCE_PERCENT}%)")
    print()

    display_config(symbol, MAX_POSITIONS, RISK_PER_TRADE, MIN_CONFIDENCE, MIN_ALIGNMENT)

    # Connect to MT5
    print("Conectando ao MT5...")
    mt5 = MT5Adapter(
        login=config.mt5_login,
        password=config.mt5_password,
        server=config.mt5_server,
    )

    if not mt5.connect():
        print("[ERRO] Falha ao conectar ao MT5")
        return

    print("[OK] Conectado ao MT5")
    print()

    # Get account info
    try:
        balance = mt5.get_account_balance()
        print(f"Saldo da Conta: R$ {balance:,.2f}")
        print()
    except Exception as e:
        print(f"[AVISO] Nao foi possivel obter saldo: {e}")
        print()

    # Initialize engines
    operator = QuantumOperatorEngine()
    trading_engine = AutomatedTradingEngine(
        mt5_adapter=mt5,
        quantum_operator=operator,
        max_positions=MAX_POSITIONS,
        risk_per_trade=RISK_PER_TRADE,
        min_confidence=MIN_CONFIDENCE,
        min_alignment=MIN_ALIGNMENT,
        use_trailing_stop=USE_TRAILING_STOP,
        trailing_distance_percent=TRAILING_DISTANCE_PERCENT,
    )

    print("=" * 80)
    print("SISTEMA INICIADO - MONITORANDO MERCADO")
    print("=" * 80)
    print()
    print("Pressione Ctrl+C para parar")
    print()

    last_stats_display = datetime.now()
    iteration = 0
    decisions_log = []

    try:
        while True:
            try:
                iteration += 1

                # Check if market is open
                if not is_market_open():
                    if iteration == 1 or iteration % 60 == 0:  # Log every 30 minutes
                        print(f"[{datetime.now().strftime('%H:%M:%S')}] Mercado fechado. Aguardando...")
                    time.sleep(ANALYSIS_INTERVAL)
                    continue

                # Get current market data
                candles = mt5.get_candles(symbol, TimeFrame.M5, count=100)

                if not candles:
                    print("[ERRO] Falha ao obter dados do mercado")
                    time.sleep(ANALYSIS_INTERVAL)
                    continue

                current_candle = candles[-1]
                current_price = current_candle.close

                # Manage open positions first
                trading_engine.manage_open_positions(current_price)

                # Check if we can open new position
                if not trading_engine.can_open_position():
                    # Just monitor
                    if iteration % 10 == 0:  # Log every 5 minutes
                        print(f"[{datetime.now().strftime('%H:%M:%S')}] Monitorando posicao aberta...")
                    time.sleep(ANALYSIS_INTERVAL)
                    continue

                # Get correlations in real-time
                try:
                    # S&P 500
                    try:
                        wsp_tick = mt5.get_current_tick(Symbol("WSP"))
                        us_futures = wsp_tick.last.value if wsp_tick and wsp_tick.last else Decimal("5000")
                    except:
                        us_futures = Decimal("5000")

                    # Dollar
                    try:
                        wdo_tick = mt5.get_current_tick(Symbol("WDO"))
                        usd_brl = wdo_tick.last.value if wdo_tick and wdo_tick.last else Decimal("5.85")
                    except:
                        usd_brl = Decimal("5.85")

                    # Blue Chips
                    try:
                        petr_tick = mt5.get_current_tick(Symbol("PETR4"))
                        petr4 = petr_tick.last.value if petr_tick and petr_tick.last else None
                    except:
                        petr4 = None

                    try:
                        vale_tick = mt5.get_current_tick(Symbol("VALE"))
                        vale3 = vale_tick.last.value if vale_tick and vale_tick.last else None
                    except:
                        vale3 = None

                    # EWZ BDR
                    try:
                        bewz_tick = mt5.get_current_tick(Symbol("BEWZ39"))
                        bewz39 = bewz_tick.last.value if bewz_tick and bewz_tick.last else None
                    except:
                        bewz39 = None

                except Exception as e:
                    # print(f"[AVISO] Erro ao buscar correlacoes: {e}")
                    us_futures = Decimal("5000")
                    usd_brl = Decimal("5.85")
                    petr4 = None
                    vale3 = None
                    bewz39 = None

                # Analyze market
                decision = operator.analyze_and_decide(
                    symbol=symbol,
                    candles=candles,
                    us_futures=us_futures,
                    dollar_index=Decimal("104.3"),
                    vix=Decimal("16.5"),
                    selic=Decimal("10.75"),
                    ipca=Decimal("4.5"),
                    usd_brl=usd_brl,
                    embi_spread=250,
                    petr4=petr4,
                    vale3=vale3,
                    bewz39=bewz39,
                )

                # Log decision for session summary
                decisions_log.append({
                    "timestamp": decision.timestamp.isoformat(),
                    "symbol": symbol.code,
                    "action": decision.action.value,
                    "confidence": float(decision.confidence),
                    "alignment": float(decision.alignment_score),
                    "reasoning": decision.primary_reason
                })

                # Display analysis
                display_market_analysis(
                    current_price=current_price,
                    signal=decision.action,
                    confidence=decision.confidence,
                    alignment=decision.alignment_score,
                    reasoning=decision.primary_reason,
                    correlations={
                        "wdo": usd_brl,
                        "wsp": us_futures
                    },
                    symbol=symbol.code,
                    biases={
                        "Macro": decision.macro_bias,
                        "Sent": decision.sentiment_bias,
                        "Fund": decision.fundamental_bias,
                        "Tecn": decision.technical_bias
                    }
                )

                # Gestao da Posicao (Dashboard) - Busca posicoes reais do MT5
                actual_positions = mt5._mt5.positions_get(symbol=symbol.code)
                if not actual_positions:
                    # Tenta buscar sem o sufixo ou todas as posicoes para garantir
                    actual_positions = mt5._mt5.positions_get()

                display_positions(trading_engine.open_positions, mt5_positions=actual_positions)

                # Check if should enter trade
                if trading_engine.should_enter_trade(
                    signal=decision.action,
                    confidence=decision.confidence,
                    alignment=decision.alignment_score,
                ):
                    # Get recommended entry
                    if decision.recommended_entry:
                        entry = decision.recommended_entry

                        # Position size (usa CONTRACTS_PER_TRADE configurado no topo)
                        quantity = Quantity(Decimal(str(CONTRACTS_PER_TRADE)))

                        # Execute entry
                        print(f"[{datetime.now().strftime('%H:%M:%S')}] EXECUTANDO ENTRADA AUTOMATICA...")

                        ticket = trading_engine.execute_entry(
                            symbol=symbol,
                            signal=decision.action,
                            entry_price=entry.entry_price,
                            stop_loss=entry.stop_loss,
                            take_profit=entry.take_profit,
                            quantity=quantity,
                        )

                        if ticket:
                            display_entry(
                                ticket=ticket,
                                side=OrderSide.BUY if decision.action == TradeSignal.BUY else OrderSide.SELL,
                                entry_price=entry.entry_price,
                                stop_loss=entry.stop_loss,
                                take_profit=entry.take_profit,
                                quantity=quantity,
                            )

                # Display statistics every 5 minutes
                if (datetime.now() - last_stats_display).seconds >= 300:
                    actual_positions = mt5._mt5.positions_get(symbol=symbol.code)
                    if not actual_positions: actual_positions = mt5._mt5.positions_get()

                    stats = trading_engine.get_statistics(mt5_positions=actual_positions)
                    daily_pnl = trading_engine.get_daily_pnl()
                    display_statistics(stats, daily_pnl)
                    last_stats_display = datetime.now()

                # Wait before next iteration
                print(f"  Aguardando {ANALYSIS_INTERVAL}s para proxima analise...")
                time.sleep(ANALYSIS_INTERVAL)

            except Exception as e:
                print(f"[{datetime.now().strftime('%H:%M:%S')}] [ERRO NO LOOP] {e}")
                import traceback
                traceback.print_exc()
                time.sleep(10) # Pausa curta antes de tentar novamente

    except KeyboardInterrupt:
        print()
        print("=" * 80)
        print("SISTEMA INTERROMPIDO PELO USUARIO")
        print("=" * 80)
        print()

        # Close all open positions
        if trading_engine.open_positions:
            print("Fechando posicoes abertas...")
            for position in trading_engine.open_positions[:]:
                current_price = mt5.get_current_tick(symbol).last
                trading_engine.execute_exit(position, current_price, "MANUAL")
            print("[OK] Todas posicoes fechadas")
            print()

    # Final statistics
    try:
        actual_positions = mt5._mt5.positions_get(symbol=symbol.code)
        if not actual_positions: actual_positions = mt5._mt5.positions_get()

        stats = trading_engine.get_statistics(mt5_positions=actual_positions)
        daily_pnl = trading_engine.get_daily_pnl()

        print("=" * 80)
        print("RESULTADO FINAL DO DIA")
        print("=" * 80)
        display_statistics(stats, daily_pnl)

        # Persistencia de Sessao - Salvando em JSON para o proximo restart
        import json
        save_path = Path("data/db/last_session_summary.json")
        save_path.parent.mkdir(parents=True, exist_ok=True)
        with open(save_path, "w") as f:
            session_data = {
                "timestamp": datetime.now().isoformat(),
                "daily_pnl": float(daily_pnl),
                "daily_stats": stats,
                "decisions": decisions_log[-50:], # Ultimas 50 decisoes
                "total_trades": stats["total_trades"],
                "win_rate": float(stats["win_rate"]),
                "last_symbol": symbol.code
            }
            json.dump(session_data, f, indent=4)
        print(f"[OK] Sessao persistida em {save_path}")
    except Exception as e:
        print(f"[AVISO] Erro ao salvar resumo da sessao: {e}")

        print("Sistema encerrado.")

    finally:
        mt5.disconnect()
        print("[OK] Desconectado do MT5")


if __name__ == "__main__":
    run_automated_trading()
