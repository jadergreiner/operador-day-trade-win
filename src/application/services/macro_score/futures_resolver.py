"""Resolvedor de contratos futuros vigentes."""

import logging
import re
from datetime import datetime
from typing import Optional

from src.infrastructure.adapters.mt5_adapter import MT5Adapter

logger = logging.getLogger(__name__)


class FuturesContractResolver:
    """Resolve simbolo de contrato futuro vigente no MT5.

    Estrategia de resolucao (em ordem de prioridade):
    1. Contrato continuo com sufixo $N (convencao B3 no MT5)
    2. Busca por simbolos que iniciam com o prefixo base
    3. Seleção inteligente do contrato mais liquido/proximo
    4. Fallback gracioso: retorna None se nao encontrado

    Exemplos:
        WDO  -> WDO$N  (continuo disponivel)
        DI1F -> DI1F27 (vertice janeiro mais proximo)
        CCM  -> CCM$N  (continuo disponivel)
        GLDG -> GLDG26 (primeiro contrato disponivel)
    """

    # Meses de vencimento B3 (codigo letra -> mes)
    MONTH_CODES = {
        "F": 1,   # Janeiro
        "G": 2,   # Fevereiro
        "H": 3,   # Marco
        "J": 4,   # Abril
        "K": 5,   # Maio
        "M": 6,   # Junho
        "N": 7,   # Julho
        "Q": 8,   # Agosto
        "U": 9,   # Setembro
        "V": 10,  # Outubro
        "X": 11,  # Novembro
        "Z": 12,  # Dezembro
    }

    # Mapeamento de prefixos especiais para o prefixo correto de busca
    # Ex: DI1F (vertice jan) busca com prefixo DI1F, não DI1
    # Ex: DI busca com prefixo DI1
    _PREFIX_MAP = {
        "DI": "DI1",
    }

    # Símbolos que são vértices de curva (ex: DI1F, DI1J, DI1N)
    # Eles usam o símbolo como prefixo direto (DI1F -> DI1F27, DI1F28, ...)
    _VERTEX_PATTERN = re.compile(r"^DI1[A-Z]$")

    def __init__(self, mt5_adapter: MT5Adapter) -> None:
        self._mt5 = mt5_adapter
        self._cache: dict[str, Optional[str]] = {}

    def resolve(self, base_symbol: str) -> Optional[str]:
        """Resolve o simbolo do contrato futuro vigente.

        Args:
            base_symbol: Simbolo base (ex: WDO, DI, DI1F, GLDG, ICF)

        Returns:
            Simbolo resolvido (ex: WDOG26, DI1F27) ou None se indisponivel.
        """
        if base_symbol in self._cache:
            return self._cache[base_symbol]

        resolved = self._try_resolve(base_symbol)
        self._cache[base_symbol] = resolved

        if resolved:
            logger.info(
                "Contrato futuro resolvido: %s -> %s", base_symbol, resolved
            )
        else:
            logger.warning(
                "Contrato futuro NAO resolvido: %s", base_symbol
            )

        return resolved

    def _try_resolve(self, base_symbol: str) -> Optional[str]:
        """Tenta resolver o simbolo usando as estrategias disponiveis."""
        # Estrategia 0: Tentar o simbolo diretamente
        # (para contratos especificos como DI1F27, DI1F29 que ja sao o contrato)
        if self._symbol_exists(base_symbol):
            return base_symbol

        # Aplicar mapeamento de prefixo (ex: DI -> DI1)
        search_prefix = self._PREFIX_MAP.get(base_symbol, base_symbol)

        # Estrategia 1: Contrato continuo $N
        continuous = f"{search_prefix}$N"
        if self._symbol_exists(continuous):
            return continuous

        # Estrategia 2: Para vertices de curva (ex: DI1F, DI1J, DI1N),
        # buscar o contrato do proximo vencimento desse vertice
        if self._VERTEX_PATTERN.match(base_symbol):
            return self._resolve_vertex(base_symbol)

        # Estrategia 3: Buscar simbolos com o prefixo
        return self._resolve_by_prefix(search_prefix, base_symbol)

    def _resolve_vertex(self, vertex_symbol: str) -> Optional[str]:
        """Resolve vertice de curva (ex: DI1F -> DI1F27, primeiro disponivel).

        Vertices como DI1F, DI1J, DI1N representam vencimentos especificos
        da curva de juros. Buscamos o proximo contrato desse vertice.
        """
        candidates = self._mt5.get_available_symbols(vertex_symbol)
        if not candidates:
            return None

        # Filtrar apenas contratos com ano (ex: DI1F27, DI1F28)
        contract_pattern = re.compile(
            rf"^{re.escape(vertex_symbol)}(\d{{2}})$"
        )
        valid = []
        now = datetime.now()
        current_yy = now.year % 100

        for sym in candidates:
            m = contract_pattern.match(sym)
            if m:
                year_suffix = int(m.group(1))
                # Incluir contratos do ano atual em diante
                if year_suffix >= current_yy:
                    valid.append((year_suffix, sym))

        if not valid:
            return None

        # Ordenar por ano e pegar o mais proximo
        valid.sort(key=lambda x: x[0])

        for _, candidate in valid:
            if self._symbol_exists(candidate):
                return candidate

        return None

    def _resolve_by_prefix(
        self, search_prefix: str, original_symbol: str
    ) -> Optional[str]:
        """Resolve futuro por busca de prefixo + selecao do mais proximo."""
        candidates = self._mt5.get_available_symbols(search_prefix)
        if not candidates:
            return None

        # Filtrar contratos futuros validos
        contract_pattern = re.compile(
            rf"^{re.escape(search_prefix)}[A-Z]\d{{2}}$"
        )
        now = datetime.now()
        current_yy = now.year % 100
        current_month = now.month

        future_candidates = []
        for sym in candidates:
            # Ignorar continuo, sufixos especiais, ETFs
            if sym.endswith(("$N", "$D", "$", "@", "@D", "@N")):
                continue
            if sym == original_symbol or sym == search_prefix:
                continue

            m = contract_pattern.match(sym)
            if m:
                # Extrair letra do mes e ano
                month_letter = sym[len(search_prefix)]
                year_suffix = int(sym[-2:])
                month_num = self.MONTH_CODES.get(month_letter, 0)

                if month_num == 0:
                    continue

                # Calcular distancia temporal
                if year_suffix > current_yy or (
                    year_suffix == current_yy and month_num >= current_month
                ):
                    sort_key = year_suffix * 100 + month_num
                    future_candidates.append((sort_key, sym))

        if not future_candidates:
            # Fallback: tentar qualquer candidato ordenado
            plain_candidates = [
                s for s in candidates
                if s != original_symbol
                and s != search_prefix
                and not s.endswith(("$N", "$D", "$", "@", "@D", "@N"))
                and len(s) > len(search_prefix)
            ]
            plain_candidates.sort()
            for candidate in plain_candidates[:5]:
                if self._symbol_exists(candidate):
                    return candidate
            return None

        # Ordenar por proximidade temporal (mais proximo primeiro)
        future_candidates.sort(key=lambda x: x[0])

        # Tentar habilitar e validar cada candidato
        for _, candidate in future_candidates[:5]:
            if self._symbol_exists(candidate):
                return candidate

        return None

    def _symbol_exists(self, symbol: str) -> bool:
        """Verifica se um simbolo existe e esta disponivel no MT5."""
        try:
            selected = self._mt5.select_symbol(symbol)
            if not selected:
                return False

            tick = self._mt5.get_symbol_info_tick(symbol)
            return tick is not None
        except Exception:
            return False

    def clear_cache(self) -> None:
        """Limpa o cache de resolucoes (usar no inicio de nova sessao)."""
        self._cache.clear()
