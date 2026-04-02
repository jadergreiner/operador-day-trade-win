"""Testes estendidos — Painel de Observabilidade de Diarios v1.1.

Cobre funcionalidades canonicas: mapeamento de 5 threads, maquina de
estados, persistencia SQLite, exportacao JSON atomica e alertas de
inatividade com janela operacional.

Suite TDD conforme handoff QA/TDD: PO-2026-04-02-ROADMAP-DIARIOS-01.
"""

from __future__ import annotations

import datetime
import json
import logging
import sqlite3
from pathlib import Path
from unittest.mock import patch

import pytest

from src.application.diario_observability_panel import (
    MAPEAMENTO_THREADS_CANONICO,
    TIPO_APENAS_HEARTBEAT,
    TIPO_GRAVACAO_E_HEARTBEAT,
    ConfiguracaoMonitoramento,
    EventoObservabilidadeDiario,
    ObservabilidadeDiarios,
    SnapshotSaudeDiario,
    StatusDiarioEstendido,
)


# ─────────────────────────────────────────────────────────────────
# Fixtures
# ─────────────────────────────────────────────────────────────────


@pytest.fixture
def painel_canonico(tmp_path: Path) -> ObservabilidadeDiarios:
    """Painel canonico com banco temporario isolado."""
    db = tmp_path / "test_watchdog.db"
    json_saida = tmp_path / "status.json"
    return ObservabilidadeDiarios(
        caminho_banco=db,
        caminho_json=json_saida,
        janela_operacional=("00:00", "23:59"),
    )


@pytest.fixture
def painel_fora_janela(tmp_path: Path) -> ObservabilidadeDiarios:
    """Painel com janela operacional que nunca inclui o horario atual."""
    db = tmp_path / "fora.db"
    return ObservabilidadeDiarios(
        caminho_banco=db,
        caminho_json=tmp_path / "status.json",
        janela_operacional=("00:00", "00:01"),
    )


@pytest.fixture
def painel_banco_invalido(tmp_path: Path) -> ObservabilidadeDiarios:
    """Painel cujo caminho de banco e invalido (fail-open)."""
    return ObservabilidadeDiarios(
        caminho_banco=Path("/caminho/impossivel/nao_existe/db.db"),
        caminho_json=tmp_path / "status.json",
        janela_operacional=("00:00", "23:59"),
    )


# ─────────────────────────────────────────────────────────────────
# Fase 1 — Mapeamento canonico
# ─────────────────────────────────────────────────────────────────


def test_mapeamento_canonico_contem_exatamente_5_threads() -> None:
    """MAPEAMENTO_THREADS_CANONICO deve ter exatamente 5 entradas."""
    assert len(MAPEAMENTO_THREADS_CANONICO) == 5


def test_mapeamento_canonico_nomes_esperados() -> None:
    """Os 5 nomes canonicos devem estar presentes."""
    nomes = set(MAPEAMENTO_THREADS_CANONICO.keys())
    esperados = {
        "TradingJournal",
        "AIReflection",
        "RLDiary",
        "MacroGuardian",
        "DiarioExecucao",
    }
    assert nomes == esperados


def test_diario_execucao_tipo_apenas_heartbeat() -> None:
    """DiarioExecucao deve ter tipo APENAS_HEARTBEAT."""
    cfg = MAPEAMENTO_THREADS_CANONICO["DiarioExecucao"]
    assert cfg.tipo_monitoramento == TIPO_APENAS_HEARTBEAT


def test_threads_gravacao_tipo_gravacao_e_heartbeat() -> None:
    """TradingJournal, AIReflection, RLDiary e MacroGuardian devem ser GRAVACAO_E_HEARTBEAT."""
    for nome in ("TradingJournal", "AIReflection", "RLDiary", "MacroGuardian"):
        cfg = MAPEAMENTO_THREADS_CANONICO[nome]
        assert cfg.tipo_monitoramento == TIPO_GRAVACAO_E_HEARTBEAT, nome


# ─────────────────────────────────────────────────────────────────
# Fase 2 — Dataclasses
# ─────────────────────────────────────────────────────────────────


def test_evento_observabilidade_frozen_imutavel() -> None:
    """EventoObservabilidadeDiario deve ser frozen — setattr deve falhar."""
    from dataclasses import FrozenInstanceError

    evento = EventoObservabilidadeDiario(
        session_id="sid",
        nome_thread="TradingJournal",
        evento="GRAVACAO",
        estado_resultante="rodando",
        mensagem=None,
        stack_trace=None,
        gravacoes_sessao=1,
        timestamp=datetime.datetime.now(),
    )
    with pytest.raises(FrozenInstanceError):
        evento.evento = "FALHA"  # type: ignore[misc]


def test_evento_observabilidade_campos_obrigatorios() -> None:
    """EventoObservabilidadeDiario deve armazenar todos os campos corretamente."""
    ts = datetime.datetime(2026, 4, 2, 10, 0, 0)
    evento = EventoObservabilidadeDiario(
        session_id="abc-123",
        nome_thread="RLDiary",
        evento="FALHA",
        estado_resultante="com_erro",
        mensagem="msg",
        stack_trace="Traceback...",
        gravacoes_sessao=5,
        timestamp=ts,
    )
    assert evento.session_id == "abc-123"
    assert evento.nome_thread == "RLDiary"
    assert evento.evento == "FALHA"
    assert evento.estado_resultante == "com_erro"
    assert evento.mensagem == "msg"
    assert evento.stack_trace == "Traceback..."
    assert evento.gravacoes_sessao == 5
    assert evento.timestamp == ts


def test_evento_observabilidade_stack_trace_opcional() -> None:
    """stack_trace pode ser None sem erro."""
    evento = EventoObservabilidadeDiario(
        session_id="s",
        nome_thread="AIReflection",
        evento="HEARTBEAT",
        estado_resultante="rodando",
        mensagem=None,
        stack_trace=None,
        gravacoes_sessao=0,
        timestamp=datetime.datetime.now(),
    )
    assert evento.stack_trace is None


def test_snapshot_saude_para_dict_tem_campos_obrigatorios() -> None:
    """SnapshotSaudeDiario.para_dict() deve retornar session_id, timestamp e threads."""
    snapshot = SnapshotSaudeDiario(
        session_id="sess-xyz",
        timestamp_exportacao=datetime.datetime(2026, 4, 2, 9, 30),
    )
    d = snapshot.para_dict()
    assert "session_id" in d
    assert "timestamp_exportacao" in d
    assert "threads" in d
    assert d["session_id"] == "sess-xyz"


def test_snapshot_saude_threads_serializavel(
    painel_canonico: ObservabilidadeDiarios,
) -> None:
    """Snapshot gerado pelo painel deve ser JSON-serializavel sem erro."""
    snapshot = painel_canonico.gerar_snapshot_operacional()
    payload = snapshot.para_dict()
    serializado = json.dumps(payload)  # nao deve lancar excecao
    parsed = json.loads(serializado)
    assert "threads" in parsed


def test_configuracao_monitoramento_frozen() -> None:
    """ConfiguracaoMonitoramento deve ser frozen — setattr deve falhar."""
    from dataclasses import FrozenInstanceError

    cfg = ConfiguracaoMonitoramento(
        nome_logico="LOG",
        cadencia_min=5,
        threshold_alerta_min=20,
        tipo_monitoramento=TIPO_GRAVACAO_E_HEARTBEAT,
    )
    with pytest.raises(FrozenInstanceError):
        cfg.cadencia_min = 99  # type: ignore[misc]


def test_configuracao_monitoramento_threshold_alerta() -> None:
    """threshold_alerta_min deve refletir o valor passado."""
    cfg = ConfiguracaoMonitoramento(
        nome_logico="T",
        cadencia_min=10,
        threshold_alerta_min=30,
        tipo_monitoramento=TIPO_APENAS_HEARTBEAT,
    )
    assert cfg.threshold_alerta_min == 30


def test_configuracao_monitoramento_tipo_monitoramento() -> None:
    """tipo_monitoramento deve ser TIPO_APENAS_HEARTBEAT quando configurado."""
    cfg = MAPEAMENTO_THREADS_CANONICO["DiarioExecucao"]
    assert cfg.tipo_monitoramento == TIPO_APENAS_HEARTBEAT


# ─────────────────────────────────────────────────────────────────
# Fase 3 — ObservabilidadeDiarios estendida
# ─────────────────────────────────────────────────────────────────


def test_painel_canonico_tem_5_threads_no_status_estendido(
    painel_canonico: ObservabilidadeDiarios,
) -> None:
    """_status_estendido deve ter 5 threads canonicas inicializadas."""
    assert len(painel_canonico._status_estendido) == 5  # noqa: SLF001


def test_session_id_gerado_automaticamente(
    painel_canonico: ObservabilidadeDiarios,
) -> None:
    """Cada painel deve ter session_id unico nao vazio."""
    assert painel_canonico._session_id  # noqa: SLF001
    assert len(painel_canonico._session_id) > 10


def test_registrar_gravacao_canonico_incrementa_contador(
    painel_canonico: ObservabilidadeDiarios,
) -> None:
    """registrar_gravacao com nome canonico deve incrementar total_registros_sessao."""
    painel_canonico.registrar_gravacao("TradingJournal")
    status = painel_canonico._status_estendido["TradingJournal"]  # noqa: SLF001
    assert status.total_registros_sessao == 1


def test_registrar_gravacao_atualiza_ultimo_registro(
    painel_canonico: ObservabilidadeDiarios,
) -> None:
    """registrar_gravacao deve atualizar ultimo_registro para o canonico."""
    antes = datetime.datetime.now()
    painel_canonico.registrar_gravacao("AIReflection")
    status = painel_canonico._status_estendido["AIReflection"]  # noqa: SLF001
    assert status.ultimo_registro is not None
    assert status.ultimo_registro >= antes


def test_registrar_heartbeat_nao_incrementa_gravacoes(
    painel_canonico: ObservabilidadeDiarios,
) -> None:
    """registrar_heartbeat NAO deve incrementar total_registros_sessao."""
    painel_canonico.registrar_heartbeat("TradingJournal")
    status = painel_canonico._status_estendido["TradingJournal"]  # noqa: SLF001
    assert status.total_registros_sessao == 0


def test_registrar_heartbeat_atualiza_ultimo_heartbeat(
    painel_canonico: ObservabilidadeDiarios,
) -> None:
    """registrar_heartbeat deve atualizar ultimo_heartbeat."""
    antes = datetime.datetime.now()
    painel_canonico.registrar_heartbeat("DiarioExecucao")
    status = painel_canonico._status_estendido["DiarioExecucao"]  # noqa: SLF001
    assert status.ultimo_heartbeat is not None
    assert status.ultimo_heartbeat >= antes


def test_nome_canonico_invalido_levanta_value_error(
    painel_canonico: ObservabilidadeDiarios,
) -> None:
    """Nome canonico desconhecido deve levantar ValueError."""
    with pytest.raises(ValueError, match="nao reconhecida"):
        painel_canonico.registrar_heartbeat("NomeInexistente")


def test_nome_legado_ignorado_silenciosamente(
    painel_canonico: ObservabilidadeDiarios,
) -> None:
    """Nome legado desconhecido deve ser ignorado sem excecao."""
    painel_canonico.registrar_gravacao("NOME_INEXISTENTE_LEGADO")  # sem excecao


# ─────────────────────────────────────────────────────────────────
# Fase 4 — Maquina de estados
# ─────────────────────────────────────────────────────────────────


def test_estado_inicial_none(painel_canonico: ObservabilidadeDiarios) -> None:
    """Estado inicial de cada thread deve ser None (aguardando_sinal)."""
    for nome, status in painel_canonico._status_estendido.items():  # noqa: SLF001
        assert status.estado is None, f"Thread '{nome}' nao comecou com None"


def test_heartbeat_transiciona_none_para_rodando(
    painel_canonico: ObservabilidadeDiarios,
) -> None:
    """Primeiro heartbeat deve transicionar None -> rodando."""
    painel_canonico.registrar_heartbeat("TradingJournal")
    assert (
        painel_canonico._status_estendido["TradingJournal"].estado  # noqa: SLF001
        == "rodando"
    )


def test_gravacao_transiciona_para_rodando(
    painel_canonico: ObservabilidadeDiarios,
) -> None:
    """Primeira gravacao deve deixar a thread em estado rodando."""
    painel_canonico.registrar_gravacao("RLDiary")
    assert (
        painel_canonico._status_estendido["RLDiary"].estado  # noqa: SLF001
        == "rodando"
    )


def test_falha_transiciona_para_com_erro(
    painel_canonico: ObservabilidadeDiarios,
) -> None:
    """registrar_falha deve colocar thread em com_erro."""
    exc = RuntimeError("crash")
    painel_canonico.registrar_falha("AIReflection", exc, "Traceback...")
    assert (
        painel_canonico._status_estendido["AIReflection"].estado  # noqa: SLF001
        == "com_erro"
    )


def test_reinicio_transiciona_com_erro_para_reiniciando(
    painel_canonico: ObservabilidadeDiarios,
) -> None:
    """registrar_reinicio deve transicionar com_erro -> reiniciando."""
    exc = RuntimeError("crash")
    painel_canonico.registrar_falha("MacroGuardian", exc, None)
    painel_canonico.registrar_reinicio("MacroGuardian")
    assert (
        painel_canonico._status_estendido["MacroGuardian"].estado  # noqa: SLF001
        == "reiniciando"
    )


def test_heartbeat_apos_reinicio_transiciona_para_rodando(
    painel_canonico: ObservabilidadeDiarios,
) -> None:
    """Heartbeat em estado reiniciando deve ir para rodando."""
    exc = ValueError("x")
    painel_canonico.registrar_falha("RLDiary", exc, None)
    painel_canonico.registrar_reinicio("RLDiary")
    painel_canonico.registrar_heartbeat("RLDiary")
    assert (
        painel_canonico._status_estendido["RLDiary"].estado  # noqa: SLF001
        == "rodando"
    )


def test_com_erro_nao_transiciona_para_rodando_sem_reinicio(
    painel_canonico: ObservabilidadeDiarios,
) -> None:
    """Heartbeat em com_erro NAO deve mudar estado para rodando."""
    exc = ConnectionError("lost")
    painel_canonico.registrar_falha("AIReflection", exc, None)
    painel_canonico.registrar_heartbeat("AIReflection")
    assert (
        painel_canonico._status_estendido["AIReflection"].estado  # noqa: SLF001
        == "com_erro"
    )


# ─────────────────────────────────────────────────────────────────
# Fase 5 — Alertas de inatividade
# ─────────────────────────────────────────────────────────────────


def test_alertas_canonico_retorna_vazio_sem_gravacoes(
    painel_canonico: ObservabilidadeDiarios,
) -> None:
    """Sem nenhuma gravacao, nenhuma thread deve emitir alerta."""
    alertas = painel_canonico.verificar_alertas_inatividade_canonico()
    assert alertas == []


def test_alertas_canonico_detecta_thread_inativa(
    painel_canonico: ObservabilidadeDiarios,
) -> None:
    """Thread com ultimo_registro antigo deve aparecer nos alertas."""
    status = painel_canonico._status_estendido["TradingJournal"]  # noqa: SLF001
    status.ultimo_registro = datetime.datetime.now() - datetime.timedelta(
        minutes=30
    )
    alertas = painel_canonico.verificar_alertas_inatividade_canonico()
    assert "TradingJournal" in alertas


def test_diario_execucao_nunca_alerta(
    painel_canonico: ObservabilidadeDiarios,
) -> None:
    """DiarioExecucao (APENAS_HEARTBEAT) nunca deve aparecer nos alertas."""
    status = painel_canonico._status_estendido["DiarioExecucao"]  # noqa: SLF001
    status.ultimo_registro = datetime.datetime.now() - datetime.timedelta(
        hours=5
    )
    alertas = painel_canonico.verificar_alertas_inatividade_canonico()
    assert "DiarioExecucao" not in alertas


def test_alertas_canonico_vazio_fora_janela(
    painel_fora_janela: ObservabilidadeDiarios,
) -> None:
    """Fora da janela operacional, nenhum alerta deve ser emitido."""
    for status in painel_fora_janela._status_estendido.values():  # noqa: SLF001
        status.ultimo_registro = datetime.datetime.now() - datetime.timedelta(
            hours=5
        )
    alertas = painel_fora_janela.verificar_alertas_inatividade_canonico()
    assert alertas == []


# ─────────────────────────────────────────────────────────────────
# Fase 6 — Persistencia SQLite
# ─────────────────────────────────────────────────────────────────


def test_sqlite_tabela_criada_apos_inicializacao(tmp_path: Path) -> None:
    """Tabela diarios_watchdog_eventos deve existir apos criar o painel."""
    db_path = tmp_path / "check_tabela.db"
    ObservabilidadeDiarios(caminho_banco=db_path, caminho_json=tmp_path / "s.json")
    conn = sqlite3.connect(str(db_path))
    tabelas = {r[0] for r in conn.execute("SELECT name FROM sqlite_master WHERE type='table'")}
    conn.close()
    assert "diarios_watchdog_eventos" in tabelas


def test_sqlite_gravacao_insere_registro(tmp_path: Path) -> None:
    """registrar_gravacao deve inserir registro GRAVACAO no SQLite."""
    db_path = tmp_path / "gravacao.db"
    painel = ObservabilidadeDiarios(
        caminho_banco=db_path,
        caminho_json=tmp_path / "s.json",
    )
    painel.registrar_gravacao("TradingJournal")
    conn = sqlite3.connect(str(db_path))
    rows = conn.execute(
        "SELECT evento FROM diarios_watchdog_eventos WHERE nome_thread='TradingJournal'"
    ).fetchall()
    conn.close()
    assert len(rows) >= 1
    assert rows[0][0] == "GRAVACAO"


def test_sqlite_falha_insere_stack_trace(tmp_path: Path) -> None:
    """registrar_falha deve persistir stack_trace no SQLite."""
    db_path = tmp_path / "falha.db"
    painel = ObservabilidadeDiarios(
        caminho_banco=db_path,
        caminho_json=tmp_path / "s.json",
    )
    painel.registrar_falha("AIReflection", RuntimeError("err"), "linha1\nlinha2")
    conn = sqlite3.connect(str(db_path))
    row = conn.execute(
        "SELECT stack_trace FROM diarios_watchdog_eventos WHERE evento='FALHA'"
    ).fetchone()
    conn.close()
    assert row is not None
    assert "linha1" in row[0]


def test_sqlite_session_id_isolado_entre_paineis(tmp_path: Path) -> None:
    """Dois paineis devem ter session_ids distintos nos registros."""
    db = tmp_path / "multi.db"
    p1 = ObservabilidadeDiarios(caminho_banco=db, caminho_json=tmp_path / "s1.json")
    p2 = ObservabilidadeDiarios(caminho_banco=db, caminho_json=tmp_path / "s2.json")
    p1.registrar_gravacao("TradingJournal")
    p2.registrar_gravacao("TradingJournal")
    conn = sqlite3.connect(str(db))
    ids = {r[0] for r in conn.execute("SELECT session_id FROM diarios_watchdog_eventos")}
    conn.close()
    assert len(ids) == 2


def test_fail_open_banco_invalido_nao_lanca_excecao(
    painel_banco_invalido: ObservabilidadeDiarios,
    caplog: pytest.LogCaptureFixture,
) -> None:
    """Com banco invalido, operacoes nao devem propagar excecao (fail-open)."""
    with caplog.at_level(logging.WARNING):
        painel_banco_invalido.registrar_gravacao("TradingJournal")
        painel_banco_invalido.registrar_heartbeat("DiarioExecucao")
        painel_banco_invalido.registrar_falha("RLDiary", ValueError("x"), None)
    # Nenhuma excecao deve ter sido propagada — chegar aqui e suficiente


# ─────────────────────────────────────────────────────────────────
# Fase 7 — Exportacao JSON
# ─────────────────────────────────────────────────────────────────


def test_exportar_snapshot_json_cria_arquivo(
    painel_canonico: ObservabilidadeDiarios,
    tmp_path: Path,
) -> None:
    """exportar_snapshot_json deve criar o arquivo JSON no destino."""
    destino = tmp_path / "export" / "status.json"
    painel_canonico.exportar_snapshot_json(destino)
    assert destino.exists()


def test_exportar_snapshot_json_campos_obrigatorios(
    painel_canonico: ObservabilidadeDiarios,
    tmp_path: Path,
) -> None:
    """JSON exportado deve conter session_id, timestamp_exportacao e threads."""
    destino = tmp_path / "status.json"
    painel_canonico.exportar_snapshot_json(destino)
    payload = json.loads(destino.read_text(encoding="utf-8"))
    assert "session_id" in payload
    assert "timestamp_exportacao" in payload
    assert "threads" in payload
    assert len(payload["threads"]) == 5


def test_exportar_snapshot_json_sobrescreve_sem_corromper(
    painel_canonico: ObservabilidadeDiarios,
    tmp_path: Path,
) -> None:
    """Segunda exportacao deve sobrescrever o arquivo sem corrompe-lo."""
    destino = tmp_path / "status.json"
    painel_canonico.exportar_snapshot_json(destino)
    painel_canonico.registrar_gravacao("TradingJournal")
    painel_canonico.exportar_snapshot_json(destino)
    payload = json.loads(destino.read_text(encoding="utf-8"))
    assert "session_id" in payload  # arquivo valido apos sobrescrita
