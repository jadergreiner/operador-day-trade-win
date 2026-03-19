"""Servicos de validacao para staging e qualidade de release.

Pipeline:
- BL-01: validar prontidao minima de staging antes de operacao;
- BL-07: executar gate de qualidade (pytest/mypy/black/isort).
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import subprocess
import sys
from typing import Callable


@dataclass(frozen=True)
class GateResultado:
    """Resultado individual de uma verificacao de gate."""

    nome: str
    sucesso: bool
    mensagem: str

    def para_dict(self) -> dict[str, object]:
        """Converte o resultado para payload JSON serializavel."""
        return {
            "nome": self.nome,
            "sucesso": self.sucesso,
            "mensagem": self.mensagem,
        }


@dataclass(frozen=True)
class RelatorioGate:
    """Relatorio consolidado de um gate."""

    nome: str
    resultados: list[GateResultado]
    aprovado: bool

    def para_dict(self) -> dict[str, object]:
        """Converte relatorio para dicionario."""
        return {
            "nome": self.nome,
            "aprovado": self.aprovado,
            "resultados": [item.para_dict() for item in self.resultados],
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
            nome="staging_readiness", resultados=checks, aprovado=aprovado
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
        )


class QualityGateService:
    """BL-07: executa validacao de qualidade para release."""

    def __init__(
        self,
        executor: Callable[[list[str], int], tuple[int, str, str]] | None = None,
    ) -> None:
        self._executor = executor or ExecutorComando()

    def executar(self) -> RelatorioGate:
        """Executa pytest/cobertura, mypy strict, black e isort."""
        comandos: list[tuple[str, list[str], int]] = [
            (
                "pytest_cov",
                [
                    sys.executable,
                    "-m",
                    "pytest",
                    "tests",
                    "--cov=src",
                    "--cov-fail-under=80",
                    "-q",
                ],
                1200,
            ),
            (
                "mypy_strict",
                [sys.executable, "-m", "mypy", "src", "--strict"],
                900,
            ),
            (
                "black_check",
                [sys.executable, "-m", "black", "--check", "src", "tests", "scripts"],
                600,
            ),
            (
                "isort_check",
                [
                    sys.executable,
                    "-m",
                    "isort",
                    "--check-only",
                    "src",
                    "tests",
                    "scripts",
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
                    )
                )
            else:
                mensagem_falha = stderr or stdout or "Comando falhou sem mensagem"
                resultados.append(
                    GateResultado(
                        nome=nome,
                        sucesso=False,
                        mensagem=f"FAIL: {mensagem_falha}",
                    )
                )

        aprovado = all(item.sucesso for item in resultados)
        return RelatorioGate(
            nome="quality_gate_release", resultados=resultados, aprovado=aprovado
        )
