"""Servicos de validacao para staging, qualidade e UAT de release.

Pipeline:
- BL-01: validar prontidao minima de staging antes de operacao;
- BL-07: executar gate de qualidade com suite canonica do release;
- BL-08: validar evidencias operacionais do produto WIN/WIN$N.
"""

from __future__ import annotations

import json
import subprocess
import sys
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Callable, Sequence

DEFAULT_PRODUCT_SCOPE = "WIN/WIN$N"
DEFAULT_RUNTIME_EVIDENCE_MAX_AGE_HOURS = 36
DEFAULT_RELEASE_REPORT_REQUIRED_KEYS = ("nome", "aprovado", "resultados")
DEFAULT_RUNTIME_SUMMARY_REQUIRED_KEYS = ("timestamp", "daily_stats", "decisions")
DEFAULT_RUNTIME_DAILY_STATS_REQUIRED_KEYS = (
    "total_trades",
    "winners",
    "losers",
    "open_positions",
)
DEFAULT_EXPECTED_AGENTS = (
    "INICIAR_DIARIOS.bat",
    "INICIAR_MICRO_TENDENCIA_AUTO_TRADE.bat",
    "INICIAR_AGENTE_RL_5000.bat",
    "INICIAR_AGENTE_RL_DIRETO.bat",
)
DEFAULT_CANONICAL_QUALITY_TARGETS = (
    "tests/unit/reconciliadores",
    "tests/unit/test_release_gates.py",
    "tests/unit/test_guardian_agent_coordinator.py",
    "tests/unit/test_macro_guardian_universal.py",
    "tests/unit/test_universal_kill_switch.py",
    "tests/unit/test_market_regime_adapter.py",
    "tests/unit/test_order_manager_learner.py",
    "tests/unit/test_diarios_runtime_mlops_bridge.py",
    "tests/unit/test_logging_recovery_handler.py",
    "tests/unit/test_thread_watchdog_advanced.py",
    "tests/unit/test_diarios_health_monitor.py",
    "tests/unit/test_narrative_persistence.py",
    "tests/unit/test_trade_narrative_correlator.py",
    "tests/unit/test_reflection_action_channel.py",
    "tests/unit/test_adaptive_retraining_pipeline.py",
    "tests/unit/test_directional_bias_detector.py",
    "tests/unit/test_validate_documentation.py",
    "tests/unit/test_multi_agent_conflict_resolver.py",
    "tests/unit/test_diario_order_manager.py",
    "tests/unit/test_s2_6_analytics.py",
)
DEFAULT_CANONICAL_COVERAGE_TARGETS = (
    "src.application.reconciliadores.mt5_sync_validator",
    "src.application.reconciliadores.trade_outcome_reconciler",
    "src.application.reconciliadores.unknown_result_detector",
    "src.application.release_gates",
    "src.application.guardian_agent_coordinator",
    "src.application.macro_guardian_universal",
    "src.application.universal_kill_switch",
    "src.application.market_regime_adapter",
    "src.application.order_manager_learner",
    "src.application.diarios_runtime_mlops_bridge",
    "src.application.logging_recovery_handler",
    "src.application.thread_watchdog_advanced",
    "src.application.diarios_health_monitor",
    "src.application.narrative_persistence",
    "src.application.trade_narrative_correlator",
    "src.application.reflection_action_channel",
    "src.application.adaptive_retraining_pipeline",
    "src.application.directional_bias_detector",
    "src.application.multi_agent_conflict_resolver",
    "src.application.diario_order_manager",
    "agente_micro_tendencia_winfut.s2_6_analytics.trader_feedback_api",
)
DEFAULT_CANONICAL_MYPY_TARGETS = (
    "src/application/release_gates.py",
    "scripts/validate_release_quality_gate.py",
    "scripts/validate_go_live_gates.py",
    "agente_micro_tendencia_winfut/s2_6_analytics/trader_feedback_api.py",
)
DEFAULT_CANONICAL_FORMAT_TARGETS = (
    "src/application/release_gates.py",
    "src/application/orders_executor.py",
    "scripts/validate_release_quality_gate.py",
    "scripts/validate_go_live_gates.py",
    "scripts/agente_rl_direto_independente.py",
    "agente_micro_tendencia_winfut/s2_6_analytics/trader_feedback_api.py",
    "tests/test_orders_executor.py",
    "tests/unit/test_agente_rl_5000_runtime.py",
    "tests/unit/test_agente_rl_direto_guardrails.py",
    "tests/unit/test_agente_rl_direto_runtime.py",
    "tests/unit/test_orders_executor_hardening.py",
    "tests/unit/test_release_gates.py",
    "tests/unit/test_s2_6_analytics.py",
)


def _now_iso() -> str:
    """Retorna timestamp ISO curto para artefatos de release."""
    return datetime.now().isoformat(timespec="seconds")


def _safe_text(value: Any, default: str = "") -> str:
    """Converte um valor qualquer para texto sem gerar excecao."""
    if value is None:
        return default
    text = str(value).strip()
    return text if text else default


def _safe_mapping(value: Any) -> dict[str, Any]:
    """Normaliza uma estrutura para dicionario."""
    if isinstance(value, dict):
        return dict(value)
    return {}


def _read_text(path: Path) -> str:
    """Le um arquivo texto em UTF-8 e retorna string vazia em falha."""
    try:
        return path.read_text(encoding="utf-8")
    except Exception:
        return ""


def _read_json_mapping(path: Path) -> dict[str, Any] | None:
    """Le um JSON e retorna dicionario apenas quando o payload e mapeavel."""
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return None
    if isinstance(payload, dict):
        return dict(payload)
    return None


def _parse_timestamp(value: Any) -> datetime | None:
    """Converte timestamps ISO simples ou UTC ('Z') para datetime naive."""
    text = _safe_text(value)
    if not text:
        return None
    normalized = text[:-1] + "+00:00" if text.endswith("Z") else text
    try:
        parsed = datetime.fromisoformat(normalized)
    except ValueError:
        return None
    if parsed.tzinfo is None:
        return parsed
    return parsed.astimezone().replace(tzinfo=None)


@dataclass(frozen=True)
class GateResultado:
    """Resultado individual de uma verificacao de gate."""

    nome: str
    sucesso: bool
    mensagem: str
    evidencias: list[str] = field(default_factory=list)
    detalhes: dict[str, Any] = field(default_factory=dict)

    def para_dict(self) -> dict[str, object]:
        """Converte o resultado para payload JSON serializavel."""
        return {
            "nome": self.nome,
            "sucesso": self.sucesso,
            "mensagem": self.mensagem,
            "evidencias": list(self.evidencias),
            "detalhes": dict(self.detalhes),
        }


@dataclass(frozen=True)
class RelatorioGate:
    """Relatorio consolidado de um gate."""

    nome: str
    resultados: list[GateResultado]
    aprovado: bool
    metadados: dict[str, Any] = field(default_factory=dict)

    def para_dict(self) -> dict[str, object]:
        """Converte relatorio para dicionario serializavel."""
        return {
            "nome": self.nome,
            "aprovado": self.aprovado,
            "resultados": [item.para_dict() for item in self.resultados],
            "metadados": dict(self.metadados),
        }


@dataclass(frozen=True)
class GoLiveDecision:
    """Artefato final com decisao do release."""

    timestamp: str
    aprovado: bool
    decisao: str
    produto_alvo: str
    gates: list[RelatorioGate]
    agentes_previstos: list[str] = field(default_factory=list)
    evidencias: list[str] = field(default_factory=list)
    resumo: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def from_gates(
        cls,
        *,
        gates: Sequence[RelatorioGate],
        produto_alvo: str = DEFAULT_PRODUCT_SCOPE,
        agentes_previstos: Sequence[str] = DEFAULT_EXPECTED_AGENTS,
    ) -> "GoLiveDecision":
        """Cria a decisao final a partir dos gates executados."""
        gate_list = list(gates)
        aprovado = all(gate.aprovado for gate in gate_list)
        decisao = "GO_LIVE" if aprovado else "NO_GO"
        evidencias: list[str] = []
        for gate in gate_list:
            evidencias.extend(
                _safe_text(item)
                for item in _safe_mapping(gate.metadados).get("evidencias", [])
            )
        evidencias = sorted({e for e in evidencias if e})
        resumo = {
            "total_gates": len(gate_list),
            "gates_aprovados": [gate.nome for gate in gate_list if gate.aprovado],
            "gates_reprovados": [gate.nome for gate in gate_list if not gate.aprovado],
        }
        return cls(
            timestamp=_now_iso(),
            aprovado=aprovado,
            decisao=decisao,
            produto_alvo=produto_alvo,
            gates=gate_list,
            agentes_previstos=list(agentes_previstos),
            evidencias=evidencias,
            resumo=resumo,
        )

    def para_dict(self) -> dict[str, object]:
        """Converte a decisao final para JSON."""
        return {
            "timestamp": self.timestamp,
            "aprovado": self.aprovado,
            "decisao": self.decisao,
            "produto_alvo": self.produto_alvo,
            "agentes_previstos": list(self.agentes_previstos),
            "evidencias": list(self.evidencias),
            "resumo": dict(self.resumo),
            "gates": [gate.para_dict() for gate in self.gates],
        }


class ExecutorComando:
    """Executa comandos de shell com timeout e captura de saida."""

    def __call__(
        self, comando: list[str], timeout_segundos: int
    ) -> tuple[int, str, str]:
        processo = subprocess.run(
            comando,
            capture_output=True,
            text=True,
            timeout=timeout_segundos,
            check=False,
        )
        return processo.returncode, processo.stdout.strip(), processo.stderr.strip()


class StagingReadinessService:
    """BL-01: valida estrutura minima para operacao em staging."""

    def __init__(self, base_dir: Path) -> None:
        self._base_dir = base_dir

    def executar(self) -> RelatorioGate:
        """Executa checks de prontidao de staging."""
        checks = [
            self._check_path(
                nome="db_trading",
                path_rel="data/db/trading.db",
                tipo="arquivo",
                mensagem_ok="Banco SQLite principal encontrado",
            ),
            self._check_path(
                nome="diretorio_modelos",
                path_rel="data/models",
                tipo="diretorio",
                mensagem_ok="Diretorio de modelos encontrado",
            ),
            self._check_path(
                nome="diretorio_outputs",
                path_rel="outputs",
                tipo="diretorio",
                mensagem_ok="Diretorio de outputs encontrado",
            ),
            self._check_path(
                nome="script_healthcheck",
                path_rel="scripts/system_health_monitor.py",
                tipo="arquivo",
                mensagem_ok="Script de healthcheck encontrado",
            ),
        ]
        aprovado = all(item.sucesso for item in checks)
        return RelatorioGate(
            nome="staging_readiness",
            resultados=checks,
            aprovado=aprovado,
            metadados={
                "base_dir": str(self._base_dir),
                "evidencias": [
                    str(self._base_dir / "data/db/trading.db"),
                    str(self._base_dir / "data/models"),
                    str(self._base_dir / "outputs"),
                    str(self._base_dir / "scripts/system_health_monitor.py"),
                ],
            },
        )

    def _check_path(
        self, nome: str, path_rel: str, tipo: str, mensagem_ok: str
    ) -> GateResultado:
        alvo = self._base_dir / path_rel
        if tipo == "arquivo":
            existe = alvo.is_file()
        else:
            existe = alvo.is_dir()
        if existe:
            return GateResultado(nome=nome, sucesso=True, mensagem=mensagem_ok)
        return GateResultado(
            nome=nome,
            sucesso=False,
            mensagem=f"Ausente em staging: {path_rel}",
            evidencias=[str(alvo)],
        )


class QualityGateService:
    """BL-07: executa validacao de qualidade para release."""

    def __init__(
        self,
        executor: Callable[[list[str], int], tuple[int, str, str]] | None = None,
        test_targets: Sequence[str] | None = None,
        coverage_targets: Sequence[str] | None = None,
        mypy_targets: Sequence[str] | None = None,
        format_targets: Sequence[str] | None = None,
        coverage_threshold: int = 80,
    ) -> None:
        self._executor = executor or ExecutorComando()
        self._test_targets = tuple(test_targets or DEFAULT_CANONICAL_QUALITY_TARGETS)
        self._coverage_targets = tuple(
            coverage_targets or DEFAULT_CANONICAL_COVERAGE_TARGETS
        )
        self._mypy_targets = tuple(mypy_targets or DEFAULT_CANONICAL_MYPY_TARGETS)
        self._format_targets = tuple(format_targets or DEFAULT_CANONICAL_FORMAT_TARGETS)
        self._coverage_threshold = int(coverage_threshold)

    @property
    def test_targets(self) -> tuple[str, ...]:
        """Expõe a suite canonica usada pelo gate."""
        return self._test_targets

    @property
    def coverage_targets(self) -> tuple[str, ...]:
        """Expõe os modulos monitorados para cobertura canônica."""
        return self._coverage_targets

    @property
    def mypy_targets(self) -> tuple[str, ...]:
        """Expõe baseline de arquivos analisados pelo mypy strict."""
        return self._mypy_targets

    @property
    def format_targets(self) -> tuple[str, ...]:
        """Expõe baseline de arquivos validados por black/isort."""
        return self._format_targets

    def executar(self) -> RelatorioGate:
        """Executa pytest/cobertura, mypy strict, black e isort."""
        pytest_command = [
            sys.executable,
            "-m",
            "pytest",
            "-q",
            *self._test_targets,
            *[f"--cov={target}" for target in self._coverage_targets],
            f"--cov-fail-under={self._coverage_threshold}",
        ]
        comandos: list[tuple[str, list[str], int]] = [
            (
                "pytest_cov",
                pytest_command,
                1200,
            ),
            (
                "mypy_strict",
                [
                    sys.executable,
                    "-m",
                    "mypy",
                    "--strict",
                    "--follow-imports=skip",
                    *self._mypy_targets,
                ],
                900,
            ),
            (
                "black_check",
                [
                    sys.executable,
                    "-m",
                    "black",
                    "--check",
                    *self._format_targets,
                ],
                600,
            ),
            (
                "isort_check",
                [
                    sys.executable,
                    "-m",
                    "isort",
                    "--check-only",
                    *self._format_targets,
                ],
                600,
            ),
        ]

        resultados: list[GateResultado] = []
        for nome, comando, timeout_segundos in comandos:
            codigo, stdout, stderr = self._executor(comando, timeout_segundos)
            if codigo == 0:
                resultados.append(
                    GateResultado(
                        nome=nome,
                        sucesso=True,
                        mensagem=f"PASS: {stdout or 'sem saida'}",
                        evidencias=[" ".join(comando)],
                        detalhes={"returncode": codigo},
                    )
                )
            else:
                mensagem_falha = stderr or stdout or "Comando falhou sem mensagem"
                resultados.append(
                    GateResultado(
                        nome=nome,
                        sucesso=False,
                        mensagem=f"FAIL: {mensagem_falha}",
                        evidencias=[" ".join(comando)],
                        detalhes={"returncode": codigo},
                    )
                )

        aprovado = all(item.sucesso for item in resultados)
        return RelatorioGate(
            nome="quality_gate_release",
            resultados=resultados,
            aprovado=aprovado,
            metadados={
                "coverage_threshold": self._coverage_threshold,
                "test_targets": list(self._test_targets),
                "coverage_targets": list(self._coverage_targets),
                "mypy_targets": list(self._mypy_targets),
                "format_targets": list(self._format_targets),
            },
        )


class OperationalUATService:
    """BL-08: valida evidencias operacionais do produto atual."""

    def __init__(
        self,
        base_dir: Path,
        *,
        evidence_dir: Path | None = None,
        expected_agents: Sequence[str] | None = None,
        legacy_markers: Sequence[str] | None = None,
        runtime_evidence_max_age_hours: int = DEFAULT_RUNTIME_EVIDENCE_MAX_AGE_HOURS,
    ) -> None:
        self._base_dir = base_dir
        self._evidence_dir = evidence_dir or (base_dir / "outputs" / "release_gates")
        self._expected_agents = tuple(expected_agents or DEFAULT_EXPECTED_AGENTS)
        self._legacy_markers = tuple(legacy_markers or ("BTCUSD",))
        self._runtime_evidence_max_age = timedelta(
            hours=int(runtime_evidence_max_age_hours)
        )

    def executar(self) -> RelatorioGate:
        """Executa a validacao operacional guiada por evidencias locais."""
        checks = [
            self._check_product_scope(),
            self._check_agent_documentation(),
            self._check_release_artifacts(),
            self._check_runtime_artifacts(),
            self._check_legacy_markers_absent(),
        ]
        aprovado = all(item.sucesso for item in checks)
        evidencias = [
            str(self._base_dir / "docs/PRD.md"),
            str(self._base_dir / "docs/OPERACAO_4_AGENTES.md"),
            str(self._evidence_dir / "bl01_staging_readiness.json"),
            str(self._evidence_dir / "bl07_quality_gate.json"),
            str(self._base_dir / "data/db/trading.db"),
            str(self._base_dir / "data/db/last_session_summary.json"),
            str(self._base_dir / "tests/uat/uat_test_cases.py"),
        ]
        return RelatorioGate(
            nome="uat_operacional",
            resultados=checks,
            aprovado=aprovado,
            metadados={
                "produto_alvo": DEFAULT_PRODUCT_SCOPE,
                "agentes_previstos": list(self._expected_agents),
                "evidence_dir": str(self._evidence_dir),
                "runtime_evidence_max_age_hours": int(
                    self._runtime_evidence_max_age.total_seconds() // 3600
                ),
                "release_artifact_required_keys": list(
                    DEFAULT_RELEASE_REPORT_REQUIRED_KEYS
                ),
                "runtime_summary_required_keys": list(
                    DEFAULT_RUNTIME_SUMMARY_REQUIRED_KEYS
                ),
                "evidencias": evidencias,
            },
        )

    def _check_product_scope(self) -> GateResultado:
        prd = _read_text(self._base_dir / "docs/PRD.md")
        operacao = _read_text(self._base_dir / "docs/OPERACAO_4_AGENTES.md")
        missing: list[str] = []
        if DEFAULT_PRODUCT_SCOPE not in prd:
            missing.append(f"docs/PRD.md:{DEFAULT_PRODUCT_SCOPE}")
        for agent in self._expected_agents:
            if agent not in operacao:
                missing.append(f"docs/OPERACAO_4_AGENTES.md:{agent}")
        sucesso = not missing
        mensagem = (
            "Produto WIN/WIN$N e 4 agentes operacionais confirmados"
            if sucesso
            else f"Marcadores ausentes: {', '.join(missing)}"
        )
        return GateResultado(
            nome="product_scope",
            sucesso=sucesso,
            mensagem=mensagem,
            evidencias=[
                str(self._base_dir / "docs/PRD.md"),
                str(self._base_dir / "docs/OPERACAO_4_AGENTES.md"),
            ],
            detalhes={
                "missing_markers": missing,
                "produto_alvo": DEFAULT_PRODUCT_SCOPE,
            },
        )

    def _check_agent_documentation(self) -> GateResultado:
        operacao = _read_text(self._base_dir / "docs/OPERACAO_4_AGENTES.md")
        missing_agents = [
            agent for agent in self._expected_agents if agent not in operacao
        ]
        sucesso = not missing_agents
        mensagem = (
            "Agentes documentados e alinhados ao produto atual"
            if sucesso
            else f"Agentes ausentes na documentacao: {', '.join(missing_agents)}"
        )
        return GateResultado(
            nome="agent_documentation",
            sucesso=sucesso,
            mensagem=mensagem,
            evidencias=[str(self._base_dir / "docs/OPERACAO_4_AGENTES.md")],
            detalhes={"missing_agents": missing_agents},
        )

    def _check_release_artifacts(self) -> GateResultado:
        required = [
            self._evidence_dir / "bl01_staging_readiness.json",
            self._evidence_dir / "bl07_quality_gate.json",
        ]
        missing = [str(path) for path in required if not path.is_file()]
        invalid: list[str] = []
        if not missing:
            for path in required:
                payload = _read_json_mapping(path)
                if payload is None:
                    invalid.append(f"{path}: JSON invalido")
                    continue
                missing_keys = [
                    key
                    for key in DEFAULT_RELEASE_REPORT_REQUIRED_KEYS
                    if key not in payload
                ]
                if missing_keys:
                    invalid.append(f"{path}: sem campos {', '.join(missing_keys)}")
        sucesso = not missing and not invalid
        if sucesso:
            mensagem = "Artefatos BL-01 e BL-07 encontrados e parseaveis"
        elif missing:
            mensagem = f"Artefatos ausentes: {', '.join(missing)}"
        else:
            mensagem = f"Artefatos invalidos: {'; '.join(invalid)}"
        return GateResultado(
            nome="release_artifacts",
            sucesso=sucesso,
            mensagem=mensagem,
            evidencias=[str(path) for path in required],
            detalhes={
                "missing_artifacts": missing,
                "invalid_artifacts": invalid,
            },
        )

    def _check_runtime_artifacts(self) -> GateResultado:
        summary_path = self._base_dir / "data/db/last_session_summary.json"
        required = [
            self._base_dir / "data/db/trading.db",
            summary_path,
            self._base_dir / "outputs",
        ]
        missing = [str(path) for path in required if not path.exists()]
        invalid: list[str] = []
        stale: list[str] = []
        detalhes: dict[str, Any] = {
            "missing_runtime_artifacts": missing,
            "invalid_runtime_artifacts": invalid,
            "stale_runtime_artifacts": stale,
            "runtime_evidence_max_age_hours": int(
                self._runtime_evidence_max_age.total_seconds() // 3600
            ),
        }

        if not missing:
            payload = _read_json_mapping(summary_path)
            if payload is None:
                invalid.append(f"{summary_path}: JSON invalido")
            else:
                missing_keys = [
                    key
                    for key in DEFAULT_RUNTIME_SUMMARY_REQUIRED_KEYS
                    if key not in payload
                ]
                if missing_keys:
                    invalid.append(
                        f"{summary_path}: sem campos {', '.join(missing_keys)}"
                    )

                daily_stats = _safe_mapping(payload.get("daily_stats"))
                missing_daily_stats = [
                    key
                    for key in DEFAULT_RUNTIME_DAILY_STATS_REQUIRED_KEYS
                    if key not in daily_stats
                ]
                if missing_daily_stats:
                    invalid.append(
                        f"{summary_path}: daily_stats sem campos "
                        f"{', '.join(missing_daily_stats)}"
                    )

                decisions = payload.get("decisions")
                if not isinstance(decisions, list):
                    invalid.append(f"{summary_path}: decisions nao e lista")

                embedded_timestamp = _parse_timestamp(payload.get("timestamp"))
                if embedded_timestamp is None:
                    invalid.append(f"{summary_path}: timestamp invalido")
                else:
                    now = datetime.now()
                    idade_timestamp = now - embedded_timestamp
                    detalhes["summary_timestamp"] = embedded_timestamp.isoformat(
                        timespec="seconds"
                    )
                    detalhes["summary_timestamp_age_hours"] = round(
                        idade_timestamp.total_seconds() / 3600,
                        2,
                    )
                    if idade_timestamp > self._runtime_evidence_max_age:
                        stale.append(
                            f"{summary_path}: timestamp com idade de "
                            f"{round(idade_timestamp.total_seconds() / 3600, 2)}h"
                        )

                modified_at = datetime.fromtimestamp(summary_path.stat().st_mtime)
                idade_arquivo = datetime.now() - modified_at
                detalhes["summary_file_mtime"] = modified_at.isoformat(
                    timespec="seconds"
                )
                detalhes["summary_file_age_hours"] = round(
                    idade_arquivo.total_seconds() / 3600,
                    2,
                )
                if idade_arquivo > self._runtime_evidence_max_age:
                    stale.append(
                        f"{summary_path}: arquivo com idade de "
                        f"{round(idade_arquivo.total_seconds() / 3600, 2)}h"
                    )

        sucesso = not missing and not invalid and not stale
        if sucesso:
            mensagem = (
                "Artefatos de runtime validos e frescos "
                f"(<= {int(self._runtime_evidence_max_age.total_seconds() // 3600)}h)"
            )
        else:
            falhas = missing + invalid + stale
            mensagem = f"Artefatos de runtime invalidos: {'; '.join(falhas)}"
        return GateResultado(
            nome="runtime_artifacts",
            sucesso=sucesso,
            mensagem=mensagem,
            evidencias=[str(path) for path in required],
            detalhes=detalhes,
        )

    def _check_legacy_markers_absent(self) -> GateResultado:
        files = [
            self._base_dir / "docs/PRD.md",
            self._base_dir / "docs/OPERACAO_4_AGENTES.md",
            self._base_dir / "tests/uat/uat_test_cases.py",
        ]
        hits: list[str] = []
        for path in files:
            text = _read_text(path)
            for marker in self._legacy_markers:
                if marker in text:
                    hits.append(f"{path}:{marker}")
        sucesso = not hits
        mensagem = (
            "Marcadores legados nao encontrados"
            if sucesso
            else f"Marcadores legados encontrados: {', '.join(hits)}"
        )
        return GateResultado(
            nome="legacy_markers_absent",
            sucesso=sucesso,
            mensagem=mensagem,
            evidencias=[str(path) for path in files],
            detalhes={"hits": hits},
        )
