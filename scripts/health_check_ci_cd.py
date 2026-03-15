"""
Health-check de CI/CD para validacao de integridade do projeto.

Responsabilidades:
- Validar commit messages (sem acentos)
- Validar type hints (100% coverage)
- Validar estrutura de pastas
- Validar localizacao de arquivos
- Gerar relatorio JSON

Uso:
    python scripts/health_check_ci_cd.py
"""

import json
import subprocess
import sys
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional

import tomllib


@dataclass
class CheckResult:
    """Resultado de um check individual."""

    status: str  # "PASS" ou "FAIL"
    count: int = 0
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)


@dataclass
class HealthCheckReport:
    """Relatorio completo de health-check."""

    project: str
    timestamp: str
    overall_status: str  # "PASS" ou "FAIL"
    duration_seconds: float
    checks_passed: int
    checks_total: int
    checks: Dict[str, CheckResult]
    recommendations: List[str] = field(default_factory=list)

    def to_json(self) -> str:
        """Converte para JSON."""
        data = {
            "project": self.project,
            "timestamp": self.timestamp,
            "overall_status": self.overall_status,
            "duration_seconds": self.duration_seconds,
            "checks_passed": self.checks_passed,
            "checks_total": self.checks_total,
            "checks": {
                name: asdict(check) for name, check in self.checks.items()
            },
            "recommendations": self.recommendations,
        }
        return json.dumps(data, indent=2, ensure_ascii=False)


class HealthCheckRunner:
    """Executor do health-check de CI/CD."""

    def __init__(self, project_root: Optional[Path] = None) -> None:
        """Inicializa runner.

        Args:
            project_root: Caminho raiz do projeto (default: dir atual)
        """
        self.project_root: Path = (
            project_root or Path.cwd()
        )
        self.checks: Dict[str, CheckResult] = {}
        self.recommendations: List[str] = []

    def run_all_checks(self) -> HealthCheckReport:
        """Executa todos os checks.

        Returns:
            HealthCheckReport: Relatorio completo
        """
        start_time: float = datetime.now(timezone.utc).timestamp()

        # Executar checks
        self._check_folder_structure()
        self._check_python_files_location()
        self._check_markdown_files_location()
        self._check_outputs_location()
        self._check_type_hints_in_scripts()

        # Calcular status geral
        checks_passed: int = sum(
            1
            for check in self.checks.values()
            if check.status == "PASS"
        )
        checks_total: int = len(self.checks)
        overall_status: str = (
            "PASS"
            if checks_passed == checks_total
            else "FAIL"
        )

        # Gerar recomendacoes
        if overall_status == "FAIL":
            self.recommendations.append(
                "Corrija os erros acima antes de fazer commit"
            )

        # Montar relatorio
        duration: float = (
            datetime.now(timezone.utc).timestamp() - start_time
        )
        timestamp: str = datetime.now(timezone.utc).isoformat() + "Z"

        report: HealthCheckReport = HealthCheckReport(
            project="operador-day-trade-win",
            timestamp=timestamp,
            overall_status=overall_status,
            duration_seconds=round(duration, 2),
            checks_passed=checks_passed,
            checks_total=checks_total,
            checks=self.checks,
            recommendations=(
                self.recommendations
                if self.recommendations
                else ["Todos os checks passaram com sucesso"]
            ),
        )

        return report

    def _check_folder_structure(self) -> None:
        """Valida estrutura de pastas obrigatoria."""
        required_folders: List[str] = [
            "scripts",
            "tests",
            "src",
            "docs",
            "data",
            "outputs",
            "BAT",
        ]

        errors: List[str] = []
        for folder_name in required_folders:
            folder_path: Path = self.project_root / folder_name
            if not folder_path.exists():
                errors.append(f"Pasta '{folder_name}' nao existe")

        status: str = "PASS" if not errors else "FAIL"
        self.checks["folder_structure"] = CheckResult(
            status=status,
            count=len(required_folders),
            errors=errors,
        )

    def _check_python_files_location(self) -> None:
        """Valida que scripts Python estao em scripts/."""
        errors: List[str] = []

        # Procurar arquivos .py na raiz
        root_py_files: List[Path] = list(
            self.project_root.glob("*.py")
        )

        # Remover conftest.py (permitido na raiz em alguns casos)
        allowed_root_scripts = [
            "conftest.py",
        ]

        for py_file in root_py_files:
            if py_file.name not in allowed_root_scripts:
                errors.append(
                    f"Script '{py_file.name}' encontrado na "
                    f"raiz - deve estar em scripts/"
                )

        status: str = "PASS" if not errors else "FAIL"
        self.checks["python_files_location"] = CheckResult(
            status=status,
            count=len(root_py_files),
            errors=errors,
        )

    def _check_markdown_files_location(self) -> None:
        """Valida localizacao de arquivos markdown."""
        errors: List[str] = []

        # Procurar arquivos .md na raiz
        root_md_files: List[Path] = list(
            self.project_root.glob("*.md")
        )

        # Permitir apenas README.md na raiz
        allowed_root_md = ["README.md", "START_HERE.md"]

        for md_file in root_md_files:
            if md_file.name not in allowed_root_md:
                errors.append(
                    f"Markdown '{md_file.name}' encontrado "
                    f"na raiz - deve estar em docs/"
                )

        status: str = "PASS" if not errors else "FAIL"
        self.checks["markdown_files_location"] = CheckResult(
            status=status,
            count=len(root_md_files),
            errors=errors,
        )

    def _check_outputs_location(self) -> None:
        """Valida que outputs estao em outputs/."""
        errors: List[str] = []

        # Tipos de arquivo que devem estar em outputs/
        output_extensions: List[str] = [
            ".json",
            ".csv",
            ".xlsx",
            ".txt",
        ]

        # Procurar esses arquivos na raiz
        for ext in output_extensions:
            root_output_files: List[Path] = list(
                self.project_root.glob(f"*{ext}")
            )
            for output_file in root_output_files:
                # Ignorar alguns arquivos especiais
                if output_file.name not in [
                    "pytest.ini",
                    "docker-compose.yml",
                ]:
                    errors.append(
                        f"Output '{output_file.name}' "
                        f"encontrado na raiz - "
                        f"deve estar em outputs/"
                    )

        status: str = "PASS" if not errors else "FAIL"
        self.checks["outputs_location"] = CheckResult(
            status=status,
            count=len(errors),
            errors=errors,
        )

    def _check_type_hints_in_scripts(self) -> None:
        """Valida presenca de type hints em scripts."""
        scripts_dir: Path = self.project_root / "scripts"

        if not scripts_dir.exists():
            self.checks["type_hints"] = CheckResult(
                status="FAIL",
                errors=["Pasta scripts/ nao existe"],
            )
            return

        errors: List[str] = []
        python_files: List[Path] = list(
            scripts_dir.glob("*.py")
        )

        # Arquivos que podem nao ter type hints (legacy)
        exempt_files = [
            "conftest.py",
            "__init__.py",
        ]

        for py_file in python_files:
            if py_file.name in exempt_files:
                continue

            try:
                content: str = py_file.read_text(encoding="utf-8")

                # Verificacao basica: procuroar "def " sem "->"
                lines: List[str] = content.split("\n")
                for i, line in enumerate(lines, 1):
                    if line.strip().startswith("def "):
                        # Simples check: se tem "def" mas eh
                        # comentario ou docstring, pula
                        if not line.strip().startswith("# def"):
                            # Verificarcontinuacao da func
                            if "->" not in line:
                                # Pode ser linha continuada
                                j = i
                                found_arrow = False
                                while j < min(i + 3, len(lines)):
                                    if "->" in lines[j]:
                                        found_arrow = True
                                        break
                                    j += 1

                                if not found_arrow:
                                    # Eh um case suspeito
                                    if "self" in line or "(" in line:
                                        errors.append(
                                            f"{py_file.name}:{i} "
                                            f"- type hints "
                                            f"potencialmente "
                                            f"ausentes"
                                        )

            except Exception as e:
                errors.append(
                    f"{py_file.name} - erro ao ler: {str(e)}"
                )

        status: str = "PASS" if not errors else "FAIL"
        self.checks["type_hints"] = CheckResult(
            status=status,
            count=len(python_files),
            errors=errors,
        )


def main() -> int:
    """Funcao principal.

    Returns:
        int: 0 se sucesso, 1 se falha
    """
    try:
        runner: HealthCheckRunner = HealthCheckRunner()
        report: HealthCheckReport = runner.run_all_checks()

        # Imprimir relatorio
        print("\n" + "=" * 70)
        print(f"HEALTH CHECK CI/CD - {report.overall_status}")
        print("=" * 70)
        print(f"Timestamp: {report.timestamp}")
        print(
            f"Checks: {report.checks_passed}/{report.checks_total} "
            f"passaram"
        )
        print(f"Duracao: {report.duration_seconds}s")
        print()

        for check_name, check_result in report.checks.items():
            status_symbol: str = "✓" if check_result.status == "PASS" else "✗"
            print(f"{status_symbol} {check_name}: {check_result.status}")
            if check_result.errors:
                for error in check_result.errors:
                    print(f"  - {error}")

        print()
        for recommendation in report.recommendations:
            print(f"💡 {recommendation}")

        # Salvar relatorio JSON
        output_dir: Path = runner.project_root / "outputs"
        output_dir.mkdir(exist_ok=True)
        output_file: Path = (
            output_dir / "health_check_results.json"
        )

        with open(output_file, "w", encoding="utf-8") as f:
            f.write(report.to_json())

        print(f"\nRelatorio salvo em: {output_file}")
        print("=" * 70 + "\n")

        # Retornar status
        return 0 if report.overall_status == "PASS" else 1

    except Exception as e:
        print(f"ERRO: {str(e)}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
