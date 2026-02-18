#!/usr/bin/env python3
"""
Aplica lições de um BDI para um pregão alvo.

Exemplo:
  python scripts/aplicar_licoes_bdi.py --bdi-date 20260212 --target-date 2026-02-13

Fluxo:
1) Lê artefato de extração do BDI (data/BDI/bdi_<data>_key_data.txt)
2) Persiste diretiva ativa do Head (head_directives)
3) Persiste feedback no diário operacional (diary_feedback)
4) Persiste anotação histórica no reflections_log.jsonl
5) Registra resumo em diário markdown do pregão alvo

Idempotência: source_tag + target_date.
"""

from __future__ import annotations

import argparse
import json
import sqlite3
import sys
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from src.application.services.diary_feedback import DiaryFeedback, save_diary_feedback
from src.application.services.head_directives import (
    HeadDirective,
    load_active_directive,
    save_directive,
)


@dataclass
class LessonContext:
    bdi_date_code: str
    target_date: str

    @property
    def bdi_date_human(self) -> str:
        return f"{self.bdi_date_code[6:8]}/{self.bdi_date_code[4:6]}/{self.bdi_date_code[0:4]}"

    @property
    def target_date_human(self) -> str:
        d = self.target_date.replace("-", "")
        return f"{d[6:8]}/{d[4:6]}/{d[0:4]}"

    @property
    def target_date_compact(self) -> str:
        return self.target_date.replace("-", "")

    @property
    def source_tag(self) -> str:
        return f"head_bdi_{self.bdi_date_code}_para_{self.target_date_compact}"

    @property
    def db_path(self) -> Path:
        return ROOT_DIR / "data" / "db" / "trading.db"

    @property
    def bdi_key_file(self) -> Path:
        return ROOT_DIR / "data" / "BDI" / f"bdi_{self.bdi_date_code}_key_data.txt"

    @property
    def bdi_pdf_file(self) -> Path:
        return ROOT_DIR / "data" / "BDI" / f"BDI_00_{self.bdi_date_code}.pdf"

    @property
    def reflections_log(self) -> Path:
        return ROOT_DIR / "data" / "db" / "reflections" / "reflections_log.jsonl"

    @property
    def diario_md(self) -> Path:
        return ROOT_DIR / "data" / "diarios" / f"diario_head_{self.target_date_compact}.md"


def _parse_bdi_totais(ctx: LessonContext) -> tuple[str, str]:
    total_com_minis = "n/d"
    total_sem_minis = "n/d"

    if not ctx.bdi_key_file.exists():
        return total_com_minis, total_sem_minis

    for line in ctx.bdi_key_file.read_text(encoding="utf-8", errors="ignore").splitlines():
        if "Total com minis" in line and total_com_minis == "n/d":
            tokens = line.replace(".", "").split()
            for tk in tokens:
                if tk.isdigit() and len(tk) >= 6:
                    total_com_minis = f"{int(tk):,}".replace(",", ".")
                    break
        if "Total sem minis" in line and total_sem_minis == "n/d":
            tokens = line.replace(".", "").split()
            for tk in tokens:
                if tk.isdigit() and len(tk) >= 6:
                    total_sem_minis = f"{int(tk):,}".replace(",", ".")
                    break
        if total_com_minis != "n/d" and total_sem_minis != "n/d":
            break

    return total_com_minis, total_sem_minis


def _feedback_ja_registrado(ctx: LessonContext) -> bool:
    if not ctx.db_path.exists():
        return False

    conn = sqlite3.connect(str(ctx.db_path))
    try:
        row = conn.execute(
            """
            SELECT id FROM diary_feedback
            WHERE date = ? AND source = ?
            ORDER BY id DESC LIMIT 1
            """,
            (ctx.target_date, ctx.source_tag),
        ).fetchone()
        return row is not None
    except Exception:
        return False
    finally:
        conn.close()


def _diretiva_ja_registrada(ctx: LessonContext) -> int:
    if not ctx.db_path.exists():
        return 0

    conn = sqlite3.connect(str(ctx.db_path))
    try:
        row = conn.execute(
            """
            SELECT id FROM head_directives
            WHERE date = ? AND source = ? AND active = 1
            ORDER BY id DESC LIMIT 1
            """,
            (ctx.target_date, ctx.source_tag),
        ).fetchone()
        return int(row[0]) if row else 0
    except Exception:
        return 0
    finally:
        conn.close()


def _registrar_diretiva(ctx: LessonContext, total_com_minis: str, total_sem_minis: str) -> int:
    directive_exists = _diretiva_ja_registrada(ctx)
    if directive_exists:
        return directive_exists

    directive = HeadDirective(
        date=ctx.target_date,
        created_at=datetime.now().isoformat(),
        source=ctx.source_tag,
        analyst="Head de Finanças - Mercado Futuro BR",
        direction="NEUTRAL",
        confidence_market=55,
        aggressiveness="MODERATE",
        position_size_pct=70,
        stop_loss_pts=280,
        max_daily_trades=4,
        max_rsi_for_buy=70,
        min_rsi_for_sell=30,
        min_adx_for_entry=18,
        forbidden_zone_above=190600.0,
        forbidden_zone_below=186800.0,
        ideal_buy_zone_low=187200.0,
        ideal_buy_zone_high=188100.0,
        ideal_sell_zone_low=189500.0,
        ideal_sell_zone_high=190200.0,
        reduce_before_event=False,
        event_description="Sem evento macro crítico validado no repositório. Monitorar agenda ao vivo antes da abertura.",
        event_time="",
        notes=(
            f"BDI {ctx.bdi_date_human}: Derivativos com minis={total_com_minis}, sem minis={total_sem_minis}. "
            f"Plano para {ctx.target_date_human}: operar zonas de valor com exposição reduzida, "
            "evitando perseguição de preço em extremos."
        ),
        risk_scenario=(
            "Risco principal: continuação de distribuição intraday com serrilhado e falsa retomada. "
            "Mitigação: reduzir tamanho de posição para 70%, stop de 280 pts e máximo de 4 trades."
        ),
        active=True,
    )

    return save_directive(str(ctx.db_path), directive)


def _registrar_feedback(ctx: LessonContext) -> int:
    if _feedback_ja_registrado(ctx):
        return 0

    feedback = DiaryFeedback(
        date=ctx.target_date,
        timestamp=datetime.now().isoformat(),
        source=ctx.source_tag,
        nota_agente=7,
        alertas_criticos=[
            "Evitar overtrade em rompimento tardio sem confirmação de fluxo.",
            "Validar agenda macro antes da abertura para reduzir risco de surpresa.",
        ],
        incoerencias=[
            "Direção diária pode divergir de reversão intraday; manter leitura por contexto e não por viés fixo.",
        ],
        filtros_bloqueantes=[
            "Não travar em HOLD quando houver tendência inicial clara com pullback validado.",
        ],
        parametros_questionados=[
            "Threshold de entrada excessivo pode gerar paralisia em aceleração de mercado.",
        ],
        sugestoes=[
            "Priorizar compras em desconto com confirmação micro.",
            "Reduzir agressividade ao perder suporte com fluxo vendedor.",
            "Encerrar tentativa de rompimento após falhas consecutivas no topo intraday.",
        ],
        custo_oportunidade_pts=420.0,
        eficiencia_pct=62.0,
        hold_pct=58.0,
        win_rate_pct=50.0,
        market_range_pts=2810.0,
        n_opportunities=6,
        n_episodes=12,
        threshold_sugerido_buy=4,
        threshold_sugerido_sell=-4,
        smc_bypass_recomendado=True,
        trend_following_recomendado=True,
        max_adx_para_trend=24.0,
        confianca_minima_sugerida=52.0,
        regioes_fortes=["compra em desconto", "realização/venda tática em resistência"],
        regioes_armadilhas=["compra tardia em esticamento", "venda em exaustão"],
        veredicto_regioes="Operar regiões de valor e evitar extremos.",
        direcional_vieses=["Viés neutro com gatilhos por preço/região"],
        direcional_contradicoes=["Movimento agregado e intraday podem divergir"],
        direcional_questionamentos=["Fluxo institucional confirmará continuidade ou lateralização?"],
        veredicto_direcional="NEUTRAL com assimetria por contexto.",
        confianca_direcional_ajustada=55.0,
        guardian_kill_switch=False,
        guardian_kill_reason="",
        guardian_reduced_exposure=True,
        guardian_confidence_penalty=8.0,
        guardian_bias_override="",
        guardian_scenario_changes=2,
        guardian_alertas=[
            "Reduzir exposição após falhas repetidas de rompimento.",
            "Evitar terceira tentativa sem novo contexto de fluxo.",
        ],
        macro_signal_dominante="NEUTRO",
        smc_equilibrium_dominante="DISCOUNT",
        adx_medio=21.0,
        micro_score_medio=3.8,
        active=True,
    )

    return save_diary_feedback(str(ctx.db_path), feedback)


def _append_reflection_once(ctx: LessonContext, total_com_minis: str, total_sem_minis: str) -> bool:
    ctx.reflections_log.parent.mkdir(parents=True, exist_ok=True)

    if ctx.reflections_log.exists():
        for line in ctx.reflections_log.read_text(encoding="utf-8", errors="ignore").splitlines()[-400:]:
            if ctx.source_tag in line and ctx.target_date in line:
                return False

    payload = {
        "timestamp": datetime.now().isoformat(),
        "entry_id": f"HEAD_{ctx.source_tag}_{datetime.now().strftime('%H%M%S')}",
        "date": ctx.target_date,
        "source": ctx.source_tag,
        "type": "head_lesson",
        "title": f"Lições BDI {ctx.bdi_date_human} aplicadas para {ctx.target_date_human}",
        "summary": (
            "Aplicação de lições do boletim BDI para reduzir exposição, "
            "operar zonas de valor e evitar extremos no pregão alvo."
        ),
        "market_observations": [
            f"BDI referência: {ctx.bdi_date_human}.",
            f"Derivativos com minis: {total_com_minis}; sem minis: {total_sem_minis}.",
            "Plano tático baseado em zonas e controle de risco.",
        ],
        "plan_today": [
            "Compra preferencial em desconto com confirmação micro.",
            "Realização/venda tática em resistência.",
            "Evitar perseguição de preço nos extremos.",
        ],
    }

    with ctx.reflections_log.open("a", encoding="utf-8") as f:
        f.write(json.dumps(payload, ensure_ascii=False) + "\n")

    return True


def _append_diario_markdown(ctx: LessonContext, total_com_minis: str, total_sem_minis: str) -> bool:
    ctx.diario_md.parent.mkdir(parents=True, exist_ok=True)

    if not ctx.diario_md.exists():
        ctx.diario_md.write_text(
            f"# Diário Head - {ctx.target_date_human}\n\n"
            "Registro operacional e lições aplicadas para o pregão.\n\n",
            encoding="utf-8",
        )

    current = ctx.diario_md.read_text(encoding="utf-8", errors="ignore")
    marker = f"## Lições BDI {ctx.bdi_date_human} aplicadas"
    legacy_marker = f"## Lições BDI {ctx.bdi_date_human[:5]} aplicadas"
    source_marker = f"<!-- SOURCE_TAG: {ctx.source_tag} -->"
    if marker in current or legacy_marker in current or source_marker in current:
        return False

    bloco = (
        "\n"
        f"<!-- SOURCE_TAG: {ctx.source_tag} -->\n"
        f"## Lições BDI {ctx.bdi_date_human} aplicadas\n\n"
        "### Síntese do BDI (fatos extraídos)\n\n"
        f"- Derivativos total com minis: **{total_com_minis}** contratos (dia).\n"
        f"- Derivativos total sem minis: **{total_sem_minis}** contratos (dia).\n"
        f"- Boletim referência: `data/BDI/BDI_00_{ctx.bdi_date_code}.pdf` (extração em `data/BDI/bdi_{ctx.bdi_date_code}_key_data.txt`).\n\n"
        f"### Pontos de atenção para {ctx.target_date_human}\n\n"
        "- Operar zonas de valor, evitando perseguição de preço em extremos.\n"
        "- Manter exposição reduzida (70%), stop de 280 pts e máximo de 4 trades.\n"
        "- Revalidar contexto macro antes da abertura e após mudanças de regime intraday.\n\n"
        "---\n"
    )

    with ctx.diario_md.open("a", encoding="utf-8") as f:
        f.write(bloco)

    return True


def _build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Aplica lições de um BDI para um pregão alvo.")
    parser.add_argument("--bdi-date", required=True, help="Data do BDI no formato YYYYMMDD (ex: 20260212).")
    parser.add_argument("--target-date", required=True, help="Data do pregão alvo no formato YYYY-MM-DD (ex: 2026-02-13).")
    return parser


def _validate_dates(bdi_date: str, target_date: str) -> None:
    datetime.strptime(bdi_date, "%Y%m%d")
    datetime.strptime(target_date, "%Y-%m-%d")


def main() -> int:
    parser = _build_arg_parser()
    args = parser.parse_args()

    try:
        _validate_dates(args.bdi_date, args.target_date)
    except ValueError:
        print("[ERRO] Formato de data inválido. Use --bdi-date YYYYMMDD e --target-date YYYY-MM-DD.")
        return 2

    ctx = LessonContext(bdi_date_code=args.bdi_date, target_date=args.target_date)

    total_com_minis, total_sem_minis = _parse_bdi_totais(ctx)

    directive_id = _registrar_diretiva(ctx, total_com_minis, total_sem_minis)
    feedback_id = _registrar_feedback(ctx)
    reflection_added = _append_reflection_once(ctx, total_com_minis, total_sem_minis)
    diario_added = _append_diario_markdown(ctx, total_com_minis, total_sem_minis)

    loaded = load_active_directive(str(ctx.db_path), ctx.target_date)
    if loaded is None:
        print("[ERRO] Diretiva ativa não encontrada após gravação.")
        return 1

    print("=" * 72)
    print(f"  LIÇÕES BDI {ctx.bdi_date_human} APLICADAS COM SUCESSO")
    print("=" * 72)
    print(f"Diretiva ID: {directive_id} | Data: {ctx.target_date} | Direção: {loaded.direction} | Conf: {loaded.confidence_market}%")
    print(f"Feedback diário ID: {feedback_id if feedback_id else 'já existente'}")
    print(f"Reflection JSONL: {'adicionado' if reflection_added else 'já existente'}")
    print(f"Diário markdown: {'adicionado' if diario_added else 'já existente'} -> {ctx.diario_md}")
    print(f"DB: {ctx.db_path}")

    if not ctx.bdi_key_file.exists():
        print(f"[AVISO] Arquivo de extração não encontrado: {ctx.bdi_key_file}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
