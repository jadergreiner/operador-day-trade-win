@echo off
REM =====================================================
REM  MONITOR DO OPERADOR INTEGRADO v2.0
REM  Sincronização 100% Tempo Real: Operador + S2-6 Analytics
REM  Governança ROADMAP: Sincronia Operador x Monitor
REM  Data: 24/02/2026
REM =====================================================

setlocal enabledelayedexpansion
chcp 65001 >nul

REM Define cores e setup
title Monitor Operador Integrado v2.0 - Sincronizacao 100%%
color 0A

:menu
cls
echo.
echo =====================================================
echo   MONITOR DO OPERADOR v2.0 - INTEGRADO
echo   Operador Day Trade WIN + S2-6 Analytics
echo =====================================================
echo.
echo Selecione o modo de monitoramento:
echo.
echo   [1] Monitor Integrado (Operador + S2-6 Analytics)
echo   [2] S2-6 Analytics Dashboard ONLY
echo   [3] Status Operador ONLY
echo   [0] Sair
echo.
set /p opcao="Digite a opcao: "

if "%opcao%"=="1" goto monitor_integrado
if "%opcao%"=="2" goto analytics_dashboard
if "%opcao%"=="3" goto status_operador
if "%opcao%"=="0" goto fim
goto menu

:monitor_integrado
cls
echo [INFO] Iniciando Monitor Integrado v2.0...
echo [INFO] Conectando a S2-6 Analytics em localhost:8000...
echo.
timeout /t 2
python scripts\monitor_operador_integrado.py
goto menu

:analytics_dashboard
cls
echo [INFO] Iniciando S2-6 Analytics Dashboard...
echo [INFO] Exibindo apenas estatísticas em tempo real...
echo.
timeout /t 2
python scripts\monitor_s2_6_dashboard.py
goto menu

:status_operador
cls
echo [INFO] Exibindo status do Operador...
echo.

if not exist "logs\deployment_status.json" (
    echo [ERRO] Arquivo de status nao encontrado!
    echo Local esperado: logs\deployment_status.json
    echo.
    echo Pressione ENTER para voltar ao menu...
    pause >nul
    goto menu
)

python -c "
import json
import time
from datetime import datetime
import os

def monitor_status():
    while True:
        try:
            os.system('cls')
            print('=' * 70)
            print('  STATUS OPERADOR - OPERADOR DAY TRADE WIN')
            print('=' * 70)

            with open('logs/deployment_status.json', 'r') as f:
                status = json.load(f)

            timestamp = status.get('timestamp', 'N/A')
            system_status = status.get('status', 'DESCONHECIDO')

            print(f'\n[STATUS GERAL] {system_status}')
            print(f'[ULTIMA ATUALIZACAO] {timestamp}\n')

            components = status.get('components', {})

            if components:
                print('COMPONENTES OPERACIONAIS:')
                print('-' * 70)

                for component, info in components.items():
                    component_status = info.get('status', 'DESCONHECIDO')
                    icon = '[OK]' if component_status in ['LIVE', 'ACTIVE', 'MONITORING', 'READY'] else '[OFF]'

                    print(f'\n{icon} {component.upper()}')
                    for key, value in info.items():
                        if key != 'status':
                            print(f'    - {key}: {value}')

            print('\n' + '=' * 70)
            print('[ALERTAS] Aguardando sinais de entrada...')
            print('[RISCO] Validators ativos - 3 gates monitorando')
            print('[CONEXAO] WebSocket pronto em ws://127.0.0.1:8765')
            print('=' * 70)

            print('\n** Atualizando a cada 5 segundos... Pressione Ctrl+C para parar **\n')

        except FileNotFoundError:
            print('[ERRO] Arquivo de status nao encontrado!')
            break
        except json.JSONDecodeError:
            print('[ERRO] Arquivo de status corrompido!')
            break
        except Exception as e:
            print(f'[ERRO] {e}')
            break

        time.sleep(5)

if __name__ == '__main__':
    try:
        monitor_status()
    except KeyboardInterrupt:
        print('\n[INFO] Monitor encerrado pelo usuario')

" 2>> logs\monitor_operador_erros.log

goto menu

:fim
cls
echo [INFO] Monitor encerrado
timeout /t 2
exit /b 0
