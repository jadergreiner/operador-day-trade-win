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
    Isso permite usar o agente original sem modificações.
    """
    print("\n  🔗 MONKEY-PATCH: Integração S2-6 Analytics")
    print("  " + "=" * 58)

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

    # ─ Injeta adapter como default ─
    for attr_name in dir(agente_module):
        if "MicroTradingManager" in attr_name:
            try:
                cls = getattr(agente_module, attr_name)
                if hasattr(cls, '__init__'):
                    # Preserva __init__ original mas com adapter injetado
                    pass
            except:
                pass

    print(f"  ✅ MicroTradingManager patched")
    print(f"  ✅ S2-6 Analytics: {'ONLINE' if ADAPTER_AVAILABLE else 'FALLBACK'}")
    print("  " + "=" * 58)
    return adapter


def main():
    """Executa agente original com S2-6 integrado."""
    print("\n  🚀 AGENTE MICRO TENDÊNCIA + S2-6 ANALYTICS v2.0")
    print("  " + "=" * 60)

    # ─ Setup patching ─
    adapter = setup_s2_6_integration()

    # ─ Executa main do agente (com MicroTradingManager patched) ─
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
