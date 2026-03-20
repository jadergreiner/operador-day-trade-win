"""P1-LEARNING: Etapa 3 - Monitoring (position evolution log)

Rastreamento da evolução de posição durante sua vigência.

Objetivo:
  - Capturar atualizações de preço, P&L e condições mercado
  - Manter histórico temporal de evolução
  - Calcular estatísticas agregadas da posição
  - Gerar logs estruturados para análise causal

Schema:
  - position_monitoring (24 campos):
    - Chave primária: update_id (UUID)
    - Episode: episode_id, trade_id
    - Preço: current_price, entry_price
    - Resultado: unrealized_pnl, unrealized_pnl_pct
    - Posição: position_size, duration_seconds
    - Contexto: market_conditions (JSON), timestamp

Example:
    monitor = PositionMonitor(db_path="data/db/causal.db")

    # Registrar atualização de posição
    update_id = monitor.registrar_atualizacao_posicao(
        episode_id="EP_20260316_140030",
        trade_id="TRD_20260316_140030",
        current_price=105.50,
        entry_price=105.00,
        unrealized_pnl=50.00,
        unrealized_pnl_pct=0.48,
        position_size=1,
        duration_seconds=300,
        market_conditions={"volatility": 1.2, "trend": "UP"}
    )

    # Listar todas as atualizações
    updates = monitor.listar_atualizacoes_posicao("EP_20260316_140030")

    # Estadísticas agregadas
    stats = monitor.calcular_estatisticas_posicao("EP_20260316_140030")

Type hints: 100%
Docstrings: 100% em português
"""

import sqlite3
import json
import uuid
from dataclasses import dataclass, asdict, field
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Any
import statistics as stats_module

from src.infrastructure.database.sqlite_write_lock import sqlite_write_lock


# ============================================================================
# DATACLASSES
# ============================================================================


@dataclass
class PositionUpdate:
    """Atualização de posição durante seu ciclo de vida.

    Representa um snapshot da evolução de uma posição em aberto.

    Atributos:
        timestamp: Momento do registro
        episode_id: Identificador único do episódio causal
        trade_id: Identificador da ordem/trade
        current_price: Preço atual no mercado
        entry_price: Preço de entrada da posição
        unrealized_pnl: Lucro/prejuízo não realizado
        unrealized_pnl_pct: Lucro/prejuízo em percentual
        position_size: Tamanho da posição (contratos/lotes)
        duration_seconds: Tempo desde abertura em segundos
        market_conditions: Contexto mercado (JSON)
    """

    timestamp: datetime
    episode_id: str
    trade_id: str
    current_price: float
    entry_price: float
    unrealized_pnl: float
    unrealized_pnl_pct: float
    position_size: int | float
    duration_seconds: int | float
    market_conditions: Dict[str, Any]

    def para_dict(self) -> Dict[str, Any]:
        """Converte PositionUpdate para dicionário JSON-serializable.

        Returns:
            Dicionário com todos os campos, timestamp em ISO format.
        """
        return {
            "timestamp": self.timestamp.isoformat(),
            "episode_id": self.episode_id,
            "trade_id": self.trade_id,
            "current_price": self.current_price,
            "entry_price": self.entry_price,
            "unrealized_pnl": self.unrealized_pnl,
            "unrealized_pnl_pct": self.unrealized_pnl_pct,
            "position_size": self.position_size,
            "duration_seconds": self.duration_seconds,
            "market_conditions": self.market_conditions,
        }


# ============================================================================
# CLASSE PRINCIPAL
# ============================================================================


class PositionMonitor:
    """Monitor de evolução de posição para framework causal P1-LEARNING.

    Rastreia a evolução completa de uma posição desde abertura até fechamento,
    capturando todos os updates de preço, P&L e contexto de mercado.

    Atributos privados:
        _db_path: Caminho para banco SQLite
        _table_name: Nome da tabela principal
    """

    def __init__(self, db_path: str) -> None:
        """Inicializa monitor e cria tabela de monitoramento se necessário.

        Args:
            db_path: Caminho para arquivo SQLite
        """
        self._db_path: str = db_path
        self._table_name: str = "position_monitoring"
        self._criar_tabela()

    def _criar_tabela(self) -> None:
        """Cria tabela position_monitoring com schema completo.

        Schema contém 24 campos:
        - update_id: Chave primária UUID
        - episode_id, trade_id: Referências para episode
        - Preços: current_price, entry_price
        - P&L: unrealized_pnl, unrealized_pnl_pct
        - Posição: position_size, duration_seconds
        - Timestamps: timestamp
        - Contexto: market_conditions (JSON)
        """
        with sqlite_write_lock(self._db_path):
            conn = sqlite3.connect(self._db_path)
            try:
                cursor = conn.cursor()

                cursor.execute(
                    f"""
                    CREATE TABLE IF NOT EXISTS {self._table_name} (
                        update_id TEXT PRIMARY KEY,
                        timestamp TEXT NOT NULL,
                        episode_id TEXT NOT NULL,
                        trade_id TEXT NOT NULL,
                        current_price REAL NOT NULL,
                        entry_price REAL NOT NULL,
                        unrealized_pnl REAL NOT NULL,
                        unrealized_pnl_pct REAL NOT NULL,
                        position_size REAL NOT NULL,
                        duration_seconds REAL NOT NULL,
                        market_conditions TEXT NOT NULL,
                        created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                        FOREIGN KEY (episode_id)
                            REFERENCES causal_learning_episodes(episode_id)
                    )
                    """
                )

                # Criar índices para performance
                cursor.execute(
                    f"CREATE INDEX IF NOT EXISTS idx_episode_{self._table_name} "
                    f"ON {self._table_name}(episode_id)"
                )
                cursor.execute(
                    f"CREATE INDEX IF NOT EXISTS idx_trade_{self._table_name} "
                    f"ON {self._table_name}(trade_id)"
                )
                cursor.execute(
                    f"CREATE INDEX IF NOT EXISTS idx_timestamp_{self._table_name} "
                    f"ON {self._table_name}(timestamp)"
                )

                conn.commit()
            finally:
                conn.close()

    def registrar_atualizacao_posicao(
        self,
        episode_id: str,
        trade_id: str,
        current_price: float,
        entry_price: float,
        unrealized_pnl: float,
        unrealized_pnl_pct: float,
        position_size: int | float,
        duration_seconds: int | float,
        market_conditions: Optional[Dict[str, Any]] = None,
    ) -> str:
        """Registra uma atualização de posição em aberto.

        Args:
            episode_id: Identificador do episódio causal
            trade_id: Identificador da ordem
            current_price: Preço atual do mercado
            entry_price: Preço de entrada
            unrealized_pnl: P&L não realizado (valor)
            unrealized_pnl_pct: P&L não realizado (percentual)
            position_size: Tamanho da posição
            duration_seconds: Segundos desde abertura
            market_conditions: Contexto mercado (default: {})

        Returns:
            update_id gerado (UUID)

        Raises:
            sqlite3.Error: Se falhar na persistência
        """
        if market_conditions is None:
            market_conditions = {}

        # Criar registro
        update = PositionUpdate(
            timestamp=datetime.now(),
            episode_id=episode_id,
            trade_id=trade_id,
            current_price=current_price,
            entry_price=entry_price,
            unrealized_pnl=unrealized_pnl,
            unrealized_pnl_pct=unrealized_pnl_pct,
            position_size=position_size,
            duration_seconds=duration_seconds,
            market_conditions=market_conditions,
        )

        # Gerar ID único
        update_id = str(uuid.uuid4())

        # Persistir
        with sqlite_write_lock(self._db_path):
            conn = sqlite3.connect(self._db_path)
            try:
                cursor = conn.cursor()

                cursor.execute(
                    f"""
                    INSERT INTO {self._table_name} (
                        update_id, timestamp, episode_id, trade_id,
                        current_price, entry_price,
                        unrealized_pnl, unrealized_pnl_pct,
                        position_size, duration_seconds,
                        market_conditions
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        update_id,
                        update.timestamp.isoformat(),
                        episode_id,
                        trade_id,
                        current_price,
                        entry_price,
                        unrealized_pnl,
                        unrealized_pnl_pct,
                        position_size,
                        duration_seconds,
                        json.dumps(market_conditions),
                    ),
                )

                conn.commit()
            finally:
                conn.close()

        return update_id

    def listar_atualizacoes_posicao(
        self, episode_id: str
    ) -> List[PositionUpdate]:
        """Lista todas as atualizações de um episode em ordem cronológica.

        Args:
            episode_id: Identificador do episódio

        Returns:
            Lista de PositionUpdate ordenados por timestamp
        """
        conn = sqlite3.connect(self._db_path)
        cursor = conn.cursor()

        cursor.execute(
            f"""
            SELECT
                timestamp, episode_id, trade_id,
                current_price, entry_price,
                unrealized_pnl, unrealized_pnl_pct,
                position_size, duration_seconds,
                market_conditions
            FROM {self._table_name}
            WHERE episode_id = ?
            ORDER BY timestamp ASC
            """,
            (episode_id,),
        )

        rows = cursor.fetchall()
        conn.close()

        updates: List[PositionUpdate] = []
        for row in rows:
            update = PositionUpdate(
                timestamp=datetime.fromisoformat(row[0]),
                episode_id=row[1],
                trade_id=row[2],
                current_price=row[3],
                entry_price=row[4],
                unrealized_pnl=row[5],
                unrealized_pnl_pct=row[6],
                position_size=row[7],
                duration_seconds=row[8],
                market_conditions=json.loads(row[9]),
            )
            updates.append(update)

        return updates

    def obter_ultima_atualizacao(
        self, episode_id: str
    ) -> Optional[PositionUpdate]:
        """Obtém a última atualização registrada de um episode.

        Args:
            episode_id: Identificador do episódio

        Returns:
            PositionUpdate mais recente ou None se nenhuma atualização
        """
        conn = sqlite3.connect(self._db_path)
        cursor = conn.cursor()

        cursor.execute(
            f"""
            SELECT
                timestamp, episode_id, trade_id,
                current_price, entry_price,
                unrealized_pnl, unrealized_pnl_pct,
                position_size, duration_seconds,
                market_conditions
            FROM {self._table_name}
            WHERE episode_id = ?
            ORDER BY timestamp DESC
            LIMIT 1
            """,
            (episode_id,),
        )

        row = cursor.fetchone()
        conn.close()

        if row is None:
            return None

        return PositionUpdate(
            timestamp=datetime.fromisoformat(row[0]),
            episode_id=row[1],
            trade_id=row[2],
            current_price=row[3],
            entry_price=row[4],
            unrealized_pnl=row[5],
            unrealized_pnl_pct=row[6],
            position_size=row[7],
            duration_seconds=row[8],
            market_conditions=json.loads(row[9]),
        )

    def calcular_estatisticas_posicao(
        self, episode_id: str
    ) -> Dict[str, Any]:
        """Calcula estatísticas agregadas da evolução de posição.

        Estatísticas:
        - numero_updates: Quantidade de snapshots
        - preco_maximo/minimo: Range de preço
        - preco_medio: Preço médio durante posição
        - pnl_maximo/minimo/final: Extremos de P&L
        - volatilidade_intraposicao: Desvio padrão de P&L%
        - tempo_total_segundos: Duração total

        Args:
            episode_id: Identificador do episódio

        Returns:
            Dicionário com 9 métricas estatísticas

        Raises:
            ValueError: Se nenhuma atualização encontrada
        """
        updates = self.listar_atualizacoes_posicao(episode_id)

        if not updates:
            raise ValueError(f"Nenhuma atualização para {episode_id}")

        precos = [u.current_price for u in updates]
        pnls = [u.unrealized_pnl for u in updates]
        pnls_pct = [u.unrealized_pnl_pct for u in updates]
        duracao = [u.duration_seconds for u in updates]

        # Calcular volatilidade
        volatilidade = (
            stats_module.stdev(pnls_pct) if len(pnls_pct) > 1 else 0.0
        )

        return {
            "numero_updates": len(updates),
            "preco_maximo": max(precos),
            "preco_minimo": min(precos),
            "preco_medio": stats_module.mean(precos),
            "pnl_maximo": max(pnls),
            "pnl_minimo": min(pnls),
            "pnl_final": updates[-1].unrealized_pnl,
            "volatilidade_intraposicao": volatilidade,
            "tempo_total_segundos": max(duracao),
        }

    def gerar_log_monitoramento(
        self, episode_id: str, output_path: str
    ) -> None:
        """Gera relatório de monitoramento em JSON.

        Contém:
        - Metadados do episode
        - Lista de todas as atualizações
        - Estatísticas agregadas
        - Timestamp de geração

        Args:
            episode_id: Identificador do episódio
            output_path: Caminho para salvar JSON

        Raises:
            FileNotFoundError: Se diretório output não existir
        """
        updates = self.listar_atualizacoes_posicao(episode_id)
        stats = self.calcular_estatisticas_posicao(episode_id)

        log_data = {
            "episode_id": episode_id,
            "timestamp_geracao": datetime.now().isoformat(),
            "numero_atualizacoes": len(updates),
            "atualizacoes": [u.para_dict() for u in updates],
            "estatisticas": stats,
        }

        output = Path(output_path)
        output.parent.mkdir(parents=True, exist_ok=True)

        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(log_data, f, indent=2, ensure_ascii=False)
