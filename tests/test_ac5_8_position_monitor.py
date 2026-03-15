"""
Test AC5.8: Monitoramento em Tempo Real de Execucao

Testa trade manager/position monitor em tempo real com:
- Atualizacao de status de ordem e posicao
- Reacao a erro, parcial, cancelamento e encerramento
- Rastreamento de transicoes de estado
- Persistencia em BD SQLite

Coverage Target: >=80%
Type Hints: 100%
Idioma: Portugues
"""

import pytest
import sqlite3
from datetime import datetime, timedelta
from decimal import Decimal
from typing import Dict, List, Any, Optional
from dataclasses import dataclass
from unittest.mock import Mock, patch, MagicMock

from src.application.ac5_8_position_monitor import (
    MonitorPositionManager,
    PosicaoAberta,
    EvendoOrdem,
    StatusOrdem,
    StatusPosicao,
)


# ============================================================================
# FIXTURES
# ============================================================================


@pytest.fixture
def memoria_db() -> sqlite3.Connection:
    """Cria BD SQLite em memoria para testes."""
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    _inicializar_schema(conn)
    return conn


def _inicializar_schema(conn: sqlite3.Connection) -> None:
    """Inicializa schema de BD para testes."""
    cursor = conn.cursor()

    cursor.execute("""
        CREATE TABLE ordens (
            trade_id TEXT PRIMARY KEY,
            signal_id TEXT NOT NULL,
            symbol TEXT NOT NULL,
            direcao TEXT NOT NULL,
            volume INTEGER NOT NULL,
            preco_entrada REAL NOT NULL,
            sl REAL NOT NULL,
            tp REAL NOT NULL,
            status TEXT NOT NULL DEFAULT 'PENDING',
            criado_em TEXT NOT NULL,
            atualizado_em TEXT NOT NULL
        )
    """)

    cursor.execute("""
        CREATE TABLE posicoes_abertas (
            posicao_id TEXT PRIMARY KEY,
            trade_id TEXT NOT NULL UNIQUE,
            symbol TEXT NOT NULL,
            direcao TEXT NOT NULL,
            volume INTEGER NOT NULL,
            preco_entrada REAL NOT NULL,
            preco_atual REAL NOT NULL,
            pl REAL NOT NULL,
            status TEXT NOT NULL DEFAULT 'ABERTA',
            criado_em TEXT NOT NULL,
            atualizado_em TEXT NOT NULL,
            FOREIGN KEY(trade_id) REFERENCES ordens(trade_id)
        )
    """)

    cursor.execute("""
        CREATE TABLE eventos_monitoramento (
            evento_id TEXT PRIMARY KEY,
            trade_id TEXT NOT NULL,
            tipo_evento TEXT NOT NULL,
            descricao TEXT,
            timestamp TEXT NOT NULL,
            FOREIGN KEY(trade_id) REFERENCES ordens(trade_id)
        )
    """)

    conn.commit()


@pytest.fixture
def monitor(memoria_db: sqlite3.Connection) -> MonitorPositionManager:
    """Cria MonitorPositionManager com BD em memoria."""
    return MonitorPositionManager(db_conexao=memoria_db)


# ============================================================================
# TESTES DE INICIALIZACAO
# ============================================================================


class TestInicializacao:
    """Testes de inicializacao do monitor."""

    def test_criar_monitor_com_conexao_valida(
        self, monitor: MonitorPositionManager
    ) -> None:
        """Verifica criacao com conexao BD valida."""
        assert monitor is not None
        assert monitor.bd_conexao is not None

    def test_monitor_inicializa_vazio(self, monitor: MonitorPositionManager) -> None:
        """Verifica que monitor comeca vazio."""
        posicoes = monitor.listar_posicoes_abertas()
        assert posicoes == []


# ============================================================================
# TESTES DE CRIACAO DE ORDEM
# ============================================================================


class TestCriacaoOrdem:
    """Testes para criacao e rastreamento de ordens."""

    def test_registrar_ordem_com_dados_validos(
        self, monitor: MonitorPositionManager
    ) -> None:
        """Verifica registro de ordem com dados validos."""
        ordem_spec: Dict[str, Any] = {
            "trade_id": "TRADE_001",
            "signal_id": "SIG_001",
            "symbol": "WINFUT",
            "direcao": "BUY",
            "volume": 1,
            "preco_entrada": 100.0,
            "sl": 99.0,
            "tp": 102.0,
        }

        resultado = monitor.registrar_ordem(ordem_spec)
        assert resultado is True

        # Verificar se foi persistida
        posicoes = monitor.listar_posicoes_abertas()
        assert len(posicoes) == 1
        assert posicoes[0]["trade_id"] == "TRADE_001"

    def test_registrar_ordem_duplicada_falha(
        self, monitor: MonitorPositionManager
    ) -> None:
        """Verifica que registrar ordem duplicada falha."""
        ordem_spec: Dict[str, Any] = {
            "trade_id": "TRADE_001",
            "signal_id": "SIG_001",
            "symbol": "WINFUT",
            "direcao": "BUY",
            "volume": 1,
            "preco_entrada": 100.0,
            "sl": 99.0,
            "tp": 102.0,
        }

        monitor.registrar_ordem(ordem_spec)
        resultado = monitor.registrar_ordem(ordem_spec)  # Segunda tentativa
        assert resultado is False


# ============================================================================
# TESTES DE ATUALIZACAO DE STATUS
# ============================================================================


class TestAtualizacaoStatus:
    """Testes para transicoes de status."""

    def test_atualizar_status_ordem_pending_para_sent(
        self, monitor: MonitorPositionManager
    ) -> None:
        """Verifica transicao PENDING → SENT."""
        ordem_spec: Dict[str, Any] = {
            "trade_id": "TRADE_002",
            "signal_id": "SIG_002",
            "symbol": "WINFUT",
            "direcao": "BUY",
            "volume": 1,
            "preco_entrada": 100.0,
            "sl": 99.0,
            "tp": 102.0,
        }
        monitor.registrar_ordem(ordem_spec)

        resultado = monitor.atualizar_status_ordem(
            trade_id="TRADE_002", novo_status=StatusOrdem.SENT
        )
        assert resultado is True

        # Verificar status da ordem, não da posicao
        # A posicao permanece ABERTA ate FILLED
        cursor = monitor.bd_conexao.cursor()
        cursor.execute("SELECT status FROM ordens WHERE trade_id = ?", ("TRADE_002",))
        status_ordem = cursor.fetchone()["status"]
        assert status_ordem == StatusOrdem.SENT.value

    def test_atualizar_status_ordem_invalido_falha(
        self, monitor: MonitorPositionManager
    ) -> None:
        """Verifica que atualizar ordem inexistente falha."""
        resultado = monitor.atualizar_status_ordem(
            trade_id="TRADE_INEXISTENTE", novo_status=StatusOrdem.SENT
        )
        assert resultado is False


# ============================================================================
# TESTES DE MONITORAMENTO DE POSICAO
# ============================================================================


class TestMonitoramentoPosicao:
    """Testes para monitoramento de posicoes abertas."""

    def test_atualizar_preco_posicao_aberta(
        self, monitor: MonitorPositionManager
    ) -> None:
        """Verifica atualizacao de preco em posicao aberta."""
        ordem_spec: Dict[str, Any] = {
            "trade_id": "TRADE_003",
            "signal_id": "SIG_003",
            "symbol": "WINFUT",
            "direcao": "BUY",
            "volume": 1,
            "preco_entrada": 100.0,
            "sl": 99.0,
            "tp": 102.0,
        }
        monitor.registrar_ordem(ordem_spec)
        monitor.atualizar_status_ordem(
            trade_id="TRADE_003", novo_status=StatusOrdem.FILLED
        )

        # Atualizar preco atual
        resultado = monitor.atualizar_preco_posicao(
            trade_id="TRADE_003", preco_atual=101.0
        )
        assert resultado is True

        posicoes = monitor.listar_posicoes_abertas()
        assert posicoes[0]["preco_atual"] == 101.0

    def test_calcular_pl_posicao_buy(
        self, monitor: MonitorPositionManager
    ) -> None:
        """Verifica calculo correto de P&L para posicao BUY."""
        ordem_spec: Dict[str, Any] = {
            "trade_id": "TRADE_004",
            "signal_id": "SIG_004",
            "symbol": "WINFUT",
            "direcao": "BUY",
            "volume": 1,
            "preco_entrada": 100.0,
            "sl": 99.0,
            "tp": 102.0,
        }
        monitor.registrar_ordem(ordem_spec)
        monitor.atualizar_status_ordem(
            trade_id="TRADE_004", novo_status=StatusOrdem.FILLED
        )
        monitor.atualizar_preco_posicao(trade_id="TRADE_004", preco_atual=101.0)

        posicoes = monitor.listar_posicoes_abertas()
        # P&L = (preco_atual - preco_entrada) * volume = (101 - 100) * 1 = 1.0
        assert posicoes[0]["pl"] == 1.0

    def test_calcular_pl_posicao_sell(
        self, monitor: MonitorPositionManager
    ) -> None:
        """Verifica calculo correto de P&L para posicao SELL."""
        ordem_spec: Dict[str, Any] = {
            "trade_id": "TRADE_005",
            "signal_id": "SIG_005",
            "symbol": "WINFUT",
            "direcao": "SELL",
            "volume": 1,
            "preco_entrada": 100.0,
            "sl": 101.0,
            "tp": 98.0,
        }
        monitor.registrar_ordem(ordem_spec)
        monitor.atualizar_status_ordem(
            trade_id="TRADE_005", novo_status=StatusOrdem.FILLED
        )
        monitor.atualizar_preco_posicao(trade_id="TRADE_005", preco_atual=99.0)

        posicoes = monitor.listar_posicoes_abertas()
        # P&L = (preco_entrada - preco_atual) * volume = (100 - 99) * 1 = 1.0
        assert posicoes[0]["pl"] == 1.0


# ============================================================================
# TESTES DE REACAO A EVENTOS
# ============================================================================


class TestReacaoEventos:
    """Testes para reacao a eventos de ordem."""

    def test_encerrar_posicao_com_lucro(
        self, monitor: MonitorPositionManager
    ) -> None:
        """Verifica encerramento de posicao com lucro."""
        ordem_spec: Dict[str, Any] = {
            "trade_id": "TRADE_006",
            "signal_id": "SIG_006",
            "symbol": "WINFUT",
            "direcao": "BUY",
            "volume": 1,
            "preco_entrada": 100.0,
            "sl": 99.0,
            "tp": 102.0,
        }
        monitor.registrar_ordem(ordem_spec)
        monitor.atualizar_status_ordem(
            trade_id="TRADE_006", novo_status=StatusOrdem.FILLED
        )
        monitor.atualizar_preco_posicao(trade_id="TRADE_006", preco_atual=102.0)

        # Atingiu TP
        resultado = monitor.encerrar_posicao(
            trade_id="TRADE_006", preco_encerramento=102.0
        )
        assert resultado is True

        posicoes = monitor.listar_posicoes_abertas()
        # Posicao deveria estar vazia (encerrada)
        fechadas = monitor.listar_posicoes_encerradas()
        assert len(fechadas) == 1

    def test_cancelar_ordem_pendente(
        self, monitor: MonitorPositionManager
    ) -> None:
        """Verifica cancelamento de ordem pendente."""
        ordem_spec: Dict[str, Any] = {
            "trade_id": "TRADE_007",
            "signal_id": "SIG_007",
            "symbol": "WINFUT",
            "direcao": "BUY",
            "volume": 1,
            "preco_entrada": 100.0,
            "sl": 99.0,
            "tp": 102.0,
        }
        monitor.registrar_ordem(ordem_spec)

        resultado = monitor.cancelar_ordem(trade_id="TRADE_007")
        assert resultado is True

        posicoes = monitor.listar_posicoes_abertas()
        assert len(posicoes) == 0

    def test_registrar_rejeicao_ordem(
        self, monitor: MonitorPositionManager
    ) -> None:
        """Verifica registro de rejeicao de ordem."""
        ordem_spec: Dict[str, Any] = {
            "trade_id": "TRADE_008",
            "signal_id": "SIG_008",
            "symbol": "WINFUT",
            "direcao": "BUY",
            "volume": 1,
            "preco_entrada": 100.0,
            "sl": 99.0,
            "tp": 102.0,
        }
        monitor.registrar_ordem(ordem_spec)

        resultado = monitor.rejeitar_ordem(
            trade_id="TRADE_008", motivo="Margem insuficiente"
        )
        assert resultado is True

        posicoes = monitor.listar_posicoes_abertas()
        assert len(posicoes) == 0


# ============================================================================
# TESTES DE RASTREAMENTO DE EVENTOS
# ============================================================================


class TestRastreamentoEventos:
    """Testes para rastreamento de eventos de monitoramento."""

    def test_registrar_evento_monitoramento(
        self, monitor: MonitorPositionManager
    ) -> None:
        """Verifica registro de evento de monitoramento."""
        ordem_spec: Dict[str, Any] = {
            "trade_id": "TRADE_009",
            "signal_id": "SIG_009",
            "symbol": "WINFUT",
            "direcao": "BUY",
            "volume": 1,
            "preco_entrada": 100.0,
            "sl": 99.0,
            "tp": 102.0,
        }
        monitor.registrar_ordem(ordem_spec)

        # Evento inicial: ORDEM_REGISTRADA é criado automaticamente
        eventos_iniciais = monitor.listar_eventos(trade_id="TRADE_009")
        assert len(eventos_iniciais) == 1  # Evento ORDEM_REGISTRADA

        evento_id = monitor.registrar_evento(
            trade_id="TRADE_009",
            tipo_evento="PRICE_UPDATE",
            descricao="Preco atualizado para 101.0",
        )
        assert evento_id is not None

        eventos = monitor.listar_eventos(trade_id="TRADE_009")
        assert len(eventos) == 2  # Agora tem 2
        # Verificar que novo evento está na lista
        tipos_eventos = [e["tipo_evento"] for e in eventos]
        assert "PRICE_UPDATE" in tipos_eventos
        assert "ORDEM_REGISTRADA" in tipos_eventos

    def test_listar_eventos_trade(
        self, monitor: MonitorPositionManager
    ) -> None:
        """Verifica listagem de eventos por trade."""
        ordem_spec: Dict[str, Any] = {
            "trade_id": "TRADE_010",
            "signal_id": "SIG_010",
            "symbol": "WINFUT",
            "direcao": "BUY",
            "volume": 1,
            "preco_entrada": 100.0,
            "sl": 99.0,
            "tp": 102.0,
        }
        monitor.registrar_ordem(ordem_spec)

        # Evento ORDEM_REGISTRADA é criado automaticamente (1 evento inicial)
        monitor.registrar_evento(
            "TRADE_010", "PRICE_UPDATE", "Atualizacao 1"
        )
        monitor.registrar_evento(
            "TRADE_010", "PRICE_UPDATE", "Atualizacao 2"
        )

        eventos = monitor.listar_eventos(trade_id="TRADE_010")
        # Total: ORDEM_REGISTRADA (auto) + 2 PRICE_UPDATE = 3
        assert len(eventos) == 3


# ============================================================================
# TESTES DE CONSULTA DE STATUS
# ============================================================================


class TestConsultaStatus:
    """Testes para consulta de status e relatorios."""

    def test_listar_posicoes_abertas_multiplas(
        self, monitor: MonitorPositionManager
    ) -> None:
        """Verifica listagem de multiplas posicoes abertas."""
        for i in range(3):
            ordem_spec: Dict[str, Any] = {
                "trade_id": f"TRADE_{i}",
                "signal_id": f"SIG_{i}",
                "symbol": "WINFUT",
                "direcao": "BUY",
                "volume": 1,
                "preco_entrada": 100.0 + i,
                "sl": 99.0,
                "tp": 102.0,
            }
            monitor.registrar_ordem(ordem_spec)
            monitor.atualizar_status_ordem(
                trade_id=f"TRADE_{i}", novo_status=StatusOrdem.FILLED
            )

        posicoes = monitor.listar_posicoes_abertas()
        assert len(posicoes) == 3

    def test_contar_posicoes_abertas(
        self, monitor: MonitorPositionManager
    ) -> None:
        """Verifica contagem de posicoes abertas."""
        for i in range(2):
            ordem_spec: Dict[str, Any] = {
                "trade_id": f"TRADE_COUNT_{i}",
                "signal_id": f"SIG_{i}",
                "symbol": "WINFUT",
                "direcao": "BUY",
                "volume": 1,
                "preco_entrada": 100.0,
                "sl": 99.0,
                "tp": 102.0,
            }
            monitor.registrar_ordem(ordem_spec)
            monitor.atualizar_status_ordem(
                trade_id=f"TRADE_COUNT_{i}", novo_status=StatusOrdem.FILLED
            )

        contagem = monitor.contar_posicoes_abertas()
        assert contagem == 2

    def test_obter_posicao_por_trade_id(
        self, monitor: MonitorPositionManager
    ) -> None:
        """Verifica obtencao de posicao especifica."""
        ordem_spec: Dict[str, Any] = {
            "trade_id": "TRADE_SPEC",
            "signal_id": "SIG_SPEC",
            "symbol": "WINFUT",
            "direcao": "BUY",
            "volume": 1,
            "preco_entrada": 100.0,
            "sl": 99.0,
            "tp": 102.0,
        }
        monitor.registrar_ordem(ordem_spec)
        monitor.atualizar_status_ordem(
            trade_id="TRADE_SPEC", novo_status=StatusOrdem.FILLED
        )

        posicao = monitor.obter_posicao(trade_id="TRADE_SPEC")
        assert posicao is not None
        assert posicao["trade_id"] == "TRADE_SPEC"

    def test_obter_posicao_inexistente_retorna_none(
        self, monitor: MonitorPositionManager
    ) -> None:
        """Verifica que obter posicao inexistente retorna None."""
        posicao = monitor.obter_posicao(trade_id="TRADE_INEXISTENTE")
        assert posicao is None


# ============================================================================
# TESTES DE INTEGRACAO
# ============================================================================


class TestIntegracao:
    """Testes de integracao de fluxos completos."""

    def test_fluxo_completo_ordem_ate_encerramento(
        self, monitor: MonitorPositionManager
    ) -> None:
        """Verifica fluxo completo: Ordem → Sent → Filled → Encerrada."""
        # 1. Registrar ordem
        ordem_spec: Dict[str, Any] = {
            "trade_id": "TRADE_FLUXO",
            "signal_id": "SIG_FLUXO",
            "symbol": "WINFUT",
            "direcao": "BUY",
            "volume": 1,
            "preco_entrada": 100.0,
            "sl": 99.0,
            "tp": 102.0,
        }
        assert monitor.registrar_ordem(ordem_spec) is True

        # 2. Enviar ordem
        assert (
            monitor.atualizar_status_ordem(
                trade_id="TRADE_FLUXO", novo_status=StatusOrdem.SENT
            )
            is True
        )

        # 3. Executar ordem
        assert (
            monitor.atualizar_status_ordem(
                trade_id="TRADE_FLUXO", novo_status=StatusOrdem.FILLED
            )
            is True
        )

        # 4. Atualizar precos
        assert (
            monitor.atualizar_preco_posicao(
                trade_id="TRADE_FLUXO", preco_atual=102.0
            )
            is True
        )

        # 5. Atingiu TP - Encerrar
        assert (
            monitor.encerrar_posicao(
                trade_id="TRADE_FLUXO", preco_encerramento=102.0
            )
            is True
        )

        # Verificar estado final
        aberta = monitor.obter_posicao(trade_id="TRADE_FLUXO")
        assert aberta is None  # Nao deve estar mais aberta

        fechadas = monitor.listar_posicoes_encerradas()
        assert len(fechadas) == 1
