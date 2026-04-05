"""Integracao do CoordinationSignalReader nos agentes RL (BLID-043).

Modulo fino que encapsula a verificacao de sinal de coordenacao antes da
abertura de posicao. Separado dos agentes RL para permitir teste unitario
sem dependencias pesadas (MT5, SQLAlchemy, pandas).

Uso nos agentes:

    from src.application.coordination_integration import (
        verificar_pode_abrir_posicao,
    )

    if not verificar_pode_abrir_posicao():
        continue  # nao abre posicao
"""

from __future__ import annotations

import logging
from typing import Optional

from src.application.coordination_signal_reader import CoordinationSignalReader

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Instancia padrao modulo-level — substituivel em testes via patch
# ---------------------------------------------------------------------------
_reader_padrao: CoordinationSignalReader = CoordinationSignalReader()


# ---------------------------------------------------------------------------
# API publica
# ---------------------------------------------------------------------------


def verificar_pode_abrir_posicao(
    reader: Optional[CoordinationSignalReader] = None,
) -> bool:
    """Verifica sinal de coordenacao antes de abrir posicao.

    Retorna False apenas quando o sinal e STOP_OPERACOES. Para todos os
    outros sinais (NORMAL, MODO_CONSERVADOR, MODO_DEFENSIVO) retorna True,
    pois apenas STOP_OPERACOES bloqueia abertura de novas posicoes.

    Arquivo ausente ou invalido resulta em True (fallback seguro, ADR-023).

    Args:
        reader: Leitor externo para injecao em testes. Se None, usa a
                instancia padrao ``_reader_padrao``.

    Returns:
        True se abertura de posicao e permitida, False se bloqueada.
    """
    r = reader if reader is not None else _reader_padrao
    if not r.pode_abrir_posicao():
        sinal = r.obter_sinal_atual()
        logger.warning(
            "[COORDINATION] Abertura bloqueada pelo CoordinationManager. "
            "Sinal: %s",
            sinal.value,
        )
        return False
    return True
