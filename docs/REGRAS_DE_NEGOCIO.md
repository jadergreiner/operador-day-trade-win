# Regras de Negocio Canonicas

## Premissas Operacionais

- O sistema so opera com ambiente valido.
- Auto-trade exige confirmacao explicita do operador.
- Health check reprovado bloqueia sessao.
- Terminal MT5 incorreto bloqueia operacao.

## Regras de Risco do Runtime (inalteradas)

- Janela de pregao e respeitada.
- Sem novas entradas nos minutos finais.
- Limite de trades diarios e respeitado.
- Limite de perda diaria e respeitado.
- Ordem real exige stop e alvo validos.
- Confidence minima e risco-retorno minimo devem ser atendidos.

## Regra Gate 2 para Escala de Capital

Gate 2 e uma regra de **escala de capital**, nao de entrada de trade.

- PASS -> pode ampliar capital.
- FAIL -> mantem capital conservador.
- Em execucao -> mantem capital conservador.
- Indefinido/erro -> mantem capital conservador.

## Regra de Falha Segura

Qualquer falha de pipeline P0-2 deve resultar em postura conservadora
(sem ampliacao de capital).

## Rastreabilidade

- Inicio e fim da sessao devem manter sincronizacao com historico local.
- Decisao Gate 2 deve ficar persistida em artefatos locais de `data/backtest`.
