"""
RL Diary Learning Service — Motor de Aprendizado Ativo do Diario RL.

Evolui o RL Performance Diary de diario de medicao para motor de
aprendizado ativo. Cada ciclo de 15 min registra performance e aciona
decisoes de retreinamento quando o agente degrada.

BLID-024 / ROADMAP-DIARIOS-04
Executor: INICIAR_DIARIOS.bat
"""

from __future__ import annotations

import json
import logging
import sqlite3
from datetime import date, datetime
from pathlib import Path
from typing import Any, Optional

from src.application.services.diary_feedback import (
    DiaryFeedback,
    save_diary_feedback,
)

logger = logging.getLogger("rl_diary_learning_service")


class RLDiaryLearningService:
    """Servico de aprendizado ativo baseado no Diario RL.

    Transforma o RL Performance Diary de simples diario de medicao para
    motor de aprendizado ativo — avaliando degradacao, exportando episodios
    enriquecidos e gerando relatorios de fechamento diario.
    """

    @staticmethod
    def _connect(db_path: str) -> sqlite3.Connection:
        """Abre conexao SQLite com PRAGMAs otimizados para WAL."""
        conn = sqlite3.connect(str(db_path), timeout=30)
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("PRAGMA synchronous=NORMAL")
        conn.execute("PRAGMA busy_timeout=30000")
        return conn

    def avaliar_gatilho_retreinamento(
        self,
        db_path: str,
        n_ciclos: int = 3,
        threshold_nota: int = 6,
    ) -> bool:
        """Avalia se deve acionar gatilho de retreinamento do agente RL.

        Consulta os ultimos N registros de diary_feedback com source='rl_diary'
        e verifica se todos tiveram nota_agente abaixo do threshold. Quando o
        gatilho e ativado, persiste um novo feedback com retreinamento_necessario=True.

        Args:
            db_path: Caminho do banco SQLite.
            n_ciclos: Numero de ciclos consecutivos de nota baixa para acionar.
            threshold_nota: Nota minima aceitavel (exclusive — abaixo aciona).

        Returns:
            True se gatilho ativado, False caso contrario.
        """
        try:
            conn = self._connect(db_path)
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute(
                """
                SELECT nota_agente FROM diary_feedback
                WHERE source = 'rl_diary'
                ORDER BY id DESC
                LIMIT ?
                """,
                (n_ciclos,),
            )
            rows = cursor.fetchall()
            conn.close()
        except Exception as exc:
            logger.warning("avaliar_gatilho_retreinamento: %s", exc)
            return False

        if len(rows) < n_ciclos:
            return False

        todas_baixas = all(int(r["nota_agente"]) < threshold_nota for r in rows)
        if not todas_baixas:
            return False

        # Persistir sinal de retreinamento
        feedback_gatilho = DiaryFeedback(
            date=date.today().isoformat(),
            timestamp=datetime.now().isoformat(),
            source="rl_diary",
            nota_agente=rows[0]["nota_agente"],
            retreinamento_necessario=True,
        )
        save_diary_feedback(db_path, feedback_gatilho)
        return True

    def exportar_episodios_enriquecidos(
        self,
        db_path: str,
        data_alvo: Optional[str] = None,
        diretorio_saida: Optional[Path] = None,
    ) -> Path:
        """Exporta episodios do diario como JSON enriquecido para treinamento.

        Consulta a tabela diario_episodios para a data alvo e exporta em
        formato JSON padronizado em data/training/.

        Args:
            db_path: Caminho do banco SQLite.
            data_alvo: Data no formato YYYY-MM-DD (padrao: hoje).
            diretorio_saida: Diretorio de saida (padrao: data/training/).

        Returns:
            Path do arquivo JSON criado.
        """
        if data_alvo is None:
            data_alvo = date.today().isoformat()

        if diretorio_saida is None:
            diretorio_saida = Path("data/training")

        diretorio_saida.mkdir(parents=True, exist_ok=True)

        data_fmt = data_alvo.replace("-", "")
        arquivo_saida = diretorio_saida / f"diario_episodios_{data_fmt}.json"

        episodios: list[dict[str, Any]] = []
        try:
            conn = self._connect(db_path)
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute(
                "SELECT * FROM diario_episodios WHERE data = ? ORDER BY id ASC",
                (data_alvo,),
            )
            rows = cursor.fetchall()
            conn.close()
            episodios = [dict(r) for r in rows]
        except Exception as exc:
            logger.warning("exportar_episodios_enriquecidos: %s", exc)
            episodios = []

        payload: dict[str, Any] = {
            "schema_version": "1.0",
            "data": data_alvo,
            "total_episodios": len(episodios),
            "episodios": episodios,
        }

        arquivo_saida.write_text(
            json.dumps(payload, ensure_ascii=False, indent=2, default=str),
            encoding="utf-8",
        )
        return arquivo_saida

    def calcular_win_rate_adaptativo(
        self,
        episodios: list[dict[str, Any]],
        fator_decaimento: float = 0.85,
    ) -> float:
        """Calcula win rate com janela adaptativa (pesos decrescentes).

        Episodios mais recentes (indice 0) recebem maior peso. O peso de cada
        episodio i e fator_decaimento^i. O win rate adaptativo pondera acertos
        e erros por esse esquema de decaimento exponencial.

        Args:
            episodios: Lista de dicts de episodios (mais recentes primeiro).
            fator_decaimento: Fator de decaimento exponencial (0 < fd < 1).

        Returns:
            Win rate ponderado entre 0.0 e 100.0.
        """
        if not episodios:
            return 0.0

        soma_pesos = 0.0
        soma_acertos = 0.0
        for i, ep in enumerate(episodios):
            peso = fator_decaimento ** i
            foi_acerto = int(ep.get("foi_acerto", 0))
            soma_pesos += peso
            soma_acertos += foi_acerto * peso

        if soma_pesos == 0.0:
            return 0.0

        return (soma_acertos / soma_pesos) * 100.0

    def gerar_relatorio_fechamento(
        self,
        db_path: str,
        data_alvo: Optional[str] = None,
        diretorio_saida: Optional[Path] = None,
    ) -> Path:
        """Gera relatorio de fechamento diario em Markdown.

        Consolida metricas do dia: range capturado, eficiencia, episodios e
        retreinamentos acionados. Persiste em outputs/.

        Args:
            db_path: Caminho do banco SQLite.
            data_alvo: Data no formato YYYY-MM-DD (padrao: hoje).
            diretorio_saida: Diretorio de saida (padrao: outputs/).

        Returns:
            Path do arquivo .md criado.
        """
        if data_alvo is None:
            data_alvo = date.today().isoformat()

        if diretorio_saida is None:
            diretorio_saida = Path("outputs")

        diretorio_saida.mkdir(parents=True, exist_ok=True)

        data_fmt = data_alvo.replace("-", "")
        arquivo_saida = diretorio_saida / f"rl_diary_fechamento_{data_fmt}.md"

        # Buscar ultimo feedback do dia para metricas
        market_range_pts: float = 0.0
        eficiencia_pct: float = 0.0
        n_episodes: int = 0
        retreinamentos: int = 0

        try:
            conn = self._connect(db_path)
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()

            # Ultimo feedback do dia
            cursor.execute(
                """
                SELECT market_range_pts, eficiencia_pct, n_episodes
                FROM diary_feedback
                WHERE date = ?
                ORDER BY id DESC
                LIMIT 1
                """,
                (data_alvo,),
            )
            row = cursor.fetchone()
            if row:
                market_range_pts = float(row["market_range_pts"] or 0.0)
                eficiencia_pct = float(row["eficiencia_pct"] or 0.0)
                n_episodes = int(row["n_episodes"] or 0)

            # Contar retreinamentos acionados no dia
            cursor.execute(
                """
                SELECT COUNT(*) AS total FROM diary_feedback
                WHERE date = ? AND retreinamento_necessario = 1
                """,
                (data_alvo,),
            )
            row_ret = cursor.fetchone()
            if row_ret:
                retreinamentos = int(row_ret["total"] or 0)

            conn.close()
        except Exception as exc:
            logger.warning("gerar_relatorio_fechamento: %s", exc)

        conteudo = (
            f"# Relatorio de Fechamento RL Diary — {data_alvo}\n\n"
            f"## Metricas do Dia\n\n"
            f"- **Range Capturado**: {market_range_pts:.1f} pts\n"
            f"- **Eficiencia Real**: {eficiencia_pct:.1f}%\n"
            f"- **Episodios**: {n_episodes}\n"
            f"- **Retreinamentos Acionados**: {retreinamentos}\n"
        )

        arquivo_saida.write_text(conteudo, encoding="utf-8")
        return arquivo_saida
