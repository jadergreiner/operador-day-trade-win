"""
P1-LEARNING: Etapa 6 - L2 Causal Drift Detection

Determina se erros de uma sessao tem causa causal (mudanca de regime
de mercado) ou sao erro de decisao do proprio modelo.

Responsabilidades:
- Adaptar ClosureRecord para formato compativel com DriftDetector
- Detectar drift estatistico entre baseline e sessao atual
- Classificar causa dominante: DRIFT_REGIME | ERRO_DECISAO |
  AMOSTRA_INSUFICIENTE | OK

Fluxo:
    ClosureRecord (Etapa 4)
    → adaptar_registros()   — mapeia outcome/pnl para _TradeDriftAdapter
    → detectar()            — chama DriftDetector.detectar_drift()
    → ResultadoL2           — classifica causa + serializa alertas

Pipeline:
    Etapa 5 (L1 Analysis)  -> p1_learning_l1_analysis.py
    Etapa 6 (L2 Causal)    -> p1_learning_l2_causal.py  [este modulo]
    Etapa 7 (Learning Rules) -> p1_learning_regras.py

Status: Implementacao v1.0 (02/04/2026)
Referencia: docs/BACKLOG.md (P1-LEARNING Etapas 5-7)
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any

from src.application.ac6_7_drift_detector import DriftDetector
from src.application.p1_learning_closure import ClosureRecord


# ============================================================================
# ADAPTADOR INTERNO
# ============================================================================


class _TradeDriftAdapter:
    """Adapta ClosureRecord para o formato esperado pelo DriftDetector.

    DriftDetector espera objetos com atributos .outcome (str) e .pnl (float).
    ClosureRecord usa OutcomeType enum e pnl_realizado float.
    """

    def __init__(self, rec: ClosureRecord) -> None:
        self.outcome: str = rec.outcome.value          # "WIN" | "LOSS" | "BREAKEVEN"
        self.pnl: float = rec.pnl_realizado


# ============================================================================
# DATACLASSES
# ============================================================================


@dataclass
class ResultadoL2:
    """Resultado da analise L2 causal de uma sessao de trading.

    Atributos:
        sessao_id: ID da sessao analisada
        timestamp_analise: Momento da analise
        n_episodios: Total de episodios analisados
        win_rate_sessao: Taxa de acerto da sessao (0.0-1.0)
        sharpe_sessao: Sharpe ratio da sessao
        drift_detectado: True se drift estatistico significativo
        alertas_drift: Lista de alertas em formato dict (JSON-safe)
        causa_dominante: DRIFT_REGIME | ERRO_DECISAO |
                         AMOSTRA_INSUFICIENTE | OK
        confianca: Score de confianca da classificacao (0.0-1.0)
    """

    sessao_id: str
    timestamp_analise: datetime
    n_episodios: int
    win_rate_sessao: float
    sharpe_sessao: float
    drift_detectado: bool
    alertas_drift: list[dict[str, Any]]
    causa_dominante: str
    confianca: float


# ============================================================================
# DETECTOR CAUSAL
# ============================================================================


class DetectorCausalL2:
    """Detecta causa dominante dos erros de uma sessao de trading.

    Usa DriftDetector (Z-score) para distinguir entre:
    - Mudanca de regime de mercado (DRIFT_REGIME)
    - Erros sistematicos do modelo (ERRO_DECISAO)
    - Amostra insuficiente para conclusao (AMOSTRA_INSUFICIENTE)
    - Performance dentro do esperado (OK)

    Atributos:
        _detector: Instancia de DriftDetector com baseline configurado
        _min_episodios: Minimo de episodios para analise valida
        _sessao_id: ID da sessao

    Exemplo:
        from src.application.ac6_7_drift_detector import DriftDetector

        det = DriftDetector(baseline_win_rate=0.59, baseline_sharpe=1.0)
        l2 = DetectorCausalL2(detector=det, sessao_id="SESSAO_20260402")
        resultado = l2.detectar(registros)
    """

    def __init__(
        self,
        detector: DriftDetector,
        min_episodios: int = 5,
        sessao_id: str = "",
    ) -> None:
        """Inicializa o detector causal.

        Args:
            detector: DriftDetector com baseline configurado
            min_episodios: Minimo de episodios para analise confiavel
            sessao_id: ID da sessao (usado no ResultadoL2)
        """
        self._detector = detector
        self._min_episodios = min_episodios
        self._sessao_id = sessao_id

    # -----------------------------------------------------------------------
    # ADAPTACAO
    # -----------------------------------------------------------------------

    def adaptar_registros(
        self, registros: list[ClosureRecord]
    ) -> list[_TradeDriftAdapter]:
        """Converte ClosureRecord para formato compativel com DriftDetector.

        Args:
            registros: Lista de ClosureRecord da Etapa 4

        Returns:
            Lista de _TradeDriftAdapter com .outcome e .pnl
        """
        return [_TradeDriftAdapter(rec) for rec in registros]

    # -----------------------------------------------------------------------
    # DETECCAO
    # -----------------------------------------------------------------------

    def detectar(self, registros: list[ClosureRecord]) -> ResultadoL2:
        """Detecta causa dominante dos erros da sessao.

        Fluxo:
        1. Verifica amostra minima
        2. Adapta registros para DriftDetector
        3. Calcula metricas da sessao
        4. Detecta drift via Z-score
        5. Classifica causa dominante

        Args:
            registros: Lista de ClosureRecord a analisar

        Returns:
            ResultadoL2 com classificacao e metricas
        """
        n = len(registros)

        if n < self._min_episodios:
            return ResultadoL2(
                sessao_id=self._sessao_id,
                timestamp_analise=datetime.now(),
                n_episodios=n,
                win_rate_sessao=self._calcular_win_rate(registros),
                sharpe_sessao=0.0,
                drift_detectado=False,
                alertas_drift=[],
                causa_dominante="AMOSTRA_INSUFICIENTE",
                confianca=0.0,
            )

        adaptados = self.adaptar_registros(registros)
        metricas = self._detector.calcular_metricas(adaptados)
        alertas_obj = self._detector.detectar_drift(adaptados)

        # Serializar alertas para JSON-safe
        alertas_dict: list[dict[str, Any]] = [
            a.para_dict() for a in alertas_obj
        ]
        drift_detectado = len(alertas_obj) > 0

        causa, confianca = self._classificar_causa(
            drift_detectado=drift_detectado,
            n_alertas=len(alertas_obj),
            win_rate=metricas.win_rate,
        )

        return ResultadoL2(
            sessao_id=self._sessao_id,
            timestamp_analise=datetime.now(),
            n_episodios=n,
            win_rate_sessao=round(metricas.win_rate, 4),
            sharpe_sessao=round(metricas.sharpe_ratio, 4),
            drift_detectado=drift_detectado,
            alertas_drift=alertas_dict,
            causa_dominante=causa,
            confianca=confianca,
        )

    # -----------------------------------------------------------------------
    # AUXILIARES
    # -----------------------------------------------------------------------

    def _calcular_win_rate(self, registros: list[ClosureRecord]) -> float:
        """Calcula win rate sem depender do DriftDetector.

        Args:
            registros: Lista de ClosureRecord

        Returns:
            Fracao de wins (0.0-1.0)
        """
        if not registros:
            return 0.0
        wins = sum(1 for r in registros if r.outcome.value == "WIN")
        return wins / len(registros)

    def _classificar_causa(
        self,
        drift_detectado: bool,
        n_alertas: int,
        win_rate: float,
    ) -> tuple[str, float]:
        """Classifica causa dominante e retorna (causa, confianca).

        Regras:
        - drift_detectado + win_rate baixo  → DRIFT_REGIME (confianca alta)
        - sem drift + win_rate baixo        → ERRO_DECISAO (confianca media)
        - performance normal                → OK

        Args:
            drift_detectado: True se DriftDetector gerou alertas
            n_alertas: Quantidade de alertas de drift
            win_rate: Win rate da sessao atual

        Returns:
            Tupla (causa: str, confianca: float)
        """
        baseline_wr = self._detector.baseline_win_rate

        if drift_detectado:
            # Quanto mais alertas, mais confiante sobre drift de regime
            confianca = min(0.5 + n_alertas * 0.15, 0.95)
            return "DRIFT_REGIME", round(confianca, 2)

        if baseline_wr > 0 and win_rate < baseline_wr * 0.75:
            # Win rate muito abaixo do baseline sem drift → erro do modelo
            degradacao = (baseline_wr - win_rate) / baseline_wr
            confianca = min(0.4 + degradacao * 0.5, 0.90)
            return "ERRO_DECISAO", round(confianca, 2)

        return "OK", 0.8
