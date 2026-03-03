@echo off
REM ============================================================================
REM Git Monitor Wrapper - Wrapper para monitoramento de Git
REM ============================================================================
REM Proposito: Mostrar status e log do repositorio
REM Data: 20/02/2026
REM ============================================================================

cd /d %~dp0

echo.
echo ================================================================================
echo Git Monitor - Repository Status
echo ================================================================================
echo.
echo [INFO] Ultimos 5 commits:
echo.

git log --oneline -5

echo.
echo.
echo [INFO] Status do repositorio:
echo.

git status

echo.
echo ================================================================================
echo.
echo Monitore este terminal para rastrear mudancas no repositorio.
echo Pre-condicao para commit: git add -A && git commit -m "..."
echo.
pause
