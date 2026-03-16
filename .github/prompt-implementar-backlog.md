# Prompt: Implementar Item de Backlog

Copie o bloco abaixo e cole diretamente no chat.
Substitua apenas os campos marcados com `{{ }}`.

---

## Variante 1 — Próximo item pendente (autodescoberta)

```
## INICIAR DESENVOLVIMENTO

**Tarefa:** Implementar o próximo item PENDENTE de menor complexidade
em docs/BACKLOG.md (prioridade P0 → P1 → P2).

**Procedimento (6 etapas):**

1. **Ler:** Localizar item em docs/BACKLOG.md, extrair AC e agente impactado.
   Consultar docs/ADRS.md antes de implementar.
2. **TDD:** Criar testes ANTES do código. Código em src/, scripts em scripts/.
   Type hints 100%, Português 100%, docstring com referência AC e pipeline.
3. **Testar:** pytest --cov=src (>=80%). Todos PASS antes de avançar.
4. **Validar:** mypy src/ --strict. black + isort. Confirmar que segue
   docs/ARQUITETURA_ALVO.md. Criar ADR em docs/ADRS.md se houver decisao nova.
5. **Documentar:** Atualizar docs impactados (ARQUITETURA_ALVO, DIAGRAMAS,
   MODELAGEM_DE_DADOS, REGRAS_DE_NEGOCIO se aplicavel). Marcar item como DONE
   em docs/BACKLOG.md com evidencia (LOC, casos de teste, cobertura, agente
   impactado). Lint em todos os .md editados:
   python -m pymarkdown scan docs/
6. **Commitar:** git commit com mensagem clara, SEM acentos.
   Padrao: "feat: Implementar {{ ID }} conforme backlog - {{ agente }} impactado"

**Exigencias:**
- Type hints 100% (mypy --strict sem erros)
- Portugues 100% (codigo, docstrings, comentarios)
- Cobertura >= 80% (pytest --cov)
- Lint OK em todos os .md editados
- BACKLOG.md atualizado com status DONE e evidencia
- Pelo menos 1 executor INICIAR_*.bat impactado

**Começar agora!**
```

---

## Variante 2 — Item específico

```
## INICIAR DESENVOLVIMENTO

**Tarefa:** Implementar o item {{ ID_DO_ITEM }} em docs/BACKLOG.md.

**Procedimento (6 etapas):**

1. **Ler:** Localizar item {{ ID_DO_ITEM }} em docs/BACKLOG.md, extrair AC
   e agente impactado. Consultar docs/ADRS.md antes de implementar.
2. **TDD:** Criar testes ANTES do código. Código em src/, scripts em scripts/.
   Type hints 100%, Português 100%, docstring com referência AC e pipeline.
3. **Testar:** pytest --cov=src (>=80%). Todos PASS antes de avançar.
4. **Validar:** mypy src/ --strict. black + isort. Confirmar que segue
   docs/ARQUITETURA_ALVO.md. Criar ADR em docs/ADRS.md se houver decisao nova.
5. **Documentar:** Atualizar docs impactados (ARQUITETURA_ALVO, DIAGRAMAS,
   MODELAGEM_DE_DADOS, REGRAS_DE_NEGOCIO se aplicavel). Marcar item como DONE
   em docs/BACKLOG.md com evidencia (LOC, casos de teste, cobertura, agente
   impactado). Lint em todos os .md editados:
   python -m pymarkdown scan docs/
6. **Commitar:** git commit com mensagem clara, SEM acentos.
   Padrao: "feat: Implementar {{ ID_DO_ITEM }} conforme backlog - {{ agente }} impactado"

**Exigencias:**
- Type hints 100% (mypy --strict sem erros)
- Portugues 100% (codigo, docstrings, comentarios)
- Cobertura >= 80% (pytest --cov)
- Lint OK em todos os .md editados
- BACKLOG.md atualizado com status DONE e evidencia
- Pelo menos 1 executor INICIAR_*.bat impactado

**Começar agora!**
```

---

## Variante 3 — Com feedback de mercado (repriorizar + implementar)

```text
## INICIAR DESENVOLVIMENTO

**Tarefa:** Repriorizar backlog com base em feedback de mercado e implementar
o item de maior impacto resultante.

**Feedback de mercado:**
- Periodo: {{ DATA_INICIO }} a {{ DATA_FIM }}
- Win rate atual: {{ X% }} (baseline: {{ Y% }})
- Regime: {{ normal | elevated | panic }}
- Backtest: F1={{ }} | Sharpe={{ }} | Profit Factor={{ }}
- ROI estimado: R$ {{ }}/mes

**Procedimento (6 etapas):**

1. **Ler e repriorizar:** Abrir docs/BACKLOG.md. Com base no feedback acima,
   reordenar itens por impacto + urgência. Registrar decisão de repriorização
   com evidência Tier 1 diretamente no BACKLOG.md. Consultar docs/ADRS.md.
2. **TDD:** Criar testes ANTES do código. Código em src/, scripts em scripts/.
   Type hints 100%, Português 100%, docstring com referência AC e pipeline.
3. **Testar:** pytest --cov=src (>=80%). Todos PASS antes de avançar.
4. **Validar:** mypy src/ --strict. black + isort. Confirmar que segue
   docs/ARQUITETURA_ALVO.md. Criar ADR em docs/ADRS.md se houver decisao nova.
5. **Documentar:** Atualizar docs impactados (ARQUITETURA_ALVO, DIAGRAMAS,
   MODELAGEM_DE_DADOS, REGRAS_DE_NEGOCIO se aplicavel). Marcar item como DONE
   em docs/BACKLOG.md com evidencia (LOC, casos de teste, cobertura, agente
   impactado). Lint em todos os .md editados:
   python -m pymarkdown scan docs/
6. **Commitar:** Dois commits separados — um para gestão do backlog,
   outro para a implementação. SEM acentos nas mensagens.

**Exigencias:**
- Type hints 100% (mypy --strict sem erros)
- Portugues 100% (codigo, docstrings, comentarios)
- Cobertura >= 80% (pytest --cov)
- Lint OK em todos os .md editados
- BACKLOG.md atualizado com repriorização documentada + status DONE
- Pelo menos 1 executor INICIAR_*.bat impactado

**Começar agora!**
```
