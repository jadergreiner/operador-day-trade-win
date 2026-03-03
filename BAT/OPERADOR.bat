@echo off
REM =====================================================
REM  OPERADOR - Monitor Unico de Entrada
REM  Operador Day Trade WIN - LIVE TRADING
REM =====================================================

setlocal enabledelayedexpansion
chcp 65001 >nul

title OPERADOR - Sistema de Monitoramento

color 0A

REM Executa o monitor em Python
python scripts\monitor_operador_live.py

pause
