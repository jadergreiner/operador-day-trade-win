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

    # Treinar com dados reais do MT5 (usa credenciais do .env)
    python scripts/treinar_novo_agente_rl.py --dados-reais --episodios 500

    # Apenas avaliar modelo existente com dados reais
    python scripts/treinar_novo_agente_rl.py --dados-reais --apenas-avaliar

    # Avaliar modelo já treinado
    python scripts/treinar_novo_agente_rl.py --apenas-avaliar

Configuração para dados reais:
    Configure o arquivo .env na raiz do projeto com:
        MT5_LOGIN=<numero_da_conta>
        MT5_PASSWORD=<sua_senha>
        MT5_SERVER=<nome_do_servidor>
    Consulte docs/SETUP_PRODUCAO.md para instruções detalhadas.
"""

from __future__ import annotations

import argparse
import json
import logging
import os
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Optional

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
# Carregamento de dados e validações MT5
# ---------------------------------------------------------------------------

# Saldo mínimo recomendado para operar Mini Índice (R$)
# Configurável via variável de ambiente RL_SALDO_MINIMO
_SALDO_MINIMO_BRL: float = float(os.getenv("RL_SALDO_MINIMO", "450.0"))

# Horário de funcionamento do Mini Índice (horário de Brasília)
_HORA_ABERTURA = 9
_HORA_FECHAMENTO = 18

# Fuso horário de Brasília (UTC-3)
_TZ_BRASILIA = timezone(timedelta(hours=-3))


def _obter_agora() -> datetime:
    """Retorna o datetime atual no fuso horário de Brasília.

    Função auxiliar isolada para facilitar testes unitários.

    Returns:
        datetime com timezone de Brasília (UTC-3)
    """
    return datetime.now(_TZ_BRASILIA)


def _carregar_credenciais_mt5() -> dict[str, Any]:
    """Carrega credenciais MT5 a partir de variáveis de ambiente.

    Tenta carregar o arquivo .env automaticamente se a biblioteca
    python-dotenv estiver instalada.

    Returns:
        Dicionário com chaves 'login' (int), 'senha' e 'servidor'

    Raises:
        ValueError: Se alguma credencial obrigatória estiver ausente
    """
    # Carregar .env automaticamente se disponível
    try:
        from dotenv import load_dotenv
        env_path = ROOT_DIR / ".env"
        if env_path.exists():
            load_dotenv(env_path)
    except ImportError:
        pass  # python-dotenv é opcional

    login_str = os.getenv("MT5_LOGIN", "").strip()
    senha = os.getenv("MT5_PASSWORD", "").strip()
    servidor = os.getenv("MT5_SERVER", "").strip()

    ausentes = []
    if not login_str:
        ausentes.append("MT5_LOGIN")
    if not senha:
        ausentes.append("MT5_PASSWORD")
    if not servidor:
        ausentes.append("MT5_SERVER")

    if ausentes:
        raise ValueError(
            "Variáveis de ambiente ausentes no .env: "
            + ", ".join(ausentes)
            + ". Consulte docs/SETUP_PRODUCAO.md."
        )

    if not login_str.isdigit():
        raise ValueError(
            "MT5_LOGIN deve ser numérico (somente dígitos). "
            "Verifique o valor configurado no .env."
        )

    return {
        "login": int(login_str),
        "senha": senha,
        "servidor": servidor,
    }


def _validar_conta_mt5(mt5: Any) -> dict[str, Any]:
    """Valida informações da conta MT5 conectada.

    Verifica saldo mínimo e margem disponível para operação
    segura do Mini Índice.

    Args:
        mt5: Módulo MetaTrader5 após login bem-sucedido

    Returns:
        Dicionário com tipo_conta, saldo, margem_livre e moeda

    Raises:
        RuntimeError: Se a conta não atender os critérios mínimos
    """
    info = mt5.account_info()
    if info is None:
        raise RuntimeError(
            "Não foi possível obter informações da conta. "
            "Verifique se o MT5 está conectado corretamente."
        )

    # ACCOUNT_TRADE_MODE_REAL=0, DEMO=1, CONTEST=2
    tipo_conta = "REAL" if info.trade_mode == 0 else "DEMO"

    if info.balance < _SALDO_MINIMO_BRL:
        raise RuntimeError(
            f"Saldo insuficiente: R${info.balance:,.2f}. "
            f"Mínimo recomendado: R${_SALDO_MINIMO_BRL:,.2f} "
            "para operar Mini Índice."
        )

    margem_minima = _SALDO_MINIMO_BRL * 0.1
    if info.margin_free < margem_minima:
        raise RuntimeError(
            f"Margem livre insuficiente: R${info.margin_free:,.2f}. "
            "Reduza posições abertas antes de treinar."
        )

    return {
        "login": info.login,
        "servidor": info.server,
        "tipo_conta": tipo_conta,
        "saldo": info.balance,
        "margem_livre": info.margin_free,
        "moeda": info.currency,
    }


def verificar_horario_trading() -> bool:
    """Verifica se está dentro do horário de mercado do Mini Índice.

    Mini Índice (WIN): Segunda a Sexta, 9h às 18h (horário de Brasília).

    Returns:
        True se dentro do horário de trading, False caso contrário
    """
    agora = _obter_agora()

    # Verificar se é dia útil (0=Segunda … 4=Sexta, 5=Sab, 6=Dom)
    if agora.weekday() >= 5:
        return False

    hora_abertura = agora.replace(
        hour=_HORA_ABERTURA, minute=0, second=0, microsecond=0
    )
    hora_fechamento = agora.replace(
        hour=_HORA_FECHAMENTO, minute=0, second=0, microsecond=0
    )
    return hora_abertura <= agora <= hora_fechamento


def carregar_dados_mt5(
    simbolo: str = "WINJ26",
    n_candles: int = 5000,
) -> Optional[pd.DataFrame]:
    """Carrega dados históricos reais do MT5 com login automático.

    Usa credenciais do arquivo .env para autenticação. Valida saldo,
    margem e disponibilidade do símbolo antes de baixar os dados.

    Args:
        simbolo: Símbolo do Mini Índice no MT5 (ex: 'WINJ26')
        n_candles: Quantidade de candles de 5 minutos a carregar

    Returns:
        DataFrame OHLCV ou None se MT5 não disponível
    """
    try:
        import MetaTrader5 as mt5
    except ImportError:
        logger.warning(
            "Pacote MetaTrader5 não instalado. "
            "Instale com: pip install MetaTrader5"
        )
        return None

    # Validar credenciais antes de qualquer conexão
    try:
        credenciais = _carregar_credenciais_mt5()
    except ValueError as erro:
        logger.warning(
            "Credenciais MT5 inválidas: %s", erro
        )
        return None

    # Aviso sobre horário de mercado (não bloqueante)
    if not verificar_horario_trading():
        logger.warning(
            "Fora do horário de mercado do Mini Índice "
            "(%dh-%dh, seg-sex, horário de Brasília). "
            "Os dados históricos ainda serão carregados.",
            _HORA_ABERTURA,
            _HORA_FECHAMENTO,
        )

    try:
        # Caminho fixo do terminal MT5 da Clear para evitar conexões acidentais
        mt5_path = r"C:\Program Files\Clear Investimentos MT5 Terminal\terminal64.exe"

        # Inicializar o terminal MT5 no caminho específico
        if not mt5.initialize(path=mt5_path):
            logger.warning(
                "Terminal MT5 não encontrado no caminho: %s. "
                "Erro: %s. "
                "Verifique se o MT5 da Clear está instalado e o caminho está correto.",
                mt5_path,
                mt5.last_error(),
            )
            return None

        # Realizar login com credenciais (sem exibir senha no log)
        login_ok = mt5.login(
            credenciais["login"],
            password=credenciais["senha"],
            server=credenciais["servidor"],
        )

        if not login_ok:
            logger.warning(
                "Falha no login MT5 (conta=%d, servidor=%s). "
                "Erro: %s. "
                "Verifique as credenciais no .env.",
                credenciais["login"],
                credenciais["servidor"],
                mt5.last_error(),
            )
            mt5.shutdown()
            return None

        logger.info(
            "Conectado ao MT5: conta %d em '%s'",
            credenciais["login"],
            credenciais["servidor"],
        )

        # Validar informações da conta
        try:
            info_conta = _validar_conta_mt5(mt5)
        except RuntimeError as erro:
            logger.warning("Validação de conta falhou: %s", erro)
            mt5.shutdown()
            return None

        logger.info(
            "Conta %s | Saldo: R$%.2f | Margem livre: R$%.2f",
            info_conta["tipo_conta"],
            info_conta["saldo"],
            info_conta["margem_livre"],
        )

        # Verificar se o símbolo está disponível na conta
        info_simbolo = mt5.symbol_info(simbolo)
        if info_simbolo is None:
            logger.warning(
                "Símbolo '%s' não disponível na conta. "
                "Adicione-o nos favoritos do MT5 e tente novamente.",
                simbolo,
            )
            mt5.shutdown()
            return None

        # Garantir que o símbolo está visível no Market Watch
        if not info_simbolo.visible:
            if not mt5.symbol_select(simbolo, True):
                logger.warning(
                    "Não foi possível selecionar '%s' no MT5.",
                    simbolo,
                )
                mt5.shutdown()
                return None

        # Carregar candles históricos de 5 minutos
        barras = mt5.copy_rates_from_pos(
            simbolo, mt5.TIMEFRAME_M5, 0, n_candles
        )

        mt5.shutdown()

        if barras is None or len(barras) == 0:
            logger.warning(
                "Sem dados históricos para '%s'. "
                "Verifique se o símbolo possui dados no MT5.",
                simbolo,
            )
            return None

        df = pd.DataFrame(barras)
        df = df.rename(columns={"tick_volume": "volume"})

        logger.info(
            "Dados MT5 carregados: %d candles de '%s'",
            len(df),
            simbolo,
        )
        return df[["open", "high", "low", "close", "volume"]]

    except Exception as exc:
        logger.warning(
            "Erro inesperado ao carregar dados MT5: %s", exc
        )
        try:
            mt5.shutdown()
        except Exception:
            pass
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
