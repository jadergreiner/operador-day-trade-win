"""
AC5.8: Monitoramento em Tempo Real de Execução

Gerencia trade manager e position monitor com:
- Atualizacao em tempo real de status de ordem e posicao
- Reacao a erro, parcial, cancelamento e encerramento
- Rastreamento de transicoes de estado
- Persistencia em BD SQLite com auditoria completa

Responsabilidades:
    - Receber atualizacoes de status de ordem do executor (AC5)
    - Monitorar preco atual vs SL/TP
    - Reajustar ordens parcialmente executadas
    - Registrar eventos de monitoramento para auditoria
    - Fornecer snapshot de posicoes abertas para AC6 (feedback ML)

Pipeline:
    AC5: TradeExecutor envia ordem → Status = PENDING
         ↓
    AC5.8: MonitorPositionManager rastreia transicao
           PENDING → SENT → FILLED → ABERTA
         ↓
    MonitorPositionManager: Monitora PRECO_ATUAL vs SL/TP
         ↓
    AC5.8: Se TP ou SL atingido → ENCERRADA
         ↓
    AC6: FeedbackLoop processa outcome para ML

Status: Implementacao v1.0 (15/03/2026)
Referencia: docs/BACKLOG.md (AC5.8 Monitoramento em tempo real de execucao)
            src/application/ac5_trade_executor.py (integration point)
"""

from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from enum import Enum
from typing import Optional, List, Dict, Any, Tuple
from uuid import uuid4
import sqlite3
import logging
from contextlib import contextmanager

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)


# ============================================================================
# ENUMS
# ============================================================================


class StatusOrdem(str, Enum):
    """Status possvel de uma ordem."""

    PENDING = "PENDING"  # Preparada, nao enviada
    SENT = "SENT"  # Enviada para MT5
    FILLED = "FILLED"  # Totalmente executada
    PARTIAL = "PARTIAL"  # Parcialmente executada
    CANCELLED = "CANCELLED"  # Cancelada pelo usuario
    REJECTED = "REJECTED"  # Rejeitada por MT5


class StatusPosicao(str, Enum):
    """Status possvel de uma posicao."""

    ABERTA = "ABERTA"  # Ativa, aguardando SL/TP
    ENCERRADA = "ENCERRADA"  # Encerrada (TP/SL atingido)
    CANCELADA = "CANCELADA"  # Cancelada antes de preencher


class DirecaoOperacao(str, Enum):
    """Direcao da operacao: Compra ou Venda."""

    BUY = "BUY"
    SELL = "SELL"


# ============================================================================
# DATACLASSES
# ============================================================================


@dataclass
class PosicaoAberta:
    """Posicao aberta rastreada em tempo real."""

    posicao_id: str
    trade_id: str
    signal_id: str
    symbol: str
    direcao: DirecaoOperacao
    volume: int
    preco_entrada: float
    sl: float  # Stop Loss
    tp: float  # Take Profit
    preco_atual: float = 0.0
    pl: float = 0.0
    status: StatusPosicao = StatusPosicao.ABERTA
    criado_em: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    atualizado_em: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    def calcular_pl(self) -> float:
        """Calcula P&L baseado em preco atual."""
        if self.direcao == DirecaoOperacao.BUY:
            return (self.preco_atual - self.preco_entrada) * self.volume
        else:  # SELL
            return (self.preco_entrada - self.preco_atual) * self.volume

    def atingiu_tp(self) -> bool:
        """Verifica se atingiu Take Profit."""
        if self.direcao == DirecaoOperacao.BUY:
            return self.preco_atual >= self.tp
        else:  # SELL
            return self.preco_atual <= self.tp

    def atingiu_sl(self) -> bool:
        """Verifica se atingiu Stop Loss."""
        if self.direcao == DirecaoOperacao.BUY:
            return self.preco_atual <= self.sl
        else:  # SELL
            return self.preco_atual >= self.sl


@dataclass
class EvendoOrdem:
    """Evento registrado no monitoramento de ordem."""

    evento_id: str
    trade_id: str
    tipo_evento: str
    descricao: Optional[str]
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


# ============================================================================
# MONITOR DE POSICOES
# ============================================================================


class MonitorPositionManager:
    """
    Gerenciador de monitoramento de posicoes em tempo real.

    Responsabilidades:
        - Registrar ordens entrantes de AC5
        - Rastrear transicoes de estado (PENDING → SENT → FILLED)
        - Monitorar preco atual vs SL/TP
        - Reagir a eventos (erro, parcial, cancelamento)
        - Persistir estado em BD SQLite
        - Fornecer snapshot para AC6 (feedback ML)
    """

    def __init__(self, db_caminho: Optional[str] = None, db_conexao: Optional[sqlite3.Connection] = None) -> None:
        """
        Inicializa MonitorPositionManager.

        Args:
            db_caminho: Caminho para arquivo SQLite (usara memoria se None)
            db_conexao: Conexao existente para testes (sobrescreve db_caminho)
        """
        self.db_caminho = db_caminho or ":memory:"

        if db_conexao:
            self.bd_conexao = db_conexao
        else:
            self.bd_conexao = sqlite3.connect(self.db_caminho)
            self.bd_conexao.row_factory = sqlite3.Row

        self._inicializar_schema()
        logger.info(f"MonitorPositionManager inicializado em {self.db_caminho}")

    def _inicializar_schema(self) -> None:
        """Inicializa schema BD se nao existir."""
        cursor = self.bd_conexao.cursor()

        # Para testes em memoria, dropar tabelas se existirem
        if self.db_caminho == ":memory:":
            cursor.execute("DROP TABLE IF EXISTS eventos_monitoramento")
            cursor.execute("DROP TABLE IF EXISTS posicoes_encerradas")
            cursor.execute("DROP TABLE IF EXISTS posicoes_abertas")
            cursor.execute("DROP TABLE IF EXISTS ordens")

        # Tabela de ordens
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS ordens (
                trade_id TEXT PRIMARY KEY,
                signal_id TEXT NOT NULL,
                symbol TEXT NOT NULL,
                direcao TEXT NOT NULL,
                volume INTEGER NOT NULL,
                preco_entrada REAL NOT NULL,
                sl REAL NOT NULL,
                tp REAL NOT NULL,
                status TEXT NOT NULL DEFAULT 'PENDING',
                criado_em TEXT NOT NULL,
                atualizado_em TEXT NOT NULL
            )
        """)

        # Tabela de posicoes abertas
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS posicoes_abertas (
                posicao_id TEXT PRIMARY KEY,
                trade_id TEXT NOT NULL UNIQUE,
                signal_id TEXT NOT NULL,
                symbol TEXT NOT NULL,
                direcao TEXT NOT NULL,
                volume INTEGER NOT NULL,
                preco_entrada REAL NOT NULL,
                sl REAL NOT NULL,
                tp REAL NOT NULL,
                preco_atual REAL NOT NULL DEFAULT 0.0,
                pl REAL NOT NULL DEFAULT 0.0,
                status TEXT NOT NULL DEFAULT 'ABERTA',
                criado_em TEXT NOT NULL,
                atualizado_em TEXT NOT NULL,
                FOREIGN KEY(trade_id) REFERENCES ordens(trade_id)
            )
        """)

        # Tabela de posicoes encerradas (histórico)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS posicoes_encerradas (
                posicao_id TEXT PRIMARY KEY,
                trade_id TEXT NOT NULL UNIQUE,
                signal_id TEXT NOT NULL,
                symbol TEXT NOT NULL,
                direcao TEXT NOT NULL,
                volume INTEGER NOT NULL,
                preco_entrada REAL NOT NULL,
                preco_encerramento REAL NOT NULL,
                pl_final REAL NOT NULL,
                criado_em TEXT NOT NULL,
                encerrado_em TEXT NOT NULL,
                FOREIGN KEY(trade_id) REFERENCES ordens(trade_id)
            )
        """)

        # Tabela de eventos de monitoramento
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS eventos_monitoramento (
                evento_id TEXT PRIMARY KEY,
                trade_id TEXT NOT NULL,
                tipo_evento TEXT NOT NULL,
                descricao TEXT,
                timestamp TEXT NOT NULL,
                FOREIGN KEY(trade_id) REFERENCES ordens(trade_id)
            )
        """)

        self.bd_conexao.commit()

    # ====================================================================
    # OPERACOES DE ORDEM
    # ====================================================================

    def registrar_ordem(self, ordem_spec: Dict[str, Any]) -> bool:
        """
        Registra nova ordem entrante de AC5.

        Args:
            ordem_spec: Dict com trade_id, signal_id, symbol, direcao, volume,
                       preco_entrada, sl, tp

        Returns:
            True se registrada, False se erro (ex: duplicada)
        """
        try:
            cursor = self.bd_conexao.cursor()
            agora = datetime.now(timezone.utc).isoformat()

            cursor.execute("""
                INSERT INTO ordens (
                    trade_id, signal_id, symbol, direcao, volume,
                    preco_entrada, sl, tp, status, criado_em, atualizado_em
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                ordem_spec["trade_id"],
                ordem_spec["signal_id"],
                ordem_spec["symbol"],
                ordem_spec["direcao"],
                ordem_spec["volume"],
                ordem_spec["preco_entrada"],
                ordem_spec["sl"],
                ordem_spec["tp"],
                StatusOrdem.PENDING.value,
                agora,
                agora,
            ))

            # Criar posicao aberta correspondente
            posicao_id = f"POS_{ordem_spec['trade_id']}"
            cursor.execute("""
                INSERT INTO posicoes_abertas (
                    posicao_id, trade_id, signal_id, symbol, direcao, volume,
                    preco_entrada, sl, tp, preco_atual, pl, status,
                    criado_em, atualizado_em
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                posicao_id,
                ordem_spec["trade_id"],
                ordem_spec["signal_id"],
                ordem_spec["symbol"],
                ordem_spec["direcao"],
                ordem_spec["volume"],
                ordem_spec["preco_entrada"],
                ordem_spec["sl"],
                ordem_spec["tp"],
                ordem_spec["preco_entrada"],  # Preço atual = entrada inicialmente
                0.0,  # PL inicial = 0
                StatusPosicao.ABERTA.value,
                agora,
                agora,
            ))

            self.registrar_evento(
                ordem_spec["trade_id"],
                "ORDEM_REGISTRADA",
                f"Ordem registrada: {ordem_spec['symbol']} {ordem_spec['direcao']}",
            )

            self.bd_conexao.commit()
            logger.info(f"Ordem registrada: {ordem_spec['trade_id']}")
            return True

        except sqlite3.IntegrityError:
            logger.error(f"Erro ao registrar ordem: Duplicada {ordem_spec.get('trade_id')}")
            return False
        except Exception as e:
            logger.error(f"Erro ao registrar ordem: {e}")
            return False

    def atualizar_status_ordem(self, trade_id: str, novo_status: StatusOrdem) -> bool:
        """
        Atualiza status da ordem (PENDING → SENT → FILLED).

        Args:
            trade_id: ID da ordem
            novo_status: Novo status

        Returns:
            True se atualizado, False se erro
        """
        try:
            cursor = self.bd_conexao.cursor()
            agora = datetime.now(timezone.utc).isoformat()

            cursor.execute("""
                UPDATE ordens
                SET status = ?, atualizado_em = ?
                WHERE trade_id = ?
            """, (novo_status.value, agora, trade_id))

            if cursor.rowcount == 0:
                logger.error(f"Ordem nao encontrada: {trade_id}")
                return False

            # Se FILLED, atualizar status da posicao também
            if novo_status == StatusOrdem.FILLED:
                cursor.execute("""
                    UPDATE posicoes_abertas
                    SET status = ?, atualizado_em = ?
                    WHERE trade_id = ?
                """, (StatusPosicao.ABERTA.value, agora, trade_id))

            self.registrar_evento(
                trade_id,
                "STATUS_ATUALIZADO",
                f"Status atualizado para {novo_status.value}",
            )

            self.bd_conexao.commit()
            logger.info(f"Status atualizado: {trade_id} → {novo_status.value}")
            return True

        except Exception as e:
            logger.error(f"Erro ao atualizar status: {e}")
            return False

    # ====================================================================
    # MONITORAMENTO DE PRECO
    # ====================================================================

    def atualizar_preco_posicao(self, trade_id: str, preco_atual: float) -> bool:
        """
        Atualiza preco atual de posicao aberta e calcula P&L.

        Args:
            trade_id: ID da posicao
            preco_atual: Novo preco de mercado

        Returns:
            True se atualizado, False se erro
        """
        try:
            cursor = self.bd_conexao.cursor()
            agora = datetime.now(timezone.utc).isoformat()

            # Obter posicao para calcular P&L
            cursor.execute("""
                SELECT preco_entrada, direcao, volume FROM posicoes_abertas
                WHERE trade_id = ?
            """, (trade_id,))
            row = cursor.fetchone()

            if not row:
                logger.error(f"Posicao nao encontrada: {trade_id}")
                return False

            preco_entrada = row["preco_entrada"]
            direcao = row["direcao"]
            volume = row["volume"]

            # Calcular P&L
            if direcao == DirecaoOperacao.BUY.value:
                pl = (preco_atual - preco_entrada) * volume
            else:  # SELL
                pl = (preco_entrada - preco_atual) * volume

            # Atualizar preco e P&L
            cursor.execute("""
                UPDATE posicoes_abertas
                SET preco_atual = ?, pl = ?, atualizado_em = ?
                WHERE trade_id = ?
            """, (preco_atual, pl, agora, trade_id))

            self.registrar_evento(
                trade_id,
                "PRECO_ATUALIZADO",
                f"Preco atualizado: {preco_atual} | P&L: {pl:.2f}",
            )

            self.bd_conexao.commit()
            logger.debug(f"Preco atualizado: {trade_id} → {preco_atual} | P&L: {pl:.2f}")
            return True

        except Exception as e:
            logger.error(f"Erro ao atualizar preco: {e}")
            return False

    # ====================================================================
    # ENCERRAMENTO E CANCELAMENTO
    # ====================================================================

    def encerrar_posicao(self, trade_id: str, preco_encerramento: float) -> bool:
        """
        Encerra posicao (TP ou SL atingido).

        Args:
            trade_id: ID da posicao
            preco_encerramento: Preco de encerrwmento

        Returns:
            True se encerrada, False se erro
        """
        try:
            cursor = self.bd_conexao.cursor()
            agora = datetime.now(timezone.utc).isoformat()

            # Obter dados da posicao
            cursor.execute("""
                SELECT * FROM posicoes_abertas WHERE trade_id = ?
            """, (trade_id,))
            row = cursor.fetchone()

            if not row:
                logger.error(f"Posicao nao encontrada: {trade_id}")
                return False

            # Calcular P&L final
            preco_entrada = row["preco_entrada"]
            direcao = row["direcao"]
            volume = row["volume"]

            if direcao == DirecaoOperacao.BUY.value:
                pl_final = (preco_encerramento - preco_entrada) * volume
            else:  # SELL
                pl_final = (preco_entrada - preco_encerramento) * volume

            # Mover para posicoes encerradas
            cursor.execute("""
                INSERT INTO posicoes_encerradas (
                    posicao_id, trade_id, signal_id, symbol, direcao, volume,
                    preco_entrada, preco_encerramento, pl_final, criado_em, encerrado_em
                ) SELECT
                    posicao_id, trade_id, signal_id, symbol, direcao, volume,
                    preco_entrada, ?, ?, criado_em, ?
                FROM posicoes_abertas
                WHERE trade_id = ?
            """, (preco_encerramento, pl_final, agora, trade_id))

            # Deletar posicao aberta
            cursor.execute("""
                DELETE FROM posicoes_abertas WHERE trade_id = ?
            """, (trade_id,))

            # Atualizar status da ordem
            cursor.execute("""
                UPDATE ordens
                SET status = ?, atualizado_em = ?
                WHERE trade_id = ?
            """, (StatusOrdem.CANCELLED.value, agora, trade_id))

            self.registrar_evento(
                trade_id,
                "POSICAO_ENCERRADA",
                f"Posicao encerrada em {preco_encerramento} | P&L: {pl_final:.2f}",
            )

            self.bd_conexao.commit()
            logger.info(f"Posicao encerrada: {trade_id} | P&L: {pl_final:.2f}")
            return True

        except Exception as e:
            logger.error(f"Erro ao encerrar posicao: {e}")
            return False

    def cancelar_ordem(self, trade_id: str) -> bool:
        """
        Cancela ordem antes de executar.

        Args:
            trade_id: ID da ordem

        Returns:
            True se cancelada, False se erro
        """
        try:
            cursor = self.bd_conexao.cursor()
            agora = datetime.now(timezone.utc).isoformat()

            # Atualizar status da ordem
            cursor.execute("""
                UPDATE ordens
                SET status = ?, atualizado_em = ?
                WHERE trade_id = ?
            """, (StatusOrdem.CANCELLED.value, agora, trade_id))

            if cursor.rowcount == 0:
                return False

            # Remover posicao aberta correspondente
            cursor.execute("""
                DELETE FROM posicoes_abertas WHERE trade_id = ?
            """, (trade_id,))

            self.registrar_evento(
                trade_id,
                "ORDEM_CANCELADA",
                "Ordem cancelada pelo usuario",
            )

            self.bd_conexao.commit()
            logger.info(f"Ordem cancelada: {trade_id}")
            return True

        except Exception as e:
            logger.error(f"Erro ao cancelar ordem: {e}")
            return False

    def rejeitar_ordem(self, trade_id: str, motivo: str) -> bool:
        """
        Registra rejeicao de ordem de MT5.

        Args:
            trade_id: ID da ordem
            motivo: Motivo da rejeicao

        Returns:
            True se registrada, False se erro
        """
        try:
            cursor = self.bd_conexao.cursor()
            agora = datetime.now(timezone.utc).isoformat()

            # Atualizar status da ordem
            cursor.execute("""
                UPDATE ordens
                SET status = ?, atualizado_em = ?
                WHERE trade_id = ?
            """, (StatusOrdem.REJECTED.value, agora, trade_id))

            if cursor.rowcount == 0:
                return False

            # Remover posicao aberta
            cursor.execute("""
                DELETE FROM posicoes_abertas WHERE trade_id = ?
            """, (trade_id,))

            self.registrar_evento(
                trade_id,
                "ORDEM_REJEITADA",
                f"Ordem rejeitada: {motivo}",
            )

            self.bd_conexao.commit()
            logger.warning(f"Ordem rejeitada: {trade_id} | Motivo: {motivo}")
            return True

        except Exception as e:
            logger.error(f"Erro ao rejeitar ordem: {e}")
            return False

    # ====================================================================
    # CONSULTAS
    # ====================================================================

    def listar_posicoes_abertas(self) -> List[Dict[str, Any]]:
        """
        Lista todas posicoes abertas.

        Returns:
            Lista de dicts com dados das posicoes
        """
        cursor = self.bd_conexao.cursor()
        cursor.execute("SELECT * FROM posicoes_abertas ORDER BY criado_em DESC")
        return [dict(row) for row in cursor.fetchall()]

    def listar_posicoes_encerradas(self) -> List[Dict[str, Any]]:
        """
        Lista posicoes encerradas (historico).

        Returns:
            Lista de dicts com dados das posicoes encerradas
        """
        cursor = self.bd_conexao.cursor()
        cursor.execute("SELECT * FROM posicoes_encerradas ORDER BY encerrado_em DESC")
        return [dict(row) for row in cursor.fetchall()]

    def obter_posicao(self, trade_id: str) -> Optional[Dict[str, Any]]:
        """
        Obtem posicao especifica por trade_id.

        Args:
            trade_id: ID da posicao

        Returns:
            Dict com dados ou None se nao encontrada
        """
        cursor = self.bd_conexao.cursor()
        cursor.execute("SELECT * FROM posicoes_abertas WHERE trade_id = ?", (trade_id,))
        row = cursor.fetchone()
        return dict(row) if row else None

    def contar_posicoes_abertas(self) -> int:
        """Conta total de posicoes abertas."""
        cursor = self.bd_conexao.cursor()
        cursor.execute("SELECT COUNT(*) as count FROM posicoes_abertas")
        row = cursor.fetchone()
        if row is None:
            return 0
        return int(row["count"])

    # ====================================================================
    # RASTREAMENTO DE EVENTOS
    # ====================================================================

    def registrar_evento(
        self, trade_id: str, tipo_evento: str, descricao: Optional[str] = None
    ) -> str:
        """
        Registra evento de monitoramento para auditoria.

        Args:
            trade_id: ID da ordem
            tipo_evento: Tipo de evento (ORDEM_REGISTRADA, PRECO_ATUALIZADO, etc)
            descricao: Descricao adicional

        Returns:
            evento_id
        """
        try:
            cursor = self.bd_conexao.cursor()
            evento_id = f"EVT_{uuid4()}"
            timestamp = datetime.now(timezone.utc).isoformat()

            cursor.execute("""
                INSERT INTO eventos_monitoramento (
                    evento_id, trade_id, tipo_evento, descricao, timestamp
                ) VALUES (?, ?, ?, ?, ?)
            """, (evento_id, trade_id, tipo_evento, descricao, timestamp))

            self.bd_conexao.commit()
            return evento_id

        except Exception as e:
            logger.error(f"Erro ao registrar evento: {e}")
            return ""

    def listar_eventos(self, trade_id: str) -> List[Dict[str, Any]]:
        """
        Lista eventos de uma ordem.

        Args:
            trade_id: ID da ordem

        Returns:
            Lista de eventos ordenada por timestamp
        """
        cursor = self.bd_conexao.cursor()
        cursor.execute("""
            SELECT * FROM eventos_monitoramento
            WHERE trade_id = ?
            ORDER BY timestamp DESC
        """, (trade_id,))
        return [dict(row) for row in cursor.fetchall()]

    def obter_relatorio_resumido(self) -> Dict[str, Any]:
        """
        Obtem relatorio resumido de posicoes.

        Returns:
            Dict com estatisticas (abertas, encerradas, P&L total, etc)
        """
        try:
            cursor = self.bd_conexao.cursor()

            # Aberta
            cursor.execute("""
                SELECT COUNT(*) as total, COALESCE(SUM(pl), 0) as pl_total
                FROM posicoes_abertas
            """)
            dados_abertas = cursor.fetchone()

            # Encerradas
            cursor.execute("""
                SELECT COUNT(*) as total, COALESCE(SUM(pl_final), 0) as pl_total
                FROM posicoes_encerradas
            """)
            dados_encerradas = cursor.fetchone()

            return {
                "posicoes_abertas": dados_abertas["total"],
                "pl_aberto": float(dados_abertas["pl_total"]),
                "posicoes_encerradas": dados_encerradas["total"],
                "pl_encerrado": float(dados_encerradas["pl_total"]),
                "pl_total": float(dados_abertas["pl_total"]) + float(dados_encerradas["pl_total"]),
            }

        except Exception as e:
            logger.error(f"Erro ao gerar relatorio: {e}")
            return {}

    # ====================================================================
    # LIFECYCLE
    # ====================================================================

    def fechar(self) -> None:
        """Fecha conexao com BD."""
        if self.bd_conexao:
            self.bd_conexao.close()
            logger.info("Conexao com BD fechada")

    def __enter__(self) -> "MonitorPositionManager":
        """Context manager: enter."""
        return self

    def __exit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        """Context manager: exit."""
        self.fechar()
