"""
Testes para o ConfigLoader do Profit Protection.
"""
import os
import time
from pathlib import Path
from unittest.mock import patch

import pytest
import yaml

from src.infrastructure.config.config_loader import ConfigLoader
from src.infrastructure.config.profit_protection_config import (
    ProfitProtectionProfile,
)

# Fixture para criar um arquivo YAML de teste
@pytest.fixture
def yaml_config_file(tmp_path: Path) -> Path:
    config_content = {
        "version": "1.0.0",
        "profile_ativo": "baseline",
        "shadow_mode": False,
        "profiles": {
            "baseline": {
                "nome": "Baseline Test",
                "profit_target_pct": 2.0,
                "stop_loss_pct": 1.0,
                "partial_close_pct": 0.75,
                "break_even_offset_pct": 0.10,
                "reversao_threshold_pct": 0.75,
                "cooldown_seconds": 5,
            },
            "conservador": {
                "nome": "Conservador Test",
                "profit_target_pct": 1.5,
                "stop_loss_pct": 1.0,
                "partial_close_pct": 0.70,
                "break_even_offset_pct": 0.15,
                "reversao_threshold_pct": 0.65,
                "cooldown_seconds": 5,
            },
        },
        "agent_overrides": {
            "agente_teste_override": {"profile": "conservador"}
        },
    }
    config_file = tmp_path / "profit_protection_test.yaml"
    with open(config_file, "w") as f:
        yaml.dump(config_content, f)
    return config_file


def test_singleton_retorna_mesma_instancia():
    """Garante que ConfigLoader.get_instance() retorna a mesma instância."""
    # Limpa o singleton para garantir um teste limpo
    ConfigLoader._instance = None

    loader1 = ConfigLoader.get_instance()
    loader2 = ConfigLoader.get_instance()
    assert loader1 is loader2
    assert id(loader1) == id(loader2)

def test_carregar_profile_do_yaml(yaml_config_file: Path):
    """Testa o carregamento de um perfil específico do arquivo YAML."""
    ConfigLoader._instance = None
    loader = ConfigLoader.get_instance(yaml_path=yaml_config_file)

    profile = loader.get_profile("conservador")

    assert isinstance(profile, ProfitProtectionProfile)
    assert profile.nome == "Conservador Test"
    assert profile.profit_target_pct == 1.5

def test_fallback_para_builtin_se_yaml_ausente():
    """Testa o fallback para defaults internos se o YAML não existe."""
    ConfigLoader._instance = None
    # Passar um caminho que não existe
    loader = ConfigLoader.get_instance(yaml_path=Path("caminho/inexistente.yaml"))

    profile = loader.get_profile("qualquer_coisa")

    assert profile.nome == "Baseline (builtin)"
    assert profile.profit_target_pct == 2.0

def test_erro_em_yaml_invalido(tmp_path: Path):
    """Testa o fallback para defaults se o YAML está mal formatado."""
    config_file = tmp_path / "invalid.yaml"
    config_file.write_text("key: value: {") # YAML inválido

    ConfigLoader._instance = None
    loader = ConfigLoader.get_instance(yaml_path=config_file)

    profile = loader.get_profile()

    assert profile.nome == "Baseline (builtin)"

def test_override_por_agente(yaml_config_file: Path):
    """Testa se o override por agente funciona corretamente."""
    ConfigLoader._instance = None
    loader = ConfigLoader.get_instance(yaml_path=yaml_config_file)

    # Sem override, deve pegar o 'baseline'
    profile_base = loader.get_profile(profile_name="baseline")
    assert profile_base.nome == "Baseline Test"

    # Com override, deve pegar o 'conservador'
    profile_override = loader.get_profile(profile_name="baseline", agent_id="agente_teste_override")
    assert profile_override.nome == "Conservador Test"

def test_cache_funciona(yaml_config_file: Path):
    """Testa se o cache LRU está funcionando."""
    ConfigLoader._instance = None
    loader = ConfigLoader.get_instance(yaml_path=yaml_config_file)

    with patch.object(loader, '_carregar_e_validar_yaml', wraps=loader._carregar_e_validar_yaml) as mock_load:
        # Primeira chamada, deve carregar do arquivo
        loader.get_profile("baseline")
        mock_load.assert_called_once()

        # Segunda chamada, deve vir do cache
        loader.get_profile("baseline")
        mock_load.assert_called_once() # Ainda uma chamada

        # Chamada com outro perfil, deve carregar de novo (do dict em memória, mas a função é chamada)
        loader.get_profile("conservador")
        # A lógica interna do get_profile chama _carregar_e_validar_yaml uma vez por instância
        # e depois resolve os perfis. O teste aqui valida que o arquivo não é lido múltiplas vezes.
        assert mock_load.call_count == 1

@pytest.mark.slow
def test_reload_automatico_apos_reset(tmp_path):
    """
    Testa se o loader recarrega a configuração após uma mudança no arquivo,
    simulando um reset do singleton para garantir um estado limpo.
    """
    yaml_file = tmp_path / "test_config.yaml"
    config_content_v1 = {
        "version": "1.0",
        "profile_ativo": "baseline",
        "shadow_mode": True,
        "profiles": {
            "baseline": {
                "nome": "Baseline Test",
                "profit_target_pct": 2.0,
                "stop_loss_pct": 1.0,
            }
        },
        "agent_overrides": {},
    }
    yaml_file.write_text(yaml.dump(config_content_v1), encoding="utf-8")

    # Força a criação de uma nova instância para o teste
    ConfigLoader._instance = None
    loader1 = ConfigLoader.get_instance(yaml_path=yaml_file)
    profile1 = loader1.get_profile("baseline")
    assert profile1.profit_target_pct == 2.0

    # Garante um tempo suficiente para a resolução do mtime do sistema de arquivos
    time.sleep(1.1)

    # Modifica o arquivo de configuração
    config_content_v2 = config_content_v1.copy()
    config_content_v2["profiles"]["baseline"]["profit_target_pct"] = 5.0
    yaml_file.write_text(yaml.dump(config_content_v2), encoding="utf-8")

    # Simula um "reset" do singleton, como se o processo reiniciasse
    ConfigLoader._instance = None
    ConfigLoader.get_profile.cache_clear() # Limpeza explícita do cache de classe

    loader2 = ConfigLoader.get_instance(yaml_path=yaml_file)
    profile2 = loader2.get_profile("baseline")

    # Verifica se a nova configuração foi carregada
    assert profile2.profit_target_pct == 5.0
