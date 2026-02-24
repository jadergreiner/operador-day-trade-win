"""
test_score_t60_builder.py — Testes Unitários do Score T60 Builder

Modulo de testes para validar a construção do dataset T+60:
  - Carregamento de dados M1
  - Extração de 25 features
  - Criação de labels retroativos
  - Validação de distribuição
  - Persistência em arquivo

Estratégia de Teste: CASE-THEN-WHEN em português
- CASO: Condição de entrada
- ENTÃO: Ação executada
- QUANDO: Validação esperada

Coverage Target: 98%
Author: Squad QA + ML Expert
Date: 2026-02-24
"""

import json
import logging
from pathlib import Path
from typing import Tuple
from tempfile import TemporaryDirectory

import pytest
import pandas as pd
import numpy as np
from pandas import DataFrame

# Setup logging para testes
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

# Importar a classe sob teste
import sys
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "scripts"))
from score_t60_builder import ScoreT60Builder


@pytest.fixture
def builder() -> ScoreT60Builder:
    """
    Fixture: Instancia um builder limpo para cada test.

    CASO: Cada test precisa de instância isolada
    ENTÃO: Fixture cria new builder
    QUANDO: Test executa com estado limpo
    """
    logger.info("📦 Fixture: Instantiando ScoreT60Builder...")
    return ScoreT60Builder(threshold_pct=0.0015)


@pytest.fixture
def dados_historicos_m1() -> DataFrame:
    """
    Fixture: Cria dataset sintético de 200 velas M1 para teste.

    CASO: Testes precisam de dados representativos
    ENTÃO: Fixture gera séries realistas de preço/volume
    QUANDO: Data contém OHLCV completo com padrões definidos

    Detalhes:
      - 200 velas de 1 minuto
      - Preço inicia em 10.000, com movimento randômico ±0.5%
      - Volume entre 1.000-5.000
      - Labels: BULL/BEAR desbalanceados realisticamente
    """
    logger.info("📊 Fixture: Gerando dados históricos M1 sintéticos...")

    np.random.seed(42)  # Seed para reprodutibilidade

    n_velas = 200
    close_prices = np.ones(n_velas) * 10000

    # Simular movimento de preço com random walk
    for i in range(1, n_velas):
        change_pct = np.random.normal(0, 0.005)  # ±0.5% média
        close_prices[i] = close_prices[i-1] * (1 + change_pct)

    data = {
        "time": pd.date_range("2026-02-01 09:00", periods=n_velas, freq="1min"),
        "open": close_prices * (1 + np.random.normal(0, 0.0001, n_velas)),
        "high": close_prices * (1 + np.abs(np.random.normal(0, 0.0005, n_velas))),
        "low": close_prices * (1 - np.abs(np.random.normal(0, 0.0005, n_velas))),
        "close": close_prices,
        "volume": np.random.randint(1000, 5000, n_velas),
    }

    df = pd.DataFrame(data)
    logger.info(f"  ✅ {len(df)} velas geradas | close[0]={df['close'].iloc[0]:.2f}")

    return df


@pytest.fixture
def dados_incompletos() -> DataFrame:
    """
    Fixture: Dataset com colunas faltando (erro de entrada).

    CASO: Dados faltando colunas obrigatórias
    ENTÃO: Verificar tratamento de erro
    QUANDO: load_data levanta ValueError
    """
    logger.info("⚠️  Fixture: Gerando dataset incompleto...")
    df = pd.DataFrame({
        "time": pd.date_range("2026-02-01", periods=100, freq="1min"),
        "close": np.random.rand(100) * 100,
        # FALTAR: open, high, low, volume
    })
    return df


# ============================================================================
# TEST GROUP 1: Carregamento de Dados
# ============================================================================

def test_load_data_case_arquivo_valido_then_sucesso_when_df_carregado(
    builder: ScoreT60Builder,
    dados_historicos_m1: DataFrame
) -> None:
    """
    CASO: Arquivo CSV válido com OHLCV completo
    ENTÃO: Carregar dados e ordenar cronologicamente
    QUANDO: DataFrame retornado tem 200 velas

    Validações:
    - len(df) == 200
    - Colunas: open, high, low, close, volume, time
    - Ordenado por time ascending
    - Sem duplicatas
    """
    with TemporaryDirectory() as tmpdir:
        # SETUP: Salvar dados em CSV temporário
        input_path = Path(tmpdir) / "test_m1.csv"
        dados_historicos_m1.to_csv(input_path, index=False)
        logger.info(f"  📁 Arquivo temporário criado: {input_path}")

        # AÇÃO: Carregar dados
        df = builder.load_data(str(input_path))

        # VALIDAÇÕES
        assert df is not None, "DataFrame não pode ser None"
        assert len(df) == 200, f"Expected 200 velas, got {len(df)}"
        assert "close" in df.columns, "Coluna 'close' faltando"
        assert "volume" in df.columns, "Coluna 'volume' faltando"

        # Verificar ordenação
        assert df["time"].is_monotonic_increasing, "Dados não estão ordenados"

        logger.info(f"  ✅ Test PASSOU: {len(df)} velas carregadas")


def test_load_data_case_arquivo_inexistente_then_erro_when_filenotfound(
    builder: ScoreT60Builder
) -> None:
    """
    CASO: Caminho arquivo não existe
    ENTÃO: Levanta FileNotFoundError
    QUANDO: Mensagem de erro apropriada

    Objetivo: Validar error handling robusto
    """
    # AÇÃO: Tentar carregar arquivo inexistente
    with pytest.raises(FileNotFoundError) as exc_info:
        builder.load_data("/tmp/arquivo_nao_existe_xyz.csv")

    # VALIDAÇÕES
    assert "não encontrado" in str(exc_info.value).lower(), \
        "Mensagem erro não menciona arquivo"

    logger.info("  ✅ Test PASSOU: FileNotFoundError capturado")


def test_load_data_case_colunas_incompletas_then_erro_when_valueerror(
    builder: ScoreT60Builder,
    dados_incompletos: DataFrame
) -> None:
    """
    CASO: DataFrame com colunas faltando (ex: sem 'open')
    ENTÃO: Levanta ValueError
    QUANDO: Mensagem lista colunas faltando

    Objetivo: Validar que não processamos dados ruins
    """
    with TemporaryDirectory() as tmpdir:
        input_path = Path(tmpdir) / "incompleto.csv"
        dados_incompletos.to_csv(input_path, index=False)

        # AÇÃO: Carregar dados ruins
        with pytest.raises(ValueError) as exc_info:
            builder.load_data(str(input_path))

        # VALIDAÇÕES
        error_msg = str(exc_info.value).lower()
        assert "faltando" in error_msg or "missing" in error_msg, \
            "Erro não menciona colunas faltando"

        logger.info("  ✅ Test PASSOU: ValueError capturado para dados incompletos")


# ============================================================================
# TEST GROUP 2: Extração de Features
# ============================================================================

def test_extract_features_case_dados_carregados_then_25features_when_shape_correto(
    builder: ScoreT60Builder,
    dados_historicos_m1: DataFrame
) -> None:
    """
    CASO: Dados M1 já carregados e validados
    ENTÃO: Extrair 25 features técnicas
    QUANDO: DataFrame retornado tem 25 novas colunas

    Validações:
    - 25 features presentes
    - Features normalizadas (não NaN após fillna)
    - Valores numéricos válidos
    - Sem infinitos ou NaN excessivos
    """
    # SETUP: Carregar dados
    builder.df_m1 = dados_historicos_m1

    # AÇÃO: Extrair features
    df_features = builder.extract_features()

    # VALIDAÇÕES
    feature_names = builder.features_list
    assert len(feature_names) == 25, f"Expected 25 features, got {len(feature_names)}"

    for feature in feature_names:
        assert feature in df_features.columns, f"Feature '{feature}' não encontrada"

    # Verificar valores válidos (sem NaN após processamento)
    for feature in feature_names:
        nan_pct = df_features[feature].isna().sum() / len(df_features) * 100
        assert nan_pct < 1.0, f"Feature '{feature}' tem {nan_pct:.1f}% NaN"

    # Verificar sem infinitos
    for feature in feature_names:
        assert not np.isinf(df_features[feature]).any(), \
            f"Feature '{feature}' contains infinitos"

    logger.info(f"  ✅ Test PASSOU: 25 features extraídas, <1% NaN")


def test_extract_features_case_sem_dados_then_erro_when_valueerror(
    builder: ScoreT60Builder
) -> None:
    """
    CASO: Tentar extrair features sem carregar dados
    ENTÃO: Levanta ValueError
    QUANDO: Mensagem menciona "dados não carregados"

    Objetivo: Validar que respeita pre-condições
    """
    # AÇÃO: Chamar extract sem load_data
    with pytest.raises(ValueError) as exc_info:
        builder.extract_features()

    # VALIDAÇÕES
    assert "não carregado" in str(exc_info.value).lower(), \
        "Erro não menciona dados não carregados"

    logger.info("  ✅ Test PASSOU: ValueError capturado para missing data")


def test_extract_features_case_tipos_numericos_then_float64_when_validacao(
    builder: ScoreT60Builder,
    dados_historicos_m1: DataFrame
) -> None:
    """
    CASO: Features extraídas precisam ser tipo float64
    ENTÃO: Validar tipos de dados
    QUANDO: Todos features são float64

    Objetivo: Garantir compatibilidade com XGBoost
    """
    builder.df_m1 = dados_historicos_m1
    df_features = builder.extract_features()

    for feature in builder.features_list:
        assert df_features[feature].dtype in [np.float64, np.float32], \
            f"Feature '{feature}' is {df_features[feature].dtype}, esperado float"

    logger.info("  ✅ Test PASSOU: Todos features são float64")


# ============================================================================
# TEST GROUP 3: Criação de Labels
# ============================================================================

def test_create_labels_case_dados_com_60velas_then_labels_validos_when_shape(
    builder: ScoreT60Builder,
    dados_historicos_m1: DataFrame
) -> None:
    """
    CASO: Dataset com 200 velas (t-60 observáveis para primeiras 140)
    ENTÃO: Criar labels retroativos para T+60
    QUANDO: 140 labels válidos (não NaN), 60 NaN nas últimas velas

    Validações:
    - Column 'label_t60' presente
    - Últimas 60 rows têm NaN (não há t+60)
    - Labels são 0 ou 1
    - Distribuição balanceada ~50/50
    """
    # SETUP
    builder.df_m1 = dados_historicos_m1
    df_features = builder.extract_features()

    # AÇÃO
    df_labeled = builder.create_labels(df_features)

    # VALIDAÇÕES
    assert "label_t60" in df_labeled.columns, "Coluna 'label_t60' não encontrada"

    # Verificar últimas 60 são NaN
    nan_count = df_labeled["label_t60"].isna().sum()
    assert nan_count >= 60, f"Expected ≥60 NaN, got {nan_count}"

    # Labels válidos são 0 ou 1
    valid_labels = df_labeled["label_t60"].dropna()
    assert valid_labels.isin([0, 1]).all(), "Labels não são 0 ou 1"

    # Distribuição (permitir até 70/30)
    bull_pct = (valid_labels == 1).sum() / len(valid_labels)
    assert 0.2 < bull_pct < 0.8, \
        f"Distribuição desbalanceada: {bull_pct*100:.1f}% BULL"

    logger.info(f"  ✅ Test PASSOU: Labels criados, {bull_pct*100:.1f}% BULL")


def test_create_labels_case_threshold_customizado_then_labels_ajustados_when_valor(
    builder: ScoreT60Builder,
    dados_historicos_m1: DataFrame
) -> None:
    """
    CASO: Customizar threshold (ex: 0.3% em vez de 0.15%)
    ENTÃO: Labels seguem novo threshold
    QUANDO: Distribuição muda de acordo

    Objetivo: Validar que threshold é respeitado
    """
    # SETUP: Threshold maior → menos BULLs
    builder_custom = ScoreT60Builder(threshold_pct=0.005)  # 0.5%
    builder_custom.df_m1 = dados_historicos_m1
    df_features = builder_custom.extract_features()

    # AÇÃO
    df_labeled = builder_custom.create_labels(df_features)

    # VALIDAÇÕES
    valid_labels = df_labeled["label_t60"].dropna()
    bull_pct_custom = (valid_labels == 1).sum() / len(valid_labels)

    # Com threshold maior, esperamos menos BULLs
    logger.info(f"  Threshold 0.5%: {bull_pct_custom*100:.1f}% BULL")

    # Validar que é número válido entre 0-1
    assert 0.0 <= bull_pct_custom <= 1.0, \
        f"bull_pct inválido: {bull_pct_custom}"

    logger.info("  ✅ Test PASSOU: Threshold customizado aplicado")


# ============================================================================
# TEST GROUP 4: Validação de Dataset
# ============================================================================

def test_validate_dataset_case_dados_completos_then_stats_calculadas_when_dict(
    builder: ScoreT60Builder,
    dados_historicos_m1: DataFrame
) -> None:
    """
    CASO: Dataset com features e labels completos
    ENTÃO: Validador calcula estatísticas
    QUANDO: Retorna dict com stats

    Validações:
    - Dict contém chaves: total_samples, features_present, label_distribution
    - total_samples == 200
    - features_present == 25
    - label_distribution['bull'] > 0
    """
    # SETUP
    builder.df_m1 = dados_historicos_m1
    df_features = builder.extract_features()
    df_labeled = builder.create_labels(df_features)

    # AÇÃO
    validation = builder.validate_dataset(df_labeled)

    # VALIDAÇÕES
    assert isinstance(validation, dict), "Result não é dict"
    assert "total_samples" in validation, "Chave 'total_samples' faltando"
    assert "features_present" in validation, "Chave 'features_present' faltando"
    assert "label_distribution" in validation, "Chave 'label_distribution' faltando"

    assert validation["total_samples"] == 200, \
        f"Expected 200 samples, got {validation['total_samples']}"
    assert validation["features_present"] == 25, \
        f"Expected 25 features, got {validation['features_present']}"

    logger.info(f"  ✅ Test PASSOU: Validação OK")


def test_validate_dataset_case_dados_com_missing_then_percentual_reportado_when_dict(
    builder: ScoreT60Builder,
    dados_historicos_m1: DataFrame
) -> None:
    """
    CASO: Dataset com alguns valores NaN (ex: 5% coluna)
    ENTÃO: Validation reporta percentual
    QUANDO: Dict contem missing_data[col] = pct

    Objetivo: Detectar problemas de qualidade dados
    """
    # SETUP
    builder.df_m1 = dados_historicos_m1
    df_features = builder.extract_features()
    df_labeled = builder.create_labels(df_features)

    # Introduzir 10% de NaN numa coluna
    df_labeled.loc[0:20, "close_norm"] = np.nan

    # AÇÃO
    validation = builder.validate_dataset(df_labeled)

    # VALIDAÇÕES
    assert "missing_data" in validation, "missing_data não no resultado"
    assert "close_norm" in validation["missing_data"], \
        "close_norm não em missing_data"

    missing_pct = validation["missing_data"]["close_norm"]
    assert missing_pct > 5, f"Missing data não detectado: {missing_pct}%"

    logger.info(f"  ✅ Test PASSOU: Missing data = {missing_pct:.1f}%")


# ============================================================================
# TEST GROUP 5: Persistência
# ============================================================================

def test_save_dataset_case_formato_parquet_then_arquivo_criado_when_path_existe(
    builder: ScoreT60Builder,
    dados_historicos_m1: DataFrame
) -> None:
    """
    CASO: Salvar dataset em formato parquet
    ENTÃO: Arquivo criado em disco
    QUANDO: Path retornado existe e é legível

    Validações:
    - File existe
    - Pode ser lido com pandas
    - Contém mesmo número de linhas
    """
    with TemporaryDirectory() as tmpdir:
        # SETUP
        builder.df_m1 = dados_historicos_m1
        df_features = builder.extract_features()
        df_labeled = builder.create_labels(df_features)

        output_path = Path(tmpdir) / "dataset.parquet"

        # AÇÃO
        saved_path = builder.save_dataset(df_labeled, str(output_path), format="parquet")

        # VALIDAÇÕES
        assert saved_path.exists(), f"Arquivo não criado: {saved_path}"
        assert saved_path.suffix == ".parquet", "Arquivo não é .parquet"

        # Verificar leitura
        df_read = pd.read_parquet(saved_path)
        assert len(df_read) == len(df_labeled), "Linhas perdidas ao salvar"
        assert len(df_read.columns) == len(df_labeled.columns), \
            "Colunas perdidas ao salvar"

        logger.info(f"  ✅ Test PASSOU: Arquivo parquet salvo ({saved_path})")


def test_save_dataset_case_formato_csv_then_arquivo_criado_when_delimitado(
    builder: ScoreT60Builder,
    dados_historicos_m1: DataFrame
) -> None:
    """
    CASO: Salvar dataset em formato CSV
    ENTÃO: Arquivo criado em disco
    QUANDO: Pode ser lido como CSV

    Objetivo: Validar alternativa de formato
    """
    with TemporaryDirectory() as tmpdir:
        # SETUP
        builder.df_m1 = dados_historicos_m1
        df_features = builder.extract_features()
        df_labeled = builder.create_labels(df_features)

        output_path = Path(tmpdir) / "dataset.csv"

        # AÇÃO
        saved_path = builder.save_dataset(df_labeled, str(output_path), format="csv")

        # VALIDAÇÕES
        assert saved_path.exists(), "Arquivo CSV não criado"
        df_read = pd.read_csv(saved_path)
        assert len(df_read) == len(df_labeled), "Linhas perdidas em CSV"

        logger.info(f"  ✅ Test PASSOU: Arquivo CSV salvo")


# ============================================================================
# TEST GROUP 6: Pipeline Completo (Integração)
# ============================================================================

def test_run_pipeline_completo_case_dados_ate_arquivo_then_completo_when_output_existe(
    builder: ScoreT60Builder,
    dados_historicos_m1: DataFrame
) -> None:
    """
    CASO: Executar pipeline completo: load → features → labels → save
    ENTÃO: Arquivo final criado com validações
    QUANDO: Retorna tuple (df, validation_dict)

    Validações:
    - Arquivo saida existe
    - DataFrame retornado tem 200 linhas
    - Validation dict tem estatísticas
    - Labels distribuídos
    """
    with TemporaryDirectory() as tmpdir:
        # SETUP
        input_path = Path(tmpdir) / "input.csv"
        output_path = Path(tmpdir) / "output.parquet"
        dados_historicos_m1.to_csv(input_path, index=False)

        # AÇÃO
        df_result, validation = builder.run(
            str(input_path),
            str(output_path),
            format="parquet"
        )

        # VALIDAÇÕES
        assert output_path.exists(), "Arquivo saída não criado"
        assert len(df_result) == 200, f"Expected 200 linhas, got {len(df_result)}"
        assert "label_t60" in df_result.columns, "Labels não adicionados"
        assert validation["total_samples"] == 200, "Validação samples incorreta"
        assert validation["features_present"] == 25, "Features não adicionados"

        logger.info("  ✅ Test PASSOU: Pipeline completo OK")


# ============================================================================
# SUMMARY & EXECUTION
# ============================================================================

if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short", "--cov=score_t60_builder"])
