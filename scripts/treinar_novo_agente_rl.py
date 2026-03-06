"""Treinamento do Novo Agente RL para Day Trade de Mini Índice.

Script principal para treinar o agente de Reinforcement Learning.
O agente aprende estratégias de trade de forma completamente autônoma,
sem nenhuma estratégia pré-definida.

Configuração financeira:
    - Instrumento: Mini Índice (WIN$N)
    - 1 mini contrato por operação
    - Limite de perda diária: R$250,00
    - Meta de ganho diário: R$100,00

Uso:
    # Treinar com dados sintéticos (modo desenvolvimento)
    python scripts/treinar_novo_agente_rl.py

    # Treinar com número de episódios customizado
    python scripts/treinar_novo_agente_rl.py --episodios 1000

    # Treinar com dados reais do MT5
    python scripts/treinar_novo_agente_rl.py --dados-reais

    # Avaliar modelo já treinado
    python scripts/treinar_novo_agente_rl.py --apenas-avaliar
"""

from __future__ import annotations

import argparse
import json
import logging
import sys
from pathlib import Path
from typing import Optional

import numpy as np
import pandas as pd

ROOT_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT_DIR))

from src.application.services.novo_agente.pipeline_treinamento import (
    PipelineTreinamentoRL,
    gerar_dados_sinteticos,
    DIRETORIO_MODELOS,
)
from src.application.services.novo_agente.ambiente_trading import (
    ConfiguracaoAmbiente,
)
from src.application.services.novo_agente.agente_q_learning import (
    ConfiguracaoAgente,
)

# Configuração de logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Configurações do modelo
# ---------------------------------------------------------------------------

CONFIG_AMBIENTE = ConfiguracaoAmbiente(
    limite_perda_diaria_brl=250.0,
    meta_ganho_diaria_brl=100.0,
    ponto_valor_brl=0.20,
    custo_operacao_pts=25.0,
    janela_observacao=20,
    max_trades_por_dia=10,
    penalidade_stop_loss=-50.0,
    bonus_meta_atingida=30.0,
)

CONFIG_AGENTE = ConfiguracaoAgente(
    taxa_aprendizado=0.001,
    fator_desconto=0.95,
    epsilon_inicial=1.0,
    epsilon_minimo=0.05,
    taxa_decaimento_epsilon=0.995,
    camadas_ocultas=(128, 64, 32),
    tamanho_buffer=10_000,
    tamanho_mini_lote=64,
    min_experiencias_treino=256,
    frequencia_atualizacao=4,
)


# ---------------------------------------------------------------------------
# Carregamento de dados
# ---------------------------------------------------------------------------


def carregar_dados_mt5(simbolo: str = "WIN$N") -> Optional[pd.DataFrame]:
    """Tenta carregar dados históricos reais do MT5.

    Args:
        simbolo: Símbolo do Mini Índice no MT5

    Returns:
        DataFrame OHLCV ou None se MT5 não disponível
    """
    try:
        import MetaTrader5 as mt5

        if not mt5.initialize():
            logger.warning(
                "MT5 não disponível. Usando dados sintéticos."
            )
            return None

        # Carrega últimos 5000 candles de 5 minutos
        barras = mt5.copy_rates_from_pos(
            simbolo, mt5.TIMEFRAME_M5, 0, 5000
        )
        mt5.shutdown()

        if barras is None or len(barras) == 0:
            logger.warning(
                "Sem dados para %s. Usando dados sintéticos.", simbolo
            )
            return None

        df = pd.DataFrame(barras)
        df = df.rename(
            columns={
                "open": "open",
                "high": "high",
                "low": "low",
                "close": "close",
                "tick_volume": "volume",
            }
        )
        logger.info(
            "Dados MT5 carregados: %d candles de %s", len(df), simbolo
        )
        return df[["open", "high", "low", "close", "volume"]]

    except ImportError:
        logger.warning(
            "MetaTrader5 não instalado. Usando dados sintéticos."
        )
        return None
    except Exception as exc:
        logger.warning(
            "Erro ao carregar dados MT5: %s. Usando sintéticos.", exc
        )
        return None


# ---------------------------------------------------------------------------
# Funções principais
# ---------------------------------------------------------------------------


def executar_treinamento(
    n_episodios: int = 500,
    usar_dados_reais: bool = False,
    nome_modelo: str = "modelo_final",
    semente: int = 42,
) -> None:
    """Executa o treinamento completo do agente RL.

    Args:
        n_episodios: Número de episódios de treinamento
        usar_dados_reais: Se True, tenta usar dados do MT5
        nome_modelo: Nome para salvar o modelo treinado
        semente: Semente aleatória
    """
    import pandas as pd

    logger.info("=" * 60)
    logger.info("NOVO AGENTE RL - MINI ÍNDICE DAY TRADE")
    logger.info("=" * 60)
    logger.info(
        "Configuração: R$%.0f perda máx | R$%.0f meta",
        CONFIG_AMBIENTE.limite_perda_diaria_brl,
        CONFIG_AMBIENTE.meta_ganho_diaria_brl,
    )
    logger.info("Episódios: %d | Semente: %d", n_episodios, semente)
    logger.info("-" * 60)

    # Carregar dados
    dados = None
    if usar_dados_reais:
        dados = carregar_dados_mt5()

    if dados is None:
        logger.info(
            "Gerando dados sintéticos para treinamento..."
        )
        dados = gerar_dados_sinteticos(
            n_candles=2000, semente=semente
        )

    logger.info("Total de candles: %d", len(dados))
    logger.info("-" * 60)

    # Criar pipeline e treinar
    pipeline = PipelineTreinamentoRL(
        config_ambiente=CONFIG_AMBIENTE,
        config_agente=CONFIG_AGENTE,
        semente=semente,
    )

    relatorio = pipeline.treinar(
        dados=dados,
        n_episodios=n_episodios,
        log_frequencia=max(1, n_episodios // 10),
    )

    # Avaliar o modelo treinado
    logger.info("-" * 60)
    logger.info("Avaliando o modelo treinado...")

    dados_avaliacao = gerar_dados_sinteticos(
        n_candles=1000, semente=semente + 999
    )
    resultados_aval = pipeline.avaliar(
        dados=dados_avaliacao,
        n_episodios=50,
    )

    # Exibir resumo
    logger.info("=" * 60)
    logger.info("RESUMO DO TREINAMENTO")
    logger.info("=" * 60)
    logger.info(
        "P&L médio (treino):     R$%.2f",
        relatorio.pnl_medio_treino,
    )
    logger.info(
        "P&L médio (avaliação):  R$%.2f",
        relatorio.pnl_medio_avaliacao,
    )
    logger.info(
        "Taxa meta (treino):     %.1f%%",
        relatorio.taxa_meta_treino * 100,
    )
    logger.info(
        "Taxa meta (avaliação):  %.1f%%",
        relatorio.taxa_meta_avaliacao * 100,
    )
    logger.info(
        "Taxa stop (avaliação):  %.1f%%",
        relatorio.taxa_stop_avaliacao * 100,
    )
    logger.info("-" * 60)

    # Salvar modelo
    caminho_modelo = pipeline.salvar_modelo(nome_modelo)
    logger.info("Modelo salvo em: %s", caminho_modelo)

    # Salvar relatório completo nos outputs
    Path("outputs").mkdir(exist_ok=True)
    relatorio_path = (
        Path("outputs") / "novo_agente_rl_relatorio.json"
    )
    with open(relatorio_path, "w", encoding="utf-8") as f:
        json.dump(relatorio.para_dict(), f, indent=2, ensure_ascii=False)
    logger.info("Relatório salvo em: %s", relatorio_path)

    logger.info("=" * 60)
    logger.info("TREINAMENTO CONCLUÍDO")
    logger.info("=" * 60)


def executar_avaliacao(nome_modelo: str = "modelo_final") -> None:
    """Avalia um modelo previamente treinado.

    Args:
        nome_modelo: Nome do modelo a avaliar
    """
    logger.info("=" * 60)
    logger.info("AVALIAÇÃO DO AGENTE RL")
    logger.info("=" * 60)

    pipeline = PipelineTreinamentoRL(
        config_ambiente=CONFIG_AMBIENTE,
        config_agente=CONFIG_AGENTE,
    )

    try:
        pipeline.carregar_modelo(nome_modelo)
    except FileNotFoundError:
        logger.error(
            "Modelo '%s' não encontrado. Execute o treinamento primeiro.",
            nome_modelo,
        )
        return

    dados = gerar_dados_sinteticos(n_candles=1000)
    resultados = pipeline.avaliar(dados=dados, n_episodios=100)

    pnl_medio = np.mean([r.pnl_brl for r in resultados])
    taxa_meta = np.mean([r.meta_atingida for r in resultados])
    taxa_stop = np.mean([r.stop_acionado for r in resultados])

    logger.info("P&L médio:     R$%.2f", pnl_medio)
    logger.info("Taxa meta:     %.1f%%", taxa_meta * 100)
    logger.info("Taxa stop:     %.1f%%", taxa_stop * 100)


# ---------------------------------------------------------------------------
# Ponto de entrada
# ---------------------------------------------------------------------------


def _parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    """Analisa argumentos da linha de comando."""
    parser = argparse.ArgumentParser(
        description=(
            "Treinamento do Novo Agente RL para Day Trade "
            "de Mini Índice"
        )
    )
    parser.add_argument(
        "--episodios",
        type=int,
        default=500,
        help="Número de episódios de treinamento (default: 500)",
    )
    parser.add_argument(
        "--dados-reais",
        action="store_true",
        help="Usar dados reais do MT5 (requer MT5 instalado)",
    )
    parser.add_argument(
        "--apenas-avaliar",
        action="store_true",
        help="Apenas avaliar modelo já treinado",
    )
    parser.add_argument(
        "--modelo",
        default="modelo_final",
        help="Nome do modelo (default: modelo_final)",
    )
    parser.add_argument(
        "--semente",
        type=int,
        default=42,
        help="Semente aleatória (default: 42)",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    """Ponto de entrada principal."""
    args = _parse_args(argv)

    if args.apenas_avaliar:
        executar_avaliacao(nome_modelo=args.modelo)
    else:
        executar_treinamento(
            n_episodios=args.episodios,
            usar_dados_reais=args.dados_reais,
            nome_modelo=args.modelo,
            semente=args.semente,
        )

    return 0


if __name__ == "__main__":
    sys.exit(main())
