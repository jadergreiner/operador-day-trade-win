# ROADMAP do Operador Day Trade Win

## 📊 Execução / Visibilidade (v1.0.1)
- **Sprint atual:** Sprint 2 — Inteligência e Visibilidade (Foco Execução)
- **Última atualização:** 2026-02-24T18:30:00Z
- **Progresso NOW:** 2 de 4 MUST (S2-2 e S2-3 concluídos)
- **Status da Fonte de Verdade:** [docs/STATUS_ENTREGAS.md](STATUS_ENTREGAS.md) (🟢 SINCRO)

## Visão do Produto
O operador day-trade-win é uma plataforma projetada para otimizar o desempenho de traders em operações de day trade, fornecendo ferramentas inteligentes e análises em tempo real.

## Ciclo de Evolução
### Agora (Now)
- Lançamento da versão inicial com funcionalidades básicas de trading e análise. (Status: ✅)
- Integração com as principais corretoras. (Status: ✅)
- **[NOVO 23/02] Correção Crítica SMC:** Substituição de preços fictícios (123.45) por cálculo matemático real de Swing High/Low. ✅
- **[NOVO 23/02] Auditoria Real-Time:** Mecanismo de verificação de persistência de RL validado (200 episódios capturados hoje). ✅

### Próximo (Next)
- **✅ S2-5-ISOLAMENTO COMPLETO [24/02]** — MT5 Terminal Isolation & Reconnect: ✅ Isolamento obrigatório implementado, ✅ PID do terminal validado, ✅ Fingerprint persistido em ~/.mt5_operator_session.json, ✅ Retry automático com backoff exponencial [5s, 10s, 20s], ✅ Health check contínuo (30s), ✅ 15 testes unitários PASSING (>98% coverage), ✅ MONITOR_OPERADOR.bat integrado, ✅ Documentação completa. **Status:** Sprint 2 CONCLUÍDO. **Testes:** 15/15 PASSING ✅. **Próximo:** Integração com operador .bat + UAT.
- **🟡 S2-5-PROBABILIDADE [24/02 PRIORIZADO]** — **Oportunidade 24: Previsão Direcional T+60:** Squad Multidisciplinar (8 membros). Implementar modelo XGBoost para prever direção WIN nos próximos 60 minutos (T+60). 25 features M1 + Grid Search 32 configs + Backtest validado ≥60% acertos. Confluência com detector SMC existente (Oportunidade 2). Timeline: 27/02-03/03. Expected: +2-3% win rate via confluência de curto prazo. Docs: [S2-5_PROBABILIDADE_T60_ESPECIFICACAO.md](docs/S2-5_PROBABILIDADE_T60_ESPECIFICACAO.md) + [S2-5_PROBABILIDADE_T60_SQUAD.md](docs/S2-5_PROBABILIDADE_T60_SQUAD.md).
- **🔄 S2-4 EM ANDAMENTO [24/02]** — **Oportunidade 22: Integração de Mimas (Phi Cube):** Squad Multidisciplinar (11 membros) formada. Ativar cálculo de leque (Fibonacci: 8, 17, 34, 72, 144, 305, 610) integrado ao `micro_score`. 8 subtasks paralelas. Timeline: 26-27/02. Expected: +3-5% win rate via confluência geométrica.
- **🔴 PRIORIDADE 0 — Oportunidade 23: MT5 Terminal Isolation & Reconnect (S2-5):** [VEJA LINHA ACIMA - já marcado COMPLETO] ~~Implementar isolamento obrigatório de terminal MT5 para garantir que o operador conecte sempre à conta e ao terminal corretos, evitando execução em conta/terminal errados. Requisitos: (1) Validar PID do processo `terminal64.exe` na inicialização, (2) Armazenar fingerprint (exe path + account login), (3) Rejeitar conexão se PID mudar, (4) Implementar retry automático com backoff exponencial após desconexão (3x com 5s, 10s, 20s), (5) Adicionar testes unitários para múltiplas instâncias MT5, (6) Adicionar health check contínuo com alerta em MONITOR_OPERADOR.bat quando conexão falha. **Impacto:** Elimina risco de ordem enviada para conta/terminal errado. **Timeline:** Sprint 2 (IMEDIATO). **Owner:** Arquiteto de Sistemas + Eng Sr. **Testes:** 100% cobertura de reconnect, múltiplas instâncias, terminal crash.~~
- **Oportunidade 1: Reentrada Alpha (Pós-Stop):** Evoluir o "Advogado do Diabo" para identificar quando o mercado entra em tendência forte logo após um Stop Loss, permitindo reentrada com Score reduzido se a volatilidade permitir.
- **Oportunidade 15: Materialização e Vínculo de `STATUS_ENTREGAS.md` (Gap de Governança):** ✅ **CONCLUÍDO 23/02** - Criado documento `docs/STATUS_ENTREGAS.md` (Fonte de Verdade). Este arquivo é o único local de "ancoragem" para IDs de tarefas e status de prontidão, vinculando cada linha de código no `INICIAR_MICRO_TENDENCIA_AUTO_TRADE.bat` a uma decisão orçamentária no Roadmap.
- **Oportunidade 16: Gate de Governança no Startup do Agente:** 🟢 **PLANEJADO** - Evoluir o `INICIAR_MICRO_TENDENCIA_AUTO_TRADE.bat` para ler o status de sincronização no `STATUS_ENTREGAS.md` antes do login no MT5. O sistema deve impedir o início da operação em conta real se o código local não estiver marcado como validado e sincronizado (Status != 🟢), garantindo que o desenvolvedor não execute código "out-of-roadmap".
- **Oportunidade 17: Sensor de Telemetria de Latência P95 (<500ms):** ✅ **CONCLUÍDO 24/02** - Implementado sensor de telemetria no loop principal e otimização de imports hot-path. Latência validada P95 < 500ms.
- **Oportunidade 19: Calibrador Dinâmico de Volatilidade (ATR Adaptive):** ⏳ **ROADMAP** - Evoluir o `.bat` para que os parâmetros de `Trailing Stop` e `Tamanho do Ticket` sejam ajustados automaticamente com base no ATR (Average True Range) dos últimos 15 minutos, minimizando o slippage e garantindo maior proteção em cenários de alta volatilidade intradiária.
- **Oportunidade 20: Salvaguarda de Persistência (State Lock):** ⏳ **ROADMAP** - Criar um arquivo de bloqueio de sessão (`.session_lock`) na inicialização do robô. Em caso de queda do terminal ou fechamento acidental da janela, o sistema detectará o estado anterior ao reiniciar, permitindo retomar a gestão de posições abertas e mantendo o histórico do "Advogado do Diabo" sem interrupções.
- **Oportunidade 21: Analytics de Intervenção Manual:** ⏳ **ROADMAP** - Integrar um menu de feedback no `.bat` para quando o trader encerrar uma posição manualmente. O sistema solicitará um código rápido (ex: 1-Falha Técnica, 2-Risco Externo, 3-Lucro Suficiente) para alimentar o dataset de treinamento do modelo v1.2, permitindo que a IA aprenda os critérios subjetivos do corretor humano.
- **Oportunidade 4: Hot-Reload de Pesos (Zero-Downtime):** Modificar o agente para monitorar atualizações em `modelo_ativo.pkl` e recarregar a rede neural em memória sem interromper o loop de execução do `.bat`.
- **Oportunidade 5: Treinamento Incremental em Tempo Real:** Configurar o pipeline para processar aprendizados em lotes de 50 episódios, permitindo que a IA se adapte a mudanças de volatilidade intradiárias em menos de 60 minutos.
- **Oportunidade 6: Shadow Validator de Auto-Promoção:** Implementar gate de segurança que testa automaticamente novos pesos em "Backtest Imediato" e autoriza a troca apenas se o ganho de eficiência for superior ao modelo ativo.
- **Oportunidade 7: Sincronização Dinâmica de Timezone (Heartbeat):** Substituir o offset fixo (-3h) por uma detecção automática de diferença entre o relógio local e o servidor MT5, eliminando descartos falsos de "Stale Data".
- **Oportunidade 8: Jornal de Latência e "Regra de Ouro" LKV:** Implementar persistência da defasagem (Capture vs Source Timestamp). O sistema usará o Último Dado Conhecido (LKV) em vez de descartar, mas o modelo de RL usará a idade do dado como fator de desconto de confiança.
- **Oportunidade 9: Indicadores de Antecipação Global (Lead/Lag):** Incluir US 10Y Yields, VIX e DXY no Macro Score. Implementar correlação cruzada para identificar automaticamente quais ativos globais estão "ditando o ritmo" da abertura brasileira.
- **Oportunidade 10: Ingestão de Fluxo via Streaming (Low Latency):** Transição do modelo de polling (2 min) para Streaming (Event-Driven) para os 10 ativos de maior peso (Core Drivers), eliminando pontos cegos intradiários.
- Implementação de algoritmos de aprendizado de máquina para previsão de tendências.
- Aumento das opções de customização do usuário.

### Mais tarde (Later)
- Expansão para mercados internacionais.
- Desenvolvimento de uma comunidade de traders para compartilhamento de estratégias e experiências.
- **Oportunidade 18: Dashboard de Monitoramento (S1-3):** Implementar interface visual integrada para acompanhamento de sinais e estados do bdi/smc. (Status: ⏩ DESPRIORIZADO).

---

## 🛠️ Governança de Implementação
**Sincronia Operador x Monitor:**
Toda evolução técnica no motor de trading (`scripts/agente_micro_tendencia_winfut.py`)
DEVE ser testada e aplicada simultaneamente em:
1.  **Operador de Execução:** `INICIAR_MICRO_TENDENCIA_AUTO_TRADE.bat`
2.  **Monitor de Operação:** `MONITOR_OPERADOR.bat`

Isso garante que o painel de controle reflita 100% da realidade operacional em tempo real.

**Evolução Orientada a Dados (Feedback Loop):**
O aprimoramento contínuo da estratégia e dos modelos de IA DEVE ser baseado na
geração, captura, processamento e treinamento sistemático utilizando os dados dos
diários operativos (Trading, AI, RL).

**Manutenção e Calibração de Scores (Atividade Rotineira):**
A calibração do sistema de Scores, indicadores técnicos, índices e correlações
DEVE ser tratada como o coração do processo operacional.
- É obrigatório recalibrar o modelo sempre que necessário para manter a
  aderência ao mercado.

**Governança e Sanidade Organizacional:**
O projeto deve manter uma arquitetura rigorosa, diagramas de classe e
documentação total atualizada sob supervisão do **Doc Advocate**.
- O repositório passará por um processo contínuo de limpeza e organização
  (Reorganização por Padrões), mantendo apenas o que é essencial para o
  funcionamento do projeto.

---

## Princípios Guia
- **Simplicidade**: As ferramentas devem ser intuitivas e fáceis de usar.
- **Transparência**: Informações claras sobre taxas e riscos associados ao trading.
- **Inovação**: Busca constante por novas tecnologias para melhorar a experiência do usuário.

## Documentos Relacionados
- [Estratégias Avançadas de Day Trade](link para o documento)
- [Relatório de Performance do Operador](link para o documento)