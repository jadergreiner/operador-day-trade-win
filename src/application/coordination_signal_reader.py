"""CoordinationSignalReader — Leitura do sinal de coordenacao cross-agent (BLID-042).

Le o arquivo JSON persistido pelo CoordinationManager e expoe o sinal atual
para que componentes (ex: agentes RL) possam verificar o estado de coordenacao
antes de abrir uma nova posicao.

Caracteristicas:
- Sem estado interno: cada chamada faz leitura fresca do filesystem
- Sem thread, sem cache, sem polling — modulo puramente funcional
- Arquivo ausente -> fallback seguro NORMAL (ADR-023)
- JSON malformado -> fallback seguro NORMAL (ADR-023)
- schema_version diferente de "1.0" -> fallback NORMAL + WARNING (ADR-019)

Exemplo de uso::

    reader = CoordinationSignalReader()

    if not reader.pode_abrir_posicao():
        logger.warning("STOP_OPERACOES ativo — abertura bloqueada")
        return

    sinal = reader.obter_sinal_atual()
    decisao = reader.obter_decisao_completa()
"""

from __future__ import annotations

import json
import logging
import time
import uuid
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Optional

from src.application.coordination_manager import (
    CoordinationSignal,
    DecisaoCoordinacao,
)

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Constantes
# ---------------------------------------------------------------------------

_SCHEMA_VERSION_ESPERADA = "1.0"
_SINAL_FALLBACK = CoordinationSignal.NORMAL


# ---------------------------------------------------------------------------
# DTO de métricas de leitura
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class ResultadoLeituraSinal:
    """Resultado de leitura do sinal com métricas operacionais.

    Atributos:
        sinal: Sinal efetivo após aplicar fallback quando necessário.
        latencia_leitura_ms: Latência total da leitura/validação em milissegundos.
        fallback_aplicado: True quando houve degradação para NORMAL.
        motivo_fallback: Motivo textual do fallback, quando aplicável.
    """

    sinal: CoordinationSignal
    latencia_leitura_ms: float
    fallback_aplicado: bool
    motivo_fallback: Optional[str]


# ---------------------------------------------------------------------------
# CoordinationSignalReader
# ---------------------------------------------------------------------------


class CoordinationSignalReader:
    """Leitor stateless do sinal de coordenacao emitido pelo CoordinationManager.

    Cada metodo executa uma leitura fresca do arquivo JSON no filesystem.
    Nenhum estado e mantido entre chamadas.

    Atributos:
        sinal_path: Caminho para o arquivo JSON com o sinal atual.
    """

    def __init__(
        self,
        sinal_path: str = "outputs/coordination_signal_current.json",
    ) -> None:
        """Inicializa o leitor com o caminho do arquivo de sinal.

        Args:
            sinal_path: Caminho para o arquivo JSON gerado pelo CoordinationManager.
                        Padrao: "outputs/coordination_signal_current.json"
        """
        self._sinal_path = Path(sinal_path)

    # ------------------------------------------------------------------
    # API publica
    # ------------------------------------------------------------------

    def pode_abrir_posicao(self) -> bool:
        """Verifica se e permitido abrir nova posicao conforme sinal atual.

        Retorna False apenas quando o sinal e STOP_OPERACOES.
        Para NORMAL, MODO_CONSERVADOR e MODO_DEFENSIVO retorna True,
        pois esses sinais nao bloqueiam abertura — apenas sinalizam cautela.

        Arquivo ausente ou invalido resulta em True (fallback seguro).

        Returns:
            True se abertura de posicao e permitida, False se bloqueada.
        """
        sinal = self.obter_sinal_atual()
        return sinal != CoordinationSignal.STOP_OPERACOES

    def obter_sinal_atual(self) -> CoordinationSignal:
        """Retorna o sinal de coordenacao atual do filesystem.

        Sempre faz leitura fresca. Em caso de erro (arquivo ausente, JSON
        invalido, schema_version incorreta), retorna NORMAL como fallback
        seguro conforme ADR-023 e ADR-019.

        Returns:
            CoordinationSignal atual ou NORMAL em caso de falha.
        """
        payload = self._ler_payload()
        if payload is None:
            return _SINAL_FALLBACK

        valor_sinal = payload.get("sinal")
        try:
            return CoordinationSignal(valor_sinal)
        except (ValueError, KeyError):
            logger.warning(
                "coordination_signal_reader: valor de sinal invalido '%s' — "
                "usando fallback NORMAL",
                valor_sinal,
            )
            return _SINAL_FALLBACK

    def obter_sinal_com_metricas(self) -> ResultadoLeituraSinal:
        """Retorna sinal atual com métricas de latência de leitura.

        Mantém semântica de fallback do reader:
        - qualquer erro de leitura/validação retorna sinal NORMAL
        - `fallback_aplicado` indica se houve degradação
        - `motivo_fallback` explica a causa para observabilidade
        """
        payload, motivo_fallback, latencia_leitura_ms = self._ler_payload_com_status()
        if payload is None:
            return ResultadoLeituraSinal(
                sinal=_SINAL_FALLBACK,
                latencia_leitura_ms=latencia_leitura_ms,
                fallback_aplicado=True,
                motivo_fallback=motivo_fallback,
            )

        valor_sinal = payload.get("sinal")
        try:
            sinal = CoordinationSignal(valor_sinal)
            return ResultadoLeituraSinal(
                sinal=sinal,
                latencia_leitura_ms=latencia_leitura_ms,
                fallback_aplicado=False,
                motivo_fallback=None,
            )
        except (ValueError, KeyError):
            logger.warning(
                "coordination_signal_reader: valor de sinal invalido '%s' — "
                "usando fallback NORMAL",
                valor_sinal,
            )
            return ResultadoLeituraSinal(
                sinal=_SINAL_FALLBACK,
                latencia_leitura_ms=latencia_leitura_ms,
                fallback_aplicado=True,
                motivo_fallback="sinal_invalido",
            )

    def obter_decisao_completa(self) -> Optional[DecisaoCoordinacao]:
        """Retorna o payload completo de DecisaoCoordinacao ou None.

        Reconstroi o dataclass a partir do JSON persistido.
        Retorna None se o arquivo estiver ausente, malformado ou
        com schema_version invalida.

        Returns:
            DecisaoCoordinacao reconstruida ou None em caso de falha.
        """
        payload = self._ler_payload()
        if payload is None:
            return None

        try:
            return self._deserializar_decisao(payload)
        except (KeyError, ValueError, TypeError) as exc:
            logger.warning(
                "coordination_signal_reader: falha ao desserializar DecisaoCoordinacao: %s "
                "— retornando None",
                exc,
            )
            return None

    # ------------------------------------------------------------------
    # Metodos privados
    # ------------------------------------------------------------------

    def _ler_payload(self) -> Optional[dict[str, object]]:
        """Le e valida o payload JSON do arquivo de sinal.

        Realiza validacao de existencia do arquivo, parsing JSON e
        verificacao de schema_version conforme ADR-019.

        Returns:
            Dicionario com o payload ou None em caso de qualquer falha.
        """
        payload, _, _ = self._ler_payload_com_status()
        return payload

    def _ler_payload_com_status(
        self,
    ) -> tuple[Optional[dict[str, object]], Optional[str], float]:
        """Lê payload com motivo de fallback e latência total em ms."""
        inicio = time.perf_counter()

        if not self._sinal_path.exists():
            logger.debug(
                "coordination_signal_reader: arquivo de sinal ausente em '%s' "
                "— usando fallback NORMAL",
                self._sinal_path,
            )
            lat = (time.perf_counter() - inicio) * 1000.0
            return None, "arquivo_ausente", lat

        try:
            conteudo = self._sinal_path.read_text(encoding="utf-8")
        except OSError as exc:
            logger.warning(
                "coordination_signal_reader: erro ao ler arquivo '%s': %s "
                "— usando fallback NORMAL",
                self._sinal_path,
                exc,
            )
            lat = (time.perf_counter() - inicio) * 1000.0
            return None, "erro_leitura_arquivo", lat

        try:
            payload: dict[str, object] = json.loads(conteudo)
        except json.JSONDecodeError as exc:
            logger.warning(
                "coordination_signal_reader: JSON invalido em '%s': %s "
                "— usando fallback NORMAL",
                self._sinal_path,
                exc,
            )
            lat = (time.perf_counter() - inicio) * 1000.0
            return None, "json_invalido", lat

        schema_version = payload.get("schema_version")
        if schema_version != _SCHEMA_VERSION_ESPERADA:
            logger.warning(
                "coordination_signal_reader: schema_version '%s' diferente do esperado '%s' "
                "— usando fallback NORMAL (ADR-019)",
                schema_version,
                _SCHEMA_VERSION_ESPERADA,
            )
            lat = (time.perf_counter() - inicio) * 1000.0
            return None, "schema_version_invalida", lat

        lat = (time.perf_counter() - inicio) * 1000.0
        return payload, None, lat

    def _deserializar_decisao(
        self, payload: dict[str, object]
    ) -> DecisaoCoordinacao:
        """Reconstroi DecisaoCoordinacao a partir do dicionario JSON.

        Args:
            payload: Dicionario com os campos do JSON persistido.

        Returns:
            DecisaoCoordinacao reconstruida.

        Raises:
            KeyError: Se campos obrigatorios estiverem ausentes.
            ValueError: Se o valor do sinal nao for valido.
            TypeError: Se tipos dos campos forem incompativeis.
        """
        def _para_float(campo: str) -> float:
            valor = payload[campo]
            if not isinstance(valor, (int, float)):
                raise TypeError(f"campo '{campo}' deve ser numerico, recebido: {type(valor)}")
            return float(valor)

        def _para_int(campo: str) -> int:
            valor = payload[campo]
            if not isinstance(valor, (int, float)):
                raise TypeError(f"campo '{campo}' deve ser numerico, recebido: {type(valor)}")
            return int(valor)

        def _para_int_opcional(campo: str, default: int = 0) -> int:
            valor = payload.get(campo)
            if valor is None:
                return default
            if not isinstance(valor, (int, float)):
                raise TypeError(f"campo '{campo}' deve ser numerico, recebido: {type(valor)}")
            return int(valor)

        def _para_float_opcional(campo: str, default: float = 0.0) -> float:
            valor = payload.get(campo)
            if valor is None:
                return default
            if not isinstance(valor, (int, float)):
                raise TypeError(f"campo '{campo}' deve ser numerico, recebido: {type(valor)}")
            return float(valor)

        def _para_mapa_float(campo: str) -> dict[str, float]:
            valor = payload.get(campo)
            if valor is None:
                return {}
            if not isinstance(valor, dict):
                raise TypeError(f"campo '{campo}' deve ser dict, recebido: {type(valor)}")

            resultado: dict[str, float] = {}
            for chave, valor_item in valor.items():
                if not isinstance(chave, str):
                    raise TypeError(
                        f"chave de '{campo}' deve ser str, recebido: {type(chave)}"
                    )
                if not isinstance(valor_item, (int, float)):
                    raise TypeError(
                        f"valor de '{campo}[{chave}]' deve ser numerico, "
                        f"recebido: {type(valor_item)}"
                    )
                resultado[chave] = float(valor_item)
            return resultado

        def _para_mapa_int(campo: str) -> dict[str, int]:
            valor = payload.get(campo)
            if valor is None:
                return {}
            if not isinstance(valor, dict):
                raise TypeError(f"campo '{campo}' deve ser dict, recebido: {type(valor)}")

            resultado: dict[str, int] = {}
            for chave, valor_item in valor.items():
                if not isinstance(chave, str):
                    raise TypeError(
                        f"chave de '{campo}' deve ser str, recebido: {type(chave)}"
                    )
                if not isinstance(valor_item, (int, float)):
                    raise TypeError(
                        f"valor de '{campo}[{chave}]' deve ser numerico, "
                        f"recebido: {type(valor_item)}"
                    )
                resultado[chave] = int(valor_item)
            return resultado

        drawdown_por_agente = _para_mapa_float("drawdown_por_agente_pct")
        pnl_por_agente = _para_mapa_float("pnl_por_agente_reais")
        total_trades_por_agente = _para_mapa_int("total_trades_por_agente")

        # Retrocompatibilidade: se os mapas não vierem no JSON legado,
        # reconstruir com os campos fixos tradicionais.
        if not drawdown_por_agente:
            drawdown_por_agente = {
                "rl_5000": _para_float("drawdown_rl_5000_pct"),
                "rl_direto": _para_float("drawdown_rl_direto_pct"),
            }
        if not total_trades_por_agente:
            total_trades_por_agente = {
                "rl_5000": _para_int("total_trades_rl_5000"),
                "rl_direto": _para_int("total_trades_rl_direto"),
            }
        if not pnl_por_agente:
            pnl_por_agente = {}

        return DecisaoCoordinacao(
            ciclo_id=str(payload["ciclo_id"]),
            timestamp_iso=str(payload["timestamp_iso"]),
            sinal=CoordinationSignal(payload["sinal"]),
            drawdown_rl_5000_pct=_para_float("drawdown_rl_5000_pct"),
            drawdown_rl_direto_pct=_para_float("drawdown_rl_direto_pct"),
            drawdown_conjunto_pct=_para_float("drawdown_conjunto_pct"),
            capital_estimado_reais=_para_float("capital_estimado_reais"),
            threshold_violado=(
                str(payload["threshold_violado"])
                if payload.get("threshold_violado") is not None
                else None
            ),
            agente_gatilho=(
                str(payload["agente_gatilho"])
                if payload.get("agente_gatilho") is not None
                else None
            ),
            total_trades_rl_5000=_para_int("total_trades_rl_5000"),
            total_trades_rl_direto=_para_int("total_trades_rl_direto"),
            drawdown_por_agente_pct=drawdown_por_agente,
            pnl_por_agente_reais=pnl_por_agente,
            total_trades_por_agente=total_trades_por_agente,
            ciclo_numero=_para_int_opcional("ciclo_numero", default=0),
            latencia_ciclo_ms=_para_float_opcional("latencia_ciclo_ms", default=0.0),
        )
