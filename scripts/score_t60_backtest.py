"""
score_t60_backtest.py — Backteste e Validação do Modelo T+60

Módulo responsável por:
  - Rodar modelo contra últimos 10 dias históricos
  - Calcular taxa de acertos (target ≥60%)
  - Validar contra realidade de preço
  - Gerar relatório de hits/misses

Uso:
    python score_t60_backtest.py --model models/score_t60_v1.0.pkl --data dados/ultimos_10_dias.csv

Version: 1.0.0
Author: Squad ML + QA
Date: 2026-02-24
"""

import logging
from pathlib import Path
from typing import Dict, Any, Optional, List
import json
from datetime import datetime, timedelta

import pandas as pd
import numpy as np
from pandas import DataFrame

# Configurar logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-8s | %(message)s"
)
logger = logging.getLogger(__name__)


class ScoreT60Backtest:
    """
    Validador de modelo T+60 contra histórico.

    Pipeline:
    1. Carregar últimos 10 dias de M1
    2. Para cada hora, fazer predição
    3. Comparar predição vs realidade (close[h+1] vs close[h])
    4. Calcular taxa de acertos
    5. Gerar relatório

    Attributes:
        df_m1: DataFrame com histórico
        results: Lista com resultados backtest
        accuracy: Taxa de acerto geral
    """

    def __init__(self) -> None:
        """Inicializa backtest runner."""
        self.df_m1: Optional[DataFrame] = None
        self.results: List[Dict[str, Any]] = []
        self.accuracy = 0.0
        logger.info("ScoreT60Backtest inicializado")

    def load_data(self, filepath: str) -> DataFrame:
        """
        Carrega histórico M1.

        Args:
            filepath: Arquivo CSV/Parquet

        Returns:
            DataFrame carregado
        """
        logger.info(f"Carregando histórico: {filepath}")

        path = Path(filepath)

        if path.suffix == ".parquet":
            df = pd.read_parquet(filepath)
        else:
            df = pd.read_csv(filepath)

        df = df.sort_values("time").reset_index(drop=True)
        self.df_m1 = df

        logger.info(f"✅ {len(df)} velas carregadas")

        return df

    def _get_recent_window(
        self,
        df: DataFrame,
        row_idx: int,
        window_size: int = 60
    ) -> Optional[DataFrame]:
        """
        Retorna janela de velas anteriores para uma vela específica.

        Args:
            df: DataFrame completo
            row_idx: Índice da vela
            window_size: Tamanho da janela (default 60)

        Returns:
            DataFrame com janela ou None se impossível
        """
        if row_idx < window_size:
            return None

        return df.iloc[row_idx - window_size : row_idx].copy()

    def _extract_simple_features(
        self,
        window_df: DataFrame
    ) -> np.ndarray:
        """
        Extrai features de forma simplificada (rápido para backtest).

        Args:
            window_df: Janela de 60 velas

        Returns:
            Array com features
        """
        # Usar feature básicas para speed
        # (versão completa seria igual ao inference.py)

        features = []

        # Close normalizado
        close_norm = (
            window_df["close"].iloc[-1] / window_df["close"].rolling(20).mean().iloc[-1] - 1
        )
        features.append(close_norm)

        # RSI simples
        delta = window_df["close"].diff()
        gain = delta.where(delta > 0, 0).rolling(14).mean()
        loss = -delta.where(delta < 0, 0).rolling(14).mean()
        rs = gain / loss
        rsi_14 = 100 - (100 / (1 + rs.iloc[-1]))
        features.append(rsi_14)

        # Volume
        volume_norm = (
            window_df["volume"].iloc[-1] /
            window_df["volume"].rolling(20).mean().iloc[-1]
        )
        features.append(volume_norm)

        # Continuar com restante das features
        # (simplificado para este exemplo)
        while len(features) < 25:
            features.append(0.0)

        return np.array(features)

    def run_backtest(
        self,
        model_path: str,
        lookback_days: int = 10
    ) -> Dict[str, Any]:
        """
        Executa backtest contra histórico.

        Args:
            model_path: Caminho para modelo .pkl
            lookback_days: Dias para trás (default 10)

        Returns:
            Dicionário com resultado backtest
        """
        if self.df_m1 is None:
            raise ValueError("Dados não carregados")

        logger.info(f"Iniciando backtest ({lookback_days} últimos dias)...")

        # Carregar modelo
        import pickle
        if not Path(model_path).exists():
            logger.error(f"Modelo não encontrado: {model_path}")
            return {"error": "Modelo não encontrado"}

        with open(model_path, "rb") as f:
            model = pickle.load(f)

        logger.info("Modelo carregado")

        # Filtrar últimas 10 dias (assumir 1440 min/dia)
        min_row = max(0, len(self.df_m1) - (lookback_days * 1440))
        df_backtest = self.df_m1.iloc[min_row:].copy()

        logger.info(f"Testando em {len(df_backtest)} velas")

        # Para cada vela, fazer predição e comparar com próxima
        correct = 0
        total = 0

        for idx in range(len(df_backtest) - 1):
            # Pegar janela
            window = self._get_recent_window(df_backtest, idx + 1)
            if window is None:
                continue

            # Features
            features = self._extract_simple_features(window)
            X = features.reshape(1, -1)

            # Predição
            try:
                score = model.predict_proba(X)[0, 1]
                pred_class = 1 if score > 0.5 else 0
            except Exception as e:
                logger.warning(f"Erro em predição: {e}")
                continue

            # Realidade
            close_t = df_backtest["close"].iloc[idx]
            close_t1 = df_backtest["close"].iloc[idx + 1]
            real_class = 1 if close_t1 > close_t else 0

            # Registrar
            acerto = pred_class == real_class
            if acerto:
                correct += 1

            total += 1

            self.results.append({
                "idx": idx,
                "score": float(score),
                "pred_class": int(pred_class),
                "real_class": int(real_class),
                "acerto": bool(acerto)
            })

        # Calcular acurácia
        self.accuracy = correct / total * 100 if total > 0 else 0

        logger.info(
            f"✅ Backtest completo: {correct}/{total} acertos "
            f"({self.accuracy:.1f}%)"
        )

        # Determinar resultado
        status = "PASS" if self.accuracy >= 60 else "FAIL"

        return {
            "status": status,
            "accuracy_pct": self.accuracy,
            "correct": correct,
            "total": total,
            "results": self.results[:10]  # Primeiros 10 para debug
        }

    def save_results(self, output_path: str) -> Path:
        """
        Salva resultados backtest em JSON.

        Args:
            output_path: Caminho arquivo saída

        Returns:
            Path do arquivo
        """
        logger.info(f"Salvando resultados em {output_path}...")

        path = Path(output_path)
        path.parent.mkdir(parents=True, exist_ok=True)

        output_dict = {
            "timestamp": datetime.now().isoformat(),
            "accuracy_pct": self.accuracy,
            "total_predictions": len(self.results),
            "results": self.results
        }

        with open(path, "w") as f:
            json.dump(output_dict, f, indent=2)

        logger.info(f"✅ Resultados salvos: {path}")

        return path

    def run(
        self,
        model_path: str,
        data_path: str,
        output_path: str = None
    ) -> Dict[str, Any]:
        """
        Executa pipeline completo: load → backtest → save.

        Args:
            model_path: Arquivo modelo (.pkl)
            data_path: Arquivo histórico M1
            output_path: Arquivo saída JSON (optional)

        Returns:
            Resultado backtest
        """
        logger.info("=" * 70)
        logger.info("INICIANDO PIPELINE SCORE T60 BACKTEST")
        logger.info("=" * 70)

        # Carregar dados
        self.load_data(data_path)

        # Rodar backtest
        result = self.run_backtest(model_path)

        # Salvar
        if output_path:
            self.save_results(output_path)

        logger.info("=" * 70)
        logger.info("✅ PIPELINE CONCLUÍDO")
        logger.info("=" * 70)

        return result


def main() -> None:
    """Função principal CLI."""
    import argparse

    parser = argparse.ArgumentParser(
        description="Backtest e Validação Score T+60"
    )
    parser.add_argument(
        "--model",
        required=True,
        help="Arquivo modelo (.pkl)"
    )
    parser.add_argument(
        "--data",
        required=True,
        help="Arquivo histórico M1 (CSV/Parquet)"
    )
    parser.add_argument(
        "--output",
        help="Arquivo saída JSON"
    )

    args = parser.parse_args()

    backtest = ScoreT60Backtest()
    backtest.run(args.model, args.data, args.output)


if __name__ == "__main__":
    main()
