"""Atualiza o modelo simplificado a cada 5 minutos."""

from collections import defaultdict
from datetime import datetime, timedelta
from decimal import Decimal
import os
import sys
import time

ROOT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)

from config import get_config
from src.application.services.ai_reflection_journal import (
    AIReflectionJournalService,
)
from src.application.services.quantum_operator import QuantumOperatorEngine
from src.application.services.trading_journal import TradingJournalService
from src.application.services.volume_analysis import VolumeAnalysisService
from src.domain.value_objects import Symbol
from src.infrastructure.adapters.mt5_adapter import MT5Adapter
from src.domain.enums.trading_enums import TimeFrame
from src.application.services.macro_score.engine import MacroScoreEngine
from src.infrastructure.database.schema import (
    AIReflectionLogModel,
    SimpleMacroScoreDecisionModel,
    SimpleMacroScoreItemModel,
    SimpleScoreAlignmentModel,
    SimpleScoreMatrixModel,
    TradingJournalLogModel,
    create_database,
    get_session,
)


REFRESH_SECONDS = 300
PROGRESS_BAR_WIDTH = 38
STALE_SCORE_MINUTES = 60
STALE_FEED_SECONDS = 120
LONG_TERM_MIN_CYCLES = 6
DB_PATH: str | None = None


class PriceTracker:
    """Rastreia preco para reflexao da IA."""

    def __init__(self) -> None:
        self.prices: list[tuple[datetime, Decimal]] = []

    def add_price(self, price: Decimal) -> None:
        self.prices.append((datetime.now(), price))
        cutoff = datetime.now() - timedelta(hours=1)
        self.prices = [(t, p) for t, p in self.prices if t > cutoff]

    def get_price_10min_ago(self) -> Decimal:
        target = datetime.now() - timedelta(minutes=10)
        if not self.prices:
            return Decimal("0")
        closest = min(
            self.prices,
            key=lambda x: abs((x[0] - target).total_seconds()),
        )
        return closest[1]


def _connect_mt5(config: object) -> MT5Adapter:
    mt5 = MT5Adapter(
        login=config.mt5_login,
        password=config.mt5_password,
        server=config.mt5_server,
    )
    if not mt5.connect():
        raise RuntimeError("Falha ao conectar no MT5. Verifique .env e MT5 aberto.")
    return mt5


def _run_once(engine: MacroScoreEngine) -> tuple:
    result = engine.analyze()
    items = [i for i in result.items if i.available]

    by_cat = defaultdict(list)
    for item in items:
        by_cat[item.category.value].append(item)

    summary_lines = []
    group_scores: dict[str, dict] = {}
    for cat in sorted(by_cat.keys()):
        group = by_cat[cat]
        raw_sum = sum(i.final_score for i in group)
        summary_lines.append(f"{cat}: {len(group)} itens {raw_sum:+d}")
        group_scores[cat] = {
            "count": len(group),
            "raw_sum": raw_sum,
        }

    total_raw = sum(i.final_score for i in items)

    now = datetime.now()
    timestamp = now.strftime("%Y-%m-%d %H:%M:%S")
    next_run = (now + timedelta(seconds=REFRESH_SECONDS)).strftime(
        "%Y-%m-%d %H:%M:%S"
    )
    print(f"\n[{timestamp}] DETALHE POR GRUPO")
    for cat in sorted(by_cat.keys()):
        group = sorted(by_cat[cat], key=lambda i: i.item_number)
        raw_sum = sum(i.final_score for i in group)
        print(f"{cat}: total {raw_sum:+d}")
        for item in group:
            print(f"  - {item.item_number:02d} {item.symbol}: {item.final_score:+d}")

    return result, items, group_scores, total_raw, summary_lines, next_run


def _check_feed_health(
    mt5: MT5Adapter,
    symbols: list[str],
    max_age_seconds: int,
) -> str:
    issues = []
    now = datetime.utcnow()
    for sym in symbols:
        tick = mt5.get_symbol_info_tick(sym)
        if tick is None:
            issues.append(f"{sym}: sem tick")
            continue
        age = (now - tick.timestamp).total_seconds()
        if age > max_age_seconds:
            issues.append(f"{sym}: tick {int(age)}s")

    if not issues:
        return ""

    msg = (
        f"[ALERTA] Feed possivelmente travado (>{max_age_seconds}s): "
        + ", ".join(issues)
    )
    print(msg)
    return msg


def _format_mm_ss(total_seconds: int) -> str:
    minutes = total_seconds // 60
    seconds = total_seconds % 60
    return f"{minutes:02d}m {seconds:02d}s"


def _wait_with_progress(wait_seconds: int) -> None:
    start = datetime.now()
    end = start + timedelta(seconds=wait_seconds)

    print("\n" + "=" * 80)
    print("⏳ AGUARDANDO PROXIMA ANALISE")
    print("=" * 80)

    for elapsed in range(wait_seconds + 1):
        now = datetime.now()
        remaining = max(0, wait_seconds - elapsed)
        percent = int((elapsed / wait_seconds) * 100) if wait_seconds else 100
        filled = int((percent / 100) * PROGRESS_BAR_WIDTH)
        bar = "█" * filled + "░" * (PROGRESS_BAR_WIDTH - filled)

        line = (
            f"🕐 Hora: {now.strftime('%H:%M:%S')} | "
            f"⏱️  Proxima: {end.strftime('%H:%M:%S')} | "
            f"⏳ Restam: {_format_mm_ss(remaining)} | "
            f"[{bar}] {percent}%"
        )
        sys.stdout.write("\r" + line)
        sys.stdout.flush()
        if remaining == 0:
            break
        time.sleep(1)

    print()


def _direction(delta: Decimal | int) -> int:
    if delta > 0:
        return 1
    if delta < 0:
        return -1
    return 0


def _dir_label(value: int) -> str:
    if value > 0:
        return "up"
    if value < 0:
        return "down"
    return "flat"


def _run_trading_journal_once(
    mt5: MT5Adapter,
    operator: QuantumOperatorEngine,
    journal: TradingJournalService,
    symbol: Symbol,
    current_items,
    total_raw: int,
    prev_scores: dict,
    prev_total_raw,
    prev_price,
    alignment_note: str,
) -> Decimal | None:
    try:
        candles_15m = mt5.get_candles(symbol, TimeFrame.M15, count=100)
        if not candles_15m:
            print("[AVISO] Diario de mercado: sem candles suficientes")
            return None

        opening_candle = candles_15m[0]
        current_candle = candles_15m[-1]

        opening_price = opening_candle.open.value
        current_price = current_candle.close.value
        high = max(c.high.value for c in candles_15m)
        low = min(c.low.value for c in candles_15m)

        volume_service = VolumeAnalysisService()
        volume_today, volume_avg_3days, volume_variance_pct = (
            volume_service.calculate_volume_metrics(candles_15m)
        )

        decision = operator.analyze_and_decide(
            symbol=symbol,
            candles=candles_15m,
            dollar_index=Decimal("104.3"),
            vix=Decimal("16.5"),
            selic=Decimal("10.75"),
            ipca=Decimal("4.5"),
            usd_brl=Decimal("5.85"),
            embi_spread=250,
        )

        decision_data = {
            "action": decision.action,
            "confidence": decision.confidence,
            "primary_reason": decision.primary_reason,
            "macro_bias": decision.macro_bias,
            "fundamental_bias": decision.fundamental_bias,
            "sentiment_bias": decision.sentiment_bias,
            "technical_bias": decision.technical_bias,
            "alignment_score": decision.alignment_score,
            "supporting_factors": decision.supporting_factors,
            "market_regime": decision.market_regime,
        }

        narrative = journal.create_narrative(
            symbol=symbol,
            current_price=current_price,
            opening_price=opening_price,
            high=high,
            low=low,
            decision_data=decision_data,
            volume_today=volume_today,
            volume_avg_3days=volume_avg_3days,
            volume_variance_pct=volume_variance_pct,
        )

        changes = []
        for item in current_items:
            prev = prev_scores.get(item.item_number)
            if prev is not None and prev != item.final_score:
                changes.append((item, prev, item.final_score))

        if changes:
            changes_text = ", ".join(
                f"{c.item_number:02d} {c.symbol}: {prev:+d}->{curr:+d}"
                for c, prev, curr in changes[:8]
            )
            change_summary = (
                f"Pontuacoes alteradas: {len(changes)} itens. "
                f"Principais: {changes_text}."
            )
        else:
            change_summary = "Pontuacoes alteradas: nenhuma mudanca relevante."

        if prev_price is not None:
            price_delta = current_price - prev_price
            price_pct = (price_delta / prev_price * 100) if prev_price else Decimal("0")
            price_text = (
                f"Preco desde a ultima analise: {price_delta:+.2f} "
                f"({price_pct:+.2f}%)."
            )
        else:
            price_text = "Preco desde a ultima analise: sem historico para comparar."

        lesson = "Licao: amostra insuficiente para concluir."
        if prev_total_raw is not None and prev_price is not None:
            score_delta = total_raw - prev_total_raw
            price_delta = current_price - prev_price
            if score_delta > 0 and price_delta > 0:
                lesson = "Licao: scores subiram e o preco acompanhou (alinhamento positivo)."
            elif score_delta < 0 and price_delta < 0:
                lesson = "Licao: scores cairam e o preco acompanhou (alinhamento negativo)."
            elif score_delta > 0 and price_delta < 0:
                lesson = "Licao: scores subiram, mas o preco caiu (divergencia)."
            elif score_delta < 0 and price_delta > 0:
                lesson = "Licao: scores cairam, mas o preco subiu (divergencia)."
            else:
                lesson = "Licao: pouca mudanca simultanea entre score e preco."

        narrative.detailed_narrative = (
            narrative.detailed_narrative
            + "\n\n" + change_summary
            + "\n" + price_text
            + "\n" + lesson
            + ("\n" + alignment_note if alignment_note else "")
        )
        entry = journal.save_entry(narrative, decision_data)

        print("\n" + "-" * 80)
        print("DIARIO DE MERCADO - NARRATIVA COMPLETA")
        print("-" * 80)
        print(f"Manchete: {narrative.headline}")
        print(f"Sentimento: {narrative.market_feeling}")
        print()
        print(narrative.detailed_narrative)
        print()
        print("Contexto Multidimensional:")
        print(f"  Macro:       {decision_data['macro_bias']}")
        print(f"  Fundamentos: {decision_data['fundamental_bias']}")
        print(f"  Sentimento:  {decision_data['sentiment_bias']}")
        print(f"  Tecnica:     {decision_data['technical_bias']}")
        print(f"  Alinhamento: {entry.alignment_score:.0%}")
        print()
        print("Decisao:")
        print(f"  Acao:      {narrative.decision.value}")
        print(f"  Confianca: {narrative.confidence:.0%}")
        print(f"  Razao:     {decision_data['primary_reason']}")
        print()
        print("Observacoes-chave:")
        for factor in entry.key_observations:
            print(f"  - {factor}")
        print("Tags:")
        print(f"  {', '.join(narrative.tags)}")
        print()
        print("Insights do ciclo:")
        print(f"  {change_summary}")
        print(f"  {price_text}")
        print(f"  {lesson}")
        if alignment_note:
            print(f"  {alignment_note}")
        print("-" * 80)
        _persist_trading_journal_entry(entry)
        print(f"[OK] Diario de mercado salvo: {entry.entry_id}")
        return current_price
    except Exception as exc:
        print(f"[AVISO] Diario de mercado falhou: {exc}")
        return None


def _run_ai_reflection_once(
    mt5: MT5Adapter,
    operator: QuantumOperatorEngine,
    journal: AIReflectionJournalService,
    symbol: Symbol,
    price_tracker: PriceTracker,
    stale_scores_note: str,
    alignment_note: str,
) -> None:
    try:
        candles_15m = mt5.get_candles(symbol, TimeFrame.M15, count=100)
        if not candles_15m:
            print("[AVISO] Diario da IA: sem candles suficientes")
            return

        opening_price = candles_15m[0].open.value
        current_price = candles_15m[-1].close.value

        price_10min_ago = price_tracker.get_price_10min_ago()
        price_tracker.add_price(current_price)

        volume_service = VolumeAnalysisService()
        _, _, volume_variance_pct = volume_service.calculate_volume_metrics(
            candles_15m
        )

        decision = operator.analyze_and_decide(
            symbol=symbol,
            candles=candles_15m,
            dollar_index=Decimal("104.3"),
            vix=Decimal("16.5"),
            selic=Decimal("10.75"),
            ipca=Decimal("4.5"),
            usd_brl=Decimal("5.85"),
            embi_spread=250,
        )

        change_10min = (
            (current_price - price_10min_ago) / price_10min_ago * 100
            if price_10min_ago > 0
            else Decimal("0")
        )

        macro_moved = False
        sentiment_changed = abs(change_10min) > Decimal("0.3")
        technical_triggered = decision.recommended_entry is not None

        if abs(change_10min) < Decimal("0.2"):
            learning_note = "Quando o preco fica lateral, sinais intraday perdem forca."
        elif technical_triggered and abs(change_10min) > Decimal("0.5"):
            learning_note = "Movimento forte com gatilho tecnico sugere impulso legitimo."
        elif not technical_triggered and abs(change_10min) > Decimal("0.5"):
            learning_note = "O preco pode andar sem setup tecnico evidente."
        else:
            learning_note = "Dados mistos; observar mais ciclos antes de concluir."

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
            human_last_action="Rotina automatica entre analises",
            volume_variance_pct=volume_variance_pct,
        )

        reflection.what_im_seeing = (
            reflection.what_im_seeing
            + f" Aprendizado: {learning_note}"
            + (f" {stale_scores_note}" if stale_scores_note else "")
            + (f" {alignment_note}" if alignment_note else "")
        )

        entry = journal.save_entry(reflection)

        print("\n" + "-" * 80)
        print("DIARIO DA IA - REFLEXAO COMPLETA")
        print("-" * 80)
        print(f"Humor:  {reflection.mood}")
        print(f"Frase:  {reflection.one_liner}")
        print()
        print("Avaliacao Honesta:")
        print(f"  {reflection.honest_assessment}")
        print()
        print("O que estou vendo:")
        print(f"  {reflection.what_im_seeing}")
        print()
        print("Relevancia dos dados:")
        print(f"  {reflection.data_relevance}")
        print()
        print("Sou util?")
        print(f"  {reflection.am_i_useful}")
        print()
        print("O que funcionaria melhor:")
        print(f"  {reflection.what_would_work_better}")
        print()
        print("Avaliacao do humano:")
        print(f"  Faz sentido: {'SIM' if reflection.human_makes_sense else 'NAO'}")
        print(f"  Feedback:    {reflection.human_feedback}")
        print()
        print("O que move o preco:")
        print(f"  {reflection.what_actually_moves_price}")
        print()
        print("Correlacao dos dados:")
        print(f"  {reflection.my_data_correlation}")
        print("-" * 80)
        _persist_ai_reflection_entry(entry)
        print(f"[OK] Diario da IA salvo: {entry.entry_id}")
    except Exception as exc:
        print(f"[AVISO] Diario da IA falhou: {exc}")


def _persist_simple_score(
    result,
    items,
    group_scores: dict,
    total_raw: int,
) -> None:
    signal = "NEUTRO"
    if total_raw > 0:
        signal = "COMPRA"
    elif total_raw < 0:
        signal = "VENDA"

    session = get_session(DB_PATH)
    try:
        decision = SimpleMacroScoreDecisionModel(
            timestamp=result.timestamp,
            total_items=result.total_items,
            items_available=result.items_available,
            total_raw=total_raw,
            signal=signal,
            group_scores=group_scores,
        )
        session.add(decision)
        session.flush()

        for item in items:
            session.add(
                SimpleMacroScoreItemModel(
                    decision_id=decision.id,
                    timestamp=result.timestamp,
                    item_number=item.item_number,
                    symbol=item.symbol,
                    category=item.category.value,
                    final_score=item.final_score,
                )
            )

        session.commit()
    finally:
        session.close()


def _persist_trading_journal_entry(entry) -> None:
    session = get_session(DB_PATH)
    try:
        session.add(
            TradingJournalLogModel(
                entry_id=entry.entry_id,
                timestamp=entry.narrative.timestamp,
                symbol=entry.narrative.symbol.code,
                headline=entry.narrative.headline,
                market_feeling=entry.narrative.market_feeling,
                detailed_narrative=entry.narrative.detailed_narrative,
                decision=entry.narrative.decision.value,
                confidence=float(entry.narrative.confidence),
                reasoning=entry.narrative.reasoning,
                macro_bias=entry.macro_bias,
                fundamental_bias=entry.fundamental_bias,
                sentiment_bias=entry.sentiment_bias,
                technical_bias=entry.technical_bias,
                alignment_score=float(entry.alignment_score),
                market_regime=entry.market_regime,
                key_observations=entry.key_observations,
                tags=entry.narrative.tags,
            )
        )
        session.commit()
    finally:
        session.close()


def _persist_ai_reflection_entry(entry) -> None:
    r = entry.reflection
    session = get_session(DB_PATH)
    try:
        session.add(
            AIReflectionLogModel(
                entry_id=entry.entry_id,
                timestamp=r.timestamp,
                current_price=r.current_price,
                price_change_since_open=float(r.price_change_since_open),
                price_change_last_10min=float(r.price_change_last_10min),
                my_decision=r.my_decision.value,
                my_confidence=float(r.my_confidence),
                my_alignment=float(r.my_alignment),
                honest_assessment=r.honest_assessment,
                what_im_seeing=r.what_im_seeing,
                data_relevance=r.data_relevance,
                am_i_useful=r.am_i_useful,
                what_would_work_better=r.what_would_work_better,
                human_makes_sense=1 if r.human_makes_sense else 0,
                human_feedback=r.human_feedback,
                what_actually_moves_price=r.what_actually_moves_price,
                my_data_correlation=r.my_data_correlation,
                mood=r.mood,
                one_liner=r.one_liner,
                tags=entry.tags,
            )
        )
        session.commit()
    finally:
        session.close()


def _persist_alignment_snapshot(
    timestamp: datetime,
    price: Decimal | None,
    prev_price: Decimal | None,
    price_dir: int,
    total_raw: int,
    prev_total_raw,
    score_dir: int,
    group_scores: dict,
    group_dirs: dict,
    matrix: dict,
    group_weights: dict,
) -> None:
    session = get_session(DB_PATH)
    try:
        session.add(
            SimpleScoreAlignmentModel(
                timestamp=timestamp,
                price=price,
                prev_price=prev_price,
                price_dir=price_dir,
                total_raw=total_raw,
                prev_total_raw=prev_total_raw,
                score_dir=score_dir,
                group_raws=group_scores,
                group_dirs=group_dirs,
            )
        )
        session.add(
            SimpleScoreMatrixModel(
                date=timestamp.strftime("%Y-%m-%d"),
                timestamp=timestamp,
                matrix=matrix,
                group_weights=group_weights,
            )
        )
        session.commit()
    finally:
        session.close()


def main() -> None:
    config = get_config()
    global DB_PATH
    DB_PATH = config.db_path
    if not os.path.isabs(DB_PATH):
        DB_PATH = os.path.join(ROOT_DIR, DB_PATH)
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    create_database(DB_PATH)
    iteration = 0

    symbol = Symbol(config.trading_symbol)
    operator = QuantumOperatorEngine()
    trading_journal = TradingJournalService()
    ai_journal = AIReflectionJournalService()
    price_tracker = PriceTracker()
    prev_scores: dict[int, int] = {}
    prev_total_raw = None
    prev_price = None
    last_change_at: dict[int, datetime] = {}
    prev_group_scores: dict[str, int] = {}
    matrix_counts = {
        "up": {"up": 0, "down": 0, "flat": 0},
        "down": {"up": 0, "down": 0, "flat": 0},
        "flat": {"up": 0, "down": 0, "flat": 0},
    }
    group_alignment: dict[str, dict[str, int]] = {}

    while True:
        iteration += 1
        try:
            mt5 = _connect_mt5(config)
            feed_note = _check_feed_health(
                mt5,
                ["WIN$N", "BOVA11", "SMLL"],
                STALE_FEED_SECONDS,
            )
            engine = MacroScoreEngine(
                mt5_adapter=mt5,
                neutral_threshold=config.macro_score_neutral_threshold,
            )
            result, items, group_scores, total_raw, summary_lines, next_run = _run_once(engine)
            _persist_simple_score(result, items, group_scores, total_raw)
            now = datetime.now()
            for item in items:
                if item.item_number not in last_change_at:
                    last_change_at[item.item_number] = now
                else:
                    prev_val = prev_scores.get(item.item_number)
                    if prev_val is not None and prev_val != item.final_score:
                        last_change_at[item.item_number] = now

            stale_items = [
                i for i in items
                if (now - last_change_at.get(i.item_number, now)).total_seconds()
                >= STALE_SCORE_MINUTES * 60
            ]
            if stale_items:
                sample = ", ".join(
                    f"{i.item_number:02d} {i.symbol}" for i in stale_items[:6]
                )
                stale_scores_note = (
                    f"Scores estagnados: {len(stale_items)} itens sem mudanca "
                    f"ha {STALE_SCORE_MINUTES}min+ (ex: {sample}). "
                    "Pode indicar falha de captura/atualizacao."
                )
            else:
                stale_scores_note = ""

            if feed_note:
                stale_scores_note = (
                    f"{stale_scores_note} {feed_note}".strip()
                )

            current_price_for_alignment = None
            candles_for_alignment = mt5.get_candles(symbol, TimeFrame.M15, count=2)
            if candles_for_alignment:
                current_price_for_alignment = candles_for_alignment[-1].close.value

            alignment_note = ""
            price_dir = 0
            score_dir = 0
            group_dirs: dict[str, int] = {}
            if (
                prev_total_raw is not None
                and prev_price is not None
                and current_price_for_alignment is not None
            ):
                price_dir = _direction(current_price_for_alignment - prev_price)
                score_dir = _direction(total_raw - prev_total_raw)
                matrix_counts[_dir_label(price_dir)][_dir_label(score_dir)] += 1

                for group, data in group_scores.items():
                    prev_group = prev_group_scores.get(group)
                    group_dir = _direction(data["raw_sum"] - prev_group) if prev_group is not None else 0
                    group_dirs[group] = group_dir

                    if group not in group_alignment:
                        group_alignment[group] = {
                            "aligned": 0,
                            "divergent": 0,
                            "flat": 0,
                        }

                    if group_dir == 0 or price_dir == 0:
                        group_alignment[group]["flat"] += 1
                    elif group_dir == price_dir:
                        group_alignment[group]["aligned"] += 1
                    else:
                        group_alignment[group]["divergent"] += 1

                aligned = matrix_counts["up"]["up"] + matrix_counts["down"]["down"]
                divergent = matrix_counts["up"]["down"] + matrix_counts["down"]["up"]
                total_dir = aligned + divergent
                if total_dir >= LONG_TERM_MIN_CYCLES:
                    aligned_pct = (aligned / total_dir) * 100
                    alignment_note = (
                        "Alinhamento longo prazo: "
                        f"{aligned_pct:.0f}% ({aligned}/{total_dir} ciclos alinhados)."
                    )

            group_weights = {}
            for group, stats in group_alignment.items():
                aligned = stats.get("aligned", 0)
                divergent = stats.get("divergent", 0)
                total_dir = aligned + divergent
                if total_dir:
                    group_weights[group] = round(aligned / total_dir, 4)
                else:
                    group_weights[group] = None

            if prev_total_raw is not None and current_price_for_alignment is not None:
                _persist_alignment_snapshot(
                    timestamp=now,
                    price=current_price_for_alignment,
                    prev_price=prev_price,
                    price_dir=price_dir,
                    total_raw=total_raw,
                    prev_total_raw=prev_total_raw,
                    score_dir=score_dir,
                    group_scores=group_scores,
                    group_dirs={k: _dir_label(v) for k, v in group_dirs.items()},
                    matrix=matrix_counts,
                    group_weights=group_weights,
                )

            current_price = _run_trading_journal_once(
                mt5=mt5,
                operator=operator,
                journal=trading_journal,
                symbol=symbol,
                current_items=items,
                total_raw=total_raw,
                prev_scores=prev_scores,
                prev_total_raw=prev_total_raw,
                prev_price=prev_price,
                alignment_note=alignment_note,
            )
            _run_ai_reflection_once(
                mt5=mt5,
                operator=operator,
                journal=ai_journal,
                symbol=symbol,
                price_tracker=price_tracker,
                stale_scores_note=stale_scores_note,
                alignment_note=alignment_note,
            )
            print("\nRESUMO GERAL")
            for line in summary_lines:
                print(line)
            print(f"PONTUACAO FINAL: {total_raw:+d}")
            print(f"PROXIMA ANALISE: {next_run}")
            prev_scores = {i.item_number: i.final_score for i in items}
            prev_total_raw = total_raw
            if current_price is not None:
                prev_price = current_price
            prev_group_scores = {k: v["raw_sum"] for k, v in group_scores.items()}
            print(f"CICLO CONCLUIDO: #{iteration}")
        except Exception as exc:  # noqa: BLE001 - keep loop alive
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            print(f"[{timestamp}] ERRO: {exc}")
            print(f"CICLO CONCLUIDO: #{iteration}")

        _wait_with_progress(REFRESH_SECONDS)


if __name__ == "__main__":
    main()
