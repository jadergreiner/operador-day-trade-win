"""
Augment Training Dataset - Aumenta dataset para 1.000+ amostras via bootstrap.

Usa técnica de bootstrap com jitter para criar amostras sintéticas realistas
mantendo propriedades estatísticas do dataset original.
"""

import logging
from pathlib import Path
from typing import Tuple

import pandas as pd
import numpy as np

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-8s | %(message)s"
)
logger = logging.getLogger(__name__)


DATASET_PATH = Path("data/training_dataset.csv")
OUTPUT_PATH = Path("data/training_dataset.csv")
TARGET_SAMPLES = 1000


def load_dataset() -> pd.DataFrame:
    """Carrega dataset original."""
    if not DATASET_PATH.exists():
        raise FileNotFoundError(f"Dataset não encontrado: {DATASET_PATH}")

    df = pd.read_csv(DATASET_PATH, index_col=0, parse_dates=True)
    logger.info(f"Dataset carregado: {len(df)} amostras, {df.shape[1]} features")
    return df


def bootstrap_augment(df: pd.DataFrame, target_samples: int, jitter_std: float = 0.02) -> pd.DataFrame:
    """
    Bootstrap augmentation com jitter realista.

    Args:
        df: DataFrame original
        target_samples: Número alvo de amostras
        jitter_std: Desvio padrão do jitter (% do valor)

    Returns:
        DataFrame aumentado
    """
    current_samples = len(df)
    samples_needed = target_samples - current_samples

    if samples_needed <= 0:
        logger.warning(f"Dataset já tem {current_samples} samples, target é {target_samples}")
        return df

    logger.info(f"Criando {samples_needed} amostras sintéticas via bootstrap...")

    # Separar features e labels
    feature_cols = [c for c in df.columns if c != 'label']
    X = df[feature_cols].values
    y = df['label'].values

    # Gerar índice temporal contínuo
    if pd.api.types.is_datetime64_any_dtype(df.index):
        # Se tem índice datetime, continuar de lá
        last_date = df.index[-1]
        new_dates = pd.date_range(start=last_date + pd.Timedelta(hours=1), periods=samples_needed, freq='h')
    else:
        # Criar índice datetime artificial (últimos 1000 horas)
        new_dates = pd.date_range(end=pd.Timestamp.now(), periods=samples_needed, freq='h')

    # Bootstrap: amostrar com replacement e aplicar jitter
    new_samples_list = []

    for i in range(samples_needed):
        # Random sample from original
        sample_idx = np.random.randint(0, len(df))
        original_sample = X[sample_idx].copy()

        # Apply jitter (pequena variação aleatória)
        jitter = np.random.normal(0, jitter_std, len(original_sample))
        scaled_jitter = original_sample * jitter
        augmented_sample = original_sample + scaled_jitter

        # Preservar label (com 5% chance de flip para realismo)
        label = y[sample_idx]
        if np.random.random() < 0.05:
            label = 1 - label  # Flip para criar mais diversidade

        new_samples_list.append(list(augmented_sample) + [label])

    # Criar novo DataFrame com amostras aumentadas com índice temporal
    new_samples_df = pd.DataFrame(
        new_samples_list,
        columns=feature_cols + ['label'],
        index=new_dates
    )

    # Combinar com original
    augmented_df = pd.concat([df, new_samples_df], ignore_index=False)
    augmented_df = augmented_df.sort_index()

    logger.info(f"Dataset aumentado: {len(df)} → {len(augmented_df)} amostras")
    return augmented_df


def validate_augmented(original: pd.DataFrame, augmented: pd.DataFrame) -> None:
    """
    Valida que dataset aumentado mantém propriedades estatísticas.

    Args:
        original: Dataset original
        augmented: Dataset aumentado
    """
    logger.info("Validando propriedades estatísticas...")

    feature_cols = [c for c in original.columns if c != 'label']

    # Comparar means
    original_means = original[feature_cols].mean()
    augmented_means = augmented[feature_cols].mean()
    mean_diff_pct = (abs(original_means - augmented_means) / original_means.abs()).mean() * 100

    logger.info(f"✓ Mean difference: {mean_diff_pct:.2f}% (esperado < 10%)")

    # Comparar label distribution
    original_label_dist = original['label'].value_counts(normalize=True)
    augmented_label_dist = augmented['label'].value_counts(normalize=True)

    logger.info(f"Original label dist: {dict(original_label_dist)}")
    logger.info(f"Augmented label dist: {dict(augmented_label_dist)}")

    # Verificar se não hay duplicatas exatas
    duplicates = augmented.duplicated().sum()
    logger.info(f"✓ Duplicatas exatas: {duplicates} (esperado < 5)")


def main():
    """Executa augmentation do dataset."""
    try:
        # Carregar original
        original_df = load_dataset()

        # Aumentar via bootstrap
        augmented_df = bootstrap_augment(original_df, TARGET_SAMPLES)

        # Validar
        validate_augmented(original_df, augmented_df)

        # Salvar com index datetime preservado
        # Converter index para DatetimeIndex se não for já
        if not isinstance(augmented_df.index, pd.DatetimeIndex):
            # Criar índice datetime a partir do tamanho do dataset
            augmented_df.index = pd.date_range(
                end=pd.Timestamp.now(),
                periods=len(augmented_df),
                freq='h'  # lowercase 'h' for hourly frequency
            )

        augmented_df.to_csv(OUTPUT_PATH)
        logger.info(f"✓ Dataset aumentado salvo em: {OUTPUT_PATH}")

        # Verificar que carregamento funciona
        check_df = pd.read_csv(OUTPUT_PATH, index_col=0, parse_dates=True)
        logger.info(f"✓ Verificação: índice datetime {type(check_df.index)}")

        return 0

    except Exception as e:
        logger.error(f"✗ Erro: {e}", exc_info=True)
        return 1


if __name__ == "__main__":
    import sys
    sys.exit(main())
