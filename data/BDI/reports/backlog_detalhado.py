#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
BACKLOG DE OPORTUNIDADES - PROCESSAMENTO BDI
=============================================

Arquivo de rastreamento de tarefas gerado automaticamente
Data: 20/02/2026
Status: Pronto para execução

Instruções:
1. Copie as linhas de comando terraform/script conforme necessário
2. Atualize o status das tarefas conforme avance
3. Adicione logs e observações em cada task
"""

# BACKLOG DE EXECUÇÃO IMEDIATA (Próximo Pregão: 21/02/2026)

BACKLOG = {
    "ALTA_PRIORIDADE": [
        # Nenhuma tarefa de alta prioridade no período analisado
    ],

    "MEDIA_PRIORIDADE": [
        {
            "id": "TASK-001",
            "titulo": "Análise de Posições a Termo",
            "descricao": "Extrair e analisar maiores posições abertas para identificar tendências institucionais",
            "data_criacao": "2026-02-20",
            "deadline": "2026-02-21",
            "responsavel": "Operador",
            "esforço_horas": 2.0,
            "status": "NOT_STARTED",  # NOT_STARTED | IN_PROGRESS | DONE | BLOCKED
            "prioridade": "MÉDIA",
            "categoria": "Operações a Termo",
            "tarefas_subtarefa": [
                {
                    "numero": 1,
                    "descricao": "Acessar BDI de 12/02/2026",
                    "status": "NOT_STARTED",
                    "notas": ""
                },
                {
                    "numero": 2,
                    "descricao": "Localizar seção 'Posições em Aberto' no BDI",
                    "status": "NOT_STARTED",
                    "notas": ""
                },
                {
                    "numero": 3,
                    "descricao": "Extrair top 20 ações com maior open interest em termo",
                    "status": "NOT_STARTED",
                    "notas": ""
                },
                {
                    "numero": 4,
                    "descricao": "Calcular razão compra/venda em cada posição",
                    "status": "NOT_STARTED",
                    "notas": ""
                },
                {
                    "numero": 5,
                    "descricao": "Documentar oportunidades de spreads identificadas",
                    "status": "NOT_STARTED",
                    "notas": ""
                }
            ],
            "metricas_sucesso": [
                "Top 20 ações identificadas",
                "Razão compra/venda calculada para cada",
                "Preço spot vs preço a termo registrado",
                "Opportunidades de arbitragem documentadas"
            ],
            "riscos": [
                "Dados incompletos no BDI",
                "Mudança de preços entre coleta e análise"
            ],
            "notas": "Essa análise identifica fluxo institucional e comportamento dos grandes players"
        },

        {
            "id": "TASK-002",
            "titulo": "Mapeamento de Ações Mais Negociadas",
            "descricao": "Listar e preparar setup técnico para top 50 ações por volume",
            "data_criacao": "2026-02-20",
            "deadline": "2026-02-21",
            "responsavel": "Operador",
            "esforço_horas": 1.5,
            "status": "NOT_STARTED",
            "prioridade": "MÉDIA",
            "categoria": "Swing Trading",
            "tarefas_subtarefa": [
                {
                    "numero": 1,
                    "descricao": "Extrair tabela de ações mais negociadas do BDI 12/02",
                    "status": "NOT_STARTED",
                    "notas": ""
                },
                {
                    "numero": 2,
                    "descricao": "Calcular volume diário médio dos últimos 20 dias",
                    "status": "NOT_STARTED",
                    "notas": ""
                },
                {
                    "numero": 3,
                    "descricao": "Identificar ações em breakout acima de 5 dias",
                    "status": "NOT_STARTED",
                    "notas": ""
                },
                {
                    "numero": 4,
                    "descricao": "Definir níveis de stop loss e take profit",
                    "status": "NOT_STARTED",
                    "notas": ""
                },
                {
                    "numero": 5,
                    "descricao": "Criar watchlist em plataforma de negociação",
                    "status": "NOT_STARTED",
                    "notas": ""
                }
            ],
            "metricas_sucesso": [
                "Top 50 ações listadas e analisadas",
                "Setup técnico definido para cada ação",
                "Alertas configurados na plataforma",
                "Plano de entrada/saída documentado"
            ],
            "riscos": [
                "Mudança de ranking de volume entre coleta e pregão",
                "Notícias overnight que alteram os ativos"
            ],
            "notas": "Foco em ativos de alta liquidez para minimizar slippage"
        },

        {
            "id": "TASK-003",
            "titulo": "Setup para Scalping em WIN",
            "descricao": "Preparar infraestrutura para executar scalping em mini índice",
            "data_criacao": "2026-02-20",
            "deadline": "2026-02-21",
            "responsavel": "Operador",
            "esforço_horas": 1.0,
            "status": "NOT_STARTED",
            "prioridade": "MÉDIA",
            "categoria": "Day Trading",
            "tarefas_subtarefa": [
                {
                    "numero": 1,
                    "descricao": "Abrir plataforma de negociação antes de 06:00",
                    "status": "NOT_STARTED",
                    "notas": ""
                },
                {
                    "numero": 2,
                    "descricao": "Configurar gráfico de 5 minutos do WIN",
                    "status": "NOT_STARTED",
                    "notas": ""
                },
                {
                    "numero": 3,
                    "descricao": "Desenhar suportes/resistências dos últimos 3 pregões",
                    "status": "NOT_STARTED",
                    "notas": ""
                },
                {
                    "numero": 4,
                    "descricao": "Configurar alertas de volume (>média 20 velas)",
                    "status": "NOT_STARTED",
                    "notas": ""
                },
                {
                    "numero": 5,
                    "descricao": "Definir tamanho máximo de posição e stop loss",
                    "status": "NOT_STARTED",
                    "notas": ""
                },
                {
                    "numero": 6,
                    "descricao": "Conectar orders pre-setadas para 1.5x range de consolidação",
                    "status": "NOT_STARTED",
                    "notas": ""
                }
            ],
            "metricas_sucesso": [
                "Plataforma operacional antes de 06:00",
                "Gráficos configurados corretamente",
                "Suportes/resistências desenhados",
                "Alertas ativos",
                "Máximo 5 operações negativas por dia"
            ],
            "riscos": [
                "Problemas técnicos (desconexão, latência)",
                "Posicionamento incorreto se mercado gap",
                "Liquidez insuficiente em horários off-peak"
            ],
            "notas": "Esta é a operação de maior potencial ROI do período - priorize setup adequado"
        },

        {
            "id": "TASK-004",
            "titulo": "Integração: Dados de Opções da B3",
            "descricao": "Buscar e integrar fonte de dados de opções para análise de IV",
            "data_criacao": "2026-02-20",
            "deadline": "2026-02-28",
            "responsavel": "Área Técnica",
            "esforço_horas": 4.0,
            "status": "NOT_STARTED",
            "prioridade": "MÉDIA",
            "categoria": "Desenvolvimento",
            "tarefas_subtarefa": [
                {
                    "numero": 1,
                    "descricao": "Pesquisar APIs disponíveis da B3 para dados de opções",
                    "status": "NOT_STARTED",
                    "notas": ""
                },
                {
                    "numero": 2,
                    "descricao": "Contatar B3 para acesso a dados em tempo real/EOD",
                    "status": "NOT_STARTED",
                    "notas": ""
                },
                {
                    "numero": 3,
                    "descricao": "Implementar parser para consumir dados",
                    "status": "NOT_STARTED",
                    "notas": ""
                },
                {
                    "numero": 4,
                    "descricao": "Calcular IV implícita usando modelo Black-Scholes",
                    "status": "NOT_STARTED",
                    "notas": ""
                },
                {
                    "numero": 5,
                    "descricao": "Gerar relatório de opções em relatório BDI",
                    "status": "NOT_STARTED",
                    "notas": ""
                }
            ],
            "metricas_sucesso": [
                "API de opções integrada",
                "IV calculada corretamente",
                "Relatório de opções gerado automaticamente",
                "Histórico de 30 dias das IVs"
            ],
            "riscos": [
                "Custo de acesso à API",
                "Documentação inadequada da B3",
                "Latência nos dados"
            ],
            "notas": "Gap crítico - impossibilidade atual de analisar estruturas de opções"
        },

        {
            "id": "TASK-005",
            "titulo": "Integração: Dados Intradiários de Pregão",
            "descricao": "Integrar feed de pregão em tempo real ou com latência EOD",
            "data_criacao": "2026-02-20",
            "deadline": "2026-03-05",
            "responsavel": "Área Técnica",
            "esforço_horas": 8.0,
            "status": "NOT_STARTED",
            "prioridade": "MÉDIA",
            "categoria": "Desenvolvimento",
            "tarefas_subtarefa": [
                {
                    "numero": 1,
                    "descricao": "Avaliar opções: Bloomberg, Reuters, Terra, Economática",
                    "status": "NOT_STARTED",
                    "notas": ""
                },
                {
                    "numero": 2,
                    "descricao": "Testar período de trial de cada provedor",
                    "status": "NOT_STARTED",
                    "notas": ""
                },
                {
                    "numero": 3,
                    "descricao": "Seleccionar provedor com melhor custo-benefício",
                    "status": "NOT_STARTED",
                    "notas": ""
                },
                {
                    "numero": 4,
                    "descricao": "Implementar conexão com API do provedor",
                    "status": "NOT_STARTED",
                    "notas": ""
                },
                {
                    "numero": 5,
                    "descricao": "Armazenar candles em banco de dados (1min, 5min, 15min)",
                    "status": "NOT_STARTED",
                    "notas": ""
                },
                {
                    "numero": 6,
                    "descricao": "Calcular indicadores automaticamente (ATR, RSI, MACD)",
                    "status": "NOT_STARTED",
                    "notas": ""
                },
                {
                    "numero": 7,
                    "descricao": "Gerar pivots e suportes/resistências automáticos diariamente",
                    "status": "NOT_STARTED",
                    "notas": ""
                },
                {
                    "numero": 8,
                    "descricao": "Testar setup em backtest com 3 meses de histórico",
                    "status": "NOT_STARTED",
                    "notas": ""
                }
            ],
            "metricas_sucesso": [
                "Feed intradiário operacional",
                "Candles em 1min, 5min e 15min armazenadas",
                "Indicadores calculados em tempo real/EOD",
                "Dashboard com pivots e S/R",
                "Backtest executado com pelo menos 3 meses de dados"
            ],
            "riscos": [
                "Alto custo de assinatura",
                "Latência insuficiente",
                "Problemas de integração com sistema existente"
            ],
            "notas": "Gap crítico #2 - Necessário para operações intraday com confiabilidade"
        },

        {
            "id": "TASK-006",
            "titulo": "Monitoramento: Fluxo de Capital / Participação de Investidores",
            "descricao": "Acompanhar e documentar participação por tipo de investidor",
            "data_criacao": "2026-02-20",
            "deadline": "Contínuo (20 min/dia)",
            "responsavel": "Analista",
            "esforço_horas": 0.33,  # 20 minutos diários
            "status": "NOT_STARTED",
            "prioridade": "MÉDIA",
            "categoria": "Monitoramento",
            "tarefas_subtarefa": [
                {
                    "numero": 1,
                    "descricao": "Acessar B3 > Relatórios > Participação de Investidores diariamente",
                    "status": "NOT_STARTED",
                    "notas": ""
                },
                {
                    "numero": 2,
                    "descricao": "Registrar percentual de cada tipo: PF, PJ, Exterior, Government",
                    "status": "NOT_STARTED",
                    "notas": ""
                },
                {
                    "numero": 3,
                    "descricao": "Plotar gráfico de tendência semanal",
                    "status": "NOT_STARTED",
                    "notas": ""
                },
                {
                    "numero": 4,
                    "descricao": "Alertar se mudança > 2% em um dia",
                    "status": "NOT_STARTED",
                    "notas": ""
                },
                {
                    "numero": 5,
                    "descricao": "Documentar insights em relatório semanal",
                    "status": "NOT_STARTED",
                    "notas": ""
                }
            ],
            "metricas_sucesso": [
                "Relatório diário atualizado",
                "Gráfico de tendência semanal",
                "Alertas funcionando",
                "Correlação com eventos de mercado documentada"
            ],
            "riscos": [
                "Dados divulgados com delay",
                "Formato de relatório pode mudar",
                "Anomalias difíceis de interpretar"
            ],
            "notas": "Ajuda a entender comportamento institucional e plotar tendências"
        },

        {
            "id": "TASK-007",
            "titulo": "Desenvolvimento: Módulo de Cálculo de Correlações",
            "descricao": "Implementar cálculo automático de correlações entre pares",
            "data_criacao": "2026-02-20",
            "deadline": "2026-03-10",
            "responsavel": "Área Técnica",
            "esforço_horas": 6.0,
            "status": "NOT_STARTED",
            "prioridade": "MÉDIA",
            "categoria": "Desenvolvimento",
            "tarefas_subtarefa": [
                {
                    "numero": 1,
                    "descricao": "Coletar histórico de preços últimos 252 dias (1 ano útil)",
                    "status": "NOT_STARTED",
                    "notas": ""
                },
                {
                    "numero": 2,
                    "descricao": "Implementar cálculo de correlação usando Pandas/NumPy",
                    "status": "NOT_STARTED",
                    "notas": ""
                },
                {
                    "numero": 3,
                    "descricao": "Gerar matriz de correlação para top 50 ações do IBOV",
                    "status": "NOT_STARTED",
                    "notas": ""
                },
                {
                    "numero": 4,
                    "descricao": "Identificar pares com alta correlação positiva (hedge)",
                    "status": "NOT_STARTED",
                    "notas": ""
                },
                {
                    "numero": 5,
                    "descricao": "Identificar pares com alta correlação negativa (pair trade)",
                    "status": "NOT_STARTED",
                    "notas": ""
                },
                {
                    "numero": 6,
                    "descricao": "Gerar novo relatório com análise de pares",
                    "status": "NOT_STARTED",
                    "notas": ""
                }
            ],
            "metricas_sucesso": [
                "Matriz de correlação gerada",
                "Pares com correlação >0.8 identificados",
                "Pares com correlação <-0.6 identificados",
                "Relatório com oportunidades de pair trading",
                "Seleção de hedges para operações"
            ],
            "riscos": [
                "Correlação pode não ser estável no tempo",
                "Dados históricos podem ter gaps",
                "Custos de execução podem eliminar lucro do pair trade"
            ],
            "notas": "Útil para estratégias de longo prazo e risk management"
        }
    ],

    "BAIXA_PRIORIDADE": []
}

# EXEMPLO DE COMO USAR ESTE ARQUIVO:

"""
# Para atualizar uma tarefa:
BACKLOG['MEDIA_PRIORIDADE'][0]['status'] = 'IN_PROGRESS'
BACKLOG['MEDIA_PRIORIDADE'][0]['notas'] = 'Iniciado em 21/02/2026 às 06:30'

# Para marcar subtarefa como concluída:
BACKLOG['MEDIA_PRIORIDADE'][0]['tarefas_subtarefa'][0]['status'] = 'DONE'
BACKLOG['MEDIA_PRIORIDADE'][0]['tarefas_subtarefa'][0]['notas'] = 'Completado com sucesso'

# Para extrair resumo de status:
total_tasks = len(BACKLOG['MEDIA_PRIORIDADE'])
not_started = sum(1 for t in BACKLOG['MEDIA_PRIORIDADE'] if t['status'] == 'NOT_STARTED')
in_progress = sum(1 for t in BACKLOG['MEDIA_PRIORIDADE'] if t['status'] == 'IN_PROGRESS')
done = sum(1 for t in BACKLOG['MEDIA_PRIORIDADE'] if t['status'] == 'DONE')

print(f"Total: {total_tasks}")
print(f"Not Started: {not_started}")
print(f"In Progress: {in_progress}")
print(f"Done: {done}")
"""

if __name__ == "__main__":
    import json

    # Salva o backlog em JSON
    with open('backlog_detalhado.json', 'w', encoding='utf-8') as f:
        json.dump(BACKLOG, f, ensure_ascii=False, indent=2)

    # Exibe resumo
    print("=" * 80)
    print("RESUMO DO BACKLOG")
    print("=" * 80)
    print(f"\nTarefas de ALTA prioridade: {len(BACKLOG['ALTA_PRIORIDADE'])}")
    print(f"Tarefas de MÉDIA prioridade: {len(BACKLOG['MEDIA_PRIORIDADE'])}")
    print(f"Tarefas de BAIXA prioridade: {len(BACKLOG['BAIXA_PRIORIDADE'])}")

    print(f"\nTotal de tarefas: {len(BACKLOG['ALTA_PRIORIDADE']) + len(BACKLOG['MEDIA_PRIORIDADE']) + len(BACKLOG['BAIXA_PRIORIDADE'])}")

    total_horas = sum(t.get('esforço_horas', 0) for t in BACKLOG['MEDIA_PRIORIDADE'])
    print(f"\nEsforço total estimado: {total_horas:.1f} horas")

    print("\n" + "=" * 80)
    print("TAREFAS IMEDIATAS (Próximo Pregão: 21/02/2026)")
    print("=" * 80)
    for task in BACKLOG['MEDIA_PRIORIDADE'][:3]:
        print(f"\n✓ {task['id']}: {task['titulo']}")
        print(f"  Responsável: {task['responsavel']}")
        print(f"  Esforço: {task['esforço_horas']} horas")
        print(f"  Deadline: {task['deadline']}")

    print("\n" + "=" * 80)
