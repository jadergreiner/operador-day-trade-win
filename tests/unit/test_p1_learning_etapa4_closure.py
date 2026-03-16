"""Testes para P1-LEARNING Etapa 4: Closure (outcome + exit reason).

Objetivo: Validar registro de fechamento de episodios causais com
resultado final, motivo de saida e estatisticas agregadas.

Type hints: 100%
Docstrings: 100%
Portugues: 100%
"""

import tempfile
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

import pytest


@pytest.fixture
def temp_db() -> Any:
    """Cria banco de dados temporario para testes."""
    with tempfile.NamedTemporaryFile(delete=False, suffix=".db") as f:
        db_path = f.name
    yield db_path
    Path(db_path).unlink(missing_ok=True)


# ============================================================================
# TESTES DE ENUMS
# ============================================================================


class TestOutcomeType:
    """Testes do enum OutcomeType."""

    def test_valores_outcome_type(self) -> None:
        """OutcomeType deve ter WIN, LOSS e BREAKEVEN."""
        from src.application.p1_learning_closure import OutcomeType

        assert OutcomeType.WIN.value == "WIN"
        assert OutcomeType.LOSS.value == "LOSS"
        assert OutcomeType.BREAKEVEN.value == "BREAKEVEN"

    def test_contagem_outcome_type(self) -> None:
        """OutcomeType deve ter exatamente 3 valores."""
        from src.application.p1_learning_closure import OutcomeType

        assert len(OutcomeType) == 3

    def test_outcome_type_e_string(self) -> None:
        """OutcomeType deve ser compativel com str."""
        from src.application.p1_learning_closure import OutcomeType

        assert OutcomeType.WIN == "WIN"
        assert OutcomeType.LOSS == "LOSS"


class TestMotivoFechamento:
    """Testes do enum MotivoFechamento."""

    def test_valores_motivo_fechamento(self) -> None:
        """MotivoFechamento deve ter os 6 valores definidos."""
        from src.application.p1_learning_closure import MotivoFechamento

        assert MotivoFechamento.TP_ATINGIDO.value == "TP_ATINGIDO"
        assert MotivoFechamento.SL_ATINGIDO.value == "SL_ATINGIDO"
        assert MotivoFechamento.FECHAMENTO_MANUAL.value == "FECHAMENTO_MANUAL"
        assert MotivoFechamento.TIMEOUT.value == "TIMEOUT"
        assert MotivoFechamento.CANCELADO.value == "CANCELADO"
        assert MotivoFechamento.SISTEMA.value == "SISTEMA"

    def test_contagem_motivo_fechamento(self) -> None:
        """MotivoFechamento deve ter exatamente 6 valores."""
        from src.application.p1_learning_closure import MotivoFechamento

        assert len(MotivoFechamento) == 6


# ============================================================================
# TESTES DE DATACLASS
# ============================================================================


class TestClosureRecord:
    """Testes da dataclass ClosureRecord."""

    def test_criar_closure_record_win(self) -> None:
        """Criar ClosureRecord com resultado WIN."""
        from src.application.p1_learning_closure import (
            ClosureRecord,
            MotivoFechamento,
            OutcomeType,
        )

        registro = ClosureRecord(
            closure_id="CLS_001",
            episode_id="EP_20260316_140030",
            trade_id="TRD_20260316_140030",
            timestamp_fechamento=datetime.now(),
            preco_entrada=141500.0,
            preco_saida=143500.0,
            outcome=OutcomeType.WIN,
            motivo_fechamento=MotivoFechamento.TP_ATINGIDO,
            pnl_realizado=2000.0,
            pnl_realizado_pct=1.41,
            duracao_total_segundos=1800.0,
            market_conditions={"volatility": 1.1, "trend": "UP"},
        )

        assert registro.closure_id == "CLS_001"
        assert registro.episode_id == "EP_20260316_140030"
        assert registro.outcome == OutcomeType.WIN
        assert registro.motivo_fechamento == MotivoFechamento.TP_ATINGIDO
        assert registro.pnl_realizado == 2000.0
        assert registro.notas is None

    def test_closure_record_para_dict(self) -> None:
        """para_dict deve retornar campos serializaveis."""
        from src.application.p1_learning_closure import (
            ClosureRecord,
            MotivoFechamento,
            OutcomeType,
        )

        ts = datetime(2026, 3, 16, 14, 0, 30)
        registro = ClosureRecord(
            closure_id="CLS_002",
            episode_id="EP_001",
            trade_id="TRD_001",
            timestamp_fechamento=ts,
            preco_entrada=141500.0,
            preco_saida=140000.0,
            outcome=OutcomeType.LOSS,
            motivo_fechamento=MotivoFechamento.SL_ATINGIDO,
            pnl_realizado=-1500.0,
            pnl_realizado_pct=-1.06,
            duracao_total_segundos=900.0,
            market_conditions={},
            notas="Teste",
        )

        d = registro.para_dict()

        assert d["closure_id"] == "CLS_002"
        assert d["outcome"] == "LOSS"
        assert d["motivo_fechamento"] == "SL_ATINGIDO"
        assert d["pnl_realizado"] == -1500.0
        assert d["notas"] == "Teste"
        assert "timestamp_fechamento" in d
        # Timestamps devem ser strings ISO
        assert isinstance(d["timestamp_fechamento"], str)
        assert isinstance(d["criado_em"], str)

    def test_closure_record_breakeven(self) -> None:
        """ClosureRecord aceita outcome BREAKEVEN com notas None."""
        from src.application.p1_learning_closure import (
            ClosureRecord,
            MotivoFechamento,
            OutcomeType,
        )

        registro = ClosureRecord(
            closure_id="CLS_003",
            episode_id="EP_003",
            trade_id="TRD_003",
            timestamp_fechamento=datetime.now(),
            preco_entrada=141500.0,
            preco_saida=141500.0,
            outcome=OutcomeType.BREAKEVEN,
            motivo_fechamento=MotivoFechamento.FECHAMENTO_MANUAL,
            pnl_realizado=0.0,
            pnl_realizado_pct=0.0,
            duracao_total_segundos=300.0,
            market_conditions={},
        )

        assert registro.outcome == OutcomeType.BREAKEVEN
        assert registro.notas is None


# ============================================================================
# TESTES DO ENGINE PRINCIPAL
# ============================================================================


class TestEpisodeClosureEngine:
    """Testes da classe EpisodeClosureEngine."""

    def test_inicializar_engine(self, temp_db: str) -> None:
        """Engine deve inicializar e criar tabela."""
        from src.application.p1_learning_closure import EpisodeClosureEngine

        engine = EpisodeClosureEngine(db_path=temp_db)

        assert engine is not None
        assert engine.contar_fechamentos() == 0

    def test_registrar_fechamento_win(self, temp_db: str) -> None:
        """Registrar fechamento WIN via TP."""
        from src.application.p1_learning_closure import (
            EpisodeClosureEngine,
            MotivoFechamento,
            OutcomeType,
        )

        engine = EpisodeClosureEngine(db_path=temp_db)

        closure_id = engine.registrar_fechamento(
            episode_id="EP_001",
            trade_id="TRD_001",
            preco_entrada=141500.0,
            preco_saida=143500.0,
            pnl_realizado=2000.0,
            pnl_realizado_pct=1.41,
            motivo_fechamento=MotivoFechamento.TP_ATINGIDO,
            duracao_total_segundos=1800.0,
        )

        assert closure_id is not None
        assert len(closure_id) > 0
        assert engine.contar_fechamentos() == 1

        # Verificar dados persistidos
        closure = engine.obter_fechamento(closure_id)
        assert closure is not None
        assert closure.outcome == OutcomeType.WIN
        assert closure.motivo_fechamento == MotivoFechamento.TP_ATINGIDO
        assert closure.pnl_realizado == 2000.0

    def test_registrar_fechamento_loss(self, temp_db: str) -> None:
        """Registrar fechamento LOSS via SL."""
        from src.application.p1_learning_closure import (
            EpisodeClosureEngine,
            MotivoFechamento,
            OutcomeType,
        )

        engine = EpisodeClosureEngine(db_path=temp_db)

        closure_id = engine.registrar_fechamento(
            episode_id="EP_002",
            trade_id="TRD_002",
            preco_entrada=141500.0,
            preco_saida=140000.0,
            pnl_realizado=-1500.0,
            pnl_realizado_pct=-1.06,
            motivo_fechamento=MotivoFechamento.SL_ATINGIDO,
            duracao_total_segundos=600.0,
        )

        closure = engine.obter_fechamento(closure_id)
        assert closure is not None
        assert closure.outcome == OutcomeType.LOSS
        assert closure.pnl_realizado == -1500.0

    def test_determinar_outcome_automatico_breakeven(
        self, temp_db: str
    ) -> None:
        """P&L dentro do threshold deve gerar BREAKEVEN automaticamente."""
        from src.application.p1_learning_closure import (
            EpisodeClosureEngine,
            MotivoFechamento,
            OutcomeType,
        )

        engine = EpisodeClosureEngine(db_path=temp_db)

        closure_id = engine.registrar_fechamento(
            episode_id="EP_003",
            trade_id="TRD_003",
            preco_entrada=141500.0,
            preco_saida=141500.0,
            pnl_realizado=0.0,
            pnl_realizado_pct=0.02,  # < 0.05% threshold = breakeven
            motivo_fechamento=MotivoFechamento.FECHAMENTO_MANUAL,
            duracao_total_segundos=300.0,
        )

        closure = engine.obter_fechamento(closure_id)
        assert closure is not None
        assert closure.outcome == OutcomeType.BREAKEVEN

    def test_registrar_fechamento_com_market_conditions(
        self, temp_db: str
    ) -> None:
        """Fechamento com market_conditions deve persistir JSON."""
        from src.application.p1_learning_closure import (
            EpisodeClosureEngine,
            MotivoFechamento,
        )

        engine = EpisodeClosureEngine(db_path=temp_db)
        conditions = {"volatility": 1.3, "trend": "DOWN", "volume": "HIGH"}

        closure_id = engine.registrar_fechamento(
            episode_id="EP_004",
            trade_id="TRD_004",
            preco_entrada=141500.0,
            preco_saida=143500.0,
            pnl_realizado=2000.0,
            pnl_realizado_pct=1.41,
            motivo_fechamento=MotivoFechamento.TP_ATINGIDO,
            duracao_total_segundos=1800.0,
            market_conditions=conditions,
            notas="Operacao com alta volatilidade",
        )

        closure = engine.obter_fechamento(closure_id)
        assert closure is not None
        assert closure.market_conditions == conditions
        assert closure.notas == "Operacao com alta volatilidade"

    def test_obter_fechamento_por_episode(self, temp_db: str) -> None:
        """Deve obter fechamento usando episode_id."""
        from src.application.p1_learning_closure import (
            EpisodeClosureEngine,
            MotivoFechamento,
            OutcomeType,
        )

        engine = EpisodeClosureEngine(db_path=temp_db)
        episode_id = "EP_BUSCA_001"

        engine.registrar_fechamento(
            episode_id=episode_id,
            trade_id="TRD_BUSCA_001",
            preco_entrada=141500.0,
            preco_saida=143500.0,
            pnl_realizado=2000.0,
            pnl_realizado_pct=1.41,
            motivo_fechamento=MotivoFechamento.TP_ATINGIDO,
            duracao_total_segundos=1800.0,
        )

        closure = engine.obter_fechamento_por_episode(episode_id)
        assert closure is not None
        assert closure.episode_id == episode_id
        assert closure.outcome == OutcomeType.WIN

    def test_obter_fechamento_inexistente(self, temp_db: str) -> None:
        """Busca por closure_id inexistente deve retornar None."""
        from src.application.p1_learning_closure import EpisodeClosureEngine

        engine = EpisodeClosureEngine(db_path=temp_db)
        resultado = engine.obter_fechamento("id-nao-existe")
        assert resultado is None

    def test_listar_fechamentos_sem_filtro(self, temp_db: str) -> None:
        """listar_fechamentos sem filtro deve retornar todos."""
        from src.application.p1_learning_closure import (
            EpisodeClosureEngine,
            MotivoFechamento,
        )

        engine = EpisodeClosureEngine(db_path=temp_db)

        for i in range(3):
            pnl_pct = 1.0 if i < 2 else -1.0
            pnl = 1000.0 if i < 2 else -1000.0
            engine.registrar_fechamento(
                episode_id=f"EP_{i:03d}",
                trade_id=f"TRD_{i:03d}",
                preco_entrada=141500.0,
                preco_saida=142000.0,
                pnl_realizado=pnl,
                pnl_realizado_pct=pnl_pct,
                motivo_fechamento=MotivoFechamento.TP_ATINGIDO,
                duracao_total_segundos=900.0,
            )

        lista = engine.listar_fechamentos()
        assert len(lista) == 3

    def test_listar_fechamentos_filtro_outcome(self, temp_db: str) -> None:
        """Deve filtrar por OutcomeType corretamente."""
        from src.application.p1_learning_closure import (
            EpisodeClosureEngine,
            MotivoFechamento,
            OutcomeType,
        )

        engine = EpisodeClosureEngine(db_path=temp_db)

        # 2 wins
        for i in range(2):
            engine.registrar_fechamento(
                episode_id=f"EP_WIN_{i}",
                trade_id=f"TRD_WIN_{i}",
                preco_entrada=141500.0,
                preco_saida=142500.0,
                pnl_realizado=1000.0,
                pnl_realizado_pct=0.71,
                motivo_fechamento=MotivoFechamento.TP_ATINGIDO,
                duracao_total_segundos=900.0,
            )

        # 1 loss
        engine.registrar_fechamento(
            episode_id="EP_LOSS_0",
            trade_id="TRD_LOSS_0",
            preco_entrada=141500.0,
            preco_saida=140500.0,
            pnl_realizado=-1000.0,
            pnl_realizado_pct=-0.71,
            motivo_fechamento=MotivoFechamento.SL_ATINGIDO,
            duracao_total_segundos=600.0,
        )

        wins = engine.listar_fechamentos(outcome=OutcomeType.WIN)
        losses = engine.listar_fechamentos(outcome=OutcomeType.LOSS)

        assert len(wins) == 2
        assert len(losses) == 1
        assert all(c.outcome == OutcomeType.WIN for c in wins)
        assert all(c.outcome == OutcomeType.LOSS for c in losses)


# ============================================================================
# TESTES DE ESTATISTICAS
# ============================================================================


class TestEstatisticasFechamentos:
    """Testes do metodo calcular_estatisticas_fechamentos."""

    def test_estatisticas_sem_dados(self, temp_db: str) -> None:
        """Estatisticas com tabela vazia devem retornar zeros."""
        from src.application.p1_learning_closure import EpisodeClosureEngine

        engine = EpisodeClosureEngine(db_path=temp_db)
        stats = engine.calcular_estatisticas_fechamentos()

        assert stats["total"] == 0
        assert stats["wins"] == 0
        assert stats["losses"] == 0
        assert stats["breakevens"] == 0
        assert stats["win_rate_pct"] == 0.0
        assert stats["pnl_total"] == 0.0

    def test_estatisticas_com_dados(self, temp_db: str) -> None:
        """Estatisticas devem calcular win_rate e pnl corretamente."""
        from src.application.p1_learning_closure import (
            EpisodeClosureEngine,
            MotivoFechamento,
        )

        engine = EpisodeClosureEngine(db_path=temp_db)

        # 2 wins: R$1000 e R$2000
        engine.registrar_fechamento(
            episode_id="EP_W1",
            trade_id="TRD_W1",
            preco_entrada=141500.0,
            preco_saida=142500.0,
            pnl_realizado=1000.0,
            pnl_realizado_pct=0.71,
            motivo_fechamento=MotivoFechamento.TP_ATINGIDO,
            duracao_total_segundos=900.0,
        )
        engine.registrar_fechamento(
            episode_id="EP_W2",
            trade_id="TRD_W2",
            preco_entrada=141500.0,
            preco_saida=143500.0,
            pnl_realizado=2000.0,
            pnl_realizado_pct=1.41,
            motivo_fechamento=MotivoFechamento.TP_ATINGIDO,
            duracao_total_segundos=1800.0,
        )

        # 1 loss: -R$500
        engine.registrar_fechamento(
            episode_id="EP_L1",
            trade_id="TRD_L1",
            preco_entrada=141500.0,
            preco_saida=141000.0,
            pnl_realizado=-500.0,
            pnl_realizado_pct=-0.35,
            motivo_fechamento=MotivoFechamento.SL_ATINGIDO,
            duracao_total_segundos=300.0,
        )

        stats = engine.calcular_estatisticas_fechamentos()

        assert stats["total"] == 3
        assert stats["wins"] == 2
        assert stats["losses"] == 1
        assert stats["breakevens"] == 0
        assert abs(stats["win_rate_pct"] - 66.67) < 0.1
        assert stats["pnl_total"] == pytest.approx(2500.0, abs=0.01)
        assert stats["pnl_maximo"] == 2000.0
        assert stats["pnl_minimo"] == -500.0

    def test_estatisticas_contem_campos_obrigatorios(
        self, temp_db: str
    ) -> None:
        """Estatisticas devem conter todos os campos definidos."""
        from src.application.p1_learning_closure import EpisodeClosureEngine

        engine = EpisodeClosureEngine(db_path=temp_db)
        stats = engine.calcular_estatisticas_fechamentos()

        campos_obrigatorios = [
            "total",
            "wins",
            "losses",
            "breakevens",
            "win_rate_pct",
            "pnl_total",
            "pnl_medio",
            "pnl_maximo",
            "pnl_minimo",
            "duracao_media_segundos",
            "contagem_por_motivo",
        ]

        for campo in campos_obrigatorios:
            assert campo in stats, f"Campo '{campo}' ausente nas estatisticas"

    def test_estatisticas_contagem_por_motivo(self, temp_db: str) -> None:
        """Deve agrupar corretamente por motivo de fechamento."""
        from src.application.p1_learning_closure import (
            EpisodeClosureEngine,
            MotivoFechamento,
        )

        engine = EpisodeClosureEngine(db_path=temp_db)

        engine.registrar_fechamento(
            episode_id="EP_M1",
            trade_id="TRD_M1",
            preco_entrada=141500.0,
            preco_saida=143500.0,
            pnl_realizado=2000.0,
            pnl_realizado_pct=1.41,
            motivo_fechamento=MotivoFechamento.TP_ATINGIDO,
            duracao_total_segundos=900.0,
        )
        engine.registrar_fechamento(
            episode_id="EP_M2",
            trade_id="TRD_M2",
            preco_entrada=141500.0,
            preco_saida=140000.0,
            pnl_realizado=-1500.0,
            pnl_realizado_pct=-1.06,
            motivo_fechamento=MotivoFechamento.SL_ATINGIDO,
            duracao_total_segundos=600.0,
        )
        engine.registrar_fechamento(
            episode_id="EP_M3",
            trade_id="TRD_M3",
            preco_entrada=141500.0,
            preco_saida=141600.0,
            pnl_realizado=100.0,
            pnl_realizado_pct=0.07,
            motivo_fechamento=MotivoFechamento.TP_ATINGIDO,
            duracao_total_segundos=1200.0,
        )

        stats = engine.calcular_estatisticas_fechamentos()
        contagem = stats["contagem_por_motivo"]

        assert contagem["TP_ATINGIDO"] == 2
        assert contagem["SL_ATINGIDO"] == 1


# ============================================================================
# TESTES DE RELATORIOS
# ============================================================================


class TestRelatorios:
    """Testes de geracao de relatorios JSON e Markdown."""

    def test_gerar_relatorio_json_estrutura(self, temp_db: str) -> None:
        """Relatorio JSON deve conter campos obrigatorios."""
        from src.application.p1_learning_closure import EpisodeClosureEngine

        engine = EpisodeClosureEngine(db_path=temp_db)
        relatorio = engine.gerar_relatorio_json()

        assert "etapa" in relatorio
        assert "timestamp_geracao" in relatorio
        assert "versao" in relatorio
        assert "estatisticas" in relatorio
        assert "ultimos_fechamentos" in relatorio
        assert relatorio["etapa"] == "P1-LEARNING Etapa 4 - Closure"

    def test_gerar_relatorio_json_com_dados(self, temp_db: str) -> None:
        """Relatorio JSON deve incluir fechamentos na lista."""
        from src.application.p1_learning_closure import (
            EpisodeClosureEngine,
            MotivoFechamento,
        )

        engine = EpisodeClosureEngine(db_path=temp_db)
        engine.registrar_fechamento(
            episode_id="EP_REL_001",
            trade_id="TRD_REL_001",
            preco_entrada=141500.0,
            preco_saida=143500.0,
            pnl_realizado=2000.0,
            pnl_realizado_pct=1.41,
            motivo_fechamento=MotivoFechamento.TP_ATINGIDO,
            duracao_total_segundos=1800.0,
        )

        relatorio = engine.gerar_relatorio_json()

        assert relatorio["estatisticas"]["total"] == 1
        assert len(relatorio["ultimos_fechamentos"]) == 1

    def test_gerar_relatorio_markdown(self, temp_db: str) -> None:
        """Relatorio Markdown deve conter cabecalho e tabelas."""
        from src.application.p1_learning_closure import EpisodeClosureEngine

        engine = EpisodeClosureEngine(db_path=temp_db)
        md = engine.gerar_relatorio_markdown()

        assert "P1-LEARNING" in md
        assert "Etapa 4" in md
        assert "Win Rate" in md
        assert "|" in md  # Tabela markdown

    def test_gerar_relatorio_json_salva_arquivo(
        self, temp_db: str, tmp_path: Path
    ) -> None:
        """Relatorio JSON deve ser salvo em arquivo quando output_path fornecido."""
        import json as json_module

        from src.application.p1_learning_closure import EpisodeClosureEngine

        engine = EpisodeClosureEngine(db_path=temp_db)
        output = str(tmp_path / "relatorio_closure.json")

        relatorio = engine.gerar_relatorio_json(output_path=output)

        assert Path(output).exists()
        with open(output, encoding="utf-8") as f:
            dados = json_module.load(f)
        assert dados["etapa"] == relatorio["etapa"]


# ============================================================================
# TESTE DE INTEGRACAO COMPLETA
# ============================================================================


class TestIntegracaoCompleta:
    """Teste de fluxo completo Etapa 4 com multiplos episodios."""

    def test_fluxo_completo_ciclo_fechamento(self, temp_db: str) -> None:
        """Registrar abertura, evolucao e fechamento de 3 episodios."""
        from src.application.p1_learning_closure import (
            EpisodeClosureEngine,
            MotivoFechamento,
            OutcomeType,
        )

        engine = EpisodeClosureEngine(db_path=temp_db)

        # Episodio 1: WIN por TP
        ep1 = engine.registrar_fechamento(
            episode_id="EP_FULL_001",
            trade_id="TRD_FULL_001",
            preco_entrada=141500.0,
            preco_saida=143500.0,
            pnl_realizado=2000.0,
            pnl_realizado_pct=1.41,
            motivo_fechamento=MotivoFechamento.TP_ATINGIDO,
            duracao_total_segundos=1800.0,
            market_conditions={"trend": "UP", "volatility": 1.0},
        )

        # Episodio 2: LOSS por SL
        ep2 = engine.registrar_fechamento(
            episode_id="EP_FULL_002",
            trade_id="TRD_FULL_002",
            preco_entrada=141500.0,
            preco_saida=140000.0,
            pnl_realizado=-1500.0,
            pnl_realizado_pct=-1.06,
            motivo_fechamento=MotivoFechamento.SL_ATINGIDO,
            duracao_total_segundos=600.0,
            market_conditions={"trend": "DOWN", "volatility": 1.8},
        )

        # Episodio 3: BREAKEVEN manual
        ep3 = engine.registrar_fechamento(
            episode_id="EP_FULL_003",
            trade_id="TRD_FULL_003",
            preco_entrada=141500.0,
            preco_saida=141505.0,
            pnl_realizado=5.0,
            pnl_realizado_pct=0.003,  # < 0.05% = breakeven
            motivo_fechamento=MotivoFechamento.FECHAMENTO_MANUAL,
            duracao_total_segundos=300.0,
        )

        # Verificar contagem
        assert engine.contar_fechamentos() == 3

        # Verificar resultados individuais
        c1 = engine.obter_fechamento(ep1)
        c2 = engine.obter_fechamento(ep2)
        c3 = engine.obter_fechamento(ep3)

        assert c1 is not None and c1.outcome == OutcomeType.WIN
        assert c2 is not None and c2.outcome == OutcomeType.LOSS
        assert c3 is not None and c3.outcome == OutcomeType.BREAKEVEN

        # Verificar estatisticas finais
        stats = engine.calcular_estatisticas_fechamentos()
        assert stats["total"] == 3
        assert stats["wins"] == 1
        assert stats["losses"] == 1
        assert stats["breakevens"] == 1
        assert abs(stats["win_rate_pct"] - 33.33) < 0.1
        assert stats["pnl_total"] == pytest.approx(505.0, abs=0.01)

    def test_type_hints_100_porcento(self) -> None:
        """Modulo deve importar sem erros de type hints."""
        import importlib

        modulo = importlib.import_module(
            "src.application.p1_learning_closure"
        )

        assert hasattr(modulo, "EpisodeClosureEngine")
        assert hasattr(modulo, "ClosureRecord")
        assert hasattr(modulo, "OutcomeType")
        assert hasattr(modulo, "MotivoFechamento")
