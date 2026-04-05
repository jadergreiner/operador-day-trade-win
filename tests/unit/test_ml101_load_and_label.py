"""
Testes unitarios para load_and_label() — Issue ML-101

Persona: ML Expert (Persona 2 - The Brain)
Sprint: 2 (bloqueia Grid Search)
Coverage alvo: > 90%

Criterios de Aceitacao:
  AC-1: Carregar backtest_optimized_results.json eficientemente
  AC-2: Retornar dict com label_map, dataframe, metadata, execution_time_ms
  AC-3: Mapear window_id → labels sem off-by-one errors
  AC-4: Validar class imbalance < 70%
  AC-5: Verificar zero NaN values
  AC-6: Performance < 500ms
  AC-7: Coverage > 90% — test_load_and_label_success,
         test_load_and_label_nan_handling, test_load_and_label_imbalance
"""

import json
import time
import pytest
import numpy as np
import pandas as pd
from pathlib import Path
from typing import Any, Dict

from src.application.ml_feature_engineer import load_and_label


# ============================================================================
# Fixtures
# ============================================================================

@pytest.fixture
def backtest_json_valido(tmp_path: Path) -> str:
    """JSON valido com estrutura real de backtest_optimized_results."""
    dados: Dict[str, Any] = {
        "threshold_sigma": 2.0,
        "metricas": {
            "velas_processadas": 17280,
            "alertas_gerados": 148,
            "oportunidades_esperadas": 145,
            "matches": 137,
            "false_positives": 11,
            "false_negatives": 8,
        },
        "taxas": {
            "taxa_captura_pct": 94.48,
            "taxa_false_positive_pct": 7.43,
            "win_rate_estimado_pct": 62.0,
        },
        "gates_validacao": {
            "captura_minima_85pct": True,
            "fp_maxima_10pct": True,
            "win_rate_minimo_60pct": True,
        },
        "status": "PASS",
        "timestamp": "2026-02-20T23:59:00Z",
    }
    path = tmp_path / "backtest_optimized_results.json"
    path.write_text(json.dumps(dados), encoding="utf-8")
    return str(path)


@pytest.fixture
def backtest_json_imbalance_critico(tmp_path: Path) -> str:
    """JSON com win_rate = 72% — class imbalance >= 70% deve falhar."""
    dados: Dict[str, Any] = {
        "threshold_sigma": 1.0,
        "metricas": {"velas_processadas": 1000, "matches": 100},
        "taxas": {"win_rate_estimado_pct": 72.0},
        "status": "PASS",
        "timestamp": "2026-02-20T10:00:00Z",
    }
    path = tmp_path / "backtest_imbalance.json"
    path.write_text(json.dumps(dados), encoding="utf-8")
    return str(path)


@pytest.fixture
def backtest_json_win_rate_0(tmp_path: Path) -> str:
    """JSON com win_rate = 0% — todos losses — imbalance >= 70% deve falhar."""
    dados: Dict[str, Any] = {
        "threshold_sigma": 1.5,
        "metricas": {"velas_processadas": 500, "matches": 50},
        "taxas": {"win_rate_estimado_pct": 0.0},
        "status": "PASS",
        "timestamp": "2026-02-20T11:00:00Z",
    }
    path = tmp_path / "backtest_0.json"
    path.write_text(json.dumps(dados), encoding="utf-8")
    return str(path)


@pytest.fixture
def backtest_json_grande(tmp_path: Path) -> str:
    """JSON com 17280 velas e 500 matches para testar performance."""
    dados: Dict[str, Any] = {
        "threshold_sigma": 2.0,
        "metricas": {
            "velas_processadas": 17280,
            "matches": 500,
        },
        "taxas": {"win_rate_estimado_pct": 62.0},
        "status": "PASS",
        "timestamp": "2026-02-20T23:59:00Z",
    }
    path = tmp_path / "backtest_grande.json"
    path.write_text(json.dumps(dados), encoding="utf-8")
    return str(path)


# ============================================================================
# Testes Principais (AC-7)
# ============================================================================

def test_load_and_label_success(backtest_json_valido: str) -> None:
    """
    AC-2 / AC-3: Carrega JSON e mapeia window_id → labels corretamente.

    Verifica:
      - Retorno e' um dict com as chaves obrigatorias
      - label_map contem exatamente 'matches' entradas
      - window_ids sao contiguos, sem gaps (sem off-by-one)
      - Labels sao apenas 0 ou 1
      - execution_time_ms presente e positivo
    """
    resultado = load_and_label(backtest_json_valido)

    # Estrutura do retorno (AC-2)
    assert isinstance(resultado, dict), "Resultado deve ser dict"
    assert 'label_map' in resultado, "Faltando chave 'label_map'"
    assert 'dataframe' in resultado, "Faltando chave 'dataframe'"
    assert 'metadata' in resultado, "Faltando chave 'metadata'"
    assert 'execution_time_ms' in resultado, "Faltando chave 'execution_time_ms'"

    label_map: Dict[int, int] = resultado['label_map']
    df: pd.DataFrame = resultado['dataframe']
    metadata: Dict[str, Any] = resultado['metadata']

    # AC-3: window_ids contiguos sem off-by-one
    matches = metadata['matches']
    assert len(label_map) == matches, (
        f"label_map deve ter {matches} entradas, tem {len(label_map)}"
    )
    for wid in range(matches):
        assert wid in label_map, f"window_id={wid} ausente no label_map (off-by-one)"

    # Labels apenas 0 ou 1
    unique_labels = set(label_map.values())
    assert unique_labels <= {0, 1}, f"Labels invalidos: {unique_labels}"

    # DataFrame consistente com label_map (AC-3)
    assert list(df.columns) == ['window_id', 'label']
    assert len(df) == matches
    for _, row in df.iterrows():
        wid = int(row['window_id'])
        assert label_map[wid] == int(row['label']), (
            f"Inconsistencia window_id={wid}: "
            f"label_map={label_map[wid]}, df={row['label']}"
        )

    # execution_time_ms positivo
    assert resultado['execution_time_ms'] > 0


def test_load_and_label_nan_handling(backtest_json_valido: str) -> None:
    """
    AC-5: Verifica zero NaN values em todas as colunas.

    Verifica:
      - DataFrame nao contem NaN em nenhuma celula
      - metadata['nan_count'] == 0
    """
    resultado = load_and_label(backtest_json_valido)

    df: pd.DataFrame = resultado['dataframe']
    metadata: Dict[str, Any] = resultado['metadata']

    # AC-5: zero NaN
    nan_total = int(df.isnull().sum().sum())
    assert nan_total == 0, f"DataFrame contem {nan_total} NaN(s)"

    # metadata deve registrar nan_count = 0
    assert metadata['nan_count'] == 0, (
        f"metadata['nan_count'] deve ser 0, e' {metadata['nan_count']}"
    )

    # Verificar coluna por coluna
    for col in df.columns:
        nan_col = int(df[col].isnull().sum())
        assert nan_col == 0, f"Coluna '{col}' contem {nan_col} NaN(s)"


def test_load_and_label_imbalance(
    backtest_json_imbalance_critico: str,
    backtest_json_win_rate_0: str,
) -> None:
    """
    AC-4: Valida class imbalance < 70%.

    Verifica:
      - ValueError levantado quando win_rate >= 70% (max classe >= 70%)
      - ValueError levantado quando win_rate = 0% (100% da classe loss)
      - Sucesso quando win_rate esta em faixa aceitavel (30-69%)
    """
    # Imbalance 72% deve falhar
    with pytest.raises(ValueError, match="[Ii]mbalance"):
        load_and_label(backtest_json_imbalance_critico)

    # 0% win_rate (100% loss) deve falhar
    with pytest.raises(ValueError, match="[Ii]mbalance"):
        load_and_label(backtest_json_win_rate_0)


# ============================================================================
# Testes Complementares (robustez e cobertura)
# ============================================================================

class TestLoadAndLabelAC1FileHandling:
    """AC-1: Carregamento de arquivo."""

    def test_arquivo_nao_encontrado(self) -> None:
        """FileNotFoundError para caminho inexistente."""
        with pytest.raises(FileNotFoundError):
            load_and_label("/caminho/inexistente/backtest.json")

    def test_retorna_dict_valido(self, backtest_json_valido: str) -> None:
        """Retorno e' dict com chaves esperadas."""
        resultado = load_and_label(backtest_json_valido)
        assert isinstance(resultado, dict)
        assert set(resultado.keys()) >= {
            'label_map', 'dataframe', 'metadata', 'execution_time_ms'
        }


class TestLoadAndLabelAC3Mapeamento:
    """AC-3: Mapeamento window_id → label sem off-by-one."""

    def test_window_ids_iniciam_em_zero(self, backtest_json_valido: str) -> None:
        """Primeiro window_id deve ser 0."""
        resultado = load_and_label(backtest_json_valido)
        assert 0 in resultado['label_map'], "window_id=0 ausente"

    def test_window_id_maximo_igual_matches_menos_1(
        self, backtest_json_valido: str
    ) -> None:
        """Ultimo window_id == matches - 1 (sem off-by-one)."""
        resultado = load_and_label(backtest_json_valido)
        matches = resultado['metadata']['matches']
        assert (matches - 1) in resultado['label_map'], (
            f"window_id={matches - 1} ausente (off-by-one)"
        )
        assert matches not in resultado['label_map'], (
            f"window_id={matches} presente (off-by-one extra)"
        )

    def test_reproducibilidade_com_seed(self, backtest_json_valido: str) -> None:
        """Duas chamadas devem retornar label_map identico (seed=42)."""
        r1 = load_and_label(backtest_json_valido)
        r2 = load_and_label(backtest_json_valido)
        assert r1['label_map'] == r2['label_map'], "label_map nao e' deterministico"


class TestLoadAndLabelAC4Imbalance:
    """AC-4: Validacao de class imbalance."""

    def test_imbalance_pct_no_metadata(self, backtest_json_valido: str) -> None:
        """metadata deve conter 'imbalance_pct' com valor valido."""
        resultado = load_and_label(backtest_json_valido)
        assert 'imbalance_pct' in resultado['metadata']
        imb = resultado['metadata']['imbalance_pct']
        assert 0.0 <= imb <= 100.0

    def test_max_class_abaixo_70_pct(self, backtest_json_valido: str) -> None:
        """Nenhuma classe pode ter >= 70% das amostras."""
        resultado = load_and_label(backtest_json_valido)
        df: pd.DataFrame = resultado['dataframe']
        total = len(df)
        for label_val in [0, 1]:
            pct = (df['label'] == label_val).sum() / total * 100
            assert pct < 70.0, (
                f"Classe {label_val} tem {pct:.1f}% — acima do limite de 70%"
            )


class TestLoadAndLabelAC6Performance:
    """AC-6: Performance < 500ms."""

    def test_execucao_abaixo_500ms(self, backtest_json_valido: str) -> None:
        """Execucao deve ser concluida em menos de 500ms."""
        inicio = time.perf_counter()
        load_and_label(backtest_json_valido)
        elapsed_ms = (time.perf_counter() - inicio) * 1000
        assert elapsed_ms < 500, f"Performance {elapsed_ms:.1f}ms > 500ms"

    def test_execution_time_ms_no_resultado(
        self, backtest_json_valido: str
    ) -> None:
        """execution_time_ms deve ser registrado e < 500ms."""
        resultado = load_and_label(backtest_json_valido)
        assert resultado['execution_time_ms'] < 500

    def test_performance_17k_samples(self, backtest_json_grande: str) -> None:
        """Performance para 500 matches (simulando 17k+ samples) < 500ms."""
        inicio = time.perf_counter()
        load_and_label(backtest_json_grande)
        elapsed_ms = (time.perf_counter() - inicio) * 1000
        assert elapsed_ms < 500, f"Performance {elapsed_ms:.1f}ms > 500ms"


class TestLoadAndLabelAC2Retorno:
    """AC-2: Estrutura do dict retornado."""

    def test_label_map_e_dict_int_int(self, backtest_json_valido: str) -> None:
        """label_map deve ser Dict[int, int]."""
        resultado = load_and_label(backtest_json_valido)
        label_map = resultado['label_map']
        for k, v in label_map.items():
            assert isinstance(k, int), f"Chave '{k}' nao e' int"
            assert isinstance(v, int), f"Valor '{v}' nao e' int"

    def test_dataframe_tipos_corretos(self, backtest_json_valido: str) -> None:
        """DataFrame deve ter dtypes inteiros em window_id e label."""
        resultado = load_and_label(backtest_json_valido)
        df: pd.DataFrame = resultado['dataframe']
        assert pd.api.types.is_integer_dtype(df['window_id']), (
            f"window_id dtype incorreto: {df['window_id'].dtype}"
        )
        assert pd.api.types.is_integer_dtype(df['label']), (
            f"label dtype incorreto: {df['label'].dtype}"
        )

    def test_metadata_contem_campos_obrigatorios(
        self, backtest_json_valido: str
    ) -> None:
        """metadata deve conter campos obrigatorios."""
        resultado = load_and_label(backtest_json_valido)
        metadata = resultado['metadata']
        for campo in [
            'matches', 'win_rate_estimado_pct', 'n_wins', 'n_losses',
            'nan_count', 'imbalance_pct',
        ]:
            assert campo in metadata, f"Campo '{campo}' ausente em metadata"
        # execution_time_ms e' chave raiz do dict retornado (fonte de verdade)
        assert 'execution_time_ms' in resultado, (
            "'execution_time_ms' ausente no dict raiz"
        )
