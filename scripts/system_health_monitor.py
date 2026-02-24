# -*- coding: utf-8 -*-
"""
CLI Wrapper de Monitoramento de Saude (S1-2)
Uso: python scripts/system_health_monitor.py
"""
import os
import sys
from pathlib import Path

# Adiciona o diretório raiz ao sys.path para importações absolutas de 'src'
current_dir = Path(__file__).parent.parent
sys.path.append(str(current_dir))

from src.infrastructure.monitoring.health_checker import HealthChecker

def main():
    print("==============================================================================")
    print("   SISTEMA DE MONITORAMENTO E HEALTH CHECKS 24/7 (S1-2) ")
    print("==============================================================================")
    print("")

    checker = HealthChecker()
    passed, detail = checker.run_pre_flight()

    if passed:
        print("")
        print("   [✓] Gate de Governança:      PASSED (Sincronizado)")
        print(f"   [✓] Latência P95 Central:    PASSED ({detail['latency'][1]:.2f}ms < 500ms)")
        print("   [✓] Conectividade MT5:       PASSED")
        print("")
        print("🟢 SISTEMA OPERACIONALMENTE SAUDÁVEL. PROSSEGUINDO...")
        sys.exit(0)
    else:
        print("")
        print("   [!] Gate de Governança:      " + ("PASSED" if detail['governance'][0] else "FAILED (" + str(detail['governance'][1]) + ")"))
        print("   [!] Latência P95 Central:    " + ("PASSED" if detail['latency'][0] else "FAILED (" + str(detail['latency'][1]) + "ms)"))
        print("   [!] Conectividade MT5:       " + ("PASSED" if detail['mt5'][0] else "FAILED (" + str(detail['mt5'][1]) + ")"))
        print("")
        print("🔴 BLOQUEIO DE SEGURANÇA: SISTEMA NÃO-SINCRO OU INSTÁVEL.")
        print("   Consulte docs/STATUS_ENTREGAS.md e certifique-se de ter [SYNC] ativo.")
        sys.exit(1)

if __name__ == "__main__":
    main()
