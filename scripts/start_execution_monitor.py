#!/usr/bin/env python3
"""
Start Execution Monitor (AC5.8)
"""

import argparse
import asyncio
import os
import sys
from pathlib import Path

root_dir = Path(__file__).parent.parent
if str(root_dir) not in sys.path:
    sys.path.insert(0, str(root_dir))

from src.infrastructure.ati1_broadcast_client import Ati1BroadcastClient
from src.infrastructure.execution_monitor import ExecutionMonitor, ExecutionMonitorConfig


def parse_args():
    parser = argparse.ArgumentParser(description="Start Execution Monitor")
    parser.add_argument("--db", default="data/db/trading.db")
    parser.add_argument("--trader-id", default="TRADER_001")
    parser.add_argument("--ati1-url", default="http://127.0.0.1:8000")
    parser.add_argument("--ati1-token", default=None)
    return parser.parse_args()


async def main():
    args = parse_args()
    token = args.ati1_token or os.getenv("ATI1_BROADCAST_TOKEN")

    client = Ati1BroadcastClient(base_url=args.ati1_url, token=token)
    config = ExecutionMonitorConfig(
        db_path=args.db,
        trader_id=args.trader_id,
    )

    monitor = ExecutionMonitor(ati1_client=client, config=config)
    await monitor.start()

    # Run forever
    while True:
        await asyncio.sleep(1)


if __name__ == "__main__":
    asyncio.run(main())
