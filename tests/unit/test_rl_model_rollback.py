"""
Testes unitários para P2-RL-1: Gerenciador de Rollback Automático de Modelo RL

Suite de 12 testes cobrindo:
- Inicialização, check_degradation, executar_rollback
- Validações de entrada
- Persistência de auditoria
- Histórico de rollbacks
- Geração de relatórios
"""

import json
import shutil
import tempfile
import time
from datetime import datetime
from pathlib import Path
from typing import Dict
import pytest

from src.application.rl_model_rollback_manager import (
    ModelRollbackManager,
    RollbackDecision,
    RollbackReason,
)


# ============================================================================
# FIXTURES
# ============================================================================


@pytest.fixture
def temp_checkpoint_dir() -> Path:
    """Cria diretório temporário para checkpoints."""
    temp_dir = Path(tempfile.mkdtemp())
    checkpoint_dir = temp_dir / "modelo_final"
    checkpoint_dir.mkdir(parents=True, exist_ok=True)

    # Criar checkpoints simulados (arquivos vazios de teste)
    for nome in ["checkpoint_best.pkl", "checkpoint_current.pkl", "checkpoint_backup.pkl"]:
        arquivo = checkpoint_dir / nome
        arquivo.write_bytes(b"x" * 1024)  # Mínimo 1KB

    yield checkpoint_dir

    # Limpar
    shutil.rmtree(temp_dir, ignore_errors=True)


@pytest.fixture
def temp_config_dir() -> Path:
    """Cria diretório temporário para configuração."""
    temp_dir = Path(tempfile.mkdtemp())
    yield temp_dir
    shutil.rmtree(temp_dir, ignore_errors=True)


@pytest.fixture
def config_path(temp_config_dir: Path) -> Path:
    """Cria arquivo de configuração de teste."""
    config_file = temp_config_dir / "rl_rollback_config.json"
    config = {
        "win_rate_threshold_pct": 5.0,
        "sharpe_threshold": -0.5,
        "f1_threshold": 0.05,
        "rolling_window_trades": 50,
        "max_rollback_frequency_hours": 24,
        "notification_slack": False,
        "log_file": "data/logs/rl_rollback.log",
    }
    with open(config_file, "w", encoding="utf-8") as f:
        json.dump(config, f)
    return config_file


@pytest.fixture
def manager(temp_checkpoint_dir: Path, config_path: Path, tmp_path: Path):
    """Cria manager com diretório temporário."""
    # Monkeypatch para log_dir
    manager = ModelRollbackManager(
        checkpoint_dir=str(temp_checkpoint_dir),
        config_path=str(config_path),
    )
    manager.log_dir = tmp_path / "logs"
    manager.log_dir.mkdir(parents=True, exist_ok=True)
    return manager


# ============================================================================
# TESTES - INICIALIZAÇÃO
# ============================================================================


def test_inicializar_manager_com_config_valida(
    temp_checkpoint_dir: Path, config_path: Path
) -> None:
    """Testa inicialização do manager com configuração válida."""
    manager = ModelRollbackManager(
        checkpoint_dir=str(temp_checkpoint_dir),
        config_path=str(config_path),
    )

    assert manager.checkpoint_dir == temp_checkpoint_dir
    assert manager.config["win_rate_threshold_pct"] == 5.0
    assert manager.config["max_rollback_frequency_hours"] == 24
    assert manager.historico_rollbacks == []
    assert manager.ultimo_rollback_timestamp is None


def test_inicializar_manager_diretorio_nao_existe() -> None:
    """Testa que FileNotFoundError é levantado se diretório não existe."""
    with pytest.raises(FileNotFoundError):
        ModelRollbackManager(
            checkpoint_dir="/caminho/inexistente",
            config_path="config.json",
        )


# ============================================================================
# TESTES - CHECK_DEGRADATION
# ============================================================================


def test_check_degradation_sem_degradacao(manager: ModelRollbackManager) -> None:
    """Teste: métricas estáveis → sem rollback."""
    current = {"win_rate": 65.0, "sharpe": 1.2, "f1": 0.68}
    baseline = {"win_rate": 65.0, "sharpe": 1.2, "f1": 0.68}

    decision = manager.check_degradation(current, baseline)

    assert decision.deve_fazer_rollback is False
    assert decision.razao == RollbackReason.OK.value
    assert decision.versao_rollback is None
    assert decision.delta_win_rate == 0.0
    assert decision.recomendacao == "CONTINUAR OPERACAO NORMAL"


def test_check_degradation_com_degradacao_win_rate(
    manager: ModelRollbackManager,
) -> None:
    """Teste: win_rate cai > threshold → rollback."""
    current = {"win_rate": 60.0, "sharpe": 1.1, "f1": 0.65}
    baseline = {"win_rate": 65.0, "sharpe": 1.2, "f1": 0.68}

    decision = manager.check_degradation(current, baseline)

    assert decision.deve_fazer_rollback is True
    assert decision.razao == RollbackReason.DEGRADACAO_WIN_RATE.value
    assert decision.versao_rollback == "checkpoint_best"
    assert decision.delta_win_rate == -5.0
    assert "ROLLBACK RECOMENDADO" in decision.recomendacao


def test_check_degradation_sharpe_negativo(manager: ModelRollbackManager) -> None:
    """Teste: sharpe_ratio negativo → rollback."""
    current = {"win_rate": 65.0, "sharpe": -1.0, "f1": 0.68}
    baseline = {"win_rate": 65.0, "sharpe": 1.2, "f1": 0.68}

    decision = manager.check_degradation(current, baseline)

    assert decision.deve_fazer_rollback is True
    assert decision.razao == RollbackReason.SHARPE_NEGATIVO.value
    assert decision.versao_rollback == "checkpoint_best"


def test_check_degradation_f1_degradacao(manager: ModelRollbackManager) -> None:
    """Teste: F1 score degrada > threshold → rollback."""
    current = {"win_rate": 65.0, "sharpe": 1.2, "f1": 0.60}
    baseline = {"win_rate": 65.0, "sharpe": 1.2, "f1": 0.68}

    decision = manager.check_degradation(current, baseline)

    assert decision.deve_fazer_rollback is True
    assert decision.razao == RollbackReason.F1_DEGRADACAO.value
    assert decision.versao_rollback == "checkpoint_best"


def test_check_degradation_metricas_invalidas(manager: ModelRollbackManager) -> None:
    """Teste: métricas não-dicionário → ValueError."""
    with pytest.raises(ValueError):
        manager.check_degradation(None, {})

    with pytest.raises(ValueError):
        manager.check_degradation({}, "nao_eh_dict")


# ============================================================================
# TESTES - EXECUTAR_ROLLBACK
# ============================================================================


def test_executar_rollback_sucesso(
    temp_checkpoint_dir: Path, manager: ModelRollbackManager
) -> None:
    """Teste: rollback bem-sucedido copia checkpoint corretamente."""
    # Verificar que checkpoint_best existe
    assert (temp_checkpoint_dir / "checkpoint_best.pkl").exists()

    # Executar rollback
    sucesso = manager.executar_rollback("checkpoint_best")

    assert sucesso is True
    assert manager.ultimo_rollback_timestamp is not None
    assert (temp_checkpoint_dir / "checkpoint_current.pkl").exists()


def test_executar_rollback_checkpoint_nao_existe(
    manager: ModelRollbackManager,
) -> None:
    """Teste: rollback para checkpoint inexistente → False."""
    sucesso = manager.executar_rollback("checkpoint_inexistente")

    assert sucesso is False


def test_executar_rollback_checkpoint_invalido_tamanho(
    temp_checkpoint_dir: Path, manager: ModelRollbackManager
) -> None:
    """Teste: rollback para checkpoint < 1KB → False."""
    pequeno = temp_checkpoint_dir / "checkpoint_pequeno.pkl"
    pequeno.write_bytes(b"x" * 100)  # Menor que 1KB

    sucesso = manager.executar_rollback("checkpoint_pequeno")

    assert sucesso is False


def test_executar_rollback_frequencia_maxima(
    manager: ModelRollbackManager,
) -> None:
    """Teste: bloqueia rollback se já fez um recentemente."""
    # Simular um rollback anterior
    manager.ultimo_rollback_timestamp = datetime.utcnow().isoformat()

    # Tentar fazer outro
    sucesso = manager.executar_rollback("checkpoint_best")

    assert sucesso is False


# ============================================================================
# TESTES - HISTÓRICO E RELATÓRIOS
# ============================================================================


def test_obter_historico_rollbacks(manager: ModelRollbackManager) -> None:
    """Teste: histórico retorna decisões em ordem reversa."""
    # Criar algumas decisões com delays para timestamps diferentes
    for i in range(3):
        manager.check_degradation(
            {"win_rate": 60.0 - i, "sharpe": 1.0},
            {"win_rate": 65.0, "sharpe": 1.2},
        )
        time.sleep(0.01)  # 10ms delay para garantir timestamps diferentes

    historico = manager.obter_historico_rollbacks(10)

    assert len(historico) == 3
    # Mais recente deve estar primeiro
    assert historico[0].timestamp >= historico[1].timestamp


def test_gerar_relatorio_json(manager: ModelRollbackManager) -> None:
    """Teste: gera relatório JSON válido."""
    manager.check_degradation(
        {"win_rate": 60.0, "sharpe": 1.0},
        {"win_rate": 65.0, "sharpe": 1.2},
    )

    relatorio_json = manager.gerar_relatorio("json")

    assert isinstance(relatorio_json, str)
    relatorio_dict = json.loads(relatorio_json)

    assert "timestamp" in relatorio_dict
    assert "total_rollbacks" in relatorio_dict
    assert "historico_ultimos_10" in relatorio_dict
    assert isinstance(relatorio_dict["historico_ultimos_10"], list)


def test_gerar_relatorio_markdown(manager: ModelRollbackManager) -> None:
    """Teste: gera relatório Markdown válido."""
    manager.check_degradation(
        {"win_rate": 60.0, "sharpe": 1.0},
        {"win_rate": 65.0, "sharpe": 1.2},
    )

    relatorio_md = manager.gerar_relatorio("markdown")

    assert isinstance(relatorio_md, str)
    assert "# Relatorio" in relatorio_md
    assert "Timestamp" in relatorio_md
    assert "Total de Rollbacks" in relatorio_md


def test_gerar_relatorio_formato_invalido(manager: ModelRollbackManager) -> None:
    """Teste: formato inválido → ValueError."""
    with pytest.raises(ValueError):
        manager.gerar_relatorio("formato_invalido")


# ============================================================================
# TESTES - ROLLBACK DECISION DATACLASS
# ============================================================================


def test_rollback_decision_para_dict() -> None:
    """Teste: RollbackDecision converte para dict corretamente."""
    decision = RollbackDecision(
        deve_fazer_rollback=True,
        razao=RollbackReason.DEGRADACAO_WIN_RATE.value,
        versao_rollback="checkpoint_best",
        metricas_atuais={"win_rate": 60.0},
        metricas_baseline={"win_rate": 65.0},
        timestamp="2026-03-16T10:30:00",
        recomendacao="Rollback recomendado",
        delta_win_rate=-5.0,
        confidence=0.95,
    )

    resultado = decision.para_dict()

    assert isinstance(resultado, dict)
    assert resultado["deve_fazer_rollback"] is True
    assert resultado["razao"] == "degradacao_win_rate"
    assert resultado["delta_win_rate"] == -5.0
    assert resultado["confidence"] == 0.95


# ============================================================================
# TESTE DE INTEGRAÇÃO
# ============================================================================


def test_fluxo_completo_check_e_rollback(
    temp_checkpoint_dir: Path, manager: ModelRollbackManager
) -> None:
    """Teste de integração: fluxo completo de check → decision → rollback."""
    # 1. Verificar degradação
    decision = manager.check_degradation(
        {"win_rate": 60.0, "sharpe": 0.8},
        {"win_rate": 65.0, "sharpe": 1.2},
    )

    assert decision.deve_fazer_rollback is True
    assert decision.versao_rollback == "checkpoint_best"

    # 2. Executar rollback se recomendado
    if decision.deve_fazer_rollback:
        sucesso = manager.executar_rollback(decision.versao_rollback)
        assert sucesso is True

    # 3. Verificar histórico
    historico = manager.obter_historico_rollbacks()
    assert len(historico) == 1
    assert historico[0].deve_fazer_rollback is True


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
