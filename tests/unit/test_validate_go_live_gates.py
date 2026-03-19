"""Testes para a orquestracao BL-01/BL-07/BL-08 do gate de go-live."""

from __future__ import annotations

import json
from pathlib import Path

from scripts.validate_go_live_gates import executar_go_live_pipeline
from src.application.release_gates import GateResultado, RelatorioGate


def _relatorio(nome: str, aprovado: bool, evidencias: list[str]) -> RelatorioGate:
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


class _ServicoFalso:
    def __init__(self, relatorio: RelatorioGate) -> None:
        self.relatorio = relatorio

    def executar(self) -> RelatorioGate:
        return self.relatorio


def test_executar_go_live_pipeline_persiste_todos_os_artefatos(tmp_path: Path) -> None:
    """A pipeline deve salvar BL-01, BL-07, BL-08 e a decisao final."""
    staging = _relatorio("staging_readiness", True, ["e-staging"])
    quality = _relatorio("quality_gate_release", True, ["e-quality"])
    uat = _relatorio("uat_operacional", True, ["e-uat"])

    decision = executar_go_live_pipeline(
        base_dir=tmp_path,
        output_dir=tmp_path / "outputs" / "release_gates",
        staging_service=_ServicoFalso(staging),
        quality_service=_ServicoFalso(quality),
        uat_service=_ServicoFalso(uat),
    )

    release_dir = tmp_path / "outputs" / "release_gates"
    assert decision.aprovado is True
    assert decision.decisao == "GO_LIVE"
    assert (release_dir / "bl01_staging_readiness.json").exists()
    assert (release_dir / "bl07_quality_gate.json").exists()
    assert (release_dir / "bl08_uat_operacional.json").exists()
    assert (release_dir / "go_live_decision.json").exists()

    payload = json.loads((release_dir / "go_live_decision.json").read_text(encoding="utf-8"))
    assert payload["decisao"] == "GO_LIVE"
    assert payload["resumo"]["total_gates"] == 3
    assert payload["gates"][2]["nome"] == "uat_operacional"


def test_executar_go_live_pipeline_reprova_quando_bl08_falha(tmp_path: Path) -> None:
    """A decisao final deve virar NO_GO quando o BL-08 reprovar."""
    staging = _relatorio("staging_readiness", True, ["e-staging"])
    quality = _relatorio("quality_gate_release", True, ["e-quality"])
    uat = _relatorio("uat_operacional", False, ["e-uat"])

    decision = executar_go_live_pipeline(
        base_dir=tmp_path,
        output_dir=tmp_path / "outputs" / "release_gates",
        staging_service=_ServicoFalso(staging),
        quality_service=_ServicoFalso(quality),
        uat_service=_ServicoFalso(uat),
    )

    assert decision.aprovado is False
    assert decision.decisao == "NO_GO"
    assert "uat_operacional" in decision.resumo["gates_reprovados"]


def test_executar_go_live_pipeline_persiste_bl01_e_bl07_antes_do_bl08(
    tmp_path: Path,
) -> None:
    """BL-08 deve enxergar BL-01 e BL-07 já persistidos ao ser executado."""

    class _UATVerificaArtefatos:
        def __init__(self, base_dir: Path) -> None:
            self.base_dir = base_dir

        def executar(self) -> RelatorioGate:
            release_dir = self.base_dir / "outputs" / "release_gates"
            arquivos = [
                release_dir / "bl01_staging_readiness.json",
                release_dir / "bl07_quality_gate.json",
            ]
            faltantes = [str(path) for path in arquivos if not path.exists()]
            return RelatorioGate(
                nome="uat_operacional",
                resultados=[
                    GateResultado(
                        nome="release_artifacts",
                        sucesso=not faltantes,
                        mensagem="ok" if not faltantes else f"faltando: {', '.join(faltantes)}",
                    )
                ],
                aprovado=not faltantes,
                metadados={"evidencias": [str(path) for path in arquivos]},
            )

    decision = executar_go_live_pipeline(
        base_dir=tmp_path,
        output_dir=tmp_path / "outputs" / "release_gates",
        staging_service=_ServicoFalso(_relatorio("staging_readiness", True, ["e-staging"])),
        quality_service=_ServicoFalso(_relatorio("quality_gate_release", True, ["e-quality"])),
        uat_service=_UATVerificaArtefatos(tmp_path),
    )

    assert decision.aprovado is True
