"""
Testes unitarios para prepare_training_dataset() em data_loader.py

Cobertura dos 7 criterios de aceite:
- AC1: Dataset carregado com >= 1000 amostras
- AC2: Labeling ML consistente (0/1, sem NaN, imbalance 20-80%)
- AC3: 24 features extraidas
- AC4: Splits 70/15/15 com seed fixo
- AC5: feature_names.json salvo com 24 nomes
- Extra: dataset_labeled.pkl salvo
- Extra: FileNotFoundError para path invalido
"""

import json
import pickle
import numpy as np
import pandas as pd
import pytest
from pathlib import Path
from unittest.mock import patch

from src.application.data_loader import prepare_training_dataset


# ---------------------------------------------------------------------------
# Fixture: DataFrame falso com 1000 amostras e 24 features
# ---------------------------------------------------------------------------

NOMES_FEATURES = [
    "volatility_bollinger_upper",
    "volatility_bollinger_lower",
    "volatility_atr",
    "volatility_historical",
    "momentum_rsi",
    "momentum_macd",
    "momentum_roc",
    "momentum_obv",
    "ma_sma_50",
    "ma_ema_9",
    "ma_ema_21",
    "ma_slope_short",
    "ma_slope_long",
    "pattern_mean_reversion",
    "pattern_volume_spike",
    "pattern_impulse",
    "lag_return_1",
    "lag_return_2",
    "lag_close_1",
    "lag_close_2",
    "lag_volume_1",
    "lag_volume_2",
    "correlation_20d",
    "correlation_trend",
]


def _criar_dataframe_falso(qtd_amostras: int = 1000) -> pd.DataFrame:
    """Cria DataFrame sintetico com 1000 amostras, 24 features e label valido."""
    np.random.seed(42)
    dados = {"window_id": list(range(qtd_amostras))}
    for nome in NOMES_FEATURES:
        dados[nome] = np.random.uniform(-5.0, 5.0, qtd_amostras)
    # Labels balanceados: ~55% positivos para respeitar AC2 (20-80%)
    qtd_positivos = int(qtd_amostras * 0.55)
    rotulos = np.concatenate([
        np.ones(qtd_positivos, dtype=int),
        np.zeros(qtd_amostras - qtd_positivos, dtype=int),
    ])
    np.random.shuffle(rotulos)
    dados["label"] = rotulos
    return pd.DataFrame(dados)


# ---------------------------------------------------------------------------
# Testes
# ---------------------------------------------------------------------------


def test_ac1_dataset_carregado_com_1000_amostras(tmp_path):
    """AC1: Dataset retornado deve ter pelo menos 1000 linhas."""
    dataframe_falso = _criar_dataframe_falso(1000)
    caminho_pkl = str(tmp_path / "dataset_labeled.pkl")
    caminho_fn = str(tmp_path / "feature_names.json")

    with patch("src.application.data_loader.load_and_label", return_value=dataframe_falso):
        resultado = prepare_training_dataset(
            results_path="qualquer/caminho.json",
            output_pkl=caminho_pkl,
            feature_names_path=caminho_fn,
        )

    assert "dataframe" in resultado
    assert len(resultado["dataframe"]) >= 1000, (
        f"Esperado >= 1000 amostras, obtido {len(resultado['dataframe'])}"
    )


def test_ac2_labeling_ml_consistente(tmp_path):
    """AC2: Labels devem ser apenas 0/1, sem NaN, com imbalance entre 20-80%."""
    dataframe_falso = _criar_dataframe_falso(1000)
    caminho_pkl = str(tmp_path / "dataset_labeled.pkl")
    caminho_fn = str(tmp_path / "feature_names.json")

    with patch("src.application.data_loader.load_and_label", return_value=dataframe_falso):
        resultado = prepare_training_dataset(
            results_path="qualquer/caminho.json",
            output_pkl=caminho_pkl,
            feature_names_path=caminho_fn,
        )

    df = resultado["dataframe"]
    coluna_label = df["label"]

    # Sem NaN
    assert not coluna_label.isnull().any(), "Labels contem NaN"

    # Apenas 0 e 1
    valores_unicos = set(coluna_label.unique())
    assert valores_unicos.issubset({0, 1}), f"Labels invalidos: {valores_unicos}"

    # Imbalance entre 20% e 80%
    pct_positivos = float(coluna_label.mean() * 100)
    assert 20 <= pct_positivos <= 80, (
        f"Imbalance fora do intervalo: {pct_positivos:.1f}%"
    )


def test_ac3_24_features_extraidas(tmp_path):
    """AC3: DataFrame deve conter exatamente 24 features engineered."""
    dataframe_falso = _criar_dataframe_falso(1000)
    caminho_pkl = str(tmp_path / "dataset_labeled.pkl")
    caminho_fn = str(tmp_path / "feature_names.json")

    with patch("src.application.data_loader.load_and_label", return_value=dataframe_falso):
        resultado = prepare_training_dataset(
            results_path="qualquer/caminho.json",
            output_pkl=caminho_pkl,
            feature_names_path=caminho_fn,
        )

    nomes_features = resultado["feature_names"]
    assert len(nomes_features) == 24, (
        f"Esperado 24 features, obtido {len(nomes_features)}"
    )

    # Verificar que features existem no DataFrame
    df = resultado["dataframe"]
    for nome in nomes_features:
        assert nome in df.columns, f"Feature '{nome}' ausente no DataFrame"


def test_ac4_splits_70_15_15(tmp_path):
    """AC4: Splits devem ter proporcoes aproximadas de 70/15/15."""
    dataframe_falso = _criar_dataframe_falso(1000)
    caminho_pkl = str(tmp_path / "dataset_labeled.pkl")
    caminho_fn = str(tmp_path / "feature_names.json")

    with patch("src.application.data_loader.load_and_label", return_value=dataframe_falso):
        resultado = prepare_training_dataset(
            results_path="qualquer/caminho.json",
            output_pkl=caminho_pkl,
            feature_names_path=caminho_fn,
        )

    splits = resultado["splits"]
    assert "train" in splits and "val" in splits and "test" in splits

    total = len(resultado["dataframe"])
    qtd_treino = len(splits["train"])
    qtd_val = len(splits["val"])
    qtd_teste = len(splits["test"])

    # Verificar que soma cobre o total
    assert qtd_treino + qtd_val + qtd_teste == total, (
        f"Soma dos splits ({qtd_treino}+{qtd_val}+{qtd_teste}) != total ({total})"
    )

    # Verificar proporcoes com tolerancia de 2%
    pct_treino = qtd_treino / total
    pct_val = qtd_val / total
    pct_teste = qtd_teste / total

    assert abs(pct_treino - 0.70) <= 0.02, f"Proporcao treino: {pct_treino:.2f} (esperado ~0.70)"
    assert abs(pct_val - 0.15) <= 0.02, f"Proporcao val: {pct_val:.2f} (esperado ~0.15)"
    assert abs(pct_teste - 0.15) <= 0.02, f"Proporcao teste: {pct_teste:.2f} (esperado ~0.15)"


def test_ac5_feature_names_salvos(tmp_path):
    """AC5: feature_names.json deve ser salvo com exatamente 24 nomes de features."""
    dataframe_falso = _criar_dataframe_falso(1000)
    caminho_pkl = str(tmp_path / "dataset_labeled.pkl")
    caminho_fn = str(tmp_path / "feature_names.json")

    with patch("src.application.data_loader.load_and_label", return_value=dataframe_falso):
        prepare_training_dataset(
            results_path="qualquer/caminho.json",
            output_pkl=caminho_pkl,
            feature_names_path=caminho_fn,
        )

    assert Path(caminho_fn).exists(), "feature_names.json nao foi criado"

    with open(caminho_fn, "r", encoding="utf-8") as arq:
        conteudo = json.load(arq)

    assert "features" in conteudo, "Chave 'features' ausente no JSON"
    assert len(conteudo["features"]) == 24, (
        f"Esperado 24 features no JSON, obtido {len(conteudo['features'])}"
    )
    # Todos os itens devem ser strings nao vazias
    for nome in conteudo["features"]:
        assert isinstance(nome, str) and len(nome) > 0, f"Nome invalido: {nome!r}"


def test_dataset_labeled_pkl_salvo(tmp_path):
    """Verifica que dataset_labeled.pkl foi criado e contem estrutura valida."""
    dataframe_falso = _criar_dataframe_falso(1000)
    caminho_pkl = str(tmp_path / "dataset_labeled.pkl")
    caminho_fn = str(tmp_path / "feature_names.json")

    with patch("src.application.data_loader.load_and_label", return_value=dataframe_falso):
        prepare_training_dataset(
            results_path="qualquer/caminho.json",
            output_pkl=caminho_pkl,
            feature_names_path=caminho_fn,
        )

    assert Path(caminho_pkl).exists(), "dataset_labeled.pkl nao foi criado"

    with open(caminho_pkl, "rb") as arq:
        dados_pkl = pickle.load(arq)

    assert isinstance(dados_pkl, dict), "Pickle nao contem dicionario"
    for chave in ("dataframe", "splits", "feature_names", "metadata"):
        assert chave in dados_pkl, f"Chave '{chave}' ausente no pickle"


def test_erro_arquivo_nao_encontrado(tmp_path):
    """Verifica que FileNotFoundError e lancado para path invalido."""
    caminho_pkl = str(tmp_path / "dataset_labeled.pkl")
    caminho_fn = str(tmp_path / "feature_names.json")

    with pytest.raises(FileNotFoundError):
        prepare_training_dataset(
            results_path="caminho/inexistente/arquivo.json",
            output_pkl=caminho_pkl,
            feature_names_path=caminho_fn,
        )
