@echo off
REM ============================================================================
REM Operador Quantum - Phase 6 Task Runner (Executar Tasks Especificas)
REM ============================================================================
REM Arquivo: RODAR_TASK_PHASE6.bat
REM Proposito: Menu para rodar tasks individuais
REM Data: 20/02/2026
REM ============================================================================

setlocal enabledelayedexpansion
color 0A

cls
echo.
echo ================================================================================
echo
echo          OPERADOR QUANTUM - PHASE 6 TASK RUNNER
echo
echo    Executar tasks individuais de Eng Sr ou ML Expert
echo
echo ================================================================================
echo.

echo ================================================================================
echo TAREFAS DISPONIVEIS
echo ================================================================================
echo.

echo [VALIDACAO]
echo  0 - Validar Codigo (mypy + pytest)
echo  1 - Rodar Testes (pytest)
echo  2 - Type Hints Check (mypy)
echo  3 - Importacoes Check (test_imports.py)
echo.

echo [ENG SR - TAREFAS]
echo  10 - INTEGRATION-ENG-001: BDI Integration (3-4h)
echo  11 - INTEGRATION-ENG-002: WebSocket Server (2-3h)
echo  12 - INTEGRATION-ENG-003: Email Config (1-2h)
echo  13 - INTEGRATION-ENG-004: Staging Deploy (2-3h)
echo.

echo [ML EXPERT - TAREFAS]
echo  20 - INTEGRATION-ML-001: Backtest Setup (2-3h)
echo  21 - INTEGRATION-ML-002: Backtest Validation (2-3h)
echo  22 - INTEGRATION-ML-003: Performance Benchmarking (2-3h)
echo  23 - INTEGRATION-ML-004: Final Validation (1-2h)
echo.

echo [UTILITARIOS]
echo  30 - Iniciar WebSocket Server (uvicorn)
echo  31 - Rodar Backtest (scripts/backtest_detector.py)
echo  32 - Ver Git Status
echo  33 - Ver Git Log (ultimos 10 commits)
echo.

echo [SAIR]
echo  99 - Voltar ao Menu Principal
echo.

set /p TASK="Escolha uma tarefa [0-99]: "

if "%TASK%"=="0" goto VALIDATE_ALL
if "%TASK%"=="1" goto RUN_TESTS
if "%TASK%"=="2" goto RUN_MYPY
if "%TASK%"=="3" goto CHECK_IMPORTS

if "%TASK%"=="10" goto ENG_001
if "%TASK%"=="11" goto ENG_002
if "%TASK%"=="12" goto ENG_003
if "%TASK%"=="13" goto ENG_004

if "%TASK%"=="20" goto ML_001
if "%TASK%"=="21" goto ML_002
if "%TASK%"=="22" goto ML_003
if "%TASK%"=="23" goto ML_004

if "%TASK%"=="30" goto WEBSOCKET
if "%TASK%"=="31" goto BACKTEST
if "%TASK%"=="32" goto GIT_STATUS
if "%TASK%"=="33" goto GIT_LOG

if "%TASK%"=="99" goto EXIT

goto INVALID

REM ============================================================================
REM TAREFAS DE VALIDACAO
REM ============================================================================

:VALIDATE_ALL
echo.
echo [01/03] Rodando testes...
set PYTHONPATH=.
python -m pytest tests/ -q
echo.
echo [02/03] Validando type hints...
set PYTHONPATH=.
python -m mypy src/application/services/ --ignore-missing-imports --no-error-summary
echo.
echo [03/03] Verificando importacoes...
set PYTHONPATH=.
python scripts/test_imports.py
echo.
echo ✅ Validação concluída!
pause
goto END

:RUN_TESTS
echo.
echo Rodando testes com pytest...
set PYTHONPATH=.
python -m pytest tests/ -v --tb=short
echo.
echo [OK] Testes concluidos!
pause
goto END

:RUN_MYPY
echo.
echo Validando type hints com mypy...
set PYTHONPATH=.
python -m mypy src/ --ignore-missing-imports
echo.
echo [OK] Type hints check concluido!
pause
goto END

:CHECK_IMPORTS
echo.
echo Verificando importacoes...
set PYTHONPATH=.
python scripts/test_imports.py
echo.
echo [OK] Importacoes check concluido!
pause
goto END

REM ============================================================================
REM TAREFAS ENG SR
REM ============================================================================

:ENG_001
echo.
echo [ENG-001] INTEGRATION-ENG-001: BDI Integration (3-4h)
echo.
echo Checklist:
echo  1. Encontre processador_bdi.py em src/application/services/
echo  2. Importe detectors (DetectorVolatilidade, DetectorPadroesTecnico)
echo  3. Chame detectors no loop de processamento de velas
echo  4. Adicione alertas a FilaAlertas
echo  5. Teste com dados de vela
echo.
echo Documentacao:
echo  CHECKLIST_INTEGRACAO_PHASE6.md (secao Eng Sr, Task 1)
echo.
echo Comando para validar:
set PYTHONPATH=.
python scripts/test_imports.py
echo.
pause
goto END

:ENG_002
echo.
echo [ENG-002] INTEGRATION-ENG-002: WebSocket Server (2-3h)
echo.
echo Codigo pronto em: src/interfaces/websocket_server.py
echo.
echo Iniciando servidor WebSocket na porta 8765...
echo.
set PYTHONPATH=.
python -m uvicorn src.interfaces.websocket_server:app --host 0.0.0.0 --port 8765 --reload
goto END

:ENG_003
echo.
echo [ENG-003] INTEGRATION-ENG-003: Email Configuration (1-2h)
echo.
echo Checklist:
echo  1. Configure credenciais SMTP em config/alertas.yaml
echo  2. Use variaveis de ambiente (EMAIL_USER, EMAIL_PASS, SMTP_SERVER)
echo  3. Teste com test_alerta_delivery.py
echo  4. Verifique fallback (WebSocket nao deve bloquear)
echo.
pause
goto END

:ENG_004
echo.
echo [ENG-004] INTEGRATION-ENG-004: Staging Deployment (2-3h)
echo.
echo Checklist:
echo  1. Faca commit do codigo: git commit -am "feat: ..."
echo  2. Push para branch testing: git push origin testing
echo  3. Deploy em staging (instrucoes no README)
echo  4. Execute testes E2E
echo  5. Obtem aprovacao CFO/PO
echo.
pause
goto END

REM ============================================================================
REM TAREFAS ML EXPERT
REM ============================================================================

:ML_001
echo.
echo [ML-001] INTEGRATION-ML-001: Backtest Setup (2-3h)
echo.
echo Iniciando backtest detector...
echo.
set PYTHONPATH=.
python scripts/backtest_detector.py
echo.
echo Resultado salvo em: backtest_results.json
echo.
pause
goto END

:ML_002
echo.
echo [ML-002] INTEGRATION-ML-002: Backtest Validation (2-3h)
echo.
echo Checklist:
echo  1. Verifique resultados em backtest_results.json
echo  2. Valide gates:
echo     - Capture: 85%% + PASS
echo     - False Positives: 10%% ou menos PASS
echo     - Win Rate: 60%% + PASS
echo  3. Se algum gate falhar, ajuste detectors
echo  4. Re-execute: python scripts/backtest_detector.py
echo.
pause
goto END

:ML_003
echo.
echo [ML-003] INTEGRATION-ML-003: Performance Benchmarking (2-3h)
echo.
echo Checklist:
echo  1. Instale ferramentas: pip install memory_profiler line_profiler
echo  2. Profile com cProfile: python -m cProfile -s cumulative src/main.py
echo  3. Profile memoria: python -m memory_profiler src/main.py
echo  4. Alvo: P95 latency less than 30s, Memory less than 50MB
echo  5. Otimize se necessario
echo.
pause
goto END

:ML_004
echo.
echo [ML-004] INTEGRATION-ML-004: Final Validation (1-2h)
echo.
echo Checklist:
echo  1. Rode suite completa de testes: pytest tests/ -v
echo  2. Verifique type hints: mypy src/ --strict
echo  3. Confirme backtest PASS (gates OK)
echo  4. Valide performance targets
echo  5. Obtenha sign-off CFO/PO para BETA
echo  6. Pronto para launch 13/03!
echo.
pause
goto END

REM ============================================================================
REM UTILIDADES
REM ============================================================================

:WEBSOCKET
echo.
echo Iniciando WebSocket Server...
echo     Porta: 8765
echo     URL: ws://localhost:8765/alertas
echo     Health: http://localhost:8765/health
echo     Metrics: http://localhost:8765/metrics
echo.
echo Parando servidor (CTRL+C)...
set PYTHONPATH=.
python -m uvicorn src.interfaces.websocket_server:app --host 0.0.0.0 --port 8765 --reload
goto END

:BACKTEST
echo.
echo Executando Backtest Detector...
echo.
set PYTHONPATH=.
python scripts/backtest_detector.py
echo.
echo [OK] Backtest concluido!
echo    Resultado: backtest_results.json
echo.
pause
goto END

:GIT_STATUS
echo.
echo Git Status:
echo.
git status
echo.
pause
goto END

:GIT_LOG
echo.
echo Ultimos 10 commits:
echo.
git log --oneline -10
echo.
pause
goto END

REM ============================================================================
REM ERROS
REM ============================================================================

:INVALID
echo.
echo [ERRO] Opcao invalida. Tente novamente.
echo.
pause
cls
goto :0

:EXIT
echo.
echo Saindo...
exit /b 0

:END
cls
goto :0
