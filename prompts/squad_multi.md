id = S2-2
TASK = "Calibrador ATR Dinâmico"

# Desenvolver {{id}} - {{TASK}}

Crie uma Squad Multidisciplinar {{docs\BOARD_MULTIDISCIPLINAR.json}}

[
"id": 2,
"nome": "Coordenadora de Governança",
"id": 3,
"nome": "Eng Sr",
"id": 4,
"nome": "ML Expert",
"id": 6,
"nome": "Arquiteto de Sistemas",
"id": 7,
"nome": "Infra DevOps",
"id": 8,
"nome": "Head de Documentação & Standards",
"id": 9,
"nome": "Operações",
"id": 11,
"nome": "Data Engineer",
"id": 12,
"nome": "QA Automation",
"id": 13,
"nome": "Trader Líder",
"id": 14,
"nome": "Product Owner",
"id": 17,
"nome": "Doc Advocate",
]

1. Verifique os detalhes da entrega {{id}} nas docs {{docs\STATUS_ENTREGAS.md}} e {{docs\ROADMAP.md}}
2. Registre o estado de PRIORIZADO/ANDAMENTO nas DOCs necessárias para dar visibilidade
3. Verifique se existe a arquitetura do projeto em {{docs\ARCHITECTURE.md}}. Arquitetura deve estar totalmente integrado com modelo de dados {{docs\DATA_MODELS.md}}.
3-1. Existe, siga com a atualização.
3.2. Não existe, crie a arquitetura nesta task.
4. Verifique se existe a modelagem dos dados, diagrama e schema das tabelas em {{docs\DATA_MODELS.md}}.
4-1. Existe, siga com a atualização.
4.2. Não existe, crie a arquitetura nesta task.
4.3. Modelo de dados deve estar totalmente integrado a Arquitetura {{docs\ARCHITECTURE.md}}.
5. Distribuia tasks de forma paralela entre os membros da Squad para executarem de forma autonoma
6. Valide os impactos no operador `INICIAR_MICRO_TENDENCIA_AUTO_TRADE.bat`
7. Execute os testes unitários e integração. Testar todas as opções do menu.
8. Atualize as documentações
9. Ao finalizar, complete a rodada de atualizações atualizando status em  {{docs\STATUS_ENTREGAS.md}} e {{docs\ROADMAP.md}}
10. Sempre que necessário, atualize `INICIAR_MICRO_TENDENCIA_AUTO_TRADE.bat`
11. Faça um teste mínimo garantindo que o operador `INICIAR_MICRO_TENDENCIA_AUTO_TRADE.bat.BAT` não quebrou e está minimamente funcional.
12. Aplicar lint em todos os arquivos criados
13. Prepare commit e push

## Regras

1. Testes unitarios CASE-THEN-WHEN
2. Testes unitários verbosos em Português
3. Manter a cobertura de testes em 98%
4. Clean Code
5. Comece simples
6. Crie apenas o essencial
7. O ótimo é inimigo do bom
8. Design Patterns
9. Na dúvida, pergunte.
10. Antes de criar, isso não existe no código atual?
11. Sempre consultar a arquitetura e documentação.
12. Regra do escoteiro. Sempre deixo melhor que encontrei. Encontrei código legado, primeira vez comento. O sistema não quebrou, limpo.
13. Garantir a persistência de dados.
14. Garantir o aprendizado contínuo dos modelos
15. Sempre que necessário execute o treinamento/retreinamento dos modelos