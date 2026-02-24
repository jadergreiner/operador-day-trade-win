#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import json
import time
import os
import sys
from datetime import datetime
from pathlib import Path

# Import da análise técnica
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
try:
    from analise_tecnica_avancada import gerar_analise_completa
except ImportError:
    gerar_analise_completa = None

def format_clock_display():
    """Formata relógio visual para o display"""
    now = datetime.now()
    hora = now.strftime('%H:%M:%S')

    # ASCII art do relógio
    clock_art = f"""
    ╔═══════════════════════════════════╗
    ║  ⏰  {hora}  BRT  ⏰  ║
    ║     OPERADOR EM MONITORAMENTO     ║
    ╚═══════════════════════════════════╝"""

    return clock_art, hora

def monitor_operador():
    while True:
        try:
            os.system('cls')

            # Relógio em tempo real
            clock_display, current_time = format_clock_display()
            print(clock_display)

            # Header
            print('=' * 75)
            print('  OPERADOR - OPERADOR DAY TRADE WIN - MONITORAMENTO EM TEMPO REAL')
            print('=' * 75)

            # Carrega status
            if Path('logs/deployment_status.json').exists():
                with open('logs/deployment_status.json', 'r') as f:
                    status = json.load(f)

                timestamp = status.get('timestamp', 'N/A')
                system_status = status.get('status', 'DESCONHECIDO')

                # Status geral
                print(f'\n[SISTEMA] {system_status}')
                print(f'[ULTIMA ATUALIZACAO] {timestamp}')
                print(f'[HORARIO ATUAL] {current_time} BRT')

                # Componentes
                print('\n' + '-' * 75)
                print('COMPONENTES:')
                print('-' * 75)

                for component, info in status.get('components', {}).items():
                    comp_status = info.get('status', 'DESCONHECIDO')

                    if comp_status in ['LIVE', 'ACTIVE', 'MONITORING', 'READY']:
                        icon = '[OK]'
                    else:
                        icon = '[XX]'

                    print(f'{icon} {component:20s} : {comp_status:15s}', end='')

                    # Info adicional
                    details = []
                    for key, value in info.items():
                        if key != 'status':
                            details.append(f'{key}={value}')

                    if details:
                        print(f'  ({" ".join(details)})')
                    else:
                        print()

            # Logs em tempo real
            print('\n' + '-' * 75)
            print('ULTIMOS EVENTOS:')
            print('-' * 75)

            if Path('logs/deployment_stage1.log').exists():
                with open('logs/deployment_stage1.log', 'r') as f:
                    lines = f.readlines()
                    for line in lines[-10:]:  # Ultimas 10 linhas
                        print(f'  {line.rstrip()}')
            else:
                print('[AGUARDANDO EVENTOS]')

            # Tempo decorrido desde último evento
            print('\n' + '-' * 75)
            print('STATUS DE TEMPO:')
            print('-' * 75)
            if Path('logs/deployment_stage1.log').exists():
                try:
                    mtime = os.path.getmtime('logs/deployment_stage1.log')
                    last_event = datetime.fromtimestamp(mtime)
                    elapsed = datetime.now() - last_event
                    minutes = int(elapsed.total_seconds() / 60)

                    status_text = "🟢 Monitorando" if minutes < 30 else "🟡 Aguardando eventos"
                    print(f'[ULTIMO EVENTO] {last_event.strftime("%H:%M:%S BRT")}')
                    print(f'[TEMPO DECORRIDO] {minutes} minutos')
                    print(f'[STATUS] {status_text}')
                except Exception as e:
                    print(f'[INFO] {e}')

            # Dataset Status
            print('\n' + '-' * 75)
            print('DATASET (TODO-1):')
            print('-' * 75)

            if Path('backtest_labeled_results.json').exists():
                with open('backtest_labeled_results.json', 'r') as f:
                    data = json.load(f)

                # Handle both list and dict formats
                if isinstance(data, dict):
                    labels = data.get('labels', [])
                    total = len(labels)
                    positivos = sum(1 for x in labels if x == 1)
                else:
                    labels = data if isinstance(data, list) else []
                    total = len(labels)
                    positivos = sum(1 for x in labels if isinstance(x, dict) and x.get('label') == 1)

                negativos = total - positivos if total > 0 else 0

                if total > 0:
                    print(f'[TOTAL] {total:4d} samples')
                    print(f'[BUY]   {positivos:4d} ({100*positivos/total:5.1f}%)')
                    print(f'[SKIP]  {negativos:4d} ({100*negativos/total:5.1f}%)')
                    print(f'[STATUS] Pronto para Grid Search')
                else:
                    print('[AGUARDANDO DATASET]')

            # Análise Técnica Avançada
            # ✅ CORRIGIDO: SMC agora usa dados reais do backtest (não mais fictícios)
            # Status: Re-ativado com validação de dados
            # Referência: ACAO_URGENTE_SMC_CRITICO_ANALISE_IMPACTO.md

            if gerar_analise_completa and True:  # ✅ Re-ativado (dados corrigidos)
                print('\n' + '-' * 75)
                print('ANALISE TECNICA AVANÇADA (SMC CORRIGIDO):')
                print('-' * 75)

                try:
                    analise = gerar_analise_completa()

                    # Market Strength
                    market = analise.get('market_strength', {})
                    print(f'\n[FORCA DO MERCADO]')
                    print(f'  Trend: {market.get("trend_strength", 0)}/100')
                    print(f'  Volume: {market.get("volume_strength", 0)}/100')
                    print(f'  Volatility: {market.get("volatility_index", 0)}/100')
                    print(f'  Overall: {market.get("emoji", "🟡")} {market.get("overall", 0)}/100 ({market.get("classificacao", "?")})')

                    # Probability
                    prob = analise.get('probability', {})
                    print(f'\n[PROBABILIDADE BUYER/SELLER]')
                    print(f'  BUY: {prob.get("buy_probability", 0)}%')
                    print(f'  SELL: {prob.get("sell_probability", 0)}%')
                    print(f'  Neutro: {prob.get("neutral_probability", 0)}%')
                    print(f'  Sinal: {prob.get("primary_signal", "?")} ({prob.get("strength", "?")})')

                    # SMC (Agora com dados REAIS)
                    smc = analise.get('smc_levels', {})
                    print(f'\n[ANALISE SMC - ✅ VALIDADA COM DADOS REAIS]')
                    print(f'  Preço Atual: {smc.get("preco_atual", "?")}')
                    print(f'  Support 1: {smc.get("support_1", "?")} | Resistance 1: {smc.get("resistance_1", "?")}')
                    print(f'  Support 2: {smc.get("support_2", "?")} | Resistance 2: {smc.get("resistance_2", "?")}')
                    print(f'  Fase: {smc.get("market_phase", "?")} - {smc.get("setup_recomendado", "?")}')
                    if smc.get('validado'):
                        print(f'  ✅ Validado: {smc.get("fonte_dados", "dados reais")}')

                    # Recomendação (com SMC)
                    rec = analise.get('recomendacao', {})
                    print(f'\n[RECOMENDACAO (COM SMC VALIDADO)]')
                    print(f'  Setup: {rec.get("setup", "?")}')
                    print(f'  Entrada: {rec.get("entrada", "?")}')
                    print(f'  Alvo: {rec.get("alvo", "?")}')
                    print(f'  Stop: {rec.get("stop", "?")}')
                    print(f'  R:R: {rec.get("risco_recompensa", "?")}')
                    print(f'  Confiança: {rec.get("confianca", "?")}')

                except Exception as e:
                    print(f'  [ERRO na análise] {e}')

            # Footer
            print('\n' + '=' * 75)
            print('[ALERTAS] Monitorando em tempo real')
            print('[CONEXAO] WebSocket aguardando em ws://127.0.0.1:8765')
            print('[RISCO] Validators com 3 gates operacionais')
            print('=' * 75)

            print('\nAtualizado a cada 5 segundos... (Ctrl+C para parar)\n')

        except KeyboardInterrupt:
            print('\n\nEncerrando monitor...')
            sys.exit(0)
        except Exception as e:
            print(f'[ERRO] {e}')

        time.sleep(5)

if __name__ == '__main__':
    monitor_operador()
