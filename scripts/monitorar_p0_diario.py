#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
PASSO 4: Monitorar P0-URGENT-1 Inactivity Penalty System
Script de verificação diária (5 minutos)

Checa:
  - Penalties sendo aplicadas
  - Confidence trend
  - Trades do dia
  - Erros
"""

import os
import json
from pathlib import Path
from datetime import datetime, timedelta
from collections import defaultdict

# Cores para output
class Colors:
    GREEN = '\033[92m'
    RED = '\033[91m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    RESET = '\033[0m'
    BOLD = '\033[1m'


def read_log_file(log_path):
    """Ler arquivo de log"""
    if not Path(log_path).exists():
        return []
    
    with open(log_path, 'r', encoding='utf-8', errors='ignore') as f:
        return f.readlines()


def extract_metrics(lines):
    """Extrair métricas dos logs"""
    metrics = {
        'penalties': [],
        'confidence': [],
        'trades': [],
        'errors': [],
        'timestamps': []
    }
    
    for line in lines:
        # Penalidades
        if 'INACTIVITY_PENALTY' in line or 'PENALTY' in line:
            metrics['penalties'].append(line.strip())
        
        # Confidence
        if 'confidence' in line.lower() or 'conf' in line.lower():
            metrics['confidence'].append(line.strip())
        
        # Trades
        if 'trade' in line.lower() or 'ordem' in line.lower():
            metrics['trades'].append(line.strip())
        
        # Erros
        if 'ERROR' in line or 'ERRO' in line or 'Exception' in line:
            metrics['errors'].append(line.strip())


def count_by_type(lines, pattern):
    """Contar ocorrências de um padrão"""
    return sum(1 for line in lines if pattern in line)


def monitor_p0_today():
    """Monitorar P0-URGENT-1 de hoje"""
    
    print(f"\n{Colors.BOLD}{Colors.BLUE}")
    print("=" * 70)
    print("PASSO 4: MONITORAR P0-URGENT-1 - DAILY STANDUP")
    print("=" * 70)
    print(f"{Colors.RESET}")
    
    # Data de hoje
    today = datetime.now().strftime("%d/%m/%Y")
    print(f"📅 Data: {today}")
    print(f"🕐 Hora: {datetime.now().strftime('%H:%M:%S')}\n")
    
    # Procurar logs
    logs_dir = Path("outputs")
    
    # Log contínuo (agent_execution.log)
    main_log = logs_dir / "agent_execution.log"
    
    if not main_log.exists():
        print(f"{Colors.RED}❌ Log não encontrado: {main_log}{Colors.RESET}")
        print("Agent pode não estar rodando. Verifique com:")
        print("  Get-Process python | Select-Object Id, ProcessName")
        return
    
    # Ler logs
    lines = read_log_file(main_log)
    
    if not lines:
        print(f"{Colors.RED}❌ Log vazio - agent pode não estar rodando{Colors.RESET}")
        return
    
    # Últimas N linhas do dia (últimas 1000 linhas)
    lines_today = lines[-1000:]
    
    # MÉTRICA 1: PENALTIES
    print(f"{Colors.BOLD}📊 MÉTRICA 1: INACTIVITY PENALTIES{Colors.RESET}")
    penalty_count = count_by_type(lines_today, 'INACTIVITY_PENALTY')
    penalty_count += count_by_type(lines_today, 'PENALTY')
    
    if penalty_count > 0:
        print(f"{Colors.GREEN}✅ SIM - {penalty_count} penalidades encontradas{Colors.RESET}")
        # Mostrar últimas 3 penalidades
        penalties = [l for l in lines_today if 'PENALTY' in l][-3:]
        for p in penalties:
            print(f"   └─ {p[:80]}")
    else:
        print(f"{Colors.YELLOW}⚠️  NAO ENCONTRADO - Verifique se agent está rodando{Colors.RESET}")
    
    # MÉTRICA 2: TRADES
    print(f"\n{Colors.BOLD}📊 MÉTRICA 2: TRADES{Colors.RESET}")
    trade_count = count_by_type(lines_today, 'TRADE') + count_by_type(lines_today, 'ORDEM')
    
    baseline = 0  # Esperado: 0 antes do PASSO 2
    target = 2  # Esperado: 2+ por semana com P0
    
    if trade_count > baseline:
        trend = "📈 SUBINDO"
        status = Colors.GREEN + "✅" + Colors.RESET
    else:
        trend = "→ ESTÁVEL"
        status = Colors.YELLOW + "⚠️" + Colors.RESET
    
    print(f"{status} Trades: {trade_count}")
    print(f"   Target: {target}-3 por semana")
    print(f"   Trend: {trend}")
    
    # MÉTRICA 3: CONFIDENCE
    print(f"\n{Colors.BOLD}📊 MÉTRICA 3: CONFIDENCE{Colors.RESET}")
    confidence_lines = [l for l in lines_today if 'confidence' in l.lower()]
    
    if confidence_lines:
        # Pegar últimas 3
        recent = confidence_lines[-3:]
        print(f"{Colors.GREEN}✅ Found {len(confidence_lines)} confidence entries{Colors.RESET}")
        for c in recent:
            # Tentar extrair valor numérico
            if '0.' in c:
                value = c.split('0.')[-1][:4]
                print(f"   └─ confidence: 0.{value}")
    else:
        print(f"{Colors.YELLOW}⚠️  Nenhuma entrada de confidence encontrada{Colors.RESET}")
    
    # MÉTRICA 4: ERROS
    print(f"\n{Colors.BOLD}📊 MÉTRICA 4: ERROS{Colors.RESET}")
    error_count = count_by_type(lines_today, 'ERROR') + count_by_type(lines_today, 'ERRO') + count_by_type(lines_today, 'Exception')
    
    if error_count == 0:
        print(f"{Colors.GREEN}✅ ZERO erros (OK){Colors.RESET}")
    else:
        print(f"{Colors.RED}❌ {error_count} ERROS ENCONTRADOS{Colors.RESET}")
        errors = [l for l in lines_today if 'ERROR' in l or 'ERRO' in l][-3:]
        for e in errors:
            print(f"   └─ {e[:80]}")
    
    # RESUMO
    print(f"\n{Colors.BOLD}{Colors.BLUE}")
    print("=" * 70)
    print("RESUMO DO DIA")
    print("=" * 70)
    print(f"{Colors.RESET}")
    
    status_ok = penalty_count > 0 and error_count == 0
    
    if status_ok:
        print(f"{Colors.GREEN}✅ STATUS: OK{Colors.RESET}")
    elif error_count > 0:
        print(f"{Colors.RED}❌ STATUS: ERRORS DETECTED{Colors.RESET}")
    else:
        print(f"{Colors.YELLOW}⚠️  STATUS: EM MONITORAMENTO{Colors.RESET}")
    
    print(f"\nPróxima ação:")
    print(f"  1. Verificar novamente amanhã na mesma hora")
    print(f"  2. Após 5 dias: Gate decision (GO/NO-GO)")
    print(f"  3. Se GO → Proceed to P1-LEARNING")
    
    # Salvar em arquivo de acompanhamento
    save_daily_record(today, penalty_count, trade_count, error_count)


def save_daily_record(date, penalties, trades, errors):
    """Salvar registro do dia em arquivo JSON"""
    
    record_file = Path("outputs") / "PASSO_4_ACOMPANHAMENTO_DIARIO.json"
    
    # Carregar histórico se existe
    if record_file.exists():
        with open(record_file, 'r') as f:
            history = json.load(f)
    else:
        history = {}
    
    # Adicionar dia de hoje
    history[date] = {
        'timestamp': datetime.now().isoformat(),
        'penalties': penalties,
        'trades': trades,
        'errors': errors,
        'status': 'OK' if penalties > 0 and errors == 0 else 'WARNING'
    }
    
    # Salvar
    with open(record_file, 'w') as f:
        json.dump(history, f, indent=2)
    
    print(f"\n📁 Registro salvo: {record_file}")


def show_summary():
    """Mostrar resumo histórico"""
    
    record_file = Path("outputs") / "PASSO_4_ACOMPANHAMENTO_DIARIO.json"
    
    if not record_file.exists():
        return
    
    with open(record_file, 'r') as f:
        history = json.load(f)
    
    print(f"\n{Colors.BOLD}📋 HISTÓRICO (Últimos 7 dias):{Colors.RESET}")
    print("=" * 70)
    print(f"{'Data':<12} | {'Penalties':<10} | {'Trades':<10} | {'Errors':<8} | {'Status':<10}")
    print("=" * 70)
    
    for date in sorted(history.keys())[-7:]:
        data = history[date]
        status_color = Colors.GREEN if data['status'] == 'OK' else Colors.YELLOW
        print(f"{date:<12} | {data['penalties']:<10} | {data['trades']:<10} | {data['errors']:<8} | {status_color}{data['status']:<10}{Colors.RESET}")


if __name__ == '__main__':
    os.chdir(Path(__file__).parent.parent)  # cd para raiz do projeto
    monitor_p0_today()
    show_summary()
    
    print(f"\n{Colors.BLUE}Para rodar novamente amanhã:{Colors.RESET}")
    print("  python scripts/monitorar_p0_diario.py")
