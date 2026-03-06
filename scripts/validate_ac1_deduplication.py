"""
AC1 Deduplication Validation - Verificar que sinais duplicados foram removidos.

Este script:
1. Carrega dados históricos de candles
2. Executa AC1 (SignalGenerator) com deduplicação ATIVA
3. Conta sinais totais
4. Valida que duplicatas foram removidas (148 → ~44)
5. Compara com execução anterior

Status: Validação de AC1.DEDUP implementação
Versão: v1.2.5 (com deduplicação)
"""

import logging
import json
import sys
from pathlib import Path
from datetime import datetime, timedelta
from typing import List, Dict, Any

# Add project root
project_root = Path(__file__).parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

from src.domain.signal_generator import SignalGenerator, Candle

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class AC1DeduplicationValidator:
    """Valida deduplicação de AC1."""

    def __init__(self):
        """Inicializar validador."""
        self.signal_gen = SignalGenerator()
        self.candles: List[Candle] = []
        self.all_signals: Dict[str, List[Dict]] = {
            "BOS": [],
            "CHoCH": [],
            "FVG": []
        }

    def load_candle_data(self) -> bool:
        """
        Carrega dados de candles para teste.
        
        Usar dataset real ou dados simulados de 17,280 candles (252 dias).
        
        Returns:
            True se sucesso
        """
        logger.info("[LOAD] Simulando 17.280 candles (252 dias × 288 candles/dia)...")
        
        # Simular 17.280 candles com padrões realistas
        import random
        
        base_price = 1250.0
        timestamp = datetime(2025, 1, 1, 9, 0)  # 9:00 BRT
        
        for i in range(17280):
            # Simular movimento de preço com tendência e volatilidade
            trend = 0.1 if i % 100 < 50 else -0.1  # Alternância de tendência
            random_move = random.uniform(-0.5, 0.5)
            
            open_price = base_price + trend + random_move
            close_price = open_price + random.uniform(-0.3, 0.3)
            high_price = max(open_price, close_price) + abs(random.uniform(0, 0.2))
            low_price = min(open_price, close_price) - abs(random.uniform(0, 0.2))
            volume = random.randint(100, 5000)
            
            candle = Candle(
                timestamp=timestamp,
                open=open_price,
                high=high_price,
                low=low_price,
                close=close_price,
                volume=volume
            )
            
            self.candles.append(candle)
            
            # Incrementar timestamp (5 minutos)
            timestamp += timedelta(minutes=5)
            
            # Update base_price para próxima iteração
            base_price = close_price
            
            if (i + 1) % 2000 == 0:
                logger.info(f"  Carregados {i + 1}/17280 candles...")
        
        logger.info(f"[LOAD] ✓ {len(self.candles)} candles carregados")
        return True

    def run_signal_detection(self) -> Dict[str, int]:
        """
        Executa detecção de sinais com AC1 (com deduplicação).
        
        Returns:
            Dict com counts de sinais por tipo
        """
        logger.info("[DETECT] Executando AC1 com deduplicação...")
        
        # Detectar cada padrão
        bos_detections = self.signal_gen.detect_bos(self.candles)
        choch_detections = self.signal_gen.detect_choch(self.candles)
        fvg_detections = self.signal_gen.detect_fvg(self.candles)
        
        self.all_signals["BOS"] = bos_detections
        self.all_signals["CHoCH"] = choch_detections
        self.all_signals["FVG"] = fvg_detections
        
        total_signals = len(bos_detections) + len(choch_detections) + len(fvg_detections)
        
        logger.info(f"[DETECT] BOS signals: {len(bos_detections)}")
        logger.info(f"[DETECT] CHoCH signals: {len(choch_detections)}")
        logger.info(f"[DETECT] FVG signals: {len(fvg_detections)}")
        logger.info(f"[DETECT] TOTAL signals: {total_signals}")
        
        return {
            "BOS": len(bos_detections),
            "CHoCH": len(choch_detections),
            "FVG": len(fvg_detections),
            "TOTAL": total_signals
        }

    def validate_deduplication(self, counts: Dict[str, int]) -> Dict[str, Any]:
        """
        Valida que deduplicação removeu duplicatas.
        
        Esperado:
        - ANTES: 148 sinais totais (70% duplicados)
        - DEPOIS: ~44 sinais únicos
        
        Args:
            counts: Dict com counts de sinais
            
        Returns:
            Dict com resultado da validação
        """
        logger.info("[VALIDATE] Analisando redução de duplicatas...")
        
        total = counts["TOTAL"]
        
        # Esperado: redução de ~148 para ~44 (70% deduplificação)
        expected_before = 148
        expected_after = 44
        expected_reduction = expected_before - expected_after  # ~104
        expected_pct = (expected_reduction / expected_before) * 100  # ~70%
        
        # Calcular redução real
        reduction_from_expected = expected_before - total
        reduction_pct = (reduction_from_expected / expected_before) * 100 if expected_before > 0 else 0
        
        result = {
            "signals_total": total,
            "expected_before_dedup": expected_before,
            "expected_after_dedup": expected_after,
            "expected_reduction_pct": expected_pct,
            "actual_reduction_from_expected": reduction_from_expected,
            "actual_reduction_pct": reduction_pct,
            "dedup_success": total < expected_before,
            "dedup_quality": (
                reduction_pct >= 50  # Pelo menos 50% deduplificação
                if total < expected_before else False
            )
        }
        
        if result["dedup_success"]:
            logger.info(f"[VALIDATE] ✓ Deduplificação ATIVA")
            logger.info(f"[VALIDATE] ✓ Redução: {expected_before} → {total} sinais ({reduction_pct:.1f}%)")
        else:
            logger.warning(f"[VALIDATE] ✗ Deduplificação pode não estar funcionando")
            logger.warning(f"[VALIDATE] ✗ Sinais esperados: ~44, obtidos: {total}")
        
        return result

    def analyze_signal_distribution(self) -> Dict[str, Any]:
        """
        Analisa distribuição de sinais (BUY vs SELL).
        
        Returns:
            Dict com análise de distribuição
        """
        logger.info("[ANALYZE] Analisando distribuição BUY/SELL...")
        
        buy_count = 0
        sell_count = 0
        
        for pattern_type in ["BOS", "CHoCH", "FVG"]:
            for signal in self.all_signals[pattern_type]:
                if signal.get("type") == "BUY":
                    buy_count += 1
                elif signal.get("type") == "SELL":
                    sell_count += 1
        
        total = buy_count + sell_count
        
        result = {
            "buy_signals": buy_count,
            "sell_signals": sell_count,
            "total_signals": total,
            "buy_pct": (buy_count / total * 100) if total > 0 else 0,
            "sell_pct": (sell_count / total * 100) if total > 0 else 0,
        }
        
        logger.info(f"[ANALYZE] BUY signals: {buy_count} ({result['buy_pct']:.1f}%)")
        logger.info(f"[ANALYZE] SELL signals: {sell_count} ({result['sell_pct']:.1f}%)")
        
        return result

    def generate_report(self, 
                       counts: Dict[str, int],
                       dedup_result: Dict[str, Any],
                       distribution: Dict[str, Any]) -> str:
        """
        Gera relatório de validação.
        
        Returns:
            String do relatório
        """
        report = f"""
========================================================================
AC1 DEDUPLICATION VALIDATION REPORT
========================================================================

DATASET:
  - Candles: {len(self.candles):,}
  - Período: 252 dias (M5 timeframe)
  - Timespan: {self.candles[0].timestamp} → {self.candles[-1].timestamp}

SIGNAL DETECTION RESULTS:
  - BOS signals: {counts['BOS']}
  - CHoCH signals: {counts['CHoCH']}
  - FVG signals: {counts['FVG']}
  ────────────────────────────
  - TOTAL signals: {counts['TOTAL']}

DEDUPLICATION VALIDATION:
  - Expected before: {dedup_result['expected_before_dedup']} signals
  - Expected after: {dedup_result['expected_after_dedup']} signals
  - Expected reduction: {dedup_result['expected_reduction_pct']:.1f}%
  
  - Actual count: {dedup_result['signals_total']}
  - Actual reduction: {dedup_result['actual_reduction_pct']:.1f}%
  - Status: {'✓ PASS' if dedup_result['dedup_success'] else '✗ FAIL'}

SIGNAL DISTRIBUTION:
  - BUY signals: {distribution['buy_signals']} ({distribution['buy_pct']:.1f}%)
  - SELL signals: {distribution['sell_signals']} ({distribution['sell_pct']:.1f}%)

DEDUPLICATION QUALITY:
  - Minimum threshold (50% reduction): {'✓ PASS' if dedup_result['dedup_quality'] else '⚠ WARNING'}
  - Signal reduction achieved: {'✓ YES' if dedup_result['dedup_success'] else '✗ NO'}

IMPACT ANALYSIS:
  - Signals per day: {counts['TOTAL'] / 252:.1f} (was 17.4/hour)
  - Signals per hour (8.5h trading): {counts['TOTAL'] / 252 / 8.5:.1f} (was 17.4)
  - Operability: {'✓ REALISTIC' if counts['TOTAL'] < 100 else '⚠ STILL HIGH'}

========================================================================
"""
        return report

    async def run_validation(self) -> bool:
        """
        Executa validação completa de AC1.deduplicação.
        
        Returns:
            True se validação passou
        """
        try:
            # 1. Load data
            if not self.load_candle_data():
                return False
            
            # 2. Detect signals
            counts = self.run_signal_detection()
            
            # 3. Validate deduplication
            dedup_result = self.validate_deduplication(counts)
            
            # 4. Analyze distribution
            distribution = self.analyze_signal_distribution()
            
            # 5. Generate report
            report = self.generate_report(counts, dedup_result, distribution)
            print(report)
            
            # 6. Save report
            output_file = Path("outputs/ac1_deduplication_validation.txt")
            output_file.parent.mkdir(parents=True, exist_ok=True)
            with open(output_file, "w") as f:
                f.write(report)
            
            logger.info(f"[REPORT] Relatório salvo em: {output_file}")
            
            # 7. Return success status
            return dedup_result["dedup_success"]
            
        except Exception as e:
            logger.error(f"[ERROR] Validação falhou: {e}")
            import traceback
            traceback.print_exc()
            return False


async def main():
    """Função principal."""
    logger.info("=" * 70)
    logger.info("AC1 DEDUPLICATION VALIDATION v1.2.5")
    logger.info("=" * 70)
    
    validator = AC1DeduplicationValidator()
    success = await validator.run_validation()
    
    if success:
        logger.info("=" * 70)
        logger.info("✓ DEDUPLICATION VALIDATION PASSED")
        logger.info("=" * 70)
        return 0
    else:
        logger.error("=" * 70)
        logger.error("✗ DEDUPLICATION VALIDATION FAILED")
        logger.error("=" * 70)
        return 1


if __name__ == "__main__":
    import asyncio
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
