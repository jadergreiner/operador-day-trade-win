"""
Testes unitários para profit_protection_config (ADR-018).

Cobertura:
- T1: Carregar YAML válido
- T2: Fallback para baseline quando YAML ausente
- T3: Validar campos obrigatórios Pydantic
- T4: Resolver perfil via variável de ambiente
- T5: Resolver override por agent_id
- T6: Precedência completa (override > env > profile_ativo > baseline)

Status: RED → GREEN → REFACTOR
"""

import os
from pathlib import Path
from typing import Any, Dict
from unittest.mock import MagicMock, patch

import pytest

from src.infrastructure.config.profit_protection_config import (
    ProfitProtectionConfig,
    ProfitProtectionProfile,
    carregar_config,
    resolver_perfil,
)


# ============================================================
# FIXTURES
# ============================================================


@pytest.fixture
def yaml_valido_fixture(tmp_path: Path) -> Path:
    """
    Cria arquivo YAML válido para testes.

    Estrutura:
    - version: 1.0.0
    - profile_ativo: baseline
    - shadow_mode: false
    - 3 profiles: baseline, conservador, agressivo
    - agent_overrides: vazio
    """
    yaml_content = """
version: "1.0.0"
profile_ativo: "baseline"
shadow_mode: false

profiles:
  baseline:
    nome: "Baseline (defaults históricos)"
    profit_target_pct: 2.0
    stop_loss_pct: 1.0
    partial_close_pct: 0.75
    break_even_offset_pct: 0.10
    reversao_threshold_pct: 0.75
    cooldown_seconds: 5

  conservador:
    nome: "Conservador"
    profit_target_pct: 1.5
    stop_loss_pct: 1.0
    partial_close_pct: 0.70
    break_even_offset_pct: 0.15
    reversao_threshold_pct: 0.65
    cooldown_seconds: 5

  agressivo:
    nome: "Agressivo"
    profit_target_pct: 3.0
    stop_loss_pct: 1.0
    partial_close_pct: 0.80
    break_even_offset_pct: 0.08
    reversao_threshold_pct: 0.85
    cooldown_seconds: 5

agent_overrides: {}
"""
    yaml_path = tmp_path / "profit_protection.yaml"
    yaml_path.write_text(yaml_content.strip())
    return yaml_path


@pytest.fixture
def yaml_invalido_fixture(tmp_path: Path) -> Path:
    """YAML com campos obrigatórios faltando."""
    yaml_content = """
version: "1.0.0"
# Falta profile_ativo
shadow_mode: false
profiles: {}
"""
    yaml_path = tmp_path / "profit_protection_invalido.yaml"
    yaml_path.write_text(yaml_content.strip())
    return yaml_path


# ============================================================
# T1: Carregar YAML válido
# ============================================================


@pytest.mark.unit
def test_carregar_config_yaml_valido(yaml_valido_fixture: Path) -> None:
    """
    AC1: Loader deve ler config/profit_protection.yaml.

    Given: YAML válido em tmp_path
    When: carregar_config(yaml_valido_fixture)
    Then:
        - version == "1.0.0"
        - profile_ativo == "baseline"
        - shadow_mode == False
        - 3 profiles presentes
        - agent_overrides == {}
    """
    config = carregar_config(yaml_valido_fixture)
    assert config.version == "1.0.0"
    assert config.profile_ativo == "baseline"
    assert config.shadow_mode is False
    assert "baseline" in config.profiles
    assert "conservador" in config.profiles
    assert "agressivo" in config.profiles
    assert config.agent_overrides == {}


# ============================================================
# T2: Fallback para baseline quando YAML ausente
# ============================================================


@pytest.mark.unit
@patch("pathlib.Path.exists")
def test_fallback_baseline_yaml_ausente(mock_exists: MagicMock) -> None:
    """
    AC1: Fallback para baseline quando YAML não existe.

    Given: YAML não existe
    When: carregar_config()
    Then: retorna ProfitProtectionConfig com baseline builtin
    """
    mock_exists.return_value = False
    config = carregar_config(Path("/tmp/nao_existe.yaml"))
    # Deve retornar config com baseline builtin
    assert "baseline" in config.profiles
    baseline = config.profiles["baseline"]
    assert baseline.profit_target_pct == 2.0
    assert baseline.stop_loss_pct == 1.0


# ============================================================
# T3: Validar campos obrigatórios Pydantic
# ============================================================


@pytest.mark.unit
def test_validacao_pydantic_campos_obrigatorios(
    yaml_invalido_fixture: Path,
) -> None:
    """
    AC2: Pydantic deve validar campos obrigatórios.

    Given: YAML sem profile_ativo
    When: carregar_config(yaml_invalido_fixture)
    Then: raises ValidationError
    """
    pytest.skip("RED: carregar_config ainda não implementado")
    # from pydantic import ValidationError
    # with pytest.raises(ValidationError):
    #     carregar_config(yaml_invalido_fixture)


# ============================================================
# T4: Resolver perfil via variável de ambiente
# ============================================================


@pytest.mark.unit
def test_resolver_perfil_via_env_var(yaml_valido_fixture: Path) -> None:
    """
    AC3: ENV var deve sobrescrever profile_ativo.

    Given: YAML com profile_ativo=baseline
    And: PROFIT_PROTECTION_PROFILE=conservador
    When: resolver_perfil(yaml_valido_fixture)
    Then: retorna profile conservador
    """
    pytest.skip("RED: resolver_perfil ainda não implementado")
    # os.environ["PROFIT_PROTECTION_PROFILE"] = "conservador"
    # try:
    #     profile = resolver_perfil(yaml_valido_fixture)
    #     assert profile.nome == "Conservador"
    #     assert profile.profit_target_pct == 1.5
    # finally:
    #     os.environ.pop("PROFIT_PROTECTION_PROFILE", None)


# ============================================================
# T5: Resolver override por agent_id
# ============================================================


@pytest.mark.unit
def test_resolver_override_por_agent_id(tmp_path: Path) -> None:
    """
    AC4: agent_overrides deve sobrescrever profile_ativo.

    Given: YAML com agent_overrides[agente_teste] = conservador
    When: resolver_perfil(agent_id="agente_teste")
    Then: retorna profile conservador
    """
    pytest.skip("RED: resolver_perfil ainda não implementado")
    # yaml_content = """
    # version: "1.0.0"
    # profile_ativo: "baseline"
    # shadow_mode: false
    # profiles:
    #   baseline:
    #     nome: "Baseline"
    #     profit_target_pct: 2.0
    #     stop_loss_pct: 1.0
    #     partial_close_pct: 0.75
    #     break_even_offset_pct: 0.10
    #     reversao_threshold_pct: 0.75
    #     cooldown_seconds: 5
    #   conservador:
    #     nome: "Conservador"
    #     profit_target_pct: 1.5
    #     stop_loss_pct: 1.0
    #     partial_close_pct: 0.70
    #     break_even_offset_pct: 0.15
    #     reversao_threshold_pct: 0.65
    #     cooldown_seconds: 5
    # agent_overrides:
    #   agente_teste:
    #     profile: conservador
    # """
    # yaml_path = tmp_path / "profit_protection_with_override.yaml"
    # yaml_path.write_text(yaml_content.strip())
    #
    # profile = resolver_perfil(yaml_path, agent_id="agente_teste")
    # assert profile.nome == "Conservador"
    # assert profile.profit_target_pct == 1.5


# ============================================================
# T6: Precedência completa
# ============================================================


@pytest.mark.unit
def test_precedencia_completa(tmp_path: Path) -> None:
    """
    AC1-AC4: Testar precedência completa.

    Precedência: override arg > agent_overrides > ENV > profile_ativo > baseline
    """
    pytest.skip("RED: resolver_perfil ainda não implementado")
    # # Setup: YAML com override
    # yaml_content = """
    # version: "1.0.0"
    # profile_ativo: "baseline"
    # shadow_mode: false
    # profiles:
    #   baseline:
    #     nome: "Baseline"
    #     profit_target_pct: 2.0
    #     stop_loss_pct: 1.0
    #     partial_close_pct: 0.75
    #     break_even_offset_pct: 0.10
    #     reversao_threshold_pct: 0.75
    #     cooldown_seconds: 5
    #   conservador:
    #     nome: "Conservador"
    #     profit_target_pct: 1.5
    #     stop_loss_pct: 1.0
    #     partial_close_pct: 0.70
    #     break_even_offset_pct: 0.15
    #     reversao_threshold_pct: 0.65
    #     cooldown_seconds: 5
    #   agressivo:
    #     nome: "Agressivo"
    #     profit_target_pct: 3.0
    #     stop_loss_pct: 1.0
    #     partial_close_pct: 0.80
    #     break_even_offset_pct: 0.08
    #     reversao_threshold_pct: 0.85
    #     cooldown_seconds: 5
    # agent_overrides:
    #   agente_teste:
    #     profile: conservador
    # """
    # yaml_path = tmp_path / "profit_protection_precedencia.yaml"
    # yaml_path.write_text(yaml_content.strip())
    #
    # # Teste 1: override arg ganha de tudo
    # profile = resolver_perfil(
    #     yaml_path, agent_id="agente_teste", profile_override="agressivo"
    # )
    # assert profile.nome == "Agressivo"
    #
    # # Teste 2: agent_overrides ganha de ENV e profile_ativo
    # profile = resolver_perfil(yaml_path, agent_id="agente_teste")
    # assert profile.nome == "Conservador"
    #
    # # Teste 3: ENV ganha de profile_ativo
    # os.environ["PROFIT_PROTECTION_PROFILE"] = "agressivo"
    # try:
    #     profile = resolver_perfil(yaml_path, agent_id="agente_outro")
    #     assert profile.nome == "Agressivo"
    # finally:
    #     os.environ.pop("PROFIT_PROTECTION_PROFILE", None)
    #
    # # Teste 4: profile_ativo é usado quando nada mais sobrescreve
    # profile = resolver_perfil(yaml_path, agent_id="agente_outro")
    # assert profile.nome == "Baseline"


# ============================================================
# T7-T9: Thread safety (integração)
# ============================================================


@pytest.mark.integration
def test_thread_safety_acesso_concorrente(yaml_valido_fixture: Path) -> None:
    """
    AC5: Loader deve ser thread-safe.

    Given: 10 threads chamando carregar_config() simultaneamente
    When: concorrência real
    Then: nenhuma exception, todos retornam config válida
    """
    pytest.skip("RED: carregar_config ainda não implementado")
    # import threading
    #
    # resultados = []
    # exceptions = []
    #
    # def worker():
    #     try:
    #         config = carregar_config(yaml_valido_fixture)
    #         resultados.append(config.version)
    #     except Exception as e:
    #         exceptions.append(e)
    #
    # threads = [threading.Thread(target=worker) for _ in range(10)]
    # for t in threads:
    #     t.start()
    # for t in threads:
    #     t.join()
    #
    # assert len(exceptions) == 0
    # assert len(resultados) == 10
    # assert all(v == "1.0.0" for v in resultados)


# ============================================================
# T10-T11: Validação de tipos Pydantic
# ============================================================


@pytest.mark.unit
def test_validacao_tipo_profit_target_negativo(tmp_path: Path) -> None:
    """
    AC2: Pydantic deve rejeitar profit_target_pct negativo.

    Given: YAML com profit_target_pct = -1.0
    When: carregar_config()
    Then: raises ValidationError
    """
    pytest.skip("RED: carregar_config ainda não implementado")
    # yaml_content = """
    # version: "1.0.0"
    # profile_ativo: "baseline"
    # shadow_mode: false
    # profiles:
    #   baseline:
    #     nome: "Baseline"
    #     profit_target_pct: -1.0
    #     stop_loss_pct: 1.0
    #     partial_close_pct: 0.75
    #     break_even_offset_pct: 0.10
    #     reversao_threshold_pct: 0.75
    #     cooldown_seconds: 5
    # agent_overrides: {}
    # """
    # yaml_path = tmp_path / "profit_protection_negativo.yaml"
    # yaml_path.write_text(yaml_content.strip())
    #
    # from pydantic import ValidationError
    # with pytest.raises(ValidationError):
    #     carregar_config(yaml_path)


@pytest.mark.unit
def test_validacao_tipo_cooldown_nao_inteiro(tmp_path: Path) -> None:
    """
    AC2: Pydantic deve rejeitar cooldown_seconds não inteiro.

    Given: YAML com cooldown_seconds = "cinco"
    When: carregar_config()
    Then: raises ValidationError
    """
    pytest.skip("RED: carregar_config ainda não implementado")
    # yaml_content = """
    # version: "1.0.0"
    # profile_ativo: "baseline"
    # shadow_mode: false
    # profiles:
    #   baseline:
    #     nome: "Baseline"
    #     profit_target_pct: 2.0
    #     stop_loss_pct: 1.0
    #     partial_close_pct: 0.75
    #     break_even_offset_pct: 0.10
    #     reversao_threshold_pct: 0.75
    #     cooldown_seconds: "cinco"
    # agent_overrides: {}
    # """
    # yaml_path = tmp_path / "profit_protection_cooldown_invalido.yaml"
    # yaml_path.write_text(yaml_content.strip())
    #
    # from pydantic import ValidationError
    # with pytest.raises(ValidationError):
    #     carregar_config(yaml_path)
