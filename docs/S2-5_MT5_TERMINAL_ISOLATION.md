# 🔒 S2-5: MT5 Terminal Isolation & Reconnect

**Prioridade:** 🔴 MÁXIMA (Prioridade 0)
**Sprint:** Sprint 2 (IMEDIATO)
**Atribuído a:** Arquiteto de Sistemas + Eng Sr
**Status:** ⏳ NÃO INICIADO
**Data de Criação:** 2026-02-24
**Sessão:** Reunião Virtual Board Ampliado (Agenda ID 3: Infra & QA)

---

## 📋 CONTEXTO

**Origem:** Pergunta do Head de Finanças durante reunião de Governança
> *"Nosso operador tem algum tipo de controle/bloqueio sobre qual terminal Meta Trader é usado? No meu ambiente tenho outros terminais de Meta Trader e quero garantir o total isolamento entre eles. Eventualmente ao longo do dia nosso operador perde a conexão."*

**Problema Identificado:**
- Atualmente, a biblioteca Python `MetaTrader5` conecta-se ao primeiro terminal `terminal64.exe` disponível
- Nenhuma validação do PID do processo, path executável ou fingerprint de conta
- Sem retry automático após desconexão (causa HOLD operacional)
- Risco de ordem ser enviada para **conta/terminal errado**

---

## 🎯 REQUISITOS FUNCIONAIS

### RF-1: Validação de Fingerprint de Terminal

```python
FINGERPRINT_VALIDATION = {
    "exe_path": "C:\\Program Files\\Clear Investimentos MT5 Terminal\\terminal64.exe",
    "account_login": 1000346516,
    "server": "Clear MT5 - Live"
}
```

**Ação:**
1. Na conexão inicial, capturar o PID do `terminal64.exe` em execução
2. Armazenar em `~/.mt5_operator_session.json`:
   - `pid`: PID do processo
   - `exe_path`: Caminho completo do executável
   - `account_login`: Conta conectada
   - `server`: Servidor MT5
   - `timestamp`: Data/hora da conexão

3. Em **cada operação crítica** (envio de ordem, check de posição):
   - Validar que o PID registrado ainda está em execução
   - Validar que o `account_login` do MT5 corresponde ao esperado
   - Rejeitar operação se mismatch

**Rejeição:**
```
❌ TERMINAL ISOLATION VIOLATION!
   Esperado PID: 12345 | Encontrado: 0 (terminal não está em execução)
   OU
   Esperado Conta: 1000346516 | Logado em: 1000999999

   Operação BLOQUEADA até resolução manual.
```

---

### RF-2: Reconnect Automático com Retry

**Estratégia de Retry (Exponential Backoff):**

```python
RETRY_CONFIG = {
    "max_attempts": 3,
    "backoff_seconds": [5, 10, 20],  # 5s, 10s, 20s
    "on_failure": "HALT_TRADING"
}
```

**Fluxo:**

```
[Desconexão Detectada]
         ↓
   Tentativa 1 (aguardar 5s)
   ├─ ✅ Sucesso? → Retomar operação
   └─ ❌ Falha → Tentativa 2

   Tentativa 2 (aguardar 10s)
   ├─ ✅ Sucesso? → Retomar operação
   └─ ❌ Falha → Tentativa 3

   Tentativa 3 (aguardar 20s)
   ├─ ✅ Sucesso? → Retomar operação
   └─ ❌ Falha → HALT + Alerta crítico

   [HALT OPERACIONAL]
   - Parar envio de novas ordens
   - Manter posições abertas
   - Alertar trader e MONITOR_OPERADOR.bat
   - Aguardar intervenção manual
```

**Código da Implementação:**

```python
# src/infrastructure/adapters/mt5_adapter.py

class MT5Adapter(IBrokerAdapter):

    def __init__(self, login: int, password: str, server: str,
                 terminal_exe_path: str = None):
        self.login = login
        self.password = password
        self.server = server
        self.terminal_exe_path = terminal_exe_path
        self._session_fingerprint = None
        self._mt5 = None

    def _validate_terminal_isolation(self) -> bool:
        """Valida que estamos conectados ao terminal correto."""
        import psutil

        # Validar que terminal64.exe existe com PID esperado
        if self._session_fingerprint:
            pid = self._session_fingerprint["pid"]
            if not psutil.pid_exists(pid):
                return False  # Terminal crashou

        # Validar account login
        account_info = self._mt5.account_info()
        if account_info.login != self.login:
            return False  # Conta mismatch

        return True

    def _save_session_fingerprint(self):
        """Salva fingerprint após conexão bem-sucedida."""
        import psutil
        import json

        # Encontrar PID do terminal64.exe
        pid = None
        for proc in psutil.process_iter(['pid', 'name', 'exe']):
            try:
                if 'terminal64.exe' in proc.info['name'].lower():
                    if self.terminal_exe_path is None or \
                       self.terminal_exe_path.lower() in proc.info['exe'].lower():
                        pid = proc.info['pid']
                        break
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                pass

        if pid:
            self._session_fingerprint = {
                "pid": pid,
                "exe_path": self.terminal_exe_path,
                "account_login": self.login,
                "server": self.server,
                "timestamp": datetime.now().isoformat()
            }

            # Persistir
            home = os.path.expanduser("~")
            session_file = os.path.join(home, ".mt5_operator_session.json")
            with open(session_file, "w") as f:
                json.dump(self._session_fingerprint, f, indent=2)

    def connect(self, max_retries: int = 3,
                backoff_seconds: list = None) -> bool:
        """Conecta ao MT5 com retry automático."""
        if backoff_seconds is None:
            backoff_seconds = [5, 10, 20]

        for attempt in range(max_retries):
            try:
                import MetaTrader5 as mt5
                self._mt5 = mt5

                if not mt5.initialize():
                    raise Exception(f"Initialize failed: {mt5.last_error()}")

                authorized = mt5.login(
                    login=self.login,
                    password=self.password,
                    server=self.server,
                    timeout=60000
                )

                if not authorized:
                    raise Exception(f"Login failed: {mt5.last_error()}")

                # Salvar fingerprint após sucesso
                self._save_session_fingerprint()

                return True

            except Exception as e:
                if attempt < max_retries - 1:
                    wait_time = backoff_seconds[attempt]
                    logger.warning(
                        f"MT5 connection attempt {attempt + 1}/{max_retries} failed. "
                        f"Retrying in {wait_time}s: {e}"
                    )
                    time.sleep(wait_time)
                else:
                    logger.error(
                        f"MT5 connection failed after {max_retries} attempts: {e}"
                    )
                    return False

        return False

    def _ensure_connected_with_isolation(self):
        """Valida isolamento antes de operações críticas."""
        if not self._validate_terminal_isolation():
            logger.critical("MT5 Terminal Isolation violation detected!")
            # Disparar alerta
            raise BrokerConnectionError(
                "Terminal isolation validation failed. "
                "Check PID, account login, and terminal status."
            )
```

---

### RF-3: Health Check Contínuo

**Adicionar ao `src/infrastructure/monitoring/health_checker.py`:**

```python
class MT5IsolationHealthCheck:
    """Monitora isolamento e reconexão do MT5."""

    def __init__(self, adapter: MT5Adapter, check_interval_sec: int = 30):
        self.adapter = adapter
        self.check_interval_sec = check_interval_sec
        self.last_check: datetime | None = None

    def check_health(self) -> dict:
        """Retorna status de saúde da conexão MT5."""
        result = {
            "healthy": False,
            "reason": "",
            "last_check": datetime.now().isoformat(),
            "terminal_pid": None,
            "account_login_validated": False,
            "connection_duration_sec": 0
        }

        try:
            if not self.adapter._validate_terminal_isolation():
                result["reason"] = "Terminal isolation validation failed"
                return result

            if not self.adapter.is_connected():
                result["reason"] = "MT5 adapter reports disconnected"
                # Disparar reconnect
                if not self.adapter.connect():
                    result["reason"] = "Reconnect failed after 3 attempts"
                    return result

            result["healthy"] = True
            result["terminal_pid"] = self.adapter._session_fingerprint["pid"]
            result["account_login_validated"] = True

        except Exception as e:
            result["reason"] = f"Health check exception: {str(e)}"

        return result
```

---

### RF-4: Alertas no MONITOR_OPERADOR.bat

**Adicionar à tela de monitoramento:**

```
╔════════════════════════════════════════════════════════════╗
║ 🔒 MT5 TERMINAL ISOLATION STATUS                           ║
╠════════════════════════════════════════════════════════════╣
║ Terminal PID:        12345 ✅                              ║
║ Account Validation:  1000346516 ✅                         ║
║ Server Match:        Clear MT5 - Live ✅                   ║
║ Last Health Check:   2026-02-24 15:32:15 ✅                ║
║ No. of Reconnects:   0                                     ║
║ Last Reconnect:      (nunca)                               ║
║ Status:              🟢 HEALTHY                            ║
╚════════════════════════════════════════════════════════════╝

❌ EXEMPLO DE ALERTA (se isolamento falhar):
╔════════════════════════════════════════════════════════════╗
║ 🔒 MT5 TERMINAL ISOLATION STATUS                           ║
╠════════════════════════════════════════════════════════════╣
║ Terminal PID:        12345 → PID não existe ❌              ║
║ Account Validation:  MISMATCH ❌                            ║
║ Status:              🔴 ISOLATED FAILURE                   ║
║ Action:              Aguardando intervenção manual...      ║
║ Retry Attempts:      3/3 EXHAUSTED                         ║
╚════════════════════════════════════════════════════════════╝
```

---

## 🧪 TESTES UNITÁRIOS

**Localização:** `tests/unit/test_mt5_terminal_isolation.py`

### TC-1: Validação de Fingerprint

```python
def test_mt5_fingerprint_validation_success():
    """Deve aceitarconexão válida."""
    adapter = MT5Adapter(
        login=1000346516,
        password="...",
        server="Clear MT5 - Live",
        terminal_exe_path="C:\\Program Files\\Clear Investimentos MT5 Terminal\\terminal64.exe"
    )
    assert adapter.connect()
    assert adapter._session_fingerprint is not None
    assert adapter._session_fingerprint["login"] == 1000346516

def test_mt5_fingerprint_validation_wrong_account():
    """Deve rejeitar se conta logada for diferente."""
    adapter = MT5Adapter(login=1000346516, ...)
    adapter.connect()

    # Simular mismatch de conta
    with patch.object(adapter._mt5, 'account_info') as mock:
        mock.return_value.login = 1000999999
        assert not adapter._validate_terminal_isolation()

def test_mt5_fingerprint_validation_terminal_crashed():
    """Deve detectar se terminal foi encerrado."""
    adapter = MT5Adapter(login=1000346516, ...)
    adapter.connect()

    # Simular terminal crashado
    with patch('psutil.pid_exists', return_value=False):
        assert not adapter._validate_terminal_isolation()
```

### TC-2: Reconnect Automático

```python
def test_mt5_reconnect_retry_exponential_backoff():
    """Deve fazer retry com backoff exponencial."""
    adapter = MT5Adapter(login=1000346516, ...)

    connect_attempts = []
    original_connect = adapter._mt5.login

    def mock_login_fails_then_succeeds(*args, **kwargs):
        connect_attempts.append(1)
        return len(connect_attempts) > 2  # Falha 2x, sucede na 3ª

    with patch.object(adapter._mt5, 'login', side_effect=mock_login_fails_then_succeeds):
        result = adapter.connect(
            max_retries=3,
            backoff_seconds=[0.1, 0.2, 0.3]  # Reduzir para testes
        )

        assert result is True
        assert len(connect_attempts) == 3

def test_mt5_reconnect_exhausted_halts_trading():
    """Se todos os retries falharem, deve ativar HALT."""
    adapter = MT5Adapter(login=1000346516, ...)

    with patch.object(adapter._mt5, 'login', return_value=False):
        result = adapter.connect(max_retries=3)

        assert result is False
        # Sistema deve estar em HALT
        assert adapter.is_trading_halted()
```

### TC-3: Múltiplas Instâncias MT5

```python
def test_mt5_rejects_wrong_terminal_instance():
    """Se houver 2 terminais abertos, deve rejeitar a outro."""
    # Abrir Terminal A (conta 1000346516)
    adapter_a = MT5Adapter(login=1000346516, ...)
    assert adapter_a.connect()

    # Tentar conectar em Terminal B (conta 1000999999) mas com mesma lib
    adapter_b = MT5Adapter(login=1000999999, ...)

    # adapter_b deve ser rejeitado se tentar usar mesmo terminal
    assert not adapter_b.connect()  # Isolamento previne acesso
```

---

## 📊 ACCEPTANCE CRITERIA (AC)

- [ ] AC-1: Terminal PID validado na conexão inicial
- [ ] AC-2: Fingerprint de sessão persistido em `~/.mt5_operator_session.json`
- [ ] AC-3: Mismatch de conta logada rejeita operações (teste: trocar login no MT5 enquanto operador roda)
- [ ] AC-4: Retry automático com backoff [5s, 10s, 20s] implementado
- [ ] AC-5: Após 3 tentativas falhadas, sistema entra em HALT
- [ ] AC-6: Health check a cada 30s detecta desconexões
- [ ] AC-7: MONITOR_OPERADOR.bat exibe status de isolamento
- [ ] AC-8: Todos os 4 testes unitários passam (100% coverage de isolation logic)
- [ ] AC-9: Documentado em inline comments (Python) e markdown
- [ ] AC-10: Nenhuma ordem é enviada durante estado de isolamento violado

---

## 📈 IMPACTO ESPERADO

| Métrica | Antes | Depois |
|:---|:---:|:---:|
| Risco de ordem em conta errada | 🔴 SIM | 🟢 NÃO |
| Tempo de recovery após desconexão | ~5 min (manual) | ~20s (automático) |
| Perda de operações por crash terminal | 🔴 SIM | 🟢 NÃO (retry) |
| Visibilidade de isolamento | 🔴 NÃO | 🟢 SIM (dashboard) |

---

## 🔗 ARQUIVOS A MODIFICAR

1. **`src/infrastructure/adapters/mt5_adapter.py`**
   - Adicionar `terminal_exe_path` parameter
   - Implementar `_validate_terminal_isolation()`
   - Implementar `_save_session_fingerprint()`
   - Modificar `connect()` com retry logic

2. **`src/infrastructure/monitoring/health_checker.py`**
   - Adicionar classe `MT5IsolationHealthCheck`
   - Integrar ao health check loop

3. **`MONITOR_OPERADOR.bat` (ou similar script)**
   - Adicionar seção visual de status de isolamento

4. **`tests/unit/test_mt5_terminal_isolation.py`** (novo arquivo)
   - 4+ test cases cómo especificado

5. **`docs/ARCHITECTURE.md`**
   - Atualizar diagrama de camada de infraestrutura

---

## 📅 TIMELINE

- **Sprint 2, Dia 1 (24/02):** Análise + prototipagem
- **Sprint 2, Dia 2-3 (25-26/02):** Implementação core
- **Sprint 2, Dia 4 (27/02):** Testes + integração
- **Sprint 2, Dia 5 (28/02):** Deploy de canário

**Target:** 🟢 **COMPLETO E VALIDADO ATÉ 28/02/2026**

---

## ✅ SIGN-OFF

- **Reunião:** Agenda Virtual ID 3 — Infra & QA
- **Data:** 2026-02-24 15:45 BRT
- **Levantado por:** Head de Finanças
- **Prioridade Conferida:** 🔴 **MÁXIMA (0)**
- **Consenso:** ✅ TODO O BOARD APROVA

**Próximos Passos:**
1. ✅ Tarefa adicionada ao STATUS_ENTREGAS.md (S2-5)
2. ✅ Especificação técnica capturada (este documento)
3. ⏳ **Atribuição ao Arquiteto de Sistemas** (aguardando confirmação)
4. ⏳ **Kick-off devevelopment** quando desenvolvedor confirmar
