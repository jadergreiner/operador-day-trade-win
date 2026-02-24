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
from typing import Dict, Any, Optional
import json
import pickle
from datetime import datetime
import hashlib

import pandas as pd
import numpy as np
from pandas import DataFrame

# Configurar logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-8s | %(message)s"
)
logger = logging.getLogger(__name__)


class ScoreT60Inference:
    """
    Executor de inferência para Score T+60 em tempo real.

    Pipeline:
    1. Carregar modelo + metadados
    2. Extrair últimas 60 velas M1
    3. Extrair 25 features
    4. Normalizar com scaler do modelo
    5. Fazer predição
    6. Salvar resultado em JSON

    Attributes:
        model: Modelo XGBoost carregado
        scaler: StandardScaler do treino
        metadata: Metadados do modelo
        last_score: Último score calculado
    """

    def __init__(self, model_path: str) -> None:
        """
        Inicializa inference engine.

        Args:
            model_path: Caminho para arquivo .pkl do modelo

        Raises:
            FileNotFoundError: Se modelo não existe
        """
        model_path = Path(model_path)

        if not model_path.exists():
            raise FileNotFoundError(f"Modelo não encontrado: {model_path}")

        logger.info(f"Carregando modelo: {model_path}")

        # Carregar modelo
        with open(model_path, "rb") as f:
            self.model = pickle.load(f)

        # Carregar metadados
        metadata_path = model_path.with_suffix(".json")
        if metadata_path.exists():
            with open(metadata_path, "r") as f:
                self.metadata = json.load(f)
        else:
            self.metadata = None

        # Reconstruir scaler a partir de metadados
        if self.metadata:
            from sklearn.preprocessing import StandardScaler
            self.scaler = StandardScaler()
            self.scaler.mean_ = np.array(self.metadata.get("scaler_mean", []))
            self.scaler.scale_ = np.array(self.metadata.get("scaler_std", []))
        else:
            self.scaler = None

        self.last_score: Optional[Dict[str, Any]] = None

        logger.info("✅ Modelo carregado com sucesso")

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
            0  # placeholder para 25º feature
        ])

        return features

    def predict_from_df(
        self,
        df_m1: DataFrame,
        use_last_n_rows: int = 60
    ) -> Dict[str, Any]:
        """
        Faz predição a partir de DataFrame M1.

        Args:
            df_m1: DataFrame com velas M1
            use_last_n_rows: Número de velas anteriores (default 60)

        Returns:
            Dicionário com score, classe, confiança
        """
        logger.info(f"Fazendo predição com últimas {use_last_n_rows} velas...")

        if len(df_m1) < use_last_n_rows:
            raise ValueError(
                f"DataFrame tem apenas {len(df_m1)} velas, "
                f"precisamos de {use_last_n_rows}"
            )

        # Pegar últimas N velas
        df_window = df_m1.tail(use_last_n_rows).copy()

        # Extrair features
        features = self._extract_features_from_window(df_window)

        # Reshape e normalizar
        X = features.reshape(1, -1)
        if self.scaler is not None:
            X = self.scaler.transform(X)

        # Predição
        score_raw = self.model.predict_proba(X)[0, 1]  # Probabilidade classe 1 (BULL)

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

        # Calcular hash de features para auditoria
        features_hash = hashlib.md5(str(features).encode()).hexdigest()[:8]

        result = {
            "timestamp": datetime.now().isoformat(),
            "score_t60": float(score_raw),
            "classe": classe,
            "confianca": confianca,
            "model_version": self.metadata.get("model_type", "unknown")
            if self.metadata else "unknown",
            "velas_usadas": use_last_n_rows,
            "features_hash": features_hash
        }

        self.last_score = result

        logger.info(
            f"✅ Predição: {classe} (score={score_raw:.2f}, conf={confianca})"
        )

        return result

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
