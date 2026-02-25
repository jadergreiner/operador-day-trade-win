# 🚨 TASK-CRÍTICA-0: FIX PERSISTENCE BUG

**Status:** 🔴 **BLOCKER ABSOLUTO** - Investigação + Fix Requerida  
**Prioridade:** 🔴 **P0 - CRÍTICA - Bloqueia todas as tasks subsequentes**  
**Atribuição:** Eng Sr (Lead) + DevOps + QA Automation  
**Duração Estimada:** 4-6 horas (investigação + implementação + validação)

---

## 🔴 PROBLEMA CRÍTICO

### Descoberta (Análise Executada 25/02)
```
✅ Operações Reais Executadas: 4 (confirmadas no MT5)
   • Ticket 2276014161 (SELL @ 193245)
   • Ticket 2276015509 (BUY @ 193435)
   • Ticket 2276015907 (BUY @ 193490)
   • Ticket 2276016015 (SELL @ 193475)

❌ Operações Persistidas em SQLite: 0
   • simulated_trades: VAZIO
   • mt5_orders_raw: PROVAVELMENTE VAZIO
   • mt5_deals_raw: PROVAVELMENTE VAZIO
   • trade_audit_reports: VAZIO

🔴 STATUS: FALHA CRÍTICA DE INTEGRIDADE
```

### Impacto de Negócio
- ❌ **Auditoria:** Operações reais sem registro auditável (violação CVM/B3)
- ❌ **Compliance:** Impossível reconciliar capital vs operações
- ❌ **Confiança:** Sistema não prova sua própria integridade
- ❌ **Capital:** Dados de P&L não mapeados para decisões futuras

### Impacto Técnico
- ❌ **Blocker para INTEGRATION-ML-001:** Não podemos confiar em dados sem saber se serão persistidos
- ❌ **Blocker para Phase 2 Decision:** Sem auditoria, não escalamos capital
- ❌ **Blocker para Go-Live v1.2:** Sem persistência, não temos operador viável

---

## 📋 ESCOPO

### O Que Faz Esta Task

**Investigar:** Por que operações de 24/02 não foram persistidas?
- Verificar logs de erro em: `src/infrastructure/adapters/mt5_adapter.py`
- Verificar transações de database em: `src/infrastructure/database/`
- Verificar code path: MT5Adapter → save_trade() → SQLite
- Revisar `trade_repository.py` para falhas de commit

**Corrigir:** Implementar garantias de persistência 100%
- Adicionar retry logic com exponential backoff
- Implementar dead-letter queue para trades que falham
- Adicionar transações ACID com rollback protection
- Adicionar logging detalhado de cada etapa

**Validar:** E2E test confirmando persistência
- Executar 10+ operações simuladas (não real)
- Confirmar que 100% foram salvos no SQLite
- Validar reconciliação MT5 ↔ Database
- Testes de falha de conexão + recovery

---

## ✅ ACCEPTANCE CRITERIA (5 verificáveis)

1. ✅ **Causa Raiz Identificada**
   - Documento explicando por que dados de 24/02 não foram salvos
   - Referências a logs, code path, ou configuração

2. ✅ **Fix Implementado**
   - Retry logic com 3x exponential backoff adicionado
   - Dead-letter queue criada para trades falhados
   - Transações ACID com rollback protection
   - Code review aprovado por CTO

3. ✅ **Testes E2E Passando**
   - test_persistence_e2e.py criado
   - 10 operações simuladas → 100% persistidas no SQLite
   - Zero perda de dados em cenário de falha de conexão

4. ✅ **Reconciliação Validada**
   - Script de auditoria criado: `verify_trade_reconciliation.py`
   - Valida que cada trade no MT5 tem correspondente no database
   - Report de inconsistências (se houver) documentado

5. ✅ **Documentação Atualizada**
   - AUDITORIA_CRITICA_DADOS_OPERACOES_24FEV.md atualizado com resolução
   - Novo arquivo: PERSISTENCE_GUARANTEE_PROTOCOL.md criado
   - Trade persistence flow documentado em docs/ARCHITECTURE.md

---

## 📍 DEPENDÊNCIAS

### Bloqueia
```
INTEGRATION-ML-001 (Dataset Loading)
├─ Motivo: Não podemos treinar modelo com dados se persistência é desconfiável
└─ Será iniciado APÓS este task estar 100% completo

INTEGRATION-ENG-002 (WebSocket Server)
├─ Motivo: Sem auditoria, não escalamos para produção
└─ Será iniciado APÓS este task estar 100% completo

Phase 2 Decision (Capital Increase)
├─ Motivo: Sem persistência auditável, não aprovamos 2x capital
└─ Será iniciado APÓS este task estar 100% completo
```

### Depende De
```
NENHUMA - Task é independente
├─ Pode ser iniciada IMEDIATAMENTE
└─ Não requer nenhum pré-requisito
```

---

## 🚀 PRÓXIMAS AÇÕES (IMEDIATO)

### Persona: Eng Sr (Lead)
- [ ] Revisar `src/infrastructure/adapters/mt5_adapter.py` linha 1-50
- [ ] Revisar `src/infrastructure/repositories/trade_repository.py` linha 45-80
- [ ] Buscar logs de erro: `logs/operador_*.log` entre 09:34-10:00 de 24/02
- [ ] Criar issue de investigação profunda

### Persona: DevOps
- [ ] Verificar database logs: `PostgreSQL activity logs` de 24/02
- [ ] Verificar connection pooling: há desconexões não tratadas?
- [ ] Validar retry policies na cadeia MT5 → DB

### Persona: QA Automation
- [ ] Preparar ambiente de teste isolado
- [ ] Setup mock MT5Adapter para simular operações
- [ ] Preparar fixtures de test com 10+ operações

---

## 💾 ENTREGA ESPERADA

**Quando Task está COMPLETA:**
1. Documento de causa raiz assinado por CTO
2. Código com retry + dead-letter queue implementado
3. Tests E2E com 100% passando
4. Auditoria de 24/02 agora tem reconciliação completa
5. **PRONTO PARA INICIAR INTEGRATION-ML-001**

---

## 📊 PRIORIZAÇÃO

| Aspecto | Decisão |
|---------|---------|
| **Prioridade** | 🔴 **P0 - Crítica** |
| **Bloqueador** | ✅ Sim - bloqueia 3+ tasks |
| **Dependências** | ❌ Nenhuma (independente) |
| **Impacto de Negócio** | 🔴 Crítico - Auditoria + Compliance |
| **Risco de Não Fazer** | 🔴 Crítico - Produto não viável |
| **Ordem de Execução** | **#1 - AGORA (antes de qualquer outra task)** |

---

**Status:** 🟡 **AGUARDANDO APROVAÇÃO PARA INICIAR** | **Destinatário:** Eng Sr + DevOps + CTO
