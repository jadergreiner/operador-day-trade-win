#!/usr/bin/env python
"""
quick_test_e2e.py — Quick validation de E2E tests

Roda testes rapidamente para debug
"""

import sys
import numpy as np
import pandas as pd

# Quick test
try:
    from scripts.score_t60_inference import ScoreT60Inference
    from scripts.score_t60_confluence import ScoreT60Confluence

    print("✅ Imports OK")

    # Create engines
    model_path = "models/score_t60_v1.0_BEST.pkl"
    inf = ScoreT60Inference(model_path=model_path)
    conf = ScoreT60Confluence()
    print("✅ Engines initialized")

    # Create sample data
    timestamps = pd.date_range(start="2026-02-24 09:30", periods=60, freq="1min")
    closes = np.linspace(100, 110, 60) + np.random.normal(0, 0.5, 60)
    df = pd.DataFrame({
        "timestamp": timestamps,
        "open": closes - 0.5,
        "high": closes + 1,
        "low": closes - 1,
        "close": closes,
        "volume": np.random.uniform(1000, 5000, 60),
    })
    print(f"✅ Sample data created: {df.shape[0]} candles")

    # Test inference
    t60 = inf.predict_from_df(df)
    print(f"✅ T60 Inference: score={t60['score_t60']:.3f}, classe={t60['classe']}")

    # Test confluence
    smc = {"direction": "BULL", "strength": 0.85}
    result = conf.compute_confluence(t60, smc)
    print(f"✅ Confluência: state={result['state']}, trigger={result['trigger']}")

    print("\n✅ E2E PIPELINE OK - Ready for pytest")
    sys.exit(0)

except Exception as e:
    print(f"❌ ERROR: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)
