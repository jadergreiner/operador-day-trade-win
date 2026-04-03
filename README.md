# operador-day-trade-win

Resumo rápido do repositório e nota de dependências relevantes.

Este repositório implementa um sistema de trading automatizado com 4
launchers principais e vários agentes (RL, Micro Tendência, Diários,
Monitor). Para carregar configurações canônicas (ex.: `profit_protection.yaml`)
utilizamos `pydantic` para validação/typing e `pyyaml` para parsing de YAML.

Dependências importantes (adicionadas por `Profit Protection v2`):

- `pydantic` — validação e modelos tipados para `ProfitProtectionProfile`.
- `pyyaml` — carregamento do arquivo `profit_protection.yaml`.

Nota operacional:

- Antes de atualizar agentes em produção, atualize o ambiente virtual
  (`.venv`) ou `pyproject.toml`/`requirements.txt` para incluir essas libs.
- Falha de import destas libs causa erro de arranque; o código tem fallback
  que evita crash, mas o comportamento esperado (profiles/telemetria) ficará
  restrito até a instalação.

Veja `docs/REGRAS_DE_NEGOCIO.md` e `docs/BACKLOG.md` para instruções de
operação e cards de backlog relacionados.
