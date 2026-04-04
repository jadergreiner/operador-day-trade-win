"""
Testes TDD para MacroGuardianReaderService.

Cobre leitura de snapshot, banco vazio, kill switch, enriquecimento de
episodio e geracao de relatorio semanal.

BLID-025 / ROADMAP-DIARIOS-05
"""

from __future__ import annotations

import sqlite3
import tempfile
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

import pytest

from src.application.macro_guardian_universal_log import (
    ensure_macro_guardian_log_table,
    persist_macro_guardian_events,
)
from src.application.services.macro_guardian_reader_service import (
    MacroGuardianReaderService,
    MacroGuardianSnapshotResult,
)


# ─────────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────────


def _criar_db_vazio() -> Path:
    """Cria banco temporario vazio com tabela do guardian."""
    tmp = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
    db_path = Path(tmp.name)
    tmp.close()
    ensure_macro_guardian_log_table(db_path)
    return db_path


def _inserir_evento(
    db_path: Path,
    severity: str = "WARNING",
    kill_switch: bool = False,
    score: float = -2.0,
    minutos_atras: int = 5,
) -> None:
    """Insere evento no banco com timestamp recente."""
    ts = (datetime.utcnow() - timedelta(minutes=minutos_atras)).isoformat(
        timespec="seconds"
    )
    persist_macro_guardian_events(
        db_path,
        [
            {
                "timestamp": ts,
                "severity": severity,
                "tipo_evento": "teste_evento",
                "descricao": "Evento de teste",
                "score_impacto": score,
                "kill_switch_ativo": kill_switch,
            }
        ],
    )


def _criar_db_com_feedback(db_path: Path) -> None:
    """Cria tabela diary_feedback no banco com alguns registros de trade."""
    conn = sqlite3.connect(str(db_path), timeout=30)
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS diary_feedback (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp TEXT NOT NULL,
            nota_agente INTEGER,
            source TEXT,
            retreinamento_necessario INTEGER DEFAULT 0,
            alertas_criticos TEXT,
            sugestoes TEXT
        )
        """
    )
    dados = [
        ("2026-04-01T10:00:00", 3, "rl_diary"),
        ("2026-04-02T10:00:00", 8, "rl_diary"),
        ("2026-04-03T10:00:00", 4, "rl_diary"),
        ("2026-04-04T10:00:00", 7, "rl_diary"),
        ("2026-04-05T10:00:00", 2, "rl_diary"),
    ]
    conn.executemany(
        """
        INSERT INTO diary_feedback (timestamp, nota_agente, source)
        VALUES (?, ?, ?)
        """,
        dados,
    )
    conn.commit()
    conn.close()


# ─────────────────────────────────────────────────────────────────
# Testes: ler_snapshot
# ─────────────────────────────────────────────────────────────────


class TestLerSnapshot:
    """Testes para MacroGuardianReaderService.ler_snapshot()."""

    def test_retorna_snapshot_result_com_dados(self) -> None:
        """Deve retornar MacroGuardianSnapshotResult com dados quando banco tem eventos."""
        db_path = _criar_db_vazio()
        _inserir_evento(db_path, severity="WARNING", score=-2.5)

        servico = MacroGuardianReaderService()
        resultado = servico.ler_snapshot(db_path)

        assert isinstance(resultado, MacroGuardianSnapshotResult)
        assert resultado.alertas_ativos >= 1
        assert isinstance(resultado.score_guardian, float)
        assert isinstance(resultado.regime_macro, str)
        assert isinstance(resultado.kill_switch_ativo, bool)
        assert isinstance(resultado.kill_switch_motivo, str)

    def test_retorna_snapshot_seguro_com_banco_vazio(self) -> None:
        """Deve retornar snapshot com defaults seguros quando banco esta vazio."""
        db_path = _criar_db_vazio()

        servico = MacroGuardianReaderService()
        resultado = servico.ler_snapshot(db_path)

        assert isinstance(resultado, MacroGuardianSnapshotResult)
        assert resultado.alertas_ativos == 0
        assert resultado.score_guardian == 0.0
        assert resultado.kill_switch_ativo is False
        assert resultado.regime_macro == "ESTAVEL"
        assert resultado.kill_switch_motivo == ""

    def test_snapshot_detecta_regime_critico_com_kill_switch(self) -> None:
        """Deve retornar regime CRITICO quando kill switch esta ativo nos eventos."""
        db_path = _criar_db_vazio()
        _inserir_evento(db_path, severity="CRITICAL", kill_switch=True, score=-8.0)

        servico = MacroGuardianReaderService()
        resultado = servico.ler_snapshot(db_path)

        assert resultado.kill_switch_ativo is True
        assert resultado.regime_macro == "CRITICO"

    def test_snapshot_contabiliza_alertas_warning_e_critical(self) -> None:
        """Deve contar alertas de severidade WARNING e CRITICAL."""
        db_path = _criar_db_vazio()
        _inserir_evento(db_path, severity="WARNING", score=-1.0, minutos_atras=2)
        _inserir_evento(db_path, severity="CRITICAL", score=-5.0, minutos_atras=4)
        _inserir_evento(db_path, severity="INFO", score=1.0, minutos_atras=6)

        servico = MacroGuardianReaderService()
        resultado = servico.ler_snapshot(db_path)

        assert resultado.alertas_ativos == 2

    def test_snapshot_ignora_eventos_fora_do_lookback(self) -> None:
        """Deve ignorar eventos fora do periodo de lookback."""
        db_path = _criar_db_vazio()
        # Evento de 2 horas atras — fora do lookback padrao de 30 min
        _inserir_evento(db_path, severity="CRITICAL", kill_switch=True, minutos_atras=120)

        servico = MacroGuardianReaderService()
        resultado = servico.ler_snapshot(db_path, lookback_minutes=30)

        assert resultado.kill_switch_ativo is False
        assert resultado.alertas_ativos == 0


# ─────────────────────────────────────────────────────────────────
# Testes: verificar_kill_switch
# ─────────────────────────────────────────────────────────────────


class TestVerificarKillSwitch:
    """Testes para MacroGuardianReaderService.verificar_kill_switch()."""

    def test_retorna_false_quando_kill_switch_inativo(self) -> None:
        """Deve retornar (False, '') quando nenhum kill switch ativo."""
        db_path = _criar_db_vazio()
        _inserir_evento(db_path, severity="INFO", kill_switch=False, score=1.0)

        servico = MacroGuardianReaderService()
        ativo, motivo = servico.verificar_kill_switch(db_path)

        assert ativo is False
        assert isinstance(motivo, str)

    def test_retorna_true_quando_kill_switch_ativo(self) -> None:
        """Deve retornar (True, motivo) quando kill switch ativo no banco."""
        db_path = _criar_db_vazio()
        _inserir_evento(db_path, severity="CRITICAL", kill_switch=True, score=-9.0)

        servico = MacroGuardianReaderService()
        ativo, motivo = servico.verificar_kill_switch(db_path)

        assert ativo is True
        assert isinstance(motivo, str)
        assert len(motivo) > 0

    def test_retorna_tupla_com_banco_vazio(self) -> None:
        """Deve retornar (False, '') com seguranca quando banco esta vazio."""
        db_path = _criar_db_vazio()

        servico = MacroGuardianReaderService()
        resultado = servico.verificar_kill_switch(db_path)

        assert isinstance(resultado, tuple)
        assert len(resultado) == 2
        assert resultado[0] is False
        assert isinstance(resultado[1], str)


# ─────────────────────────────────────────────────────────────────
# Testes: enriquecer_episodio
# ─────────────────────────────────────────────────────────────────


class TestEnriquecerEpisodio:
    """Testes para MacroGuardianReaderService.enriquecer_episodio()."""

    def test_adiciona_quatro_campos_macro_ao_episodio(self) -> None:
        """Deve adicionar os 4 campos macro obrigatorios ao dict de episodio."""
        db_path = _criar_db_vazio()
        _inserir_evento(db_path, severity="WARNING", score=-2.0)

        episodio: dict[str, Any] = {
            "session_id": "sess_001",
            "resultado_pts": 5.0,
            "direcao": "COMPRA",
        }

        servico = MacroGuardianReaderService()
        resultado = servico.enriquecer_episodio(episodio, db_path)

        assert "score_guardian" in resultado
        assert "alertas_ativos_count" in resultado
        assert "regime_macro" in resultado
        assert "kill_switch_ativo_no_momento" in resultado

    def test_enriquece_preservando_campos_originais(self) -> None:
        """Deve preservar todos os campos originais do episodio."""
        db_path = _criar_db_vazio()

        episodio: dict[str, Any] = {
            "session_id": "sess_002",
            "resultado_pts": -3.0,
            "direcao": "VENDA",
            "campo_extra": "valor",
        }

        servico = MacroGuardianReaderService()
        resultado = servico.enriquecer_episodio(episodio, db_path)

        assert resultado["session_id"] == "sess_002"
        assert resultado["resultado_pts"] == -3.0
        assert resultado["direcao"] == "VENDA"
        assert resultado["campo_extra"] == "valor"

    def test_enriquece_com_banco_vazio_sem_excecao(self) -> None:
        """Deve enriquecer episodio sem excecao mesmo com banco vazio."""
        db_path = _criar_db_vazio()
        episodio: dict[str, Any] = {"id": 1}

        servico = MacroGuardianReaderService()
        resultado = servico.enriquecer_episodio(episodio, db_path)

        assert resultado["score_guardian"] == 0.0
        assert resultado["alertas_ativos_count"] == 0
        assert resultado["regime_macro"] == "ESTAVEL"
        assert resultado["kill_switch_ativo_no_momento"] is False

    def test_campos_macro_com_tipos_corretos(self) -> None:
        """Deve garantir tipos corretos nos campos macro adicionados."""
        db_path = _criar_db_vazio()
        _inserir_evento(db_path, severity="CRITICAL", kill_switch=True, score=-7.0)

        servico = MacroGuardianReaderService()
        resultado = servico.enriquecer_episodio({}, db_path)

        assert isinstance(resultado["score_guardian"], float)
        assert isinstance(resultado["alertas_ativos_count"], int)
        assert isinstance(resultado["regime_macro"], str)
        assert isinstance(resultado["kill_switch_ativo_no_momento"], bool)


# ─────────────────────────────────────────────────────────────────
# Testes: gerar_relatorio_semanal
# ─────────────────────────────────────────────────────────────────


class TestGerarRelatorioSemanal:
    """Testes para MacroGuardianReaderService.gerar_relatorio_semanal()."""

    def test_gera_arquivo_markdown_na_pasta_outputs(self) -> None:
        """Deve gerar arquivo .md na pasta outputs/."""
        db_path = _criar_db_vazio()
        _inserir_evento(db_path, severity="WARNING", score=-2.0, minutos_atras=10)
        _inserir_evento(db_path, severity="CRITICAL", score=-6.0, minutos_atras=20)

        with tempfile.TemporaryDirectory() as tmpdir:
            outputs_path = Path(tmpdir)
            servico = MacroGuardianReaderService()
            caminho = servico.gerar_relatorio_semanal(
                db_path,
                diary_db_path=db_path,
                semana=15,
                outputs_dir=outputs_path,
            )

            assert caminho.exists()
            assert caminho.suffix == ".md"
            assert "semana_15" in caminho.name or "15" in caminho.name

    def test_relatorio_contem_secoes_obrigatorias(self) -> None:
        """Deve conter secoes de distribuicao e correlacao no relatorio."""
        db_path = _criar_db_vazio()
        _inserir_evento(db_path, severity="WARNING", score=-1.5, minutos_atras=5)
        _criar_db_com_feedback(db_path)

        with tempfile.TemporaryDirectory() as tmpdir:
            outputs_path = Path(tmpdir)
            servico = MacroGuardianReaderService()
            caminho = servico.gerar_relatorio_semanal(
                db_path,
                diary_db_path=db_path,
                semana=10,
                outputs_dir=outputs_path,
            )

            conteudo = caminho.read_text(encoding="utf-8")
            assert "Distribuicao" in conteudo or "distribuicao" in conteudo.lower()
            assert "schema_version" in conteudo or "1.0" in conteudo

    def test_relatorio_com_banco_vazio_nao_lanca_excecao(self) -> None:
        """Deve gerar relatorio sem excecao mesmo com bancos vazios."""
        db_path = _criar_db_vazio()

        with tempfile.TemporaryDirectory() as tmpdir:
            outputs_path = Path(tmpdir)
            servico = MacroGuardianReaderService()
            caminho = servico.gerar_relatorio_semanal(
                db_path,
                diary_db_path=db_path,
                semana=1,
                outputs_dir=outputs_path,
            )

            assert caminho.exists()
            conteudo = caminho.read_text(encoding="utf-8")
            assert len(conteudo) > 0

    def test_relatorio_numero_semana_automatico_quando_nenhum_passado(self) -> None:
        """Deve usar numero de semana atual quando semana=None."""
        db_path = _criar_db_vazio()

        with tempfile.TemporaryDirectory() as tmpdir:
            outputs_path = Path(tmpdir)
            servico = MacroGuardianReaderService()
            caminho = servico.gerar_relatorio_semanal(
                db_path,
                diary_db_path=db_path,
                semana=None,
                outputs_dir=outputs_path,
            )

            assert caminho.exists()
            semana_atual = datetime.utcnow().isocalendar()[1]
            assert str(semana_atual).zfill(2) in caminho.name


# ─────────────────────────────────────────────────────────────────
# Testes: MacroGuardianSnapshotResult
# ─────────────────────────────────────────────────────────────────


class TestMacroGuardianSnapshotResult:
    """Testes para a dataclass MacroGuardianSnapshotResult."""

    def test_to_dict_retorna_dict_com_todos_campos(self) -> None:
        """Deve converter para dict com todos os campos obrigatorios."""
        snapshot = MacroGuardianSnapshotResult(
            score_guardian=-2.5,
            alertas_ativos=3,
            regime_macro="ALERTA",
            kill_switch_ativo=False,
            kill_switch_motivo="",
            total_eventos=10,
        )

        resultado = snapshot.to_dict()

        assert resultado["score_guardian"] == -2.5
        assert resultado["alertas_ativos"] == 3
        assert resultado["regime_macro"] == "ALERTA"
        assert resultado["kill_switch_ativo"] is False
        assert resultado["kill_switch_motivo"] == ""
        assert resultado["total_eventos"] == 10

    def test_to_feature_dict_retorna_apenas_numericos(self) -> None:
        """Deve retornar apenas campos numericos para uso como features ML."""
        snapshot = MacroGuardianSnapshotResult(
            score_guardian=1.5,
            alertas_ativos=0,
            regime_macro="ESTAVEL",
            kill_switch_ativo=False,
            kill_switch_motivo="",
            total_eventos=5,
        )

        features = snapshot.to_feature_dict()

        assert "score_guardian" in features
        assert "alertas_ativos" in features
        assert "kill_switch_ativo_int" in features
        assert isinstance(features["score_guardian"], float)
        assert isinstance(features["alertas_ativos"], int)
        assert features["kill_switch_ativo_int"] in (0, 1)
