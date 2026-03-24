"""Testes unitarios para GerenciadorCooldown."""

import json
import time as time_module
from datetime import datetime, timedelta
from pathlib import Path

import pytest

from src.application.gerenciamento_risco.controles_agente.gerenciador_cooldown import (
    GerenciadorCooldown,
    ResultadoCooldown,
)
from src.domain.value_objects.risco_externo import ConfiguracaoCooldown


@pytest.fixture
def outputs_dir(tmp_path: Path) -> Path:
    """Diretorio temporario para arquivos de cooldown."""
    return tmp_path


@pytest.fixture
def config_60s() -> ConfiguracaoCooldown:
    return ConfiguracaoCooldown(periodo_espera_segundos=60)


@pytest.fixture
def gerenciador(
    config_60s: ConfiguracaoCooldown, outputs_dir: Path
) -> GerenciadorCooldown:
    return GerenciadorCooldown(configuracao=config_60s, outputs_dir=outputs_dir)


class TestVerificarCooldown:
    """Testes para verificar_cooldown."""

    def test_sem_historico_libera(
        self, gerenciador: GerenciadorCooldown
    ) -> None:
        """Sem fechamento anterior, cooldown deve estar liberado."""
        resultado = gerenciador.verificar_cooldown("agente_1")
        assert resultado.aprovado is True
        assert resultado.segundos_restantes == 0
        assert resultado.agent_id == "agente_1"

    def test_cooldown_ativo_bloqueia(
        self, gerenciador: GerenciadorCooldown
    ) -> None:
        """Apos registrar fechamento, cooldown deve bloquear."""
        gerenciador.registrar_fechamento("agente_1")
        resultado = gerenciador.verificar_cooldown("agente_1")
        assert resultado.aprovado is False
        assert resultado.segundos_restantes > 0
        assert "cooldown" in resultado.motivo.lower()

    def test_cooldown_expirado_libera(self, outputs_dir: Path) -> None:
        """Apos expiracao do cooldown, deve liberar."""
        config = ConfiguracaoCooldown(periodo_espera_segundos=1)
        gerenciador = GerenciadorCooldown(
            configuracao=config, outputs_dir=outputs_dir
        )
        gerenciador.registrar_fechamento("agente_2")
        time_module.sleep(1.1)
        resultado = gerenciador.verificar_cooldown("agente_2")
        assert resultado.aprovado is True
        assert resultado.segundos_restantes == 0

    def test_agente_diferente_nao_interfere(
        self, gerenciador: GerenciadorCooldown
    ) -> None:
        """Cooldown de agente_1 nao deve afetar agente_2."""
        gerenciador.registrar_fechamento("agente_1")
        resultado = gerenciador.verificar_cooldown("agente_2")
        assert resultado.aprovado is True

    def test_segundos_restantes_aproximado(
        self, gerenciador: GerenciadorCooldown
    ) -> None:
        """segundos_restantes deve ser proximo ao periodo configurado."""
        gerenciador.registrar_fechamento("agente_1")
        resultado = gerenciador.verificar_cooldown("agente_1")
        assert 55 <= resultado.segundos_restantes <= 60

    def test_agent_id_correto_no_resultado(
        self, gerenciador: GerenciadorCooldown
    ) -> None:
        """agent_id retornado deve corresponder ao consultado."""
        gerenciador.registrar_fechamento("agente_rl_5000")
        resultado = gerenciador.verificar_cooldown("agente_rl_5000")
        assert resultado.agent_id == "agente_rl_5000"


class TestRegistrarFechamento:
    """Testes para registrar_fechamento."""

    def test_persiste_em_arquivo_json(
        self, gerenciador: GerenciadorCooldown, outputs_dir: Path
    ) -> None:
        """Fechamento deve ser persistido em arquivo JSON."""
        gerenciador.registrar_fechamento("agente_micro")
        arquivo = outputs_dir / "cooldown_agente_micro.json"
        assert arquivo.exists()
        dados = json.loads(arquivo.read_text())
        assert "timestamp_fechamento" in dados
        assert dados["agent_id"] == "agente_micro"

    def test_sobrescreve_fechamento_anterior(
        self, gerenciador: GerenciadorCooldown, outputs_dir: Path
    ) -> None:
        """Novo fechamento deve sobrescrever o timestamp anterior."""
        gerenciador.registrar_fechamento("agente_1")
        ts1 = json.loads(
            (outputs_dir / "cooldown_agente_1.json").read_text()
        )["timestamp_fechamento"]
        time_module.sleep(0.05)
        gerenciador.registrar_fechamento("agente_1")
        ts2 = json.loads(
            (outputs_dir / "cooldown_agente_1.json").read_text()
        )["timestamp_fechamento"]
        assert ts2 > ts1

    def test_multiplos_agentes_arquivos_separados(
        self, gerenciador: GerenciadorCooldown, outputs_dir: Path
    ) -> None:
        """Cada agente deve ter seu proprio arquivo de cooldown."""
        gerenciador.registrar_fechamento("agente_a")
        gerenciador.registrar_fechamento("agente_b")
        assert (outputs_dir / "cooldown_agente_a.json").exists()
        assert (outputs_dir / "cooldown_agente_b.json").exists()


class TestResiliencia:
    """Testes de resiliencia a falhas."""

    def test_arquivo_corrompido_trata_como_sem_historico(
        self, outputs_dir: Path
    ) -> None:
        """Arquivo JSON corrompido deve ser ignorado (sem bloquear)."""
        arquivo = outputs_dir / "cooldown_agente_x.json"
        arquivo.write_text("conteudo invalido nao e json")
        config = ConfiguracaoCooldown(periodo_espera_segundos=60)
        gerenciador = GerenciadorCooldown(
            configuracao=config, outputs_dir=outputs_dir
        )
        resultado = gerenciador.verificar_cooldown("agente_x")
        assert resultado.aprovado is True

    def test_arquivo_com_timestamp_invalido_trata_como_sem_historico(
        self, outputs_dir: Path
    ) -> None:
        """Arquivo com timestamp invalido deve ser ignorado."""
        arquivo = outputs_dir / "cooldown_agente_y.json"
        arquivo.write_text(
            json.dumps({"agent_id": "agente_y", "timestamp_fechamento": "invalido"})
        )
        config = ConfiguracaoCooldown(periodo_espera_segundos=60)
        gerenciador = GerenciadorCooldown(
            configuracao=config, outputs_dir=outputs_dir
        )
        resultado = gerenciador.verificar_cooldown("agente_y")
        assert resultado.aprovado is True


class TestResultadoCooldown:
    """Testes do Value Object ResultadoCooldown."""

    def test_resultado_aprovado(self) -> None:
        resultado = ResultadoCooldown(
            aprovado=True,
            segundos_restantes=0,
            agent_id="agente_1",
            motivo="Cooldown expirado, operacao liberada",
        )
        assert resultado.aprovado is True
        assert resultado.segundos_restantes == 0

    def test_resultado_bloqueado(self) -> None:
        resultado = ResultadoCooldown(
            aprovado=False,
            segundos_restantes=45,
            agent_id="agente_1",
            motivo="Aguardando cooldown: 45s restantes",
        )
        assert resultado.aprovado is False
        assert resultado.segundos_restantes == 45
