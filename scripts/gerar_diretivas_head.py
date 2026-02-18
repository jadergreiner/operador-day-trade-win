"""
Gerador de Diretivas do Head Financeiro.

Converte análises pré-mercado (diários overnight, BDI, etc.) em
diretivas estruturadas que o agente de micro tendências consome.

Uso:
  python scripts/gerar_diretivas_head.py                         # interativo
  python scripts/gerar_diretivas_head.py --from-diary ARQUIVO    # de diário .md
  python scripts/gerar_diretivas_head.py --quick                 # parâmetros via CLI

Exemplos:
  python scripts/gerar_diretivas_head.py --quick \\
    --direction BULLISH --confidence 55 --aggressiveness MODERATE \\
    --position 80 --stop 200 --max-rsi-buy 72 \\
    --forbidden-above 188500 --ideal-buy 187800-188100 \\
    --event "Payroll americano" --event-time "10:30" \\
    --notes "RSI overbought, cautela com ATH"

  python scripts/gerar_diretivas_head.py --from-diary data/diarios/diario_overnight_20260211.md
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
from datetime import datetime, date

ROOT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)

from src.application.services.head_directives import (
    HeadDirective,
    save_directive,
    load_active_directive,
    list_directives,
    create_directives_table,
)


DEFAULT_DB_PATH = os.path.join(ROOT_DIR, "data", "db", "trading.db")


def _parse_diary_markdown(filepath: str) -> HeadDirective:
    """
    Extrai parâmetros de diretiva de um arquivo de diário markdown.
    Procura pelo bloco de parâmetros recomendados (formato chave: valor).
    """
    with open(filepath, "r", encoding="utf-8") as f:
        content = f.read()

    directive = HeadDirective(
        date=date.today().isoformat(),
        created_at=datetime.now().isoformat(),
        source=os.path.basename(filepath),
    )

    # Extrai direção — busca em múltiplos formatos
    direction_patterns = [
        r"DIRE[CÇ][AÃ]O[:\s]+(\w+)",
        r"Bias do Head[:\s\|]+(\w+)",
        r"Cen[aá]rio Base[:\s]+(\w+)",
    ]
    for pat in direction_patterns:
        m = re.search(pat, content, re.IGNORECASE)
        if m:
            val = m.group(1).upper().strip()
            if val in ("BULLISH", "BEARISH", "NEUTRAL", "NEUTRO"):
                directive.direction = "NEUTRAL" if val == "NEUTRO" else val
                break

    # Extrai confiança do mercado
    m = re.search(r"CONFIANÇA[_\s]*(?:MERCADO)?[:\s]+(\d+)", content, re.IGNORECASE)
    if m:
        directive.confidence_market = int(m.group(1))

    # Extrai agressividade
    m = re.search(r"AGRESSIVIDADE[:\s]+(\w+)", content, re.IGNORECASE)
    if m:
        val = m.group(1).upper().strip()
        if val in ("LOW", "BAIXA"):
            directive.aggressiveness = "LOW"
        elif val in ("MODERATE", "MODERADA"):
            directive.aggressiveness = "MODERATE"
        elif val in ("HIGH", "ALTA"):
            directive.aggressiveness = "HIGH"

    # Extrai tamanho de posição
    m = re.search(r"TAMANHO[_\s]*POSI[CÇ][AÃ]O[:\s]+(\d+)", content, re.IGNORECASE)
    if not m:
        m = re.search(r"Posição[:\s]+(\d+)%", content, re.IGNORECASE)
    if m:
        directive.position_size_pct = int(m.group(1))

    # Extrai stop loss
    m = re.search(r"STOP[_\s]*LOSS[:\s]+(?:MODERADO\s*\()?(\d+)\s*(?:pts|pontos)", content, re.IGNORECASE)
    if not m:
        m = re.search(r"Stop[:\s]+(\d+)\s*(?:pts|pontos)", content, re.IGNORECASE)
    if m:
        directive.stop_loss_pts = int(m.group(1))

    # Extrai RSI máximo para BUY
    m = re.search(r"RSI[_\s]*M[AÁ]XIMO[_\s]*(?:PARA[_\s]*)?BUY[:\s]+(\d+)", content, re.IGNORECASE)
    if m:
        directive.max_rsi_for_buy = int(m.group(1))

    # Extrai zona proibida para BUY
    m = re.search(r"ZONA[_\s]*PROIBIDA[_\s]*(?:BUY)?[:\s]+(?:Acima de\s*)?(\d[\d.,]+)", content, re.IGNORECASE)
    if m:
        val = m.group(1).replace(".", "").replace(",", ".")
        directive.forbidden_zone_above = float(val)

    # Extrai zona ideal de compra
    m = re.search(
        r"ZONA[_\s]*IDEAL[_\s]*(?:BUY|COMPRA)?[:\s]+(\d[\d.,]+)\s*[-–a]\s*(\d[\d.,]+)",
        content, re.IGNORECASE,
    )
    if m:
        low = m.group(1).replace(".", "").replace(",", ".")
        high = m.group(2).replace(".", "").replace(",", ".")
        directive.ideal_buy_zone_low = float(low)
        directive.ideal_buy_zone_high = float(high)

    # Extrai zona de stop (converte para forbidden_zone_below para SELL)
    m = re.search(r"ZONA[_\s]*STOP[:\s]+(?:Abaixo de\s*)?(\d[\d.,]+)", content, re.IGNORECASE)
    if m:
        val = m.group(1).replace(".", "").replace(",", ".")
        directive.forbidden_zone_below = float(val)

    # Extrai horário crítico / evento
    m = re.search(r"HOR[AÁ]RIO[_\s]*CR[IÍ]TICO[:\s]+(.*?)(?:\n|$)", content, re.IGNORECASE)
    if m:
        directive.event_description = m.group(1).strip()
        directive.reduce_before_event = True
        # Tenta extrair horário do evento
        time_match = re.search(r"(\d{1,2}:\d{2})", m.group(1))
        if time_match:
            directive.event_time = time_match.group(1)

    # Extrai eventos da tabela de eventos
    event_matches = re.findall(
        r"\|\s*(\d{1,2}:\d{2}|TBD|Manhã|Contínuo)\s*\|\s*\*\*(.+?)\*\*\s*\|.*?(MUITO ALTO|ALTO)",
        content,
    )
    if event_matches:
        # Pega o evento de maior impacto
        for evt_time, evt_desc, evt_impact in event_matches:
            if evt_impact == "MUITO ALTO":
                directive.event_description = evt_desc.strip()
                directive.reduce_before_event = True
                if re.match(r"\d{1,2}:\d{2}", evt_time):
                    directive.event_time = evt_time
                break

    # Extrai cenário de risco
    m = re.search(r"Risco principal[:\s]+(.+?)(?:\n|$)", content, re.IGNORECASE)
    if m:
        directive.risk_scenario = m.group(1).strip()

    # Extrai notas do veredicto executivo (primeira frase)
    m = re.search(r"VEREDICTO EXECUTIVO\s*\n+\*\*(.+?)\*\*", content, re.IGNORECASE)
    if m:
        directive.notes = m.group(1).strip()[:200]

    return directive


def _interactive_mode(db_path: str) -> None:
    """Modo interativo para criação de diretivas."""
    print("\n╔════════════════════════════════════════════════════════╗")
    print("║     GERADOR DE DIRETIVAS — HEAD FINANCEIRO           ║")
    print("╚════════════════════════════════════════════════════════╝\n")

    d = HeadDirective(
        date=date.today().isoformat(),
        created_at=datetime.now().isoformat(),
        source="interactive",
    )

    # Direção
    print("  Direção do mercado:")
    print("    1) BULLISH")
    print("    2) BEARISH")
    print("    3) NEUTRAL")
    choice = input("  Escolha [1-3, default=3]: ").strip() or "3"
    d.direction = {"1": "BULLISH", "2": "BEARISH", "3": "NEUTRAL"}.get(choice, "NEUTRAL")

    # Confiança
    val = input(f"  Confiança do mercado (0-100) [default=50]: ").strip() or "50"
    d.confidence_market = max(0, min(100, int(val)))

    # Agressividade
    print("  Agressividade:")
    print("    1) LOW")
    print("    2) MODERATE")
    print("    3) HIGH")
    choice = input("  Escolha [1-3, default=2]: ").strip() or "2"
    d.aggressiveness = {"1": "LOW", "2": "MODERATE", "3": "HIGH"}.get(choice, "MODERATE")

    # Posição
    val = input("  Tamanho posição % (0-100) [default=100]: ").strip() or "100"
    d.position_size_pct = max(0, min(100, int(val)))

    # Stop
    val = input("  Stop loss em pontos (0=padrão) [default=0]: ").strip() or "0"
    d.stop_loss_pts = max(0, int(val))

    # RSI
    val = input("  RSI máx para BUY (0=sem filtro) [default=0]: ").strip() or "0"
    d.max_rsi_for_buy = max(0, int(val))

    # Zona proibida
    val = input("  Zona proibida BUY acima de (0=sem) [default=0]: ").strip() or "0"
    d.forbidden_zone_above = float(val.replace(".", "").replace(",", ".") if val != "0" else "0")

    # Zona ideal
    val = input("  Zona ideal BUY (ex: 187800-188100, vazio=sem): ").strip()
    if val and "-" in val:
        parts = val.split("-")
        d.ideal_buy_zone_low = float(parts[0].replace(".", "").replace(",", "."))
        d.ideal_buy_zone_high = float(parts[1].replace(".", "").replace(",", "."))

    # Evento
    val = input("  Evento macro (vazio=sem): ").strip()
    if val:
        d.event_description = val
        d.reduce_before_event = True
        t = input("  Horário do evento (HH:MM, vazio=sem): ").strip()
        if t:
            d.event_time = t

    # Notas
    val = input("  Notas/observações (vazio=sem): ").strip()
    if val:
        d.notes = val

    # Confirma
    print("\n  ── RESUMO DA DIRETIVA ──")
    _print_directive(d)
    confirm = input("\n  Salvar? (S/N) [default=S]: ").strip().upper() or "S"
    if confirm == "S":
        row_id = save_directive(db_path, d)
        print(f"\n  ✓ Diretiva salva com ID {row_id}")
    else:
        print("  ✗ Cancelado.")


def _print_directive(d: HeadDirective) -> None:
    """Exibe uma diretiva formatada."""
    dir_icon = "🟢" if d.direction == "BULLISH" else ("🔴" if d.direction == "BEARISH" else "⚪")
    print(f"  {dir_icon} Direção: {d.direction} │ Confiança: {d.confidence_market}%")
    print(f"  Agressividade: {d.aggressiveness} │ Posição: {d.position_size_pct}%")
    print(f"  Stop: {d.stop_loss_pts or 'padrão'} pts │ Max trades: {d.max_daily_trades or 'padrão'}")
    if d.max_rsi_for_buy > 0:
        print(f"  RSI máx BUY: {d.max_rsi_for_buy} │ RSI mín SELL: {d.min_rsi_for_sell}")
    if d.forbidden_zone_above > 0:
        print(f"  🚫 BUY proibido acima de: {d.forbidden_zone_above:.0f}")
    if d.ideal_buy_zone_low > 0:
        print(f"  ✅ Zona ideal BUY: {d.ideal_buy_zone_low:.0f} - {d.ideal_buy_zone_high:.0f}")
    if d.reduce_before_event:
        print(f"  ⚠️  Evento: {d.event_description} ({d.event_time})")
    if d.notes:
        print(f"  📝 {d.notes}")
    if d.risk_scenario:
        print(f"  ⚡ Risco: {d.risk_scenario}")
    print(f"  Fonte: {d.source} │ Data: {d.date}")


def main():
    parser = argparse.ArgumentParser(
        description="Gera diretivas do Head Financeiro para o agente de micro tendências",
    )
    parser.add_argument(
        "--db", default=DEFAULT_DB_PATH,
        help=f"Caminho do banco SQLite (default: {DEFAULT_DB_PATH})",
    )
    parser.add_argument(
        "--from-diary", metavar="ARQUIVO",
        help="Gera diretiva automaticamente a partir de um diário .md",
    )
    parser.add_argument("--quick", action="store_true", help="Modo rápido via CLI")
    parser.add_argument("--list", action="store_true", help="Lista diretivas recentes")
    parser.add_argument("--show", action="store_true", help="Mostra diretiva ativa de hoje")

    # Parâmetros do modo --quick
    parser.add_argument("--direction", choices=["BULLISH", "BEARISH", "NEUTRAL"], default="NEUTRAL")
    parser.add_argument("--confidence", type=int, default=50)
    parser.add_argument("--aggressiveness", choices=["LOW", "MODERATE", "HIGH"], default="MODERATE")
    parser.add_argument("--position", type=int, default=100, help="Tamanho posição %")
    parser.add_argument("--stop", type=int, default=0, help="Stop loss em pontos")
    parser.add_argument("--max-rsi-buy", type=int, default=0, help="RSI máx para BUY")
    parser.add_argument("--min-rsi-sell", type=int, default=100, help="RSI mín para SELL")
    parser.add_argument("--forbidden-above", type=float, default=0, help="BUY proibido acima de")
    parser.add_argument("--forbidden-below", type=float, default=0, help="SELL proibido abaixo de")
    parser.add_argument("--ideal-buy", metavar="LOW-HIGH", help="Zona ideal BUY ex: 187800-188100")
    parser.add_argument("--ideal-sell", metavar="LOW-HIGH", help="Zona ideal SELL")
    parser.add_argument("--event", help="Descrição do evento macro")
    parser.add_argument("--event-time", help="Horário do evento (HH:MM)")
    parser.add_argument("--max-trades", type=int, default=0, help="Max trades dia")
    parser.add_argument("--notes", help="Notas/observações")
    parser.add_argument("--risk", help="Cenário de risco")

    args = parser.parse_args()

    # Garante que tabela existe
    create_directives_table(args.db)

    # Modo --list
    if args.list:
        directives = list_directives(args.db)
        if not directives:
            print("  Nenhuma diretiva encontrada.")
            return
        for d in directives:
            active = "✓" if d.active else "✗"
            print(f"\n  [{active}] {d.date} — {d.source}")
            _print_directive(d)
        return

    # Modo --show
    if args.show:
        d = load_active_directive(args.db)
        if d:
            print(f"\n  Diretiva ativa para hoje:")
            _print_directive(d)
        else:
            print("  Sem diretiva ativa para hoje.")
        return

    # Modo --from-diary
    if args.from_diary:
        filepath = args.from_diary
        if not os.path.exists(filepath):
            filepath = os.path.join(ROOT_DIR, filepath)
        if not os.path.exists(filepath):
            print(f"  ✗ Arquivo não encontrado: {args.from_diary}")
            sys.exit(1)

        print(f"\n  Processando diário: {os.path.basename(filepath)}")
        d = _parse_diary_markdown(filepath)
        print(f"\n  ── DIRETIVA EXTRAÍDA ──")
        _print_directive(d)

        confirm = input("\n  Salvar? (S/N) [default=S]: ").strip().upper() or "S"
        if confirm == "S":
            row_id = save_directive(args.db, d)
            print(f"\n  ✓ Diretiva salva com ID {row_id}")
        else:
            print("  ✗ Cancelado.")
        return

    # Modo --quick
    if args.quick:
        d = HeadDirective(
            date=date.today().isoformat(),
            created_at=datetime.now().isoformat(),
            source="cli_quick",
            direction=args.direction,
            confidence_market=args.confidence,
            aggressiveness=args.aggressiveness,
            position_size_pct=args.position,
            stop_loss_pts=args.stop,
            max_daily_trades=args.max_trades,
            max_rsi_for_buy=args.max_rsi_buy,
            min_rsi_for_sell=args.min_rsi_sell,
            forbidden_zone_above=args.forbidden_above,
            forbidden_zone_below=args.forbidden_below,
            notes=args.notes or "",
            risk_scenario=args.risk or "",
        )

        if args.ideal_buy and "-" in args.ideal_buy:
            parts = args.ideal_buy.split("-")
            d.ideal_buy_zone_low = float(parts[0])
            d.ideal_buy_zone_high = float(parts[1])

        if args.ideal_sell and "-" in args.ideal_sell:
            parts = args.ideal_sell.split("-")
            d.ideal_sell_zone_low = float(parts[0])
            d.ideal_sell_zone_high = float(parts[1])

        if args.event:
            d.event_description = args.event
            d.reduce_before_event = True
            d.event_time = args.event_time or ""

        row_id = save_directive(args.db, d)
        print(f"\n  ✓ Diretiva salva com ID {row_id}")
        _print_directive(d)
        return

    # Modo interativo (padrão)
    _interactive_mode(args.db)


if __name__ == "__main__":
    main()
