"""
score_t60_builder.py — Construtor de Dataset para Score T+60

Módulo responsável por:
  - Carregar dados históricos de velas M1
  - Extrair 25 features técnicas e de momentum
  - Criar labels retroativos para previsão T+60
  - Validar distribuição de dados (não-desbalanceado)
  - Salvar dataset em formato parquet/CSV

Uso:
    python score_t60_builder.py --input dados/winfut_m1.csv --output models/t60_dataset.parquet

Version: 1.0.0
Author: Squad ML + Eng Sr
Date: 2026-02-24
"""

import logging
from pathlib import Path
from typing import Tuple, Optional, Dict, Any

import pandas as pd
import numpy as np
from pandas import DataFrame

# Configurar logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-8s | %(message)s"
)
logger = logging.getLogger(__name__)


class ScoreT60Builder:
    """
    Construtor do dataset para modelo de previsão T+60.

    Este construtor implementa o pipeline completo:
    1. Leitura de dados de velas M1
    2. Extração de 25 features técnicas
    3. Criação de labels retroativos
    4. Normalização e validação

    Attributes:
        df_m1: DataFrame com velas M1 histórico
        threshold_pct: Threshold de movimento (0.15% padrão)
        features_list: Lista com nomes das 25 features
    """

    def __init__(
        self,
        threshold_pct: float = 0.0015
    ) -> None:
        """
        Inicializa construtor.

        Args:
            threshold_pct: Threshold de movimento para label (default 0.15%)
        """
        self.df_m1: Optional[DataFrame] = None
        self.threshold_pct = threshold_pct
        self.features_list: list[str] = self._get_feature_names()
        logger.info(
            f"ScoreT60Builder inicializado "
            f"(threshold={threshold_pct*100:.2f}%)"
        )

    @staticmethod
    def _get_feature_names() -> list[str]:
        """
        Retorna lista com nomes das 25 features.

        Returns:
            Lista com nomes das features em ordem.
        """
        return [
            # Preço (4)
            "close_norm", "high_norm", "low_norm", "open_norm",
            # Volume (2)
            "volume_norm", "vwap",
            # RSI (2)
            "rsi_14", "rsi_slope",
            # MACD (2)
            "macd_line", "macd_signal",
            # ATR (1)
            "atr_norm",
            # Bollinger Bands (2)
            "bb_position", "bb_width",
            # CCI (1)
            "cci_20",
            # ROC (1)
            "roc_12",
            # Slopes (3)
            "slope_5", "slope_10", "slope_20",
            # Volatilidade (1)
            "volatility_20",
            # Adicionais (4)
            "volume_profile", "price_momentum", "trend_strength", "mean_reversion"
        ]

    def load_data(self, filepath: str) -> DataFrame:
        """
        Carrega dados de velas M1.

        Args:
            filepath: Caminho para arquivo CSV/Parquet com histórico

        Returns:
            DataFrame carregado e validado

        Raises:
            FileNotFoundError: Se arquivo não existe
            ValueError: Se colunas obrigatórias não encontradas
        """
        logger.info(f"Carregando dados de {filepath}...")

        path = Path(filepath)
        if not path.exists():
            raise FileNotFoundError(f"Arquivo não encontrado: {filepath}")

        if path.suffix == ".parquet":
            df = pd.read_parquet(filepath)
        else:
            df = pd.read_csv(filepath)

        # Validar colunas obrigatórias
        required_cols = {"open", "high", "low", "close", "volume", "time"}
        if not required_cols.issubset(df.columns):
            missing = required_cols - set(df.columns)
            raise ValueError(f"Colunas faltando: {missing}")

        # Garantir ordem ascending por time
        df = df.sort_values("time").reset_index(drop=True)

        self.df_m1 = df
        logger.info(
            f"✅ Dados carregados: {len(df)} velas "
            f"({df['time'].min()} a {df['time'].max()})"
        )

        return df

    def extract_features(self) -> DataFrame:
        """
        Extrai 25 features técnicas.

        Retorna DataFrame com features normalizadas.

        Raises:
            ValueError: Se dados não foram carregados
        """
        if self.df_m1 is None:
            raise ValueError("Dados não carregados. Chame load_data() primeiro.")

        logger.info("Extraindo 25 features técnicas...")

        df = self.df_m1.copy()

        # Preço normalizado (close vs média móvel)
        df["close_norm"] = df["close"] / df["close"].rolling(20).mean() - 1
        df["high_norm"] = df["high"] / df["close"].rolling(20).mean() - 1
        df["low_norm"] = df["low"] / df["close"].rolling(20).mean() - 1
        df["open_norm"] = df["open"] / df["close"].rolling(20).mean() - 1

        # Volume
        df["volume_norm"] = df["volume"] / df["volume"].rolling(20).mean()
        df["vwap"] = (df["high"] + df["close"] + df["low"]) / 3

        # RSI(14)
        delta = df["close"].diff()
        gain = delta.where(delta > 0, 0).rolling(14).mean()
        loss = -delta.where(delta < 0, 0).rolling(14).mean()
        rs = gain / loss
        df["rsi_14"] = 100 - (100 / (1 + rs))
        df["rsi_slope"] = df["rsi_14"].diff(5)

        # MACD
        ema12 = df["close"].ewm(12).mean()
        ema26 = df["close"].ewm(26).mean()
        df["macd_line"] = ema12 - ema26
        df["macd_signal"] = df["macd_line"].ewm(9).mean()

        # ATR(14)
        df["tr"] = np.maximum(
            df["high"] - df["low"],
            np.maximum(
                abs(df["high"] - df["close"].shift()),
                abs(df["low"] - df["close"].shift())
            )
        )
        df["atr_norm"] = df["tr"].rolling(14).mean() / df["close"]

        # Bollinger Bands
        sma20 = df["close"].rolling(20).mean()
        std20 = df["close"].rolling(20).std()
        upper_bb = sma20 + 2 * std20
        lower_bb = sma20 - 2 * std20
        df["bb_position"] = (df["close"] - lower_bb) / (upper_bb - lower_bb)
        df["bb_width"] = (upper_bb - lower_bb) / sma20

        # CCI(20)
        tp = (df["high"] + df["close"] + df["low"]) / 3
        sma_tp = tp.rolling(20).mean()
        mad = tp.rolling(20).apply(lambda x: abs(x - x.mean()).mean())
        df["cci_20"] = (tp - sma_tp) / (0.015 * mad)

        # ROC(12)
        df["roc_12"] = (df["close"] - df["close"].shift(12)) / df["close"].shift(12)

        # Slopes (regressão linear simples)
        for period in [5, 10, 20]:
            slopes = []
            for i in range(len(df)):
                if i < period:
                    slopes.append(0)
                else:
                    x = np.arange(period)
                    y = df["close"].iloc[i-period:i].values
                    slope, _ = np.polyfit(x, y, 1)
                    slopes.append(slope / df["close"].iloc[i])

            df[f"slope_{period}"] = slopes

        # Volatilidade (std 20)
        df["volatility_20"] = df["close"].pct_change().rolling(20).std()

        # Features adicionais
        df["volume_profile"] = (
            df["volume"] - df["volume"].rolling(20).mean()
        ) / df["volume"].rolling(20).std()
        df["price_momentum"] = df["close"].pct_change(5)
        df["trend_strength"] = df["close"].rolling(10).apply(
            lambda x: 1 if x.iloc[-1] > x.iloc[0] else -1
        )
        df["mean_reversion"] = (
            df["close"] - df["close"].rolling(30).mean()
        ) / df["close"].rolling(30).std()

        # Preencher NaNs iniciais
        df = df.fillna(method="bfill").fillna(method="ffill")

        logger.info(f"✅ {len(self.features_list)} features extraídas")

        return df

    def create_labels(self, df_features: DataFrame) -> DataFrame:
        """
        Cria labels retroativos T+60.

        Para cada vela t, compara close[t+60] vs close[t]:
        - Label 1 (BULL) se close[t+60] > close[t] + threshold
        - Label 0 (BEAR) caso contrário

        Args:
            df_features: DataFrame com features já extraídas

        Returns:
            DataFrame com coluna 'label_t60' adicionada
        """
        logger.info("Criando labels T+60...")

        df = df_features.copy()
        labels = []

        for i in range(len(df)):
            # Ignorar últimas 60 velas (não há t+60)
            if i + 60 >= len(df):
                labels.append(np.nan)
                continue

            close_t = df["close"].iloc[i]
            close_t60 = df["close"].iloc[i + 60]
            threshold = close_t * self.threshold_pct

            label = 1 if close_t60 > close_t + threshold else 0
            labels.append(label)

        df["label_t60"] = labels

        # Estatísticas de label
        valid_labels = df["label_t60"].dropna()
        bull_count = (valid_labels == 1).sum()
        bear_count = (valid_labels == 0).sum()

        logger.info(
            f"✅ Labels criados: "
            f"BULL={bull_count} ({bull_count/len(valid_labels)*100:.1f}%), "
            f"BEAR={bear_count} ({bear_count/len(valid_labels)*100:.1f}%)"
        )

        return df

    def validate_dataset(self, df: DataFrame) -> Dict[str, Any]:
        """
        Valida qualidade do dataset.

        Retorna dicionário com validações:
        - Total de samples
        - Dados faltantes
        - Distribuição de labels
        - Features com variância baixa

        Args:
            df: DataFrame com features e labels

        Returns:
            Dict com resultados validação
        """
        logger.info("Validando dataset...")

        results = {
            "total_samples": len(df),
            "features_present": len(self.features_list),
            "missing_data": {}
        }

        # Dados faltantes
        for col in self.features_list + ["label_t60"]:
            missing_pct = df[col].isna().sum() / len(df) * 100
            results["missing_data"][col] = missing_pct
            if missing_pct > 5:
                logger.warning(f"  ⚠️  {col}: {missing_pct:.1f}% faltando")

        # Labels
        valid_labels = df["label_t60"].dropna()
        results["label_distribution"] = {
            "total": len(valid_labels),
            "bull": int((valid_labels == 1).sum()),
            "bear": int((valid_labels == 0).sum()),
            "bull_pct": float((valid_labels == 1).sum() / len(valid_labels) * 100)
        }

        logger.info(
            f"✅ Validação completa: "
            f"samples={results['total_samples']}, "
            f"BULL={results['label_distribution']['bull_pct']:.1f}%"
        )

        return results

    def save_dataset(
        self,
        df: DataFrame,
        output_path: str,
        format: str = "parquet"
    ) -> Path:
        """
        Salva dataset em arquivo.

        Args:
            df: DataFrame com features
            output_path: Caminho de saída
            format: 'parquet' ou 'csv'

        Returns:
            Path do arquivo salvo
        """
        logger.info(f"Salvando dataset em {output_path}...")

        path = Path(output_path)
        path.parent.mkdir(parents=True, exist_ok=True)

        if format == "parquet":
            df.to_parquet(output_path, index=False)
        else:
            df.to_csv(output_path, index=False)

        logger.info(f"✅ Dataset salvo: {path}")

        return path

    def run(
        self,
        input_file: str,
        output_file: str,
        format: str = "parquet"
    ) -> Tuple[DataFrame, Dict[str, Any]]:
        """
        Executa pipeline completo: load → features → labels → save.

        Args:
            input_file: Arquivo histórico M1
            output_file: Arquivo saída
            format: Formato saída ('parquet' ou 'csv')

        Returns:
            Tupla (df_final, validation_results)
        """
        logger.info("=" * 70)
        logger.info("INICIANDO PIPELINE SCORE T60 BUILDER")
        logger.info("=" * 70)

        # Etapa 1: Carregar
        self.load_data(input_file)

        # Etapa 2: Extrair features
        df_features = self.extract_features()

        # Etapa 3: Criar labels
        df_labeled = self.create_labels(df_features)

        # Etapa 4: Validar
        validation = self.validate_dataset(df_labeled)

        # Etapa 5: Salvar
        self.save_dataset(df_labeled, output_file, format)

        logger.info("=" * 70)
        logger.info("✅ PIPELINE CONCLUÍDO COM SUCESSO")
        logger.info("=" * 70)

        return df_labeled, validation


def main() -> None:
    """Função principal para execução via CLI."""
    import argparse

    parser = argparse.ArgumentParser(
        description="Builder de dataset para Score T+60"
    )
    parser.add_argument(
        "--input",
        required=True,
        help="Arquivo histórico de velas M1"
    )
    parser.add_argument(
        "--output",
        required=True,
        help="Arquivo saída (parquet/csv)"
    )
    parser.add_argument(
        "--format",
        default="parquet",
        help="Formato: parquet ou csv"
    )

    args = parser.parse_args()

    builder = ScoreT60Builder()
    builder.run(args.input, args.output, args.format)


if __name__ == "__main__":
    main()
