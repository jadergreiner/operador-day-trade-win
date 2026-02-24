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
3. Verifique se existe a arquitetura do projeto em {{docs\ARCHITECTURE.md}}.
3-1. Existe, siga com a atualização.
3.2. Não existe, crie a arquitetura nesta task.
4. Distribuia tasks de forma paralela entre os membros da Squad para executarem de forma autonoma
5. Valide os impactos no operador `agente_autonomo\INICIAR.BAT`
6. Execute os testes unitários e integração
7. Atualize as documentações
8. Ao finalizar, complete a rodada de atualizações atualizando status em  {{docs\STATUS_ENTREGAS.md}} e {{docs\ROADMAP.md}}
9. Sempre que necessário, atualize `agente_autonomo\INICIAR.BAT`
10. Faça um teste mínimo garantindo que o operador `agente_autonomo\INICIAR.BAT` não quebrou e está minimamente funcional.
11. Aplicar lint em todos os arquivos criados
12. Prepare commit e push

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