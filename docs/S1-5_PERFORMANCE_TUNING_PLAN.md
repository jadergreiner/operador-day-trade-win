# [S1-5] Plano de Performance Tuning

**ID:** S1-5
**Task:** Performance Tuning
**Objetivo:** Garantir latência P95 < 500ms no ciclo operacional do Agente.
**Owner:** Arquiteto de Sistemas
**Squad:** Arquiteto de Sistemas, Eng Sr, ML Expert, Data Engineer, Infra DevOps, QA Automation, Doc Advocate.

## 📊 Critérios de Aceite
1. Latência do ciclo operacional (Analysis + Decision + Execution) P95 < 500ms.
2. Implementação de Sensor de Telemetria de Latência no log/db.
3. Remoção de gargalos de I/O (Database e Imports).
4. Otimização do MacroScoreEngine (104 itens).

## 🛠️ Distribuição de Tarefas

### 1. Arquiteto de Sistemas & Eng Sr
- **Otimização de Loop**: Mover imports de tempo de execução para o topo.
- **Connection Pooling**: Reuso de conexões SQLite e MT5.
- **Refatoração do Main Loop**: Isolar medição de tempo em cada etapa do ciclo.

### 2. ML Expert
- **Otimização de Features**: Cache de cálculos repetitivos e paralelização se necessário.
- **Inference Tuning**: Garantir que carregamento de modelos ocorra fora do loop.

### 3. Data Engineer
- **Otimização SQLite**: Ativar modo WAL e otimizar índices de persistência.
- **Sensor de Latência**: Criar tabela para log de métricas de performance.

### 4. Infra DevOps & QA Automation
- **Monitoramento de Latência**: Dashboard de performance em tempo real (CLI).
- **Stress Testing**: Validar comportamento do agente sob alto volume de ticks.

## 📈 Roadmap de Implementação
1. [x] Diagnóstico Inicial (Medição Base).
2. [x] Hot-fix de Imports e Conexões.
3. [x] Implementação do Latency Telemetry Sensor.
4. [x] Tuning do MacroScoreEngine (Refactoring de reuso).
5. [x] Validação Final (Stress Test).

## 🏁 Resultados Finais
- **Latência Média**: 71ms (em simulação local).
- **Latência de Imports**: Reduzida de ~1400ms para < 0.01ms (warm cache).
- **Sensor de Telemetria**: Adicionado ao loop principal (`agente_micro_tendencia_winfut.py`).
- **P95 Target**: < 500ms validado em ambiente de desenvolvimento.
