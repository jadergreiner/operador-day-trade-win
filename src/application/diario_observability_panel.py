"""
ROADMAP-DIARIOS-01: Observabilidade e Watchdog dos Diarios

Responsabilidades:
- Rastrear ultimo timestamp de gravacao por diario
- Alertar quando diario ficar > limite_min sem gravar
- Exibir painel ASCII no terminal com status em tempo real
- Integrar com ThreadWatchdog para historico de restarts

Diarios monitorados:
    MICRO_TENDENCIA | RL_5000 | RL_DIRETO | DIARIOS

Pipeline:
    Diario grava -> registrar_gravacao(nome)
    -> verificar_alertas_inatividade()
    -> exibir_painel_terminal() a cada 60s

Status: Implementacao v1.0 (18/03/2026)
Referencia: docs/BACKLOG.md (ROADMAP-DIARIOS-01)
"""

import datetime
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

from src.application.opening_context_report import load_latest_opening_context_report

DIARIOS_MONITORADOS: list[str] = [
    "MICRO_TENDENCIA",
    "RL_5000",
    "RL_DIRETO",
    "DIARIOS",
]

_LARGURA_PAINEL = 60


@dataclass
class StatusDiario:
    """Estado de monitoramento de um diario especifico.

    Args:
        nome: Identificador do diario (ex: 'MICRO_TENDENCIA').
        ultimo_registro: Timestamp da ultima gravacao registrada.
        total_registros: Contador acumulado de gravacoes.
        em_alerta: True se diario ultrapassou limite de inatividade.

    """

    nome: str
    ultimo_registro: Optional[datetime.datetime] = None
    total_registros: int = 0
    em_alerta: bool = False


class ObservabilidadeDiarios:
    """Painel de observabilidade para os 4 diarios do sistema.

    Rastreia o ultimo timestamp de gravacao de cada diario e
    emite alertas quando algum fica inativo por mais do que o
    limite configurado. Exibe painel ASCII para o terminal.

    Exemplo de uso:
        painel = ObservabilidadeDiarios(limite_inatividade_min=20)
        painel.registrar_gravacao("DIARIOS")
        alertas = painel.verificar_alertas_inatividade()
        print(painel.exibir_painel_terminal())

    """

    def __init__(
        self,
        limite_inatividade_min: int = 20,
        report_dir: str | Path = "outputs/analysis",
    ) -> None:
        """Inicializa o painel com limite de inatividade configuravel.

        Args:
            limite_inatividade_min: Minutos sem gravacao para emitir alerta.
            report_dir: Diretorio com o relatorio consolidado latest.

        """
        self._limite_min = limite_inatividade_min
        self._report_dir = Path(report_dir)
        self._status: dict[str, StatusDiario] = {
            nome: StatusDiario(nome=nome) for nome in DIARIOS_MONITORADOS
        }
        self._historico_restarts: dict[str, int] = {
            nome: 0 for nome in DIARIOS_MONITORADOS
        }

    def registrar_gravacao(self, nome_diario: str) -> None:
        """Registra uma gravacao bem-sucedida de um diario.

        Atualiza o timestamp de ultimo registro e incrementa o
        contador de gravacoes. Se o diario nao estiver na lista
        monitorada, o registro e ignorado silenciosamente.

        Args:
            nome_diario: Nome do diario que gravou dados.

        """
        if nome_diario not in self._status:
            return
        status = self._status[nome_diario]
        status.ultimo_registro = datetime.datetime.now()
        status.total_registros += 1
        status.em_alerta = False

    def verificar_alertas_inatividade(self) -> list[str]:
        """Verifica quais diarios ultrapassaram o limite de inatividade.

        Percorre todos os diarios monitorados e retorna os nomes
        daqueles cujo ultimo_registro e mais antigo que o limite
        configurado, ou que nunca gravaram.

        Returns:
            Lista de nomes de diarios em alerta de inatividade.

        """
        agora = datetime.datetime.now()
        limite_delta = datetime.timedelta(minutes=self._limite_min)
        alertas: list[str] = []

        for nome, status in self._status.items():
            if status.ultimo_registro is None:
                # Nunca gravou — nao alerta ate ter referencia
                continue
            tempo_inativo = agora - status.ultimo_registro
            if tempo_inativo > limite_delta:
                status.em_alerta = True
                alertas.append(nome)
            else:
                status.em_alerta = False

        return alertas

    def exibir_painel_terminal(self) -> str:
        """Gera o painel ASCII com status de todos os diarios.

        Produz uma string formatada com cabecalho, lista de diarios
        e indicadores visuais de status (OK / ALERTA).

        Returns:
            String com o painel pronto para impressao no terminal.

        """
        agora = datetime.datetime.now()
        self.verificar_alertas_inatividade()

        linhas: list[str] = []
        separador = "=" * _LARGURA_PAINEL
        separador_fino = "-" * _LARGURA_PAINEL

        linhas.append(separador)
        linhas.append(
            " PAINEL DE OBSERVABILIDADE — DIARIOS".center(_LARGURA_PAINEL)
        )
        linhas.append(
            f" Atualizado: {agora.strftime('%d/%m/%Y %H:%M:%S')}".center(
                _LARGURA_PAINEL
            )
        )
        linhas.append(separador)

        for nome, status in self._status.items():
            if status.em_alerta:
                indicador = "[!] ALERTA"
                tempo_str = _formatar_inatividade(agora, status.ultimo_registro)
                linha = f"  {nome:<20} {indicador:<12} | inativo: {tempo_str}"
            else:
                indicador = "[+] OK"
                if status.ultimo_registro is not None:
                    tempo_str = _formatar_inatividade(agora, status.ultimo_registro)
                    linha = (
                        f"  {nome:<20} {indicador:<12}"
                        f" | ultimo: {tempo_str} atras"
                        f" | total: {status.total_registros}"
                    )
                else:
                    linha = (
                        f"  {nome:<20} {indicador:<12}"
                        f" | aguardando primeira gravacao"
                    )
            linhas.append(linha)

        linhas.append(separador_fino)
        linhas.append(
            f"  Limite inatividade: {self._limite_min} min"
            f"  |  Diarios monitorados: {len(DIARIOS_MONITORADOS)}"
        )
        report_payload = load_latest_opening_context_report(self._report_dir)
        if report_payload:
            generated_at = str(report_payload.get("generated_at", "") or "")
            generated_suffix = generated_at[11:19] if len(generated_at) >= 19 else "N/D"
            linhas.append(separador_fino)
            linhas.append(
                "  Contexto x resultado latest: "
                f"{report_payload.get('target_date', 'N/D')}"
            )
            linhas.append(
                "  Agentes: "
                f"{report_payload.get('total_agents', 0)}"
                " | Trades: "
                f"{report_payload.get('total_trades_closed', 0)}"
                " | PnL: "
                f"R$ {float(report_payload.get('total_pnl', 0.0) or 0.0):.2f}"
            )
            linhas.append(f"  Gerado em: {generated_suffix}")
        linhas.append(separador)

        return "\n".join(linhas)

    def historico_restarts_por_diario(self) -> dict[str, int]:
        """Retorna o historico de restarts registrados por diario.

        Returns:
            dict mapeando nome do diario para numero de restarts.

        """
        return dict(self._historico_restarts)

    def registrar_restart(self, nome_diario: str) -> None:
        """Incrementa o contador de restarts de um diario.

        Args:
            nome_diario: Nome do diario que foi reiniciado.

        """
        if nome_diario in self._historico_restarts:
            self._historico_restarts[nome_diario] += 1

    def obter_status(self, nome_diario: str) -> StatusDiario:
        """Retorna o objeto StatusDiario de um diario especifico.

        Args:
            nome_diario: Nome do diario a consultar.

        Returns:
            StatusDiario com informacoes do diario.

        Raises:
            KeyError: Se o diario nao estiver na lista monitorada.

        """
        return self._status[nome_diario]


def _formatar_inatividade(
    agora: datetime.datetime,
    ultimo: Optional[datetime.datetime],
) -> str:
    """Formata o tempo de inatividade em string legivel.

    Args:
        agora: Timestamp atual.
        ultimo: Timestamp do ultimo registro (pode ser None).

    Returns:
        String como '5m30s' ou '---' se ultimo for None.

    """
    if ultimo is None:
        return "---"
    delta = agora - ultimo
    total_seg = int(delta.total_seconds())
    minutos = total_seg // 60
    segundos = total_seg % 60
    return f"{minutos}m{segundos:02d}s"
