"""
ML-1: Testes para o gate de tendencia intraday (EMA9/EMA21).

Problema original: SELL @ 182590 em mercado bullish em 17/03/2026
gerou LOSS -R$61 porque o modelo RL aceitou acao=2 (SELL) com
confianca 70% sem verificar alinhamento com tendencia intraday.

Fix: Gate simetrico — bloqueia SELL quando EMA9 > EMA21
e BUY quando EMA9 < EMA21.

Referencia: docs/BACKLOG.md (ML-1 / SAR Board 17/03/2026)
"""

import unittest
import pandas as pd
import numpy as np
from unittest.mock import patch


def _criar_dados_tendencia_alta(n: int = 30) -> pd.DataFrame:
    """DataFrame com closes crescentes (tendencia de alta).
    EMA9 ficara acima de EMA21 ao final da serie.
    """
    closes = [100.0 + i * 2.0 for i in range(n)]
    return pd.DataFrame({'close': closes, 'high': closes, 'low': closes, 'open': closes})


def _criar_dados_tendencia_baixa(n: int = 30) -> pd.DataFrame:
    """DataFrame com closes decrescentes (tendencia de baixa).
    EMA9 ficara abaixo de EMA21 ao final da serie.
    """
    closes = [200.0 - i * 2.0 for i in range(n)]
    return pd.DataFrame({'close': closes, 'high': closes, 'low': closes, 'open': closes})


def _criar_dados_laterais(n: int = 30) -> pd.DataFrame:
    """DataFrame com closes oscilando (sem tendencia definida)."""
    np.random.seed(42)
    closes = [150.0 + np.random.uniform(-1, 1) for _ in range(n)]
    return pd.DataFrame({'close': closes, 'high': closes, 'low': closes, 'open': closes})


class TestCalcularEma(unittest.TestCase):
    """Testa o calculo da EMA."""

    def test_ema_retorna_zero_dados_insuficientes(self) -> None:
        """calcular_ema() retorna 0.0 quando dados < periodo."""
        from scripts.agente_rl_direto_independente import calcular_ema
        dados = pd.DataFrame({'close': [100.0, 101.0]})
        resultado = calcular_ema(dados, periodo=9)
        self.assertEqual(resultado, 0.0)

    def test_ema_retorna_float_dados_suficientes(self) -> None:
        """calcular_ema() retorna float valido com dados suficientes."""
        from scripts.agente_rl_direto_independente import calcular_ema
        dados = _criar_dados_tendencia_alta(n=30)
        resultado = calcular_ema(dados, periodo=9)
        self.assertIsInstance(resultado, float)
        self.assertGreater(resultado, 0.0)

    def test_ema_rapida_maior_que_lenta_em_alta(self) -> None:
        """EMA9 > EMA21 em tendencia de alta."""
        from scripts.agente_rl_direto_independente import calcular_ema
        dados = _criar_dados_tendencia_alta(n=40)
        ema9 = calcular_ema(dados, periodo=9)
        ema21 = calcular_ema(dados, periodo=21)
        self.assertGreater(ema9, ema21,
                           "EMA9 deve ser maior que EMA21 em tendencia de alta")

    def test_ema_rapida_menor_que_lenta_em_baixa(self) -> None:
        """EMA9 < EMA21 em tendencia de baixa."""
        from scripts.agente_rl_direto_independente import calcular_ema
        dados = _criar_dados_tendencia_baixa(n=40)
        ema9 = calcular_ema(dados, periodo=9)
        ema21 = calcular_ema(dados, periodo=21)
        self.assertLess(ema9, ema21,
                        "EMA9 deve ser menor que EMA21 em tendencia de baixa")


class TestAplicarGateTendencia(unittest.TestCase):
    """Testa o gate de tendencia intraday (ML-1)."""

    def test_sell_bloqueado_em_tendencia_alta(self) -> None:
        """SELL deve ser bloqueado quando EMA9 > EMA21 (tendencia de alta)."""
        from scripts.agente_rl_direto_independente import aplicar_gate_tendencia
        dados = _criar_dados_tendencia_alta(n=40)
        resultado = aplicar_gate_tendencia("Vender", dados, gate_ativo=True)
        self.assertEqual(resultado, "Aguardar",
                         "SELL deve ser bloqueado em tendencia de alta")

    def test_buy_bloqueado_em_tendencia_baixa(self) -> None:
        """BUY deve ser bloqueado quando EMA9 < EMA21 (tendencia de baixa)."""
        from scripts.agente_rl_direto_independente import aplicar_gate_tendencia
        dados = _criar_dados_tendencia_baixa(n=40)
        resultado = aplicar_gate_tendencia("Comprar", dados, gate_ativo=True)
        self.assertEqual(resultado, "Aguardar",
                         "BUY deve ser bloqueado em tendencia de baixa")

    def test_buy_permitido_em_tendencia_alta(self) -> None:
        """BUY deve ser PERMITIDO quando EMA9 > EMA21 (tendencia de alta)."""
        from scripts.agente_rl_direto_independente import aplicar_gate_tendencia
        dados = _criar_dados_tendencia_alta(n=40)
        resultado = aplicar_gate_tendencia("Comprar", dados, gate_ativo=True)
        self.assertEqual(resultado, "Comprar",
                         "BUY deve ser permitido em tendencia de alta")

    def test_sell_permitido_em_tendencia_baixa(self) -> None:
        """SELL deve ser PERMITIDO quando EMA9 < EMA21 (tendencia de baixa)."""
        from scripts.agente_rl_direto_independente import aplicar_gate_tendencia
        dados = _criar_dados_tendencia_baixa(n=40)
        resultado = aplicar_gate_tendencia("Vender", dados, gate_ativo=True)
        self.assertEqual(resultado, "Vender",
                         "SELL deve ser permitido em tendencia de baixa")

    def test_aguardar_passado_sem_alteracao(self) -> None:
        """Acao Aguardar nao deve ser modificada pelo gate."""
        from scripts.agente_rl_direto_independente import aplicar_gate_tendencia
        dados = _criar_dados_tendencia_alta(n=40)
        resultado = aplicar_gate_tendencia("Aguardar", dados, gate_ativo=True)
        self.assertEqual(resultado, "Aguardar")

    def test_gate_inativo_nao_bloqueia(self) -> None:
        """Gate desativado (gate_ativo=False) nao deve bloquear nenhuma acao."""
        from scripts.agente_rl_direto_independente import aplicar_gate_tendencia
        dados = _criar_dados_tendencia_alta(n=40)
        # SELL em tendencia de alta — normalmente bloqueado
        resultado_sell = aplicar_gate_tendencia("Vender", dados, gate_ativo=False)
        self.assertEqual(resultado_sell, "Vender",
                         "Gate inativo nao deve bloquear SELL")
        # BUY em tendencia de baixa — normalmente bloqueado
        dados_baixa = _criar_dados_tendencia_baixa(n=40)
        resultado_buy = aplicar_gate_tendencia("Comprar", dados_baixa, gate_ativo=False)
        self.assertEqual(resultado_buy, "Comprar",
                         "Gate inativo nao deve bloquear BUY")

    def test_gate_dados_none_nao_bloqueia(self) -> None:
        """Gate com dados=None nao deve bloquear (nao ha informacao de tendencia)."""
        from scripts.agente_rl_direto_independente import aplicar_gate_tendencia
        resultado = aplicar_gate_tendencia("Vender", None, gate_ativo=True)
        self.assertEqual(resultado, "Vender",
                         "Gate sem dados nao deve bloquear acao")

    def test_gate_dados_insuficientes_nao_bloqueia(self) -> None:
        """Gate com dados insuficientes para EMA retorna acao original."""
        from scripts.agente_rl_direto_independente import aplicar_gate_tendencia
        dados = pd.DataFrame({'close': [100.0, 101.0]})  # apenas 2 velas
        resultado = aplicar_gate_tendencia("Vender", dados, gate_ativo=True)
        # Com EMA indisponivel, gate e ignorado
        self.assertEqual(resultado, "Vender",
                         "Gate com EMAs indisponiveis nao deve bloquear")

    def test_cenario_real_17_03_2026(self) -> None:
        """
        Cenario real do bug: SELL @ 182590 em mercado bullish.
        EMA9 > EMA21 — gate deve bloquear SELL e retornar Aguardar.
        """
        from scripts.agente_rl_direto_independente import aplicar_gate_tendencia
        # Simula serie de precos crescente como observado em 17/03/2026
        closes_bullish = [182000.0 + i * 100.0 for i in range(40)]
        dados = pd.DataFrame({
            'close': closes_bullish,
            'high': closes_bullish,
            'low': closes_bullish,
            'open': closes_bullish,
        })
        resultado = aplicar_gate_tendencia("Vender", dados, gate_ativo=True)
        self.assertEqual(resultado, "Aguardar",
                         "SELL deve ser bloqueado em mercado bullish (cenario 17/03/2026)")


class TestGateTendenciaIntegracaoComMapearAcao(unittest.TestCase):
    """Testa integracao entre mapear_acao e aplicar_gate_tendencia."""

    def test_acao_1_comprar_bloqueada_em_baixa(self) -> None:
        """acao_id=1 (BUY) bloqueado em tendencia de baixa."""
        from scripts.agente_rl_direto_independente import mapear_acao, aplicar_gate_tendencia
        dados = _criar_dados_tendencia_baixa(n=40)
        acao_str = mapear_acao(1)  # "Comprar"
        resultado = aplicar_gate_tendencia(acao_str, dados, gate_ativo=True)
        self.assertEqual(resultado, "Aguardar")

    def test_acao_2_vender_bloqueada_em_alta(self) -> None:
        """acao_id=2 (SELL) bloqueado em tendencia de alta."""
        from scripts.agente_rl_direto_independente import mapear_acao, aplicar_gate_tendencia
        dados = _criar_dados_tendencia_alta(n=40)
        acao_str = mapear_acao(2)  # "Vender"
        resultado = aplicar_gate_tendencia(acao_str, dados, gate_ativo=True)
        self.assertEqual(resultado, "Aguardar")

    def test_acao_0_aguardar_nao_alterada(self) -> None:
        """acao_id=0 (HOLD) nao alterada pelo gate."""
        from scripts.agente_rl_direto_independente import mapear_acao, aplicar_gate_tendencia
        dados = _criar_dados_tendencia_alta(n=40)
        acao_str = mapear_acao(0)  # "Aguardar"
        resultado = aplicar_gate_tendencia(acao_str, dados, gate_ativo=True)
        self.assertEqual(resultado, "Aguardar")


if __name__ == "__main__":
    unittest.main()
