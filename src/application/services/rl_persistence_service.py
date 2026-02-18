"""Serviço de persistência para Aprendizagem por Reforço.

Converte análises e decisões dos motores (QuantumOperator, MicroAgente)
em episódios RL estruturados e persiste no banco de dados colunar.

Responsabilidades:
    1. Converter TradingDecision + MarketContext → episódio RL
    2. Converter CycleResult do micro agente → episódio RL
    3. Extrair indicadores técnicos e scores de correlação
    4. Criar recompensas pendentes para avaliação futura
    5. Avaliar recompensas quando o horizonte expira
"""

import logging
import uuid
from datetime import datetime
from decimal import Decimal
from typing import Optional

from src.infrastructure.repositories.rl_repository import (
    IRLRepository,
    SqliteRLRepository,
)

logger = logging.getLogger(__name__)


class RLPersistenceService:
    """Serviço de persistência para dados de Reinforcement Learning.

    Intercepta decisões do QuantumOperator e MicroAgente e persiste
    todos os dados necessários para treinamento RL:
    - Vetor de estado completo (scores + cotações + indicadores)
    - Ação tomada
    - Recompensa multi-horizonte (preenchida depois)
    """

    def __init__(self, rl_repository: IRLRepository) -> None:
        self.repo = rl_repository
        self._initialized = False

    def initialize(self) -> None:
        """Inicializa tabelas de dimensão se necessário."""
        if not self._initialized:
            try:
                self.repo.seed_dimension_tables()
                self._initialized = True
                logger.info("[RL] Tabelas de dimensão inicializadas.")
            except Exception as e:
                logger.warning(f"[RL] Erro ao inicializar dimensões: {e}")

    # ================================================================
    # QUANTUM OPERATOR → Episódio RL
    # ================================================================

    def persist_quantum_decision(
        self,
        decision,  # TradingDecision
        context=None,  # MarketContext
        macro_score_result=None,  # MacroScoreResult (85 itens)
        technical=None,  # TechnicalAnalysis
        sentiment=None,  # SentimentAnalysis
    ) -> Optional[str]:
        """Persiste uma decisão do QuantumOperator como episódio RL.

        Args:
            decision: TradingDecision do QuantumOperator
            context: MarketContext com análises completas
            macro_score_result: Resultado do MacroScoreEngine (85 itens)
            technical: Análise técnica completa
            sentiment: Análise de sentimento

        Returns:
            episode_id gerado, ou None se falhar
        """
        try:
            episode_id = str(uuid.uuid4())
            now = decision.timestamp
            session_date = now.strftime("%Y-%m-%d")

            # ---- Montar episódio ----
            episode = {
                "episode_id": episode_id,
                "timestamp": now,
                "source": "QUANTUM",
                "action": decision.action.value if hasattr(decision.action, "value") else str(decision.action),
                "urgency": decision.urgency,
                "risk_level": decision.risk_level,
                "session_date": session_date,
                # Biases
                "macro_bias": decision.macro_bias,
                "fundamental_bias": decision.fundamental_bias,
                "sentiment_bias": decision.sentiment_bias,
                "technical_bias": decision.technical_bias,
                # Alinhamento
                "alignment_score": float(decision.alignment_score) if decision.alignment_score else None,
                "overall_confidence": float(decision.confidence) if decision.confidence else None,
                # Regime
                "market_regime": decision.market_regime,
                # Reasoning
                "reasoning": decision.executive_summary if hasattr(decision, "executive_summary") else None,
            }

            # Setup de entrada
            if decision.recommended_entry:
                entry = decision.recommended_entry
                episode["entry_price"] = entry.entry_price
                episode["stop_loss"] = entry.stop_loss
                episode["take_profit"] = entry.take_profit
                episode["risk_reward_ratio"] = float(entry.risk_reward_ratio) if entry.risk_reward_ratio else None
                episode["setup_type"] = entry.setup_type if hasattr(entry, "setup_type") else None
                episode["setup_quality"] = entry.setup_quality.value if hasattr(entry, "setup_quality") and hasattr(entry.setup_quality, "value") else None

            # Macro Score (85 itens)
            if macro_score_result:
                episode["macro_score_final"] = macro_score_result.score_final
                episode["macro_score_bullish"] = macro_score_result.score_bullish
                episode["macro_score_bearish"] = macro_score_result.score_bearish
                episode["macro_score_neutral"] = macro_score_result.score_neutral
                episode["macro_items_available"] = macro_score_result.items_available
                episode["macro_confidence"] = float(macro_score_result.confidence) if macro_score_result.confidence else None
                episode["win_price"] = macro_score_result.win_price

            # Sentimento
            if sentiment:
                episode["win_price"] = episode.get("win_price") or sentiment.current_price
                episode["win_open_price"] = sentiment.opening_price
                episode["win_high_of_day"] = sentiment.high_of_day
                episode["win_low_of_day"] = sentiment.low_of_day
                episode["win_price_change_pct"] = float(sentiment.price_change_percent) if sentiment.price_change_percent else None
                episode["sentiment_intraday"] = sentiment.intraday_sentiment.value if hasattr(sentiment.intraday_sentiment, "value") else str(sentiment.intraday_sentiment)
                episode["sentiment_momentum"] = sentiment.momentum
                episode["sentiment_volatility"] = sentiment.volatility
                episode["probability_up"] = float(sentiment.probability_up)
                episode["probability_down"] = float(sentiment.probability_down)
                episode["probability_neutral"] = float(sentiment.probability_neutral)
                episode["recommended_approach"] = sentiment.recommended_approach
                episode["market_condition"] = sentiment.market_condition.value if hasattr(sentiment.market_condition, "value") else str(sentiment.market_condition)
                episode["session_phase"] = sentiment.session_phase.value if hasattr(sentiment.session_phase, "value") else str(sentiment.session_phase)

            # Técnica
            if technical:
                episode["technical_bias"] = technical.technical_bias

            # Salvar episódio
            self.repo.save_episode(episode)

            # ---- Correlações (85 itens) ----
            if macro_score_result and hasattr(macro_score_result, "items"):
                self._persist_macro_correlation_scores(episode_id, now, macro_score_result.items)

            # ---- Indicadores técnicos ----
            if technical:
                self._persist_technical_indicators(episode_id, now, technical)

            # ---- Recompensas pendentes ----
            win_price = episode.get("win_price")
            if win_price:
                self.repo.create_pending_rewards(
                    episode_id,
                    {
                        "timestamp": now,
                        "win_price": win_price,
                        "action": episode["action"],
                    },
                )

            logger.info(
                f"[RL] Episódio QUANTUM persistido: {episode_id[:8]}... "
                f"ação={episode['action']} conf={episode.get('overall_confidence', '?')}"
            )
            return episode_id

        except Exception as e:
            logger.error(f"[RL] Erro ao persistir decisão quantum: {e}")
            return None

    # ================================================================
    # MICRO AGENTE → Episódio RL
    # ================================================================

    def persist_micro_cycle(
        self,
        cycle_result,  # CycleResult do agente micro tendência
    ) -> Optional[str]:
        """Persiste um ciclo do agente micro tendência como episódio RL.

        Args:
            cycle_result: CycleResult do agente_micro_tendencia_winfut

        Returns:
            episode_id gerado, ou None se falhar
        """
        try:
            episode_id = str(uuid.uuid4())
            now = cycle_result.timestamp
            session_date = now.strftime("%Y-%m-%d")

            # Determinar ação baseado no macro_signal + micro_score
            action = self._derive_action_from_micro(cycle_result)

            episode = {
                "episode_id": episode_id,
                "timestamp": now,
                "source": "MICRO_AGENT",
                "session_date": session_date,
                # Preços
                "win_price": cycle_result.price_current,
                "win_open_price": cycle_result.price_open,
                # Macro
                "macro_score_final": Decimal(str(cycle_result.macro_score)),
                "macro_confidence": float(cycle_result.macro_confidence),
                # Micro
                "micro_score": cycle_result.micro_score,
                "micro_trend": cycle_result.micro_trend,
                # VWAP
                "vwap_value": cycle_result.vwap.vwap if cycle_result.vwap else None,
                "vwap_upper_1sigma": cycle_result.vwap.upper_1 if cycle_result.vwap else None,
                "vwap_lower_1sigma": cycle_result.vwap.lower_1 if cycle_result.vwap else None,
                "vwap_upper_2sigma": cycle_result.vwap.upper_2 if cycle_result.vwap else None,
                "vwap_lower_2sigma": cycle_result.vwap.lower_2 if cycle_result.vwap else None,
                "vwap_position": self._calc_vwap_position(cycle_result),
                # Pivots
                "pivot_pp": cycle_result.pivots.pp if cycle_result.pivots else None,
                "pivot_r1": cycle_result.pivots.r1 if cycle_result.pivots else None,
                "pivot_r2": cycle_result.pivots.r2 if cycle_result.pivots else None,
                "pivot_r3": cycle_result.pivots.r3 if cycle_result.pivots else None,
                "pivot_s1": cycle_result.pivots.s1 if cycle_result.pivots else None,
                "pivot_s2": cycle_result.pivots.s2 if cycle_result.pivots else None,
                "pivot_s3": cycle_result.pivots.s3 if cycle_result.pivots else None,
                # SMC
                "smc_direction": cycle_result.smc.direction if cycle_result.smc else None,
                "smc_bos_score": cycle_result.smc.bos_score if cycle_result.smc else None,
                "smc_equilibrium": cycle_result.smc.equilibrium if cycle_result.smc else None,
                "smc_equilibrium_score": cycle_result.smc.equilibrium_score if cycle_result.smc else None,
                "smc_fvg_score": cycle_result.smc.fvg_score if cycle_result.smc else None,
                # Volume
                "volume_score": cycle_result.volume_score,
                "obv_score": cycle_result.obv_score,
                # Agressão
                "aggression_score": cycle_result.aggression_score if hasattr(cycle_result, "aggression_score") else None,
                "aggression_ratio": float(cycle_result.aggression_ratio) if hasattr(cycle_result, "aggression_ratio") else None,
                # Candle patterns
                "candle_pattern_score": cycle_result.candle_pattern_score,
                # Ação derivada
                "action": action,
                "macro_bias": _signal_to_bias(cycle_result.macro_signal),
                # Reasoning com contexto do diary feedback
                "reasoning": self._build_micro_reasoning(cycle_result, action),
            }

            self.repo.save_episode(episode)

            # ---- Correlações macro (19 itens do micro) ----
            if cycle_result.macro_items:
                self._persist_micro_macro_items(episode_id, now, cycle_result.macro_items)

            # ---- Indicadores momentum ----
            if cycle_result.momentum:
                self._persist_momentum_indicators(episode_id, now, cycle_result.momentum)

            # ---- Recompensas pendentes ----
            if cycle_result.price_current:
                self.repo.create_pending_rewards(
                    episode_id,
                    {
                        "timestamp": now,
                        "win_price": cycle_result.price_current,
                        "action": action,
                    },
                )

            logger.info(
                f"[RL] Episódio MICRO persistido: {episode_id[:8]}... "
                f"macro={cycle_result.macro_score} micro={cycle_result.micro_score} "
                f"trend={cycle_result.micro_trend}"
            )
            return episode_id

        except Exception as e:
            logger.error(f"[RL] Erro ao persistir ciclo micro: {e}")
            return None

    # ================================================================
    # AVALIAÇÃO DE RECOMPENSAS
    # ================================================================

    def evaluate_pending_rewards(
        self,
        get_current_price_fn,  # Callable que retorna preço atual do WIN
        get_price_range_fn=None,  # Callable(start, end) → (max, min)
    ) -> int:
        """Avalia recompensas pendentes para todos os horizontes.

        Deve ser chamado periodicamente (ex: a cada ciclo de análise).

        Args:
            get_current_price_fn: Função que retorna preço atual WIN
            get_price_range_fn: Função que retorna (max, min) num intervalo

        Returns:
            Número de recompensas avaliadas
        """
        total_evaluated = 0

        for horizon in self.repo.REWARD_HORIZONS:
            pending = self.repo.get_pending_rewards(horizon)

            for reward_data in pending:
                try:
                    current_price = get_current_price_fn()
                    if current_price is None:
                        continue

                    decision_price = Decimal(str(reward_data["win_price_at_decision"]))
                    current_price = Decimal(str(current_price))
                    action = reward_data["action_at_decision"]

                    # Variação em pontos
                    price_change = current_price - decision_price
                    price_change_pct = float(price_change / decision_price * 100) if decision_price else 0

                    # Direção real
                    if price_change > 0:
                        direction = "UP"
                    elif price_change < 0:
                        direction = "DOWN"
                    else:
                        direction = "FLAT"

                    # Acertou?
                    # HOLD tolerante: mercado precisa mover > 100 pts para considerar
                    # que o HOLD "errou" — lateralizações pequenas são HOLD correto.
                    HOLD_TOLERANCE_PTS = Decimal("100")  # pts abaixo disso = mercado lateral
                    was_correct = 0
                    if action == "BUY" and direction == "UP":
                        was_correct = 1
                    elif action == "SELL" and direction == "DOWN":
                        was_correct = 1
                    elif action == "HOLD":
                        # HOLD é correto se o mercado não moveu significativamente
                        if abs(price_change) <= HOLD_TOLERANCE_PTS:
                            was_correct = 1  # Mercado lateral — HOLD correto
                        # Não penalizar HOLD por movimentos pequenos

                    # Reward normalizado: pontos na direção da ação
                    if action == "BUY":
                        reward_continuous = float(price_change)
                    elif action == "SELL":
                        reward_continuous = float(-price_change)
                    else:  # HOLD
                        # HOLD neutro: só penaliza se o mercado moveu muito (>100 pts)
                        # Penalidade proporcional ao excesso além da tolerância
                        excess = abs(float(price_change)) - float(HOLD_TOLERANCE_PTS)
                        if excess > 0:
                            reward_continuous = -excess  # Penaliza apenas o excesso
                        else:
                            reward_continuous = 0.0  # Mercado lateral — HOLD neutro, sem penalidade

                    # Normalization: clip entre -1 e +1 baseado em ATR típico (~200 pontos)
                    atr_reference = 200.0
                    reward_normalized = max(-1.0, min(1.0, reward_continuous / atr_reference))

                    # MFE / MAE / Volatility
                    mfe = None
                    mae = None
                    volatility = None
                    if get_price_range_fn:
                        try:
                            max_price, min_price = get_price_range_fn(
                                reward_data["timestamp_decision"],
                                datetime.now(),
                            )
                            if max_price is not None and min_price is not None:
                                max_price = Decimal(str(max_price))
                                min_price = Decimal(str(min_price))
                                if action == "BUY":
                                    mfe = float(max_price - decision_price)
                                    mae = float(decision_price - min_price)
                                elif action == "SELL":
                                    mfe = float(decision_price - min_price)
                                    mae = float(max_price - decision_price)
                                elif action == "HOLD":
                                    # Para HOLD, MFE/MAE = range total
                                    mfe = float(max_price - decision_price)
                                    mae = float(decision_price - min_price)
                                # Volatilidade = range máx-mín no horizonte (em pontos)
                                volatility = float(max_price - min_price)
                        except Exception as e:
                            logger.debug(f"[RL] Erro ao calcular MFE/MAE: {e}")

                    evaluation = {
                        "evaluated_at": datetime.now(),
                        "win_price_at_evaluation": current_price,
                        "price_change_points": price_change,
                        "price_change_pct": price_change_pct,
                        "reward_direction": direction,
                        "was_correct": was_correct,
                        "reward_normalized": reward_normalized,
                        "reward_continuous": reward_continuous,
                        "max_favorable_points": mfe,
                        "max_adverse_points": mae,
                        "volatility_in_horizon": volatility,
                    }

                    self.repo.evaluate_reward(
                        reward_data["episode_id"],
                        horizon,
                        evaluation,
                    )
                    total_evaluated += 1

                except Exception as e:
                    logger.error(
                        f"[RL] Erro ao avaliar reward {reward_data['episode_id'][:8]} "
                        f"h={horizon}: {e}"
                    )

        if total_evaluated > 0:
            logger.info(f"[RL] {total_evaluated} recompensas avaliadas.")

        return total_evaluated

    # ================================================================
    # HELPERS PRIVADOS
    # ================================================================

    def _persist_macro_correlation_scores(
        self, episode_id: str, timestamp: datetime, items: list
    ) -> None:
        """Persiste scores de correlação dos 85 itens macro."""
        scores = []
        for item in items:
            # Calcular variação %
            price_change_pct = None
            if hasattr(item, "opening_price") and hasattr(item, "current_price"):
                if item.opening_price and item.current_price and item.opening_price > 0:
                    price_change_pct = float(
                        (item.current_price - item.opening_price) / item.opening_price * 100
                    )

            scores.append({
                "timestamp": timestamp,
                "item_number": item.item_number,
                "symbol": item.symbol,
                "category": item.category.value if hasattr(item.category, "value") else str(item.category),
                "correlation_type": item.correlation.value if hasattr(item.correlation, "value") else str(item.correlation),
                "opening_price": item.opening_price if hasattr(item, "opening_price") else None,
                "current_price": item.current_price if hasattr(item, "current_price") else None,
                "price_change_pct": price_change_pct,
                "raw_score": item.raw_score if hasattr(item, "raw_score") else item.final_score,
                "final_score": item.final_score,
                "weight": item.weight,
                "weighted_score": item.weighted_score,
                "is_available": 1 if item.available else 0,
                "resolved_symbol": item.resolved_symbol if hasattr(item, "resolved_symbol") else None,
            })

        if scores:
            self.repo.save_correlation_scores(episode_id, scores)

    def _persist_micro_macro_items(
        self, episode_id: str, timestamp: datetime, items: list
    ) -> None:
        """Persiste items macro do micro agente como correlações."""
        scores = []
        for item in items:
            price_change_pct = None
            if hasattr(item, "price_open") and hasattr(item, "price_current"):
                if item.price_open and item.price_current and item.price_open > 0:
                    price_change_pct = float(
                        (item.price_current - item.price_open) / item.price_open * 100
                    )

            scores.append({
                "timestamp": timestamp,
                "item_number": item.number if hasattr(item, "number") else item.item_number,
                "symbol": item.symbol,
                "category": item.category,
                "correlation_type": item.correlation,
                "opening_price": item.price_open if hasattr(item, "price_open") else None,
                "current_price": item.price_current if hasattr(item, "price_current") else None,
                "price_change_pct": price_change_pct,
                "raw_score": item.score if hasattr(item, "score") else 0,
                "final_score": item.score if hasattr(item, "score") else 0,
                "weight": Decimal("1.0"),
                "weighted_score": Decimal(str(item.score)) if hasattr(item, "score") else Decimal("0"),
                "is_available": 1 if (hasattr(item, "available") and item.available) or (hasattr(item, "price_current") and item.price_current) else 0,
            })

        if scores:
            self.repo.save_correlation_scores(episode_id, scores)

    def _persist_technical_indicators(
        self, episode_id: str, timestamp: datetime, technical
    ) -> None:
        """Extrai e persiste indicadores técnicos da análise."""
        indicators = []

        if hasattr(technical, "indicators") and technical.indicators:
            ind = technical.indicators
            tf = "M5"  # timeframe padrão do quantum

            indicator_map = [
                ("RSI_14", "rsi_14", None, None),
                ("MACD_12_26_9", "macd", "macd_signal", "macd_histogram"),
                ("ADX_14", "adx", None, None),
                ("EMA_9", "ema_9", None, None),
                ("EMA_21", "ema_21", None, None),
                ("SMA_20", "sma_20", None, None),
                ("SMA_50", "sma_50", None, None),
                ("BB_UPPER", "bb_upper", None, None),
                ("BB_MIDDLE", "bb_middle", None, None),
                ("BB_LOWER", "bb_lower", None, None),
                ("ATR_14", "atr_14", None, None),
            ]

            for code, primary_attr, secondary_attr, tertiary_attr in indicator_map:
                val = getattr(ind, primary_attr, None)
                if val is not None:
                    signal = self._derive_indicator_signal(code, val, ind)
                    score = self._derive_indicator_score(code, val, ind)

                    indicators.append({
                        "timestamp": timestamp,
                        "indicator_code": code,
                        "timeframe": tf,
                        "value": float(val) if val else None,
                        "value_secondary": float(getattr(ind, secondary_attr, None)) if secondary_attr and getattr(ind, secondary_attr, None) else None,
                        "value_tertiary": float(getattr(ind, tertiary_attr, None)) if tertiary_attr and getattr(ind, tertiary_attr, None) else None,
                        "score": score,
                        "signal": signal,
                    })

        if indicators:
            self.repo.save_indicator_values(episode_id, indicators)

    def _persist_momentum_indicators(
        self, episode_id: str, timestamp: datetime, momentum
    ) -> None:
        """Persiste indicadores momentum do micro agente."""
        indicators = []
        tf = "M5"

        if hasattr(momentum, "rsi"):
            indicators.append({
                "timestamp": timestamp,
                "indicator_code": "RSI_14",
                "timeframe": tf,
                "value": float(momentum.rsi) if momentum.rsi else None,
                "score": momentum.rsi_score if hasattr(momentum, "rsi_score") else None,
                "signal": self._rsi_signal(momentum.rsi),
            })

        if hasattr(momentum, "stoch_k"):
            indicators.append({
                "timestamp": timestamp,
                "indicator_code": "STOCH_14",
                "timeframe": tf,
                "value": float(momentum.stoch_k) if momentum.stoch_k else None,
                "value_secondary": float(momentum.stoch_d) if hasattr(momentum, "stoch_d") and momentum.stoch_d else None,
                "score": momentum.stoch_score if hasattr(momentum, "stoch_score") else None,
                "signal": self._stoch_signal(momentum.stoch_k),
            })

        if hasattr(momentum, "macd"):
            indicators.append({
                "timestamp": timestamp,
                "indicator_code": "MACD_12_26_9",
                "timeframe": tf,
                "value": float(momentum.macd) if momentum.macd else None,
                "value_secondary": float(momentum.macd_signal) if hasattr(momentum, "macd_signal") and momentum.macd_signal else None,
                "score": momentum.macd_score if hasattr(momentum, "macd_score") else None,
            })

        if hasattr(momentum, "adx"):
            indicators.append({
                "timestamp": timestamp,
                "indicator_code": "ADX_14",
                "timeframe": tf,
                "value": float(momentum.adx) if momentum.adx else None,
                "score": momentum.adx_score if hasattr(momentum, "adx_score") else None,
            })

        if hasattr(momentum, "bb_position"):
            indicators.append({
                "timestamp": timestamp,
                "indicator_code": "BB_POSITION",
                "timeframe": tf,
                "value": None,
                "score": momentum.bb_score if hasattr(momentum, "bb_score") else None,
                "signal": momentum.bb_position,
            })

        if hasattr(momentum, "ema9_distance_pct"):
            indicators.append({
                "timestamp": timestamp,
                "indicator_code": "EMA_9",
                "timeframe": tf,
                "value": float(momentum.ema9_distance_pct) if momentum.ema9_distance_pct else None,
                "score": momentum.ema9_score if hasattr(momentum, "ema9_score") else None,
            })

        if indicators:
            self.repo.save_indicator_values(episode_id, indicators)

    def _build_micro_reasoning(self, cycle_result, action: str) -> Optional[str]:
        """Constrói reasoning com contexto de diary feedback se ativo."""
        parts = []
        # FIX 12/02/2026: Incluir score bruto vs suavizado e status guardian
        raw_score = getattr(cycle_result, '_raw_macro_score', cycle_result.macro_score)
        if raw_score != cycle_result.macro_score:
            parts.append(f"macro={cycle_result.macro_score}(raw={raw_score})")
        else:
            parts.append(f"macro={cycle_result.macro_score}")
        parts.append(f"micro={cycle_result.micro_score}")
        parts.append(f"trend={cycle_result.micro_trend}")
        if cycle_result.smc:
            parts.append(f"smc={cycle_result.smc.equilibrium}")
        if cycle_result.momentum:
            parts.append(f"adx={cycle_result.momentum.adx}")
        # Detectar guardian override ativo (via rejection_reasons)
        rejection_reasons = getattr(cycle_result, '_rejection_reasons', [])
        for rr in rejection_reasons:
            if "SUSPENSA" in rr or "guardian override" in rr.lower():
                parts.append("DIRECTIVE_SUSPENDED")
                break

        # Detectar se diary feedback influenciou (via oportunidade reason)
        diary_influenced = False
        for opp in cycle_result.opportunities:
            if hasattr(opp, "reason") and opp.reason and "[DIARY:" in opp.reason:
                diary_influenced = True
                # Extrair info do diary
                diary_tag = opp.reason[opp.reason.index("[DIARY:"):opp.reason.index("]", opp.reason.index("[DIARY:")) + 1]
                parts.append(diary_tag)
                break

        if diary_influenced:
            parts.insert(0, "DIARY_INFLUENCED")

        return " | ".join(parts)

    def _derive_action_from_micro(self, cycle_result) -> str:
        """Deriva ação BUY/SELL/HOLD com base no ciclo micro."""
        if cycle_result.opportunities:
            # Se há oportunidades, usa a primeira
            first_opp = cycle_result.opportunities[0]
            direction = first_opp.direction if hasattr(first_opp, "direction") else ""
            if direction == "COMPRA":
                return "BUY"
            elif direction == "VENDA":
                return "SELL"

        # Fallback baseado no macro_signal
        if cycle_result.macro_signal == "COMPRA" and cycle_result.micro_score > 0:
            return "BUY"
        elif cycle_result.macro_signal == "VENDA" and cycle_result.micro_score < 0:
            return "SELL"

        return "HOLD"

    def _calc_vwap_position(self, cycle_result) -> Optional[str]:
        """Calcula posição do preço em relação ao VWAP e desvios."""
        if not cycle_result.vwap or not cycle_result.price_current:
            return None

        price = cycle_result.price_current
        vwap = cycle_result.vwap

        if hasattr(vwap, "upper_2") and vwap.upper_2 and price >= vwap.upper_2:
            return "ABOVE_2S"
        elif hasattr(vwap, "upper_1") and vwap.upper_1 and price >= vwap.upper_1:
            return "ABOVE_1S"
        elif hasattr(vwap, "lower_2") and vwap.lower_2 and price <= vwap.lower_2:
            return "BELOW_2S"
        elif hasattr(vwap, "lower_1") and vwap.lower_1 and price <= vwap.lower_1:
            return "BELOW_1S"
        else:
            return "AT_VWAP"

    def _derive_indicator_signal(self, code: str, value, indicators) -> Optional[str]:
        """Deriva sinal textual de um indicador."""
        try:
            val = float(value)
            if code == "RSI_14":
                return self._rsi_signal(val)
            elif code == "ADX_14":
                return "STRONG_TREND" if val > 25 else "WEAK_TREND" if val > 15 else "NO_TREND"
        except (TypeError, ValueError):
            pass
        return None

    def _derive_indicator_score(self, code: str, value, indicators) -> Optional[int]:
        """Deriva score (-1, 0, +1) de um indicador."""
        try:
            val = float(value)
            if code == "RSI_14":
                if val < 30:
                    return 1  # Oversold → bullish
                elif val > 70:
                    return -1  # Overbought → bearish
                return 0
            elif code == "ADX_14":
                return 1 if val > 25 else 0
        except (TypeError, ValueError):
            pass
        return None

    def _rsi_signal(self, rsi) -> Optional[str]:
        """Converte RSI em sinal textual."""
        if rsi is None:
            return None
        rsi = float(rsi)
        if rsi < 30:
            return "OVERSOLD"
        elif rsi > 70:
            return "OVERBOUGHT"
        elif rsi < 45:
            return "BEARISH"
        elif rsi > 55:
            return "BULLISH"
        return "NEUTRAL"

    def _stoch_signal(self, stoch) -> Optional[str]:
        """Converte Estocástico em sinal textual."""
        if stoch is None:
            return None
        stoch = float(stoch)
        if stoch < 20:
            return "OVERSOLD"
        elif stoch > 80:
            return "OVERBOUGHT"
        return "NEUTRAL"


# ================================================================
# HELPERS
# ================================================================


def _signal_to_bias(signal: str) -> str:
    """Converte sinal macro (COMPRA/VENDA/NEUTRO) em bias."""
    mapping = {
        "COMPRA": "BULLISH",
        "VENDA": "BEARISH",
        "NEUTRO": "NEUTRAL",
    }
    return mapping.get(signal, "NEUTRAL")
