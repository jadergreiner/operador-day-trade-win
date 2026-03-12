#!/usr/bin/env python3
"""
Load Testing Script for Order Queue
Simula 100+ ordens/minuto e valida performance

Testa:
1. Throughput: 100+ ordens/min
2. Latencia P95: < 500ms
3. Consumo memoria: < 100MB
4. CPU: < 80%
5. Taxa de sucesso: > 99%

Usage:
    python load_test_order_queue.py --duration 60 --rate 100
    python load_test_order_queue.py --backend real --db data/db/trading.db
    python load_test_order_queue.py --profile-memory
"""

import argparse
import asyncio
import json
import logging
import tempfile
import time
import tracemalloc
import sys
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import psutil

ROOT_DIR = Path(__file__).resolve().parents[1]
if str(ROOT_DIR) not in sys.path:
    sys.path.append(str(ROOT_DIR))

from src.application.order_queue_sqlite import OrderQueue, Order

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s"
)
logger = logging.getLogger(__name__)


class LoadTestMetrics:
    """Coleta e analisa metricas de load test"""

    def __init__(self):
        self.timestamps: List[float] = []
        self.latencies: List[float] = []
        self.successes: int = 0
        self.failures: int = 0
        self.start_time = None
        self.end_time = None

    def add_latency(self, latency_ms: float):
        """Registra latencia de uma ordem"""
        self.latencies.append(latency_ms)
        self.timestamps.append(time.time())

    def success(self):
        self.successes += 1

    def failure(self):
        self.failures += 1

    def get_summary(self) -> Dict:
        """Retorna sumario de metricas"""
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
            "throughput_orders_per_min": round(
                (total_orders / ((self.end_time - self.start_time) / 60))
                if (self.end_time and self.start_time)
                else 0,
                2,
            ),
            "latency_min_ms": round(min(sorted_latencies), 2),
            "latency_max_ms": round(max(sorted_latencies), 2),
            "latency_mean_ms": round(
                sum(self.latencies) / len(self.latencies), 2
            ),
            "latency_p50_ms": round(
                sorted_latencies[len(sorted_latencies) // 2], 2
            ),
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
        """Simula adicao de ordem com latencia variavel"""
        # Simula latencia de 5-50ms
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

    def get_backend_name(self) -> str:
        return "mock"


class RealOrderQueue:
    """Wrapper async para OrderQueue real (SQLite)"""

    def __init__(self, db_path: str):
        self.queue = OrderQueue(db_path=db_path)

    async def add_order(self, order: Dict) -> bool:
        """Insere ordem real na fila"""
        order_obj = Order(
            order_id=str(order["id"]),
            symbol=order["symbol"],
            order_type=order["order_type"],
            volume=order["quantity"],
            price=order.get("price"),
            sl=order.get("sl"),
            tp=order.get("tp"),
            comment=order.get("comment", "load_test"),
        )
        return self.queue.push(order_obj)

    def get_queue_size(self) -> int:
        return self.queue.get_stats().get("PENDING", 0)

    def get_backend_name(self) -> str:
        return "real"


def _create_temp_db() -> Tuple[str, Optional[tempfile.NamedTemporaryFile]]:
    """Cria DB temporario para load test real."""
    temp = tempfile.NamedTemporaryFile(
        prefix="load_test_", suffix=".db", delete=False
    )
    return temp.name, temp


async def simulate_orders(
    queue,
    metrics: LoadTestMetrics,
    count: int,
    rate_per_minute: int,
):
    """Simula submissao de N ordens a uma taxa especifica"""
    interval = 60.0 / rate_per_minute if rate_per_minute > 0 else 0.0

    for i in range(count):
        order = {
            "id": i,
            "symbol": "ES",
            "quantity": 1.0,
            "order_type": "BUY",
            "timestamp": datetime.now().isoformat(),
        }

        # Mede latencia
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
        if interval > 0:
            await asyncio.sleep(interval)


async def run_load_test(
    duration_seconds: int = 60,
    target_rate_per_min: int = 100,
    failure_rate: float = 0.01,
    backend: str = "mock",
    db_path: Optional[str] = None,
    profile_memory: bool = False,
) -> Dict:
    """
    Executa load test por X segundos a Y ordens/minuto

    Args:
        duration_seconds: Duracao do teste
        target_rate_per_min: Alvo ordens/minuto
        failure_rate: Taxa de falhas simuladas (mock)
        backend: mock ou real
        db_path: caminho do banco para backend real
        profile_memory: ativa profiling com tracemalloc
    """

    logger.info("=" * 60)
    logger.info("LOAD TEST - Order Queue (P1-CORE Etapa 4)")
    logger.info("=" * 60)
    logger.info(f"Duration: {duration_seconds}s")
    logger.info(f"Target rate: {target_rate_per_min} ordens/min")
    logger.info(
        f"Expected total orders: {int(duration_seconds * target_rate_per_min / 60)}"
    )
    logger.info(f"Failure rate: {failure_rate * 100}%")
    logger.info(f"Backend: {backend}")
    logger.info("-" * 60)

    # Calcula total de ordens
    total_orders = max(1, int(duration_seconds * target_rate_per_min / 60))

    # Cria queue e metricas
    temp_handle = None
    if backend == "real":
        if not db_path:
            db_path, temp_handle = _create_temp_db()
        queue = RealOrderQueue(db_path=db_path)
    else:
        queue = MockOrderQueue(failure_rate=failure_rate)

    metrics = LoadTestMetrics()
    metrics.start_time = time.time()

    # Memory profiling
    if profile_memory:
        tracemalloc.start()

    # Monitora recursos antes
    process = psutil.Process()
    memory_before = process.memory_info().rss / 1024 / 1024  # MB
    cpu_start = process.cpu_percent(interval=1)

    logger.info(f"Memory before: {memory_before:.1f} MB")
    logger.info(f"CPU before: {cpu_start}%")
    logger.info("-" * 60)

    # Executa teste
    logger.info("Submitting orders...")
    await simulate_orders(queue, metrics, total_orders, target_rate_per_min)

    metrics.end_time = time.time()

    # Monitora recursos depois
    memory_after = process.memory_info().rss / 1024 / 1024  # MB
    cpu_end = process.cpu_percent(interval=1)
    memory_delta = memory_after - memory_before

    logger.info("-" * 60)
    logger.info(f"Memory after: {memory_after:.1f} MB (delta: {memory_delta:+.1f} MB)")
    logger.info(f"CPU after: {cpu_end}%")

    # Calcula sumario
    summary = metrics.get_summary()
    summary["memory_before_mb"] = round(memory_before, 1)
    summary["memory_after_mb"] = round(memory_after, 1)
    summary["memory_delta_mb"] = round(memory_delta, 1)
    summary["cpu_percent"] = float(cpu_end)
    summary["queue_final_size"] = queue.get_queue_size()
    summary["backend"] = queue.get_backend_name()
    summary["db_path"] = str(db_path) if db_path else None
    summary["rate_per_min"] = target_rate_per_min

    if profile_memory:
        current, peak = tracemalloc.get_traced_memory()
        stats = tracemalloc.take_snapshot().statistics("lineno")
        top_stats = []
        for stat in stats[:10]:
            top_stats.append(
                {
                    "file": str(stat.traceback[0].filename),
                    "line": stat.traceback[0].lineno,
                    "size_kb": round(stat.size / 1024, 2),
                }
            )
        memory_profile = {
            "current_kb": round(current / 1024, 2),
            "peak_kb": round(peak / 1024, 2),
            "top_allocations": top_stats,
        }
        summary["memory_profile"] = memory_profile
        output_dir = Path("outputs")
        output_dir.mkdir(exist_ok=True, parents=True)
        profile_path = output_dir / f"memory_profile_{int(time.time())}.json"
        with open(profile_path, "w", encoding="utf-8") as f:
            json.dump(memory_profile, f, indent=2)
        summary["memory_profile_path"] = str(profile_path)
        tracemalloc.stop()

    if temp_handle:
        try:
            temp_handle.close()
        except Exception:
            pass

    return summary


def validate_results(summary: Dict) -> bool:
    """Valida se os resultados atendem criterios de aceitacao"""

    logger.info("-" * 60)
    logger.info("VALIDATION RESULTS")
    logger.info("-" * 60)

    checks = {
        "Success Rate >= 99%": summary["success_rate_percent"] >= 99.0,
        "P95 Latency < 500ms": summary["latency_p95_ms"] < 500,
        "Memory increase < 50MB": summary["memory_delta_mb"] < 50,
        "CPU < 80%": summary["cpu_percent"] < 80,
        "Throughput >= 100 ord/min": summary["throughput_orders_per_min"] >= 100,
    }

    all_passed = True
    for check_name, result in checks.items():
        status = "PASS" if result else "FAIL"
        logger.info(f"{status}: {check_name}")
        if not result:
            all_passed = False

    return all_passed


def print_summary(summary: Dict):
    """Imprime sumario formatado"""

    logger.info("-" * 60)
    logger.info("METRICS SUMMARY")
    logger.info("-" * 60)
    logger.info(f"Total Orders:          {summary['total_orders']}")
    logger.info(f"Successful:            {summary['successful']}")
    logger.info(f"Failed:                {summary['failed']}")
    logger.info(f"Success Rate:          {summary['success_rate_percent']:.1f}%")
    logger.info(f"Duration:              {summary['duration_seconds']:.1f}s")
    logger.info(
        f"Throughput:            {summary['throughput_orders_per_min']:.1f} ord/min"
    )
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
    if "memory_profile" in summary:
        logger.info(f"Memory Peak:           {summary['memory_profile']['peak_kb']} KB")


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
        help="Target orders per minute (default: 100)",
    )
    parser.add_argument(
        "--failure",
        type=float,
        default=0.01,
        help="Simulated failure rate (default: 0.01 = 1%)",
    )
    parser.add_argument(
        "--backend",
        type=str,
        default="mock",
        choices=["mock", "real"],
        help="Backend: mock or real (OrderQueue + SQLite)",
    )
    parser.add_argument(
        "--db",
        type=str,
        default=None,
        help="Database path for real backend (optional)",
    )
    parser.add_argument(
        "--profile-memory",
        action="store_true",
        help="Enable memory profiling with tracemalloc",
    )

    args = parser.parse_args()

    # Executa teste
    summary = await run_load_test(
        duration_seconds=args.duration,
        target_rate_per_min=args.rate,
        failure_rate=args.failure,
        backend=args.backend,
        db_path=args.db,
        profile_memory=args.profile_memory,
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
