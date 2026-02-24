#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Teste rápido de imports S2-6."""

import sys
import os

sys.path.insert(0, os.path.dirname(__file__))

try:
    from agente_micro_tendencia_s2_6_integrated import (
        MicroTradingManagerS2_6,
        initialize_s2_6_adapter,
        ADAPTER_AVAILABLE,
    )
    print("\n  ✅ Imports de S2-6 OK")
    print(f"  📌 S2-6 Adapter: {'DISPONÍVEL' if ADAPTER_AVAILABLE else 'FALLBACK'}")
    print(f"  📌 MicroTradingManagerS2_6: Pronto\n")
except Exception as e:
    print(f"\n  ❌ Erro: {e}\n")
    import traceback
    traceback.print_exc()
    sys.exit(1)
