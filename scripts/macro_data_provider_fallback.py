#!/usr/bin/env python3
"""
FIX #3: Redundância para dados macro - Sistema de fallback estratégico.

Implementa:
1. BCB SGS (primary) - dados macro Brasil
2. Yahoo Finance (fallback 1) - DXY, VIX via yfinance
3. Hardcoded (fallback 2) - valores default confiáveis
4. Cache (fallback 3) - dados da execução anterior

Execução automática em start_journals_full_display.py
"""

import os
import json
from pathlib import Path
from decimal import Decimal
from datetime import datetime
from typing import Optional, Dict
import logging

logger = logging.getLogger(__name__)

PROJECT_ROOT = Path(__file__).parent.parent
DATA_DIR = PROJECT_ROOT / "data"
CACHE_FILE = DATA_DIR / "macro_cache_latest.json"


# ============================================================================
# Valores defaults - Market-based, não hardcoded arbitrariamente
# ============================================================================
DEFAULT_MACRO_VALUES = {
    "dxy": Decimal("104.30"),  # Historical avg ~104
    "vix": Decimal("18.50"),   # Historical avg ~18
    "selic": Decimal("10.75"),  # Current year rate
    "ipca": Decimal("4.50"),    # Current inflation estimate
    "usd_brl": Decimal("5.85"), # Current spot rate 2026
}


class MacroDataProvider:
    """Fallback-based macro data provider with multiple sources."""

    def __init__(self):
        """Initialize provider."""
        self.cache = self._load_cache()
        self.last_update = None

    def _load_cache(self) -> Dict:
        """Load cached values from last successful fetch."""
        if CACHE_FILE.exists():
            try:
                with open(CACHE_FILE, "r") as f:
                    return json.load(f)
            except (json.JSONDecodeError, IOError):
                return {}
        return {}

    def _save_cache(self, data: Dict) -> None:
        """Save data to cache."""
        try:
            DATA_DIR.mkdir(parents=True, exist_ok=True)
            with open(CACHE_FILE, "w") as f:
                json.dump(data, f, indent=2, default=str)
        except Exception as e:
            logger.warning(f"Cache save failed: {e}")

    # ========================================================================
    # Source 1: BCB SGS API (Brazil Central Bank)
    # ========================================================================
    def _get_bcb_selic(self) -> Optional[Decimal]:
        """Get SELIC rate from BCB."""
        try:
            import requests
            response = requests.get(
                "https://api.bcb.gov.br/dados/serie/bcdata.sgs.11/dados/ultimos/1",
                timeout=3
            )
            if response.status_code == 200:
                data = response.json()
                if data and len(data) > 0:
                    return Decimal(str(data[0]["valor"]))
        except Exception as e:
            logger.debug(f"BCB SELIC fetch failed: {e}")
        return None

    def _get_bcb_ipca(self) -> Optional[Decimal]:
        """Get IPCA from BCB."""
        try:
            import requests
            response = requests.get(
                "https://api.bcb.gov.br/dados/serie/bcdata.sgs.433/dados/ultimos/1",
                timeout=3
            )
            if response.status_code == 200:
                data = response.json()
                if data and len(data) > 0:
                    return Decimal(str(data[0]["valor"]))
        except Exception as e:
            logger.debug(f"BCB IPCA fetch failed: {e}")
        return None

    def _get_bcb_usd_brl(self) -> Optional[Decimal]:
        """Get USD/BRL from BCB."""
        try:
            import requests
            response = requests.get(
                "https://api.bcb.gov.br/dados/serie/bcdata.sgs.1/dados/ultimos/1",
                timeout=3
            )
            if response.status_code == 200:
                data = response.json()
                if data and len(data) > 0:
                    return Decimal(str(data[0]["valor"]))
        except Exception as e:
            logger.debug(f"BCB USD/BRL fetch failed: {e}")
        return None

    # ========================================================================
    # Source 2: Yahoo Finance (DXY, VIX)
    # ========================================================================
    def _get_fred_dxy(self) -> Optional[Decimal]:
        """Get DXY from Yahoo Finance."""
        try:
            import yfinance as yf
            ticker = yf.Ticker("DXY=F")
            data = ticker.history(period="1d")
            if not data.empty:
                close = data["Close"].iloc[-1]
                return Decimal(str(close))
        except Exception as e:
            logger.debug(f"Yahoo DXY fetch failed: {e}")
        return None

    def _get_fred_vix(self) -> Optional[Decimal]:
        """Get VIX from Yahoo Finance."""
        try:
            import yfinance as yf
            ticker = yf.Ticker("^VIX")
            data = ticker.history(period="1d")
            if not data.empty:
                close = data["Close"].iloc[-1]
                return Decimal(str(close))
        except Exception as e:
            logger.debug(f"Yahoo VIX fetch failed: {e}")
        return None

    def _get_bcb_embi(self) -> Optional[Decimal]:
        """Get EMBI from BCB (Brazil sovereign risk)."""
        try:
            import requests
            response = requests.get(
                "https://api.bcb.gov.br/dados/serie/bcdata.sgs.40940/dados/ultimos/1",
                timeout=3
            )
            if response.status_code == 200:
                data = response.json()
                if data and len(data) > 0:
                    return Decimal(str(data[0]["valor"]))
        except Exception as e:
            logger.debug(f"BCB EMBI fetch failed: {e}")
        return None

    # ========================================================================
    # Source 3: Cache (previous successful values)
    # ========================================================================
    def _get_cached_value(self, key: str) -> Optional[Decimal]:
        """Get value from cache."""
        if key in self.cache:
            try:
                return Decimal(str(self.cache[key]))
            except (ValueError, TypeError):
                return None
        return None

    # ========================================================================
    # Main fetch with fallback chain
    # ========================================================================
    def fetch_dxy(self) -> Decimal:
        """
        Fetch DXY with fallback chain:
        1. Yahoo Finance
        2. Cache
        3. Default
        """
        # Try Yahoo
        val = self._get_fred_dxy()
        if val:
            self.cache["dxy"] = str(val)
            return val

        # Try cache
        val = self._get_cached_value("dxy")
        if val:
            return val

        # Fallback to default
        logger.warning("DXY: Using default value")
        return DEFAULT_MACRO_VALUES["dxy"]

    def fetch_vix(self) -> Decimal:
        """
        Fetch VIX with fallback chain:
        1. Yahoo Finance
        2. Cache
        3. Default
        """
        # Try Yahoo
        val = self._get_fred_vix()
        if val:
            self.cache["vix"] = str(val)
            return val

        # Try cache
        val = self._get_cached_value("vix")
        if val:
            return val

        # Fallback
        logger.warning("VIX: Using default value")
        return DEFAULT_MACRO_VALUES["vix"]

    def fetch_selic(self) -> Decimal:
        """
        Fetch SELIC with fallback chain:
        1. BCB SGS
        2. Cache
        3. Default
        """
        # Try BCB
        val = self._get_bcb_selic()
        if val:
            self.cache["selic"] = str(val)
            return val

        # Try cache
        val = self._get_cached_value("selic")
        if val:
            return val

        # Fallback
        logger.warning("SELIC: Using default value")
        return DEFAULT_MACRO_VALUES["selic"]

    def fetch_ipca(self) -> Decimal:
        """
        Fetch IPCA with fallback chain:
        1. BCB SGS
        2. Cache
        3. Default
        """
        # Try BCB
        val = self._get_bcb_ipca()
        if val:
            self.cache["ipca"] = str(val)
            return val

        # Try cache
        val = self._get_cached_value("ipca")
        if val:
            return val

        # Fallback
        logger.warning("IPCA: Using default value")
        return DEFAULT_MACRO_VALUES["ipca"]

    def fetch_usd_brl(self) -> Decimal:
        """
        Fetch USD/BRL with fallback chain:
        1. BCB SGS
        2. Cache
        3. Default
        """
        # Try BCB
        val = self._get_bcb_usd_brl()
        if val:
            self.cache["usd_brl"] = str(val)
            return val

        # Try cache
        val = self._get_cached_value("usd_brl")
        if val:
            return val

        # Fallback
        logger.warning("USD/BRL: Using default value")
        return DEFAULT_MACRO_VALUES["usd_brl"]

    def fetch_embi_spread(self) -> Decimal:
        """
        Fetch EMBI with fallback chain:
        1. BCB SGS
        2. Cache
        3. Default (250)
        """
        # Try BCB
        val = self._get_bcb_embi()
        if val:
            self.cache["embi_spread"] = str(val)
            return val

        # Try cache
        val = self._get_cached_value("embi_spread")
        if val:
            return val

        # Default: use reasonable spread
        logger.warning("EMBI: Using default value (250)")
        return Decimal("250")

    def fetch_all(self) -> Dict[str, Decimal]:
        """Fetch all macro data with fallback protection."""
        data = {
            "dxy": self.fetch_dxy(),
            "vix": self.fetch_vix(),
            "selic": self.fetch_selic(),
            "ipca": self.fetch_ipca(),
            "usd_brl": self.fetch_usd_brl(),
            "embi_spread": self.fetch_embi_spread(),
        }

        # Save updated cache
        self._save_cache({k: str(v) for k, v in data.items()})
        self.last_update = datetime.now()

        return data


# Singleton instance
_provider = None


def get_macro_provider() -> MacroDataProvider:
    """Get or create macro provider."""
    global _provider
    if _provider is None:
        _provider = MacroDataProvider()
    return _provider


if __name__ == "__main__":
    # Test the provider
    print("=" * 70)
    print("MACRO DATA PROVIDER - FIX #3 Fallback Test")
    print("=" * 70)

    provider = get_macro_provider()
    data = provider.fetch_all()

    print("\nFetched macro data:")
    for key, val in data.items():
        print(f"  {key:15} = {val}")

    print("\nCache saved to:", CACHE_FILE)
    print("✅ Fallback system operational")
