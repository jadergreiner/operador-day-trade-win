# AU200 - Validacao do Framework

## Objetivo

Validar as etapas minimas do framework de analise AU200.

## Script de validacao

- Caminho: scripts/validacao/validar_framework_au200.py
- O que valida:
  1) Conexao MT5
  2) Simbolo AU200 disponivel
  3) Dados historicos suficientes
  4) Retornos calculados
  5) Calendario economico via MT5

## Execucao

`python scripts/validacao/validar_framework_au200.py`

## Resultado esperado

- Saida com "OK: framework AU200 validado"
- Exit code 0
