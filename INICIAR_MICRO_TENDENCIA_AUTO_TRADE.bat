@echo off
REM ============================================================
REM  OPERADOR MICRO TENDENCIA - v1.2.3 (25/02/2026)
REM ============================================================
REM 
REM  Releases:
REM    v1.2.0 (20/02): TASK-CRITICA-0 - Core infrastructure + ORM
REM    v1.2.3 (25/02): INTEGRATION-ML-001 - ML dataset loading
REM                    14/14 tests PASSING | 94% code coverage
REM 
REM  Integrações Ativas:
REM    ✅ BDI Detection (v1.2.0)
REM    ✅ SMC Confluence (M1/M5 validation)
REM    ✅ ML Classifier (v1.2.3 - 94% coverage)
REM    🔄 WebSocket Monitor (Sprint 1 - starts 27/02)
REM    🔄 Risk Validator (Sprint 1 - starts 28/02)
REM
REM  Delegamos toda a logica ao Python para evitar problemas
REM  de sintaxe batch. O arquivo .py contem todas as integrações.
REM ============================================================
REM

echo.
echo   ============================================================
echo   OPERADOR MICRO TENDENCIA - v1.2.3
echo   ============================================================
echo.
echo   Integrações presentes:
echo     - Infrastructure (v1.2.0)
echo     - ML Dataset Loading (v1.2.3)
echo     - Sprint 1 Timeline (27/02 Kickoff)
echo.
echo   Iniciando agente...
echo.

python INICIAR_MICRO_TENDENCIA_AUTO_TRADE.py
pause
