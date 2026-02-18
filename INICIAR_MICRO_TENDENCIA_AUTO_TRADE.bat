@echo off
REM Inicia o Agente de Micro Tendencias WINFUT
REM Permite escolher entre TRADING REAL e MODO SIMULADO

echo ==============================================================================
echo    AGENTE MICRO TENDENCIA WINFUT - CALIBRADO (POS-CARNAVAL)
echo ==============================================================================
echo.
echo    Analise Head de Financas (18/02/2026):
echo      - US CPI forte + DXY alto + EWZ em queda (-2.5%%).
echo      - GAP de Baixa esperado. Direcional: BEARISH.
echo      - Abertura B3: 13:00 (Quarta-feira de Cinzas).
echo.
echo    Calibracao Ativa:
echo      Conta MT5:       1000346516
echo      Contratos:       1
echo      Max Posicoes:    1
echo      Max Loss Diario: 500 pts
echo      Max Trades/Dia:  3 (REDUZIDO: Cautela Volatilidade)
echo      Trailing Stop:   200 pts (AJUSTADO: Mais Volatilidade)
echo      Confianca Min:   55%% (MAIOR SELETIVIDADE)
echo      Risk/Reward Min: 1.5:1
echo.
echo    Escolha o modo de operacao:
echo.
echo      [1] SIMULADO (Shadow Mode)
echo          - Analisa mercado e gera sinais normalmente
echo          - NAO envia ordens ao MT5
echo          - Loga sinais em 'simulated_trades' para analise
echo.
echo      [2] AUTO-TRADE (Ordens Reais)
echo          - EXECUTA ORDENS REAIS no MetaTrader 5
echo          - Voce pode GANHAR ou PERDER dinheiro
echo.
echo      [3] Cancelar
echo.

set /p MODO="Escolha [1/2/3]: "

if "%MODO%"=="3" (
    echo Operacao cancelada.
    pause
    exit /b 0
)
if "%MODO%"=="2" goto MODO_REAL
if "%MODO%"=="1" goto MODO_SIMULADO

echo Opcao invalida.
pause
exit /b 1

:MODO_REAL
echo.
echo    *** AVISO CRITICO ***
echo    ORDENS REAIS serao executadas no MetaTrader 5.
echo    Voce pode PERDER dinheiro.
echo.
set /p CONFIRM="Tem certeza? (S/N): "
if /i not "%CONFIRM%"=="S" (
    echo Operacao cancelada.
    pause
    exit /b 0
)
set TRADE_FLAG=--auto-trade
echo.
echo Iniciando em modo AUTO-TRADE (ordens reais)...
goto INICIAR

:MODO_SIMULADO
set TRADE_FLAG=--simulate
echo.
echo Iniciando em modo SIMULADO (shadow mode)...
goto INICIAR

:INICIAR
echo.

set PYTHON_EXE=C:\Users\Usuario\AppData\Local\Programs\Python\Python311\python.exe

if not exist "%PYTHON_EXE%" (
    echo ERRO: Python nao encontrado em "%PYTHON_EXE%"
    echo Ajuste o caminho do Python neste arquivo.
    pause
    exit /b 1
)

cd /d "%~dp0"

REM Sincroniza operações reais recentes do MT5 para o banco local
echo Sincronizando operacoes reais MT5 -> SQLite...
"%PYTHON_EXE%" scripts\sync_mt5_trades_to_db.py --days-back 3
if errorlevel 1 (
    echo [AVISO] Falha ao sincronizar operacoes reais no inicio da sessao.
)
echo.

REM Aplica lições persistentes do BDI (ontem) para pregão de hoje (idempotente)
set B3_CALENDAR_FILE=data\calendario\feriados_b3.txt
for /f "tokens=1,2 delims=," %%A in ('powershell -NoProfile -Command "$calendar='%B3_CALENDAR_FILE%'; $holidays=@(); if (Test-Path $calendar) { $holidays=Get-Content $calendar ^| ForEach-Object { $_.Trim() } ^| Where-Object { $_ -and -not $_.StartsWith('#') } }; $target=Get-Date; while (($target.DayOfWeek -eq 'Saturday' -or $target.DayOfWeek -eq 'Sunday') -or ($holidays -contains $target.ToString('yyyy-MM-dd'))) { $target=$target.AddDays(-1) }; $bdi=$target.AddDays(-1); while (($bdi.DayOfWeek -eq 'Saturday' -or $bdi.DayOfWeek -eq 'Sunday') -or ($holidays -contains $bdi.ToString('yyyy-MM-dd'))) { $bdi=$bdi.AddDays(-1) }; Write-Output ($bdi.ToString('yyyyMMdd') + ',' + $target.ToString('yyyy-MM-dd'))"') do (
    set BDI_DATE=%%A
    set TARGET_DATE=%%B
)
echo Aplicando licoes BDI: BDI=%BDI_DATE% -^> Pregao=%TARGET_DATE%...
"%PYTHON_EXE%" scripts\aplicar_licoes_bdi.py --bdi-date %BDI_DATE% --target-date %TARGET_DATE%
if errorlevel 1 (
    echo [AVISO] Falha ao aplicar licoes BDI. Seguindo inicializacao do agente.
)
echo.

REM Inicia o Diario RL em segundo plano (aprendizado intra-sessao)
echo Iniciando Diario RL (analise critica + feedback) em segundo plano...
start "DIARIO RL - Feedback Intra-Sessao" /min "%PYTHON_EXE%" scripts\start_journals_full_display.py
echo   [OK] Diario RL iniciado (janela minimizada)
echo.

"%PYTHON_EXE%" scripts\agente_micro_tendencia_winfut.py %TRADE_FLAG% --account 1000346516

REM Sincroniza novamente ao fim da sessao para capturar ultimas execucoes
echo Sincronizando operacoes reais no encerramento da sessao...
"%PYTHON_EXE%" scripts\sync_mt5_trades_to_db.py --days-back 1
if errorlevel 1 (
    echo [AVISO] Falha ao sincronizar operacoes reais no encerramento.
)

REM Executa auditoria completa (MT5 x SQLite) e persiste dados brutos para aprendizado
echo Executando auditoria MT5 x SQLite para aprendizado do modelo...
"%PYTHON_EXE%" scripts\auditar_trades_mt5_vs_sqlite.py --date %TARGET_DATE%
if errorlevel 1 (
    echo [AVISO] Auditoria apresentou falhas. Verifique logs e execute manualmente o script de auditoria.
)

REM Fluxo único: sessão Head + persistência + refresh ML
echo Executando fluxo unico de encerramento (Head + persistencia + refresh ML)...
"%PYTHON_EXE%" scripts\executar_fluxo_head_encerramento.py --base-date %TARGET_DATE% --python "%PYTHON_EXE%"
if errorlevel 1 (
    echo [AVISO] Fluxo de encerramento Head falhou parcialmente.
)

pause
