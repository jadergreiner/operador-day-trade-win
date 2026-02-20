# ❓ FAQ e Lições Aprendidas

**Versão:** 1.0.0  
**Data:** 20/02/2026

---

## 🤔 Perguntas Frequentes

### P1: Como iniciar a análise BDI?
**R:** Execute `python scripts/processar_bdi.py` no terminal. Os relatórios serão gerados em `data/BDI/reports/`.

### P2: Onde encontro as oportunidades de trading?
**R:** Consulte `relatorio_consolidado.md` e `relatorio_bdi_YYYYMMDD_HHMMSS.html` em `data/BDI/reports/`.

### P3: Como atualizar o backlog com novas tarefas?
**R:** Edite `backlog_detalhado.py` ou `backlog_detalhado.json` e execute sincronização.

### P4: Qual é o ROI esperado?
**R:** 1-2% ao dia para operações de curto prazo (day trading + swing).

### P5: Como monitorar o progresso das tarefas?
**R:** Execute `python backlog_detalhado.py` para obter o status consolidado.

---

## 📚 Lições Aprendidas

### ✅ O Que Funciona Bem

1. **Extração Automática de Dados BDI**
   - Pipeline confiável de parse e extração
   - Relatórios gerados em múltiplos formatos
   - **Lição:** Modularidade em parsers economiza 40% de tempo

2. **Sincronização Baseada em Timestamps**
   - Arquivos versionados e rastreáveis
   - Conflitos de merge reduzidos significativamente
   - **Lição:** Checksum automático é essencial

3. **Documentação Integrada ao Código**
   - Menos divergência entre código e docs
   - Atualizações mais rápidas
   - **Lição:** Docs como código (Markdown) > banco de dados

### ⚠️ Desafios Identificados

1. **Latência em Dados Intradiários**
   - BDI oferece apenas dados consolidados
   - Necessário integrar feed de pregão em tempo real
   - **Solução em Progresso:** TASK-005 (Integração de Dados)

2. **Falta de Dados de Opções Detalhados**
   - Impossível analisar IV e estruturas
   - Requer relatório específico de opções
   - **Solução em Progresso:** TASK-004 (Dados de Opções)

3. **Volatilidade Baixa = Menos Oportunidades**
   - Período analisado tinha volatilidade moderada
   - Limita número de sinais ALTA prioridade
   - **Mitigação:** Múltiplas estratégias para diferentes condições

### 🎯 Recomendações Futuras

1. **Integração com APIs Externas**
   - Bloomberg Terminal API
   - Reuters Eikon
   - Consolidação de múltiplas fontes

2. **Machine Learning para Padrões**
   - Detectar padrões recorrentes
   - Prever movimentos com base em histórico
   - Validação cruzada obrigatória

3. **Automação de Alertas**
   - Email, SMS, Telegram
   - Escalação de criticidade
   - Limites de exposição

---

**Documentos Relacionados:** FEATURES, ROADMAP, RL
