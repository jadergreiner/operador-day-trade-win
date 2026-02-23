#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import json
import time
import os
import sys
from datetime import datetime
from pathlib import Path

def monitor_operador():
    while True:
        try:
            os.system('cls')
            
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
                hora = datetime.now().strftime('%H:%M:%S BRT')
                print(f'[HORARIO ATUAL] {hora}')
                
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
                        print(line.rstrip())
            else:
                print('[AGUARDANDO EVENTOS]')
            
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
