@echo off
chcp 65001 >nul
title Monitor Quantico WIN$ - Tendencia do Dia

echo ============================================================
echo   MONITOR QUANTICO - WIN$ Mini Indice Brasileiro
echo   Tendencia do Dia - Contexto Global
echo ============================================================
echo.

if exist ".venv\Scripts\activate.bat" (
    call .venv\Scripts\activate.bat
    echo [OK] Ambiente virtual ativado
) else (
    echo [AVISO] Ambiente virtual nao encontrado - usando Python global
)

python -c "import yfinance" 2>nul
if errorlevel 1 (
    echo [INFO] Instalando dependencia obrigatoria yfinance...
    pip install yfinance --quiet
    if errorlevel 1 (
        echo [ERRO] Falha ao instalar yfinance. Verifique sua conexao.
        pause
        exit /b 1
    )
)

python -c "import tradingview_ta" 2>nul
if errorlevel 1 (
    echo [INFO] Instalando dependencia opcional tradingview-ta...
    pip install tradingview-ta --quiet
    if errorlevel 1 (
        echo [AVISO] tradingview-ta nao instalado - indicadores tecnicos desabilitados
    )
)

echo.
echo [INFO] Iniciando backend do monitor...
echo [INFO] API JSON: http://localhost:8765/dados
echo [INFO] Monitor: http://localhost:8765/
echo.

python scripts\monitor_quantico_tendencia.py &

echo [INFO] Aguardando servidor iniciar...
timeout /t 3 /nobreak >nul

echo [INFO] Abrindo monitor no browser: http://localhost:8765/
start "" "http://localhost:8765/"

echo.
echo [INFO] Servidor rodando. Feche esta janela para encerrar o monitor.
echo.

python scripts\monitor_quantico_tendencia.py
