"""
Teste do Novo Modelo Day Trade - Pesos Hierárquicos.

Testa o novo modelo com dados atuais do mercado.
"""

import sys
from pathlib import Path

project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from decimal import Decimal
from src.application.services.quantum_operator import QuantumOperatorEngine
from src.infrastructure.adapters.mt5_adapter import MT5Adapter
from src.domain.value_objects import Symbol
from config.settings import TradingConfig

def main():
    print("=" * 80)
    print("TESTE DO NOVO MODELO DAY TRADE - PESOS HIERARQUICOS")
    print("=" * 80)
    print()
    print("MODELO:")
    print("  - Sentimento (50%) + Tecnica (30%) = 80% (CORE intraday)")
    print("  - Fundamentos (15%) + Macro (5%) = 20% (Contexto)")
    print("  - Threshold: 65% (reduzido de 75%)")
    print()
    print("=" * 80)
    print()

    # Load config
    config = TradingConfig()

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

    print("[OK] Conectado!")
    print()

    # Get market data
    symbol = Symbol("WING26")
    candles = mt5.get_candles(
        symbol=symbol,
        timeframe="M5",
        count=500,
    )

    opening_price = candles[0].close.value
    current_price = candles[-1].close.value

    print(f"Simbolo:  {symbol}")
    print(f"Abertura: R$ {opening_price:,.2f}")
    print(f"Atual:    R$ {current_price:,.2f}")
    print(f"Variacao: {((current_price - opening_price) / opening_price * 100):+.2f}%")
    print()
    print("=" * 80)
    print()

    # Create operator
    operator = QuantumOperatorEngine()

    # Analyze
    print("Analisando mercado com NOVO MODELO...")
    print()

    decision = operator.analyze_and_decide(
        symbol=symbol,
        candles=candles,
        # Macro
        dollar_index=Decimal("104.3"),
        vix=Decimal("16.5"),
        treasury_yield=Decimal("4.5"),
        us_futures=Decimal("0.2"),
        # Fundamentos
        selic=Decimal("10.75"),
        ipca=Decimal("4.5"),
        usd_brl=Decimal("5.85"),
        embi_spread=250,
    )

    print("RESULTADO DA ANALISE:")
    print("=" * 80)
    print()

    # COMPARACAO ANTES/DEPOIS
    print("DIMENSOES:")
    print(f"  Macro:       {decision.macro_bias:10} (peso: 5%)")
    print(f"  Fundamentos: {decision.fundamental_bias:10} (peso: 15%)")
    print(f"  Sentimento:  {decision.sentiment_bias:10} (peso: 50%) <- CORE")
    print(f"  Tecnica:     {decision.technical_bias:10} (peso: 30%) <- CORE")
    print()

    # Verificar alinhamento CORE
    core_aligned = (
        decision.sentiment_bias == decision.technical_bias
        and decision.sentiment_bias != "NEUTRAL"
    )

    print("ALINHAMENTO CORE (Sentimento + Tecnica):")
    if core_aligned:
        print(f"  [OK] ALINHADOS em {decision.sentiment_bias}")
        print(f"       -> Peso combinado: 80%")
    else:
        print(f"  [X] NAO ALINHADOS")
        print(f"      Sentimento: {decision.sentiment_bias}")
        print(f"      Tecnica:    {decision.technical_bias}")
    print()

    print("METRICAS FINAIS:")
    print(f"  Alinhamento (ponderado): {decision.alignment_score:.1%}")
    print(f"  Confianca:               {decision.confidence:.1%}")
    print(f"  Threshold:               65%")
    print()

    if decision.confidence >= Decimal("0.65"):
        print("  [OK] CONFIANCA >= 65% - PRONTO PARA OPERAR!")
    else:
        print("  [X] CONFIANCA < 65% - AGUARDANDO")
    print()

    print("DECISAO FINAL:")
    print(f"  Acao:     {decision.action.value}")
    print(f"  Urgencia: {decision.urgency}")
    print()

    if decision.recommended_entry:
        print(f"  Entrada:  R$ {decision.recommended_entry.price.value:,.2f}")
        print(f"  Stop:     R$ {decision.recommended_entry.stop_loss.value:,.2f}")
        print(f"  Target:   R$ {decision.recommended_entry.take_profit.value:,.2f}")
        print(f"  R/R:      {decision.recommended_entry.risk_reward_ratio:.2f}")
    else:
        print("  [!] Sem setup tecnico definido")
    print()

    print("=" * 80)
    print()

    # ANALISE COMPARATIVA
    print("ANALISE COMPARATIVA COM MODELO ANTIGO:")
    print("-" * 80)
    print()
    print("MODELO ANTIGO (75% threshold, peso igual):")
    print("  - Exigia 3/4 dimensoes alinhadas")
    print("  - Fundamentos BULLISH bloqueava venda intraday")
    print("  - Resultado: HOLD (confianca 40%, alinhamento 50%)")
    print()
    print("MODELO NOVO (65% threshold, pesos hierarquicos):")
    if core_aligned and decision.confidence >= Decimal("0.65"):
        print("  - Sentimento + Tecnica ALINHADOS = core 80%")
        print(f"  - Confianca {decision.confidence:.0%} >= 65%")
        print(f"  - Resultado: {decision.action.value} (operaria!)")
        print()
        print("  [!] DIFERENCA: Modelo novo OPERARIA, modelo antigo NAO")
    else:
        print("  - Sentimento e Tecnica NAO alinhados OU sem setup")
        print(f"  - Resultado: {decision.action.value}")
        print()
        print("  [=] Ambos modelos chegam na mesma conclusao: HOLD")
    print()

    print("=" * 80)
    print("TESTE CONCLUIDO")
    print("=" * 80)

    mt5.disconnect()


if __name__ == "__main__":
    main()
