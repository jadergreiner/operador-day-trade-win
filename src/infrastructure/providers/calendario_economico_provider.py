"""
Provider do calendario economico para o GateCalendarioEconomico.

Responsabilidades:
- Definir interface ICalendarioEconomicoProvider
- Implementar CalendarioEconomicoNoop (stub para testes e ambientes sem API)
- Implementar CalendarioEconomicoFinnhub com cache TTL (producao)

Fail-open: erros de rede retornam lista vazia — nao bloqueiam operacoes.
Cache TTL: 300 segundos (configuravel) para evitar excesso de requisicoes.

Status: v1.0 (24/03/2026)
Referencia: docs/BACKLOG.md (Camada Risco Externo - Calendario)
"""

from __future__ import annotations

import logging
import time
from abc import ABC, abstractmethod
from datetime import datetime, timedelta, timezone
from typing import Optional
from urllib import request
from urllib.error import URLError

import json as json_module

from src.domain.value_objects.risco_externo import EventoCalendario

logger = logging.getLogger(__name__)


class ICalendarioEconomicoProvider(ABC):
    """Interface do provedor de calendario economico."""

    @abstractmethod
    def obter_proximos_eventos(
        self,
        janela_minutos: int = 60,
    ) -> list[EventoCalendario]:
        """
        Retorna eventos economicos dentro da janela de tempo futura.

        Args:
            janela_minutos: Janela futura em minutos para buscar eventos.

        Returns:
            Lista de EventoCalendario (pode ser vazia).
            Nunca lanca excecao — erros retornam lista vazia (fail-open).
        """
        ...

    @abstractmethod
    def obter_eventos_recentes(
        self,
        janela_passado_minutos: int = 10,
    ) -> list[EventoCalendario]:
        """
        Retorna eventos economicos ocorridos nos ultimos N minutos.

        Usado pelo gate para verificar janela pos-evento (minutos_apos_abrir).

        Args:
            janela_passado_minutos: Minutos para tras para buscar eventos.

        Returns:
            Lista de EventoCalendario ocorridos recentemente.
        """
        ...


class CalendarioEconomicoNoop(ICalendarioEconomicoProvider):
    """
    Implementacao vazia do provider de calendario.

    Uso: testes unitarios, ambientes sem API configurada,
    ou quando o usuario optar por desabilitar o gate de calendario.
    """

    def obter_proximos_eventos(
        self, janela_minutos: int = 60
    ) -> list[EventoCalendario]:
        return []

    def obter_eventos_recentes(
        self, janela_passado_minutos: int = 10
    ) -> list[EventoCalendario]:
        return []


class CalendarioEconomicoFinnhub(ICalendarioEconomicoProvider):
    """
    Provider que consome a Finnhub Economic Calendar API com cache TTL.

    Endpoint: GET https://finnhub.io/api/v1/calendar/economic
    Autenticacao: api_key como parametro de query string
    Cache TTL: 300 segundos por padrao

    Fail-open: qualquer erro de rede, timeout ou parse retorna lista vazia.

    Eventos filtrados (alto impacto):
        COPOM, FOMC, NFP, CPI, PPI, GDP, IPCA, IGP-M, Payroll
    """

    _EVENTOS_ALTO_IMPACTO = {
        "copom", "fomc", "nfp", "cpi", "ppi", "gdp",
        "ipca", "igp-m", "payroll", "federal reserve",
        "interest rate", "unemployment",
    }
    _TIMEOUT_SEGUNDOS = 5

    def __init__(
        self,
        api_key: str,
        cache_ttl_segundos: int = 300,
    ) -> None:
        self._api_key = api_key
        self._cache_ttl = cache_ttl_segundos
        self._cache: list[EventoCalendario] = []
        self._cache_timestamp: float = 0.0

    def obter_proximos_eventos(
        self, janela_minutos: int = 60
    ) -> list[EventoCalendario]:
        """
        Retorna eventos dentro da janela de tempo futura, usando cache TTL.

        Args:
            janela_minutos: Janela futura em minutos.

        Returns:
            Lista de EventoCalendario (vazia em caso de erro ou sem eventos).
        """
        try:
            todos = self._obter_com_cache()
            agora = datetime.now(tz=timezone.utc)
            limite = agora + timedelta(minutes=janela_minutos)
            return [e for e in todos if agora <= e.timestamp_evento <= limite]
        except Exception as e:
            logger.warning(
                "Erro ao consultar calendario economico — fail-open: %s", e
            )
            return []

    def obter_eventos_recentes(
        self, janela_passado_minutos: int = 10
    ) -> list[EventoCalendario]:
        """Retorna eventos ocorridos nos ultimos N minutos."""
        try:
            todos = self._obter_com_cache()
            agora = datetime.now(tz=timezone.utc)
            limite = agora - timedelta(minutes=janela_passado_minutos)
            return [e for e in todos if limite <= e.timestamp_evento < agora]
        except Exception as e:
            logger.warning("Erro ao consultar eventos recentes — fail-open: %s", e)
            return []

    def _obter_com_cache(self) -> list[EventoCalendario]:
        """Retorna cache se valido, caso contrario faz nova requisicao."""
        agora_ts = time.monotonic()
        if agora_ts - self._cache_timestamp < self._cache_ttl:
            return self._cache

        eventos = self._buscar_api()
        self._cache = eventos
        self._cache_timestamp = agora_ts
        return eventos

    def _buscar_api(self) -> list[EventoCalendario]:
        """Faz requisicao HTTP a API Finnhub e converte resposta."""
        url = (
            f"https://finnhub.io/api/v1/calendar/economic"
            f"?token={self._api_key}"
        )
        try:
            req = request.Request(url, headers={"Accept": "application/json"})
            with request.urlopen(req, timeout=self._TIMEOUT_SEGUNDOS) as resp:
                dados = json_module.loads(resp.read().decode("utf-8"))
        except (URLError, OSError, ValueError) as e:
            logger.warning("Falha na requisicao Finnhub: %s", e)
            return []

        return self._parsear_eventos(dados)

    def _parsear_eventos(self, dados: object) -> list[EventoCalendario]:
        """Converte resposta da API em lista de EventoCalendario."""
        if not isinstance(dados, dict):
            return []

        economicCalendar = dados.get("economicCalendar", [])
        if not isinstance(economicCalendar, list):
            return []

        eventos: list[EventoCalendario] = []
        for item in economicCalendar:
            if not isinstance(item, dict):
                continue
            nome = str(item.get("event", ""))
            if not self._e_alto_impacto(nome):
                continue
            try:
                ts_str = str(item.get("time", ""))
                ts = datetime.fromisoformat(ts_str)
                if ts.tzinfo is None:
                    ts = ts.replace(tzinfo=timezone.utc)
                eventos.append(EventoCalendario(nome=nome, timestamp_evento=ts))
            except (ValueError, TypeError):
                continue

        return eventos

    def _e_alto_impacto(self, nome: str) -> bool:
        """Verifica se o evento e de alto impacto."""
        nome_lower = nome.lower()
        return any(kw in nome_lower for kw in self._EVENTOS_ALTO_IMPACTO)
