"""Agente Q-Learning para Day Trade de Mini Índice.

Implementa um agente de Reinforcement Learning baseado em Q-Learning
com aproximação de função por rede neural (MLP).

O agente aprende autonomamente quais ações tomar em cada estado do
mercado, sem nenhuma estratégia pré-definida. O aprendizado ocorre
por tentativa e erro (Exploração vs Explotação).

Algoritmo:
    Q-Learning com Experience Replay e Target Network simplificado.
    A função Q(s, a) é aproximada por um MLPRegressor do sklearn.
"""

from __future__ import annotations

import json
import logging
from collections import deque
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

import joblib
import numpy as np
from sklearn.neural_network import MLPRegressor

logger = logging.getLogger(__name__)


@dataclass
class ConfiguracaoAgente:
    """Configuração do agente Q-Learning.

    Os hiperparâmetros são ajustados automaticamente durante o
    treinamento. O agente começa explorando muito (epsilon alto)
    e gradualmente passa a explotar mais (epsilon baixo).
    """

    # Hiperparâmetros de aprendizado
    taxa_aprendizado: float = 0.001
    fator_desconto: float = 0.95       # gamma: importância recompensas futuras
    epsilon_inicial: float = 1.0       # exploração inicial: 100%
    epsilon_minimo: float = 0.05       # exploração mínima: 5%
    taxa_decaimento_epsilon: float = 0.995  # decaimento por episódio

    # Configuração da rede neural (Q-function approximator)
    camadas_ocultas: tuple = (128, 64, 32)
    max_iteracoes_mlp: int = 200

    # Experience Replay
    tamanho_buffer: int = 10_000
    tamanho_mini_lote: int = 64
    min_experiencias_treino: int = 256  # Mínimo para iniciar treinamento

    # Frequência de atualização
    frequencia_atualizacao: int = 4  # Treina a cada N passos


class AgenteQLearningMiniIndice:
    """Agente Q-Learning para Day Trade de Mini Índice.

    Aprende quais ações (HOLD, COMPRAR, VENDER) tomadas em cada
    estado do mercado levam ao maior retorno acumulado.

    O agente não tem conhecimento prévio do mercado. Aprende
    exclusivamente pela experiência de interagir com o ambiente.

    Atributos:
        config: Configuração do agente
        epsilon: Taxa de exploração atual
        n_passos: Número total de passos executados
        n_episodios: Número total de episódios treinados
    """

    def __init__(
        self,
        tamanho_estado: int,
        n_acoes: int,
        config: Optional[ConfiguracaoAgente] = None,
        semente: int = 42,
    ) -> None:
        """Inicializa o agente Q-Learning.

        Args:
            tamanho_estado: Dimensão do vetor de estado do ambiente
            n_acoes: Número de ações disponíveis
            config: Configuração do agente (usa padrão se None)
            semente: Semente aleatória para reprodutibilidade
        """
        self.tamanho_estado = tamanho_estado
        self.n_acoes = n_acoes
        self.config = config or ConfiguracaoAgente()
        self.rng = np.random.default_rng(semente)

        # Taxa de exploração atual (decai com o tempo)
        self.epsilon: float = self.config.epsilon_inicial

        # Contadores de progresso
        self.n_passos: int = 0
        self.n_episodios: int = 0

        # Buffer de experiências para Experience Replay
        self._buffer: deque = deque(
            maxlen=self.config.tamanho_buffer
        )

        # Rede neural para aproximar Q(s, a)
        self._modelo = self._criar_modelo(semente)

        # Flag: indica se o modelo já foi ajustado (fit) ao menos 1 vez
        self._modelo_inicializado: bool = False

        logger.info(
            "Agente Q-Learning inicializado. "
            "Estado: %d dims, Ações: %d",
            tamanho_estado,
            n_acoes,
        )

    # ------------------------------------------------------------------
    # Interface principal do agente
    # ------------------------------------------------------------------

    def selecionar_acao(self, estado: np.ndarray) -> int:
        """Seleciona ação usando política epsilon-greedy.

        Com probabilidade epsilon, explora (ação aleatória).
        Com probabilidade 1-epsilon, explota (melhor ação conhecida).

        Args:
            estado: Vetor de estado atual (shape: [tamanho_estado])

        Returns:
            Ação selecionada (int em [0, n_acoes-1])
        """
        if self.rng.random() < self.epsilon:
            # Exploração: ação aleatória
            return int(self.rng.integers(0, self.n_acoes))

        # Explotação: ação com maior Q-value
        return self._acao_gulosa(estado)

    def obter_acao_e_confianca(
        self,
        estado: np.ndarray,
        *,
        modo_producao: bool = True,
    ) -> tuple[int, float]:
        """Retorna ação e confiança derivada dos Q-values.

        Em produção, a ação é sempre gulosa para evitar exploração
        aleatória com capital real. A confiança é calculada via
        softmax estável sobre os Q-values previstos.
        """
        acao = self._acao_gulosa(estado) if modo_producao else self.selecionar_acao(estado)
        q_valores = self._prever_q_values(estado)

        if q_valores.size != self.n_acoes or not np.isfinite(q_valores).all():
            return acao, 0.0

        q_estavel = q_valores - np.max(q_valores)
        exp_q = np.exp(q_estavel)
        soma_exp = float(np.sum(exp_q))
        if soma_exp <= 0 or not np.isfinite(soma_exp):
            return acao, 0.0

        probabilidades = exp_q / soma_exp
        confianca = float(probabilidades[int(acao)])
        return acao, max(0.0, min(1.0, confianca))

    def memorizar(
        self,
        estado: np.ndarray,
        acao: int,
        recompensa: float,
        proximo_estado: np.ndarray,
        terminado: bool,
    ) -> None:
        """Armazena experiência no buffer de replay.

        Args:
            estado: Estado atual
            acao: Ação executada
            recompensa: Recompensa recebida
            proximo_estado: Estado resultante
            terminado: Se o episódio terminou
        """
        self._buffer.append(
            (estado, acao, recompensa, proximo_estado, terminado)
        )
        self.n_passos += 1

    def aprender(self) -> Optional[float]:
        """Treina a rede neural com um mini-lote de experiências.

        Usa Temporal Difference (TD) para calcular os alvos Q:
            Q(s, a) ← r + γ * max_a' Q(s', a')

        Returns:
            Erro médio de treinamento (None se buffer insuficiente)
        """
        if len(self._buffer) < self.config.min_experiencias_treino:
            return None

        if self.n_passos % self.config.frequencia_atualizacao != 0:
            return None

        # Amostrar mini-lote aleatório do buffer
        indices = self.rng.choice(
            len(self._buffer),
            size=min(self.config.tamanho_mini_lote, len(self._buffer)),
            replace=False,
        )
        lote = [self._buffer[i] for i in indices]

        estados = np.array([e[0] for e in lote], dtype=np.float32)
        acoes = np.array([e[1] for e in lote], dtype=np.int32)
        recompensas = np.array([e[2] for e in lote], dtype=np.float32)
        proximos_estados = np.array(
            [e[3] for e in lote], dtype=np.float32
        )
        terminados = np.array([e[4] for e in lote], dtype=bool)

        # Calcular alvos TD para cada experiência
        alvos_q = self._calcular_alvos_td(
            estados, acoes, recompensas, proximos_estados, terminados
        )

        # Treinar a rede neural
        erro = self._treinar_rede(estados, alvos_q)

        return erro

    def encerrar_episodio(self) -> None:
        """Atualiza epsilon ao encerrar um episódio (exploração decai)."""
        self.n_episodios += 1
        self.epsilon = max(
            self.config.epsilon_minimo,
            self.epsilon * self.config.taxa_decaimento_epsilon,
        )

    def salvar(self, caminho: Path) -> None:
        """Salva o modelo e metadados em disco.

        Args:
            caminho: Diretório onde salvar o modelo
        """
        caminho = Path(caminho)
        caminho.mkdir(parents=True, exist_ok=True)

        # Salvar rede neural
        joblib.dump(self._modelo, caminho / "q_network.pkl")

        # Salvar metadados
        metadados = {
            "tamanho_estado": self.tamanho_estado,
            "n_acoes": self.n_acoes,
            "epsilon": self.epsilon,
            "n_passos": self.n_passos,
            "n_episodios": self.n_episodios,
            "modelo_inicializado": self._modelo_inicializado,
            "config": {
                "taxa_aprendizado": self.config.taxa_aprendizado,
                "fator_desconto": self.config.fator_desconto,
                "epsilon_inicial": self.config.epsilon_inicial,
                "epsilon_minimo": self.config.epsilon_minimo,
                "taxa_decaimento_epsilon": (
                    self.config.taxa_decaimento_epsilon
                ),
            },
        }
        with open(caminho / "metadados.json", "w", encoding="utf-8") as f:
            json.dump(metadados, f, indent=2, ensure_ascii=False)

        logger.info(
            "Modelo salvo em %s (episódios=%d, epsilon=%.3f)",
            caminho,
            self.n_episodios,
            self.epsilon,
        )

    def carregar(self, caminho: Path) -> None:
        """Carrega modelo e metadados do disco.

        Args:
            caminho: Diretório onde o modelo está salvo
        """
        caminho = Path(caminho)

        # Carregar rede neural
        self._modelo = joblib.load(caminho / "q_network.pkl")
        self._modelo_inicializado = True

        # Carregar metadados
        with open(caminho / "metadados.json", encoding="utf-8") as f:
            metadados = json.load(f)

        self.epsilon = metadados["epsilon"]
        self.n_passos = metadados["n_passos"]
        self.n_episodios = metadados["n_episodios"]

        logger.info(
            "Modelo carregado de %s (episódios=%d, epsilon=%.3f)",
            caminho,
            self.n_episodios,
            self.epsilon,
        )

    # ------------------------------------------------------------------
    # Métodos internos
    # ------------------------------------------------------------------

    def _criar_modelo(self, semente: int) -> MLPRegressor:
        """Cria a rede neural para aproximar Q(s, a).

        Returns:
            MLPRegressor configurado para Q-Learning
        """
        return MLPRegressor(
            hidden_layer_sizes=self.config.camadas_ocultas,
            activation="relu",
            solver="adam",
            alpha=1e-4,          # regularização L2
            learning_rate="adaptive",
            learning_rate_init=self.config.taxa_aprendizado,
            max_iter=self.config.max_iteracoes_mlp,
            warm_start=True,     # crucial: reutiliza pesos anteriores
            random_state=semente,
            n_iter_no_change=10,
            tol=1e-5,
        )

    def _acao_gulosa(self, estado: np.ndarray) -> int:
        """Retorna a ação com maior Q-value estimado.

        Args:
            estado: Vetor de estado atual

        Returns:
            Índice da ação com maior Q-value
        """
        if not self._modelo_inicializado:
            # Antes do primeiro treino, ação aleatória
            return int(self.rng.integers(0, self.n_acoes))

        q_valores = self._prever_q_values(estado)
        return int(np.argmax(q_valores))

    def _prever_q_values(self, estado: np.ndarray) -> np.ndarray:
        """Prevê Q-values para todas as ações dado o estado.

        Args:
            estado: Vetor de estado (shape: [tamanho_estado])

        Returns:
            Array de Q-values (shape: [n_acoes])
        """
        if not self._modelo_inicializado:
            return np.zeros(self.n_acoes, dtype=np.float32)

        estado_2d = estado.reshape(1, -1)
        saida = self._modelo.predict(estado_2d)[0]

        # Garantir que a saída tem exatamente n_acoes valores
        if saida.ndim == 0:
            # Saída escalar: expande para vetor
            return np.full(self.n_acoes, float(saida), dtype=np.float32)

        if len(saida) != self.n_acoes:
            # Shape inesperado: retorna zeros para segurança
            return np.zeros(self.n_acoes, dtype=np.float32)

        return saida.astype(np.float32)

    def _calcular_alvos_td(
        self,
        estados: np.ndarray,
        acoes: np.ndarray,
        recompensas: np.ndarray,
        proximos_estados: np.ndarray,
        terminados: np.ndarray,
    ) -> np.ndarray:
        """Calcula os alvos Q usando a equação de Bellman.

        Q(s, a) ← r + γ * max_a' Q(s', a')  (se não terminado)
        Q(s, a) ← r                           (se terminado)

        Returns:
            Array de alvos Q (shape: [tamanho_lote, n_acoes])
        """
        n = len(estados)

        if self._modelo_inicializado:
            q_atual = self._modelo.predict(estados)
            q_proximo = self._modelo.predict(proximos_estados)
        else:
            q_atual = np.zeros((n, self.n_acoes))
            q_proximo = np.zeros((n, self.n_acoes))

        # Garantir shape correto
        if q_atual.ndim == 1:
            q_atual = np.tile(q_atual.reshape(-1, 1), (1, self.n_acoes))
        if q_proximo.ndim == 1:
            q_proximo = np.tile(
                q_proximo.reshape(-1, 1), (1, self.n_acoes)
            )

        alvos = q_atual.copy()

        for i in range(n):
            if terminados[i]:
                alvo = recompensas[i]
            else:
                alvo = (
                    recompensas[i]
                    + self.config.fator_desconto * np.max(q_proximo[i])
                )
            alvos[i, acoes[i]] = alvo

        return alvos

    def _treinar_rede(
        self, estados: np.ndarray, alvos: np.ndarray
    ) -> float:
        """Treina a rede neural com os dados fornecidos.

        Args:
            estados: Lote de estados de entrada
            alvos: Lote de Q-values alvo

        Returns:
            Perda média do treinamento
        """
        try:
            self._modelo.fit(estados, alvos)
            self._modelo_inicializado = True
            return float(self._modelo.loss_)
        except Exception as exc:
            logger.warning("Erro no treinamento da rede: %s", exc)
            return float("nan")
