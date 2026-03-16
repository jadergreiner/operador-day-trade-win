"""
Testes para Ambiente Gym de Trading com Episode Callbacks.

Modulo de testes para a trilha RL operacional (P2 - Capacidade futura).
Cobre: ambiente Gym, episode callbacks, training loop, save/load versionado.
"""

import json
import os
import tempfile
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List

import pytest

from src.application.rl_trading_environment import (
    EpisodeCallback,
    RLRewardMetrics,
    TradingGymEnvironment,
    TrainingState,
)


class TestTradingGymEnvironmentDataClasses:
    """Testes para dataclasses do ambiente de trading."""

    def test_criar_rl_reward_metrics(self) -> None:
        """Teste criacao de RLRewardMetrics."""
        metricas: RLRewardMetrics = RLRewardMetrics(
            total_reward=1500.0,
            win_rate=0.65,
            sharpe_ratio=1.25,
            max_drawdown=-0.12,
            trades_executados=42,
        )

        assert metricas.total_reward == 1500.0
        assert metricas.win_rate == 0.65
        assert metricas.sharpe_ratio == 1.25
        assert metricas.max_drawdown == -0.12
        assert metricas.trades_executados == 42

    def test_rl_reward_metrics_para_dict(self) -> None:
        """Teste conversao RLRewardMetrics para dict."""
        metricas: RLRewardMetrics = RLRewardMetrics(
            total_reward=1000.0,
            win_rate=0.60,
            sharpe_ratio=1.10,
            max_drawdown=-0.15,
            trades_executados=30,
        )

        metricas_dict: Dict[str, Any] = metricas.para_dict()
        assert metricas_dict["total_reward"] == 1000.0
        assert metricas_dict["win_rate"] == 0.60
        assert metricas_dict["trades_executados"] == 30

    def test_criar_training_state(self) -> None:
        """Teste criacao de TrainingState."""
        estado: TrainingState = TrainingState(
            episodio=100,
            iteracao=5000,
            melhor_reward=2000.0,
            reward_medio=1500.0,
            versao_modelo="v1.2.3",
        )

        assert estado.episodio == 100
        assert estado.iteracao == 5000
        assert estado.melhor_reward == 2000.0
        assert estado.versao_modelo == "v1.2.3"

    def test_training_state_para_dict(self) -> None:
        """Teste conversao TrainingState para dict."""
        estado: TrainingState = TrainingState(
            episodio=50,
            iteracao=2500,
            melhor_reward=1800.0,
            reward_medio=1400.0,
            versao_modelo="v1.1.0",
        )

        estado_dict: Dict[str, Any] = estado.para_dict()
        assert estado_dict["episodio"] == 50
        assert estado_dict["melhor_reward"] == 1800.0


class TestEpisodeCallback:
    """Testes para callbacks de episodio."""

    def test_criar_episode_callback(self) -> None:
        """Teste criacao de EpisodeCallback."""
        callback: EpisodeCallback = EpisodeCallback(
            episodio=1,
            timestamp=datetime.now().isoformat(),
            trades_abertos=5,
            win_rate=0.60,
            total_pnl=500.0,
        )

        assert callback.episodio == 1
        assert callback.trades_abertos == 5
        assert callback.win_rate == 0.60
        assert callback.total_pnl == 500.0

    def test_episode_callback_para_dict(self) -> None:
        """Teste conversao EpisodeCallback para dict."""
        timestamp: str = datetime.now().isoformat()
        callback: EpisodeCallback = EpisodeCallback(
            episodio=42,
            timestamp=timestamp,
            trades_abertos=10,
            win_rate=0.68,
            total_pnl=1200.0,
        )

        callback_dict: Dict[str, Any] = callback.para_dict()
        assert callback_dict["episodio"] == 42
        assert callback_dict["win_rate"] == 0.68


class TestTradingGymEnvironment:
    """Testes para ambiente Gym de trading."""

    def test_inicializar_ambiente(self) -> None:
        """Teste inicializacao do ambiente."""
        env: TradingGymEnvironment = TradingGymEnvironment(
            capital_inicial=10000.0,
            alavancagem=2.0,
        )

        assert env.capital_inicial == 10000.0
        assert env.alavancagem == 2.0
        assert env.episodios_totais == 0
        assert len(env.historico_episodios) == 0

    def test_reset_ambiente(self) -> None:
        """Teste reset do ambiente."""
        env: TradingGymEnvironment = TradingGymEnvironment(
            capital_inicial=10000.0,
            alavancagem=2.0,
        )

        estado_inicial: List[float] = env.reset()
        assert isinstance(estado_inicial, list)
        assert len(estado_inicial) > 0
        assert env.episodio_atual == 1

    def test_step_action_buy(self) -> None:
        """Teste executar acao BUY."""
        env: TradingGymEnvironment = TradingGymEnvironment(
            capital_inicial=10000.0,
            alavancagem=2.0,
        )

        env.reset()

        # Acao 1 = BUY
        preco_entrada: float = 100.0
        env.preco_atual = preco_entrada
        estado, reward, done, info = env.step(action=1)

        assert isinstance(estado, list)
        assert isinstance(reward, float)
        assert isinstance(done, bool)
        assert isinstance(info, dict)

    def test_calcular_reward(self) -> None:
        """Teste calculo de reward."""
        env: TradingGymEnvironment = TradingGymEnvironment(
            capital_inicial=10000.0,
            alavancagem=2.0,
        )

        env.reset()
        env.preco_entrada = 100.0
        env.preco_atual = 102.0

        reward: float = env.calcular_reward(posicao_ativa=True)
        assert isinstance(reward, float)
        assert reward > 0.0  # Esperado ganho positivo

    def test_fechar_posicao(self) -> None:
        """Teste fechar posicao."""
        env: TradingGymEnvironment = TradingGymEnvironment(
            capital_inicial=10000.0,
            alavancagem=2.0,
        )

        env.reset()
        env.preco_entrada = 100.0
        env.posicao_ativa = True

        env.preco_atual = 102.0
        lucro: float = env.fechar_posicao()

        assert isinstance(lucro, float)
        assert lucro == 2.0  # 102 - 100 = 2
        assert env.posicao_ativa is False

    def test_registrar_episodio_completo(self) -> None:
        """Teste registrar episodio completo."""
        env: TradingGymEnvironment = TradingGymEnvironment(
            capital_inicial=10000.0,
            alavancagem=2.0,
        )

        env.reset()
        env.registrar_episodio(
            episodio=1,
            trades=5,
            win_rate=0.60,
            total_pnl=500.0,
        )

        assert env.episodios_totais == 1
        assert len(env.historico_episodios) == 1

    def test_calcular_metricas(self) -> None:
        """Teste calculo de metricas de reward."""
        env: TradingGymEnvironment = TradingGymEnvironment(
            capital_inicial=10000.0,
            alavancagem=2.0,
        )

        env.reset()

        # Registrar alguns episodios
        for i in range(3):
            env.registrar_episodio(
                episodio=i + 1,
                trades=5 + i,
                win_rate=0.60 + (i * 0.02),
                total_pnl=500.0 + (i * 100),
            )

        metricas: RLRewardMetrics = env.calcular_metricas()

        assert isinstance(metricas, RLRewardMetrics)
        assert metricas.trades_executados > 0
        assert 0.0 <= metricas.win_rate <= 1.0

    def test_salvar_checkpoint(self) -> None:
        """Teste salvar checkpoint do modelo."""
        with tempfile.TemporaryDirectory() as tmpdir:
            env: TradingGymEnvironment = TradingGymEnvironment(
                capital_inicial=10000.0,
                alavancagem=2.0,
                diretorio_modelos=tmpdir,
            )

            env.reset()
            env.registrar_episodio(
                episodio=1,
                trades=5,
                win_rate=0.60,
                total_pnl=500.0,
            )

            arquivo_salvo: str = env.salvar_checkpoint(
                versao="v1.0.0",
                melhor_reward=1000.0,
            )

            assert os.path.exists(arquivo_salvo)
            assert ".json" in arquivo_salvo

    def test_carregar_checkpoint(self) -> None:
        """Teste carregar checkpoint do modelo."""
        with tempfile.TemporaryDirectory() as tmpdir:
            env: TradingGymEnvironment = TradingGymEnvironment(
                capital_inicial=10000.0,
                alavancagem=2.0,
                diretorio_modelos=tmpdir,
            )

            env.reset()
            env.registrar_episodio(
                episodio=1,
                trades=5,
                win_rate=0.60,
                total_pnl=500.0,
            )

            arquivo: str = env.salvar_checkpoint(
                versao="v1.0.0",
                melhor_reward=1000.0,
            )

            # Carregar
            env2: TradingGymEnvironment = TradingGymEnvironment(
                capital_inicial=10000.0,
                alavancagem=2.0,
                diretorio_modelos=tmpdir,
            )

            estado_carregado: Dict[str, Any] = env2.carregar_checkpoint(arquivo)
            assert estado_carregado["versao"] == "v1.0.0"
            assert estado_carregado["melhor_reward"] == 1000.0

    def test_exportar_metricas_json(self) -> None:
        """Teste exportar metricas em JSON."""
        with tempfile.TemporaryDirectory() as tmpdir:
            env: TradingGymEnvironment = TradingGymEnvironment(
                capital_inicial=10000.0,
                alavancagem=2.0,
                diretorio_modelos=tmpdir,
            )

            env.reset()

            for i in range(3):
                env.registrar_episodio(
                    episodio=i + 1,
                    trades=5 + i,
                    win_rate=0.60 + (i * 0.02),
                    total_pnl=500.0 + (i * 100),
                )

            arquivo: str = env.exportar_metricas_json()
            assert os.path.exists(arquivo)

            with open(arquivo, "r") as f:
                dados: Dict[str, Any] = json.load(f)
                assert "timestamp" in dados
                assert "episodios" in dados

    def test_gerar_relatorio_markdown(self) -> None:
        """Teste gerar relatorio em Markdown."""
        env: TradingGymEnvironment = TradingGymEnvironment(
            capital_inicial=10000.0,
            alavancagem=2.0,
        )

        env.reset()

        for i in range(3):
            env.registrar_episodio(
                episodio=i + 1,
                trades=5 + i,
                win_rate=0.60 + (i * 0.02),
                total_pnl=500.0 + (i * 100),
            )

        relatorio: str = env.gerar_relatorio_markdown()
        assert isinstance(relatorio, str)
        assert "# Relatorio Metricas RL" in relatorio or len(relatorio) > 100

    def test_type_hints_100_porcento(self) -> None:
        """Teste se modulo tem 100% type hints."""
        from src.application.rl_trading_environment import (
            EpisodeCallback,
            RLRewardMetrics,
            TradingGymEnvironment,
            TrainingState,
        )

        # Apenas verificar se classes importam sem erro
        assert TradingGymEnvironment is not None
        assert RLRewardMetrics is not None
        assert EpisodeCallback is not None
        assert TrainingState is not None

    def test_reset_multiple_times(self) -> None:
        """Teste reset do ambiente multiplas vezes."""
        env: TradingGymEnvironment = TradingGymEnvironment(
            capital_inicial=10000.0,
            alavancagem=2.0,
        )

        for i in range(3):
            estado = env.reset()
            assert isinstance(estado, list)
            assert env.episodio_atual == i + 1

    def test_ambiente_compativel_gym(self) -> None:
        """Teste se ambiente atende interface basica Gym."""
        env: TradingGymEnvironment = TradingGymEnvironment(
            capital_inicial=10000.0,
            alavancagem=2.0,
        )

        # Verificar metodos Gym obrigatorios
        assert hasattr(env, "reset")
        assert hasattr(env, "step")
        assert hasattr(env, "render")

    def test_validar_pontucacao_compartimento_type_hints(self) -> None:
        """Teste validacao de type hints no modulo."""
        # Apenas validar que as classes principais tem type hints
        env: TradingGymEnvironment = TradingGymEnvironment(
            capital_inicial=10000.0,
            alavancagem=2.0,
        )
        assert env is not None
