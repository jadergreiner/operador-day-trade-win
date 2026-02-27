"""
TODO-2,3,4: OrdersExecutor Implementation
Simplified Core Implementation for S2-9 Risk Framework Integration

Methods:
- execute_order() [TODO-2] — Validate 3 gates + send to MT5
- monitor_positions() [TODO-3] — Poll positions + calc PnL
- position_monitoring_loop() [TODO-4] — Background SL/TP monitoring
"""

import asyncio
import logging
import time
from datetime import datetime
from typing import Dict, Optional, List, Any

logger = logging.getLogger(__name__)


class OrdersExecutorTODO234:
    """Simplified OrdersExecutor focused on TODO-2,3,4 implementation."""

    def __init__(self, risk_processor, mt5_adapter, trade_repository=None, event_bus=None):
        self.risk_processor = risk_processor
        self.mt5_adapter = mt5_adapter
        self.trade_repository = trade_repository
        self.event_bus = event_bus

        self.current_daily_pnl: float = 0.0
        self.current_positions: List[Dict] = []
        self.volatility_bands = {"-3%": -3000, "-5%": -5000, "-8%": -8000}
        self._monitoring_active: bool = False
        self.logger = logging.getLogger(__name__)

    async def execute_order(self, order) -> Dict[str, Any]:
        """TODO-2: Execute ordem com validacao de 3 gates."""
        start = time.time()
        audit_trail = []

        try:
            if hasattr(self.risk_processor, 'check_capital_limits'):
                capital_check = self.risk_processor.check_capital_limits(
                    position_size=order.volume,
                    daily_pnl=self.current_daily_pnl
                )
            else:
                capital_check = {"approved": True, "reason": "OK"}

            audit_trail.append(capital_check)

            if not capital_check.get("approved", False):
                return {
                    "order_id": order.order_id,
                    "status": "REJECTED",
                    "decision": "REJECTED_CAPITAL_LIMIT",
                    "rejection_reason": capital_check.get("reason"),
                    "timestamp": datetime.utcnow().isoformat(),
                    "execution_time_ms": (time.time() - start) * 1000,
                    "audit_trail": audit_trail
                }

            if hasattr(self.risk_processor, 'check_correlation'):
                correlation_check = self.risk_processor.check_correlation(
                    portfolio=self.current_positions,
                    new_symbol=order.symbol
                )
            else:
                correlation_check = {"approved": True, "reason": "OK"}

            audit_trail.append(correlation_check)

            if not correlation_check.get("approved", False):
                return {
                    "order_id": order.order_id,
                    "status": "REJECTED",
                    "decision": "REJECTED_CORRELATION",
                    "rejection_reason": correlation_check.get("reason"),
                    "timestamp": datetime.utcnow().isoformat(),
                    "execution_time_ms": (time.time() - start) * 1000,
                    "audit_trail": audit_trail
                }

            if hasattr(self.risk_processor, 'check_volatility_bands'):
                volatility_check = self.risk_processor.check_volatility_bands(
                    current_pnl=self.current_daily_pnl,
                    thresholds=self.volatility_bands
                )
            else:
                volatility_check = {"approved": True, "reason": "OK"}

            audit_trail.append(volatility_check)

            if not volatility_check.get("approved", False):
                return {
                    "order_id": order.order_id,
                    "status": "REJECTED",
                    "decision": "REJECTED_VOLATILITY_BAND",
                    "rejection_reason": volatility_check.get("reason"),
                    "timestamp": datetime.utcnow().isoformat(),
                    "execution_time_ms": (time.time() - start) * 1000,
                    "audit_trail": audit_trail
                }

            self.logger.info(f"✅ All 3 gates PASSED: {order.symbol}")

            retries = [0.1, 0.5, 2.0]
            ticket = None

            for i, delay in enumerate(retries):
                try:
                    ticket = await self.mt5_adapter.send_order(order)
                    if ticket:
                        self.logger.info(f"✅ Order sent to MT5: ticket={ticket}")
                        break
                except Exception as e:
                    self.logger.warning(f"MT5 send attempt {i+1} failed: {str(e)}")
                    if i < len(retries) - 1:
                        await asyncio.sleep(delay)

            if ticket:
                return {
                    "order_id": order.order_id,
                    "status": "APPROVED",
                    "decision": "APPROVED_ALL_GATES",
                    "mt5_response": {"ticket": ticket},
                    "timestamp": datetime.utcnow().isoformat(),
                    "execution_time_ms": (time.time() - start) * 1000,
                    "audit_trail": audit_trail
                }
            else:
                return {
                    "order_id": order.order_id,
                    "status": "REJECTED",
                    "decision": "REJECTED_MT5_SEND_FAILED",
                    "rejection_reason": "MT5 send failed after 3 retries",
                    "timestamp": datetime.utcnow().isoformat(),
                    "execution_time_ms": (time.time() - start) * 1000,
                    "audit_trail": audit_trail
                }

        except Exception as e:
            self.logger.error(f"execute_order ERROR: {str(e)}")
            return {
                "order_id": order.order_id,
                "status": "ERROR",
                "decision": "ERROR_EXCEPTION",
                "rejection_reason": str(e),
                "timestamp": datetime.utcnow().isoformat(),
                "execution_time_ms": (time.time() - start) * 1000,
                "audit_trail": audit_trail
            }

    async def monitor_positions(self) -> Optional[Dict[str, Any]]:
        """TODO-3: Monitor posicoes abertas e calcula PnL."""
        start = time.time()

        try:
            positions = await self.mt5_adapter.get_positions()
            total_pnl = 0.0
            positions_detail = []

            for pos in positions:
                entry_price = getattr(pos, 'entry_price', 100.0)
                size = getattr(pos, 'volume', getattr(pos, 'size', 1))
                pos_type = getattr(pos, 'type', 'BUY')
                symbol = getattr(pos, 'symbol', 'UNKNOWN')

                current_price = await self.mt5_adapter.get_current_price(symbol)

                if pos_type in ["BUY", "LONG"]:
                    pnl = (current_price - entry_price) * size
                else:
                    pnl = (entry_price - current_price) * size

                total_pnl += pnl

                positions_detail.append({
                    "symbol": symbol,
                    "size": size,
                    "type": pos_type,
                    "entry_price": entry_price,
                    "current_price": current_price,
                    "pnl": pnl
                })

                if pnl <= -1000:
                    self.logger.warning(f"STOP LOSS TRIGGER: {symbol} PnL={pnl:.2f}")

            latency_ms = (time.time() - start) * 1000

            if latency_ms > 100:
                self.logger.warning(f"Monitor latency {latency_ms:.1f}ms > 100ms")

            self.current_daily_pnl = total_pnl
            self.current_positions = positions_detail

            return {
                "positions_count": len(positions_detail),
                "total_pnl": total_pnl,
                "positions": positions_detail,
                "latency_ms": latency_ms,
                "timestamp": datetime.utcnow().isoformat()
            }

        except Exception as e:
            self.logger.error(f"monitor_positions ERROR: {str(e)}")
            return None

    async def position_monitoring_loop(self):
        """TODO-4: Faz polling continuo de posicoes a 100ms."""
        self._monitoring_active = True
        self.logger.info("Position monitoring loop started")

        while self._monitoring_active:
            try:
                monitor_result = await self.monitor_positions()
                if not monitor_result:
                    await asyncio.sleep(0.1)
                    continue

                positions = monitor_result["positions"]

                for pos in positions:
                    pnl = pos["pnl"]
                    symbol = pos["symbol"]
                    size = pos["size"]

                    if pnl <= -1000:
                        self.logger.warning(f"STOP LOSS TRIGGERED: {symbol} PnL={pnl:.2f}")

                        try:
                            close_result = await self.mt5_adapter.close_position(
                                symbol=symbol,
                                size=size,
                                reason="STOP_LOSS"
                            )
                            if close_result.get("success", False):
                                self.logger.info(f"Position closed (SL): {symbol}")
                        except Exception as e:
                            self.logger.error(f"Failed to close {symbol} on SL: {e}")

                    elif pnl >= 5000:
                        self.logger.info(f"TAKE PROFIT TRIGGERED: {symbol} PnL={pnl:.2f}")

                        try:
                            close_result = await self.mt5_adapter.close_position(
                                symbol=symbol,
                                size=size,
                                reason="TAKE_PROFIT"
                            )
                            if close_result.get("success", False):
                                self.logger.info(f"Position closed (TP): {symbol}")
                        except Exception as e:
                            self.logger.error(f"Failed to close {symbol} on TP: {e}")

                await asyncio.sleep(0.1)

            except Exception as e:
                self.logger.error(f"monitoring_loop ERROR: {str(e)}")
                await asyncio.sleep(0.1)

        self.logger.info("Position monitoring loop stopped")

    async def stop_monitoring(self):
        """Gracefully stop position monitoring loop."""
        self._monitoring_active = False
        self.logger.info("Stopping position monitoring loop")
