"""
Diario Order Manager — Motor de Execucao Autonomo do Agente Diarios.

O Agente Diarios e INDEPENDENTE. Opera como um head de tesouraria:
  - QuantumOperatorEngine: 106 ativos correlacionados, macro, tecnico
  - LeituraDeOperador: percepcao contextual (fase, exaustao, armadilhas,
    barato/caro, correlacoes inter-mercado, mudanca de cenario)
  - EpisodioOperador: aprende com seus proprios trades — o que funcionou,
    em qual fase do dia, em qual contexto de mercado
  - GuardianState: kill_switch e alertas macros criticos

Nao depende de sinais de outros agentes. "Sente o mercado."

Pipeline (ciclo de 30s):
    candles M15 + macro + guardian
    → LeituraDeOperador.ler() → percepcao contextual
    → consolidar_sinal() → decisao com leitura integrada
    → monitorar_posicao() ou abrir_posicao()
    → registrar_episodio() → aprendizado proprio

Magic Number: 234800
Status: v3.0 (17/03/2026) — head de tesouraria, aprende com episodios
"""

from __future__ import annotations

import json
import logging
import threading
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Optional

from src.application.diario_leitura_operador import LeituraDeOperador, LeituraOperador
from src.application.diario_episodio_operador import (
    EpisodioOperadorRepo,
    AprendizadoOperador,
    construir_episodio,
    construir_episodio_neutro,
)
from src.application.diario_market_features import (
    build_diario_market_features_snapshot,
    persist_diario_market_features_snapshot,
)
from src.application.opening_market_confirmation import (
    build_live_market_confirmation,
)
from src.application.opening_context_policy import (
    apply_opening_context_strict_filters,
    evaluate_opening_context_gate,
    normalize_opening_context,
)
from src.application.confidence_utils import (
    CONFIDENCE_OVERRIDE_TODAY_FILE,
    load_daily_confidence_override,
    resolve_daily_confidence_gate,
)

logger = logging.getLogger("diario_order_manager")

# ── Identidade ──────────────────────────────────────────────────
MAGIC_NUMBER = 234800
SIMBOLO = "WIN$N"
VOLUME = 1

# ── Parametros de entrada ────────────────────────────────────────
# Confianca minima do QuantumOperatorEngine para considerar entrada
CONFIANCA_MINIMA = 0.60
# Piso cauteloso quando houver confidence diaria do P50-B
CONFIANCA_MINIMA_CAUTELOSA = 0.35
# Alinhamento minimo entre macro/tecnico/sentimento (0-1)
ALINHAMENTO_MINIMO = 0.55
# Multiplicadores de ATR para SL e TP
# Historico: SL era 1.5x ATR (max 1.200 pts). Analise de 23-24/03/2026
# mostrou R:R efetivo de 0.44 (ganho medio=327pts, perda media=739pts).
# Recalibrado em 24/03/2026 para reduzir risco por operacao.
SL_ATR_MULT = 0.75  # SL = preco +/- 0.75 * ATR (era 1.5x)
TP_ATR_MULT = 1.5   # TP = preco +/- 1.5 * ATR  (era 2.5x) — R:R teorico=2.0
# ATR minimo em pontos (proteção contra mercado parado)
ATR_MINIMO = 80
# ATR maximo em pontos (proteção contra volatilidade extrema)
ATR_MAXIMO = 800
# Reversao: pontos contra a posicao para fechar antecipado
REVERSAO_ATR_MULT = 0.8  # fecha se preco reverteu 0.8*ATR (era 1.2x)
# Devolucao de ganho: % do ganho maximo que aciona fechamento
REVERSAO_PCT_GANHO = 0.50  # protege 50% do ganho maximo (era 60%)
# Horario de pregao
HORA_INICIO = (9, 0)
HORA_FIM = (17, 30)


# ────────────────────────────────────────────────────────────────
# ATR a partir de candles
# ────────────────────────────────────────────────────────────────


def calcular_atr(candles: list, periodo: int = 14) -> float:
    """
    Calcula ATR (Average True Range) a partir dos candles.

    Cada candle deve ter atributos .high, .low, .close com .value.
    Retorna ATR em pontos. Retorna ATR_MINIMO se dados insuficientes.
    """
    if len(candles) < periodo + 1:
        return float(ATR_MINIMO)

    trs = []
    for i in range(1, len(candles)):
        h = float(candles[i].high.value)
        l = float(candles[i].low.value)
        c_ant = float(candles[i - 1].close.value)
        tr = max(h - l, abs(h - c_ant), abs(l - c_ant))
        trs.append(tr)

    # Media dos ultimos `periodo` TRs
    atr = sum(trs[-periodo:]) / periodo
    return max(float(ATR_MINIMO), min(float(ATR_MAXIMO), atr))


def calcular_momentum(candles: list, janela: int = 5) -> float:
    """
    Momentum simples: variacao de preco nas ultimas `janela` velas.
    Retorna pontos (positivo = alta, negativo = baixa).
    """
    if len(candles) < janela + 1:
        return 0.0
    preco_atual = float(candles[-1].close.value)
    preco_passado = float(candles[-janela].close.value)
    return preco_atual - preco_passado


# ────────────────────────────────────────────────────────────────
# Sinal consolidado
# ────────────────────────────────────────────────────────────────


@dataclass
class SinalDiario:
    """Decisao consolidada do Agente Diarios para um ciclo."""

    timestamp: str
    direcao: str  # "BUY", "SELL", "NEUTRO"
    confianca: float  # 0.0-1.0 (ajustada pelos episodios proprios)
    alinhamento: float  # alignment_score do QuantumOperatorEngine
    macro_bias: str
    tecnico_bias: str
    sentimento_bias: str
    atr: float  # ATR da sessao atual em pontos
    momentum: float  # momentum das ultimas 5 velas
    preco_atual: float
    sl: float  # stop loss calculado
    tp: float  # take profit calculado
    guardian_ok: bool
    guardian_penalty: float
    win_rate_propria: float  # win rate dos episodios proprios do Diarios
    n_episodios_proprios: int
    leitura: Optional[LeituraOperador] = None  # percepcao contextual do operador
    vies_intraday: str = ""
    watchlist: list[str] = field(default_factory=list)
    contexto_flags: list[str] = field(default_factory=list)
    confirmacao_live: dict[str, Any] = field(default_factory=dict)
    pode_operar: bool = False
    motivo_bloqueio: str = ""


# ────────────────────────────────────────────────────────────────
# Estado da posicao (JSON — mesmo padrao dos outros agentes)
# ────────────────────────────────────────────────────────────────


@dataclass
class DiarioPosicao:
    aberta: bool = False
    ticket: Optional[int] = None
    direcao: str = ""
    preco_entrada: float = 0.0
    sl: float = 0.0
    tp: float = 0.0
    atr_entrada: float = 0.0  # ATR no momento da entrada
    abertura_ts: str = ""
    session_id: str = ""
    max_ganho_pts: float = 0.0
    ultimo_preco: float = 0.0
    n_checks: int = 0

    def to_dict(self) -> dict:
        return {
            "aberta": self.aberta,
            "ticket": self.ticket,
            "direcao": self.direcao,
            "preco_entrada": self.preco_entrada,
            "sl": self.sl,
            "tp": self.tp,
            "atr_entrada": self.atr_entrada,
            "abertura_ts": self.abertura_ts,
            "session_id": self.session_id,
            "max_ganho_pts": self.max_ganho_pts,
            "ultimo_preco": self.ultimo_preco,
            "n_checks": self.n_checks,
        }

    @classmethod
    def from_dict(cls, d: dict) -> "DiarioPosicao":
        obj = cls()
        obj.aberta = d.get("aberta", False)
        obj.ticket = d.get("ticket")
        obj.direcao = d.get("direcao", "")
        obj.preco_entrada = float(d.get("preco_entrada", 0))
        obj.sl = float(d.get("sl", 0))
        obj.tp = float(d.get("tp", 0))
        obj.atr_entrada = float(d.get("atr_entrada", 0))
        obj.abertura_ts = d.get("abertura_ts", "")
        obj.session_id = d.get("session_id", "")
        obj.max_ganho_pts = float(d.get("max_ganho_pts", 0))
        obj.ultimo_preco = float(d.get("ultimo_preco", 0))
        obj.n_checks = int(d.get("n_checks", 0))
        return obj


class DiarioPosicaoStatus:
    """
    Rastreia posicao aberta do Agente Diarios em arquivo JSON.

    Arquivo: outputs/agente_posicao_diarios_{session_id}.json
    """

    def __init__(self, session_id: str, outputs_dir: str = "outputs"):
        self.session_id = session_id
        self._path = Path(outputs_dir) / f"agente_posicao_diarios_{session_id}.json"
        self._lock = threading.Lock()
        self._posicao = DiarioPosicao(session_id=session_id)
        self._carregar()

    def _carregar(self) -> None:
        if self._path.exists():
            try:
                data = json.loads(self._path.read_text(encoding="utf-8"))
                self._posicao = DiarioPosicao.from_dict(data)
            except Exception as e:
                logger.warning("Erro ao carregar posicao JSON: %s", e)

    def _salvar(self) -> None:
        try:
            self._path.parent.mkdir(parents=True, exist_ok=True)
            self._path.write_text(
                json.dumps(self._posicao.to_dict(), indent=2, ensure_ascii=False),
                encoding="utf-8",
            )
        except Exception as e:
            logger.error("Erro ao salvar posicao JSON: %s", e)

    @property
    def posicao(self) -> DiarioPosicao:
        with self._lock:
            return self._posicao

    def tem_posicao_aberta(self) -> bool:
        with self._lock:
            return self._posicao.aberta

    def registrar_abertura(
        self,
        ticket: int,
        direcao: str,
        preco_entrada: float,
        sl: float,
        tp: float,
        atr_entrada: float = 0.0,
    ) -> None:
        with self._lock:
            self._posicao.aberta = True
            self._posicao.ticket = ticket
            self._posicao.direcao = direcao
            self._posicao.preco_entrada = preco_entrada
            self._posicao.sl = sl
            self._posicao.tp = tp
            self._posicao.atr_entrada = atr_entrada
            self._posicao.abertura_ts = datetime.now().isoformat()
            self._posicao.max_ganho_pts = 0.0
            self._posicao.ultimo_preco = preco_entrada
            self._posicao.n_checks = 0
            self._salvar()
        logger.info(
            "Posicao aberta: ticket=%s dir=%s entrada=%.0f SL=%.0f TP=%.0f ATR=%.0f",
            ticket,
            direcao,
            preco_entrada,
            sl,
            tp,
            atr_entrada,
        )

    def atualizar_preco(self, preco_atual: float) -> None:
        with self._lock:
            self._posicao.ultimo_preco = preco_atual
            self._posicao.n_checks += 1
            if self._posicao.direcao == "BUY":
                ganho = preco_atual - self._posicao.preco_entrada
            else:
                ganho = self._posicao.preco_entrada - preco_atual
            if ganho > self._posicao.max_ganho_pts:
                self._posicao.max_ganho_pts = ganho
            self._salvar()

    def registrar_fechamento(self, motivo: str = "") -> None:
        with self._lock:
            logger.info(
                "Posicao fechada: ticket=%s dir=%s entrada=%.0f ultimo=%.0f motivo=%s",
                self._posicao.ticket,
                self._posicao.direcao,
                self._posicao.preco_entrada,
                self._posicao.ultimo_preco,
                motivo,
            )
            self._posicao.aberta = False
            self._posicao.ticket = None
            self._salvar()


# ────────────────────────────────────────────────────────────────
# Motor principal
# ────────────────────────────────────────────────────────────────


class DiarioOrderManager:
    """
    Motor de execucao autonomo do Agente Diarios.

    Toma decisoes proprias com base em:
      - QuantumOperatorEngine (macro + tecnico + alinhamento)
      - Candles M15 (ATR, momentum, preco atual)
      - GuardianState (kill_switch, bias)
      - Win rate dos proprios episodios (auto-ajuste de confianca)

    Nao depende de oportunidades ou sinais de outros agentes.

    Uso:
        manager = DiarioOrderManager(mt5, db_path, session_id)
        resultado = manager.ciclo(decisao, candles, guardian, dir_analysis)
    """

    def __init__(
        self,
        mt5_adapter: object,
        db_path: str,
        session_id: str,
        outputs_dir: str = "outputs",
        rl_reader: Optional[object] = None,
        opening_context: Optional[Any] = None,
        confidence_override_path: str | Path | None = None,
    ):
        self._mt5 = mt5_adapter
        self._db_path = db_path
        self._session_id = session_id
        self._outputs_dir = Path(outputs_dir)
        self._confidence_override_path = (
            Path(confidence_override_path)
            if confidence_override_path is not None
            else CONFIDENCE_OVERRIDE_TODAY_FILE
        )
        self._latest_market_features_path = (
            self._outputs_dir / "analysis" / "diario_market_features_latest.json"
        )
        self._posicao = DiarioPosicaoStatus(session_id, outputs_dir)
        self._leitor = LeituraDeOperador()
        self._ep_repo = EpisodioOperadorRepo(db_path)
        self._aprendizado = AprendizadoOperador(self._ep_repo)
        self._sinal_abertura: Optional[SinalDiario] = None  # sinal quando abriu posicao
        self._n_ciclos = 0
        self._ultimo_sinal: Optional[SinalDiario] = None
        self._ultimo_snapshot_intraday: Optional[dict[str, Any]] = None
        self._ultimo_neutro_registrado: int = 0  # ciclo do ultimo episodio neutro
        self._candles_no_neutro: Optional[list] = None  # snapshot para avaliar decisao
        self._opening_context_raw = opening_context
        self._opening_context = normalize_opening_context(opening_context)

        if rl_reader is not None:
            self._rl_reader = rl_reader
        else:
            from scripts.start_journals_full_display import RLPerformanceReader

            self._rl_reader = RLPerformanceReader(db_path)

    def _confidence_gate_minima(self) -> float:
        """Retorna o threshold efetivo do gate de confianca."""
        if not hasattr(self, "_confidence_override_path"):
            return CONFIANCA_MINIMA

        override = load_daily_confidence_override(self._confidence_override_path)
        return resolve_daily_confidence_gate(
            override,
            default_gate=CONFIANCA_MINIMA,
            cautious_floor=CONFIANCA_MINIMA_CAUTELOSA,
        )

    def _opening_context_source(self) -> Any:
        raw = getattr(self, "_opening_context_raw", None)
        if raw not in (None, {}, []):
            return raw
        return getattr(self, "_opening_context", None)

    def _publicar_snapshot_intraday(
        self,
        sinal: SinalDiario,
        candles: list,
        guardian_state: object,
    ) -> dict[str, Any]:
        latest_path = getattr(
            self,
            "_latest_market_features_path",
            Path("outputs") / "analysis" / "diario_market_features_latest.json",
        )
        snapshot = build_diario_market_features_snapshot(
            session_id=self._session_id,
            symbol=SIMBOLO,
            signal=sinal,
            candles=candles,
            guardian_state=guardian_state,
            live_confirmation=sinal.confirmacao_live,
            opening_context=self._opening_context_source(),
        )
        payload = snapshot.to_dict()
        try:
            persist_diario_market_features_snapshot(
                self._db_path,
                snapshot,
                latest_json_path=latest_path,
            )
        except Exception as exc:
            logger.warning("Falha ao persistir snapshot intraday do Diario: %s", exc)
        self._ultimo_snapshot_intraday = payload
        return payload

    # ── Horario de pregao ────────────────────────────────────────

    def _no_pregao(self) -> bool:
        agora = datetime.now()
        inicio = agora.replace(hour=HORA_INICIO[0], minute=HORA_INICIO[1], second=0)
        fim = agora.replace(hour=HORA_FIM[0], minute=HORA_FIM[1], second=0)
        return inicio <= agora <= fim

    # ── Win rate dos episodios proprios (magic=234800) ───────────

    def _win_rate_propria(self) -> tuple[float, int]:
        """
        Calcula win rate baseado nos proprios episodios do Agente Diarios.

        Usa rewards avaliados do dia. Retorna (win_rate 0-100, n_episodios).
        """
        try:
            rewards = self._rl_reader.get_today_rewards()
            avaliados = [r for r in rewards if r.get("is_evaluated") == 1]
            if len(avaliados) < 3:
                return 50.0, 0  # neutro se poucos dados
            corretos = sum(1 for r in avaliados if r.get("was_correct") == 1)
            wr = corretos / len(avaliados) * 100
            return wr, len(avaliados)
        except Exception:
            return 50.0, 0

    # ── Ajuste de confianca pelos proprios resultados ────────────

    def _ajustar_confianca(
        self,
        confianca_base: float,
        guardian_penalty: float,
    ) -> float:
        """
        Ajusta confianca com base no proprio historico e penalidade Guardian.

        Win rate > 65%: bonus +0.08
        Win rate 50-65%: sem ajuste
        Win rate < 40%: penalidade -0.12 (agente aprendeu que estava errando)
        Guardian penalty: -penalty/100
        """
        wr, n = self._win_rate_propria()

        if n >= 3:
            if wr >= 65.0:
                confianca_base = min(0.95, confianca_base + 0.08)
            elif wr < 40.0:
                confianca_base = max(0.0, confianca_base - 0.12)

        confianca_base = max(0.0, confianca_base - guardian_penalty / 100.0)
        return confianca_base

    def _motivo_direcao_neutra(
        self,
        leitura: Optional[LeituraOperador],
        direcao_decisao: str,
        contexto_trend_follow: bool,
        confianca_final: float,
        confianca_minima_efetiva: float,
        kill_switch: bool,
    ) -> str:
        """Classifica a subcondicao que levou o sinal a NEUTRO."""
        if kill_switch:
            return "direcao_neutro:guardian_kill_switch"
        if leitura is not None:
            if leitura.exaustao_detectada:
                return "direcao_neutro:exaustao_detectada"
            if leitura.divergencia_critica:
                return "direcao_neutro:divergencia_critica"
            if leitura.cenario_mudou:
                return "direcao_neutro:cenario_mudou"
        if contexto_trend_follow and confianca_final < confianca_minima_efetiva:
            return (
                "direcao_neutro:trend_follow_baixa_confianca:"
                f"{confianca_final:.2f}<{confianca_minima_efetiva:.2f}"
            )
        if direcao_decisao == "NEUTRO":
            return "direcao_neutro:direcao_decisao_neutra"
        return "direcao_neutro:indefinido"

    def _eh_contexto_trend_follow(
        self,
        leitura: Optional[LeituraOperador],
    ) -> bool:
        """Detecta quando a leitura aponta para pullback/trend-follow."""
        if leitura is None:
            return False

        resumo = str(getattr(leitura, "resumo", "") or "").lower()
        direcao = str(getattr(leitura, "direcao_preferida", "NEUTRO")).upper()

        return direcao in ("BUY", "SELL") and (
            getattr(leitura, "pullback_saudavel", False)
            or "pullback" in resumo
            or "trend" in resumo
            or "direcao da tendencia" in resumo
        )

    # ── Consolidar decisao propria ───────────────────────────────

    def consolidar_sinal(
        self,
        decisao: object,  # OperatorDecision
        candles: list,  # Candles M15 ao vivo
        guardian_state: object,
        dir_analysis: Optional[dict] = None,
    ) -> SinalDiario:
        """
        Consolida todas as fontes proprias em um SinalDiario.

        Logica de direcao (hierarquia):
        1. Guardian kill_switch → NEUTRO (para tudo)
        2. Guardian bias_override CONTRA → inverte sinal macro
        3. Alinhamento abaixo do minimo → NEUTRO (sinais contraditórios)
        4. analyze_directional_critical: se confianca_ajustada < 50 e
           tem contradicoes → penalidade adicional na confianca
        5. Momentum confirma ou contradiz a direcao macro? Se contradiz
           fortemente (>2*ATR), penalidade de 0.10
        """
        agora = datetime.now().isoformat()

        # ── Dados do QuantumOperatorEngine ──
        acao = str(getattr(decisao, "action", "HOLD"))
        if hasattr(getattr(decisao, "action", None), "value"):
            acao = decisao.action.value
        confianca_base = float(getattr(decisao, "confidence", 0.0))
        alinhamento = float(getattr(decisao, "alignment_score", 0.0))
        macro_bias = str(getattr(decisao, "macro_bias", "NEUTRO"))
        tecnico_bias = str(getattr(decisao, "technical_bias", "NEUTRO"))
        sentimento_bias = str(getattr(decisao, "sentiment_bias", "NEUTRO"))

        # ── Guardian ──
        kill_switch = getattr(guardian_state, "active_kill_switch", False)
        bias_override = str(getattr(guardian_state, "bias_override", ""))
        guardian_penalty = float(getattr(guardian_state, "confidence_penalty", 0.0))
        guardian_ok = not kill_switch

        # ── Mercado: ATR e momentum ──
        atr = calcular_atr(candles)
        momentum = calcular_momentum(candles)
        preco_atual = float(candles[-1].close.value) if candles else 0.0

        # ── Direcao base ──
        if kill_switch:
            direcao = "NEUTRO"
        elif bias_override == "CONTRA":
            direcao = "SELL" if acao == "BUY" else "BUY" if acao == "SELL" else "NEUTRO"
        elif bias_override == "NEUTRO":
            direcao = "NEUTRO"
        else:
            direcao = acao if acao in ("BUY", "SELL") else "NEUTRO"

        # ── Penalidade de momentum contraditorio ──
        # Se momentum forte na direcao oposta (> 1.5*ATR), reduz confianca
        if direcao == "BUY" and momentum < -(atr * 1.5):
            confianca_base = max(0.0, confianca_base - 0.10)
            logger.debug(
                "Momentum BUY contradiz: %.0f pts, penalidade aplicada", momentum
            )
        elif direcao == "SELL" and momentum > (atr * 1.5):
            confianca_base = max(0.0, confianca_base - 0.10)
            logger.debug(
                "Momentum SELL contradiz: %.0f pts, penalidade aplicada", momentum
            )

        # ── Penalidade de contradicoes macro ──
        if dir_analysis:
            contradicoes = dir_analysis.get("contradicoes", [])
            conf_dir = float(dir_analysis.get("confianca_ajustada", 100))
            if len(contradicoes) >= 2 and conf_dir < 50:
                confianca_base = max(0.0, confianca_base - 0.08)

        # ── Leitura de operador: percepcao contextual ──
        # Obter items macro do MacroScoreResult (se disponivel via dir_analysis)
        macro_items = dir_analysis.get("detalhes_categorias") if dir_analysis else None
        leitura = self._leitor.ler(
            candles=candles,
            decisao=decisao,
            guardian_state=guardian_state,
            macro_items=macro_items,
            atr=atr,
        )

        # Aplicar ajuste da leitura na confianca
        confianca_base = max(0.0, confianca_base + leitura.ajuste_confianca)

        # Se leitura indica direcao preferida diferente da macro → NEUTRO
        if (
            leitura.direcao_preferida not in ("NEUTRO", "")
            and leitura.direcao_preferida != direcao
            and direcao != "NEUTRO"
        ):
            # Leitura e macro divergem: reduzir confianca adicionalmente
            confianca_base = max(0.0, confianca_base - 0.10)
            logger.debug(
                "Leitura diverge da macro: leitura=%s macro=%s, penalidade -0.10",
                leitura.direcao_preferida,
                direcao,
            )

        # ── Confianca final (ajustada pelos proprios episodios) ──
        confianca_final = self._ajustar_confianca(confianca_base, guardian_penalty)
        wr, n_ep = self._win_rate_propria()
        opening_context_source = self._opening_context_source()
        live_confirmation = build_live_market_confirmation(
            self._mt5,
            opening_context_source,
        )
        opening_context_gate = evaluate_opening_context_gate(
            direcao,
            opening_context_source,
            confidence=confianca_final,
            alignment=alinhamento,
            market_confirmation=live_confirmation.to_dict(),
        )
        opening_context_gate = apply_opening_context_strict_filters(
            opening_context_gate
        )
        contexto_flags = list(opening_context_gate.reasons)

        # ── SL e TP por ATR ──
        if preco_atual > 0 and direcao in ("BUY", "SELL"):
            sl_dist = atr * SL_ATR_MULT
            tp_dist = atr * TP_ATR_MULT
            if direcao == "BUY":
                sl = preco_atual - sl_dist
                tp = preco_atual + tp_dist
            else:
                sl = preco_atual + sl_dist
                tp = preco_atual - tp_dist
        else:
            sl = tp = 0.0

        # ── Decisao final ──
        pode_operar = True
        motivo_bloqueio = ""
        confianca_minima_efetiva = self._confidence_gate_minima()
        contexto_trend_follow = self._eh_contexto_trend_follow(leitura)

        if not self._no_pregao():
            pode_operar = False
            motivo_bloqueio = "fora_do_pregao"
        elif kill_switch:
            pode_operar = False
            motivo_bloqueio = "guardian_kill_switch"
        elif direcao == "NEUTRO":
            pode_operar = False
            motivo_bloqueio = self._motivo_direcao_neutra(
                leitura,
                direcao,
                contexto_trend_follow,
                confianca_final,
                confianca_minima_efetiva,
                kill_switch,
            )
        elif alinhamento < ALINHAMENTO_MINIMO:
            pode_operar = False
            motivo_bloqueio = (
                f"alinhamento_baixo:{alinhamento:.2f}<{ALINHAMENTO_MINIMO}"
            )
        elif confianca_final < confianca_minima_efetiva:
            pode_operar = False
            motivo_bloqueio = (
                f"confianca_baixa:{confianca_final:.2f}<"
                f"{confianca_minima_efetiva:.2f}"
            )
        elif atr < ATR_MINIMO:
            pode_operar = False
            motivo_bloqueio = f"mercado_parado:ATR={atr:.0f}<{ATR_MINIMO}"
        elif preco_atual == 0.0:
            pode_operar = False
            motivo_bloqueio = "sem_preco"
        elif leitura.divergencia_critica:
            pode_operar = False
            motivo_bloqueio = "divergencia_critica_correlatos"
        elif not leitura.momento_favoravel and leitura.risco_armadilha == "ALTA":
            pode_operar = False
            motivo_bloqueio = f"armadilha_alta:{leitura.armadilhas[0][:60] if leitura.armadilhas else ''}"
        elif not opening_context_gate.allow_entry:
            pode_operar = False
            motivo_bloqueio = f"contexto_abertura:{opening_context_gate.summary}"

        return SinalDiario(
            timestamp=agora,
            direcao=direcao,
            confianca=confianca_final,
            alinhamento=alinhamento,
            macro_bias=macro_bias,
            tecnico_bias=tecnico_bias,
            sentimento_bias=sentimento_bias,
            atr=atr,
            momentum=momentum,
            preco_atual=preco_atual,
            sl=sl,
            tp=tp,
            guardian_ok=guardian_ok,
            guardian_penalty=guardian_penalty,
            win_rate_propria=wr,
            n_episodios_proprios=n_ep,
            leitura=leitura,
            vies_intraday=opening_context_gate.policy.vies_intraday,
            watchlist=list(opening_context_gate.policy.watchlist),
            contexto_flags=contexto_flags,
            confirmacao_live=live_confirmation.to_dict(),
            pode_operar=pode_operar,
            motivo_bloqueio=motivo_bloqueio,
        )

    # ── Verificar posicao no MT5 ─────────────────────────────────

    @staticmethod
    def _extrair_campo_posicao(pos: Any, campo: str, padrao: Any = None) -> Any:
        """Le campo de posicao suportando dict ou objeto do MT5."""
        if isinstance(pos, dict):
            return pos.get(campo, padrao)
        return getattr(pos, campo, padrao)

    def _normalizar_direcao_posicao(self, pos: Any) -> str:
        """Normaliza direcao da posicao para BUY/SELL."""
        valor_tipo = self._extrair_campo_posicao(pos, "type", "")
        if isinstance(valor_tipo, str):
            tipo_texto = valor_tipo.upper()
            if "BUY" in tipo_texto:
                return "BUY"
            if "SELL" in tipo_texto:
                return "SELL"

        try:
            tipo_int = int(valor_tipo)
            # Convencao MT5: BUY=0, SELL=1
            return "BUY" if tipo_int == 0 else "SELL"
        except Exception:
            return "BUY"

    def _listar_posicoes_abertas_agente_mt5(self) -> list[dict[str, Any]]:
        """Lista posicoes abertas no MT5 apenas do proprio agente (magic)."""
        try:
            from src.domain.value_objects import Symbol

            posicoes = self._mt5.get_positions(Symbol(SIMBOLO))
            abertas: list[dict[str, Any]] = []

            for pos in posicoes:
                magic = self._extrair_campo_posicao(pos, "magic")
                if magic != MAGIC_NUMBER:
                    continue

                ticket = int(self._extrair_campo_posicao(pos, "ticket", 0) or 0)
                preco_entrada = float(
                    self._extrair_campo_posicao(pos, "price_open", 0.0) or 0.0
                )
                preco_atual = float(
                    self._extrair_campo_posicao(pos, "price_current", 0.0) or 0.0
                )
                sl = float(self._extrair_campo_posicao(pos, "sl", 0.0) or 0.0)
                tp = float(self._extrair_campo_posicao(pos, "tp", 0.0) or 0.0)

                abertas.append(
                    {
                        "ticket": ticket,
                        "direcao": self._normalizar_direcao_posicao(pos),
                        "preco_entrada": preco_entrada,
                        "preco_atual": preco_atual,
                        "sl": sl,
                        "tp": tp,
                    }
                )

            return abertas
        except Exception as e:
            logger.error("Erro ao listar posicoes do agente no MT5: %s", e)
            return []

    def _sincronizar_posicao_local_com_mt5(self) -> tuple[bool, str]:
        """Sincroniza estado local com MT5 e aplica trava de multi-posicao.

        Retorna (bloquear_entrada, detalhe).
        """
        posicoes_abertas = self._listar_posicoes_abertas_agente_mt5()
        if not posicoes_abertas:
            return False, ""

        if len(posicoes_abertas) > 1:
            tickets = [str(p["ticket"]) for p in posicoes_abertas]
            detalhe = (
                "multiposicao_detectada_mt5: "
                f"{len(posicoes_abertas)} abertas (tickets={','.join(tickets)})"
            )
            logger.error(
                "Trava de seguranca ativada: %s. Nao abrira novas ordens.",
                detalhe,
            )
            return True, detalhe

        pos_mt5 = posicoes_abertas[0]
        pos_local = self._posicao.posicao
        precisa_sincronizar = (
            (not pos_local.aberta)
            or (pos_local.ticket is None)
            or (int(pos_local.ticket) != int(pos_mt5["ticket"]))
        )
        if precisa_sincronizar:
            preco_referencia = pos_mt5["preco_entrada"] or pos_mt5["preco_atual"]
            self._posicao.registrar_abertura(
                ticket=pos_mt5["ticket"],
                direcao=pos_mt5["direcao"],
                preco_entrada=preco_referencia,
                sl=pos_mt5["sl"],
                tp=pos_mt5["tp"],
                atr_entrada=pos_local.atr_entrada,
            )
            if pos_mt5["preco_atual"] > 0:
                self._posicao.atualizar_preco(pos_mt5["preco_atual"])
            logger.warning(
                "Sincronizacao de posicao aplicada: ticket=%s dir=%s",
                pos_mt5["ticket"],
                pos_mt5["direcao"],
            )

        return False, ""

    def _posicao_existe_no_mt5(self, ticket: int) -> tuple[bool, float]:
        try:
            from src.domain.value_objects import Symbol

            posicoes = self._mt5.get_positions(Symbol(SIMBOLO))
            for pos in posicoes:
                t = getattr(pos, "ticket", None) or (
                    pos.get("ticket") if isinstance(pos, dict) else None
                )
                magic = getattr(pos, "magic", None) or (
                    pos.get("magic") if isinstance(pos, dict) else None
                )
                if t == ticket and magic == MAGIC_NUMBER:
                    preco = getattr(pos, "price_current", 0) or (
                        pos.get("price_current", 0) if isinstance(pos, dict) else 0
                    )
                    return True, float(preco)
            return False, 0.0
        except Exception as e:
            logger.error("Erro ao verificar posicao MT5: %s", e)
            return True, 0.0  # assume aberta em caso de erro

    # ── Deteccao de reversao / exaustao ─────────────────────────

    def _deve_fechar_por_reversao(self, preco_atual: float) -> tuple[bool, str]:
        """
        Fecha posicao se detectar reversao ou exaustao.

        Criterio 1 (reversao rapida): preco reverteu >= 1.2 * ATR_entrada
        desde o ultimo tick registrado.

        Criterio 2 (devolucao de ganho): devolveu >= 60% do ganho maximo
        (so ativa se ganho_max >= 0.8 * ATR_entrada).
        """
        pos = self._posicao.posicao
        if not pos.aberta:
            return False, ""

        atr_ref = pos.atr_entrada if pos.atr_entrada > 0 else float(ATR_MINIMO)
        reversao_limite = atr_ref * REVERSAO_ATR_MULT

        # Criterio 1: reversao absoluta desde ultimo tick
        if pos.direcao == "BUY":
            move_contra = pos.ultimo_preco - preco_atual
        else:
            move_contra = preco_atual - pos.ultimo_preco

        if move_contra >= reversao_limite:
            return True, f"reversao_{move_contra:.0f}pts_lim{reversao_limite:.0f}"

        # Criterio 2: devolucao de ganho maximo
        ganho_minimo_para_ativar = atr_ref * 0.8
        if pos.max_ganho_pts >= ganho_minimo_para_ativar:
            if pos.direcao == "BUY":
                ganho_atual = preco_atual - pos.preco_entrada
            else:
                ganho_atual = pos.preco_entrada - preco_atual

            ganho_devolvido = pos.max_ganho_pts - ganho_atual
            if ganho_devolvido >= pos.max_ganho_pts * REVERSAO_PCT_GANHO:
                return (
                    True,
                    f"devolucao_{ganho_devolvido:.0f}pts_de_{pos.max_ganho_pts:.0f}",
                )

        return False, ""

    # ── Fechar posicao ───────────────────────────────────────────

    def _fechar_posicao(self, motivo: str) -> bool:
        pos = self._posicao.posicao
        if not pos.aberta or pos.ticket is None:
            return False
        try:
            sucesso = self._mt5.close_position_by_ticket(int(pos.ticket))
            if sucesso:
                self._posicao.registrar_fechamento(motivo)
            else:
                logger.warning("Falha ao fechar posicao: ticket=%s", pos.ticket)
            return sucesso
        except Exception as e:
            logger.error("Erro ao fechar posicao: %s", e)
            return False

    # ── Abrir posicao ────────────────────────────────────────────

    def _abrir_posicao(self, sinal: SinalDiario) -> bool:
        try:
            from src.domain.entities.trade import Order
            from src.domain.value_objects import Symbol, Price, Quantity
            from src.domain.enums.trading_enums import OrderSide, OrderType

            side = OrderSide.BUY if sinal.direcao == "BUY" else OrderSide.SELL

            order = Order(
                symbol=Symbol(SIMBOLO),
                side=side,
                quantity=Quantity(VOLUME),
                order_type=OrderType.MARKET,
                stop_loss=Price(sinal.sl),
                take_profit=Price(sinal.tp),
                magic_number=MAGIC_NUMBER,
                execution_method="automated",
            )

            ticket_str = self._mt5.send_order(order)
            if ticket_str:
                ticket = int(ticket_str) if str(ticket_str).isdigit() else 0
                self._posicao.registrar_abertura(
                    ticket=ticket,
                    direcao=sinal.direcao,
                    preco_entrada=sinal.preco_atual,
                    sl=sinal.sl,
                    tp=sinal.tp,
                    atr_entrada=sinal.atr,
                )
                logger.info(
                    "Ordem enviada: dir=%s preco=%.0f SL=%.0f TP=%.0f "
                    "ATR=%.0f conf=%.2f align=%.2f ticket=%s",
                    sinal.direcao,
                    sinal.preco_atual,
                    sinal.sl,
                    sinal.tp,
                    sinal.atr,
                    sinal.confianca,
                    sinal.alinhamento,
                    ticket_str,
                )
                return True
            else:
                logger.warning("MT5 rejeitou a ordem")
                return False
        except Exception as e:
            logger.error("Erro ao abrir posicao: %s", e)
            return False

    # ── Ciclo principal ──────────────────────────────────────────

    def ciclo(
        self,
        decisao: object,
        candles: list,
        guardian_state: object,
        dir_analysis: Optional[dict] = None,
    ) -> dict:
        """
        Executa um ciclo completo (30s).

        1. Consolida sinal proprio
        2. Se posicao aberta: verifica MT5, Guardian, reversao/exaustao
        3. Se sem posicao: avalia entrada autonoma

        Returns dict com status para display na Thread 5.
        """
        self._n_ciclos += 1
        resultado = {
            "ciclo": self._n_ciclos,
            "timestamp": datetime.now().isoformat(),
            "sinal": None,
            "diario_market_features": None,
            "acao": "NENHUMA",
            "posicao_aberta": False,
            "detalhe": "",
        }

        sinal = self.consolidar_sinal(decisao, candles, guardian_state, dir_analysis)
        self._ultimo_sinal = sinal
        resultado["sinal"] = sinal
        resultado["diario_market_features"] = self._publicar_snapshot_intraday(
            sinal,
            candles,
            guardian_state,
        )

        bloquear_entrada, detalhe_bloqueio = self._sincronizar_posicao_local_com_mt5()
        if bloquear_entrada:
            resultado["acao"] = "BLOQUEADO"
            resultado["posicao_aberta"] = True
            resultado["detalhe"] = detalhe_bloqueio
            return resultado

        # ── Posicao aberta: monitorar ──
        if self._posicao.tem_posicao_aberta():
            resultado["posicao_aberta"] = True
            pos = self._posicao.posicao

            existe, preco_atual = self._posicao_existe_no_mt5(pos.ticket or 0)

            if not existe:
                # Registrar episodio: SL/TP atingido pelo MT5
                preco_saida_est = (
                    pos.ultimo_preco if pos.ultimo_preco > 0 else pos.preco_entrada
                )
                self._registrar_episodio(pos, "sl_tp_mt5", preco_saida_est)
                self._posicao.registrar_fechamento("sl_tp_mt5")
                resultado["acao"] = "POSICAO_FECHADA_MT5"
                resultado["detalhe"] = "SL ou TP atingido pelo MT5"
                resultado["posicao_aberta"] = False
                return resultado

            # Guardian kill switch com posicao aberta: fechar imediatamente
            if not sinal.guardian_ok:
                fechou = self._fechar_posicao("guardian_kill_switch")
                if fechou:
                    self._registrar_episodio(pos, "guardian_kill_switch", preco_atual)
                resultado["acao"] = (
                    "FECHAMENTO_GUARDIAN" if fechou else "ERRO_FECHAR_GUARDIAN"
                )
                resultado["detalhe"] = "Guardian ativo"
                resultado["posicao_aberta"] = not fechou
                return resultado

            # Verificar reversao/exaustao ANTES de atualizar ultimo_preco
            if preco_atual > 0:
                deve_fechar, motivo_rev = self._deve_fechar_por_reversao(preco_atual)
                if deve_fechar:
                    fechou = self._fechar_posicao(motivo_rev)
                    if fechou:
                        self._registrar_episodio(pos, motivo_rev, preco_atual)
                    resultado["acao"] = (
                        "FECHAMENTO_REVERSAO" if fechou else "ERRO_FECHAR_REVERSAO"
                    )
                    resultado["detalhe"] = f"Reversao: {motivo_rev}"
                    resultado["posicao_aberta"] = not fechou
                    return resultado

            # Atualizar preco apos verificacoes
            if preco_atual > 0:
                self._posicao.atualizar_preco(preco_atual)

            pos_atual = self._posicao.posicao
            if preco_atual > 0:
                ganho = (
                    (preco_atual - pos_atual.preco_entrada)
                    if pos_atual.direcao == "BUY"
                    else (pos_atual.preco_entrada - preco_atual)
                )
                resultado["detalhe"] = (
                    f"dir={pos_atual.direcao} entrada={pos_atual.preco_entrada:.0f} "
                    f"atual={preco_atual:.0f} ganho={ganho:+.0f}pts "
                    f"max={pos_atual.max_ganho_pts:.0f}pts ATR={pos_atual.atr_entrada:.0f}"
                )
            resultado["acao"] = "MONITORANDO"
            return resultado

        # ── Sem posicao: avaliar entrada ──
        resultado["posicao_aberta"] = False

        if not sinal.pode_operar:
            resultado["acao"] = "BLOQUEADO"
            resultado["detalhe"] = sinal.motivo_bloqueio
            # Registrar episodio neutro a cada ~5 min (10 ciclos de 30s)
            # para aprender se ficar fora foi sabio
            self._registrar_episodio_neutro(sinal, candles)
            return resultado

        abriu = self._abrir_posicao(sinal)
        if abriu:
            self._sinal_abertura = (
                sinal  # guardar para registrar episodio no fechamento
            )
            resultado["acao"] = "ORDEM_ENVIADA"
            resultado["detalhe"] = (
                f"dir={sinal.direcao} preco={sinal.preco_atual:.0f} "
                f"SL={sinal.sl:.0f} TP={sinal.tp:.0f} "
                f"ATR={sinal.atr:.0f} conf={sinal.confianca:.0%} "
                f"align={sinal.alinhamento:.0%} "
                f"vies={sinal.vies_intraday or 'N/D'} "
                f"buy_live={sinal.confirmacao_live.get('buy_confirmed')} "
                f"sell_live={sinal.confirmacao_live.get('sell_quality_confirmed')}"
            )
            resultado["posicao_aberta"] = True
        else:
            resultado["acao"] = "ERRO_ORDEM"
            resultado["detalhe"] = "MT5 rejeitou ou erro interno"

        return resultado

    # ── Aprendizado ──────────────────────────────────────────────────────────

    def _registrar_episodio(
        self, pos: DiarioPosicao, motivo: str, preco_saida: float
    ) -> None:
        """Constroi e persiste episodio apos fechamento de posicao."""
        if self._sinal_abertura is None:
            return
        try:
            ep = construir_episodio(
                pos, motivo, preco_saida, self._sinal_abertura, self._session_id
            )
            self._ep_repo.salvar(ep)
            logger.info(
                "Episodio registrado: ticket=%s motivo=%s resultado=%s",
                pos.ticket,
                motivo,
                ep.resultado,
            )
        except Exception as e:
            logger.error("Erro ao registrar episodio: %s", e)
        finally:
            self._sinal_abertura = None

    def _registrar_episodio_neutro(self, sinal: SinalDiario, candles: list) -> None:
        """
        Registra episodio quando o agente decidiu ficar fora (NEUTRO).

        A cada ~5 min (10 ciclos de 30s), avalia o que teria acontecido
        se tivesse entrado. Isso permite aprender se ficar fora foi
        uma decisao sabia ou se perdeu oportunidade.

        Resultado: compara preco no momento da decisao com preco 10
        ciclos (~5 min) depois. Se o mercado andou na direcao que os
        indicadores sugeriam (macro, momentum), registra como 'perda
        de oportunidade'. Se o mercado ficou lateral ou reverteu,
        registra como 'decisao correta'.
        """
        # Avaliar episodio neutro anterior (se houver)
        if (
            self._candles_no_neutro is not None
            and self._n_ciclos - self._ultimo_neutro_registrado >= 10
        ):
            self._avaliar_episodio_neutro(sinal, candles)

        # Registrar novo snapshot neutro a cada 10 ciclos
        if self._n_ciclos - self._ultimo_neutro_registrado >= 10:
            self._candles_no_neutro = candles[-5:] if candles else None
            self._ultimo_neutro_registrado = self._n_ciclos

    def _avaliar_episodio_neutro(
        self, sinal_atual: SinalDiario, candles_atuais: list
    ) -> None:
        """
        Avalia o que teria acontecido se o agente tivesse operado
        no momento em que decidiu ficar fora.
        """
        if not self._candles_no_neutro or not candles_atuais:
            return

        try:
            preco_decisao = float(self._candles_no_neutro[-1].close.value)
            preco_agora = float(candles_atuais[-1].close.value)
            variacao = preco_agora - preco_decisao

            # Inferir direcao que o mercado sugeria (momentum do sinal)
            direcao_sugerida = "BUY" if sinal_atual.momentum > 0 else "SELL"

            # Se tivesse entrado na direcao do momentum:
            if direcao_sugerida == "BUY":
                resultado_hipotetico = variacao
            else:
                resultado_hipotetico = -variacao

            # Positivo = perdeu oportunidade, Negativo = decisao sábia
            foi_acerto_ficar_fora = resultado_hipotetico <= 0

            ep = construir_episodio_neutro(
                sinal=sinal_atual,
                session_id=self._session_id,
                preco_decisao=preco_decisao,
                preco_avaliacao=preco_agora,
                direcao_sugerida=direcao_sugerida,
                resultado_hipotetico=resultado_hipotetico,
                foi_acerto_ficar_fora=foi_acerto_ficar_fora,
            )
            self._ep_repo.salvar(ep)
            logger.info(
                "Episodio neutro registrado: sugestao=%s var=%.0f "
                "hipotetico=%.0f acerto_fora=%s motivo=%s",
                direcao_sugerida,
                variacao,
                resultado_hipotetico,
                foi_acerto_ficar_fora,
                sinal_atual.motivo_bloqueio,
            )
        except Exception as e:
            logger.error("Erro ao avaliar episodio neutro: %s", e)
        finally:
            self._candles_no_neutro = None
