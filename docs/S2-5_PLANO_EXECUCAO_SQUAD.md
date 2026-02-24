<!-- pyml disable md013 -->

# 🔒 S2-5: Plano de Execução Paralela — Squad Multidisciplinar

**Prioridade:** 🔴 MÁXIMA (Prioridade 0)
**Sprint:** Sprint 2 (24/02 - 28/02/2026)
**Status:** 🟡 EM ANDAMENTO
**Última Atualização:** 2026-02-24T18:45:00Z

---

## 📋 RESUMO EXECUTIVO

**Objetivo:** Implementar isolamento obrigatório de terminal MT5 para garantir
que o operador conecte sempre à conta e terminal corretos, com retry automático
após desconexão e validação contínua de integridade.

**Entrega Esperada:** 28/02/2026 (4.5 dias de desenvolvimento paralelo)
**Risco Eliminado:** Ordem enviada para conta/terminal errado
**Impacto:** Reduz tempo de recovery de ~5min (manual) para ~20s (automático)

---

## 🎯 SQUAD MULTIDISCIPLINAR ALOCADA

| # | Persona | Role | Alocação | Tarefas |
|---|---------|------|----------|---------|
| **3** | Eng Sr | Arquiteto + Dev | 40h | Impl. MT5Adapter + Retry logic |
| **6** | Arq. Sistemas | Lead Técnico | 30h | Design + Integrate health checks |
| **4** | ML Expert | Support (contingência) | 5h | Testes e validação |
| **7** | Infra DevOps | Integração .bat | 10h | MONITOR_OPERADOR.bat + CI/CD |
| **12** | QA Automation | Test Lead | 25h | Testes + Coverage |
| **8** | Head Docs & Stds | Standards | 8h | Lint + Documentação |
| **14** | Product Owner | Validação AC | 5h | Sign-off de AC |
| **17** | Doc Advocate | Sync docs | 5h | Atualizar SYNC_MANIFEST |

**Total:** 128h em paralelo (efetivamente ~32h de caminho crítico)

---

## 📅 TIMELINE PARALELA (4.5 dias)

### 🟢 Dia 1 (24/02 - 14h-23h): DESIGN + PROTOTIPAGEM

```bash
Paralelo:
├─ Eng Sr (8h)          → Análise código mt5_adapter.py existente
├─ Arq. Sistemas (8h)   → Design isolamento + fluxo de retry
├─ QA (6h)              → Planejar strategy de testes
├─ DevOps (3h)          → Analisar MONITOR_OPERADOR.bat atual
├─ Docs (2h)            → Preparar template docstring
└─ Sync result: Design Document

Resultado esperado:
✅ Protótipo de interfaces de isolamento
✅ Strategy de testes definida
✅ Diagramas de fluxo de retry
```

### 🟡 Dia 2 (25/02 - 08h-20h): IMPLEMENTAÇÃO CORE

```bash
Paralelo:
├─ Eng Sr (10h)         → MT5Adapter terminalIsolation() + retry
├─ Arq. Sistemas (8h)   → MT5IsolationHealthCheck + persistência
├─ QA (8h)              → Escrever test fixtures + mocks
├─ DevOps (4h)          → Setup CI/CD para novos testes
└─ Docs (2h)            → Documentar código enquanto escreve

Resultado esperado:
✅ Código core 90% feito
✅ Testes unitários estruturados
✅ Health check integrado
```

### 🟠 Dia 3 (26/02 - 08h-20h): TESTES + INTEGRAÇÃO

```bash
Paralelo:
├─ Eng Sr (8h)          → Refinamento + edge cases
├─ QA (10h)             → Executar testes + buscar bugs
├─ Arq. Sistemas (6h)   → Validar isolamento em múltiplas instâncias
├─ DevOps (2h)          → Integrar a MONITOR_OPERADOR.bat
└─ Docs (2h)            → Lint + correção documentação

Resultado esperado:
✅ Todos os 9 testes unitários PASSING
✅ Coverage >98% de isolation logic
✅ Múltiplas instâncias MT5 testadas
```

### 🔵 Dia 4 (27/02 - 08h-18h): INTEGRAÇÃO E2E

```bash
Paralelo:
├─ Eng Sr (6h)          → Integração no INICIAR_MICRO_TENDENCIA_AUTO_TRADE.bat
├─ Arq. Sistemas (4h)   → Validar fluxos de desconexão/retry
├─ QA (4h)              → Testes E2E + regression
├─ DevOps (3h)          → Deploy teste em staging
├─ Infra (2h)           → Health check no MONITOR_OPERADOR.bat visual
└─ Data Eng (2h)        → Audit trail logging

Resultado esperado:
✅ .bat operional com validação de isolamento
✅ Health check ativo e visível
✅ Retry automático funcionando
```

### 🎯 Dia 5 (28/02 - 08h-14h): VALIDAÇÃO + COMMIT

```bash
Sequencial (caminho crítico):
├─ QA (2h)              → Validações finais (AC checklist)
├─ Produtos Owner (1h)  → Sign-off de AC (10/10 ✅)
├─ Docs (1h)            → Limpeza final + lint
├─ Eng Sr (1h)          → Commit + CHANGELOG
└─ Doc Advocate (1h)    → Sync MANIFEST + ROADMAP

Resultado esperado:
✅ Commit com 10/10 AC PASSED
✅ Documentação sincronizada
✅ Deploy pronto para produção
```

---

## 🔧 TAREFAS DETALHADAS POR PERSONA

### 👨‍💻 ENG SR (40h total)

#### Tarefa EngSr-1 (8h): Análise + Design | 24/02

1. Ler MT5Adapter atual em `src/infrastructure/adapters/mt5_adapter.py`
2. Identificar pontos de integração para isolamento
3. Desenhar fluxo de retry com backoff exponencial
4. Design de persistência de fingerprint (JSON)
5. Output: Proposal documento com pseudo-código

#### Tarefa EngSr-2 (12h): Implementação MT5Adapter | 25-26/02

```python
# Adicionar ao MT5Adapter:
- __init__: parameter terminal_exe_path
- _validate_terminal_isolation(): bool
- _save_session_fingerprint(): None
- connect(max_retries=3, backoff_seconds=[5,10,20]): bool
- _ensure_connected_with_isolation(): None
- is_trading_halted(): bool
```

#### Tarefa EngSr-3 (8h): Integração .bat | 27/02

1. Testar INICIAR_MICRO_TENDENCIA_AUTO_TRADE.bat com novo código
2. Validar que isolamento é validado antes de send_order()
3. Testar desconexão simulated + retry automático
4. Verificar que HALT trader quando retry exauria

#### Tarefa EngSr-4 (6h): Refinamento | 26-27/02

1. Edge cases: terminal_exe_path = None (usar primeiro terminal64.exe)
2. Edge cases: PID muda (validar exe_path alternativamente)
3. Error handling robusto
4. Logging estruturado (DEBUG, INFO, WARNING, ERROR, CRITICAL)

#### Tarefa EngSr-5 (6h): Documentação inline | Paralelo

- Docstrings em cada método (português)
- Inline comments para lógica complexa
- Type hints completos (100%)
- Examples em docstring

---

### 🏗️ ARQ. SISTEMAS (30h total)

#### Tarefa ArqSys-1 (8h): Design Técnico | 24/02

1. Diagrama de sequência: conexão → validação → operação
2. Diagrama de sequência: desconexão → retry → halt
3. Design de persistência da sessão
4. Design de health check integrado
5. Output: Diagramas + documento de design

#### Tarefa ArqSys-2 (10h): MT5IsolationHealthCheck | 25-26/02

```python
# Criar em src/infrastructure/monitoring/health_checker.py
class MT5IsolationHealthCheck:
    - __init__(adapter: MT5Adapter, check_interval_sec: int = 30)
    - check_health(): dict
    - get_status_report(): str  # Para MONITOR_OPERADOR.bat
```

#### Tarefa ArqSys-3 (6h): Persistência + State | 26/02

1. Implementar ~/.mt5_operator_session.json
2. Carregar fingerprint ao iniciar (graceful degradation)
3. Validar integridade do arquivo JSON
4. Logging de alterações de fingerprint

#### Tarefa ArqSys-4 (4h): Audit Trail | 27/02

1. Registrar cada validação de isolamento
2. Registrar cada event de reconnect (sucesso/falha)
3. Registrar cada HALT event
4. Format: timestamp | event_type | status | details

#### Tarefa ArqSys-5 (2h): Sync & Review | 28/02

1. Code review da implementação EngSr
2. Validar alinhamento com ARCHITECTURE.md
3. Sign-off técnico

---

### 🧪 QA AUTOMATION (25h total)

#### Tarefa QA-1 (6h): Strategy de Testes | 24/02

1. Ler S2-5_MT5_TERMINAL_ISOLATION.md (test cases)
2. Expandir com edge cases adicionais
3. Criar matriz de cobertura (9+ test cases)
4. Definir fixtures e mocks necesários
5. Output: test_mt5_terminal_isolation.py estrutura

#### Tarefa QA-2 (10h): Implementação Testes | 25-26/02

```python
# tests/unit/test_mt5_terminal_isolation.py

Testes obrigatórios:
✓ test_fingerprint_validation_success
✓ test_fingerprint_validation_wrong_account
✓ test_fingerprint_validation_terminal_crashed
✓ test_reconnect_retry_exponential_backoff
✓ test_reconnect_exhausted_halts_trading
✓ test_multiple_mt5_instances_isolation
✓ test_health_check_detects_disconnection
✓ test_session_persistence_on_restart
✓ test_sanitization_of_credentials_in_logs

Cada teste: verbose em português, CASE-THEN-WHEN
```

#### Tarefa QA-3 (4h): Execution + Reports | 26-27/02

1. Rodar pytest com coverage: `coverage run -m pytest tests/unit/test_mt5_terminal_isolation.py`
2. Validar coverage >98% de isolation logic
3. Gerar relatório HTML de coverage
4. Buscar flaky tests

#### Tarefa QA-4 (3h): Regression Testing | 27/02

1. Rodar suite inteira: `pytest tests/unit/ -q`
2. Validar que nenhum teste anterior quebrou
3. Performance check: latência P95 continua <500ms
4. Report: PASSOU/FALHOU

#### Tarefa QA-5 (2h): AC Validation | 28/02

1. Checklist dos 10 AC do S2-5_MT5_TERMINAL_ISOLATION.md
2. Verificação manual (manual test cases se necessário)
3. Gerar relatório de AC de sign-off

---

### 🔧 INFRA DEVOPS (10h total)

#### Tarefa DevOps-1 (3h): Análise MONITOR_OPERADOR.bat | 24/02

1. Ler MONITOR_OPERADOR.bat atual
2. Identificar onde colocar MT5 Isolation Status
3. Design de UI textual (template)
4. Output: Mock-up do painel

#### Tarefa DevOps-2 (3h): Implementação Visual | 25-26/02

1. Criar função `display_mt5_isolation_status()` em Python ou PowerShell
2. Integrar ao .bat principal
3. Atualizar a cada 30s (ou on-demand)
4. Cores: 🟢 (healthy), 🟡 (warning), 🔴 (critical)

#### Tarefa DevOps-3 (2h): CI/CD Setup | 26/02

1. Adicionar novo teste ao pipeline CI
2. Validar que pytest corre em cada commit
3. Bloquear merge se coverage <98%

#### Tarefa DevOps-4 (2h): Deployment | 27/02

1. Deploy para staging
2. Smoke test no .bat
3. Validar que retry funciona em staging

---

### 📝 HEAD DOCS & STANDARDS (8h total)

#### Tarefa Docs-1 (3h): Lint + Standards | 24/02

1. Template de docstring para isolamento features
2. Style guide para logging messages
3. Verificar SE existe pyproject.toml (pylint, mypy config)
4. Setup pre-commit hooks

#### Tarefa Docs-2 (3h): Documentação | Paralelo com dev

1. Atualizar ARCHITECTURE.md com seção de isolamento
2. Atualizar SOLUTION_DESIGN.md (se existe)
3. Criar/atualizar docstrings (português)
4. Exemplos de usage

#### Tarefa Docs-3 (2h): Lint Final | 28/02

1. Rodar `pymarkdown scan docs/S2-5_*.md`
2. Corrigir MD013 (line length) e outros warnings
3. GIT não permite commit se lint fallhar

---

## 🎯 ACCEPTANCE CRITERIA (AC) - CHECKLIST

### AC-1: Terminal PID Validado | 26/02

```bash
✓ Quando: Operador iniciado
"ENTÃO:" PID do terminal64.exe é capturado
"E:" armazenado em ~/.mt5_operator_session.json
```

### AC-2: Fingerprint Persistido | 26/02

```bash
✓ Quando: Conexão bem-sucedida ao MT5
"ENTÃO:" Fingerprint é salvo (PID, exe_path, login, server, timestamp)
"E:" arquivo surviva múltiplas execuções do .bat
```

### AC-3: Mismatch de Conta Rejeitado | 26/02

```bash
✓ Quando: Trader muda account login no MT5 durante operador rodando
"ENTÃO:" Próxima operação crítica é REJEITADA
"E:" Alerta de isolamento violation é logado
```

### AC-4: Retry Automático com Backoff | 25/02

```bash
✓ Quando: Desconexão detectada
"ENTÃO:" Tentativa 1 aguarda 5s
"E:" Tentativa 2 aguarda 10s
"E:" Tentativa 3 aguarda 20s
"E:" Log de cada tentativa
```

### AC-5: HALT Após 3 Falhas | 25/02

```bash
✓ Quando: Todos os 3 retries falharem
"ENTÃO:" Sistema entra em trading HALT
"E:" Nenhuma nova ordem é enviada
"E:" Alerta CRÍTICO disparado
```

### AC-6: Health Check a Cada 30s | 26/02

```bash
✓ Quando: Sistema rodando
"ENTÃO:" MT5IsolationHealthCheck executa a cada 30s
"E:" Detecta desconexões (PID morto, account mismatch)
"E:" Dispara reconnect automático
```

### AC-7: MONITOR_OPERADOR.bat Exibe Status | 27/02

```bash
✓ Quando: MONITOR_OPERADOR.bat rodando
"ENTÃO:" Seção "MT5 TERMINAL ISOLATION STATUS" visível
"E:" Mostra: PID ✓/✗, Account ✓/✗, Reconects count
"E:" Status: 🟢 HEALTHY | 🟡 WARNING | 🔴 FAILURE
```

### AC-8: Testes Unitários 100% Coverage | 26/02

```bash
✓ Quando: pytest tests/unit/test_mt5_terminal_isolation.py
"ENTÃO:" 9+ test cases PASSING
"E:" Coverage >98% (isolation logic)
"E:" Sem flaky tests (3x runs idêntico)
```

### AC-9: Documentação Completa | 28/02

```bash
✓ Quando: Código entregue
"ENTÃO:" Docstrings em 100% dos métodos (português)
"E:" Type hints completos
"E:" Exemplos em docstring
"E:" Lint PASSED (pymarkdown, pylint)
```

### AC-10: Nenhuma Ordem sem Validação | 26/02

```bash
✓ Quando: Operador enviando ordem
"ENTÃO:" Isolamento é validado ANTES de send_order()
"E:" Se mismatch, exception BrokerConnectionError
"E:" Ordem NUNCA é enviada em estado violado
```

---

## 🔗 ARQUIVOS A MODIFICAR

| Arquivo | Ação | Persona | Data |
|---------|------|---------|------|
| `src/infrastructure/adapters/mt5_adapter.py` | Modificar (adicionar métodos) | Eng Sr | 25/02 |
| `src/infrastructure/monitoring/health_checker.py` | Criar classe (ou adicionar) | Arq. Sistemas | 25/02 |
| `tests/unit/test_mt5_terminal_isolation.py` | Criar novo arquivo | QA | 25/02 |
| `MONITOR_OPERADOR.bat` (ou .ps1) | Modificar (adicionar seção) | DevOps | 26/02 |
| `docs/ARCHITECTURE.md` | Atualizar (diagrama + seção) | Docs | 26/02 |
| `docs/S2-5_PLANO_EXECUCAO_SQUAD.md` | Este arquivo (tracking) | Doc Advocate | Paralelo |
| `.github/workflows/test.yml` (se existe) | Modificar CI | DevOps | 26/02 |

---

## 📊 MÉTRICAS DE SUCESSO

| Métrica | Target | Status |
|---------|--------|--------|
| Timeline (4.5 dias) | ✅ | 📅 |
| Test Coverage (isolation) | >98% | 🧪 |
| AC Passed (10/10) | 100% | ✓ |
| Testes Unitários | 9+ PASSING | 🟢 |
| Code Review Approved | ✅ | 👀 |
| Documentação Lint | 0 errors | 🔍 |
| Produção Ready | YES | 🚀 |

---

## 🎯 PRÓXIMOS PASSOS

1. ✅ STATUS_ENTREGAS.md atualizado (24/02 18:45)
2. ✅ Squad Multidisciplinar alocada (este documento)
3. ⏳ **[AGORA] Kick-off paralelo:** Pessoal começa tarefas em paralelo
4. ⏳ Dia 1 (24/02 20h) → Deliverable: Design Document
5. ⏳ Dia 2-3 (25-26/02) → Deliverable: Código + Testes
6. ⏳ Dia 4 (27/02) → Deliverable: Integração E2E
7. ⏳ Dia 5 (28/02) → Deliverable: Commit + Go-Live Ready

---

## 📞 CONTATOS E ESCALONAMENTO

- **Lead Técnico:** Arquiteto de Sistemas (design + integration)
- **Lead Desenvolvimento:** Eng Sr (implementação core)
- **Lead QA:** QA Automation (testes + coverage)
- **Escalação:** Head de Finanças (se impasse)
- **Sync Docs:** Doc Advocate (15min daily standup)

---

## ✅ APROVAÇÃO

| Persona | Aprovação | Data |
|---------|-----------|------|
| Product Owner | ✅ | 24/02 |
| Tech Lead (Eng Sr) | ✅ | 24/02 |
| QA Lead | ✅ | 24/02 |
| DevOps | ✅ | 24/02 |
| Doc Advocate | ✅ | 24/02 |

**Status:** 🟢 **APROVADO PARA EXECUÇÃO PARALELA**

---

*Documento atualizado automaticamente a cada status change*
*Próxima sincronização: cada 12h ou on-demand*
