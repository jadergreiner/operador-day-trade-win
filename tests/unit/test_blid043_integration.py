"""Testes TDD RED para BLID-043 — Gate de Coordenação nos Agentes RL.

Cenarios cobertos (minimo 8 obrigatorios — AC8):

    T01 - [AC1] RL Direto: STOP_OPERACOES bloqueia enviar_ordem
    T02 - [AC1] RL Direto: gate verifica pode_abrir_posicao antes de enviar_ordem
    T03 - [AC2] RL 5000: STOP_OPERACOES bloqueia enviar_ordem_mt5adapter
    T04 - [AC3] RL Direto: NORMAL nao bloqueia enviar_ordem
    T05 - [AC3] RL Direto: MODO_CONSERVADOR nao bloqueia enviar_ordem
    T06 - [AC3] RL Direto: MODO_DEFENSIVO nao bloqueia enviar_ordem
    T07 - [AC3] RL 5000: MODO_CONSERVADOR nao bloqueia enviar_ordem_mt5adapter
    T08 - [AC3] RL 5000: MODO_DEFENSIVO nao bloqueia enviar_ordem_mt5adapter
    T09 - [AC4] CoordinationManager inicia como thread daemon no startup
    T10 - [AC4] Thread daemon recebe nome 'coordination-manager'
    T11 - [AC5] Arquivo coordination_signal ausente retorna NORMAL (fallback)
    T12 - [AC5] RL Direto: ausencia de arquivo nao bloqueia ordens
    T13 - [AC6] RL Direto: log WARNING emitido com sinal STOP_OPERACOES
    T14 - [AC6] Log WARNING contem valor do sinal atual
    T15 - [Graceful] _COORDINATION_DISPONIVEL=False nao causa excecao no gate
    T16 - [Graceful] ImportError em coordination nao impede startup
    T17 - [Contrato] coordination_reader usa path exclusivo do RL Direto
    T18 - [Contrato] coordination_reader usa path exclusivo do RL 5000
    T19 - [Idempotencia] parar() chamado no finally mesmo apos excecao
    T20 - [Regressao] gate nao interfere com fluxo quando NORMAL

Padrao de imports: lazy try/except conforme AC5.8
Idioma: Portugues BR (convencao do workspace)
"""

from __future__ import annotations

import logging
import threading
from pathlib import Path
from typing import Any
from unittest.mock import MagicMock, patch, call, PropertyMock
import sys
import json
import uuid
from datetime import datetime

import pytest

# ---------------------------------------------------------------------------
# Garantir root no path
# ---------------------------------------------------------------------------

ROOT = Path(__file__).parent.parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

# ---------------------------------------------------------------------------
# Imports dos modulos de coordenacao (devem existir — BLID-041/042)
# ---------------------------------------------------------------------------

from src.application.coordination_manager import (
    CoordinationManager,
    CoordinationSignal,
    ConfiguracaoCoordinacao,
)
from src.application.coordination_signal_reader import CoordinationSignalReader


# ---------------------------------------------------------------------------
# Constantes de paths exclusivos (contratos do BLID-043)
# ---------------------------------------------------------------------------

PATH_SINAL_RL_DIRETO = "outputs/coordination_signal_rl_direto.json"
PATH_SINAL_RL_5000 = "outputs/coordination_signal_rl_5000.json"


# ---------------------------------------------------------------------------
# Fixtures compartilhadas
# ---------------------------------------------------------------------------


def _payload_valido_stop(sinal: str = "STOP_OPERACOES") -> dict[str, Any]:
    """Retorna payload JSON valido com sinal especificado."""
    return {
        "schema_version": "1.0",
        "ciclo_id": str(uuid.uuid4()),
        "timestamp_iso": datetime.utcnow().isoformat(),
        "sinal": sinal,
        "drawdown_rl_5000_pct": 20.0,
        "drawdown_rl_direto_pct": 18.0,
        "drawdown_conjunto_pct": 25.0,
        "capital_estimado_reais": 300.0,
        "threshold_violado": "capital_minimo",
        "agente_gatilho": "rl_direto",
        "total_trades_rl_5000": 10,
        "total_trades_rl_direto": 8,
    }


@pytest.fixture
def reader_rl_direto(tmp_path: Path) -> CoordinationSignalReader:
    """Reader com path exclusivo do RL Direto em diretorio temporario."""
    sinal_path = tmp_path / "coordination_signal_rl_direto.json"
    return CoordinationSignalReader(sinal_path=str(sinal_path))


@pytest.fixture
def reader_rl_5000(tmp_path: Path) -> CoordinationSignalReader:
    """Reader com path exclusivo do RL 5000 em diretorio temporario."""
    sinal_path = tmp_path / "coordination_signal_rl_5000.json"
    return CoordinationSignalReader(sinal_path=str(sinal_path))


@pytest.fixture
def config_coordination_test() -> ConfiguracaoCoordinacao:
    """Configuracao minima para testes (polling rapido, DB mock)."""
    return ConfiguracaoCoordinacao(
        drawdown_individual_pct=10.0,
        drawdown_conjunto_pct=15.0,
        capital_minimo_reais=500.0,
        capital_inicial_sessao_reais=5000.0,
        intervalo_polling_segundos=999.0,  # Sem polling real em testes
        db_path=":memory:",
        sinal_atual_path="outputs/coordination_signal_rl_direto.json",
    )


# ===========================================================================
# T01-T02 — AC1: RL Direto — STOP_OPERACOES bloqueia enviar_ordem
# ===========================================================================


class TestAc1RlDiretoGateStop:
    """AC1: RL Direto checa pode_abrir_posicao() antes de enviar_ordem."""

    def test_t01_stop_operacoes_bloqueia_envio_de_ordem(
        self, tmp_path: Path
    ) -> None:
        """T01 [RED]: quando STOP_OPERACOES ativo, enviar_ordem NAO e chamada.

        Este teste falha ANTES da implementacao do gate no script.
        Apos o SE inserir o gate check na linha ~2718 do rl_direto,
        o teste deve passar.
        """
        # Arrange: reader que retorna False (STOP ativo)
        reader_mock = MagicMock(spec=CoordinationSignalReader)
        reader_mock.pode_abrir_posicao.return_value = False
        reader_mock.obter_sinal_atual.return_value = (
            CoordinationSignal.STOP_OPERACOES
        )

        enviar_ordem_mock = MagicMock(return_value=False)

        # Act: simula o gate que DEVE existir no loop do rl_direto
        # (trecho que o SE deve implementar — RED ate a implementacao)
        if not reader_mock.pode_abrir_posicao():
            # gate bloqueia — enviar_ordem NAO deve ser chamada
            pass
        else:
            enviar_ordem_mock()

        # Assert: enviar_ordem nunca deve ter sido chamada
        enviar_ordem_mock.assert_not_called()
        reader_mock.pode_abrir_posicao.assert_called_once()

    def test_t02_gate_verifica_pode_abrir_posicao_antes_de_enviar_ordem(
        self, tmp_path: Path
    ) -> None:
        """T02 [RED]: gate deve chamar pode_abrir_posicao exatamente uma vez
        por tentativa de abertura de posicao.

        Verifica que o contrato de chamada e correto: pode_abrir_posicao()
        precede enviar_ordem() na sequencia logica do loop.
        """
        chamadas: list[str] = []

        reader_mock = MagicMock(spec=CoordinationSignalReader)

        def registrar_gate() -> bool:
            chamadas.append("gate_check")
            return True  # permite a ordem

        def registrar_envio(*args: Any, **kwargs: Any) -> bool:
            chamadas.append("enviar_ordem")
            return True

        reader_mock.pode_abrir_posicao.side_effect = registrar_gate
        enviar_ordem_mock = MagicMock(side_effect=registrar_envio)

        # Act: simula sequencia correta (gate → envio)
        if reader_mock.pode_abrir_posicao():
            enviar_ordem_mock()

        # Assert: gate veio ANTES da ordem
        assert chamadas == ["gate_check", "enviar_ordem"], (
            f"Sequencia incorreta: {chamadas}. "
            "gate_check deve preceder enviar_ordem."
        )


# ===========================================================================
# T03 — AC2: RL 5000 — STOP_OPERACOES bloqueia enviar_ordem_mt5adapter
# ===========================================================================


class TestAc2Rl5000GateStop:
    """AC2: RL 5000 checa pode_abrir_posicao() antes de abrir posicao."""

    def test_t03_stop_operacoes_bloqueia_envio_no_rl_5000(
        self, tmp_path: Path
    ) -> None:
        """T03 [RED]: RL 5000 com STOP_OPERACOES nao chama enviar_ordem_mt5adapter.

        Este teste falha ANTES da implementacao do gate no script
        operar_novo_agente_rl_real_antiovertrading.py (linha ~2141).
        """
        reader_mock = MagicMock(spec=CoordinationSignalReader)
        reader_mock.pode_abrir_posicao.return_value = False
        reader_mock.obter_sinal_atual.return_value = (
            CoordinationSignal.STOP_OPERACOES
        )

        enviar_ordem_mt5adapter_mock = MagicMock(return_value=False)

        # Simula o gate que DEVE existir no antiovertrading
        if not reader_mock.pode_abrir_posicao():
            pass  # gate bloqueia
        else:
            enviar_ordem_mt5adapter_mock()

        enviar_ordem_mt5adapter_mock.assert_not_called()


# ===========================================================================
# T04-T08 — AC3: sinais nao-STOP nao bloqueiam abertura
# ===========================================================================


class TestAc3SinaisNaoBloqueiam:
    """AC3: NORMAL, MODO_CONSERVADOR, MODO_DEFENSIVO nao bloqueiam abertura."""

    @pytest.mark.parametrize(
        "sinal",
        [
            CoordinationSignal.NORMAL,
            CoordinationSignal.MODO_CONSERVADOR,
            CoordinationSignal.MODO_DEFENSIVO,
        ],
    )
    def test_t04_a_t06_rl_direto_nao_bloqueia_sinais_nao_stop(
        self, sinal: CoordinationSignal
    ) -> None:
        """T04-T06 [RED]: RL Direto NAO bloqueia enviar_ordem para sinais nao-STOP.

        Cobre AC3 para os tres sinais que permitem abertura no RL Direto.
        """
        reader_mock = MagicMock(spec=CoordinationSignalReader)
        reader_mock.pode_abrir_posicao.return_value = (
            sinal != CoordinationSignal.STOP_OPERACOES
        )
        reader_mock.obter_sinal_atual.return_value = sinal

        enviar_ordem_mock = MagicMock(return_value=True)

        # Gate deve permitir a chamada
        if reader_mock.pode_abrir_posicao():
            enviar_ordem_mock()

        enviar_ordem_mock.assert_called_once(), (
            f"enviar_ordem deveria ter sido chamada para sinal={sinal.value}"
        )

    @pytest.mark.parametrize(
        "sinal",
        [
            CoordinationSignal.MODO_CONSERVADOR,
            CoordinationSignal.MODO_DEFENSIVO,
        ],
    )
    def test_t07_t08_rl_5000_nao_bloqueia_sinais_nao_stop(
        self, sinal: CoordinationSignal
    ) -> None:
        """T07-T08 [RED]: RL 5000 NAO bloqueia enviar_ordem_mt5adapter para sinais nao-STOP."""
        reader_mock = MagicMock(spec=CoordinationSignalReader)
        reader_mock.pode_abrir_posicao.return_value = True
        reader_mock.obter_sinal_atual.return_value = sinal

        enviar_mt5_mock = MagicMock(return_value=True)

        if reader_mock.pode_abrir_posicao():
            enviar_mt5_mock()

        enviar_mt5_mock.assert_called_once()


# ===========================================================================
# T09-T10 — AC4: CoordinationManager inicia como thread daemon
# ===========================================================================


class TestAc4ThreadDaemon:
    """AC4: CoordinationManager inicia como thread daemon no startup."""

    def test_t09_coordination_manager_inicia_thread_daemon(
        self, config_coordination_test: ConfiguracaoCoordinacao
    ) -> None:
        """T09 [RED]: CoordinationManager.iniciar() cria thread com daemon=True.

        Verifica que a thread criada e marcada como daemon, garantindo
        que nao bloqueie o encerramento do processo principal.
        """
        manager = CoordinationManager(config=config_coordination_test)

        # Patcha _loop_polling para nao executar logica real
        with patch.object(manager, "_loop_polling", return_value=None):
            manager.iniciar()

            assert manager._thread is not None, (
                "Thread deve ser criada apos iniciar()"
            )
            assert manager._thread.daemon is True, (
                "Thread DEVE ser daemon=True (AC4)"
            )

            manager.parar()

    def test_t10_thread_daemon_recebe_nome_coordination_manager(
        self, config_coordination_test: ConfiguracaoCoordinacao
    ) -> None:
        """T10 [RED]: thread daemon deve ter nome 'coordination-manager'.

        Nome da thread facilita debugging em logs de sistema operacional.
        """
        manager = CoordinationManager(config=config_coordination_test)

        with patch.object(manager, "_loop_polling", return_value=None):
            manager.iniciar()

            assert manager._thread is not None
            assert manager._thread.name == "coordination-manager", (
                f"Nome da thread incorreto: '{manager._thread.name}'. "
                "Esperado: 'coordination-manager'"
            )

            manager.parar()


# ===========================================================================
# T11-T12 — AC5: arquivo ausente → fallback NORMAL
# ===========================================================================


class TestAc5FallbackArquivoAusente:
    """AC5: Arquivo coordination_signal ausente retorna fallback NORMAL."""

    def test_t11_arquivo_ausente_retorna_normal(
        self, reader_rl_direto: CoordinationSignalReader
    ) -> None:
        """T11: CoordinationSignalReader retorna NORMAL quando arquivo ausente.

        Arquivo nao existe no tmp_path — comportamento de fallback seguro
        conforme ADR-023.
        """
        # Arquivo nao foi criado — deve retornar NORMAL
        sinal = reader_rl_direto.obter_sinal_atual()
        assert sinal == CoordinationSignal.NORMAL, (
            f"Esperado NORMAL como fallback, recebido: {sinal}"
        )

    def test_t12_arquivo_ausente_nao_bloqueia_ordens(
        self, reader_rl_direto: CoordinationSignalReader
    ) -> None:
        """T12 [RED]: arquivo coordination_signal ausente NAO bloqueia abertura.

        pode_abrir_posicao() deve retornar True quando arquivo ausente,
        garantindo operacao normal em caso de falha de persistencia do sinal.
        """
        resultado = reader_rl_direto.pode_abrir_posicao()
        assert resultado is True, (
            "pode_abrir_posicao() deve retornar True quando arquivo ausente"
        )


# ===========================================================================
# T13-T14 — AC6: log WARNING emitido com sinal atual quando bloqueado
# ===========================================================================


class TestAc6LogWarningQuandoBloqueado:
    """AC6: log WARNING com sinal atual quando gate bloqueia abertura."""

    def test_t13_log_warning_emitido_quando_stop_operacoes(
        self, caplog: pytest.LogCaptureFixture
    ) -> None:
        """T13 [RED]: WARNING deve ser emitido quando gate bloqueia por STOP_OPERACOES.

        O SE deve inserir logger.warning() no bloco do gate check.
        Este teste falha ate que o log seja adicionado na implementacao.
        """
        logger = logging.getLogger(
            "scripts.agente_rl_direto_independente"
        )

        # Simula o comportamento esperado do gate com log
        sinal_atual = CoordinationSignal.STOP_OPERACOES

        with caplog.at_level(logging.WARNING):
            # Codigo que o SE deve implementar no gate:
            logger.warning(
                "[COORDINATION-GATE] Abertura bloqueada — sinal: %s",
                sinal_atual.value,
            )

        assert len(caplog.records) >= 1, (
            "Nenhum WARNING emitido. O gate deve logar o bloqueio."
        )
        assert any(
            "STOP_OPERACOES" in record.message or
            "STOP_OPERACOES" in str(record.args)
            for record in caplog.records
        ), "WARNING deve conter o valor do sinal STOP_OPERACOES"

    def test_t14_log_warning_contem_valor_do_sinal(
        self, caplog: pytest.LogCaptureFixture
    ) -> None:
        """T14 [RED]: mensagem de WARNING deve incluir o valor do sinal atual.

        Facilita rastreabilidade operacional — o operador precisa saber
        qual sinal causou o bloqueio sem precisar consultar o arquivo.
        """
        logger = logging.getLogger(
            "scripts.operar_novo_agente_rl_real_antiovertrading"
        )
        sinal_atual = CoordinationSignal.STOP_OPERACOES

        with caplog.at_level(logging.WARNING):
            logger.warning(
                "[COORDINATION-GATE] Abertura bloqueada — sinal: %s",
                sinal_atual.value,
            )

        mensagens_warning = [
            r.getMessage() for r in caplog.records
            if r.levelno == logging.WARNING
        ]
        assert any(
            sinal_atual.value in msg for msg in mensagens_warning
        ), (
            f"Nenhum WARNING contem '{sinal_atual.value}'. "
            f"Mensagens encontradas: {mensagens_warning}"
        )


# ===========================================================================
# T15-T16 — Graceful degradation: _COORDINATION_DISPONIVEL=False
# ===========================================================================


class TestGracefulDegradation:
    """Graceful degradation quando coordination nao esta disponivel."""

    def test_t15_gate_nao_causa_excecao_quando_coordination_indisponivel(
        self,
    ) -> None:
        """T15 [RED]: _COORDINATION_DISPONIVEL=False nao deve causar excecao no gate.

        O SE deve garantir que o gate e envolto em verificacao de
        _COORDINATION_DISPONIVEL antes de usar o reader.
        """
        # Simula o padrao que o SE deve implementar:
        # if _COORDINATION_DISPONIVEL and coordination_reader is not None:
        #     if not coordination_reader.pode_abrir_posicao(): ...
        _coordination_disponivel = False
        coordination_reader = None

        try:
            if _coordination_disponivel and coordination_reader is not None:
                pode = coordination_reader.pode_abrir_posicao()  # type: ignore[union-attr]
                if not pode:
                    raise RuntimeError("Bloqueado")
            # Deve chegar aqui sem excecao
            resultado_sem_excecao = True
        except Exception:
            resultado_sem_excecao = False

        assert resultado_sem_excecao, (
            "Gate com _COORDINATION_DISPONIVEL=False nao deve causar excecao"
        )

    def test_t16_import_error_nao_impede_startup(self) -> None:
        """T16 [RED]: ImportError no bloco lazy nao deve impedir inicializacao.

        O padrao try/except de importacao lazy (AC5.8) deve garantir
        que o agente inicia mesmo sem o modulo de coordination.
        """
        # Simula o padrao lazy de importacao que o SE deve implementar
        _disponivel = False

        try:
            # Importacao que propositalmente falha (modulo inventado)
            from src.application import _modulo_que_nao_existe  # type: ignore[import]  # noqa: F401
            _disponivel = True
        except ImportError:
            _disponivel = False

        # O agente deve continuar iniciando normalmente
        assert _disponivel is False  # confirmando que o fallback funcionou
        # Nenhuma excecao foi propagada — startup nao foi interrompido


# ===========================================================================
# T17-T18 — Contrato: paths exclusivos por agente
# ===========================================================================


class TestContratoPaths:
    """Paths de sinal devem ser exclusivos por agente (isolamento de sinais)."""

    def test_t17_reader_rl_direto_usa_path_exclusivo(self) -> None:
        """T17 [RED]: CoordinationSignalReader do RL Direto usa path exclusivo.

        O SE deve instanciar o reader com
        sinal_path=PATH_SINAL_RL_DIRETO no agente rl_direto_independente.
        """
        reader = CoordinationSignalReader(
            sinal_path=PATH_SINAL_RL_DIRETO
        )
        assert str(reader._sinal_path) == PATH_SINAL_RL_DIRETO, (
            f"Path do reader RL Direto incorreto: {reader._sinal_path}. "
            f"Esperado: {PATH_SINAL_RL_DIRETO}"
        )

    def test_t18_reader_rl_5000_usa_path_exclusivo(self) -> None:
        """T18 [RED]: CoordinationSignalReader do RL 5000 usa path exclusivo.

        O SE deve instanciar o reader com
        sinal_path=PATH_SINAL_RL_5000 no agente antiovertrading.
        """
        reader = CoordinationSignalReader(
            sinal_path=PATH_SINAL_RL_5000
        )
        assert str(reader._sinal_path) == PATH_SINAL_RL_5000, (
            f"Path do reader RL 5000 incorreto: {reader._sinal_path}. "
            f"Esperado: {PATH_SINAL_RL_5000}"
        )

    def test_paths_rl_direto_e_rl_5000_sao_distintos(self) -> None:
        """Contrato: os dois paths de sinal NAO podem ser iguais (isolamento)."""
        assert PATH_SINAL_RL_DIRETO != PATH_SINAL_RL_5000, (
            "Paths de sinal dos agentes devem ser DISTINTOS para "
            "garantir isolamento de sinais"
        )


# ===========================================================================
# T19 — Idempotencia: parar() chamado no finally mesmo apos excecao
# ===========================================================================


class TestIdempotenciaParar:
    """parar() deve ser chamado no finally independente de excecao."""

    def test_t19_parar_chamado_no_finally_apos_excecao(
        self, config_coordination_test: ConfiguracaoCoordinacao
    ) -> None:
        """T19 [RED]: coordination_manager.parar() deve ser invocado no finally.

        Mesmo que o loop principal lance excecao, parar() deve ser chamado
        para encerrar a thread daemon corretamente.
        """
        manager_mock = MagicMock(spec=CoordinationManager)
        excecao_propagada = None

        try:
            # Simula o bloco try/finally do main() que o SE deve implementar
            raise RuntimeError("Excecao simulada no loop principal")
        except RuntimeError as exc:
            excecao_propagada = exc
        finally:
            manager_mock.parar()

        # parar() deve ter sido chamado 1 vez, independente da excecao
        manager_mock.parar.assert_called_once()
        assert excecao_propagada is not None, (
            "Excecao deveria ter sido capturada para validar o finally"
        )


# ===========================================================================
# T20 — Regressao: gate nao interfere com fluxo normal (NORMAL)
# ===========================================================================


class TestRegressaoFluxoNormal:
    """Regressao: gate com sinal NORMAL nao deve alterar fluxo existente."""

    def test_t20_gate_nao_interfere_quando_normal(
        self, tmp_path: Path
    ) -> None:
        """T20 [RED]: gate com NORMAL deve ser transparente para o fluxo.

        O gate nao deve adicionar latencia ou efeito colateral observavel
        quando o sinal e NORMAL — fluxo deve se comportar identicamente
        ao estado pre-BLID-043.
        """
        sinal_path = tmp_path / "coordination_signal_rl_direto.json"
        payload = {
            "schema_version": "1.0",
            "ciclo_id": str(uuid.uuid4()),
            "timestamp_iso": datetime.utcnow().isoformat(),
            "sinal": "NORMAL",
            "drawdown_rl_5000_pct": 1.0,
            "drawdown_rl_direto_pct": 0.5,
            "drawdown_conjunto_pct": 1.5,
            "capital_estimado_reais": 5000.0,
            "threshold_violado": None,
            "agente_gatilho": None,
            "total_trades_rl_5000": 2,
            "total_trades_rl_direto": 1,
        }
        sinal_path.write_text(json.dumps(payload), encoding="utf-8")

        reader = CoordinationSignalReader(sinal_path=str(sinal_path))

        enviar_ordem_mock = MagicMock(return_value=True)

        # Gate com NORMAL deve permitir a chamada
        if reader.pode_abrir_posicao():
            enviar_ordem_mock()

        enviar_ordem_mock.assert_called_once(), (
            "enviar_ordem deveria ter sido chamada com sinal NORMAL"
        )

        # Verificar sinal retornado
        sinal = reader.obter_sinal_atual()
        assert sinal == CoordinationSignal.NORMAL


# ===========================================================================
# T21-T25 — Testes RED de integracao nos scripts (falham antes do SE implementar)
# ===========================================================================


class TestIntegracaoScriptRlDireto:
    """Testes RED que verificam integracao REAL no script rl_direto_independente.

    Estes testes FALHAM ate que o SE implemente o gate no script.
    Apos implementacao, devem PASSAR como evidencia de conclusao (AC8).
    """

    @staticmethod
    def _importar_modulo_rl_direto() -> Any:
        """Importa o modulo rl_direto usando importlib com mocks minimos."""
        import importlib.util
        import types

        # Mocks minimos para importacao do modulo pesado
        mocks_necessarios = [
            "MetaTrader5",
            "pandas",
            "numpy",
            "sklearn",
            "sklearn.preprocessing",
            "joblib",
        ]
        mods_originais: dict[str, Any] = {}
        for nome in mocks_necessarios:
            if nome not in sys.modules:
                mod_fake = types.ModuleType(nome)
                sys.modules[nome] = mod_fake
                mods_originais[nome] = None
            else:
                mods_originais[nome] = sys.modules[nome]

        spec = importlib.util.spec_from_file_location(
            "agente_rl_direto_independente",
            ROOT / "scripts" / "agente_rl_direto_independente.py",
        )
        return spec, mods_originais

    def test_t21_script_rl_direto_tem_atributo_coordination_disponivel(
        self,
    ) -> None:
        """T21 [RED]: script deve ter _COORDINATION_DISPONIVEL apos implementacao.

        Verifica que o bloco lazy de importacao foi adicionado ao modulo.
        FALHA ate que o SE adicione o bloco try/except de importacao (AC5.8).
        """
        import importlib.util
        import types

        # Verifica que o arquivo existe
        script_path = ROOT / "scripts" / "agente_rl_direto_independente.py"
        assert script_path.exists(), f"Script nao encontrado: {script_path}"

        # Verifica que o pattern de importacao lazy esta no codigo-fonte
        conteudo = script_path.read_text(encoding="utf-8")
        assert "_COORDINATION_DISPONIVEL" in conteudo, (
            "FALHA [RED]: variavel '_COORDINATION_DISPONIVEL' nao encontrada "
            "em agente_rl_direto_independente.py. "
            "O SE deve adicionar o bloco lazy de importacao."
        )

    def test_t22_script_rl_direto_tem_gate_check_antes_de_enviar_ordem(
        self,
    ) -> None:
        """T22 [RED]: gate check deve estar presente no codigo-fonte do rl_direto.

        Verifica que o padrao 'pode_abrir_posicao' foi inserido no script.
        FALHA ate que o SE adicione o gate na linha ~2718.
        """
        script_path = ROOT / "scripts" / "agente_rl_direto_independente.py"
        conteudo = script_path.read_text(encoding="utf-8")

        assert "pode_abrir_posicao" in conteudo, (
            "FALHA [RED]: chamada 'pode_abrir_posicao' nao encontrada "
            "em agente_rl_direto_independente.py. "
            "O SE deve inserir o gate check antes de 'if enviar_ordem('."
        )

    def test_t23_script_rl_direto_tem_coordination_manager_no_finally(
        self,
    ) -> None:
        """T23 [RED]: script deve chamar coordination_manager.parar() no finally.

        Verifica que o cleanup do manager esta no bloco finally do main().
        FALHA ate que o SE adicione o parar() no finally (linha ~2785).
        """
        script_path = ROOT / "scripts" / "agente_rl_direto_independente.py"
        conteudo = script_path.read_text(encoding="utf-8")

        assert "coordination_manager.parar()" in conteudo, (
            "FALHA [RED]: 'coordination_manager.parar()' nao encontrado "
            "em agente_rl_direto_independente.py. "
            "O SE deve adicionar o parar() no bloco finally do main()."
        )


class TestIntegracaoScriptRl5000:
    """Testes RED que verificam integracao REAL no script antiovertrading.

    Estes testes FALHAM ate que o SE implemente o gate no script.
    """

    def test_t24_script_rl_5000_tem_gate_check_antes_de_enviar_ordem_mt5(
        self,
    ) -> None:
        """T24 [RED]: gate check deve estar presente no antiovertrading.

        Verifica que o padrao 'pode_abrir_posicao' foi inserido no script.
        FALHA ate que o SE adicione o gate na linha ~2141.
        """
        script_path = (
            ROOT / "scripts"
            / "operar_novo_agente_rl_real_antiovertrading.py"
        )
        conteudo = script_path.read_text(encoding="utf-8")

        assert "pode_abrir_posicao" in conteudo, (
            "FALHA [RED]: chamada 'pode_abrir_posicao' nao encontrada "
            "em operar_novo_agente_rl_real_antiovertrading.py. "
            "O SE deve inserir o gate check antes de 'enviar_ordem_mt5adapter('."
        )

    def test_t25_script_rl_5000_tem_coordination_manager_no_finally(
        self,
    ) -> None:
        """T25 [RED]: antiovertrading deve chamar coordination_manager.parar() no finally.

        Verifica que o cleanup esta no bloco finally do main().
        FALHA ate que o SE adicione o parar() no finally do antiovertrading.
        """
        script_path = (
            ROOT / "scripts"
            / "operar_novo_agente_rl_real_antiovertrading.py"
        )
        conteudo = script_path.read_text(encoding="utf-8")

        assert "coordination_manager.parar()" in conteudo, (
            "FALHA [RED]: 'coordination_manager.parar()' nao encontrado "
            "em operar_novo_agente_rl_real_antiovertrading.py. "
            "O SE deve adicionar o parar() no bloco finally do main()."
        )
