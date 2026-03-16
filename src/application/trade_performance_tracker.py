"""
TradePerformanceTracker - Rastreamento de ganhos e perdas por trade.

Monitora cada trade aberto no agente RL, registrando:
- Preco e horario de entrada
- Preco e horario de saida
- P&L em R$ e percentual
- Motivo de fechamento (TP, SL, manual, timeout)
- Duracao do trade

Persiste dados em JSON para analise offline e alimenta sistema
de aprendizado com feedback de execucao.

Arquitetura:
- TradeClosureReason: Enum de motivos de fechamento
- TradePerformanceResult: Dataclass com resultado de 1 trade
- TradePerformanceTracker: Classe que rastreia session completa
"""

import json
from dataclasses import asdict, dataclass
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional


class TradeClosureReason(Enum):
    """Enum dos motivos possíveis de fechamento de posicao."""

    TP_HIT = "TP_HIT"  # Take Profit foi atingido
    SL_HIT = "SL_HIT"  # Stop Loss foi atingido
    MANUAL_CLOSE = "MANUAL_CLOSE"  # Operador fechou manualmente
    TIMEOUT = "TIMEOUT"  # Posicao aberta >24h, auto-fechada
    CANCELLED = "CANCELLED"  # Ordem foi cancelada antes de executar


@dataclass
class TradePerformanceResult:
    """Resultado de performance de um trade individual.

    Armazena todos dados relevantes: entrada, saida, PnL, duracao, motivo.
    """

    ticket: int
    """ID unico da ordem no MT5."""

    simbolo: str
    """Simbolo tradado (ex: WINFUT, DOLLFUT)."""

    direcao: str
    """Direcao da posicao: BUY ou SELL."""

    preco_entrada: float
    """Preco de entrada em R$ (ou preco do simbolo)."""

    horario_entrada: datetime
    """Timestamp de abertura da funcao."""

    preco_saida: float
    """Preco de saida em R$ (preco de fechamento)."""

    horario_saida: datetime
    """Timestamp de fechamento da funcao."""

    pnl_reais: float
    """Ganho/Perda total em R$ (lucro bruto, sem comissao)."""

    percentual_pnl: float
    """Ganho/Perda em percentual (%) relativo ao capital entrada."""

    motivo_fechamento: TradeClosureReason
    """Motivo pelo qual a posicao foi fechada."""

    duracao_minutos: int
    """Duracao total da posicao em minutos."""

    def para_dict(self) -> Dict[str, Any]:
        """Converter resultado para dicionario (JSON-serializable).

        Returns:
            Dict com todos dados, timestamps em ISO 8601 string.
        """
        resultado_dict: Dict[str, Any] = asdict(self)

        # Converter timestamps para ISO 8601 string
        resultado_dict["horario_entrada"] = self.horario_entrada.isoformat()
        resultado_dict["horario_saida"] = self.horario_saida.isoformat()

        # Converter enum para string
        resultado_dict["motivo_fechamento"] = self.motivo_fechamento.value

        return resultado_dict


class TradePerformanceTracker:
    """Rastreador de performance de trades em sessao RL.

    Responsabilidades:
    - Registrar entrada/saida de cada trade
    - Calcular P&L em R$ e percentual
    - Persistir em JSON por session_id
    - Gerar relatorio com estatisticas agregadas
    - Alimentar dados para loop ML (feedback de execucao)

    Exemplo:
        tracker = TradePerformanceTracker("agente_rl_001")
        resultado = tracker.registrar_trade(
            ticket=123456,
            simbolo="WINFUT",
            direcao="BUY",
            preco_entrada=100.0,
            horario_entrada=datetime.now(),
            preco_saida=102.0,
            horario_saida=datetime.now(),
            motivo_fechamento=TradeClosureReason.TP_HIT,
        )
        stats = tracker.calcular_estatisticas()
        arquivo = tracker.gravar_json()
    """

    def __init__(
        self,
        session_id: str,
        output_dir: Optional[Path] = None,
    ) -> None:
        """Inicializar tracker para uma sessao.

        Args:
            session_id: ID unico da sessao do agente (ex: "agente_direto_20260316_103045")
            output_dir: Diretorio onde gravar JSON. Default: outputs/
        """
        self.session_id: str = session_id
        self.output_dir: Path = output_dir or Path("outputs")
        self.trades: List[TradePerformanceResult] = []
        self.lotes_gravados: int = 0

        # Garantir diretorio existe
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def registrar_trade(
        self,
        ticket: int,
        simbolo: str,
        direcao: str,
        preco_entrada: float,
        horario_entrada: datetime,
        preco_saida: float,
        horario_saida: datetime,
        motivo_fechamento: TradeClosureReason,
    ) -> TradePerformanceResult:
        """Registrar resultado de um trade fechado.

        Calcula P&L em R$ e percentual baseado nos precos entrada/saida
        e, direction (BUY/SELL).

        Args:
            ticket: ID unico da ordem
            simbolo: Simbolo tradado
            direcao: BUY ou SELL
            preco_entrada: Preco de abertura
            horario_entrada: Timestamp de abertura
            preco_saida: Preco de fechamento
            horario_saida: Timestamp de fechamento
            motivo_fechamento: Motivo da clausure (TP, SL, etc)

        Returns:
            TradePerformanceResult com todos dados calculados.
        """
        # Calcular PnL
        if direcao.upper() == "BUY":
            diferenca_preco: float = preco_saida - preco_entrada
            percentual: float = (diferenca_preco / preco_entrada) * 100.0
        else:  # SELL
            diferenca_preco = preco_entrada - preco_saida
            percentual = (diferenca_preco / preco_entrada) * 100.0

        # Calcular PnL em reais (assumindo tamanho padrao de contrato)
        # Tamanho padrao: 50 contratos (tipico para WINFUT)
        tamanho_contrato: int = 50
        pnl_total: float = diferenca_preco * tamanho_contrato

        # Calcular duracao em minutos
        duracao: timedelta = horario_saida - horario_entrada
        duracao_minutos: int = int(duracao.total_seconds() / 60)

        # Criar resultado
        resultado: TradePerformanceResult = TradePerformanceResult(
            ticket=ticket,
            simbolo=simbolo,
            direcao=direcao,
            preco_entrada=preco_entrada,
            horario_entrada=horario_entrada,
            preco_saida=preco_saida,
            horario_saida=horario_saida,
            pnl_reais=pnl_total,
            percentual_pnl=percentual,
            motivo_fechamento=motivo_fechamento,
            duracao_minutos=duracao_minutos,
        )

        # Registrar na lista
        self.trades.append(resultado)

        return resultado

    def calcular_estatisticas(self) -> Dict[str, Any]:
        """Calcular estatisticas agregadas de todos trades.

        Retorna metricas como:
        - Total de trades
        - Win/Loss/Breakeven
        - Win rate (%)
        - PnL total em R$
        - Duracao media
        - Distribuicao por motivo

        Returns:
            Dict com estatisticas calculadas.
        """
        if not self.trades:
            return {
                "total_trades": 0,
                "total_ganhos": 0,
                "total_perdas": 0,
                "total_breakeven": 0,
                "win_rate": 0.0,
                "pnl_total_reais": 0.0,
                "duracao_media_minutos": 0.0,
                "pnl_medio_por_trade": 0.0,
            }

        # Contar tipos de resultado
        total_ganhos: int = sum(1 for t in self.trades if t.pnl_reais > 0.0)
        total_perdas: int = sum(1 for t in self.trades if t.pnl_reais < 0.0)
        total_breakeven: int = sum(
            1 for t in self.trades if t.pnl_reais == 0.0
        )

        # Calcular metricas
        total_trades: int = len(self.trades)
        win_rate: float = (total_ganhos / total_trades * 100.0) if total_trades > 0 else 0.0
        pnl_total: float = sum(t.pnl_reais for t in self.trades)
        duracao_media: float = (
            sum(t.duracao_minutos for t in self.trades) / total_trades
            if total_trades > 0
            else 0.0
        )
        pnl_medio: float = (
            pnl_total / total_trades if total_trades > 0 else 0.0
        )

        # Distribuicao por motivo
        motivos_dist: Dict[str, int] = {}
        for trade in self.trades:
            motivo_str: str = trade.motivo_fechamento.value
            motivos_dist[motivo_str] = motivos_dist.get(motivo_str, 0) + 1

        return {
            "total_trades": total_trades,
            "total_ganhos": total_ganhos,
            "total_perdas": total_perdas,
            "total_breakeven": total_breakeven,
            "win_rate": win_rate,
            "pnl_total_reais": round(pnl_total, 2),
            "duracao_media_minutos": round(duracao_media, 2),
            "pnl_medio_por_trade": round(pnl_medio, 2),
            "distribuicao_motivos": motivos_dist,
        }

    def gravar_json(self) -> Path:
        """Gravar todos trades e estatisticas em arquivo JSON.

        Arquivo nomeado como: agente_performance_{session_id}.json
        Localizado em self.output_dir

        Conteudo:
        - metadata: session_id, timestamp gravacao, total_trades
        - trades: lista de todos trades com dados completos
        - estatisticas: agregacoes (win_rate, pnl_total, etc)

        Returns:
            Path do arquivo gravado.
        """
        # Preparar dados
        stats: Dict[str, Any] = self.calcular_estatisticas()

        dados: Dict[str, Any] = {
            "metadata": {
                "session_id": self.session_id,
                "timestamp_gravacao": datetime.now().isoformat(),
                "total_trades": len(self.trades),
                "lotes_gravados": self.lotes_gravados + 1,
            },
            "trades": [t.para_dict() for t in self.trades],
            "estatisticas": stats,
        }

        # Gerar nome do arquivo
        nome_arquivo: str = f"agente_performance_{self.session_id}.json"
        caminho_arquivo: Path = self.output_dir / nome_arquivo

        # Gravar JSON
        with open(caminho_arquivo, "w", encoding="utf-8") as f:
            json.dump(dados, f, indent=2, ensure_ascii=False)

        self.lotes_gravados += 1

        return caminho_arquivo


# Import para facilitar uso
from datetime import timedelta

__all__ = [
    "TradeClosureReason",
    "TradePerformanceResult",
    "TradePerformanceTracker",
]
