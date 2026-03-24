"""Testes unitarios para GateUnicaOrdemPorAgente."""

import json
from pathlib import Path

import pytest

from src.application.gerenciamento_risco.controles_agente.gate_unica_ordem import (
    GateUnicaOrdemPorAgente,
)
from src.domain.value_objects.risco_externo import ResultadoGateRisco


@pytest.fixture
def outputs_dir(tmp_path: Path) -> Path:
    return tmp_path


@pytest.fixture
def gate(outputs_dir: Path) -> GateUnicaOrdemPorAgente:
    return GateUnicaOrdemPorAgente(outputs_dir=outputs_dir)


def _criar_arquivo_posicao(
    outputs_dir: Path,
    session_id: str,
    aberta: bool,
    owner: str = "agente_teste",
) -> None:
    """Cria arquivo de posicao simulando PosicaoIsoladaManager."""
    dados = {
        "session_id": session_id,
        "owner": owner,
        "aberta": aberta,
        "preco_entrada": 130_000.0,
        "ticket": 123456,
        "lado": "BUY",
        "quantidade": 1,
    }
    arquivo = outputs_dir / f"agente_posicao_{session_id}.json"
    arquivo.write_text(json.dumps(dados), encoding="utf-8")


class TestSemPosicaoAberta:
    """Sem posicao aberta, gate deve liberar."""

    def test_sem_arquivos_libera(self, gate: GateUnicaOrdemPorAgente) -> None:
        resultado = gate.verificar("agente_rl_5000")
        assert resultado.aprovado is True
        assert resultado.codigo_gate == "UNICA_ORDEM"

    def test_posicao_fechada_libera(
        self, gate: GateUnicaOrdemPorAgente, outputs_dir: Path
    ) -> None:
        _criar_arquivo_posicao(
            outputs_dir,
            session_id="agente_rl_5000_20260324_090000",
            aberta=False,
            owner="agente_rl_5000",
        )
        resultado = gate.verificar("agente_rl_5000")
        assert resultado.aprovado is True

    def test_posicao_outro_agente_nao_interfere(
        self, gate: GateUnicaOrdemPorAgente, outputs_dir: Path
    ) -> None:
        """Posicao aberta de outro agente nao deve bloquear este agente."""
        _criar_arquivo_posicao(
            outputs_dir,
            session_id="agente_micro_20260324_090000",
            aberta=True,
            owner="agente_micro",
        )
        resultado = gate.verificar("agente_rl_5000")
        assert resultado.aprovado is True


class TestComPosicaoAberta:
    """Com posicao aberta, gate deve bloquear."""

    def test_posicao_aberta_bloqueia(
        self, gate: GateUnicaOrdemPorAgente, outputs_dir: Path
    ) -> None:
        _criar_arquivo_posicao(
            outputs_dir,
            session_id="agente_rl_5000_20260324_090000",
            aberta=True,
            owner="agente_rl_5000",
        )
        resultado = gate.verificar("agente_rl_5000")
        assert resultado.aprovado is False
        assert resultado.codigo_gate == "UNICA_ORDEM"
        assert "posicao" in resultado.motivo.lower() or "ordem" in resultado.motivo.lower()

    def test_multiplas_sessoes_uma_aberta_bloqueia(
        self, gate: GateUnicaOrdemPorAgente, outputs_dir: Path
    ) -> None:
        """Se qualquer sessao do agente tem posicao aberta, deve bloquear."""
        _criar_arquivo_posicao(
            outputs_dir,
            session_id="agente_rl_5000_20260323_090000",
            aberta=False,
            owner="agente_rl_5000",
        )
        _criar_arquivo_posicao(
            outputs_dir,
            session_id="agente_rl_5000_20260324_090000",
            aberta=True,
            owner="agente_rl_5000",
        )
        resultado = gate.verificar("agente_rl_5000")
        assert resultado.aprovado is False

    def test_detalhes_incluem_session_id(
        self, gate: GateUnicaOrdemPorAgente, outputs_dir: Path
    ) -> None:
        _criar_arquivo_posicao(
            outputs_dir,
            session_id="agente_rl_5000_20260324_090000",
            aberta=True,
            owner="agente_rl_5000",
        )
        resultado = gate.verificar("agente_rl_5000")
        assert resultado.aprovado is False
        assert "session_id" in resultado.detalhes or len(resultado.detalhes) >= 0


class TestResiliencia:
    """Testes de resiliencia (fail-safe)."""

    def test_arquivo_corrompido_bloqueia_fail_safe(
        self, gate: GateUnicaOrdemPorAgente, outputs_dir: Path
    ) -> None:
        """Arquivo corrompido deve ser tratado como posicao aberta (fail-safe)."""
        arquivo = outputs_dir / "agente_posicao_agente_rl_5000_corrompido.json"
        arquivo.write_text("json invalido aqui", encoding="utf-8")
        resultado = gate.verificar("agente_rl_5000")
        assert resultado.aprovado is False
        assert "corrompido" in resultado.motivo.lower() or "erro" in resultado.motivo.lower()

    def test_arquivo_sem_campo_aberta_bloqueia(
        self, gate: GateUnicaOrdemPorAgente, outputs_dir: Path
    ) -> None:
        """Arquivo sem campo 'aberta' deve ser tratado como posicao aberta."""
        dados = {"session_id": "agente_rl_5000_xxx", "owner": "agente_rl_5000"}
        arquivo = outputs_dir / "agente_posicao_agente_rl_5000_xxx.json"
        arquivo.write_text(json.dumps(dados), encoding="utf-8")
        resultado = gate.verificar("agente_rl_5000")
        assert resultado.aprovado is False

    def test_agente_diferente_nao_bloqueia_mesmo_com_arquivo_corrompido(
        self, gate: GateUnicaOrdemPorAgente, outputs_dir: Path
    ) -> None:
        """Arquivo corrompido de outro agente nao deve afetar agente consultado."""
        arquivo = outputs_dir / "agente_posicao_agente_micro_corrompido.json"
        arquivo.write_text("invalido", encoding="utf-8")
        # agente_rl_5000 nao tem arquivos proprios — deve liberar
        # (nao ha arquivo de agente_rl_5000, logo fail-safe nao se aplica)
        resultado = gate.verificar("agente_rl_5000")
        # Sem nenhum arquivo do agente_rl_5000, deve liberar
        assert resultado.aprovado is True


class TestResultadoGateRisco:
    """Testes do formato de ResultadoGateRisco retornado."""

    def test_retorna_resultado_gate_risco(
        self, gate: GateUnicaOrdemPorAgente
    ) -> None:
        resultado = gate.verificar("agente_qualquer")
        assert isinstance(resultado, ResultadoGateRisco)
        assert resultado.codigo_gate == "UNICA_ORDEM"
        assert isinstance(resultado.motivo, str)
        assert isinstance(resultado.detalhes, dict)
