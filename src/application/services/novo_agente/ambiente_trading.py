"""Ambiente de Trading para Reinforcement Learning - Mini Índice.

Simula o mercado de Mini Índice (WINFUT) para treinamento do agente RL.
O agente aprende estratégias de trade interagindo com este ambiente.

O modelo de valor do ponto:
    - 1 ponto = R$0,20 por contrato mini
    - Custo estimado por operação: ~25 pontos (spread + slippage + taxas)
    - Limite de perda diária: R$250,00 (= 1.250 pontos)
    - Meta de ganho diário: R$100,00 (= 500 pontos)
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import IntEnum
from typing import Optional
import numpy as np
import pandas as pd


class AcaoTrading(IntEnum):
    """Ações disponíveis para o agente de trading."""

    HOLD = 0   # Manter posição atual (ou ficar sem posição)
    COMPRAR = 1  # Abrir compra (ou fechar venda)
    VENDER = 2   # Abrir venda (ou fechar compra)


class EstadoPosicao(IntEnum):
    """Estado da posição atual do agente."""

    SEM_POSICAO = 0
    LONG = 1    # Posição comprada
    SHORT = -1  # Posição vendida


@dataclass(frozen=True)
class ConfiguracaoAmbiente:
    """Configuração do ambiente de trading.

    Todos os valores são calculados automaticamente com base nos
    parâmetros financeiros reais do Mini Índice B3.
    """

    # Parâmetros financeiros
    limite_perda_diaria_brl: float = 250.0
    meta_ganho_diaria_brl: float = 100.0
    ponto_valor_brl: float = 0.20
    custo_operacao_pts: float = 25.0  # spread + slippage + emolumentos

    # Parâmetros do ambiente
    janela_observacao: int = 20       # Número de candles para calcular features
    max_trades_por_dia: int = 10      # Limite de operações por sessão

    # Penalidades e bônus de recompensa
    penalidade_stop_loss: float = -50.0  # Punição ao atingir limite de perda
    bonus_meta_atingida: float = 30.0    # Bônus ao atingir meta de ganho

    @property
    def limite_perda_pts(self) -> float:
        """Limite de perda diária em pontos."""
        return self.limite_perda_diaria_brl / self.ponto_valor_brl

    @property
    def meta_ganho_pts(self) -> float:
        """Meta de ganho diária em pontos."""
        return self.meta_ganho_diaria_brl / self.ponto_valor_brl


class AmbienteTradingMiniIndice:
    """Ambiente de Reinforcement Learning para Day Trade de Mini Índice.

    O ambiente fornece:
    - Estado: vetor de features calculadas automaticamente dos preços OHLCV
    - Ações: HOLD, COMPRAR, VENDER
    - Recompensa: P&L normalizado com penalidades por risco

    O agente aprende sozinho quais estados levam a ações lucrativas,
    sem nenhuma estratégia pré-definida.
    """

    N_FEATURES = 15  # Dimensão do vetor de estado

    def __init__(
        self,
        dados: pd.DataFrame,
        config: Optional[ConfiguracaoAmbiente] = None,
        semente: int = 42,
    ) -> None:
        """Inicializa o ambiente com dados históricos OHLCV.

        Args:
            dados: DataFrame com colunas ['open', 'high', 'low', 'close', 'volume']
            config: Configuração do ambiente (usa padrão se None)
            semente: Semente aleatória para reprodutibilidade
        """
        self._validar_dados(dados)
        self.dados = dados.reset_index(drop=True)
        self.config = config or ConfiguracaoAmbiente()
        self.rng = np.random.default_rng(semente)

        # Estado interno do episódio
        self._indice: int = 0
        self._posicao: EstadoPosicao = EstadoPosicao.SEM_POSICAO
        self._preco_entrada: float = 0.0
        self._pnl_dia_pts: float = 0.0
        self._n_trades: int = 0
        self._n_vitorias: int = 0  # Trades com P&L positivo
        self._terminado: bool = False

    # ------------------------------------------------------------------
    # Interface principal do ambiente RL
    # ------------------------------------------------------------------

    def reset(self) -> np.ndarray:
        """Reinicia o ambiente para um novo episódio.

        Returns:
            Vetor de estado inicial (shape: [N_FEATURES])
        """
        inicio_minimo = self.config.janela_observacao
        self._indice = inicio_minimo
        self._posicao = EstadoPosicao.SEM_POSICAO
        self._preco_entrada = 0.0
        self._pnl_dia_pts = 0.0
        self._n_trades = 0
        self._n_vitorias = 0
        self._terminado = False

        return self._calcular_estado()

    def step(
        self, acao: int
    ) -> tuple[np.ndarray, float, bool, dict]:
        """Executa uma ação no ambiente.

        Args:
            acao: Ação a executar (0=HOLD, 1=COMPRAR, 2=VENDER)

        Returns:
            Tupla (proximo_estado, recompensa, terminado, info)
        """
        if self._terminado:
            raise RuntimeError(
                "Episódio encerrado. Chame reset() para iniciar novo."
            )

        acao_enum = AcaoTrading(acao)
        preco_atual = float(self.dados.loc[self._indice, "close"])
        recompensa = 0.0
        info: dict = {
            "acao": acao_enum.name,
            "posicao": self._posicao.name,
            "preco": preco_atual,
            "pnl_dia_pts": self._pnl_dia_pts,
            "n_trades": self._n_trades,
        }

        # Processar a ação
        recompensa += self._executar_acao(acao_enum, preco_atual)

        # Avançar no tempo
        self._indice += 1

        # Verificar condições de término
        terminado = self._verificar_termino()
        self._terminado = terminado

        proximo_estado = self._calcular_estado()
        info["terminado_motivo"] = self._motivo_termino()

        return proximo_estado, recompensa, terminado, info

    @property
    def tamanho_estado(self) -> int:
        """Dimensão do vetor de estado."""
        return self.N_FEATURES

    @property
    def n_acoes(self) -> int:
        """Número de ações disponíveis."""
        return len(AcaoTrading)

    @property
    def pnl_atual_brl(self) -> float:
        """P&L atual em R$."""
        return self._pnl_dia_pts * self.config.ponto_valor_brl

    # ------------------------------------------------------------------
    # Cálculo de estado (features extraídas automaticamente)
    # ------------------------------------------------------------------

    def _calcular_estado(self) -> np.ndarray:
        """Calcula vetor de features a partir dos dados de preço.

        O agente aprende sozinho quais features são relevantes.
        As features são calculadas de forma completamente automática,
        sem estratégias pré-definidas.

        Returns:
            Array numpy de shape [N_FEATURES] normalizado em [-1, 1]
        """
        fim = self._indice + 1
        inicio = max(0, fim - self.config.janela_observacao)
        janela = self.dados.iloc[inicio:fim]

        fechamentos = janela["close"].values.astype(float)
        volumes = janela["volume"].values.astype(float)
        maximas = janela["high"].values.astype(float)
        minimas = janela["low"].values.astype(float)

        preco_atual = fechamentos[-1]
        preco_std = np.std(fechamentos) if len(fechamentos) > 1 else 0.0
        if preco_std == 0:
            # Fallback independente de escala: 1% do preço atual
            preco_std = preco_atual * 0.01 if preco_atual > 0 else 1.0

        # Feature 1-5: Retornos em diferentes janelas (momentum)
        retornos = np.diff(fechamentos) / (fechamentos[:-1] + 1e-8)
        ret_1 = retornos[-1] if len(retornos) >= 1 else 0.0
        ret_3 = np.mean(retornos[-3:]) if len(retornos) >= 3 else 0.0
        ret_5 = np.mean(retornos[-5:]) if len(retornos) >= 5 else 0.0
        ret_10 = (
            np.mean(retornos[-10:]) if len(retornos) >= 10 else 0.0
        )
        ret_20 = np.mean(retornos) if len(retornos) >= 1 else 0.0

        # Feature 6: Volatilidade (desvio padrão dos retornos)
        volatilidade = (
            np.std(retornos[-10:]) if len(retornos) >= 2 else 0.0
        )

        # Feature 7: Posição relativa ao range da janela
        max_janela = np.max(maximas)
        min_janela = np.min(minimas)
        range_janela = max_janela - min_janela
        posicao_range = (
            (preco_atual - min_janela) / range_janela
            if range_janela > 0
            else 0.5
        )

        # Feature 8: Distância da média móvel (tendência)
        media_movel = np.mean(fechamentos)
        dist_media = (preco_atual - media_movel) / preco_std

        # Feature 9: Ratio volume atual vs médio
        vol_medio = np.mean(volumes) if np.mean(volumes) > 0 else 1.0
        ratio_volume = volumes[-1] / vol_medio if vol_medio > 0 else 1.0

        # Feature 10: High-Low ratio (amplitude do candle atual)
        candle_atual_idx = self._indice
        candle_amplitude = (
            (maximas[-1] - minimas[-1]) / preco_atual
            if preco_atual > 0
            else 0.0
        )

        # Feature 11: Posição atual codificada
        posicao_cod = float(self._posicao.value)

        # Feature 12: PnL acumulado normalizado
        pnl_norm = np.tanh(
            self._pnl_dia_pts / (self.config.limite_perda_pts + 1e-8)
        )

        # Feature 13: Fração do dia consumida (progresso)
        total_candles = len(self.dados) - self.config.janela_observacao
        fracao_dia = (
            (self._indice - self.config.janela_observacao)
            / max(total_candles, 1)
        )

        # Feature 14: Número de trades normalizado
        trades_norm = self._n_trades / max(
            self.config.max_trades_por_dia, 1
        )

        # Feature 15: Pressão direcional (alta vs queda na janela)
        n_alta = np.sum(retornos > 0) if len(retornos) > 0 else 0
        pressao_direcional = (
            2.0 * n_alta / len(retornos) - 1.0
            if len(retornos) > 0
            else 0.0
        )

        estado = np.array(
            [
                np.tanh(ret_1 * 100),          # 1: retorno 1 período
                np.tanh(ret_3 * 100),          # 2: retorno 3 períodos
                np.tanh(ret_5 * 100),          # 3: retorno 5 períodos
                np.tanh(ret_10 * 100),         # 4: retorno 10 períodos
                np.tanh(ret_20 * 100),         # 5: retorno 20 períodos
                np.tanh(volatilidade * 100),   # 6: volatilidade
                posicao_range * 2 - 1,         # 7: posição no range [-1,1]
                np.tanh(dist_media),           # 8: distância da média
                np.tanh(ratio_volume - 1),     # 9: ratio volume
                np.tanh(candle_amplitude * 100),  # 10: amplitude candle
                posicao_cod,                   # 11: posição atual
                pnl_norm,                      # 12: PnL acumulado
                fracao_dia * 2 - 1,            # 13: progresso do dia
                trades_norm * 2 - 1,           # 14: trades realizados
                pressao_direcional,            # 15: pressão direcional
            ],
            dtype=np.float32,
        )

        return np.clip(estado, -2.0, 2.0)

    # ------------------------------------------------------------------
    # Execução de ações e cálculo de recompensas
    # ------------------------------------------------------------------

    def _executar_acao(
        self, acao: AcaoTrading, preco: float
    ) -> float:
        """Executa a ação escolhida pelo agente.

        Args:
            acao: Ação a executar
            preco: Preço atual de execução

        Returns:
            Recompensa imediata da ação
        """
        recompensa = 0.0

        if acao == AcaoTrading.HOLD:
            # Sem transação; recompensa neutra
            pass

        elif acao == AcaoTrading.COMPRAR:
            if self._posicao == EstadoPosicao.SEM_POSICAO:
                # Abre posição LONG
                self._posicao = EstadoPosicao.LONG
                self._preco_entrada = preco
                self._n_trades += 1
                # Custo de entrada
                recompensa -= self.config.custo_operacao_pts / 2
            elif self._posicao == EstadoPosicao.SHORT:
                # Fecha posição SHORT
                pnl_bruto = (
                    self._preco_entrada - preco
                )  # Short lucra quando preço cai
                recompensa = self._fechar_posicao(pnl_bruto)

        elif acao == AcaoTrading.VENDER:
            if self._posicao == EstadoPosicao.SEM_POSICAO:
                # Abre posição SHORT
                self._posicao = EstadoPosicao.SHORT
                self._preco_entrada = preco
                self._n_trades += 1
                # Custo de entrada
                recompensa -= self.config.custo_operacao_pts / 2
            elif self._posicao == EstadoPosicao.LONG:
                # Fecha posição LONG
                pnl_bruto = (
                    preco - self._preco_entrada
                )  # Long lucra quando preço sobe
                recompensa = self._fechar_posicao(pnl_bruto)

        # Penalidade se limite de perda atingido
        if self._pnl_dia_pts <= -self.config.limite_perda_pts:
            recompensa += self.config.penalidade_stop_loss

        # Bônus se meta atingida
        if self._pnl_dia_pts >= self.config.meta_ganho_pts:
            recompensa += self.config.bonus_meta_atingida

        return float(recompensa)

    def _fechar_posicao(self, pnl_bruto_pts: float) -> float:
        """Fecha a posição atual e calcula o P&L líquido.

        Args:
            pnl_bruto_pts: P&L bruto em pontos antes dos custos

        Returns:
            Recompensa normalizada (P&L líquido em pontos)
        """
        pnl_liquido_pts = (
            pnl_bruto_pts - self.config.custo_operacao_pts
        )
        self._pnl_dia_pts += pnl_liquido_pts
        self._posicao = EstadoPosicao.SEM_POSICAO
        self._preco_entrada = 0.0

        # Registrar vitória real (trade fechado com lucro)
        if pnl_liquido_pts > 0:
            self._n_vitorias += 1

        # Recompensa proporcional ao P&L (com normalização para aprendizado)
        return float(np.tanh(pnl_liquido_pts / 100.0) * 10.0)

    # ------------------------------------------------------------------
    # Controle de término do episódio
    # ------------------------------------------------------------------

    def _verificar_termino(self) -> bool:
        """Verifica se o episódio deve ser encerrado."""
        if self._indice >= len(self.dados) - 1:
            return True
        if self._pnl_dia_pts <= -self.config.limite_perda_pts:
            return True
        if self._pnl_dia_pts >= self.config.meta_ganho_pts:
            return True
        if self._n_trades >= self.config.max_trades_por_dia:
            if self._posicao == EstadoPosicao.SEM_POSICAO:
                return True
        return False

    def _motivo_termino(self) -> str:
        """Retorna o motivo do término do episódio."""
        if self._indice >= len(self.dados) - 1:
            return "dados_esgotados"
        if self._pnl_dia_pts <= -self.config.limite_perda_pts:
            return "stop_loss_diario"
        if self._pnl_dia_pts >= self.config.meta_ganho_pts:
            return "meta_atingida"
        if self._n_trades >= self.config.max_trades_por_dia:
            return "limite_trades"
        return "em_andamento"

    # ------------------------------------------------------------------
    # Validação
    # ------------------------------------------------------------------

    @staticmethod
    def _validar_dados(dados: pd.DataFrame) -> None:
        """Valida que o DataFrame contém as colunas necessárias."""
        colunas_requeridas = {"open", "high", "low", "close", "volume"}
        colunas_presentes = set(dados.columns.str.lower())
        faltando = colunas_requeridas - colunas_presentes
        if faltando:
            raise ValueError(
                f"DataFrame faltando colunas obrigatórias: {faltando}"
            )
        if len(dados) < 25:
            raise ValueError(
                "DataFrame deve ter pelo menos 25 linhas para o cálculo "
                "das features (janela mínima de observação)."
            )
