"""
ROADMAP-MICRO-03: Repositorio de HistoricoFechamento.

Responsabilidades:
- Interface para leitura e atualizacao de historicos de fechamento
- Implementacao JSON lendo arquivos produzidos por MotorDecisaoIsolado

Pipeline:
    TradeOutcomeReconciler chama atualizar_resultado_fechamento()
    -> JsonFechamentoRepository faz write-back no JSON do motor
"""

import json
import logging
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

_VALORES_RESULTADO_VALIDOS = frozenset({"WIN", "LOSS", "BREAKEVEN"})


class IFechamentoRepository(ABC):
    """Interface para repositorio de historicos de fechamento."""

    @abstractmethod
    def atualizar_resultado_fechamento(
        self,
        ticket: int,
        resultado: str,
        pnl: float,
    ) -> bool:
        """Persiste resultado (WIN/LOSS/BREAKEVEN) para o ticket.

        Args:
            ticket: ID da posicao.
            resultado: Literal "WIN", "LOSS" ou "BREAKEVEN".
            pnl: Valor de pnl_reais associado ao fechamento.

        Returns:
            True se o registro foi encontrado e atualizado; False caso contrario.

        Raises:
            ValueError: Se ``resultado`` nao for um dos literais validos.
        """
        ...

    @abstractmethod
    def listar_sem_resultado(
        self,
        agent_id: str,
        magic_number: Optional[int] = None,
    ) -> List[Dict[str, Any]]:
        """Retorna fechamentos cujo resultado ainda e NULL para o agente.

        Quando ``magic_number`` for None, nao aplica filtro por magic.

        Args:
            agent_id: Identificador do agente.
            magic_number: Numero magico do agente; None para sem filtro.
        """
        ...

    @abstractmethod
    def obter_resultado_local(self, ticket: int) -> Optional[str]:
        """Retorna o resultado classificado para um ticket, ou None.

        Retorna None se o ticket nao existir ou se resultado ainda e NULL.

        Args:
            ticket: ID da posicao.
        """
        ...


class JsonFechamentoRepository(IFechamentoRepository):
    """Repositorio que le/escreve no JSON produzido por MotorDecisaoIsolado.

    O arquivo tem o padrao: ``{data_dir}/historico_fechamentos_{agent_id}.json``
    e contem uma lista de objetos serializados de HistoricoFechamento.
    """

    def __init__(self, agent_id: str, data_dir: Path) -> None:
        self._agent_id = agent_id
        self._data_dir = Path(data_dir)
        self._arquivo = self._data_dir / f"historico_fechamentos_{agent_id}.json"

    # ------------------------------------------------------------------
    # Helpers internos
    # ------------------------------------------------------------------

    def _carregar(self) -> List[Dict[str, Any]]:
        if not self._arquivo.exists():
            return []
        try:
            conteudo = self._arquivo.read_text(encoding="utf-8")
            dados = json.loads(conteudo)
            return dados if isinstance(dados, list) else []
        except (json.JSONDecodeError, OSError) as exc:
            logger.warning(
                "JsonFechamentoRepository: erro ao ler %s: %s",
                self._arquivo,
                exc,
            )
            return []

    def _salvar(self, registros: List[Dict[str, Any]]) -> None:
        self._data_dir.mkdir(parents=True, exist_ok=True)
        self._arquivo.write_text(
            json.dumps(registros, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

    # ------------------------------------------------------------------
    # Interface publica
    # ------------------------------------------------------------------

    def atualizar_resultado_fechamento(
        self,
        ticket: int,
        resultado: str,
        pnl: float,
    ) -> bool:
        if resultado not in _VALORES_RESULTADO_VALIDOS:
            raise ValueError(
                f"resultado invalido: {resultado!r}. "
                f"Valores aceitos: {sorted(_VALORES_RESULTADO_VALIDOS)}"
            )

        registros = self._carregar()
        atualizado = False
        for reg in registros:
            if int(reg.get("ticket", -1)) == int(ticket):
                reg["resultado"] = resultado
                reg["pnl_reais"] = float(pnl)
                atualizado = True
                break

        if atualizado:
            self._salvar(registros)

        return atualizado

    def listar_sem_resultado(
        self,
        agent_id: str,
        magic_number: Optional[int] = None,
    ) -> List[Dict[str, Any]]:
        registros = self._carregar()
        resultado = [
            r
            for r in registros
            if r.get("resultado") is None
            and r.get("agent_id") == agent_id
        ]
        if magic_number is not None:
            resultado = [
                r for r in resultado
                if int(r.get("magic_number", -1)) == int(magic_number)
            ]
        return resultado

    def obter_resultado_local(self, ticket: int) -> Optional[str]:
        for reg in self._carregar():
            if int(reg.get("ticket", -1)) == int(ticket):
                return reg.get("resultado")  # str ou None
        return None
