"""
Integração do TradePerformanceTracker com o Agente RL Direto.

Fornece helper functions para rastrear trades durante a operação
do agente RL, registrando entrada/saida e gerando relatorios.

Uso:
    from src.application.trade_tracker_integration import TradeTrackerIntegration

    tracker_integration = TradeTrackerIntegration("agente_direto_TIMESTAMP")

    # Ao abrir uma posição
    tracker_integration.registrar_entrada(
        ticket=123456,
        simbolo="WINFUT",
        direcao="BUY",
        preco_entrada=100.50,
    )

    # Ao fechar uma posição
    resultado = tracker_integration.registrar_saida(
        ticket=123456,
        preco_saida=102.00,
        motivo_fechamento=TradeClosureReason.TP_HIT,
    )

    # Gerar relatorio
    arquivo = tracker_integration.gerar_relatorio_json()
"""

from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Optional

from src.application.trade_performance_tracker import (
    TradeClosureReason,
    TradePerformanceTracker,
)


class TradeTrackerIntegration:
    """Integração do TradePerformanceTracker com o agente RL.

    Gerencia:
    - Rastreamento de posições abertas (ticket → dados entrada)
    - Registro de saida e calculo P&L
    - Persistencia em JSON
    - Relatorios markdown
    """

    def __init__(
        self,
        session_id: str,
        output_dir: Optional[Path] = None,
    ) -> None:
        """Inicializar integração de tracking de trades.

        Args:
            session_id: ID da sessão do agente
            output_dir: Diretório para gravar JSON. Default: outputs/
        """
        self.session_id: str = session_id
        self.output_dir: Path = output_dir or Path("outputs")

        # Inicializar tracker interno
        self.tracker: TradePerformanceTracker = TradePerformanceTracker(
            session_id=session_id,
            output_dir=self.output_dir,
        )

        # Dicionário de trades abertos para rastreamento
        # ticket → {preco_entrada, horario_entrada, direcao, simbolo}
        self.trades_abertos: Dict[int, Dict[str, Any]] = {}

    def registrar_entrada(
        self,
        ticket: int,
        simbolo: str,
        direcao: str,
        preco_entrada: float,
    ) -> None:
        """Registrar uma posição aberta.

        Armazena dados para correlacionar com fechamento posterior.

        Args:
            ticket: ID da ordem no MT5
            simbolo: Simbolo tradado (ex: WINFUT)
            direcao: BUY ou SELL
            preco_entrada: Preco de abertura
        """
        self.trades_abertos[ticket] = {
            "simbolo": simbolo,
            "direcao": direcao,
            "preco_entrada": preco_entrada,
            "horario_entrada": datetime.now(),
        }

    def registrar_saida(
        self,
        ticket: int,
        preco_saida: float,
        motivo_fechamento: TradeClosureReason,
    ) -> Optional[Any]:
        """Registrar fechamento de uma posição.

        Busca dados de entrada, calcula P&L e persiste no tracker.

        Args:
            ticket: ID da ordem
            preco_saida: Preco de fechamento
            motivo_fechamento: Motivo (TP_HIT, SL_HIT, MANUAL_CLOSE, etc)

        Returns:
            TradePerformanceResult ou None se ticket não encontrado.
        """
        if ticket not in self.trades_abertos:
            return None

        # Recuperar dados de entrada
        dados_entrada: Dict[str, Any] = self.trades_abertos.pop(ticket)

        # Registrar trade completo no tracker
        resultado = self.tracker.registrar_trade(
            ticket=ticket,
            simbolo=dados_entrada["simbolo"],
            direcao=dados_entrada["direcao"],
            preco_entrada=dados_entrada["preco_entrada"],
            horario_entrada=dados_entrada["horario_entrada"],
            preco_saida=preco_saida,
            horario_saida=datetime.now(),
            motivo_fechamento=motivo_fechamento,
        )

        return resultado

    def gerar_relatorio_json(self) -> Path:
        """Gerar relatorio JSON com todos trades gravados.

        Returns:
            Path do arquivo JSON gerado.
        """
        return self.tracker.gravar_json()

    def obter_estatisticas(self) -> Dict[str, Any]:
        """Obter estatísticas agregadas dos trades.

        Returns:
            Dict com métricas: total_trades, win_rate, pnl_total, etc.
        """
        return self.tracker.calcular_estatisticas()

    def tem_posicoes_abertas(self) -> bool:
        """Verificar se há posições ainda abertas.

        Returns:
            True se ainda há trades não fechados.
        """
        return len(self.trades_abertos) > 0

    def listar_posicoes_abertas(self) -> Dict[int, Dict[str, Any]]:
        """Listar todas posições ainda abertas.

        Returns:
            Dict {ticket: dados_entrada}.
        """
        return self.trades_abertos.copy()


__all__ = [
    "TradeTrackerIntegration",
]
