"""Entidade AlertaOportunidade - representa um alerta de trading."""

from dataclasses import dataclass, field
from datetime import datetime
from decimal import Decimal
from typing import Optional
from uuid import UUID, uuid4

from src.domain.enums.alerta_enums import (
    CanalEntrega,
    NivelAlerta,
    PatraoAlerta,
    StatusAlerta,
)
from src.domain.value_objects import Price, Symbol


@dataclass
class AlertaOportunidade:
    """
    Entidade representando uma oportunidade de trading alertada.

    Possui identidade única (id) e ciclo de vida desde geração até execução.
    Rastreavel para auditoria CVM completa.
    """

    # Identificação
    id: UUID = field(default_factory=uuid4)
    ativo: Symbol = field()
    padrao: PatraoAlerta = field()
    nivel: NivelAlerta = field()

    # Dados de mercado no momento da detecção
    preco_atual: Price = field()
    timestamp_deteccao: datetime = field()

    # Setup de entrada (onde operador entra)
    entrada_minima: Price = field()
    entrada_maxima: Price = field()
    stop_loss: Price = field()
    take_profit: Optional[Price] = None

    # Métricas de confiança
    confianca: Decimal = field()  # 0.0 a 1.0
    risk_reward: Decimal = field()  # ex: 2.5

    # Rastreamento de ciclo de vida
    status: StatusAlerta = field(default=StatusAlerta.GERADO)
    timestamps: dict = field(default_factory=dict)  # rastreamento de eventos
    canais_entregues: list = field(default_factory=list)  # quais canais foram usados

    # Operador que executou
    operador_username: Optional[str] = None
    timestamp_acao_operador: Optional[datetime] = None
    acao_operador: Optional[str] = None  # "EXECUTOU", "REJEITOU", "TIMEOUT"

    # Resultado do trade
    ordem_mt5_id: Optional[str] = None
    pnl: Optional[Decimal] = None
    timestamp_fechamento: Optional[datetime] = None

    def __post_init__(self) -> None:
        """Valida dados após inicialização."""
        if self.entrada_minima >= self.entrada_maxima:
            raise ValueError(
                "entrada_minima deve ser menor que entrada_maxima"
            )

        if self.preco_atual < self.entrada_minima or \
           self.preco_atual > self.entrada_maxima:
            raise ValueError(
                "preco_atual deve estar dentro da faixa de entrada"
            )

        if self.stop_loss >= self.entrada_minima:
            raise ValueError(
                "stop_loss deve ser menor que entrada_minima"
            )

        if self.confianca < Decimal("0") or self.confianca > Decimal("1"):
            raise ValueError("confianca deve estar entre 0.0 e 1.0")

        # Inicializa timestamps
        self.timestamps["criacao"] = datetime.now()

    def marcar_enfileirado(self) -> None:
        """Marca quando alerta foi enfileirado com sucesso."""
        self.status = StatusAlerta.ENFILEIRADO
        self.timestamps["enfileirado"] = datetime.now()

    def marcar_entregue(self, canal: CanalEntrega) -> None:
        """Marca entrega bem-sucedida em canal."""
        self.canais_entregues.append(canal.value)
        self.timestamps[f"entregue_{canal.value}"] = datetime.now()

        # Se todos os canais foram entregues, marca status
        if StatusAlerta.ENTREGUE not in str(self.status):
            self.status = StatusAlerta.ENTREGUE

    def marcar_falha_entrega(self, canal: CanalEntrega, erro: str) -> None:
        """Marca falha na entrega."""
        self.status = StatusAlerta.FALHA_ENTREGA
        self.timestamps[f"falha_{canal.value}"] = datetime.now()

    def registrar_acao_operador(
        self, operador: str, acao: str, resultado: Optional[str] = None
    ) -> None:
        """Registra ação do operador (executou, rejeitou, etc)."""
        self.operador_username = operador
        self.acao_operador = acao
        self.timestamp_acao_operador = datetime.now()
        self.timestamps["acao_operador"] = datetime.now()

        if acao == "EXECUTOU":
            self.status = StatusAlerta.EXECUTADO
        elif acao == "REJEITOU":
            self.status = StatusAlerta.REJEITADO
        elif acao == "TIMEOUT":
            self.status = StatusAlerta.REJEITADO

    def registrar_resultado_trade(
        self, ordem_id: str, pnl: Decimal, timestamp_fechamento: datetime
    ) -> None:
        """Registra resultado final do trade."""
        self.ordem_mt5_id = ordem_id
        self.pnl = pnl
        self.timestamp_fechamento = timestamp_fechamento
        self.timestamps["resultado"] = datetime.now()

    def calcular_latencia_total(self) -> int:
        """Calcula latência (ms) entre detecção e acao operador."""
        if not self.timestamp_acao_operador:
            return -1
        delta = self.timestamp_acao_operador - self.timestamp_deteccao
        return int(delta.total_seconds() * 1000)

    def __eq__(self, other: object) -> bool:
        """Alertas sao iguais se possuem mesmo id."""
        if not isinstance(other, AlertaOportunidade):
            return False
        return self.id == other.id

    def __hash__(self) -> int:
        """Hash baseado no id."""
        return hash(self.id)
