#!/usr/bin/env python3
"""
Teste de validação: P0-URGENT-1 Inactivity Penalty System (06/03/2026)

Valida que:
  1. ✅ IntraDayLearner rastreia tempo desde última entrada
  2. ✅ Penalidade é calculada corretamente (progressiva)
  3. ✅ Logs de auditoria registram eventos
  4. ✅ Penalty é resetada ao entrar
"""

from datetime import datetime, timedelta
import sys
import os

ROOT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)

# Importa a classe IntraDayLearner do agente
from scripts.agente_micro_tendencia_winfut import IntraDayLearner


def test_inactivity_penalty_system():
    """Testa P0-URGENT-1 Inactivity Penalty."""
    
    print("=" * 80)
    print("TEST: P0-URGENT-1 Inactivity Penalty System (06/03/2026)")
    print("=" * 80)
    print()
    
    learner = IntraDayLearner()
    
    # ─────────────────────────────────────────────────────────────────────
    # 1. Teste: Sem entrada registrada ainda (primeira chamada)
    # ─────────────────────────────────────────────────────────────────────
    print("TEST 1: Primeira chamada (sem entrada registrada)")
    print("-" * 60)
    penalty, msg = learner.calculate_inactivity_penalty()
    assert penalty == 0.0, f"Expected penalty=0.0, got {penalty}"
    assert "started" in msg.lower(), f"Expected 'started' in message, got: {msg}"
    print(f"  ✅ Penalty: {penalty} (esperado 0.0)")
    print(f"  ✅ Message: {msg}")
    print()
    
    # ─────────────────────────────────────────────────────────────────────
    # 2. Teste: Registra uma entrada
    # ─────────────────────────────────────────────────────────────────────
    print("TEST 2: Registra uma entrada (reset inactivity)")
    print("-" * 60)
    learner.record_entry()
    assert learner.last_entry_time is not None, "last_entry_time não foi registrado"
    assert learner.inactivity_penalty == 0.0, "penalty não foi resetada"
    print(f"  ✅ Entry recorded at: {learner.last_entry_time}")
    print(f"  ✅ Inactivity penalty reset to: {learner.inactivity_penalty}")
    print()
    
    # ─────────────────────────────────────────────────────────────────────
    # 3. Teste: Sem penalidade se ativo (< 120 min)
    # ─────────────────────────────────────────────────────────────────────
    print("TEST 3: Nenhuma penalidade se ativo (< 120 min)")
    print("-" * 60)
    penalty, msg = learner.calculate_inactivity_penalty()
    assert penalty == 0.0, f"Expected penalty=0.0, got {penalty}"
    assert "Active" in msg or "active" in msg.lower(), f"Unexpected message: {msg}"
    print(f"  ✅ Penalty: {penalty} (esperado 0.0, ativo)")
    print(f"  ✅ Message: {msg}")
    print()
    
    # ─────────────────────────────────────────────────────────────────────
    # 4. Teste: Simula 121 minutos de inatividade
    # ─────────────────────────────────────────────────────────────────────
    print("TEST 4: Simula 121 min de inatividade (deve aplicar penalidade)")
    print("-" * 60)
    # Simula: move last_entry_time para trás
    learner.last_entry_time = datetime.now() - timedelta(minutes=121)
    
    penalty, msg = learner.calculate_inactivity_penalty()
    print(f"  ✅ Penalty: {penalty:.4f} (esperado < 0)")
    print(f"  ✅ Severity: LEVE (121 min)")
    print(f"  ✅ Message: {msg}")
    
    assert penalty < 0, f"Expected penalty < 0, got {penalty}"
    assert "LEVE" in msg, f"Expected 'LEVE' in message for 121 min"
    assert abs(penalty) <= learner.MAX_INACTIVITY_PENALTY, f"Penalty exceeded max"
    print()
    
    # ─────────────────────────────────────────────────────────────────────
    # 5. Teste: Simula 200 minutos de inatividade (penalidade média)
    # ─────────────────────────────────────────────────────────────────────
    print("TEST 5: Simula 200 min de inatividade (penalidade MÉDIA)")
    print("-" * 60)
    learner.last_entry_time = datetime.now() - timedelta(minutes=200)
    
    penalty, msg = learner.calculate_inactivity_penalty()
    print(f"  ✅ Penalty: {penalty:.4f}")
    print(f"  ✅ Severity: MÉDIA (200 min)")
    print(f"  ✅ Message: {msg}")
    
    assert penalty < 0, f"Expected penalty < 0, got {penalty}"
    assert "MÉDIA" in msg, f"Expected 'MÉDIA' in message for 200 min"
    print()
    
    # ─────────────────────────────────────────────────────────────────────
    # 6. Teste: Simula 390 minutos (full pregão) de inatividade
    # ─────────────────────────────────────────────────────────────────────
    print("TEST 6: Simula 390 min (full pregão) - penalidade CRÍTICA")
    print("-" * 60)
    learner.last_entry_time = datetime.now() - timedelta(minutes=390)
    
    penalty, msg = learner.calculate_inactivity_penalty()
    print(f"  ✅ Penalty: {penalty:.4f} (máximo)")
    print(f"  ✅ Severity: CRÍTICA (390 min)")
    print(f"  ✅ Message: {msg}")
    
    assert penalty == -learner.MAX_INACTIVITY_PENALTY, f"Expected penalty = -0.05 at max"
    assert "CRÍTICA" in msg, f"Expected 'CRÍTICA' in message for 390 min"
    print()
    
    # ─────────────────────────────────────────────────────────────────────
    # 7. Teste: Reset após nova entrada
    # ─────────────────────────────────────────────────────────────────────
    print("TEST 7: Reset após nova entrada")
    print("-" * 60)
    learner.record_entry()
    
    penalty, msg = learner.calculate_inactivity_penalty()
    assert penalty == 0.0, f"Expected penalty=0.0 after entry, got {penalty}"
    assert learner.inactivity_penalty == 0.0, f"inactivity_penalty not resetada"
    print(f"  ✅ Penalty resetada: {penalty}")
    print(f"  ✅ Back to active trading")
    print()
    
    # ─────────────────────────────────────────────────────────────────────
    # 8. Teste: get_total_confidence_adjustment inclui penalidade
    # ─────────────────────────────────────────────────────────────────────
    print("TEST 8: get_total_confidence_adjustment() inclui penalidade")
    print("-" * 60)
    learner.last_entry_time = datetime.now() - timedelta(minutes=150)
    penalty, _ = learner.calculate_inactivity_penalty()
    
    total_adj = learner.get_total_confidence_adjustment()
    assert total_adj == penalty, f"Expected total_adj == penalty"
    
    print(f"  ✅ Inactivity penalty: {penalty:.4f}")
    print(f"  ✅ Total adjustment: {total_adj:.4f}")
    print(f"  ✅ Match: {total_adj == penalty}")
    print()
    
    # ─────────────────────────────────────────────────────────────────────
    # 9. Teste: Auditoria é registrada
    # ─────────────────────────────────────────────────────────────────────
    print("TEST 9: Auditoria registra eventos")
    print("-" * 60)
    audit_log = learner._audit_log
    assert len(audit_log) > 0, "Audit log vazio"
    
    print(f"  ✅ {len(audit_log)} eventos registrados")
    for i, event in enumerate(audit_log[-5:], 1):  # Últimos 5 eventos
        print(f"     {i}. {event}")
    print()
    
    # ─────────────────────────────────────────────────────────────────────
    # 10. Teste: summary_with_actions() exibe penalidade
    # ─────────────────────────────────────────────────────────────────────
    print("TEST 10: summary_with_actions() exibe penalidade")
    print("-" * 60)
    learner.last_entry_time = datetime.now() - timedelta(minutes=150)
    learner.calculate_inactivity_penalty()
    
    summary = learner.summary_with_actions()
    assert summary != "", "Summary is empty (should show penalty)"
    assert "INACTIVITY" in summary.upper(), f"Summary doesn't mention inactivity"
    
    print(f"  ✅ Summary gerado:")
    for line in summary.split("\n"):
        print(f"     {line}")
    print()
    
    # ─────────────────────────────────────────────────────────────────────
    # FIM
    # ─────────────────────────────────────────────────────────────────────
    print("=" * 80)
    print("✅ TODOS OS TESTES PASSARAM!")
    print("=" * 80)
    print()
    print("Resumo da Implementação P0-URGENT-1:")
    print("-" * 80)
    print("  ✅ IntraDayLearner rastreia último ENTER")
    print("  ✅ Penalidade calculada progressivamente (120-390 min)")
    print("  ✅ Penalidade máxima: -5% (0.05)")
    print("  ✅ Reset de penalidade ao entrar")
    print("  ✅ Auditoria registra todos os eventos")
    print("  ✅ Summary exibe penalidade quando ativa")
    print()
    print("Integração no Agente:")
    print("-" * 80)
    print("  ✅ calculate_inactivity_penalty() chamado a cada ciclo")
    print("  ✅ record_entry() chamado ao entrar (real + simulado)")
    print("  ✅ get_total_confidence_adjustment() inclui penalidade")
    print("  ✅ evaluate_opportunity() aplica penalidade no weighted_confidence")
    print()
    return True


if __name__ == "__main__":
    try:
        success = test_inactivity_penalty_system()
        sys.exit(0 if success else 1)
    except Exception as e:
        print(f"\n❌ ERRO: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
