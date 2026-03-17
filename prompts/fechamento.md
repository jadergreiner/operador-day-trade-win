# Revisao Pos-Pregao — 4 Agentes Operacionais

**Papel:** Head of Trading e Senior Automation Engineer

Utilize os dados REAIS presentes nos arquivos do workspace para responder
ao checklist de fechamento abaixo. Nao simule dados; se uma informacao nao
estiver disponivel nos logs, reporte como "Dados nao encontrados".

## INSTRUCOES DE EXECUCAO

1. Analise os 4 scripts de entrada dos agentes operacionais:
   - `INICIAR_MICRO_TENDENCIA_AUTO_TRADE.bat`
   - `INICIAR_AGENTE_RL_DIRETO.bat`
   - `INICIAR_AGENTE_RL_5000.bat`
   - `INICIAR_DIARIOS.bat`
2. Analise os arquivos de log recentes em `outputs/*.log` e os arquivos
   de posicao em `outputs/agente_posicao_*.json`.
3. Consulte `docs/BACKLOG.md` para contexto dos itens pendentes.
4. Responda aos 10 pontos do "Checklist de Fechamento" com base
   estritamente nas evidencias encontradas no codigo e nos logs.

## CHECKLIST DE FECHAMENTO

1. **Aderencia ao Sinal:** Verifique nos logs se houve discrepancia
   entre sinal disparado e ordem enviada (por agente).
2. **Slippage e Latencia:** Calcule a diferenca entre o timestamp do
   sinal e a execucao da ordem (se disponivel).
3. **Gestao de Drawdown:** Identifique o maior rebaixamento registrado
   no log de cada agente no pregao de hoje.
4. **Relacao Win/Loss:** Extraia a taxa de acerto real por agente
   (`resultado=WIN` vs `resultado=LOSS` nos logs).
5. **Exposicao no VWAP:** Analise se os scripts registram entradas
   proximas a VWAP; reporte "Dados nao encontrados" se ausente.
6. **Custo Operacional:** Estime os custos com base no volume de
   contratos executados (emolumentos B3 WIN: ~R$1,00/contrato/lado).
7. **Comportamento em Volatilidade:** Verifique se houve picos de
   volatilidade nao tratados, rollover de contrato nao detectado ou
   interrupcao inesperada de sessao.
8. **Concentracao de Volume:** Mapeie o horario das maiores execucoes
   por agente.
9. **Analise de Logs:** Reporte erros criticos encontrados:
   `NameError`, `OrderExecutionError`, `Terminal mismatch`,
   timeouts de conexao, e qualquer `[ERROR]` recorrente.
10. **Escalabilidade:** Avalie se o volume atual agride o book
    (liquidez media do WIN$N: ~400k-600k contratos/dia).

## OUTPUT ESPERADO

Apos o checklist, identifique as **OPORTUNIDADES DE EVOLUCAO** tecnicas
encontradas nos logs do dia que ainda nao estejam no `docs/BACKLOG.md`.

Para cada oportunidade nova, adicione ao `docs/BACKLOG.md` seguindo
o padrao de entrada existente no arquivo:

- **Status:** PENDENTE
- **Origem:** Fechamento diario DD/MM/AAAA — [descricao da evidencia]
- **Problema tecnico:** [causa raiz identificada no log]
- **Entregar:** [lista de acoes concretas]
- **Arquivo afetado:** [caminho do arquivo]
- **Agente impactado:** [nome do .bat]
- **Pronto quando:** [criterio de aceite mensuravel]
