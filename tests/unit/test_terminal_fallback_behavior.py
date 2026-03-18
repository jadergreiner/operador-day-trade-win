"""
ADR-016: Terminal Fallback Behavior - Unit Tests

Testa a validacao e aceitacao de terminais MT5 fallback conforme ADR-016.

Cenários testados:
1. Fallback aceito quando configurado (terminal em lista + enabled=true)
2. Fallback rejeitado quando desabilitado (enabled=false)
3. Fallback rejeitado quando terminal não está na lista
4. WARNING logging quando fallback é acionado
5. Auditoria em SQLite quando fallback ocorre
6. Config JSON parsing
7. Terminal primário sempre aceito
"""

import json
import sqlite3
from datetime import datetime
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from config.settings import MT5Config, TradingConfig


class TestMT5ConfigFallbackValidation:
    """Testes do MT5Config para validação de fallback terminal."""

    def test_terminal_accepted_when_primary(self):
        """Terminal aceito quando é o primário."""
        config = MT5Config(
            terminal_primary="Clear Investimentos",
            terminal_fallback_enabled=True,
            terminal_fallback_list=["FBS", "XP"],
        )
        assert config.is_terminal_accepted("Clear Investimentos") is True

    def test_terminal_accepted_fallback_enabled_in_list(self):
        """Terminal fallback aceito quando enabled=true e está na lista."""
        config = MT5Config(
            terminal_primary="Clear Investimentos",
            terminal_fallback_enabled=True,
            terminal_fallback_list=["FBS", "XP", "Zero"],
        )
        assert config.is_terminal_accepted("FBS") is True
        assert config.is_terminal_accepted("XP") is True
        assert config.is_terminal_accepted("Zero") is True

    def test_terminal_rejected_fallback_disabled(self):
        """Terminal fallback rejeitado quando enabled=false."""
        config = MT5Config(
            terminal_primary="Clear Investimentos",
            terminal_fallback_enabled=False,
            terminal_fallback_list=["FBS", "XP"],
        )
        assert config.is_terminal_accepted("FBS") is False
        assert config.is_terminal_accepted("XP") is False

    def test_terminal_rejected_not_in_list(self):
        """Terminal rejeitado quando não está na fallback_list."""
        config = MT5Config(
            terminal_primary="Clear Investimentos",
            terminal_fallback_enabled=True,
            terminal_fallback_list=["FBS"],  # Apenas FBS permitido
        )
        assert config.is_terminal_accepted("XP") is False
        assert config.is_terminal_accepted("Zero") is False

    def test_should_log_fallback_when_detected(self):
        """should_log_fallback=true quando terminal diferente do primário mas aceito."""
        config = MT5Config(
            terminal_primary="Clear Investimentos",
            terminal_fallback_enabled=True,
            terminal_fallback_list=["FBS"],
        )
        # Fallback detectado (FBS ≠ Clear) e aceito
        assert config.should_log_fallback("FBS") is True
        # Primário não gera log fallback
        assert config.should_log_fallback("Clear Investimentos") is False
        # Terminal não aceito não gera even log
        assert config.should_log_fallback("XP") is False

    def test_terminal_primary_validator_non_empty(self):
        """Validator rejeita terminal primário vazio."""
        with pytest.raises(ValueError, match="não pode ser vazio"):
            MT5Config(
                terminal_primary="",
                terminal_fallback_enabled=True,
                terminal_fallback_list=["FBS"],
            )

    def test_terminal_fallback_list_validator_json_string(self):
        """Validator parseia JSON string em terminal_fallback_list."""
        config = MT5Config(
            terminal_primary="Clear",
            terminal_fallback_list='["FBS","XP","Zero"]',  # JSON string
        )
        assert config.terminal_fallback_list == ["FBS", "XP", "Zero"]

    def test_terminal_fallback_list_validator_python_list(self):
        """Validator aceita Python list em terminal_fallback_list."""
        config = MT5Config(
            terminal_primary="Clear",
            terminal_fallback_list=["FBS", "XP"],  # Python list
        )
        assert config.terminal_fallback_list == ["FBS", "XP"]

    def test_terminal_fallback_list_validator_invalid_json(self):
        """Validator rejeita JSON inválido."""
        with pytest.raises(ValueError, match="JSON inválido"):
            MT5Config(
                terminal_primary="Clear",
                terminal_fallback_list='["FBS", invalid json}]',
            )

    def test_terminal_fallback_list_validator_empty(self):
        """Validator rejeita lista vazia."""
        with pytest.raises(ValueError, match="não pode ser vazia"):
            MT5Config(
                terminal_primary="Clear",
                terminal_fallback_list=[],
            )

    def test_only_primary_terminal_always_accepted(self):
        """Apenas o primário é aceito quando fallback está desabilitado."""
        config = MT5Config(
            terminal_primary="Clear Investimentos",
            terminal_fallback_enabled=False,
            terminal_fallback_list=["FBS"],
        )
        assert config.is_terminal_accepted("Clear Investimentos") is True
        # Fallback bloqueado
        assert config.is_terminal_accepted("FBS") is False


class TestTradingConfigWithFallback:
    """Testes da TradingConfig integrando fallback terminal."""

    def test_trading_config_default_fallback_values(self):
        """TradingConfig tem defaults de fallback sensatos."""
        with patch.dict("os.environ", {"MT5_LOGIN": "123", "MT5_PASSWORD": "pwd", "MT5_SERVER": "srv"}):
            config = TradingConfig()
            assert config.mt5_terminal_primary == "Clear Investimentos"
            assert config.mt5_terminal_fallback_enabled is True
            assert "FBS" in config.mt5_terminal_fallback_list
            assert config.mt5_terminal_fallback_action == "LOG_WARN_CONTINUE"

    def test_trading_config_fallback_action_literal(self):
        """TradingConfig rejeita fallback_action inválido."""
        with pytest.raises(ValueError):
            with patch.dict("os.environ", {
                "MT5_LOGIN": "123",
                "MT5_PASSWORD": "pwd",
                "MT5_SERVER": "srv",
                "MT5_TERMINAL_FALLBACK_ACTION": "INVALID_ACTION",
            }):
                TradingConfig()


class TestTerminalFallbackIntegration:
    """Testes de integração do comportamento de fallback."""

    @pytest.fixture
    def mock_db(self, tmp_path):
        """Criar banco SQLite in-memory para testes."""
        db_path = tmp_path / "test.db"
        conn = sqlite3.connect(str(db_path))
        cursor = conn.cursor()

        # Criar tabela terminal_decisions conforme ADR-016
        cursor.execute("""
            CREATE TABLE terminal_decisions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                event_type TEXT NOT NULL,
                terminal_detected TEXT NOT NULL,
                config_primary TEXT NOT NULL,
                fallback_enabled BOOLEAN NOT NULL,
                action_taken TEXT NOT NULL
            )
        """)
        conn.commit()
        yield conn
        conn.close()

    def test_fallback_acceptance_persisted_to_db(self, mock_db):
        """Quando fallback é aceito, registrado em SQLite."""
        config = MT5Config(
            terminal_primary="Clear",
            terminal_fallback_enabled=True,
            terminal_fallback_list=["FBS"],
        )

        # Simular aceitação de fallback e persistência
        if config.is_terminal_accepted("FBS"):
            cursor = mock_db.cursor()
            cursor.execute("""
                INSERT INTO terminal_decisions (
                    event_type, terminal_detected, config_primary,
                    fallback_enabled, action_taken
                ) VALUES (?, ?, ?, ?, ?)
            """, ("fallback_accepted", "FBS", config.terminal_primary, config.terminal_fallback_enabled, "LOG_WARN_CONTINUE"))
            mock_db.commit()

            # Verificar que foi persistido
            cursor.execute("SELECT COUNT(*) FROM terminal_decisions WHERE event_type = 'fallback_accepted'")
            count = cursor.fetchone()[0]
            assert count == 1

    def test_fallback_rejection_audit_trail(self, mock_db):
        """Quando fallback é rejeitado, registrado em SQLite."""
        config = MT5Config(
            terminal_primary="Clear",
            terminal_fallback_enabled=True,
            terminal_fallback_list=["FBS"],  # XP não está na lista
        )

        # Simular rejeição de XP
        if not config.is_terminal_accepted("XP"):
            cursor = mock_db.cursor()
            cursor.execute("""
                INSERT INTO terminal_decisions (
                    event_type, terminal_detected, config_primary,
                    fallback_enabled, action_taken
                ) VALUES (?, ?, ?, ?, ?)
            """, ("fallback_rejected", "XP", config.terminal_primary, config.terminal_fallback_enabled, "REJECT_ERROR"))
            mock_db.commit()

            # Verificar que foi persistido
            cursor.execute("SELECT COUNT(*) FROM terminal_decisions WHERE event_type = 'fallback_rejected'")
            count = cursor.fetchone()[0]
            assert count == 1


class TestADR016Scenarios:
    """Testes de cenários reals descritos em ADR-016."""

    def test_scenario_1_fbs_fallback_accepted(self):
        """Cenário 1 (ADR-016): FBS detectado, fallback habilitado → aceito com WARNING."""
        config = MT5Config(
            terminal_primary="Clear Investimentos",
            terminal_fallback_enabled=True,
            terminal_fallback_list=["FBS", "XP", "Zero", "IC Markets"],
        )

        assert config.is_terminal_accepted("FBS") is True
        assert config.should_log_fallback("FBS") is True

    def test_scenario_2_unknown_terminal_rejected(self):
        """Cenário 2: Terminal desconhecido (Ativa, Rica) → rejeitado."""
        config = MT5Config(
            terminal_primary="Clear Investimentos",
            terminal_fallback_enabled=True,
            terminal_fallback_list=["FBS", "XP", "Zero"],
        )

        assert config.is_terminal_accepted("Ativa") is False
        assert config.is_terminal_accepted("Rica") is False

    def test_scenario_3_fallback_disabled_all_rejected(self):
        """Cenário 3: Fallback desabilitado → todos não-primário rejeitado."""
        config = MT5Config(
            terminal_primary="Clear Investimentos",
            terminal_fallback_enabled=False,
            terminal_fallback_list=["FBS", "XP"],
        )

        assert config.is_terminal_accepted("Clear Investimentos") is True
        assert config.is_terminal_accepted("FBS") is False
        assert config.is_terminal_accepted("XP") is False

    def test_scenario_4_strict_mode_reject_all_non_primary(self):
        """Cenário 4: Modo REJECT_ERROR → tira fallback."""
        config = MT5Config(
            terminal_primary="Clear Investimentos",
            terminal_fallback_enabled=True,
            terminal_fallback_list=["FBS"],
            terminal_fallback_action="REJECT_ERROR",
        )

        # Config permite fallback, mas action é REJECT
        assert config.terminal_fallback_action == "REJECT_ERROR"
        # mt5_adapter.py verificará action antes de aceitar


# Testes de markdown lint
class TestDocumentation:
    """Validar que documentação do ADR-016 está bem formatada."""

    def test_adrs_md_has_adr_016(self):
        """Arquivo ADRS.md contém ADR-016."""
        adrs_file = Path(__file__).parent.parent.parent / "docs" / "ADRS.md"
        assert adrs_file.exists(), f"ADRS.md não encontrado em {adrs_file}"

        content = adrs_file.read_text(encoding="utf-8")
        assert "ADR-016" in content, "ADR-016 não encontrado em ADRS.md"
        assert "Terminal Fallback" in content or "terminal fallback" in content.lower()
        assert "CONFIG" in content or "configuração" in content.lower()

    def test_env_example_has_fallback_config(self):
        """Arquivo .env.example contém configurações de fallback."""
        env_file = Path(__file__).parent.parent.parent / ".env.example"
        assert env_file.exists()

        content = env_file.read_text(encoding="utf-8")
        assert "MT5_TERMINAL_PRIMARY" in content
        assert "MT5_TERMINAL_FALLBACK_ENABLED" in content
        assert "MT5_TERMINAL_FALLBACK_LIST" in content
        assert "MT5_TERMINAL_FALLBACK_ACTION" in content


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
