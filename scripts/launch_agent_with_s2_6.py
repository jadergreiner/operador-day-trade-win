#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
LAUNCHER: AGENTE MICRO TENDÊNCIA WITH S2-6 ANALYTICS

Executa o agente original com S2-6 Analytics integrado via monkey-patching.
Compatível 100% com flags originais do agente.

Uso:
    python launch_agent_with_s2_6.py --auto-trade
    python launch_agent_with_s2_6.py --simulate
    python launch_agent_with_s2_6.py --account 456789

Status: ✅ PRODUÇÃO
"""

import sys
import os

# ─ Setup path ─
current_dir = os.path.dirname(os.path.abspath(__file__))
if current_dir not in sys.path:
    sys.path.insert(0, current_dir)

# ─ Imports ─
from agente_micro_tendencia_s2_6_integrated import (
    MicroTradingManagerS2_6,
    initialize_s2_6_adapter,
    ADAPTER_AVAILABLE,
)
import agente_micro_tendencia_winfut as agente_module


def setup_s2_6_integration():
    """
    Monkey-patch: substitui MicroTradingManager por versão com S2-6.
    Tolerante a falhas - funciona mesmo se S2-6 estiver offline.
    """
    print("\n  🔗 MONKEY-PATCH: Integração S2-6 Analytics")
    print("  " + "=" * 58)

    try:
        # ─ Guarda referência original ─
        OriginalMicroTradingManager = agente_module.MicroTradingManager

        # ─ Cria nova classe que herda da original + S2-6 ─
        class MicroTradingManagerPatched(MicroTradingManagerS2_6):
            """Versão patched com S2-6 que mantém compatibilidade."""
            pass

        # ─ Substitui classe original ─
        agente_module.MicroTradingManager = MicroTradingManagerPatched

        # ─ Inicializa adapter global ─
        api_url = os.getenv("S2_6_API_URL", "http://localhost:8000")
        adapter = initialize_s2_6_adapter(api_url)

        print(f"  ✅ MicroTradingManager patched")
        print(f"  ✅ S2-6 Analytics: {'ONLINE' if ADAPTER_AVAILABLE else 'FALLBACK'}")
        print("  " + "=" * 58)
        return adapter

    except Exception as e:
        print(f"  ⚠️  Erro ao patchear S2-6: {e}")
        print(f"     Sistema operará sem S2-6 (fallback mode)")
        print("  " + "=" * 58)
        # Retorna adapter dummy mesmo em caso de erro
        from agente_micro_tendencia_s2_6_integrated import AnalyticsAdapter
        return AnalyticsAdapter()


def main():
    """Executa agente original com S2-6 integrado (tolerante a falhas)."""
    print("\n  🚀 AGENTE MICRO TENDÊNCIA + S2-6 ANALYTICS v2.0")
    print("  " + "=" * 60)

    # ─ Setup patching (tolera falhas) ─
    try:
        adapter = setup_s2_6_integration()
    except Exception as e:
        print(f"\n  ⚠️  Erro ao setup S2-6: {e}")
        print(f"     Continuando com agente original (sem S2-6)...\n")
        adapter = None

    # ─ Executa main do agente ─
    try:
        agente_module.main()
    except KeyboardInterrupt:
        print("\n\n  🛑 Agente interrompido pelo usuário")
        sys.exit(0)
    except Exception as e:
        print(f"\n  ❌ Erro no agente: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
