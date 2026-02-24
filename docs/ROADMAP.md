# ROADMAP do Operador Day Trade Win

## 📊 Execução / Visibilidade (v1.0.1)
- **Sprint atual:** Sprint 1 — Operacionalização (Foco Execução)
- **Última atualização:** 2026-02-24T00:15:00Z
- **Progresso NOW:** 3 de 3 MUST (S1-1, S1-2 e S1-4 concluídos)
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
- **Oportunidade 1: Reentrada Alpha (Pós-Stop):** Evoluir o "Advogado do Diabo" para identificar quando o mercado entra em tendência forte logo após um Stop Loss, permitindo reentrada com Score reduzido se a volatilidade permitir.
- **Oportunidade 14: Mapa ATR e Confluência SMC (M1/M5):** Implementar motor de "Teia de Volatilidade" baseado em ATR dinâmico para calcular pontos de entrada, parciais e alvos. Integrar cálculo de SMC (Support/Resistance/Supply/Demand) em timeframes curtos (M1/M5) para identificar confluências com o Mapa ATR, gerando sinais de "Convicção Máxima" para o `INICIAR_MICRO_TENDENCIA_AUTO_TRADE.bat`.
- **Oportunidade 22: Integração de Mimas (Phi Cube):** 🟢 **PRIORIZADO SPRINT 2** - Ativar o cálculo de alinhamento de leque das Mimas (8, 17, 34, 72, 144, 305, 610) e integrá-lo ao `micro_score`. Atualmente o cálculo existe em código mas não é contabilizado na decisão.
- **Oportunidade 2: Autópsia Automática de Perdas:** Criar script que isola trades com P&L negativo e prioriza esses "Episódios de Falha" no pipeline de treinamento do RL para acelerar a correção de viés.
- **Oportunidade 3: Filtro de Consolidação Dinâmico:** Refinar o `MicroTrendDecision` para distinguir entre "Consolidação de Descanso" (Oportunidade) vs "Consolidação de Exaustão" (Risco), baseado nos novos dados de S/R reais.
- **Oportunidade 11: Probabilidade Direcional de Curto Prazo (T+60):** Implementar feature no motor de execução para prever a probabilidade direcional dominante (Compra/Venda) e o preço alvo estimado para a próxima janela de 60 minutos, servindo de suporte estratégico para alocação de capital e posições de longo prazo.
- **Oportunidade 12: Módulo 'Pre-Flight Check' de Abertura:** Integração automática de drivers globais (EWZ, SPY, VIX) no `INICIAR_MICRO_TENDENCIA_AUTO_TRADE.bat`. O sistema travará ordens a mercado em GAPs > 1.0% nos primeiros 15 minutos, priorizando defesas baseadas no cenário global.
- **Oportunidade 13: Reconciliação Automática Post-Market:** Criar rotina de fechamento que valida 100% da integridade MT5 vs SQLite e calcula o Decay de Sinal do dia anterior para recalibrar o Take Profit dinâmico da abertura do dia seguinte.
- **Oportunidade 14: Mapa ATR e Confluência SMC (M1/M5):** Implementar motor de "Teia de Volatilidade" baseado em ATR dinâmico para calcular pontos de entrada, parciais e alvos. Integrar cálculo de SMC (Support/Resistance/Supply/Demand) em timeframes curtos (M1/M5) para identificar confluências com o Mapa ATR, gerando sinais de "Convicção Máxima" para o `INICIAR_MICRO_TENDENCIA_AUTO_TRADE.bat`.
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