@echo off
REM =====================================================
REM  DASHBOARD OPERADOR - Menu de Monitoramento
REM  Operador Day Trade WIN - Todas as opcoes em um lugar
REM =====================================================

setlocal enabledelayedexpansion
chcp 65001 >nul

title Dashboard Operador - Operador Day Trade WIN
color 0B

:menu
cls
echo.
echo =====================================================
echo   DASHBOARD OPERADOR - OPERADOR DAY TRADE WIN
echo =====================================================
echo.
echo Selecione uma opcao:
echo.
echo   [1] Monitor de Status (RECOMENDADO)
echo   [2] Monitor de Logs Detalhados
echo   [3] Monitor de Alertas (WebSocket)
echo   [4] Ver Status JSON da Sistema
echo   [5] Validar Dataset (TODO-1 Labels)
echo   [6] Iniciar Stage 1 Deployment
echo   [7] Sair
echo.

set /p opcao="Digite sua opcao (1-7): "

if "%opcao%"=="1" goto status
if "%opcao%"=="2" goto logs
if "%opcao%"=="3" goto websocket
if "%opcao%"=="4" goto json
if "%opcao%"=="5" goto dataset
if "%opcao%"=="6" goto deploy
if "%opcao%"=="7" goto fim

echo [ERRO] Opcao invalida!
timeout /t 2
goto menu

REM ===== OPCAO 1: Monitor de Status =====
:status
cls
echo.
echo [Monitor de Status Ativado]
echo.
python -c "
import json
import time
import os

while True:
    os.system('cls')
    print('=' * 70)
    print('  [1] MONITOR DE STATUS - OPERADOR DAY TRADE WIN')
    print('=' * 70)
    
    try:
        with open('logs/deployment_status.json', 'r') as f:
            status = json.load(f)
        
        print(f\"\nStatus Geral: {status.get('status', 'DESCONHECIDO')}\")
        print(f\"Timestamp: {status.get('timestamp', 'N/A')}\n\")
        
        for component, info in status.get('components', {}).items():
            comp_status = info.get('status', 'DESCONHECIDO')
            icon = '[OK]' if comp_status in ['LIVE', 'ACTIVE', 'MONITORING', 'READY'] else '[OFF]'
            print(f'{icon} {component.upper()}: {comp_status}')
        
        print('\n(Atualizando a cada 5 segundos... Pressione Ctrl+C para parar)')
        
    except Exception as e:
        print(f'Erro: {e}')
    
    time.sleep(5)
" 2>> logs\monitor_operador_erros.log
goto menu

REM ===== OPCAO 2: Monitor de Logs =====
:logs
cls
echo.
echo [Monitor de Logs Ativado]
echo.
powershell -Command "Get-Content 'logs\deployment_stage1.log' -Tail 50 -Wait"
goto menu

REM ===== OPCAO 3: Monitor de WebSocket =====
:websocket
cls
echo.
echo [Monitor de WebSocket Ativado]
echo.
python -c "
import asyncio
import websockets
import json
from datetime import datetime

async def monitor_websocket():
    uri = 'ws://127.0.0.1:8765'
    print(f'Conectando em {uri}...\n')
    
    try:
        async with websockets.connect(uri) as websocket:
            print('[OK] Conectado ao WebSocket!')
            print('Aguardando alertas de entrada...\n')
            
            while True:
                try:
                    msg = await asyncio.wait_for(websocket.recv(), timeout=60.0)
                    alert = json.loads(msg)
                    timestamp = datetime.now().strftime('%H:%M:%S')
                    print(f'[{timestamp}] ALERTA: {json.dumps(alert, indent=2)}')
                except asyncio.TimeoutError:
                    print('[INFO] Aguardando alertas...')
                    
    except Exception as e:
        print(f'[ERRO] Conexao falhou: {e}')
        print('Certifique-se de que o servidor WebSocket esta rodando.')

asyncio.run(monitor_websocket())
" 2>> logs\monitor_operador_erros.log
goto menu

REM ===== OPCAO 4: Ver Status JSON =====
:json
cls
echo.
echo [Status JSON]
echo.
type logs\deployment_status.json | python -m json.tool
echo.
pause
goto menu

REM ===== OPCAO 5: Validar Dataset =====
:dataset
cls
echo.
echo [Validacao de Dataset - TODO-1]
echo.
python -c "
import json

try:
    with open('backtest_labeled_results.json', 'r') as f:
        data = json.load(f)
    
    total = len(data)
    positivos = sum(1 for x in data if x.get('label') == 1)
    negativos = sum(1 for x in data if x.get('label') == 0)
    
    print(f'Total de samples: {total}')
    print(f'Positivos (BUY): {positivos} ({100*positivos/total:.1f}%)')
    print(f'Negativos (SKIP): {negativos} ({100*negativos/total:.1f}%)')
    print(f'Imbalance: {max(100*positivos/total, 100*negativos/total):.1f}%')
    print(f'Status: [OK] Dataset pronto para Grid Search')
    
except FileNotFoundError:
    print('[ERRO] backtest_labeled_results.json nao encontrado!')
except Exception as e:
    print(f'[ERRO] {e}')
"
echo.
pause
goto menu

REM ===== OPCAO 6: Deploy Stage 1 =====
:deploy
cls
echo.
echo [Iniciando Stage 1 Deployment]
echo.
python scripts\DEPLOY_STAGE1_PRODUCAO.py
echo.
pause
goto menu

REM ===== Sair =====
:fim
echo.
echo Saindo do Dashboard...
timeout /t 2
exit /b
