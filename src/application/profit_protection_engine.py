"""
Motor de Proteção de Lucros em Tempo Real para Trading Automatizado.

Módulo responsável por:
1. Monitorar lucros/prejuízos de trades abertos
2. Detectar reversões agudas após ganho inicial
3. Sugerir ações (fechar parcial, ativar break-even stop, etc)
4. Prevenir devolução de lucros por movimentos amplos do mercado

Classes Principais:
- ProtectionStatus: Enum com estados de proteção
- ProfitProtectionResult: Dataclass com resultado de análise
- ProfitProtectionEngine: Motor principal de proteção dinâmica
"""

import json
import logging
from dataclasses import asdict, dataclass
from datetime import datetime
from enum import Enum
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)


# ============================================================
# ENUM: Estados de Proteção
# ============================================================


class ProtectionStatus(Enum):
    """Estados possíveis de proteção de lucro."""

    PARADO = "PARADO"  # Trade sem proteção ativa (prejuízo ou parado)
    ATIVO = "ATIVO"  # Trade com proteção ativa (em ganho)
    LUCRO_PROTEGIDO = "LUCRO_PROTEGIDO"  # Lucro em nível seguro
    ALERTA = "ALERTA"  # Reversão detectada, recomenda ação


# ============================================================
# DATACLASS: Resultado de Proteção
# ============================================================


@dataclass
class ProfitProtectionResult:
    """
    Resultado da análise de proteção de lucro para um trade.

    Atributos:
        trade_id: Identificador único do trade
        status: ProtectionStatus atual (PARADO, ATIVO, etc)
        profit_atual: Lucro/Prejuízo em porcentagem do entry
        profit_objetivo: Target de lucro em porcentagem
        acao_sugerida: Ação recomendada (str descritiva)
        timestamp: Quando a análise foi realizada
        lucro_maximo_sessao: Máximo ganho desde abertura (optional)
        deviance_reversao: Desvio de reversão desde máximo (optional)
    """

    trade_id: str
    status: ProtectionStatus
    profit_atual: float
    profit_objetivo: float
    acao_sugerida: str
    timestamp: datetime
    lucro_maximo_sessao: Optional[float] = None
    deviance_reversao: Optional[float] = None

    def to_dict(self) -> Dict[str, Any]:
        """Converte resultado para dicionário."""
        resultado = asdict(self)
        # Converte enum para string
        resultado["status"] = self.status.value
        # Converte datetime para ISO format
        resultado["timestamp"] = self.timestamp.isoformat()
        return resultado

    def to_json(self) -> str:
        """Converte resultado para JSON."""
        return json.dumps(self.to_dict(), indent=2, ensure_ascii=False)


# ============================================================
# CLASSE: Motor de Proteção de Lucros
# ============================================================


class ProfitProtectionEngine:
    """
    Motor dinâmico de proteção de lucros em tempo real.

    Funcionalidades:
    1. Monitora lucros/prejuízos de trades
    2. Detecta reversões agudas (problema: mercado sobe e volta)
    3. Recomenda break-even stops automáticos
    4. Sugere fechamento parcial quando lucro é robusto
    5. Previne overtrading com cooldown

    Configuração com valores defaults mais conservadores:
    - profit_target_pct: 2.0 (alvo de lucro)
    - stop_loss_pct: 1.0 (limite de prejuízo)
    - partial_close_pct: 0.75 (quando fechar parcial vs target)
    - break_even_offset_pct: 0.10 (offset de break-even stop)
    - reversao_threshold_pct: 0.75 (quando ativar alerta de reversão)
    - cooldown_seconds: 5 (mínimo entre sinais)
    """

    def __init__(
        self,
        profit_target_pct: float = 2.0,
        stop_loss_pct: float = 1.0,
        partial_close_pct: float = 0.75,
        break_even_offset_pct: float = 0.10,
        reversao_threshold_pct: float = 0.75,
        cooldown_seconds: int = 5,
    ) -> None:
        """
        Inicializa motor de proteção com configuração.

        Args:
            profit_target_pct: Target de lucro em % (default 2.0%)
            stop_loss_pct: Limite de prejuízo em % (default 1.0%)
            partial_close_pct: % do target para fechar parcial (default 75%)
            break_even_offset_pct: Offset para break-even em % (default 0.1%)
            reversao_threshold_pct: % de reversão para alerta (default 75%)
            cooldown_seconds: Segundos entre sinais (default 5s)
        """
        self.config: Dict[str, float] = {
            "profit_target_pct": profit_target_pct,
            "stop_loss_pct": stop_loss_pct,
            "partial_close_pct": partial_close_pct,
            "break_even_offset_pct": break_even_offset_pct,
            "reversao_threshold_pct": reversao_threshold_pct,
            "cooldown_seconds": cooldown_seconds,
        }
        self.historico_processamento: Dict[str, datetime] = {}  # Cooldown

    def processar_protecao(
        self,
        trade: Dict[str, Any],
        preco_atual: float,
        break_even_stop_ativo: bool = False,
        lucro_maximo_sessao: Optional[float] = None,
    ) -> ProfitProtectionResult:
        """
        Processa proteção para um trade específico.

        Algoritmo:
        1. Valida entrada (trade, preço, quantidade)
        2. Calcula lucro/prejuízo atual
        3. Detecta reversão aguda (se ganho máximo foi maior)
        4. Recomenda ações (break-even, fechar parcial, etc)
        5. Retorna resultado estruturado

        Args:
            trade: Dict com dados do trade
                - trade_id: str
                - symbol: str
                - entry_price: float
                - direction: "BUY" ou "SELL"
                - quantity: float (>0)
                - initial_sl: float (stop loss)
                - initial_tp: float (take profit)
            preco_atual: Preço atual do ativo
            break_even_stop_ativo: Se break-even stop já ativo
            lucro_maximo_sessao: Máximo ganho desde abertura (para detectar
                                  reversão)

        Returns:
            ProfitProtectionResult com análise completa

        Raises:
            ValueError: Se entrada inválida (None, preço negativo, qty=0)
        """
        # ============================================================
        # ETAPA 1: Validação de Entrada
        # ============================================================
        if trade is None:
            raise ValueError("Trade não pode ser None")

        if preco_atual < 0:
            raise ValueError(f"Preço inválido: {preco_atual}")

        quantidade = trade.get("quantity", 0)
        if quantidade <= 0:
            raise ValueError(f"Quantidade inválida: {quantidade}")

        trade_id: str = trade.get("trade_id", "UNKNOWN")
        entry_price: float = trade.get("entry_price", 0.0)
        direction: str = trade.get("direction", "unknown").upper()
        initial_sl: float = trade.get("initial_sl", 0.0)
        initial_tp: float = trade.get("initial_tp", 0.0)

        if direction not in ["BUY", "SELL"]:
            raise ValueError(f"Direção inválida: {direction}")

        # ============================================================
        # ETAPA 2: Cálculo de Lucro/Prejuízo
        # ============================================================
        # Diferença em pontos (preço atual vs entrada)
        diferenca_pontos: float = abs(preco_atual - entry_price)

        # Direção do movimento afeta sinal do lucro
        if direction == "BUY":
            # BUY: positivo se preço subiu
            lucro_prejuizo = preco_atual - entry_price
        else:  # SELL
            # SELL: positivo se preço caiu
            lucro_prejuizo = entry_price - preco_atual

        # Converter para porcentagem
        profit_pct: float = (lucro_prejuizo / entry_price) * 100

        # ============================================================
        # ETAPA 3: Determinar Estado Atual (PARADO, ATIVO, etc)
        # ============================================================
        # Usar epsilon para comparações floating point
        epsilon: float = 1e-6

        if profit_pct < -epsilon:
            # Em prejuízo
            status = ProtectionStatus.PARADO
            acao_sugerida = "AGUARDAR_RECUPERACAO"
        elif profit_pct >= (
            self.config["profit_target_pct"] - epsilon
        ):
            # Target atingido ou muito próximo
            status = ProtectionStatus.LUCRO_PROTEGIDO
            acao_sugerida = "FECHAR_TOTAL"
        else:
            # Em ganho mas não atingiu target
            status = ProtectionStatus.ATIVO
            acao_sugerida = "AGUARDAR"

        # ============================================================
        # ETAPA 4: Detectar Reversão Aguda (somente se não atingiu target)
        # ============================================================
        deviance_reversao: Optional[float] = None

        if (
            status != ProtectionStatus.LUCRO_PROTEGIDO
            and lucro_maximo_sessao is not None
            and profit_pct < lucro_maximo_sessao
        ):
            # Estava em maior ganho, agora em ganho menor = reversão
            deviance_reversao = lucro_maximo_sessao - profit_pct

            # Se reversão é significativa (> 75% do máximo)
            limite_reversao = lucro_maximo_sessao * self.config[
                "reversao_threshold_pct"
            ]
            if deviance_reversao > (lucro_maximo_sessao - limite_reversao):
                status = ProtectionStatus.ALERTA
                acao_sugerida = "CONSIDERAR_FECHAR_PARCIAL"

        # ============================================================
        # ETAPA 5: Recomendar Break-Even Stop (somente se não LUCRO_PROTEGIDO)
        # ============================================================
        if status != ProtectionStatus.LUCRO_PROTEGIDO:
            if break_even_stop_ativo:
                # Break-even já ativo, proteção continua
                if status == ProtectionStatus.ATIVO:
                    if profit_pct >= self.config["profit_target_pct"] * 0.5:
                        acao_sugerida = "MANTER_COM_BREAK_EVEN"

            elif profit_pct >= self.config["profit_target_pct"] * 0.5:
                # Lucro suficiente para ativar break-even
                if status == ProtectionStatus.ATIVO:
                    acao_sugerida = "ATIVAR_BREAK_EVEN_STOP"

        # ============================================================
        # ETAPA 6: Sugerir Fechamento Parcial (somente se não LUCRO_PROTEGIDO)
        # ============================================================
        if status != ProtectionStatus.LUCRO_PROTEGIDO:
            partial_trigger = (
                self.config["profit_target_pct"]
                * self.config["partial_close_pct"]
            )

            if profit_pct >= partial_trigger and status == ProtectionStatus.ATIVO:
                acao_sugerida = "FECHAR_PARCIAL"

        # ============================================================
        # ETAPA 7: Aplicar Cooldown
        # ============================================================
        ultima_processamento = self.historico_processamento.get(trade_id)
        if ultima_processamento is not None:
            tempo_decorrido = (
                datetime.now() - ultima_processamento
            ).total_seconds()
            if tempo_decorrido < self.config["cooldown_seconds"]:
                # Em cooldown, manter ação anterior
                acao_sugerida = "COOLDOWN_ATIVO"

        # Atualizar timestamp de processamento
        self.historico_processamento[trade_id] = datetime.now()

        # ============================================================
        # ETAPA 8: Retornar Resultado
        # ============================================================
        return ProfitProtectionResult(
            trade_id=trade_id,
            status=status,
            profit_atual=profit_pct,
            profit_objetivo=self.config["profit_target_pct"],
            acao_sugerida=acao_sugerida,
            timestamp=datetime.now(),
            lucro_maximo_sessao=lucro_maximo_sessao,
            deviance_reversao=deviance_reversao,
        )

    def gerar_relatorio_json(
        self, resultados: list[ProfitProtectionResult]
    ) -> str:
        """
        Gera relatório consolidado em JSON.

        Args:
            resultados: Lista de ProfitProtectionResult

        Returns:
            String JSON com relatório formatado
        """
        relatorio = {
            "timestamp": datetime.now().isoformat(),
            "total_trades": len(resultados),
            "status_distribuicao": {
                "PARADO": len(
                    [r for r in resultados if r.status == ProtectionStatus.PARADO]
                ),
                "ATIVO": len(
                    [r for r in resultados if r.status == ProtectionStatus.ATIVO]
                ),
                "LUCRO_PROTEGIDO": len(
                    [
                        r
                        for r in resultados
                        if r.status == ProtectionStatus.LUCRO_PROTEGIDO
                    ]
                ),
                "ALERTA": len(
                    [
                        r
                        for r in resultados
                        if r.status == ProtectionStatus.ALERTA
                    ]
                ),
            },
            "resultados": [r.to_dict() for r in resultados],
        }
        return json.dumps(relatorio, indent=2, ensure_ascii=False)

    def gerar_relatorio_markdown(
        self, resultados: list[ProfitProtectionResult]
    ) -> str:
        """
        Gera relatório consolidado em Markdown (legível).

        Args:
            resultados: Lista de ProfitProtectionResult

        Returns:
            String Markdown com relatório formatado
        """
        texto = "# Relatório de Proteção de Lucros\n\n"
        texto += f"**Data/Hora:** {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}\n"
        texto += f"**Total de Trades:** {len(resultados)}\n\n"

        # Distribuição de status
        texto += "## Distribuição de Status\n\n"
        status_count: Dict[str, int] = {}
        for r in resultados:
            chave = r.status.value
            status_count[chave] = status_count.get(chave, 0) + 1

        for status, count in status_count.items():
            texto += f"- **{status}:** {count}\n"

        # Detalhes por trade
        texto += "\n## Detalhes por Trade\n\n"
        for r in resultados:
            texto += f"### Trade: {r.trade_id}\n"
            texto += f"- Status: {r.status.value}\n"
            texto += f"- Lucro: {r.profit_atual:.2f}%\n"
            texto += f"- Objetivo: {r.profit_objetivo:.2f}%\n"
            texto += f"- Ação: {r.acao_sugerida}\n\n"

        return texto
