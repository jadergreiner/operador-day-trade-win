@echo off
REM Criar tarefa agendada para limpeza diaria do banco
REM Execute como ADMINISTRADOR

echo [*] Criando tarefa agendada de limpeza diaria...

REM Criar tarefa para rodar cleanup diariamente as 4 AM
schtasks /create /tn "DBCleanup-Daily" /tr "python c:\repo\operador-day-trade-win\cleanup_dados_automatico.py" /sc daily /st 04:00 /f

echo [+] Tarefa criada com sucesso!
echo [*] Proxima execucao: Amanha as 04:00 AM
echo.
echo Para verificar a tarefa:
echo   schtasks /query /tn "DBCleanup-Daily"
echo.
echo Para remover a tarefa:
echo   schtasks /delete /tn "DBCleanup-Daily" /f
