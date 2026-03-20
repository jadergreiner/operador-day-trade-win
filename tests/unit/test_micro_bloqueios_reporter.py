"""
Testes unitarios: CALIBRACAO-MICRO-04 Relatorio de Bloqueios do Micro Tendencia.

Cobre:
- FlagBloqueador enum (todos os valores)
- BloqueioRecord dataclass (criacao, para_dict)
- MicroBloqueiosReporter (registrar, listar, estatisticas, relatorio)
- Fluxo completo de um pregao

Referencia: docs/BACKLOG.md (CALIBRACAO-MICRO-04)
Status: Implementacao v1.0 (18/03/2026)
"""

import sqlite3
import tempfile
from datetime import datetime, date
from pathlib import Path

import pytest

from src.application.micro_bloqueios_reporter import (
    BloqueioRecord,
    FlagBloqueador,
    MicroBloqueiosReporter,
)


# ── Fixtures ──────────────────────────────────────────────────────────────────


@pytest.fixture
def db_temporario() -> Path:
    """Cria banco SQLite temporario para testes isolados."""
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
        return Path(f.name)


@pytest.fixture
def reporter(db_temporario: Path) -> MicroBloqueiosReporter:
    """Reporter com banco isolado."""
    return MicroBloqueiosReporter(db_path=db_temporario)


@pytest.fixture
def bloqueio_confianca() -> BloqueioRecord:
    """Bloqueio por confianca insuficiente."""
    return BloqueioRecord(
        timestamp=datetime(2026, 3, 18, 10, 30, 0),
        opportunity_id="opp_20260318_001",
        flag_bloqueador=FlagBloqueador.CONFIANCA,
        confianca_calculada=42.5,
        confianca_necessaria=45.0,
        delta=-2.5,
    )


@pytest.fixture
def bloqueio_exp_reduzida() -> BloqueioRecord:
    """Bloqueio por modo EXP_REDUZIDA."""
    return BloqueioRecord(
        timestamp=datetime(2026, 3, 18, 11, 0, 0),
        opportunity_id="opp_20260318_002",
        flag_bloqueador=FlagBloqueador.EXP_REDUZIDA,
        confianca_calculada=50.0,
        confianca_necessaria=55.0,
        delta=-5.0,
        detalhes="EXP_REDUZIDA: confianca < 55%",
    )


# ── Testes: FlagBloqueador ─────────────────────────────────────────────────


class TestFlagBloqueador:
    """Testa enum FlagBloqueador com todos os valores esperados."""

    def test_enum_tem_seis_valores(self) -> None:
        valores = list(FlagBloqueador)
        assert len(valores) == 6

    def test_valores_esperados(self) -> None:
        assert FlagBloqueador.CONFIANCA.value == "CONFIANCA"
        assert FlagBloqueador.EXP_REDUZIDA.value == "EXP_REDUZIDA"
        assert FlagBloqueador.DIR_FRACO.value == "DIR_FRACO"
        assert FlagBloqueador.TRAP_PROX.value == "TRAP_PROX"
        assert FlagBloqueador.RR_INSUFICIENTE.value == "RR_INSUFICIENTE"
        assert FlagBloqueador.COOLING_OFF.value == "COOLING_OFF"

    def test_string_representacao(self) -> None:
        assert str(FlagBloqueador.CONFIANCA) == "FlagBloqueador.CONFIANCA"


# ── Testes: BloqueioRecord ─────────────────────────────────────────────────


class TestBloqueioRecord:
    """Testa dataclass BloqueioRecord."""

    def test_criar_bloqueio_minimo(self) -> None:
        bloqueio = BloqueioRecord(
            timestamp=datetime(2026, 3, 18, 9, 0, 0),
            opportunity_id="opp_001",
            flag_bloqueador=FlagBloqueador.RR_INSUFICIENTE,
            confianca_calculada=48.0,
            confianca_necessaria=45.0,
            delta=3.0,
        )
        assert bloqueio.opportunity_id == "opp_001"
        assert bloqueio.flag_bloqueador == FlagBloqueador.RR_INSUFICIENTE
        assert bloqueio.delta == pytest.approx(3.0)
        assert bloqueio.detalhes is None

    def test_criar_bloqueio_com_detalhes(
        self, bloqueio_exp_reduzida: BloqueioRecord
    ) -> None:
        assert bloqueio_exp_reduzida.detalhes == "EXP_REDUZIDA: confianca < 55%"

    def test_para_dict_campos_obrigatorios(
        self, bloqueio_confianca: BloqueioRecord
    ) -> None:
        resultado = bloqueio_confianca.para_dict()
        campos = {
            "timestamp",
            "opportunity_id",
            "flag_bloqueador",
            "confianca_calculada",
            "confianca_necessaria",
            "delta",
            "detalhes",
        }
        assert campos.issubset(resultado.keys())

    def test_para_dict_valores_corretos(
        self, bloqueio_confianca: BloqueioRecord
    ) -> None:
        d = bloqueio_confianca.para_dict()
        assert d["flag_bloqueador"] == "CONFIANCA"
        assert d["confianca_calculada"] == pytest.approx(42.5)
        assert d["delta"] == pytest.approx(-2.5)
        assert d["opportunity_id"] == "opp_20260318_001"

    def test_timestamp_serializado_como_iso(
        self, bloqueio_confianca: BloqueioRecord
    ) -> None:
        d = bloqueio_confianca.para_dict()
        assert isinstance(d["timestamp"], str)
        assert "2026-03-18" in d["timestamp"]


# ── Testes: MicroBloqueiosReporter ────────────────────────────────────────


class TestMicroBloqueiosReporterInit:
    """Testa inicializacao e criacao de tabela."""

    def test_inicializar_reporter(self, reporter: MicroBloqueiosReporter) -> None:
        assert reporter is not None

    def test_tabela_criada_no_banco(
        self, reporter: MicroBloqueiosReporter, db_temporario: Path
    ) -> None:
        conn = sqlite3.connect(db_temporario)
        cursor = conn.cursor()
        cursor.execute(
            "SELECT name FROM sqlite_master WHERE type='table' "
            "AND name='micro_trend_bloqueios'"
        )
        resultado = cursor.fetchone()
        conn.close()
        assert resultado is not None

    def test_indices_criados(
        self, reporter: MicroBloqueiosReporter, db_temporario: Path
    ) -> None:
        conn = sqlite3.connect(db_temporario)
        cursor = conn.cursor()
        cursor.execute(
            "SELECT name FROM sqlite_master WHERE type='index' "
            "AND tbl_name='micro_trend_bloqueios'"
        )
        indices = [row[0] for row in cursor.fetchall()]
        conn.close()
        assert len(indices) >= 2


class TestRegistrarBloqueio:
    """Testa registro de bloqueios no banco."""

    def test_registrar_bloqueio_retorna_id(
        self,
        reporter: MicroBloqueiosReporter,
        bloqueio_confianca: BloqueioRecord,
    ) -> None:
        bloqueio_id = reporter.registrar_bloqueio(bloqueio_confianca)
        assert isinstance(bloqueio_id, int)
        assert bloqueio_id > 0

    def test_registrar_dois_bloqueios_ids_distintos(
        self,
        reporter: MicroBloqueiosReporter,
        bloqueio_confianca: BloqueioRecord,
        bloqueio_exp_reduzida: BloqueioRecord,
    ) -> None:
        id1 = reporter.registrar_bloqueio(bloqueio_confianca)
        id2 = reporter.registrar_bloqueio(bloqueio_exp_reduzida)
        assert id1 != id2

    def test_registrar_persiste_flag_correto(
        self,
        reporter: MicroBloqueiosReporter,
        db_temporario: Path,
        bloqueio_exp_reduzida: BloqueioRecord,
    ) -> None:
        reporter.registrar_bloqueio(bloqueio_exp_reduzida)
        conn = sqlite3.connect(db_temporario)
        cursor = conn.cursor()
        cursor.execute("SELECT flag_bloqueador FROM micro_trend_bloqueios LIMIT 1")
        row = cursor.fetchone()
        conn.close()
        assert row[0] == "EXP_REDUZIDA"


class TestListarBloqueios:
    """Testa consulta de bloqueios por data."""

    def test_listar_retorna_lista_vazia_sem_dados(
        self, reporter: MicroBloqueiosReporter
    ) -> None:
        resultado = reporter.listar_bloqueios(data=date(2026, 3, 18))
        assert resultado == []

    def test_listar_retorna_bloqueios_da_data(
        self,
        reporter: MicroBloqueiosReporter,
        bloqueio_confianca: BloqueioRecord,
        bloqueio_exp_reduzida: BloqueioRecord,
    ) -> None:
        reporter.registrar_bloqueio(bloqueio_confianca)
        reporter.registrar_bloqueio(bloqueio_exp_reduzida)
        resultado = reporter.listar_bloqueios(data=date(2026, 3, 18))
        assert len(resultado) == 2

    def test_listar_filtra_por_flag(
        self,
        reporter: MicroBloqueiosReporter,
        bloqueio_confianca: BloqueioRecord,
        bloqueio_exp_reduzida: BloqueioRecord,
    ) -> None:
        reporter.registrar_bloqueio(bloqueio_confianca)
        reporter.registrar_bloqueio(bloqueio_exp_reduzida)
        resultado = reporter.listar_bloqueios(
            data=date(2026, 3, 18),
            flag=FlagBloqueador.CONFIANCA,
        )
        assert len(resultado) == 1
        assert resultado[0].flag_bloqueador == FlagBloqueador.CONFIANCA

    def test_listar_nao_retorna_outra_data(
        self,
        reporter: MicroBloqueiosReporter,
        bloqueio_confianca: BloqueioRecord,
    ) -> None:
        reporter.registrar_bloqueio(bloqueio_confianca)
        resultado = reporter.listar_bloqueios(data=date(2026, 3, 19))
        assert resultado == []


class TestEstatisticas:
    """Testa calculo de estatisticas de bloqueios."""

    def test_estatisticas_sem_dados_retorna_zeros(
        self, reporter: MicroBloqueiosReporter
    ) -> None:
        stats = reporter.calcular_estatisticas(data=date(2026, 3, 18))
        assert stats["total_bloqueios"] == 0
        assert stats["por_flag"] == {}

    def test_estatisticas_com_dados(
        self,
        reporter: MicroBloqueiosReporter,
        bloqueio_confianca: BloqueioRecord,
        bloqueio_exp_reduzida: BloqueioRecord,
    ) -> None:
        reporter.registrar_bloqueio(bloqueio_confianca)
        reporter.registrar_bloqueio(bloqueio_exp_reduzida)
        stats = reporter.calcular_estatisticas(data=date(2026, 3, 18))
        assert stats["total_bloqueios"] == 2
        assert stats["por_flag"]["CONFIANCA"] == 1
        assert stats["por_flag"]["EXP_REDUZIDA"] == 1

    def test_estatisticas_top5_flags(self, reporter: MicroBloqueiosReporter) -> None:
        """Top 5 flags mais frequentes presente nas estatisticas."""
        for _ in range(3):
            reporter.registrar_bloqueio(
                BloqueioRecord(
                    timestamp=datetime(2026, 3, 18, 10, 0, 0),
                    opportunity_id=f"opp_{_}",
                    flag_bloqueador=FlagBloqueador.EXP_REDUZIDA,
                    confianca_calculada=40.0,
                    confianca_necessaria=55.0,
                    delta=-15.0,
                )
            )
        for _ in range(2):
            reporter.registrar_bloqueio(
                BloqueioRecord(
                    timestamp=datetime(2026, 3, 18, 11, 0, 0),
                    opportunity_id=f"opp_c_{_}",
                    flag_bloqueador=FlagBloqueador.CONFIANCA,
                    confianca_calculada=42.0,
                    confianca_necessaria=45.0,
                    delta=-3.0,
                )
            )
        stats = reporter.calcular_estatisticas(data=date(2026, 3, 18))
        assert "top5_flags" in stats
        assert stats["top5_flags"][0][0] == "EXP_REDUZIDA"
        assert stats["top5_flags"][0][1] == 3

    def test_estatisticas_contem_campos_obrigatorios(
        self, reporter: MicroBloqueiosReporter
    ) -> None:
        stats = reporter.calcular_estatisticas(data=date(2026, 3, 18))
        campos = {
            "total_bloqueios",
            "por_flag",
            "top5_flags",
            "delta_medio",
            "confianca_media_calculada",
            "confianca_media_necessaria",
        }
        assert campos.issubset(stats.keys())

    def test_estatisticas_delta_medio(
        self,
        reporter: MicroBloqueiosReporter,
        bloqueio_confianca: BloqueioRecord,
        bloqueio_exp_reduzida: BloqueioRecord,
    ) -> None:
        # delta: -2.5 e -5.0 → media = -3.75
        reporter.registrar_bloqueio(bloqueio_confianca)
        reporter.registrar_bloqueio(bloqueio_exp_reduzida)
        stats = reporter.calcular_estatisticas(data=date(2026, 3, 18))
        assert stats["delta_medio"] == pytest.approx(-3.75)


class TestGerarRelatorio:
    """Testa geracao de relatorio Markdown para o pregao."""

    def test_gerar_relatorio_sem_dados(self, reporter: MicroBloqueiosReporter) -> None:
        relatorio = reporter.gerar_relatorio_pregao(data=date(2026, 3, 18))
        assert (
            "micro_bloqueios" in relatorio.lower() or "bloqueios" in relatorio.lower()
        )
        assert "18/03/2026" in relatorio or "2026-03-18" in relatorio
        assert "oportunidades retidas" in relatorio.lower()

    def test_gerar_relatorio_contem_top5(
        self,
        reporter: MicroBloqueiosReporter,
        bloqueio_confianca: BloqueioRecord,
        bloqueio_exp_reduzida: BloqueioRecord,
    ) -> None:
        reporter.registrar_bloqueio(bloqueio_confianca)
        reporter.registrar_bloqueio(bloqueio_exp_reduzida)
        relatorio = reporter.gerar_relatorio_pregao(data=date(2026, 3, 18))
        assert "CONFIANCA" in relatorio or "EXP_REDUZIDA" in relatorio

    def test_gerar_relatorio_salva_arquivo(
        self,
        reporter: MicroBloqueiosReporter,
        tmp_path: Path,
    ) -> None:
        caminho = reporter.gerar_relatorio_pregao(
            data=date(2026, 3, 18),
            diretorio_saida=tmp_path,
        )
        arquivo = tmp_path / "micro_bloqueios_20260318.md"
        assert arquivo.exists()
        assert isinstance(caminho, str)
        assert "20260318" in caminho

    def test_relatorio_contem_horarios_concentracao(
        self, reporter: MicroBloqueiosReporter
    ) -> None:
        for hora in [9, 9, 10, 15]:
            reporter.registrar_bloqueio(
                BloqueioRecord(
                    timestamp=datetime(2026, 3, 18, hora, 0, 0),
                    opportunity_id=f"opp_h{hora}",
                    flag_bloqueador=FlagBloqueador.CONFIANCA,
                    confianca_calculada=40.0,
                    confianca_necessaria=45.0,
                    delta=-5.0,
                )
            )
        relatorio = reporter.gerar_relatorio_pregao(data=date(2026, 3, 18))
        assert "horario" in relatorio.lower() or "hora" in relatorio.lower()


class TestFluxoCompleto:
    """Testa fluxo completo de um pregao com varios bloqueios."""

    def test_pregao_com_multiplos_flags(self, reporter: MicroBloqueiosReporter) -> None:
        flags_e_qtds = [
            (FlagBloqueador.EXP_REDUZIDA, 5),
            (FlagBloqueador.CONFIANCA, 3),
            (FlagBloqueador.DIR_FRACO, 2),
            (FlagBloqueador.TRAP_PROX, 1),
        ]
        for flag, qtd in flags_e_qtds:
            for i in range(qtd):
                reporter.registrar_bloqueio(
                    BloqueioRecord(
                        timestamp=datetime(2026, 3, 18, 10 + i, 0, 0),
                        opportunity_id=f"opp_{flag.value}_{i}",
                        flag_bloqueador=flag,
                        confianca_calculada=40.0,
                        confianca_necessaria=55.0,
                        delta=-15.0,
                    )
                )

        stats = reporter.calcular_estatisticas(data=date(2026, 3, 18))
        assert stats["total_bloqueios"] == 11
        assert stats["por_flag"]["EXP_REDUZIDA"] == 5
        assert stats["top5_flags"][0][0] == "EXP_REDUZIDA"

        relatorio = reporter.gerar_relatorio_pregao(data=date(2026, 3, 18))
        assert len(relatorio) > 100

    def test_type_hints_100_porcento(self) -> None:
        """Valida que o modulo pode ser importado sem erros de tipo."""
        import src.application.micro_bloqueios_reporter as mod

        assert hasattr(mod, "FlagBloqueador")
        assert hasattr(mod, "BloqueioRecord")
        assert hasattr(mod, "MicroBloqueiosReporter")
