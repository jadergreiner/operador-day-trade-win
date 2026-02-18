# WINFUT Micro Tendências - Validação do Framework

## Objetivo

Validar as etapas mínimas do framework de micro tendências WINFUT.

## Script de validação

- Caminho: scripts/validacao/validar_framework_winfut_micro.py
- O que valida:
  1) Conexão MT5
  2) Símbolo WIN$N disponível e com cotações
  3) Dados históricos M5/M15/H1 suficientes (>= 100 candles)
  4) Cálculo de VWAP funcional
  5) Cálculo de Pivôs Diários funcional
  6) Indicadores técnicos M5 (RSI, MACD, Bollinger, ADX)
  7) Detecção de BOS/CHoCH funcional
  8) Símbolos de contexto macro acessíveis
  9) Persistência SQLite funcional

## Execução

```bash
python scripts/validacao/validar_framework_winfut_micro.py
```

## Resultado esperado

- Saída com "OK: framework WINFUT Micro Tendências validado"
- Exit code 0
