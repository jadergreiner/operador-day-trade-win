"""
conftest.py principal - Carrega todas as fixtures de submódulos

Pytest procura automaticamente por conftest.py e carrega todas as fixtures.
Este arquivo importa as fixtures de conftest_clean_architecture.py.
"""

# Importar todas as fixtures de conftest_clean_architecture
from .conftest_clean_architecture import (
    trade_id,
    sample_trade_outcome,
    sample_unknown_outcome,
    sample_multiple_outcomes,
    mt5_position_state,
    local_position_state,
    audit_entry,
    divergent_outcomes,
    timestamp_misalign,
)

__all__ = [
    "trade_id",
    "sample_trade_outcome",
    "sample_unknown_outcome",
    "sample_multiple_outcomes",
    "mt5_position_state",
    "local_position_state",
    "audit_entry",
    "divergent_outcomes",
    "timestamp_misalign",
]
