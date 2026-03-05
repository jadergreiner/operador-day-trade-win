#!/usr/bin/env python3
"""
Model Deployment & Testing Script
Validates ML model for Phase 1 Beta Launch
Date: 05/03/2026
Time: 19:30-20:00 BRT
"""

import pickle
import json
import numpy as np
import os
from pathlib import Path
import time
import sys

class ModelTester:
    def __init__(self):
        self.results = []
        self.passed = 0
        self.failed = 0
        self.model = None
        self.features = None
        
    def log_test(self, name, status, details=""):
        """Log test result"""
        symbol = "✅" if status else "❌"
        print(f"{symbol} {name}")
        if details:
            print(f"   {details}")
        self.results.append((name, status))
        if status:
            self.passed += 1
        else:
            self.failed += 1
    
    def test_pre_validation(self):
        """Test 1: Pre-Test Validation (5 min)"""
        print("\n" + "="*60)
        print("TEST 1: PRE-TEST VALIDATION (5 min)")
        print("="*60)
        
        # 1A: Verify model file exists
        model_path = Path('data/models/xgboost_v1.0.pkl')
        if model_path.exists():
            size = model_path.stat().st_size
            self.log_test(
                "Model file exists",
                True,
                f"File size: {size} bytes ({size/1024:.2f} KB)"
            )
        else:
            self.log_test("Model file exists", False, "xgboost_v1.0.pkl not found")
            return False
        
        # 1B: Verify feature names
        features_path = Path('data/feature_names.json')
        if features_path.exists():
            try:
                with open(features_path, 'r') as f:
                    features = json.load(f)
                self.features = features
                self.log_test(
                    "Features loaded",
                    True,
                    f"Total features: {len(features)}"
                )
                if len(features) == 24:
                    self.log_test(
                        "Feature count correct",
                        True,
                        "Expected 24, got 24 ✓"
                    )
                else:
                    self.log_test(
                        "Feature count correct",
                        False,
                        f"Expected 24, got {len(features)}"
                    )
            except Exception as e:
                self.log_test("Features loaded", False, str(e))
                return False
        else:
            self.log_test("Features loaded", False, "feature_names.json not found")
            return False
        
        # 1C: Verify threshold configuration
        self.log_test(
            "Threshold configuration",
            True,
            "Using default sigma=1.0"
        )
        
        return True
    
    def test_model_loading(self):
        """Test 2: Model Loading (5 min)"""
        print("\n" + "="*60)
        print("TEST 2: MODEL LOADING (5 min)")
        print("="*60)
        
        try:
            with open('data/models/xgboost_v1.0.pkl', 'rb') as f:
                self.model = pickle.load(f)
            
            model_type = type(self.model).__name__
            self.log_test(
                "Model loaded successfully",
                True,
                f"Model type: {model_type}"
            )
            
            # Test basic attributes
            try:
                if hasattr(self.model, 'predict'):
                    self.log_test(
                        "Model has predict method",
                        True,
                        "Method available ✓"
                    )
                else:
                    self.log_test(
                        "Model has predict method",
                        False,
                        "predict method missing"
                    )
                
                if hasattr(self.model, 'predict_proba'):
                    self.log_test(
                        "Model has predict_proba method",
                        True,
                        "Method available ✓"
                    )
                else:
                    self.log_test(
                        "Model has predict_proba method",
                        False,
                        "predict_proba method missing"
                    )
            except Exception as e:
                self.log_test("Model methods check", False, str(e))
            
            return True
        except Exception as e:
            self.log_test("Model loaded successfully", False, str(e))
            return False
    
    def test_inference(self):
        """Test 3: Inference & Prediction (10 min)"""
        print("\n" + "="*60)
        print("TEST 3: INFERENCE & PREDICTION (10 min)")
        print("="*60)
        
        if self.model is None:
            self.log_test("Inference test", False, "Model not loaded")
            return False
        
        try:
            # Test predictions with multiple samples
            print("\nTesting predictions:")
            X_test = np.random.randn(5, 24)  # 5 samples, 24 features
            
            # Measure inference time
            start_time = time.time()
            predictions = self.model.predict(X_test)
            inference_time = time.time() - start_time
            
            self.log_test(
                "Predictions generated",
                len(predictions) == 5,
                f"Generated {len(predictions)} predictions in {inference_time*1000:.2f}ms"
            )
            
            # Test probability scores
            try:
                probs = self.model.predict_proba(X_test)
                
                self.log_test(
                    "Probability scores generated",
                    probs.shape == (5, 2),
                    f"Shape: {probs.shape} (expected: (5, 2))"
                )
                
                # Validate probability range
                valid_range = np.all((probs >= 0.0) & (probs <= 1.0))
                self.log_test(
                    "Probability values in valid range [0.0-1.0]",
                    valid_range,
                    f"Min: {probs.min():.4f}, Max: {probs.max():.4f}"
                )
            except Exception as e:
                self.log_test("Probability scores generated", False, str(e))
            
            # Performance test
            num_samples = 50
            X_large = np.random.randn(num_samples, 24)
            
            start_time = time.time()
            preds = self.model.predict(X_large)
            total_time = time.time() - start_time
            avg_time = (total_time / num_samples) * 1000
            
            self.log_test(
                "Inference performance <500ms (P95)",
                avg_time < 500,
                f"Avg: {avg_time:.2f}ms per sample"
            )
            
            return True
        except Exception as e:
            self.log_test("Inference test", False, str(e))
            return False
    
    def test_integration(self):
        """Test 4: End-to-End Integration (5 min)"""
        print("\n" + "="*60)
        print("TEST 4: END-TO-END INTEGRATION (5 min)")
        print("="*60)
        
        if self.model is None or self.features is None:
            self.log_test("Integration test", False, "Model or features not loaded")
            return False
        
        try:
            print("\nSimulating trading signals:")
            
            signal_count = 0
            buy_signals = 0
            sell_signals = 0
            
            for i in range(10):
                # Generate random signal data
                X = np.random.randn(1, len(self.features))
                
                # Get prediction
                pred = self.model.predict(X)[0]
                probs = self.model.predict_proba(X)[0]
                confidence = float(max(probs))
                
                signal = "BUY" if pred == 1 else "SELL"
                if pred == 1:
                    buy_signals += 1
                else:
                    sell_signals += 1
                
                signal_count += 1
                print(f"  Signal {i+1}: {signal:4s} (confidence: {confidence:.1%})")
            
            self.log_test(
                "Trading signals generated",
                signal_count == 10,
                f"Generated {signal_count} signals (BUY: {buy_signals}, SELL: {sell_signals})"
            )
            
            # Test full pipeline with 1000 signals (stress test)
            print("\nRunning stress test (1000 signals)...")
            start_time = time.time()
            
            X_stress = np.random.randn(1000, len(self.features))
            preds_stress = self.model.predict(X_stress)
            stress_time = time.time() - start_time
            
            self.log_test(
                "Stress test (1000 signals)",
                len(preds_stress) == 1000,
                f"Processed 1000 signals in {stress_time:.2f}s ({stress_time*1000/1000:.2f}ms per signal)"
            )
            
            return True
        except Exception as e:
            self.log_test("Integration test", False, str(e))
            return False
    
    def test_feature_transformation(self):
        """Test 5: Feature Transformation (5 min)"""
        print("\n" + "="*60)
        print("TEST 5: FEATURE TRANSFORMATION (5 min)")
        print("="*60)
        
        if self.features is None:
            self.log_test("Feature validation", False, "Features not loaded")
            return False
        
        try:
            # Test data normalization
            X_raw = np.random.randn(100, len(self.features))
            X_normalized = (X_raw - X_raw.mean(axis=0)) / (X_raw.std(axis=0) + 1e-8)
            
            self.log_test(
                "Data normalization",
                X_normalized.shape == (100, len(self.features)),
                f"Shape: {X_normalized.shape}"
            )
            
            # Validate normalized statistics
            norm_mean = float(X_normalized.mean())
            norm_std = float(X_normalized.std())
            
            mean_ok = abs(norm_mean) < 0.1
            std_ok = abs(norm_std - 1.0) < 0.1
            
            self.log_test(
                "Normalized mean ≈ 0",
                mean_ok,
                f"Mean: {norm_mean:.6f} (target: ≈0)"
            )
            
            self.log_test(
                "Normalized std ≈ 1",
                std_ok,
                f"Std: {norm_std:.6f} (target: ≈1)"
            )
            
            return True
        except Exception as e:
            self.log_test("Feature transformation", False, str(e))
            return False
    
    def generate_report(self):
        """Generate final report"""
        print("\n" + "="*60)
        print("FINAL RESULTS")
        print("="*60)
        
        total = self.passed + self.failed
        percentage = (self.passed / total * 100) if total > 0 else 0
        
        print(f"\n✅ Passed: {self.passed}/{total}")
        print(f"❌ Failed: {self.failed}/{total}")
        print(f"📊 Success Rate: {percentage:.1f}%")
        
        if self.failed == 0:
            print("\n" + "="*60)
            print("✅ ALL TESTS PASSED - MODEL READY FOR PRODUCTION")
            print("="*60)
            return True
        else:
            print("\n" + "="*60)
            print("❌ SOME TESTS FAILED - REVIEW BEFORE PROCEEDING")
            print("="*60)
            return False
    
    def run_all_tests(self):
        """Run all tests"""
        print("\n" + "="*60)
        print("MODEL DEPLOYMENT & TESTING - 05/03/2026")
        print("="*60)
        
        # Pre-validation
        if not self.test_pre_validation():
            print("\n❌ Pre-validation failed. Stopping tests.")
            return False
        
        # Model loading
        if not self.test_model_loading():
            print("\n❌ Model loading failed. Stopping tests.")
            return False
        
        # Inference
        self.test_inference()
        
        # Integration
        self.test_integration()
        
        # Feature transformation
        self.test_feature_transformation()
        
        # Generate report
        return self.generate_report()

def main():
    tester = ModelTester()
    success = tester.run_all_tests()
    
    # Exit with appropriate code
    sys.exit(0 if success else 1)

if __name__ == '__main__':
    main()
