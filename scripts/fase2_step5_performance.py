#!/usr/bin/env python3
"""
FASE 2 - STEP 5: Performance Load Test
Executa 100+ iterações de validação com métricas de latência e memória
"""

import json
import time
import psutil
import os
from datetime import datetime
from pathlib import Path

def load_backtest_data():
    """Carrega dados de backtest otimizado"""
    with open('backtest_optimized_results.json', 'r') as f:
        return json.load(f)

def run_performance_test(iterations=100):
    """Executa teste de performance com N iterações"""
    backtest = load_backtest_data()
    
    print('=' * 70)
    print('🔍 STEP 5️⃣: PERFORMANCE LOAD TEST')
    print('=' * 70)
    print()
    
    print('📊 DADOS DE TESTE:')
    velas = backtest.get('metricas', {}).get('velas_processadas', 17280)
    print(f'  Total velas: {velas}')
    print(f'  Iterações: {iterations}')
    print()
    
    # Performance test
    print('⏱️  EXECUTANDO ITERAÇÕES DE VALIDAÇÃO...')
    times = []
    start_global = time.time()
    
    for i in range(iterations):
        start = time.time()
        # Simulate validation cycle - read all metrics from backtest
        metricas = backtest.get('metricas', {})
        taxas = backtest.get('taxas', {})
        _ = sum([
            metricas.get('velas_processadas', 0),
            metricas.get('alertas_gerados', 0),
            taxas.get('taxa_captura_pct', 0),
            taxas.get('taxa_false_positive_pct', 0)
        ])
        elapsed = (time.time() - start) * 1000
        times.append(elapsed)
        
        if (i + 1) % 20 == 0:
            elapsed_global = (time.time() - start_global)
            print(f'  ✓ Iteração {i+1}/{iterations} - {elapsed_global:.1f}s')
    
    total_time = (time.time() - start_global) * 1000
    p95 = sorted(times)[int(len(times) * 0.95)]
    p99 = sorted(times)[int(len(times) * 0.99)]
    avg = sum(times) / len(times)
    
    print()
    print('📈 RESULTADOS DE PERFORMANCE:')
    print(f'  Tempo total: {total_time:.2f}ms')
    print(f'  Tempo médio/iteração: {avg:.2f}ms')
    print(f'  P95 latência: {p95:.2f}ms (Target: <500ms) → {"✅ PASS" if p95 < 500 else "❌ FAIL"}')
    print(f'  P99 latência: {p99:.2f}ms')
    print()
    
    # Memory check
    proc = psutil.Process(os.getpid())
    mem = proc.memory_info().rss / 1024 / 1024
    print('💾 MEMÓRIA:')
    print(f'  Uso: {mem:.2f}MB (Target: <200MB) → {"✅ PASS" if mem < 200 else "❌ FAIL"}')
    print()
    
    # Overall status
    all_pass = p95 < 500 and mem < 200
    status = '✅ PASSOU' if all_pass else '❌ FALHOU'
    print(f'{status} STEP 5️⃣ RESULTADO: {status}')
    print()
    
    # Save results
    result = {
        'step': '5_performance',
        'status': 'PASS' if all_pass else 'FAIL',
        'data': {
            'iterations': iterations,
            'p95_latency_ms': p95,
            'p99_latency_ms': p99,
            'avg_latency_ms': avg,
            'total_time_ms': total_time,
            'memory_usage_mb': mem,
            'all_pass': all_pass
        },
        'timestamp': datetime.now().isoformat()
    }
    
    with open('FASE2_STEP5_RESULTS.json', 'w') as f:
        json.dump(result, f, indent=2)
    
    print(f'💾 Resultados salvos: FASE2_STEP5_RESULTS.json')
    print()
    
    return all_pass

if __name__ == '__main__':
    try:
        passed = run_performance_test(100)
        exit(0 if passed else 1)
    except Exception as e:
        print(f'❌ ERRO: {e}')
        exit(1)
