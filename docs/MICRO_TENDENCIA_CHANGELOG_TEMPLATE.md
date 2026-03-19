# Template de Changelog do Micro Tendencia

Use este template para cada nova versao do micro.

```md
## vMAJOR.MINOR.PATCH_YYYYMMDD
- data_treino: YYYY-MM-DDTHH:MM:SS
- episodios_usados: N
- rewards_no_treino: N
- win_rate_treino: 0.000
- win_rate_validacao: 0.000
- delta_vs_anterior: +0.0pp
- rollback_realizado: False
- versao_anterior_ativa: vX.Y.Z_YYYYMMDD
- data_ultima_versao_ativa: YYYY-MM-DDTHH:MM:SS
- aprendizado_entrada: resumo do que o modelo passou a considerar melhor
- aprendizado_saida: resumo do que o modelo deixou de fazer
- notas: observacoes operacionais
```

## Exemplos de aprendizado

- `aprendizado_entrada`: passou a reconhecer HOLD como decisao util quando R/R esta ruim
- `aprendizado_saida`: reduziu compra tardia em rally exausto
- `aprendizado_entrada`: passou a dar mais peso a confirmacao macro em abertura
- `aprendizado_saida`: deixou de reagir a VWAP isolada sem contexto

## Regra pratica

Se a versao nova nao explicar claramente o que o micro aprendeu, a entrada
nao deve ser considerada concluida.

