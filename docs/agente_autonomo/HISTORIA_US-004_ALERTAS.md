# 📬 História de Usuário - US-004: Alertas Automáticos em Tempo Real

**ID:** US-004  
**Versão:** 1.0.0  
**Data de Criação:** 20/02/2026  
**Prioridade:** 🔴 CRÍTICA  
**Sprint de Entrega:** v1.1.0 (13/03/2026)  
**Esforço Estimado:** 13 pontos (1 sprint)

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

### AC-002: Entrega Multicanal

```gherkin
Dado um alerta gerado
Quando está configurado para envio
Então recebo notificação em:
  ✅ Email (SMTP)
  ✅ SMS (Twilio)
  ✅ Push (WebSocket local)
  E dentro do SLA: <5 segundos
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

### AC-004: Controle de Taxa

```gherkin
Dado um fluxo de alertas
Quando múltiplos alertas do mesmo padrão ocorrem
Então sistema implementa:
  • Rate limiting: máx 1 alerta por padrão/minuto
  • Deduplicação: consolidar sinais similares
  • Backpressure: não descartar dados, fila ordenada
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

### RQ-003: Canais de Entrega

#### Email (SMTP)

- Provider: Configurável (Gmail, SendGrid, Postmark)
- Template: HTML com styling Bootstrap
- Retry: exponencial (1s, 2s, 4s, até 60s)
- Timeout: 10s max

#### SMS (Twilio)

- Account SID: variável de ambiente
- Message: máximo 160 caracteres (condensado)
- Retry: 3 tentativas
- Timeout: 5s max

#### Push (WebSocket local)

- Endpoint: `ws://localhost:8765/alertas`
- Autenticação: token Bearer
- Formato: JSON
- Reconexão automática

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
