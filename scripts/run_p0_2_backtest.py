"""
Run P0-2 Backtest - Script que executa P0-2 completo em background.

Fluxo:
1. Carregar dataset histórico
2. Executar backtest 5-fold completo
3. Gerar métricas e relatório HTML
4. Validar GATE 2 criteria
5. Salvar decisão em JSON

Designed para ser chamado via: start /B python scripts/run_p0_2_backtest.py
"""

import logging
import sys
from datetime import datetime
from pathlib import Path
from typing import Optional

from src.infrastructure.backtests.backtest_engine import BacktestEngine
from src.infrastructure.reports.backtest_reporter import BacktestReporter
from src.infrastructure.reports.backtest_visualizer import BacktestVisualizer
from src.infrastructure.validators.backtest_validator import BacktestValidator


# ============================================================================
# CONFIGURAÇÃO
# ============================================================================

DATASET_PATH = "data/training_dataset.csv"
BACKTEST_OUTPUT_DIR = Path("data/backtest")
REPORTS_OUTPUT_DIR = Path("data/backtest/reports")
LOGS_OUTPUT_DIR = Path("data/logs")


def setup_logging() -> None:
    """Configura logging para arquivo + console."""
    logs_dir = LOGS_OUTPUT_DIR
    logs_dir.mkdir(parents=True, exist_ok=True)

    log_file = logs_dir / f"p0_2_execution_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s | %(levelname)-8s | %(message)s",
        handlers=[
            logging.FileHandler(log_file),
            logging.StreamHandler(sys.stdout),
        ],
    )

    logging.info("=" * 70)
    logging.info("P0-2 BACKTEST VALIDATION - ETAPA 3 INTEGRATION TEST")
    logging.info("=" * 70)


def run_etapa_1_backtest() -> bool:
    """
    Executa Etapa 1: Design & Infrastructure.

    Returns:
        True se sucesso, False se falha
    """
    logging.info("[ETAPA 1] Iniciando backtest de 252 dias...")

    try:
        # Validar dataset existe
        if not Path(DATASET_PATH).exists():
            logging.error(f"[ETAPA 1] ✗ Dataset não encontrado: {DATASET_PATH}")
            return False

        # Executar backtest
        engine = BacktestEngine()
        logging.info("[ETAPA 1] Carregando dataset...")
        engine.load_dataset(DATASET_PATH)

        logging.info("[ETAPA 1] Executando 5-fold cross-validation...")
        engine.run_backtest()

        # Salvar resultados
        BACKTEST_OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
        results_file = BACKTEST_OUTPUT_DIR / "backtest_results.json"
        engine.save_results(str(results_file))

        logging.info(f"[ETAPA 1] ✓ Backtest completo: {results_file}")
        return True

    except Exception as e:
        logging.error(f"[ETAPA 1] ✗ Erro no backtest: {e}", exc_info=True)
        return False


def run_etapa_2_reporting(results_path: str) -> bool:
    """
    Executa Etapa 2: Reporting & Validation.

    Args:
        results_path: Caminho do backtest_results.json

    Returns:
        True se sucesso, False se falha
    """
    logging.info("[ETAPA 2] Gerando relatórios e visualizações...")

    try:
        reports_dir = REPORTS_OUTPUT_DIR
        reports_dir.mkdir(parents=True, exist_ok=True)

        # Gerar HTML
        logging.info("[ETAPA 2] Gerando relatório HTML...")
        reporter = BacktestReporter()
        html_file = reports_dir / "backtest_report.html"
        reporter.generate_html(results_path, str(html_file))
        logging.info(f"[ETAPA 2] ✓ Relatório HTML: {html_file}")

        # Gerar gráficos SVG
        logging.info("[ETAPA 2] Gerando gráficos de visualização...")
        charts_dir = reports_dir / "charts"
        viz = BacktestVisualizer()
        viz.generate_all_charts(results_path, str(charts_dir))
        logging.info(f"[ETAPA 2] ✓ Gráficos SVG: {charts_dir}")

        return True

    except Exception as e:
        logging.error(f"[ETAPA 2] ✗ Erro na geração de relatórios: {e}", exc_info=True)
        return False


def run_etapa_2_validation(results_path: str) -> bool:
    """
    Executa validação GATE 2.

    Args:
        results_path: Caminho do backtest_results.json

    Returns:
        True se GATE 2 PASS, False se FAIL
    """
    logging.info("[ETAPA 2] Validando critérios GATE 2...")

    try:
        validator = BacktestValidator()
        decision = validator.validate(results_path)

        # Salvar relatório de validação
        reports_dir = REPORTS_OUTPUT_DIR
        validator.save_validation_report(results_path, str(reports_dir))

        # Log a decisão
        report = validator.get_validation_report()
        logging.info(f"[ETAPA 2] GATE 2 Decision:\n{report}")

        is_pass = decision.value == "PASS"
        status = "✓ PASS" if is_pass else "✗ FAIL"
        action = "Escalar para R$ 100k" if is_pass else "Manter em R$ 50k"

        logging.info(f"[ETAPA 2] {status} - {action}")

        return is_pass

    except Exception as e:
        logging.error(f"[ETAPA 2] ✗ Erro na validação GATE 2: {e}", exc_info=True)
        return False


def create_status_marker(gate2_pass: bool) -> None:
    """
    Cria arquivo de status para outros scripts consultarem.

    Args:
        gate2_pass: True se GATE 2 passou
    """
    status_file = BACKTEST_OUTPUT_DIR / "p0_2_status.json"

    import json

    status = {
        "completed": True,
        "gate2_passed": gate2_pass,
        "timestamp": datetime.now().isoformat(),
        "backtest_results": str(BACKTEST_OUTPUT_DIR / "backtest_results.json"),
        "reports_dir": str(REPORTS_OUTPUT_DIR),
        "decision": "PASS" if gate2_pass else "FAIL",
    }

    with open(status_file, "w") as f:
        json.dump(status, f, indent=2)

    logging.info(f"[STATUS] Status marker criado: {status_file}")


def main() -> int:
    """
    Executa pipeline completo P0-2.

    Returns:
        0 se GATE 2 PASS, 1 se GATE 2 FAIL, 2 se erro
    """
    setup_logging()

    results_path = str(BACKTEST_OUTPUT_DIR / "backtest_results.json")

    try:
        # Etapa 1: Backtest
        if not run_etapa_1_backtest():
            logging.error("[MAIN] Etapa 1 falhou - abortando")
            create_status_marker(False)
            return 2

        # Etapa 2: Reporting
        if not run_etapa_2_reporting(results_path):
            logging.error("[MAIN] Etapa 2 (reporting) falhou - continuando com validação")
            # Não aborta aqui - validação é crítica

        # Etapa 2: Validation
        gate2_pass = run_etapa_2_validation(results_path)
        create_status_marker(gate2_pass)

        if gate2_pass:
            logging.info("[MAIN] ✓ P0-2 COMPLETOU COM SUCESSO - GATE 2 PASS")
            return 0
        else:
            logging.info("[MAIN] ✗ P0-2 COMPLETOU - GATE 2 FAIL")
            return 1

    except Exception as e:
        logging.error(f"[MAIN] Erro fatal: {e}", exc_info=True)
        create_status_marker(False)
        return 2

    finally:
        logging.info("=" * 70)
        logging.info("P0-2 BACKTEST VALIDATION - EXECUTION FINISHED")
        logging.info("=" * 70)


if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)
