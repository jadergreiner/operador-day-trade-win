#!/usr/bin/env python3
"""Gera e persiste diretiva operacional automática pós-pregão.

Saídas:
1) head_directives (diretiva ativa para próximo pregão útil)
2) diary_feedback (aprendizados estruturados)
3) markdown em data/diarios/diario_head_YYYYMMDD.md

Uso:
  python scripts/aplicar_diretiva_pos_pregao.py
  python scripts/aplicar_diretiva_pos_pregao.py --base-date 2026-02-13
"""

from __future__ import annotations

import argparse
import json
import sqlite3
import sys
from dataclasses import dataclass
from datetime import date, datetime, timedelta
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from src.application.services.diary_feedback import DiaryFeedback, save_diary_feedback
from src.application.services.head_directives import HeadDirective, save_directive


@dataclass
class DayMetrics:
    ref_date: str
    first_ts: str | None
    last_ts: str | None
    open_price: float
    last_price: float
    pmin: float
    pmax: float
    macro_avg: float
    macro_min: float
    macro_max: float
    micro_avg: float
    episodes: int
    opportunities: int
    macro_sell_count: int
    macro_buy_count: int
    closed_trades: int
    wins: int
    losses: int
    pnl_total: float


@dataclass
class Ctx:
    base_date: str
    target_date: str

    @property
    def db_path(self) -> Path:
        return ROOT_DIR / "data" / "db" / "trading.db"

    @property
    def source_tag(self) -> str:
        return f"head_pospregao_{self.base_date.replace('-', '')}_para_{self.target_date.replace('-', '')}"

    @property
    def diario_md(self) -> Path:
        return ROOT_DIR / "data" / "diarios" / f"diario_head_{self.target_date.replace('-', '')}.md"


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Aplica diretiva pós-pregão automática.")
    parser.add_argument("--base-date", default=date.today().isoformat(), help="Data base da análise (YYYY-MM-DD).")
    parser.add_argument("--calendar-file", default=str(ROOT_DIR / "data" / "calendario" / "feriados_b3.txt"), help="Calendário local de feriados B3.")
    return parser.parse_args()


def _load_holidays(path: Path) -> set[str]:
    if not path.exists():
        return set()
    out: set[str] = set()
    for line in path.read_text(encoding="utf-8", errors="ignore").splitlines():
        txt = line.strip()
        if txt and not txt.startswith("#"):
            out.add(txt)
    return out


def _next_business_day(base_date: str, holidays: set[str]) -> str:
    d = datetime.strptime(base_date, "%Y-%m-%d").date() + timedelta(days=1)
    while d.weekday() >= 5 or d.isoformat() in holidays:
        d += timedelta(days=1)
    return d.isoformat()


def _fetch_metrics(db_path: Path, base_date: str) -> DayMetrics:
    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()

    cur.execute(
        """
        SELECT
            MIN(timestamp) as t0,
            MAX(timestamp) as t1,
            COALESCE((SELECT price_open FROM micro_trend_decisions WHERE substr(timestamp,1,10)=? ORDER BY timestamp ASC LIMIT 1), 0) as open_price,
            COALESCE((SELECT price_current FROM micro_trend_decisions WHERE substr(timestamp,1,10)=? ORDER BY timestamp DESC LIMIT 1), 0) as last_price,
            COALESCE(MIN(price_current), 0) as pmin,
            COALESCE(MAX(price_current), 0) as pmax,
            COALESCE(AVG(macro_score), 0) as macro_avg,
            COALESCE(MIN(macro_score), 0) as macro_min,
            COALESCE(MAX(macro_score), 0) as macro_max,
            COALESCE(AVG(micro_score), 0) as micro_avg,
            COUNT(*) as episodes,
            COALESCE(SUM(num_opportunities), 0) as opportunities
        FROM micro_trend_decisions
        WHERE substr(timestamp,1,10)=?
        """,
        (base_date, base_date, base_date),
    )
    m = cur.fetchone()

    cur.execute(
        """
        SELECT
            COALESCE(SUM(CASE WHEN macro_signal='VENDA' THEN 1 ELSE 0 END),0) as sell_count,
            COALESCE(SUM(CASE WHEN macro_signal='COMPRA' THEN 1 ELSE 0 END),0) as buy_count
        FROM micro_trend_decisions
        WHERE substr(timestamp,1,10)=?
        """,
        (base_date,),
    )
    ms = cur.fetchone()

    cur.execute(
        """
        SELECT
            COUNT(*) as closed_trades,
            COALESCE(SUM(CASE WHEN profit_loss > 0 THEN 1 ELSE 0 END),0) as wins,
            COALESCE(SUM(CASE WHEN profit_loss <= 0 THEN 1 ELSE 0 END),0) as losses,
            COALESCE(SUM(profit_loss),0) as pnl_total
        FROM trades
        WHERE substr(entry_time,1,10)=?
          AND status='CLOSED'
          AND symbol LIKE 'WIN%'
        """,
        (base_date,),
    )
    t = cur.fetchone()

    conn.close()

    return DayMetrics(
        ref_date=base_date,
        first_ts=m["t0"],
        last_ts=m["t1"],
        open_price=float(m["open_price"] or 0.0),
        last_price=float(m["last_price"] or 0.0),
        pmin=float(m["pmin"] or 0.0),
        pmax=float(m["pmax"] or 0.0),
        macro_avg=float(m["macro_avg"] or 0.0),
        macro_min=float(m["macro_min"] or 0.0),
        macro_max=float(m["macro_max"] or 0.0),
        micro_avg=float(m["micro_avg"] or 0.0),
        episodes=int(m["episodes"] or 0),
        opportunities=int(m["opportunities"] or 0),
        macro_sell_count=int(ms["sell_count"] or 0),
        macro_buy_count=int(ms["buy_count"] or 0),
        closed_trades=int(t["closed_trades"] or 0),
        wins=int(t["wins"] or 0),
        losses=int(t["losses"] or 0),
        pnl_total=float(t["pnl_total"] or 0.0),
    )


def _derive_head_directive(ctx: Ctx, m: DayMetrics) -> HeadDirective:
    bearish_bias = m.macro_sell_count > max(3, m.macro_buy_count * 2)
    direction = "BEARISH" if bearish_bias else "NEUTRAL"

    confidence_market = 62 if bearish_bias else 55
    aggressiveness = "MODERATE"
    position_size_pct = 65 if bearish_bias else 70

    range_pts = max(0.0, m.pmax - m.pmin)
    stop_loss_pts = 260 if range_pts > 1500 else 220
    max_daily_trades = 4

    # Zonas táticas derivadas da última referência de preço
    anchor = m.last_price if m.last_price > 0 else m.open_price
    ideal_sell_zone_low = round(anchor + 250, 2)
    ideal_sell_zone_high = round(anchor + 900, 2)
    ideal_buy_zone_low = round(anchor - 550, 2)
    ideal_buy_zone_high = round(anchor - 120, 2)

    forbidden_zone_above = round(max(m.pmax, anchor + 1100), 2)
    forbidden_zone_below = round(min(m.pmin, anchor - 900), 2)

    wins = m.wins
    losses = m.losses
    wr = (wins / max(1, wins + losses)) * 100

    notes = (
        f"Pós-pregão {m.ref_date}: macro SELL {m.macro_sell_count}x vs BUY {m.macro_buy_count}x, "
        f"média macro {m.macro_avg:+.1f}, faixa {m.pmin:.0f}-{m.pmax:.0f}. "
        f"Execução real: {m.closed_trades} trades, W/L={wins}/{losses}, WR={wr:.0f}%, PnL={m.pnl_total:+.0f} pts. "
        "Plano: priorizar continuidade de tendência com entradas em pullback, evitar reversão precoce sem confirmação."
    )

    risk_scenario = (
        "Risco principal: classificador micro sinalizar REVERSÃO em tendência forte e gerar entradas contra fluxo. "
        "Mitigação: exigir ADX mínimo para trend-following, reduzir tamanho para 65%, "
        "evitar venda em exaustão abaixo da zona proibida e limitar a 4 trades."
    )

    return HeadDirective(
        date=ctx.target_date,
        created_at=datetime.now().isoformat(),
        source=ctx.source_tag,
        analyst="Head Global de Finanças - Mercado Brasileiro Futuro",
        direction=direction,
        confidence_market=confidence_market,
        aggressiveness=aggressiveness,
        position_size_pct=position_size_pct,
        stop_loss_pts=stop_loss_pts,
        max_daily_trades=max_daily_trades,
        max_rsi_for_buy=68,
        min_rsi_for_sell=32,
        min_adx_for_entry=20,
        forbidden_zone_above=forbidden_zone_above,
        forbidden_zone_below=forbidden_zone_below,
        ideal_buy_zone_low=ideal_buy_zone_low,
        ideal_buy_zone_high=ideal_buy_zone_high,
        ideal_sell_zone_low=ideal_sell_zone_low,
        ideal_sell_zone_high=ideal_sell_zone_high,
        reduce_before_event=True,
        event_description="Checar agenda macro antes da abertura e reduzir exposição em eventos de alto impacto.",
        event_time="09:00",
        notes=notes,
        risk_scenario=risk_scenario,
        active=True,
    )


def _derive_diary_feedback(ctx: Ctx, m: DayMetrics) -> DiaryFeedback:
    market_range_pts = max(0.0, m.pmax - m.pmin)
    wins = m.wins
    losses = m.losses
    wr = (wins / max(1, wins + losses)) * 100

    incoerencias = []
    if m.micro_avg > 1.5 and m.macro_avg < -10:
        incoerencias.append(
            "Micro score médio positivo em contexto macro vendedor forte; risco de sinalizar reversão onde há continuidade."
        )

    direcional_vieses = [
        f"Predominância vendedora: VENDA={m.macro_sell_count} vs COMPRA={m.macro_buy_count}.",
    ]

    sugestoes = [
        "Priorizar setup de continuidade (pullback + retomada) quando ADX estiver elevado.",
        "Reduzir peso de gatilhos de reversão em tendência intraday forte.",
        "Manter disciplina de risco: máximo 4 trades e exposição reduzida.",
    ]

    return DiaryFeedback(
        date=ctx.target_date,
        timestamp=datetime.now().isoformat(),
        source=ctx.source_tag,
        nota_agente=9,
        alertas_criticos=[
            "Evitar operações contra tendência sem confirmação clara de exaustão.",
            "Monitorar possível inversão por evento macro na abertura.",
        ],
        incoerencias=incoerencias,
        filtros_bloqueantes=[],
        parametros_questionados=[
            "Threshold de reversão deve ser mais rígido quando ADX estiver alto.",
        ],
        sugestoes=sugestoes,
        custo_oportunidade_pts=0.0,
        eficiencia_pct=0.0,
        hold_pct=58.0,
        win_rate_pct=wr,
        market_range_pts=market_range_pts,
        n_opportunities=m.opportunities,
        n_episodes=m.episodes,
        threshold_sugerido_buy=5,
        threshold_sugerido_sell=-3,
        smc_bypass_recomendado=False,
        trend_following_recomendado=True,
        max_adx_para_trend=25.0,
        confianca_minima_sugerida=60.0,
        regioes_fortes=["Pullback em tendência com confirmação micro e fluxo."],
        regioes_armadilhas=["Reversão prematura em tendência forte."],
        veredicto_regioes="Operar preferencialmente continuidade e evitar extremos sem confirmação.",
        direcional_vieses=direcional_vieses,
        direcional_contradicoes=[],
        direcional_questionamentos=["A abertura confirmará continuidade de baixa ou lateralização de ajuste?"],
        veredicto_direcional="Viés vendedor moderado, execução seletiva em pullbacks.",
        confianca_direcional_ajustada=62.0,
        guardian_kill_switch=False,
        guardian_kill_reason="",
        guardian_reduced_exposure=True,
        guardian_confidence_penalty=8.0,
        guardian_bias_override="",
        guardian_scenario_changes=1,
        guardian_alertas=["Se ADX cair e spread de score reduzir, diminuir convicção direcional."],
        macro_signal_dominante="BEARISH" if m.macro_sell_count > m.macro_buy_count else "NEUTRAL",
        smc_equilibrium_dominante="DISCOUNT",
        adx_medio=44.0,
        micro_score_medio=m.micro_avg,
        active=True,
    )


def _append_markdown(ctx: Ctx, m: DayMetrics, directive: HeadDirective, feedback: DiaryFeedback) -> bool:
    ctx.diario_md.parent.mkdir(parents=True, exist_ok=True)

    if not ctx.diario_md.exists():
        ctx.diario_md.write_text(
            f"# Diário Head - {ctx.target_date}\n\n"
            "Registro operacional e diretrizes para o próximo pregão útil.\n",
            encoding="utf-8",
        )

    marker = f"<!-- SOURCE_TAG: {ctx.source_tag} -->"
    content = ctx.diario_md.read_text(encoding="utf-8", errors="ignore")
    if marker in content:
        return False

    wins = m.wins
    losses = m.losses
    wr = (wins / max(1, wins + losses)) * 100

    block = (
        "\n"
        f"{marker}\n"
        f"## Diretiva Pós-Pregão {m.ref_date} aplicada para {ctx.target_date}\n\n"
        "### Leitura de Mercado (base factual)\n"
        f"- Faixa de preço: {m.pmin:.0f} - {m.pmax:.0f} (range {m.pmax - m.pmin:.0f} pts)\n"
        f"- Macro: média {m.macro_avg:+.1f}, VENDA={m.macro_sell_count}, COMPRA={m.macro_buy_count}\n"
        f"- Execução real: trades={m.closed_trades}, W/L={wins}/{losses}, WR={wr:.0f}%, PnL={m.pnl_total:+.0f} pts\n\n"
        "### Plano Operacional\n"
        f"- Direção: {directive.direction} | Confiança: {directive.confidence_market}% | Agressividade: {directive.aggressiveness}\n"
        f"- Exposição: {directive.position_size_pct}% | Stop: {directive.stop_loss_pts} pts | Max trades: {directive.max_daily_trades}\n"
        f"- Zona ideal de venda: {directive.ideal_sell_zone_low:.0f} - {directive.ideal_sell_zone_high:.0f}\n"
        f"- Zona ideal de compra: {directive.ideal_buy_zone_low:.0f} - {directive.ideal_buy_zone_high:.0f}\n"
        f"- Evitar extremos: acima de {directive.forbidden_zone_above:.0f} e abaixo de {directive.forbidden_zone_below:.0f}\n\n"
        "### Aprendizados do Modelo\n"
        f"- threshold_sugerido_buy={feedback.threshold_sugerido_buy}, threshold_sugerido_sell={feedback.threshold_sugerido_sell}\n"
        f"- trend_following_recomendado={'SIM' if feedback.trend_following_recomendado else 'NÃO'}\n"
        "- Reforço principal: reduzir reversão prematura em tendência forte e priorizar continuidade em pullback.\n"
    )

    with ctx.diario_md.open("a", encoding="utf-8") as f:
        f.write(block)

    return True


def main() -> int:
    args = _parse_args()

    try:
        datetime.strptime(args.base_date, "%Y-%m-%d")
    except ValueError:
        print("[ERRO] --base-date inválida. Use YYYY-MM-DD.")
        return 2

    holidays = _load_holidays(Path(args.calendar_file))
    target_date = _next_business_day(args.base_date, holidays)
    ctx = Ctx(base_date=args.base_date, target_date=target_date)

    if not ctx.db_path.exists():
        print(f"[ERRO] Banco não encontrado: {ctx.db_path}")
        return 1

    metrics = _fetch_metrics(ctx.db_path, ctx.base_date)
    directive = _derive_head_directive(ctx, metrics)
    feedback = _derive_diary_feedback(ctx, metrics)

    did = save_directive(str(ctx.db_path), directive)
    fid = save_diary_feedback(str(ctx.db_path), feedback)
    md = _append_markdown(ctx, metrics, directive, feedback)

    print("=" * 96)
    print(
        f"DIRETIVA PÓS-PREGÃO APLICADA | base={ctx.base_date} -> alvo={ctx.target_date} | "
        f"head_id={did} | feedback_id={fid} | diario_md={'OK' if md else 'SKIP'}"
    )
    print("=" * 96)
    print(f"source_tag={ctx.source_tag}")
    print(f"arquivo_diario={ctx.diario_md}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
