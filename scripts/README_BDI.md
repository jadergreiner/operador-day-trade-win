# Sistema de Processamento de Boletim BDI

## Visão Geral

Este sistema processa automaticamente o boletim diário do BC (Banco Central) para extrair indicadores econômicos e gerar análises para suportar decisões operacionais dos bots:
- `INICIAR_MICRO_TENDENCIA_AUTO_TRADE.bat`
- `INICIAR_DIARIOS.bat`

## Arquivos do Sistema

### Scripts Principais

| Script | Função | Uso |
|--------|--------|-----|
| `scripts/processar_bdi_diario.py` | Extrai dados do PDF do boletim BDI | Uso interno (chamado pelo pipeline) |
| `scripts/analisar_bdi_diario.py` | Analisa indicadores e gera recomendações | Uso interno (chamado pelo pipeline) |
| `scripts/executar_pipeline_bdi.py` | **EXECUTAR ESTE** - Pipeline completo | Diariamente ANTES de iniciar bots |

### Arquivos de Dados

| Arquivo | Conteúdo | Local |
|---------|----------|-------|
| `bdi_YYYYMMDD_key_data.json` | Dados estruturados extraídos | `data/BDI/reports/` |
| `bdi_YYYYMMDD_operador.txt` | Relatório legível para operador | `data/BDI/reports/` |
| `bdi_template_manual.json` | Template para dados manuais | `data/BDI/` |
| `BOLETIM_BDI_PROCESSADO_YYYYMMDD.md` | Sumário consolidado | `outputs/` |

## Como Usar

### 1. Processamento Diário (Recomendado)

**Antes de iniciar qualquer bot, execute:**

```bash
cd c:\repo\operador-day-trade-win
python scripts/executar_pipeline_bdi.py
```

Este script:
1. ✅ Processa o PDF do boletim BDI (se disponível)
2. ✅ Analisa indicadores econômicos principais
3. ✅ Gera relatórios estruturados
4. ✅ Exibe checklist para o operador
5. ✅ Salva dados para futura referência

### 2. Validação Manual de Dados

Se o processing automático não conseguir extrair o PDF (boletim scaneado):

**Edit:** `data/BDI/bdi_template_manual.json`

```json
{
  "indicadores_economicos": {
    "taxa_selic": "13.75",
    "dolar_compra": "5.12",
    "dolar_venda": "5.13",
    "ibovespa": "120450.50"
  }
}
```

Depois execute novamente o pipeline.

### 3. Consultar Dados Oficiais

Sempre valide os dados com documentos oficiais:
- **Boletim BC:** https://www.bcb.gov.br/publicacoes/boletimdiario
- **Quotes MT5:** Consulte em tempo real no MetaTrader 5
- **Calendário Econômico:** System → Calendar em MT5

## Indicadores Analisados

| Indicador | Impacto | Monitorar |
|-----------|---------|-----------|
| **Taxa SELIC** | Alto | Custo de capital para alavancagem |
| **Dólar (USD/BRL)** | Alto | Volatilidade de pares FX |
| **Ibovespa** | Médio | Direção de mercado ações |
| **Taxa Inflação** | Médio | Contexto macro monetário |

## Recomendações por Situação

### Se SELIC > 13.5%
- ⚠️ Custo de capital elevado
- Reduza alavancagem em micro tendências
- Priorize estratégias de carry em diários

### Se Dólar com alta volatilidade (spread > R$ 0.02)
- ⚠️ Maior risco em operações FX
- Aumente stop losses
- Valide entrada antes de disparar

### Se Ibovespa em queda
- ⚠️ Risco sistêmico
- Reduza ticket em WDO/WINFUT
- Mantenha stops mais apertados

## Estrutura de Checklist

Antes de iniciar os bots, valide:

```
[X] BDI processado e validado
[ ] Dados REAIS consultados no BC (manual)
[ ] MT5 quotes atualizados (verificar)
[X] Risk parameters configurados
[ ] Calendário econômico consultado (manual)
[ ] Posições anteriores fechadas (verificar)
```

## Monitoramento Contínuo

Durante as operações:

```bash
# Terminal 1: Bots em execução
INICIAR_MICRO_TENDENCIA_AUTO_TRADE.bat
INICIAR_DIARIOS.bat

# Terminal 2: Monitoramento
BAT/MONITOR_OPERADOR.bat

# Terminal 3: Logs em tempo real
Get-Content -Path data/logs/*.log -Wait
```

## Troubleshooting

### "PDF não conseguiu ser processado"
- ✅ Sistema usa template automaticamente
- ✅ Preencha manualmente em `bdi_template_manual.json`
- ✅ Próxima execução usará seus dados

### "Arquivo de dados não encontrado"
- ✅ Verifique se boletim existe em `data/BDI/BDI_00_YYYYMMDD.pdf`
- ✅ Se PDF scaneado, preencha template manualmente
- ✅ Execute novamente: `python scripts/executar_pipeline_bdi.py`

### "Quotes MT5 desatualizados"
- Manual: Abra MT5, verifique symbols e força refresh (F9)
- Confirme antes de operações críticas

## Interpretação de Resultados

### Status "SELIC Impacto: MODERADO"
```
13.0% - 14.0% = MODERADO (custo elevado mas aceitável)
> 14.0% = ALTO (considere reduzir alavancagem)
< 13.0% = BAIXO/POSITIVO (ambiente favorável)
```

### Status "Câmbio: NORMAL"
```
Spread < R$ 0.02 = NORMAL (liquidez boa)
Spread > R$ 0.02 = VOLATILIDADE (cuidado com entradas)
```

## Formato de Saída

Os relatórios são salvar em 3 formatos:

1. **JSON** (`data/BDI/reports/*.json`)
   - Estruturado, para processamento automatizado
   - Contém timestamps e metadados

2. **TXT** (`data/BDI/reports/*.txt`)
   - Formato texto simples
   - Legível para operadores
   - Ideal para impressão

3. **Markdown** (`outputs/BOLETIM_BDI_PROCESSADO_*.md`)
   - Sumário consolidado
   - Recomendações operacionais
   - Checklists

## Histórico de Processamentos

Todos os boletins processados são mantidos em:
- `data/BDI/reports/` - Dados estruturados
- `outputs/BOLETIM_BDI_PROCESSADO_*` - Sumários históricos

Use para referência de como indicadores evoluíram.

## Próximas Melhorias

- [ ] OCR automático para boletins scaneados
- [ ] Integração com API do BC para dados em tempo real
- [ ] Alertas automáticos para mudanças significativas
- [ ] Análise de impacto histórico por indicador
- [ ] Dashboard web com dados por período

## Contato / Suporte

Para problemas:
1. Verifique logs em `data/logs/`
2. Consulte `data/BDI/reports/bdi_YYYYMMDD_operador.txt` para úItimo processamento
3. Valide dados manualmente em: https://www.bcb.gov.br/publicacoes/boletimdiario

---

**Última Atualização:** 04/03/2026
**Status:** ✅ OPERACIONAL
