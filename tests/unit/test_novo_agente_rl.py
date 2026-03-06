"""Testes unitários do Novo Agente RL para Day Trade de Mini Índice.

Cobre as três classes principais:
    - AmbienteTradingMiniIndice
    - AgenteQLearningMiniIndice
    - PipelineTreinamentoRL

Os testes usam dados sintéticos e não requerem MT5 ou GPU.
"""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(ROOT))

from src.application.services.novo_agente.ambiente_trading import (
    AcaoTrading,
    AmbienteTradingMiniIndice,
    ConfiguracaoAmbiente,
    EstadoPosicao,
)
from src.application.services.novo_agente.agente_q_learning import (
    AgenteQLearningMiniIndice,
    ConfiguracaoAgente,
)
from src.application.services.novo_agente.pipeline_treinamento import (
    PipelineTreinamentoRL,
    ResultadoEpisodio,
    RelatorioTreinamento,
    gerar_dados_sinteticos,
)


# ---------------------------------------------------------------------------
# Fixtures compartilhadas
# ---------------------------------------------------------------------------


@pytest.fixture()
def dados_sinteticos_minimos() -> pd.DataFrame:
    """DataFrame OHLCV sintético com 50 candles (mínimo para testes)."""
    return gerar_dados_sinteticos(n_candles=50, semente=0)


@pytest.fixture()
def dados_sinteticos_treino() -> pd.DataFrame:
    """DataFrame OHLCV sintético com 300 candles para treinamento."""
    return gerar_dados_sinteticos(n_candles=300, semente=42)


@pytest.fixture()
def config_ambiente_padrao() -> ConfiguracaoAmbiente:
    """Configuração padrão do ambiente de trading."""
    return ConfiguracaoAmbiente(
        limite_perda_diaria_brl=250.0,
        meta_ganho_diaria_brl=100.0,
        ponto_valor_brl=0.20,
        custo_operacao_pts=25.0,
        janela_observacao=20,
        max_trades_por_dia=10,
    )


@pytest.fixture()
def config_agente_rapido() -> ConfiguracaoAgente:
    """Configuração de agente com parâmetros menores para testes rápidos."""
    return ConfiguracaoAgente(
        taxa_aprendizado=0.01,
        fator_desconto=0.95,
        epsilon_inicial=1.0,
        epsilon_minimo=0.1,
        taxa_decaimento_epsilon=0.9,
        camadas_ocultas=(16, 8),
        tamanho_buffer=200,
        tamanho_mini_lote=32,
        min_experiencias_treino=50,
        frequencia_atualizacao=2,
    )


@pytest.fixture()
def ambiente(
    dados_sinteticos_minimos: pd.DataFrame,
    config_ambiente_padrao: ConfiguracaoAmbiente,
) -> AmbienteTradingMiniIndice:
    """Instância do ambiente de trading para testes."""
    return AmbienteTradingMiniIndice(
        dados=dados_sinteticos_minimos,
        config=config_ambiente_padrao,
        semente=0,
    )


@pytest.fixture()
def agente(
    ambiente: AmbienteTradingMiniIndice,
    config_agente_rapido: ConfiguracaoAgente,
) -> AgenteQLearningMiniIndice:
    """Instância do agente Q-Learning para testes."""
    return AgenteQLearningMiniIndice(
        tamanho_estado=ambiente.tamanho_estado,
        n_acoes=ambiente.n_acoes,
        config=config_agente_rapido,
        semente=0,
    )


# ---------------------------------------------------------------------------
# Testes de ConfiguracaoAmbiente
# ---------------------------------------------------------------------------


class TestConfiguracaoAmbiente:
    """Testes das propriedades derivadas da configuração do ambiente."""

    def test_limite_perda_pts_calculado_corretamente(
        self, config_ambiente_padrao: ConfiguracaoAmbiente
    ) -> None:
        """Limite em pontos deve ser brl / valor_ponto."""
        assert config_ambiente_padrao.limite_perda_pts == pytest.approx(
            250.0 / 0.20
        )

    def test_meta_ganho_pts_calculada_corretamente(
        self, config_ambiente_padrao: ConfiguracaoAmbiente
    ) -> None:
        """Meta em pontos deve ser brl / valor_ponto."""
        assert config_ambiente_padrao.meta_ganho_pts == pytest.approx(
            100.0 / 0.20
        )

    def test_configuracao_e_imutavel(
        self, config_ambiente_padrao: ConfiguracaoAmbiente
    ) -> None:
        """ConfiguracaoAmbiente deve ser frozen (imutável)."""
        import dataclasses

        with pytest.raises(dataclasses.FrozenInstanceError):
            config_ambiente_padrao.limite_perda_diaria_brl = 500.0  # type: ignore[misc]


# ---------------------------------------------------------------------------
# Testes de AcaoTrading e EstadoPosicao
# ---------------------------------------------------------------------------


class TestEnumsTrading:
    """Testes dos enumeradores de ação e posição."""

    def test_acao_trading_tem_tres_valores(self) -> None:
        """AcaoTrading deve ter exatamente 3 ações."""
        assert len(AcaoTrading) == 3

    def test_acoes_trading_valores_corretos(self) -> None:
        """Valores numéricos das ações devem ser 0, 1, 2."""
        assert AcaoTrading.HOLD == 0
        assert AcaoTrading.COMPRAR == 1
        assert AcaoTrading.VENDER == 2

    def test_estado_posicao_tem_tres_valores(self) -> None:
        """EstadoPosicao deve ter 3 estados."""
        assert len(EstadoPosicao) == 3

    def test_estado_posicao_valores_corretos(self) -> None:
        """Long = 1, Short = -1, Sem posição = 0."""
        assert EstadoPosicao.LONG == 1
        assert EstadoPosicao.SHORT == -1
        assert EstadoPosicao.SEM_POSICAO == 0


# ---------------------------------------------------------------------------
# Testes de AmbienteTradingMiniIndice
# ---------------------------------------------------------------------------


class TestAmbienteTradingValidacao:
    """Testes de validação dos dados de entrada do ambiente."""

    def test_dados_sem_colunas_obrigatorias_levanta_erro(self) -> None:
        """Deve lançar ValueError se colunas obrigatórias faltarem."""
        df_invalido = pd.DataFrame(
            {"preco": [100, 101, 102], "volume": [1000, 1000, 1000]}
        )
        with pytest.raises(ValueError, match="colunas obrigatórias"):
            AmbienteTradingMiniIndice(dados=df_invalido)

    def test_dados_com_menos_de_25_linhas_levanta_erro(self) -> None:
        """Deve lançar ValueError se dados insuficientes."""
        df_pequeno = pd.DataFrame(
            {
                "open": [100.0] * 10,
                "high": [101.0] * 10,
                "low": [99.0] * 10,
                "close": [100.5] * 10,
                "volume": [1000.0] * 10,
            }
        )
        with pytest.raises(ValueError, match="25 linhas"):
            AmbienteTradingMiniIndice(dados=df_pequeno)

    def test_dados_validos_cria_ambiente_sem_erro(
        self, dados_sinteticos_minimos: pd.DataFrame
    ) -> None:
        """Dados válidos devem criar ambiente sem exceção."""
        ambiente = AmbienteTradingMiniIndice(
            dados=dados_sinteticos_minimos
        )
        assert ambiente is not None


class TestAmbienteTradingReset:
    """Testes do método reset do ambiente."""

    def test_reset_retorna_array_numpy(
        self, ambiente: AmbienteTradingMiniIndice
    ) -> None:
        """reset() deve retornar array numpy."""
        estado = ambiente.reset()
        assert isinstance(estado, np.ndarray)

    def test_reset_retorna_estado_com_n_features(
        self, ambiente: AmbienteTradingMiniIndice
    ) -> None:
        """Estado retornado deve ter tamanho correto."""
        estado = ambiente.reset()
        assert estado.shape == (AmbienteTradingMiniIndice.N_FEATURES,)

    def test_reset_estado_valores_em_range_valido(
        self, ambiente: AmbienteTradingMiniIndice
    ) -> None:
        """Valores do estado devem estar em [-2, 2]."""
        estado = ambiente.reset()
        assert np.all(estado >= -2.0)
        assert np.all(estado <= 2.0)

    def test_reset_posicao_inicial_sem_posicao(
        self, ambiente: AmbienteTradingMiniIndice
    ) -> None:
        """Após reset, posição deve ser SEM_POSICAO."""
        ambiente.reset()
        assert ambiente._posicao == EstadoPosicao.SEM_POSICAO

    def test_reset_pnl_inicial_zero(
        self, ambiente: AmbienteTradingMiniIndice
    ) -> None:
        """Após reset, P&L deve ser zero."""
        ambiente.reset()
        assert ambiente._pnl_dia_pts == 0.0

    def test_reset_n_trades_inicial_zero(
        self, ambiente: AmbienteTradingMiniIndice
    ) -> None:
        """Após reset, número de trades deve ser zero."""
        ambiente.reset()
        assert ambiente._n_trades == 0


class TestAmbienteTradingStep:
    """Testes do método step do ambiente."""

    def test_step_retorna_tupla_correta(
        self, ambiente: AmbienteTradingMiniIndice
    ) -> None:
        """step() deve retornar (estado, recompensa, terminado, info)."""
        ambiente.reset()
        resultado = ambiente.step(AcaoTrading.HOLD)
        assert len(resultado) == 4
        estado, recompensa, terminado, info = resultado
        assert isinstance(estado, np.ndarray)
        assert isinstance(recompensa, float)
        assert isinstance(terminado, bool)
        assert isinstance(info, dict)

    def test_step_hold_nao_abre_posicao(
        self, ambiente: AmbienteTradingMiniIndice
    ) -> None:
        """Ação HOLD não deve abrir posição."""
        ambiente.reset()
        ambiente.step(AcaoTrading.HOLD)
        assert ambiente._posicao == EstadoPosicao.SEM_POSICAO

    def test_step_comprar_abre_long(
        self, ambiente: AmbienteTradingMiniIndice
    ) -> None:
        """Ação COMPRAR deve abrir posição LONG."""
        ambiente.reset()
        ambiente.step(AcaoTrading.COMPRAR)
        assert ambiente._posicao == EstadoPosicao.LONG

    def test_step_vender_abre_short(
        self, ambiente: AmbienteTradingMiniIndice
    ) -> None:
        """Ação VENDER deve abrir posição SHORT."""
        ambiente.reset()
        ambiente.step(AcaoTrading.VENDER)
        assert ambiente._posicao == EstadoPosicao.SHORT

    def test_step_vender_fecha_long(
        self, ambiente: AmbienteTradingMiniIndice
    ) -> None:
        """Ação VENDER em posição LONG deve fechar a posição."""
        ambiente.reset()
        ambiente.step(AcaoTrading.COMPRAR)  # abre LONG
        assert ambiente._posicao == EstadoPosicao.LONG
        ambiente.step(AcaoTrading.VENDER)  # fecha LONG
        assert ambiente._posicao == EstadoPosicao.SEM_POSICAO

    def test_step_comprar_fecha_short(
        self, ambiente: AmbienteTradingMiniIndice
    ) -> None:
        """Ação COMPRAR em posição SHORT deve fechar a posição."""
        ambiente.reset()
        ambiente.step(AcaoTrading.VENDER)  # abre SHORT
        assert ambiente._posicao == EstadoPosicao.SHORT
        ambiente.step(AcaoTrading.COMPRAR)  # fecha SHORT
        assert ambiente._posicao == EstadoPosicao.SEM_POSICAO

    def test_step_apos_termino_levanta_erro(
        self, ambiente: AmbienteTradingMiniIndice
    ) -> None:
        """step() após episódio terminado deve lançar RuntimeError."""
        ambiente.reset()
        # Simular término forçando índice ao fim
        ambiente._terminado = True
        with pytest.raises(RuntimeError, match="Episódio encerrado"):
            ambiente.step(AcaoTrading.HOLD)

    def test_step_info_contem_campos_obrigatorios(
        self, ambiente: AmbienteTradingMiniIndice
    ) -> None:
        """info retornado pelo step deve conter campos obrigatórios."""
        ambiente.reset()
        _, _, _, info = ambiente.step(AcaoTrading.HOLD)
        assert "acao" in info
        assert "posicao" in info
        assert "preco" in info
        assert "pnl_dia_pts" in info


class TestAmbienteTradingTermino:
    """Testes das condições de término de episódio."""

    def test_termina_ao_esgotar_dados(
        self, ambiente: AmbienteTradingMiniIndice
    ) -> None:
        """Episódio deve terminar quando dados se esgotam."""
        estado = ambiente.reset()
        terminado = False
        for _ in range(1000):
            _, _, terminado, _ = ambiente.step(AcaoTrading.HOLD)
            if terminado:
                break
        assert terminado

    def test_pnl_atual_brl_correto(
        self, ambiente: AmbienteTradingMiniIndice
    ) -> None:
        """pnl_atual_brl deve ser pnl_pts * valor_ponto."""
        ambiente.reset()
        ambiente._pnl_dia_pts = 100.0
        assert ambiente.pnl_atual_brl == pytest.approx(
            100.0 * 0.20
        )

    def test_tamanho_estado_correto(
        self, ambiente: AmbienteTradingMiniIndice
    ) -> None:
        """tamanho_estado deve ser N_FEATURES."""
        assert ambiente.tamanho_estado == AmbienteTradingMiniIndice.N_FEATURES

    def test_n_acoes_correto(
        self, ambiente: AmbienteTradingMiniIndice
    ) -> None:
        """n_acoes deve ser 3 (HOLD, COMPRAR, VENDER)."""
        assert ambiente.n_acoes == 3


# ---------------------------------------------------------------------------
# Testes de AgenteQLearningMiniIndice
# ---------------------------------------------------------------------------


class TestAgenteQLearningInicializacao:
    """Testes de inicialização do agente Q-Learning."""

    def test_epsilon_inicial_correto(
        self, agente: AgenteQLearningMiniIndice
    ) -> None:
        """Epsilon inicial deve ser 1.0 (exploração total)."""
        assert agente.epsilon == pytest.approx(1.0)

    def test_n_passos_inicial_zero(
        self, agente: AgenteQLearningMiniIndice
    ) -> None:
        """Número de passos inicial deve ser zero."""
        assert agente.n_passos == 0

    def test_n_episodios_inicial_zero(
        self, agente: AgenteQLearningMiniIndice
    ) -> None:
        """Número de episódios inicial deve ser zero."""
        assert agente.n_episodios == 0

    def test_buffer_inicial_vazio(
        self, agente: AgenteQLearningMiniIndice
    ) -> None:
        """Buffer de experiências deve estar vazio inicialmente."""
        assert len(agente._buffer) == 0


class TestAgenteQLearningSelecaoAcao:
    """Testes de seleção de ação do agente."""

    def test_selecionar_acao_retorna_inteiro_valido(
        self,
        agente: AgenteQLearningMiniIndice,
        ambiente: AmbienteTradingMiniIndice,
    ) -> None:
        """Ação selecionada deve estar no range válido."""
        estado = ambiente.reset()
        acao = agente.selecionar_acao(estado)
        assert 0 <= acao < agente.n_acoes

    def test_exploracao_aleatoria_com_epsilon_maximo(
        self,
        agente: AgenteQLearningMiniIndice,
        ambiente: AmbienteTradingMiniIndice,
    ) -> None:
        """Com epsilon=1.0, todas as ações devem ocorrer aleatoriamente."""
        agente.epsilon = 1.0
        estado = ambiente.reset()
        acoes = {agente.selecionar_acao(estado) for _ in range(200)}
        # Com 200 tentativas e 3 ações, deve aparecer pelo menos 2
        assert len(acoes) >= 2

    def test_acao_sem_modelo_inicializado_e_aleatoria(
        self,
        agente: AgenteQLearningMiniIndice,
        ambiente: AmbienteTradingMiniIndice,
    ) -> None:
        """Sem modelo treinado e epsilon=0, deve retornar ação válida."""
        agente.epsilon = 0.0
        agente._modelo_inicializado = False
        estado = ambiente.reset()
        acao = agente.selecionar_acao(estado)
        assert 0 <= acao < agente.n_acoes


class TestAgenteQLearningMemorizar:
    """Testes do armazenamento de experiências."""

    def test_memorizar_adiciona_ao_buffer(
        self,
        agente: AgenteQLearningMiniIndice,
        ambiente: AmbienteTradingMiniIndice,
    ) -> None:
        """memorizar() deve adicionar experiência ao buffer."""
        estado = ambiente.reset()
        proximo, _, _, _ = ambiente.step(AcaoTrading.HOLD)
        agente.memorizar(estado, 0, 1.0, proximo, False)
        assert len(agente._buffer) == 1

    def test_n_passos_incrementa_ao_memorizar(
        self,
        agente: AgenteQLearningMiniIndice,
        ambiente: AmbienteTradingMiniIndice,
    ) -> None:
        """n_passos deve incrementar a cada memorização."""
        estado = ambiente.reset()
        proximo, _, _, _ = ambiente.step(AcaoTrading.HOLD)
        agente.memorizar(estado, 0, 0.0, proximo, False)
        assert agente.n_passos == 1

    def test_buffer_respeita_tamanho_maximo(
        self, config_agente_rapido: ConfiguracaoAgente
    ) -> None:
        """Buffer não deve exceder tamanho máximo configurado."""
        config = ConfiguracaoAgente(
            tamanho_buffer=10,
            min_experiencias_treino=5,
        )
        agente = AgenteQLearningMiniIndice(
            tamanho_estado=5, n_acoes=3, config=config
        )
        estado = np.zeros(5)
        for i in range(20):
            agente.memorizar(estado, 0, 0.0, estado, False)
        assert len(agente._buffer) <= 10


class TestAgenteQLearningAprendizado:
    """Testes do ciclo de aprendizado do agente."""

    def test_aprender_retorna_none_com_buffer_insuficiente(
        self, agente: AgenteQLearningMiniIndice
    ) -> None:
        """aprender() deve retornar None se buffer insuficiente."""
        assert len(agente._buffer) < agente.config.min_experiencias_treino
        resultado = agente.aprender()
        assert resultado is None

    def test_encerrar_episodio_reduz_epsilon(
        self, agente: AgenteQLearningMiniIndice
    ) -> None:
        """encerrar_episodio() deve reduzir epsilon."""
        epsilon_antes = agente.epsilon
        agente.encerrar_episodio()
        assert agente.epsilon <= epsilon_antes

    def test_epsilon_nao_cai_abaixo_minimo(
        self, agente: AgenteQLearningMiniIndice
    ) -> None:
        """Epsilon não deve cair abaixo do mínimo configurado."""
        for _ in range(10000):
            agente.encerrar_episodio()
        assert agente.epsilon >= agente.config.epsilon_minimo

    def test_n_episodios_incrementa_ao_encerrar(
        self, agente: AgenteQLearningMiniIndice
    ) -> None:
        """n_episodios deve incrementar a cada encerramento."""
        agente.encerrar_episodio()
        agente.encerrar_episodio()
        assert agente.n_episodios == 2


class TestAgenteQLearningPersistencia:
    """Testes de salvar e carregar modelo."""

    def test_salvar_e_carregar_modelo(
        self,
        agente: AgenteQLearningMiniIndice,
        tmp_path: Path,
    ) -> None:
        """Modelo salvo deve ser carregável com mesmos metadados."""
        agente.encerrar_episodio()
        agente.encerrar_episodio()

        agente.salvar(tmp_path / "modelo_teste")

        agente2 = AgenteQLearningMiniIndice(
            tamanho_estado=agente.tamanho_estado,
            n_acoes=agente.n_acoes,
        )
        agente2.carregar(tmp_path / "modelo_teste")

        assert agente2.n_episodios == agente.n_episodios
        assert agente2.epsilon == pytest.approx(agente.epsilon)

    def test_salvar_cria_arquivos_necessarios(
        self,
        agente: AgenteQLearningMiniIndice,
        tmp_path: Path,
    ) -> None:
        """salvar() deve criar q_network.pkl e metadados.json."""
        caminho = tmp_path / "modelo"
        agente.salvar(caminho)
        assert (caminho / "q_network.pkl").exists()
        assert (caminho / "metadados.json").exists()


# ---------------------------------------------------------------------------
# Testes de ResultadoEpisodio
# ---------------------------------------------------------------------------


class TestResultadoEpisodio:
    """Testes das propriedades de ResultadoEpisodio."""

    def test_taxa_acerto_com_trades(self) -> None:
        """taxa_acerto deve ser n_vitorias / n_trades."""
        resultado = ResultadoEpisodio(
            episodio=1,
            pnl_pts=100.0,
            pnl_brl=20.0,
            n_trades=4,
            n_vitorias=3,
            epsilon=0.1,
            motivo_termino="dados_esgotados",
            recompensa_total=5.0,
        )
        assert resultado.taxa_acerto == pytest.approx(0.75)

    def test_taxa_acerto_sem_trades(self) -> None:
        """taxa_acerto sem trades deve retornar zero."""
        resultado = ResultadoEpisodio(
            episodio=1,
            pnl_pts=0.0,
            pnl_brl=0.0,
            n_trades=0,
            n_vitorias=0,
            epsilon=0.5,
            motivo_termino="dados_esgotados",
            recompensa_total=0.0,
        )
        assert resultado.taxa_acerto == 0.0

    def test_meta_atingida_verdadeiro(self) -> None:
        """meta_atingida deve ser True quando motivo for meta_atingida."""
        resultado = ResultadoEpisodio(
            episodio=1,
            pnl_pts=500.0,
            pnl_brl=100.0,
            n_trades=2,
            n_vitorias=2,
            epsilon=0.1,
            motivo_termino="meta_atingida",
            recompensa_total=10.0,
        )
        assert resultado.meta_atingida is True

    def test_stop_acionado_verdadeiro(self) -> None:
        """stop_acionado deve ser True quando motivo for stop_loss_diario."""
        resultado = ResultadoEpisodio(
            episodio=1,
            pnl_pts=-1250.0,
            pnl_brl=-250.0,
            n_trades=5,
            n_vitorias=1,
            epsilon=0.3,
            motivo_termino="stop_loss_diario",
            recompensa_total=-20.0,
        )
        assert resultado.stop_acionado is True


# ---------------------------------------------------------------------------
# Testes de gerar_dados_sinteticos
# ---------------------------------------------------------------------------


class TestGerarDadosSinteticos:
    """Testes da função de geração de dados sintéticos."""

    def test_retorna_dataframe_com_colunas_corretas(self) -> None:
        """Deve retornar DataFrame com colunas OHLCV."""
        df = gerar_dados_sinteticos(n_candles=50)
        assert set(df.columns) >= {"open", "high", "low", "close", "volume"}

    def test_retorna_numero_correto_de_candles(self) -> None:
        """Deve retornar exatamente n_candles linhas."""
        df = gerar_dados_sinteticos(n_candles=100)
        assert len(df) == 100

    def test_high_sempre_maior_igual_low(self) -> None:
        """Máxima deve ser sempre >= mínima em todos os candles."""
        df = gerar_dados_sinteticos(n_candles=200)
        assert (df["high"] >= df["low"]).all()

    def test_reproducibilidade_com_mesma_semente(self) -> None:
        """Mesma semente deve gerar dados idênticos."""
        df1 = gerar_dados_sinteticos(n_candles=50, semente=42)
        df2 = gerar_dados_sinteticos(n_candles=50, semente=42)
        pd.testing.assert_frame_equal(df1, df2)

    def test_sementes_diferentes_geram_dados_distintos(self) -> None:
        """Sementes diferentes devem gerar dados distintos."""
        df1 = gerar_dados_sinteticos(n_candles=50, semente=1)
        df2 = gerar_dados_sinteticos(n_candles=50, semente=2)
        assert not df1["close"].equals(df2["close"])

    def test_volumes_positivos(self) -> None:
        """Todos os volumes devem ser positivos."""
        df = gerar_dados_sinteticos(n_candles=100)
        assert (df["volume"] > 0).all()


# ---------------------------------------------------------------------------
# Testes de PipelineTreinamentoRL
# ---------------------------------------------------------------------------


class TestPipelineTreinamentoRL:
    """Testes do pipeline de treinamento completo."""

    def test_treinar_retorna_relatorio(
        self,
        dados_sinteticos_treino: pd.DataFrame,
        config_ambiente_padrao: ConfiguracaoAmbiente,
        config_agente_rapido: ConfiguracaoAgente,
    ) -> None:
        """treinar() deve retornar RelatorioTreinamento."""
        pipeline = PipelineTreinamentoRL(
            config_ambiente=config_ambiente_padrao,
            config_agente=config_agente_rapido,
            semente=42,
        )
        relatorio = pipeline.treinar(
            dados=dados_sinteticos_treino,
            n_episodios=5,
        )
        assert isinstance(relatorio, RelatorioTreinamento)

    def test_relatorio_tem_numero_correto_de_episodios(
        self,
        dados_sinteticos_treino: pd.DataFrame,
        config_ambiente_padrao: ConfiguracaoAmbiente,
        config_agente_rapido: ConfiguracaoAgente,
    ) -> None:
        """Relatório deve registrar o número correto de episódios."""
        pipeline = PipelineTreinamentoRL(
            config_ambiente=config_ambiente_padrao,
            config_agente=config_agente_rapido,
        )
        relatorio = pipeline.treinar(
            dados=dados_sinteticos_treino,
            n_episodios=3,
        )
        assert relatorio.n_episodios_treino == 3
        assert len(relatorio.episodios_treino) == 3

    def test_avaliar_sem_treino_levanta_erro(
        self,
        dados_sinteticos_treino: pd.DataFrame,
    ) -> None:
        """avaliar() sem treino deve lançar RuntimeError."""
        pipeline = PipelineTreinamentoRL()
        with pytest.raises(RuntimeError, match="Agente não treinado"):
            pipeline.avaliar(dados=dados_sinteticos_treino)

    def test_avaliar_retorna_lista_de_resultados(
        self,
        dados_sinteticos_treino: pd.DataFrame,
        config_ambiente_padrao: ConfiguracaoAmbiente,
        config_agente_rapido: ConfiguracaoAgente,
    ) -> None:
        """avaliar() deve retornar lista de ResultadoEpisodio."""
        pipeline = PipelineTreinamentoRL(
            config_ambiente=config_ambiente_padrao,
            config_agente=config_agente_rapido,
        )
        pipeline.treinar(dados=dados_sinteticos_treino, n_episodios=3)
        resultados = pipeline.avaliar(
            dados=dados_sinteticos_treino, n_episodios=2
        )
        assert len(resultados) == 2
        assert all(
            isinstance(r, ResultadoEpisodio) for r in resultados
        )

    def test_salvar_e_carregar_modelo_pipeline(
        self,
        dados_sinteticos_treino: pd.DataFrame,
        config_ambiente_padrao: ConfiguracaoAmbiente,
        config_agente_rapido: ConfiguracaoAgente,
        tmp_path: Path,
    ) -> None:
        """Pipeline deve salvar e carregar modelo sem erro."""
        pipeline = PipelineTreinamentoRL(
            config_ambiente=config_ambiente_padrao,
            config_agente=config_agente_rapido,
            diretorio_modelos=tmp_path / "modelos",
        )
        pipeline.treinar(dados=dados_sinteticos_treino, n_episodios=3)
        caminho = pipeline.salvar_modelo("teste_modelo")
        assert caminho.exists()

        pipeline2 = PipelineTreinamentoRL(
            config_ambiente=config_ambiente_padrao,
            config_agente=config_agente_rapido,
            diretorio_modelos=tmp_path / "modelos",
        )
        pipeline2.carregar_modelo("teste_modelo")
        assert pipeline2._agente is not None

    def test_relatorio_para_dict_campos_obrigatorios(
        self,
        dados_sinteticos_treino: pd.DataFrame,
        config_ambiente_padrao: ConfiguracaoAmbiente,
        config_agente_rapido: ConfiguracaoAgente,
    ) -> None:
        """para_dict() do relatório deve ter campos obrigatórios."""
        pipeline = PipelineTreinamentoRL(
            config_ambiente=config_ambiente_padrao,
            config_agente=config_agente_rapido,
        )
        relatorio = pipeline.treinar(
            dados=dados_sinteticos_treino,
            n_episodios=3,
        )
        dados = relatorio.para_dict()
        assert "timestamp_inicio" in dados
        assert "timestamp_fim" in dados
        assert "n_episodios_treino" in dados
        assert "config_ambiente" in dados
        assert "config_agente" in dados
        assert "metricas_treino" in dados
