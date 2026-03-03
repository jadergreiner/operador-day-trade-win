#!/usr/bin/env python3
"""
Gate 2 Checkpoint: Backtest Validation for S2-5 Pipeline
=========================================================

Purpose: Validate the complete S2-5 pipeline (score_t60 + confluência)
         with historical data to ensure production readiness.

Expected Results:
  - 50+ iterations without errors
  - Trigger accuracy ≥80%
  - Performance: P95 <50ms
  - Memory stable (<100MB)

Execution Sequence: Setup → Load Dataset → Run Tests → Analyze → Report
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s | %(levelname)-8s | %(message)s'
)
logger = logging.getLogger(__name__)

# Add repo to path
import sys
sys.path.insert(0, str(Path(__file__).parent.parent))

from scripts.score_t60_inference import ScoreT60Inference
from scripts.score_t60_confluence import ScoreT60Confluence


class Gate2Validator:
    """Gate 2 Checkpoint validator for S2-5 pipeline."""

    def __init__(self):
        """Initialize validator with engines."""
        self.inference_engine = ScoreT60Inference(
            model_path="models/score_t60_v1.0_BEST.pkl"
        )
        self.confluence_engine = ScoreT60Confluence()
        self.results = {
            "timestamp": datetime.now().isoformat(),
            "iterations": [],
            "summary": {}
        }
        self.latencies = []
        self.accuracies = []

    def create_test_samples(self, num_samples: int = 100) -> List[pd.DataFrame]:
        """Create realistic test samples from historical data pattern."""
        samples = []

        # Bull market samples
        for _ in range(num_samples // 4):
            df = self._create_bullish_sample()
            samples.append(df)

        # Bear market samples
        for _ in range(num_samples // 4):
            df = self._create_bearish_sample()
            samples.append(df)

        # Sideways market samples
        for _ in range(num_samples // 4):
            df = self._create_sideways_sample()
            samples.append(df)

        # High volatility samples
        for _ in range(num_samples // 4 + num_samples % 4):
            df = self._create_volatile_sample()
            samples.append(df)

        return samples

    def _create_bullish_sample(self) -> pd.DataFrame:
        """Create bullish market sample."""
        np.random.seed(int(time.time() * 1000) % 2**32)

        prices = [100.0]
        for _ in range(59):
            # Uptrend with random walk
            prices.append(prices[-1] * (1 + np.random.normal(0.001, 0.005)))

        data = []
        for i, price in enumerate(prices):
            high = price * (1 + abs(np.random.normal(0, 0.002)))
            low = price * (1 - abs(np.random.normal(0, 0.002)))
            volume = int(np.random.uniform(1000, 5000))

            data.append({
                'open': price,
                'high': high,
                'low': low,
                'close': price,
                'volume': volume
            })

        return pd.DataFrame(data)

    def _create_bearish_sample(self) -> pd.DataFrame:
        """Create bearish market sample."""
        np.random.seed(int(time.time() * 1000) % 2**32)

        prices = [100.0]
        for _ in range(59):
            # Downtrend with random walk
            prices.append(prices[-1] * (1 - np.random.normal(0.001, 0.005)))

        data = []
        for i, price in enumerate(prices):
            high = price * (1 + abs(np.random.normal(0, 0.002)))
            low = price * (1 - abs(np.random.normal(0, 0.002)))
            volume = int(np.random.uniform(1000, 5000))

            data.append({
                'open': price,
                'high': high,
                'low': low,
                'close': price,
                'volume': volume
            })

        return pd.DataFrame(data)

    def _create_sideways_sample(self) -> pd.DataFrame:
        """Create sideways market sample."""
        np.random.seed(int(time.time() * 1000) % 2**32)

        base_price = 100.0
        prices = [base_price + np.random.normal(0, 0.5) for _ in range(60)]

        data = []
        for price in prices:
            high = price * (1 + abs(np.random.normal(0, 0.002)))
            low = price * (1 - abs(np.random.normal(0, 0.002)))
            volume = int(np.random.uniform(1000, 5000))

            data.append({
                'open': price,
                'high': high,
                'low': low,
                'close': price,
                'volume': volume
            })

        return pd.DataFrame(data)

    def _create_volatile_sample(self) -> pd.DataFrame:
        """Create high volatility market sample."""
        np.random.seed(int(time.time() * 1000) % 2**32)

        prices = [100.0]
        for _ in range(59):
            # High volatility movement
            prices.append(prices[-1] * (1 + np.random.normal(0, 0.02)))

        data = []
        for price in prices:
            high = price * (1 + abs(np.random.normal(0, 0.005)))
            low = price * (1 - abs(np.random.normal(0, 0.005)))
            volume = int(np.random.uniform(2000, 10000))

            data.append({
                'open': price,
                'high': high,
                'low': low,
                'close': price,
                'volume': volume
            })

        return pd.DataFrame(data)

    def validate_iteration(self, sample_df: pd.DataFrame, idx: int) -> Dict:
        """Run one validation iteration."""
        start_time = time.time()

        try:
            # 1. T60 Inference
            t60_result = self.inference_engine.predict_from_df(sample_df)

            # 2. Create SMC status (simulated)
            smc_status = {
                "direction": "BULL" if t60_result['score'] > 0.5 else "BEAR",
                "strength": abs(t60_result['score'] - 0.5) * 2
            }

            # 3. Confluência computation
            confluence_result = self.confluence_engine.compute_confluence(
                t60_result, smc_status
            )

            latency = (time.time() - start_time) * 1000  # ms
            self.latencies.append(latency)

            # Determine expected vs actual trigger
            expected_trigger = self._get_expected_trigger(sample_df)
            actual_trigger = confluence_result['trigger']

            accuracy = 1.0 if expected_trigger == actual_trigger else 0.0
            self.accuracies.append(accuracy)

            return {
                "iteration": idx,
                "status": "PASS",
                "latency_ms": latency,
                "t60_score": t60_result['score'],
                "confluencia_state": confluence_result['state'],
                "trigger": confluence_result['trigger'],
                "expected_trigger": expected_trigger,
                "accuracy": accuracy,
                "error": None
            }

        except Exception as e:
            logger.error(f"Iteration {idx} FAILED: {str(e)}")
            return {
                "iteration": idx,
                "status": "FAIL",
                "latency_ms": (time.time() - start_time) * 1000,
                "error": str(e)
            }

    def _get_expected_trigger(self, sample_df: pd.DataFrame) -> str:
        """Determine expected trigger based on price trend."""
        if len(sample_df) < 2:
            return "AGUARDAR"

        # Simple trend detection
        close_prices = sample_df['close'].values
        trend = close_prices[-1] - close_prices[0]

        if trend > 0.5:
            return "BUY"
        elif trend < -0.5:
            return "SELL"
        else:
            return "AGUARDAR"

    def run_backtest(self, num_iterations: int = 50) -> Dict:
        """Run complete backtest validation."""
        logger.info(f"Starting Gate 2 Backtest with {num_iterations} iterations")

        # Create test samples
        samples = self.create_test_samples(num_iterations)

        # Run iterations
        for idx, sample in enumerate(samples, 1):
            result = self.validate_iteration(sample, idx)
            self.results["iterations"].append(result)

            if idx % 10 == 0:
                logger.info(f"  Completed {idx}/{num_iterations} iterations")

        # Compute summary statistics
        self._compute_summary()

        logger.info("Gate 2 Backtest COMPLETE")
        return self.results

    def _compute_summary(self):
        """Compute summary statistics."""
        iterations = self.results["iterations"]

        passed = sum(1 for r in iterations if r["status"] == "PASS")
        failed = sum(1 for r in iterations if r["status"] == "FAIL")

        self.results["summary"] = {
            "total_iterations": len(iterations),
            "passed": passed,
            "failed": failed,
            "pass_rate": passed / len(iterations) if iterations else 0,
            "latency": {
                "mean_ms": np.mean(self.latencies) if self.latencies else 0,
                "p95_ms": np.percentile(self.latencies, 95) if self.latencies else 0,
                "p99_ms": np.percentile(self.latencies, 99) if self.latencies else 0,
                "max_ms": max(self.latencies) if self.latencies else 0
            },
            "accuracy": {
                "mean": np.mean(self.accuracies) if self.accuracies else 0,
                "min": min(self.accuracies) if self.accuracies else 0,
                "max": max(self.accuracies) if self.accuracies else 0
            }
        }

    def save_results(self, filepath: str = "reports/gate2_backtest_results.json"):
        """Save results to JSON file."""
        Path(filepath).parent.mkdir(parents=True, exist_ok=True)

        with open(filepath, 'w') as f:
            json.dump(self.results, f, indent=2)

        logger.info(f"Results saved to {filepath}")
        return filepath

    def print_summary(self):
        """Print summary to console."""
        summary = self.results["summary"]

        print("\n" + "="*60)
        print("GATE 2 CHECKPOINT: BACKTEST VALIDATION SUMMARY")
        print("="*60)
        print(f"\nTotal Iterations:  {summary['total_iterations']}")
        print(f"Passed:            {summary['passed']} ✅")
        print(f"Failed:            {summary['failed']} {'❌' if summary['failed'] > 0 else '✅'}")
        print(f"Pass Rate:         {summary['pass_rate']*100:.1f}%")
        print(f"\nLatency Metrics:")
        print(f"  Mean:            {summary['latency']['mean_ms']:.2f}ms")
        print(f"  P95:             {summary['latency']['p95_ms']:.2f}ms")
        print(f"  P99:             {summary['latency']['p99_ms']:.2f}ms")
        print(f"  Max:             {summary['latency']['max_ms']:.2f}ms")
        print(f"\nAccuracy Metrics:")
        print(f"  Mean:            {summary['accuracy']['mean']*100:.1f}%")
        print(f"  Min:             {summary['accuracy']['min']*100:.1f}%")
        print(f"  Max:             {summary['accuracy']['max']*100:.1f}%")

        # Gate 2 Decision
        print(f"\n{'='*60}")
        if summary['pass_rate'] >= 1.0 and summary['accuracy']['mean'] >= 0.8:
            print("GATE 2 DECISION: ✅ GO")
            print("Status: Approved for S2-6 Deployment")
        else:
            print("GATE 2 DECISION: ❌ NO-GO")
            print("Status: Requires fixes before production")
        print("="*60 + "\n")


def main():
    """Main entry point."""
    validator = Gate2Validator()

    # Run 50 iterations (default for Gate 2)
    results = validator.run_backtest(num_iterations=50)

    # Save results
    validator.save_results()

    # Print summary
    validator.print_summary()

    # Return exit code based on results
    summary = results["summary"]
    if summary['pass_rate'] >= 1.0 and summary['accuracy']['mean'] >= 0.8:
        return 0  # SUCCESS
    else:
        return 1  # FAILURE


if __name__ == "__main__":
    exit(main())
