# ROLE: Head of Trading & Senior Automation Engineer
# CONTEXT: Post-Market Review of "INICIAR_MICRO_TENDENCIA_AUTO_TRADE.bat"

Utilize os dados REAIS presentes nos arquivos do workspace para responder ao checklist de fechamento abaixo. Não simule dados; se uma informação não estiver disponível nos logs, reporte como "Dados não encontrados".

## INSTRUÇÕES DE EXECUÇÃO:
1. Analise o arquivo `INICIAR_MICRO_TENDENCIA_AUTO_TRADE.bat` para entender a lógica de execução.
2. Analise os arquivos de log recentes (ex: `logs/*.log` ou saídas de console salvas) e o arquivo `docs\BACKLOG_UNIFICADO.md`.
3. Responda aos 10 pontos do "Checklist de Fechamento" com base estritamente nas evidências encontradas no código e logs.

## CHECKLIST DE FECHAMENTO:
1. **Aderência ao Sinal:** Verifique nos logs se houve discrepância entre sinal disparado e ordem enviada.
2. **Slippage e Latência:** Calcule a diferença entre o timestamp do sinal e a execução (se disponível).
3. **Gestão de Drawdown:** Identifique o maior rebaixamento registrado no log do pregão de hoje.
4. **Relação Win/Loss:** Extraia a taxa de acerto real das micro tendências.
5. **Exposição no VWAP:** Analise como o script tratou ordens próximas à VWAP.
6. **Custo Operacional:** Projete os custos com base no volume de contratos operados hoje.
7. **Comportamento em Notícias:** Verifique se o script foi interrompido ou se houve picos de volatilidade não tratados.
8. **Concentração de Volume:** Mapeie o horário das maiores execuções.
9. **Análise de Logs:** Reporte erros de sintaxe ou timeouts de conexão encontrados.
10. **Escalabilidade:** Avalie se o volume atual agride o book (análise de liquidez média do WIN).

## OUTPUT ESPERADO:
Após o checklist, sintetize **3 OPORTUNIDADES DE EVOLUÇÃO** técnicas para o script `.bat`.
Formate a saída como um PR (Pull Request) de atualização para o arquivo `docs\BACKLOG_UNIFICADO.md`, seguindo o padrão:
- **ID:** [Auto-gerado]
- **Melhoria:** [Título]
- **Justificativa Técnica:** [Baseado nos dados de hoje]
- **Prioridade:** [Alta/Média/Baixa]