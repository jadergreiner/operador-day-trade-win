#!/usr/bin/env python3
"""
Launcher para Agente Micro Tendência WINFUT
Versão Python (mais confiável que batch)
"""

import subprocess
import sys
import os
from pathlib import Path
from datetime import datetime, timedelta

# Cores para terminal
class Colors:
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    RED = '\033[91m'
    BLUE = '\033[94m'
    RESET = '\033[0m'
    BOLD = '\033[1m'

def print_header():
    """Exibe header do agente"""
    print(f"{Colors.BLUE}{Colors.BOLD}")
    print("="*80)
    print("   AGENTE MICRO TENDENCIA WINFUT - CALIBRADO (POS-CARNAVAL)")
    print("="*80)
    print(f"{Colors.RESET}")
    print()
    print("   Analise Head de Financas (18/02/2026):")
    print("     - US CPI forte + DXY alto + EWZ em queda (-2.5%).")
    print("     - GAP de Baixa esperado. Direcional: BEARISH.")
    print("     - Abertura B3: 13:00 (Quarta-feira de Cinzas).")
    print()
    print("   Calibracao Ativa:")
    print("     Conta MT5:       1000346516")
    print("     Contratos:       Dinamico (Calibrador ATR S2-2)")
    print("     Max Posicoes:    1")
    print("     Max Loss Diario: 500 pts")
    print("     Max Trades/Dia:  3 (REDUZIDO: Cautela Volatilidade)")
    print("     Trailing Stop:   Dinamico (2.0x ATR 15m)")
    print("     Conviccao SMC:   ATIVA (M1/M5 Confluence S2-3)")
    print("     Confianca Min:   45% (MAIOR SELETIVIDADE)")
    print("     Risk/Reward Min: 1.5:1")
    print()
    print("   Seguranca Ativa (Phase 7 / Sprint 2):")
    print("     - SMC Confluence: M1/M5 multi-timeframe validation (S2-3)")
    print("     - Risk Validator: 3 gates (Capital, Correlacao, Volatilidade)")
    print("     - OrdersExecutor: Async queue + P&L monitor")
    print("     - Performance: P95 Tuning ativo (Imports Estaticos + RL Engine Pool)")
    print("     - S2-6 ANALYTICS: INTEGRADO com Monitor Operador (sync real-time)")
    print()

def get_choice():
    """Obtém escolha do usuário"""
    print("   Escolha o modo de operacao:")
    print()
    print("     [1] SIMULADO (Shadow Mode)")
    print("         - Analisa mercado e gera sinais normalmente")
    print("         - NAO envia ordens ao MT5")
    print("         - Loga sinais em 'simulated_trades' para analise")
    print()
    print("     [2] AUTO-TRADE (Ordens Reais)")
    print("         - EXECUTA ORDENS REAIS no MetaTrader 5")
    print("         - Voce pode GANHAR ou PERDER dinheiro")
    print()
    print("     [3] Cancelar")
    print()

    while True:
        choice = input("Escolha [1/2/3]: ").strip()
        if choice in ["1", "2", "3"]:
            return choice
        print("Opcao invalida. Tente novamente.")

def get_confirmation():
    """Confirma operação em modo real"""
    print()
    print("   *** AVISO CRITICO ***")
    print("   ORDENS REAIS serao executadas no MetaTrader 5.")
    print("   Voce pode PERDER dinheiro.")
    print()
    while True:
        choice = input("Tem certeza? (S/N): ").strip().upper()
        if choice in ["S", "N"]:
            return choice == "S"
        print("Responda S ou N.")

def get_trading_dates():
    """Calcula datas de trading"""
    try:
        # Tenta executar PowerShell script
        result = subprocess.run(
            ["powershell", "-NoProfile", "-File", "scripts/get_trading_dates.ps1"],
            capture_output=True,
            text=True,
            check=True
        )
        parts = result.stdout.strip().split(",")
        if len(parts) == 2:
            return parts[0], parts[1]
    except:
        pass

    # Fallback: calcula em Python
    calendar_file = Path("data/calendario/feriados_b3.txt")
    holidays = set()

    if calendar_file.exists():
        with open(calendar_file) as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#"):
                    holidays.add(line)

    def is_business_day(d):
        if d.weekday() >= 5:  # Sábado/Domingo
            return False
        if d.strftime("%Y-%m-%d") in holidays:
            return False
        return True

    target = datetime.now().date()
    while not is_business_day(target):
        target -= timedelta(days=1)

    bdi = target - timedelta(days=1)
    while not is_business_day(bdi):
        bdi -= timedelta(days=1)

    return bdi.strftime("%Y%m%d"), target.strftime("%Y-%m-%d")

def run_health_check():
    """Executa health check"""
    print("[PRE-FLIGHT] Verificando saude do sistema (S1-2)...")
    result = subprocess.run(
        [sys.executable, "scripts/system_health_monitor.py"],
        capture_output=False
    )
    return result.returncode == 0

def sync_mt5_trades(days_back):
    """Sincroniza trades do MT5"""
    print(f"Sincronizando operacoes reais MT5 -> SQLite...")
    subprocess.run(
        [sys.executable, "scripts/sync_mt5_trades_to_db.py", f"--days-back {days_back}"],
        capture_output=True
    )

def apply_bdi_lessons(bdi_date, target_date):
    """Aplica lições BDI"""
    print(f"Aplicando licoes BDI: BDI={bdi_date} -> Pregao={target_date}...")
    subprocess.run(
        [sys.executable, "scripts/aplicar_licoes_bdi.py",
         f"--bdi-date {bdi_date}", f"--target-date {target_date}"],
        capture_output=True
    )

def start_journals():
    """Inicia journaling em segundo plano"""
    print("Iniciando Diario RL (analise critica + feedback) em segundo plano...")
    subprocess.Popen(
        [sys.executable, "scripts/start_journals_full_display.py"],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL
    )
    print("   [OK] Diario RL iniciado (janela minimizada)")
    print()

def run_agent(trade_flag, target_date):
    """Executa o agente principal COM S2-6 ANALYTICS INTEGRADO"""
    print(f"Iniciando Agente Micro Tendencia WINFUT + S2-6 ANALYTICS...")
    print(f"   🔗 S2-6 Analytics: INTEGRADO")
    print(f"   📊 Monitor Operador: SINCRONIZADO (real-time)")
    print()

    # ─ Usa launcher com S2-6 integrado (em vez do agente original) ─
    cmd = [
        sys.executable,
        "scripts/launch_agent_with_s2_6.py",
        trade_flag,
        "--account 1000346516"
    ]

    subprocess.run(cmd)

def main():
    """Main entry point"""
    os.chdir(Path(__file__).parent)

    print_header()

    choice = get_choice()

    if choice == "3":
        print("Operacao cancelada.")
        return 0

    if choice == "2":
        if not get_confirmation():
            print("Operacao cancelada.")
            return 0
        trade_flag = "--auto-trade"
        print()
        print("Iniciando em modo AUTO-TRADE (ordens reais)...")
    else:
        trade_flag = "--simulate"
        print()
        print("Iniciando em modo SIMULADO (shadow mode)...")

    # Pre-flight checks
    if not run_health_check():
        print()
        print(f"{Colors.RED}[ERRO CRITICO] Falha no Pre-Flight Check (S1-2).{Colors.RESET}")
        print("O sistema NAO esta pronto para operacao real ou simulada.")
        return 1

    print()

    # Sync with MT5
    sync_mt5_trades(3)
    print()

    # Get trading dates
    bdi_date, target_date = get_trading_dates()

    # Apply BDI lessons
    apply_bdi_lessons(bdi_date, target_date)
    print()

    # Start journals
    start_journals()

    # Run agent
    run_agent(trade_flag, target_date)

    # Final sync
    print()
    print("Sincronizando operacoes reais no encerramento da sessao...")
    sync_mt5_trades(1)

    return 0

if __name__ == "__main__":
    sys.exit(main())
