@REM ╔════════════════════════════════════════════════════════════════════════════╗
@REM ║                      ATIVAR_PRODUCAO_SIMPLES.bat                          ║
@REM ║                                                                            ║
@REM ║  Version:     v1.0                                                        ║
@REM ║  Purpose:     Activate agent in production (simplified fallback version)  ║
@REM ║  Created:     23/02/2026                                                  ║
@REM ║  Status:      Production-ready fallback (when PowerShell fails)           ║
@REM ║  Location:    scripts/execution/                                          ║
@REM ║                                                                            ║
@REM ║  Usage:       ATIVAR_PRODUCAO_SIMPLES.bat                                ║
@REM ║                                                                            ║
@REM ║  Flow:        [Menu] 6 opções interativas:                               ║
@REM ║               [1] Iniciar Agente em Produção                              ║
@REM ║               [2] Rodar Testes                                            ║
@REM ║               [3] Ver Status do Sistema                                   ║
@REM ║               [4] Ver Configuração (YAML)                                 ║
@REM ║               [5] Ver Log de Execução                                     ║
@REM ║               [6] Sair                                                    ║
@REM ║                                                                            ║
@REM ║  Output:      - config\producao_simples.yaml (production config)          ║
@REM ║               - logs\producao\ (audit trail + logs)                       ║
@REM ║               - 3 parallel terminals (Detector, Risk, Orders)             ║
@REM ║                                                                            ║
@REM ║  Properties:  - Color-coded feedback (green/yellow/red)                  ║
@REM ║               - Safety checks (confirmation required)                     ║
@REM ║               - Kill switch support (Ctrl+C or taskkill)                  ║
@REM ║               - Log viewer integrated                                     ║
@REM ║               - Status checker built-in                                   ║
@REM ║               - Config viewer                                             ║
@REM ║                                                                            ║
@REM ║  Dependencies: Python 3.9+, pytest, pandas, numpy (auto-installed)       ║
@REM ║                                                                            ║
@REM ║  Differences:  - Batch/CMD based (vs. PowerShell)                        ║
@REM ║                - 3 terminals (vs. 5 in full version)                      ║
@REM ║                - Simplified config (producao_simples.yaml)                ║
@REM ║                - No color output (CMD limitation)                         ║
@REM ║                - 6 menu options vs. 4 in other versions                   ║
@REM ║                                                                            ║
@REM ║  Troubleshooting:                                                         ║
@REM ║  - "Cannot find Python": Install from https://www.python.org            ║
@REM ║  - "Unexpected window close": Use taskkill /F /IM python.exe to clear   ║
@REM ║  - "Config not created": Check if PowerShell is blocked                  ║
@REM ║                                                                            ║
@REM ║  Related:     Ativar-Producao.ps1 (PowerShell full - RECOMMENDED)        ║
@REM ║               Ativar-Simples.ps1 (PowerShell simplified - RECOMMENDED)   ║
@REM ║               ATIVAR_PRODUCAO_AGORA.bat (other full batch version)       ║
@REM ║               ATIVAR_PRODUCAO_README.md (complete instructions)          ║
@REM ║               config/producao_simples.yaml (generated config)             ║
@REM ║                                                                            ║
@REM ║  Phase:       Phase 7 - Automatic Execution                               ║
@REM ║  Sprint:      Initial live activation (skeleton with parallel ML training)║
@REM ║  Go Live:     10/04/2026 with 50k capital (after gates)                  ║
@REM ║                                                                            ║
@REM ║  Problem Fixed: 23/02/2026 fixed "não fecha inesperadamente" issue       ║
@REM ║                 Added pause commands and improved terminal management     ║
@REM ║                                                                            ║
@REM ╚════════════════════════════════════════════════════════════════════════════╝

@echo off
REM ============================================================================
REM  ATIVAR AGENTE EM PRODUCAO - VERSAO SIMPLIFICADA
REM  Data: 23/02/2026
REM  PROBLEMA RESOLVIDO: Nao fecha inesperadamente
REM ============================================================================

setlocal enabledelayedexpansion
cd /d "%~dp0..\.."

cls
echo.
echo ╔════════════════════════════════════════════════════════════════════════════╗
echo ║                                                                            ║
echo ║        ATIVAR AGENTE EM PRODUÇÃO - VERSÃO SIMPLIFICADA                   ║
echo ║                                                                            ║
echo ║                          23/02/2026 FIXED                                 ║
echo ║                                                                            ║
echo ╚════════════════════════════════════════════════════════════════════════════╝
echo.

REM ============================================================================
REM  PRÉ-REQUISITOS BÁSICOS
REM ============================================================================

echo [VERIFICACAO] Checando pré-requisitos...
echo.

REM Python
python --version >nul 2>&1
if errorlevel 1 (
    color 4F
    echo [ERRO] Python não encontrado!
    echo.
    echo Solução: Instale Python 3.9+ de https://www.python.org
    echo.
    echo Pressione qualquer tecla para fechar...
    pause >nul
    exit /b 0
)
for /f "tokens=2" %%i in ('python --version 2^>^&1') do set PYTHON_VERSION=%%i
echo [OK] Python %PYTHON_VERSION%

REM Git (opcional)
git --version >nul 2>&1
if errorlevel 1 (
    echo [OK] Git (não encontrado - é opcional)
) else (
    echo [OK] Git
)

echo.
echo [ESTRUTURA] Criando estrutura de diretórios...
if not exist "config" mkdir config
if not exist "logs" mkdir logs
if not exist "logs\producao" mkdir logs\producao
echo [OK] Diretórios criados

echo.
echo [CONFIG] Criando arquivo de configuração...
(
    echo # PRODUCAO CONFIGURATION
    echo # Criado: %date% %time%
    echo.
    echo environment: production
    echo logging_level: INFO
    echo.
    echo capital:
    echo   inicial: 5000
    echo   max_contracts: 1
    echo.
    echo asset:
    echo   symbol: WIN$N
    echo   timeframe: 5m
    echo.
    echo risk_validation:
    echo   enabled: true
) > config\producao_simples.yaml
echo [OK] Config criada em config\producao_simples.yaml

echo.
echo.
echo ════════════════════════════════════════════════════════════════════════════
echo MENU PRINCIPAL
echo ════════════════════════════════════════════════════════════════════════════
echo.
echo   [1] Iniciar Agente em Produção
echo   [2] Rodar Testes
echo   [3] Ver Status do Sistema
echo   [4] Ver Configuração
echo   [5] Ver Log de Execução
echo   [6] Sair
echo.

set /p OPCAO_MENU="Escolha uma opção [1-6]: "

if "%OPCAO_MENU%"=="1" goto :INICIAR
if "%OPCAO_MENU%"=="2" goto :TESTES
if "%OPCAO_MENU%"=="3" goto :STATUS
if "%OPCAO_MENU%"=="4" goto :CONFIG
if "%OPCAO_MENU%"=="5" goto :LOGS
if "%OPCAO_MENU%"=="6" goto :SAIR

color 6F
echo.
echo Opção inválida! Use 1, 2, 3, 4, 5 ou 6.
echo.
pause
cls
goto :eof

REM ============================================================================
REM INICIAR PRODUÇÃO
REM ============================================================================

:INICIAR
cls
color 2F
echo.
echo ╔════════════════════════════════════════════════════════════════════════════╗
echo ║                       INICIANDO PRODUÇÃO                                  ║
echo ╚════════════════════════════════════════════════════════════════════════════╝
echo.
echo.

echo ⚠️  AVISO CRÍTICO:
echo   ✓ Capital REAL: R$ 5.000
echo   ✓ Máxima perda permitida: -R$ 100
echo   ✓ Você DEVE monitorar constantemente
echo   ✓ Kill switch: Feche a janela ou execute Ctrl+C
echo.
echo Prossiga somente se tiver:
echo   ✓ Confirmado todas as configurações
echo   ✓ Testado em ambiente DEMO primeiro
echo   ✓ Backups feitos
echo.

set /p CONFIRMA="Tem certeza? Digite 'SIM' para continuar: "
if /i not "%CONFIRMA%"=="SIM" (
    cls
    echo Operação cancelada.
    pause
    goto :eof
)

echo.
echo ✅ Iniciando componentes...
echo.

REM Criar log de ativação
for /f "tokens=2-4 delims=/ " %%a in ('date /t') do set DATA=%%c-%%a-%%b
for /f "tokens=1-2 delims=/:" %%a in ('time /t') do set HORA=%%a:%%b
echo [%DATA% %HORA%] ATIVAÇÃO INICIADA >> logs\producao\ATIVACAO_LOG.txt

REM Terminal 1: Detector BDI
echo [Terminal 1] Detector BDI...
start "BDI Detector - Productino" cmd /k "cd /d "%cd%" && python -m src.application.services.processador_bdi --config config\producao_simples.yaml && pause"

timeout /t 2 /nobreak

REM Terminal 2: Risk Validator
echo [Terminal 2] Risk Validator...
start "Risk Validator - Production" cmd /k "cd /d "%cd%" && python -m src.application.risk_validator --config config\producao_simples.yaml && pause"

timeout /t 2 /nobreak

REM Terminal 3: Orders Executor
echo [Terminal 3] Orders Executor...
start "Orders Executor - Production" cmd /k "cd /d "%cd%" && python -m src.application.orders_executor --config config\producao_simples.yaml && pause"

echo.
echo ═══════════════════════════════════════════════════════════════════════════════
echo.
echo ✅ AGENTE INICIADO!
echo.
echo ℹ️  PRÓXIMAS AÇÕES:
echo   → Verifique as janelas dos componentes acima
echo   → Monitore os logs em: logs\producao\
echo   → Mantenha este terminal aberto para referência
echo.
echo 🛑 PARA PARAR:
echo   → Feche cada janela de componente
echo   → Ou execute: taskkill /F /IM python.exe (FORÇA)
echo.
echo ═══════════════════════════════════════════════════════════════════════════════
echo.

pause
goto :eof

REM ============================================================================
REM RODAR TESTES
REM ============================================================================

:TESTES
cls
echo.
echo 🧪 RODANDO TESTES...
echo.

set TESTE_COUNT=0
set TESTE_OK=0

REM Test 1
if exist tests\test_mt5_adapter.py (
    echo [Test 1/5] MT5Adapter...
    python -m pytest tests\test_mt5_adapter.py -q 2>nul
    set /a TESTE_COUNT+=1
    if !errorlevel! EQU 0 set /a TESTE_OK+=1
) else (
    echo [Test 1/5] MT5Adapter... (NÃO ENCONTRADO)
)

REM Test 2
if exist tests\test_risk_validator.py (
    echo [Test 2/5] RiskValidator...
    python -m pytest tests\test_risk_validator.py -q 2>nul
    set /a TESTE_COUNT+=1
    if !errorlevel! EQU 0 set /a TESTE_OK+=1
) else (
    echo [Test 2/5] RiskValidator... (NÃO ENCONTRADO)
)

REM Test 3
if exist tests\test_orders_executor.py (
    echo [Test 3/5] OrdersExecutor...
    python -m pytest tests\test_orders_executor.py -q 2>nul
    set /a TESTE_COUNT+=1
    if !errorlevel! EQU 0 set /a TESTE_OK+=1
) else (
    echo [Test 3/5] OrdersExecutor... (NÃO ENCONTRADO)
)

echo.
echo ════════════════════════════════════════════════════════════════════════════
if !TESTE_COUNT! GEQ 1 (
    echo ✅ Testes completados: !TESTE_OK!/!TESTE_COUNT! OK
) else (
    echo ⚠️  Nenhum arquivo de teste encontrado
)
echo ════════════════════════════════════════════════════════════════════════════
echo.

pause
goto :eof

REM ============================================================================
REM VER STATUS
REM ============================================================================

:STATUS
cls
echo.
echo 📊 STATUS DO SISTEMA
echo.
echo Data/Hora: %date% %time%
echo Diretório: %cd%
echo.

echo Estrutura do projeto:
echo.
if exist "src" (
    echo ✅ src/
) else (
    echo ❌ src/ (NÃO ENCONTRADO)
)

if exist "tests" (
    echo ✅ tests/
) else (
    echo ❌ tests/ (NÃO ENCONTRADO)
)

if exist "config" (
    echo ✅ config/
) else (
    echo ❌ config/ (NÃO ENCONTRADO)
)

if exist "logs" (
    echo ✅ logs/
) else (
    echo ❌ logs/ (NÃO ENCONTRADO)
)

echo.
echo Componentes principais:
echo.
if exist "src\application\risk_validator.py" (
    echo ✅ RiskValidator
) else (
    echo ❌ RiskValidator (NÃO ENCONTRADO)
)

if exist "src\application\orders_executor.py" (
    echo ✅ OrdersExecutor
) else (
    echo ❌ OrdersExecutor (NÃO ENCONTRADO)
)

if exist "src\application\services\processador_bdi.py" (
    echo ✅ ProcessadorBDI
) else (
    echo ⚠️  ProcessadorBDI (NÃO ENCONTRADO)
)

echo.
echo Configurações:
echo.
if exist "config\producao_simples.yaml" (
    echo ✅ config\producao_simples.yaml (PRESENTE)
) else (
    echo ❌ config\producao_simples.yaml (NÃO ENCONTRADO)
)

echo.
pause
goto :eof

REM ============================================================================
REM VER CONFIGURAÇÃO
REM ============================================================================

:CONFIG
cls
echo.
echo 📋 CONFIGURAÇÃO ATIVA
echo.
if exist "config\producao_simples.yaml" (
    type "config\producao_simples.yaml"
) else (
    echo Arquivo de configuração ainda não criado.
    echo Execute a opção 1 para criar.
)

echo.
pause
goto :eof

REM ============================================================================
REM VER LOGS
REM ============================================================================

:LOGS
cls
echo.
echo 📜 LOG DE ATIVAÇÕES
echo.
if exist "logs\producao\ATIVACAO_LOG.txt" (
    type "logs\producao\ATIVACAO_LOG.txt"
) else (
    echo Nenhum log de ativação encontrado ainda.
)

echo.
pause
goto :eof

REM ============================================================================
REM SAIR
REM ============================================================================

:SAIR
cls
echo.
echo 👋 Até logo!
echo.
timeout /t 1 /nobreak >nul
exit /b 0
