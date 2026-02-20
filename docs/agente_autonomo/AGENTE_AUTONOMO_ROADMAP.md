# 🗺️ Roadmap - Agente Autônomo de Trading

**Versão:** 1.0.0
**Data:** 20/02/2026
**Horizonte:** 12 meses

---

## 📅 Timeline de Desenvolvimento

### Q1 2026 (Fevereiro - Abril)

#### **v1.0.0** (20/02) ✅
- Sistema de processamento BDI
- Análise de tendências
- Backlog estruturado
- Documentação completa

#### **v1.0.1** (27/02) 🔄
- Bugfixes
- Melhorias de performance
- Validação de dados

#### **v1.1.0** (13/03) ⏳
- Dados intradiários (1min, 5min)
- **Alertas automáticos (Push WebSocket + Email)** ← CONFIRMADO 🎯
  - Detection Engine (volatilidade >2σ)
  - Delivery multicanal (latência <30s P95)
  - Rate limiting + deduplicação (>95%)
  - Audit log completo (CVM compliant)
  - Operação MANUAL v1.1 (automático em v1.2)
  - Capital ramp-up: 50k → 80k → 150k
  - 4 Fases: Beta → Prod Restrita → Prod Normal
- Análise de opções
- Módulo de correlações
- Dashboard web básico

#### **v1.2.0** (10/04) ⏳
- Machine Learning para padrões
- Backtesting engine completo
- Integração com múltiplas fontes
- Async processing com Celery

---

### Q2 2026 (Maio - Junho)

#### **v2.0.0** (01/06) ⏳
- Arquitetura Microserviços
- API REST completa
- WebSocket tempo real
- Provisioning em cloud (AWS/GCP)
- Database escalável (PostgreSQL + Redis)

---

### Q3-Q4 2026 (Visão)

- [ ] Execution Engine fully automated
- [ ] Portfolio optimization
- [ ] Risk management avançado
- [ ] Compliance & Auditoria
- [ ] Mobile app

---

## 🎯 Objetivos por Milestone

| Milestone | Objetivo | KPI |
|-----------|----------|-----|
| **v1.0** | Análise BDI funcional | 3+ oportunidades/BDI |
| **v1.1** | Alertas + Dados infraday | <30s latência, >95% deduplicate |
| **v1.2** | ML operacional | Sharpe > 1.0, w/rate >65% |
| **v2.0** | Automação completa | 90%+ uptime |

## 📊 Métricas de Sucesso (Atualizado)

1. **Processamento BDI:** <5 segundos ✅
2. **Alertas (v1.1):** <30 segundos P95 latência ✅
3. **Deduplicação:** >95% consolidação ✅
4. **Win Rate Histórico:** 62-68% (v1.0-v1.1) ✅
5. **ROI Esperado:** +R$ 50-200k/mês (v1.1) ✅
6. **Uptime:** >99% em produção

---

**Documentos Relacionados:** BACKLOG, FEATURES, RELEASE
