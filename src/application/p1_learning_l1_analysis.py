"""
P1-LEARNING: Etapa 5 - L1 Decision Correctness Analysis

Avalia se cada decisao de entrada foi consistente com o regime de
mercado que se seguiu. Produz um score de "corretude" (0.0-1.0) por
episodio fechado e persiste os resultados em JSONL para auditoria.

Responsabilidades:
- Ler episodios fechados da sessao atual (ClosureRecord)
- Calcular score de corretude por heuristica de contexto de mercado
- Persistir resultados em data/models/l1_analysis_YYYYMMDD.jsonl
- Identificar candidatos a regras de aprendizado (corretude < 0.5)

Logica de corretude (heuristica v1):
  WIN por TP + condicoes favoraveis  → 1.0
  WIN por TP + condicoes adversas    → 0.6
  LOSS por SL + volatilidade alta    → 0.7
  LOSS por SL + volatilidade baixa   → 0.2
  LOSS por TIMEOUT                   → 0.4
  BREAKEVEN                          → 0.5
  outros                             → 0.5

Pipeline:
    Etapa 4 (Closure) -> p1_learning_closure.py
    Etapa 5 (L1 Analysis) -> p1_learning_l1_analysis.py  [este modulo]
    Etapa 6 (L2 Causal) -> p1_learning_l2_causal.py
    Etapa 7 (Learning Rules) -> p1_learning_regras.py

Status: Implementacao v1.0 (02/04/2026)
Referencia: docs/BACKLOG.md (P1-LEARNING Etapas 5-7)
"""

from __future__ import annotations

import json
import sqlite3
from dataclasses import asdict, dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Optional

from src.application.p1_learning_closure import (
    ClosureRecord,
    EpisodeClosureEngine,
    MotivoFechamento,
    OutcomeType,
)


# ============================================================================
# DATACLASSES
# ============================================================================


@dataclass
class ResultadoL1:
    """Resultado da analise L1 de corretude de decisao para um episodio.

    Atributos:
        closure_id: ID do fechamento analisado
        episode_id: ID do episodio causal vinculado
        outcome: Resultado do trade (WIN/LOSS/BREAKEVEN)
        motivo_fechamento: Causa do encerramento
        corretude_decisao: Score 0.0-1.0 (>= 0.5 = defensavel)
        contexto_mercado: Condicoes de mercado no fechamento
        diagnostico: Descricao textual da avaliacao
        sessao_id: ID da sessao de trading
        timestamp_analise: Momento da analise
    """

    closure_id: str
    episode_id: str
    outcome: str
    motivo_fechamento: str
    corretude_decisao: float
    contexto_mercado: dict[str, Any]
    diagnostico: str
    sessao_id: str
    timestamp_analise: datetime

    def para_dict(self) -> dict[str, Any]:
        """Converte para dicionario JSON-serializable."""
        d = asdict(self)
        d["timestamp_analise"] = self.timestamp_analise.isoformat()
        return d


# ============================================================================
# ANALISADOR PRINCIPAL
# ============================================================================


class AnalisadorDecisaoL1:
    """Analisa corretude das decisoes de entrada nos episodios da sessao.

    Responsabilidades:
    - Carregar ClosureRecords da sessao atual via SQLite
    - Calcular score de corretude por heuristica de contexto
    - Persistir ResultadoL1 em arquivo JSONL por sessao

    Exemplo:
        analisador = AnalisadorDecisaoL1(
            db_path=Path("data/db/causal_learning.db"),
            sessao_id="SESSAO_20260402_093000",
        )
        resultados = analisador.analisar_sessao()
        caminho = analisador.persistir_analise(resultados)
    """

    def __init__(self, db_path: Path, sessao_id: str) -> None:
        """Inicializa o analisador.

        Args:
            db_path: Caminho para o banco SQLite com episode_closures
            sessao_id: ID da sessao de trading a analisar
        """
        self._db_path = db_path
        self._sessao_id = sessao_id
        self._registros: list[ClosureRecord] = []

    # -----------------------------------------------------------------------
    # CARREGAMENTO
    # -----------------------------------------------------------------------

    def obter_episodios_sessao(self) -> list[ClosureRecord]:
        """Carrega episodios fechados do banco SQLite.

        Returns:
            Lista de ClosureRecord ordenados por timestamp de fechamento.
            Retorna lista vazia se banco nao existir ou nao tiver dados.
        """
        if not self._db_path.exists():
            return []

        engine = EpisodeClosureEngine(db_path=str(self._db_path))
        registros = engine.listar_fechamentos(limite=500)
        self._registros = registros
        return registros

    # -----------------------------------------------------------------------
    # AVALIACAO DE CORRETUDE
    # -----------------------------------------------------------------------

    def avaliar_corretude_decisao(self, rec: ClosureRecord) -> ResultadoL1:
        """Calcula score de corretude para um ClosureRecord.

        Heuristica v1 baseada em outcome + motivo + volatilidade:
          - WIN por TP + favoravel  → 1.0
          - WIN por TP + adverso    → 0.6
          - WIN outros              → 0.7
          - LOSS por SL + alta vol  → 0.7 (aceitavel)
          - LOSS por SL + baixa vol → 0.2 (erro de direcao)
          - LOSS por TIMEOUT        → 0.4
          - LOSS outros             → 0.3
          - BREAKEVEN               → 0.5

        Args:
            rec: ClosureRecord do episodio a avaliar

        Returns:
            ResultadoL1 com score e diagnostico
        """
        score, diagnostico = self._calcular_score(rec)

        return ResultadoL1(
            closure_id=rec.closure_id,
            episode_id=rec.episode_id,
            outcome=rec.outcome.value,
            motivo_fechamento=rec.motivo_fechamento.value,
            corretude_decisao=score,
            contexto_mercado=dict(rec.market_conditions),
            diagnostico=diagnostico,
            sessao_id=self._sessao_id,
            timestamp_analise=datetime.now(),
        )

    def _calcular_score(self, rec: ClosureRecord) -> tuple[float, str]:
        """Calcula score e diagnostico com base nas regras heuristicas.

        Args:
            rec: Registro de fechamento

        Returns:
            Tupla (score: float, diagnostico: str)
        """
        outcome = rec.outcome
        motivo = rec.motivo_fechamento
        volatilidade = str(
            rec.market_conditions.get("volatilidade", "")
        ).lower()
        tendencia = str(
            rec.market_conditions.get("tendencia", "")
        ).upper()

        # WIN
        if outcome == OutcomeType.WIN:
            if motivo == MotivoFechamento.TP_ATINGIDO:
                condicoes_favoraveis = (
                    volatilidade in ("baixa", "normal")
                    or tendencia in ("UP", "DOWN")
                )
                if condicoes_favoraveis:
                    return (
                        1.0,
                        "WIN por TP com condicoes favoraveis — decisao correta",
                    )
                return (
                    0.6,
                    "WIN por TP mas condicoes adversas — sorte pode ter contribuido",
                )
            return (
                0.7,
                f"WIN por {motivo.value} — decisao defensavel",
            )

        # LOSS
        if outcome == OutcomeType.LOSS:
            if motivo == MotivoFechamento.SL_ATINGIDO:
                if volatilidade == "alta":
                    return (
                        0.7,
                        "LOSS por SL com volatilidade alta — aceitavel dado o contexto",
                    )
                return (
                    0.2,
                    "LOSS por SL com volatilidade baixa — possivel erro de direcao",
                )
            if motivo == MotivoFechamento.TIMEOUT:
                return (
                    0.4,
                    "LOSS por TIMEOUT — posicao mantida alem do tempo ideal",
                )
            return (
                0.3,
                f"LOSS por {motivo.value} — decisao questionavel",
            )

        # BREAKEVEN
        return (
            0.5,
            "BREAKEVEN — decisao neutra, sem ganho nem perda significativa",
        )

    # -----------------------------------------------------------------------
    # ANALISE DE SESSAO
    # -----------------------------------------------------------------------

    def analisar_sessao(self) -> list[ResultadoL1]:
        """Analisa todos os episodios carregados e retorna ResultadoL1 por episodio.

        Se _registros estiver vazio, tenta carregar do banco primeiro.

        Returns:
            Lista de ResultadoL1 (pode ser vazia se nao ha episodios)
        """
        if not self._registros:
            self.obter_episodios_sessao()

        return [self.avaliar_corretude_decisao(rec) for rec in self._registros]

    # -----------------------------------------------------------------------
    # PERSISTENCIA
    # -----------------------------------------------------------------------

    def persistir_analise(
        self,
        resultados: list[ResultadoL1],
        output_dir: Optional[Path] = None,
    ) -> Path:
        """Persiste resultados L1 em arquivo JSONL.

        Cada linha do arquivo contem um JSON de ResultadoL1.
        Nome do arquivo: l1_analysis_YYYYMMDD_<sessao_id>.jsonl

        Args:
            resultados: Lista de ResultadoL1 a persistir
            output_dir: Diretorio de saida (default: data/models/)

        Returns:
            Path do arquivo criado
        """
        if output_dir is None:
            output_dir = Path("data/models")

        output_dir.mkdir(parents=True, exist_ok=True)

        data_str = datetime.now().strftime("%Y%m%d")
        sessao_slug = self._sessao_id.replace(" ", "_")[:20]
        nome = f"l1_analysis_{data_str}_{sessao_slug}.jsonl"
        caminho = output_dir / nome

        linhas = [json.dumps(r.para_dict(), ensure_ascii=False) for r in resultados]
        caminho.write_text("\n".join(linhas), encoding="utf-8")

        return caminho
