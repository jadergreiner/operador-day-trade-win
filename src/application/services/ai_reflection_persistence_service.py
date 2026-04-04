"""Servico de persistencia para AI Reflection (BLID-023 / ROADMAP-DIARIOS-03).

Responsavel por salvar reflexoes, registrar perguntas, acompanhar outcomes,
avaliar obsolescencia e detectar padroes recorrentes no banco SQLite.

Banco alvo: data/db/trading_diarios.db (magic_number=234800, ADR-019).
"""
from __future__ import annotations

import sqlite3
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

from src.infrastructure.database.ai_reflection_schema import (
    criar_tabelas_ai_reflection,
    obter_conexao_ai_reflection,
)


def _agora_iso() -> str:
    """Retorna timestamp ISO 8601 UTC sem dependencia de zona local."""
    return datetime.now(tz=timezone.utc).isoformat()


class AIReflectionPersistenceService:
    """Servico de persistencia para reflexoes e perguntas da IA.

    Encapsula todas as operacoes de leitura e escrita no banco SQLite
    relacionadas ao modulo de AI Reflection.

    Args:
        db_path: Caminho para o arquivo SQLite do banco de dados.
    """

    def __init__(self, db_path: Path) -> None:
        self._db_path = db_path
        criar_tabelas_ai_reflection(db_path)

    # ------------------------------------------------------------------
    # Conexao interna
    # ------------------------------------------------------------------

    def _conectar(self) -> sqlite3.Connection:
        """Retorna conexao configurada (WAL + busy_timeout)."""
        return obter_conexao_ai_reflection(self._db_path)

    # ------------------------------------------------------------------
    # Reflexoes
    # ------------------------------------------------------------------

    def salvar_reflexao(
        self,
        entry_id: str,
        timestamp: str,
        mood: str,
        decisao: str,
        confianca: float,
        alinhamento: float,
        avaliacao_honesta: str,
        relevancia_dados: str,
        sou_util: str,
        correlacao_dados: str,
        frase_ciclo: str,
    ) -> None:
        """Persiste uma reflexao da IA no banco de dados.

        Operacao idempotente: ignora silenciosamente se entry_id ja existe.

        Args:
            entry_id: Identificador unico da reflexao.
            timestamp: ISO timestamp da reflexao.
            mood: Estado emocional da IA (ex: "Frustrado", "Confiante").
            decisao: Decisao tomada (ex: "BUY", "SELL", "HOLD").
            confianca: Nivel de confianca da IA (0.0 a 1.0).
            alinhamento: Score de alinhamento com dados macro (0.0 a 1.0).
            avaliacao_honesta: Avaliacao sincera da situacao.
            relevancia_dados: Se os dados sao relevantes ("ALTA", "MEDIA", "BAIXA").
            sou_util: Auto-avaliacao da utilidade da IA.
            correlacao_dados: Correlacao dos dados com o movimento de preco.
            frase_ciclo: Frase resumo do ciclo de reflexao.
        """
        criado_em = _agora_iso()
        conn = self._conectar()
        try:
            conn.execute(
                """
                INSERT OR IGNORE INTO ai_reflection_logs (
                    entry_id, timestamp, mood, my_decision,
                    my_confidence, my_alignment, honest_assessment,
                    data_relevance, am_i_useful, my_data_correlation,
                    one_liner, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    entry_id,
                    timestamp,
                    mood,
                    decisao,
                    confianca,
                    alinhamento,
                    avaliacao_honesta,
                    relevancia_dados,
                    sou_util,
                    correlacao_dados,
                    frase_ciclo,
                    criado_em,
                ),
            )
            conn.commit()
        finally:
            conn.close()

    def listar_reflexoes_recentes(self, dias: int = 7) -> list[dict[str, Any]]:
        """Lista reflexoes recentes ordenadas por timestamp decrescente.

        Args:
            dias: Janela de dias para filtrar reflexoes.

        Returns:
            Lista de dicionarios com os campos de cada reflexao.
        """
        desde = (
            datetime.now(tz=timezone.utc) - timedelta(days=dias)
        ).isoformat()
        conn = self._conectar()
        conn.row_factory = sqlite3.Row
        try:
            cursor = conn.execute(
                """
                SELECT * FROM ai_reflection_logs
                WHERE timestamp >= ?
                ORDER BY timestamp DESC
                """,
                (desde,),
            )
            return [dict(row) for row in cursor.fetchall()]
        finally:
            conn.close()

    # ------------------------------------------------------------------
    # Perguntas
    # ------------------------------------------------------------------

    def registrar_pergunta(
        self,
        question_id: str,
        prompt: str,
        category: str,
        level: str = "basico",
    ) -> None:
        """Registra uma nova pergunta de reflexao no banco.

        Operacao idempotente: nao duplica se question_id ja existe.

        Args:
            question_id: Identificador unico da pergunta.
            prompt: Texto da pergunta.
            category: Categoria tematica (ex: "decisao", "risco").
            level: Nivel de profundidade ("basico", "intermediario", "avancado").
        """
        agora = _agora_iso()
        conn = self._conectar()
        try:
            conn.execute(
                """
                INSERT OR IGNORE INTO reflection_questions (
                    question_id, prompt, category, level, data_criacao
                ) VALUES (?, ?, ?, ?, ?)
                """,
                (question_id, prompt, category, level, agora),
            )
            conn.commit()
        finally:
            conn.close()

    def registrar_outcome_pergunta(
        self,
        question_id: str,
        outcome: str,
    ) -> None:
        """Registra o resultado de uma operacao associada a uma pergunta.

        Incrementa os contadores e recalcula o score de relevancia.

        Args:
            question_id: Identificador da pergunta.
            outcome: Resultado da operacao ("WIN", "LOSS" ou "BREAKEVEN").
        """
        agora = _agora_iso()
        conn = self._conectar()
        try:
            conn.execute(
                """
                UPDATE reflection_questions
                SET total_respostas = total_respostas + 1,
                    respostas_win   = respostas_win + CASE WHEN ? = 'WIN' THEN 1 ELSE 0 END,
                    respostas_loss  = respostas_loss + CASE WHEN ? = 'LOSS' THEN 1 ELSE 0 END,
                    score_relevancia = CASE
                        WHEN (total_respostas + 1) > 0
                        THEN CAST(respostas_win + CASE WHEN ? = 'WIN' THEN 1 ELSE 0 END AS REAL)
                             / (total_respostas + 1)
                        ELSE 0.0
                    END,
                    data_ultima_avaliacao = ?
                WHERE question_id = ?
                """,
                (outcome, outcome, outcome, agora, question_id),
            )
            conn.commit()
        finally:
            conn.close()

    def avaliar_obsolescencia(
        self,
        threshold_score: float = 0.3,
        min_respostas: int = 5,
    ) -> list[str]:
        """Avalia e marca perguntas obsoletas.

        Criterios de obsolescencia:
        - score_relevancia < threshold E total_respostas >= min_respostas
        - data_criacao > 30 dias E total_respostas == 0

        Args:
            threshold_score: Score minimo para manter a pergunta ativa.
            min_respostas: Numero minimo de respostas para avaliar score.

        Returns:
            Lista de question_ids marcados como obsoletos nesta chamada.
        """
        agora = datetime.now(tz=timezone.utc)
        limite_inatividade = (agora - timedelta(days=30)).isoformat()
        agora_iso = agora.isoformat()

        conn = self._conectar()
        try:
            # Buscar candidatos a obsolescencia por score baixo
            cursor = conn.execute(
                """
                SELECT question_id FROM reflection_questions
                WHERE obsoleta = 0
                  AND ativa = 1
                  AND (
                      (score_relevancia < ? AND total_respostas >= ?)
                      OR
                      (data_criacao <= ? AND total_respostas = 0)
                  )
                """,
                (threshold_score, min_respostas, limite_inatividade),
            )
            candidatos = [row[0] for row in cursor.fetchall()]

            if candidatos:
                placeholders = ",".join("?" for _ in candidatos)
                conn.execute(
                    f"""
                    UPDATE reflection_questions
                    SET obsoleta = 1,
                        data_obsoleta = ?,
                        ativa = 0
                    WHERE question_id IN ({placeholders})
                    """,
                    [agora_iso] + candidatos,
                )
                conn.commit()

            return candidatos
        finally:
            conn.close()

    def listar_perguntas_ativas(self) -> list[dict[str, Any]]:
        """Lista perguntas ativas e nao obsoletas.

        Returns:
            Lista de dicionarios com os campos de cada pergunta.
        """
        conn = self._conectar()
        conn.row_factory = sqlite3.Row
        try:
            cursor = conn.execute(
                """
                SELECT * FROM reflection_questions
                WHERE ativa = 1 AND obsoleta = 0
                ORDER BY score_relevancia DESC
                """
            )
            return [dict(row) for row in cursor.fetchall()]
        finally:
            conn.close()

    # ------------------------------------------------------------------
    # Deteccao de padroes
    # ------------------------------------------------------------------

    def detectar_padroes_recorrentes(self, janela_dias: int = 5) -> list[str]:
        """Detecta padroes recorrentes nas reflexoes recentes.

        Padroes verificados:
        - Padrão 1: mood = "Frustrado" em 3+ reflexoes na janela.
        - Padrão 2: my_decision = "HOLD" em TODAS as reflexoes da janela.
        - Padrão 3: data_relevance = "BAIXA" em 4+ reflexoes na janela.

        Args:
            janela_dias: Numero de dias a considerar para analise.

        Returns:
            Lista de strings descrevendo os padroes detectados.
        """
        desde = (
            datetime.now(tz=timezone.utc) - timedelta(days=janela_dias)
        ).isoformat()

        conn = self._conectar()
        try:
            cursor = conn.execute(
                """
                SELECT mood, my_decision, data_relevance
                FROM ai_reflection_logs
                WHERE timestamp >= ?
                ORDER BY timestamp ASC
                """,
                (desde,),
            )
            reflexoes = cursor.fetchall()
        finally:
            conn.close()

        if not reflexoes:
            return []

        padroes: list[str] = []
        total = len(reflexoes)

        # Padrao 1: mood = "Frustrado" em 3+ reflexoes
        frustradas = sum(1 for r in reflexoes if r[0] == "Frustrado")
        if frustradas >= 3:
            padroes.append(
                f"PADRAO_MOOD_FRUSTRADO: {frustradas} reflexoes com mood=Frustrado "
                f"nos ultimos {janela_dias} dias"
            )

        # Padrao 2: my_decision = "HOLD" em todas as reflexoes (sem operacao)
        todas_hold = all(r[1] == "HOLD" for r in reflexoes)
        if todas_hold and total > 0:
            padroes.append(
                f"PADRAO_HOLD_TOTAL: todas as {total} reflexoes com decisao=HOLD "
                f"nos ultimos {janela_dias} dias (sem operacao)"
            )

        # Padrao 3: data_relevance = "BAIXA" em 4+ reflexoes
        baixa_relevancia = sum(1 for r in reflexoes if r[2] == "BAIXA")
        if baixa_relevancia >= 4:
            padroes.append(
                f"PADRAO_DADOS_IRRELEVANTES: {baixa_relevancia} reflexoes com "
                f"data_relevance=BAIXA nos ultimos {janela_dias} dias"
            )

        return padroes
