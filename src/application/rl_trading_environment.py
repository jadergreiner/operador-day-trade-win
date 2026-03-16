"""
Ambiente Gym de Trading com Episode Callbacks e Training Loop.

Modulo para Trilha RL Operacional (P2 - Capacidade Futura).
Fornece ambiente compativel com OpenAI Gym para treinar agentes RL.

Features:
- Ambiente com reset/step compativel Gym
- Episode callbacks para rastreamento
- Save/load versionado para checkpoint
- Metricas de reward e performance
- Training state para resumir progressao
"""

import json
import os
from dataclasses import asdict, dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple


@dataclass
class RLRewardMetrics:
    """Metricas de reward e performance do RL."""

    total_reward: float
    """Reward total acumulado no episodio."""

    win_rate: float
    """Taxa de vitoria (0.0 a 1.0)."""

    sharpe_ratio: float
    """Sharpe ratio da estrategia."""

    max_drawdown: float
    """Drawdown maximo da curva equity."""

    trades_executados: int
    """Numero de trades executados."""

    def para_dict(self) -> Dict[str, Any]:
        """Converte metricas para dict."""
        return asdict(self)


@dataclass
class TrainingState:
    """Estado do treino do modelo RL."""

    episodio: int
    """Numero do episodio atual."""

    iteracao: int
    """Numero de iteracao (acao) dentro da sessao."""

    melhor_reward: float
    """Melhor reward obtido ate agora."""

    reward_medio: float
    """Reward medio dos ultimos episodios."""

    versao_modelo: str
    """Versao semantica do modelo (ex: v1.2.3)."""

    def para_dict(self) -> Dict[str, Any]:
        """Converte estado para dict."""
        return asdict(self)


@dataclass
class EpisodeCallback:
    """Callback de episodio para rastreamento."""

    episodio: int
    """Numero do episodio."""

    timestamp: str
    """Timestamp em ISO 8601."""

    trades_abertos: int
    """Numero de trades abertos neste episodio."""

    win_rate: float
    """Taxa de vitoria neste episodio."""

    total_pnl: float
    """P&L total do episodio."""

    def para_dict(self) -> Dict[str, Any]:
        """Converte callback para dict."""
        return asdict(self)


class TradingGymEnvironment:
    """Ambiente Gym compativel para trading com RL."""

    def __init__(
        self,
        capital_inicial: float = 10000.0,
        alavancagem: float = 2.0,
        diretorio_modelos: Optional[str] = None,
    ) -> None:
        """
        Inicializa ambiente de trading Gym.

        Args:
            capital_inicial: Capital inicial em reais.
            alavancagem: Alavancagem maxima.
            diretorio_modelos: Diretorio para salvar checkpoints.
        """
        self.capital_inicial: float = capital_inicial
        self.alavancagem: float = alavancagem
        self.diretorio_modelos: str = (
            diretorio_modelos or "data/models/rl_environment"
        )

        # Estado do ambiente
        self.episodio_atual: int = 0
        self.capital_atual: float = capital_inicial
        self.preco_atual: float = 100.0
        self.preco_entrada: float = 0.0
        self.posicao_ativa: bool = False
        self.historico_episodios: List[EpisodeCallback] = []
        self.episodios_totais: int = 0

        # Criar diretorio se nao existir
        Path(self.diretorio_modelos).mkdir(parents=True, exist_ok=True)

    def reset(self) -> List[float]:
        """
        Reset do ambiente (compativel Gym).

        Returns:
            Estado inicial como lista de floats.
        """
        self.episodio_atual += 1
        self.capital_atual = self.capital_inicial
        self.preco_atual = 100.0
        self.preco_entrada = 0.0
        self.posicao_ativa = False

        # Estado inicial: [capital_disponivel, preco_atual, posicao_ativa]
        estado: List[float] = [
            self.capital_atual,
            self.preco_atual,
            1.0 if self.posicao_ativa else 0.0,
        ]
        return estado

    def step(
        self,
        action: int,
    ) -> Tuple[List[float], float, bool, Dict[str, Any]]:
        """
        Executar acao no ambiente (compativel Gym).

        Args:
            action: 0=HOLD, 1=BUY, 2=SELL, 3=FECHAR

        Returns:
            Tupla (estado, reward, done, info)
        """
        reward: float = 0.0
        done: bool = False

        if action == 1 and not self.posicao_ativa:
            # BUY
            self.preco_entrada = self.preco_atual
            self.posicao_ativa = True
            reward = -10.0  # Penalidade por iniciar posicao

        elif action == 2 and self.posicao_ativa:
            # SELL (fechar)
            lucro = self.fechar_posicao()
            reward = lucro * 10  # Reward proporcional ao ganho

        elif action == 3 and self.posicao_ativa:
            # FECHAR FORCA
            lucro = self.fechar_posicao()
            reward = lucro * 5  # Menos reward que SELL normal

        elif action == 0:
            # HOLD
            if self.posicao_ativa:
                reward = self.calcular_reward(posicao_ativa=True)

        # Simular movimento de preco
        self.preco_atual += (self.preco_atual * 0.001)

        # Estado: [capital, preco_atual, posicao_ativa]
        estado: List[float] = [
            self.capital_atual,
            self.preco_atual,
            1.0 if self.posicao_ativa else 0.0,
        ]

        info: Dict[str, Any] = {
            "capital": self.capital_atual,
            "preco": self.preco_atual,
            "posicao_ativa": self.posicao_ativa,
        }

        return estado, reward, done, info

    def calcular_reward(self, posicao_ativa: bool) -> float:
        """
        Calcula reward baseado em ganho/perda atual.

        Args:
            posicao_ativa: Se posicao esta aberta.

        Returns:
            Valor do reward.
        """
        if not posicao_ativa or not self.preco_entrada:
            return 0.0

        ganho_percentual = (self.preco_atual - self.preco_entrada) / self.preco_entrada
        return ganho_percentual * 100  # Escalado para -100 a +100

    def fechar_posicao(self) -> float:
        """
        Fecha posicao e retorna lucro/prejuizo.

        Returns:
            Diferenca de preco (lucro ou prejuizo).
        """
        if not self.preco_entrada:
            return 0.0

        lucro = self.preco_atual - self.preco_entrada
        self.posicao_ativa = False
        self.capital_atual += lucro
        return lucro

    def registrar_episodio(
        self,
        episodio: int,
        trades: int,
        win_rate: float,
        total_pnl: float,
    ) -> None:
        """
        Registra episodio completado com metricas.

        Args:
            episodio: Numero do episodio.
            trades: Numero de trades.
            win_rate: Taxa de vitoria.
            total_pnl: P&L total.
        """
        callback = EpisodeCallback(
            episodio=episodio,
            timestamp=datetime.now().isoformat(),
            trades_abertos=trades,
            win_rate=win_rate,
            total_pnl=total_pnl,
        )
        self.historico_episodios.append(callback)
        self.episodios_totais += 1

    def calcular_metricas(self) -> RLRewardMetrics:
        """
        Calcula metricas agregadas dos episodios.

        Returns:
            Objeto RLRewardMetrics com metricas consolidadas.
        """
        if not self.historico_episodios:
            return RLRewardMetrics(
                total_reward=0.0,
                win_rate=0.0,
                sharpe_ratio=0.0,
                max_drawdown=0.0,
                trades_executados=0,
            )

        total_reward = sum(cb.total_pnl for cb in self.historico_episodios)
        total_trades = sum(cb.trades_abertos for cb in self.historico_episodios)
        win_rate_media = (
            sum(cb.win_rate for cb in self.historico_episodios)
            / len(self.historico_episodios)
        )

        # Calcular Sharpe ratio simplificado
        pnls = [cb.total_pnl for cb in self.historico_episodios]
        media = sum(pnls) / len(pnls) if pnls else 0.0
        variancia = (
            sum((x - media) ** 2 for x in pnls) / len(pnls) if pnls else 0.0
        )
        desvio_padrao = variancia**0.5
        sharpe = media / desvio_padrao if desvio_padrao > 0 else 0.0

        # Drawdown maximo
        max_drawdown = min(pnls) if pnls else 0.0

        return RLRewardMetrics(
            total_reward=total_reward,
            win_rate=win_rate_media,
            sharpe_ratio=sharpe,
            max_drawdown=max_drawdown / self.capital_inicial
            if self.capital_inicial > 0
            else 0.0,
            trades_executados=total_trades,
        )

    def salvar_checkpoint(
        self,
        versao: str,
        melhor_reward: float,
    ) -> str:
        """
        Salva checkpoint versionado do modelo.

        Args:
            versao: Versao semantica (ex: v1.2.3).
            melhor_reward: Melhor reward obtido.

        Returns:
            Caminho do arquivo salvo.
        """
        checkpoint_data: Dict[str, Any] = {
            "timestamp": datetime.now().isoformat(),
            "versao": versao,
            "melhor_reward": melhor_reward,
            "episodios_totais": self.episodios_totais,
            "metricas": self.calcular_metricas().para_dict(),
            "historico_resumido": [
                cb.para_dict() for cb in self.historico_episodios[-10:]
            ],
        }

        arquivo = os.path.join(
            self.diretorio_modelos,
            f"checkpoint_{versao}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json",
        )

        Path(self.diretorio_modelos).mkdir(parents=True, exist_ok=True)
        with open(arquivo, "w") as f:
            json.dump(checkpoint_data, f, indent=2)

        return arquivo

    def carregar_checkpoint(
        self,
        arquivo: str,
    ) -> Dict[str, Any]:
        """
        Carrega checkpoint salvo.

        Args:
            arquivo: Caminho do arquivo de checkpoint.

        Returns:
            Dados do checkpoint.
        """
        with open(arquivo, "r") as f:
            dados: Dict[str, Any] = json.load(f)
        return dados

    def exportar_metricas_json(self) -> str:
        """
        Exporta metricas em JSON.

        Returns:
            Caminho do arquivo JSON exportado.
        """
        metricas_data: Dict[str, Any] = {
            "timestamp": datetime.now().isoformat(),
            "episodios_totais": self.episodios_totais,
            "metricas": self.calcular_metricas().para_dict(),
            "episodios": [cb.para_dict() for cb in self.historico_episodios],
        }

        arquivo = os.path.join(
            self.diretorio_modelos,
            f"metricas_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json",
        )

        Path(self.diretorio_modelos).mkdir(parents=True, exist_ok=True)
        with open(arquivo, "w") as f:
            json.dump(metricas_data, f, indent=2)

        return arquivo

    def gerar_relatorio_markdown(self) -> str:
        """
        Gera relatorio em Markdown das metricas.

        Returns:
            String com relatorio formatado.
        """
        metricas = self.calcular_metricas()

        relatorio = f"""# Relatorio Metricas RL

## Resumo Geral

- **Episodios Totais:** {self.episodios_totais}
- **Reward Total:** R$ {metricas.total_reward:.2f}
- **Win Rate Medio:** {metricas.win_rate * 100:.2f}%
- **Sharpe Ratio:** {metricas.sharpe_ratio:.2f}
- **Drawdown Maximo:** {metricas.max_drawdown * 100:.2f}%
- **Total de Trades:** {metricas.trades_executados}

## Ultimos Episodios

| Episodio | Win Rate | P&L | Trades |
|----------|----------|-----|--------|
"""

        for cb in self.historico_episodios[-5:]:
            relatorio += f"| {cb.episodio} | {cb.win_rate*100:.2f}% | R$ {cb.total_pnl:.2f} | {cb.trades_abertos} |\n"

        return relatorio

    def render(self) -> None:
        """Render para compatibilidade Gym (opcional)."""
        print(
            f"Episodio: {self.episodio_atual} | "
            f"Capital: R$ {self.capital_atual:.2f} | "
            f"Preco: {self.preco_atual:.2f} | "
            f"Posicao: {'Aberta' if self.posicao_ativa else 'Fechada'}"
        )
