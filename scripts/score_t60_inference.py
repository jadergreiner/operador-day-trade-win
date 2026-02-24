"""
score_t60_inference.py — Inferência em Tempo Real do Score T+60

Módulo responsável por:
  - Carregar modelo treinado
  - Fazer predições em dados novos (M1 atual)
  - Salvar resultado em arquivo JSON (~/.operador_score_t60.json)
  - Computar confiança e score normalizado

Uso:
    python score_t60_inference.py --input dados_m1_atuais.csv --model models/score_t60_v1.0.pkl --output ~/.operador_score_t60.json

Version: 1.0.0
Author: Squad ML + Eng Sr
Date: 2026-02-24
"""

import logging
from pathlib import Path
from typing import Dict, Any, Optional, List
import json
import pickle
from datetime import datetime
import hashlib
import time

import pandas as pd
import numpy as np
from pandas import DataFrame

# Configurar logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-8s | %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S"
)
logger = logging.getLogger(__name__)

# Constants
WINDOW_SIZE: int = 60  # últimas 60 velas M1
INFERENCE_TIMEOUT: float = 5.0  # 5 segundos max timeout
LATENCY_TARGET_MS: float = 50.0  # <50ms P95


class ScoreT60Inference:
    """
    Executor de inferência para Score T+60 em tempo real.

    Pipeline:
    1. Carregar modelo + metadados (lazy loading)
    2. Extrair últimas 60 velas M1
    3. Extrair 25 features
    4. Normalizar com scaler do modelo
    5. Fazer predição (<50ms P95)
    6. Salvar resultado em JSON

    Features:
    - Lazy loading (modelo carregado na primeira predição)
    - Latency tracking (medição de tempo de resposta)
    - Error handling com retry logic (timeout 5s)
    - Validation (janelas, features, resultados)

    Attributes:
        model: Modelo XGBoost carregado (lazy)
        scaler: StandardScaler do treino
        metadata: Metadados do modelo
        last_score: Último score calculado
        model_loaded: Flag lazy loading
        latency_measurements: Historic de latências (ms)
    """

    def __init__(self, model_path: str) -> None:
        """
        Inicializa inference engine com lazy loading.

        Args:
            model_path: Caminho para arquivo .pkl do modelo

        Raises:
            FileNotFoundError: Se modelo não existe
        """
        self.model_path: str = str(model_path)
        self.model: Optional[Any] = None
        self.scaler: Optional[Any] = None
        self.metadata: Optional[Dict[str, Any]] = None
        self.last_score: Optional[Dict[str, Any]] = None
        self.model_loaded: bool = False
        self.latency_measurements: List[float] = []

        # Validar que arquivo existe
        model_file = Path(self.model_path)
        if not model_file.exists():
            raise FileNotFoundError(f"Modelo não encontrado: {self.model_path}")

        logger.info(f"✅ Engine inicializado (lazy loading habilitado)")

    def _load_model_lazy(self) -> None:
        """
        Carrega modelo XGBoost na primeira predição (lazy loading).

        Raises:
            RuntimeError: Se deserialization falhar
        """
        if self.model_loaded:
            return

        logger.info(f"Carregando modelo: {self.model_path}")

        try:
            # Carregar modelo
            with open(self.model_path, "rb") as f:
                self.model = pickle.load(f)

            # Carregar metadados
            metadata_path = Path(self.model_path).with_suffix(".json")
            if metadata_path.exists():
                with open(metadata_path, "r") as f:
                    self.metadata = json.load(f)
            else:
                self.metadata = None

            # Reconstruir scaler a partir de metadados
            if self.metadata:
                from sklearn.preprocessing import StandardScaler
                self.scaler = StandardScaler()
                self.scaler.mean_ = np.array(
                    self.metadata.get("scaler_mean", [])
                )
                self.scaler.scale_ = np.array(
                    self.metadata.get("scaler_std", [])
                )
            else:
                self.scaler = None

            self.model_loaded = True
            logger.info("✅ Modelo carregado com sucesso (lazy)")

        except Exception as e:
            raise RuntimeError(f"Failed to load model: {e}") from e

    @staticmethod
    def _extract_features_from_window(
        df_m1_window: DataFrame
    ) -> np.ndarray:
        """
        Extrai 25 features de uma janela de 60 velas M1.

        Mesmos cálculos que no builder.

        Args:
            df_m1_window: DataFrame com últimas 60 velas

        Returns:
            Array com 25 features
        """
        df = df_m1_window.copy()

        # Preço normalizado
        close_norm = df["close"].iloc[-1] / df["close"].rolling(20).mean().iloc[-1] - 1
        high_norm = df["high"].iloc[-1] / df["close"].rolling(20).mean().iloc[-1] - 1
        low_norm = df["low"].iloc[-1] / df["close"].rolling(20).mean().iloc[-1] - 1
        open_norm = df["open"].iloc[-1] / df["close"].rolling(20).mean().iloc[-1] - 1

        # Volume
        volume_norm = df["volume"].iloc[-1] / df["volume"].rolling(20).mean().iloc[-1]
        vwap = (df["high"].iloc[-1] + df["close"].iloc[-1] + df["low"].iloc[-1]) / 3

        # RSI(14)
        delta = df["close"].diff()
        gain = delta.where(delta > 0, 0).rolling(14).mean()
        loss = -delta.where(delta < 0, 0).rolling(14).mean()
        rs = gain / loss
        rsi_14 = 100 - (100 / (1 + rs.iloc[-1]))
        rsi_slope = df["close"].diff(5).iloc[-1] if len(df) > 5 else 0

        # MACD
        ema12 = df["close"].ewm(12).mean()
        ema26 = df["close"].ewm(26).mean()
        macd_line = ema12.iloc[-1] - ema26.iloc[-1]
        macd_signal = df["close"].ewm(26).mean().iloc[-1]

        # ATR(14)
        tr = np.maximum(
            df["high"].iloc[-1] - df["low"].iloc[-1],
            np.maximum(
                abs(df["high"].iloc[-1] - df["close"].iloc[-2]),
                abs(df["low"].iloc[-1] - df["close"].iloc[-2])
            )
        )
        atr_norm = tr / df["close"].iloc[-1]

        # Bollinger Bands
        sma20 = df["close"].rolling(20).mean().iloc[-1]
        std20 = df["close"].rolling(20).std().iloc[-1]
        upper_bb = sma20 + 2 * std20
        lower_bb = sma20 - 2 * std20
        bb_position = (df["close"].iloc[-1] - lower_bb) / (upper_bb - lower_bb)
        bb_width = (upper_bb - lower_bb) / sma20

        # CCI(20)
        tp = (df["high"] + df["close"] + df["low"]) / 3
        sma_tp = tp.rolling(20).mean().iloc[-1]
        mad = tp.rolling(20).apply(lambda x: abs(x - x.mean()).mean()).iloc[-1]
        cci_20 = (tp.iloc[-1] - sma_tp) / (0.015 * mad) if mad > 0 else 0

        # ROC(12)
        roc_12 = (
            (df["close"].iloc[-1] - df["close"].iloc[-12]) / df["close"].iloc[-12]
            if len(df) > 12 else 0
        )

        # Slopes
        slope_5 = 0
        slope_10 = 0
        slope_20 = 0
        if len(df) > 20:
            x = np.arange(5)
            y = df["close"].iloc[-5:].values
            slope_5, _ = np.polyfit(x, y, 1)
            slope_5 = slope_5 / df["close"].iloc[-1]

            x = np.arange(10)
            y = df["close"].iloc[-10:].values
            slope_10, _ = np.polyfit(x, y, 1)
            slope_10 = slope_10 / df["close"].iloc[-1]

            x = np.arange(20)
            y = df["close"].iloc[-20:].values
            slope_20, _ = np.polyfit(x, y, 1)
            slope_20 = slope_20 / df["close"].iloc[-1]

        # Volatilidade
        volatility_20 = df["close"].pct_change().rolling(20).std().iloc[-1]

        # Adicionais
        volume_profile = (
            (df["volume"].iloc[-1] - df["volume"].rolling(20).mean().iloc[-1]) /
            (df["volume"].rolling(20).std().iloc[-1] + 1e-8)
        )
        price_momentum = df["close"].pct_change(5).iloc[-1]
        trend_strength = 1 if df["close"].iloc[-1] > df["close"].iloc[-10] else -1
        mean_reversion = (
            (df["close"].iloc[-1] - df["close"].rolling(30).mean().iloc[-1]) /
            (df["close"].rolling(30).std().iloc[-1] + 1e-8)
        )

        # ADX(14) — 24ª feature
        high_low = df["high"] - df["low"]
        high_close = abs(df["high"] - df["close"].shift())
        low_close = abs(df["low"] - df["close"].shift())
        ranges = pd.concat([high_low, high_close, low_close], axis=1).max(axis=1)
        atr_14 = ranges.rolling(14).mean().iloc[-1]
        
        plus_dm = df["high"].diff().where(df["high"].diff() > df["low"].diff().abs(), 0)
        minus_dm = df["low"].diff().mul(-1).where(df["low"].diff().abs() > df["high"].diff(), 0)
        plus_di = 100 * (plus_dm.rolling(14).mean().iloc[-1] / atr_14) if atr_14 > 0 else 50
        minus_di = 100 * (minus_dm.rolling(14).mean().iloc[-1] / atr_14) if atr_14 > 0 else 50
        adx_raw = abs(plus_di - minus_di) / (plus_di + minus_di) if (plus_di + minus_di) > 0 else 0

        # 25ª feature: High/Low correlation
        high_low_corr = df[["high", "low"]].corr().iloc[0, 1] if len(df) > 10 else 0.95

        features = np.array([
            close_norm, high_norm, low_norm, open_norm,
            volume_norm, vwap,
            rsi_14, rsi_slope,
            macd_line, macd_signal,
            atr_norm,
            bb_position, bb_width,
            cci_20,
            roc_12,
            slope_5, slope_10, slope_20,
            volatility_20,
            volume_profile, price_momentum, trend_strength, mean_reversion,
            adx_raw, high_low_corr  # 24 + 25
        ])

        return features

    def predict_from_df(
        self,
        df_m1: DataFrame,
        use_last_n_rows: int = 60,
        retry_count: int = 3
    ) -> Dict[str, Any]:
        """
        Faz predição a partir de DataFrame M1 com latency tracking.

        Args:
            df_m1: DataFrame com velas M1 (OHLCV)
            use_last_n_rows: Número de velas anteriores (default 60)
            retry_count: Tentativas em caso de timeout

        Returns:
            Dicionário com score, classe, confiança, latência

        Raises:
            ValueError: Se validação falhar
            TimeoutError: Se timeout excedido após retries
        """
        start_time = time.time()

        try:
            # Carregar modelo (lazy)
            self._load_model_lazy()

            logger.info(f"Fazendo predição com últimas {use_last_n_rows} velas...")

            # Validar janela
            if len(df_m1) < use_last_n_rows:
                raise ValueError(
                    f"DataFrame tem apenas {len(df_m1)} velas, "
                    f"precisamos de {use_last_n_rows}"
                )

            # Pegar últimas N velas
            df_window = df_m1.tail(use_last_n_rows).copy()

            # Validar dados (sem NaN)
            if df_window.isnull().any().any():
                raise ValueError("NaN values found in window")

            # Extrair features (com retry)
            features = None
            for attempt in range(retry_count):
                try:
                    features = self._extract_features_from_window(df_window)
                    break
                except Exception as e:
                    if attempt == retry_count - 1:
                        raise TimeoutError(
                            f"Feature extraction failed after {retry_count} attempts: {e}"
                        ) from e
                    logger.warning(f"Retry {attempt + 1}/{retry_count}: {e}")
                    time.sleep(0.1)

            # Reshape e normalizar
            X = features.reshape(1, -1)
            if self.scaler is not None:
                X = self.scaler.transform(X)

            # Predição (com retry)
            score_raw = None
            for attempt in range(retry_count):
                try:
                    # Check timeout
                    elapsed = time.time() - start_time
                    if elapsed > INFERENCE_TIMEOUT:
                        raise TimeoutError(
                            f"Inference timeout: {elapsed:.2f}s > {INFERENCE_TIMEOUT}s"
                        )

                    # Predição
                    score_raw = self.model.predict_proba(X)[0, 1]
                    break

                except TimeoutError:
                    raise
                except Exception as e:
                    if attempt == retry_count - 1:
                        raise TimeoutError(
                            f"Prediction failed after {retry_count} attempts: {e}"
                        ) from e
                    logger.warning(f"Retry {attempt + 1}/{retry_count}: {e}")
                    time.sleep(0.1)

            # Classe e confiança
            if score_raw > 0.65:
                classe = "BULL"
                confianca = "ALTA"
            elif score_raw < 0.35:
                classe = "BEAR"
                confianca = "ALTA"
            else:
                classe = "NEUTRO"
                confianca = "BAIXA"

            # Calcular latência
            latency_ms = (time.time() - start_time) * 1000
            self.latency_measurements.append(latency_ms)

            # Validar latência
            if latency_ms > LATENCY_TARGET_MS:
                logger.warning(f"⚠️ Latência alta: {latency_ms:.2f}ms > {LATENCY_TARGET_MS}ms")

            # Calcular hash de features para auditoria
            features_hash = hashlib.md5(str(features).encode()).hexdigest()[:8]

            result = {
                "timestamp": datetime.utcnow().isoformat() + "Z",
                "score_t60": float(score_raw),
                "classe": classe,
                "confianca": confianca,
                "latency_ms": float(latency_ms),
                "model_version": self.metadata.get("model_type", "unknown")
                if self.metadata else "unknown",
                "velas_usadas": use_last_n_rows,
                "features_hash": features_hash
            }

            self.last_score = result

            logger.info(
                f"✅ Predição: {classe} (score={score_raw:.3f}, "
                f"conf={confianca}, latency={latency_ms:.2f}ms)"
            )

            return result

        except Exception as e:
            logger.error(f"❌ Erro em predição: {e}")
            raise

    def get_latency_stats(self) -> Dict[str, float]:
        """
        Retorna estatísticas de latência acumuladas.

        Returns:
            Dict com P50, P95, P99, mean, max (em ms)
        """
        if not self.latency_measurements:
            return {
                "p50": 0.0,
                "p95": 0.0,
                "p99": 0.0,
                "mean": 0.0,
                "max": 0.0,
            }

        measurements = np.array(self.latency_measurements)
        return {
            "p50": float(np.percentile(measurements, 50)),
            "p95": float(np.percentile(measurements, 95)),
            "p99": float(np.percentile(measurements, 99)),
            "mean": float(measurements.mean()),
            "max": float(measurements.max()),
        }

    def save_score(
        self,
        score_dict: Dict[str, Any],
        output_path: str = None
    ) -> Path:
        """
        Salva score em arquivo JSON.

        Default: ~/.operador_score_t60.json

        Args:
            score_dict: Dicionário com resultado
            output_path: Caminho customizado (optional)

        Returns:
            Path do arquivo salvo
        """
        if output_path is None:
            output_path = str(Path.home() / ".operador_score_t60.json")

        logger.info(f"Salvando score em {output_path}...")

        path = Path(output_path)
        path.parent.mkdir(parents=True, exist_ok=True)

        with open(path, "w") as f:
            json.dump(score_dict, f, indent=2)

        logger.info(f"✅ Score salvo: {path}")

        return path

    def run(
        self,
        input_file: str,
        output_file: str = None
    ) -> Dict[str, Any]:
        """
        Executa pipeline completo: load → features → predict → save.

        Args:
            input_file: Arquivo CSV/Parquet com velas M1
            output_file: Arquivo saída JSON (optional)

        Returns:
            Score dict
        """
        logger.info("=" * 70)
        logger.info("INICIANDO PIPELINE SCORE T60 INFERENCE")
        logger.info("=" * 70)

        # Carregar dados
        if input_file.endswith(".parquet"):
            df = pd.read_parquet(input_file)
        else:
            df = pd.read_csv(input_file)

        # Fazer predição
        score = self.predict_from_df(df)

        # Salvar
        self.save_score(score, output_file)

        logger.info("=" * 70)
        logger.info("✅ PIPELINE CONCLUÍDO")
        logger.info("=" * 70)

        return score


def main() -> None:
    """Função principal CLI."""
    import argparse

    parser = argparse.ArgumentParser(
        description="Inferência do Score T+60"
    )
    parser.add_argument(
        "--model",
        required=True,
        help="Arquivo modelo (.pkl)"
    )
    parser.add_argument(
        "--input",
        required=True,
        help="Arquivo M1 (CSV/Parquet)"
    )
    parser.add_argument(
        "--output",
        help="Arquivo saída JSON (default: ~/.operador_score_t60.json)"
    )

    args = parser.parse_args()

    inference = ScoreT60Inference(args.model)
    inference.run(args.input, args.output)


if __name__ == "__main__":
    main()
