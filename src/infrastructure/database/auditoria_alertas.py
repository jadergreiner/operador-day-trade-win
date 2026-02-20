"""Auditoria append-only de alertas (SQLite, CVM compliant)."""

import logging
import sqlite3
from datetime import datetime
from pathlib import Path
from typing import List, Optional

logger = logging.getLogger(__name__)


class AuditoriaAlertas:
    """
    Log append-only de alertas em SQLite.

    Requisitos CVM:
    - Retenção: 7 anos
    - Integridade: append-only (sem update/delete)
    - Rastreabilidade: todos fluxos registrados
    - Performance: índices para queries rápidas

    Tabelas:
    - alertas_audit: log de alertas gerados
    - entrega_audit: log de entregas (canais, status)
    - acao_operador_audit: log de ações do operador
    """

    SCHEMA_ALERTAS = """
    CREATE TABLE IF NOT EXISTS alertas_audit (
        id TEXT PRIMARY KEY,
        
        -- Identificação
        ativo TEXT NOT NULL,
        padr ao TEXT NOT NULL,
        nivel TEXT NOT NULL,
        
        -- Detecção
        timestamp_deteccao DATETIME NOT NULL,
        preco_atual REAL NOT NULL,
        
        -- Setup recomendado
        entrada_min REAL,
        entrada_max REAL,
        stop_loss REAL,
        take_profit REAL,
        
        -- Métricas
        confianca REAL,
        risk_reward REAL,
        
        -- Registro
        created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
        
        CONSTRAINT alertas_audit_pk PRIMARY KEY (id)
    )
    """

    SCHEMA_ENTREGA = """
    CREATE TABLE IF NOT EXISTS entrega_audit (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        alerta_id TEXT NOT NULL,
        canal TEXT NOT NULL,
        status TEXT NOT NULL,
        latencia_ms INTEGER,
        timestamp_tentativa DATETIME DEFAULT CURRENT_TIMESTAMP,
        erro_descricao TEXT,
        
        CONSTRAINT entrega_audit_fk FOREIGN KEY (alerta_id) 
            REFERENCES alertas_audit(id),
        CONSTRAINT entrega_audit_pk PRIMARY KEY (id)
    )
    """

    SCHEMA_ACAO = """
    CREATE TABLE IF NOT EXISTS acao_operador_audit (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        alerta_id TEXT NOT NULL,
        operador_username TEXT NOT NULL,
        acao TEXT NOT NULL,
        timestamp_acao DATETIME NOT NULL,
        ordem_mt5_id TEXT,
        resultado_trade TEXT,
        pnl REAL,
        timestamp_fechamento DATETIME,
        created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
        
        CONSTRAINT acao_operador_fk FOREIGN KEY (alerta_id)
            REFERENCES alertas_audit(id),
        CONSTRAINT acao_operador_pk PRIMARY KEY (id)
    )
    """

    INDICES = [
        "CREATE INDEX IF NOT EXISTS idx_alertas_data "
        "ON alertas_audit(timestamp_deteccao DESC)",
        "CREATE INDEX IF NOT EXISTS idx_alertas_ativo "
        "ON alertas_audit(ativo)",
        "CREATE INDEX IF NOT EXISTS idx_alertas_padrao "
        "ON alertas_audit(padrao)",
        "CREATE INDEX IF NOT EXISTS idx_entrega_alerta "
        "ON entrega_audit(alerta_id)",
        "CREATE INDEX IF NOT EXISTS idx_entrega_canal "
        "ON entrega_audit(canal)",
        "CREATE INDEX IF NOT EXISTS idx_entrega_status "
        "ON entrega_audit(status)",
        "CREATE INDEX IF NOT EXISTS idx_acao_alerta "
        "ON acao_operador_audit(alerta_id)",
        "CREATE INDEX IF NOT EXISTS idx_acao_operador "
        "ON acao_operador_audit(operador_username)",
        "CREATE INDEX IF NOT EXISTS idx_acao_timestamp "
        "ON acao_operador_audit(timestamp_acao DESC)",
    ]

    def __init__(self, db_path: str = "data/alertas_audit.db"):
        """
        Inicializa auditoria com database SQLite.

        Args:
            db_path: Caminho do arquivo SQLite
        """
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)

        self.conn = sqlite3.connect(str(self.db_path), check_same_thread=False)
        self.conn.row_factory = sqlite3.Row

        # Cria schema
        self._criar_schema()

        logger.info(f"✅ Auditoria inicializada: {self.db_path}")

    def _criar_schema(self) -> None:
        """Cria tabelas e índices se não existirem."""
        cursor = self.conn.cursor()

        # Tabelas
        cursor.execute(self.SCHEMA_ALERTAS)
        cursor.execute(self.SCHEMA_ENTREGA)
        cursor.execute(self.SCHEMA_ACAO)

        # Índices
        for indice in self.INDICES:
            cursor.execute(indice)

        self.conn.commit()
        logger.debug("Schema criado/validado com sucesso")

    def registrar_alerta(
        self,
        alerta_id: str,
        ativo: str,
        padrao: str,
        nivel: str,
        timestamp_deteccao: datetime,
        preco_atual: float,
        entrada_min: float,
        entrada_max: float,
        stop_loss: float,
        take_profit: Optional[float] = None,
        confianca: float = 0.0,
        risk_reward: float = 0.0,
    ) -> None:
        """
        Registra novo alerta (append-only).

        Args:
            alerta_id: UUID do alerta
            ativo: Código do ativo (WIN$N, etc)
            padrao: Padrão detectado
            nivel: Nível de severidade
            timestamp_deteccao: Quando foi detectado
            preco_atual: Preço no momento
            entrada_min: Entrada mínima recomendada
            entrada_max: Entrada máxima recomendada
            stop_loss: Stop loss recomendado
            take_profit: Take profit (opcional)
            confianca: Confiança 0-1
            risk_reward: Ratio R:R
        """
        cursor = self.conn.cursor()

        try:
            cursor.execute(
                """
                INSERT INTO alertas_audit (
                    id, ativo, padrão, nivel, timestamp_deteccao,
                    preco_atual, entrada_min, entrada_max, stop_loss,
                    take_profit, confianca, risk_reward
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    alerta_id,
                    ativo,
                    padrao,
                    nivel,
                    timestamp_deteccao,
                    preco_atual,
                    entrada_min,
                    entrada_max,
                    stop_loss,
                    take_profit,
                    confianca,
                    risk_reward,
                ),
            )
            self.conn.commit()
            logger.debug(f"Alerta registrado: {alerta_id}")

        except sqlite3.IntegrityError as e:
            logger.warning(f"Alerta já existe: {alerta_id} ({e})")
            # Não é erro fatal, apenas duplicado
        except Exception as e:
            logger.error(f"Erro ao registrar alerta: {e}")
            raise

    def registrar_entrega(
        self,
        alerta_id: str,
        canal: str,
        status: str,
        latencia_ms: int,
        erro_descricao: Optional[str] = None,
    ) -> None:
        """
        Registra tentativa de entrega (append-only).

        Args:
            alerta_id: ID do alerta
            canal: Canal de entrega (websocket, email, sms)
            status: Status (entregue, falha, timeout)
            latencia_ms: Latência em ms
            erro_descricao: Descrição de erro se houver
        """
        cursor = self.conn.cursor()

        try:
            cursor.execute(
                """
                INSERT INTO entrega_audit (
                    alerta_id, canal, status, latencia_ms, erro_descricao
                ) VALUES (?, ?, ?, ?, ?)
                """,
                (alerta_id, canal, status, latencia_ms, erro_descricao),
            )
            self.conn.commit()
            logger.debug(f"Entrega registrada: {alerta_id} / {canal} / {status}")

        except Exception as e:
            logger.error(f"Erro ao registrar entrega: {e}")
            raise

    def registrar_acao_operador(
        self,
        alerta_id: str,
        operador_username: str,
        acao: str,
        timestamp_acao: datetime,
        ordem_mt5_id: Optional[str] = None,
        resultado_trade: Optional[str] = None,
        pnl: Optional[float] = None,
        timestamp_fechamento: Optional[datetime] = None,
    ) -> None:
        """
        Registra ação do operador (append-only).

        Args:
            alerta_id: ID do alerta
            operador_username: Username do operador
            acao: Ação (EXECUTOU, REJEITOU, TIMEOUT)
            timestamp_acao: Quando executou a ação
            ordem_mt5_id: ID da ordem no MT5 (se executou)
            resultado_trade: Resultado (ganho, perda, etc)
            pnl: P&L realizado
            timestamp_fechamento: Quando trade foi fechado
        """
        cursor = self.conn.cursor()

        try:
            cursor.execute(
                """
                INSERT INTO acao_operador_audit (
                    alerta_id, operador_username, acao, timestamp_acao,
                    ordem_mt5_id, resultado_trade, pnl, timestamp_fechamento
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    alerta_id,
                    operador_username,
                    acao,
                    timestamp_acao,
                    ordem_mt5_id,
                    resultado_trade,
                    pnl,
                    timestamp_fechamento,
                ),
            )
            self.conn.commit()
            logger.info(f"Ação registrada: {alerta_id} / {acao} por {operador_username}")

        except Exception as e:
            logger.error(f"Erro ao registrar ação: {e}")
            raise

    def consultar_alertas(
        self,
        data_inicio: Optional[datetime] = None,
        data_fim: Optional[datetime] = None,
        ativo: Optional[str] = None,
        padr ao: Optional[str] = None,
        limit: int = 100,
    ) -> List[dict]:
        """
        Consulta alertas com filtros (para auditoria CVM).

        Args:
            data_inicio: Data inicial (padrão: últimas 24h)
            data_fim: Data final (padrão: agora)
            ativo: Filtrar por ativo
            padrão: Filtrar por padrão
            limit: Máximo de resultados

        Returns:
            Lista de dicts com alertas
        """
        cursor = self.conn.cursor()

        # Default: últimas 24h
        if not data_inicio:
            data_inicio = datetime.now() - timedelta(hours=24)
        if not data_fim:
            data_fim = datetime.now()

        query = "SELECT * FROM alertas_audit WHERE timestamp_deteccao BETWEEN ? AND ?"
        params = [data_inicio, data_fim]

        if ativo:
            query += " AND ativo = ?"
            params.append(ativo)

        if padrao:
            query += " AND padrão = ?"
            params.append(padrao)

        query += " ORDER BY timestamp_deteccao DESC LIMIT ?"
        params.append(limit)

        cursor.execute(query, params)
        rows = cursor.fetchall()

        return [dict(row) for row in rows]

    def obter_estatisticas(self, dias: int = 30) -> dict:
        """
        Retorna estatísticas dos últimos N dias.

        Args:
            dias: Período para análise

        Returns:
            Dict com estatísticas
        """
        cursor = self.conn.cursor()
        data_inicio = datetime.now() - timedelta(days=dias)

        # Total de alertas
        cursor.execute(
            "SELECT COUNT(*) as total FROM alertas_audit WHERE timestamp_deteccao > ?",
            (data_inicio,),
        )
        total_alertas = cursor.fetchone()["total"]

        # Por nível
        cursor.execute(
            """
            SELECT nivel, COUNT(*) as count FROM alertas_audit
            WHERE timestamp_deteccao > ?
            GROUP BY nivel
            """,
            (data_inicio,),
        )
        por_nivel = {row["nivel"]: row["count"] for row in cursor.fetchall()}

        # Taxa de entrega
        cursor.execute(
            """
            SELECT COUNT(CASE WHEN status = 'entregue' THEN 1 END) as entregues,
                   COUNT(*) as total
            FROM entrega_audit
            WHERE timestamp_tentativa > ?
            """,
            (data_inicio,),
        )
        entrega_row = cursor.fetchone()
        taxa_entrega = (
            entrega_row["entregues"] / entrega_row["total"]
            if entrega_row["total"] > 0
            else 0
        )

        # Taxa de execução
        cursor.execute(
            """
            SELECT COUNT(CASE WHEN acao = 'EXECUTOU' THEN 1 END) as executados,
                   COUNT(*) as total
            FROM acao_operador_audit
            WHERE timestamp_acao > ?
            """,
            (data_inicio,),
        )
        acao_row = cursor.fetchone()
        taxa_execucao = (
            acao_row["executados"] / acao_row["total"]
            if acao_row["total"] > 0
            else 0
        )

        return {
            "periodo_dias": dias,
            "total_alertas": total_alertas,
            "alertas_por_nivel": por_nivel,
            "taxa_entrega": taxa_entrega,
            "taxa_execucao": taxa_execucao,
        }

    def fechar(self) -> None:
        """Fecha conexão com database."""
        if self.conn:
            self.conn.close()
            logger.info("Auditoria fechada")

    def __enter__(self):
        """Context manager entry."""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.fechar()
