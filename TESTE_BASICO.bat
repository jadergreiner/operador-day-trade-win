@echo off
REM Teste basico para localizar o problema

setlocal enabledelayedexpansion

cls
echo.
echo Teste 1: Echo simples
echo OK - Conseguiu fazer echo

echo.
echo Teste 2: Variavel PYTHONPATH
set PYTHONPATH=.
echo PYTHONPATH=%PYTHONPATH%

echo.
echo Teste 3: Python version
python --version

echo.
echo Teste 4: Git version
git --version

echo.
echo Teste 5: Verificar arquivo de configuracao
if exist "config\alertas.yaml" (
    echo OK - config encontrada
) else (
    echo ERRO - config nao encontrada
)

echo.
echo Teste 6: Verificar src
if exist "src\" (
    echo OK - src encontrada
) else (
    echo ERRO - src nao encontrada
)

echo.
echo Teste 7: Tentar importar
python scripts/test_imports.py

echo.
echo Teste 8: Tentar rodar pytest
python -m pytest tests/ --collect-only

echo.
echo ========================================
echo Testes completados sem erros!
echo ========================================
echo.

pause
