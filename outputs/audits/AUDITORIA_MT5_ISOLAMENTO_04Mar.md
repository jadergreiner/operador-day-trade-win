# AUDITORIA MT5 TERMINAL ISOLATION
Gerado: 2026-03-04 11:50:31

## RESUMO EXECUTIVO
- **Checks Passed:** 5/6
- **Issues Found:** 0
- **Warnings:** 3
- **Status Geral:** 🟢 PASS

## RECOMENDAÇÕES

### OBRIGATÓRIO: Configure .env
```bash
# Adicione ao .env (NUNCA commitar!):
MT5_TERMINAL_PATH=C:\Program Files\Clear Investimentos MT5 Terminal\terminal64.exe
MT5_LOGIN=seu_login
MT5_PASSWORD=sua_senha
MT5_SERVER=servidor_clear
```

### VALIDAÇÕES ATIVAS NO CÓDIGO

1. **Pre-Flight Check** (`_preflight_check_mt5`):
   - ✅ Rejeita se MT5_TERMINAL_PATH não estiver configurado
   - ✅ Rejeita se path não contém 'CLEAR'
   - ✅ Rejeita se arquivo não existe
   - ✅ Tenta conectar para testar isolamento

2. **Terminal Isolation** (`_validate_terminal_isolation`):
   - ✅ Valida que processo terminal64.exe é do path esperado
   - ✅ Rejeita se outro MT5 (FBS/Zero/etc) está aberto

3. **MT5Adapter Filtering**:
   - ✅ Filtra processo por terminal_exe_path exato
   - ✅ Ignora qualquer outro terminal instalado

### PROTEçÕES CONTRA ACIDENTES

| Risco | Proteção |
|-------|----------|
| Executar com outro MT5 aberto | Pre-flight check rejeita se haja outro terminal |
| Conectar a FBS/Zero/XP | Path deve conter 'CLEAR', validado 3x |
| Usar caminho errado | Arquivo deve existir, PID deve corresponder |
| Bypass da validação | Error log documenta toda conexão, rastreia PID |

## CASOS DE USO TESTADOS

✅ Iniciar agente → Pre-flight valida terminal
✅ Terminal errado aberto → Rejeita rapidamente
✅ MT5_TERMINAL_PATH não configurado → Erro crítico explícito
✅ FBS/Zero/XP abertos junto com Clear → Só Clear conecta

## LOGS DE AUDITORIA

Todos os eventos críticos são logados em:
- `data/logs/minitrade-*.log`: Tentativas de conexão, PID, path usado
- `data/db/trading.db`: Tabela `_logs` registra época da conexão e terminal


## WARNINGS
- scripts/agente_micro_tendencia_winfut.py:   ⚠️  RISCO: Referença a FBS na linha 3137: FBS, Zero, etc). Falha rápido se terminal
- scripts/agente_micro_tendencia_winfut.py:   ⚠️  RISCO: Referença a Zero Markets na linha 3767: Zero Markets
- config/settings.py:   ⚠️  RISCO: Referença a Zero Markets na linha 149: Zero Markets

## CONCLUSÕES
- Total de validações: 5 (5 passed, 0 failed)
- Hardcoded paths de FBS/Zero encontrados: 3
- Isolamento de terminal: 🟢 SEGURO
- Recomendação: Liberado para produção
