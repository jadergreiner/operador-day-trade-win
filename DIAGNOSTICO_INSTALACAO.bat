@echo off
REM ============================================================================
REM DIAGNOSTICO - Problema na instalacao de dependencias
REM ============================================================================

setlocal enabledelayedexpansion
chcp 65001 >nul 2>&1

cls
echo.
echo ******************************************************************************
echo *  DIAGNOSTICO DE PROBLEMA NA INSTALACAO                                   *
echo ******************************************************************************
echo.

echo [PASSO 1] Verificar Python e pip
echo.
python --version
python -m pip --version
echo.

echo [PASSO 2] Verificar conexao de internet
echo.
ping google.com -n 1 >nul 2>&1
if errorlevel 1 (
    echo [ERRO] Sem conexao de internet - nao consegue fazer pip install
    pause
    exit /b 1
) else (
    echo [OK] Conexao de internet OK
)
echo.

echo [PASSO 3] Atualizar pip (pode resolver muitos problemas)
echo.
python -m pip install --upgrade pip
echo.

echo [PASSO 4] Tentar instalar fastapi (teste individual)
echo.
echo Instalando fastapi==0.104.1...
python -m pip install fastapi==0.104.1 -v
if errorlevel 1 (
    echo.
    echo [ERRO] Falha ao instalar fastapi
    echo.
    echo Tentando sem versao especifica...
    python -m pip install fastapi
)
echo.

echo [PASSO 5] Tentar instalar uvicorn (teste individual)
echo.
echo Instalando uvicorn==0.24.0...
python -m pip install uvicorn==0.24.0 -v
if errorlevel 1 (
    echo.
    echo [ERRO] Falha ao instalar uvicorn
    echo.
    echo Tentando sem versao especifica...
    python -m pip install uvicorn
)
echo.

echo [PASSO 6] Listar pacotes instalados
echo.
python -m pip list
echo.

echo ******************************************************************************
echo *  RESULTADO DIAGNOSTICO                                                    *
echo ******************************************************************************
echo.
echo Se todos os passos acima funcionaram:
echo   → O problema foi apenas de timeout ou conexao temporia
echo   → Tente rodar INICIAR_PHASE6.bat novamente
echo.
echo Se teve erro em algum passo:
echo   → Veja qual erro especifico apareceu acima
echo   → Solucoes comuns:
echo.
echo   1. Sem conexao de internet?
echo      → Verificar router/wifi
echo      → Ou tentar ping google.com manualmente
echo.
echo   2. Erro de permissao?
echo      → Abra CMD como ADMINISTRADOR
echo      → Windows + X → Command Prompt (Admin)
echo      → Execute este script novamente
echo.
echo   3. Versao do Python muito antiga?
echo      → Instale Python 3.9+ de https://www.python.org
echo      → Com "Add Python to PATH" marcado
echo.
echo   4. Problema com pip cache?
echo      → python -m pip cache purge
echo      → Tente instalar novamente
echo.

pause
