"""
Sistema de logging e rastreamento de bloqueios de execução de trade.

Responsável por:
1. Registrar motivos de bloqueio (anti-overtrading protection)
2. Exportar dados em CSV/JSON
3. Gerar relatórios estruturados
4. Calcular estatísticas de bloqueios

Categorias de bloqueio:
- HOURLY_LIMIT_EXCEEDED: 3+ trades na última hora
- COOLDOWN_ACTIVE: 5 min entre trades não atendido
- LOSS_STREAK_COOLDOWN: 2+ perdas consecutivas (30 min wait)
- OUTSIDE_TRADING_HOURS: Fora do horário 09:00-17:30 BRT
"""

import csv
import json
from dataclasses import dataclass, asdict
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Dict, List, Optional


class BlockageReason(Enum):
    """Enum com razões de bloqueio de execução de trade."""

    HOURLY_LIMIT_EXCEEDED = "HOURLY_LIMIT_EXCEEDED"
    COOLDOWN_ACTIVE = "COOLDOWN_ACTIVE"
    LOSS_STREAK_COOLDOWN = "LOSS_STREAK_COOLDOWN"
    OUTSIDE_TRADING_HOURS = "OUTSIDE_TRADING_HOURS"


@dataclass
class BlockageLog:
    """Registro de um bloqueio de execução."""

    timestamp: datetime
    motivo: BlockageReason
    detalhes: str
    agent_session_id: str

    def para_dict(self) -> Dict[str, str]:
        """
        Converte BlockageLog para dicionário.

        Returns:
            Dicionário com timestamp em ISO 8601 e motivo em formato string.
        """
        return {
            "timestamp": self.timestamp.isoformat(),
            "motivo": self.motivo.value,
            "detalhes": self.detalhes,
            "agent_session_id": self.agent_session_id,
        }


class BlockageLogger:
    """
    Logger para bloqueios de execução de trade.

    Responsável por registrar, persistir e gerar relatórios de bloqueios
    causados por anti-overtrading protection.
    """

    def __init__(
        self,
        agent_session_id: str,
        outputs_dir: Optional[Path] = None,
    ) -> None:
        """
        Inicializa BlockageLogger.

        Args:
            agent_session_id: ID único da sessão do agente
            outputs_dir: Diretório para salvar exportações
                        (padrão: ./outputs)
        """
        self.agent_session_id = agent_session_id
        self.outputs_dir = outputs_dir or Path("outputs")
        self.outputs_dir.mkdir(exist_ok=True)
        self.bloqueios: List[BlockageLog] = []

    def registrar_bloqueio(
        self,
        motivo: BlockageReason,
        detalhes: str,
    ) -> None:
        """
        Registra um bloqueio.

        Args:
            motivo: Razão do bloqueio (enum BlockageReason)
            detalhes: Descrição adicional do bloqueio
        """
        log = BlockageLog(
            timestamp=datetime.now(),
            motivo=motivo,
            detalhes=detalhes,
            agent_session_id=self.agent_session_id,
        )
        self.bloqueios.append(log)

    def exportar_csv(self) -> Path:
        """
        Exporta bloqueios para arquivo CSV.

        Returns:
            Caminho do arquivo CSV criado.
        """
        arquivo = (
            self.outputs_dir
            / f"agente_bloqueios_{self.agent_session_id}.csv"
        )

        with open(arquivo, "w", newline="", encoding="utf-8") as f:
            writers = csv.DictWriter(
                f,
                fieldnames=["timestamp", "motivo", "detalhes",
                           "agent_session_id"],
            )
            writers.writeheader()
            for bloqueio in self.bloqueios:
                writers.writerow(bloqueio.para_dict())

        return arquivo

    def exportar_json(self) -> Path:
        """
        Exporta bloqueios para arquivo JSON.

        Returns:
            Caminho do arquivo JSON criado.
        """
        arquivo = (
            self.outputs_dir
            / f"agente_bloqueios_{self.agent_session_id}.json"
        )

        dados = {
            "agent_session_id": self.agent_session_id,
            "timestamp_criacao": datetime.now().isoformat(),
            "total_bloqueios": len(self.bloqueios),
            "bloqueios": [bloqueio.para_dict() for bloqueio in self.bloqueios],
        }

        with open(arquivo, "w", encoding="utf-8") as f:
            json.dump(dados, f, indent=2, ensure_ascii=False)

        return arquivo

    def obter_estatisticas(self) -> Dict[str, int]:
        """
        Calcula estatísticas de bloqueios por motivo.

        Returns:
            Dicionário com contagem de bloqueios por motivo.
        """
        stats: Dict[str, int] = {
            motivo.value: 0 for motivo in BlockageReason
        }
        stats["total_bloqueios"] = len(self.bloqueios)

        for bloqueio in self.bloqueios:
            stats[bloqueio.motivo.value] += 1

        return stats

    def gerar_relatorio_markdown(self) -> str:
        """
        Gera relatório estruturado em Markdown.

        Returns:
            String com relatório formatado em Markdown.
        """
        stats = self.obter_estatisticas()
        total = stats["total_bloqueios"]

        linhas = [
            f"# Relatório de Bloqueios - {self.agent_session_id}",
            "",
            f"**Data:** {datetime.now().isoformat()}",
            "",
            "## Resumo",
            "",
            f"- **Total de bloqueios:** {total}",
            "",
        ]

        if total > 0:
            linhas.extend([
                "## Distribuição por Motivo",
                "",
            ])

            for motivo in BlockageReason:
                valor = motivo.value
                count = stats.get(valor, 0)
                percentual = (count / total * 100) if total > 0 else 0
                linhas.append(
                    f"- **{valor}**: {count} ({percentual:.1f}%)"
                )

            linhas.extend([
                "",
                "## Bloqueios Recentes (últimos 5)",
                "",
            ])

            for bloqueio in self.bloqueios[-5:]:
                linhas.append(
                    f"- {bloqueio.timestamp.isoformat()} | "
                    f"{bloqueio.motivo.value} | {bloqueio.detalhes}"
                )

        else:
            linhas.append("Nenhum bloqueio registrado.")

        return "\n".join(linhas)
