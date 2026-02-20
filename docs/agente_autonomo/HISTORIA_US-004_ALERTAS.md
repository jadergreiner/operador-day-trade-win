# 📬 História de Usuário - US-004: Alertas Automáticos em Tempo Real

**ID:** US-004
**Versão:** 1.0.0
**Data de Criação:** 20/02/2026
**Prioridade:** 🔴 CRÍTICA
**Sprint de Entrega:** v1.1.0 (13/03/2026)
**Esforço Estimado:** 13 pontos (1 sprint)
**Status:** ✅ REFINADA e APROVADA (20/02/2026)
**Aprovação:** Head de Finanças + PO + Dev Lead

---

## 📝 Narrativa

### Como Operador de Trading

Eu quero receber alertas automáticos sobre oportunidades de trading

### Para que

Eu possa executar operações com **latência mínima** e capitalizar
oportunidades antes da difusão no mercado

---

## ✅ Critérios de Aceitação

### AC-001: Detecção de Padrão

```gherkin
Dado um padrão de volatilidade extrema (>2σ)
Quando o padrão é detectado no fluxo de análise
Então um alerta é gerado em <30 segundos
```

### AC-002: Entrega Multicanal (v1.1)

```gherkin
Dado um alerta gerado
Quando está configurado para envio
Então recebo notificação em:
  ✅ Push (WebSocket local) - PRIMARY <500ms
  ✅ Email (SMTP) - BACKUP <8s (async)

  ⚠️ SMS (Twilio): DESATIVADO em v1.1
  📅 Habilitação: v1.2 (se email falhar > 2%)
```

### AC-003: Conteúdo do Alerta

```gherkin
Dado um alerta de oportunidade
Então a mensagem contém:
  • [CRÍTICO] Status de alerta
  • Oportunidade: ativo + padrão
  • Preço atual (UTM)
  • Nível de entrada recomendado
  • Stop Loss automático
  • Relação Risk:Reward (ex: 1:2.5)
  • Timestamp (MS precision)
  • Link para análise completa
```

### AC-004: Controle de Taxa (Deduplicação Strict)

```gherkin
Dado um fluxo de alertas
Quando múltiplos alertas do mesmo padrão ocorrem
Então sistema implementa:
  • Rate limiting: máx 1 alerta/padrão/minuto (STRICT)
  • Deduplicação: consolidar sinais >90% similares
  • Consolidação: máx 3 alertas simultâneos
  • Backpressure: não descartar dados, fila ordenada

Performance SLA:
  • P50 (mediana): <15 segundos
  • P95 (nosso alvo): <30 segundos ✅
  • P99 (contingência): <50 segundos
```

### AC-005: Logging e Auditoria

```gherkin
Dado todo alerta gerado
Então registro contém:
  ✅ ID único (UUID)
  ✅ Timestamp origem
  ✅ Canal de entrega
  ✅ Status (enviado/falha)
  ✅ Latência medida
  E é consultável por: data, padrão, canal
```

---

## 🏗️ Requisitos Técnicos

### RQ-001: Arquitetura de Alertas

#### Componentes

1. **Detection Engine** (analytics agora, detector novo)
2. **Alert Formatter** (estrutura padrão)
3. **Delivery Manager** (multi-canal)
4. **Queue System** (Redis ou file-based)
5. **Audit Log** (SQLite append-only)

#### Fluxo

```plaintext
Data IN → [Detection] → [Format] → [Queue] → [Delivery] → OUT
          ↓ (rules)     ↓ (tmpl)    ↓ (prio)    ↓ (chan)
        Triggers      Message      Ready    Email/SMS/Push
```

### RQ-002: Integração com BDI

- Reusa estrutura de `CapturaDia` do `fechamento_diario.py`
- Nova classe: `AlertaOportunidade` (dataclass)
- Estende `AGENTE_AUTONOMO_BACKLOG.md` com regras de alerta

### RQ-003: Canais de Entrega (v1.1 MVP)

#### Push (WebSocket local) - PRIMARY ⭐

- Endpoint: `ws://localhost:8765/alertas`
- Latência: <500ms (sub-segundo, tempo real)
- Autenticação: token Bearer
- Formato: JSON estruturado
- Reconexão automática com exponential backoff
- Fallback automático se falhar

#### Email (SMTP) - BACKUP Redundante ✅

- Provider: SendGrid (recomendado) ou Postmark
- Template: HTML com styling Bootstrap
- Latência: 2-8 segundos (async paralelo)
- Retry: exponencial (1s, 2s, 4s, até 60s)
- Timeout: 10s máximo
- Evidência permanente (compliance CVM)
- Sempre tenta (nunca ignora falhas)

#### SMS (Twilio) - v1.2 OPCIONAL 📅

- Status: DESATIVADO em v1.1
- Habilitação: v1.2 (condicional)
- Critério: se email falha > 2% em 30 dias
- Account SID: variável de ambiente
- Message: máximo 160 caracteres
- Timeout: 5s
- Custo: ~R$ 0.35/SMS (revisar em v1.2)

### RQ-004: Configuração

```yaml
# config/alertas.yaml (novo)
alertas:
  enabled: true
  detection_window: 60  # segundos
  channels:
    email:
      enabled: true
      provider: smtp
      from: bot@trading.local
      retry_max: 3
    sms:
      enabled: true
      provider: twilio
      retry_max: 3
    websocket:
      enabled: true
      url: ws://localhost:8765
      retry_max: -1  # infinito
  rules:
    volatilidade_extrema:
      threshold_sigma: 2.0
      alert_level: CRÍTICO
    oportunidade_padrao:
      setup_confidence: 0.8
      alert_level: ALTO
    divergencia_indicador:
      alert_level: MÉDIO
```

### RQ-005: Testes

#### Unit Tests (target: 8 testes)

- [ ] `test_detector_identifica_volatilidade_extrema()`
- [ ] `test_alertformatter_gera_html_valido()`
- [ ] `test_delivery_email_com_retry()`
- [ ] `test_delivery_sms_com_limite_caracteres()`
- [ ] `test_queue_deduplicacao_alerts()`
- [ ] `test_rate_limiting_falha_corretamente()`
- [ ] `test_audit_log_registra_completo()`
- [ ] `test_config_validation()`

#### Integration Tests (target: 3 testes)

- [ ] `test_fluxo_completo_volatilidade_ate_email()`
- [ ] `test_fluxo_completo_volatilidade_ate_sms()`
- [ ] `test_fluxo_completo_volatilidade_ate_websocket()`

#### Performance Tests

- [ ] Latência end-to-end: <30s (95 percentil)
- [ ] Throughput: 100+ alertas/minuto
- [ ] Memory: <50MB steady state

---

## 📋 Tarefas de Implementação

### Fase 1: Fundação (Sprint v1.1, semana 1)

- [ ] **[TASK-001]** Criar `AlertaOportunidade` dataclass
  - Arquivo: `src/alertas/modelo.py`
  - Esforço: 1pt
  - Dependência: nenhuma

- [ ] **[TASK-002]** Implementar Detection Engine
  - Arquivo: `src/alertas/detector.py`
  - Métodos: `detectar_volatilidade()`, `detectar_padrao()`
  - Esforço: 3pt
  - Dependência: TASK-001

- [ ] **[TASK-003]** Implementar Alert Formatter
  - Arquivo: `src/alertas/formatter.py`
  - Templates: email HTML, SMS text
  - Esforço: 2pt
  - Dependência: TASK-001

### Fase 2: Entrega (Sprint v1.1, semana 2)

- [ ] **[TASK-004]** Implementar Delivery Manager
  - Arquivo: `src/alertas/delivery.py`
  - Canais: email, SMS, websocket
  - Esforço: 5pt
  - Dependência: TASK-003

- [ ] **[TASK-005]** Implementar Queue e Rate Limiting
  - Arquivo: `src/alertas/fila.py`
  - Deduplicação e preservação de ordem
  - Esforço: 3pt
  - Dependência: TASK-001

- [ ] **[TASK-006]** Implementar Audit Log
  - Arquivo: `src/alertas/auditoria.py`
  - SQLite append-only e índices
  - Esforço: 2pt
  - Dependência: TASK-004, TASK-005

### Fase 3: Testes e Integração (Sprint v1.1, semana 3)

- [ ] **[TASK-007]** Unit Tests (8 testes)
  - Arquivo: `tests/test_alertas_unit.py`
  - Esforço: 3pt
  - Dependência: TASK-002 até TASK-006

- [ ] **[TASK-008]** Integration Tests (3 testes)
  - Arquivo: `tests/test_alertas_integration.py`
  - Esforço: 3pt
  - Dependência: TASK-004, TASK-005, TASK-006

- [ ] **[TASK-009]** Integração com BDI existente
  - Arquivo: `src/processador_bdi.py` (modificar)
  - Hook: ao gerar oportunidade, enviar para detector
  - Esforço: 2pt
  - Dependência: TASK-004

### Fase 4: Configuração e Documentação (Sprint v1.1, semana 4)

- [ ] **[TASK-010]** Criar `config/alertas.yaml`
  - Template com valores padrão
  - Validação de schema
  - Esforço: 1pt
  - Dependência: nenhuma (paralelo)

- [ ] **[TASK-011]** Documentação de API
  - Arquivo: `docs/ALERTAS_API.md`
  - Exemplos de uso e troubleshooting
  - Esforço: 2pt
  - Dependência: TASK-004

- [ ] **[TASK-012]** Sincronização de documentação
  - Atualizar: `AGENTE_AUTONOMO_FEATURES.md`
  - Atualizar: `AGENTE_AUTONOMO_ROADMAP.md` (v1.1)
  - Atualizar: `SYNC_MANIFEST.json`
  - Esforço: 1pt
  - Dependência: TASK-011

---

## 📊 Definição de Pronto

Antes de marcar como **CONCLUÍDO**, todos os critérios abaixo devem
estar em 100% GREEN:

- [ ] **Funcionalidade:** Todos os AC (AC-001 a AC-005) atendidos
- [ ] **Testes:** 11/11 testes passando (8 unit e 3 integration)
- [ ] **Cobertura:** ≥80% de cobertura de código
- [ ] **Performance:** Latência <30s (95 percentil)
- [ ] **Documentação:** API docs e README de configuração
- [ ] **Sincronização:** SYNC_MANIFEST atualizado e checksums OK
- [ ] **Lint:** Markdown sem erros (pymarkdown scan)
- [ ] **Commits:** Mensagens em português e UTF-8 válido
- [ ] **Code Review:** Aprovado por 2 reviewers
- [ ] **Release Notes:** Entrada em CHANGELOG incluída

---

## 💰 Refinamento Head de Finanças (20/02/2026)

### Aprovações de Negócio

| Aspecto | Status | Decisão |
|---------|--------|---------|
| **SLA 30s viável?** | ✅ APROVADO | Não menos que 30s (ROI -R$ 720k/mês) |
| **Canal primário?** | ✅ APROVADO | Push PRIMARY + Email BACKUP (SMS v1.2) |
| **Capital inicial?** | ✅ APROVADO | Ramp-up 50k → 80k → 150k (condicional) |
| **Manual ou Auto?** | ✅ APROVADO | Manual v1.1 (Automático v1.2 + Board) |
| **Timeline?** | ✅ APROVADO | 4 Fases: Beta → Prod → Normal → Auto |

### Capital Ramp-Up (Obrigatório)

```yaml
FASE 1: BETA (Semana 1-2, 13-27 mar)
  Capital/Trade: R$ 50.000 (10% AUM)
  Capital diário máx: R$ 400k (8 trades)
  Drawdown máx: -R$ 40k (-10%)
  Saída: Win rate ≥ 60%?
  └─ ✅ SIM → avança FASE 2

FASE 2: PRODUÇÃO RESTRITA (Semana 3-4, 27 mar-13 abr)
  Capital/Trade: R$ 80.000 (16% AUM)
  Capital diário máx: R$ 640k (8 trades)
  Drawdown máx: -R$ 64k (-10%)
  Saída: Win rate ≥ 65%?
  └─ ✅ SIM → avança FASE 3

FASE 3: PRODUÇÃO NORMAL (Mês 2+, 13 abr+)
  Capital/Trade: R$ 150.000 (30% AUM)
  Capital diário máx: R$ 1.5M (10 trades)
  Drawdown máx: -R$ 150k (-10%)
  Saída: 30 dias estável + compliance OK?
  └─ ✅ SIM → FASE 4 (v1.2)

FASE 4: AUTOMÁTICO OPCIONAL (v1.2, 13 mai+)
  Status: FUTURO (fora v1.1)
  Requisito: Board approval + Legal sign-off
```

### Gatilhos de Redução (Automático)

```
If win_rate_7d < 60% → volta R$ 50k
If drawdown_atual < -8% → FREEZE (nenhum trade)
If volatilidade > 3σ → reduz capital -20%
```

### Operação: Manual v1.1

```
v1.1 GO-LIVE (13 MARÇO 2026):
  ✅ Execução: MANUAL 100%
     └─ Operador decide se clica ou não
  ✅ Responsabilidade: Claro (operador está no controle)
  ✅ Auditoria: Rastreada cada ação (CVM compliant)

v1.2 (13 MAIO 2026) - FUTURO:
  📅 Automático: Opcional
  📅 Escopo: Apenas WIN$N + micro capital (R$ 50k)
  📅 Aprovação: CEO + CFO + CRO
  📅 Compliance: Novo review cycle
```

### KPIs de Aprovação

```yaml
FASE 1 (BETA):
  target_win_rate: ≥ 60%
  target_latency_p95: < 40s
  target_system_crashes: 0
  target_audit_recovery: 100%

FASE 2 (PROD_RESTRITA):
  target_win_rate: ≥ 65%
  target_capital_ramp: 50k → 80k → 150k
  target_deduplication: > 95%
  target_email_delivery: > 98%

FASE 3 (PROD_NORMAL):
  target_win_rate: ≥ 65% (sustentável)
  target_monthly_pnl: +R$ 50-80k
  target_drawdown: < -10%
  target_uptime: 99.5%

POST-DEPLOY (30 dias):
  target_roi_vs_dev_cost: > 2.0x
  target_compliance_violations: 0
```

---

## 🔄 Sincronização de Documentação (OBRIGATÓRIA)

Ao finalizar esta história, os seguintes documentos DEVEM ser atualizados:

- [ ] AGENTE_AUTONOMO_FEATURES.md (adicionar ✅ Alertas v1.1)
- [ ] AGENTE_AUTONOMO_ROADMAP.md (confirmar v1.1 timeline 13/03)
- [ ] AGENTE_AUTONOMO_RELEASE.md (detalhar v1.1 incluído)
- [ ] AGENTE_AUTONOMO_BACKLOG.md (mover para "Em Andamento")
- [ ] SYNC_MANIFEST.json (atualizar checksums)
- [ ] VERSIONING.json (registrar v1.1 features)
- [ ] README.md (mencionar alertas como feature v1.1)

---

## 🎨 Design da Mensagem de Alerta

### Exemplo: Email (HTML)

```html
Subject: [CRÍTICO] Oportunidade WINFUT - Volatilidade Extrema

---

🚨 ALERTA DE OPORTUNIDADE

📊 Padrão: Volatilidade Extrema (2.3σ)
🔹 Ativo: WINFUT
💰 Preço Atual: 89.250
🎯 Entrada: 89.100 - 89.300
🛑 Stop Loss: 88.800
🎲 Risk:Reward: 1:2.5

⏰ Timestamp: 2026-02-20T14:23:45.123Z
ID Alerta: alrt_abc123xyz

[Ver Análise Completa]

---
Gerenciado por: Agente Autônomo v1.1
```

### Exemplo: SMS

```plaintext
[CRÍTICO] WINFUT 89.250 | E: 89.100-300 | SL: 88.800 |
R:1 Rw:2.5 | https://app.local/alrt_abc123xyz
```

### Exemplo: WebSocket (JSON)

```json
{
  "id": "alrt_abc123xyz",
  "nivel": "CRÍTICO",
  "ativo": "WINFUT",
  "padrao": "volatilidade_extrema",
  "preco_atual": 89.250,
  "entrada_min": 89.100,
  "entrada_max": 89.300,
  "stop_loss": 88.800,
  "risk_reward": "1:2.5",
  "timestamp": "2026-02-20T14:23:45.123Z"
}
```

---

## 🔗 Dependências e Sincronização

### Documentos a atualizar

#### 1. AGENTE_AUTONOMO_FEATURES.md

- Adicionar: `✅ Alertas automáticos (v1.1)`
- Mover de `⏳ Análise Técnica` para `✅ Gerenciamento de Alertas`

#### 2. AGENTE_AUTONOMO_ROADMAP.md

- v1.1.0 (13/03): Adicionar "Alertas automáticos (email/SMS/push)"

#### 3. SYNC_MANIFEST.json

- Adicionar: `HISTORIA_US-004_ALERTAS.md`
- Atualizar: checksums de arquivos modificados

#### 4. AGENTE_AUTONOMO_BACKLOG.md

- Mover de `⏳ Próximas` para `🔄 Em Andamento`

#### 5. AGENTE_AUTONOMO_CHANGELOG.md

- Adicionar entrada v1.1.0 com este feature

---

## 📞 Perguntas para Refinamento

### Validação com Stakeholders

1. **Prioridade de canais:** Email > SMS > WebSocket?
2. **SLA de latência:** 30s é aceitável ou precisa <10s?
3. **Volume esperado:** Quantos alertas/dia em produção?
4. **Integração externa:** Conectar com sistemas de execução?
5. **Mobile:** Precisamos de app nativa ou web é suficiente?

---

## 📚 Referências

- [x] Baseado em: US-004 (AGENTE_AUTONOMO_HISTORIAS.md)
- [x] Alinhado com: AGENTE_AUTONOMO_FEATURES.md v1.0
- [x] Roadmap: v1.1.0 (13/03/2026)
- [x] Sprint: Sprint 1 (Março 2026)
- [x] Closure: AGENTE_AUTONOMO_RELEASE.md

---

**Status:** 📋 PRONTA PARA REFINAMENTO COM ANALISTA

**Próximo Passo:** Planning poker e identificação de riscos

**Data de Espera:** 20/02/2026 10h30m
