# Contratos de Dados

Este diretorio centraliza contratos de dados versionados do projeto.

## Estado atual

Os contratos ainda estao distribuidos em documentos arquiteturais e de
modelagem.

Referencias atuais:

- [../ADRS.md](../ADRS.md)
- [../MODELAGEM_DE_DADOS.md](../MODELAGEM_DE_DADOS.md)
- [../REGRAS_DE_NEGOCIO.md](../REGRAS_DE_NEGOCIO.md)

## Padrao alvo

Cada contrato deve seguir versionamento explicito por entidade:

- `<entidade>_v1.md`
- `<entidade>_v2.md` (quando houver breaking change)

## Proximos passos

1. Extrair contratos embutidos em ADRs.
2. Publicar contratos em arquivos dedicados nesta pasta.
3. Registrar alteracoes em `docs/CHANGELOG.md`.

