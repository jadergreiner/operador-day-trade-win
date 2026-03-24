"""
GateUnicaOrdemPorAgente: Impede abertura de segunda ordem com posicao ja aberta.

Responsabilidades:
- Verificar arquivos outputs/agente_posicao_{session_id}.json para o agent_id
- Bloquear se qualquer sessao do agente tiver posicao aberta
- Fail-safe: erros de leitura ou arquivos corrompidos = BLOQUEAR

Estrategia de identificacao:
- Cada arquivo de posicao tem campo "owner" com o identificador do agente
- Arquivos com owner == agent_id sao verificados quanto a "aberta": true
- Arquivos corrompidos (sem owner, sem aberta, JSON invalido) = BLOQUEIO
  (fail-safe: melhor bloquear erroneamente do que abrir posicao duplicada)

Pipeline:
    GerenciadorRiscoExterno.avaliar_todos()
    → GateUnicaOrdemPorAgente.verificar(agent_id)
    → ResultadoGateRisco.aprovado determina EXECUTE/REJECT no AC4

Status: v1.0 (24/03/2026)
Referencia: docs/BACKLOG.md (Camada Risco Externo - Unica Ordem)
"""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any

from src.domain.value_objects.risco_externo import ResultadoGateRisco

logger = logging.getLogger(__name__)

_CODIGO_GATE = "UNICA_ORDEM"


class GateUnicaOrdemPorAgente:
    """
    Impede que um agente abra nova ordem enquanto ja tem posicao aberta.

    Consulta os arquivos outputs/agente_posicao_*.json e verifica se algum
    deles pertence ao agent_id consultado e tem "aberta": true.

    Fail-safe: qualquer erro de leitura ou arquivo malformado e tratado
    como posicao aberta — bloqueia a nova entrada.

    Exemplo de uso:
        gate = GateUnicaOrdemPorAgente()
        resultado = gate.verificar("agente_rl_5000")
        if not resultado.aprovado:
            # rejeitar nova ordem
    """

    def __init__(
        self,
        outputs_dir: Path = Path("outputs"),
    ) -> None:
        self._outputs_dir = outputs_dir

    def verificar(self, agent_id: str) -> ResultadoGateRisco:
        """
        Verifica se o agente ja tem posicao aberta.

        Args:
            agent_id: Identificador do agente a verificar.

        Returns:
            ResultadoGateRisco com aprovado=False se posicao aberta encontrada.
        """
        arquivos_do_agente = self._listar_arquivos_do_agente(agent_id)

        if not arquivos_do_agente:
            return ResultadoGateRisco(
                aprovado=True,
                codigo_gate=_CODIGO_GATE,
                motivo="Nenhum arquivo de posicao encontrado para o agente",
                detalhes={"agent_id": agent_id, "arquivos_verificados": 0},
            )

        for arquivo in arquivos_do_agente:
            resultado = self._verificar_arquivo(arquivo, agent_id)
            if resultado is not None:
                return resultado

        return ResultadoGateRisco(
            aprovado=True,
            codigo_gate=_CODIGO_GATE,
            motivo="Todas as posicoes do agente estao fechadas",
            detalhes={
                "agent_id": agent_id,
                "arquivos_verificados": len(arquivos_do_agente),
            },
        )

    def _listar_arquivos_do_agente(self, agent_id: str) -> list[Path]:
        """Retorna arquivos de posicao que pertencem ao agent_id.

        Inclui arquivos corrompidos cujo nome contenha o agent_id
        (fail-safe: se nao sabemos o dono mas o nome sugere o agente,
        bloqueamos para evitar posicao duplicada).
        """
        if not self._outputs_dir.exists():
            return []

        todos_arquivos = list(self._outputs_dir.glob("agente_posicao_*.json"))
        return [a for a in todos_arquivos if self._pertence_ao_agente(a, agent_id)]

    def _pertence_ao_agente(self, arquivo: Path, agent_id: str) -> bool:
        """
        Verifica se o arquivo de posicao pertence ao agent_id.

        Retorna True se:
        - O campo 'owner' do arquivo corresponde ao agent_id, OU
        - O arquivo esta corrompido E o nome do arquivo contem o agent_id
          (fail-safe: nao sabemos o dono, mas o nome sugere ser deste agente)
        """
        try:
            dados = json.loads(arquivo.read_text(encoding="utf-8"))
            owner = dados.get("owner", "")
            return bool(owner == agent_id)
        except (json.JSONDecodeError, OSError):
            # Arquivo corrompido: aplica fail-safe se o nome contem o agent_id
            return agent_id in arquivo.name

    def _verificar_arquivo(
        self, arquivo: Path, agent_id: str
    ) -> ResultadoGateRisco | None:
        """
        Verifica um arquivo de posicao individual.

        Returns:
            ResultadoGateRisco de bloqueio se posicao aberta ou corrompida.
            None se posicao fechada (continuar verificando outros).
        """
        try:
            dados: dict[str, Any] = json.loads(
                arquivo.read_text(encoding="utf-8")
            )
        except (json.JSONDecodeError, OSError) as e:
            logger.warning(
                "Arquivo de posicao corrompido %s: %s — aplicando fail-safe",
                arquivo.name,
                e,
            )
            return ResultadoGateRisco(
                aprovado=False,
                codigo_gate=_CODIGO_GATE,
                motivo=f"Arquivo de posicao corrompido ou ilegivel: {arquivo.name}",
                detalhes={
                    "agent_id": agent_id,
                    "arquivo": arquivo.name,
                    "erro": str(e),
                },
            )

        # Campo 'aberta' ausente = tratado como aberta (fail-safe)
        if "aberta" not in dados:
            logger.warning(
                "Campo 'aberta' ausente em %s — aplicando fail-safe",
                arquivo.name,
            )
            return ResultadoGateRisco(
                aprovado=False,
                codigo_gate=_CODIGO_GATE,
                motivo=(
                    f"Campo 'aberta' ausente no arquivo {arquivo.name} "
                    f"— posicao tratada como aberta (fail-safe)"
                ),
                detalhes={
                    "agent_id": agent_id,
                    "arquivo": arquivo.name,
                    "session_id": dados.get("session_id", "desconhecido"),
                },
            )

        if dados["aberta"]:
            session_id = dados.get("session_id", "desconhecido")
            logger.info(
                "Posicao aberta encontrada para %s: session=%s",
                agent_id,
                session_id,
            )
            return ResultadoGateRisco(
                aprovado=False,
                codigo_gate=_CODIGO_GATE,
                motivo=(
                    f"Agente {agent_id} ja possui posicao aberta "
                    f"(session: {session_id})"
                ),
                detalhes={
                    "agent_id": agent_id,
                    "session_id": session_id,
                    "arquivo": arquivo.name,
                    "ticket": dados.get("ticket"),
                    "lado": dados.get("lado"),
                },
            )

        return None  # posicao fechada, continuar verificando
