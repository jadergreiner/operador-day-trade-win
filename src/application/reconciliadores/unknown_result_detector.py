"""
ROADMAP-MICRO-03: Detector de Resultados Desconhecidos.

Responsabilidades:
- Identificar ordens com resultado IS NULL filtrando por magic_number.
- Consultar SQLite diretamente via detectar_por_db().
- Garantir isolamento: tickets de outros agentes nao aparecem.

Pipeline:
    UnknownResultDetector.detectar_lacunas() identifica tickets sem resultado
    -> TradeOutcomeReconciler.reconciliar_ordem() preenche resultado
    -> MT5SyncValidator.validar_sincronizacao() confirma consistencia
"""

import logging
import sqlite3
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

_RESULTADOS_VALIDOS = frozenset({"WIN", "LOSS", "BREAKEVEN"})


class UnknownResultDetector:
    """
    ROADMAP-MICRO-03: Detector de Resultados Desconhecidos.

    Detecta fechamentos sem resultado classificado, respeitando
    isolamento obrigatorio por magic_number.
    """

    def __init__(self, logger_inst: Optional[logging.Logger] = None) -> None:
        self._log = logger_inst or logging.getLogger(__name__)

    # ------------------------------------------------------------------
    # Interface publica principal
    # ------------------------------------------------------------------

    def detectar_lacunas(
        self,
        agent_id: str,
        magic_number: int,
        ordens_locais: List[Dict[str, Any]],
        ordens_mt5: List[Dict[str, Any]],
    ) -> List[str]:
        """Retorna tickets cujo resultado e None, filtrados por magic_number.

        Apenas tickets cujo ``magic_number`` coincide sao retornados.
        Tickets de outros agentes (magic_number diferente) sao ignorados
        silenciosamente.

        Args:
            agent_id: Identificador do agente chamador.
            magic_number: Numero magico que identifica o agente no MT5.
            ordens_locais: Lista de dicts com chaves ``ticket``,
                ``magic_number`` e ``resultado``.
            ordens_mt5: Lista de dicts com chave ``ticket`` representando
                ordens visiveis no MT5 para o agente.

        Returns:
            Lista ordenada de tickets (strings) sem resultado.

        Raises:
            ValueError: Se ``agent_id`` for vazio ou None.
        """
        if not agent_id:
            raise ValueError("agent_id nao pode ser vazio")

        lacunas: List[str] = []
        for ordem in ordens_locais:
            ticket_raw = ordem.get("ticket")
            if ticket_raw is None:
                continue

            ticket = str(ticket_raw).strip()
            if not ticket:
                continue

            ordem_magic = int(ordem.get("magic_number", -1))
            if ordem_magic != int(magic_number):
                continue

            if ordem.get("resultado") is None:
                lacunas.append(ticket)

        if not lacunas:
            self._log.info(
                "nenhuma lacuna detectada para agent_id=%s", agent_id
            )
            return []

        self._log.warning(
            "detectar_lacunas: %d lacuna(s) para agent_id=%s magic=%s",
            len(lacunas),
            agent_id,
            magic_number,
        )
        return sorted(lacunas)

    def detectar_por_db(
        self,
        db_path: Path,
        agent_id: Optional[str] = None,
        magic_number: Optional[int] = None,
    ) -> List[Dict[str, Any]]:
        """Consulta SQLite e retorna registros com resultado IS NULL.

        Cria a tabela ``reconciliation_log`` se nao existir.
        Nao retorna posicoes cujo ``status`` indica aberta.

        Args:
            db_path: Caminho para o arquivo SQLite.
            agent_id: Filtro opcional por agente.
            magic_number: Filtro opcional por magic_number.

        Returns:
            Lista de dicts com os registros sem resultado.
        """
        db_path = Path(db_path)
        conn = sqlite3.connect(str(db_path))
        try:
            conn.row_factory = sqlite3.Row
            conn.execute("""
                CREATE TABLE IF NOT EXISTS reconciliation_log (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    ticket INTEGER NOT NULL,
                    agent_id TEXT NOT NULL,
                    resultado TEXT,
                    fonte TEXT,
                    status TEXT,
                    timestamp TEXT,
                    UNIQUE(ticket, agent_id)
                )
            """)
            conn.commit()

            query = """
                SELECT * FROM historico_fechamentos
                WHERE resultado IS NULL
                AND (status IS NULL OR UPPER(status) != 'ABERTA')
            """
            params: List[Any] = []

            if agent_id is not None:
                query += " AND agent_id = ?"
                params.append(agent_id)

            if magic_number is not None:
                query += " AND magic_number = ?"
                params.append(int(magic_number))

            cursor = conn.execute(query, params)
            return [dict(row) for row in cursor.fetchall()]
        except sqlite3.OperationalError as exc:
            self._log.debug("detectar_por_db: OperationalError: %s", exc)
            return []
        finally:
            conn.close()

    # ------------------------------------------------------------------
    # Metodo legado mantido para compatibilidade
    # ------------------------------------------------------------------

    def validar_integridade_resultado(self, resultado: Dict[str, Any]) -> bool:
        """Valida se os dados do resultado sao consistentes (Preco, Volume, Profit)."""
        if not resultado:
            return False

        required = ["price", "volume", "profit"]
        for chave in required:
            if chave not in resultado:
                return False

            valor = resultado[chave]
            if valor is None:
                return False

            if chave == "volume" and isinstance(valor, bool):
                return False

        return True

