# HANDOFF PARA PROJECT MANAGER

## 1. Identificação

- id_demanda: P1-PROFIT_PROTECTION-THRESHOLDS-20260402
- título: Profit Protection v2 — Externalizar thresholds, perfis YAML e shadow_mode
- estado_documentacao: CONCLUIDO (handoff gerado)
- prioridade: Alta
- data: 2026-04-02

---

## 2. Resumo da Entrega

- objetivo da demanda: Externalizar os thresholds do `ProfitProtectionEngine` para
  um arquivo YAML (`config/profit_protection.yaml`), prover perfis configuráveis
  (ex.: `default`, `staging_ab1`, `conservative`, `aggressive`), suportar
  `shadow_mode` (aplicação sem executar ordens) e fornecer script de calibração
  A/B para validar combos antes do deploy em produção.
- problema resolvido: thresholds hardcoded dificultavam calibração rápida e
  obrigavam deploys para alterar comportamento de proteção de lucros.
- valor esperado pelo PO: reduzir devolução de lucros por reversões agudas, e
  permitir calibração segura em staging com menor risco operacional.
- valor entregue: especificação operacional e artefatos iniciais (backlog,
  changelog, requirements e handoff). Implementação de runtime pendente.

---

## 3. Impacto no Produto

- melhoria funcional: parametrização de proteções (break-even, partial-close,
  cooldown) por perfil, modo shadow para testes, e script A/B para validar
  trade-offs entre captura e drawdown.
- melhoria técnica: separação de configuração e código, injeção de `ProfitProtectionProfile`
  (Pydantic) no `ProfitProtectionEngine`, e loader YAML com cache e reload.
- impacto operacional: necessidade de instalar dependências (`pydantic`, `pyyaml`),
  reiniciar agentes RL após deploy, e rodar calibração em staging antes de ativar
  em produção.

---

## 4. Evolução Arquitetural

- mudanças estruturais:
  - novo arquivo de configuração: `config/profit_protection.yaml` (perfilização)
  - novo Pydantic model: `src/application/profit_protection_profile.py` (tipado)
  - config loader singleton: `src/application/config_loader.py` (cache + reload)
  - `ProfitProtectionEngine.__init__` atualizado para aceitar `ProfitProtectionProfile`
    via DI (compatível com kwargs antigos, mantendo fallback defaults)
- decisões técnicas relevantes:
  - usar `pydantic` para validação e documentação dos perfis;
  - usar `pyyaml` para carregar YAML (mais legível para operadores);
  - `shadow_mode` desliga efeitos de execução (apenas escreve artefatos em `outputs/`);
  - fallback: se parse YAML falhar, engine usará valores internos seguros e gerará alerta.
- compatibilidade preservada: `ProfitProtectionEngine` continuará aceitando
  kwargs antigos; nova API adiciona `profile: ProfitProtectionProfile` opcional.

---

## 5. Documentação Atualizada

- ADRs: considerar registrar ADR para a decisão de usar `pydantic`+`pyyaml` e
  `shadow_mode` (se ainda não existir).
- arquitetura alvo: atualizar `docs/ARQUITETURA_ALVO.md` se a injeção de perfil
  afetar diagramas de inicialização dos agentes.
- diagramas: atualizar `docs/DIAGRAMAS.md` com o fluxo "Config YAML → Loader → Engine".
- modelagem de dados: nenhum esquema DB alterado.
- regras de negócio: `docs/REGRAS_DE_NEGOCIO.md` já recebeu seção descrevendo
  `profit_protection.yaml` e comportamento de `shadow_mode`.
- backlog: cards adicionados em `docs/BACKLOG.md` (IDs: `P1-PROFIT_PROTECTION-THRESHOLDS-20260402`, `DEV-DEP-PROFIT-PROTECTION-20260402`).

---

## 6. Evidências Técnicas

- alteração planejada refere-se a `src/application/profit_protection_engine.py` (existing engine).
- scripts previstos:
  - `scripts/calibrar_profit_protection.py` — backtest A/B (gera `outputs/backtest_profit_protection_*`)
  - `scripts/backtest_profit_protection.py` — backtest de rotina (existente/permissível)
- outputs de observabilidade: `outputs/profit_protection_summary_YYYYMMDD.json` e `outputs/backtest_profit_protection_*`.
- dependências: `pydantic`, `pyyaml` (adicionados a `requirements.txt`).

---

## 7. Riscos ou Ressalvas

- riscos remanescentes:
  - se deployar sem instalar dependências, agentes cairão na inicialização (RuntimeError);
  - habilitar perfil agressivo em produção sem backtest pode aumentar drawdown;
  - event-loop gap detectado em `agente_rl_direto_independente.py` (ver pendência) pode impedir chamadas periódicas a `processar_protecao()` — risco de proteção não executada.
- limitações conhecidas:
  - o handoff exige que DevOps atualize CI/Docker para instalar `requirements.txt`;
  - o rollout recomendado é staged: shadow_mode → staging AB tests → gradual enable.

---

## 8. Pendências / Ações Recomendadas

- Implementar Pydantic model `ProfitProtectionProfile` e loader YAML (dev).
- Implementar `scripts/calibrar_profit_protection.py` e rodar em staging.
- Atualizar agentes para aceitar `profile` e suportar `shadow_mode`.
- Adicionar entradas em CI/Docker para instalar `requirements.txt`.
- Verificar e corrigir `agente_rl_direto_independente.py` para garantir
  chamadas periódicas a `processar_protecao()` (backlog já criado).
- Executar testes de integração e backtests antes do deploy em produção.

---

## 9. Impacto por Agente (avaliacao automatizada)

- `INICIAR_AGENTE_RL_5000.bat`: **ALTO | DIRETO** — precisa reiniciar após deploy;
  ação operacional: reiniciar e monitorar logs de `protection`.
- `INICIAR_AGENTE_RL_DIRETO.bat`: **ALTO | DIRETO** — deploy crítico; executar
  em `shadow_mode` em staging e validar antes de ligar em produção; reiniciar.
- `INICIAR_DIARIOS.bat`: **NENHUM | SEM IMPACTO** — leitura de outputs apenas.
- `INICIAR_MICRO_TENDENCIA_AUTO_TRADE.bat`: **MEDIO | INDIRETO** — pode consumir
  alguns parâmetros para partial-close; validar integração.
- `INICIAR_MONITOR_QUANTICO.bat`: **NENHUM | SEM IMPACTO** — somente observabilidade.

---

## 10. Recomendação

- rollout em 3 passos:
  1. `staging`: instalar dependências, habilitar `shadow_mode` com perfil `staging_ab1`, rodar `scripts/calibrar_profit_protection.py` (A/B test) e validar outputs em `outputs/`;
  2. `canary`: aplicar perfil `conservative` em um agente RL Direto isolado por 1 dia, monitorar `backtest` e `outputs` e verificar métricas (win rate, drawdown, devolucao de lucros);
  3. `prod`: gradualmente habilitar profile escolhido e monitorar rollbacks via `rl_retrain_scheduler`/`ModelRollbackManager` se degradacao ocorrer.

- Reiniciar os agentes RL após deploy (cold restart recomendado).
- Notificar operadores e DevOps com instrucoes de rollback e validar que `requirements.txt` foi instalada.

---

## 11. Definition of Ready para o Project Manager

- [ ] documentação consolidada (este handoff)
- [ ] `config/profit_protection.yaml` criado no branch de feature
- [ ] `ProfitProtectionProfile` implementado e testado
- [ ] `scripts/calibrar_profit_protection.py` implementado e executado em staging
- [ ] `requirements.txt` instalado em staging e validado
- [ ] plano de rollback definido e testado

---

*Arquivo gerado automaticamente por agente — salvar em local seguro e anexar ao ticket do backlog se necessário.*
