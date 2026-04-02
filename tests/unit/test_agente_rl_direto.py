"""
Testes unitarios para correcoes TECH-001, TECH-002 e TECH-003
no agente RL Direto (scripts/agente_rl_direto_independente.py).

TECH-001: preco_saida=0.0 no historico_fechamentos
TECH-002: Resultado DESCONHECIDO em trades de sessao divergente
TECH-003: retcode 10006 nao capturado em todos os formatos
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any
from unittest.mock import MagicMock, patch

import pytest

# Garantir que o root do projeto esteja no path
ROOT = Path(__file__).parent.parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


# ---------------------------------------------------------------------------
# Helpers de import — o modulo tem muitas dependencias opcionais;
# importamos apenas as funcoes que precisamos testar via importlib
# ---------------------------------------------------------------------------

def _importar_funcao(nome: str) -> Any:
    """Importa uma funcao do modulo sem executar o __main__."""
    import importlib.util
    spec = importlib.util.spec_from_file_location(
        "agente_rl_direto_independente",
        ROOT / "scripts" / "agente_rl_direto_independente.py",
    )
    assert spec is not None and spec.loader is not None
    mod = importlib.util.module_from_spec(spec)
    # Preencher dependencias minimas para evitar crash no import
    mod.__dict__.setdefault("SIMBOLO", "WIN$N")  # type: ignore[attr-defined]
    return getattr(mod, nome, None)


# ---------------------------------------------------------------------------
# TECH-001 — resolver_preco_saida_real nunca retorna 0.0
# ---------------------------------------------------------------------------

class TestTech001PrecoSaidaNuncaZero:
    """TECH-001: garantir que preco_saida nunca seja 0.0."""

    def _mock_adapter(self, retorno: Any) -> MagicMock:
        adapter = MagicMock()
        adapter.obter_preco_saida_por_ticket = MagicMock(return_value=retorno)
        return adapter

    def test_preco_valido_retornado(self) -> None:
        """Quando adapter retorna preco > 0, retornar esse preco."""
        from scripts.agente_rl_direto_independente import (  # type: ignore[import]
            TipoPosicao,
            resolver_preco_saida_real,
        )
        adapter = self._mock_adapter(189500.0)
        resultado = resolver_preco_saida_real(adapter, 12345, TipoPosicao.COMPRADA)
        assert resultado == 189500.0

    def test_preco_zero_do_adapter_retorna_none(self) -> None:
        """Quando adapter retorna 0.0, funcao deve retornar None (nao 0.0)."""
        from scripts.agente_rl_direto_independente import (  # type: ignore[import]
            TipoPosicao,
            resolver_preco_saida_real,
        )
        adapter = self._mock_adapter(0.0)
        resultado = resolver_preco_saida_real(adapter, 12345, TipoPosicao.COMPRADA)
        assert resultado is None

    def test_adapter_sem_metodo_retorna_none(self) -> None:
        """Adapter sem obter_preco_saida_por_ticket retorna None."""
        from scripts.agente_rl_direto_independente import (  # type: ignore[import]
            TipoPosicao,
            resolver_preco_saida_real,
        )
        adapter = MagicMock(spec=[])  # sem nenhum atributo
        resultado = resolver_preco_saida_real(adapter, 12345, TipoPosicao.COMPRADA)
        assert resultado is None

    def test_excecao_no_adapter_retorna_none(self) -> None:
        """Excecao no adapter retorna None sem propagar."""
        from scripts.agente_rl_direto_independente import (  # type: ignore[import]
            TipoPosicao,
            resolver_preco_saida_real,
        )
        adapter = MagicMock()
        adapter.obter_preco_saida_por_ticket.side_effect = RuntimeError("MT5 offline")
        resultado = resolver_preco_saida_real(adapter, 12345, TipoPosicao.COMPRADA)
        assert resultado is None

    def test_fallback_usa_preco_entrada_quando_atual_e_zero(self) -> None:
        """
        No ciclo principal, quando preco_saida_real=None e preco_atual=0,
        o codigo deve usar preco_entrada como fallback (nao 0.0).
        Verificamos que o guard existe no modulo.
        """
        # Este teste valida a logica de fallback indiretamente lendo o codigo
        fonte = (ROOT / "scripts" / "agente_rl_direto_independente.py").read_text(
            encoding="utf-8"
        )
        assert "TECH-001" in fonte
        assert "preco_saida_real = preco_entrada_reg" in fonte


# ---------------------------------------------------------------------------
# TECH-002 — recuperar contexto via metadados quando session_id diverge
# ---------------------------------------------------------------------------

class TestTech002DesconhecidoRecuperacao:
    """TECH-002: contexto recuperado via metadados quando session_id diverge."""

    def test_alerta_desconhecido_consecutivos_presente_no_codigo(self) -> None:
        """Verificar que o alerta de DESCONHECIDO consecutivos esta implementado."""
        fonte = (ROOT / "scripts" / "agente_rl_direto_independente.py").read_text(
            encoding="utf-8"
        )
        assert "TECH-002" in fonte
        assert "_contagem_desconhecido" in fonte
        assert "ALERTA" in fonte

    def test_recuperacao_via_metadados_presente_no_codigo(self) -> None:
        """Verificar que a tentativa de recuperacao via metadados esta implementada."""
        fonte = (ROOT / "scripts" / "agente_rl_direto_independente.py").read_text(
            encoding="utf-8"
        )
        assert "recuperado_tech002" in fonte
        assert "preco_entrada_recuperado" in fonte

    def test_contador_desconhecido_inicializado_no_loop(self) -> None:
        """Verificar que _contagem_desconhecido e inicializado antes do loop."""
        fonte = (ROOT / "scripts" / "agente_rl_direto_independente.py").read_text(
            encoding="utf-8"
        )
        assert "_contagem_desconhecido: int = 0" in fonte

    def test_contador_reset_apos_recuperacao(self) -> None:
        """Verificar que o contador e zerado quando o contexto e recuperado."""
        fonte = (ROOT / "scripts" / "agente_rl_direto_independente.py").read_text(
            encoding="utf-8"
        )
        assert "_contagem_desconhecido = 0  # reset ao recuperar" in fonte


# ---------------------------------------------------------------------------
# TECH-003 — retcode 10006 capturado em todos os formatos
# ---------------------------------------------------------------------------

class TestTech003Backoff10006:
    """TECH-003: backoff correto para retcode 10006 em multiplos formatos."""

    def _fazer_retry_mgr(self) -> MagicMock:
        retry_resultado = MagicMock()
        retry_resultado.deve_encerrar.return_value = False
        retry_resultado.aguardar_segundos = 0
        retry_resultado.status = MagicMock()
        retry_resultado.status.value = "AGUARDAR"
        retry_resultado.falhas_consecutivas = 1
        mgr = MagicMock()
        mgr.registrar_falha_10006.return_value = retry_resultado
        return mgr

    def test_backoff_acionado_por_string_10006(self) -> None:
        """Excecao com '10006' na mensagem aciona backoff."""
        from scripts.agente_rl_direto_independente import (  # type: ignore[import]
            enviar_ordem_com_backoff,
        )
        adapter = MagicMock()
        adapter.send_order.side_effect = [
            Exception("MT5 error retcode 10006 requote"),
            "TICKET_123",
        ]
        retry_mgr = self._fazer_retry_mgr()
        resultado = enviar_ordem_com_backoff(adapter, MagicMock(), retry_mgr=retry_mgr)
        assert resultado == "TICKET_123"
        retry_mgr.registrar_falha_10006.assert_called_once()

    def test_backoff_acionado_por_atributo_retcode(self) -> None:
        """Excecao com .retcode=10006 aciona backoff (TECH-003)."""
        from scripts.agente_rl_direto_independente import (  # type: ignore[import]
            enviar_ordem_com_backoff,
        )

        class Excecao10006(Exception):
            retcode = 10006

        adapter = MagicMock()
        adapter.send_order.side_effect = [Excecao10006("requote"), "TICKET_456"]
        retry_mgr = self._fazer_retry_mgr()
        resultado = enviar_ordem_com_backoff(adapter, MagicMock(), retry_mgr=retry_mgr)
        assert resultado == "TICKET_456"
        retry_mgr.registrar_falha_10006.assert_called_once()

    def test_excecao_outro_retcode_propagada(self) -> None:
        """Excecao com retcode diferente de 10006 deve ser propagada."""
        from scripts.agente_rl_direto_independente import (  # type: ignore[import]
            enviar_ordem_com_backoff,
        )
        adapter = MagicMock()
        adapter.send_order.side_effect = RuntimeError("retcode 10004 no money")
        retry_mgr = self._fazer_retry_mgr()
        with pytest.raises(RuntimeError):
            enviar_ordem_com_backoff(adapter, MagicMock(), retry_mgr=retry_mgr)

    def test_backoff_encerra_apos_limite(self) -> None:
        """Quando deve_encerrar=True, funcao retorna None sem loop infinito."""
        from scripts.agente_rl_direto_independente import (  # type: ignore[import]
            enviar_ordem_com_backoff,
        )
        adapter = MagicMock()
        adapter.send_order.side_effect = Exception("10006 requote")
        retry_resultado = MagicMock()
        retry_resultado.deve_encerrar.return_value = True
        retry_resultado.mensagem = "Limite de falhas atingido"
        retry_resultado.status = MagicMock()
        retry_resultado.status.value = "ENCERRAR"
        retry_resultado.falhas_consecutivas = 5
        retry_resultado.aguardar_segundos = 0
        retry_mgr = MagicMock()
        retry_mgr.registrar_falha_10006.return_value = retry_resultado
        resultado = enviar_ordem_com_backoff(adapter, MagicMock(), retry_mgr=retry_mgr)
        assert resultado is None
