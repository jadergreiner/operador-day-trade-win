"""Testes unitarios para gates de staging e qualidade de release."""

from __future__ import annotations

from pathlib import Path

from src.application.release_gates import (
    ExecutorComando,
    GateResultado,
    QualityGateService,
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
