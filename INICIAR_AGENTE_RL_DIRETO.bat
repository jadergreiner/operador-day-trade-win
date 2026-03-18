@echo off
REM ============================================================================
REM INICIAR_AGENTE_RL_DIRETO.bat - Agente RL com Posicao Independente
REM ============================================================================
REM
REM Uso: Duplo-clique neste arquivo para iniciar operador RL com posicao
REM       ISOLADA e independente do INICIAR_AGENTE_RL_5000.bat
REM
REM Diferencas vs INICIAR_AGENTE_RL_5000.bat:
REM   - Session ID unico: agente_direto_TIMESTAMP
REM   - Logs separados: agente_direto_[session].log
REM   - Estado isolado: nao compartilha positions/trades com outro agente
REM   - Pode rodar em PARALELO com o agente 5000
REM
REM Logs salvos em:
REM   - outputs/agente_direto_[TIMESTAMP].log (saida completa)
REM   - outputs/agente_direto_debug_[TIMESTAMP].log (logs debug detalhados)
REM
REM ============================================================================

setlocal enabledelayedexpansion

REM Define titulo com timestamp para diferenciar das outras instancias
for /f "tokens=2-4 delims=/ " %%a in ('date /t') do (set mydate=%%c%%a%%b)
for /f "tokens=1-2 delims=/:" %%a in ('time /t') do (set mytime=%%a%%b)

title RL DIRETO - POSICAO INDEPENDENTE - EA ID: 234600 [%mydate%_%mytime%]

echo.
echo   ============================================================================
echo   OPERADOR RL - AGENTE DIRETO (POSICAO INDEPENDENTE)
echo   ============================================================================
echo.
echo   Versao: 3.0 - Estado isolado vs INICIAR_AGENTE_RL_5000.bat
echo.
echo   Status: Inicializando agente com estado INDEPENDENTE...
echo.
echo   [*] Diretorio: %cd%
echo   [*] Script: scripts/agente_rl_direto_independente.py
echo   [*] Session: agente_direto_[TIMESTAMP UNICO]
echo   [*] Logs: outputs/agente_direto_*.log (separados)
echo.
echo   Pode rodar PARALELO com INICIAR_AGENTE_RL_5000.bat
echo   Cada agente tem sua propria posicao e logs
echo.
echo   Press Ctrl+C a qualquer momento para PARAR este agente.
echo.
echo   ============================================================================
echo.

REM Verifica se script de agente direto existe
if not exist "scripts\agente_rl_direto_independente.py" (
  echo   [ERROR] Arquivo nao encontrado: scripts\agente_rl_direto_independente.py
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

REM Executa agente direto com posicao independente
echo   [*] Executando agente DIRETO com posicao INDEPENDENTE...
echo   [*] Modo: SL/TP DINAMICOS (estado isolado)
echo.

cd /d "%~dp0"
python scripts\agente_rl_direto_independente.py --mode dinamico

REM Verifica resultado da execucao
if errorlevel 1 (
  echo.
  echo   ============================================================================
  echo   [ERROR] AGENTE DIRETO ENCERROU COM ERRO
  echo   ============================================================================
  echo.
  echo   Logs:
  echo   - outputs/agente_direto_*.log (saida completa)
  echo   - outputs/agente_direto_debug_*.log (logs detalhados)
  echo.
  echo   Opcoes:
  echo   1. Verificar logs acima
  echo   2. Verificar conexao MT5
  echo   3. Comparar com INICIAR_AGENTE_RL_5000.bat
  echo.
  pause
  exit /b 1
) else (
  echo.
  echo   ============================================================================
  echo   [OK] AGENTE DIRETO ENCERROU COM SUCESSO
  echo   ============================================================================
  echo.
  echo   Resumo:
  echo   - Session encerrada normalmente
  echo   - Estado isolado foi mantido (sem interferencia com outro agente)
  echo   - Logs salvos em outputs/agente_direto_*.log
  echo.
  pause
  exit /b 0
)
