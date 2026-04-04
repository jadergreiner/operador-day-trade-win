"""Testes unitários TDD — FechamentoDiarioAgenteService.

BLID-029 — Fechamento Diário por Agente (RL_5000 / RL_DIRETO).
Executor: INICIAR_DIARIOS.bat

FASE RED: estes testes DEVEM falhar até que o serviço seja implementado em:
    src/application/services/fechamento_diario_agente_service.py

Cenários cobertos:
    Happy path:  H1–H5
    Erro:        E1–E4
    Borda:       B1–B5
    Regressão:   R1–R3

Execução:
    python3 -m pytest tests/unit/test_fechamento_diario_agente_service.py -v
"""
from __future__ import annotations

import sqlite3
import sys
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any
from unittest.mock import MagicMock

import pytest

# ---------------------------------------------------------------------------
# Garante que src/ está no PYTHONPATH independente de onde pytest é chamado.
# ---------------------------------------------------------------------------
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

# ---------------------------------------------------------------------------
# Import do módulo alvo (pode falhar na RED phase — comportamento esperado).
# ---------------------------------------------------------------------------
from src.application.services.fechamento_diario_agente_service import (
    FechamentoDiarioAgenteService,
    RelatorioFechamentoDiarioAgente,
)

# ---------------------------------------------------------------------------
# Constantes de teste
# ---------------------------------------------------------------------------
_DATA_PADRAO = "2026-05-01"
_DATA_FUTURA = str(date.today().replace(year=date.today().year + 1))
_MAGIC_RL_5000 = 234500
_MAGIC_RL_DIRETO = 234600
_MAGIC_INVALIDO = 999999

_DDL_TRADES = """
CREATE TABLE IF NOT EXISTS trades (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    magic_number INTEGER NOT NULL,
    side         TEXT    NOT NULL,
    entry_time   TEXT    NOT NULL,
    exit_time    TEXT,
    profit_loss  REAL,
    status       TEXT
);
"""


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _insert_trade(
    conn: sqlite3.Connection,
    magic_number: int,
    profit_loss: float | None,
    entry_time: str = f"{_DATA_PADRAO} 10:00:00",
    exit_time: str | None = f"{_DATA_PADRAO} 10:05:00",
    side: str = "BUY",
    status: str = "CLOSED",
) -> None:
    conn.execute(
        """
        INSERT INTO trades (magic_number, side, entry_time, exit_time,
                            profit_loss, status)
        VALUES (?, ?, ?, ?, ?, ?)
        """,
        (magic_number, side, entry_time, exit_time, profit_loss, status),
    )
    conn.commit()


def _banco_em_memoria() -> sqlite3.Connection:
    conn = sqlite3.connect(":memory:")
    conn.execute(_DDL_TRADES)
    conn.commit()
    return conn


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture()
def db_path(tmp_path: Path) -> Path:
    """Banco SQLite isolado com DDL da tabela trades."""
    path = tmp_path / "trading.db"
    conn = sqlite3.connect(str(path))
    conn.execute(_DDL_TRADES)
    conn.commit()
    conn.close()
    return path


@pytest.fixture()
def svc() -> FechamentoDiarioAgenteService:
    """Instância do service sob teste."""
    return FechamentoDiarioAgenteService()


@pytest.fixture()
def outputs_dir(tmp_path: Path) -> Path:
    """Diretório temporário para saídas Markdown."""
    d = tmp_path / "outputs" / "diarios"
    d.mkdir(parents=True)
    return d


# ===========================================================================
# H — Happy Path
# ===========================================================================


@pytest.mark.unit
class TestHappyPath:
    """H1–H4: cenários felizes do service principal."""

    def test_H1_tres_trades_vencedores_rl5000(
        self, svc: FechamentoDiarioAgenteService, db_path: Path
    ) -> None:
        """H1: 3 trades win RL_5000 → total_trades=3, win_rate=1.0, pnl=450."""
        conn = sqlite3.connect(str(db_path))
        for pnl, t in [
            (100.0, "09:10:00"),
            (200.0, "10:30:00"),
            (150.0, "11:00:00"),
        ]:
            _insert_trade(conn, _MAGIC_RL_5000, pnl, entry_time=f"{_DATA_PADRAO} {t}")
        conn.close()

        rel = svc.gerar_relatorio("rl_5000", _MAGIC_RL_5000, _DATA_PADRAO, db_path)

        assert rel.total_trades == 3
        assert rel.win_rate == pytest.approx(1.0)
        assert rel.pnl_total_reais == pytest.approx(450.0)
        assert rel.status == "LUCRATIVO"
        assert rel.agent_name == "rl_5000"
        assert rel.magic_number == _MAGIC_RL_5000
        assert rel.data == _DATA_PADRAO

    def test_H2_mix_win_loss_rl_direto(
        self, svc: FechamentoDiarioAgenteService, db_path: Path
    ) -> None:
        """H2: 4 trades mix rl_direto → win_rate=0.5, pnl=170.0, LUCRATIVO."""
        conn = sqlite3.connect(str(db_path))
        for pnl, t in [
            (200.0, "09:00:00"),
            (-50.0, "09:30:00"),
            (100.0, "10:00:00"),
            (-80.0, "10:30:00"),
        ]:
            _insert_trade(conn, _MAGIC_RL_DIRETO, pnl, entry_time=f"{_DATA_PADRAO} {t}")
        conn.close()

        rel = svc.gerar_relatorio("rl_direto", _MAGIC_RL_DIRETO, _DATA_PADRAO, db_path)

        assert rel.total_trades == 4
        assert rel.win_rate == pytest.approx(0.5)
        assert rel.pnl_total_reais == pytest.approx(170.0)
        assert rel.status == "LUCRATIVO"

    def test_H3_break_even(
        self, svc: FechamentoDiarioAgenteService, db_path: Path
    ) -> None:
        """H3: 2 trades cancelam-se → status=NEUTRO, pnl=0.0."""
        conn = sqlite3.connect(str(db_path))
        _insert_trade(conn, _MAGIC_RL_5000, 100.0, entry_time=f"{_DATA_PADRAO} 09:00:00")
        _insert_trade(conn, _MAGIC_RL_5000, -100.0, entry_time=f"{_DATA_PADRAO} 10:00:00")
        conn.close()

        rel = svc.gerar_relatorio("rl_5000", _MAGIC_RL_5000, _DATA_PADRAO, db_path)

        assert rel.status == "NEUTRO"
        assert rel.pnl_total_reais == pytest.approx(0.0, abs=1e-9)

    def test_H4_dia_deficitario(
        self, svc: FechamentoDiarioAgenteService, db_path: Path
    ) -> None:
        """H4: 3 trades perdedores → status=DEFICITARIO, pnl=-350.0."""
        conn = sqlite3.connect(str(db_path))
        for pnl, t in [(-100.0, "09:00:00"), (-200.0, "10:00:00"), (-50.0, "11:00:00")]:
            _insert_trade(conn, _MAGIC_RL_5000, pnl, entry_time=f"{_DATA_PADRAO} {t}")
        conn.close()

        rel = svc.gerar_relatorio("rl_5000", _MAGIC_RL_5000, _DATA_PADRAO, db_path)

        assert rel.status == "DEFICITARIO"
        assert rel.pnl_total_reais == pytest.approx(-350.0)

    def test_H5_session_id_formato(
        self, svc: FechamentoDiarioAgenteService, db_path: Path
    ) -> None:
        """H5: session_id deve seguir padrão '{agent_name}_{YYYY-MM-DD}_{magic}'."""
        conn = sqlite3.connect(str(db_path))
        _insert_trade(conn, _MAGIC_RL_5000, 100.0)
        conn.close()

        rel = svc.gerar_relatorio("rl_5000", _MAGIC_RL_5000, _DATA_PADRAO, db_path)

        expected_id = f"rl_5000_{_DATA_PADRAO}_{_MAGIC_RL_5000}"
        assert rel.session_id == expected_id

    def test_H5_campos_obrigatorios_preenchidos(
        self, svc: FechamentoDiarioAgenteService, db_path: Path
    ) -> None:
        """H5: todos os campos obrigatórios devem estar presentes e tipados."""
        conn = sqlite3.connect(str(db_path))
        _insert_trade(conn, _MAGIC_RL_5000, 50.0)
        conn.close()

        rel = svc.gerar_relatorio("rl_5000", _MAGIC_RL_5000, _DATA_PADRAO, db_path)

        assert isinstance(rel, RelatorioFechamentoDiarioAgente)
        assert rel.schema_version == "1.0"
        assert rel.gerado_em  # não vazio
        # gerado_em deve ser ISO UTC
        datetime.fromisoformat(rel.gerado_em.replace("Z", "+00:00"))
        assert rel.drawdown_max_sessao >= 0.0

    def test_H5_gerar_markdown_cria_arquivo(
        self,
        svc: FechamentoDiarioAgenteService,
        db_path: Path,
        outputs_dir: Path,
    ) -> None:
        """H5: gerar_markdown deve criar arquivo .md no diretório informado."""
        conn = sqlite3.connect(str(db_path))
        _insert_trade(conn, _MAGIC_RL_5000, 100.0)
        conn.close()

        rel = svc.gerar_relatorio("rl_5000", _MAGIC_RL_5000, _DATA_PADRAO, db_path)
        md_path = svc.gerar_markdown(rel, outputs_dir)

        assert md_path.exists()
        assert md_path.suffix == ".md"
        content = md_path.read_text(encoding="utf-8")
        assert "rl_5000" in content
        assert _DATA_PADRAO in content


# ===========================================================================
# E — Cenários de Erro
# ===========================================================================


@pytest.mark.unit
class TestCenariosErro:
    """E1–E4: comportamentos de erro esperados."""

    def test_E1_banco_nao_encontrado_levanta_file_not_found(
        self, svc: FechamentoDiarioAgenteService, tmp_path: Path
    ) -> None:
        """E1: banco inexistente deve lançar FileNotFoundError."""
        db_inexistente = tmp_path / "nao_existe.db"

        with pytest.raises(FileNotFoundError):
            svc.gerar_relatorio("rl_5000", _MAGIC_RL_5000, _DATA_PADRAO, db_inexistente)

    def test_E2_magic_number_invalido_levanta_value_error(
        self, svc: FechamentoDiarioAgenteService, db_path: Path
    ) -> None:
        """E2: magic_number fora de AGENT_MAGIC_NUMBERS deve lançar ValueError."""
        with pytest.raises(ValueError, match="magic_number"):
            svc.gerar_relatorio("rl_5000", _MAGIC_INVALIDO, _DATA_PADRAO, db_path)

    def test_E3_data_futura_levanta_value_error(
        self, svc: FechamentoDiarioAgenteService, db_path: Path
    ) -> None:
        """E3: data futura deve lançar ValueError."""
        with pytest.raises(ValueError, match="data"):
            svc.gerar_relatorio("rl_5000", _MAGIC_RL_5000, _DATA_FUTURA, db_path)

    def test_E4_trades_com_profit_loss_null_sao_ignorados(
        self, svc: FechamentoDiarioAgenteService, db_path: Path
    ) -> None:
        """E4: trades com profit_loss=NULL devem ser ignorados pela query."""
        conn = sqlite3.connect(str(db_path))
        # 1 trade válido + 1 com NULL
        _insert_trade(conn, _MAGIC_RL_5000, 100.0)
        _insert_trade(conn, _MAGIC_RL_5000, None)  # deve ser ignorado
        conn.close()

        rel = svc.gerar_relatorio("rl_5000", _MAGIC_RL_5000, _DATA_PADRAO, db_path)

        # Somente 1 trade computado — o NULL é descartado pela query
        assert rel.total_trades == 1
        assert rel.pnl_total_reais == pytest.approx(100.0)


# ===========================================================================
# B — Cenários de Borda
# ===========================================================================


@pytest.mark.unit
class TestCenariosBorda:
    """B1–B5: limites e casos extremos."""

    def test_B1_exatamente_um_trade(
        self, svc: FechamentoDiarioAgenteService, db_path: Path
    ) -> None:
        """B1: exatamente 1 trade deve produzir relatório válido."""
        conn = sqlite3.connect(str(db_path))
        _insert_trade(conn, _MAGIC_RL_5000, 75.0, entry_time=f"{_DATA_PADRAO} 14:30:00")
        conn.close()

        rel = svc.gerar_relatorio("rl_5000", _MAGIC_RL_5000, _DATA_PADRAO, db_path)

        assert rel.total_trades == 1
        assert rel.win_rate == pytest.approx(1.0)
        assert rel.pnl_total_reais == pytest.approx(75.0)
        assert rel.horario_primeiro_trade == rel.horario_ultimo_trade

    def test_B1_zero_trades_retorna_neutro(
        self, svc: FechamentoDiarioAgenteService, db_path: Path
    ) -> None:
        """B1-ext: banco sem trades para a data → total_trades=0, status=NEUTRO."""
        rel = svc.gerar_relatorio("rl_5000", _MAGIC_RL_5000, _DATA_PADRAO, db_path)

        assert rel.total_trades == 0
        assert rel.win_rate == pytest.approx(0.0)
        assert rel.pnl_total_reais == pytest.approx(0.0)
        assert rel.status == "NEUTRO"
        assert rel.horario_primeiro_trade is None
        assert rel.horario_ultimo_trade is None

    def test_B2_todos_trades_perdas(
        self, svc: FechamentoDiarioAgenteService, db_path: Path
    ) -> None:
        """B2: todos os trades são perdas → win_rate=0.0."""
        conn = sqlite3.connect(str(db_path))
        for pnl, t in [(-50.0, "09:00:00"), (-30.0, "10:00:00")]:
            _insert_trade(conn, _MAGIC_RL_5000, pnl, entry_time=f"{_DATA_PADRAO} {t}")
        conn.close()

        rel = svc.gerar_relatorio("rl_5000", _MAGIC_RL_5000, _DATA_PADRAO, db_path)

        assert rel.win_rate == pytest.approx(0.0)
        assert rel.status == "DEFICITARIO"

    def test_B3_drawdown_maximo_calculado(
        self, svc: FechamentoDiarioAgenteService, db_path: Path
    ) -> None:
        """B3: sequência +100, -200, +50 → drawdown_max=200.0."""
        conn = sqlite3.connect(str(db_path))
        for pnl, t in [(100.0, "09:00:00"), (-200.0, "10:00:00"), (50.0, "11:00:00")]:
            _insert_trade(conn, _MAGIC_RL_5000, pnl, entry_time=f"{_DATA_PADRAO} {t}")
        conn.close()

        rel = svc.gerar_relatorio("rl_5000", _MAGIC_RL_5000, _DATA_PADRAO, db_path)

        assert rel.drawdown_max_sessao == pytest.approx(200.0)

    def test_B3_calcular_drawdown_max_helper(
        self, svc: FechamentoDiarioAgenteService
    ) -> None:
        """B3-unit: _calcular_drawdown_max com lista conhecida.

        O arquiteto especificou explicitamente este helper como parte do contrato
        público do service (ADR: method signature deve ser preservada).
        O teste direto do helper garante comportamento isolado do cálculo de drawdown,
        complementando o teste de integração via gerar_relatorio em test_B3_drawdown_maximo_calculado.
        """
        result = svc._calcular_drawdown_max([100.0, -200.0, 50.0])
        assert result == pytest.approx(200.0)

    def test_B3_drawdown_max_sem_perda_e_zero(
        self, svc: FechamentoDiarioAgenteService
    ) -> None:
        """B3-edge: sem perdas → drawdown_max=0.0."""
        result = svc._calcular_drawdown_max([100.0, 200.0, 50.0])
        assert result == pytest.approx(0.0)

    def test_B4_rl5000_e_rl_direto_independentes(
        self, svc: FechamentoDiarioAgenteService, db_path: Path
    ) -> None:
        """B4: RL_5000 e RL_DIRETO no mesmo banco devem ser totalmente isolados."""
        conn = sqlite3.connect(str(db_path))
        # RL_5000: 1 trade +300
        _insert_trade(conn, _MAGIC_RL_5000, 300.0, entry_time=f"{_DATA_PADRAO} 09:00:00")
        # RL_DIRETO: 2 trades -50, -70
        _insert_trade(conn, _MAGIC_RL_DIRETO, -50.0, entry_time=f"{_DATA_PADRAO} 09:05:00")
        _insert_trade(conn, _MAGIC_RL_DIRETO, -70.0, entry_time=f"{_DATA_PADRAO} 09:10:00")
        conn.close()

        rel_5000 = svc.gerar_relatorio("rl_5000", _MAGIC_RL_5000, _DATA_PADRAO, db_path)
        rel_direto = svc.gerar_relatorio(
            "rl_direto", _MAGIC_RL_DIRETO, _DATA_PADRAO, db_path
        )

        assert rel_5000.total_trades == 1
        assert rel_5000.pnl_total_reais == pytest.approx(300.0)
        assert rel_5000.status == "LUCRATIVO"

        assert rel_direto.total_trades == 2
        assert rel_direto.pnl_total_reais == pytest.approx(-120.0)
        assert rel_direto.status == "DEFICITARIO"

    def test_B5_gerar_markdown_sobrescreve_idempotente(
        self,
        svc: FechamentoDiarioAgenteService,
        db_path: Path,
        outputs_dir: Path,
    ) -> None:
        """B5: segunda chamada a gerar_markdown sobrescreve sem erro (idempotente)."""
        conn = sqlite3.connect(str(db_path))
        _insert_trade(conn, _MAGIC_RL_5000, 100.0)
        conn.close()

        rel = svc.gerar_relatorio("rl_5000", _MAGIC_RL_5000, _DATA_PADRAO, db_path)

        # Primeira geração
        md1 = svc.gerar_markdown(rel, outputs_dir)
        assert md1.exists()

        # Segunda geração — deve sobrescrever sem lançar exceção
        md2 = svc.gerar_markdown(rel, outputs_dir)
        assert md2 == md1
        assert md2.exists()


# ===========================================================================
# R — Regressão
# ===========================================================================


@pytest.mark.unit
class TestRegressao:
    """R1–R3: garantias de não-regressão contra componentes existentes."""

    def test_R1_agent_magic_numbers_correto(self) -> None:
        """R1: AGENT_MAGIC_NUMBERS deve conter rl_5000=234500 e rl_direto=234600."""
        from config.settings import AGENT_MAGIC_NUMBERS  # type: ignore[import]

        assert AGENT_MAGIC_NUMBERS["rl_5000"] == 234500
        assert AGENT_MAGIC_NUMBERS["rl_direto"] == 234600

    def test_R1_service_usa_settings_nao_hardcoded(
        self, svc: FechamentoDiarioAgenteService
    ) -> None:
        """R1: o service deve ler magic_numbers de config.settings (não hardcoded)."""
        import inspect
        import src.application.services.fechamento_diario_agente_service as mod

        source = inspect.getsource(mod)

        # 1) Garante que AGENT_MAGIC_NUMBERS é referenciado (importado de settings)
        assert "AGENT_MAGIC_NUMBERS" in source, (
            "Service deve referenciar AGENT_MAGIC_NUMBERS de config.settings"
        )

        # 2) Garante que valores literais de magic_number não estão hardcoded no módulo
        # (somente referências via AGENT_MAGIC_NUMBERS são aceitáveis)
        assert "234500" not in source, (
            "Magic number 234500 não deve aparecer hardcoded — use AGENT_MAGIC_NUMBERS"
        )
        assert "234600" not in source, (
            "Magic number 234600 não deve aparecer hardcoded — use AGENT_MAGIC_NUMBERS"
        )

    def test_R2_module_nao_quebra_pipeline_diarios_consolidator(self) -> None:
        """R2: importar o service não deve quebrar pipeline_diarios_consolidator."""
        # Se o pipeline_diarios_consolidator já está importado, re-importar
        # o service não deve invalidá-lo.
        from src.application.services import pipeline_diarios_consolidator  # noqa: F401
        from src.application.services import fechamento_diario_agente_service  # noqa: F401

        assert hasattr(pipeline_diarios_consolidator, "PipelineDiariosConsolidator")
        assert hasattr(
            fechamento_diario_agente_service, "FechamentoDiarioAgenteService"
        )

    def test_R3_nao_le_trading_diarios_db(
        self, svc: FechamentoDiarioAgenteService, tmp_path: Path
    ) -> None:
        """R3: service NÃO deve jamais ler trading_diarios.db — banco errado."""
        # Cria trading_diarios.db com dados que NÃO devem influenciar o resultado.
        diarios_db = tmp_path / "trading_diarios.db"
        conn_d = sqlite3.connect(str(diarios_db))
        conn_d.execute(_DDL_TRADES)
        conn_d.execute(
            "INSERT INTO trades (magic_number, side, entry_time, exit_time, "
            "profit_loss, status) VALUES (?, 'BUY', ?, ?, ?, 'CLOSED')",
            (_MAGIC_RL_5000, f"{_DATA_PADRAO} 09:00:00", f"{_DATA_PADRAO} 09:05:00", 9999.0),
        )
        conn_d.commit()
        conn_d.close()

        # Banco correto (trading.db) sem trades
        trading_db = tmp_path / "trading.db"
        conn_t = sqlite3.connect(str(trading_db))
        conn_t.execute(_DDL_TRADES)
        conn_t.commit()
        conn_t.close()

        # Service recebe o banco correto — resultado deve ser 0 trades,
        # ignorando totalmente trading_diarios.db mesmo que exista ao lado.
        rel = svc.gerar_relatorio("rl_5000", _MAGIC_RL_5000, _DATA_PADRAO, trading_db)
        assert rel.total_trades == 0, (
            "Service não deve ler trading_diarios.db — somente o db_path informado"
        )

    def test_R3_db_path_passado_explicitamente(
        self, svc: FechamentoDiarioAgenteService, db_path: Path
    ) -> None:
        """R3: db_path é parâmetro explícito — sem resolução implícita de caminho."""
        import inspect

        import src.application.services.fechamento_diario_agente_service as mod

        source = inspect.getsource(mod)
        # Garante que trading_diarios.db não é referenciado hardcoded
        assert "trading_diarios" not in source, (
            "Service não deve referenciar trading_diarios.db de forma hardcoded"
        )


# ===========================================================================
# Auxiliares de contrato de dataclass
# ===========================================================================


@pytest.mark.unit
class TestContratoRelatorio:
    """Valida o contrato da dataclass RelatorioFechamentoDiarioAgente."""

    def test_relatorio_e_dataclass_com_campos_obrigatorios(self) -> None:
        """Dataclass deve aceitar instanciação com campos obrigatórios."""
        import dataclasses

        fields = {f.name for f in dataclasses.fields(RelatorioFechamentoDiarioAgente)}
        obrigatorios = {
            "session_id",
            "magic_number",
            "agent_name",
            "data",
            "total_trades",
            "win_rate",
            "pnl_total_reais",
            "drawdown_max_sessao",
            "horario_primeiro_trade",
            "horario_ultimo_trade",
            "status",
            "schema_version",
            "gerado_em",
        }
        assert obrigatorios.issubset(fields), (
            f"Campos ausentes na dataclass: {obrigatorios - fields}"
        )

    def test_relatorio_status_literal_valido(
        self, svc: FechamentoDiarioAgenteService, db_path: Path
    ) -> None:
        """status deve ser exclusivamente LUCRATIVO, DEFICITARIO ou NEUTRO."""
        conn = sqlite3.connect(str(db_path))
        _insert_trade(conn, _MAGIC_RL_5000, 50.0)
        conn.close()

        rel = svc.gerar_relatorio("rl_5000", _MAGIC_RL_5000, _DATA_PADRAO, db_path)

        assert rel.status in {"LUCRATIVO", "DEFICITARIO", "NEUTRO"}

    def test_relatorio_win_rate_entre_zero_e_um(
        self, svc: FechamentoDiarioAgenteService, db_path: Path
    ) -> None:
        """win_rate deve estar no intervalo [0.0, 1.0]."""
        conn = sqlite3.connect(str(db_path))
        for pnl, t in [(100.0, "09:00:00"), (-50.0, "10:00:00")]:
            _insert_trade(conn, _MAGIC_RL_5000, pnl, entry_time=f"{_DATA_PADRAO} {t}")
        conn.close()

        rel = svc.gerar_relatorio("rl_5000", _MAGIC_RL_5000, _DATA_PADRAO, db_path)

        assert 0.0 <= rel.win_rate <= 1.0

    def test_relatorio_drawdown_nao_negativo(
        self, svc: FechamentoDiarioAgenteService, db_path: Path
    ) -> None:
        """drawdown_max_sessao deve ser >= 0."""
        conn = sqlite3.connect(str(db_path))
        _insert_trade(conn, _MAGIC_RL_5000, 100.0)
        conn.close()

        rel = svc.gerar_relatorio("rl_5000", _MAGIC_RL_5000, _DATA_PADRAO, db_path)

        assert rel.drawdown_max_sessao >= 0.0
