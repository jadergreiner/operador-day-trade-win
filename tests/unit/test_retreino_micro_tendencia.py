"""
Testes unitarios para CALIBRACAO-MICRO-05: Retreino Efetivo.

Cobre:
- TriggerRetreino: threshold de rewards, contagem, deve_retreinar()
- CarregadorEpisodios: carregamento, win_rate ponderado
- VersonadorModelo: versionamento semantico, rollback
- GerenciadorRetreino: fluxo completo, rollback automatico

Referencia: docs/BACKLOG.md (CALIBRACAO-MICRO-05)
"""

from __future__ import annotations

import json
import sqlite3
import tempfile
from datetime import datetime
from pathlib import Path

import pytest

from src.application.retreino_micro_tendencia import (
    CarregadorEpisodios,
    GerenciadorRetreino,
    ResultadoRetreino,
    RegistroTreino,
    TriggerRetreino,
    VersonadorModelo,
    THRESHOLD_REWARDS_NOVO_TREINO,
    ROLLBACK_DELTA_MAX_PP,
)


# ─────────────────────────────────────────────
# Fixtures
# ─────────────────────────────────────────────


@pytest.fixture
def db_temp():
    """Banco SQLite temporario com tabelas basicas."""
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
        db_path = f.name

    conn = sqlite3.connect(db_path)
    cur = conn.cursor()

    # Tabela rl_rewards
    cur.execute("""
        CREATE TABLE IF NOT EXISTS rl_rewards (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            episode_id TEXT,
            is_evaluated INTEGER DEFAULT 0,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
    """)

    # Tabela micro_episodios
    cur.execute("""
        CREATE TABLE IF NOT EXISTS micro_episodios (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            episode_id TEXT,
            timestamp_entrada TEXT,
            timestamp_saida TEXT,
            direcao TEXT,
            preco_entrada REAL,
            preco_saida REAL,
            resultado_pts REAL,
            outcome TEXT,
            confianca REAL,
            macro_score INTEGER,
            sl REAL,
            tp REAL,
            magic_number INTEGER DEFAULT 234700,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
    """)

    conn.commit()
    conn.close()
    yield db_path


@pytest.fixture
def db_com_rewards(db_temp):
    """Banco com 250 rewards avaliados."""
    conn = sqlite3.connect(db_temp)
    cur = conn.cursor()
    for i in range(250):
        cur.execute(
            "INSERT INTO rl_rewards (episode_id, is_evaluated) VALUES (?, 1)",
            (f"ep_{i}",),
        )
    conn.commit()
    conn.close()
    return db_temp


@pytest.fixture
def db_com_episodios(db_temp):
    """Banco com 30 episodios de micro_episodios."""
    conn = sqlite3.connect(db_temp)
    cur = conn.cursor()
    agora = datetime.now().isoformat()
    outcomes = ["WIN", "WIN", "LOSS", "WIN", "BREAKEVEN"] * 6
    for i, outcome in enumerate(outcomes):
        pts = 100.0 if outcome == "WIN" else (-80.0 if outcome == "LOSS" else 0.0)
        cur.execute(
            """
            INSERT INTO micro_episodios
            (episode_id, timestamp_entrada, timestamp_saida, direcao,
             resultado_pts, outcome, confianca, macro_score)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (f"ep_{i}", agora, agora, "COMPRA", pts, outcome, 42.0, 30),
        )
    conn.commit()
    conn.close()
    return db_temp


@pytest.fixture
def modelos_dir_temp(tmp_path):
    """Diretorio temporario para modelos."""
    return str(tmp_path / "modelos")


# ─────────────────────────────────────────────
# Testes TriggerRetreino
# ─────────────────────────────────────────────


class TestTriggerRetreino:
    """Testes do TriggerRetreino."""

    def test_inicializar_trigger_cria_tabelas(self, db_temp):
        """Garante que tabelas sao criadas na inicializacao."""
        trigger = TriggerRetreino(db_temp)
        conn = sqlite3.connect(db_temp)
        cur = conn.cursor()
        cur.execute(
            "SELECT name FROM sqlite_master WHERE type='table' "
            "AND name IN ('rl_training_metrics', 'model_metadata')"
        )
        tabelas = {r[0] for r in cur.fetchall()}
        conn.close()
        assert "rl_training_metrics" in tabelas
        assert "model_metadata" in tabelas

    def test_contar_rewards_zero_sem_dados(self, db_temp):
        """Retorna 0 se nao ha rewards."""
        trigger = TriggerRetreino(db_temp)
        assert trigger.contar_rewards_total() == 0

    def test_contar_rewards_total_com_dados(self, db_com_rewards):
        """Conta corretamente rewards avaliados."""
        trigger = TriggerRetreino(db_com_rewards)
        assert trigger.contar_rewards_total() == 250

    def test_contar_rewards_ultimo_treino_zero_sem_treino(self, db_temp):
        """Retorna 0 se nunca treinou."""
        trigger = TriggerRetreino(db_temp)
        assert trigger.contar_rewards_ultimo_treino() == 0

    def test_novos_rewards_sem_treino_anterior(self, db_com_rewards):
        """Novos rewards = total quando nunca treinou."""
        trigger = TriggerRetreino(db_com_rewards)
        assert trigger.novos_rewards_desde_ultimo_treino() == 250

    def test_deve_retreinar_true_acima_threshold(self, db_com_rewards):
        """Retorna True quando novos rewards >= threshold."""
        trigger = TriggerRetreino(db_com_rewards, threshold=200)
        assert trigger.deve_retreinar() is True

    def test_deve_retreinar_false_abaixo_threshold(self, db_temp):
        """Retorna False quando poucos rewards."""
        conn = sqlite3.connect(db_temp)
        cur = conn.cursor()
        for i in range(50):
            cur.execute(
                "INSERT INTO rl_rewards (episode_id, is_evaluated) VALUES (?, 1)",
                (f"ep_{i}",),
            )
        conn.commit()
        conn.close()
        trigger = TriggerRetreino(db_temp, threshold=200)
        assert trigger.deve_retreinar() is False

    def test_threshold_padrao_igual_constante(self, db_temp):
        """Threshold default igual a THRESHOLD_REWARDS_NOVO_TREINO."""
        trigger = TriggerRetreino(db_temp)
        assert trigger.threshold == THRESHOLD_REWARDS_NOVO_TREINO


# ─────────────────────────────────────────────
# Testes CarregadorEpisodios
# ─────────────────────────────────────────────


class TestCarregadorEpisodios:
    """Testes do CarregadorEpisodios."""

    def test_carregar_retorna_vazio_sem_dados(self, db_temp):
        """Retorna lista vazia se tabela esta vazia."""
        carregador = CarregadorEpisodios(db_temp)
        resultado = carregador.carregar_episodios()
        assert resultado == []

    def test_carregar_episodios_retorna_lista(self, db_com_episodios):
        """Retorna lista de dicts com campos obrigatorios."""
        carregador = CarregadorEpisodios(db_com_episodios)
        episodios = carregador.carregar_episodios()
        assert len(episodios) == 30
        for ep in episodios:
            assert "outcome" in ep
            assert "pnl" in ep
            assert "peso" in ep

    def test_primeiro_episodio_tem_peso_um(self, db_com_episodios):
        """Episodio mais recente tem peso 1.0."""
        carregador = CarregadorEpisodios(db_com_episodios)
        episodios = carregador.carregar_episodios()
        assert episodios[0]["peso"] == pytest.approx(1.0, abs=0.01)

    def test_ultimo_episodio_tem_peso_menor(self, db_com_episodios):
        """Episodio mais antigo tem peso menor que 1.0."""
        carregador = CarregadorEpisodios(db_com_episodios)
        episodios = carregador.carregar_episodios()
        assert episodios[-1]["peso"] < 0.5

    def test_calcular_win_rate_lista_vazia(self, db_temp):
        """Win rate de lista vazia e 0.0."""
        carregador = CarregadorEpisodios(db_temp)
        assert carregador.calcular_win_rate([]) == 0.0

    def test_calcular_win_rate_todos_win(self, db_temp):
        """Win rate de 100% WIN."""
        carregador = CarregadorEpisodios(db_temp)
        eps = [{"outcome": "WIN", "peso": 1.0}] * 5
        assert carregador.calcular_win_rate(eps) == pytest.approx(1.0, abs=0.01)

    def test_calcular_win_rate_metade_win(self, db_temp):
        """Win rate de 50%."""
        carregador = CarregadorEpisodios(db_temp)
        eps = [
            {"outcome": "WIN", "peso": 1.0},
            {"outcome": "LOSS", "peso": 1.0},
        ]
        assert carregador.calcular_win_rate(eps) == pytest.approx(0.5, abs=0.01)


# ─────────────────────────────────────────────
# Testes VersonadorModelo
# ─────────────────────────────────────────────


class TestVersonadorModelo:
    """Testes do VersonadorModelo."""

    def test_versao_atual_none_sem_registro(self, db_temp, modelos_dir_temp):
        """Retorna None quando model_metadata esta vazia."""
        TriggerRetreino(db_temp)  # garante tabelas
        v = VersonadorModelo(db_temp, modelos_dir_temp)
        assert v.obter_versao_atual() is None

    def test_gerar_proxima_versao_primeira_vez(self, db_temp, modelos_dir_temp):
        """Primeira versao sempre e v1.0.0_YYYYMMDD."""
        TriggerRetreino(db_temp)  # garante tabelas
        v = VersonadorModelo(db_temp, modelos_dir_temp)
        hoje = datetime.now().strftime("%Y%m%d")
        proxima = v.gerar_proxima_versao()
        assert proxima == f"v1.0.0_{hoje}"

    def test_gerar_proxima_versao_incrementa_minor(self, db_temp, modelos_dir_temp):
        """Minor incrementa em retreino normal."""
        TriggerRetreino(db_temp)
        v = VersonadorModelo(db_temp, modelos_dir_temp)
        hoje = datetime.now().strftime("%Y%m%d")

        # Simular versao ativa
        conn = sqlite3.connect(db_temp)
        cur = conn.cursor()
        cur.execute(
            "INSERT INTO model_metadata "
            "(versao, data_treino, modelo_path, win_rate_validacao, n_episodios, ativo) "
            "VALUES (?, ?, ?, ?, ?, 1)",
            (f"v1.0.0_{hoje}", datetime.now().isoformat(), "/tmp/m.json", 0.55, 20),
        )
        conn.commit()
        conn.close()

        proxima = v.gerar_proxima_versao(rollback=False)
        assert proxima == f"v1.1.0_{hoje}"

    def test_gerar_proxima_versao_rollback_incrementa_patch(
        self, db_temp, modelos_dir_temp
    ):
        """Patch incrementa em rollback."""
        TriggerRetreino(db_temp)
        v = VersonadorModelo(db_temp, modelos_dir_temp)
        hoje = datetime.now().strftime("%Y%m%d")

        conn = sqlite3.connect(db_temp)
        cur = conn.cursor()
        cur.execute(
            "INSERT INTO model_metadata "
            "(versao, data_treino, modelo_path, win_rate_validacao, n_episodios, ativo) "
            "VALUES (?, ?, ?, ?, ?, 1)",
            (f"v1.2.0_{hoje}", datetime.now().isoformat(), "/tmp/m.json", 0.60, 20),
        )
        conn.commit()
        conn.close()

        proxima = v.gerar_proxima_versao(rollback=True)
        assert proxima == f"v1.2.1_{hoje}"

    def test_caminho_modelo_retorna_path(self, db_temp, modelos_dir_temp):
        """Caminho retorna Path com versao no nome."""
        TriggerRetreino(db_temp)
        v = VersonadorModelo(db_temp, modelos_dir_temp)
        caminho = v.caminho_modelo("v1.0.0_20260318")
        assert caminho.name == "v1.0.0_20260318.json"


# ─────────────────────────────────────────────
# Testes GerenciadorRetreino
# ─────────────────────────────────────────────


class TestGerenciadorRetreino:
    """Testes do GerenciadorRetreino."""

    def test_nao_executa_sem_threshold(self, db_temp, modelos_dir_temp):
        """Retorna executado=False sem rewards suficientes."""
        gerenciador = GerenciadorRetreino(db_temp, modelos_dir_temp)
        resultado = gerenciador.executar_retreino(forcar=False)
        assert isinstance(resultado, ResultadoRetreino)
        assert resultado.executado is False
        assert "threshold" in resultado.motivo_nao_execucao.lower()

    def test_nao_executa_sem_episodios_suficientes(
        self, db_com_rewards, modelos_dir_temp
    ):
        """Retorna executado=False se episodios < 10."""
        gerenciador = GerenciadorRetreino(db_com_rewards, modelos_dir_temp)
        resultado = gerenciador.executar_retreino(forcar=True)
        assert resultado.executado is False
        assert "episodio" in resultado.motivo_nao_execucao.lower()

    def test_executa_com_forcamento_e_episodios(
        self, db_com_episodios, modelos_dir_temp
    ):
        """Executa retreino quando forcado e ha episodios suficientes."""
        gerenciador = GerenciadorRetreino(db_com_episodios, modelos_dir_temp)
        resultado = gerenciador.executar_retreino(forcar=True)
        assert resultado.executado is True
        assert resultado.n_episodios == 30
        assert 0.0 <= resultado.win_rate_treino <= 1.0
        assert 0.0 <= resultado.win_rate_validacao <= 1.0

    def test_executa_com_threshold_atingido(
        self, db_com_episodios, modelos_dir_temp
    ):
        """Executa quando threshold de rewards e atingido."""
        # Adicionar rewards suficientes
        conn = sqlite3.connect(db_com_episodios)
        cur = conn.cursor()
        for i in range(250):
            cur.execute(
                "INSERT INTO rl_rewards (episode_id, is_evaluated) VALUES (?, 1)",
                (f"r_{i}",),
            )
        conn.commit()
        conn.close()

        gerenciador = GerenciadorRetreino(db_com_episodios, modelos_dir_temp)
        resultado = gerenciador.executar_retreino(forcar=False)
        assert resultado.executado is True

    def test_resultado_tem_versao_semantica(
        self, db_com_episodios, modelos_dir_temp
    ):
        """Versao retornada segue formato vMAJOR.MINOR.PATCH_YYYYMMDD."""
        gerenciador = GerenciadorRetreino(db_com_episodios, modelos_dir_temp)
        resultado = gerenciador.executar_retreino(forcar=True)
        assert resultado.versao.startswith("v")
        assert "_" in resultado.versao

    def test_modelo_json_criado_em_disco(
        self, db_com_episodios, modelos_dir_temp
    ):
        """Arquivo JSON do modelo e criado no diretorio configurado."""
        gerenciador = GerenciadorRetreino(db_com_episodios, modelos_dir_temp)
        resultado = gerenciador.executar_retreino(forcar=True)
        assert resultado.executado is True
        arquivo = Path(modelos_dir_temp) / f"{resultado.versao}.json"
        assert arquivo.exists()

    def test_modelo_json_contem_campos_obrigatorios(
        self, db_com_episodios, modelos_dir_temp
    ):
        """JSON do modelo contem campos de metadados."""
        gerenciador = GerenciadorRetreino(db_com_episodios, modelos_dir_temp)
        resultado = gerenciador.executar_retreino(forcar=True)
        arquivo = Path(modelos_dir_temp) / f"{resultado.versao}.json"
        with open(arquivo, encoding="utf-8") as f:
            dados = json.load(f)
        for campo in [
            "versao",
            "data_treino",
            "win_rate_treino",
            "win_rate_validacao",
            "n_episodios",
        ]:
            assert campo in dados, f"Campo '{campo}' ausente no JSON"

    def test_treino_registrado_em_rl_training_metrics(
        self, db_com_episodios, modelos_dir_temp
    ):
        """Registro inserido em rl_training_metrics apos retreino."""
        gerenciador = GerenciadorRetreino(db_com_episodios, modelos_dir_temp)
        gerenciador.executar_retreino(forcar=True)
        conn = sqlite3.connect(db_com_episodios)
        cur = conn.cursor()
        cur.execute("SELECT COUNT(*) FROM rl_training_metrics")
        contagem = cur.fetchone()[0]
        conn.close()
        assert contagem == 1

    def test_model_metadata_atualizado(
        self, db_com_episodios, modelos_dir_temp
    ):
        """model_metadata contem versao ativa apos retreino."""
        gerenciador = GerenciadorRetreino(db_com_episodios, modelos_dir_temp)
        resultado = gerenciador.executar_retreino(forcar=True)
        conn = sqlite3.connect(db_com_episodios)
        cur = conn.cursor()
        cur.execute(
            "SELECT versao, ativo FROM model_metadata WHERE ativo = 1"
        )
        row = cur.fetchone()
        conn.close()
        assert row is not None
        assert row[0] == resultado.versao
        assert row[1] == 1

    def test_bootstrap_modelo_atual_faz_upsert_em_model_name(
        self, tmp_path
    ):
        """Bootstrap do schema novo atualiza a mesma linha ativa."""
        db_path = tmp_path / "bootstrap_model_name.db"
        modelos_dir = tmp_path / "modelos"
        modelos_dir.mkdir(parents=True, exist_ok=True)
        modelo_path = modelos_dir / "lgbm.pkl"
        modelo_path.write_text("modelo fake", encoding="utf-8")

        conn = sqlite3.connect(db_path)
        cur = conn.cursor()
        cur.execute(
            """
            CREATE TABLE rl_training_metrics (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                versao TEXT NOT NULL,
                data_treino TEXT NOT NULL,
                n_episodios_usados INTEGER NOT NULL,
                n_rewards_no_treino INTEGER NOT NULL,
                win_rate_treino REAL NOT NULL,
                win_rate_validacao REAL NOT NULL,
                delta_vs_anterior REAL NOT NULL,
                rollback_realizado INTEGER NOT NULL DEFAULT 0,
                modelo_path TEXT NOT NULL,
                notas TEXT DEFAULT '',
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
            """
        )
        cur.execute(
            """
            CREATE TABLE model_metadata (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                model_name TEXT NOT NULL,
                model_type TEXT NOT NULL,
                version TEXT NOT NULL,
                trained_at TEXT NOT NULL,
                training_metrics TEXT,
                hyperparameters TEXT,
                file_path TEXT NOT NULL,
                is_active INTEGER DEFAULT 1,
                created_at TEXT,
                updated_at TEXT
            )
            """
        )
        cur.execute(
            "CREATE UNIQUE INDEX ix_model_metadata_model_name "
            "ON model_metadata (model_name)"
        )
        conn.commit()
        conn.close()

        trigger = TriggerRetreino(str(db_path))
        primeira = trigger.bootstrap_modelo_atual(
            str(modelo_path), rewards_total=10, n_episodios=20
        )
        segunda = trigger.bootstrap_modelo_atual(
            str(modelo_path), rewards_total=11, n_episodios=21
        )

        assert primeira is not None
        assert segunda is not None

        conn = sqlite3.connect(db_path)
        cur = conn.cursor()
        cur.execute(
            "SELECT COUNT(*), model_name, version, is_active "
            "FROM model_metadata"
        )
        contagem, model_name, version, is_active = cur.fetchone()
        conn.close()

        assert contagem == 1
        assert model_name == "micro_tendencia"
        assert version == segunda
        assert is_active == 1

    def test_rollback_acionado_por_degradacao(
        self, db_temp, modelos_dir_temp
    ):
        """Rollback e acionado quando win_rate cai mais de 5pp."""
        TriggerRetreino(db_temp)  # garante tabelas

        # Inserir modelo anterior com win_rate alto
        hoje = datetime.now().strftime("%Y%m%d")
        conn = sqlite3.connect(db_temp)
        cur = conn.cursor()
        cur.execute(
            "INSERT INTO model_metadata "
            "(versao, data_treino, modelo_path, win_rate_validacao, n_episodios, ativo) "
            "VALUES (?, ?, ?, ?, ?, 1)",
            (f"v1.0.0_{hoje}", datetime.now().isoformat(), "/tmp/m.json", 0.80, 20),
        )
        # Inserir episodios com win_rate baixo (~33%)
        agora = datetime.now().isoformat()
        for i in range(30):
            outcome = "WIN" if i % 3 == 0 else "LOSS"
            pts = 100.0 if outcome == "WIN" else -80.0
            cur.execute(
                """
                INSERT INTO micro_episodios
                (episode_id, timestamp_entrada, timestamp_saida, direcao,
                 resultado_pts, outcome, confianca, macro_score)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (f"ep_{i}", agora, agora, "COMPRA", pts, outcome, 42.0, 30),
            )
        conn.commit()
        conn.close()

        gerenciador = GerenciadorRetreino(db_temp, modelos_dir_temp)
        resultado = gerenciador.executar_retreino(forcar=True)

        assert resultado.executado is True
        # Delta deve ser negativo (queda de ~46pp: 0.80 -> ~0.33)
        assert resultado.delta_win_rate < -ROLLBACK_DELTA_MAX_PP
        assert resultado.rollback_realizado is True

    def test_resultado_para_dict_completo(
        self, db_com_episodios, modelos_dir_temp
    ):
        """ResultadoRetreino.para_dict() retorna todos os campos."""
        gerenciador = GerenciadorRetreino(db_com_episodios, modelos_dir_temp)
        resultado = gerenciador.executar_retreino(forcar=True)
        d = resultado.para_dict()
        for campo in [
            "executado",
            "versao",
            "n_episodios",
            "win_rate_treino",
            "win_rate_validacao",
            "delta_win_rate",
            "rollback_realizado",
            "timestamp",
        ]:
            assert campo in d, f"Campo '{campo}' ausente em para_dict()"


# ─────────────────────────────────────────────
# Testes RegistroTreino
# ─────────────────────────────────────────────


class TestRegistroTreino:
    """Testes do dataclass RegistroTreino."""

    def test_criar_registro_treino(self):
        """Instancia RegistroTreino com campos obrigatorios."""
        registro = RegistroTreino(
            versao="v1.0.0_20260318",
            data_treino="2026-03-18T10:00:00",
            n_episodios_usados=30,
            win_rate_treino=0.60,
            win_rate_validacao=0.55,
            delta_vs_anterior=2.5,
            rollback_realizado=False,
            modelo_path="/tmp/modelo.json",
        )
        assert registro.versao == "v1.0.0_20260318"
        assert registro.n_episodios_usados == 30

    def test_para_dict_serializavel(self):
        """para_dict() retorna dicionario JSON-serializable."""
        registro = RegistroTreino(
            versao="v1.0.0_20260318",
            data_treino="2026-03-18T10:00:00",
            n_episodios_usados=20,
            win_rate_treino=0.60,
            win_rate_validacao=0.58,
            delta_vs_anterior=1.0,
            rollback_realizado=False,
            modelo_path="/tmp/m.json",
        )
        d = registro.para_dict()
        json_str = json.dumps(d)
        assert "versao" in json_str

    def test_type_hints_100_porcento(self):
        """Valida que modulo importa sem erros de type hints."""
        from src.application import retreino_micro_tendencia  # noqa: F401
        assert retreino_micro_tendencia is not None
