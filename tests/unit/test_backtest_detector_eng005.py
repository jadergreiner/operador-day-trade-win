"""
Testes unitários para BacktestValidator — TODO-7 (ENG-005)

Valida a chamada correta do detector_padroes no pipeline de backtest:
- AC-1: detector_padroes chamado corretamente (engulfing, break s/r)
- AC-2: reconhecimento de padrões habilitado
- AC-3: acurácia do backtest validada
- AC-4: testes unitários passando
- AC-5: resultados correspondem às métricas esperadas
"""

import asyncio
import sys
from datetime import datetime, timedelta
from pathlib import Path
from typing import List
from unittest.mock import MagicMock, patch
import pytest

# Adicionar src ao path para imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))
# Adicionar scripts ao path para importar BacktestValidator
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "scripts"))


def _construir_vela(
    ativo: str,
    open_: float,
    high: float,
    low: float,
    close: float,
    volume: int = 1000,
    timestamp: str = "2026-01-01T09:00:00",
) -> dict:
    """Constrói dicionário de vela para testes."""
    return {
        "ativo": ativo,
        "open": open_,
        "high": high,
        "low": low,
        "close": close,
        "volume": volume,
        "time": timestamp,
    }


@pytest.fixture
def mock_config():
    """Config mockada para evitar dependência de arquivo .env."""
    cfg = MagicMock()
    cfg.detection.volatilidade.window = 20
    cfg.detection.volatilidade.threshold_sigma = 2.0
    cfg.detection.padroes.engulfing_enabled = True
    cfg.detection.padroes.break_suporte_enabled = True
    cfg.detection.padroes.break_resistencia_enabled = True
    return cfg


@pytest.fixture
def validator(mock_config):
    """
    BacktestValidator com dependências mockadas.
    Evita necessidade de MT5 ou arquivo de configuração.
    """
    with patch(
        "backtest_detector.get_config", return_value=mock_config
    ), patch(
        "backtest_detector.DetectorVolatilidade"
    ) as MockVol:
        MockVol.return_value.analisar_vela.return_value = None
        import backtest_detector
        v = backtest_detector.BacktestValidator()
        return v


class TestBacktestValidatorInit:
    """Testes de inicialização do BacktestValidator."""

    def test_historico_velas_inicializado_vazio(self, validator):
        """AC-1: BacktestValidator deve inicializar historico_velas vazio."""
        assert isinstance(validator.historico_velas, dict)
        assert len(validator.historico_velas) == 0

    def test_detector_padroes_instanciado(self, validator):
        """AC-1: detector_padroes deve ser instância de DetectorPadroesTecnico."""
        assert type(validator.detector_padroes).__name__ == "DetectorPadroesTecnico"

    def test_metricas_inicializadas_zeradas(self, validator):
        """Métricas devem começar zeradas."""
        assert validator.velas_processadas == 0
        assert validator.matches == 0
        assert validator.false_positives == 0
        assert validator.false_negatives == 0
        assert validator.alertas_gerados == []
        assert validator.oportunidades_manuais == []


class TestProcessarVelaHistorico:
    """Testes para gerenciamento do histórico de velas em processar_vela."""

    def test_primeira_vela_adiciona_ao_historico(self, validator):
        """AC-1: Primeira vela deve ser adicionada ao histórico do símbolo."""
        vela = _construir_vela("WIN$N", 127500, 127700, 127300, 127600)
        asyncio.run(validator.processar_vela(vela))
        assert "WIN$N" in validator.historico_velas
        assert len(validator.historico_velas["WIN$N"]) == 1

    def test_velas_acumulam_no_historico(self, validator):
        """AC-1: Velas subsequentes devem acumular no histórico."""
        for i in range(5):
            ts = f"2026-01-01T09:0{i}:00"
            vela = _construir_vela(
                "WIN$N", 127500 + i * 10, 127700, 127300, 127600 + i * 5,
                timestamp=ts
            )
            asyncio.run(validator.processar_vela(vela))
        assert len(validator.historico_velas["WIN$N"]) == 5

    def test_historico_limitado_a_20_velas(self, validator):
        """AC-1: Histórico deve manter no máximo 20 velas por símbolo."""
        for i in range(25):
            ts = f"2026-01-01T{9 + i // 60:02d}:{i % 60:02d}:00"
            vela = _construir_vela(
                "WIN$N", 127500.0, 127700.0, 127300.0, 127600.0 + float(i),
                timestamp=ts
            )
            asyncio.run(validator.processar_vela(vela))
        assert len(validator.historico_velas["WIN$N"]) == 20

    def test_historicos_isolados_por_simbolo(self, validator):
        """AC-1: Históricos de símbolos diferentes devem ser independentes."""
        vela_win = _construir_vela("WIN$N", 127500, 127700, 127300, 127600)
        vela_wdo = _construir_vela("WDO$N", 5200, 5210, 5190, 5205)
        asyncio.run(validator.processar_vela(vela_win))
        asyncio.run(validator.processar_vela(vela_wdo))
        assert "WIN$N" in validator.historico_velas
        assert "WDO$N" in validator.historico_velas
        assert len(validator.historico_velas["WIN$N"]) == 1
        assert len(validator.historico_velas["WDO$N"]) == 1


class TestDetectorEngulfingIntegrado:
    """Testes de integração do detectar_engulfing no backtest."""

    def test_engulfing_nao_chamado_na_primeira_vela(self, validator):
        """AC-1: Engulfing não deve ser chamado sem vela anterior."""
        vela = _construir_vela("WIN$N", 127500, 127700, 127300, 127600)
        with patch.object(
            validator.detector_padroes, "detectar_engulfing"
        ) as mock_eng:
            asyncio.run(validator.processar_vela(vela))
            mock_eng.assert_not_called()

    def test_engulfing_chamado_a_partir_da_segunda_vela(self, validator):
        """AC-1: Engulfing deve ser chamado a partir da segunda vela."""
        vela1 = _construir_vela(
            "WIN$N", 127600, 127700, 127400, 127400,  # bearish
            timestamp="2026-01-01T09:00:00",
        )
        vela2 = _construir_vela(
            "WIN$N", 127350, 127900, 127300, 127800,  # bullish envolve
            timestamp="2026-01-01T09:05:00",
        )
        asyncio.run(validator.processar_vela(vela1))
        with patch.object(
            validator.detector_padroes, "detectar_engulfing", return_value=None
        ) as mock_eng:
            asyncio.run(validator.processar_vela(vela2))
            mock_eng.assert_called_once()
            call_kwargs = mock_eng.call_args.kwargs
            assert call_kwargs["symbol"] == "WIN$N"
            assert call_kwargs["vela_atual"] == vela2
            assert call_kwargs["vela_anterior"] == vela1

    def test_engulfing_bullish_detectado_e_adicionado_aos_alertas(self, validator):
        """AC-2: Alerta de engulfing bullish deve ser adicionado à lista."""
        # Vela anterior: bearish
        vela1 = _construir_vela(
            "WIN$N", 127600.0, 127700.0, 127400.0, 127400.0,
            timestamp="2026-01-01T09:00:00",
        )
        # Vela atual: bullish que envolve a anterior
        vela2 = _construir_vela(
            "WIN$N", 127350.0, 127900.0, 127300.0, 127800.0,
            timestamp="2026-01-01T09:05:00",
        )
        asyncio.run(validator.processar_vela(vela1))
        alertas = asyncio.run(validator.processar_vela(vela2))

        # Deve haver pelo menos um alerta de engulfing
        from src.domain.enums.alerta_enums import PatraoAlerta

        alertas_engulfing = [
            a for a in alertas
            if hasattr(a, "padrao")
            and a.padrao == PatraoAlerta.ENGULFING_BULLISH
        ]
        assert len(alertas_engulfing) == 1, (
            "Deve detectar Bullish Engulfing quando vela bullish envolve bearish anterior"
        )

    def test_engulfing_vela_anterior_correta_apos_multiplas(self, validator):
        """AC-1: Após múltiplas velas, vela_anterior deve ser a imediatamente anterior."""
        velas = [
            _construir_vela(
                "WIN$N", 127500.0 + float(i * 10), 127700.0, 127300.0,
                127600.0 + float(i * 5),
                timestamp=f"2026-01-01T09:0{i}:00",
            )
            for i in range(4)
        ]
        for v in velas[:-1]:
            asyncio.run(validator.processar_vela(v))

        with patch.object(
            validator.detector_padroes, "detectar_engulfing", return_value=None
        ) as mock_eng:
            asyncio.run(validator.processar_vela(velas[-1]))
            call_kwargs = mock_eng.call_args.kwargs
            assert call_kwargs["vela_anterior"] == velas[-2]


class TestDetectorBreakSRIntegrado:
    """Testes de integração do break suporte/resistência no backtest."""

    def test_break_suporte_nao_chamado_com_menos_de_6_velas(self, validator):
        """AC-1: detectar_break_suporte não deve ser chamado com < 6 candles."""
        with patch.object(
            validator.detector_padroes, "detectar_break_suporte"
        ) as mock_bs:
            for i in range(5):
                ts = f"2026-01-01T09:0{i}:00"
                vela = _construir_vela(
                    "WIN$N", 127500.0, 127700.0, 127300.0, 127600.0,
                    timestamp=ts,
                )
                asyncio.run(validator.processar_vela(vela))
            mock_bs.assert_not_called()

    def test_break_suporte_chamado_a_partir_da_sexta_vela(self, validator):
        """AC-1: detectar_break_suporte deve ser chamado quando histórico >= 6."""
        with patch.object(
            validator.detector_padroes, "detectar_break_suporte", return_value=None
        ) as mock_bs, patch.object(
            validator.detector_padroes, "detectar_break_resistencia", return_value=None
        ):
            for i in range(6):
                ts = f"2026-01-01T09:0{i}:00"
                vela = _construir_vela(
                    "WIN$N", 127500.0, 127700.0, 127300.0, 127600.0,
                    timestamp=ts,
                )
                asyncio.run(validator.processar_vela(vela))
            mock_bs.assert_called_once()
            call_kwargs = mock_bs.call_args.kwargs
            assert call_kwargs["symbol"] == "WIN$N"
            assert len(call_kwargs["precos"]) == 6

    def test_break_resistencia_chamado_junto_com_suporte(self, validator):
        """AC-1: detectar_break_resistencia deve ser chamado junto com break suporte."""
        with patch.object(
            validator.detector_padroes, "detectar_break_suporte", return_value=None
        ), patch.object(
            validator.detector_padroes,
            "detectar_break_resistencia",
            return_value=None,
        ) as mock_br:
            for i in range(6):
                ts = f"2026-01-01T09:0{i}:00"
                vela = _construir_vela(
                    "WIN$N", 127500.0, 127700.0, 127300.0, 127600.0,
                    timestamp=ts,
                )
                asyncio.run(validator.processar_vela(vela))
            mock_br.assert_called_once()

    def test_precos_hist_passados_corretamente(self, validator):
        """AC-1: precos passados ao detector devem corresponder ao histórico real."""
        closes_esperados = [127600.0, 127610.0, 127620.0, 127630.0, 127640.0, 127500.0]

        for idx, close in enumerate(closes_esperados):
            ts = f"2026-01-01T09:0{idx}:00"
            vela = _construir_vela(
                "WIN$N", close - 50.0, close + 100.0, close - 100.0, close,
                timestamp=ts,
            )
            if idx < len(closes_esperados) - 1:
                asyncio.run(validator.processar_vela(vela))
            else:
                with patch.object(
                    validator.detector_padroes,
                    "detectar_break_suporte",
                    return_value=None,
                ) as mock_bs, patch.object(
                    validator.detector_padroes,
                    "detectar_break_resistencia",
                    return_value=None,
                ):
                    asyncio.run(validator.processar_vela(vela))
                    call_kwargs = mock_bs.call_args.kwargs
                    assert call_kwargs["precos"] == closes_esperados


class TestContadorVelas:
    """Testes do contador de velas processadas."""

    def test_velas_processadas_incrementa(self, validator):
        """AC-5: velas_processadas deve incrementar a cada vela."""
        vela = _construir_vela("WIN$N", 127500, 127700, 127300, 127600)
        asyncio.run(validator.processar_vela(vela))
        asyncio.run(validator.processar_vela(
            _construir_vela("WIN$N", 127600, 127800, 127400, 127700,
                            timestamp="2026-01-01T09:05:00")
        ))
        assert validator.velas_processadas == 2

    def test_alertas_gerados_acumula(self, validator):
        """AC-5: alertas_gerados deve acumular alertas de todas as velas."""
        # Vela anterior bearish
        vela1 = _construir_vela(
            "WIN$N", 127600.0, 127700.0, 127400.0, 127400.0,
            timestamp="2026-01-01T09:00:00",
        )
        # Vela atual bullish envolve anterior → gera alerta engulfing
        vela2 = _construir_vela(
            "WIN$N", 127350.0, 127900.0, 127300.0, 127800.0,
            timestamp="2026-01-01T09:05:00",
        )
        asyncio.run(validator.processar_vela(vela1))
        asyncio.run(validator.processar_vela(vela2))

        assert len(validator.alertas_gerados) >= 1


class TestGeradorRelatorio:
    """Testes do gerador de relatório do backtest."""

    def test_relatorio_contem_chaves_obrigatorias(self, validator):
        """AC-5: Relatório deve conter todas as chaves obrigatórias."""
        relatorio = validator.gerar_relatorio()
        chaves_obrigatorias = [
            "periodo",
            "ativo",
            "timeframe",
            "metricas",
            "taxas",
            "gates_validacao",
            "status",
            "timestamp",
        ]
        for chave in chaves_obrigatorias:
            assert chave in relatorio, f"Chave '{chave}' ausente no relatório"

    def test_relatorio_metricas_refletem_estado(self, validator):
        """AC-5: Métricas do relatório devem refletir o estado atual."""
        vela = _construir_vela("WIN$N", 127500, 127700, 127300, 127600)
        asyncio.run(validator.processar_vela(vela))

        relatorio = validator.gerar_relatorio()
        assert relatorio["metricas"]["velas_processadas"] == 1

    def test_gates_de_validacao_presentes(self, validator):
        """AC-5: Gates de validação devem estar no relatório."""
        relatorio = validator.gerar_relatorio()
        gates = relatorio["gates_validacao"]
        assert "captura_minima_85pct" in gates
        assert "fp_maxima_10pct" in gates
        assert "win_rate_minimo_60pct" in gates


class TestRobustezProcessarVela:
    """Testes de robustez para processar_vela — cenários de erro."""

    def test_vela_sem_campo_ativo_retorna_lista_vazia(self, validator):
        """Vela sem campo 'ativo' deve retornar lista vazia sem KeyError."""
        vela_invalida = {
            "time": "2026-01-01T09:00:00",
            "open": 127500.0,
            "high": 127700.0,
            "low": 127300.0,
            "close": 127600.0,
        }
        alertas = asyncio.run(validator.processar_vela(vela_invalida))
        assert alertas == []
        assert validator.velas_processadas == 0

    def test_vela_sem_campo_close_retorna_lista_vazia(self, validator):
        """Vela sem campo 'close' deve retornar lista vazia sem KeyError."""
        vela_invalida = {
            "ativo": "WIN$N",
            "time": "2026-01-01T09:00:00",
            "open": 127500.0,
            "high": 127700.0,
            "low": 127300.0,
        }
        alertas = asyncio.run(validator.processar_vela(vela_invalida))
        assert alertas == []
        assert validator.velas_processadas == 0

    def test_timestamp_invalido_retorna_lista_vazia(self, validator):
        """Timestamp malformado deve retornar lista vazia sem exceção."""
        vela_ts_invalido = _construir_vela(
            "WIN$N", 127500.0, 127700.0, 127300.0, 127600.0,
            timestamp="timestamp-invalido-xyz",
        )
        alertas = asyncio.run(validator.processar_vela(vela_ts_invalido))
        assert alertas == []
        assert validator.velas_processadas == 0

    def test_vela_valida_apos_vela_invalida_processa_normalmente(self, validator):
        """Após vela inválida ignorada, vela válida deve ser processada."""
        vela_invalida = {"ativo": "WIN$N", "time": "bad-ts"}
        vela_valida = _construir_vela("WIN$N", 127500.0, 127700.0, 127300.0, 127600.0)
        asyncio.run(validator.processar_vela(vela_invalida))
        asyncio.run(validator.processar_vela(vela_valida))
        assert validator.velas_processadas == 1
