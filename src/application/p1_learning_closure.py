"""P1-LEARNING: Etapa 4 - Closure (outcome + exit reason)

Registro de fechamento de posicao com resultado final e motivo de saida.

Objetivo:
  - Capturar o resultado final de cada episodio causal
  - Registrar motivo de fechamento (TP, SL, manual, timeout, cancelado)
  - Calcular P&L realizado e duracao total
  - Ligar fechamento ao episodio das Etapas 1-3 via episode_id
  - Gerar relatorios JSON + Markdown para auditoria

Schema:
  - episode_closures (18 campos):
    - Chave primaria: closure_id (UUID)
    - Vinculo: episode_id, trade_id
    - Resultado: outcome (WIN/LOSS/BREAKEVEN)
    - Motivo: motivo_fechamento (TP_ATINGIDO, SL_ATINGIDO, ...)
    - Financeiro: pnl_realizado, pnl_realizado_pct
    - Temporal: timestamp_fechamento, duracao_total_segundos
    - Contexto: preco_entrada, preco_saida, market_conditions

Pipeline:
    Etapa 1 (Signal Detection) -> p1_learning_engine.py
    Etapa 2 (Decision Recording) -> p1_learning_engine.py
    Etapa 3 (Monitoring) -> p1_learning_monitoring.py
    Etapa 4 (Closure) -> p1_learning_closure.py  [este modulo]
    Etapa 5 (L1 Analysis) -> proximo
    Etapa 6 (L2 Causal Analysis) -> proximo
    Etapa 7 (Learning Rule) -> proximo

Exemplo:
    engine = EpisodeClosureEngine(db_path="data/db/causal.db")

    closure_id = engine.registrar_fechamento(
        episode_id="EP_20260316_140030",
        trade_id="TRD_20260316_140030",
        preco_entrada=141500.0,
        preco_saida=143500.0,
        pnl_realizado=2000.0,
        pnl_realizado_pct=1.41,
        motivo_fechamento=MotivoFechamento.TP_ATINGIDO,
        duracao_total_segundos=1800,
        market_conditions={"volatility": 1.1, "trend": "UP"},
    )

    # Obter fechamento registrado
    closure = engine.obter_fechamento(closure_id)

    # Estatisticas de todos os fechamentos
    stats = engine.calcular_estatisticas_fechamentos()

Type hints: 100%
Docstrings: 100% em portugues
"""

import json
import sqlite3
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional


# ============================================================================
# ENUMS
# ============================================================================


class OutcomeType(str, Enum):
    """Tipo de resultado final do trade.

    Valores:
        WIN: Trade encerrado com lucro positivo
        LOSS: Trade encerrado com prejuizo
        BREAKEVEN: Trade encerrado no ponto de equilibrio (+/- 0)
    """

    WIN = "WIN"
    LOSS = "LOSS"
    BREAKEVEN = "BREAKEVEN"


class MotivoFechamento(str, Enum):
    """Motivo que causou o fechamento da posicao.

    Valores:
        TP_ATINGIDO: Take profit atingido automaticamente
        SL_ATINGIDO: Stop loss atingido automaticamente
        FECHAMENTO_MANUAL: Operador fechou manualmente
        TIMEOUT: Posicao aberta por tempo excessivo
        CANCELADO: Operacao cancelada antes de executar
        SISTEMA: Fechamento por regra de sistema (ex: fim do pregao)
    """

    TP_ATINGIDO = "TP_ATINGIDO"
    SL_ATINGIDO = "SL_ATINGIDO"
    FECHAMENTO_MANUAL = "FECHAMENTO_MANUAL"
    TIMEOUT = "TIMEOUT"
    CANCELADO = "CANCELADO"
    SISTEMA = "SISTEMA"


# ============================================================================
# DATACLASSES
# ============================================================================


@dataclass
class ClosureRecord:
    """Registro de fechamento de episodio causal (Etapa 4).

    Captura o resultado final de uma posicao apos seu encerramento,
    incluindo P&L realizado, motivo de saida e contexto de mercado.

    Atributos:
        closure_id: Identificador unico do fechamento (UUID)
        episode_id: Vinculo com episodio causal (Etapas 1-3)
        trade_id: Identificador da ordem no broker
        timestamp_fechamento: Momento do fechamento
        preco_entrada: Preco de abertura da posicao
        preco_saida: Preco de fechamento da posicao
        outcome: Resultado (WIN, LOSS, BREAKEVEN)
        motivo_fechamento: Causa do encerramento
        pnl_realizado: Lucro/prejuizo realizado em valor absoluto
        pnl_realizado_pct: Lucro/prejuizo em percentual
        duracao_total_segundos: Tempo total da posicao aberta
        market_conditions: Condicoes de mercado no momento do fechamento
        notas: Observacoes opcionais do operador ou sistema
        criado_em: Timestamp de criacao do registro
    """

    closure_id: str
    episode_id: str
    trade_id: str
    timestamp_fechamento: datetime
    preco_entrada: float
    preco_saida: float
    outcome: OutcomeType
    motivo_fechamento: MotivoFechamento
    pnl_realizado: float
    pnl_realizado_pct: float
    duracao_total_segundos: float
    market_conditions: Dict[str, Any]
    notas: Optional[str] = None
    criado_em: datetime = field(default_factory=datetime.now)

    def para_dict(self) -> Dict[str, Any]:
        """Converte para dicionario JSON-serializable.

        Returns:
            Dicionario completo com timestamps em ISO format e
            enums convertidos para string.
        """
        return {
            "closure_id": self.closure_id,
            "episode_id": self.episode_id,
            "trade_id": self.trade_id,
            "timestamp_fechamento": self.timestamp_fechamento.isoformat(),
            "preco_entrada": self.preco_entrada,
            "preco_saida": self.preco_saida,
            "outcome": self.outcome.value,
            "motivo_fechamento": self.motivo_fechamento.value,
            "pnl_realizado": self.pnl_realizado,
            "pnl_realizado_pct": self.pnl_realizado_pct,
            "duracao_total_segundos": self.duracao_total_segundos,
            "market_conditions": self.market_conditions,
            "notas": self.notas,
            "criado_em": self.criado_em.isoformat(),
        }


# ============================================================================
# ENGINE PRINCIPAL
# ============================================================================


class EpisodeClosureEngine:
    """Engine para registrar fechamentos de episodios causais (Etapa 4).

    Responsabilidades:
    - Registrar o resultado final de cada episodio (outcome + motivo)
    - Calcular estatisticas agregadas de fechamentos
    - Gerar relatorios JSON e Markdown para auditoria
    - Vincular fechamento ao historico das Etapas 1-3 via episode_id

    Atributos privados:
        _db_path: Caminho para banco SQLite
        _table_name: Nome da tabela principal

    Exemplo:
        engine = EpisodeClosureEngine()
        closure_id = engine.registrar_fechamento(
            episode_id="EP_001",
            trade_id="TRD_001",
            preco_entrada=141500.0,
            preco_saida=143500.0,
            pnl_realizado=2000.0,
            pnl_realizado_pct=1.41,
            motivo_fechamento=MotivoFechamento.TP_ATINGIDO,
            duracao_total_segundos=1800,
        )
    """

    BREAKEVEN_THRESHOLD_PCT: float = 0.05  # +/- 0.05% = breakeven

    def __init__(self, db_path: Optional[str] = None) -> None:
        """Inicializa engine e cria tabela se necessario.

        Args:
            db_path: Caminho para arquivo SQLite.
                     Default: data/db/causal_learning.db
        """
        if db_path is None:
            self._db_path: str = str(Path("data/db/causal_learning.db"))
        else:
            self._db_path = db_path

        Path(self._db_path).parent.mkdir(parents=True, exist_ok=True)
        self._table_name: str = "episode_closures"
        self._criar_tabela()

    def _criar_tabela(self) -> None:
        """Cria tabela episode_closures com schema completo.

        Schema contem 18 campos:
        - closure_id: Chave primaria UUID
        - episode_id, trade_id: Vinculos
        - timestamp_fechamento: Momento do fechamento
        - preco_entrada, preco_saida: Precos da operacao
        - outcome: WIN/LOSS/BREAKEVEN
        - motivo_fechamento: Causa do encerramento
        - pnl_realizado, pnl_realizado_pct: Resultado financeiro
        - duracao_total_segundos: Tempo de exposicao
        - market_conditions: JSON de contexto
        - notas: Texto livre
        - criado_em: Timestamp do registro
        """
        conn = sqlite3.connect(self._db_path)
        cursor = conn.cursor()

        cursor.execute(
            f"""
            CREATE TABLE IF NOT EXISTS {self._table_name} (
                closure_id TEXT PRIMARY KEY,
                episode_id TEXT NOT NULL,
                trade_id TEXT NOT NULL,
                timestamp_fechamento TEXT NOT NULL,
                preco_entrada REAL NOT NULL,
                preco_saida REAL NOT NULL,
                outcome TEXT NOT NULL,
                motivo_fechamento TEXT NOT NULL,
                pnl_realizado REAL NOT NULL,
                pnl_realizado_pct REAL NOT NULL,
                duracao_total_segundos REAL NOT NULL,
                market_conditions TEXT NOT NULL DEFAULT '{{}}',
                notas TEXT,
                criado_em TEXT DEFAULT CURRENT_TIMESTAMP
            )
            """
        )

        # Indices para performance
        cursor.execute(
            f"CREATE INDEX IF NOT EXISTS idx_episode_{self._table_name} "
            f"ON {self._table_name}(episode_id)"
        )
        cursor.execute(
            f"CREATE INDEX IF NOT EXISTS idx_trade_{self._table_name} "
            f"ON {self._table_name}(trade_id)"
        )
        cursor.execute(
            f"CREATE INDEX IF NOT EXISTS idx_outcome_{self._table_name} "
            f"ON {self._table_name}(outcome)"
        )

        conn.commit()
        conn.close()

    # ========================================================================
    # REGISTRO DE FECHAMENTO
    # ========================================================================

    def registrar_fechamento(
        self,
        episode_id: str,
        trade_id: str,
        preco_entrada: float,
        preco_saida: float,
        pnl_realizado: float,
        pnl_realizado_pct: float,
        motivo_fechamento: MotivoFechamento,
        duracao_total_segundos: float,
        market_conditions: Optional[Dict[str, Any]] = None,
        notas: Optional[str] = None,
        timestamp_fechamento: Optional[datetime] = None,
    ) -> str:
        """Registra o fechamento de um episodio causal.

        Determina automaticamente o outcome (WIN/LOSS/BREAKEVEN)
        com base no pnl_realizado_pct e no threshold de breakeven.

        Args:
            episode_id: ID do episodio causal (vinculo com Etapas 1-3)
            trade_id: ID da ordem no broker
            preco_entrada: Preco de abertura da posicao
            preco_saida: Preco de fechamento da posicao
            pnl_realizado: P&L realizado em valor absoluto (R$)
            pnl_realizado_pct: P&L realizado em percentual
            motivo_fechamento: Motivo do encerramento
            duracao_total_segundos: Duracao da posicao em segundos
            market_conditions: Condicoes de mercado no fechamento
            notas: Observacoes opcionais
            timestamp_fechamento: Momento do fechamento (default: agora)

        Returns:
            closure_id gerado (UUID string)

        Raises:
            sqlite3.Error: Se falhar na persistencia
        """
        if market_conditions is None:
            market_conditions = {}

        if timestamp_fechamento is None:
            timestamp_fechamento = datetime.now()

        # Determinar outcome automaticamente
        outcome = self._determinar_outcome(pnl_realizado_pct)

        # Gerar ID unico
        closure_id = str(uuid.uuid4())

        # Criar registro
        registro = ClosureRecord(
            closure_id=closure_id,
            episode_id=episode_id,
            trade_id=trade_id,
            timestamp_fechamento=timestamp_fechamento,
            preco_entrada=preco_entrada,
            preco_saida=preco_saida,
            outcome=outcome,
            motivo_fechamento=motivo_fechamento,
            pnl_realizado=pnl_realizado,
            pnl_realizado_pct=pnl_realizado_pct,
            duracao_total_segundos=duracao_total_segundos,
            market_conditions=market_conditions,
            notas=notas,
        )

        # Persistir
        conn = sqlite3.connect(self._db_path)
        cursor = conn.cursor()

        cursor.execute(
            f"""
            INSERT INTO {self._table_name} (
                closure_id, episode_id, trade_id,
                timestamp_fechamento, preco_entrada, preco_saida,
                outcome, motivo_fechamento,
                pnl_realizado, pnl_realizado_pct,
                duracao_total_segundos, market_conditions, notas,
                criado_em
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                closure_id,
                episode_id,
                trade_id,
                timestamp_fechamento.isoformat(),
                preco_entrada,
                preco_saida,
                outcome.value,
                motivo_fechamento.value,
                pnl_realizado,
                pnl_realizado_pct,
                duracao_total_segundos,
                json.dumps(market_conditions),
                notas,
                registro.criado_em.isoformat(),
            ),
        )

        conn.commit()
        conn.close()

        return closure_id

    def _determinar_outcome(self, pnl_pct: float) -> OutcomeType:
        """Determina o outcome com base no percentual de P&L.

        Regras:
        - abs(pnl_pct) <= BREAKEVEN_THRESHOLD_PCT -> BREAKEVEN
        - pnl_pct > threshold -> WIN
        - pnl_pct < -threshold -> LOSS

        Args:
            pnl_pct: Percentual de lucro/prejuizo

        Returns:
            OutcomeType correspondente
        """
        if abs(pnl_pct) <= self.BREAKEVEN_THRESHOLD_PCT:
            return OutcomeType.BREAKEVEN
        if pnl_pct > 0:
            return OutcomeType.WIN
        return OutcomeType.LOSS

    # ========================================================================
    # CONSULTAS
    # ========================================================================

    def obter_fechamento(
        self, closure_id: str
    ) -> Optional[ClosureRecord]:
        """Obtém um fechamento pelo closure_id.

        Args:
            closure_id: ID do fechamento

        Returns:
            ClosureRecord ou None se nao encontrado
        """
        conn = sqlite3.connect(self._db_path)
        cursor = conn.cursor()

        cursor.execute(
            f"""
            SELECT
                closure_id, episode_id, trade_id,
                timestamp_fechamento, preco_entrada, preco_saida,
                outcome, motivo_fechamento,
                pnl_realizado, pnl_realizado_pct,
                duracao_total_segundos, market_conditions, notas,
                criado_em
            FROM {self._table_name}
            WHERE closure_id = ?
            """,
            (closure_id,),
        )

        row = cursor.fetchone()
        conn.close()

        if row is None:
            return None

        return self._row_para_closure(row)

    def obter_fechamento_por_episode(
        self, episode_id: str
    ) -> Optional[ClosureRecord]:
        """Obtém o fechamento de um episodio pelo episode_id.

        Args:
            episode_id: ID do episodio causal

        Returns:
            ClosureRecord ou None se episodio nao foi fechado
        """
        conn = sqlite3.connect(self._db_path)
        cursor = conn.cursor()

        cursor.execute(
            f"""
            SELECT
                closure_id, episode_id, trade_id,
                timestamp_fechamento, preco_entrada, preco_saida,
                outcome, motivo_fechamento,
                pnl_realizado, pnl_realizado_pct,
                duracao_total_segundos, market_conditions, notas,
                criado_em
            FROM {self._table_name}
            WHERE episode_id = ?
            ORDER BY criado_em DESC
            LIMIT 1
            """,
            (episode_id,),
        )

        row = cursor.fetchone()
        conn.close()

        if row is None:
            return None

        return self._row_para_closure(row)

    def listar_fechamentos(
        self,
        outcome: Optional[OutcomeType] = None,
        motivo: Optional[MotivoFechamento] = None,
        limite: int = 100,
    ) -> List[ClosureRecord]:
        """Lista fechamentos com filtros opcionais.

        Args:
            outcome: Filtrar por tipo de resultado (opcional)
            motivo: Filtrar por motivo de fechamento (opcional)
            limite: Numero maximo de registros (default: 100)

        Returns:
            Lista de ClosureRecord ordenados por timestamp decrescente
        """
        conn = sqlite3.connect(self._db_path)
        cursor = conn.cursor()

        filtros = []
        params: List[Any] = []

        if outcome is not None:
            filtros.append("outcome = ?")
            params.append(outcome.value)

        if motivo is not None:
            filtros.append("motivo_fechamento = ?")
            params.append(motivo.value)

        where_clause = (
            "WHERE " + " AND ".join(filtros) if filtros else ""
        )

        params.append(limite)
        cursor.execute(
            f"""
            SELECT
                closure_id, episode_id, trade_id,
                timestamp_fechamento, preco_entrada, preco_saida,
                outcome, motivo_fechamento,
                pnl_realizado, pnl_realizado_pct,
                duracao_total_segundos, market_conditions, notas,
                criado_em
            FROM {self._table_name}
            {where_clause}
            ORDER BY timestamp_fechamento DESC
            LIMIT ?
            """,
            tuple(params),
        )

        rows = cursor.fetchall()
        conn.close()

        return [self._row_para_closure(r) for r in rows]

    def _row_para_closure(
        self, row: tuple  # type: ignore[type-arg]
    ) -> ClosureRecord:
        """Converte linha do banco para ClosureRecord.

        Args:
            row: Tupla com 14 campos na ordem definida pelo SELECT

        Returns:
            ClosureRecord populado
        """
        (
            closure_id,
            episode_id,
            trade_id,
            ts_fechamento,
            preco_entrada,
            preco_saida,
            outcome_str,
            motivo_str,
            pnl_realizado,
            pnl_pct,
            duracao,
            market_cond_json,
            notas,
            criado_em_str,
        ) = row

        return ClosureRecord(
            closure_id=closure_id,
            episode_id=episode_id,
            trade_id=trade_id,
            timestamp_fechamento=datetime.fromisoformat(ts_fechamento),
            preco_entrada=preco_entrada,
            preco_saida=preco_saida,
            outcome=OutcomeType(outcome_str),
            motivo_fechamento=MotivoFechamento(motivo_str),
            pnl_realizado=pnl_realizado,
            pnl_realizado_pct=pnl_pct,
            duracao_total_segundos=duracao,
            market_conditions=(
                json.loads(market_cond_json)
                if market_cond_json
                else {}
            ),
            notas=notas,
            criado_em=datetime.fromisoformat(criado_em_str),
        )

    # ========================================================================
    # ESTATISTICAS
    # ========================================================================

    def calcular_estatisticas_fechamentos(self) -> Dict[str, Any]:
        """Calcula estatisticas agregadas de todos os fechamentos.

        Metricas:
        - total: Total de fechamentos registrados
        - wins / losses / breakevens: Contagem por outcome
        - win_rate_pct: Percentual de operacoes vencedoras
        - pnl_total: Soma de todo P&L realizado
        - pnl_medio: Media de P&L por operacao
        - pnl_maximo: Melhor operacao
        - pnl_minimo: Pior operacao
        - duracao_media_segundos: Tempo medio de exposicao
        - contagem_por_motivo: Distribuicao de motivos de fechamento

        Returns:
            Dicionario com todas as metricas. Retorna zeros se sem dados.
        """
        conn = sqlite3.connect(self._db_path)
        cursor = conn.cursor()

        cursor.execute(
            f"""
            SELECT
                COUNT(*) as total,
                SUM(CASE WHEN outcome = 'WIN' THEN 1 ELSE 0 END) as wins,
                SUM(CASE WHEN outcome = 'LOSS' THEN 1 ELSE 0 END) as losses,
                SUM(CASE WHEN outcome = 'BREAKEVEN' THEN 1 ELSE 0 END)
                    as breakevens,
                SUM(pnl_realizado) as pnl_total,
                AVG(pnl_realizado) as pnl_medio,
                MAX(pnl_realizado) as pnl_maximo,
                MIN(pnl_realizado) as pnl_minimo,
                AVG(duracao_total_segundos) as duracao_media
            FROM {self._table_name}
            """
        )

        row = cursor.fetchone()

        # Contagem por motivo
        cursor.execute(
            f"""
            SELECT motivo_fechamento, COUNT(*) as contagem
            FROM {self._table_name}
            GROUP BY motivo_fechamento
            ORDER BY contagem DESC
            """
        )
        motivos_rows = cursor.fetchall()
        conn.close()

        if row is None or row[0] == 0:
            return {
                "total": 0,
                "wins": 0,
                "losses": 0,
                "breakevens": 0,
                "win_rate_pct": 0.0,
                "pnl_total": 0.0,
                "pnl_medio": 0.0,
                "pnl_maximo": 0.0,
                "pnl_minimo": 0.0,
                "duracao_media_segundos": 0.0,
                "contagem_por_motivo": {},
            }

        total = row[0] or 0
        wins = row[1] or 0

        contagem_por_motivo = {
            motivo: contagem for motivo, contagem in motivos_rows
        }

        return {
            "total": total,
            "wins": wins,
            "losses": row[2] or 0,
            "breakevens": row[3] or 0,
            "win_rate_pct": (wins / total * 100) if total > 0 else 0.0,
            "pnl_total": round(row[4] or 0.0, 2),
            "pnl_medio": round(row[5] or 0.0, 2),
            "pnl_maximo": round(row[6] or 0.0, 2),
            "pnl_minimo": round(row[7] or 0.0, 2),
            "duracao_media_segundos": round(row[8] or 0.0, 1),
            "contagem_por_motivo": contagem_por_motivo,
        }

    def contar_fechamentos(self) -> int:
        """Conta total de fechamentos registrados.

        Returns:
            Numero de registros na tabela
        """
        conn = sqlite3.connect(self._db_path)
        cursor = conn.cursor()
        cursor.execute(f"SELECT COUNT(*) FROM {self._table_name}")
        result = cursor.fetchone()
        conn.close()
        if result is None:
            return 0
        count: int = result[0]
        return count

    # ========================================================================
    # RELATORIOS
    # ========================================================================

    def gerar_relatorio_json(
        self, output_path: Optional[str] = None
    ) -> Dict[str, Any]:
        """Gera relatorio completo de fechamentos em formato JSON.

        Contem:
        - Metadados (timestamp de geracao, versao)
        - Estatisticas agregadas
        - Lista dos ultimos 50 fechamentos

        Args:
            output_path: Caminho para salvar arquivo JSON (opcional).
                         Se None, retorna apenas o dicionario.

        Returns:
            Dicionario com relatorio completo
        """
        stats = self.calcular_estatisticas_fechamentos()
        ultimos = self.listar_fechamentos(limite=50)

        relatorio: Dict[str, Any] = {
            "etapa": "P1-LEARNING Etapa 4 - Closure",
            "timestamp_geracao": datetime.now().isoformat(),
            "versao": "1.0",
            "estatisticas": stats,
            "ultimos_fechamentos": [c.para_dict() for c in ultimos],
        }

        if output_path is not None:
            Path(output_path).parent.mkdir(parents=True, exist_ok=True)
            with open(output_path, "w", encoding="utf-8") as f:
                json.dump(relatorio, f, indent=2, ensure_ascii=False)

        return relatorio

    def gerar_relatorio_markdown(self) -> str:
        """Gera relatorio de fechamentos em formato Markdown.

        Contem:
        - Titulo e data de geracao
        - Tabela de estatisticas
        - Distribuicao por motivo de fechamento
        - Ultimos 10 fechamentos com resultado

        Returns:
            String com conteudo Markdown
        """
        stats = self.calcular_estatisticas_fechamentos()
        ultimos = self.listar_fechamentos(limite=10)

        linhas = [
            "# P1-LEARNING Etapa 4 - Relatorio de Fechamentos",
            "",
            f"**Gerado em:** {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}",
            "",
            "## Estatisticas Gerais",
            "",
            "| Metrica | Valor |",
            "| ------- | ----- |",
            f"| Total de fechamentos | {stats['total']} |",
            f"| Wins | {stats['wins']} |",
            f"| Losses | {stats['losses']} |",
            f"| Breakevens | {stats['breakevens']} |",
            f"| Win Rate | {stats['win_rate_pct']:.1f}% |",
            f"| P&L Total | R$ {stats['pnl_total']:.2f} |",
            f"| P&L Medio | R$ {stats['pnl_medio']:.2f} |",
            f"| Melhor Trade | R$ {stats['pnl_maximo']:.2f} |",
            f"| Pior Trade | R$ {stats['pnl_minimo']:.2f} |",
            f"| Duracao Media | {stats['duracao_media_segundos']:.0f}s |",
            "",
            "## Distribuicao por Motivo",
            "",
            "| Motivo | Contagem |",
            "| ------ | -------- |",
        ]

        for motivo, contagem in stats.get("contagem_por_motivo", {}).items():
            linhas.append(f"| {motivo} | {contagem} |")

        if ultimos:
            linhas += [
                "",
                "## Ultimos Fechamentos",
                "",
                "| Episode | Outcome | Motivo | P&L | Duracao |",
                "| ------- | ------- | ------ | --- | ------- |",
            ]
            for c in ultimos:
                duracao_min = c.duracao_total_segundos / 60
                linhas.append(
                    f"| {c.episode_id[:16]} "
                    f"| {c.outcome.value} "
                    f"| {c.motivo_fechamento.value} "
                    f"| R$ {c.pnl_realizado:.2f} "
                    f"| {duracao_min:.1f}min |"
                )

        return "\n".join(linhas)
