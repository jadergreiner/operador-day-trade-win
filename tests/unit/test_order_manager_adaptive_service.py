"""
Testes TDD para OrderManagerAdaptiveService.

Cobre identificacao de regime, deteccao de vies direcional,
retreinamento incremental e geracao de relatorio diario.
"""
from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import patch, MagicMock

import pytest

from src.application.diario_episodio_operador import EpisodioOperador
from src.application.services.order_manager_adaptive_service import (
    OrderManagerAdaptiveService,
    RegimeMercado,
)


# ────────────────────────────────────────────────────────────
# Helpers / Fixtures
# ────────────────────────────────────────────────────────────

def _criar_episodio(
    direcao: str = "BUY",
    foi_acerto: bool = True,
    resultado_pts: float = 5.0,
) -> EpisodioOperador:
    """Cria EpisodioOperador com campos minimos para testes."""
    return EpisodioOperador(
        session_id="test-001",
        timestamp_entrada="2026-04-04T10:00:00",
        timestamp_saida="2026-04-04T10:30:00",
        direcao=direcao,
        preco_entrada=100.0,
        preco_saida=105.0 if foi_acerto else 95.0,
        sl=98.0,
        tp=108.0,
        atr_entrada=2.0,
        resultado_pts=resultado_pts,
        motivo_saida="tp",
        fase_sessao="manha",
        qualidade_movimento="forte",
        exaustao=False,
        pullback=False,
        correlacao_estado="alinhado",
        divergencia_critica=False,
        risco_armadilha="baixo",
        preco_extremo=False,
        desvio_vwap_pts=0.0,
        ajuste_confianca_leitura=0.0,
        confianca_entrada=75.0,
        alinhamento_entrada=0.8,
        momentum_entrada=0.6,
        foi_acerto=foi_acerto,
        max_ganho_pts=abs(resultado_pts),
        eficiencia=0.8,
    )


@pytest.fixture
def servico() -> OrderManagerAdaptiveService:
    """Instancia do servico para testes."""
    return OrderManagerAdaptiveService()


def _candles_tendencia_alta(n: int = 10) -> list[dict[str, float]]:
    """
    Candles com range pequeno e progressao de preco crescente.

    adx_proxy = (range_total / media_range) * _ADX_PROXY_FATOR_ESCALA >> 25.
    range_total < 2.0 * soma_ranges (nao VOLATIL).
    ultimo close > primeiro close (ALTA).
    """
    candles = []
    for i in range(n):
        # Preco sobe 1.8 por candle, range=1 por candle
        close = 100.0 + i * 1.8
        candles.append({"high": close + 0.5, "low": close - 0.5, "close": close})
    return candles


def _candles_tendencia_baixa(n: int = 10) -> list[dict[str, float]]:
    """
    Candles com range pequeno e progressao de preco decrescente.

    adx_proxy >> 25. ultimo close < primeiro close (BAIXA).
    """
    candles = []
    for i in range(n):
        # Preco cai 1.8 por candle, range=1 por candle
        close = 100.0 + (n - 1 - i) * 1.8
        candles.append({"high": close + 0.5, "low": close - 0.5, "close": close})
    return candles


def _candles_laterais(n: int = 10) -> list[dict[str, float]]:
    """
    Candles todos no mesmo nivel de preco — ADX proxy baixo, lateral.

    range_total ≈ media_range → adx_proxy ≈ 10 < 25 → LATERAL.
    """
    candles = []
    for _ in range(n):
        candles.append({"high": 100.1, "low": 99.9, "close": 100.0})
    return candles


def _candles_volateis() -> list[dict[str, float]]:
    """
    Dois candles com range minimo mas salto de preco extremo.

    range_total >> soma_ranges → dispara VOLATIL.
    """
    return [
        {"high": 100.05, "low": 99.95, "close": 100.0},
        {"high": 200.05, "low": 199.95, "close": 200.0},
    ]


# ────────────────────────────────────────────────────────────
# 1. Testes de identificar_regime
# ────────────────────────────────────────────────────────────

def test_identificar_regime_tendencia_alta(servico: OrderManagerAdaptiveService) -> None:
    """
    Candles com range pequeno e progressao crescente: TENDENCIA_ALTA, multiplier 1.5.

    adx_proxy = (range_total / media_range) * 10 >= 25.
    range_total <= 2.0 * soma_ranges (nao VOLATIL).
    ultimo close > primeiro close.
    """
    candles = _candles_tendencia_alta()

    resultado = servico.identificar_regime(candles)

    assert resultado.regime == RegimeMercado.TENDENCIA_ALTA
    assert resultado.atr_multiplier_sl == pytest.approx(1.5)
    assert resultado.atr_multiplier_tp == pytest.approx(1.5)


def test_identificar_regime_tendencia_baixa(servico: OrderManagerAdaptiveService) -> None:
    """
    Candles com range pequeno e progressao decrescente: TENDENCIA_BAIXA, multiplier 1.5.
    """
    candles = _candles_tendencia_baixa()

    resultado = servico.identificar_regime(candles)

    assert resultado.regime == RegimeMercado.TENDENCIA_BAIXA
    assert resultado.atr_multiplier_sl == pytest.approx(1.5)
    assert resultado.atr_multiplier_tp == pytest.approx(1.5)


def test_identificar_regime_lateral(servico: OrderManagerAdaptiveService) -> None:
    """
    Candles todos no mesmo nivel (ADX proxy baixo): LATERAL, multiplier 0.8.
    """
    candles = _candles_laterais()

    resultado = servico.identificar_regime(candles)

    assert resultado.regime == RegimeMercado.LATERAL
    assert resultado.atr_multiplier_sl == pytest.approx(0.8)
    assert resultado.atr_multiplier_tp == pytest.approx(0.8)


def test_identificar_regime_volatil(servico: OrderManagerAdaptiveService) -> None:
    """
    Dois candles com range minimo e salto extremo: VOLATIL, multiplier 1.2.

    range_total >> 2.0 * soma_ranges dispara classificacao VOLATIL.
    """
    candles = _candles_volateis()

    resultado = servico.identificar_regime(candles)

    assert resultado.regime == RegimeMercado.VOLATIL
    assert resultado.atr_multiplier_sl == pytest.approx(1.2)
    assert resultado.atr_multiplier_tp == pytest.approx(1.2)


def test_identificar_regime_lista_vazia(servico: OrderManagerAdaptiveService) -> None:
    """
    Lista vazia deve retornar LATERAL como fallback seguro.
    """
    resultado = servico.identificar_regime([])

    assert resultado.regime == RegimeMercado.LATERAL
    assert resultado.atr_multiplier_sl == pytest.approx(0.8)


# ────────────────────────────────────────────────────────────
# 2. Testes de detectar_vies_direcional
# ────────────────────────────────────────────────────────────

def test_detectar_vies_sem_episodios(
    servico: OrderManagerAdaptiveService, tmp_path: Path
) -> None:
    """
    BD vazio deve retornar detectado=False.
    """
    db_path = tmp_path / "test.db"

    with patch(
        "src.application.services.order_manager_adaptive_service.EpisodioOperadorRepo"
    ) as MockRepo:
        mock_repo = MockRepo.return_value
        mock_repo.listar_ultimos.return_value = []

        resultado = servico.detectar_vies_direcional(db_path)

    assert resultado.detectado is False
    assert resultado.direcao_dominante == ""


def test_detectar_vies_equilibrado(
    servico: OrderManagerAdaptiveService, tmp_path: Path
) -> None:
    """
    50% BUY / 50% SELL deve retornar detectado=False.
    """
    db_path = tmp_path / "test.db"
    episodios = (
        [_criar_episodio(direcao="BUY") for _ in range(10)]
        + [_criar_episodio(direcao="SELL") for _ in range(10)]
    )

    with patch(
        "src.application.services.order_manager_adaptive_service.EpisodioOperadorRepo"
    ) as MockRepo:
        mock_repo = MockRepo.return_value
        mock_repo.listar_ultimos.return_value = episodios

        resultado = servico.detectar_vies_direcional(db_path)

    assert resultado.detectado is False


def test_detectar_vies_buy_dominante(
    servico: OrderManagerAdaptiveService, tmp_path: Path
) -> None:
    """
    80% BUY deve retornar detectado=True, direcao_dominante='BUY', ratio=0.8.
    """
    db_path = tmp_path / "test.db"
    episodios = (
        [_criar_episodio(direcao="BUY") for _ in range(16)]
        + [_criar_episodio(direcao="SELL") for _ in range(4)]
    )

    with patch(
        "src.application.services.order_manager_adaptive_service.EpisodioOperadorRepo"
    ) as MockRepo:
        mock_repo = MockRepo.return_value
        mock_repo.listar_ultimos.return_value = episodios

        with patch.object(servico, "_contar_pregoes_vies", return_value=2):
            resultado = servico.detectar_vies_direcional(db_path)

    assert resultado.detectado is True
    assert resultado.direcao_dominante == "BUY"
    assert resultado.ratio == pytest.approx(0.8)


def test_detectar_vies_sell_dominante(
    servico: OrderManagerAdaptiveService, tmp_path: Path
) -> None:
    """
    80% SELL deve retornar detectado=True, direcao_dominante='SELL'.
    """
    db_path = tmp_path / "test.db"
    episodios = (
        [_criar_episodio(direcao="SELL") for _ in range(16)]
        + [_criar_episodio(direcao="BUY") for _ in range(4)]
    )

    with patch(
        "src.application.services.order_manager_adaptive_service.EpisodioOperadorRepo"
    ) as MockRepo:
        mock_repo = MockRepo.return_value
        mock_repo.listar_ultimos.return_value = episodios

        with patch.object(servico, "_contar_pregoes_vies", return_value=2):
            resultado = servico.detectar_vies_direcional(db_path)

    assert resultado.detectado is True
    assert resultado.direcao_dominante == "SELL"


def test_detectar_vies_persiste_feedback(
    servico: OrderManagerAdaptiveService, tmp_path: Path
) -> None:
    """
    Vies detectado com pregoes >= 2 deve chamar save_diary_feedback.
    """
    db_path = tmp_path / "test.db"
    episodios = (
        [_criar_episodio(direcao="BUY") for _ in range(16)]
        + [_criar_episodio(direcao="SELL") for _ in range(4)]
    )

    with patch(
        "src.application.services.order_manager_adaptive_service.EpisodioOperadorRepo"
    ) as MockRepo:
        mock_repo = MockRepo.return_value
        mock_repo.listar_ultimos.return_value = episodios

        with patch.object(servico, "_contar_pregoes_vies", return_value=2):
            with patch(
                "src.application.services.order_manager_adaptive_service.save_diary_feedback"
            ) as mock_save:
                resultado = servico.detectar_vies_direcional(db_path)

    assert resultado.detectado is True
    mock_save.assert_called_once()
    chamada_feedback = mock_save.call_args[0][1]
    assert chamada_feedback.source == "vies_detector"
    assert chamada_feedback.retreinamento_necessario is True


# ────────────────────────────────────────────────────────────
# 3. Testes de executar_retreinamento
# ────────────────────────────────────────────────────────────

def test_retreinamento_sem_episodios_suficientes(
    servico: OrderManagerAdaptiveService, tmp_path: Path
) -> None:
    """
    Menos de 10 episodios deve retornar acionado=False.
    """
    db_path = tmp_path / "test.db"
    modelo_dir = tmp_path / "modelos"
    episodios = [_criar_episodio(resultado_pts=5.0) for _ in range(5)]

    with patch(
        "src.application.services.order_manager_adaptive_service.EpisodioOperadorRepo"
    ) as MockRepo:
        mock_repo = MockRepo.return_value
        mock_repo.listar_ultimos.return_value = episodios

        resultado = servico.executar_retreinamento(db_path, modelo_dir)

    assert resultado.acionado is False
    assert resultado.n_episodios == 5
    assert resultado.caminho_modelo is None
    assert "insuficientes" in resultado.motivo_nao_acionado.lower()


def test_retreinamento_aciona_com_10_episodios(
    servico: OrderManagerAdaptiveService, tmp_path: Path
) -> None:
    """
    12 episodios conhecidos devem acionar retreinamento e criar arquivo JSON.
    """
    db_path = tmp_path / "test.db"
    modelo_dir = tmp_path / "modelos"
    episodios = [_criar_episodio(resultado_pts=5.0) for _ in range(12)]

    with patch(
        "src.application.services.order_manager_adaptive_service.EpisodioOperadorRepo"
    ) as MockRepo:
        mock_repo = MockRepo.return_value
        mock_repo.listar_ultimos.return_value = episodios

        resultado = servico.executar_retreinamento(db_path, modelo_dir)

    assert resultado.acionado is True
    assert resultado.n_episodios == 12
    assert resultado.caminho_modelo is not None
    assert resultado.caminho_modelo.exists()

    # Verificar conteudo do arquivo gerado
    conteudo = json.loads(resultado.caminho_modelo.read_text(encoding="utf-8"))
    assert conteudo["schema_version"] == "1.0"
    assert conteudo["n_episodios"] == 12
    assert len(conteudo["features"]) == 12


def test_retreinamento_salva_historico_versoes(
    servico: OrderManagerAdaptiveService, tmp_path: Path
) -> None:
    """
    Retreinamento deve atualizar historico_versoes.json com schema_version='1.0'.
    """
    db_path = tmp_path / "test.db"
    modelo_dir = tmp_path / "modelos"
    episodios = [_criar_episodio(resultado_pts=5.0) for _ in range(12)]

    with patch(
        "src.application.services.order_manager_adaptive_service.EpisodioOperadorRepo"
    ) as MockRepo:
        mock_repo = MockRepo.return_value
        mock_repo.listar_ultimos.return_value = episodios

        resultado = servico.executar_retreinamento(db_path, modelo_dir)

    assert resultado.acionado is True

    historico_path = modelo_dir / "historico_versoes.json"
    assert historico_path.exists()

    historico = json.loads(historico_path.read_text(encoding="utf-8"))
    assert historico["schema_version"] == "1.0"
    assert len(historico["versoes"]) == 1
    assert historico["versoes"][0]["n_episodios"] == 12
    assert historico["versoes"][0]["versao"] == resultado.versao


def test_retreinamento_win_rate_calculado_corretamente(
    servico: OrderManagerAdaptiveService, tmp_path: Path
) -> None:
    """
    8 acertos em 12 episodios deve resultar em win_rate ~ 0.667.
    """
    db_path = tmp_path / "test.db"
    modelo_dir = tmp_path / "modelos"

    episodios = (
        [_criar_episodio(foi_acerto=True, resultado_pts=5.0) for _ in range(8)]
        + [_criar_episodio(foi_acerto=False, resultado_pts=-3.0) for _ in range(4)]
    )

    with patch(
        "src.application.services.order_manager_adaptive_service.EpisodioOperadorRepo"
    ) as MockRepo:
        mock_repo = MockRepo.return_value
        mock_repo.listar_ultimos.return_value = episodios

        resultado = servico.executar_retreinamento(db_path, modelo_dir)

    assert resultado.acionado is True
    assert resultado.win_rate == pytest.approx(8 / 12, abs=1e-6)


# ────────────────────────────────────────────────────────────
# 4. Teste de gerar_relatorio_diario
# ────────────────────────────────────────────────────────────

def test_gerar_relatorio_diario_cria_arquivo_md(
    servico: OrderManagerAdaptiveService, tmp_path: Path
) -> None:
    """
    gerar_relatorio_diario deve criar arquivo .md no diretorio de saida.
    """
    db_path = tmp_path / "test.db"
    modelo_dir = tmp_path / "modelos"
    outputs_dir = tmp_path / "outputs"

    episodios = [_criar_episodio() for _ in range(5)]

    with patch(
        "src.application.services.order_manager_adaptive_service.EpisodioOperadorRepo"
    ) as MockRepo:
        mock_repo = MockRepo.return_value
        mock_repo.listar_ultimos.return_value = episodios

        with patch.object(
            servico,
            "detectar_vies_direcional",
            return_value=MagicMock(
                detectado=False,
                direcao_dominante="",
                ratio=0.5,
                ajuste_threshold_pp=0,
                pregoes_consecutivos=0,
                motivo="Sem vies detectado",
            ),
        ):
            with patch.object(
                servico,
                "executar_retreinamento",
                return_value=MagicMock(
                    acionado=False,
                    n_episodios=5,
                    win_rate=0.0,
                    versao="",
                    caminho_modelo=None,
                    motivo_nao_acionado="Episodios insuficientes: 5/10",
                ),
            ):
                caminho = servico.gerar_relatorio_diario(db_path, modelo_dir, outputs_dir)

    assert caminho.exists()
    assert caminho.suffix == ".md"
    assert "order_manager_relatorio_" in caminho.name

    conteudo = caminho.read_text(encoding="utf-8")
    assert "Order Manager" in conteudo
    assert "Metricas do Dia" in conteudo
    assert "schema_version=1.0" in conteudo
