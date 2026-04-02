"""
Motor de Decisão Isolado por Agent ID
======================================

Implementa isolamento total de decisões e rastreamento de posições entre agentes
paralelos.

Cada agente tem seu próprio executor de posições, completamente isolado em nível:
- Estado de posição aberta (em memória + persistência)
- Histórico de decisões
- Limite de operações
- Rastreamento de P&L

Uso:
    motor = MotorDecisaoIsolado(agent_id='agente_5000', db_path='...')
    motor.abrir_posicao(ticket=123456, ...)
    motor.fechar_posicao(ticket=123456)
    posicoes_abertas = motor.obter_posicoes_abertas()

Cada agente pode operar em paralelo sem interferência.
"""

import json
import logging
from dataclasses import dataclass, asdict, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)


class DecisaoOperacional(Enum):
    """Tipos de decisão operacional."""
    ABRIR = "ABRIR"           # Abrir nova posição
    FECHAR = "FECHAR"         # Fechar posição existente
    FECHAR_PARCIAL = "FECHAR_PARCIAL"  # Fechar parte da posição
    HOLD = "HOLD"             # Manter posição aberta
    CANCELAR = "CANCELAR"     # Cancelar ordem pendente
    CONTINGENCIA = "CONTINGENCIA"  # Ação de emergência


class TipoPosicao(Enum):
    """Tipos de posição."""
    COMPRADA = "BUY"
    VENDIDA = "SELL"


class MotivoFechamento(Enum):
    """Motivos possíveis de fechamento de posição."""
    TP_ATINGIDO = "TP_ATINGIDO"
    SL_ATINGIDO = "SL_ATINGIDO"
    TIMEOUT = "TIMEOUT"
    MANUAL = "MANUAL"
    CANCELADA = "CANCELADA"
    HOUVER_ALTERNATIVA = "HOUVER_ALTERNATIVA"


@dataclass
class PosicaoAberta:
    """Representa uma posição aberta isolada por agent."""
    ticket: int
    agent_id: str
    tipo: TipoPosicao
    preco_entrada: float
    volume: float
    stop_loss: float
    take_profit: float
    timestamp_abertura: str  # ISO 8601
    preco_atual: Optional[float] = None
    pnl_reais: Optional[float] = None
    pnl_pct: Optional[float] = None

    def para_dict(self) -> Dict[str, Any]:
        """Converte para dicionário."""
        d = asdict(self)
        d['tipo'] = self.tipo.value  # Converter enum para string
        return d


@dataclass
class DecisaoRegistrada:
    """Registro de uma decisão tomada pelo agente."""
    agent_id: str
    timestamp: str  # ISO 8601
    decisao: DecisaoOperacional
    ticket: Optional[int] = None
    reasoning: str = ""
    confianca: float = 0.0
    fatores: List[str] = field(default_factory=list)
    contexto_operacional: Dict[str, Any] = field(default_factory=dict)

    def para_dict(self) -> Dict[str, Any]:
        """Converte para dicionário."""
        d = asdict(self)
        d['decisao'] = self.decisao.value  # Converter enum para string
        return d


@dataclass
class HistoricoFechamento:
    """Histórico de posição fechada."""
    ticket: int
    agent_id: str
    tipo: TipoPosicao
    preco_entrada: float
    preco_saida: float
    volume: float
    pnl_reais: float
    pnl_pct: float
    motivo: MotivoFechamento
    duracao_minutos: float
    timestamp_abertura: str
    timestamp_fechamento: str
    resultado: Optional[str] = None  # "WIN", "LOSS" ou "BREAKEVEN"

    def para_dict(self) -> Dict[str, Any]:
        """Converte para dicionário."""
        d = asdict(self)
        d['tipo'] = self.tipo.value  # Converter enum para string
        d['motivo'] = self.motivo.value  # Converter enum para string
        return d


class MotorDecisaoIsolado:
    """
    Motor de decisão isolado por agent ID.

    Cada agente tem seu próprio executor, sem interferência de outros agentes.
    Responsabilidades:
    - Registro de posições abertas por agent
    - Rastreamento de histórico de decisões
    - Cálculo de limites por agent (max posições, max operações/hora, etc)
    - Isolamento total de estado entre agentes
    """

    def __init__(self, agent_id: str, data_dir: Path):
        """
        Inicializa motor de decisão isolado.

        Args:
            agent_id: Identificador único do agente (ex: 'agente_5000', 'agente_direto_20260316_103045')
            data_dir: Diretório para persistência de dados (ex: outputs/)
        """
        self.agent_id = agent_id
        self.data_dir = Path(data_dir)
        self.data_dir.mkdir(exist_ok=True, parents=True)

        # Arquivos de persistência (isolados por agent_id)
        self.posicoes_ativas_file = self.data_dir / f'posicoes_ativas_{self.agent_id}.json'
        self.decisoes_file = self.data_dir / f'decisoes_{self.agent_id}.json'
        self.historico_file = self.data_dir / f'historico_fechamentos_{self.agent_id}.json'

        # Estado em memória
        self.posicoes_ativas: Dict[int, PosicaoAberta] = {}
        self.decisoes: List[DecisaoRegistrada] = []
        self.historico: List[HistoricoFechamento] = []

        # Carregar estado anterior se existir
        self._carregar_estado()

        logger.info(f'[MotorDecisaoIsolado] Inicializado para agent: {self.agent_id}')
        logger.info(f'[MotorDecisaoIsolado] Posições ativas carregadas: {len(self.posicoes_ativas)}')

    def _carregar_estado(self) -> None:
        """Carrega estado anterior do agente (posições ativas, decisões, histórico)."""
        # Carregar posições ativas
        if self.posicoes_ativas_file.exists():
            try:
                with open(self.posicoes_ativas_file, 'r', encoding='utf-8') as f:
                    dados = json.load(f)
                    for ticket_str, pos_dict in dados.items():
                        ticket = int(ticket_str)
                        self.posicoes_ativas[ticket] = PosicaoAberta(
                            ticket=ticket,
                            agent_id=pos_dict['agent_id'],
                            tipo=TipoPosicao(pos_dict['tipo']),
                            preco_entrada=pos_dict['preco_entrada'],
                            volume=pos_dict['volume'],
                            stop_loss=pos_dict['stop_loss'],
                            take_profit=pos_dict['take_profit'],
                            timestamp_abertura=pos_dict['timestamp_abertura'],
                            preco_atual=pos_dict.get('preco_atual'),
                            pnl_reais=pos_dict.get('pnl_reais'),
                            pnl_pct=pos_dict.get('pnl_pct'),
                        )
                logger.debug(f'[MotorDecisaoIsolado] {len(self.posicoes_ativas)} posições carregadas')
            except Exception as e:
                logger.warning(f'[MotorDecisaoIsolado] Erro ao carregar posições: {e}')

        # Carregar decisões
        if self.decisoes_file.exists():
            try:
                with open(self.decisoes_file, 'r', encoding='utf-8') as f:
                    dados_list = json.load(f)
                    self.decisoes = [
                        DecisaoRegistrada(
                            agent_id=d['agent_id'],
                            timestamp=d['timestamp'],
                            decisao=DecisaoOperacional(d['decisao']),
                            ticket=d.get('ticket'),
                            reasoning=d.get('reasoning', ''),
                            confianca=d.get('confianca', 0.0),
                            fatores=d.get('fatores', []),
                            contexto_operacional=d.get('contexto_operacional', {}),
                        )
                        for d in dados_list
                    ]
                logger.debug(f'[MotorDecisaoIsolado] {len(self.decisoes)} decisões carregadas')
            except Exception as e:
                logger.warning(f'[MotorDecisaoIsolado] Erro ao carregar decisões: {e}')

        # Carregar histórico
        if self.historico_file.exists():
            try:
                with open(self.historico_file, 'r', encoding='utf-8') as f:
                    dados_list = json.load(f)
                    self.historico = [
                        HistoricoFechamento(
                            ticket=h['ticket'],
                            agent_id=h['agent_id'],
                            tipo=TipoPosicao(h['tipo']),
                            preco_entrada=h['preco_entrada'],
                            preco_saida=h['preco_saida'],
                            volume=h['volume'],
                            pnl_reais=h['pnl_reais'],
                            pnl_pct=h['pnl_pct'],
                            motivo=MotivoFechamento(h['motivo']),
                            duracao_minutos=h['duracao_minutos'],
                            timestamp_abertura=h['timestamp_abertura'],
                            timestamp_fechamento=h['timestamp_fechamento'],
                        )
                        for h in dados_list
                    ]
                logger.debug(f'[MotorDecisaoIsolado] {len(self.historico)} fechamentos carregados')
            except Exception as e:
                logger.warning(f'[MotorDecisaoIsolado] Erro ao carregar histórico: {e}')

    def _salvar_estado(self) -> None:
        """Persiste estado atual em arquivos JSON (isolados por agent)."""
        try:
            # Salvar posições ativas
            posicoes_dict = {
                str(ticket): pos.para_dict()
                for ticket, pos in self.posicoes_ativas.items()
            }
            with open(self.posicoes_ativas_file, 'w', encoding='utf-8') as f:
                json.dump(posicoes_dict, f, indent=2, ensure_ascii=False)

            # Salvar decisões
            decisoes_list = [d.para_dict() for d in self.decisoes]
            with open(self.decisoes_file, 'w', encoding='utf-8') as f:
                json.dump(decisoes_list, f, indent=2, ensure_ascii=False)

            # Salvar histórico
            historico_list = [h.para_dict() for h in self.historico]
            with open(self.historico_file, 'w', encoding='utf-8') as f:
                json.dump(historico_list, f, indent=2, ensure_ascii=False)
        except Exception as e:
            logger.error(f'[MotorDecisaoIsolado] Erro ao salvar estado: {e}')

    def registrar_decisao(self, decisao: DecisaoOperacional, ticket: Optional[int] = None,
                         reasoning: str = "", confianca: float = 0.0,
                         fatores: Optional[List[str]] = None,
                         contexto_operacional: Optional[Dict[str, Any]] = None) -> None:
        """
        Registra uma decisão tomada pelo agente.

        Args:
            decisao: Tipo de decisão (ABRIR, FECHAR, HOLD, etc.)
            ticket: Ticket da posição (se aplicável)
            reasoning: Justificativa da decisão
            confianca: Nível de confiança (0.0-1.0)
            fatores: Lista de fatores que influenciaram a decisão
            contexto_operacional: Snapshot estruturado do contexto da abertura
        """
        decisao_reg = DecisaoRegistrada(
            agent_id=self.agent_id,
            timestamp=datetime.now().isoformat(),
            decisao=decisao,
            ticket=ticket,
            reasoning=reasoning,
            confianca=confianca,
            fatores=fatores or [],
            contexto_operacional=contexto_operacional or {},
        )
        self.decisoes.append(decisao_reg)
        self._salvar_estado()
        logger.debug(f'[DECISAO] {self.agent_id}: {decisao.value} (ticket: {ticket})')

    def abrir_posicao(self, ticket: int, tipo: TipoPosicao, preco_entrada: float,
                     volume: float, stop_loss: float, take_profit: float,
                     contexto_operacional: Optional[Dict[str, Any]] = None) -> bool:
        """
        Registra abertura de nova posição DESTE agente.

        Args:
            ticket: Ticket da ordem MT5
            tipo: COMPRADA ou VENDIDA
            preco_entrada: Preço de entrada
            volume: Volume em contratos
            stop_loss: Nível de stop loss
            take_profit: Nível de take profit

        Returns:
            True se posição foi registrada com sucesso
        """
        if ticket in self.posicoes_ativas:
            logger.warning(f'[POSICAO] {self.agent_id}: Ticket {ticket} já está aberto')
            return False

        # Verificar limite máximo de posições simultâneas (ex: máximo 1)
        if len(self.posicoes_ativas) >= 1:
            logger.warning(f'[POSICAO] {self.agent_id}: Limite de posições simultâneas atingido')
            return False

        posicao = PosicaoAberta(
            ticket=ticket,
            agent_id=self.agent_id,
            tipo=tipo,
            preco_entrada=preco_entrada,
            volume=volume,
            stop_loss=stop_loss,
            take_profit=take_profit,
            timestamp_abertura=datetime.now().isoformat(),
        )

        self.posicoes_ativas[ticket] = posicao
        self.registrar_decisao(DecisaoOperacional.ABRIR, ticket=ticket,
                             reasoning=f'Abertura de posição {tipo.value}',
                             contexto_operacional=contexto_operacional)
        self._salvar_estado()

        logger.info(f'[POSICAO] {self.agent_id}: Posição aberta (ticket: {ticket}, {tipo.value})')
        return True

    def atualizar_posicao(self, ticket: int, preco_atual: float) -> bool:
        """
        Atualiza preço e P&L de posição aberta.

        Args:
            ticket: Ticket da posição
            preco_atual: Preço atual do ativo

        Returns:
            True se posição foi atualizada
        """
        if ticket not in self.posicoes_ativas:
            logger.warning(f'[POSICAO] {self.agent_id}: Ticket {ticket} não está aberto')
            return False

        posicao = self.posicoes_ativas[ticket]
        posicao.preco_atual = preco_atual

        # Calcular P&L — WINFUT: R$ 0,20 por ponto por contrato (BUG-2 fix)
        valor_ponto_winfut = 0.20  # R$ por ponto do mini-indice
        if posicao.tipo == TipoPosicao.COMPRADA:
            pontos_ganhos = preco_atual - posicao.preco_entrada
            posicao.pnl_reais = pontos_ganhos * posicao.volume * valor_ponto_winfut
            posicao.pnl_pct = ((preco_atual - posicao.preco_entrada) / posicao.preco_entrada) * 100
        else:  # VENDIDA
            pontos_ganhos = posicao.preco_entrada - preco_atual
            posicao.pnl_reais = pontos_ganhos * posicao.volume * valor_ponto_winfut
            posicao.pnl_pct = ((posicao.preco_entrada - preco_atual) / posicao.preco_entrada) * 100

        self._salvar_estado()
        return True

    def fechar_posicao(self, ticket: int, preco_saida: float,
                      motivo: MotivoFechamento,
                      contexto_operacional: Optional[Dict[str, Any]] = None) -> Optional[HistoricoFechamento]:
        """
        Fecha posição aberta e a move para histórico.

        Args:
            ticket: Ticket da posição
            preco_saida: Preço de fechamento
            motivo: Motivo do fechamento (TP, SL, manual, etc.)

        Returns:
            HistoricoFechamento se posição foi fechada com sucesso
        """
        if ticket not in self.posicoes_ativas:
            logger.warning(f'[POSICAO] {self.agent_id}: Ticket {ticket} não está aberto')
            return None

        posicao = self.posicoes_ativas.pop(ticket)

        # Calcular P&L final — WINFUT: R$ 0,20 por ponto por contrato (BUG-2 fix)
        valor_ponto_winfut = 0.20  # R$ por ponto do mini-indice
        if posicao.tipo == TipoPosicao.COMPRADA:
            pontos_ganhos = preco_saida - posicao.preco_entrada
            pnl_reais = pontos_ganhos * posicao.volume * valor_ponto_winfut
            pnl_pct = ((preco_saida - posicao.preco_entrada) / posicao.preco_entrada) * 100
        else:  # VENDIDA
            pontos_ganhos = posicao.preco_entrada - preco_saida
            pnl_reais = pontos_ganhos * posicao.volume * valor_ponto_winfut
            pnl_pct = ((posicao.preco_entrada - preco_saida) / posicao.preco_entrada) * 100

        # Calcular duração
        tempo_abertura = datetime.fromisoformat(posicao.timestamp_abertura)
        duracao_minutos = (datetime.now() - tempo_abertura).total_seconds() / 60.0

        # Criar registro de histórico
        historico = HistoricoFechamento(
            ticket=ticket,
            agent_id=self.agent_id,
            tipo=posicao.tipo,
            preco_entrada=posicao.preco_entrada,
            preco_saida=preco_saida,
            volume=posicao.volume,
            pnl_reais=pnl_reais,
            pnl_pct=pnl_pct,
            motivo=motivo,
            duracao_minutos=duracao_minutos,
            timestamp_abertura=posicao.timestamp_abertura,
            timestamp_fechamento=datetime.now().isoformat(),
        )

        self.historico.append(historico)
        self.registrar_decisao(DecisaoOperacional.FECHAR, ticket=ticket,
                             reasoning=f'Fechamento por {motivo.value}',
                             contexto_operacional=contexto_operacional)
        self._salvar_estado()

        resultado = "✅ GANHO" if pnl_reais > 0 else "❌ PERDA" if pnl_reais < 0 else "➖ BREAKEVEN"
        logger.info(f'[POSICAO] {self.agent_id}: Posição fechada (ticket: {ticket}, {resultado}, '
                   f'P&L: R${pnl_reais:.2f} ({pnl_pct:+.2f}%), Duração: {duracao_minutos:.1f}min)')

        return historico

    def obter_posicoes_abertas(self) -> List[PosicaoAberta]:
        """Retorna lista de posições abertas DESTE agente."""
        return list(self.posicoes_ativas.values())

    def tem_posicao_aberta(self) -> bool:
        """Retorna True se agente tem alguma posição aberta."""
        return len(self.posicoes_ativas) > 0

    def obter_posicao(self, ticket: int) -> Optional[PosicaoAberta]:
        """Retorna posição específica DESTE agente."""
        return self.posicoes_ativas.get(ticket)

    def obter_historico(self, tempo_minutos: int = 1440) -> List[HistoricoFechamento]:
        """
        Retorna histórico de posições fechadas DESTE agente.

        Args:
            tempo_minutos: Filtra histórico dos últimos N minutos (padrão: 24h)

        Returns:
            Lista de HistoricoFechamento
        """
        cutoff_time = datetime.now().timestamp() - (tempo_minutos * 60)

        return [
            h for h in self.historico
            if datetime.fromisoformat(h.timestamp_fechamento).timestamp() > cutoff_time
        ]

    def obter_estatisticas(self) -> Dict[str, Any]:
        """Retorna estatísticas de performance DESTE agente."""
        if not self.historico:
            return {
                'agent_id': self.agent_id,
                'total_trades': 0,
                'wins': 0,
                'losses': 0,
                'breakevens': 0,
                'win_rate': 0.0,
                'total_pnl': 0.0,
                'avg_win': 0.0,
                'avg_loss': 0.0,
                'sharpe_ratio': 0.0,
            }

        wins = [h for h in self.historico if h.pnl_reais > 0]
        losses = [h for h in self.historico if h.pnl_reais < 0]
        breakevens = [h for h in self.historico if h.pnl_reais == 0]

        total_trades = len(self.historico)
        win_rate = (len(wins) / total_trades * 100) if total_trades > 0 else 0.0
        total_pnl = sum(h.pnl_reais for h in self.historico)
        avg_win = sum(h.pnl_reais for h in wins) / len(wins) if wins else 0.0
        avg_loss = sum(h.pnl_reais for h in losses) / len(losses) if losses else 0.0

        return {
            'agent_id': self.agent_id,
            'total_trades': total_trades,
            'wins': len(wins),
            'losses': len(losses),
            'breakevens': len(breakevens),
            'win_rate': win_rate,
            'total_pnl': total_pnl,
            'avg_win': avg_win,
            'avg_loss': avg_loss,
        }
