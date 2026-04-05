"""Testes unitarios para ModelSyncManager (BLID-039).

Suite de testes RED-first para hot-reload de modelo entre agentes paralelos.

Estrategia de teste:
- Mock de filesystem (tmp_path do pytest)
- Mock de threading para controle de polling
- Validacao de callbacks, marker file e logging
"""

from __future__ import annotations

import json
import threading
import time
from pathlib import Path
from typing import Any
from unittest.mock import MagicMock, patch, call

import pytest

from src.application.model_sync_manager import (
    EventoSincronizacao,
    ModelSyncManager,
    ConfiguracaoSync,
    StatusSync,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture()
def diretorio_modelos(tmp_path: Path) -> Path:
    """Cria estrutura de diretorios de modelos temporarios."""
    dir_modelo = tmp_path / "models" / "novo_agente_rl" / "modelo_final"
    dir_modelo.mkdir(parents=True)
    return dir_modelo


@pytest.fixture()
def diretorio_marker(tmp_path: Path) -> Path:
    """Diretorio para marker file de sincronizacao."""
    dir_sync = tmp_path / "sync"
    dir_sync.mkdir(parents=True)
    return dir_sync


@pytest.fixture()
def config_sync(diretorio_modelos: Path, diretorio_marker: Path) -> ConfiguracaoSync:
    """Configuracao padrao para testes."""
    return ConfiguracaoSync(
        diretorios_modelos=[diretorio_modelos],
        caminho_marker=diretorio_marker / ".sync_marker",
        intervalo_polling=0.1,  # 100ms para testes rapidos
        id_agente="agente_teste",
    )


@pytest.fixture()
def manager(config_sync: ConfiguracaoSync) -> ModelSyncManager:
    """Instancia ModelSyncManager para testes (sem iniciar thread)."""
    return ModelSyncManager(configuracao=config_sync)


# ---------------------------------------------------------------------------
# Testes de ConfiguracaoSync
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_configuracao_sync_valores_padrao(diretorio_modelos: Path) -> None:
    """ConfiguracaoSync deve aceitar valores padrao sensiveis."""
    config = ConfiguracaoSync(
        diretorios_modelos=[diretorio_modelos],
        caminho_marker=diretorio_modelos / ".sync_marker",
    )

    assert config.intervalo_polling == 30.0
    assert config.id_agente == "agente_principal"
    assert config.max_eventos_historico == 100


@pytest.mark.unit
def test_configuracao_sync_valores_customizados(
    diretorio_modelos: Path, diretorio_marker: Path
) -> None:
    """ConfiguracaoSync deve aceitar valores customizados."""
    config = ConfiguracaoSync(
        diretorios_modelos=[diretorio_modelos],
        caminho_marker=diretorio_marker / ".sync_marker",
        intervalo_polling=15.0,
        id_agente="agente_rl_5000",
        max_eventos_historico=50,
    )

    assert config.intervalo_polling == 15.0
    assert config.id_agente == "agente_rl_5000"
    assert config.max_eventos_historico == 50


@pytest.mark.unit
def test_configuracao_sync_intervalo_invalido(diretorio_modelos: Path) -> None:
    """ConfiguracaoSync deve rejeitar intervalo de polling <= 0."""
    with pytest.raises(ValueError, match="intervalo_polling"):
        ConfiguracaoSync(
            diretorios_modelos=[diretorio_modelos],
            caminho_marker=diretorio_modelos / ".sync_marker",
            intervalo_polling=0.0,
        )


@pytest.mark.unit
def test_configuracao_sync_lista_vazia() -> None:
    """ConfiguracaoSync deve rejeitar lista vazia de diretorios."""
    with pytest.raises(ValueError, match="diretorios_modelos"):
        ConfiguracaoSync(
            diretorios_modelos=[],
            caminho_marker=Path("/tmp/.sync_marker"),
        )


# ---------------------------------------------------------------------------
# Testes de EventoSincronizacao
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_evento_sincronizacao_criacao(diretorio_modelos: Path) -> None:
    """EventoSincronizacao deve armazenar os campos corretamente."""
    evento = EventoSincronizacao(
        caminho_modelo=diretorio_modelos,
        id_agente_origem="agente_rl_5000",
        timestamp_iso="2026-05-01T10:00:00",
        mtime_anterior=1000.0,
        mtime_novo=2000.0,
    )

    assert evento.caminho_modelo == diretorio_modelos
    assert evento.id_agente_origem == "agente_rl_5000"
    assert evento.timestamp_iso == "2026-05-01T10:00:00"
    assert evento.mtime_anterior == 1000.0
    assert evento.mtime_novo == 2000.0


@pytest.mark.unit
def test_evento_sincronizacao_para_dict(diretorio_modelos: Path) -> None:
    """EventoSincronizacao.para_dict() deve retornar dict serializavel."""
    evento = EventoSincronizacao(
        caminho_modelo=diretorio_modelos,
        id_agente_origem="agente_teste",
        timestamp_iso="2026-05-01T10:00:00",
        mtime_anterior=1000.0,
        mtime_novo=2000.0,
    )

    resultado = evento.para_dict()

    assert isinstance(resultado, dict)
    assert resultado["caminho_modelo"] == str(diretorio_modelos)
    assert resultado["id_agente_origem"] == "agente_teste"
    assert resultado["timestamp_iso"] == "2026-05-01T10:00:00"
    assert resultado["mtime_anterior"] == 1000.0
    assert resultado["mtime_novo"] == 2000.0


# ---------------------------------------------------------------------------
# Testes de StatusSync
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_status_sync_inicial(manager: ModelSyncManager) -> None:
    """Status inicial deve indicar parado com zero eventos."""
    status = manager.obter_status()

    assert isinstance(status, StatusSync)
    assert status.ativo is False
    assert status.total_eventos == 0
    assert status.ultimo_evento is None
    assert status.id_agente == "agente_teste"


# ---------------------------------------------------------------------------
# Testes de registro de callback
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_registrar_callback_unico(manager: ModelSyncManager) -> None:
    """Deve aceitar registro de um callback."""
    callback = MagicMock()
    manager.registrar_callback(callback)

    assert manager.obter_total_callbacks() == 1


@pytest.mark.unit
def test_registrar_multiplos_callbacks(manager: ModelSyncManager) -> None:
    """Deve aceitar multiplos callbacks registrados."""
    cb1 = MagicMock()
    cb2 = MagicMock()
    cb3 = MagicMock()

    manager.registrar_callback(cb1)
    manager.registrar_callback(cb2)
    manager.registrar_callback(cb3)

    assert manager.obter_total_callbacks() == 3


@pytest.mark.unit
def test_remover_callback(manager: ModelSyncManager) -> None:
    """Deve permitir remover callback registrado."""
    callback = MagicMock()
    manager.registrar_callback(callback)
    manager.remover_callback(callback)

    assert manager.obter_total_callbacks() == 0


@pytest.mark.unit
def test_remover_callback_inexistente_nao_levanta_excecao(
    manager: ModelSyncManager,
) -> None:
    """Remover callback nao registrado nao deve levantar excecao."""
    callback = MagicMock()
    manager.remover_callback(callback)  # nao deve lancar excecao


# ---------------------------------------------------------------------------
# Testes de deteccao de mudanca de modelo
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_detectar_mudanca_quando_mtime_aumenta(
    manager: ModelSyncManager, diretorio_modelos: Path
) -> None:
    """Deve detectar mudanca quando mtime do diretorio aumenta."""
    # Inicializa baseline de mtimes via metodo publico
    mtime_inicial = diretorio_modelos.stat().st_mtime
    manager.definir_mtime_baseline({diretorio_modelos: mtime_inicial})

    # Simula mudanca: escreve arquivo novo no diretorio
    (diretorio_modelos / "model.pkl").write_bytes(b"modelo_binario")

    eventos = manager._verificar_mudancas()

    assert len(eventos) == 1
    assert eventos[0].caminho_modelo == diretorio_modelos


@pytest.mark.unit
def test_nao_detectar_mudanca_sem_alteracao(
    manager: ModelSyncManager, diretorio_modelos: Path
) -> None:
    """Nao deve detectar mudanca se mtime nao alterou."""
    mtime_atual = diretorio_modelos.stat().st_mtime
    manager.definir_mtime_baseline({diretorio_modelos: mtime_atual})

    eventos = manager._verificar_mudancas()

    assert len(eventos) == 0


@pytest.mark.unit
def test_detectar_mudanca_multiplos_diretorios(
    tmp_path: Path,
) -> None:
    """Deve detectar mudancas em multiplos diretorios monitorados."""
    dir1 = tmp_path / "models" / "agente1"
    dir2 = tmp_path / "models" / "agente2"
    dir1.mkdir(parents=True)
    dir2.mkdir(parents=True)

    config = ConfiguracaoSync(
        diretorios_modelos=[dir1, dir2],
        caminho_marker=tmp_path / ".sync_marker",
        intervalo_polling=0.1,
        id_agente="teste",
    )
    mgr = ModelSyncManager(configuracao=config)

    mtime1 = dir1.stat().st_mtime
    mtime2 = dir2.stat().st_mtime
    mgr.definir_mtime_baseline({dir1: mtime1, dir2: mtime2})

    # Altera apenas dir1
    (dir1 / "model.pkl").write_bytes(b"v2")

    eventos = mgr._verificar_mudancas()

    assert len(eventos) == 1
    assert eventos[0].caminho_modelo == dir1


# ---------------------------------------------------------------------------
# Testes de marker file
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_escrever_marker_file(
    manager: ModelSyncManager, diretorio_modelos: Path, diretorio_marker: Path
) -> None:
    """Deve escrever marker file JSON valido apos mudanca detectada."""
    evento = EventoSincronizacao(
        caminho_modelo=diretorio_modelos,
        id_agente_origem="agente_teste",
        timestamp_iso="2026-05-01T10:00:00",
        mtime_anterior=1000.0,
        mtime_novo=2000.0,
    )

    manager._escrever_marker(evento)

    caminho_marker = diretorio_marker / ".sync_marker"
    assert caminho_marker.exists()

    conteudo = json.loads(caminho_marker.read_text())
    assert conteudo["id_agente_origem"] == "agente_teste"
    assert conteudo["caminho_modelo"] == str(diretorio_modelos)
    assert conteudo["timestamp_iso"] == "2026-05-01T10:00:00"


@pytest.mark.unit
def test_ler_marker_file_existente(
    manager: ModelSyncManager, diretorio_marker: Path
) -> None:
    """Deve ler marker file existente e retornar dict."""
    caminho_marker = diretorio_marker / ".sync_marker"
    dados = {
        "id_agente_origem": "agente_externo",
        "caminho_modelo": "/data/models/novo_agente_rl",
        "timestamp_iso": "2026-05-01T09:00:00",
        "mtime_anterior": 500.0,
        "mtime_novo": 600.0,
    }
    caminho_marker.write_text(json.dumps(dados))

    resultado = manager._ler_marker()

    assert resultado is not None
    assert resultado["id_agente_origem"] == "agente_externo"


@pytest.mark.unit
def test_ler_marker_file_inexistente(manager: ModelSyncManager) -> None:
    """Deve retornar None quando marker file nao existe."""
    resultado = manager._ler_marker()

    assert resultado is None


@pytest.mark.unit
def test_ler_marker_file_corrompido(
    manager: ModelSyncManager, diretorio_marker: Path
) -> None:
    """Deve retornar None quando marker file esta corrompido."""
    caminho_marker = diretorio_marker / ".sync_marker"
    caminho_marker.write_text("json_invalido{{{")

    resultado = manager._ler_marker()

    assert resultado is None


# ---------------------------------------------------------------------------
# Testes de disparo de callbacks
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_disparar_callbacks_ao_detectar_mudanca(
    manager: ModelSyncManager, diretorio_modelos: Path
) -> None:
    """Callbacks devem ser chamados com EventoSincronizacao ao detectar mudanca."""
    callback = MagicMock()
    manager.registrar_callback(callback)

    evento = EventoSincronizacao(
        caminho_modelo=diretorio_modelos,
        id_agente_origem="agente_teste",
        timestamp_iso="2026-05-01T10:00:00",
        mtime_anterior=1000.0,
        mtime_novo=2000.0,
    )

    manager._disparar_callbacks(evento)

    callback.assert_called_once_with(evento)


@pytest.mark.unit
def test_disparar_callbacks_multiplos(
    manager: ModelSyncManager, diretorio_modelos: Path
) -> None:
    """Todos os callbacks devem ser chamados ao detectar mudanca."""
    cb1 = MagicMock()
    cb2 = MagicMock()
    manager.registrar_callback(cb1)
    manager.registrar_callback(cb2)

    evento = EventoSincronizacao(
        caminho_modelo=diretorio_modelos,
        id_agente_origem="agente_teste",
        timestamp_iso="2026-05-01T10:00:00",
        mtime_anterior=1000.0,
        mtime_novo=2000.0,
    )

    manager._disparar_callbacks(evento)

    cb1.assert_called_once_with(evento)
    cb2.assert_called_once_with(evento)


@pytest.mark.unit
def test_callback_com_excecao_nao_para_outros(
    manager: ModelSyncManager, diretorio_modelos: Path
) -> None:
    """Excecao em callback nao deve impedir execucao dos demais callbacks."""
    cb_falha = MagicMock(side_effect=RuntimeError("erro no callback"))
    cb_ok = MagicMock()

    manager.registrar_callback(cb_falha)
    manager.registrar_callback(cb_ok)

    evento = EventoSincronizacao(
        caminho_modelo=diretorio_modelos,
        id_agente_origem="agente_teste",
        timestamp_iso="2026-05-01T10:00:00",
        mtime_anterior=1000.0,
        mtime_novo=2000.0,
    )

    manager._disparar_callbacks(evento)  # nao deve levantar excecao

    cb_ok.assert_called_once_with(evento)


# ---------------------------------------------------------------------------
# Testes de historico de eventos
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_historico_de_eventos_acumula(
    manager: ModelSyncManager, diretorio_modelos: Path
) -> None:
    """Historico de eventos deve acumular conforme mudancas sao detectadas."""
    evento = EventoSincronizacao(
        caminho_modelo=diretorio_modelos,
        id_agente_origem="agente_teste",
        timestamp_iso="2026-05-01T10:00:00",
        mtime_anterior=1000.0,
        mtime_novo=2000.0,
    )

    manager._registrar_evento(evento)
    manager._registrar_evento(evento)

    status = manager.obter_status()
    assert status.total_eventos == 2


@pytest.mark.unit
def test_historico_de_eventos_limitado(
    manager: ModelSyncManager, diretorio_modelos: Path
) -> None:
    """Historico de eventos deve ser limitado ao max_eventos_historico."""
    max_eventos = manager._config.max_eventos_historico

    for i in range(max_eventos + 10):
        evento = EventoSincronizacao(
            caminho_modelo=diretorio_modelos,
            id_agente_origem="agente_teste",
            timestamp_iso=f"2026-05-01T10:00:{i:02d}",
            mtime_anterior=float(i),
            mtime_novo=float(i + 1),
        )
        manager._registrar_evento(evento)

    assert len(manager._historico_eventos) <= max_eventos


@pytest.mark.unit
def test_ultimo_evento_atualizado(
    manager: ModelSyncManager, diretorio_modelos: Path
) -> None:
    """obter_status() deve retornar o ultimo evento registrado."""
    evento = EventoSincronizacao(
        caminho_modelo=diretorio_modelos,
        id_agente_origem="agente_teste",
        timestamp_iso="2026-05-01T12:00:00",
        mtime_anterior=1000.0,
        mtime_novo=2000.0,
    )
    manager._registrar_evento(evento)

    status = manager.obter_status()

    assert status.ultimo_evento is not None
    assert status.ultimo_evento.timestamp_iso == "2026-05-01T12:00:00"


# ---------------------------------------------------------------------------
# Testes de ciclo de vida (iniciar/parar)
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_iniciar_marca_ativo(manager: ModelSyncManager) -> None:
    """iniciar() deve marcar o manager como ativo."""
    try:
        manager.iniciar()
        assert manager.obter_status().ativo is True
    finally:
        manager.parar()


@pytest.mark.unit
def test_parar_marca_inativo(manager: ModelSyncManager) -> None:
    """parar() deve marcar o manager como inativo."""
    manager.iniciar()
    manager.parar()

    assert manager.obter_status().ativo is False


@pytest.mark.unit
def test_iniciar_duas_vezes_nao_duplica_thread(manager: ModelSyncManager) -> None:
    """Chamar iniciar() duas vezes nao deve criar thread duplicada."""
    try:
        manager.iniciar()
        threads_antes = threading.active_count()
        manager.iniciar()  # segunda chamada - deve ser no-op
        threads_depois = threading.active_count()

        assert threads_depois == threads_antes
    finally:
        manager.parar()


@pytest.mark.unit
def test_parar_sem_iniciar_nao_levanta_excecao(manager: ModelSyncManager) -> None:
    """parar() sem iniciar() nao deve levantar excecao."""
    manager.parar()  # nao deve levantar excecao


# ---------------------------------------------------------------------------
# Testes de integracao de polling com filesystem
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_polling_detecta_novo_arquivo(
    config_sync: ConfiguracaoSync, diretorio_modelos: Path
) -> None:
    """Polling deve detectar criacao de arquivo no diretorio monitorado."""
    eventos_capturados: list[EventoSincronizacao] = []
    evento_detectado = threading.Event()

    def callback_captura(evento: EventoSincronizacao) -> None:
        eventos_capturados.append(evento)
        evento_detectado.set()

    mgr = ModelSyncManager(configuracao=config_sync)
    mgr.registrar_callback(callback_captura)

    try:
        mgr.iniciar()
        time.sleep(0.05)  # aguarda inicializacao da thread

        # Cria arquivo para simular novo modelo
        (diretorio_modelos / "modelo_v2.pkl").write_bytes(b"novo_modelo")

        # Aguarda o callback ser invocado (timeout 3s)
        detectado = evento_detectado.wait(timeout=3.0)

        assert detectado, "Callback nao foi invocado dentro do timeout"
        assert len(eventos_capturados) >= 1
        assert eventos_capturados[0].caminho_modelo == diretorio_modelos
    finally:
        mgr.parar()


@pytest.mark.unit
def test_obter_historico_retorna_copia(
    manager: ModelSyncManager, diretorio_modelos: Path
) -> None:
    """obter_historico_eventos() deve retornar copia imutavel da lista."""
    evento = EventoSincronizacao(
        caminho_modelo=diretorio_modelos,
        id_agente_origem="agente_teste",
        timestamp_iso="2026-05-01T10:00:00",
        mtime_anterior=1000.0,
        mtime_novo=2000.0,
    )
    manager._registrar_evento(evento)

    historico = manager.obter_historico_eventos()
    historico.append(evento)  # modifica copia

    # Lista interna nao deve ser alterada
    assert len(manager._historico_eventos) == 1


@pytest.mark.unit
def test_inicializar_mtimes_para_diretorios_inexistentes(
    tmp_path: Path,
) -> None:
    """Diretorios inexistentes nao devem causar crash na inicializacao."""
    dir_inexistente = tmp_path / "nao_existe" / "modelo"

    config = ConfiguracaoSync(
        diretorios_modelos=[dir_inexistente],
        caminho_marker=tmp_path / ".sync_marker",
        intervalo_polling=0.1,
        id_agente="teste",
    )
    mgr = ModelSyncManager(configuracao=config)

    # Iniciar sem criar o diretorio — nao deve lancar excecao
    mgr.iniciar()
    mgr.parar()

    # Diretorio inexistente nao deve ter entrada no baseline
    status = mgr.obter_status()
    assert status.total_eventos == 0
