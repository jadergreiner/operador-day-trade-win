# 🖼️ Plano de Implementação S2-1: Dashboard Real-Time

**Status:** Planejamento
**Owner:** Executor Técnico
**Prioridade:** P0 (Must)

---

## 🎯 Objetivo
Criar uma interface visual (Dashboard) que consolide os sinais do MT5, as decisões do BDI e os estados do SMC em tempo real, eliminando a dependência exclusiva da leitura de logs textuais no console.

## 🏗️ Arquitetura Proposta

### Componentes Core:
1. **Source de Dados:** SQLite (`trading_data.db`) + WebSocket Server.
2. **Frontend:** Streamlit ou FastAPI + Jinja2 (Simplicidade vs Performance).
3. **Frequência de Atualização:** 5s a 15s (Polling ou Push via WS).

### Visões do Dashboard:
- **Painel de Operação:** Status da conexão MT5, Saldo, P&L do dia.
- **Decision Matrix:** Score BDI (0.0-1.0), Voto dos Detectores, Estado do "Advogado do Diabo".
- **SMC Map:** Preços de Swing High/Low detectados, zonas de Supply/Demand.
- **Log Stream:** Últimas 5 mensagens críticas filtradas.

## 📋 Critérios de Aceite
- [ ] Interface acessível via `http://localhost:8501` (ou similar).
- [ ] Visualização clara do Score consolidado do Macro Score Engine.
- [ ] Indicador visual de "AUTORIZADO" vs "BLOQUEADO" para novas ordens.
- [ ] Latência de atualização da UI inferior a 5 segundos após alteração no DB.

## 📅 Roadmap Interno
1. **Dia 1-2:** Setup do framework de UI e conexão com `trading_data.db`.
2. **Dia 3-4:** Implementação dos widgets de Score e P&L.
3. **Dia 5:** Integração com o monitor de SMC.
