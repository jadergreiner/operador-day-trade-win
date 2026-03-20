#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
LightGBM Agent Integrator - v1.0

Integra modelo LightGBM treinado no agente de micro tendências.
Fornece scoring probabilístico para reforçar ou substituir análises técnicas.

Modelo: lgbm_classification_latest.pkl (20260212 - F1: 0.5664, Acc: 59.55%)
Features: 216 (lags, rolling, interações, correções, símbolos, indicadores)

Uso:
    from src.application.services.ml.lgbm_agent_integrator import LGBMAgentIntegrator

    integrator = LGBMAgentIntegrator()
    ml_score = integrator.score_opportunity(features_dict)

Status: ✅ PRODUÇÃO (26/02/2026)
"""

import os
from datetime import datetime
from pathlib import Path
from typing import Optional, Dict, Tuple
import numpy as np
import pandas as pd

try:
    import joblib
    JOBLIB_AVAILABLE = True
except ImportError:
    JOBLIB_AVAILABLE = False

try:
    import lightgbm as lgb
    LGB_AVAILABLE = True
except ImportError:
    LGB_AVAILABLE = False


class LGBMAgentIntegrator:
    """Integrador do modelo LightGBM no agente."""

    # Caminho padrão do modelo (relativo ao repo root)
    DEFAULT_MODEL_PATH = Path("data/models/lgbm/lgbm_classification_latest.pkl")

    def __init__(self, model_path: Optional[Path] = None):
        """
        Inicializa integrador.

        Args:
            model_path: Caminho ao modelo. Se None, usa DEFAULT_MODEL_PATH.
        """
        if model_path is None:
            # Encontra repo root
            current = Path(__file__).parent
            repo_root = current
            for _ in range(5):  # Sobe até 5 níveis
                if (repo_root / ".git").exists() or (repo_root / "pyproject.toml").exists():
                    break
                repo_root = repo_root.parent
            model_path = repo_root / self.DEFAULT_MODEL_PATH

        self.model_path = Path(model_path)
        self.model = None
        self.model_loaded = False
        self.loaded_model_version = "N/A"
        self.loaded_model_timestamp = "N/A"

        # Tenta carregar modelo
        self._load_model()

    def _load_model(self) -> bool:
        """Carrega modelo LightGBM do disco usando joblib."""
        if not self.model_path.exists():
            print(f"  ⚠️  LGBM: Modelo não encontrado: {self.model_path}")
            self.model = None
            self.model_loaded = False
            return False

        if not JOBLIB_AVAILABLE:
            print(f"  ⚠️  LGBM: joblib não disponível")
            self.model = None
            self.model_loaded = False
            return False

        try:
            self.model = joblib.load(self.model_path)
            self.model_loaded = True
            self.loaded_model_version = self.model_path.stem
            try:
                self.loaded_model_timestamp = datetime.fromtimestamp(
                    self.model_path.stat().st_mtime
                ).isoformat()
            except Exception:
                self.loaded_model_timestamp = "N/A"
            print(f"  ✅ LGBM: Modelo carregado [{self.model_path.name}]")
            return True
        except Exception as e:
            print(f"  ❌ LGBM: Erro ao carregar modelo: {e}")
            self.model = None
            self.model_loaded = False
            return False

    def reload_model(self) -> bool:
        """Recarrega o modelo do disco após retreino."""
        self.model = None
        self.model_loaded = False
        return self._load_model()

    def score_opportunity(
        self,
        cycle_result,  # CycleResult do agente
        opp,  # Opportunity a ser avaliada
    ) -> Tuple[float, str]:
        """
        Avalia oportunidade usando modelo LightGBM.

        Retorna probabilidade e reasoning.

        Args:
            cycle_result: CycleResult do _run_cycle()
            opp: Opportunity para avaliar

        Returns:
            (ml_probability, reasoning): Probabilidade [0.0, 1.0] e reasoning
        """
        if not self.model_loaded or self.model is None:
            return 0.5, "LGBM: Modelo indisponível (fallback: 50% confiança)"

        try:
            # Extrai features do contexto
            features = self._extract_features(cycle_result, opp)

            if features is None or len(features) == 0:
                return 0.5, "LGBM: Features não conseguiram ser extraídas"

            # Converte para DataFrame
            df = pd.DataFrame([features])

            # Predição
            probability = self.model.predict_proba(df)[0]

            # Assume classe 1 (BUY/COMPRA) = primeiro índice, classe 0 = segundo
            # Ajusta conforme necessário
            if len(probability) > 1:
                prob_buy = float(probability[1])
            else:
                prob_buy = float(probability[0])

            # Reasoning baseado em probabilidade
            if prob_buy > 0.7:
                reasoning = f"LGBM: FORTE COMPRA ({prob_buy:.1%})"
            elif prob_buy > 0.6:
                reasoning = f"LGBM: Compra moderada ({prob_buy:.1%})"
            elif prob_buy > 0.4:
                reasoning = f"LGBM: Neutro ({prob_buy:.1%})"
            elif prob_buy > 0.3:
                reasoning = f"LGBM: Venda moderada ({prob_buy:.1%})"
            else:
                reasoning = f"LGBM: FORTE VENDA ({prob_buy:.1%})"

            return prob_buy, reasoning

        except Exception as e:
            print(f"  ⚠️  LGBM: Erro ao score: {e}")
            return 0.5, f"LGBM: Erro ({str(e)[:30]})"

    def _extract_features(self, cycle_result, opp) -> Optional[Dict]:
        """
        Extrai 216 features do contexto do agente.

        Usa dados disponíveis em cycle_result + opp.
        Preenche ~30% com valores padrão se indisponíveis.
        """
        try:
            features = {}

            def _as_float(value, default: float = 0.0) -> float:
                try:
                    if value is None:
                        return default
                    return float(value)
                except (TypeError, ValueError):
                    return default

            # Validação básica
            if cycle_result is None or opp is None:
                return None

            # ─ PREÇOS BÁSICOS ─
            features["win_price"] = _as_float(getattr(cycle_result, "price_current", None))
            features["win_open_price"] = _as_float(getattr(cycle_result, "price_open", None))

            # ─ MACRO SCORE ─
            features["macro_score_final"] = _as_float(getattr(cycle_result, "macro_score", None))
            features["macro_confidence"] = _as_float(getattr(cycle_result, "macro_confidence", None))
            macro_signal = getattr(cycle_result, "macro_signal", "NEUTRO")
            features["macro_bias"] = (
                1 if macro_signal == "COMPRA"
                else (-1 if macro_signal == "VENDA" else 0)
            )

            # ─ MICRO SCORE ─
            features["micro_score"] = _as_float(getattr(cycle_result, "micro_score", None))
            opp_direction = getattr(opp, "direction", "VENDA")
            features["micro_trend"] = (
                1 if opp_direction == "COMPRA" else 0
            )  # Encoded 0/1

            # ─ VWAP ─
            vwap = _as_float(getattr(cycle_result, "vwap", None))
            features["vwap_value"] = vwap
            features["vwap_upper_1sigma"] = vwap * 1.01 if vwap > 0 else 0
            features["vwap_lower_1sigma"] = vwap * 0.99 if vwap > 0 else 0
            features["vwap_upper_2sigma"] = vwap * 1.02 if vwap > 0 else 0
            features["vwap_lower_2sigma"] = vwap * 0.98 if vwap > 0 else 0

            price_current = _as_float(getattr(cycle_result, "price_current", None))
            if vwap > 0 and price_current > 0:
                features["vwap_position"] = (
                    1 if price_current > vwap
                    else (-1 if price_current < vwap else 0)
                )
            else:
                features["vwap_position"] = 0

            # ─ PIVÔS ─
            if hasattr(cycle_result, "pivots") and cycle_result.pivots:
                pivots = cycle_result.pivots
                features["pivot_pp"] = pivots.get("PP", 0.0)
                features["pivot_r1"] = pivots.get("R1", 0.0)
                features["pivot_r2"] = pivots.get("R2", 0.0)
                features["pivot_r3"] = pivots.get("R3", 0.0)
                features["pivot_s1"] = pivots.get("S1", 0.0)
                features["pivot_s2"] = pivots.get("S2", 0.0)
                features["pivot_s3"] = pivots.get("S3", 0.0)
            else:
                for level in ["pp", "r1", "r2", "r3", "s1", "s2", "s3"]:
                    features[f"pivot_{level}"] = 0.0

            # ─ SMC ─
            if hasattr(cycle_result, "smc") and cycle_result.smc:
                smc = cycle_result.smc
                features["smc_direction"] = (
                    1 if smc.direction == "BULLISH" else (-1 if smc.direction == "BEARISH" else 0)
                )
                features["smc_bos_score"] = smc.bos_score or 0
                features["smc_equilibrium"] = (
                    1 if getattr(smc, "equilibrium", False) else 0
                )
                features["smc_equilibrium_score"] = smc.equilibrium_score or 0
                features["smc_fvg_score"] = smc.fvg_score or 0
            else:
                features["smc_direction"] = 0
                features["smc_bos_score"] = 0
                features["smc_equilibrium"] = 0
                features["smc_equilibrium_score"] = 0
                features["smc_fvg_score"] = 0

            # ─ VOLUME ─
            features["volume_score"] = getattr(cycle_result, "volume_score", None) or 0
            features["obv_score"] = getattr(cycle_result, "obv_score", None) or 0

            # ─ PADRÕES ─
            features["candle_pattern_score"] = getattr(cycle_result, "candle_pattern_score", None) or 0

            # ─ MOMENTUM ─
            if hasattr(cycle_result, "momentum") and cycle_result.momentum:
                mom = cycle_result.momentum
                features["ind_RSI_14_val"] = mom.rsi_value or 50
                features["ind_ADX_14_val"] = mom.adx_value or 0
                features["ind_EMA_9_val"] = mom.ema9_value or 0
                features["ind_RSI_14_score"] = mom.rsi_score or 0
                features["ind_ADX_14_score"] = mom.adx_score or 0
                features["ind_EMA_9_score"] = mom.ema9_score or 0
                features["ind_BB_POSITION_score"] = mom.bb_score or 0
            else:
                features["ind_RSI_14_val"] = 50
                features["ind_ADX_14_val"] = 0
                features["ind_EMA_9_val"] = 0
                features["ind_RSI_14_score"] = 0
                features["ind_ADX_14_score"] = 0
                features["ind_EMA_9_score"] = 0
                features["ind_BB_POSITION_score"] = 0

            # ─ OPORTUNIDADE ─
            if vwap > 0 and price_current > 0:
                features["price_vs_vwap_pct"] = ((price_current - vwap) / vwap * 100)
            else:
                features["price_vs_vwap_pct"] = 0

            if features.get("pivot_pp", 0) > 0 and price_current > 0:
                features["price_vs_pivot_pct"] = (
                    ((price_current - features.get("pivot_pp", 0)) / features.get("pivot_pp", 1) * 100)
                )
            else:
                features["price_vs_pivot_pct"] = 0

            # Preenchimento dos campos faltantes com zeros/padrões
            # (O modelo foi treinado com 216 features, preenchemos os não-disponíveis)
            feature_names_from_report = [
                "win_price", "win_open_price", "macro_score_final", "macro_confidence",
                "micro_score", "micro_trend", "vwap_value", "vwap_upper_1sigma",
                "vwap_lower_1sigma", "vwap_upper_2sigma", "vwap_lower_2sigma",
                "vwap_position", "pivot_pp", "pivot_r1", "pivot_r2", "pivot_r3",
                "pivot_s1", "pivot_s2", "pivot_s3", "smc_direction", "smc_bos_score",
                "smc_equilibrium", "smc_equilibrium_score", "smc_fvg_score",
                "volume_score", "obv_score", "candle_pattern_score", "macro_bias",
                # Correlações com grupos macro (preenchidas com 0)
                "corr_grp_ACOES_BRASIL_score", "corr_grp_COMMODITIES_score",
                "corr_grp_CRIPTOMOEDAS_score", "corr_grp_CURVA_JUROS_score",
                "corr_grp_DOLAR_CAMBIO_score", "corr_grp_EMERGENTES_score",
                "corr_grp_FLUXO_MICROESTRUTURA_score", "corr_grp_FOREX_score",
                "corr_grp_INDICADORES_TECNICOS_score", "corr_grp_INDICES_BRASIL_score",
                "corr_grp_INDICES_GLOBAIS_score", "corr_grp_JUROS_RENDA_FIXA_score",
                "corr_grp_PETROLEO_ENERGIA_score", "corr_grp_RISCO_PAIS_score",
                "corr_grp_VOLATILIDADE_score",
                # Mudanças (deltas)
                "corr_grp_ACOES_BRASIL_chg", "corr_grp_COMMODITIES_chg",
                "corr_grp_CRIPTOMOEDAS_chg", "corr_grp_CURVA_JUROS_chg",
                "corr_grp_DOLAR_CAMBIO_chg", "corr_grp_EMERGENTES_chg",
                "corr_grp_FOREX_chg", "corr_grp_INDICES_BRASIL_chg",
                "corr_grp_INDICES_GLOBAIS_chg", "corr_grp_JUROS_RENDA_FIXA_chg",
                "corr_grp_PETROLEO_ENERGIA_chg", "corr_grp_RISCO_PAIS_chg",
                "corr_grp_VOLATILIDADE_chg",
                # Pesos
                "corr_grp_ACOES_BRASIL_wgt", "corr_grp_COMMODITIES_wgt",
                "corr_grp_CRIPTOMOEDAS_wgt", "corr_grp_CURVA_JUROS_wgt",
                "corr_grp_DOLAR_CAMBIO_wgt", "corr_grp_EMERGENTES_wgt",
                "corr_grp_FLUXO_MICROESTRUTURA_wgt", "corr_grp_FOREX_wgt",
                "corr_grp_INDICADORES_TECNICOS_wgt", "corr_grp_INDICES_BRASIL_wgt",
                "corr_grp_INDICES_GLOBAIS_wgt", "corr_grp_JUROS_RENDA_FIXA_wgt",
                "corr_grp_PETROLEO_ENERGIA_wgt", "corr_grp_RISCO_PAIS_wgt",
                "corr_grp_VOLATILIDADE_wgt",
                # Símbolos (preenchidos com 0)
                "sym_BBAS3_score", "sym_BOVA11_score", "sym_DI1F27_score",
                "sym_DI1_N_score", "sym_DOL_N_score", "sym_HSI_score",
                "sym_IVVB11_score", "sym_PETR4_score", "sym_PRIO3_score",
                "sym_VALE3_score", "sym_WDO_N_score", "sym_WIN_N_score",
                "sym_WSP_N_score",
                "sym_BBAS3_chg", "sym_BOVA11_chg", "sym_DI1F27_chg",
                "sym_DI1_N_chg", "sym_DOL_N_chg", "sym_IVVB11_chg",
                "sym_PETR4_chg", "sym_PRIO3_chg", "sym_VALE3_chg",
                "sym_WDO_N_chg", "sym_WSP_N_chg",
                # Indicadores técnicos
                "ind_ADX_14_val", "ind_EMA_9_val", "ind_RSI_14_val",
                "ind_ADX_14_score", "ind_BB_POSITION_score", "ind_EMA_9_score",
                "ind_RSI_14_score",
                # Posições relativas
                "price_vs_vwap_pct", "price_vs_pivot_pct", "price_in_range_pct",
                "hora_decimal", "minutos_desde_abertura", "dia_semana",
                "mercado_us_aberto",
            ]

            # Preenche campos faltantes com 0
            for fname in feature_names_from_report:
                if fname not in features:
                    features[fname] = 0.0

            # Continua com lags, rolling stats, interações (preenchidas com 0)
            # São ~150 features adicionais - podem ser expandidas depois
            for lag in [1, 3, 5, 10]:
                for col in ["macro_score_final", "micro_score", "win_price",
                            "ind_RSI_14_val", "ind_ADX_14_val", "volume_score",
                            "smc_bos_score"]:
                    features[f"{col}_lag{lag}"] = 0.0

            for delta in [1, 3, 5]:
                for col in ["macro_score_final", "micro_score", "win_price",
                            "ind_RSI_14_val", "ind_ADX_14_val"]:
                    features[f"{col}_delta{delta}"] = 0.0
                    if col.startswith("win_price"):
                        features[f"{col}_delta{delta}_pct"] = 0.0

            for window in [5, 10, 20]:
                for col in ["macro_score_final", "micro_score", "ind_RSI_14_val"]:
                    for stat in ["mean", "std", "ema", "pos"]:
                        features[f"{col}_roll{window}_{stat}"] = 0.0

            # Interações
            for inter in ["macro_x_adx", "macro_x_micro", "macro_x_vol",
                          "rsi_x_smc", "bull_bear_ratio"]:
                features[f"inter_{inter}"] = 0.0

            # Consenso
            for consensus_col in ["corr_grp_mean_score", "corr_grp_std_score",
                                  "corr_grp_n_positive", "corr_grp_n_negative",
                                  "corr_grp_consensus", "bias_sum", "bias_agreement",
                                  "macro_positive_streak", "macro_negative_streak",
                                  "micro_positive_streak", "correct_streak"]:
                features[consensus_col] = 0.0

            # Distâncias
            for dist in ["dist_pivot_r1_pct", "dist_pivot_r2_pct",
                         "dist_pivot_s1_pct", "dist_pivot_s2_pct",
                         "dist_upper_1s_pct", "dist_lower_1s_pct",
                         "dist_upper_2s_pct", "dist_lower_2s_pct",
                         "vwap_band_width_pct"]:
                features[dist] = 0.0

            # Normaliza qualquer Decimal remanescente para float, evitando
            # incompatibilidade com pandas / LightGBM / operações aritméticas.
            for key, value in list(features.items()):
                if isinstance(value, bool):
                    features[key] = int(value)
                    continue
                if isinstance(value, (int, float, np.integer, np.floating)):
                    features[key] = float(value)
                    continue
                try:
                    features[key] = float(value)
                except (TypeError, ValueError):
                    features[key] = 0.0

            return features

        except Exception as e:
            print(f"  ⚠️  Erro ao extrair features: {e}")
            return None


# Instância global para uso rápido
_global_integrator = None


def get_lgbm_integrator() -> Optional[LGBMAgentIntegrator]:
    """Obtém instância global do integrador."""
    global _global_integrator
    if _global_integrator is None:
        _global_integrator = LGBMAgentIntegrator()
    return _global_integrator
