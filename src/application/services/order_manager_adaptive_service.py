"""
Order Manager Adaptive Service - Pipeline de retreinamento e antienviesamento.

Responsabilidades:
  1. identificar_regime: ADX simplificado + range do dia
  2. detectar_vies_direcional: ratio BUY/SELL nos ultimos N episodios
  3. executar_retreinamento: treino incremental via JSON features
  4. gerar_relatorio_diario: Markdown com resumo do dia

ADR-022: Servico separado do DiarioOrderManager para SRP.
Schema version: 1.0
"""
from __future__ import annotations

import json
import logging
import sqlite3
from dataclasses import dataclass, asdict
from datetime import datetime, date
from enum import Enum
from pathlib import Path
from typing import Optional

from src.application.diario_episodio_operador import EpisodioOperadorRepo
from src.application.services.diary_feedback import DiaryFeedback, save_diary_feedback

logger = logging.getLogger("order_manager_adaptive_service")

# ────────────────────────────────────────────────────────────
# Constantes (magic numbers centralizados em settings, aqui apenas ref)
# ────────────────────────────────────────────────────────────
_JANELA_VIES: int = 20           # episodios para calculo do ratio
_RATIO_VIES: float = 0.75        # threshold de vies direcional
_PREGOES_CONSECUTIVOS: int = 2   # pregoes consecutivos com vies para alerta
_MIN_EPISODIOS_RETREI: int = 10  # minimo para acionar retreinamento
_AJUSTE_THRESHOLD_PP: int = 10   # pontos percentuais de ajuste do threshold
_ADX_TENDENCIA: float = 25.0     # ADX acima = tendencia
_ADX_LATERAL: float = 20.0       # ADX abaixo = lateral
_RANGE_VOLATIL: float = 2.0      # range > 2x ATR = volatil
_ATR_MULT_LATERAL: float = 0.8
_ATR_MULT_TENDENCIA: float = 1.5
_ATR_MULT_VOLATIL: float = 1.2
_ADX_PROXY_FATOR_ESCALA: int = 10  # fator de escala do ADX proxy (0-100+)


# ────────────────────────────────────────────────────────────
# Enums e Dataclasses
# ────────────────────────────────────────────────────────────

class RegimeMercado(Enum):
    """Regime de mercado identificado pelo ADX simplificado."""

    TENDENCIA_ALTA = "TENDENCIA_ALTA"
    TENDENCIA_BAIXA = "TENDENCIA_BAIXA"
    LATERAL = "LATERAL"
    VOLATIL = "VOLATIL"


@dataclass
class ParametrosRegime:
    """Parametros operacionais derivados do regime de mercado identificado."""

    regime: RegimeMercado
    atr_multiplier_sl: float
    atr_multiplier_tp: float
    descricao: str


@dataclass
class ResultadoRetreino:
    """Resultado da execucao do pipeline de retreinamento incremental."""

    acionado: bool
    n_episodios: int
    win_rate: float
    versao: str
    caminho_modelo: Optional[Path]
    motivo_nao_acionado: str = ""


@dataclass
class AlertaVies:
    """Alerta de vies direcional detectado nos episodios recentes."""

    detectado: bool
    direcao_dominante: str    # "BUY" ou "SELL"
    ratio: float              # ex: 0.82 = 82% BUY
    ajuste_threshold_pp: int  # +10 pontos percentuais
    pregoes_consecutivos: int
    motivo: str


# ────────────────────────────────────────────────────────────
# Servico principal
# ────────────────────────────────────────────────────────────

class OrderManagerAdaptiveService:
    """
    Servico adaptativo do Order Manager.

    Identifica regime de mercado, detecta vies direcional nos episodios
    recentes e aciona retreinamento incremental quando necessario.
    Responsabilidade unica (SRP) separada do DiarioOrderManager (ADR-022).
    """

    def identificar_regime(self, candles: list[dict[str, float]]) -> ParametrosRegime:
        """
        Identifica o regime de mercado via ADX simplificado e range do dia.

        Args:
            candles: Lista de candles com chaves 'high', 'low', 'close'.

        Returns:
            ParametrosRegime com regime identificado e multiplicadores ATR.
        """
        if not candles:
            logger.warning("identificar_regime: lista de candles vazia, retornando LATERAL")
            return ParametrosRegime(
                regime=RegimeMercado.LATERAL,
                atr_multiplier_sl=_ATR_MULT_LATERAL,
                atr_multiplier_tp=_ATR_MULT_LATERAL,
                descricao="Fallback seguro: sem candles fornecidos",
            )

        # Calcular range de cada candle
        ranges_candles = [float(c["high"]) - float(c["low"]) for c in candles]
        media_range = sum(ranges_candles) / len(ranges_candles)

        # Range total do dia
        high_max = max(float(c["high"]) for c in candles)
        low_min = min(float(c["low"]) for c in candles)
        range_total = high_max - low_min

        # ADX proxy: quanto o range total supera o range medio de um candle.
        # Formula: (range_total / media_range) * 10 — mede direcionalidade
        # independente do numero de candles, compativel com _ADX_TENDENCIA=25.
        # Limiar VOLATIL usa soma_ranges para escalar pelo periodo.
        soma_ranges = sum(ranges_candles)  # equivale a media_range * len(candles)
        adx_proxy = (range_total / media_range * _ADX_PROXY_FATOR_ESCALA) if media_range > 0 else 0.0

        # Primeiro close e ultimo close para identificar direcao
        primeiro_close = float(candles[0]["close"])
        ultimo_close = float(candles[-1]["close"])

        # Classificacao do regime
        if range_total > _RANGE_VOLATIL * soma_ranges:
            return ParametrosRegime(
                regime=RegimeMercado.VOLATIL,
                atr_multiplier_sl=_ATR_MULT_VOLATIL,
                atr_multiplier_tp=_ATR_MULT_VOLATIL,
                descricao=f"Mercado volatil: range_total={range_total:.2f} > {_RANGE_VOLATIL}x soma_ranges",
            )

        if adx_proxy >= _ADX_TENDENCIA:
            if ultimo_close > primeiro_close:
                return ParametrosRegime(
                    regime=RegimeMercado.TENDENCIA_ALTA,
                    atr_multiplier_sl=_ATR_MULT_TENDENCIA,
                    atr_multiplier_tp=_ATR_MULT_TENDENCIA,
                    descricao=f"Tendencia de alta: adx_proxy={adx_proxy:.2f}, close {primeiro_close:.2f}->{ultimo_close:.2f}",
                )
            return ParametrosRegime(
                regime=RegimeMercado.TENDENCIA_BAIXA,
                atr_multiplier_sl=_ATR_MULT_TENDENCIA,
                atr_multiplier_tp=_ATR_MULT_TENDENCIA,
                descricao=f"Tendencia de baixa: adx_proxy={adx_proxy:.2f}, close {primeiro_close:.2f}->{ultimo_close:.2f}",
            )

        return ParametrosRegime(
            regime=RegimeMercado.LATERAL,
            atr_multiplier_sl=_ATR_MULT_LATERAL,
            atr_multiplier_tp=_ATR_MULT_LATERAL,
            descricao=f"Mercado lateral: adx_proxy={adx_proxy:.2f}",
        )

    def _contar_pregoes_vies(
        self, db_path: Path, direcao_dominante: str
    ) -> int:
        """
        Conta pregoes consecutivos com vies na direcao dominante.

        Implementacao simplificada: retorna 2 se qualquer episodio
        recente (ultimos 2 dias) tiver ratio alto para a direcao.

        Args:
            db_path: Caminho para o banco SQLite.
            direcao_dominante: "BUY" ou "SELL".

        Returns:
            Numero de pregoes consecutivos com vies.
        """
        try:
            repo = EpisodioOperadorRepo(str(db_path))
            episodios = repo.listar_ultimos(n=_JANELA_VIES * 2, dias=2)
            if not episodios:
                return 0

            direcionais = [e for e in episodios if e.direcao in ("BUY", "SELL")]
            if not direcionais:
                return 0

            n_dominante = sum(1 for e in direcionais if e.direcao == direcao_dominante)
            total = len(direcionais)
            ratio_recente = n_dominante / total if total > 0 else 0.0

            if ratio_recente > _RATIO_VIES:
                return _PREGOES_CONSECUTIVOS

            return 0
        except Exception as exc:
            logger.warning("_contar_pregoes_vies: erro ao consultar repo: %s", exc)
            return 0

    def detectar_vies_direcional(self, db_path: Path) -> AlertaVies:
        """
        Detecta vies direcional nos ultimos episodios e persiste feedback se necessario.

        Analisa o ratio BUY/SELL nos ultimos _JANELA_VIES episodios.
        Se ratio > _RATIO_VIES por _PREGOES_CONSECUTIVOS pregoes, gera
        DiaryFeedback com sugestao de ajuste de threshold.

        Args:
            db_path: Caminho para o banco SQLite de episodios.

        Returns:
            AlertaVies com resultado da deteccao.
        """
        repo = EpisodioOperadorRepo(str(db_path))
        episodios = repo.listar_ultimos(n=_JANELA_VIES)

        direcionais = [e for e in episodios if e.direcao in ("BUY", "SELL")]

        if not direcionais:
            return AlertaVies(
                detectado=False,
                direcao_dominante="",
                ratio=0.0,
                ajuste_threshold_pp=0,
                pregoes_consecutivos=0,
                motivo="Sem episodios direcionais para analise",
            )

        n_buy = sum(1 for e in direcionais if e.direcao == "BUY")
        total = len(direcionais)
        ratio_buy = n_buy / total

        # Maior ratio entre BUY e SELL
        ratio = max(ratio_buy, 1.0 - ratio_buy)
        direcao_dominante = "BUY" if ratio_buy >= 0.5 else "SELL"

        if ratio <= _RATIO_VIES:
            return AlertaVies(
                detectado=False,
                direcao_dominante="",
                ratio=ratio,
                ajuste_threshold_pp=0,
                pregoes_consecutivos=0,
                motivo="Sem vies detectado",
            )

        # Verificar pregoes consecutivos
        pregoes = self._contar_pregoes_vies(db_path, direcao_dominante)

        if pregoes >= _PREGOES_CONSECUTIVOS:
            feedback = DiaryFeedback(
                date=date.today().isoformat(),
                timestamp=datetime.now().isoformat(),
                source="vies_detector",
                nota_agente=6,
                sugestoes=[
                    f"Ajustar threshold {direcao_dominante} em +{_AJUSTE_THRESHOLD_PP}pp"
                ],
                alertas_criticos=[
                    f"Vies direcional detectado: {direcao_dominante} ({ratio:.0%}) "
                    f"por {pregoes} pregoes consecutivos"
                ],
                retreinamento_necessario=True,
                win_rate_pct=0.0,
                n_episodes=total,
            )
            save_diary_feedback(str(db_path), feedback)
            logger.warning(
                "Vies detectado: direcao=%s ratio=%.2f pregoes=%d — feedback persistido",
                direcao_dominante, ratio, pregoes,
            )

        return AlertaVies(
            detectado=True,
            direcao_dominante=direcao_dominante,
            ratio=ratio,
            ajuste_threshold_pp=_AJUSTE_THRESHOLD_PP,
            pregoes_consecutivos=pregoes,
            motivo=(
                f"Vies {direcao_dominante} detectado: ratio={ratio:.2f}, "
                f"pregoes_consecutivos={pregoes}"
            ),
        )

    def executar_retreinamento(
        self, db_path: Path, modelo_dir: Path
    ) -> ResultadoRetreino:
        """
        Executa retreinamento incremental com episodios do dia.

        Exporta features dos episodios conhecidos em JSON e atualiza
        o historico de versoes. Aciona apenas se houver episodios suficientes.

        Args:
            db_path: Caminho para o banco SQLite de episodios.
            modelo_dir: Diretorio onde salvar os artefatos do modelo.

        Returns:
            ResultadoRetreino com status e metricas do retreinamento.
        """
        repo = EpisodioOperadorRepo(str(db_path))
        episodios_dia = repo.listar_ultimos(n=100, dias=1)

        # Filtrar apenas episodios com resultado conhecido
        filtrados = [e for e in episodios_dia if e.resultado_pts != 0]

        if len(filtrados) < _MIN_EPISODIOS_RETREI:
            logger.info(
                "Retreinamento nao acionado: %d/%d episodios validos",
                len(filtrados), _MIN_EPISODIOS_RETREI,
            )
            return ResultadoRetreino(
                acionado=False,
                n_episodios=len(filtrados),
                win_rate=0.0,
                versao="",
                caminho_modelo=None,
                motivo_nao_acionado=(
                    f"Episodios insuficientes: {len(filtrados)}/{_MIN_EPISODIOS_RETREI}"
                ),
            )

        # Calcular win rate
        n_acertos = sum(1 for e in filtrados if e.foi_acerto)
        win_rate = n_acertos / len(filtrados)

        # Versao baseada no timestamp atual
        versao = datetime.now().strftime("%Y%m%d_%H%M%S")

        # Garantir diretorio
        modelo_dir.mkdir(parents=True, exist_ok=True)

        # Exportar features
        features: list[dict[str, object]] = [
            {
                "session_id": ep.session_id,
                "direcao": ep.direcao,
                "confianca_entrada": ep.confianca_entrada,
                "alinhamento_entrada": ep.alinhamento_entrada,
                "momentum_entrada": ep.momentum_entrada,
                "atr_entrada": ep.atr_entrada,
                "eficiencia": ep.eficiencia,
                "foi_acerto": 1 if ep.foi_acerto else 0,
                "resultado_pts": ep.resultado_pts,
            }
            for ep in filtrados
        ]

        payload: dict[str, object] = {
            "schema_version": "1.0",
            "versao": versao,
            "n_episodios": len(filtrados),
            "win_rate": win_rate,
            "features": features,
        }

        caminho_modelo = modelo_dir / f"modelo_{versao}.json"
        caminho_modelo.write_text(
            json.dumps(payload, indent=2, ensure_ascii=False),
            encoding="utf-8",
        )

        # Atualizar historico de versoes
        self._atualizar_historico_versoes(
            modelo_dir=modelo_dir,
            versao=versao,
            n_episodios=len(filtrados),
            win_rate=win_rate,
            nome_arquivo=caminho_modelo.name,
        )

        logger.info(
            "Retreinamento concluido: versao=%s n=%d win_rate=%.2f",
            versao, len(filtrados), win_rate,
        )

        return ResultadoRetreino(
            acionado=True,
            n_episodios=len(filtrados),
            win_rate=win_rate,
            versao=versao,
            caminho_modelo=caminho_modelo,
        )

    def _atualizar_historico_versoes(
        self,
        modelo_dir: Path,
        versao: str,
        n_episodios: int,
        win_rate: float,
        nome_arquivo: str,
    ) -> None:
        """
        Atualiza o arquivo historico_versoes.json com a nova versao.

        Args:
            modelo_dir: Diretorio do modelo.
            versao: Identificador da versao gerada.
            n_episodios: Numero de episodios usados no retreinamento.
            win_rate: Win rate calculado.
            nome_arquivo: Nome do arquivo JSON de features gerado.
        """
        historico_path = modelo_dir / "historico_versoes.json"

        if historico_path.exists():
            try:
                historico = json.loads(historico_path.read_text(encoding="utf-8"))
            except (json.JSONDecodeError, OSError):
                historico = {"schema_version": "1.0", "versoes": []}
        else:
            historico = {"schema_version": "1.0", "versoes": []}

        # Garantir schema_version correto
        historico["schema_version"] = "1.0"

        nova_entrada: dict[str, object] = {
            "versao": versao,
            "n_episodios": n_episodios,
            "win_rate": win_rate,
            "caminho": nome_arquivo,
        }
        versoes: list[dict[str, object]] = historico.get("versoes", [])
        versoes.append(nova_entrada)
        historico["versoes"] = versoes

        historico_path.write_text(
            json.dumps(historico, indent=2, ensure_ascii=False),
            encoding="utf-8",
        )

    def gerar_relatorio_diario(
        self,
        db_path: Path,
        modelo_dir: Path,
        outputs_dir: Optional[Path] = None,
    ) -> Path:
        """
        Gera relatorio diario em Markdown com metricas de performance e retreinamento.

        Consolida: win rate do dia, deteccao de vies direcional, resultado
        do retreinamento e identificacao de regime (sem candles = N/A).

        Args:
            db_path: Caminho para o banco SQLite de episodios.
            modelo_dir: Diretorio de modelos para retreinamento.
            outputs_dir: Diretorio de saida (default: "outputs").

        Returns:
            Path do arquivo Markdown gerado.
        """
        dir_saida = outputs_dir or Path("outputs")
        dir_saida.mkdir(parents=True, exist_ok=True)

        repo = EpisodioOperadorRepo(str(db_path))
        episodios = repo.listar_ultimos(n=200, dias=1)

        # Metricas do dia
        n_episodios = len(episodios)
        win_rate = 0.0
        eficiencia_media = 0.0

        if n_episodios > 0:
            n_acertos = sum(1 for e in episodios if e.foi_acerto)
            win_rate = n_acertos / n_episodios
            eficiencia_media = sum(e.eficiencia for e in episodios) / n_episodios

        # Deteccao de vies
        alerta_vies = self.detectar_vies_direcional(db_path)

        # Retreinamento
        resultado_retrei = self.executar_retreinamento(db_path, modelo_dir)

        # Gerar Markdown
        data_hoje = date.today().strftime("%Y%m%d")
        nome_arquivo = f"order_manager_relatorio_{data_hoje}.md"
        caminho_relatorio = dir_saida / nome_arquivo

        linhas: list[str] = [
            f"# Order Manager — Relatorio Diario {date.today().isoformat()}",
            "",
            "## Metricas do Dia",
            f"- **Episodios registrados:** {n_episodios}",
            f"- **Win Rate:** {win_rate:.1%}",
            f"- **Eficiencia Media:** {eficiencia_media:.2f}",
            "",
            "## Deteccao de Vies Direcional",
            f"- **Detectado:** {'Sim' if alerta_vies.detectado else 'Nao'}",
        ]

        if alerta_vies.detectado:
            linhas += [
                f"- **Direcao Dominante:** {alerta_vies.direcao_dominante}",
                f"- **Ratio:** {alerta_vies.ratio:.2f}",
                f"- **Pregoes Consecutivos:** {alerta_vies.pregoes_consecutivos}",
                f"- **Ajuste Sugerido:** +{alerta_vies.ajuste_threshold_pp}pp",
            ]
        else:
            linhas.append(f"- **Motivo:** {alerta_vies.motivo}")

        linhas += [
            "",
            "## Retreinamento Incremental",
            f"- **Acionado:** {'Sim' if resultado_retrei.acionado else 'Nao'}",
            f"- **Episodios Validos:** {resultado_retrei.n_episodios}",
        ]

        if resultado_retrei.acionado:
            linhas += [
                f"- **Versao:** {resultado_retrei.versao}",
                f"- **Win Rate Calculado:** {resultado_retrei.win_rate:.1%}",
                f"- **Caminho:** {resultado_retrei.caminho_modelo}",
            ]
        else:
            linhas.append(f"- **Motivo:** {resultado_retrei.motivo_nao_acionado}")

        linhas += [
            "",
            "---",
            f"*Gerado em {datetime.now().isoformat()} — schema_version=1.0*",
        ]

        caminho_relatorio.write_text(
            "\n".join(linhas) + "\n",
            encoding="utf-8",
        )

        logger.info("Relatorio diario gerado: %s", caminho_relatorio)
        return caminho_relatorio
