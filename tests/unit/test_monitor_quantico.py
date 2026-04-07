"""
Testes unitarios para scripts/monitor_quantico_tendencia.py

Cobre:
- _buscar_yfinance: preco zero, sem yfinance, variacao, campos, excecao
- Validacao de sanidade de precos (LIMITES_SANIDADE)
- Mapa de simbolos Yahoo Finance (_MAPA_YFINANCE)
- _buscar_dados_externos: 3-tupla, criticos ausentes, sanidade falha
- _calcular_score_tendencia: denominador fixo 7, WIN$ nao conta
- _thread_atualizacao: sleep antes da coleta
- _buscar_indicadores_tv: tv-ta ausente, campos, excecao
- qualidade_dados no JSON e backward-compat com HTML

Status: v2.0 (01/04/2026) — migrado para yfinance
Referencia: docs/BACKLOG.md
"""

from __future__ import annotations

import sys
import json
from datetime import datetime
from pathlib import Path
from typing import Any
from unittest.mock import MagicMock, patch

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

import scripts.monitor_quantico_tendencia as mqt


# ---------------------------------------------------------------------------
# Helpers de fixture
# ---------------------------------------------------------------------------

def _dado_ativo(preco: float = 100.0, variacao: float = 1.0) -> dict[str, Any]:
    return {
        "preco": preco,
        "variacao_pct": variacao,
        "abertura": preco * 0.99,
        "max": preco * 1.01,
        "min": preco * 0.98,
    }


def _ativos_completos() -> dict[str, Any]:
    """Retorna os 7 ativos externos com precos dentro dos limites de sanidade."""
    return {
        "sp500":        _dado_ativo(5500.0,  1.0),
        "nasdaq":       _dado_ativo(18000.0, 1.2),
        "dxy":          _dado_ativo(104.0,  -0.3),
        "vix":          _dado_ativo(18.0,   -5.0),
        "ouro":         _dado_ativo(3200.0,  0.5),
        "petroleo_wti": _dado_ativo(70.0,   -1.0),
        "usd_brl":      _dado_ativo(5.10,    0.2),
    }


def _fast_info_mock(
    last_price: float = 5500.0,
    open_: float = 5480.0,
    day_high: float = 5520.0,
    day_low: float = 5470.0,
) -> MagicMock:
    """Cria mock de yf.Ticker().fast_info."""
    fi = MagicMock()
    fi.last_price = last_price
    fi.open = open_
    fi.day_high = day_high
    fi.day_low = day_low
    return fi


def _ticker_mock(fast_info: MagicMock) -> MagicMock:
    t = MagicMock()
    t.fast_info = fast_info
    return t


# ---------------------------------------------------------------------------
# TestBuscarYfinance
# ---------------------------------------------------------------------------

class TestBuscarYfinance:
    """Testa _buscar_yfinance."""

    @pytest.mark.unit
    def test_retorna_none_quando_preco_zero(self) -> None:
        """Preco zero e sentinela de sem-dado — deve retornar None."""
        fi = _fast_info_mock(last_price=0.0)
        with (
            patch.object(mqt, "_YFINANCE_DISPONIVEL", True),
            patch("scripts.monitor_quantico_tendencia.yf.Ticker",
                  return_value=_ticker_mock(fi)),
        ):
            resultado = mqt._buscar_yfinance("sp500", "^GSPC")
        assert resultado is None

    @pytest.mark.unit
    def test_retorna_none_sem_yfinance(self) -> None:
        """Sem yfinance instalado retorna None sem chamar yf.Ticker."""
        with patch.object(mqt, "_YFINANCE_DISPONIVEL", False):
            resultado = mqt._buscar_yfinance("sp500", "^GSPC")
        assert resultado is None

    @pytest.mark.unit
    def test_calcula_variacao_corretamente(self) -> None:
        """Variacao = (preco - abertura) / abertura * 100."""
        fi = _fast_info_mock(last_price=110.0, open_=100.0)
        with (
            patch.object(mqt, "_YFINANCE_DISPONIVEL", True),
            patch("scripts.monitor_quantico_tendencia.yf.Ticker",
                  return_value=_ticker_mock(fi)),
        ):
            resultado = mqt._buscar_yfinance("sp500", "^GSPC")
        assert resultado is not None
        assert resultado["preco"] == 110.0
        assert resultado["variacao_pct"] == pytest.approx(10.0, abs=0.01)

    @pytest.mark.unit
    def test_retorna_campos_obrigatorios(self) -> None:
        """Retorno deve conter preco/variacao_pct/abertura/max/min."""
        fi = _fast_info_mock()
        with (
            patch.object(mqt, "_YFINANCE_DISPONIVEL", True),
            patch("scripts.monitor_quantico_tendencia.yf.Ticker",
                  return_value=_ticker_mock(fi)),
        ):
            resultado = mqt._buscar_yfinance("sp500", "^GSPC")
        assert resultado is not None
        for campo in ("preco", "variacao_pct", "abertura", "max", "min"):
            assert campo in resultado

    @pytest.mark.unit
    def test_retorna_none_em_excecao(self) -> None:
        """Excecao de qualquer tipo retorna None sem propagar."""
        with (
            patch.object(mqt, "_YFINANCE_DISPONIVEL", True),
            patch("scripts.monitor_quantico_tendencia.yf.Ticker",
                  side_effect=Exception("conexao recusada")),
        ):
            resultado = mqt._buscar_yfinance("sp500", "^GSPC")
        assert resultado is None

    @pytest.mark.unit
    def test_open_none_nao_divide_por_zero(self) -> None:
        """fast_info.open = None nao deve lancar ZeroDivisionError."""
        fi = _fast_info_mock(last_price=5500.0)
        fi.open = None
        with (
            patch.object(mqt, "_YFINANCE_DISPONIVEL", True),
            patch("scripts.monitor_quantico_tendencia.yf.Ticker",
                  return_value=_ticker_mock(fi)),
        ):
            resultado = mqt._buscar_yfinance("sp500", "^GSPC")
        assert resultado is not None
        assert resultado["variacao_pct"] == 0.0


# ---------------------------------------------------------------------------
# TestPrecoDentroLimites
# ---------------------------------------------------------------------------

class TestPrecoDentroLimites:
    """Testa a funcao auxiliar _preco_dentro_limites."""

    @pytest.mark.unit
    def test_preco_valido_sp500_passa(self) -> None:
        assert mqt._preco_dentro_limites("sp500", 5500.0) is True

    @pytest.mark.unit
    def test_preco_abaixo_minimo_falha(self) -> None:
        assert mqt._preco_dentro_limites("sp500", 100.0) is False

    @pytest.mark.unit
    def test_preco_acima_maximo_falha(self) -> None:
        assert mqt._preco_dentro_limites("sp500", 99_999.0) is False

    @pytest.mark.unit
    def test_chave_sem_limites_sempre_passa(self) -> None:
        assert mqt._preco_dentro_limites("ativo_desconhecido", 0.001) is True

    @pytest.mark.unit
    def test_wti_preco_341_falha(self) -> None:
        """Reproducao do bug historico P2: $3.41 e invalido para WTI."""
        assert mqt._preco_dentro_limites("petroleo_wti", 3.41) is False

    @pytest.mark.unit
    def test_vix_zero_falha(self) -> None:
        assert mqt._preco_dentro_limites("vix", 0.0) is False

    @pytest.mark.unit
    def test_vix_normal_passa(self) -> None:
        assert mqt._preco_dentro_limites("vix", 18.5) is True

    @pytest.mark.unit
    def test_wti_preco_valido_passa(self) -> None:
        assert mqt._preco_dentro_limites("petroleo_wti", 72.0) is True


# ---------------------------------------------------------------------------
# TestMapaSimbolos
# ---------------------------------------------------------------------------

class TestMapaSimbolos:
    """Verifica que o mapa de simbolos yfinance esta correto."""

    @pytest.mark.unit
    def test_wti_simbolo_correto_no_yfinance(self) -> None:
        """WTI deve usar CL=F (futuro continuo) no Yahoo Finance."""
        assert mqt._MAPA_YFINANCE["petroleo_wti"] == "CL=F"

    @pytest.mark.unit
    def test_total_ativos_yfinance_e_nove(self) -> None:
        assert len(mqt._MAPA_YFINANCE) == 9

    @pytest.mark.unit
    def test_ativos_criticos_contem_sp500_e_dxy(self) -> None:
        assert "sp500" in mqt._ATIVOS_CRITICOS
        assert "dxy" in mqt._ATIVOS_CRITICOS

    @pytest.mark.unit
    def test_vix_simbolo_correto(self) -> None:
        assert mqt._MAPA_YFINANCE["vix"] == "^VIX"

    @pytest.mark.unit
    def test_ibov_simbolo_correto(self) -> None:
        assert mqt._MAPA_YFINANCE["ibov"] == "^BVSP"


# ---------------------------------------------------------------------------
# TestBuscarDadosExternos
# ---------------------------------------------------------------------------

class TestBuscarDadosExternos:
    """Testa _buscar_dados_externos com mocks de _buscar_yfinance."""

    @pytest.mark.unit
    def test_retorna_tupla_tres_elementos(self) -> None:
        with patch.object(mqt, "_buscar_yfinance", return_value=None):
            resultado = mqt._buscar_dados_externos()
        assert isinstance(resultado, tuple)
        assert len(resultado) == 3

    @pytest.mark.unit
    def test_ativos_criticos_ausentes_quando_sem_dados(self) -> None:
        with patch.object(mqt, "_buscar_yfinance", return_value=None):
            _, criticos, _ = mqt._buscar_dados_externos()
        assert "sp500" in criticos
        assert "dxy" in criticos

    @pytest.mark.unit
    def test_sanidade_falha_rastreada(self) -> None:
        """Preco invalido de WTI deve aparecer em ativos_sanidade_falha."""
        dado_invalido: dict[str, Any] = {"preco": 3.41, "variacao_pct": -5.0}
        dado_valido = _dado_ativo(5500.0, 1.0)

        def _yf_mock(chave: str, simbolo: str) -> Any:
            if chave == "petroleo_wti":
                return dado_invalido
            if chave == "sp500":
                return dado_valido
            return None

        with patch.object(mqt, "_buscar_yfinance", side_effect=_yf_mock):
            ativos, _, sanidade_falha = mqt._buscar_dados_externos()

        assert "petroleo_wti" in sanidade_falha
        assert "petroleo_wti" not in ativos

    @pytest.mark.unit
    def test_ativo_valido_aceito(self) -> None:
        dado = _dado_ativo(5500.0, 1.0)
        with patch.object(
            mqt, "_buscar_yfinance",
            side_effect=lambda c, s: dado if c == "sp500" else None,
        ):
            ativos, _, _ = mqt._buscar_dados_externos()
        assert "sp500" in ativos

    @pytest.mark.unit
    def test_sem_dados_dict_vazio(self) -> None:
        """Sem nenhum dado coletado, ativos deve ser dict vazio."""
        with patch.object(mqt, "_buscar_yfinance", return_value=None):
            ativos, _, _ = mqt._buscar_dados_externos()
        assert ativos == {}


# ---------------------------------------------------------------------------
# TestCalcularScoreTendencia
# ---------------------------------------------------------------------------

class TestCalcularScoreTendencia:
    """Testa _calcular_score_tendencia com foco no denominador de confianca."""

    @pytest.mark.unit
    def test_denominador_fixo_sem_mt5(self) -> None:
        """Sem MT5, confianca = ativos_com_dados / 7."""
        ativos = _ativos_completos()
        resultado = mqt._calcular_score_tendencia(ativos, {})
        assert resultado["ativos_externos_total"] == 7
        assert resultado["confianca_pct"] == 100

    @pytest.mark.unit
    def test_denominador_fixo_com_mt5(self) -> None:
        """Com MT5, denominador ainda e 7 — WIN$ nao altera a confianca."""
        ativos = _ativos_completos()
        mt5 = {"win": {"variacao_pct": 0.5, "preco": 140000.0}}
        resultado_sem = mqt._calcular_score_tendencia(ativos, {})
        resultado_com = mqt._calcular_score_tendencia(ativos, mt5)
        assert resultado_sem["confianca_pct"] == resultado_com["confianca_pct"]

    @pytest.mark.unit
    def test_win_nao_conta_no_denominador(self) -> None:
        ativos = _ativos_completos()
        mt5 = {"win": {"variacao_pct": 1.0, "preco": 140000.0}}
        resultado = mqt._calcular_score_tendencia(ativos, mt5)
        assert resultado["confianca_pct"] == 100
        assert resultado["ativos_externos_total"] == mqt._TOTAL_FATORES_EXTERNOS

    @pytest.mark.unit
    def test_confianca_proporcional_a_ativos_disponiveis(self) -> None:
        ativos = {
            "sp500": _dado_ativo(5500.0, 1.0),
            "nasdaq": _dado_ativo(18000.0, 1.2),
            "dxy": _dado_ativo(104.0, -0.3),
        }
        resultado = mqt._calcular_score_tendencia(ativos, {})
        assert resultado["confianca_pct"] == int(3 / 7 * 100)

    @pytest.mark.unit
    def test_score_clampado_em_100(self) -> None:
        ativos = {k: _dado_ativo(v, 5.0) for k, v in {
            "sp500": 5500.0, "nasdaq": 18000.0, "dxy": 104.0,
            "vix": 10.0, "ouro": 3200.0, "petroleo_wti": 72.0,
            "usd_brl": 5.1,
        }.items()}
        assert mqt._calcular_score_tendencia(ativos, {})["score"] <= 100.0

    @pytest.mark.unit
    def test_score_clampado_em_menos_100(self) -> None:
        ativos = {k: _dado_ativo(v, -5.0) for k, v in {
            "sp500": 5500.0, "nasdaq": 18000.0, "dxy": 104.0,
            "vix": 10.0, "ouro": 3200.0, "petroleo_wti": 72.0,
            "usd_brl": 5.1,
        }.items()}
        assert mqt._calcular_score_tendencia(ativos, {})["score"] >= -100.0

    @pytest.mark.unit
    def test_todos_ativos_ausentes_confianca_zero(self) -> None:
        resultado = mqt._calcular_score_tendencia({}, {})
        assert resultado["confianca_pct"] == 0
        assert resultado["ativos_com_dados"] == 0


# ---------------------------------------------------------------------------
# TestThreadAtualizacao
# ---------------------------------------------------------------------------

class TestThreadAtualizacao:
    """Testa que _thread_atualizacao dorme ANTES da primeira coleta."""

    @pytest.mark.unit
    def test_sleep_antes_da_primeira_coleta(self) -> None:
        chamadas: list[str] = []
        iteracoes = {"n": 0}

        def _sleep_mock(t: float) -> None:
            chamadas.append("sleep")
            iteracoes["n"] += 1
            if iteracoes["n"] >= 2:
                raise StopIteration

        def _coleta_mock() -> None:
            chamadas.append("coleta")

        with (
            patch("scripts.monitor_quantico_tendencia.time.sleep",
                  side_effect=_sleep_mock),
            patch("scripts.monitor_quantico_tendencia._atualizar_dados",
                  side_effect=_coleta_mock),
        ):
            with pytest.raises(StopIteration):
                mqt._thread_atualizacao()

        assert len(chamadas) >= 2
        assert chamadas[0] == "sleep", "Thread deve dormir ANTES da primeira coleta"
        assert chamadas[1] == "coleta"

    @pytest.mark.unit
    def test_intervalo_de_sleep_correto(self) -> None:
        sleeps: list[float] = []

        def _sleep_mock(t: float) -> None:
            sleeps.append(t)
            raise StopIteration

        with (
            patch("scripts.monitor_quantico_tendencia.time.sleep",
                  side_effect=_sleep_mock),
            patch("scripts.monitor_quantico_tendencia._atualizar_dados"),
        ):
            with pytest.raises(StopIteration):
                mqt._thread_atualizacao()

        assert sleeps[0] == mqt.INTERVALO_ATUALIZACAO


# ---------------------------------------------------------------------------
# TestBuscarIndicadoresTv
# ---------------------------------------------------------------------------

class TestBuscarIndicadoresTv:
    """Testa _buscar_indicadores_tv."""

    @pytest.mark.unit
    def test_retorna_none_sem_tradingview_ta(self) -> None:
        with patch.object(mqt, "_TV_TA_DISPONIVEL", False):
            resultado = mqt._buscar_indicadores_tv("WINCONTFUT")
        assert resultado is None

    @pytest.mark.unit
    def test_retorna_campos_esperados(self) -> None:
        mock_analysis = MagicMock()
        mock_analysis.indicators = {
            "RSI": 58.5,
            "MACD.macd": 120.0,
            "MACD.signal": 115.0,
            "EMA20": 140500.0,
        }
        mock_analysis.summary = {
            "RECOMMENDATION": "BUY",
            "BUY": 12,
            "SELL": 4,
            "NEUTRAL": 6,
        }
        mock_handler = MagicMock()
        mock_handler.get_analysis.return_value = mock_analysis

        with (
            patch.object(mqt, "_TV_TA_DISPONIVEL", True),
            patch("scripts.monitor_quantico_tendencia.TA_Handler",
                  return_value=mock_handler),
        ):
            resultado = mqt._buscar_indicadores_tv("WINCONTFUT")

        assert resultado is not None
        assert resultado["rsi"] == pytest.approx(58.5)
        assert resultado["recomendacao"] == "BUY"
        assert resultado["sinal_buy"] == 12
        assert resultado["simbolo"] == "WINCONTFUT"
        assert resultado["intervalo"] == "5m"

    @pytest.mark.unit
    def test_retorna_none_em_excecao(self) -> None:
        with (
            patch.object(mqt, "_TV_TA_DISPONIVEL", True),
            patch("scripts.monitor_quantico_tendencia.TA_Handler",
                  side_effect=Exception("sem conexao")),
        ):
            resultado = mqt._buscar_indicadores_tv("WINCONTFUT")
        assert resultado is None


# ---------------------------------------------------------------------------
# TestQualidadeDadosJson
# ---------------------------------------------------------------------------

class TestQualidadeDadosJson:
    """Testa presenca de qualidade_dados no JSON e compatibilidade backward."""

    def _executar_atualizar_dados(self) -> dict[str, Any]:
        ativos = _ativos_completos()
        with (
            patch.object(
                mqt, "_buscar_dados_externos",
                return_value=(ativos, [], []),
            ),
            patch.object(mqt, "_dados_mt5", return_value={}),
            patch.object(mqt, "_buscar_indicadores_tv", return_value=None),
        ):
            mqt._atualizar_dados()
        with mqt._lock_cache:
            return dict(mqt._cache_dados)

    @pytest.mark.unit
    def test_qualidade_dados_presente_no_json(self) -> None:
        dados = self._executar_atualizar_dados()
        assert "qualidade_dados" in dados

    @pytest.mark.unit
    def test_qualidade_dados_campos_obrigatorios(self) -> None:
        qd = self._executar_atualizar_dados()["qualidade_dados"]
        assert "ativos_disponiveis" in qd
        assert "ativos_total_esperado" in qd
        assert "ativos_criticos_ausentes" in qd
        assert "ativos_sanidade_falha" in qd
        assert "confianca_score" in qd

    @pytest.mark.unit
    def test_indicadores_tv_presente_no_json(self) -> None:
        """Campo indicadores_tv deve aparecer no JSON (pode ser None)."""
        dados = self._executar_atualizar_dados()
        assert "indicadores_tv" in dados

    @pytest.mark.unit
    def test_backward_compat_campos_html(self) -> None:
        """Campos consumidos pelo HTML devem continuar presentes."""
        campos = [
            "timestamp_legivel", "tendencia", "narrativa",
            "regime_macro", "ativos", "mt5", "meta",
        ]
        dados = self._executar_atualizar_dados()
        for campo in campos:
            assert campo in dados, f"Campo '{campo}' ausente — quebra o HTML"

    @pytest.mark.unit
    def test_campos_tendencia_para_html(self) -> None:
        campos = [
            "score", "tendencia", "cor_tendencia",
            "emoji", "mensagem", "confianca_pct", "fatores",
        ]
        dados = self._executar_atualizar_dados()
        for campo in campos:
            assert campo in dados["tendencia"]

    @pytest.mark.unit
    def test_ativos_criticos_ausentes_no_json(self) -> None:
        ativos = _ativos_completos()
        del ativos["sp500"]
        with (
            patch.object(
                mqt, "_buscar_dados_externos",
                return_value=(ativos, ["sp500"], []),
            ),
            patch.object(mqt, "_dados_mt5", return_value={}),
            patch.object(mqt, "_buscar_indicadores_tv", return_value=None),
        ):
            mqt._atualizar_dados()
        with mqt._lock_cache:
            dados = dict(mqt._cache_dados)
        assert "sp500" in dados["qualidade_dados"]["ativos_criticos_ausentes"]

    @pytest.mark.unit
    def test_confianca_100_quando_todos_ativos_presentes(self) -> None:
        dados = self._executar_atualizar_dados()
        assert dados["qualidade_dados"]["confianca_score"] == 100

    @pytest.mark.unit
    def test_scheduler_symbol_promotion_presente_no_json(self) -> None:
        dados = self._executar_atualizar_dados()
        assert "scheduler_symbol_promotion" in dados
        assert "status" in dados["scheduler_symbol_promotion"]


class TestSchedulerPromotionStatus:
    """Testa leitura do status de promocao do scheduler por simbolo."""

    @pytest.mark.unit
    def test_sem_artefato_retorna_sem_promocao(self, tmp_path: Path) -> None:
        outputs_dir = tmp_path / "outputs"
        outputs_dir.mkdir()
        runtime = tmp_path / "runtime.json"
        status = mqt._carregar_status_promocao_scheduler(
            outputs_dir=outputs_dir,
            runtime_config_path=runtime,
        )
        assert status["status"] == "sem_promocao"
        assert status["aprovado"] is False

    @pytest.mark.unit
    def test_arquivo_valido_retorna_aprovado(self, tmp_path: Path) -> None:
        outputs_dir = tmp_path / "outputs"
        outputs_dir.mkdir()
        promotion_file = outputs_dir / "scheduler_symbol_promotion_20260406_160217.json"
        promotion_file.write_text(
            json.dumps(
                {
                    "timestamp_promocao": "2026-04-06T16:02:17",
                    "aprovado": True,
                    "motivo": "gate manual aprovado",
                    "source_report": "outputs/scheduler_symbol_calibration_20260406_160217.json",
                }
            ),
            encoding="utf-8",
        )
        runtime = tmp_path / "symbol_calibration_runtime.json"
        runtime.write_text("{}", encoding="utf-8")
        status = mqt._carregar_status_promocao_scheduler(
            outputs_dir=outputs_dir,
            runtime_config_path=runtime,
        )
        assert status["status"] == "aprovado"
        assert status["aprovado"] is True
        assert status["runtime_config_presente"] is True

    @pytest.mark.unit
    def test_sem_promocao_no_pre_open_sinaliza_tolerancia_ativa(self, tmp_path: Path) -> None:
        outputs_dir = tmp_path / "outputs"
        outputs_dir.mkdir()
        status = mqt._carregar_status_promocao_scheduler(
            outputs_dir=outputs_dir,
            runtime_config_path=tmp_path / "runtime.json",
            allow_sem_promocao_until="09:05",
            now=datetime(2026, 4, 7, 8, 55),
        )
        assert status["status"] == "sem_promocao"
        assert status["janela_tolerancia_ativa"] is True
        assert status["bloqueio_efetivo"] is False

    @pytest.mark.unit
    def test_sem_promocao_apos_janela_ativa_bloqueio_efetivo(self, tmp_path: Path) -> None:
        outputs_dir = tmp_path / "outputs"
        outputs_dir.mkdir()
        status = mqt._carregar_status_promocao_scheduler(
            outputs_dir=outputs_dir,
            runtime_config_path=tmp_path / "runtime.json",
            allow_sem_promocao_until="09:05",
            now=datetime(2026, 4, 7, 9, 6),
        )
        assert status["status"] == "sem_promocao"
        assert status["janela_tolerancia_ativa"] is False
        assert status["bloqueio_efetivo"] is True


class TestStatusPayload:
    """Testa payload enxuto do endpoint /status."""

    @pytest.mark.unit
    def test_status_payload_inclui_resumo_promocao_quando_cache_preenchido(self) -> None:
        with mqt._lock_cache:
            mqt._cache_dados.clear()
            mqt._cache_dados.update(
                {
                    "timestamp_legivel": "06/04/2026 16:30:00",
                    "scheduler_symbol_promotion": {
                        "status": "aprovado",
                        "aprovado": True,
                        "runtime_config_presente": True,
                        "motivo": "gate manual aprovado",
                    },
                }
            )
        payload = mqt._build_status_payload()
        assert payload["ok"] is True
        assert payload["scheduler_symbol_promotion"]["status"] == "aprovado"
        assert payload["scheduler_symbol_promotion"]["runtime_config_presente"] is True

    @pytest.mark.unit
    def test_status_payload_fallback_para_leitor_quando_cache_sem_promocao(self) -> None:
        with mqt._lock_cache:
            mqt._cache_dados.clear()
            mqt._cache_dados.update({"timestamp_legivel": "06/04/2026 16:31:00"})
        with patch.object(
            mqt,
            "_carregar_status_promocao_scheduler",
            return_value={
                "status": "sem_promocao",
                "aprovado": False,
                "runtime_config_presente": False,
                "motivo": "artefato ausente",
                "janela_tolerancia_ativa": True,
                "bloqueio_efetivo": False,
                "allow_sem_promocao_until": "09:05",
            },
        ):
            payload = mqt._build_status_payload()
        assert payload["ok"] is True
        assert payload["scheduler_symbol_promotion"]["status"] == "sem_promocao"
        assert payload["scheduler_symbol_promotion"]["aprovado"] is False
        assert payload["scheduler_symbol_promotion"]["janela_tolerancia_ativa"] is True
        assert payload["scheduler_symbol_promotion"]["bloqueio_efetivo"] is False
