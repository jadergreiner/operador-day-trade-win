# 🚨 AUDITORIA CRÍTICA - VIOLAÇÃO DE ISOLAMENTO TERMINAL (S2-5)
**Data:** 27 Feb 2026 14:45 BRT
**Status:** 🔴 CRÍTICO - Em Investigação
**Severidade:** P0 | **Impacto:** Risco de Ordens Erradas | **Frequência:** RECORRENTE

---

## 📌 RESUMO EXECUTIVO

### O Problema
Ao executar `INICIAR_MICRO_TENDENCIA_AUTO_TRADE.bat`, o operador **frequentemente se conecta ao terminal ERRADO**:

```
❌ ESPERADO:   Login 1000346516 (Clear Investimentos)
❌ OBTIDO:     Login 111833527   (FBS MetaTrader 5)

Terminal isolation violation: Expected login 1000346516, but MT5 is logged in as 111833527
  ⚠️  ISOLAMENTO DE TERMINAL VIOLADO!
     Login esperado: 1000346516
     Terminal esperado: C:\Program Files\Clear Investimentos MT5 Terminal\terminal64.exe
     🛑 Abortando ciclo — reconecte no terminal correto
```

### Impacto
- ⚠️ Sistema detecta e **aborta** (protege contra envio de ordens erradas) ✅ **SEGURO**
- ❌ MAS operador fica em HALT cíclico, aguardando reconexão manual
- ❌ Reduz uptime operacional
- ❌ **ROOT CAUSE:** Biblioteca Python MT5 conecta ao "primeiro terminal disponível" ao inicializar

---

## 🔍 INVESTIGAÇÃO PROFUNDA

### 1. AMBIENTE DO USUÁRIO - Dois Terminais

```
Terminal 1 (CORRETO):
├─ Nome: Clear Investimentos MT5
├─ Path: C:\Program Files\Clear Investimentos MT5 Terminal\terminal64.exe
├─ Login: 1000346516
├─ Server: Clear MT5 - Live
└─ Status: ✅ ATIVO

Terminal 2 (RISCO):
├─ Nome: FBS MetaTrader 5
├─ Path: C:\Program Files\FBS MetaTrader 5\terminal64.exe
├─ Login: 111833527
├─ Server: FBS Demo/Live
└─ Status: ✅ ATIVO (aberto pelo usuário)
```

### 2. COMO O SISTEMA DEVERIA FUNCIONAR (S2-5)

#### Fluxo Esperado:
```
[INICIAR_MICRO_TENDENCIA_AUTO_TRADE.bat]
  ↓
[scripts/agente_micro_tendencia_winfut.py]
  ├─ Valida MT5_TERMINAL_PATH em .env
  └─ Carrega: C:\Program Files\Clear Investimentos MT5 Terminal\terminal64.exe
    ↓
[MT5Adapter._connect_single()]
  ├─ import MetaTrader5 as mt5
  ├─ mt5.initialize()                      [⚠️ PROBLEMA AQUI!]
  └─ mt5.login(login=1000346516, ...)
    ↓
[MT5Adapter._validate_terminal_isolation()]
  ├─ Valida PID do processo
  └─ Valida account_info.login == 1000346516
    ✅ OK → Prossegue
    ❌ MISMATCH → Aborta com mensagem de erro
```

### 3. POR QUE ESTÁ FALHANDO

#### ⚠️ Problema Identificado:

Quando `MetaTrader5.initialize()` é chamado, ele **conecta ao primeiro terminal MT5 disponível** que ele consegue encontrar, **independentemente de qual é**.

```python
# src/infrastructure/adapters/mt5_adapter.py (linha 387)
def _connect_single(self) -> bool:
    try:
        import MetaTrader5 as mt5
        self._mt5 = mt5

        # ⚠️ PROBLEMA: initialize() sem specify terminal_exe_path
        if not mt5.initialize():  # Conecta ao "primeiro" terminal
            raise BrokerConnectionError(
                f"MT5 initialize failed: {mt5.last_error()}"
            )

        # Aqui temos 50% de chance de estar no terminal ERRADO!
        authorized = mt5.login(
            login=self.login,        # 1000346516
            password=self.password,
            server=self.server,
            timeout=self.timeout,
        )
```

**O que acontece:**
1. Terminal 1 (Clear) aberto e logado com conta 1000346516 ✅
2. Terminal 2 (FBS) aberto e logado com conta 111833527 ✅
3. Operador executa `INICIAR_MICRO_TENDENCIA_AUTO_TRADE.bat`
4. Python MT5 library faz `initialize()` → Pega **Terminal 2 (FBS)** por acaso
5. Tenta fazer login com `1000346516` no Terminal 2
6. **Falha de login OU conecta a conta ERRADA no Terminal 2**
7. `_validate_terminal_isolation()` detecta: Login é 111833527, não 1000346516
8. **Sistema aborta** (comportamento seguro) ✅
9. Operador fica em HALT cíclico

---

### 4. EVIDÊNCIA - MAPEAMENTO DO CÓDIGO

#### A. Inicialização (Linha 387-421 em mt5_adapter.py)
```python
def _connect_single(self) -> bool:
    try:
        import MetaTrader5 as mt5
        self._mt5 = mt5

        # ⚠️ RISCO: Sem path específico, mt5.initialize() pega qualquer terminal
        if not mt5.initialize():
            raise BrokerConnectionError(...)

        # Tenta login
        authorized = mt5.login(
            login=self.login,        # 1000346516
            password=self.password,
            server=self.server,
            timeout=self.timeout,
        )
```

#### B. Validação de Isolamento (Linha 241-293 em mt5_adapter.py) ✅ **FUNCIONA CORRETAMENTE**
```python
def _validate_terminal_isolation(self) -> bool:
    """Valida que estamos conectados ao terminal correto."""
    if not self._session_fingerprint:
        return True

    try:
        import psutil

        # 1. Valida PID
        pid = self._session_fingerprint.get("pid")
        if pid and not psutil.pid_exists(pid):
            return False  # Terminal crashou

        # 2. ✅ Valida account login - AQUI DETECTA!
        account_info = self._mt5.account_info()
        if account_info.login != self.login:  # 1000346516 vs 111833527
            logger.error(
                f"Terminal isolation violation: Expected login {self.login}, "
                f"but MT5 is logged in as {account_info.login}"  # ← DETECTA AQUI!
            )
            return False

        logger.debug("Terminal isolation validation passed")
        return True
```

#### C. Loop Principal (scripts/agente_micro_tendencia_winfut.py - Linha 2953-2959) ✅ **VALIDA MAS CHEGA TARDE**
```python
def _connect_mt5(config) -> MT5Adapter:
    """Conecta ao MetaTrader 5 com isolamento de terminal."""
    mt5 = MT5Adapter(
        login=config.mt5_login,
        password=config.mt5_password,
        server=config.mt5_server,
        terminal_exe_path=config.mt5_terminal_path,  # Tem path, mas...
    )
    if not mt5.connect():
        raise RuntimeError("Falha ao conectar no MT5...")
    return mt5

# No loop principal:
mt5 = _connect_mt5(config)

# ✅ Valida isolamento
if not mt5._validate_terminal_isolation():
    print(f"  ⚠️  ISOLAMENTO DE TERMINAL VIOLADO!")
    print(f"     Login esperado: {config.mt5_login}")
    print(f"     Terminal esperado: {config.mt5_terminal_path}")
    print(f"     🛑 Abortando ciclo — reconecte no terminal correto")
    mt5.disconnect()
    continue  # ← TAL sistema aguarda reconexão manual
```

**Problema:** `terminal_exe_path` é **PASSADO** ao MT5Adapter, mas **NÃO UTILIZADO** em `_connect_single()`.

---

### 5. RAIZ: CÓDIGO NÃO USA O PARÂMETRO

#### Arquivo: `src/infrastructure/adapters/mt5_adapter.py`

**Inicialização (Linha 156):**
```python
def __init__(
    self,
    login: int,
    password: str,
    server: str,
    timeout: int = 60000,
    terminal_exe_path: Optional[str] = None,  # ← Parâmetro RECEBIDO
):
    self.login = login
    self.password = password
    self.server = server
    self.timeout = timeout
    self.terminal_exe_path = terminal_exe_path  # ← Armazenado...
```

**Mas em `_connect_single()` (Linha 387):**
```python
def _connect_single(self) -> bool:
    try:
        import MetaTrader5 as mt5
        self._mt5 = mt5

        # ❌ PROBLEMA: Não usa self.terminal_exe_path!
        if not mt5.initialize():  # Sem argumento de path
            raise BrokerConnectionError(...)
```

**Deveria ser:**
```python
# ✅ SOLUÇÃO: Passar path ao initialize
if not mt5.initialize(path=self.terminal_exe_path):
    raise BrokerConnectionError(...)
```

---

### 6. CONFERÊNCIA COM A DOCUMENTAÇÃO OFICIAL MT5

```python
# API de MetaTrader5 (Python package documentation)

mt5.initialize(path=None, login=None, password=None, server=None, timeout=None,
               portable=False)

# Parâmetros:
# path (str) – caminho para o executável terminal64.exe ou terminal.exe
#   Se None, tenta encontrar o MT5 automaticamente
#   PROBLEMA: ↑ Encontra qualquer terminal MT5 instalado!
#
# login (int) – número da conta de trading
# password (str) – senha
# server (str) – nome do servidor
```

**Implicação:** Se não passar `path`, a biblioteca usa um mecanismo automático que **não garante qual terminal será selecionado quando há múltiplas instalações**.

---

## ✅ SOLUÇÃO - PROPOSTA

### R1: Usar `path` no `initialize()`

**Arquivo:** `src/infrastructure/adapters/mt5_adapter.py` (Linha 389)

```python
# ANTES (❌ ERRADO):
if not mt5.initialize():
    raise BrokerConnectionError(...)

# DEPOIS (✅ CORRETO):
if not mt5.initialize(path=self.terminal_exe_path):
    raise BrokerConnectionError(...)
```

**Impacto:**
- ✅ Força conexão ao terminal específico
- ✅ Elimina incerteza de qual terminal
- ✅ Funcionará com múltiplos terminais MT5 instalados
- ⏱️ Esforço: 10 minutos (uma linha)

---

### R2: Aprimorar Validação - Verificar Antes de Conectar

Adicionar verificação prévia do path:

```python
def _connect_single(self) -> bool:
    import os

    # ✅ Validar que path existe ANTES de conectar
    if self.terminal_exe_path:
        if not os.path.isfile(self.terminal_exe_path):
            raise BrokerConnectionError(
                f"Terminal executable not found: {self.terminal_exe_path}\n"
                f"Verifique o MT5_TERMINAL_PATH em .env"
            )

    # Então conecta com path específico
    try:
        import MetaTrader5 as mt5
        self._mt5 = mt5

        if not mt5.initialize(path=self.terminal_exe_path):  # ✅ USA PATH
            raise BrokerConnectionError(...)
```

**Impacto:**
- ✅ Fail-fast se configuração errada
- ✅ Mensagem clara para o usuário
- ⏱️ Esforço: 15 minutos

---

### R3: Melhorar Feedback no Monitor

Atualizar `MONITOR_OPERADOR.bat` para mostrar:

```
════════════════════════════════════════════════════════════
 🔒 ISOLAMENTO DE TERMINAL (S2-5)
════════════════════════════════════════════════════════════

Terminal Esperado:  C:\Program Files\Clear Investimentos MT5...
Terminal Conectado: [mostrar qual realmente conectou]
Login Esperado:     1000346516
Login Atual:        [mostrar qual está logado]
Status:             ✅ HEALTHY vs ❌ VIOLATION

[Se VIOLATION]
Recomendação: Feche os outros terminais MT5 ou resete .env
```

**Impacto:**
- ✅ Visibilidade em tempo real
- ✅ Diagnóstico mais rápido
- ⏱️ Esforço: 20 minutos

---

## 📋 CRONOGRAMA DE IMPLEMENTAÇÃO

| Item | Responsável | Duração | Prioridade |
|------|------------|---------|-----------|
| R1: Fix `initialize(path=...)` | Eng Sr | 10 min | 🔴 HOJE |
| R2: Validação de path | Eng Sr | 15 min | 🔴 HOJE |
| R3: Monitor feedback | Dev-Frontend | 20 min | 🟡 27/02 |
| **Total** | | **45 min** | **HOJE** |

---

## 🎯 IMPACTO

### Antes (Status Atual)
- ❌ Violação recorrente de isolamento
- ❌ Operador em HALT cíclico
- ❌ Necessita reconexão manual frequente
- ⚠️ Uptime reduzido

### Depois (Pós-Fix)
- ✅ Sempre conecta ao terminal CORRETO
- ✅ Eliminação de violações
- ✅ Uptime próximo a 100%
- ✅ Operador pode deixar rodando 8h sem intervenção

---

## 📊 TIMELINE PARA IMPLEMENTAÇÃO

**27/02 09:00-09:45:** Dev executa fix R1 + R2
**27/02 10:00:** Deploy em produção
**27/02 14:00-15:00:** Dev-Frontend executa R3
**27/02 17:00:** ✅ Completamente resolvido

---

## 🔐 SEGURANÇA

**Status atual:** ✅ **SEGURO**
- Sistema **detecta** violação
- Sistema **aborta** (não envia ordem errada)
- Sistema **aguarda** reconexão correta

**Após fix:** ✅ **MAIS SEGURO + CONFIÁVEL**
- Sistema **previne** violação
- Sistema **força** terminal correto
- Sistema **valida** antes de conectar

---

## 📞 CONVOCAÇÃO DO BOARD

### Personas Convocadas:

| ID | Persona | Responsabilidade | Status |
|---|---------|-----------------|--------|
| 3 | Eng Sr | Implementar R1 + R2 | 🟢 Ready |
| 6 | Arquiteto | Validar segurança | 🟢 Ready |
| 7 | DevOps | Monitor produção pós-fix | 🟢 Ready |
| 5 | Risk Officer | Assinar resolução | 🟡 Aguardando análise |
| 1 | Presidente | Aprovar cronograma | 🟡 Aguardando análise |

### Decisão Requerida:
✅ **Aprovar implementação de R1 + R2 HOJE (27/02) antes do GATE 1**

---

## 📎 ANEXOS

### A. Arquivos a Modificar

1. **`src/infrastructure/adapters/mt5_adapter.py`**
   - Linha 389: Adicionar `path=self.terminal_exe_path` ao `mt5.initialize()`
   - Linha 370-380: Adicionar validação de path

2. **`MONITOR_OPERADOR.bat` (ou script equivalente)**
   - Adicionar seção de visualização de isolamento

### B. Códigos Referência

**Antes:**
```python
if not mt5.initialize():
```

**Depois:**
```python
if not mt5.initialize(path=self.terminal_exe_path):
```

### C. Testes

Já existem testes em:
- `tests/unit/test_mt5_terminal_isolation.py` ✅

Adicionar teste de múltiplos terminais:
```python
def test_initializes_with_correct_path(self):
    """Garante que MT5 inicializa com path específico"""
    adapter = MT5Adapter(
        login=1000346516,
        password="...",
        server="Clear MT5 - Live",
        terminal_exe_path="C:\\Program Files\\Clear Investimentos MT5 Terminal\\terminal64.exe"
    )
    adapter.connect()
    assert adapter._session_fingerprint["account_login"] == 1000346516
```

---

## ✍️ ASSINATURA PELA AUDITORIA

**Auditor Técnico:** GitHub Copilot - Infrastructure Review
**Data:** 27 Feb 2026 14:45 BRT
**Severidade:** 🔴 CRÍTICO (Recorrente, identifiable, fixable)
**Recomendação:** ✅ **FIX IMEDIATAMENTE**

---

**Próxima Reunião:** 27/02 15:00 BRT (após execução do fix)
