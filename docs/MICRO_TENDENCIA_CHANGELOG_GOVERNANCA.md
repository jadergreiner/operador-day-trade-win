# Governanca de Changelog do Micro Tendencia

Este documento define como versionar, registrar e auditar a evolucao do
`INICIAR_MICRO_TENDENCIA_AUTO_TRADE.bat` e do modelo de micro tendencia.

## Objetivo

Garantir que cada versao do micro tenha:

- registro do que entrou de aprendizado
- data e identificador da versao
- referencia ao arquivo de modelo
- resumo de melhoria ou regressao
- trilha auditavel no banco e em markdown

## Fonte de verdade

1. Banco SQLite do ambiente
2. `data/models/micro_tendencia/CHANGELOG.md`
3. `data/models/micro_tendencia/vMAJOR.MINOR.PATCH_YYYYMMDD.json`
4. `rl_training_metrics`
5. `model_metadata`

## Regra de versionamento

Formato padrao:

`vMAJOR.MINOR.PATCH_YYYYMMDD`

### Semantica

- `MAJOR`: quebra de contrato, mudanca estrutural relevante ou rollback de amplo impacto
- `MINOR`: novo ciclo de aprendizado aceito
- `PATCH`: ajuste corretivo, rollback pontual ou refinamento sem mudar a estrategia central

## O que registrar por versao

Cada versao deve documentar, no minimo:

- versao
- data do treino
- total de episodios usados
- total de rewards avaliados
- win rate de treino
- win rate de validacao
- delta vs versao anterior
- rollback realizado ou nao
- caminho do modelo
- notas de aprendizado

## O que entra como aprendizado

O changelog do micro deve explicitar, em linguagem operacional:

- quais features foram mais uteis
- quais motivos de entrada se confirmaram
- quais HOLDs foram corretos
- quais sinais foram casualidade
- quais filtros deixaram de ser confiaveis
- quais ajustes de threshold mudaram a decisao

## Processo de escrita

Ao finalizar um retreino:

1. persistir `rl_training_metrics`
2. atualizar `model_metadata`
3. anexar entrada em `CHANGELOG.md`
4. atualizar o JSON da versao
5. expor a versao no terminal do micro e no painel de diarios

## Processo de bootstrap

Quando ainda nao existir historico formal de treino:

- registrar um bootstrap inicial
- usar a versao do modelo carregado como baseline auditavel
- preservar a data do arquivo do modelo como referencia

## Regras de auditoria

- Nunca sobrescrever manualmente versao ja publicada
- Nunca apagar historico para “limpar” inconsistencias
- Em caso de regressao, registrar rollback e motivo
- O changelog deve refletir o que realmente entrou em producao

## Estrutura sugerida do CHANGELOG.md

```md
## v1.2.4_20260319
- data_treino: 2026-03-19T12:30:00
- episodios_usados: 500
- rewards_no_treino: 200
- aprendizado_entrada: HOLDs corretos + macro confirmado + redução de falso positivo
- aprendizado_saida: fechamento precoce menos agressivo em ADX alto
- delta_vs_anterior: +1.8pp
- rollback_realizado: False
- notas: Ajuste de microestrutura e risco
```

## Responsabilidade

- O runtime escreve o histórico
- A documentação descreve a política
- A validação operacional confirma se a política foi respeitada

