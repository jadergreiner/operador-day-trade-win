"""
BUG-3: Backoff Exponencial e Deteccao de Rollover WINFUT

Problema: agente acumulou 20+ rejeicoes consecutivas com retcode=10006
(Order execution failed) sem halt nem backoff. Causa raiz: rollover de
contrato WINFUT sem deteccao automatica.

Responsabilidades:
- Detectar retcode=10006 e aplicar backoff exponencial
- Verificar disponibilidade do simbolo antes de retentar
- Detectar vencimento de contrato WINFUT (rollover)
- Encerrar sessao graciosamente apos N falhas consecutivas

Integracao:
- src.application.ordem_backoff_retry.GerenciadorRetryOrdem
- Usado em enviar_ordem() dos agentes RL_5000 e RL_DIRETO

Status: BUG-3 (18/03/2026)
Referencia: docs/BACKLOG.md (BUG-3 / CRITICO)
"""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field
from datetime import date, datetime, timedelta
from enum import Enum
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)

# Retcode MT5: ordem rejeitada (simbolo indisponivel, fora de horario,
# contrato expirado, sem liquidez)
RETCODE_ORDER_FAILED = 10006

# Calendario de rollover WINFUT: terceira quarta-feira do mes
# Python weekday(): 0=segunda, 1=terca, 2=quarta, 3=quinta ... 6=domingo
_DIA_ROLLOVER_WINFUT = 2  # quarta-feira = 2
_SEMANA_ROLLOVER = 3       # 3a semana do mes (1-indexed)


class StatusRetry(Enum):
    """Estado do mecanismo de retry apos rejeicao."""

    PERMITIDO = "PERMITIDO"          # Pode retentar agora
    EM_BACKOFF = "EM_BACKOFF"        # Aguardando backoff
    ENCERRAR_SESSAO = "ENCERRAR_SESSAO"  # Limite atingido — parar
    ROLLOVER_DETECTADO = "ROLLOVER_DETECTADO"  # Contrato expirado
    SIMBOLO_INATIVO = "SIMBOLO_INATIVO"  # Simbolo fora de negociacao


@dataclass
class ResultadoRetry:
    """Resultado de uma avaliacao de retry.

    Args:
        status: Estado atual do mecanismo de retry.
        aguardar_segundos: Segundos a aguardar antes de retentar.
        mensagem: Descricao legivel do estado.
        falhas_consecutivas: Contador atual de falhas.
    """

    status: StatusRetry
    aguardar_segundos: float
    mensagem: str
    falhas_consecutivas: int

    def permitido(self) -> bool:
        """Retorna True se o retry e permitido imediatamente."""
        return self.status == StatusRetry.PERMITIDO

    def deve_encerrar(self) -> bool:
        """Retorna True se a sessao deve ser encerrada."""
        return self.status in (
            StatusRetry.ENCERRAR_SESSAO,
            StatusRetry.ROLLOVER_DETECTADO,
        )


def calcular_terceira_quarta_do_mes(ano: int, mes: int) -> date:
    """Calcula a data da terceira quarta-feira de um mes.

    O rollover do WINFUT ocorre na terceira quarta-feira do mes de vencimento.

    Args:
        ano: Ano (ex: 2026)
        mes: Mes (1-12)

    Returns:
        Data da terceira quarta-feira do mes.
    """
    primeiro_dia = date(ano, mes, 1)
    # dia_semana do primeiro dia: 0=segunda ... 6=domingo
    # Queremos quarta-feira = 2 (ISO: 0=segunda)
    dia_semana_primeiro = primeiro_dia.weekday()  # 0=seg, 2=qua

    # Distancia ate a primeira quarta-feira (usando timedelta para nao
    # cruzar meses acidentalmente via date.replace)
    dias_ate_quarta = (_DIA_ROLLOVER_WINFUT - dia_semana_primeiro) % 7
    primeira_quarta = primeiro_dia + timedelta(days=dias_ate_quarta)

    # Terceira quarta = primeira + 14 dias
    terceira_quarta = primeira_quarta + timedelta(days=14)
    return terceira_quarta


def detectar_rollover_winfut(data_referencia: Optional[date] = None) -> bool:
    """Verifica se hoje e dia de rollover do WINFUT.

    O vencimento ocorre na terceira quarta-feira do mes de vencimento.
    Contratos WIN vencem nos meses pares (fev, abr, jun, ago, out, dez).

    Args:
        data_referencia: Data para verificar (default: hoje).

    Returns:
        True se hoje e dia de rollover, False caso contrario.
    """
    hoje = data_referencia or date.today()
    terceira_quarta = calcular_terceira_quarta_do_mes(hoje.year, hoje.month)
    return hoje == terceira_quarta


def obter_proximo_simbolo_winfut(simbolo_atual: str) -> Optional[str]:
    """Sugere o proximo simbolo WINFUT apos rollover.

    Convencao de simbolos:
    - WIN + letra do mes + dois digitos do ano
    - Meses de vencimento: F(jan), G(fev), H(mar), J(abr), K(mai),
      M(jun), N(jul), Q(ago), U(set), V(out), X(nov), Z(dez)
    - WINFUT: vence nos meses pares (G, J, M, Q, V, Z)

    Args:
        simbolo_atual: Simbolo atual (ex: "WINJ26").

    Returns:
        Proximo simbolo sugerido ou None se nao conseguir determinar.
    """
    _MESES_WINFUT = {
        'G': 2, 'J': 4, 'M': 6, 'Q': 8, 'V': 10, 'Z': 12
    }
    _CODIGOS_MESES_WINFUT = {v: k for k, v in _MESES_WINFUT.items()}

    if len(simbolo_atual) < 6:
        return None

    try:
        letra_mes = simbolo_atual[3]
        ano_sufixo = int(simbolo_atual[4:6])
        mes_atual = _MESES_WINFUT.get(letra_mes)

        if mes_atual is None:
            return None

        # Proximo mes de vencimento
        meses_disponiveis = sorted(_MESES_WINFUT.values())
        idx_atual = meses_disponiveis.index(mes_atual)

        if idx_atual + 1 < len(meses_disponiveis):
            proximo_mes = meses_disponiveis[idx_atual + 1]
            proximo_ano = ano_sufixo
        else:
            proximo_mes = meses_disponiveis[0]
            proximo_ano = (ano_sufixo + 1) % 100

        codigo = _CODIGOS_MESES_WINFUT[proximo_mes]
        return f"WIN{codigo}{proximo_ano:02d}"

    except (ValueError, IndexError, KeyError):
        return None


class GerenciadorRetryOrdem:
    """Gerencia backoff exponencial e deteccao de rollover para ordens MT5.

    Implementa a politica de retry definida no BUG-3:
    - 3 falhas consecutivas: aguardar 60s
    - 5 falhas consecutivas: encerrar sessao

    Uso:
        retry_mgr = GerenciadorRetryOrdem(simbolo="WINJ26")

        retcode = mt5.send_order(...)
        if retcode == 10006:
            resultado = retry_mgr.registrar_falha_10006(retcode)
            if resultado.deve_encerrar():
                logger.error(resultado.mensagem)
                sys.exit(1)
            time.sleep(resultado.aguardar_segundos)
        else:
            retry_mgr.registrar_sucesso()
    """

    # Tabela de backoff: {n_falhas: segundos_de_espera}
    _TABELA_BACKOFF: dict[int, float] = {
        1: 5.0,    # 1a falha: 5s
        2: 15.0,   # 2a falha: 15s
        3: 60.0,   # 3a falha: 60s (backoff agressivo)
        4: 60.0,   # 4a falha: 60s
    }
    _LIMITE_ENCERRAR = 5  # A partir da 5a falha: encerrar sessao

    def __init__(
        self,
        simbolo: str,
        limite_encerrar: int = 5,
        verificar_rollover: bool = True,
    ) -> None:
        """Inicializa o gerenciador de retry.

        Args:
            simbolo: Simbolo atual (ex: "WINJ26").
            limite_encerrar: Numero de falhas apos o qual encerra a sessao.
            verificar_rollover: Se True, verifica vencimento de contrato.
        """
        self.simbolo = simbolo
        self.limite_encerrar = limite_encerrar
        self.verificar_rollover = verificar_rollover
        self._falhas_consecutivas: int = 0
        self._ultima_falha: Optional[datetime] = None
        self._historico_falhas: list[Dict[str, Any]] = []

    def registrar_falha_10006(self, retcode: int) -> ResultadoRetry:
        """Registra falha com retcode 10006 e determina acao.

        Args:
            retcode: Codigo de retorno MT5 (esperado: 10006).

        Returns:
            ResultadoRetry com status e tempo de espera.
        """
        self._falhas_consecutivas += 1
        self._ultima_falha = datetime.now()
        self._historico_falhas.append({
            "timestamp": self._ultima_falha.isoformat(),
            "retcode": retcode,
            "falha_n": self._falhas_consecutivas,
        })

        logger.warning(
            f"[BACKOFF] retcode={retcode} no simbolo={self.simbolo}. "
            f"Falha consecutiva #{self._falhas_consecutivas}."
        )

        # Verificar rollover antes de decidir pelo backoff
        if self.verificar_rollover and detectar_rollover_winfut():
            proximo = obter_proximo_simbolo_winfut(self.simbolo)
            mensagem = (
                f"[ROLLOVER] Vencimento detectado! Simbolo {self.simbolo} "
                f"expirou. Proximo: {proximo or 'desconhecido'}. "
                f"Encerrar sessao e atualizar simbolo."
            )
            logger.error(mensagem)
            return ResultadoRetry(
                status=StatusRetry.ROLLOVER_DETECTADO,
                aguardar_segundos=0.0,
                mensagem=mensagem,
                falhas_consecutivas=self._falhas_consecutivas,
            )

        # Encerrar apos N falhas consecutivas
        if self._falhas_consecutivas >= self.limite_encerrar:
            mensagem = (
                f"[BACKOFF] {self._falhas_consecutivas} falhas consecutivas "
                f"com retcode={retcode} no simbolo={self.simbolo}. "
                f"Limite atingido ({self.limite_encerrar}). Encerrar sessao."
            )
            logger.error(mensagem)
            return ResultadoRetry(
                status=StatusRetry.ENCERRAR_SESSAO,
                aguardar_segundos=0.0,
                mensagem=mensagem,
                falhas_consecutivas=self._falhas_consecutivas,
            )

        # Calcular backoff
        n = min(self._falhas_consecutivas, max(self._TABELA_BACKOFF.keys()))
        aguardar = self._TABELA_BACKOFF.get(n, 60.0)
        mensagem = (
            f"[BACKOFF] Falha #{self._falhas_consecutivas} com retcode={retcode}. "
            f"Aguardando {aguardar:.0f}s antes de retentar."
        )
        logger.warning(mensagem)

        return ResultadoRetry(
            status=StatusRetry.EM_BACKOFF,
            aguardar_segundos=aguardar,
            mensagem=mensagem,
            falhas_consecutivas=self._falhas_consecutivas,
        )

    def registrar_sucesso(self) -> None:
        """Reseta contador de falhas apos envio bem-sucedido."""
        if self._falhas_consecutivas > 0:
            logger.info(
                f"[BACKOFF] Sucesso apos {self._falhas_consecutivas} "
                f"falhas. Resetando contador."
            )
        self._falhas_consecutivas = 0

    def verificar_simbolo_ativo(self, mt5_instance: Any) -> bool:
        """Verifica se o simbolo esta ativo e aceitando ordens no MT5.

        Usa `mt5.symbol_info()` para verificar `trade_mode`.
        trade_mode == 0 significa TRADE_MODE_DISABLED.

        Args:
            mt5_instance: Instancia do modulo MetaTrader5.

        Returns:
            True se simbolo esta ativo, False caso contrario.
        """
        try:
            info = mt5_instance.symbol_info(self.simbolo)
            if info is None:
                logger.warning(
                    f"[SIMBOLO] symbol_info({self.simbolo}) retornou None. "
                    f"Simbolo pode estar inativo ou com nome incorreto."
                )
                return False

            trade_mode = getattr(info, 'trade_mode', -1)
            if trade_mode == 0:
                logger.warning(
                    f"[SIMBOLO] {self.simbolo} com trade_mode=DISABLED. "
                    f"Sem negociacao disponivel."
                )
                return False

            return True

        except Exception as e:
            logger.warning(f"[SIMBOLO] Erro ao verificar simbolo {self.simbolo}: {e}")
            return False

    @property
    def falhas_consecutivas(self) -> int:
        """Retorna o numero atual de falhas consecutivas."""
        return self._falhas_consecutivas

    @property
    def historico_falhas(self) -> list[Dict[str, Any]]:
        """Retorna o historico de falhas registradas."""
        return list(self._historico_falhas)

    def resumo(self) -> Dict[str, Any]:
        """Retorna resumo do estado atual do gerenciador.

        Returns:
            Dicionario com estado atual para log/debug.
        """
        return {
            "simbolo": self.simbolo,
            "falhas_consecutivas": self._falhas_consecutivas,
            "limite_encerrar": self.limite_encerrar,
            "ultima_falha": (
                self._ultima_falha.isoformat() if self._ultima_falha else None
            ),
            "rollover_hoje": (
                detectar_rollover_winfut() if self.verificar_rollover else False
            ),
        }
