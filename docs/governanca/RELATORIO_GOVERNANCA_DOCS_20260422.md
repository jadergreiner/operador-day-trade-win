# Relatorio de Governanca de Docs - 2026-04-22

## Escopo

Revisao do conjunto de documentos em `docs/` com foco em:

- ADRs
- Contratos de dados
- Modelos
- Referencias cruzadas

## Resultado executivo

- Status ADRs: parcial, com fonte principal em [../ADRS.md](../ADRS.md).
- Status contratos: gap estrutural, sem pasta canônica previa.
- Status modelos: parcial, concentrado em
  [../MODELAGEM_DE_DADOS.md](../MODELAGEM_DE_DADOS.md) e legados.
- Referencias cruzadas: alto volume de links locais quebrados em legado.

## Evidencias

- Grupo `docs/architecture`: parcial no repositório atual.
- Grupo `docs/contratos`: ausente antes desta consolidacao.
- Grupo `docs/governanca`: ausente antes desta consolidacao.
- Grupo `docs/modelos`: ausente antes desta consolidacao.
- Auditoria de links locais: ~145 links quebrados detectados na varredura.

## Acoes executadas

1. Criado alias de compatibilidade:
   - [../ADRS.md](../ADRS.md)
2. Formalizadas pastas canônicas:
   - [../contratos/README.md](../contratos/README.md)
   - [README.md](README.md)
   - [../modelos/README.md](../modelos/README.md)
3. Atualizada politica canônica em [../ADRS.md](../ADRS.md).

## GAPs remanescentes

1. Remediacao completa de links quebrados em `docs/legacy/`.
2. Materializacao de contratos versionados em `docs/contratos/`.
3. Consolidacao de modelos legados em `docs/modelos/`.

## Recomendacao

Executar remediation incremental por lote:

1. Corrigir links quebrados de alta criticidade fora de `docs/legacy/`.
2. Migrar contratos de dados de ADRs para arquivos versionados dedicados.
3. Publicar modelo conceitual e ER como fonte canônica em `docs/modelos/`.


