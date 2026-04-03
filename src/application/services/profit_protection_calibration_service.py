"""
Serviço de calibração comparativa do ProfitProtectionEngine.

Responsabilidades:
- Receber um conjunto de trades fechados (replay ou live).
- Executar o motor com perfil baseline e perfis candidatos.
- Calcular métricas comparativas (win rate, drawdown, Sharpe, profit factor).
- Retornar relatório estruturado com recomendação.

Uso típico:
    from src.application.services.profit_protection_calibration_service import (
        calibrar_perfis,
        RelatorioCalibracaoPP,
    )

ADR: ADR-018
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

from src.application.profit_protection_engine import ProfitProtectionEngine
from src.infrastructure.config.profit_protection_config import (
    ProfitProtectionConfig,
    ProfitProtectionProfile,
)

# Limite mínimo de evidência para calibração (ADR-018)
MIN_PREGOES = 5
MIN_TRADES = 30

# Degradação máxima tolerada de win rate vs baseline (em p.p.)
MAX_DEGRADACAO_WIN_RATE_PP = 2.0


# ============================================================
# DATACLASSES
# ============================================================


@dataclass
class MetricasPerfil:
    """Métricas de desempenho calculadas para um perfil."""

    nome: str
    n_trades: int
    win_rate: float  # [0..1]
    profit_factor: float
    max_drawdown_pct: float
    sharpe: float
    taxa_reversao_protegida: float  # reversões que viraram ALERTA
    taxa_break_even_acionado: float  # ATIVAR_BREAK_EVEN_STOP / n_trades


@dataclass
class RelatorioCalibracaoPP:
    """Relatório completo de calibração comparativa."""

    baseline: MetricasPerfil
    candidatos: List[MetricasPerfil]
    perfil_recomendado: str
    versao_config: str
    min_pregoes_evidencia: int = MIN_PREGOES
    min_trades_evidencia: int = MIN_TRADES
    evidencia_suficiente: bool = False
    motivo_recomendacao: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "baseline": self._metrica_dict(self.baseline),
            "candidatos": [self._metrica_dict(c) for c in self.candidatos],
            "perfil_recomendado": self.perfil_recomendado,
            "versao_config": self.versao_config,
            "min_pregoes_evidencia": self.min_pregoes_evidencia,
            "min_trades_evidencia": self.min_trades_evidencia,
            "evidencia_suficiente": self.evidencia_suficiente,
            "motivo_recomendacao": self.motivo_recomendacao,
        }

    def to_markdown(self) -> str:
        linhas = [
            "# Relatório de Calibração — Profit Protection Engine",
            "",
            f"**Versão config:** {self.versao_config}",
            f"**Evidência suficiente:** {'SIM' if self.evidencia_suficiente else 'NÃO'}",
            f"**Trades analisados:** {self.baseline.n_trades}",
            "",
            "## Resultado da Calibração",
            "",
            f"**Perfil recomendado:** `{self.perfil_recomendado}`",
            f"**Motivo:** {self.motivo_recomendacao}",
            "",
            "## Métricas Comparativas",
            "",
            "| Perfil | Win Rate | Profit Factor | Max Drawdown | Sharpe |"
            " BE Acionado | Reversão Protegida |",
            "|---|---|---|---|---|---|---|",
        ]
        for m in [self.baseline] + self.candidatos:
            linhas.append(
                f"| {m.nome} | {m.win_rate:.1%} | {m.profit_factor:.2f} |"
                f" {m.max_drawdown_pct:.2f}% | {m.sharpe:.3f} |"
                f" {m.taxa_break_even_acionado:.1%} |"
                f" {m.taxa_reversao_protegida:.1%} |"
            )
        return "\n".join(linhas)

    @staticmethod
    def _metrica_dict(m: MetricasPerfil) -> Dict[str, Any]:
        return {
            "nome": m.nome,
            "n_trades": m.n_trades,
            "win_rate": round(m.win_rate, 4),
            "profit_factor": round(m.profit_factor, 4),
            "max_drawdown_pct": round(m.max_drawdown_pct, 4),
            "sharpe": round(m.sharpe, 4),
            "taxa_reversao_protegida": round(m.taxa_reversao_protegida, 4),
            "taxa_break_even_acionado": round(m.taxa_break_even_acionado, 4),
        }


# ============================================================
# FUNÇÕES DE CÁLCULO
# ============================================================


def _calcular_metricas(
    nome: str,
    resultados_pct: List[float],
    acoes: List[str],
) -> MetricasPerfil:
    """Calcula métricas a partir de lista de retornos e ações sugeridas.

    Args:
        nome: Nome do perfil.
        resultados_pct: Lista de retornos percentuais por trade (positivo = ganho).
        acoes: Lista de ações sugeridas pelo motor para cada tick analisado.

    Returns:
        MetricasPerfil com métricas calculadas.
    """
    n = len(resultados_pct)
    if n == 0:
        return MetricasPerfil(
            nome=nome,
            n_trades=0,
            win_rate=0.0,
            profit_factor=0.0,
            max_drawdown_pct=0.0,
            sharpe=0.0,
            taxa_reversao_protegida=0.0,
            taxa_break_even_acionado=0.0,
        )

    wins = [r for r in resultados_pct if r > 0]
    losses = [r for r in resultados_pct if r <= 0]
    win_rate = len(wins) / n

    gross_profit = sum(wins) if wins else 0.0
    gross_loss = abs(sum(losses)) if losses else 0.0
    profit_factor = gross_profit / gross_loss if gross_loss > 0 else float("inf")

    # Drawdown máximo (equity curve)
    equity = 0.0
    pico = 0.0
    max_dd = 0.0
    for r in resultados_pct:
        equity += r
        if equity > pico:
            pico = equity
        dd = pico - equity
        if dd > max_dd:
            max_dd = dd
    max_drawdown_pct = max_dd

    # Sharpe simplificado (retorno médio / desvio padrão)
    media = sum(resultados_pct) / n
    variancia = sum((r - media) ** 2 for r in resultados_pct) / n
    desvio = math.sqrt(variancia) if variancia > 0 else 1e-9
    sharpe = media / desvio

    be_count = acoes.count("ATIVAR_BREAK_EVEN_STOP")
    alerta_count = sum(
        1 for a in acoes if a in {"CONSIDERAR_FECHAR_PARCIAL", "FECHAR_PARCIAL"}
    )
    taxa_be = be_count / n
    taxa_reversao = alerta_count / n

    return MetricasPerfil(
        nome=nome,
        n_trades=n,
        win_rate=win_rate,
        profit_factor=profit_factor,
        max_drawdown_pct=max_drawdown_pct,
        sharpe=sharpe,
        taxa_reversao_protegida=taxa_reversao,
        taxa_break_even_acionado=taxa_be,
    )


# ============================================================
# FUNÇÃO PRINCIPAL
# ============================================================


def calibrar_perfis(
    trades_replay: List[Dict[str, Any]],
    cfg: ProfitProtectionConfig,
    perfis_candidatos: Optional[List[str]] = None,
    n_pregoes: int = 0,
) -> RelatorioCalibracaoPP:
    """Executa calibração A/B comparando baseline vs candidatos.

    Args:
        trades_replay: Lista de dicts com dados de cada trade:
            - trade_id: str
            - entry_price: float
            - direction: "BUY"|"SELL"
            - quantity: float (>0)
            - precos: List[float] — preços tick-by-tick após entrada
            - resultado_final_pct: float — retorno real do trade
        cfg: ProfitProtectionConfig carregado do YAML.
        perfis_candidatos: Nomes dos perfis candidatos a comparar.
            Se None, compara todos os perfis definidos exceto baseline.
        n_pregoes: Número de pregões cobertos pela amostra (para gauge de evidência).

    Returns:
        RelatorioCalibracaoPP com métricas e recomendação.
    """
    evidencia_suficiente = (
        n_pregoes >= MIN_PREGOES and len(trades_replay) >= MIN_TRADES
    )

    candidatos_nomes = perfis_candidatos or [
        k for k in cfg.profiles if k != "baseline"
    ]

    def _rodar_perfil(
        perfil: ProfitProtectionProfile, nome: str
    ) -> Tuple[List[float], List[str]]:
        motor = ProfitProtectionEngine(
            profile=perfil,
            profile_nome=nome,
            shadow_mode=True,  # Calibração sempre em shadow mode
        )
        resultados: List[float] = []
        acoes_all: List[str] = []

        for trade in trades_replay:
            trade_dict = {
                "trade_id": trade.get("trade_id", "REPLAY"),
                "symbol": trade.get("symbol", "WIN$N"),
                "entry_price": float(trade["entry_price"]),
                "entry_time": trade.get("entry_time"),
                "direction": trade["direction"],
                "quantity": float(trade.get("quantity", 1)),
                "initial_sl": float(trade.get("initial_sl", 0.0)),
                "initial_tp": float(trade.get("initial_tp", 0.0)),
            }
            lucro_maximo = 0.0
            for preco in trade.get("precos", []):
                try:
                    resultado = motor.processar_protecao(
                        trade=trade_dict,
                        preco_atual=float(preco),
                        lucro_maximo_sessao=lucro_maximo,
                    )
                    acoes_all.append(resultado.acao_sugerida)
                    if resultado.profit_atual > lucro_maximo:
                        lucro_maximo = resultado.profit_atual
                except Exception:
                    pass

            resultados.append(float(trade.get("resultado_final_pct", 0.0)))

        return resultados, acoes_all

    # Baseline
    baseline_perfil = cfg.profiles.get("baseline", ProfitProtectionProfile())
    baseline_ret, baseline_acoes = _rodar_perfil(baseline_perfil, "baseline")
    metricas_baseline = _calcular_metricas("baseline", baseline_ret, baseline_acoes)

    # Candidatos
    metricas_candidatos: List[MetricasPerfil] = []
    for nome_cand in candidatos_nomes:
        if nome_cand not in cfg.profiles:
            continue
        ret_c, acoes_c = _rodar_perfil(cfg.profiles[nome_cand], nome_cand)
        metricas_candidatos.append(_calcular_metricas(nome_cand, ret_c, acoes_c))

    # Seleção da recomendação
    perfil_recomendado = "baseline"
    motivo = "Baseline mantido como referência segura (sem candidato melhor)."

    for cand in metricas_candidatos:
        degradacao_wr = (metricas_baseline.win_rate - cand.win_rate) * 100
        if degradacao_wr > MAX_DEGRADACAO_WIN_RATE_PP:
            continue  # Degrada demais o win rate

        if (
            cand.max_drawdown_pct < metricas_baseline.max_drawdown_pct
            and cand.sharpe >= metricas_baseline.sharpe * 0.90
        ):
            perfil_recomendado = cand.nome
            motivo = (
                f"'{cand.nome}' reduz drawdown de {metricas_baseline.max_drawdown_pct:.2f}% "
                f"para {cand.max_drawdown_pct:.2f}% com degradação de win rate "
                f"de {degradacao_wr:.1f} p.p. (dentro do limite de {MAX_DEGRADACAO_WIN_RATE_PP} p.p.)."
            )
            break

    return RelatorioCalibracaoPP(
        baseline=metricas_baseline,
        candidatos=metricas_candidatos,
        perfil_recomendado=perfil_recomendado,
        versao_config=cfg.version,
        min_pregoes_evidencia=MIN_PREGOES,
        min_trades_evidencia=MIN_TRADES,
        evidencia_suficiente=evidencia_suficiente,
        motivo_recomendacao=motivo,
    )
