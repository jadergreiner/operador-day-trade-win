@echo off
REM ============================================================================
REM INICIAR_AGENTE_RL_DIRETO.bat - Executa agente RL com supervisao
REM ============================================================================
REM
REM Uso: Duplo-clique neste arquivo para iniciar operador RL com anti-overtrading
REM
REM Logs salvos em:
REM   - outputs/agente_supervision.log (saida completa)
REM   - outputs/agente_debug.log (logs debug detalhados)
REM
REM ============================================================================

setlocal enabledelayedexpansion

title OPERADOR RL - ANTI-OVERTRADING (BALANCED)

echo.
echo   ============================================================================
echo   OPERADOR RL v5000 - EXECUCAO COM SUPERVISAO
echo   ============================================================================
echo.
echo   Status: Inicializando agente com supervisao completa...
echo.
echo   [*] Diretorio: %cd%
echo   [*] Script: scripts/agente_com_supervision.py
echo   [*] Logs: outputs/agente_supervision.log
echo.
echo   Press Ctrl+C a qualquer momento para PARAR o agente.
echo.
echo   ============================================================================
echo.

REM Verifica se arquivo de supervisao existe
if not exist "scripts\agente_com_supervision.py" (
  echo   [ERROR] Arquivo nao encontrado: scripts\agente_com_supervision.py
  echo.
  pause
  exit /b 1
)

REM Verifica se Python esta instalado
python --version >nul 2>&1
if errorlevel 1 (
  echo   [ERROR] Python nao encontrado no PATH
  echo   [!] Instale Python 3.10+ e adicione ao PATH
  echo.
  pause
  exit /b 1
)

REM Executa agente com supervisao (SL/TP FIXO)
echo   [*] Executando agente com SL/TP FIXO...
echo   [*] Modo: Valores fixos (150 pontos SL, 300 pontos TP)
echo.

cd /d "%~dp0"
python scripts\agente_com_supervision.py --sl-tp-mode fixo

REM Verifica resultado da execucao
if errorlevel 1 (
  echo.
  echo   ============================================================================
  echo   [ERROR] AGENTE ENCERROU COM ERRO
  echo   ============================================================================
  echo.
  echo   Logs:
  echo   - outputs/agente_supervision.log (saida completa)
  echo   - outputs/agente_debug.log (logs detalhados)
  echo.
  echo   Opcoes:
  echo   1. Verificar logs acima
  echo   2. Verificar conexao MT5
  echo   3. Contatar suporte
  echo.
  pause
  exit /b 1
) else (
  echo.
  echo   ============================================================================
  echo   [OK] AGENTE ENCERROU COM SUCESSO
  echo   ============================================================================
  echo.
  pause
  exit /b 0
)
