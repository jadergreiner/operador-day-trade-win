#!/usr/bin/env python3
"""
Load Testing Script for Order Queue
Simulates 100+ orders/minute and validates performance

Testa:
1. Throughput: 100+ ordens/min
2. Latência P95: < 500ms
3. Consumo memória: < 100MB
4. CPU: < 80%
5. Taxa de sucesso: > 99%

Usage:
    python load_test_order_queue.py --duration 60 --rate 100
    python load_test_order_queue.py --help
"""

import asyncio
import json
import time
import psutil
import argparse
from datetime import datetime, timedelta
from pathlib import Path
from typing import List, Dict
import logging

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s"
)
logger = logging.getLogger(__name__)


class LoadTestMetrics:
    """Coleta e analisa métricas de load test"""

    def __init__(self):
        self.timestamps: List[float] = []
        self.latencies: List[float] = []
        self.successes: int = 0
        self.failures: int = 0
        self.start_time = None
        self.end_time = None

    def add_latency(self, latency_ms: float):
        """Registra latência de uma ordem"""
        self.latencies.append(latency_ms)
        self.timestamps.append(time.time())

    def success(self):
        self.successes += 1

    def failure(self):
        self.failures += 1

    def get_summary(self) -> Dict:
        """Retorna sumário de métricas"""
        if not self.latencies:
            return {}

        sorted_latencies = sorted(self.latencies)
        total_orders = len(self.latencies)
        success_rate = (
            self.successes / (self.successes + self.failures) * 100
            if (self.successes + self.failures) > 0
            else 0
        )

        return {
            "total_orders": total_orders,
            "successful": self.successes,
            "failed": self.failures,
            "success_rate_percent": round(success_rate, 2),
            "duration_seconds": (
                self.end_time - self.start_time
                if self.end_time and self.start_time
                else 0
            ),
            "throughput_orders_per_sec": round(
                total_orders
                / (self.end_time - self.start_time)
                if (self.end_time and self.start_time)
                else 0,
                2,
            ),
            "latency_min_ms": round(min(sorted_latencies), 2),
            "latency_max_ms": round(max(sorted_latencies), 2),
            "latency_mean_ms": round(
                sum(self.latencies) / len(self.latencies), 2
            ),
            "latency_p50_ms": round(sorted_latencies[len(sorted_latencies) // 2], 2),
            "latency_p95_ms": round(
                sorted_latencies[int(len(sorted_latencies) * 0.95)], 2
            ),
            "latency_p99_ms": round(
                sorted_latencies[int(len(sorted_latencies) * 0.99)], 2
            ),
        }


class MockOrderQueue:
    """Mock do queue processor para testes"""

    def __init__(self, failure_rate: float = 0.01):
        self.orders: List[Dict] = []
        self.failure_rate = failure_rate

    async def add_order(self, order: Dict) -> bool:
        """Simula adição de ordem com latência variável"""
        # Simula latência de 5-50ms
        latency = 0.005 + (hash(str(order)) % 45) / 1000
        await asyncio.sleep(latency)

        # Simula falhas ocasionais
        import random
        if random.random() < self.failure_rate:
            return False

        self.orders.append(order)
        return True

    def get_queue_size(self) -> int:
        return len(self.orders)


async def simulate_orders(
    queue: MockOrderQueue,
    metrics: LoadTestMetrics,
    count: int,
    rate_per_second: int,
):
    """Simula submissão de N ordens a uma taxa específica"""
    interval = 1.0 / rate_per_second

    for i in range(count):
        order = {
            "id": i,
            "symbol": "ES",
            "quantity": 1,
            "timestamp": datetime.now().isoformat(),
        }

        # Mede latência
        start = time.perf_counter()
        success = await queue.add_order(order)
        elapsed_ms = (time.perf_counter() - start) * 1000

        if success:
            metrics.success()
        else:
            metrics.failure()

        metrics.add_latency(elapsed_ms)

        if i % 100 == 0:
            logger.info(f"    [{i}/{count}] ordens adicionadas")

        # Controla taxa: aguarda interval entre ordens
        await asyncio.sleep(interval)


async def run_load_test(
    duration_seconds: int = 60,
    target_rate: int = 100,
    failure_rate: float = 0.01,
) -> Dict:
    """
    Executa load test por X segundos a Y ordens/segundo

    Args:
        duration_seconds: Duração do teste
        target_rate: Alvo ordens/segundo
        failure_rate: Taxa de falhas simuladas

    Returns:
        Dicionário com resultados
    """

    logger.info("=" * 60)
    logger.info("LOAD TEST - Order Queue (P1-CORE Etapa 4)")
    logger.info("=" * 60)
    logger.info(f"Duration: {duration_seconds}s")
    logger.info(f"Target rate: {target_rate} ordens/seg")
    logger.info(f"Expected total orders: {duration_seconds * target_rate}")
    logger.info(f"Failure rate: {failure_rate * 100}%")
    logger.info("-" * 60)

    # Calcula total de ordens
    total_orders = duration_seconds * target_rate

    # Cria queue e métricas
    queue = MockOrderQueue(failure_rate=failure_rate)
    metrics = LoadTestMetrics()
    metrics.start_time = time.time()

    # Monitora recursos antes
    process = psutil.Process()
    memory_before = process.memory_info().rss / 1024 / 1024  # MB
    cpu_start = process.cpu_percent(interval=1)

    logger.info(f"Memory before: {memory_before:.1f} MB")
    logger.info(f"CPU before: {cpu_start}%")
    logger.info("-" * 60)

    # Executa teste
    logger.info("Submitting orders...")
    await simulate_orders(queue, metrics, total_orders, target_rate)

    metrics.end_time = time.time()

    # Monitora recursos depois
    memory_after = process.memory_info().rss / 1024 / 1024  # MB
    cpu_end = process.cpu_percent(interval=1)
    memory_delta = memory_after - memory_before

    logger.info("-" * 60)
    logger.info(f"Memory after: {memory_after:.1f} MB (delta: {memory_delta:+.1f} MB)")
    logger.info(f"CPU after: {cpu_end}%")

    # Calcula sumário
    summary = metrics.get_summary()
    summary["memory_before_mb"] = round(memory_before, 1)
    summary["memory_after_mb"] = round(memory_after, 1)
    summary["memory_delta_mb"] = round(memory_delta, 1)
    summary["cpu_percent"] = float(cpu_end)
    summary["queue_final_size"] = queue.get_queue_size()

    return summary


def validate_results(summary: Dict) -> bool:
    """Valida se os resultados atendem critérios de aceitação"""

    logger.info("-" * 60)
    logger.info("VALIDATION RESULTS")
    logger.info("-" * 60)

    checks = {
        "Success Rate >= 99%": summary["success_rate_percent"] >= 99.0,
        "P95 Latency < 500ms": summary["latency_p95_ms"] < 500,
        "Memory increase < 50MB": summary["memory_delta_mb"] < 50,
        "CPU < 80%": summary["cpu_percent"] < 80,
        "Throughput >= 100 ord/sec": summary["throughput_orders_per_sec"] >= 100,
    }

    all_passed = True
    for check_name, result in checks.items():
        status = "✅ PASS" if result else "❌ FAIL"
        logger.info(f"{status}: {check_name}")
        if not result:
            all_passed = False

    return all_passed


def print_summary(summary: Dict):
    """Imprime sumário formatado"""

    logger.info("-" * 60)
    logger.info("METRICS SUMMARY")
    logger.info("-" * 60)
    logger.info(f"Total Orders:          {summary['total_orders']}")
    logger.info(f"Successful:            {summary['successful']}")
    logger.info(f"Failed:                {summary['failed']}")
    logger.info(f"Success Rate:          {summary['success_rate_percent']:.1f}%")
    logger.info(f"Duration:              {summary['duration_seconds']:.1f}s")
    logger.info(f"Throughput:            {summary['throughput_orders_per_sec']:.1f} ord/s")
    logger.info("-" * 60)
    logger.info(f"Latency Min:           {summary['latency_min_ms']:.1f}ms")
    logger.info(f"Latency Max:           {summary['latency_max_ms']:.1f}ms")
    logger.info(f"Latency Mean:          {summary['latency_mean_ms']:.1f}ms")
    logger.info(f"Latency P50:           {summary['latency_p50_ms']:.1f}ms")
    logger.info(f"Latency P95:           {summary['latency_p95_ms']:.1f}ms")
    logger.info(f"Latency P99:           {summary['latency_p99_ms']:.1f}ms")
    logger.info("-" * 60)
    logger.info(f"Memory Before:         {summary['memory_before_mb']:.1f}MB")
    logger.info(f"Memory After:          {summary['memory_after_mb']:.1f}MB")
    logger.info(f"Memory Increase:       {summary['memory_delta_mb']:+.1f}MB")
    logger.info(f"CPU:                   {summary['cpu_percent']:.0f}%")
    logger.info(f"Queue Final Size:      {summary['queue_final_size']}")


async def main():
    parser = argparse.ArgumentParser(
        description="Load test for Order Queue"
    )
    parser.add_argument(
        "--duration",
        type=int,
        default=60,
        help="Duration in seconds (default: 60)",
    )
    parser.add_argument(
        "--rate",
        type=int,
        default=100,
        help="Target orders per second (default: 100)",
    )
    parser.add_argument(
        "--failure",
        type=float,
        default=0.01,
        help="Simulated failure rate (default: 0.01 = 1%)",
    )

    args = parser.parse_args()

    # Executa teste
    summary = await run_load_test(
        duration_seconds=args.duration,
        target_rate=args.rate,
        failure_rate=args.failure,
    )

    # Imprime resultados
    print_summary(summary)
    all_passed = validate_results(summary)

    # Salva resultados
    output_file = Path("outputs") / f"load_test_results_{int(time.time())}.json"
    output_file.parent.mkdir(exist_ok=True, parents=True)
    with open(output_file, "w") as f:
        json.dump(summary, f, indent=2)
    logger.info(f"\nResults saved to: {output_file}")

    # Exit code
    return 0 if all_passed else 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    exit(exit_code)
