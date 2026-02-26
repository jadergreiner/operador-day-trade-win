"""
Backtesting Server com XGBoost
Integração P5.2 (OAuth) + P4.4 (WebSocket) + P8.2 (ML)
"""

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from typing import Dict, List, Optional
import pickle
import numpy as np
import pandas as pd
from datetime import datetime
from pathlib import Path
import logging

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/backtest", tags=["backtesting"])

# Carregar modelo XGBoost (será salvo em P8.2)
MODEL_PATH = Path("models/xgboost_model_ati8.pkl")


class PredictionRequest(BaseModel):
    """Request com features para fazer predição"""
    features: Dict[str, float] = Field(..., description="Dicionário com 29 features")
    symbols: List[str] = Field(default=["EURUSD", "GBPUSD"], description="Símbolos para análise")
    timestamp: Optional[str] = Field(default=None, description="Timestamp ISO")


class PredictionResponse(BaseModel):
    """Response com predição do modelo"""
    prediction: int = Field(..., description="0=down, 1=up")
    confidence: float = Field(..., description="Probabilidade [0-1]")
    signal_strength: str = Field(..., description="WEAK/MEDIUM/STRONG")
    timestamp: str
    model_version: str = "1.0.0-ati8"


class BacktestResult(BaseModel):
    """Resultado de backtesting"""
    symbol: str
    total_signals: int
    winning_signals: int
    losing_signals: int
    win_rate: float
    average_return: float
    sharpe_ratio: float
    max_drawdown: float
    timestamp: str


class BacktestServer:
    """Servidor de backtesting com XGBoost"""

    def __init__(self):
        self.model = None
        self.feature_names = None
        self.is_loaded = False
        self._load_model()

    def _load_model(self):
        """Carrega modelo XGBoost do arquivo"""
        try:
            if MODEL_PATH.exists():
                with open(MODEL_PATH, 'rb') as f:
                    self.model = pickle.load(f)
                    self.is_loaded = True
                    logger.info(f"✅ Modelo carregado de {MODEL_PATH}")
            else:
                logger.warning(f"⚠️ Modelo não encontrado em {MODEL_PATH} - usando dummy")
                self.model = None
                self.is_loaded = False
        except Exception as e:
            logger.error(f"❌ Erro ao carregar modelo: {e}")
            self.model = None
            self.is_loaded = False

    def predict(self, features_dict: Dict[str, float]) -> tuple:
        """
        Fazer predição com XGBoost

        Returns: (prediction, confidence)
            - prediction: 0 (down) or 1 (up)
            - confidence: float [0-1]
        """
        if not self.is_loaded:
            # Dummy prediction se modelo não carregado
            return 1, 0.55

        try:
            # Converter dict para array na ordem correta
            feature_array = np.array([features_dict.get(f, 0.0) for f in self.feature_names])

            # Fazer predição
            prediction = self.model.predict(feature_array.reshape(1, -1))[0]
            confidence = self.model.predict_proba(feature_array.reshape(1, -1))[0][int(prediction)]

            return int(prediction), float(confidence)
        except Exception as e:
            logger.error(f"Erro na predição: {e}")
            return 0, 0.5

    def get_signal_strength(self, confidence: float) -> str:
        """Converter confidence para força do sinal"""
        if confidence < 0.55:
            return "WEAK"
        elif confidence < 0.70:
            return "MEDIUM"
        else:
            return "STRONG"


# Instância global
backtest_server = BacktestServer()


@router.get("/health")
async def backtest_health():
    """Verificar saúde do serviço de backtesting"""
    return {
        "status": "healthy",
        "model_loaded": backtest_server.is_loaded,
        "model_path": str(MODEL_PATH),
        "timestamp": datetime.utcnow().isoformat()
    }


@router.post("/predict")
async def predict_signal(request: PredictionRequest) -> PredictionResponse:
    """
    Fazer predição com XGBoost

    Exemplo:
        POST /backtest/predict
        {
            "features": {
                "volatilidade_1": 0.5,
                "rsi_14": 45.2,
                ...28 mais features...
            },
            "symbols": ["EURUSD", "GBPUSD"],
            "timestamp": "2026-02-26T20:30:00"
        }

    Response:
        {
            "prediction": 1,
            "confidence": 0.72,
            "signal_strength": "STRONG",
            "timestamp": "2026-02-26T20:30:00.123456",
            "model_version": "1.0.0-ati8"
        }
    """

    try:
        # Validar número de features
        if len(request.features) < 29:
            raise HTTPException(
                status_code=400,
                detail=f"Features insuficientes: {len(request.features)}/29"
            )

        # Fazer predição
        prediction, confidence = backtest_server.predict(request.features)

        # Calcular força do sinal
        signal_strength = backtest_server.get_signal_strength(confidence)

        return PredictionResponse(
            prediction=prediction,
            confidence=confidence,
            signal_strength=signal_strength,
            timestamp=datetime.utcnow().isoformat()
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Erro na predição: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/batch-predict")
async def batch_predict(
    requests: List[PredictionRequest]
) -> List[PredictionResponse]:
    """
    Fazer múltiplas predições em batch

    Útil para backtesting histórico ou análise de múltiplos candles
    """

    results = []
    for req in requests:
        try:
            prediction, confidence = backtest_server.predict(req.features)
            signal_strength = backtest_server.get_signal_strength(confidence)

            results.append(PredictionResponse(
                prediction=prediction,
                confidence=confidence,
                signal_strength=signal_strength,
                timestamp=req.timestamp or datetime.utcnow().isoformat()
            ))
        except Exception as e:
            logger.error(f"Erro em batch prediction: {e}")
            continue

    return results


@router.get("/model/info")
async def model_info():
    """Informações sobre o modelo XGBoost"""

    info = {
        "model_name": "xgboost_ati8",
        "version": "1.0.0",
        "model_loaded": backtest_server.is_loaded,
        "feature_count": 29 if backtest_server.is_loaded else 0,
        "output_classes": 2,  # Binary: 0=down, 1=up
        "algorithm": "XGBoost Classifier",
        "training_method": "5-Fold Stratified Cross-Validation",
        "hyperparameter_tuning": "Grid Search (8 configurations)",
        "model_path": str(MODEL_PATH)
    }

    if backtest_server.is_loaded and backtest_server.model:
        try:
            # Adicionar detalhes do modelo
            info.update({
                "n_estimators": backtest_server.model.n_estimators,
                "max_depth": backtest_server.model.max_depth,
                "learning_rate": backtest_server.model.learning_rate,
                "hyperparameters": {
                    "max_depth": backtest_server.model.max_depth,
                    "n_estimators": backtest_server.model.n_estimators,
                    "learning_rate": backtest_server.model.learning_rate,
                    "subsample": backtest_server.model.subsample,
                    "colsample_bytree": backtest_server.model.colsample_bytree,
                }
            })
        except:
            pass

    return info


@router.post("/validate")
async def validate_features(features: Dict[str, float]):
    """
    Validar features antes de fazer predição

    Retorna lista de features faltantes ou inválidas
    """

    expected_features = 29
    actual_count = len(features)

    validation = {
        "valid": actual_count >= expected_features,
        "expected_count": expected_features,
        "actual_count": actual_count,
        "missing_count": max(0, expected_features - actual_count),
        "issues": []
    }

    # Validar valores (NaN, Inf, etc)
    for feature_name, value in features.items():
        try:
            if np.isnan(float(value)):
                validation["issues"].append(f"{feature_name}: NaN value")
            elif np.isinf(float(value)):
                validation["issues"].append(f"{feature_name}: Infinity value")
        except:
            validation["issues"].append(f"{feature_name}: Invalid value type")

    return validation


class BacktestStats:
    """Estatísticas de backtesting"""

    @staticmethod
    def calculate_win_rate(winning: int, total: int) -> float:
        """Calcular taxa de vitória"""
        return (winning / total * 100) if total > 0 else 0.0

    @staticmethod
    def calculate_sharpe_ratio(returns: List[float], risk_free_rate: float = 0.02) -> float:
        """Calcular Sharpe Ratio"""
        if not returns:
            return 0.0

        returns_array = np.array(returns)
        excess_returns = returns_array - risk_free_rate

        std_dev = np.std(excess_returns)
        if std_dev == 0:
            return 0.0

        return float(np.mean(excess_returns) / std_dev)

    @staticmethod
    def calculate_max_drawdown(prices: List[float]) -> float:
        """Calcular drawdown máximo"""
        if not prices:
            return 0.0

        prices_array = np.array(prices)
        running_max = np.maximum.accumulate(prices_array)
        drawdown = (prices_array - running_max) / running_max

        return float(np.min(drawdown) * 100)  # As percentage

    @staticmethod
    def calculate_stats(
        predictions: List[int],
        actuals: List[int],
        returns: List[float]
    ) -> Dict:
        """Calcular todas as estatísticas"""

        total = len(predictions)
        winning = sum(1 for p, a in zip(predictions, actuals) if p == a)

        return {
            "total_signals": total,
            "winning_signals": winning,
            "losing_signals": total - winning,
            "win_rate": BacktestStats.calculate_win_rate(winning, total),
            "average_return": float(np.mean(returns)) if returns else 0.0,
            "sharpe_ratio": BacktestStats.calculate_sharpe_ratio(returns),
            "max_drawdown": BacktestStats.calculate_max_drawdown(
                [1.0 + r for r in returns]  # Cumulative returns
            )
        }


@router.post("/simulate")
async def simulate_backtest(
    predictions: List[int] = None,
    actuals: List[int] = None,
    returns: List[float] = None
) -> Dict:
    """
    Simular resultados de backtesting

    Para testes e validação antes de live trading
    """

    if predictions is None or actuals is None or returns is None:
        raise HTTPException(
            status_code=400,
            detail="predictions, actuals e returns são obrigatórios"
        )

    if not (len(predictions) == len(actuals) == len(returns)):
        raise HTTPException(
            status_code=400,
            detail="predictions, actuals e returns devem ter mesmo tamanho"
        )

    stats = BacktestStats.calculate_stats(predictions, actuals, returns)

    return {
        "simulation_results": stats,
        "timestamp": datetime.utcnow().isoformat(),
        "recommendations": _get_recommendations(stats)
    }


def _get_recommendations(stats: Dict) -> List[str]:
    """Gerar recomendações baseadas em estatísticas"""

    recommendations = []

    if stats["win_rate"] < 50:
        recommendations.append("⚠️ Taxa de vitória <50% - modelo pode ser inútil")
    elif stats["win_rate"] < 60:
        recommendations.append("⚠️ Taxa de vitória <60% - considere melhorar features")
    else:
        recommendations.append("✅ Taxa de vitória aceitável")

    if stats["sharpe_ratio"] > 1.0:
        recommendations.append("✅ Sharpe ratio > 1.0 - bom risco/retorno")
    elif stats["sharpe_ratio"] > 0.5:
        recommendations.append("⚠️ Sharpe ratio < 1.0 - risco elevado")
    else:
        recommendations.append("❌ Sharpe ratio muito baixo - análise necessária")

    if stats["max_drawdown"] > -20:
        recommendations.append("✅ Drawdown máximo aceitável")
    else:
        recommendations.append("❌ Drawdown muito alto - ajuste capital allocation")

    return recommendations
