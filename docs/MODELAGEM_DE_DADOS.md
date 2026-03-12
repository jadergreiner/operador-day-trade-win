# Modelagem de Dados Canonica

## Artefatos P0-2

### 1) `data/backtest/backtest_results.json`

Campos minimos:

- `timestamp`: string ISO-8601
- `summary`:
  - `mean_sharpe`: float
  - `mean_win_rate`: float
  - `mean_max_drawdown`: float
  - `consistency_std`: float (canonico)
  - `mean_monthly_consistency`: float (legado para compatibilidade)
  - `total_folds`: int
  - `total_trades`: int
  - `mean_pnl`: float
- `folds`: lista de objetos com metricas por fold

### 2) `data/backtest/gate2_decision.json`

Campos minimos:

- `decision`: `"PASS"` ou `"FAIL"`
- `criteria`: lista de criterios avaliados
- `all_passed`: bool
- `recommendation`: string

### 3) `data/backtest/p0_2_status.json`

Campos minimos:

- `completed`: bool
- `gate2_passed`: bool
- `timestamp`: string ISO-8601
- `backtest_results`: path string
- `reports_dir`: path string
- `decision`: `"PASS"` ou `"FAIL"`

## Contrato de Compatibilidade

- Consumidores novos devem ler `consistency_std`.
- Consumidores antigos podem usar `mean_monthly_consistency`.
- `check_p0_2_status.py` consome decisao em `data/backtest/gate2_decision.json`.
