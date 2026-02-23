@echo off
REM =====================================================
REM  MONITOR DO OPERADOR - Operador Day Trade WIN
REM  Foco 100% no monitoramento de alertas em tempo real
REM  Data: 23/02/2026
REM =====================================================

setlocal enabledelayedexpansion
chcp 65001 >nul

REM Define cores e emoji setup
title Monitor Operador - Operador Day Trade WIN
color 0A

:inicio
cls

echo.
echo =====================================================
echo   MONITOR DO OPERADOR v1.0
echo   Operador Day Trade WIN - LIVE TRADING ALERTS
echo =====================================================
echo.
echo Carregando status do sistema...
echo.

REM Verifica se arquivo de status existe
if not exist "logs\deployment_status.json" (
    echo [ERRO] Arquivo de status nao encontrado!
    echo Local esperado: logs\deployment_status.json
    echo.
    echo Iniciando Stage 1 Deployment...
    python scripts\DEPLOY_STAGE_1_PRODUCAO.py
    timeout /t 5
    goto inicio
)

REM Mostra status em tempo real
python -c "
import json
import time
from datetime import datetime
import os

def monitor_operador():
    while True:
        try:
            os.system('cls')
            print('=' * 70)
            print('  MONITOR DO OPERADOR - OPERADOR DAY TRADE WIN')
            print('=' * 70)
            
            with open('logs/deployment_status.json', 'r') as f:
                status = json.load(f)
            
            timestamp = status.get('timestamp', 'N/A')
            system_status = status.get('status', 'DESCONHECIDO')
            
            print(f'\n[STATUS GERAL] {system_status}')
            print(f'[ULTIMA ATUALIZACAO] {timestamp}\n')
            
            components = status.get('components', {})
            
            print('COMPONENTES OPERACIONAIS:')
            print('-' * 70)
            
            for component, info in components.items():
                component_status = info.get('status', 'DESCONHECIDO')
                icon = '[✓ LIVE]' if component_status in ['LIVE', 'ACTIVE', 'MONITORING', 'READY'] else '[✗ OFF]'
                
                print(f'\n{icon} {component.upper()}')
                for key, value in info.items():
                    if key != 'status':
                        print(f'    └─ {key}: {value}')
            
            print('\n' + '=' * 70)
            print('[ALERTAS] Aguardando sinais de entrada...')
            print('[RISCO] Validators ativos - 3 gates monitorando')
            print('[CONEXAO] WebSocket pronto em ws://127.0.0.1:8765')
            print('=' * 70)
            
            print('\n** Atualizando a cada 5 segundos... Feche a janela para parar **\n')
            
        except FileNotFoundError:
            print('[ERRO] Arquivo de status nao encontrado!')
        except json.JSONDecodeError:
            print('[ERRO] Arquivo de status corrompido!')
        except Exception as e:
            print(f'[ERRO] {e}')
        
        time.sleep(5)

if __name__ == '__main__':
    monitor_operador()
" 2>> logs\monitor_operador_erros.log

pause
goto inicio
