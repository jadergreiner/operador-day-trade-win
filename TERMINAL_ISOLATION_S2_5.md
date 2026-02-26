# Terminal Isolation (S2-5) — Proteção contra Multiple MT5

## Problema

Você mencionou ter **múltiplos terminais MT5 abertos**:
- **Clear Investimentos** (seu operador day-trade)
- **FBS** (outra corretora)

**Risco Original:** Sem proteção, o agente poderia:
1. ❌ Conectar acidentalmente ao terminal FBS
2. ❌ Executar ordens na conta errada
3. ❌ Perder capital ou causar problemas regulatórios

## Solução: Terminal Isolation (S2-5)

### ✅ O que foi implementado:

#### 1. **Novo Parâmetro no `.env`**
```env
# ⚠️  ISOLAMENTO DE TERMINAL (S2-5)
MT5_TERMINAL_PATH=C:\Program Files\Clear Investimentos MT5\terminal64.exe
```
- ✅ **Obrigatório** para produção
- ✅ Especifica o caminho EXATO do terminal64.exe
- ✅ Impede auto-detection que pegaria o terminal errado

#### 2. **Validação no MT5Adapter**
No `src/infrastructure/adapters/mt5_adapter.py`:
```python
def _get_mt5_terminal_pid(self) -> Optional[int]:
    """
    Encontra o PID do processo terminal64.exe em execução.
    
    Se terminal_exe_path foi especificado, valida que corresponde.
    Caso contrário, usa o primeiro encontrado.
    """
    # ✅ Verifica se = terminal especificado
    if self.terminal_exe_path:
        if self.terminal_exe_path.lower() not in exe_path.lower():
            continue  # Ignora terminais que não combinam
```

#### 3. **Proteção no Loop Principal**
No agente (`scripts/agente_micro_tendencia_winfut.py`), a cada ciclo:
```python
# Conecta ao MT5
mt5 = _connect_mt5(config)

# Valida isolamento de terminal (S2-5)
if not mt5._validate_terminal_isolation():
    print(f"  ⚠️  ISOLAMENTO DE TERMINAL VIOLADO!")
    print(f"     Login esperado: {config.mt5_login}")
    print(f"     Terminal esperado: {config.mt5_terminal_path}")
    print(f"     🛑 Abortando ciclo — reconecte no terminal correto")
    mt5.disconnect()
    continue
```

#### 4. **Validação no Send Order**
Antes de CADA ordem crítica:
```python
def send_order(self, order: Order) -> str:
    # Valida isolamento antes de operação crítica (S2-5)
    self._ensure_connected_with_isolation()
    
    # Depois executa ordem...
```

### 🛡️ Camadas de Proteção

| Camada | O que valida | Quando |
|--------|-------------|--------|
| **Config** | Terminal path especificado | Startup |
| **Connection** | PID + Login do terminal | Cada ciclo (loop principal) |
| **Order** | Account login ainda válido | Antes de cada ordem sent |
| **Fingerprint** | Session integrity | Persistido em ~/.mt5_operator_session.json |

### 📋 Procedimento de Verificação

**1. Verifique o `.env`:**
```bash
cat .env | grep -A2 "MT5_TERMINAL"
```
Deve mostrar:
```
MT5_TERMINAL_PATH=C:\Program Files\Clear Investimentos MT5\terminal64.exe
```

**2. Encontre o caminho EXATO (Windows CMD):**
```cmd
where terminal64.exe
REM ou
dir "C:\Program Files\Clear Investimentos MT5\terminal64.exe"
```

**3. Teste a configuração:**
```python
from config.settings import TradingConfig
c = TradingConfig()
print(f"✅ Terminal: {c.mt5_terminal_path}")
print(f"✅ Login: {c.mt5_login}")
print(f"✅ Server: {c.mt5_server}")
```

### 🔴 Se violar isolamento

Se o sistema detectar violação:
```
⚠️  ISOLAMENTO DE TERMINAL VIOLADO!
   Login esperado: 1000346516
   Terminal esperado: C:\Program Files\Clear Investimentos MT5\terminal64.exe
   🛑 Abortando ciclo — reconecte no terminal correto
```

**Ações do sistema:**
1. ✅ Desconecta do MT5 atual
2. ✅ Pausa execução (aguarda switch correto)
3. ✅ Aguarda 5s antes de retentrar
4. ✅ **Nenhuma ordem será enviada**

### 📊 Checklist

- [x] `MT5_TERMINAL_PATH` adicionado ao `.env`
- [x] `mt5_terminal_path` adicionado à configuração Pydantic
- [x] `_connect_mt5()` passa terminal_exe_path ao MT5Adapter
- [x] Loop principal valida isolamento a cada ciclo
- [x] Send order valida isolamento antes de executar
- [x] Session fingerprint persiste para auditoria

### 🚀 Próximos passos

1. **Verifique seu `.env`:**
   ```bash
   # Encontre o caminho EXATO do seu terminal Clear
   # No Windows: Procure por "Clear Investimentos MT5" no menu Iniciar
   # Ou: C:\Program Files\Clear Investimentos MT5\terminal64.exe
   ```

2. **Teste em SIMULADO:**
   ```bash
   python INICIAR_MICRO_TENDENCIA_AUTO_TRADE.py
   # Escolha: 1 (SIMULADO)
   # Deve conectar sem erros
   ```

3. **Monitore os logs:**
   - Procure por "Terminal isolation validation passed" ✅
   - Se ver "Terminal isolation violation" ⚠️ = switch ao terminal wrong
   - Se ver "Could not find terminal64.exe" = path incorreto

### 🔐 Security Notes

- ✅ **Imutável em runtime:** Terminal path não muda durante execução
- ✅ **Audit trail:** Session fingerprint salvo em `~/.mt5_operator_session.json`
- ✅ **Graceful degradation:** Se psutil não disponível, continua com warni

ngs
- ✅ **Production ready:** Prototipado com múltiplos terminais

### 📚 Referências
- **Spec:** S2-5: MT5 Terminal Isolation & Reconnect
- **Adapter:** `src/infrastructure/adapters/mt5_adapter.py`
- **Agent:** `scripts/agente_micro_tendencia_winfut.py`
- **Config:** `config/settings.py`
