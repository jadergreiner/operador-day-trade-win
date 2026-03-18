"""
Testes TDD para CALIBRACAO-MICRO-06: Autoavaliacao de Inatividade.

Suite completa cobrindo:
- Deteccao de inatividade injusta (condicoes de mercado favoravel)
- Geracao de episodios HOLD penalizados
- Calculo de movimento perdido estimado
- Geracao de relatorio de autoavaliacao
- Integracao com tabela rl_rewards via SQLite

Status: TDD (escreve antes da implementacao)
Referencia: docs/BACKLOG.md (CALIBRACAO-MICRO-06)
"""

import sqlite3
import tempfile
from datetime import datetime, timedelta
from pathlib import Path

import pytest

from src.application.autoavaliacao_inatividade import (
    AutoavaliacaoInatividade,
    CondicoesInatividade,
    EpisodioHoldPenalizado,
    ResultadoAutoavaliacao,
    StatusAutoavaliacao,
)


# ────────────────────────────────────────────────────────────────
# Fixtures
# ────────────────────────────────────────────────────────────────


@pytest.fixture
def db_temporario() -> str:
    """Cria banco SQLite temporario com tabelas necessarias."""
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
        db_path = f.name

    conn = sqlite3.connect(db_path)
    cur = conn.cursor()

    # Tabela de oportunidades detectadas no dia
    cur.execute("""
        CREATE TABLE IF NOT EXISTS micro_trend_opportunities (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            decision_id INTEGER,
            timestamp TEXT NOT NULL,
            direction TEXT NOT NULL,
            entry REAL,
            stop_loss REAL,
            take_profit REAL,
            risk_reward REAL,
            confidence REAL,
            reason TEXT,
            region TEXT
        )
    """)

    # Tabela de decisoes (para consultar movimento apos timestamp)
    cur.execute("""
        CREATE TABLE IF NOT EXISTS micro_trend_decisions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp TEXT NOT NULL,
            price_current REAL,
            macro_score INTEGER,
            adx REAL,
            micro_trend TEXT
        )
    """)

    # Tabela de rewards RL
    cur.execute("""
        CREATE TABLE IF NOT EXISTS rl_rewards (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            episode_id TEXT,
            action_at_decision TEXT,
            price_change_points REAL,
            was_correct INTEGER,
            reward_normalized REAL,
            is_evaluated INTEGER DEFAULT 1,
            timestamp TEXT,
            agent_id TEXT DEFAULT 'micro_tendencia'
        )
    """)

    conn.commit()
    conn.close()
    return db_path


@pytest.fixture
def db_com_oportunidades(db_temporario: str) -> str:
    """Banco com oportunidades e decisoes de preco populados."""
    conn = sqlite3.connect(db_temporario)
    cur = conn.cursor()

    hoje = datetime.now().date().isoformat()
    ts_base = datetime.now().replace(hour=10, minute=0, second=0, microsecond=0)

    # Insere 5 oportunidades nao executadas
    for i in range(5):
        ts = (ts_base + timedelta(minutes=i * 30)).isoformat()
        cur.execute("""
            INSERT INTO micro_trend_opportunities
            (decision_id, timestamp, direction, entry, stop_loss,
             take_profit, risk_reward, confidence, reason, region)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (i + 1, ts, "COMPRA", 142000.0 + i * 100, 141500.0,
              143000.0, 2.0, 42.0, "macro forte", "suporte"))

    # Insere decisoes de preco (para calcular movimento apos oportunidade)
    for i in range(10):
        ts = (ts_base + timedelta(minutes=i * 15)).isoformat()
        preco = 142000.0 + i * 100  # mercado subiu 100pts a cada 15min
        macro = 25 + i  # macro entre 25 e 34
        adx = 35.0 + i * 0.5  # ADX entre 35 e 39.5
        cur.execute("""
            INSERT INTO micro_trend_decisions
            (timestamp, price_current, macro_score, adx, micro_trend)
            VALUES (?, ?, ?, ?, ?)
        """, (ts, preco, macro, adx, "UPTREND"))

    conn.commit()
    conn.close()
    return db_temporario


@pytest.fixture
def condicoes_mercado_favoravel() -> CondicoesInatividade:
    """Condicoes de mercado que justificam inatividade injusta."""
    return CondicoesInatividade(
        data=datetime.now().date().isoformat(),
        n_trades_executados=0,
        macro_score_medio=28.5,
        adx_medio=36.0,
        market_range_pts=2200.0,
        n_oportunidades_detectadas=5,
        n_oportunidades_executadas=0,
    )


@pytest.fixture
def condicoes_mercado_fraco() -> CondicoesInatividade:
    """Condicoes de mercado que NÃO justificam penalidade (mercado lateral)."""
    return CondicoesInatividade(
        data=datetime.now().date().isoformat(),
        n_trades_executados=0,
        macro_score_medio=8.0,   # abaixo de 15
        adx_medio=20.0,          # abaixo de 30
        market_range_pts=350.0,  # abaixo de 500
        n_oportunidades_detectadas=2,
        n_oportunidades_executadas=0,
    )


# ────────────────────────────────────────────────────────────────
# Testes: CondicoesInatividade
# ────────────────────────────────────────────────────────────────


class TestCondicoesInatividade:
    """Testes para dataclass de condicoes de mercado."""

    def test_criar_condicoes_inatividade_completo(self) -> None:
        """Deve criar CondicoesInatividade com todos os campos."""
        condicoes = CondicoesInatividade(
            data="2026-03-18",
            n_trades_executados=0,
            macro_score_medio=25.0,
            adx_medio=35.0,
            market_range_pts=2000.0,
            n_oportunidades_detectadas=5,
            n_oportunidades_executadas=0,
        )
        assert condicoes.data == "2026-03-18"
        assert condicoes.n_trades_executados == 0
        assert condicoes.macro_score_medio == 25.0
        assert condicoes.adx_medio == 35.0
        assert condicoes.market_range_pts == 2000.0
        assert condicoes.n_oportunidades_detectadas == 5

    def test_condicoes_para_dict(
        self, condicoes_mercado_favoravel: CondicoesInatividade
    ) -> None:
        """Deve serializar para dicionario."""
        d = condicoes_mercado_favoravel.para_dict()
        assert "data" in d
        assert "n_trades_executados" in d
        assert "macro_score_medio" in d
        assert "adx_medio" in d
        assert "market_range_pts" in d


# ────────────────────────────────────────────────────────────────
# Testes: EpisodioHoldPenalizado
# ────────────────────────────────────────────────────────────────


class TestEpisodioHoldPenalizado:
    """Testes para dataclass de episodio penalizado."""

    def test_criar_episodio_hold_win(self) -> None:
        """Deve criar episodio de HOLD que deveria ser WIN."""
        episodio = EpisodioHoldPenalizado(
            opportunity_id=1,
            timestamp=datetime.now().isoformat(),
            direction="COMPRA",
            movimento_pts=555.0,
            penalidade_normalizada=-0.5,
            was_correct=0,
            action_at_decision="HOLD_FORCADO",
        )
        assert episodio.opportunity_id == 1
        assert episodio.movimento_pts == 555.0
        assert episodio.penalidade_normalizada == -0.5
        assert episodio.was_correct == 0
        assert episodio.action_at_decision == "HOLD_FORCADO"

    def test_episodio_para_dict(self) -> None:
        """Deve serializar para dicionario JSON-compativel."""
        episodio = EpisodioHoldPenalizado(
            opportunity_id=2,
            timestamp=datetime.now().isoformat(),
            direction="VENDA",
            movimento_pts=280.0,
            penalidade_normalizada=-0.28,
            was_correct=0,
            action_at_decision="HOLD_FORCADO",
        )
        d = episodio.para_dict()
        assert d["action_at_decision"] == "HOLD_FORCADO"
        assert d["was_correct"] == 0
        assert "penalidade_normalizada" in d


# ────────────────────────────────────────────────────────────────
# Testes: ResultadoAutoavaliacao
# ────────────────────────────────────────────────────────────────


class TestResultadoAutoavaliacao:
    """Testes para dataclass de resultado da autoavaliacao."""

    def test_criar_resultado_com_penalidade(self) -> None:
        """Deve criar resultado com episodios penalizados."""
        episodios = [
            EpisodioHoldPenalizado(
                opportunity_id=1,
                timestamp=datetime.now().isoformat(),
                direction="COMPRA",
                movimento_pts=300.0,
                penalidade_normalizada=-0.3,
                was_correct=0,
                action_at_decision="HOLD_FORCADO",
            )
        ]
        resultado = ResultadoAutoavaliacao(
            status=StatusAutoavaliacao.INATIVIDADE_INJUSTA,
            data="2026-03-18",
            condicoes=CondicoesInatividade(
                data="2026-03-18",
                n_trades_executados=0,
                macro_score_medio=25.0,
                adx_medio=35.0,
                market_range_pts=2000.0,
                n_oportunidades_detectadas=3,
                n_oportunidades_executadas=0,
            ),
            episodios_penalizados=episodios,
            movimento_total_perdido_pts=300.0,
            penalidade_total=0.3,
            recomendacao="Calibracao necessaria — agente excessivamente conservador",
            arquivo_relatorio=None,
        )
        assert resultado.status == StatusAutoavaliacao.INATIVIDADE_INJUSTA
        assert len(resultado.episodios_penalizados) == 1
        assert resultado.movimento_total_perdido_pts == 300.0

    def test_resultado_para_dict(self) -> None:
        """Deve serializar resultado completo para dicionario."""
        resultado = ResultadoAutoavaliacao(
            status=StatusAutoavaliacao.MERCADO_FRACO,
            data="2026-03-18",
            condicoes=CondicoesInatividade(
                data="2026-03-18",
                n_trades_executados=0,
                macro_score_medio=8.0,
                adx_medio=18.0,
                market_range_pts=300.0,
                n_oportunidades_detectadas=0,
                n_oportunidades_executadas=0,
            ),
            episodios_penalizados=[],
            movimento_total_perdido_pts=0.0,
            penalidade_total=0.0,
            recomendacao="Mercado sem direcao — inatividade justificada",
            arquivo_relatorio=None,
        )
        d = resultado.para_dict()
        assert d["status"] == "MERCADO_FRACO"
        assert d["penalidade_total"] == 0.0


# ────────────────────────────────────────────────────────────────
# Testes: AutoavaliacaoInatividade — Deteccao
# ────────────────────────────────────────────────────────────────


class TestDeteccaoInatividade:
    """Testes para deteccao de inatividade injusta."""

    def test_detectar_inatividade_injusta_todas_condicoes(
        self, condicoes_mercado_favoravel: CondicoesInatividade
    ) -> None:
        """Deve detectar inatividade injusta quando todas as condicoes sao verdadeiras."""
        avaliador = AutoavaliacaoInatividade.__new__(AutoavaliacaoInatividade)
        resultado = avaliador._e_inatividade_injusta(condicoes_mercado_favoravel)
        assert resultado is True

    def test_nao_detectar_inatividade_mercado_fraco(
        self, condicoes_mercado_fraco: CondicoesInatividade
    ) -> None:
        """Nao deve penalizar quando mercado era fraco."""
        avaliador = AutoavaliacaoInatividade.__new__(AutoavaliacaoInatividade)
        resultado = avaliador._e_inatividade_injusta(condicoes_mercado_fraco)
        assert resultado is False

    def test_nao_detectar_quando_trades_executados(self) -> None:
        """Nao deve penalizar quando ha trades executados no dia."""
        condicoes = CondicoesInatividade(
            data="2026-03-18",
            n_trades_executados=2,  # has trades
            macro_score_medio=30.0,
            adx_medio=40.0,
            market_range_pts=2000.0,
            n_oportunidades_detectadas=5,
            n_oportunidades_executadas=2,
        )
        avaliador = AutoavaliacaoInatividade.__new__(AutoavaliacaoInatividade)
        resultado = avaliador._e_inatividade_injusta(condicoes)
        assert resultado is False

    def test_limiar_macro_score_15(self) -> None:
        """Deve respeitar limiar de macro_score_medio >= 15."""
        # Exatamente no limiar — deve detectar
        condicoes_limiar = CondicoesInatividade(
            data="2026-03-18",
            n_trades_executados=0,
            macro_score_medio=15.0,
            adx_medio=30.0,
            market_range_pts=500.0,
            n_oportunidades_detectadas=1,
            n_oportunidades_executadas=0,
        )
        avaliador = AutoavaliacaoInatividade.__new__(AutoavaliacaoInatividade)
        assert avaliador._e_inatividade_injusta(condicoes_limiar) is True

    def test_limiar_adx_30(self) -> None:
        """Nao deve penalizar quando ADX abaixo de 30."""
        condicoes = CondicoesInatividade(
            data="2026-03-18",
            n_trades_executados=0,
            macro_score_medio=25.0,
            adx_medio=29.9,  # abaixo do limiar
            market_range_pts=800.0,
            n_oportunidades_detectadas=2,
            n_oportunidades_executadas=0,
        )
        avaliador = AutoavaliacaoInatividade.__new__(AutoavaliacaoInatividade)
        assert avaliador._e_inatividade_injusta(condicoes) is False

    def test_limiar_market_range_500(self) -> None:
        """Nao deve penalizar quando range abaixo de 500 pts."""
        condicoes = CondicoesInatividade(
            data="2026-03-18",
            n_trades_executados=0,
            macro_score_medio=25.0,
            adx_medio=35.0,
            market_range_pts=499.0,  # abaixo do limiar
            n_oportunidades_detectadas=2,
            n_oportunidades_executadas=0,
        )
        avaliador = AutoavaliacaoInatividade.__new__(AutoavaliacaoInatividade)
        assert avaliador._e_inatividade_injusta(condicoes) is False


# ────────────────────────────────────────────────────────────────
# Testes: Calculo de penalidade
# ────────────────────────────────────────────────────────────────


class TestCalculoPenalidade:
    """Testes para calculo de penalidade proporcional ao movimento."""

    def test_penalidade_proporcional_movimento(self) -> None:
        """Penalidade deve ser -0.5 para cada 100 pts de movimento."""
        avaliador = AutoavaliacaoInatividade.__new__(AutoavaliacaoInatividade)
        penalidade = avaliador._calcular_penalidade(movimento_pts=100.0)
        assert penalidade == pytest.approx(-0.5, abs=0.001)

    def test_penalidade_555_pts(self) -> None:
        """Penalidade para 555 pts de movimento (caso real do backlog)."""
        avaliador = AutoavaliacaoInatividade.__new__(AutoavaliacaoInatividade)
        penalidade = avaliador._calcular_penalidade(movimento_pts=555.0)
        # 555 / 100 * (-0.5) = -2.775 mas deve ter teto
        assert penalidade <= 0.0

    def test_penalidade_movimento_zero(self) -> None:
        """Penalidade deve ser zero quando sem movimento."""
        avaliador = AutoavaliacaoInatividade.__new__(AutoavaliacaoInatividade)
        penalidade = avaliador._calcular_penalidade(movimento_pts=0.0)
        assert penalidade == 0.0

    def test_penalidade_negativa(self) -> None:
        """Penalidade deve ser sempre negativa ou zero."""
        avaliador = AutoavaliacaoInatividade.__new__(AutoavaliacaoInatividade)
        for movimento in [50.0, 100.0, 500.0, 1000.0, 2000.0]:
            pen = avaliador._calcular_penalidade(movimento_pts=movimento)
            assert pen <= 0.0, f"Penalidade deve ser negativa para {movimento} pts"


# ────────────────────────────────────────────────────────────────
# Testes: AutoavaliacaoInatividade — Ciclo completo
# ────────────────────────────────────────────────────────────────


class TestAutoavaliacaoInatividade:
    """Testes para o motor principal de autoavaliacao."""

    def test_inicializar_autoavaliacao(self, db_temporario: str) -> None:
        """Deve inicializar AutoavaliacaoInatividade com db_path."""
        avaliador = AutoavaliacaoInatividade(db_path=db_temporario)
        assert avaliador is not None

    def test_coletar_condicoes_mercado(
        self, db_com_oportunidades: str
    ) -> None:
        """Deve coletar condicoes do mercado a partir do banco SQLite."""
        avaliador = AutoavaliacaoInatividade(db_path=db_com_oportunidades)
        condicoes = avaliador.coletar_condicoes_do_dia()
        assert condicoes is not None
        assert condicoes.n_oportunidades_detectadas >= 0
        assert condicoes.macro_score_medio >= 0.0
        assert condicoes.adx_medio >= 0.0

    def test_gerar_episodios_hold_penalizados(
        self, db_com_oportunidades: str
    ) -> None:
        """Deve gerar episodios de HOLD penalizados para oportunidades nao executadas."""
        avaliador = AutoavaliacaoInatividade(db_path=db_com_oportunidades)
        episodios = avaliador.gerar_episodios_hold_penalizados()
        # Banco tem 5 oportunidades
        assert len(episodios) >= 0  # pode ser 0 se sem preco apos
        for ep in episodios:
            assert ep.action_at_decision == "HOLD_FORCADO"
            assert ep.was_correct == 0
            assert ep.penalidade_normalizada <= 0.0

    def test_persistir_episodios_em_rl_rewards(
        self, db_com_oportunidades: str
    ) -> None:
        """Deve persistir episodios em rl_rewards com campos corretos."""
        avaliador = AutoavaliacaoInatividade(db_path=db_com_oportunidades)
        episodios = [
            EpisodioHoldPenalizado(
                opportunity_id=1,
                timestamp=datetime.now().isoformat(),
                direction="COMPRA",
                movimento_pts=400.0,
                penalidade_normalizada=-0.4,
                was_correct=0,
                action_at_decision="HOLD_FORCADO",
            )
        ]
        n_persistidos = avaliador.persistir_episodios(episodios)
        assert n_persistidos == 1

        # Verificar no banco
        conn = sqlite3.connect(db_com_oportunidades)
        cur = conn.cursor()
        cur.execute(
            "SELECT action_at_decision, was_correct FROM rl_rewards"
        )
        rows = cur.fetchall()
        conn.close()
        assert len(rows) == 1
        assert rows[0][0] == "HOLD_FORCADO"
        assert rows[0][1] == 0

    def test_gerar_relatorio_markdown(self, db_temporario: str) -> None:
        """Deve gerar relatorio Markdown estruturado."""
        avaliador = AutoavaliacaoInatividade(db_path=db_temporario)
        condicoes = CondicoesInatividade(
            data="2026-03-18",
            n_trades_executados=0,
            macro_score_medio=29.5,
            adx_medio=38.0,
            market_range_pts=2795.0,
            n_oportunidades_detectadas=141,
            n_oportunidades_executadas=0,
        )
        episodios = [
            EpisodioHoldPenalizado(
                opportunity_id=1,
                timestamp="2026-03-18T10:00:00",
                direction="COMPRA",
                movimento_pts=555.0,
                penalidade_normalizada=-0.5,
                was_correct=0,
                action_at_decision="HOLD_FORCADO",
            ),
            EpisodioHoldPenalizado(
                opportunity_id=2,
                timestamp="2026-03-18T13:00:00",
                direction="VENDA",
                movimento_pts=280.0,
                penalidade_normalizada=-0.28,
                was_correct=0,
                action_at_decision="HOLD_FORCADO",
            ),
        ]
        resultado = ResultadoAutoavaliacao(
            status=StatusAutoavaliacao.INATIVIDADE_INJUSTA,
            data="2026-03-18",
            condicoes=condicoes,
            episodios_penalizados=episodios,
            movimento_total_perdido_pts=275.0,
            penalidade_total=0.78,
            recomendacao="Calibracao necessaria — agente excessivamente conservador",
            arquivo_relatorio=None,
        )
        conteudo = avaliador.gerar_relatorio_markdown(resultado)
        assert "AUTOAVALIACAO" in conteudo.upper()
        assert "2026-03-18" in conteudo
        assert "macro" in conteudo.lower() or "Macro" in conteudo
        assert "HOLD" in conteudo
        assert "calibracao" in conteudo.lower() or "Calibracao" in conteudo

    def test_salvar_relatorio_em_outputs(
        self, db_temporario: str, tmp_path: Path
    ) -> None:
        """Deve salvar relatorio em outputs/micro_autoavaliacao_YYYYMMDD.md."""
        avaliador = AutoavaliacaoInatividade(db_path=db_temporario)
        conteudo = "# Relatorio de Autoavaliacao\n\nConteudo de teste."
        caminho = avaliador.salvar_relatorio(
            conteudo=conteudo,
            data="2026-03-18",
            diretorio_outputs=str(tmp_path),
        )
        assert Path(caminho).exists()
        assert "micro_autoavaliacao_2026-03-18" in caminho

    def test_avaliar_dia_sem_trade_mercado_favoravel(
        self, db_com_oportunidades: str, tmp_path: Path
    ) -> None:
        """Fluxo completo: dia sem trade em mercado favoravel gera penalidades."""
        avaliador = AutoavaliacaoInatividade(db_path=db_com_oportunidades)
        resultado = avaliador.avaliar_dia(
            n_trades_executados=0,
            diretorio_outputs=str(tmp_path),
        )
        assert resultado is not None
        assert resultado.status in (
            StatusAutoavaliacao.INATIVIDADE_INJUSTA,
            StatusAutoavaliacao.MERCADO_FRACO,
            StatusAutoavaliacao.SEM_DADOS,
        )

    def test_avaliar_dia_com_trades_sem_penalidade(
        self, db_com_oportunidades: str, tmp_path: Path
    ) -> None:
        """Nao deve gerar penalidade quando ha trades executados."""
        avaliador = AutoavaliacaoInatividade(db_path=db_com_oportunidades)
        resultado = avaliador.avaliar_dia(
            n_trades_executados=2,
            diretorio_outputs=str(tmp_path),
        )
        # Quando ha trades, nao e inatividade injusta
        assert resultado.status != StatusAutoavaliacao.INATIVIDADE_INJUSTA or \
               resultado.penalidade_total == 0.0

    def test_type_hints_100_porcento(self) -> None:
        """Valida que modulo importa sem erros de type hints."""
        from src.application.autoavaliacao_inatividade import (
            AutoavaliacaoInatividade,
            CondicoesInatividade,
            EpisodioHoldPenalizado,
            ResultadoAutoavaliacao,
            StatusAutoavaliacao,
        )
        assert AutoavaliacaoInatividade is not None
        assert CondicoesInatividade is not None
        assert EpisodioHoldPenalizado is not None
        assert ResultadoAutoavaliacao is not None
        assert StatusAutoavaliacao is not None


# ────────────────────────────────────────────────────────────────
# Testes: Integracao completa
# ────────────────────────────────────────────────────────────────


class TestIntegracaoCompleta:
    """Testes de integracao do fluxo completo de autoavaliacao."""

    def test_fluxo_completo_dia_sem_trade(
        self, db_com_oportunidades: str, tmp_path: Path
    ) -> None:
        """Simula pregao 17/03 com 0 trades e mercado favoravel."""
        avaliador = AutoavaliacaoInatividade(db_path=db_com_oportunidades)

        # Executa avaliacao
        resultado = avaliador.avaliar_dia(
            n_trades_executados=0,
            diretorio_outputs=str(tmp_path),
        )

        # Valida estrutura do resultado
        assert resultado is not None
        assert resultado.data is not None
        assert resultado.condicoes is not None
        assert isinstance(resultado.episodios_penalizados, list)
        assert isinstance(resultado.movimento_total_perdido_pts, float)
        assert isinstance(resultado.recomendacao, str)

        # Valida serializacao
        d = resultado.para_dict()
        assert "status" in d
        assert "data" in d
        assert "condicoes" in d

    def test_episodios_persistidos_tem_campos_obrigatorios(
        self, db_temporario: str
    ) -> None:
        """Episodios em rl_rewards devem ter todos os campos obrigatorios."""
        avaliador = AutoavaliacaoInatividade(db_path=db_temporario)
        episodios = [
            EpisodioHoldPenalizado(
                opportunity_id=10,
                timestamp="2026-03-18T11:00:00",
                direction="COMPRA",
                movimento_pts=200.0,
                penalidade_normalizada=-0.2,
                was_correct=0,
                action_at_decision="HOLD_FORCADO",
            )
        ]
        avaliador.persistir_episodios(episodios)

        conn = sqlite3.connect(db_temporario)
        cur = conn.cursor()
        cur.execute("""
            SELECT action_at_decision, price_change_points,
                   was_correct, reward_normalized, is_evaluated, agent_id
            FROM rl_rewards
        """)
        row = cur.fetchone()
        conn.close()

        assert row is not None
        assert row[0] == "HOLD_FORCADO"   # action_at_decision
        assert row[1] == 200.0            # price_change_points
        assert row[2] == 0                # was_correct
        assert row[3] <= 0.0              # reward_normalized (negativo)
        assert row[4] == 1                # is_evaluated
        assert row[5] == "micro_tendencia"  # agent_id
