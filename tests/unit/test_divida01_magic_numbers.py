"""
DIVIDA-01: Testes de integridade dos magic numbers canônicos.

Garante que todos os pontos de uso importam do dict canônico
`AGENT_MAGIC_NUMBERS` em `config/settings.py`, sem valores hardcoded.

Critério de aceite:
- AGENT_MAGIC_NUMBERS contém os 4 agentes com valores únicos e positivos.
- mt5_adapter.AGENT_LABELS_BY_MAGIC usa as chaves do dict canônico.
- trade_outcome_reconciler._MAGIC_POR_AGENT é o mesmo dict canônico.
- diario_order_manager.MAGIC_NUMBER == AGENT_MAGIC_NUMBERS["diarios"].
- pipeline_episodios_micro._MAGIC_MICRO == AGENT_MAGIC_NUMBERS["micro_tendencia"].
"""

import pytest

from config.settings import AGENT_MAGIC_NUMBERS


# ---------------------------------------------------------------------------
# Testes do dict canônico
# ---------------------------------------------------------------------------


class TestAgentMagicNumbers:
    """Valida estrutura e consistência do dict canônico."""

    AGENTES_ESPERADOS = {"rl_5000", "rl_direto", "micro_tendencia", "diarios"}

    def test_todos_os_agentes_presentes(self) -> None:
        """AGENT_MAGIC_NUMBERS deve conter exatamente os 4 agentes."""
        assert set(AGENT_MAGIC_NUMBERS.keys()) == self.AGENTES_ESPERADOS

    def test_valores_sao_inteiros_positivos(self) -> None:
        """Cada magic number deve ser inteiro positivo."""
        for agente, magic in AGENT_MAGIC_NUMBERS.items():
            assert isinstance(magic, int), f"{agente}: esperado int, recebeu {type(magic)}"
            assert magic > 0, f"{agente}: magic number deve ser positivo, recebeu {magic}"

    def test_valores_unicos(self) -> None:
        """Nenhum agente pode ter o mesmo magic number."""
        valores = list(AGENT_MAGIC_NUMBERS.values())
        assert len(valores) == len(set(valores)), (
            "Colisão de magic numbers detectada: "
            f"{[v for v in valores if valores.count(v) > 1]}"
        )

    def test_valores_conhecidos(self) -> None:
        """Verifica valores exatos conforme especificação operacional."""
        assert AGENT_MAGIC_NUMBERS["rl_5000"] == 234500
        assert AGENT_MAGIC_NUMBERS["rl_direto"] == 234600
        assert AGENT_MAGIC_NUMBERS["micro_tendencia"] == 234700
        assert AGENT_MAGIC_NUMBERS["diarios"] == 234800


# ---------------------------------------------------------------------------
# Ponto 1: mt5_adapter.AGENT_LABELS_BY_MAGIC
# ---------------------------------------------------------------------------


class TestMt5AdapterLabels:
    """AGENT_LABELS_BY_MAGIC deve derivar do dict canônico."""

    def test_agent_labels_usa_valores_canonicos(self) -> None:
        """Chaves de AGENT_LABELS_BY_MAGIC devem bater com os valores canônicos."""
        from src.infrastructure.adapters.mt5_adapter import AGENT_LABELS_BY_MAGIC

        for agente, magic in AGENT_MAGIC_NUMBERS.items():
            assert magic in AGENT_LABELS_BY_MAGIC, (
                f"magic {magic} ({agente}) ausente em AGENT_LABELS_BY_MAGIC"
            )

    def test_nenhuma_chave_extra(self) -> None:
        """Não deve haver magic numbers em AGENT_LABELS_BY_MAGIC fora do canônico."""
        from src.infrastructure.adapters.mt5_adapter import AGENT_LABELS_BY_MAGIC

        valores_canonicos = set(AGENT_MAGIC_NUMBERS.values())
        chaves_adapter = set(AGENT_LABELS_BY_MAGIC.keys())
        extras = chaves_adapter - valores_canonicos
        assert not extras, f"Chaves extras em AGENT_LABELS_BY_MAGIC: {extras}"


# ---------------------------------------------------------------------------
# Ponto 3: trade_outcome_reconciler._MAGIC_POR_AGENT
# ---------------------------------------------------------------------------


class TestTradeOutcomeReconcilerMagic:
    """_MAGIC_POR_AGENT deve ser o dict canônico."""

    def test_magic_por_agent_igual_ao_canonico(self) -> None:
        """_MAGIC_POR_AGENT deve conter exatamente os mesmos pares do dict canônico."""
        from src.application.reconciliadores.trade_outcome_reconciler import (
            _MAGIC_POR_AGENT,
        )

        assert dict(_MAGIC_POR_AGENT) == dict(AGENT_MAGIC_NUMBERS)

    def test_magic_por_agent_id_retorna_valor_canonico(self) -> None:
        """_magic_por_agent_id deve retornar valores do dict canônico."""
        from src.application.reconciliadores.trade_outcome_reconciler import (
            _magic_por_agent_id,
        )

        for agente, magic in AGENT_MAGIC_NUMBERS.items():
            assert _magic_por_agent_id(agente) == magic

    def test_magic_por_agent_id_levanta_para_desconhecido(self) -> None:
        """_magic_por_agent_id deve levantar ValueError para agente desconhecido."""
        from src.application.reconciliadores.trade_outcome_reconciler import (
            _magic_por_agent_id,
        )

        with pytest.raises(ValueError, match="agent_id desconhecido"):
            _magic_por_agent_id("agente_inexistente_xyz")


# ---------------------------------------------------------------------------
# diario_order_manager.MAGIC_NUMBER
# ---------------------------------------------------------------------------


class TestDiarioOrderManagerMagic:
    """MAGIC_NUMBER do DiarioOrderManager deve vir do dict canônico."""

    def test_magic_number_igual_ao_canonico(self) -> None:
        """MAGIC_NUMBER deve igualar AGENT_MAGIC_NUMBERS["diarios"]."""
        from src.application.diario_order_manager import MAGIC_NUMBER

        assert MAGIC_NUMBER == AGENT_MAGIC_NUMBERS["diarios"]


# ---------------------------------------------------------------------------
# pipeline_episodios_micro._MAGIC_MICRO
# ---------------------------------------------------------------------------


class TestPipelineEpisodiosMicro:
    """_MAGIC_MICRO do pipeline deve vir do dict canônico."""

    def test_magic_micro_igual_ao_canonico(self) -> None:
        """_MAGIC_MICRO deve igualar AGENT_MAGIC_NUMBERS["micro_tendencia"]."""
        from src.application.pipeline_episodios_micro import _MAGIC_MICRO

        assert _MAGIC_MICRO == AGENT_MAGIC_NUMBERS["micro_tendencia"]
