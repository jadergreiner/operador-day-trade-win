"""Repositório para persistência de dados de Aprendizagem por Reforço.

Responsável por salvar e consultar episódios, scores de correlação,
indicadores técnicos e recompensas para treinamento do modelo RL.
"""

from abc import ABC, abstractmethod
from datetime import datetime, timedelta
from decimal import Decimal
from typing import Optional

from sqlalchemy import and_, func
from sqlalchemy.orm import Session

from src.infrastructure.database.rl_schema import (
    DimCorrelationItemModel,
    DimTechnicalIndicatorModel,
    RLCorrelationScoreModel,
    RLEpisodeModel,
    RLIndicatorValueModel,
    RLRewardModel,
    RLTrainingMetricsModel,
)


class IRLRepository(ABC):
    """Interface do repositório de Aprendizagem por Reforço."""

    @abstractmethod
    def save_episode(self, episode: dict) -> None:
        """Persiste um episódio completo (estado + ação)."""

    @abstractmethod
    def save_correlation_scores(
        self, episode_id: str, scores: list[dict]
    ) -> None:
        """Persiste scores de correlação de um episódio."""

    @abstractmethod
    def save_indicator_values(
        self, episode_id: str, indicators: list[dict]
    ) -> None:
        """Persiste valores de indicadores técnicos."""

    @abstractmethod
    def create_pending_rewards(
        self, episode_id: str, decision_data: dict
    ) -> None:
        """Cria registros pendentes de recompensa multi-horizonte."""

    @abstractmethod
    def evaluate_reward(
        self, episode_id: str, horizon_minutes: int, evaluation: dict
    ) -> None:
        """Avalia e preenche a recompensa de um horizonte."""

    @abstractmethod
    def get_pending_rewards(self, horizon_minutes: int) -> list[dict]:
        """Retorna recompensas pendentes de avaliação."""

    @abstractmethod
    def get_episodes_for_training(
        self,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        limit: int = 10000,
    ) -> list[dict]:
        """Retorna episódios completos para treinamento RL."""

    @abstractmethod
    def get_episode_state_vector(self, episode_id: str) -> Optional[dict]:
        """Retorna o vetor de estado completo de um episódio."""

    @abstractmethod
    def seed_dimension_tables(self) -> None:
        """Popula tabelas de dimensão com dados de referência."""


class SqliteRLRepository(IRLRepository):
    """Implementação SQLite do repositório de RL."""

    # Horizontes de avaliação de recompensa em minutos
    REWARD_HORIZONS = [5, 15, 30, 60, 120]

    def __init__(self, session: Session) -> None:
        self.session = session

    def save_episode(self, episode: dict) -> None:
        """Persiste um episódio completo."""
        model = RLEpisodeModel(
            episode_id=episode["episode_id"],
            timestamp=episode["timestamp"],
            source=episode["source"],
            # Preços
            win_price=episode.get("win_price"),
            win_open_price=episode.get("win_open_price"),
            win_high_of_day=episode.get("win_high_of_day"),
            win_low_of_day=episode.get("win_low_of_day"),
            win_price_change_pct=episode.get("win_price_change_pct"),
            # Scores agregados
            macro_score_final=episode.get("macro_score_final"),
            macro_score_bullish=episode.get("macro_score_bullish"),
            macro_score_bearish=episode.get("macro_score_bearish"),
            macro_score_neutral=episode.get("macro_score_neutral"),
            macro_items_available=episode.get("macro_items_available"),
            macro_confidence=episode.get("macro_confidence"),
            micro_score=episode.get("micro_score"),
            micro_trend=episode.get("micro_trend"),
            # Alinhamento
            alignment_score=episode.get("alignment_score"),
            overall_confidence=episode.get("overall_confidence"),
            # VWAP
            vwap_value=episode.get("vwap_value"),
            vwap_upper_1sigma=episode.get("vwap_upper_1sigma"),
            vwap_lower_1sigma=episode.get("vwap_lower_1sigma"),
            vwap_upper_2sigma=episode.get("vwap_upper_2sigma"),
            vwap_lower_2sigma=episode.get("vwap_lower_2sigma"),
            vwap_position=episode.get("vwap_position"),
            # Pivots
            pivot_pp=episode.get("pivot_pp"),
            pivot_r1=episode.get("pivot_r1"),
            pivot_r2=episode.get("pivot_r2"),
            pivot_r3=episode.get("pivot_r3"),
            pivot_s1=episode.get("pivot_s1"),
            pivot_s2=episode.get("pivot_s2"),
            pivot_s3=episode.get("pivot_s3"),
            # SMC
            smc_direction=episode.get("smc_direction"),
            smc_bos_score=episode.get("smc_bos_score"),
            smc_equilibrium=episode.get("smc_equilibrium"),
            smc_equilibrium_score=episode.get("smc_equilibrium_score"),
            smc_fvg_score=episode.get("smc_fvg_score"),
            # Volume
            volume_today=episode.get("volume_today"),
            volume_avg=episode.get("volume_avg"),
            volume_variance_pct=episode.get("volume_variance_pct"),
            volume_score=episode.get("volume_score"),
            obv_score=episode.get("obv_score"),
            # Sentimento
            sentiment_intraday=episode.get("sentiment_intraday"),
            sentiment_momentum=episode.get("sentiment_momentum"),
            sentiment_volatility=episode.get("sentiment_volatility"),
            probability_up=episode.get("probability_up"),
            probability_down=episode.get("probability_down"),
            probability_neutral=episode.get("probability_neutral"),
            recommended_approach=episode.get("recommended_approach"),
            # Regime
            market_regime=episode.get("market_regime"),
            market_condition=episode.get("market_condition"),
            session_phase=episode.get("session_phase"),
            # Candle patterns
            candle_pattern_score=episode.get("candle_pattern_score"),
            candle_pattern_detail=episode.get("candle_pattern_detail"),
            # Ação
            action=episode["action"],
            urgency=episode.get("urgency"),
            risk_level=episode.get("risk_level"),
            # Setup
            entry_price=episode.get("entry_price"),
            stop_loss=episode.get("stop_loss"),
            take_profit=episode.get("take_profit"),
            risk_reward_ratio=episode.get("risk_reward_ratio"),
            setup_type=episode.get("setup_type"),
            setup_quality=episode.get("setup_quality"),
            # Biases
            macro_bias=episode.get("macro_bias"),
            fundamental_bias=episode.get("fundamental_bias"),
            sentiment_bias=episode.get("sentiment_bias"),
            technical_bias=episode.get("technical_bias"),
            # Meta
            reasoning=episode.get("reasoning"),
            session_date=episode.get("session_date"),
        )
        self.session.add(model)
        self.session.commit()

    def save_correlation_scores(
        self, episode_id: str, scores: list[dict]
    ) -> None:
        """Persiste scores de correlação (um por item)."""
        for score in scores:
            model = RLCorrelationScoreModel(
                episode_id=episode_id,
                timestamp=score["timestamp"],
                item_number=score["item_number"],
                symbol=score["symbol"],
                category=score["category"],
                correlation_type=score["correlation_type"],
                opening_price=score.get("opening_price"),
                current_price=score.get("current_price"),
                price_change_pct=score.get("price_change_pct"),
                raw_score=score["raw_score"],
                final_score=score["final_score"],
                weight=score["weight"],
                weighted_score=score["weighted_score"],
                is_available=score.get("is_available", 1),
                resolved_symbol=score.get("resolved_symbol"),
                detail=score.get("detail"),
            )
            self.session.add(model)

        self.session.commit()

    def save_indicator_values(
        self, episode_id: str, indicators: list[dict]
    ) -> None:
        """Persiste valores de indicadores técnicos."""
        for ind in indicators:
            model = RLIndicatorValueModel(
                episode_id=episode_id,
                timestamp=ind["timestamp"],
                indicator_code=ind["indicator_code"],
                timeframe=ind["timeframe"],
                value=ind.get("value"),
                value_secondary=ind.get("value_secondary"),
                value_tertiary=ind.get("value_tertiary"),
                score=ind.get("score"),
                signal=ind.get("signal"),
                detail=ind.get("detail"),
            )
            self.session.add(model)

        self.session.commit()

    def create_pending_rewards(
        self, episode_id: str, decision_data: dict
    ) -> None:
        """Cria registros de recompensa pendente para cada horizonte."""
        for horizon in self.REWARD_HORIZONS:
            model = RLRewardModel(
                episode_id=episode_id,
                timestamp_decision=decision_data["timestamp"],
                win_price_at_decision=decision_data["win_price"],
                action_at_decision=decision_data["action"],
                horizon_minutes=horizon,
                is_evaluated=0,
            )
            self.session.add(model)

        self.session.commit()

    def evaluate_reward(
        self, episode_id: str, horizon_minutes: int, evaluation: dict
    ) -> None:
        """Avalia e preenche a recompensa de um horizonte específico."""
        reward = (
            self.session.query(RLRewardModel)
            .filter(
                RLRewardModel.episode_id == episode_id,
                RLRewardModel.horizon_minutes == horizon_minutes,
            )
            .first()
        )

        if not reward:
            return

        reward.evaluated_at = evaluation["evaluated_at"]
        reward.win_price_at_evaluation = evaluation["win_price_at_evaluation"]
        reward.price_change_points = evaluation.get("price_change_points")
        reward.price_change_pct = evaluation.get("price_change_pct")
        reward.reward_direction = evaluation.get("reward_direction")
        reward.was_correct = evaluation.get("was_correct")
        reward.reward_normalized = evaluation.get("reward_normalized")
        reward.reward_continuous = evaluation.get("reward_continuous")
        reward.max_favorable_points = evaluation.get("max_favorable_points")
        reward.max_adverse_points = evaluation.get("max_adverse_points")
        reward.volatility_in_horizon = evaluation.get("volatility_in_horizon")
        reward.is_evaluated = 1

        self.session.commit()

    def get_pending_rewards(self, horizon_minutes: int) -> list[dict]:
        """Retorna recompensas pendentes de avaliação para um horizonte."""
        now = datetime.now()
        cutoff = now - timedelta(minutes=horizon_minutes)

        models = (
            self.session.query(RLRewardModel)
            .filter(
                RLRewardModel.is_evaluated == 0,
                RLRewardModel.horizon_minutes == horizon_minutes,
                RLRewardModel.timestamp_decision <= cutoff,
            )
            .order_by(RLRewardModel.timestamp_decision.asc())
            .all()
        )

        return [
            {
                "episode_id": m.episode_id,
                "timestamp_decision": m.timestamp_decision,
                "win_price_at_decision": float(m.win_price_at_decision),
                "action_at_decision": m.action_at_decision,
                "horizon_minutes": m.horizon_minutes,
            }
            for m in models
        ]

    def get_episodes_for_training(
        self,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        limit: int = 10000,
    ) -> list[dict]:
        """Retorna episódios com recompensas avaliadas para treinamento.

        Retorna dados estruturados para montar dataset de RL:
        - Estado (features do episódio)
        - Ação
        - Recompensa (média dos horizontes avaliados)
        """
        query = self.session.query(RLEpisodeModel)

        if start_date:
            query = query.filter(RLEpisodeModel.timestamp >= start_date)
        if end_date:
            query = query.filter(RLEpisodeModel.timestamp <= end_date)

        query = query.order_by(RLEpisodeModel.timestamp.asc()).limit(limit)
        episodes = query.all()

        results = []
        for ep in episodes:
            # Buscar recompensas avaliadas
            rewards = (
                self.session.query(RLRewardModel)
                .filter(
                    RLRewardModel.episode_id == ep.episode_id,
                    RLRewardModel.is_evaluated == 1,
                )
                .all()
            )

            if not rewards:
                continue

            reward_by_horizon = {
                r.horizon_minutes: {
                    "reward_normalized": r.reward_normalized,
                    "reward_continuous": r.reward_continuous,
                    "was_correct": r.was_correct,
                    "price_change_points": float(r.price_change_points)
                    if r.price_change_points
                    else None,
                }
                for r in rewards
            }

            results.append(
                {
                    "episode_id": ep.episode_id,
                    "timestamp": ep.timestamp,
                    "source": ep.source,
                    "action": ep.action,
                    # Estado resumido
                    "win_price": float(ep.win_price) if ep.win_price else None,
                    "macro_score_final": (
                        float(ep.macro_score_final) if ep.macro_score_final else None
                    ),
                    "micro_score": ep.micro_score,
                    "alignment_score": ep.alignment_score,
                    "overall_confidence": ep.overall_confidence,
                    "probability_up": ep.probability_up,
                    "probability_down": ep.probability_down,
                    # Biases
                    "macro_bias": ep.macro_bias,
                    "fundamental_bias": ep.fundamental_bias,
                    "sentiment_bias": ep.sentiment_bias,
                    "technical_bias": ep.technical_bias,
                    # Regime
                    "market_regime": ep.market_regime,
                    "session_phase": ep.session_phase,
                    # Recompensas
                    "rewards": reward_by_horizon,
                }
            )

        return results

    def get_episode_state_vector(self, episode_id: str) -> Optional[dict]:
        """Retorna vetor de estado completo de um episódio para inferência.

        Inclui: episódio + correlações + indicadores.
        """
        ep = (
            self.session.query(RLEpisodeModel)
            .filter(RLEpisodeModel.episode_id == episode_id)
            .first()
        )

        if not ep:
            return None

        # Correlações
        correlations = (
            self.session.query(RLCorrelationScoreModel)
            .filter(RLCorrelationScoreModel.episode_id == episode_id)
            .order_by(RLCorrelationScoreModel.item_number)
            .all()
        )

        # Indicadores
        indicators = (
            self.session.query(RLIndicatorValueModel)
            .filter(RLIndicatorValueModel.episode_id == episode_id)
            .all()
        )

        return {
            "episode": {
                "episode_id": ep.episode_id,
                "timestamp": ep.timestamp,
                "win_price": float(ep.win_price) if ep.win_price else None,
                "macro_score_final": (
                    float(ep.macro_score_final) if ep.macro_score_final else None
                ),
                "macro_score_bullish": (
                    float(ep.macro_score_bullish) if ep.macro_score_bullish else None
                ),
                "macro_score_bearish": (
                    float(ep.macro_score_bearish) if ep.macro_score_bearish else None
                ),
                "micro_score": ep.micro_score,
                "alignment_score": ep.alignment_score,
                "overall_confidence": ep.overall_confidence,
                "volume_score": ep.volume_score,
                "obv_score": ep.obv_score,
                "candle_pattern_score": ep.candle_pattern_score,
                "probability_up": ep.probability_up,
                "probability_down": ep.probability_down,
                "probability_neutral": ep.probability_neutral,
                "vwap_position": ep.vwap_position,
                "smc_direction": ep.smc_direction,
                "smc_equilibrium": ep.smc_equilibrium,
                "market_regime": ep.market_regime,
                "market_condition": ep.market_condition,
                "session_phase": ep.session_phase,
                "action": ep.action,
            },
            "correlations": [
                {
                    "item_number": c.item_number,
                    "symbol": c.symbol,
                    "category": c.category,
                    "correlation_type": c.correlation_type,
                    "current_price": float(c.current_price) if c.current_price else None,
                    "price_change_pct": c.price_change_pct,
                    "raw_score": c.raw_score,
                    "final_score": c.final_score,
                    "weighted_score": float(c.weighted_score),
                    "is_available": c.is_available,
                }
                for c in correlations
            ],
            "indicators": [
                {
                    "indicator_code": i.indicator_code,
                    "timeframe": i.timeframe,
                    "value": i.value,
                    "value_secondary": i.value_secondary,
                    "score": i.score,
                    "signal": i.signal,
                }
                for i in indicators
            ],
        }

    def get_correlation_accuracy(
        self,
        item_number: int,
        horizon_minutes: int = 30,
        limit: int = 100,
    ) -> Optional[dict]:
        """Calcula acurácia histórica de um item de correlação.

        Para cada episódio, verifica se o score do item acompanhou
        a direção real do WIN no horizonte especificado.

        Retorna:
            dict com accuracy, total, correct, avg_reward
        """
        # Busca correlações + rewards
        results = (
            self.session.query(RLCorrelationScoreModel, RLRewardModel)
            .join(
                RLRewardModel,
                and_(
                    RLCorrelationScoreModel.episode_id == RLRewardModel.episode_id,
                    RLRewardModel.horizon_minutes == horizon_minutes,
                    RLRewardModel.is_evaluated == 1,
                ),
            )
            .filter(
                RLCorrelationScoreModel.item_number == item_number,
                RLCorrelationScoreModel.is_available == 1,
            )
            .order_by(RLCorrelationScoreModel.timestamp.desc())
            .limit(limit)
            .all()
        )

        if not results:
            return None

        correct = 0
        total = 0
        total_reward = 0.0

        for corr, reward in results:
            if corr.final_score == 0:
                continue  # Neutro não conta

            total += 1
            direction = reward.reward_direction

            # Score +1 e preço subiu, ou score -1 e preço caiu
            if (corr.final_score > 0 and direction == "UP") or (
                corr.final_score < 0 and direction == "DOWN"
            ):
                correct += 1

            if reward.reward_normalized is not None:
                total_reward += reward.reward_normalized

        if total == 0:
            return None

        return {
            "item_number": item_number,
            "accuracy": correct / total,
            "total": total,
            "correct": correct,
            "avg_reward": total_reward / total,
        }

    def get_category_performance(
        self, horizon_minutes: int = 30
    ) -> list[dict]:
        """Retorna performance agrupada por categoria de ativo.

        Útil para o RL ajustar pesos das categorias.
        """
        results = (
            self.session.query(
                RLCorrelationScoreModel.category,
                func.count().label("total"),
                func.avg(RLCorrelationScoreModel.weighted_score).label("avg_weighted_score"),
            )
            .filter(RLCorrelationScoreModel.is_available == 1)
            .group_by(RLCorrelationScoreModel.category)
            .all()
        )

        return [
            {
                "category": r.category,
                "total_observations": r.total,
                "avg_weighted_score": float(r.avg_weighted_score) if r.avg_weighted_score else 0,
            }
            for r in results
        ]

    def save_training_metrics(self, metrics: dict) -> None:
        """Persiste métricas de um ciclo de treinamento RL."""
        model = RLTrainingMetricsModel(
            training_id=metrics["training_id"],
            timestamp=metrics["timestamp"],
            model_name=metrics["model_name"],
            model_version=metrics["model_version"],
            algorithm=metrics["algorithm"],
            episodes_total=metrics["episodes_total"],
            episodes_train=metrics["episodes_train"],
            episodes_validation=metrics["episodes_validation"],
            date_range_start=metrics.get("date_range_start"),
            date_range_end=metrics.get("date_range_end"),
            avg_reward=metrics.get("avg_reward"),
            cumulative_reward=metrics.get("cumulative_reward"),
            win_rate=metrics.get("win_rate"),
            profit_factor=metrics.get("profit_factor"),
            sharpe_ratio=metrics.get("sharpe_ratio"),
            max_drawdown=metrics.get("max_drawdown"),
            buy_accuracy=metrics.get("buy_accuracy"),
            sell_accuracy=metrics.get("sell_accuracy"),
            hold_accuracy=metrics.get("hold_accuracy"),
            hyperparameters=metrics.get("hyperparameters"),
            feature_importance=metrics.get("feature_importance"),
            validation_reward=metrics.get("validation_reward"),
            overfitting_ratio=metrics.get("overfitting_ratio"),
            notes=metrics.get("notes"),
        )
        self.session.add(model)
        self.session.commit()

    def seed_dimension_tables(self) -> None:
        """Popula tabelas de dimensão com dados do item_registry.

        Faz inserção incremental e atualiza itens existentes cujos
        símbolos ou configurações foram alterados.
        """
        from src.application.services.macro_score.item_registry import (
            get_item_registry,
        )

        # Busca itens já cadastrados (indexados por item_number)
        existing_models = {
            row.item_number: row
            for row in self.session.query(DimCorrelationItemModel).all()
        }

        # Popula/atualiza dim_correlation_items
        items = get_item_registry()
        new_count = 0
        updated_count = 0
        for item in items:
            if item.number in existing_models:
                # Verificar se precisa atualizar
                model = existing_models[item.number]
                needs_update = (
                    model.symbol != item.symbol
                    or model.name != item.name
                    or model.category != item.category.value
                    or model.is_futures != (1 if item.is_futures else 0)
                    or model.scoring_type != item.scoring_type.value
                )
                if needs_update:
                    model.symbol = item.symbol
                    model.name = item.name
                    model.category = item.category.value
                    model.correlation_type = item.correlation.value
                    model.weight = item.weight
                    model.is_futures = 1 if item.is_futures else 0
                    model.scoring_type = item.scoring_type.value
                    model.indicator_config = item.indicator_config
                    updated_count += 1
                continue

            model = DimCorrelationItemModel(
                item_number=item.number,
                symbol=item.symbol,
                name=item.name,
                category=item.category.value,
                correlation_type=item.correlation.value,
                weight=item.weight,
                is_futures=1 if item.is_futures else 0,
                scoring_type=item.scoring_type.value,
                indicator_config=item.indicator_config,
            )
            self.session.add(model)
            new_count += 1

        # Popula dim_technical_indicators (incremental)
        existing_codes = {
            row[0]
            for row in self.session.query(
                DimTechnicalIndicatorModel.indicator_code
            ).all()
        }

        indicators = [
            ("RSI_14", "RSI 14 períodos", "MOMENTUM", {"period": 14, "overbought": 70, "oversold": 30}, "NUMERIC"),
            ("STOCH_14", "Estocástico 14", "MOMENTUM", {"period": 14, "overbought": 80, "oversold": 20}, "NUMERIC"),
            ("MACD_12_26_9", "MACD(12,26,9)", "MOMENTUM", {"fast": 12, "slow": 26, "signal": 9}, "NUMERIC"),
            ("ADX_14", "ADX 14 períodos", "TREND", {"period": 14, "threshold": 25}, "NUMERIC"),
            ("EMA_9", "EMA 9 períodos", "TREND", {"period": 9}, "NUMERIC"),
            ("EMA_21", "EMA 21 períodos", "TREND", {"period": 21}, "NUMERIC"),
            ("SMA_20", "SMA 20 períodos", "TREND", {"period": 20}, "NUMERIC"),
            ("SMA_50", "SMA 50 períodos", "TREND", {"period": 50}, "NUMERIC"),
            ("BB_UPPER", "Bollinger Band Superior", "VOLATILITY", {"period": 20, "std_dev": 2}, "NUMERIC"),
            ("BB_MIDDLE", "Bollinger Band Média", "VOLATILITY", {"period": 20, "std_dev": 2}, "NUMERIC"),
            ("BB_LOWER", "Bollinger Band Inferior", "VOLATILITY", {"period": 20, "std_dev": 2}, "NUMERIC"),
            ("BB_POSITION", "Posição nas Bollinger Bands", "VOLATILITY", {"period": 20, "std_dev": 2}, "SCORE"),
            ("ATR_14", "ATR 14 períodos", "VOLATILITY", {"period": 14}, "NUMERIC"),
            ("VWAP", "VWAP do dia", "VOLUME", {}, "NUMERIC"),
            ("OBV", "On Balance Volume", "VOLUME", {}, "NUMERIC"),
            ("VOLUME", "Volume Financeiro", "VOLUME", {}, "NUMERIC"),
            ("AGGRESSION", "Saldo de Agressão", "VOLUME", {}, "SCORE"),
            ("DI_PLUS", "DI+", "TREND", {"period": 14}, "NUMERIC"),
            ("DI_MINUS", "DI-", "TREND", {"period": 14}, "NUMERIC"),
        ]

        for code, name, group, params, vtype in indicators:
            if code in existing_codes:
                continue
            model = DimTechnicalIndicatorModel(
                indicator_code=code,
                indicator_name=name,
                indicator_group=group,
                default_params=params,
                value_type=vtype,
            )
            self.session.add(model)

        self.session.commit()
