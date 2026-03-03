@echo off
REM ============================================================================
REM ML Expert Wrapper - Wrapper para execucao de tasks do ML Expert
REM ============================================================================
REM Proposito: Definir PYTHONPATH corretamente antes de rodar scripts
REM Data: 20/02/2026
REM ============================================================================

setlocal enabledelayedexpansion
cd /d %~dp0
set PYTHONPATH=.

echo.
echo ================================================================================
echo ML Expert - Backtest Setup Task
echo ================================================================================
echo.
echo Iniciando backtest detector...
echo.

python scripts/backtest_detector.py

echo.
echo ================================================================================
echo.
if exist backtest_results.json (
    echo [OK] Backtest concluido com sucesso!
    echo Resultado salvo em: backtest_results.json
) else (
    echo [ERRO] Backtest falhou. Verifique os logs acima.
)
echo.
echo Proximos passos:
echo  1. Verifique backtest_results.json para resultados
echo  2. Siga CHECKLIST_INTEGRACAO_PHASE6.md para Task 2 (Backtest Validation)
echo  3. Use RODAR_TASK_PHASE6.bat para rodar validacoes
echo.
pause
