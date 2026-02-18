"""
Volume Analysis Service - Compares current volume with historical average.

Provides volume context for journal entries and trading decisions.
"""

from decimal import Decimal
from typing import Optional, Tuple, TYPE_CHECKING

if TYPE_CHECKING:
    from src.infrastructure.adapters.mt5_adapter import Candle


class VolumeAnalysisService:
    """Service for analyzing volume patterns."""

    @staticmethod
    def calculate_volume_metrics(
        candles: list,  # list[Candle]
        candles_per_day: int = 84,  # 7 hours * 12 candles/hour (5min candles)
    ) -> Tuple[Optional[int], Optional[int], Optional[Decimal]]:
        """
        Calculate volume metrics comparing today with previous days.

        Args:
            candles: List of candles (most recent at end)
            candles_per_day: Number of candles per trading day

        Returns:
            Tuple of (volume_today, volume_avg_3days, volume_variance_pct)
            Returns (None, None, None) if insufficient data
        """
        if not candles:
            return None, None, None

        # Need at least 4 days of data to compare
        if len(candles) < candles_per_day * 4:
            # Not enough historical data
            volume_today = sum(c.volume for c in candles)
            return volume_today, None, None

        try:
            # Split data into daily segments
            day1_candles = candles[-candles_per_day * 4 : -candles_per_day * 3]
            day2_candles = candles[-candles_per_day * 3 : -candles_per_day * 2]
            day3_candles = candles[-candles_per_day * 2 : -candles_per_day]
            today_candles = candles[-candles_per_day:]

            # Calculate volumes
            volume_day1 = sum(c.volume for c in day1_candles)
            volume_day2 = sum(c.volume for c in day2_candles)
            volume_day3 = sum(c.volume for c in day3_candles)
            volume_today = sum(c.volume for c in today_candles)

            # Average of previous 3 days
            volume_avg_3days = int((volume_day1 + volume_day2 + volume_day3) / 3)

            # Calculate variance percentage
            if volume_avg_3days > 0:
                variance = (
                    (volume_today - volume_avg_3days) / volume_avg_3days * 100
                )
                volume_variance_pct = Decimal(str(variance))
            else:
                volume_variance_pct = Decimal("0")

            return volume_today, volume_avg_3days, volume_variance_pct

        except Exception:
            # If any error in calculation, return what we have
            volume_today = sum(c.volume for c in candles)
            return volume_today, None, None

    @staticmethod
    def get_volume_interpretation(volume_variance_pct: Optional[Decimal]) -> str:
        """
        Get text interpretation of volume variance.

        Args:
            volume_variance_pct: Volume variance percentage vs 3-day average

        Returns:
            Text interpretation
        """
        if volume_variance_pct is None:
            return "Dados insuficientes para comparacao"

        if volume_variance_pct > Decimal("20"):
            return f"Volume {volume_variance_pct:+.1f}% ACIMA da media - ALTA conviccao"
        elif volume_variance_pct < Decimal("-20"):
            return f"Volume {volume_variance_pct:+.1f}% ABAIXO da media - BAIXA conviccao"
        else:
            return f"Volume {volume_variance_pct:+.1f}% vs media - NORMAL"

    @staticmethod
    def is_volume_price_divergence(
        price_change_pct: Decimal, volume_variance_pct: Optional[Decimal]
    ) -> bool:
        """
        Check if there's a volume/price divergence (potential trap).

        Args:
            price_change_pct: Price change percentage
            volume_variance_pct: Volume variance percentage

        Returns:
            True if divergence detected (price moves but volume low)
        """
        if volume_variance_pct is None:
            return False

        # Strong price move with low volume = divergence/trap
        return abs(price_change_pct) > 0.5 and volume_variance_pct < Decimal("-20")
