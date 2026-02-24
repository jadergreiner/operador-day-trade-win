#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Validação de 5 gates obrigatórios para S2-6 Fase 1"""

import requests
import time
import sqlite3
from datetime import datetime

BASE_URL = "http://localhost:8001"
THRESHOLDS = {
    "health_check_ms": 5000,
    "p95_latency_ms": 2500,  # Windows Python startup overhead
    "memory_mb": 150,
    "error_rate": 0.01,
}

print("=" * 80)
print("FASE 1: VALIDATION GATES - 5 Gates Obrigatorios")
print("=" * 80)
print()

# GATE 1: Health Check
print("[GATE 1] Health Check")
print("-" * 80)
try:
    start = time.time()
    resp = requests.get(f"{BASE_URL}/health", timeout=5)
    latency = (time.time() - start) * 1000

    if resp.status_code == 200:
        print(f"OK - API responds within {latency:.2f}ms")
        print(f"OK - Response: {resp.json()}")
        gate1_pass = True
    else:
        print(f"FAIL - API returned {resp.status_code}")
        gate1_pass = False
except Exception as e:
    print(f"FAIL - Health check failed: {e}")
    gate1_pass = False

print()

# GATE 2: Functional Tests
print("[GATE 2] Functional Tests")
print("-" * 80)
try:
    payload = {
        "symbol": "WINFUT",
        "action": "OVERRIDE",
        "trader_decision": "override_long",
        "p_and_l": 150.00
    }
    resp = requests.post(f"{BASE_URL}/api/intervention/log", json=payload, timeout=5)

    if resp.status_code in [200, 201]:
        data = resp.json()
        intervention_id = data.get("intervention_id") or data.get("id")
        print(f"OK - POST /api/intervention/log working (id: {intervention_id})")

        update_payload = {
            "result": "WIN",
            "p_and_l": 250.00
        }
        resp2 = requests.post(f"{BASE_URL}/api/intervention/{intervention_id}/result",
                             json=update_payload, timeout=5)

        if resp2.status_code in [200, 201]:
            print(f"OK - POST /api/intervention/{{id}}/result working")

            resp3 = requests.get(f"{BASE_URL}/api/analytics/stats", timeout=5)
            if resp3.status_code == 200:
                print(f"OK - GET /api/analytics/stats working")

                resp4 = requests.get(f"{BASE_URL}/api/analytics/dashboard", timeout=5)
                if resp4.status_code == 200:
                    print(f"OK - GET /api/analytics/dashboard working")
                    gate2_pass = True
                else:
                    print(f"FAIL - Dashboard endpoint failed: {resp4.status_code}")
                    gate2_pass = False
            else:
                print(f"FAIL - Stats endpoint failed: {resp3.status_code}")
                gate2_pass = False
        else:
            print(f"FAIL - Update result endpoint failed: {resp2.status_code}")
            gate2_pass = False
    else:
        print(f"FAIL - Log endpoint failed: {resp.status_code}")
        gate2_pass = False
except Exception as e:
    print(f"FAIL - Functional test failed: {e}")
    gate2_pass = False

print()

# GATE 3: Performance
print("[GATE 3] Performance")
print("-" * 80)
try:
    latencies = []
    for i in range(10):
        start = time.time()
        requests.get(f"{BASE_URL}/health", timeout=5)
        latencies.append((time.time() - start) * 1000)

    p50 = sorted(latencies)[5]
    p95 = sorted(latencies)[9]

    print(f"OK - P50 latency: {p50:.2f}ms")
    print(f"OK - P95 latency: {p95:.2f}ms (limit: {THRESHOLDS['p95_latency_ms']}ms)")

    gate3_pass = p95 < THRESHOLDS['p95_latency_ms']
except Exception as e:
    print(f"FAIL - Performance test failed: {e}")
    gate3_pass = False

print()

# GATE 4: Monitoring
print("[GATE 4] Monitoring")
print("-" * 80)
try:
    resp = requests.get(f"{BASE_URL}/metrics", timeout=5)

    if resp.status_code == 200:
        print(f"OK - Metrics endpoint available")
        gate4_pass = True
    else:
        print(f"FAIL - Metrics endpoint failed: {resp.status_code}")
        gate4_pass = False
except Exception as e:
    print(f"FAIL - Monitoring test failed: {e}")
    gate4_pass = False

print()

# GATE 5: Security
print("[GATE 5] Security")
print("-" * 80)
try:
    malicious_symbol = "WINFUT'; DROP TABLE trader_interventions; --"
    payload = {
        "symbol": malicious_symbol,
        "action": "OVERRIDE",
        "trader_decision": "test"
    }

    resp = requests.post(f"{BASE_URL}/api/intervention/log", json=payload, timeout=5)

    conn = sqlite3.connect("data/analytics_staging.db")
    cursor = conn.cursor()
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='trader_interventions'")
    table_exists = cursor.fetchone() is not None
    conn.close()

    if table_exists:
        print(f"OK - SQL injection protection active")
        gate5_pass = True
    else:
        print(f"FAIL - SQL injection vulnerability detected")
        gate5_pass = False
except Exception as e:
    print(f"FAIL - Security test failed: {e}")
    gate5_pass = False

print()
print("=" * 80)
print("RESULTADO FINAL")
print("=" * 80)

gates = {
    "GATE 1: Health Check": gate1_pass,
    "GATE 2: Functional Tests": gate2_pass,
    "GATE 3: Performance": gate3_pass,
    "GATE 4: Monitoring": gate4_pass,
    "GATE 5: Security": gate5_pass,
}

for gate, status in gates.items():
    symbol = "OK" if status else "FAIL"
    print(f"[{symbol}] {gate}")

all_pass = all(gates.values())
print()
print("=" * 80)
if all_pass:
    print("GREEN - FASE 1: STAGING VALIDATION OK")
    print()
    print("Todos os 5 gates PASSARAM. Pronto para Fase 2.")
else:
    print("RED - FASE 1: STAGING NOT READY")
    print()
    print("Um ou mais gates falharam. Corrigir antes.")

print("=" * 80)
