@echo off
REM ============================================================================
REM Eng Sr Wrapper - Wrapper para execucao de tasks do Eng Sr
REM ============================================================================
REM Proposito: Definir PYTHONPATH corretamente antes de rodar scripts
REM Data: 20/02/2026
REM ============================================================================

setlocal enabledelayedexpansion
cd /d %~dp0
set PYTHONPATH=.

echo.
echo ================================================================================
echo Eng Sr - BDI Integration Task
echo ================================================================================
echo.
echo Carregando importacoes e configuracoes...
echo.

python scripts/test_imports.py

echo.
echo ================================================================================
echo.
echo Status: Verificacao de importacoes concluida
echo Proximos passos:
echo  1. Abra CHECKLIST_INTEGRACAO_PHASE6.md
echo  2. Siga as instrucoes da Task 1 (BDI Integration)
echo  3. Use RODAR_TASK_PHASE6.bat para rodar validacoes
echo.
pause
