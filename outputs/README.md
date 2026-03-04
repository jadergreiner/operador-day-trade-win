# Outputs Directory

Diretório organizado para artefatos gerados (relatórios, análises, testes, auditoria).

## Estrutura

```
outputs/
├── audits/          Auditoria de isolamento de terminal MT5
│   ├── AUDITORIA_MT5_ISOLAMENTO_04Mar.md
│   └── AUDITORIA_CRITICA_*.md
│
├── analysis/        Relatórios, análises, consolidações
│   ├── ANALISE_*.md
│   ├── RELATORIO_*.md
│   ├── CONSOLIDACAO_*.md
│   └── RESUMO_*.md
│
├── backtest/        Resultados de backtest e otimização
│   ├── backtest_results.json
│   ├── backtest_optimized_results.json
│   └── backtest_*.json
│
├── tests/           Resultados de testes
│   ├── pytest_results.txt
│   └── test_*.txt
│
└── misc/            Utilitários, configs, outputs diversos
    ├── requirements.txt
    ├── SPRINT2_DASHBOARD.json
    └── *.txt (configurações, notas)
```

## Uso

### Terminal Isolation Audit
```bash
$ outputs/audits/AUDITORIA_MT5_ISOLAMENTO_04Mar.md
# Último relatório de isolamento de terminal
```

### Backtest Results
```bash
$ outputs/backtest/backtest_optimized_results.json
# Resultados otimizados da validação de backtest
```

### Test Results
```bash
$ outputs/tests/pytest_results.txt
# Resultados dos testes unitários
```

### Analysis & Reports
```bash
$ outputs/analysis/
# Consolidações, análises, relatórios de sessão
```

## Limpeza Periódica

Para manter a estrutura limpa:
1. Arquivos muito antigos (> 30 dias) podem ser movidos para backup
2. Manter apenas últimas 5 análises de cada tipo
3. JSON files podem ser comprimidos se > 1MB

---

**Última reorganização:** 04/03/2026 (refactor: Output structure organization)
