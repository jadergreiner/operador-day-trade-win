#!/usr/bin/env python3
"""
P50-C: Generate Opportunity Summary (Fim do Dia)

Executado ao final do pregão (via INICIAR_DIARIOS.bat) para gerar sumário
com diagnóstico automático e recomendações acionáveis.

Lê:
  - outputs/agent_feedback_live.txt (histórico do dia)
  - config/confidence_history.json (trend de confiança)
  - config/pessimism_mode.json (status de pessimismo)

Gera:
  - outputs/opportunity_summary_YYYYMMDD.txt (sumário estruturado)

Conteúdo do Sumário:
  1. Status geral (zero ops, operações normais, etc)
  2. Confidence atual e trend
  3. Top 5 motivos de rejeição
  4. Diagnóstico automático (pessimismo? anomalia? normal?)
  5. Recomendação acionável ("execute P50-A se...", "aguarde B se...", etc)
  6. Próximos passos

Uso:
  python scripts/generate_opportunity_summary.py

Saída:
  - Console: Sumário visual
  - Arquivo: outputs/opportunity_summary_YYYYMMDD.txt
"""

import json
import sys
from datetime import datetime
from pathlib import Path
from collections import defaultdict
from typing import Optional, Dict, List, Tuple

# Setup paths
PROJECT_ROOT = Path(__file__).parent.parent
OUTPUTS_DIR = PROJECT_ROOT / "outputs"
CONFIG_DIR = PROJECT_ROOT / "config"
DATA_DIR = PROJECT_ROOT / "data"
LOGS_DIR = DATA_DIR / "logs"

# Files
FEEDBACK_LOG_FILE = OUTPUTS_DIR / "agent_feedback_live.txt"
CONFIDENCE_HISTORY_FILE = CONFIG_DIR / "confidence_history.json"
PESSIMISM_CONFIG_FILE = CONFIG_DIR / "pessimism_mode.json"
SUMMARY_LOG_FILE = LOGS_DIR / "generate_opportunity_summary.log"

# Output file (daily)
TODAY = datetime.now().date().isoformat().replace("-", "")
SUMMARY_OUTPUT_FILE = OUTPUTS_DIR / f"opportunity_summary_{TODAY}.txt"


def log_message(message: str) -> None:
    """Log message to file."""
    with open(SUMMARY_LOG_FILE, "a", encoding="utf-8") as f:
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        f.write(f"[{timestamp}] {message}\n")


def parse_feedback_log() -> Tuple[int, Dict[str, int], float]:
    """
    Parse agent_feedback_live.txt

    Returns:
        (operation_count, rejection_reasons_dict, avg_confidence)
    """
    rejection_counter = defaultdict(int)
    operation_count = 0
    confidence_values = []

    if not FEEDBACK_LOG_FILE.exists():
        return 0, {}, 0.0

    try:
        with open(FEEDBACK_LOG_FILE, "r", encoding="utf-8") as f:
            for line in f:
                # Parse lines like:
                # [09:35:22] WING26   HOLD   | score= 2.1 | conf= 45% | ❌ reason

                if "[LOGGER]" in line or "=" * 20 in line:
                    continue  # Skip headers

                if "❌" in line:
                    # Extract rejection reason
                    try:
                        reason_start = line.find("❌")
                        reason = line[reason_start + 2:].strip()
                        rejection_counter[reason] += 1
                    except:
                        pass
                else:
                    operation_count += 1

                # Extract confidence percentage
                try:
                    if "conf=" in line:
                        conf_part = line.split("conf=")[1].split("%")[0].strip()
                        confidence_values.append(int(conf_part) / 100.0)
                except:
                    pass

    except IOError:
        pass

    avg_confidence = sum(confidence_values) / len(confidence_values) if confidence_values else 0.0

    return operation_count, dict(rejection_counter), avg_confidence


def load_confidence_history() -> Tuple[float, float, List[float]]:
    """
    Load confidence history.

    Returns:
        (current_confidence, trend_avg, full_history)
    """
    if not CONFIDENCE_HISTORY_FILE.exists():
        return 0.0, 0.0, []

    try:
        with open(CONFIDENCE_HISTORY_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
            history = data.get("history", [])

            if not history:
                return 0.0, 0.0, []

            current = history[-1]
            trend_avg = sum(history) / len(history)

            return float(current), float(trend_avg), history
    except (json.JSONDecodeError, IOError):
        return 0.0, 0.0, []


def load_pessimism_config() -> bool:
    """Load pessimism detection status."""
    if not PESSIMISM_CONFIG_FILE.exists():
        return False

    try:
        with open(PESSIMISM_CONFIG_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
            return data.get("pessimism_detected", False)
    except (json.JSONDecodeError, IOError):
        return False


def diagnose_system(
    ops_count: int,
    confidence: float,
    rejections: Dict[str, int],
    pessimism_detected: bool
) -> Tuple[str, str]:
    """
    Generate automatic diagnosis and recommendation.

    Returns:
        (diagnosis, recommendation)
    """
    diagnosis = ""
    recommendation = ""

    # Diagnose based on metrics
    if ops_count == 0:
        diagnosis = "🔴 ZERO operações geradas hoje"

        if confidence < 0.45 and pessimism_detected:
            diagnosis += "\n     → Pessimismo crônico detectado"
            recommendation = (
                "✅ AÇÃO RECOMENDADA:\n"
                "   Execute P50-A (detector pessimismo + reset)\n"
                "   Esperado resultado: +15-20 sinais/dia após reset"
            )
        elif confidence < 0.45:
            diagnosis += "\n     → Confiança baixa (0.45 threshold)"
            recommendation = (
                "⚠️ INVESTIGAR:\n"
                "   Verificar logs de decisão do agente\n"
                "   Pode indicar início de pessimismo aprendido"
            )

    elif ops_count > 0 and ops_count < 5:
        diagnosis = f"🟡 POUCAS operações ({ops_count} sinais)"
        if confidence < 0.50:
            diagnosis += "\n     → Confiança reduzida"
            recommendation = (
                "⚠️ MONITORAR:\n"
                "   Sistema operando com cautela\n"
                "   Aguarde recuperação de confiança (P50-B)"
            )

    else:
        diagnosis = f"🟢 OPERAÇÕES NORMAIS ({ops_count} sinais)"
        if confidence > 0.55:
            diagnosis += "\n     → Confiança saudável"
            recommendation = (
                "✅ STATUS: NORMAL\n"
                "   Sistema operando conforme esperado\n"
                "   Continuar monitoramento"
            )

    # Check for anomalies in rejections
    if rejections:
        top_reason = max(rejections.items(), key=lambda x: x[1])
        if top_reason[1] > 50:
            diagnosis += f"\n     → Anomalia: {top_reason[0]} ({top_reason[1]}x)"

    return diagnosis, recommendation


def generate_summary() -> str:
    """Generate complete summary HTML/text."""
    # Parse data
    ops_count, rejections, avg_conf = parse_feedback_log()
    current_conf, conf_trend, history = load_confidence_history()
    pessimism_detected = load_pessimism_config()
    diagnosis, recommendation = diagnose_system(
        ops_count, current_conf, rejections, pessimism_detected
    )

    # Prepare top rejections list
    top_rejections = sorted(rejections.items(), key=lambda x: x[1], reverse=True)[:5]

    # Build summary
    summary = (
        f"\n{'═' * 80}\n"
        f"  SUMÁRIO DIÁRIO - {datetime.now().strftime('%d/%m/%Y')}\n"
        f"{'═' * 80}\n\n"

        f"STATUS OPERACIONAL\n"
        f"─" * 40 + "\n"
        f"Operações geradas: {ops_count} sinais\n"
        f"Confidence atual: {current_conf:.2f} ({int(current_conf*100)}%)\n"
        f"Trend (média histórica): {conf_trend:.2f}\n"
        f"Pessimismo detectado: {'SIM ⚠️' if pessimism_detected else 'NÃO ✅'}\n\n"

        f"DIAGNÓSTICO\n"
        f"─" * 40 + "\n"
        f"{diagnosis}\n\n"
    )

    if top_rejections:
        summary += (
            f"TOP 5 MOTIVOS DE REJEIÇÃO\n"
            f"─" * 40 + "\n"
        )
        for rank, (reason, count) in enumerate(top_rejections, 1):
            summary += f"{rank}. {reason} ({count}x)\n"
        summary += "\n"

    summary += (
        f"RECOMENDAÇÃO\n"
        f"─" * 40 + "\n"
        f"{recommendation}\n\n"

        f"{'═' * 80}\n"
        f"Gerado em: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n"
        f"Arquivo: {SUMMARY_OUTPUT_FILE.name}\n"
        f"{'═' * 80}\n"
    )

    return summary


def main() -> int:
    """Main entry point."""
    try:
        summary = generate_summary()

        # Write to file
        with open(SUMMARY_OUTPUT_FILE, "w", encoding="utf-8") as f:
            f.write(summary)

        # Print to console
        print(summary)

        log_message(f"Sumário gerado com sucesso: {SUMMARY_OUTPUT_FILE}")

        return 0

    except Exception as e:
        print(f"[ERRO] {e}", file=sys.stderr)
        log_message(f"Erro ao gerar sumário: {e}")
        return 1


if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)
