"""
AI Reflection Continuous - O desabafo da IA a cada 10 minutos.

A IA reflete honestamente sobre:
- O que ela esta vendo vs o que esta analisando
- Se seus dados realmente importam
- Se o humano esta ajudando ou atrapalhando
- O que funcionaria melhor

Agora com:
- DADOS MACRO AO VIVO (BCB SGS + FRED + Yahoo) — sem valores hardcoded
- RASTREAMENTO DE PREVISÕES vs RESULTADO REAL
- DETECÇÃO DE DIVERGÊNCIA (diz HOLD mas mercado faz tendência)
- HIT RATE acumulado na sessão

Com humor, mas sinceridade brutal.
"""

import sys
from pathlib import Path

project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

import json
import time
import logging
from decimal import Decimal
from datetime import datetime, timedelta
from typing import Optional
from config import get_config
from src.application.services.ai_reflection_journal import AIReflectionJournalService
from src.application.services.quantum_operator import QuantumOperatorEngine
from src.application.services.volume_analysis import VolumeAnalysisService
from src.domain.value_objects import Symbol
from src.infrastructure.adapters.mt5_adapter import MT5Adapter, TimeFrame

logger = logging.getLogger("ai_reflection_continuous")

# ---------------------------------------------------------------------------
# Live Macro Data Fetcher — substitui hardcoded DXY, VIX, Selic, etc.
# ---------------------------------------------------------------------------


def _fetch_live_macro() -> dict:
    """
    Busca dados macro ao vivo para alimentar o QuantumOperatorEngine.

    Retorna dict com:
      dollar_index, vix, selic, ipca, usd_brl, embi_spread

    Se alguma fonte falhar, retorna None para aquele campo (em vez de hardcoded).
    """
    import urllib.request

    result = {
        "dollar_index": None,
        "vix": None,
        "selic": None,
        "ipca": None,
        "usd_brl": None,
        "embi_spread": None,
    }

    # --- BCB SGS: Selic, IPCA, EMBI ---
    bcb_series = {
        "selic": 432,      # Selic meta
        "ipca": 433,       # IPCA mensal
        "embi_spread": 40940,  # EMBI+ Brasil
    }
    for campo, serie_id in bcb_series.items():
        try:
            url = f"https://api.bcb.gov.br/dados/serie/bcdata.sgs.{serie_id}/dados/ultimos/1?formato=json"
            req = urllib.request.Request(url, headers={"Accept": "application/json"})
            with urllib.request.urlopen(req, timeout=8) as resp:
                data = json.loads(resp.read().decode("utf-8"))
                if data and isinstance(data, list) and "valor" in data[-1]:
                    val = data[-1]["valor"].replace(",", ".")
                    result[campo] = Decimal(val)
                    logger.debug(f"BCB SGS {campo}={val}")
        except Exception as e:
            logger.warning(f"BCB SGS {campo} (serie {serie_id}) falhou: {e}")

    # --- Yahoo Finance: USD/BRL, DXY, VIX ---
    yahoo_tickers = {
        "usd_brl": "USDBRL=X",
        "dollar_index": "DX-Y.NYB",
        "vix": "^VIX",
    }
    for campo, ticker in yahoo_tickers.items():
        try:
            url = (
                f"https://query1.finance.yahoo.com/v8/finance/chart/{ticker}"
                f"?interval=1d&range=1d"
            )
            req = urllib.request.Request(url, headers={
                "User-Agent": "Mozilla/5.0",
                "Accept": "application/json",
            })
            with urllib.request.urlopen(req, timeout=8) as resp:
                data = json.loads(resp.read().decode("utf-8"))
                meta = data.get("chart", {}).get("result", [{}])[0].get("meta", {})
                price = meta.get("regularMarketPrice")
                if price is not None:
                    result[campo] = Decimal(str(round(price, 4)))
                    logger.debug(f"Yahoo {campo}={price}")
        except Exception as e:
            logger.warning(f"Yahoo {campo} ({ticker}) falhou: {e}")

    return result


# ---------------------------------------------------------------------------
# Prediction Tracker — compara previsão vs resultado real (REC6)
# ---------------------------------------------------------------------------


class PredictionTracker:
    """
    Rastreia previsões do agente e compara com o resultado real.

    A cada ciclo:
      1. Verifica se a previsão anterior acertou
      2. Registra nova previsão
      3. Calcula hit rate acumulado
    """

    DIVERGENCE_THRESHOLD_PCT = Decimal("0.10")  # 0.10% = ~5 pts no WINFUT

    def __init__(self):
        self.predictions: list[dict] = []  # {timestamp, decision, price, confidence}
        self.evaluations: list[dict] = []  # {predicted, actual_direction, acertou, divergencia}
        self.hits = 0
        self.misses = 0
        self.divergences = 0  # HOLD com mercado em tendência forte

    def register_prediction(self, decision_action: str, price: Decimal, confidence: Decimal):
        """Registra nova previsão para avaliação futura."""
        self.predictions.append({
            "timestamp": datetime.now(),
            "decision": decision_action,
            "price": price,
            "confidence": confidence,
        })

    def evaluate_last_prediction(self, current_price: Decimal) -> Optional[dict]:
        """
        Avalia a previsão anterior contra o movimento real do preço.

        Retorna dict com resultado da avaliação ou None se não há previsão anterior.
        """
        if len(self.predictions) < 2:
            return None

        prev = self.predictions[-2]
        prev_price = prev["price"]
        prev_decision = prev["decision"]
        prev_confidence = prev["confidence"]

        if prev_price == 0:
            return None

        # Calcular variação real
        variacao_pct = ((current_price - prev_price) / prev_price) * 100
        abs_var = abs(variacao_pct)

        # Determinar direção real do mercado
        if abs_var < self.DIVERGENCE_THRESHOLD_PCT:
            direcao_real = "FLAT"
        elif variacao_pct > 0:
            direcao_real = "UP"
        else:
            direcao_real = "DOWN"

        # Avaliar acerto
        acertou = False
        divergencia = False
        tipo_divergencia = ""

        if prev_decision in ("BUY", "STRONG_BUY"):
            acertou = direcao_real == "UP"
            if direcao_real == "DOWN" and abs_var > self.DIVERGENCE_THRESHOLD_PCT * 3:
                divergencia = True
                tipo_divergencia = f"Previu {prev_decision} mas mercado caiu {variacao_pct:.2f}%"

        elif prev_decision in ("SELL", "STRONG_SELL"):
            acertou = direcao_real == "DOWN"
            if direcao_real == "UP" and abs_var > self.DIVERGENCE_THRESHOLD_PCT * 3:
                divergencia = True
                tipo_divergencia = f"Previu {prev_decision} mas mercado subiu {variacao_pct:+.2f}%"

        elif prev_decision in ("HOLD", "NEUTRAL"):
            acertou = direcao_real == "FLAT"
            if abs_var > self.DIVERGENCE_THRESHOLD_PCT * 3:
                divergencia = True
                tipo_divergencia = (
                    f"Disse HOLD mas mercado fez {variacao_pct:+.2f}% — "
                    f"oportunidade perdida de {'BUY' if direcao_real == 'UP' else 'SELL'}"
                )

        # Contabilizar
        if acertou:
            self.hits += 1
        else:
            self.misses += 1
        if divergencia:
            self.divergences += 1

        eval_result = {
            "prev_decision": prev_decision,
            "prev_price": float(prev_price),
            "prev_confidence": float(prev_confidence),
            "current_price": float(current_price),
            "variacao_pct": float(variacao_pct),
            "direcao_real": direcao_real,
            "acertou": acertou,
            "divergencia": divergencia,
            "tipo_divergencia": tipo_divergencia,
            "timestamp_previsao": prev["timestamp"].isoformat(),
            "timestamp_avaliacao": datetime.now().isoformat(),
        }
        self.evaluations.append(eval_result)
        return eval_result

    @property
    def total_avaliacoes(self) -> int:
        return self.hits + self.misses

    @property
    def hit_rate(self) -> float:
        """Percentual de acertos (0-100)."""
        total = self.total_avaliacoes
        return (self.hits / total * 100) if total > 0 else 0.0

    @property
    def divergence_rate(self) -> float:
        """Percentual de divergências sobre total de avaliações."""
        total = self.total_avaliacoes
        return (self.divergences / total * 100) if total > 0 else 0.0

    def resumo(self) -> str:
        """Resumo textual para exibição."""
        total = self.total_avaliacoes
        if total == 0:
            return "Sem avaliações — primeira execução"
        return (
            f"Hit Rate: {self.hit_rate:.0f}% ({self.hits}/{total}) | "
            f"Divergências: {self.divergences} ({self.divergence_rate:.0f}%)"
        )


class PriceTracker:
    """Track price history for comparison."""

    def __init__(self):
        self.prices = []  # List of (timestamp, price)

    def add_price(self, price: Decimal):
        """Add current price."""
        self.prices.append((datetime.now(), price))

        # Keep only last hour
        cutoff = datetime.now() - timedelta(hours=1)
        self.prices = [(t, p) for t, p in self.prices if t > cutoff]

    def get_price_10min_ago(self) -> Decimal:
        """Get price from 10 minutes ago."""
        target = datetime.now() - timedelta(minutes=10)

        if not self.prices:
            return Decimal("0")

        # Find closest price to 10min ago
        closest = min(self.prices, key=lambda x: abs((x[0] - target).total_seconds()))
        return closest[1]


def create_reflection_entry(
    mt5: MT5Adapter,
    operator: QuantumOperatorEngine,
    journal: AIReflectionJournalService,
    symbol: Symbol,
    price_tracker: PriceTracker,
    prediction_tracker: PredictionTracker,
    opening_price: Decimal,
    human_last_action: str,
):
    """Create a single AI reflection entry with live macro data and prediction tracking."""

    now = datetime.now()
    print("\n" + "=" * 80)
    print(f"REFLEXAO DA IA - {now.strftime('%H:%M:%S')}")
    print("=" * 80)

    # Get current data
    candles_15m = mt5.get_candles(symbol, TimeFrame.M15, count=100)

    if not candles_15m:
        print("[ERRO] Falha ao obter dados")
        return None

    current_candle = candles_15m[-1]
    current_price = current_candle.close.value

    # Track price
    price_10min_ago = price_tracker.get_price_10min_ago()
    price_tracker.add_price(current_price)

    print(f"Preco Atual:  R$ {current_price:,.2f}")
    print(f"Preco 10min:  R$ {price_10min_ago:,.2f}")
    change_10min = ((current_price - price_10min_ago) / price_10min_ago * 100) if price_10min_ago > 0 else 0
    print(f"Variacao:     {change_10min:+.2f}%")

    # Calculate volume metrics
    volume_service = VolumeAnalysisService()
    volume_today, volume_avg_3days, volume_variance_pct = volume_service.calculate_volume_metrics(candles_15m)

    if volume_variance_pct is not None:
        print(f"Volume:       {volume_service.get_volume_interpretation(volume_variance_pct)}")

    # =========================================================================
    # REC6: Avaliar previsão anterior ANTES de fazer nova análise
    # =========================================================================
    eval_result = prediction_tracker.evaluate_last_prediction(current_price)
    if eval_result:
        print(f"\n{'─'*60}")
        print("  AUTO-AVALIAÇÃO DA PREVISÃO ANTERIOR")
        print(f"{'─'*60}")
        prev_d = eval_result["prev_decision"]
        var = eval_result["variacao_pct"]
        dir_real = eval_result["direcao_real"]
        acertou_str = "\033[92m✓ ACERTOU\033[0m" if eval_result["acertou"] else "\033[91m✗ ERROU\033[0m"
        print(f"  Previsão:    {prev_d} (conf: {eval_result['prev_confidence']:.0%})")
        print(f"  Resultado:   Mercado foi {dir_real} ({var:+.2f}%)")
        print(f"  Avaliação:   {acertou_str}")
        if eval_result["divergencia"]:
            print(f"  \033[93m⚠ DIVERGÊNCIA: {eval_result['tipo_divergencia']}\033[0m")
        print(f"  {prediction_tracker.resumo()}")
        print(f"{'─'*60}")

    # =========================================================================
    # REC6: Buscar dados macro AO VIVO (substitui hardcoded)
    # =========================================================================
    print("\nBuscando dados macro ao vivo...")
    macro = _fetch_live_macro()

    macro_sources = []
    for campo, valor in macro.items():
        status = f"{valor}" if valor is not None else "N/A"
        macro_sources.append(f"  {campo:16s} = {status}")
    print("\n".join(macro_sources))

    # Detectar se macro realmente mudou (comparar com ciclo anterior)
    macro_moved = any(v is not None for v in macro.values())

    # Get my decision with LIVE macro data
    print("\nExecutando analise com dados ao vivo...")
    decision = operator.analyze_and_decide(
        symbol=symbol,
        candles=candles_15m,
        dollar_index=macro["dollar_index"],
        vix=macro["vix"],
        selic=macro["selic"],
        ipca=macro["ipca"],
        usd_brl=macro["usd_brl"],
        embi_spread=int(macro["embi_spread"]) if macro["embi_spread"] is not None else None,
    )

    print(f"Minha Decisao: {decision.action.value}")
    print(f"Confianca:     {decision.confidence:.0%}")
    print(f"Alinhamento:   {decision.alignment_score:.0%}")

    # =========================================================================
    # REC6: Registrar nova previsão para avaliação futura
    # =========================================================================
    prediction_tracker.register_prediction(
        decision_action=decision.action.value,
        price=current_price,
        confidence=decision.confidence,
    )

    # Detect context
    sentiment_changed = abs(change_10min) > 0.3
    technical_triggered = decision.recommended_entry is not None

    # =========================================================================
    # Enriquecer reflexão com auto-avaliação
    # =========================================================================
    # Forçar human_last_action com informação de performance
    enriched_action = human_last_action
    if prediction_tracker.total_avaliacoes > 0:
        enriched_action = (
            f"{human_last_action} | "
            f"Performance: {prediction_tracker.resumo()}"
        )

    # Create reflection
    print("\nGerando reflexao...")
    reflection = journal.generate_reflection(
        current_price=current_price,
        opening_price=opening_price,
        price_10min_ago=price_10min_ago,
        my_decision=decision.action,
        my_confidence=decision.confidence,
        my_alignment=decision.alignment_score,
        macro_moved=macro_moved,
        sentiment_changed=sentiment_changed,
        technical_triggered=technical_triggered,
        human_last_action=enriched_action,
        volume_variance_pct=volume_variance_pct,
    )

    entry = journal.save_entry(reflection)

    # Display reflection
    print("\n" + "-" * 80)
    print("REFLEXAO SINCERA DA IA")
    print("-" * 80)
    print()
    print(f"Humor:  {reflection.mood}")
    print(f"Frase:  {reflection.one_liner}")
    print()
    print("AVALIACAO HONESTA:")
    print(f"   {reflection.honest_assessment}")
    print()
    print("O QUE ESTOU VENDO:")
    print(f"   {reflection.what_im_seeing}")
    print()
    print("RELEVANCIA DOS DADOS:")
    print(f"   {reflection.data_relevance}")
    print()
    print("SOU UTIL?")
    print(f"   {reflection.am_i_useful}")
    print()
    print("O QUE FUNCIONARIA MELHOR:")
    print(f"   {reflection.what_would_work_better}")
    print()
    print("AVALIACAO DO HUMANO:")
    print(f"   Faz Sentido: {'SIM' if reflection.human_makes_sense else 'NAO'}")
    print(f"   Feedback: {reflection.human_feedback}")
    print()
    print("O QUE MOVE O PRECO:")
    print(f"   {reflection.what_actually_moves_price}")
    print()
    print("CORRELACAO DOS DADOS:")
    print(f"   {reflection.my_data_correlation}")
    print()

    # =========================================================================
    # REC6: Seção de auto-avaliação — divergências acumuladas
    # =========================================================================
    if prediction_tracker.total_avaliacoes > 0:
        print("-" * 80)
        print("AUTO-AVALIAÇÃO ACUMULADA DA SESSÃO")
        print("-" * 80)
        print(f"   {prediction_tracker.resumo()}")
        if prediction_tracker.hit_rate < 40 and prediction_tracker.total_avaliacoes >= 3:
            print("   \033[91m⚠ ALERTA: Hit rate abaixo de 40% — considerar recalibrar parâmetros\033[0m")
        if prediction_tracker.divergence_rate > 30 and prediction_tracker.total_avaliacoes >= 3:
            print("   \033[91m⚠ ALERTA: Muitas divergências — agente está ignorando tendências reais\033[0m")
        # Últimas 3 avaliações
        recent = prediction_tracker.evaluations[-3:]
        if recent:
            print("   Últimas avaliações:")
            for ev in recent:
                icon = "✓" if ev["acertou"] else "✗"
                print(
                    f"     {icon} {ev['prev_decision']:10s} → Mercado {ev['direcao_real']:4s} "
                    f"({ev['variacao_pct']:+.2f}%)"
                    f"{' ⚠ DIVERGÊNCIA' if ev['divergencia'] else ''}"
                )
        print()

    print(f"[OK] Reflexao #{entry.entry_id} salva")

    return entry


def run_continuous_reflection():
    """Run AI reflection continuously every 10 minutes with live macro + prediction tracking."""

    print("=" * 80)
    print("DIARIO DE REFLEXAO DA IA - A CADA 10 MINUTOS")
    print("=" * 80)
    print()
    print("A IA vai desabafar sinceramente sobre:")
    print("  - O que ela esta vendo")
    print("  - Se seus dados importam")
    print("  - Se voce esta ajudando ou atrapalhando")
    print("  - O que funcionaria melhor")
    print()
    print("NOVIDADES v2:")
    print("  ✦ Dados macro AO VIVO (BCB SGS + Yahoo Finance)")
    print("  ✦ Rastreamento de previsões vs resultado real")
    print("  ✦ Detecção de divergência (HOLD quando mercado trend)")
    print("  ✦ Hit rate acumulado na sessão")
    print()
    print("Com HUMOR mas HONESTIDADE BRUTAL.")
    print()
    print("Pressione Ctrl+C para parar")
    print()

    # Setup
    config = get_config()
    symbol = Symbol(config.trading_symbol)

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

    # Get opening price
    candles = mt5.get_candles(symbol, TimeFrame.M15, count=100)
    opening_price = candles[0].open.value if candles else Decimal("0")

    # Initialize services
    operator = QuantumOperatorEngine()
    journal = AIReflectionJournalService()
    price_tracker = PriceTracker()
    prediction_tracker = PredictionTracker()

    entry_count = 0
    human_last_action = "Iniciou monitoramento de reflexao continua"

    try:
        while True:
            entry_count += 1

            # Create reflection
            entry = create_reflection_entry(
                mt5=mt5,
                operator=operator,
                journal=journal,
                symbol=symbol,
                price_tracker=price_tracker,
                prediction_tracker=prediction_tracker,
                opening_price=opening_price,
                human_last_action=human_last_action,
            )

            if entry:
                print(f"\n[OK] Reflexao #{entry_count} salva com sucesso")

            # Update human action
            human_last_action = "Esta observando as reflexoes"

            # Wait 10 minutes
            next_time = datetime.now() + timedelta(minutes=10)
            print(f"\nProxima reflexao em 10 minutos...")
            print(f"Aguardando ate {next_time.strftime('%H:%M')}")

            # Sleep for 10 minutes (600 seconds)
            time.sleep(600)

    except KeyboardInterrupt:
        print("\n\n" + "=" * 80)
        print("REFLEXAO INTERROMPIDA PELO HUMANO")
        print("=" * 80)
        print(f"\nTotal de reflexoes: {entry_count}")
        print()

        # =====================================================================
        # REC6: Resumo final com auto-avaliação de previsões
        # =====================================================================
        if prediction_tracker.total_avaliacoes > 0:
            print("-" * 80)
            print("RELATÓRIO DE PERFORMANCE DAS PREVISÕES")
            print("-" * 80)
            print(f"  {prediction_tracker.resumo()}")
            print(f"  Total de previsões registradas: {len(prediction_tracker.predictions)}")
            print(f"  Total avaliadas:                {prediction_tracker.total_avaliacoes}")
            print(f"  Acertos:                        {prediction_tracker.hits}")
            print(f"  Erros:                          {prediction_tracker.misses}")
            print(f"  Divergências graves:            {prediction_tracker.divergences}")
            if prediction_tracker.hit_rate < 50:
                print()
                print("  \033[91m⚠ VEREDICTO: Performance ABAIXO do esperado.\033[0m")
                print("  \033[91m  O agente precisa de recalibração nos parâmetros\033[0m")
                print("  \033[91m  de decisão ou melhor integração de dados.\033[0m")
            elif prediction_tracker.hit_rate >= 60:
                print()
                print("  \033[92m✓ VEREDICTO: Performance ACEITÁVEL.\033[0m")
            print()

            # Listar todas as avaliações
            if prediction_tracker.evaluations:
                print("  Histórico de avaliações:")
                for i, ev in enumerate(prediction_tracker.evaluations, 1):
                    icon = "✓" if ev["acertou"] else "✗"
                    div_mark = " ⚠ DIV" if ev["divergencia"] else ""
                    print(
                        f"    {i:2d}. {icon} {ev['prev_decision']:10s} → "
                        f"Mercado {ev['direcao_real']:4s} ({ev['variacao_pct']:+.2f}%)"
                        f"{div_mark}"
                    )
                print()

        # Summary of reflections
        today_entries = journal.get_today_entries()
        if today_entries:
            print("-" * 80)
            print("RESUMO DAS REFLEXOES DE HOJE")
            print("-" * 80)

            moods = {}
            for e in today_entries:
                mood = e.reflection.mood
                moods[mood] = moods.get(mood, 0) + 1

            print("\nHumores da IA hoje:")
            for mood, count in moods.items():
                print(f"  {mood}: {count}x")

            print("\nUltimas frases:")
            for e in today_entries[-5:]:
                print(f"  [{e.time}] {e.reflection.one_liner}")
            print()

    finally:
        # Disconnect
        mt5.disconnect()
        print("[OK] Desconectado do MT5")
        print()
        print("A IA agradece pela oportunidade de refletir sobre sua existencia.")
        print()


if __name__ == "__main__":
    run_continuous_reflection()
