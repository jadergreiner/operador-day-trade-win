# 🚀 Guia Rápido — 5 Agentes Customizados

Seu projeto tem 5 agentes especializados. Use eles assim:

## Como Usar

```
/agente-trading     → Implementar features de trading (ordens, risk, MT5)
/agente-ml         → Treinar/validar modelos ML (backtest, grid search)
/agente-auditoria  → Auditar operações (sincronização, compliance)
/agente-aprendizado → Analisar performance (win rate, lessons learned)
/agente-governanca → Consolidar documentação (maintain BACKLOG_UNIFICADO.md)
```

## Exemplos de Prompt

### Trading
```
/agente-trading implementar validador de correlacao maxima 70% para ordens abertas
/agente-trading adicionar circuit breaker -5% slow mode com 50% ticket size
```

### ML
```
/agente-ml treinar XGBoost com grid search 8 configs, target F1 >= 0.65
/agente-ml validar backtest Mar 01-15 com win rate esperado 62-70%
```

### Auditoria
```
/agente-auditoria validar sincronizacao ordens MT5 vs SQLite periodo 01-15_MAR
/agente-auditoria gerar compliance report com todos overrides CIO/CFO
```

### Aprendizado
```
/agente-aprendizado analisar performance ultima semana com Deep Dive por hora
/agente-aprendizado identificar padroes de losing trades e propor fixes
```

### Governança
```
/agente-governanca consolidar 5 documentos orphan em BACKLOG P(N)
/agente-governanca auditar integridade documentacao e lint rules
```

## Padrões Obrigatórios

✅ Todos agentes garantem:
- 🇧🇷 Comunicação 100% Português
- 📝 Commits UTF-8 clean (SEM ACENTOS)
- ✔️ Lint: MD013 80 chars, pymarkdown 0 errors
- 💯 Type hints: 100% mypy strict
- 🧪 Tests: >80% coverage, markers pytest
- 📚 Documentação: Consolidada em BACKLOG_UNIFICADO.md

## Arquivos Relacionados

- **Instruções Principais:** `.github/copilot-instructions.md`
- **Prompts Agentes:** `.github/agente-*.prompt.md` (5 arquivos)
- **BACKLOG Histórico:** `docs/BACKLOG_UNIFICADO.md` (P19-P49, 440+ arquivos)
- **Arquitetura Projeto:** Explorada em SESSION memory

## Workflow Rápido

1. **Tarefa** → Escolha agente certo
2. **Detalhar** → Forneça contexto (quais arquivos, resultado esperado)
3. **Executar** → Agente implementa + testa + valida
4. **Revisar** → Confirme output contra AC, lint, tests
5. **Commit** → Agente faz commit limpo com mensagem Português

---

**Próximo step:** Experimente `/agente-governanca auditar integridade` para validar docs!
