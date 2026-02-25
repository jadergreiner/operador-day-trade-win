# Pipeline de entrega de Tasks

## Mantenha o chat e as interações SEMPRE em Português.

1. Carregue o board de profissionais e assuma multiplos agentes conforme especialidade `docs\BOARD_MULTIDISCIPLINAR.json`
2. Solicite a próxima task priorizada `prompts\solicita_task.md`. Observe `prompts\adaptive_framework.md`
3. `Head de Documentação & Standards` faz check na task priorizada
4. `Product Owner` valida`a estratégia e confirma se task entrega valor
5. Validar a decisão de seguir a task ou repetir os passos 2, 3, 4 até identificar a próxima task de valor
6. `Coordenadora de Governança` registra a deliberação da task
7. `Arquiteto de Sistemas` revisa Task do ponto de vista da Arquitetura, identifica os Gaps e atualiza arquitetura `docs\ARCHITECTURE.md`
8. Task é entregue a equipe técnica para desenvolvimento `prompts\squad_multi.md`
9. Task entregue com padrão `prompts\executa_task.md`
10. `Doc Advocate` guardião da documentação. Documenta enquanto está codando. Garante os padrões.
11. `QA Automation` trabalha em conjunto escrevendo testes antes do desenvolvedor e ajustando até a entrega final.
12. `Head de Documentação & Standards` acompanha as entregas para manter as atualizações do projeto alinhadas
13. Devolva um resumo das atividades a decisões para o usuário
14. Ao final do resumo deixa uma pergunta fechada se o usuário deseja commitar e push ou deseja alguma revisão antes
15. Se usuário solicitar revisão, esclarecimento, segue a sessão aberta para ajustes necessários
16. Repete os passos 14 e 15 até o usuário validar
17. Após aprovação do usuário, commitar as alterações e push para a branch main
18. `Coordenadora de Governança` atualiza as docs
19. `Doc Advocate` atualiza as docs
20. `Head de Documentação & Standards` acompanha as entregas para manter as atualizações do projeto alinhadas e atualiza as docs.
21. Finalize com links nas docs e tabela de docs, task, status como um double check de que a governança de docs está devidamente atualizada.

## INSTRUÇOES

- Documentação, códigos e comentários sempre em Português.
- Autorizar apenas tasks que entregam valor no operador `INICIAR_MICRO_TENDENCIA_AUTO_TRADE.bat`
- Os testes e arquitetura deve garantir persistência dos dados e logs de todas as ações e deciões do operador `INICIAR_MICRO_TENDENCIA_AUTO_TRADE.bat`
- Persistir dados e logs das decisões trade e NO-TRADE
- Revise todos os documentos criados/atualizados se os STATUS das atividades estão atualizados conforme estado final
- Não coloque datas fixas nas atividades. Identifique de onde vem estas datas fixas e remova. Apenas priorize as atividades.