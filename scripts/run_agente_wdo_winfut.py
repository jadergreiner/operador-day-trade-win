#!/usr/bin/env python3
"""
Runner do Agente WDO/WINFUT Macro Score.

Executa o scoring duplo (WDO + WINFUT), exibe resultado formatado no console
e persiste no SQLite. Pode ser executado periodicamente via .bat ou cron.

Uso:
    python run_agente_wdo_winfut.py                    # Execucao unica
    python run_agente_wdo_winfut.py --loop              # Loop continuo (30 min)
    python run_agente_wdo_winfut.py --loop --interval 60 # Loop a cada 60 min
    python run_agente_wdo_winfut.py --fred-key YOUR_KEY  # Com API key FRED
"""

from __future__ import annotations

import argparse
import logging
import os
import sys
import time
from datetime import datetime, timezone, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

# Adicionar raiz do projeto ao path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from scripts.agente_wdo_winfut.agente_wdo_winfut import AgenteWdoWinfut

# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------

LOG_DIR = PROJECT_ROOT / "data" / "logs"
LOG_DIR.mkdir(parents=True, exist_ok=True)


def setup_logging(verbose: bool = False):
    level = logging.DEBUG if verbose else logging.INFO
    fmt = "%(asctime)s | %(levelname)-7s | %(name)s | %(message)s"
    handlers = [
        logging.StreamHandler(sys.stdout),
        logging.FileHandler(str(LOG_DIR / "agente_wdo_winfut.log"), encoding="utf-8"),
    ]
    logging.basicConfig(level=level, format=fmt, handlers=handlers)


# ---------------------------------------------------------------------------
# Formatacao do Resultado
# ---------------------------------------------------------------------------

CORES = {
    "STRONG_BUY": "\033[92m\033[1m",   # Verde brilhante
    "BUY": "\033[92m",                  # Verde
    "NEUTRAL": "\033[93m",              # Amarelo
    "SELL": "\033[91m",                 # Vermelho
    "STRONG_SELL": "\033[91m\033[1m",   # Vermelho brilhante
    "VETO": "\033[95m\033[1m",          # Magenta
    "RESET": "\033[0m",
    "BOLD": "\033[1m",
    "DIM": "\033[2m",
    "CYAN": "\033[96m",
    "WHITE": "\033[97m",
    "GREEN": "\033[92m",
    "YELLOW": "\033[93m",
    "RED": "\033[91m",
}


def barra_score(score: float, max_score: float = 20.0) -> str:
    """Gera barra visual ASCII para o score."""
    width = 40
    center = width // 2
    normalized = max(min(score / max_score, 1.0), -1.0)
    fill = int(abs(normalized) * center)

    bar = list("." * width)
    bar[center] = "|"

    if normalized > 0:
        for i in range(center + 1, min(center + 1 + fill, width)):
            bar[i] = "█"
    elif normalized < 0:
        for i in range(max(center - fill, 0), center):
            bar[i] = "█"

    return "".join(bar)


def formatar_resultado(resultado: dict) -> str:
    """Formata resultado completo para exibicao no console."""
    c = CORES
    lines = []

    lines.append("")
    lines.append(f"{c['BOLD']}{'='*72}{c['RESET']}")
    lines.append(f"{c['BOLD']}{c['CYAN']}  AGENTE WDO/WINFUT MACRO SCORE  {c['RESET']}")
    lines.append(f"{c['DIM']}  {resultado['timestamp']}{c['RESET']}")
    lines.append(f"{c['BOLD']}{'='*72}{c['RESET']}")

    # --- VETO ---
    if resultado.get("veto"):
        lines.append(f"\n  {c['VETO']}⚠  {resultado['veto_msg']}  ⚠{c['RESET']}\n")

    # --- WDO ---
    wdo = resultado["wdo"]
    cor_wdo = c.get(wdo["veredito"], c["NEUTRAL"])
    lines.append(f"\n{c['BOLD']}  ╔══════════════════════════════════════════════════════╗{c['RESET']}")
    lines.append(f"{c['BOLD']}  ║  WDO (Dolar Futuro / USDBRL)                         ║{c['RESET']}")
    lines.append(f"{c['BOLD']}  ╚══════════════════════════════════════════════════════╝{c['RESET']}")
    lines.append(f"  Score Raw:     {wdo['score_raw']:+.1f}")
    lines.append(f"  Score Ajust:   {wdo['score_ajustado']:+.1f}  (x{wdo['multiplicador_sessao']:.1f} {wdo['sessao']})")
    lines.append(f"  Veredito:      {cor_wdo}{wdo['veredito']}{c['RESET']}")
    lines.append(f"  Confianca:     {wdo['confianca']:.1f}%")
    lines.append(f"  Score Bar:     [{barra_score(wdo['score_ajustado'])}]")
    lines.append(f"  {c['DIM']}--- Capitulos ---{c['RESET']}")
    for cap, val in wdo["scores_capitulos"].items():
        marker = "+" if val > 0 else (" " if val == 0 else "")
        lines.append(f"    {cap:24s} {marker}{val:.0f}")

    # --- WINFUT ---
    winfut = resultado["winfut"]
    cor_winfut = c.get(winfut["veredito"], c["NEUTRAL"])
    lines.append(f"\n{c['BOLD']}  ╔══════════════════════════════════════════════════════╗{c['RESET']}")
    lines.append(f"{c['BOLD']}  ║  WINFUT (Ibovespa Futuro)                            ║{c['RESET']}")
    lines.append(f"{c['BOLD']}  ╚══════════════════════════════════════════════════════╝{c['RESET']}")
    lines.append(f"  Score Raw:     {winfut['score_raw']:+.1f}")
    lines.append(f"  Score Ajust:   {winfut['score_ajustado']:+.1f}  (x{winfut['multiplicador_sessao']:.1f} {winfut['sessao']})")
    lines.append(f"  Veredito:      {cor_winfut}{winfut['veredito']}{c['RESET']}")
    lines.append(f"  Confianca:     {winfut['confianca']:.1f}%")
    lines.append(f"  Score Bar:     [{barra_score(winfut['score_ajustado'])}]")
    lines.append(f"  {c['DIM']}--- Capitulos ---{c['RESET']}")
    for cap, val in winfut["scores_capitulos"].items():
        marker = "+" if val > 0 else (" " if val == 0 else "")
        lines.append(f"    {cap:24s} {marker}{val:.0f}")

    # --- Contexto ---
    lines.append(f"\n{c['BOLD']}  ── Contexto ──{c['RESET']}")
    vix = resultado.get("vix")
    sp = resultado.get("sp500_var_pct")
    lines.append(f"  VIX:           {vix:.2f}" if vix else "  VIX:           N/A")
    lines.append(f"  S&P500 Var:    {sp:+.2f}%" if sp else "  S&P500 Var:    N/A")

    # --- Calendario Economico ---
    cal = resultado.get("calendario", {})
    if cal:
        copom = "SIM" if cal.get("copom_semana") else "nao"
        fomc = "SIM" if cal.get("fomc_semana") else "nao"
        n_br = len(cal.get("eventos_br", []))
        n_us = len(cal.get("eventos_us", []))
        lines.append(f"\n{c['BOLD']}  ── Calendario Economico ──{c['RESET']}")
        lines.append(f"  COPOM semana:  {copom}")
        lines.append(f"  FOMC semana:   {fomc}")
        lines.append(f"  Eventos BR:    {n_br} alto impacto")
        lines.append(f"  Eventos US:    {n_us} alto impacto")
        if cal.get("copom_fomc_mesma_semana"):
            lines.append(f"  {c['VETO']}⚠ COPOM + FOMC mesma semana!{c['RESET']}")

    # --- Threshold / Cobertura ---
    notas_th = resultado.get("threshold_notas", [])
    cob = resultado.get("cobertura_dados", {})
    if notas_th or cob:
        lines.append(f"\n{c['BOLD']}  ── Qualidade do Sinal ──{c['RESET']}")
        if cob:
            total = cob.get("total_itens", 0)
            sem = cob.get("sem_dados", 0)
            com = cob.get("com_dados", 0)
            pct = (com / total * 100) if total > 0 else 0
            cor_cob = c["GREEN"] if pct >= 70 else (c["YELLOW"] if pct >= 50 else c["RED"])
            lines.append(f"  Cobertura:     {cor_cob}{com}/{total} indicadores ({pct:.0f}%){c['RESET']}")
        for nota in notas_th:
            lines.append(f"  {c['YELLOW']}⚠ {nota}{c['RESET']}")

    # --- Detalhes ---
    lines.append(f"\n{c['DIM']}  ── Detalhes (score componentes) ──{c['RESET']}")
    for det in resultado.get("detalhes", []):
        sw = det["score_wdo"]
        si = det["score_winfut"]
        if sw == 0 and si == 0:
            continue  # Skip neutros para limpar output
        lines.append(
            f"  {c['DIM']}{det['capitulo']:22s} {det['componente']:20s} "
            f"WDO={sw:+.0f}  WIN={si:+.0f}  "
            f"[{det['valor_raw'][:40]}]{c['RESET']}"
        )

    lines.append(f"\n{c['BOLD']}{'='*72}{c['RESET']}")
    lines.append("")
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(description="Agente WDO/WINFUT Macro Score")
    parser.add_argument("--loop", action="store_true", help="Execucao em loop continuo")
    parser.add_argument("--interval", type=int, default=5, help="Intervalo em minutos (default: 5)")
    parser.add_argument("--fred-key", type=str, default=None, help="FRED API Key")
    parser.add_argument("--twelvedata-key", type=str, default=None, help="TwelveData API Key")
    parser.add_argument("--alphavantage-key", type=str, default=None, help="AlphaVantage API Key")
    parser.add_argument("--finnhub-key", type=str, default=None, help="Finnhub API Key")
    parser.add_argument("--telegram-token", type=str, default=None, help="Telegram Bot Token")
    parser.add_argument("--telegram-chat-id", type=str, default=None, help="Telegram Chat ID")
    parser.add_argument("--verbose", action="store_true", help="Logging verbose (DEBUG)")
    parser.add_argument("--config", type=str, default=None, help="Path para config JSON customizado")
    args = parser.parse_args()

    setup_logging(args.verbose)
    logger = logging.getLogger("runner_wdo_winfut")

    fred_key = args.fred_key or os.environ.get("FRED_API_KEY")
    twelvedata_key = args.twelvedata_key or os.environ.get("TWELVEDATA_API_KEY")
    alphavantage_key = args.alphavantage_key or os.environ.get("ALPHAVANTAGE_API_KEY")
    finnhub_key = args.finnhub_key or os.environ.get("FINNHUB_API_KEY")
    telegram_token = args.telegram_token or os.environ.get("TELEGRAM_BOT_TOKEN")
    telegram_chat_id = args.telegram_chat_id or os.environ.get("TELEGRAM_CHAT_ID")

    config_path = args.config
    if not config_path:
        # Tenta localizar o config na pasta do agente
        agent_dir = Path(__file__).resolve().parent / "agente_wdo_winfut"
        default_config = agent_dir / "config_wdo_winfut.json"
        if not default_config.exists():
            # Fallback para docs
            default_config = PROJECT_ROOT / "docs" / "model_agente" / "wdo_winfut" / "config_wdo_winfut.json"
        config_path = str(default_config)

    logger.info("Config: %s", config_path)
    logger.info("FRED Key: %s", "***" if fred_key else "DEMO_KEY")
    logger.info("APIs extras: TwelveData=%s, AlphaVantage=%s, Finnhub=%s, Telegram=%s",
                "OK" if twelvedata_key else "--",
                "OK" if alphavantage_key else "--",
                "OK" if finnhub_key else "--",
                "OK" if telegram_token else "--")

    # ── Controle de Horário de Pregão (REC4 Head Financeiro) ──
    BRT = ZoneInfo("America/Sao_Paulo")
    PREGAO_INICIO = 9    # 09:00 BRT
    PREGAO_FIM = 18      # 18:00 BRT (após after-market 17:30 + margem)
    ANALISE_INICIO = 8   # 08:00 BRT — pré-abertura permitida
    ANALISE_FIM = 19     # 19:00 BRT — encerramento final

    def _esta_em_horario_operacional() -> tuple[bool, bool, str]:
        """Verifica se estamos em horário operacional.

        Returns:
            (em_pregao, em_analise, descricao)
            - em_pregao: True se dentro do pregão regular (09-18h BRT)
            - em_analise: True se em janela de análise (08-19h BRT)
            - descricao: texto para exibição
        """
        agora = datetime.now(BRT)
        hora = agora.hour
        minutos = agora.minute
        dia_semana = agora.weekday()  # 0=seg, 6=dom

        # Fim de semana
        if dia_semana >= 5:
            return False, False, f"FIM DE SEMANA ({agora.strftime('%A %H:%M BRT')})"

        # Pregão regular
        if PREGAO_INICIO <= hora < PREGAO_FIM:
            return True, True, f"PREGÃO ATIVO ({agora.strftime('%H:%M BRT')})"

        # Janela de análise (pré/pós)
        if ANALISE_INICIO <= hora < ANALISE_FIM:
            if hora < PREGAO_INICIO:
                return False, True, f"PRÉ-ABERTURA ({agora.strftime('%H:%M BRT')}) — projeção para abertura"
            else:
                return False, True, f"PÓS-MERCADO ({agora.strftime('%H:%M BRT')}) — projeção próximo pregão"

        # Fora de horário
        return False, False, f"FORA DE HORÁRIO ({agora.strftime('%H:%M BRT')})"

    def _tempo_ate_proxima_sessao() -> int:
        """Retorna segundos até próxima janela de análise."""
        agora = datetime.now(BRT)
        hora = agora.hour
        dia_semana = agora.weekday()

        if dia_semana >= 5:
            # Fim de semana → segunda 08:00
            dias_ate_segunda = (7 - dia_semana) % 7
            if dias_ate_segunda == 0:
                dias_ate_segunda = 7
            proxima = agora.replace(hour=ANALISE_INICIO, minute=0, second=0,
                                    microsecond=0) + timedelta(days=dias_ate_segunda)
        elif hora >= ANALISE_FIM:
            # Após 19h → amanhã 08:00
            proxima = agora.replace(hour=ANALISE_INICIO, minute=0, second=0,
                                    microsecond=0) + timedelta(days=1)
        elif hora < ANALISE_INICIO:
            # Antes de 08h → hoje 08:00
            proxima = agora.replace(hour=ANALISE_INICIO, minute=0, second=0,
                                    microsecond=0)
        else:
            return 0  # Já em horário

        return max(int((proxima - agora).total_seconds()), 0)

    def executar_uma_vez():
        agente = AgenteWdoWinfut(
            config_path=config_path,
            fred_api_key=fred_key,
            twelvedata_key=twelvedata_key,
            alphavantage_key=alphavantage_key,
            finnhub_key=finnhub_key,
            telegram_token=telegram_token,
            telegram_chat_id=telegram_chat_id,
        )
        try:
            resultado = agente.executar()

            # ── Sinalizar contexto horário ──
            em_pregao, em_analise, desc_horario = _esta_em_horario_operacional()
            resultado["contexto_horario"] = {
                "em_pregao": em_pregao,
                "em_analise": em_analise,
                "descricao": desc_horario,
            }

            if not em_pregao:
                # Adicionar aviso visual no resultado
                resultado["aviso_horario"] = (
                    f"⚠ ANÁLISE FORA DO PREGÃO — {desc_horario}. "
                    "Scores devem ser interpretados como PROJEÇÃO, não como sinal operacional."
                )

            output = formatar_resultado(resultado)

            # Exibir aviso de horário antes do resultado
            if not em_pregao and em_analise:
                print(f"\n{CORES['VETO']}{'─'*72}")
                print(f"  ⚠  {desc_horario}")
                print(f"  Scores são PROJEÇÃO para o próximo pregão, não sinais operacionais.")
                print(f"{'─'*72}{CORES['RESET']}")
            elif not em_analise:
                print(f"\n{CORES['DIM']}{'─'*72}")
                print(f"  {desc_horario} — Análise para referência/backtest apenas.")
                print(f"{'─'*72}{CORES['RESET']}")

            print(output)
            return resultado
        finally:
            agente.fechar()

    if args.loop:
        logger.info("Modo loop ativado — intervalo: %d min", args.interval)
        logger.info("Horário operacional: %02d:00-%02d:00 BRT (pregão: %02d:00-%02d:00)",
                     ANALISE_INICIO, ANALISE_FIM, PREGAO_INICIO, PREGAO_FIM)
        while True:
            try:
                em_pregao, em_analise, desc_horario = _esta_em_horario_operacional()

                if em_analise:
                    executar_uma_vez()
                    logger.info("Proxima execucao em %d minutos...", args.interval)
                    time.sleep(args.interval * 60)
                else:
                    # Fora de horário — esperar até próxima sessão
                    espera = _tempo_ate_proxima_sessao()
                    if espera > 0:
                        proxima = datetime.now(BRT) + timedelta(seconds=espera)
                        logger.info(
                            "%s — Agente suspenso. Próxima sessão: %s BRT (%d min)",
                            desc_horario,
                            proxima.strftime("%d/%m %H:%M"),
                            espera // 60
                        )
                        # Dormir em blocos de 5 min para permitir Ctrl+C responsivo
                        while espera > 0:
                            sleep_chunk = min(espera, 300)
                            time.sleep(sleep_chunk)
                            espera -= sleep_chunk
                    else:
                        time.sleep(60)

            except KeyboardInterrupt:
                logger.info("Loop interrompido pelo usuario.")
                break
            except Exception as e:
                logger.error("Erro na execucao: %s", e, exc_info=True)
                time.sleep(60)  # Retry em 1 min
    else:
        executar_uma_vez()


if __name__ == "__main__":
    main()
