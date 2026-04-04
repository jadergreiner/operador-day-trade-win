"""
Testes unitários para DatasetLoader.load_backtest_optimized_results()

Issue: [SPRINT-1] Label backtest_optimized_results (ml_feature_engineer.py)
Persona: ML Expert (Persona 2 - 'The Brain')
Sprint: 1 (27/02-05/03)

Critérios de Aceitação:
  AC-1: Load JSON e map window_id a labels (win/loss)
  AC-2: Performance < 500ms
  AC-3: Labels válidos (apenas 0 ou 1, sem NaN)
  AC-4: Test coverage > 90%

Cobertura alvo: > 90% em ml_feature_engineer.py :: DatasetLoader
"""

import json
import time
import tempfile
import pytest
import numpy as np
import pandas as pd
from pathlib import Path
from typing import Any, Dict, List

from src.application.ml_feature_engineer import DatasetLoader


# ============================================================================
# Fixtures
# ============================================================================

@pytest.fixture
def backtest_json_valido(tmp_path: Path) -> str:
    """Fixture: JSON válido com estrutura real de backtest_optimized_results."""
    dados = {
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
def backtest_json_win_rate_100(tmp_path: Path) -> str:
    """Fixture: JSON com win rate 100% (todos wins)."""
    dados = {
        "threshold_sigma": 1.5,
        "metricas": {"velas_processadas": 1000, "matches": 50},
        "taxas": {"win_rate_estimado_pct": 100.0},
        "status": "PASS",
        "timestamp": "2026-02-20T10:00:00Z",
    }
    path = tmp_path / "backtest_100.json"
    path.write_text(json.dumps(dados), encoding="utf-8")
    return str(path)


@pytest.fixture
def backtest_json_win_rate_0(tmp_path: Path) -> str:
    """Fixture: JSON com win rate 0% (todos losses)."""
    dados = {
        "threshold_sigma": 3.0,
        "metricas": {"velas_processadas": 2000, "matches": 30},
        "taxas": {"win_rate_estimado_pct": 0.0},
        "status": "FAIL",
        "timestamp": "2026-02-20T11:00:00Z",
    }
    path = tmp_path / "backtest_0.json"
    path.write_text(json.dumps(dados), encoding="utf-8")
    return str(path)


@pytest.fixture
def backtest_json_sem_matches(tmp_path: Path) -> str:
    """Fixture: JSON sem matches (deve lançar ValueError)."""
    dados = {
        "threshold_sigma": 5.0,
        "metricas": {"velas_processadas": 5000, "matches": 0},
        "taxas": {"win_rate_estimado_pct": 62.0},
        "status": "FAIL",
        "timestamp": "2026-02-20T12:00:00Z",
    }
    path = tmp_path / "backtest_sem_matches.json"
    path.write_text(json.dumps(dados), encoding="utf-8")
    return str(path)


@pytest.fixture
def backtest_json_minimo(tmp_path: Path) -> str:
    """Fixture: JSON com estrutura mínima (sem campos opcionais)."""
    dados = {
        "metricas": {"matches": 10},
        "taxas": {"win_rate_estimado_pct": 50.0},
    }
    path = tmp_path / "backtest_minimo.json"
    path.write_text(json.dumps(dados), encoding="utf-8")
    return str(path)


@pytest.fixture
def arquivo_real_backtest() -> Path:
    """Fixture: Usa o arquivo real data/backtest_optimized_results.json."""
    return Path("data/backtest_optimized_results.json")


# ============================================================================
# Testes - AC-1: Load JSON e map window_id → label (win/loss)
# ============================================================================

class TestAC1LoadEMapearLabels:
    """AC-1: Load JSON e mapear window_id → label (win/loss)."""

    def test_retorna_dicionario_com_chaves_esperadas(
        self, backtest_json_valido: str
    ) -> None:
        """Resultado deve conter label_map, dataframe, metadata e execution_time_ms."""
        loader = DatasetLoader(backtest_json_valido)
        resultado = loader.load_backtest_optimized_results()

        assert isinstance(resultado, dict)
        assert "label_map" in resultado
        assert "dataframe" in resultado
        assert "metadata" in resultado
        assert "execution_time_ms" in resultado

    def test_label_map_e_dict_int_int(self, backtest_json_valido: str) -> None:
        """label_map deve ser Dict[int, int]."""
        loader = DatasetLoader(backtest_json_valido)
        resultado = loader.load_backtest_optimized_results()

        label_map = resultado["label_map"]
        assert isinstance(label_map, dict)
        for window_id, label in label_map.items():
            assert isinstance(window_id, int), f"window_id deve ser int, got {type(window_id)}"
            assert isinstance(label, int), f"label deve ser int, got {type(label)}"

    def test_window_ids_sao_contiguos(self, backtest_json_valido: str) -> None:
        """window_ids deve ser 0, 1, ..., matches-1 sem lacunas."""
        loader = DatasetLoader(backtest_json_valido)
        resultado = loader.load_backtest_optimized_results()

        label_map = resultado["label_map"]
        matches = resultado["metadata"]["matches"]

        assert set(label_map.keys()) == set(range(matches))

    def test_quantidade_de_labels_igual_a_matches(
        self, backtest_json_valido: str
    ) -> None:
        """Número de entradas em label_map deve ser igual a 'matches'."""
        loader = DatasetLoader(backtest_json_valido)
        resultado = loader.load_backtest_optimized_results()

        assert len(resultado["label_map"]) == 137

    def test_labels_apenas_0_ou_1(self, backtest_json_valido: str) -> None:
        """Labels devem ser apenas 0 (loss) ou 1 (win)."""
        loader = DatasetLoader(backtest_json_valido)
        resultado = loader.load_backtest_optimized_results()

        valores = set(resultado["label_map"].values())
        assert valores <= {0, 1}, f"Labels invalidos encontrados: {valores - {0, 1}}"

    def test_usa_self_results_path_por_padrao(
        self, backtest_json_valido: str
    ) -> None:
        """Quando backtest_path=None, usa self.results_path."""
        loader = DatasetLoader(backtest_json_valido)
        resultado = loader.load_backtest_optimized_results(backtest_path=None)

        assert resultado is not None
        assert len(resultado["label_map"]) > 0

    def test_backtest_path_explicito_sobrescreve_results_path(
        self, backtest_json_valido: str, backtest_json_minimo: str
    ) -> None:
        """backtest_path explícito deve ser usado no lugar de self.results_path."""
        loader = DatasetLoader(backtest_json_valido)
        # Carregar arquivo diferente via parâmetro explícito
        resultado = loader.load_backtest_optimized_results(
            backtest_path=backtest_json_minimo
        )
        # O arquivo mínimo tem 10 matches
        assert len(resultado["label_map"]) == 10

    def test_carrega_arquivo_real_quando_existente(
        self, arquivo_real_backtest: Path
    ) -> None:
        """Deve carregar o arquivo real data/backtest_optimized_results.json."""
        if not arquivo_real_backtest.exists():
            pytest.skip("Arquivo real data/backtest_optimized_results.json não encontrado")

        loader = DatasetLoader(str(arquivo_real_backtest))
        resultado = loader.load_backtest_optimized_results()

        assert len(resultado["label_map"]) > 0
        assert resultado["metadata"]["status"] in ("PASS", "FAIL", "UNKNOWN")


# ============================================================================
# Testes - AC-2: Performance < 500ms
# ============================================================================

class TestAC2Performance:
    """AC-2: Performance de execução < 500ms."""

    def test_execucao_abaixo_500ms(self, backtest_json_valido: str) -> None:
        """Execução completa deve ser < 500ms."""
        loader = DatasetLoader(backtest_json_valido)

        inicio = time.perf_counter()
        resultado = loader.load_backtest_optimized_results()
        elapsed_ms = (time.perf_counter() - inicio) * 1000

        assert elapsed_ms < 500, (
            f"Performance {elapsed_ms:.1f}ms excedeu 500ms"
        )

    def test_execution_time_ms_no_metadata(
        self, backtest_json_valido: str
    ) -> None:
        """execution_time_ms deve estar presente e ser positivo."""
        loader = DatasetLoader(backtest_json_valido)
        resultado = loader.load_backtest_optimized_results()

        assert "execution_time_ms" in resultado
        assert resultado["execution_time_ms"] >= 0
        assert resultado["execution_time_ms"] < 500

    def test_execution_time_ms_no_metadata_interno(
        self, backtest_json_valido: str
    ) -> None:
        """metadata['execution_time_ms'] deve estar presente."""
        loader = DatasetLoader(backtest_json_valido)
        resultado = loader.load_backtest_optimized_results()

        assert "execution_time_ms" in resultado["metadata"]
        assert resultado["metadata"]["execution_time_ms"] >= 0


# ============================================================================
# Testes - AC-3: Labels válidos (sem NaN, apenas 0 ou 1)
# ============================================================================

class TestAC3LabelsValidos:
    """AC-3: Labels válidos — apenas 0/1 sem NaN."""

    def test_sem_nan_no_label_map(self, backtest_json_valido: str) -> None:
        """Nenhum valor NaN deve existir no label_map."""
        loader = DatasetLoader(backtest_json_valido)
        resultado = loader.load_backtest_optimized_results()

        for window_id, label in resultado["label_map"].items():
            assert label in (0, 1), f"window_id={window_id} tem label={label}"

    def test_dataframe_sem_nan(self, backtest_json_valido: str) -> None:
        """DataFrame não deve ter valores NaN."""
        loader = DatasetLoader(backtest_json_valido)
        resultado = loader.load_backtest_optimized_results()

        df = resultado["dataframe"]
        assert df.isnull().sum().sum() == 0, "DataFrame contém NaN"

    def test_dataframe_colunas_corretas(self, backtest_json_valido: str) -> None:
        """DataFrame deve ter colunas window_id e label."""
        loader = DatasetLoader(backtest_json_valido)
        resultado = loader.load_backtest_optimized_results()

        df = resultado["dataframe"]
        assert "window_id" in df.columns
        assert "label" in df.columns

    def test_dataframe_tipos_corretos(self, backtest_json_valido: str) -> None:
        """Colunas do DataFrame devem ter tipos numéricos corretos."""
        loader = DatasetLoader(backtest_json_valido)
        resultado = loader.load_backtest_optimized_results()

        df = resultado["dataframe"]
        assert df["window_id"].dtype in (np.int32, np.int64, "int32", "int64")
        assert df["label"].dtype in (np.int32, np.int64, "int32", "int64")

    def test_distribuicao_win_rate_62_pct(
        self, backtest_json_valido: str
    ) -> None:
        """Com win_rate=62% e 137 matches, n_wins deve ser round(0.62*137)=85."""
        loader = DatasetLoader(backtest_json_valido)
        resultado = loader.load_backtest_optimized_results()

        metadata = resultado["metadata"]
        assert metadata["n_wins"] == round(137 * 0.62)
        assert metadata["n_losses"] == 137 - round(137 * 0.62)

    def test_win_rate_100_pct_todos_wins(
        self, backtest_json_win_rate_100: str
    ) -> None:
        """Com win_rate=100%, todos os labels devem ser 1 (win)."""
        loader = DatasetLoader(backtest_json_win_rate_100)
        resultado = loader.load_backtest_optimized_results()

        labels = list(resultado["label_map"].values())
        assert all(l == 1 for l in labels), "Todos deveriam ser wins (1)"

    def test_win_rate_0_pct_todos_losses(
        self, backtest_json_win_rate_0: str
    ) -> None:
        """Com win_rate=0%, todos os labels devem ser 0 (loss)."""
        loader = DatasetLoader(backtest_json_win_rate_0)
        resultado = loader.load_backtest_optimized_results()

        labels = list(resultado["label_map"].values())
        assert all(l == 0 for l in labels), "Todos deveriam ser losses (0)"

    def test_seed_fixo_garante_reproducibilidade(
        self, backtest_json_valido: str
    ) -> None:
        """Com a mesma seed, o mapeamento deve ser idêntico."""
        loader = DatasetLoader(backtest_json_valido)
        resultado_a = loader.load_backtest_optimized_results(seed=42)
        resultado_b = loader.load_backtest_optimized_results(seed=42)

        assert resultado_a["label_map"] == resultado_b["label_map"]

    def test_seed_diferente_gera_mapeamento_diferente(
        self, backtest_json_valido: str
    ) -> None:
        """Com seeds diferentes, o mapeamento deve ser diferente."""
        loader = DatasetLoader(backtest_json_valido)
        resultado_a = loader.load_backtest_optimized_results(seed=1)
        resultado_b = loader.load_backtest_optimized_results(seed=99)

        # Com 137 amostras e 2 seeds muito diferentes, deve haver diferença
        assert resultado_a["label_map"] != resultado_b["label_map"]


# ============================================================================
# Testes - Tratamento de Erros
# ============================================================================

class TestTratamentoDeErros:
    """Testes para tratamento de erros e casos extremos."""

    def test_arquivo_nao_encontrado_lanca_file_not_found(self) -> None:
        """FileNotFoundError deve ser lançado se arquivo não existe."""
        loader = DatasetLoader("/caminho/inexistente/backtest.json")
        with pytest.raises(FileNotFoundError):
            loader.load_backtest_optimized_results()

    def test_backtest_path_invalido_lanca_file_not_found(
        self, backtest_json_valido: str
    ) -> None:
        """FileNotFoundError ao passar backtest_path inexistente."""
        loader = DatasetLoader(backtest_json_valido)
        with pytest.raises(FileNotFoundError):
            loader.load_backtest_optimized_results(
                backtest_path="/nao/existe/backtest.json"
            )

    def test_sem_matches_lanca_value_error(
        self, backtest_json_sem_matches: str
    ) -> None:
        """ValueError deve ser lançado se matches=0."""
        loader = DatasetLoader(backtest_json_sem_matches)
        with pytest.raises(ValueError, match="Nenhum match"):
            loader.load_backtest_optimized_results()

    def test_win_rate_invalido_lanca_value_error(
        self, tmp_path: Path
    ) -> None:
        """ValueError deve ser lançado se win_rate > 100."""
        dados = {
            "metricas": {"matches": 50},
            "taxas": {"win_rate_estimado_pct": 150.0},
        }
        path = tmp_path / "backtest_invalido.json"
        path.write_text(json.dumps(dados), encoding="utf-8")

        loader = DatasetLoader(str(path))
        with pytest.raises(ValueError, match="Win rate invalido"):
            loader.load_backtest_optimized_results()

    def test_json_sem_campo_metricas_usa_defaults(
        self, tmp_path: Path
    ) -> None:
        """JSON sem campo metricas deve usar defaults (matches=0 → ValueError)."""
        dados = {
            "taxas": {"win_rate_estimado_pct": 62.0},
        }
        path = tmp_path / "backtest_sem_metricas.json"
        path.write_text(json.dumps(dados), encoding="utf-8")

        loader = DatasetLoader(str(path))
        with pytest.raises(ValueError, match="Nenhum match"):
            loader.load_backtest_optimized_results()

    def test_json_sem_campo_taxas_usa_win_rate_zero(
        self, tmp_path: Path
    ) -> None:
        """JSON sem campo taxas usa win_rate_estimado_pct=0.0 (todos losses)."""
        dados = {
            "metricas": {"matches": 20},
        }
        path = tmp_path / "backtest_sem_taxas.json"
        path.write_text(json.dumps(dados), encoding="utf-8")

        loader = DatasetLoader(str(path))
        resultado = loader.load_backtest_optimized_results()

        labels = list(resultado["label_map"].values())
        assert all(l == 0 for l in labels)


# ============================================================================
# Testes - Metadata
# ============================================================================

class TestMetadata:
    """Testes para validação da estrutura de metadata."""

    def test_metadata_contem_chaves_obrigatorias(
        self, backtest_json_valido: str
    ) -> None:
        """Metadata deve ter todas as chaves esperadas."""
        loader = DatasetLoader(backtest_json_valido)
        resultado = loader.load_backtest_optimized_results()

        chaves_obrigatorias = [
            "backtest_path",
            "threshold_sigma",
            "matches",
            "win_rate_estimado_pct",
            "actual_win_rate_pct",
            "n_wins",
            "n_losses",
            "velas_processadas",
            "status",
            "timestamp",
            "execution_time_ms",
        ]
        metadata = resultado["metadata"]
        for chave in chaves_obrigatorias:
            assert chave in metadata, f"Chave ausente em metadata: '{chave}'"

    def test_metadata_matches_correto(self, backtest_json_valido: str) -> None:
        """metadata['matches'] deve ser 137."""
        loader = DatasetLoader(backtest_json_valido)
        resultado = loader.load_backtest_optimized_results()

        assert resultado["metadata"]["matches"] == 137

    def test_metadata_win_rate_correto(self, backtest_json_valido: str) -> None:
        """metadata['win_rate_estimado_pct'] deve ser 62.0."""
        loader = DatasetLoader(backtest_json_valido)
        resultado = loader.load_backtest_optimized_results()

        assert resultado["metadata"]["win_rate_estimado_pct"] == 62.0

    def test_metadata_velas_processadas(self, backtest_json_valido: str) -> None:
        """metadata['velas_processadas'] deve ser 17280."""
        loader = DatasetLoader(backtest_json_valido)
        resultado = loader.load_backtest_optimized_results()

        assert resultado["metadata"]["velas_processadas"] == 17280

    def test_metadata_status_pass(self, backtest_json_valido: str) -> None:
        """metadata['status'] deve ser 'PASS'."""
        loader = DatasetLoader(backtest_json_valido)
        resultado = loader.load_backtest_optimized_results()

        assert resultado["metadata"]["status"] == "PASS"

    def test_metadata_n_wins_mais_n_losses_igual_matches(
        self, backtest_json_valido: str
    ) -> None:
        """n_wins + n_losses deve ser igual a matches."""
        loader = DatasetLoader(backtest_json_valido)
        resultado = loader.load_backtest_optimized_results()

        meta = resultado["metadata"]
        assert meta["n_wins"] + meta["n_losses"] == meta["matches"]

    def test_metadata_actual_win_rate_coerente(
        self, backtest_json_valido: str
    ) -> None:
        """actual_win_rate_pct deve ser coerente com n_wins/matches."""
        loader = DatasetLoader(backtest_json_valido)
        resultado = loader.load_backtest_optimized_results()

        meta = resultado["metadata"]
        esperado = round(meta["n_wins"] / meta["matches"] * 100, 2)
        assert abs(meta["actual_win_rate_pct"] - esperado) < 0.01

    def test_metadata_backtest_path_aponta_para_arquivo(
        self, backtest_json_valido: str
    ) -> None:
        """metadata['backtest_path'] deve apontar para o arquivo carregado."""
        loader = DatasetLoader(backtest_json_valido)
        resultado = loader.load_backtest_optimized_results()

        path_metadata = Path(resultado["metadata"]["backtest_path"])
        assert path_metadata.exists()


# ============================================================================
# Testes - Integração com DatasetLoader
# ============================================================================

class TestIntegracaoDatasetLoader:
    """Testes de integração: load_backtest_optimized_results + DatasetLoader."""

    def test_metodo_acessivel_via_dataset_loader(
        self, backtest_json_valido: str
    ) -> None:
        """Método deve estar disponível na classe DatasetLoader."""
        loader = DatasetLoader(backtest_json_valido)
        assert hasattr(loader, "load_backtest_optimized_results")
        assert callable(loader.load_backtest_optimized_results)

    def test_resultado_compativel_com_pandas_dataframe(
        self, backtest_json_valido: str
    ) -> None:
        """DataFrame retornado deve ser pandas.DataFrame válido."""
        loader = DatasetLoader(backtest_json_valido)
        resultado = loader.load_backtest_optimized_results()

        df = resultado["dataframe"]
        assert isinstance(df, pd.DataFrame)
        assert len(df) == 137

    def test_label_map_e_dataframe_sao_consistentes(
        self, backtest_json_valido: str
    ) -> None:
        """label_map e dataframe devem ter os mesmos valores."""
        loader = DatasetLoader(backtest_json_valido)
        resultado = loader.load_backtest_optimized_results()

        label_map = resultado["label_map"]
        df = resultado["dataframe"]

        for _, row in df.iterrows():
            wid = int(row["window_id"])
            assert label_map[wid] == int(row["label"]), (
                f"Inconsistencia em window_id={wid}: "
                f"label_map={label_map[wid]}, df={row['label']}"
            )

    def test_sem_conflito_com_load_and_label(
        self, backtest_json_valido: str
    ) -> None:
        """load_backtest_optimized_results não deve interferir em load_and_label."""
        import tempfile
        import os

        loader = DatasetLoader(backtest_json_valido)

        # Criar CSV temporário com 26 colunas (window_id + 24 features + label)
        np.random.seed(0)
        n = 100
        cols_features = [
            "volatility_bollinger_upper", "volatility_bollinger_lower",
            "volatility_atr", "volatility_historical",
            "momentum_rsi", "momentum_macd", "momentum_roc", "momentum_obv",
            "ma_sma_50", "ma_ema_9", "ma_ema_21",
            "ma_slope_short", "ma_slope_long",
            "pattern_mean_reversion", "pattern_volume_spike",
            "pattern_impulse", "lag_return_1", "lag_return_2",
            "lag_close_1", "lag_close_2", "lag_volume_1", "lag_volume_2",
            "correlation_20d", "correlation_trend",
        ]
        data: Dict[str, Any] = {"window_id": list(range(n))}
        for col in cols_features:
            data[col] = np.random.randn(n).tolist()
        # labels balanceados
        lbls = [1] * 50 + [0] * 50
        np.random.shuffle(lbls)
        data["label"] = lbls

        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".csv", delete=False
        ) as f:
            pd.DataFrame(data).to_csv(f, index=False)
            csv_path = f.name

        try:
            resultado_csv = loader.load_and_label(dataset_path=csv_path)
            resultado_json = loader.load_backtest_optimized_results()

            assert resultado_csv is not None
            assert resultado_json is not None
        finally:
            os.unlink(csv_path)
