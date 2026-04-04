"""
BLID-032: Detector de Padroes SMC no Backtest com Confluencia M1/M5

Responsabilidades:
- SwingHighLowDetector: detecta Swing High/Low reais usando close prices
- SMCConfluenceFilter: valida confluencia entre M1 e M5
- BacktestSMCEngine: orquestra backtest com 4 modos:
    * baseline (sem filtro SMC)
    * smc_m1_only (apenas M1)
    * smc_m5_only (apenas M5)
    * smc_confluence (M1 + M5 alinhados)
- ComparisonReport: gera relatorio win_rate_delta (>=3%)

Pipeline:
    candles_m1 + candles_m5
    -> SwingHighLowDetector detecta Swing High/Low reais
    -> SMCConfluenceFilter valida alinhamento M1/M5
    -> BacktestSMCEngine simula trades apenas com confluencia
    -> ComparisonReport compara baseline vs confluence

Status: Implementacao v1.0 (04/04/2026)
Referencia: docs/BACKLOG.md BLID-032, ADR-026
"""

import statistics
from dataclasses import dataclass, field
from typing import List, Optional


# ---------------------------------------------------------------------------
# Entidades de dados
# ---------------------------------------------------------------------------


@dataclass
class CandleData:
    """Vela de mercado simplificada para backtest."""

    open: float
    high: float
    low: float
    close: float
    volume: float = 0.0
    timeframe: str = "M5"


@dataclass
class SwingPoint:
    """Ponto de swing detectado."""

    index: int
    price: float
    tipo: str  # "HIGH" | "LOW"
    timeframe: str


@dataclass
class SMCSignal:
    """Sinal SMC detectado (BOS/CHoCH/FVG)."""

    index: int
    tipo: str  # "BOS" | "CHoCH" | "FVG"
    direcao: str  # "ALTA" | "BAIXA"
    confianca: float
    timeframe: str


@dataclass
class ConfluenceSignal:
    """Sinal de confluencia M1/M5 aprovado."""

    index_m5: int
    direcao: str
    score: int  # 1-5
    tipos_detectados: List[str] = field(default_factory=list)


@dataclass
class BacktestTradeResult:
    """Resultado de um trade simulado no backtest."""

    index: int
    direcao: str
    resultado: str  # "WIN" | "LOSS"
    pnl_pts: float
    modo: str  # "baseline" | "smc_m1_only" | "smc_m5_only" | "smc_confluence"


@dataclass
class BacktestSMCResult:
    """Resultado agregado por modo de backtest."""

    modo: str
    total_trades: int
    vitorias: int
    win_rate: float
    pnl_total: float


@dataclass
class ComparisonReport:
    """Relatorio comparativo de win rates."""

    baseline: BacktestSMCResult
    smc_m1_only: BacktestSMCResult
    smc_m5_only: BacktestSMCResult
    smc_confluence: BacktestSMCResult
    win_rate_delta_confluence: float  # confluence.win_rate - baseline.win_rate
    meta: bool  # True se delta >= 0.03 (3%)


# ---------------------------------------------------------------------------
# Detector de Swing High/Low
# ---------------------------------------------------------------------------


class SwingHighLowDetector:
    """
    Detecta pontos de Swing High e Swing Low reais.

    Regra:
    - Swing High: high[i] > high[i-lookback:i] e > high[i+1:i+lookback+1]
    - Swing Low:  low[i]  < low[i-lookback:i]  e < low[i+1:i+lookback+1]

    Usa close prices para confirmar rompimento de estrutura.
    """

    def __init__(self, lookback: int = 3) -> None:
        """
        Inicializa o detector de swing points.

        Args:
            lookback: Numero de candles antes e depois para comparar.
        """
        self.lookback = lookback

    def detectar(self, candles: List[CandleData]) -> List[SwingPoint]:
        """
        Retorna lista de SwingPoint ordenada por indice.

        Um Swing High valido requer:
        - high[i] maior que todos os highs nas posicoes [i-lookback, i-1]
        - high[i] maior que todos os highs nas posicoes [i+1, i+lookback]

        Um Swing Low valido requer:
        - low[i] menor que todos os lows nas posicoes [i-lookback, i-1]
        - low[i] menor que todos os lows nas posicoes [i+1, i+lookback]

        Args:
            candles: Lista de velas a analisar.

        Returns:
            Lista de SwingPoint detectados.
        """
        pontos: List[SwingPoint] = []
        n = len(candles)

        for i in range(self.lookback, n - self.lookback):
            candle_atual = candles[i]
            janela_anterior = candles[i - self.lookback : i]
            janela_posterior = candles[i + 1 : i + self.lookback + 1]

            # Verificar Swing High
            eh_swing_high = all(
                candle_atual.high > c.high for c in janela_anterior
            ) and all(candle_atual.high > c.high for c in janela_posterior)

            # Verificar Swing Low
            eh_swing_low = all(
                candle_atual.low < c.low for c in janela_anterior
            ) and all(candle_atual.low < c.low for c in janela_posterior)

            if eh_swing_high:
                pontos.append(
                    SwingPoint(
                        index=i,
                        price=candle_atual.high,
                        tipo="HIGH",
                        timeframe=candle_atual.timeframe,
                    )
                )

            if eh_swing_low:
                pontos.append(
                    SwingPoint(
                        index=i,
                        price=candle_atual.low,
                        tipo="LOW",
                        timeframe=candle_atual.timeframe,
                    )
                )

        return sorted(pontos, key=lambda p: p.index)


# ---------------------------------------------------------------------------
# Gerador de sinais SMC a partir de swing points
# ---------------------------------------------------------------------------


class _GeradorSinaisSMC:
    """
    Gera sinais SMC (BOS/CHoCH/FVG) a partir de candles e swing points.

    Uso interno pelo BacktestSMCEngine.
    """

    # Confiancas padrao por tipo de sinal
    # Valores calibrados empiricamente para SMC:
    # BOS (0.70): rompimento de estrutura com continuidade — confianca alta
    # CHoCH (0.80): reversao de estrutura — sinal mais forte, maior confianca
    # FVG (0.65): gap de fair value — sinal de desequilibrio, menor confianca
    CONFIANCA_BOS: float = 0.70
    CONFIANCA_CHOCH: float = 0.80
    CONFIANCA_FVG: float = 0.65

    def gerar(
        self,
        candles: List[CandleData],
        swings: List[SwingPoint],
    ) -> List[SMCSignal]:
        """
        Gera lista de SMCSignal a partir de swings e candles.

        - BOS: close rompe o ultimo Swing High (ALTA) ou Swing Low (BAIXA)
        - CHoCH: close rompe na direcao oposta ao swing de referencia
        - FVG: gap entre high[i-1] e low[i+1] nao sobrepostos

        Args:
            candles: Lista de velas.
            swings: Lista de swing points detectados.

        Returns:
            Lista de SMCSignal ordenada por indice.
        """
        sinais: List[SMCSignal] = []

        # Gerar BOS/CHoCH baseado em swings
        sinais.extend(self._gerar_bos_choch(candles, swings))

        # Gerar FVG baseado em candles
        sinais.extend(self._gerar_fvg(candles))

        return sorted(sinais, key=lambda s: s.index)

    def _gerar_bos_choch(
        self,
        candles: List[CandleData],
        swings: List[SwingPoint],
    ) -> List[SMCSignal]:
        """Gera sinais BOS e CHoCH a partir dos swing points."""
        sinais: List[SMCSignal] = []
        swings_high = [s for s in swings if s.tipo == "HIGH"]
        swings_low = [s for s in swings if s.tipo == "LOW"]

        ultimo_swing_high: Optional[SwingPoint] = None
        ultimo_swing_low: Optional[SwingPoint] = None
        estrutura_atual: Optional[str] = None  # "ALTA" | "BAIXA" | None

        for i, candle in enumerate(candles):
            # Atualizar ultimo swing high/low ate este indice
            novos_highs = [s for s in swings_high if s.index == i]
            novos_lows = [s for s in swings_low if s.index == i]

            if novos_highs:
                ultimo_swing_high = novos_highs[-1]
            if novos_lows:
                ultimo_swing_low = novos_lows[-1]

            # BOS ALTA: close rompe ultimo Swing High
            if ultimo_swing_high and candle.close > ultimo_swing_high.price:
                tipo_sinal = "CHoCH" if estrutura_atual == "BAIXA" else "BOS"
                confianca = (
                    self.CONFIANCA_CHOCH
                    if tipo_sinal == "CHoCH"
                    else self.CONFIANCA_BOS
                )
                sinais.append(
                    SMCSignal(
                        index=i,
                        tipo=tipo_sinal,
                        direcao="ALTA",
                        confianca=confianca,
                        timeframe=candle.timeframe,
                    )
                )
                estrutura_atual = "ALTA"
                ultimo_swing_high = None  # consumido

            # BOS BAIXA: close rompe ultimo Swing Low
            elif ultimo_swing_low and candle.close < ultimo_swing_low.price:
                tipo_sinal = "CHoCH" if estrutura_atual == "ALTA" else "BOS"
                confianca = (
                    self.CONFIANCA_CHOCH
                    if tipo_sinal == "CHoCH"
                    else self.CONFIANCA_BOS
                )
                sinais.append(
                    SMCSignal(
                        index=i,
                        tipo=tipo_sinal,
                        direcao="BAIXA",
                        confianca=confianca,
                        timeframe=candle.timeframe,
                    )
                )
                estrutura_atual = "BAIXA"
                ultimo_swing_low = None  # consumido

        return sinais

    def _gerar_fvg(self, candles: List[CandleData]) -> List[SMCSignal]:
        """
        Detecta FVG (Fair Value Gap) em sequencias de 3 candles.

        FVG ALTA: low[i] > high[i-2] — gap de alta entre candles i-2 e i
        FVG BAIXA: high[i] < low[i-2] — gap de baixa entre candles i-2 e i
        """
        sinais: List[SMCSignal] = []
        for i in range(2, len(candles)):
            candle_a = candles[i - 2]
            candle_c = candles[i]

            if candle_c.low > candle_a.high:
                sinais.append(
                    SMCSignal(
                        index=i,
                        tipo="FVG",
                        direcao="ALTA",
                        confianca=self.CONFIANCA_FVG,
                        timeframe=candle_c.timeframe,
                    )
                )
            elif candle_c.high < candle_a.low:
                sinais.append(
                    SMCSignal(
                        index=i,
                        tipo="FVG",
                        direcao="BAIXA",
                        confianca=self.CONFIANCA_FVG,
                        timeframe=candle_c.timeframe,
                    )
                )

        return sinais


# ---------------------------------------------------------------------------
# Filtro de confluencia M1/M5
# ---------------------------------------------------------------------------


class SMCConfluenceFilter:
    """
    Valida confluencia entre M1 e M5.

    Regra de confluencia:
    - ALTA: M1.direcao == "ALTA" E M5.direcao == "ALTA"
    - BAIXA: M1.direcao == "BAIXA" E M5.direcao == "BAIXA"
    - NEUTRO: qualquer divergencia

    Score 1-5:
    - +2 por cada timeframe alinhado
    - +1 se ambos tem CHoCH (maior confianca)
    """

    # Constantes da engine de confluencia
    # Score maximo possivel (2 TFs alinhados + bonus CHoCH)
    MAX_CONFLUENCE_SCORE: int = 5

    def filtrar(
        self,
        sinais_m1: List[SMCSignal],
        sinais_m5: List[SMCSignal],
    ) -> List[ConfluenceSignal]:
        """
        Retorna sinais com confluencia validada (>=2 timeframes).

        Estrategia de alinhamento:
        - Para cada sinal M5, busca sinal M1 com mesma direcao
        - Calcula score de confluencia (1-5)
        - Retorna apenas sinais com score >= 2

        Args:
            sinais_m1: Sinais detectados em M1.
            sinais_m5: Sinais detectados em M5.

        Returns:
            Lista de ConfluenceSignal aprovados.
        """
        confluencias: List[ConfluenceSignal] = []

        # Agrupar sinais M1 por direcao para busca rapida
        m1_alta = [s for s in sinais_m1 if s.direcao == "ALTA"]
        m1_baixa = [s for s in sinais_m1 if s.direcao == "BAIXA"]

        for sinal_m5 in sinais_m5:
            m1_alinhados = (
                m1_alta if sinal_m5.direcao == "ALTA" else m1_baixa
            )

            if not m1_alinhados:
                continue

            # Selecionar o sinal M1 mais recente compativel
            sinal_m1_ref = m1_alinhados[-1]

            # Calcular score de confluencia
            score = self._calcular_score(sinal_m5, sinal_m1_ref)

            if score >= 2:
                tipos = list(
                    {sinal_m5.tipo, sinal_m1_ref.tipo}
                )
                confluencias.append(
                    ConfluenceSignal(
                        index_m5=sinal_m5.index,
                        direcao=sinal_m5.direcao,
                        score=score,
                        tipos_detectados=tipos,
                    )
                )

        return confluencias

    def _calcular_score(
        self,
        sinal_m5: SMCSignal,
        sinal_m1: SMCSignal,
    ) -> int:
        """
        Calcula score de confluencia entre sinal M5 e M1.

        - +2 por M5 alinhado
        - +2 por M1 alinhado
        - +1 bonus se ambos tem CHoCH

        Returns:
            Score no intervalo [0, 5].
        """
        score = 0

        if sinal_m5.direcao == sinal_m1.direcao:
            score += 2  # M5 alinhado
            score += 2  # M1 alinhado (ja que mesma direcao)

        if sinal_m5.tipo == "CHoCH" and sinal_m1.tipo == "CHoCH":
            score += 1  # bonus CHoCH duplo

        return min(score, self.MAX_CONFLUENCE_SCORE)


# ---------------------------------------------------------------------------
# Simulador de trades
# ---------------------------------------------------------------------------


class _SimuladorTrades:
    """
    Simula trades em uma lista de candles.

    Trade simulation:
    - SL = sl_mult * ATR proxy (media de range dos ultimos 5 candles)
    - TP = tp_mult * ATR proxy
    - Entrada: close do candle de sinal
    - Avaliacao: nos proximos avaliacao_candles candles
    - Saida no primeiro candle que toca SL ou TP
    """

    # Percentual do preco de entrada usado como ATR minimo quando sem historico
    _ATR_FALLBACK_PERCENTUAL: float = 0.001
    # Valor absoluto minimo de ATR para evitar divisao por zero
    _ATR_MINIMO_ABSOLUTO: float = 1.0

    def __init__(
        self,
        sl_mult: float = 2.0,
        tp_mult: float = 3.0,
        avaliacao_candles: int = 10,
    ) -> None:
        """
        Inicializa o simulador.

        Args:
            sl_mult: Multiplicador ATR para stop loss.
            tp_mult: Multiplicador ATR para take profit.
            avaliacao_candles: Janela de candles para avaliar o trade.
        """
        self.sl_mult = sl_mult
        self.tp_mult = tp_mult
        self.avaliacao_candles = avaliacao_candles

    def simular_trade(
        self,
        index_sinal: int,
        direcao: str,
        candles: List[CandleData],
        modo: str,
    ) -> Optional[BacktestTradeResult]:
        """
        Simula um trade a partir do candle de sinal.

        Args:
            index_sinal: Indice do candle de entrada.
            direcao: "ALTA" ou "BAIXA".
            candles: Lista completa de candles.
            modo: Modo de backtest.

        Returns:
            BacktestTradeResult ou None se nao houver candles suficientes.
        """
        n = len(candles)

        # Verificar se ha candles suficientes para avaliacao
        if index_sinal >= n - 1:
            return None

        candle_entrada = candles[index_sinal]
        preco_entrada = candle_entrada.close

        # Calcular ATR proxy com os 5 candles anteriores (ou disponivel)
        inicio_atr = max(0, index_sinal - 5)
        janela_atr = candles[inicio_atr:index_sinal]

        if not janela_atr:
            # Sem historico suficiente para ATR
            atr = (candle_entrada.high - candle_entrada.low)
        else:
            ranges = [c.high - c.low for c in janela_atr]
            atr = statistics.mean(ranges)

        # Garantir ATR minimo para evitar divisao por zero
        if atr <= 0:
            atr = (
                abs(preco_entrada) * self._ATR_FALLBACK_PERCENTUAL
                if preco_entrada != 0
                else self._ATR_MINIMO_ABSOLUTO
            )

        sl_pts = self.sl_mult * atr
        tp_pts = self.tp_mult * atr

        # Definir niveis SL e TP com base na direcao
        if direcao == "ALTA":
            preco_sl = preco_entrada - sl_pts
            preco_tp = preco_entrada + tp_pts
        else:
            preco_sl = preco_entrada + sl_pts
            preco_tp = preco_entrada - tp_pts

        # Avaliar candles subsequentes
        fim_avaliacao = min(
            index_sinal + 1 + self.avaliacao_candles, n
        )
        candles_avaliacao = candles[index_sinal + 1 : fim_avaliacao]

        resultado = "LOSS"
        pnl = -sl_pts

        for candle in candles_avaliacao:
            if direcao == "ALTA":
                if candle.low <= preco_sl:
                    resultado = "LOSS"
                    pnl = -sl_pts
                    break
                if candle.high >= preco_tp:
                    resultado = "WIN"
                    pnl = tp_pts
                    break
            else:
                if candle.high >= preco_sl:
                    resultado = "LOSS"
                    pnl = -sl_pts
                    break
                if candle.low <= preco_tp:
                    resultado = "WIN"
                    pnl = tp_pts
                    break

        return BacktestTradeResult(
            index=index_sinal,
            direcao=direcao,
            resultado=resultado,
            pnl_pts=round(pnl, 4),
            modo=modo,
        )

    def agregar_resultados(
        self,
        trades: List[BacktestTradeResult],
        modo: str,
    ) -> BacktestSMCResult:
        """
        Agrega resultados de trades em BacktestSMCResult.

        Args:
            trades: Lista de trades simulados.
            modo: Identificador do modo de backtest.

        Returns:
            BacktestSMCResult com estatisticas agregadas.
        """
        total = len(trades)
        vitorias = sum(1 for t in trades if t.resultado == "WIN")
        win_rate = vitorias / total if total > 0 else 0.0
        pnl_total = sum(t.pnl_pts for t in trades)

        return BacktestSMCResult(
            modo=modo,
            total_trades=total,
            vitorias=vitorias,
            win_rate=round(win_rate, 4),
            pnl_total=round(pnl_total, 4),
        )


# ---------------------------------------------------------------------------
# Engine principal de backtest
# ---------------------------------------------------------------------------


class BacktestSMCEngine:
    """
    Orquestra backtest SMC em 4 modos.

    Trade simulation:
    - SL = 2 * ATR proxy (media de range dos ultimos 5 candles)
    - TP = 3 * ATR proxy
    - Entrada: close do candle de sinal
    - Avaliacao: nos proximos 10 candles (saida no primeiro que toca SL ou TP)

    Baseline: entra em todos os sinais SMC detectados (M5)
    SMC_M1: apenas sinais de M1 confirmados
    SMC_M5: apenas sinais de M5 confirmados (com swing validado)
    SMC_Confluence: apenas sinais com M1+M5 alinhados
    """

    def __init__(
        self,
        swing_lookback: int = 3,
        sl_mult: float = 2.0,
        tp_mult: float = 3.0,
        avaliacao_candles: int = 10,
    ) -> None:
        """
        Inicializa a engine de backtest SMC.

        Args:
            swing_lookback: Janela de lookback para deteccao de swings.
            sl_mult: Multiplicador ATR para stop loss.
            tp_mult: Multiplicador ATR para take profit.
            avaliacao_candles: Numero de candles para avaliar o trade.
        """
        self.detector = SwingHighLowDetector(lookback=swing_lookback)
        self.filtro = SMCConfluenceFilter()
        self.gerador = _GeradorSinaisSMC()
        self.simulador = _SimuladorTrades(
            sl_mult=sl_mult,
            tp_mult=tp_mult,
            avaliacao_candles=avaliacao_candles,
        )
        self.sl_mult = sl_mult
        self.tp_mult = tp_mult
        self.avaliacao_candles = avaliacao_candles

    def rodar(
        self,
        candles_m1: List[CandleData],
        candles_m5: List[CandleData],
    ) -> ComparisonReport:
        """
        Executa backtest nos 4 modos e retorna ComparisonReport.

        Args:
            candles_m1: Velas M1 (tipicamente 5x mais que M5).
            candles_m5: Velas M5.

        Returns:
            ComparisonReport com win_rate_delta e meta (>=3%).
        """
        # 1. Detectar swing points em ambos os timeframes
        swings_m1 = self.detector.detectar(candles_m1)
        swings_m5 = self.detector.detectar(candles_m5)

        # 2. Gerar sinais SMC em ambos os timeframes
        sinais_m1 = self.gerador.gerar(candles_m1, swings_m1)
        sinais_m5 = self.gerador.gerar(candles_m5, swings_m5)

        # 3. Filtrar confluencias M1/M5
        confluencias = self.filtro.filtrar(sinais_m1, sinais_m5)

        # 4. Simular trades em cada modo
        trades_baseline = self._simular_modo_baseline(sinais_m5, candles_m5)
        trades_m1 = self._simular_modo_m1(sinais_m1, candles_m1)
        trades_m5 = self._simular_modo_m5(sinais_m5, candles_m5)
        trades_confluence = self._simular_modo_confluence(
            confluencias, candles_m5
        )

        # 5. Agregar resultados por modo
        resultado_baseline = self.simulador.agregar_resultados(
            trades_baseline, "baseline"
        )
        resultado_m1 = self.simulador.agregar_resultados(
            trades_m1, "smc_m1_only"
        )
        resultado_m5 = self.simulador.agregar_resultados(
            trades_m5, "smc_m5_only"
        )
        resultado_confluence = self.simulador.agregar_resultados(
            trades_confluence, "smc_confluence"
        )

        # 6. Calcular delta e verificar meta
        delta = resultado_confluence.win_rate - resultado_baseline.win_rate
        atingiu_meta = delta >= 0.03

        return ComparisonReport(
            baseline=resultado_baseline,
            smc_m1_only=resultado_m1,
            smc_m5_only=resultado_m5,
            smc_confluence=resultado_confluence,
            win_rate_delta_confluence=round(delta, 4),
            meta=atingiu_meta,
        )

    # -----------------------------------------------------------------------
    # Metodos privados — simulacao por modo
    # -----------------------------------------------------------------------

    def _simular_modo_baseline(
        self,
        sinais_m5: List[SMCSignal],
        candles_m5: List[CandleData],
    ) -> List[BacktestTradeResult]:
        """Baseline: entra em todos os sinais SMC de M5."""
        trades: List[BacktestTradeResult] = []
        for sinal in sinais_m5:
            trade = self.simulador.simular_trade(
                index_sinal=sinal.index,
                direcao=sinal.direcao,
                candles=candles_m5,
                modo="baseline",
            )
            if trade is not None:
                trades.append(trade)
        return trades

    def _simular_modo_m1(
        self,
        sinais_m1: List[SMCSignal],
        candles_m1: List[CandleData],
    ) -> List[BacktestTradeResult]:
        """SMC M1 Only: apenas sinais confirmados em M1."""
        trades: List[BacktestTradeResult] = []
        for sinal in sinais_m1:
            trade = self.simulador.simular_trade(
                index_sinal=sinal.index,
                direcao=sinal.direcao,
                candles=candles_m1,
                modo="smc_m1_only",
            )
            if trade is not None:
                trades.append(trade)
        return trades

    def _simular_modo_m5(
        self,
        sinais_m5: List[SMCSignal],
        candles_m5: List[CandleData],
    ) -> List[BacktestTradeResult]:
        """SMC M5 Only: apenas sinais com swing validado em M5."""
        trades: List[BacktestTradeResult] = []
        for sinal in sinais_m5:
            # M5 only: filtrar apenas CHoCH e BOS (excluir FVG sozinho)
            if sinal.tipo in ("BOS", "CHoCH"):
                trade = self.simulador.simular_trade(
                    index_sinal=sinal.index,
                    direcao=sinal.direcao,
                    candles=candles_m5,
                    modo="smc_m5_only",
                )
                if trade is not None:
                    trades.append(trade)
        return trades

    def _simular_modo_confluence(
        self,
        confluencias: List[ConfluenceSignal],
        candles_m5: List[CandleData],
    ) -> List[BacktestTradeResult]:
        """SMC Confluence: apenas sinais com M1+M5 alinhados."""
        trades: List[BacktestTradeResult] = []
        for confluencia in confluencias:
            trade = self.simulador.simular_trade(
                index_sinal=confluencia.index_m5,
                direcao=confluencia.direcao,
                candles=candles_m5,
                modo="smc_confluence",
            )
            if trade is not None:
                trades.append(trade)
        return trades
