"""Testes unitarios para gates de staging e qualidade de release."""

from __future__ import annotations

import json
import sys
from datetime import datetime, timedelta
from pathlib import Path

from src.application.release_gates import (
    ExecutorComando,
    GateResultado,
    GoLiveDecision,
    OperationalUATService,
    QualityGateService,
    RelatorioGate,
    StagingReadinessService,
)


class ExecutorFalsoSucesso:
    """Executor fake para simular comandos bem-sucedidos."""

    def __call__(
        self, comando: list[str], timeout_segundos: int
    ) -> tuple[int, str, str]:
        _ = timeout_segundos
        return 0, f"executado: {' '.join(comando)}", ""


class ExecutorFalsoFalha:
    """Executor fake para simular falha de comando."""

    def __call__(
        self, comando: list[str], timeout_segundos: int
    ) -> tuple[int, str, str]:
        _ = timeout_segundos
        return 1, "", f"falha: {' '.join(comando)}"


def _criar_relatorio(
    nome: str,
    aprovado: bool,
    evidencias: list[str],
) -> RelatorioGate:
    return RelatorioGate(
        nome=nome,
        resultados=[
            GateResultado(
                nome=f"{nome}_check",
                sucesso=aprovado,
                mensagem="ok" if aprovado else "falhou",
            )
        ],
        aprovado=aprovado,
        metadados={"evidencias": evidencias},
    )


def _runtime_summary_payload(*, timestamp: datetime | None = None) -> dict[str, object]:
    referencia = timestamp or datetime.now()
    return {
        "timestamp": referencia.isoformat(timespec="seconds"),
        "daily_stats": {
            "total_trades": 1,
            "winners": 1,
            "losers": 0,
            "open_positions": 0,
        },
        "decisions": [],
    }


def _write_promotion_payload(
    base_dir: Path,
    *,
    status: str = "aprovado",
    motivo: str = "gate aprovado para release",
) -> None:
    (base_dir / "outputs" / "scheduler_symbol_promotion_20260406_160217.json").write_text(
        json.dumps(
            {
                "scheduler_symbol_promotion": {
                    "status": status,
                    "motivo": motivo,
                }
            }
        ),
        encoding="utf-8",
    )


def test_staging_readiness_aprova_estrutura_minima(tmp_path: Path) -> None:
    """BL-01: staging deve aprovar quando artefatos obrigatorios existem."""
    (tmp_path / "data" / "db").mkdir(parents=True)
    (tmp_path / "data" / "models").mkdir(parents=True)
    (tmp_path / "outputs").mkdir(parents=True)
    (tmp_path / "scripts").mkdir(parents=True)
    (tmp_path / "data" / "db" / "trading.db").write_text("ok", encoding="utf-8")
    (tmp_path / "scripts" / "system_health_monitor.py").write_text(
        "print('ok')",
        encoding="utf-8",
    )

    servico = StagingReadinessService(base_dir=tmp_path)
    relatorio = servico.executar()

    assert relatorio.aprovado is True
    assert all(item.sucesso for item in relatorio.resultados)


def test_staging_readiness_reprova_sem_banco(tmp_path: Path) -> None:
    """BL-01: staging deve reprovar sem banco principal."""
    (tmp_path / "data" / "models").mkdir(parents=True)
    (tmp_path / "outputs").mkdir(parents=True)
    (tmp_path / "scripts").mkdir(parents=True)
    (tmp_path / "scripts" / "system_health_monitor.py").write_text(
        "print('ok')",
        encoding="utf-8",
    )

    servico = StagingReadinessService(base_dir=tmp_path)
    relatorio = servico.executar()

    assert relatorio.aprovado is False
    assert any(
        item.nome == "db_trading" and not item.sucesso for item in relatorio.resultados
    )


def test_quality_gate_aprova_quando_todos_comandos_passam() -> None:
    """BL-07: quality gate aprova com pytest/mypy/black/isort em sucesso."""
    servico = QualityGateService(executor=ExecutorFalsoSucesso())

    relatorio = servico.executar()

    assert relatorio.aprovado is True
    assert len(relatorio.resultados) == 4
    assert all(item.sucesso for item in relatorio.resultados)


def test_quality_gate_reprova_quando_um_comando_falha() -> None:
    """BL-07: quality gate reprova com qualquer etapa falhando."""

    class ExecutorMisto:
        def __init__(self) -> None:
            self._contador = 0

        def __call__(
            self, comando: list[str], timeout_segundos: int
        ) -> tuple[int, str, str]:
            _ = comando, timeout_segundos
            self._contador += 1
            if self._contador == 2:
                return 1, "", "mypy falhou"
            return 0, "ok", ""

    servico = QualityGateService(executor=ExecutorMisto())
    relatorio = servico.executar()

    assert relatorio.aprovado is False
    assert any(
        item.nome == "mypy_strict" and not item.sucesso for item in relatorio.resultados
    )


def test_quality_gate_usa_suite_canonica_explicitamente_sem_ati5() -> None:
    """BL-07 deve usar allowlist explicita e excluir o suite ATI-5."""
    comandos: list[list[str]] = []

    class ExecutorCaptura:
        def __call__(
            self, comando: list[str], timeout_segundos: int
        ) -> tuple[int, str, str]:
            _ = timeout_segundos
            comandos.append(list(comando))
            return 0, "ok", ""

    servico = QualityGateService(executor=ExecutorCaptura())
    relatorio = servico.executar()

    assert relatorio.aprovado is True
    assert "tests/unit/test_ati5_ml_features.py" not in servico.test_targets
    assert comandos
    assert comandos[0][0] == sys.executable
    primeiro = " ".join(comandos[0])
    assert "pytest tests" not in primeiro
    assert "-m pytest" in primeiro
    assert "tests/unit/test_release_gates.py" in primeiro
    assert "tests/unit/test_validate_documentation.py" in primeiro
    assert "--cov=src.application.release_gates" in primeiro
    assert "--cov-fail-under=80" in primeiro

    segundo = " ".join(comandos[1])
    assert "-m mypy" in segundo
    assert "--strict" in segundo
    assert "--follow-imports=skip" in segundo
    assert "src/application/release_gates.py" in segundo

    terceiro = " ".join(comandos[2])
    quarto = " ".join(comandos[3])
    assert "src/application/release_gates.py" in terceiro
    assert "src/application/release_gates.py" in quarto


def test_operational_uat_aprova_com_evidencias_locais(tmp_path: Path) -> None:
    """BL-08 aprova com docs, runtime e artefatos locais do produto atual."""
    (tmp_path / "docs").mkdir(parents=True)
    (tmp_path / "docs" / "PRD.md").write_text(
        "Produto WIN/WIN$N para operacao real.",
        encoding="utf-8",
    )
    (tmp_path / "docs" / "OPERACAO_4_AGENTES.md").write_text(
        "\n".join(
            [
                "## Agente 1: INICIAR_DIARIOS.bat",
                "## Agente 2: INICIAR_MICRO_TENDENCIA_AUTO_TRADE.bat",
                "## Agente 3: INICIAR_AGENTE_RL_5000.bat",
                "## Agente 4: INICIAR_AGENTE_RL_DIRETO.bat",
            ]
        ),
        encoding="utf-8",
    )
    (tmp_path / "data" / "db").mkdir(parents=True)
    (tmp_path / "data" / "db" / "trading.db").write_text("ok", encoding="utf-8")
    (tmp_path / "data" / "db" / "last_session_summary.json").write_text(
        json.dumps(_runtime_summary_payload()),
        encoding="utf-8",
    )
    (tmp_path / "outputs" / "release_gates").mkdir(parents=True)
    (tmp_path / "outputs").mkdir(exist_ok=True)
    (tmp_path / "tests" / "uat").mkdir(parents=True)
    (tmp_path / "tests" / "uat" / "uat_test_cases.py").write_text(
        "# runner limpo\n",
        encoding="utf-8",
    )

    (tmp_path / "outputs" / "release_gates" / "bl01_staging_readiness.json").write_text(
        json.dumps({"nome": "staging_readiness", "aprovado": True, "resultados": []}),
        encoding="utf-8",
    )
    (tmp_path / "outputs" / "release_gates" / "bl07_quality_gate.json").write_text(
        json.dumps(
            {"nome": "quality_gate_release", "aprovado": True, "resultados": []}
        ),
        encoding="utf-8",
    )
    _write_promotion_payload(tmp_path, status="aprovado")

    servico = OperationalUATService(base_dir=tmp_path)
    relatorio = servico.executar()

    assert relatorio.aprovado is True
    assert relatorio.nome == "uat_operacional"
    assert all(item.sucesso for item in relatorio.resultados)
    assert relatorio.metadados["produto_alvo"] == "WIN/WIN$N"


def test_operational_uat_tolera_sem_promocao_na_janela_pre_open(tmp_path: Path) -> None:
    """BL-08 pode tolerar `sem_promocao` na janela mínima de pre-open."""
    (tmp_path / "docs").mkdir(parents=True)
    (tmp_path / "docs" / "PRD.md").write_text(
        "Produto WIN/WIN$N para operacao real.",
        encoding="utf-8",
    )
    (tmp_path / "docs" / "OPERACAO_4_AGENTES.md").write_text(
        "\n".join(
            [
                "## Agente 1: INICIAR_DIARIOS.bat",
                "## Agente 2: INICIAR_MICRO_TENDENCIA_AUTO_TRADE.bat",
                "## Agente 3: INICIAR_AGENTE_RL_5000.bat",
                "## Agente 4: INICIAR_AGENTE_RL_DIRETO.bat",
            ]
        ),
        encoding="utf-8",
    )
    (tmp_path / "data" / "db").mkdir(parents=True)
    (tmp_path / "data" / "db" / "trading.db").write_text("ok", encoding="utf-8")
    (tmp_path / "data" / "db" / "last_session_summary.json").write_text(
        json.dumps(_runtime_summary_payload(timestamp=datetime(2026, 4, 7, 8, 55))),
        encoding="utf-8",
    )
    (tmp_path / "outputs" / "release_gates").mkdir(parents=True)
    (tmp_path / "outputs").mkdir(exist_ok=True)
    (tmp_path / "tests" / "uat").mkdir(parents=True)
    (tmp_path / "tests" / "uat" / "uat_test_cases.py").write_text(
        "# runner limpo\n",
        encoding="utf-8",
    )
    (tmp_path / "outputs" / "release_gates" / "bl01_staging_readiness.json").write_text(
        json.dumps({"nome": "staging_readiness", "aprovado": True, "resultados": []}),
        encoding="utf-8",
    )
    (tmp_path / "outputs" / "release_gates" / "bl07_quality_gate.json").write_text(
        json.dumps(
            {"nome": "quality_gate_release", "aprovado": True, "resultados": []}
        ),
        encoding="utf-8",
    )
    _write_promotion_payload(tmp_path, status="sem_promocao", motivo="pre-open tolerado")

    servico = OperationalUATService(
        base_dir=tmp_path,
        promotion_gate_allow_sem_promocao_until="09:05",
        now_provider=lambda: datetime(2026, 4, 7, 8, 55),
    )
    relatorio = servico.executar()

    assert relatorio.aprovado is True
    assert any(item.nome == "scheduler_promotion_gate" and item.sucesso for item in relatorio.resultados)


def test_operational_uat_reprova_quando_legado_btcusd_aparece(tmp_path: Path) -> None:
    """BL-08 reprova se o runner ou docs ainda expuserem BTCUSD."""
    (tmp_path / "docs").mkdir(parents=True)
    (tmp_path / "docs" / "PRD.md").write_text(
        "Produto WIN/WIN$N para operacao real.",
        encoding="utf-8",
    )
    (tmp_path / "docs" / "OPERACAO_4_AGENTES.md").write_text(
        "\n".join(
            [
                "## Agente 1: INICIAR_DIARIOS.bat",
                "## Agente 2: INICIAR_MICRO_TENDENCIA_AUTO_TRADE.bat",
                "## Agente 3: INICIAR_AGENTE_RL_5000.bat",
                "## Agente 4: INICIAR_AGENTE_RL_DIRETO.bat",
            ]
        ),
        encoding="utf-8",
    )
    (tmp_path / "data" / "db").mkdir(parents=True)
    (tmp_path / "data" / "db" / "trading.db").write_text("ok", encoding="utf-8")
    (tmp_path / "data" / "db" / "last_session_summary.json").write_text(
        json.dumps(_runtime_summary_payload()),
        encoding="utf-8",
    )
    (tmp_path / "outputs" / "release_gates").mkdir(parents=True)
    (tmp_path / "tests" / "uat").mkdir(parents=True)
    (tmp_path / "tests" / "uat" / "uat_test_cases.py").write_text(
        "print('BTCUSD')\n",
        encoding="utf-8",
    )
    (tmp_path / "outputs" / "release_gates" / "bl01_staging_readiness.json").write_text(
        json.dumps({"nome": "staging_readiness", "aprovado": True, "resultados": []}),
        encoding="utf-8",
    )
    (tmp_path / "outputs" / "release_gates" / "bl07_quality_gate.json").write_text(
        json.dumps(
            {"nome": "quality_gate_release", "aprovado": True, "resultados": []}
        ),
        encoding="utf-8",
    )

    servico = OperationalUATService(base_dir=tmp_path)
    relatorio = servico.executar()

    assert relatorio.aprovado is False
    assert any(
        item.nome == "legacy_markers_absent" and not item.sucesso
        for item in relatorio.resultados
    )


def test_operational_uat_reprova_runtime_stale(tmp_path: Path) -> None:
    """BL-08 reprova quando a evidencia diaria de runtime esta velha."""
    (tmp_path / "docs").mkdir(parents=True)
    (tmp_path / "docs" / "PRD.md").write_text(
        "Produto WIN/WIN$N para operacao real.",
        encoding="utf-8",
    )
    (tmp_path / "docs" / "OPERACAO_4_AGENTES.md").write_text(
        "\n".join(
            [
                "## Agente 1: INICIAR_DIARIOS.bat",
                "## Agente 2: INICIAR_MICRO_TENDENCIA_AUTO_TRADE.bat",
                "## Agente 3: INICIAR_AGENTE_RL_5000.bat",
                "## Agente 4: INICIAR_AGENTE_RL_DIRETO.bat",
            ]
        ),
        encoding="utf-8",
    )
    (tmp_path / "data" / "db").mkdir(parents=True)
    (tmp_path / "data" / "db" / "trading.db").write_text("ok", encoding="utf-8")
    runtime_path = tmp_path / "data" / "db" / "last_session_summary.json"
    runtime_path.write_text(
        json.dumps(
            _runtime_summary_payload(
                timestamp=datetime.now() - timedelta(days=3),
            )
        ),
        encoding="utf-8",
    )
    (tmp_path / "outputs" / "release_gates").mkdir(parents=True)
    (tmp_path / "tests" / "uat").mkdir(parents=True)
    (tmp_path / "tests" / "uat" / "uat_test_cases.py").write_text(
        "# runner limpo\n",
        encoding="utf-8",
    )
    (tmp_path / "outputs" / "release_gates" / "bl01_staging_readiness.json").write_text(
        json.dumps({"nome": "staging_readiness", "aprovado": True, "resultados": []}),
        encoding="utf-8",
    )
    (tmp_path / "outputs" / "release_gates" / "bl07_quality_gate.json").write_text(
        json.dumps(
            {"nome": "quality_gate_release", "aprovado": True, "resultados": []}
        ),
        encoding="utf-8",
    )

    servico = OperationalUATService(
        base_dir=tmp_path, runtime_evidence_max_age_hours=36
    )
    relatorio = servico.executar()

    assert relatorio.aprovado is False
    assert any(
        item.nome == "runtime_artifacts"
        and not item.sucesso
        and "idade" in item.mensagem
        for item in relatorio.resultados
    )


def test_operational_uat_reprova_release_artifact_sem_campos_minimos(
    tmp_path: Path,
) -> None:
    """BL-08 reprova quando BL-01/BL-07 existem, mas nao sao evidencias validas."""
    (tmp_path / "docs").mkdir(parents=True)
    (tmp_path / "docs" / "PRD.md").write_text(
        "Produto WIN/WIN$N para operacao real.",
        encoding="utf-8",
    )
    (tmp_path / "docs" / "OPERACAO_4_AGENTES.md").write_text(
        "\n".join(
            [
                "## Agente 1: INICIAR_DIARIOS.bat",
                "## Agente 2: INICIAR_MICRO_TENDENCIA_AUTO_TRADE.bat",
                "## Agente 3: INICIAR_AGENTE_RL_5000.bat",
                "## Agente 4: INICIAR_AGENTE_RL_DIRETO.bat",
            ]
        ),
        encoding="utf-8",
    )
    (tmp_path / "data" / "db").mkdir(parents=True)
    (tmp_path / "data" / "db" / "trading.db").write_text("ok", encoding="utf-8")
    (tmp_path / "data" / "db" / "last_session_summary.json").write_text(
        json.dumps(_runtime_summary_payload()),
        encoding="utf-8",
    )
    (tmp_path / "outputs" / "release_gates").mkdir(parents=True)
    (tmp_path / "tests" / "uat").mkdir(parents=True)
    (tmp_path / "tests" / "uat" / "uat_test_cases.py").write_text(
        "# runner limpo\n",
        encoding="utf-8",
    )
    (tmp_path / "outputs" / "release_gates" / "bl01_staging_readiness.json").write_text(
        json.dumps({"aprovado": True}),
        encoding="utf-8",
    )
    (tmp_path / "outputs" / "release_gates" / "bl07_quality_gate.json").write_text(
        json.dumps({"nome": "quality_gate_release"}),
        encoding="utf-8",
    )

    servico = OperationalUATService(base_dir=tmp_path)
    relatorio = servico.executar()

    assert relatorio.aprovado is False
    assert any(
        item.nome == "release_artifacts" and not item.sucesso
        for item in relatorio.resultados
    )


def test_operational_uat_reprova_quando_promocao_scheduler_reprovada(
    tmp_path: Path,
) -> None:
    """BL-08 reprova release quando gate de promocao do scheduler esta reprovado."""
    (tmp_path / "docs").mkdir(parents=True)
    (tmp_path / "docs" / "PRD.md").write_text(
        "Produto WIN/WIN$N para operacao real.",
        encoding="utf-8",
    )
    (tmp_path / "docs" / "OPERACAO_4_AGENTES.md").write_text(
        "\n".join(
            [
                "## Agente 1: INICIAR_DIARIOS.bat",
                "## Agente 2: INICIAR_MICRO_TENDENCIA_AUTO_TRADE.bat",
                "## Agente 3: INICIAR_AGENTE_RL_5000.bat",
                "## Agente 4: INICIAR_AGENTE_RL_DIRETO.bat",
            ]
        ),
        encoding="utf-8",
    )
    (tmp_path / "data" / "db").mkdir(parents=True)
    (tmp_path / "data" / "db" / "trading.db").write_text("ok", encoding="utf-8")
    (tmp_path / "data" / "db" / "last_session_summary.json").write_text(
        json.dumps(_runtime_summary_payload()),
        encoding="utf-8",
    )
    (tmp_path / "outputs" / "release_gates").mkdir(parents=True)
    (tmp_path / "tests" / "uat").mkdir(parents=True)
    (tmp_path / "tests" / "uat" / "uat_test_cases.py").write_text(
        "# runner limpo\n",
        encoding="utf-8",
    )
    (tmp_path / "outputs" / "release_gates" / "bl01_staging_readiness.json").write_text(
        json.dumps({"nome": "staging_readiness", "aprovado": True, "resultados": []}),
        encoding="utf-8",
    )
    (tmp_path / "outputs" / "release_gates" / "bl07_quality_gate.json").write_text(
        json.dumps(
            {"nome": "quality_gate_release", "aprovado": True, "resultados": []}
        ),
        encoding="utf-8",
    )
    _write_promotion_payload(
        tmp_path,
        status="reprovado",
        motivo="dd_curto_excedeu_limite",
    )

    servico = OperationalUATService(base_dir=tmp_path)
    relatorio = servico.executar()

    assert relatorio.aprovado is False
    assert any(
        item.nome == "scheduler_promotion_gate" and not item.sucesso
        for item in relatorio.resultados
    )


def test_operational_uat_reprova_quando_promocao_scheduler_sem_promocao(
    tmp_path: Path,
) -> None:
    """BL-08 estrito deve reprovar quando status da promocao for sem_promocao."""
    (tmp_path / "docs").mkdir(parents=True)
    (tmp_path / "docs" / "PRD.md").write_text(
        "Produto WIN/WIN$N para operacao real.",
        encoding="utf-8",
    )
    (tmp_path / "docs" / "OPERACAO_4_AGENTES.md").write_text(
        "\n".join(
            [
                "## Agente 1: INICIAR_DIARIOS.bat",
                "## Agente 2: INICIAR_MICRO_TENDENCIA_AUTO_TRADE.bat",
                "## Agente 3: INICIAR_AGENTE_RL_5000.bat",
                "## Agente 4: INICIAR_AGENTE_RL_DIRETO.bat",
            ]
        ),
        encoding="utf-8",
    )
    (tmp_path / "data" / "db").mkdir(parents=True)
    (tmp_path / "data" / "db" / "trading.db").write_text("ok", encoding="utf-8")
    (tmp_path / "data" / "db" / "last_session_summary.json").write_text(
        json.dumps(_runtime_summary_payload()),
        encoding="utf-8",
    )
    (tmp_path / "outputs" / "release_gates").mkdir(parents=True)
    (tmp_path / "tests" / "uat").mkdir(parents=True)
    (tmp_path / "tests" / "uat" / "uat_test_cases.py").write_text(
        "# runner limpo\n",
        encoding="utf-8",
    )
    (tmp_path / "outputs" / "release_gates" / "bl01_staging_readiness.json").write_text(
        json.dumps({"nome": "staging_readiness", "aprovado": True, "resultados": []}),
        encoding="utf-8",
    )
    (tmp_path / "outputs" / "release_gates" / "bl07_quality_gate.json").write_text(
        json.dumps(
            {"nome": "quality_gate_release", "aprovado": True, "resultados": []}
        ),
        encoding="utf-8",
    )

    servico = OperationalUATService(base_dir=tmp_path)
    relatorio = servico.executar()

    assert relatorio.aprovado is False
    assert any(
        item.nome == "scheduler_promotion_gate" and not item.sucesso
        for item in relatorio.resultados
    )

def test_go_live_decision_serializa_gates_e_evidencias() -> None:
    """A decisao final deve ser serializavel e consolidar os 3 gates."""
    staging = _criar_relatorio("staging_readiness", True, ["e1", "e2"])
    quality = _criar_relatorio("quality_gate_release", True, ["e2", "e3"])
    uat = _criar_relatorio("uat_operacional", False, ["e4"])

    decision = GoLiveDecision.from_gates(gates=[staging, quality, uat])
    payload = decision.para_dict()

    assert payload["aprovado"] is False
    assert payload["decisao"] == "NO_GO"
    assert payload["produto_alvo"] == "WIN/WIN$N"
    assert payload["resumo"]["total_gates"] == 3
    assert payload["resumo"]["gates_aprovados"] == [
        "staging_readiness",
        "quality_gate_release",
    ]
    assert payload["resumo"]["gates_reprovados"] == ["uat_operacional"]
    assert payload["evidencias"] == ["e1", "e2", "e3", "e4"]
    assert payload["gates"][2]["nome"] == "uat_operacional"


def test_executor_comando_retorna_saida_de_processo() -> None:
    """Executor real deve retornar codigo, stdout e stderr."""
    executor = ExecutorComando()
    codigo, stdout, stderr = executor(
        ["python", "-c", "print('ok')"], timeout_segundos=10
    )

    assert codigo == 0
    assert "ok" in stdout
    assert stderr == ""


def test_gate_resultado_para_dict() -> None:
    """Resultado deve ser serializavel para uso em relatorios JSON."""
    resultado = GateResultado(nome="pytest_cov", sucesso=True, mensagem="ok")
    payload = resultado.para_dict()

    assert payload["nome"] == "pytest_cov"
    assert payload["sucesso"] is True
    assert payload["mensagem"] == "ok"
