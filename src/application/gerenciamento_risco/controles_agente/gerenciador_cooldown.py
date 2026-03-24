"""
GerenciadorCooldown: Controle de periodo de espera entre operacoes por agente.

Responsabilidades:
- Registrar timestamp de fechamento de posicao por agent_id
- Verificar se o periodo_espera_segundos ja expirou
- Persistir estado em outputs/cooldown_{agent_id}.json (isolamento por agente)
- Tratar arquivos corrompidos sem bloquear operacoes (fail-safe gracioso)

Pipeline:
    MotorDecisaoIsolado/AC5.8 fecha posicao
    → GerenciadorCooldown.registrar_fechamento(agent_id)
    → GerenciadorRiscoExterno.avaliar_todos() consulta
      GerenciadorCooldown.verificar_cooldown(agent_id)
    → ResultadoCooldown.aprovado determina EXECUTE/REJECT no AC4

Status: v1.0 (24/03/2026)
Referencia: docs/BACKLOG.md (Camada Risco Externo - Cooldown)
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

from src.domain.value_objects.risco_externo import ConfiguracaoCooldown

logger = logging.getLogger(__name__)


@dataclass
class ResultadoCooldown:
    """
    Resultado da verificacao de cooldown para um agente.

    Atributos:
        aprovado: True se o agente pode abrir nova posicao.
        segundos_restantes: Segundos ate o cooldown expirar (0 se aprovado).
        agent_id: Identificador do agente consultado.
        motivo: Descricao textual da decisao.
    """

    aprovado: bool
    segundos_restantes: int
    agent_id: str
    motivo: str


class GerenciadorCooldown:
    """
    Controla o periodo de espera entre operacoes por agente.

    O estado e persistido em arquivo JSON para sobreviver a reinicializacoes.
    Arquivos corrompidos ou ausentes sao tratados como "sem historico" (libera).

    Exemplo de uso:
        config = ConfiguracaoCooldown(periodo_espera_segundos=120)
        gerenciador = GerenciadorCooldown(config)
        gerenciador.registrar_fechamento("agente_rl_5000")
        resultado = gerenciador.verificar_cooldown("agente_rl_5000")
        if not resultado.aprovado:
            # rejeitar nova entrada
    """

    def __init__(
        self,
        configuracao: ConfiguracaoCooldown,
        outputs_dir: Path = Path("outputs"),
    ) -> None:
        self._configuracao = configuracao
        self._outputs_dir = outputs_dir
        self._outputs_dir.mkdir(parents=True, exist_ok=True)

    def registrar_fechamento(self, agent_id: str) -> None:
        """
        Registra o timestamp do fechamento de posicao para o agente.

        Deve ser chamado imediatamente apos fechar qualquer posicao,
        independente do motivo (SL, TP, manual).

        Args:
            agent_id: Identificador unico do agente.
        """
        agora = datetime.now(tz=timezone.utc)
        dados = {
            "agent_id": agent_id,
            "timestamp_fechamento": agora.isoformat(),
        }
        arquivo = self._caminho_arquivo(agent_id)
        try:
            arquivo.write_text(json.dumps(dados), encoding="utf-8")
            logger.info(
                "Cooldown registrado: agent_id=%s, timestamp=%s",
                agent_id,
                agora.isoformat(),
            )
        except OSError as e:
            logger.error(
                "Falha ao persistir cooldown para %s: %s", agent_id, e
            )

    def verificar_cooldown(self, agent_id: str) -> ResultadoCooldown:
        """
        Verifica se o cooldown ainda esta ativo para o agente.

        Args:
            agent_id: Identificador unico do agente.

        Returns:
            ResultadoCooldown com aprovado=True se pode operar.
        """
        timestamp_fechamento = self._carregar_timestamp_fechamento(agent_id)

        if timestamp_fechamento is None:
            return ResultadoCooldown(
                aprovado=True,
                segundos_restantes=0,
                agent_id=agent_id,
                motivo="Sem fechamento anterior registrado, operacao liberada",
            )

        agora = datetime.now(tz=timezone.utc)
        segundos_decorridos = (agora - timestamp_fechamento).total_seconds()
        periodo = self._configuracao.periodo_espera_segundos
        segundos_restantes = max(0, int(periodo - segundos_decorridos))

        if segundos_restantes > 0:
            return ResultadoCooldown(
                aprovado=False,
                segundos_restantes=segundos_restantes,
                agent_id=agent_id,
                motivo=(
                    f"Cooldown ativo: aguardar {segundos_restantes}s "
                    f"antes da proxima operacao"
                ),
            )

        return ResultadoCooldown(
            aprovado=True,
            segundos_restantes=0,
            agent_id=agent_id,
            motivo="Cooldown expirado, operacao liberada",
        )

    def _caminho_arquivo(self, agent_id: str) -> Path:
        """Retorna o caminho do arquivo de cooldown para o agente."""
        nome_seguro = agent_id.replace("/", "_").replace("\\", "_")
        return self._outputs_dir / f"cooldown_{nome_seguro}.json"

    def _carregar_timestamp_fechamento(
        self, agent_id: str
    ) -> datetime | None:
        """
        Carrega o timestamp do ultimo fechamento do arquivo JSON.

        Retorna None se arquivo nao existir, estiver corrompido ou
        com timestamp invalido.
        """
        arquivo = self._caminho_arquivo(agent_id)
        if not arquivo.exists():
            return None
        try:
            dados = json.loads(arquivo.read_text(encoding="utf-8"))
            ts_str = dados.get("timestamp_fechamento", "")
            ts = datetime.fromisoformat(ts_str)
            # Garantir que tem timezone para comparacao segura
            if ts.tzinfo is None:
                ts = ts.replace(tzinfo=timezone.utc)
            return ts
        except (json.JSONDecodeError, KeyError, ValueError, TypeError) as e:
            logger.warning(
                "Arquivo de cooldown invalido para %s, ignorando: %s",
                agent_id,
                e,
            )
            return None
