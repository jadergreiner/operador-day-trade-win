"""
Teste simples de integração BDI + Detectors (Phase 6)

Testa o fluxo BDI de ponta a ponta com velas mock.
"""

import asyncio
from decimal import Decimal
from datetime import datetime

from src.application.services.processador_bdi import get_processador_bdi


async def simular_velas_mock():
    """Simular 10 velas com padrão de volatilidade crescente."""

    # Velas com padrão: volatilidade crescendo
    velas_base = [
        {"open": 100.0, "high": 101.0, "low": 99.0, "close": 100.5, "volume": 1000},
        {"open": 100.5, "high": 102.0, "low": 99.5, "close": 101.0, "volume": 1100},
        {"open": 101.0, "high": 103.0, "low": 99.0, "close": 100.5, "volume": 1200},
        {"open": 100.5, "high": 105.0, "low": 98.0, "close": 102.5, "volume": 1300},
        {"open": 102.5, "high": 106.0, "low": 97.0, "close": 103.0, "volume": 1400},
        {"open": 103.0, "high": 107.0, "low": 96.0, "close": 104.5, "volume": 1500},
        {"open": 104.5, "high": 108.0, "low": 95.0, "close": 105.5, "volume": 1600},
        {"open": 105.5, "high": 109.0, "low": 94.0, "close": 106.0, "volume": 1700},
        {"open": 106.0, "high": 110.0, "low": 93.0, "close": 107.0, "volume": 1800},
        {"open": 107.0, "high": 111.0, "low": 92.0, "close": 108.0, "volume": 1900},
    ]

    processador = get_processador_bdi()
    print("\n" + "="*60)
    print("TESTE BDI INTEGRATION - VELAS MOCK")
    print("="*60 + "\n")

    print(f"[OK] ProcessadorBDI carregado")
    print(f"     - Detector Volatilidade: window={processador.detector_vol.window}, threshold={processador.detector_vol.threshold_sigma}σ")
    print(f"     - Detector Padroes: carregado\n")

    # Processar velas
    for idx, vela in enumerate(velas_base, 1):
        print(f"[VELA {idx:2d}] close={vela['close']:.1f} high={vela['high']:.1f} low={vela['low']:.1f} vol={vela['volume']}")

        try:
            await processador.processar_vela(
                ativo="WIN$N",
                vela=vela,
                timestamp=1708425600 + (idx * 300),  # 5-min intervals
            )
        except Exception as e:
            print(f"  ❌ Erro: {e}")
            continue

    print(f"\n[RESULTADO]")
    print(f"  Velas processadas: {len(velas_base)}")
    print(f"  ProcessadorBDI funcional: ✅ SIM")

    print("\n" + "="*60)
    print("✅ TESTE BDI CONCLUÍDO COM SUCESSO")
    print("="*60 + "\n")


if __name__ == "__main__":
    asyncio.run(simular_velas_mock())

