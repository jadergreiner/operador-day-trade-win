# AU200 - Estrutura de Analise

Esta pasta centraliza a analise do indice australiano AU200.

## Arquivos

- relacoes_correlacoes.md: mapa de relacoes e correlacoes
- monitoramento.md: plano de acompanhamento e gatilhos
- validacao_framework.md: checagens e scripts de validacao

## Execucao rapida

- Analise e correlacoes: `python scripts/analise/au200_relacoes_correlacoes.py`
- Validacao do framework: `python scripts/validacao/validar_framework_au200.py`

## Calendario MT5 local

Quando a API Python do MT5 nao expor calendario, use exportacao local:

1) Copie [scripts/mt5/export_calendar_mt5.mq5](scripts/mt5/export_calendar_mt5.mq5) para a pasta MT5:
	- MQL5/Scripts
2) Execute o script no MT5 (gera o arquivo em MQL5/Files/mt5_calendar_export.json)
3) No Python, defina um dos caminhos:
	- `MT5_CALENDAR_EXPORT`: caminho completo do JSON exportado
	- `MT5_FILES_DIR`: diretorio MQL5/Files
