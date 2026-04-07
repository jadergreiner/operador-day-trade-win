"""
Detector de como posicoes foram fechadas em operacoes de trading.

Identifica o motivo de fechamento de uma posicao:
- TP_HIT: Preco atingiu Take Profit (fechamento automatico lucro)
- SL_HIT: Preco atingiu Stop Loss (fechamento automatico prejuizo)
- MANUAL_CLOSE: Operador fechou manualmente
- TIMEOUT: Posicao aberta >24h sem fechar (auto-close)
- CANCELLED: Ordem cancelada antes de executar

Arquitetura:
- ClosureReason: Enum com 5 motivos validos
- ClosureDetectionResult: Dataclass com resultado de deteccao
- PositionClosureDetector: Motor principal de deteccao
"""

from dataclasses import dataclass, asdict
from datetime import datetime, timedelta
from enum import Enum
from typing import Optional, Tuple, Dict, Any, List


class ClosureReason(Enum):
    """Enum com 5 motivos validos de fechamento de posicao."""

    TP_HIT = "TP_HIT"
    SL_HIT = "SL_HIT"
    MANUAL_CLOSE = "MANUAL_CLOSE"
    TIMEOUT = "TIMEOUT"
    CANCELLED = "CANCELLED"


class ClosureOrigin(Enum):
    """Origem operacional do encerramento detectado."""

    AGENTE = "AGENTE"
    OPERADOR = "OPERADOR"
    MERCADO = "MERCADO"
    SISTEMA = "SISTEMA"


@dataclass
class ClosureDetectionResult:
    """
    Dataclass com resultado de deteccao de fechamento.

    Campos:
        ticket: Numero da ordem MT5
        simbolo: Simbolo tradado (ex: WINFUT)
        preco_entrada: Preco de entrada da posicao
        preco_saida: Preco onde posicao foi fechada
        pnl_reais: P&L em valor absoluto (R$)
        pnl_pct: P&L em percentual (%)
        motivo_fechamento: ClosureReason (TP_HIT, SL_HIT, etc)
        duracao_minutos: Quantos minutos posicao ficou aberta
        timestamp_deteccao: Quando fechamento foi detectado
    """

    ticket: int
    simbolo: str
    preco_entrada: float
    preco_saida: float
    pnl_reais: float
    pnl_pct: float
    motivo_fechamento: ClosureReason
    duracao_minutos: int
    timestamp_deteccao: datetime
    encerrado_por: ClosureOrigin = ClosureOrigin.MERCADO

    def para_dict(self) -> Dict[str, Any]:
        """Converte resultado para dicionario estruturado."""
        resultado_dict = asdict(self)
        # Converter enums para string
        resultado_dict["motivo_fechamento"] = self.motivo_fechamento.value
        resultado_dict["encerrado_por"] = self.encerrado_por.value
        # Converter datetime para ISO format
        resultado_dict["timestamp_deteccao"] = (
            self.timestamp_deteccao.isoformat()
        )
        return resultado_dict


class PositionClosureDetector:
    """
    Motor para detectar como posicoes foram fechadas.

    Metodos principais:
        detectar_tp_hit(): Verifica se preco atingiu Take Profit
        detectar_sl_hit(): Verifica se preco atingiu Stop Loss
        detectar_timeout(): Verifica se posicao aberta >24h
        detectar_manual_close(): Classifica como manual se nenhum motivo auto
        calcular_pnl(): Calcula P&L com direcao (BUY/SELL)
        registrar_deteccao(): Armazena resultado
        gerar_relatorio_markdown(): Exporta relatorio estruturado
    """

    def __init__(self) -> None:
        """Inicializa PositionClosureDetector."""
        self.deteccoes: List[ClosureDetectionResult] = []
        self.timeout_horas: int = 24  # Posicao >24h = timeout

    def detectar_tp_hit(
        self,
        preco_entrada: float,
        preco_saida: float,
        take_profit: float,
        direcao: str,
    ) -> Optional[ClosureReason]:
        """
        Detecta se preco atingiu Take Profit.

        Args:
            preco_entrada: Preco de entrada
            preco_saida: Preco de saida
            take_profit: Nivel de Take Profit configurado
            direcao: "BUY" (esperava subir) ou "SELL" (esperava descer)

        Returns:
            ClosureReason.TP_HIT se preco atingiu TP, None caso contrario
        """
        if direcao == "BUY":
            # BUY: TP atingido se preco_saida >= TP
            if preco_saida >= take_profit:
                return ClosureReason.TP_HIT
        elif direcao == "SELL":
            # SELL: TP atingido se preco_saida <= TP
            if preco_saida <= take_profit:
                return ClosureReason.TP_HIT

        return None

    def detectar_sl_hit(
        self,
        preco_entrada: float,
        preco_saida: float,
        stop_loss: float,
        direcao: str,
    ) -> Optional[ClosureReason]:
        """
        Detecta se preco atingiu Stop Loss.

        Args:
            preco_entrada: Preco de entrada
            preco_saida: Preco de saida
            stop_loss: Nivel de Stop Loss configurado
            direcao: "BUY" ou "SELL"

        Returns:
            ClosureReason.SL_HIT se preco atingiu SL, None caso contrario
        """
        if direcao == "BUY":
            # BUY: SL atingido se preco_saida <= SL
            if preco_saida <= stop_loss:
                return ClosureReason.SL_HIT
        elif direcao == "SELL":
            # SELL: SL atingido se preco_saida >= SL
            if preco_saida >= stop_loss:
                return ClosureReason.SL_HIT

        return None

    def detectar_timeout(
        self,
        timestamp_abertura: datetime,
        timestamp_fechamento: datetime,
    ) -> Optional[ClosureReason]:
        """
        Detecta se posicao ficou aberta >24h (timeout).

        Args:
            timestamp_abertura: Quando posicao foi aberta
            timestamp_fechamento: Quando foi fechada

        Returns:
            ClosureReason.TIMEOUT se duracao >24h, None caso contrario
        """
        duracao = timestamp_fechamento - timestamp_abertura
        horas_abertas = duracao.total_seconds() / 3600

        if horas_abertas > self.timeout_horas:
            return ClosureReason.TIMEOUT

        return None

    def detectar_manual_close(
        self,
        preco_entrada: float,
        preco_saida: float,
        take_profit: float,
        stop_loss: float,
        direcao: str,
        timestamp_abertura: datetime,
        timestamp_fechamento: datetime,
    ) -> Optional[ClosureReason]:
        """
        Classifica como MANUAL_CLOSE se nenhum motivo automatico aplica.

        Verifica: nao foi TP (atingiu), nao foi SL, nao foi timeout.
        Se nenhum desses aplica, foi manual.

        Args:
            preco_entrada: Preco de entrada
            preco_saida: Preco de saida
            take_profit: TP nivel
            stop_loss: SL nivel
            direcao: "BUY" ou "SELL"
            timestamp_abertura: Abertura
            timestamp_fechamento: Fechamento

        Returns:
            ClosureReason.MANUAL_CLOSE se foi fechamento manual
        """
        # Verificar se foi TP
        foi_tp = self.detectar_tp_hit(
            preco_entrada, preco_saida, take_profit, direcao
        )
        if foi_tp:
            return None

        # Verificar se foi SL
        foi_sl = self.detectar_sl_hit(
            preco_entrada, preco_saida, stop_loss, direcao
        )
        if foi_sl:
            return None

        # Verificar se foi timeout
        foi_timeout = self.detectar_timeout(
            timestamp_abertura, timestamp_fechamento
        )
        if foi_timeout:
            return None

        # Se nao foi nenhum dos acima, foi manual
        return ClosureReason.MANUAL_CLOSE

    def classificar_fechamento_externo(
        self,
        preco_entrada: float,
        preco_saida: float,
        take_profit: float,
        stop_loss: float,
        direcao: str,
        timestamp_abertura: datetime,
        timestamp_fechamento: datetime,
        origem_forcada: Optional[ClosureOrigin] = None,
        tolerancia_preco: float = 0.5,
    ) -> Tuple[ClosureReason, ClosureOrigin]:
        """Classifica fechamento externo com motivo e origem operacional.

        Regras:
        - TP/SL => origem MERCADO
        - TIMEOUT => origem SISTEMA
        - Caso contrário => MANUAL_CLOSE com origem OPERADOR
          (ou ``origem_forcada`` quando explicitamente informada)
        """
        direcao_normalizada = direcao.upper()

        if direcao_normalizada == "BUY":
            if preco_saida >= (take_profit - tolerancia_preco):
                return ClosureReason.TP_HIT, ClosureOrigin.MERCADO
            if preco_saida <= (stop_loss + tolerancia_preco):
                return ClosureReason.SL_HIT, ClosureOrigin.MERCADO
        elif direcao_normalizada == "SELL":
            if preco_saida <= (take_profit + tolerancia_preco):
                return ClosureReason.TP_HIT, ClosureOrigin.MERCADO
            if preco_saida >= (stop_loss - tolerancia_preco):
                return ClosureReason.SL_HIT, ClosureOrigin.MERCADO

        motivo_timeout = self.detectar_timeout(
            timestamp_abertura, timestamp_fechamento
        )
        if motivo_timeout is not None:
            return motivo_timeout, ClosureOrigin.SISTEMA

        return ClosureReason.MANUAL_CLOSE, origem_forcada or ClosureOrigin.OPERADOR

    def calcular_pnl(
        self,
        preco_entrada: float,
        preco_saida: float,
        direcao: str,
        tamanho_contrato: int = 100,
    ) -> Tuple[float, float]:
        """
        Calcula P&L com direcao correta (BUY/SELL).

        Args:
            preco_entrada: Preco entrada
            preco_saida: Preco saida
            direcao: "BUY" (profit se subir) ou "SELL" (profit se descer)
            tamanho_contrato: Multiplo contrato (ex: WINFUT=100 pontos/contrato)

        Returns:
            Tupla (pnl_reais, pnl_pct)
        """
        movimento_pontos: float = 0.0

        if direcao == "BUY":
            # BUY: ganho se preco sobe
            movimento_pontos = preco_saida - preco_entrada

        elif direcao == "SELL":
            # SELL: ganho se preco desce
            movimento_pontos = preco_entrada - preco_saida

        # P&L em reais (pontos * tamanho contrato)
        pnl_reais: float = movimento_pontos * tamanho_contrato

        # P&L em percentual
        pnl_pct: float = (movimento_pontos / preco_entrada) * 100.0

        return pnl_reais, pnl_pct

    def registrar_deteccao(
        self, resultado: ClosureDetectionResult
    ) -> None:
        """
        Armazena resultado de deteccao.

        Args:
            resultado: ClosureDetectionResult com dados completos
        """
        self.deteccoes.append(resultado)

    def obter_estadisticas_por_motivo(self) -> Dict[str, int]:
        """
        Calcula contagem de fechamentos por motivo.

        Returns:
            Dict com {motivo: quantidade}
        """
        estatisticas: Dict[str, int] = {reason.value: 0 for reason in ClosureReason}

        for deteccao in self.deteccoes:
            motivo = deteccao.motivo_fechamento.value
            estatisticas[motivo] += 1

        return estatisticas

    def gerar_relatorio_markdown(self) -> str:
        """
        Gera relatorio markdown com estatisticas de fechamentos.

        Returns:
            String markdown estruturada com resumo e tabela
        """
        markdown = "# Relatorio de Deteccao de Fechamento\n\n"

        # Resumo estatistico
        markdown += "## Estatisticas por Motivo\n\n"
        stats = self.obter_estadisticas_por_motivo()

        for motivo, count in stats.items():
            markdown += f"- **{motivo}**: {count} fechamentos\n"

        markdown += "\n"

        # Tabela de deteccoes recentes
        if self.deteccoes:
            markdown += "## Deteccoes Recentes\n\n"
            markdown += (
                "| Ticket | Simbolo | Entrada | Saida | "
                "P&L (R$) | P&L (%) | Motivo | Duracao (min) |\n"
            )
            markdown += (
                "|--------|---------|---------|-------|"
                "----------|---------|--------|---------------|\n"
            )

            for deteccao in self.deteccoes[-10:]:  # Ultimos 10
                markdown += (
                    f"| {deteccao.ticket} | {deteccao.simbolo} | "
                    f"{deteccao.preco_entrada:.2f} | {deteccao.preco_saida:.2f} | "
                    f"{deteccao.pnl_reais:.2f} | {deteccao.pnl_pct:.2f}% | "
                    f"{deteccao.motivo_fechamento.value} | "
                    f"{deteccao.duracao_minutos} |\n"
                )

        return markdown

    def exportar_json(self) -> List[Dict[str, Any]]:
        """
        Exporta todas deteccoes em formato JSON estruturado.

        Returns:
            Lista de dicts com deteccoes
        """
        return [deteccao.para_dict() for deteccao in self.deteccoes]
