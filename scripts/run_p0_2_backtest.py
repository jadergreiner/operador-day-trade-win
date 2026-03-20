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
import subprocess
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Optional
import json

# FIX: Adicionar project root ao PYTHONPATH se não estiver
project_root = Path(__file__).parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

from src.infrastructure.database.db_paths import resolve_operational_db_path
from src.infrastructure.backtests.backtest_engine import BacktestEngine
from src.infrastructure.backtests.dataset_auditor import audit_dataset
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
DEFAULT_DB_PATH = str(resolve_operational_db_path(project_root))
DEFAULT_SYMBOL = "WINJ26"
DEFAULT_TIMEFRAME = "M5"
DEFAULT_LOOKBACK_DAYS = 365
DEFAULT_MIN_ROWS = 1000


def _safe_ascii(text: str) -> str:
    """Normaliza mensagem para ASCII para evitar falhas no console Windows."""
    return text.encode("ascii", errors="replace").decode("ascii")


def setup_logging() -> None:
    """Configura logging para arquivo + console."""
    logs_dir = LOGS_OUTPUT_DIR
    logs_dir.mkdir(parents=True, exist_ok=True)

    log_file = logs_dir / f"p0_2_execution_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s | %(levelname)-8s | %(message)s",
        handlers=[
            logging.FileHandler(log_file, encoding="utf-8"),
            logging.StreamHandler(sys.stdout),
        ],
    )

    logging.info("=" * 70)
    logging.info("P0-2 BACKTEST VALIDATION - ETAPA 3 INTEGRATION TEST")
    logging.info("=" * 70)


def _prepare_dataset() -> Dict[str, Any]:
    """Executa preparação do dataset real via script dedicado."""
    script_path = project_root / "scripts" / "prepare_p0_2_mt5_dataset.py"
    command = [
        sys.executable,
        str(script_path),
        "--db-path",
        DEFAULT_DB_PATH,
        "--symbol",
        DEFAULT_SYMBOL,
        "--timeframe",
        DEFAULT_TIMEFRAME,
        "--lookback-days",
        str(DEFAULT_LOOKBACK_DAYS),
        "--min-rows",
        str(DEFAULT_MIN_ROWS),
    ]
    logging.warning("[AUDIT] Dataset nao confiavel - preparando dataset real automaticamente...")
    result = subprocess.run(
        command,
        capture_output=True,
        text=True,
        cwd=str(project_root),
    )
    return {
        "prepare_command": " ".join(command),
        "prepare_exit_code": result.returncode,
        "prepare_stdout": result.stdout.strip(),
        "prepare_stderr": result.stderr.strip(),
        "prepare_success": result.returncode == 0,
    }


def run_dataset_audit() -> Dict[str, Any]:
    """Audita o dataset e persiste resultado para rastreabilidade."""
    logging.info("[AUDIT] Validando dataset historico e proveniencia...")
    BACKTEST_OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    result = audit_dataset(DATASET_PATH)
    prepare_info = None
    if not result.reliable:
        prepare_info = _prepare_dataset()
        if prepare_info.get("prepare_success"):
            logging.info("[AUDIT] Dataset preparado. Reexecutando auditoria...")
            result = audit_dataset(DATASET_PATH)
        else:
            logging.error(
                "[AUDIT] Falha ao preparar dataset automaticamente (exit=%s)",
                prepare_info.get("prepare_exit_code"),
            )
    audit_file = BACKTEST_OUTPUT_DIR / "dataset_audit.json"
    with open(audit_file, "w", encoding="utf-8") as handle:
        payload = result.to_dict()
        if prepare_info is not None:
            payload["auto_prepare"] = prepare_info
        json.dump(payload, handle, indent=2)

    if result.reliable:
        logging.info(
            "[AUDIT] OK Dataset confiavel: rows=%s range=%s..%s",
            result.rows_detected,
            result.date_start_detected,
            result.date_end_detected,
        )
    else:
        logging.error("[AUDIT] FAIL Dataset nao confiavel: %s", ", ".join(result.issues))

    return {
        "audit_passed": result.reliable,
        "audit_file": str(audit_file),
        "audit_issues": result.issues,
        "dataset_rows": result.rows_detected,
        "dataset_range": {
            "start": result.date_start_detected,
            "end": result.date_end_detected,
        },
        "metadata_path": result.metadata_path,
        "auto_prepare": prepare_info,
    }


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
        engine.load_dataset()

        logging.info("[ETAPA 1] Executando 5-fold cross-validation...")
        engine.run_backtest()

        # Salvar resultados
        BACKTEST_OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
        results_file = BACKTEST_OUTPUT_DIR / "backtest_results.json"
        engine.save_results(str(results_file))

        logging.info(f"[ETAPA 1] OK Backtest completo: {results_file}")
        return True

    except Exception as e:
        logging.error(f"[ETAPA 1] ERROR no backtest: {e}", exc_info=True)
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
        logging.info(f"[ETAPA 2] OK Relatorio HTML: {html_file}")

        # Gerar gráficos SVG
        logging.info("[ETAPA 2] Gerando gráficos de visualização...")
        charts_dir = reports_dir / "charts"
        viz = BacktestVisualizer()
        viz.generate_all_charts(results_path, str(charts_dir))
        logging.info(f"[ETAPA 2] OK Graficos SVG: {charts_dir}")

        return True

    except Exception as e:
        logging.error(f"[ETAPA 2] ERROR na geracao de relatorios: {e}", exc_info=True)
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
        validator.save_validation_report(
            results_path,
            str(reports_dir),
            decision_output_dir=str(BACKTEST_OUTPUT_DIR),
        )

        # Log a decisão
        report = validator.get_validation_report()
        logging.info(f"[ETAPA 2] GATE 2 Decision:\n{_safe_ascii(report)}")

        is_pass = decision.value == "PASS"
        status = "PASS" if is_pass else "FAIL"
        action = "Escalar para R$ 100k" if is_pass else "Manter em R$ 50k"

        logging.info(f"[ETAPA 2] {status} - {action}")

        return is_pass

    except Exception as e:
        logging.error(f"[ETAPA 2] ERROR na validacao GATE 2: {e}", exc_info=True)
        return False


def create_status_marker(
    gate2_pass: bool,
    *,
    completed: bool = True,
    audit_info: Optional[Dict[str, Any]] = None,
    error_code: Optional[str] = None,
) -> None:
    """
    Cria arquivo de status para outros scripts consultarem.

    Args:
        gate2_pass: True se GATE 2 passou
    """
    status_file = BACKTEST_OUTPUT_DIR / "p0_2_status.json"

    status = {
        "completed": completed,
        "gate2_passed": gate2_pass,
        "timestamp": datetime.now().isoformat(),
        "backtest_results": str(BACKTEST_OUTPUT_DIR / "backtest_results.json"),
        "reports_dir": str(REPORTS_OUTPUT_DIR),
        "decision": "PASS" if gate2_pass else "FAIL",
        "decision_is_final": (
            completed
            and error_code is None
            and (audit_info or {}).get("audit_passed", True)
        ),
        "error_code": error_code,
    }
    if audit_info is not None:
        status["dataset_audit"] = audit_info

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
        audit_info = run_dataset_audit()
        if not audit_info["audit_passed"]:
            logging.error("[MAIN] Dataset audit falhou - abortando Gate 2 como decisao final")
            create_status_marker(
                False,
                completed=True,
                audit_info=audit_info,
                error_code="DATASET_AUDIT_FAILED",
            )
            return 2

        # Etapa 1: Backtest
        if not run_etapa_1_backtest():
            logging.error("[MAIN] Etapa 1 falhou - abortando")
            create_status_marker(
                False,
                completed=True,
                audit_info=audit_info,
                error_code="BACKTEST_EXECUTION_FAILED",
            )
            return 2

        # Etapa 2: Reporting
        if not run_etapa_2_reporting(results_path):
            logging.error("[MAIN] Etapa 2 (reporting) falhou - continuando com validação")
            # Não aborta aqui - validação é crítica

        # Etapa 2: Validation
        gate2_pass = run_etapa_2_validation(results_path)
        create_status_marker(gate2_pass, completed=True, audit_info=audit_info)

        if gate2_pass:
            logging.info("[MAIN] P0-2 COMPLETOU COM SUCESSO - GATE 2 PASS")
            return 0
        else:
            logging.info("[MAIN] P0-2 COMPLETOU - GATE 2 FAIL")
            return 1

    except Exception as e:
        logging.error(f"[MAIN] Erro fatal: {e}", exc_info=True)
        create_status_marker(
            False,
            completed=True,
            error_code="UNHANDLED_EXCEPTION",
        )
        return 2

    finally:
        logging.info("=" * 70)
        logging.info("P0-2 BACKTEST VALIDATION - EXECUTION FINISHED")
        logging.info("=" * 70)


if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)
