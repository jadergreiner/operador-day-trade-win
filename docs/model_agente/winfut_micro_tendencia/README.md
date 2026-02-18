# WINFUT Micro Tendências - Estrutura de Análise

Esta pasta centraliza a análise de micro tendências para Day Trade no mini
índice futuro (WINFUT) da B3.

## Objetivo

Identificar o direcional do dia via sistema de pontuação e mapear regiões de
interesse e liquidez para surfar micro tendências e/ou reversões intraday.

## Arquivos

- relacoes_correlacoes.md: mapa de relações, correlações e sistema de pontuação
- monitoramento.md: plano de acompanhamento, gatilhos e micro tendências
- validacao_framework.md: checagens e scripts de validação

## Execução rápida

- Agente Micro Tendência: `python scripts/agente_micro_tendencia_winfut.py`
- Validação do framework: `python scripts/validacao/validar_framework_winfut_micro.py`

## Conexão MT5

As cotações são capturadas via MetaTrader 5 da Clear, configurado no `.env`:

```bash
MT5_LOGIN=...
MT5_PASSWORD=...
MT5_SERVER=...
```

## APIs complementares

Dados adicionais de mercado disponíveis via chaves no `.env`:
- TwelveData, Alpha Vantage, Finnhub, FMP, FRED
- Binance (crypto como proxy de risco)
- ExchangeRate (câmbio)
