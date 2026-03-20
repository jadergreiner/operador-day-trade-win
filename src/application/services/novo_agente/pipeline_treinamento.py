"""Pipeline de Treinamento RL para Day Trade de Mini Índice.

Coordena o ciclo completo de treinamento:
    1. Gerar ou carregar dados históricos de preços
    2. Criar o ambiente de simulação
    3. Treinar o agente RL por múltiplos episódios
    4. Avaliar o desempenho e gerar relatório
    5. Salvar o modelo treinado

O pipeline aceita dados reais (MT5) ou dados sintéticos (para testes).
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Optional

import numpy as np
import pandas as pd

from src.application.services.novo_agente.ambiente_trading import (
    AmbienteTradingMiniIndice,
    ConfiguracaoAmbiente,
    AcaoTrading,
)
from src.application.services.novo_agente.agente_q_learning import (
    AgenteQLearningMiniIndice,
    ConfiguracaoAgente,
)

logger = logging.getLogger(__name__)

DIRETORIO_MODELOS = Path("data/models/novo_agente_rl")


@dataclass
class ResultadoEpisodio:
    """Resultado de um episódio de treinamento ou avaliação."""

    episodio: int
    pnl_pts: float
    pnl_brl: float
    n_trades: int
    n_vitorias: int
    epsilon: float
    motivo_termino: str
    recompensa_total: float

    @property
    def taxa_acerto(self) -> float:
        """Taxa de acerto do episódio."""
        return self.n_vitorias / self.n_trades if self.n_trades > 0 else 0.0

    @property
    def meta_atingida(self) -> bool:
        """Indica se a meta de ganho diário foi atingida."""
        return self.motivo_termino == "meta_atingida"

    @property
    def stop_acionado(self) -> bool:
        """Indica se o stop de perda diário foi acionado."""
        return self.motivo_termino == "stop_loss_diario"


@dataclass
class RelatorioTreinamento:
    """Relatório consolidado do treinamento."""

    timestamp_inicio: str
    timestamp_fim: str
    n_episodios_treino: int
    n_episodios_avaliacao: int
    config_ambiente: dict
    config_agente: dict

    # Métricas de treinamento
    episodios_treino: list[ResultadoEpisodio] = field(
        default_factory=list
    )
    episodios_avaliacao: list[ResultadoEpisodio] = field(
        default_factory=list
    )

    @property
    def pnl_medio_treino(self) -> float:
        """P&L médio em R$ dos episódios de treinamento."""
        if not self.episodios_treino:
            return 0.0
        return np.mean([e.pnl_brl for e in self.episodios_treino])

    @property
    def pnl_medio_avaliacao(self) -> float:
        """P&L médio em R$ dos episódios de avaliação."""
        if not self.episodios_avaliacao:
            return 0.0
        return np.mean([e.pnl_brl for e in self.episodios_avaliacao])

    @property
    def taxa_meta_treino(self) -> float:
        """Fração de episódios de treino em que a meta foi atingida."""
        if not self.episodios_treino:
            return 0.0
        return np.mean([e.meta_atingida for e in self.episodios_treino])

    @property
    def taxa_meta_avaliacao(self) -> float:
        """Fração de episódios de avaliação em que a meta foi atingida."""
        if not self.episodios_avaliacao:
            return 0.0
        return np.mean(
            [e.meta_atingida for e in self.episodios_avaliacao]
        )

    @property
    def taxa_stop_avaliacao(self) -> float:
        """Fração de episódios de avaliação com stop acionado."""
        if not self.episodios_avaliacao:
            return 0.0
        return np.mean(
            [e.stop_acionado for e in self.episodios_avaliacao]
        )

    def para_dict(self) -> dict:
        """Converte o relatório para dicionário serializável."""
        return {
            "timestamp_inicio": self.timestamp_inicio,
            "timestamp_fim": self.timestamp_fim,
            "n_episodios_treino": self.n_episodios_treino,
            "n_episodios_avaliacao": self.n_episodios_avaliacao,
            "config_ambiente": self.config_ambiente,
            "config_agente": self.config_agente,
            "metricas_treino": {
                "pnl_medio_brl": round(self.pnl_medio_treino, 2),
                "taxa_meta": round(self.taxa_meta_treino, 4),
            },
            "metricas_avaliacao": {
                "pnl_medio_brl": round(self.pnl_medio_avaliacao, 2),
                "taxa_meta": round(self.taxa_meta_avaliacao, 4),
                "taxa_stop": round(self.taxa_stop_avaliacao, 4),
            },
        }


class PipelineTreinamentoRL:
    """Pipeline de Treinamento do Agente RL para Mini Índice.

    Gerencia o ciclo completo de treinamento e avaliação do agente.
    Pode usar dados reais (MT5) ou dados sintéticos (para desenvolvimento).
    """

    def __init__(
        self,
        config_ambiente: Optional[ConfiguracaoAmbiente] = None,
        config_agente: Optional[ConfiguracaoAgente] = None,
        diretorio_modelos: Optional[Path] = None,
        semente: int = 42,
    ) -> None:
        """Inicializa o pipeline.

        Args:
            config_ambiente: Configuração do ambiente de trading
            config_agente: Configuração do agente Q-Learning
            diretorio_modelos: Onde salvar modelos treinados
            semente: Semente aleatória
        """
        self.config_ambiente = config_ambiente or ConfiguracaoAmbiente()
        self.config_agente = config_agente or ConfiguracaoAgente()
        self.diretorio_modelos = Path(
            diretorio_modelos or DIRETORIO_MODELOS
        )
        self.semente = semente

        self._agente: Optional[AgenteQLearningMiniIndice] = None
        self._relatorio: Optional[RelatorioTreinamento] = None

        logger.info(
            "Pipeline RL inicializado. "
            "Limite perda: R$%.2f | Meta: R$%.2f",
            self.config_ambiente.limite_perda_diaria_brl,
            self.config_ambiente.meta_ganho_diaria_brl,
        )

    # ------------------------------------------------------------------
    # Interface principal
    # ------------------------------------------------------------------

    def treinar(
        self,
        dados: pd.DataFrame,
        n_episodios: int = 500,
        log_frequencia: int = 50,
    ) -> RelatorioTreinamento:
        """Executa o ciclo de treinamento do agente RL.

        O agente aprende a partir de interações repetidas com o
        ambiente de simulação usando os dados históricos fornecidos.

        Args:
            dados: DataFrame OHLCV com dados históricos
            n_episodios: Número de episódios de treinamento
            log_frequencia: Frequência de log de progresso

        Returns:
            Relatório com métricas de treinamento
        """
        ts_inicio = datetime.now().isoformat()

        ambiente = AmbienteTradingMiniIndice(
            dados=dados,
            config=self.config_ambiente,
            semente=self.semente,
        )

        self._agente = AgenteQLearningMiniIndice(
            tamanho_estado=ambiente.tamanho_estado,
            n_acoes=ambiente.n_acoes,
            config=self.config_agente,
            semente=self.semente,
        )

        episodios_treino: list[ResultadoEpisodio] = []

        logger.info(
            "Iniciando treinamento: %d episódios", n_episodios
        )

        for ep in range(n_episodios):
            resultado = self._executar_episodio(
                ambiente=ambiente,
                agente=self._agente,
                treinando=True,
            )
            episodios_treino.append(resultado)
            self._agente.encerrar_episodio()

            if (ep + 1) % log_frequencia == 0:
                recentes = episodios_treino[-log_frequencia:]
                pnl_medio = np.mean([e.pnl_brl for e in recentes])
                taxa_meta = np.mean(
                    [e.meta_atingida for e in recentes]
                )
                logger.info(
                    "Ep %d/%d | PnL médio: R$%.2f | "
                    "Meta: %.1f%% | ε=%.3f",
                    ep + 1,
                    n_episodios,
                    pnl_medio,
                    taxa_meta * 100,
                    self._agente.epsilon,
                )

        ts_fim = datetime.now().isoformat()

        self._relatorio = RelatorioTreinamento(
            timestamp_inicio=ts_inicio,
            timestamp_fim=ts_fim,
            n_episodios_treino=n_episodios,
            n_episodios_avaliacao=0,
            config_ambiente={
                "limite_perda_brl": (
                    self.config_ambiente.limite_perda_diaria_brl
                ),
                "meta_ganho_brl": (
                    self.config_ambiente.meta_ganho_diaria_brl
                ),
                "janela_observacao": (
                    self.config_ambiente.janela_observacao
                ),
                "max_trades_por_dia": (
                    self.config_ambiente.max_trades_por_dia
                ),
            },
            config_agente={
                "taxa_aprendizado": (
                    self.config_agente.taxa_aprendizado
                ),
                "fator_desconto": self.config_agente.fator_desconto,
                "epsilon_inicial": self.config_agente.epsilon_inicial,
                "camadas_ocultas": list(
                    self.config_agente.camadas_ocultas
                ),
            },
            episodios_treino=episodios_treino,
        )

        logger.info(
            "Treinamento concluído. "
            "P&L médio (treino): R$%.2f | Meta: %.1f%%",
            self._relatorio.pnl_medio_treino,
            self._relatorio.taxa_meta_treino * 100,
        )

        return self._relatorio

    def avaliar(
        self,
        dados: pd.DataFrame,
        n_episodios: int = 100,
    ) -> list[ResultadoEpisodio]:
        """Avalia o agente treinado sem exploração (epsilon=0).

        Args:
            dados: DataFrame OHLCV para avaliação
            n_episodios: Número de episódios de avaliação

        Returns:
            Lista de resultados de avaliação
        """
        if self._agente is None:
            raise RuntimeError(
                "Agente não treinado. Execute treinar() primeiro."
            )

        ambiente = AmbienteTradingMiniIndice(
            dados=dados,
            config=self.config_ambiente,
            semente=self.semente + 1000,
        )

        epsilon_original = self._agente.epsilon
        self._agente.epsilon = 0.0  # Sem exploração na avaliação

        resultados: list[ResultadoEpisodio] = []

        for ep in range(n_episodios):
            resultado = self._executar_episodio(
                ambiente=ambiente,
                agente=self._agente,
                treinando=False,
            )
            resultados.append(resultado)

        self._agente.epsilon = epsilon_original

        if self._relatorio is not None:
            self._relatorio.episodios_avaliacao = resultados
            self._relatorio.n_episodios_avaliacao = n_episodios

        pnl_medio = np.mean([e.pnl_brl for e in resultados])
        taxa_meta = np.mean([e.meta_atingida for e in resultados])
        taxa_stop = np.mean([e.stop_acionado for e in resultados])

        logger.info(
            "Avaliação concluída (%d ep). "
            "P&L médio: R$%.2f | Meta: %.1f%% | Stop: %.1f%%",
            n_episodios,
            pnl_medio,
            taxa_meta * 100,
            taxa_stop * 100,
        )

        return resultados

    def treinar_incremental_de_episodios(
        self,
        episodios: list[dict],
        *,
        horizonte_padrao: int = 30,
        max_amostras: int = 64,
        salvar_modelo: bool = True,
    ) -> dict:
        """Executa um retrain incremental a partir de episódios já avaliados."""
        if self._agente is None:
            raise RuntimeError("Agente não inicializado.")

        if not episodios:
            return {"executado": False, "motivo": "sem_episodios"}

        amostras: list[tuple[np.ndarray, int, float]] = []
        acao_map = {"HOLD": 0, "BUY": 1, "SELL": 2}

        for ep in episodios[-max_amostras:]:
            state_vector = ep.get("state_vector")
            if not state_vector:
                continue

            action = str(ep.get("action", "")).upper().strip()
            if action not in acao_map:
                continue

            rewards = ep.get("rewards") or {}
            if isinstance(rewards, dict) and rewards:
                reward_values = []
                for reward_data in rewards.values():
                    if not isinstance(reward_data, dict):
                        continue
                    reward_val = reward_data.get("reward_normalized")
                    if reward_val is not None:
                        reward_values.append(float(reward_val))
                if reward_values:
                    reward = float(np.mean(reward_values))
                else:
                    continue
            else:
                reward = ep.get(f"reward_norm_{horizonte_padrao}m")
                if reward is None:
                    continue
                reward = float(reward)

            state_arr = np.asarray(state_vector, dtype=np.float32)
            if state_arr.size != self._agente.tamanho_estado:
                logger.debug(
                    "Ignorando episódio %s por estado incompatível (%s != %s)",
                    ep.get("episode_id"),
                    state_arr.size,
                    self._agente.tamanho_estado,
                )
                continue

            amostras.append((state_arr, acao_map[action], reward))

        if not amostras:
            return {"executado": False, "motivo": "sem_amostras_validas"}

        estados = np.stack([item[0] for item in amostras]).astype(np.float32)
        acoes = np.array([item[1] for item in amostras], dtype=np.int32)
        recompensas = np.array([item[2] for item in amostras], dtype=np.float32)
        proximos_estados = np.zeros_like(estados)
        terminados = np.ones(len(amostras), dtype=bool)

        loss = self._agente.treinar_batch(
            estados=estados,
            acoes=acoes,
            recompensas=recompensas,
            proximos_estados=proximos_estados,
            terminados=terminados,
        )

        if salvar_modelo:
            try:
                self.salvar_modelo("modelo_final")
            except Exception as exc:
                logger.warning("Falha ao persistir modelo incremental: %s", exc)

        resumo = {
            "executado": True,
            "amostras": len(amostras),
            "loss": loss,
            "reward_media": float(np.mean(recompensas)),
            "reward_min": float(np.min(recompensas)),
            "reward_max": float(np.max(recompensas)),
        }
        logger.info(
            "Retreino incremental RL executado: amostras=%d | loss=%s | reward_media=%.4f",
            resumo["amostras"],
            f"{loss:.6f}" if loss is not None else "None",
            resumo["reward_media"],
        )
        return resumo

    def salvar_modelo(self, nome: str = "modelo_final") -> Path:
        """Salva o modelo treinado e o relatório em disco.

        Args:
            nome: Nome do arquivo/diretório do modelo

        Returns:
            Caminho onde o modelo foi salvo
        """
        if self._agente is None:
            raise RuntimeError(
                "Agente não treinado. Execute treinar() primeiro."
            )

        caminho = self.diretorio_modelos / nome
        self._agente.salvar(caminho)

        if self._relatorio is not None:
            relatorio_path = caminho / "relatorio_treinamento.json"
            with open(
                relatorio_path, "w", encoding="utf-8"
            ) as f:
                json.dump(
                    self._relatorio.para_dict(),
                    f,
                    indent=2,
                    ensure_ascii=False,
                )
            logger.info("Relatório salvo: %s", relatorio_path)

        return caminho

    def carregar_modelo(self, nome: str = "modelo_final") -> None:
        """Carrega modelo previamente treinado.

        Args:
            nome: Nome do arquivo/diretório do modelo
        """
        caminho = self.diretorio_modelos / nome

        self._agente = AgenteQLearningMiniIndice(
            tamanho_estado=AmbienteTradingMiniIndice.N_FEATURES,
            n_acoes=len(AcaoTrading),
            config=self.config_agente,
            semente=self.semente,
        )
        self._agente.carregar(caminho)

    # ------------------------------------------------------------------
    # Execução de episódio (interno)
    # ------------------------------------------------------------------

    def _executar_episodio(
        self,
        ambiente: AmbienteTradingMiniIndice,
        agente: AgenteQLearningMiniIndice,
        treinando: bool,
    ) -> ResultadoEpisodio:
        """Executa um único episódio (dia de trading simulado).

        Args:
            ambiente: Ambiente de simulação
            agente: Agente a executar
            treinando: Se True, o agente aprende (atualiza Q-values)

        Returns:
            Resultado do episódio
        """
        estado = ambiente.reset()
        recompensa_total = 0.0
        motivo_termino = "em_andamento"

        while True:
            acao = agente.selecionar_acao(estado)
            proximo_estado, recompensa, terminado, info = ambiente.step(
                acao
            )
            recompensa_total += recompensa

            if treinando:
                agente.memorizar(
                    estado, acao, recompensa, proximo_estado, terminado
                )
                agente.aprender()

            estado = proximo_estado

            if terminado:
                motivo_termino = info.get(
                    "terminado_motivo", "desconhecido"
                )
                break

        # Usar vitórias reais registradas pelo ambiente
        return ResultadoEpisodio(
            episodio=agente.n_episodios,
            pnl_pts=ambiente._pnl_dia_pts,
            pnl_brl=ambiente.pnl_atual_brl,
            n_trades=ambiente._n_trades,
            n_vitorias=ambiente._n_vitorias,
            epsilon=agente.epsilon,
            motivo_termino=motivo_termino,
            recompensa_total=recompensa_total,
        )


# ---------------------------------------------------------------------------
# Gerador de dados sintéticos para testes e desenvolvimento
# ---------------------------------------------------------------------------

def gerar_dados_sinteticos(
    n_candles: int = 1000,
    preco_inicial: float = 128_000.0,
    volatilidade_diaria: float = 0.003,
    semente: int = 42,
) -> pd.DataFrame:
    """Gera dados OHLCV sintéticos para treino/testes.

    Simula um mercado com random walk + tendência suave.
    Útil para validação do pipeline sem dados reais.

    Args:
        n_candles: Número de candles a gerar
        preco_inicial: Preço de abertura inicial
        volatilidade_diaria: Volatilidade diária (desvio padrão)
        semente: Semente aleatória

    Returns:
        DataFrame com colunas [open, high, low, close, volume]
    """
    rng = np.random.default_rng(semente)

    retornos = rng.normal(0, volatilidade_diaria, n_candles)
    fechamentos = preco_inicial * np.cumprod(1 + retornos)

    amplitude = preco_inicial * volatilidade_diaria * 0.5
    maximas = fechamentos * (
        1 + abs(rng.normal(0, 0.001, n_candles))
    )
    minimas = fechamentos * (
        1 - abs(rng.normal(0, 0.001, n_candles))
    )

    volumes = rng.integers(1000, 50000, n_candles).astype(float)

    aberturas = np.roll(fechamentos, 1)
    aberturas[0] = preco_inicial

    return pd.DataFrame(
        {
            "open": aberturas,
            "high": maximas,
            "low": minimas,
            "close": fechamentos,
            "volume": volumes,
        }
    )
