"""
Testes unitarios para ROADMAP-DIARIOS-01: ObservabilidadeDiarios.

Cobre:
- Registro de gravacoes por diario
- Verificacao de alertas de inatividade
- Exibicao do painel ASCII
- Contagem de registros por diario
- Historico de restarts

Status: TDD v1.0 (18/03/2026)
Referencia: docs/BACKLOG.md (ROADMAP-DIARIOS-01)
"""

import datetime
import json
import pytest
from src.application.diario_observability_panel import (
    ObservabilidadeDiarios,
    StatusDiario,
    DIARIOS_MONITORADOS,
)


# ─────────────────────────────────────────────────────────────────
# Fixtures
# ─────────────────────────────────────────────────────────────────


@pytest.fixture
def painel() -> ObservabilidadeDiarios:
    """Painel com limite padrao de 20 minutos."""
    return ObservabilidadeDiarios(limite_inatividade_min=20)


@pytest.fixture
def painel_curto() -> ObservabilidadeDiarios:
    """Painel com limite curto de 1 minuto para testes de alerta."""
    return ObservabilidadeDiarios(limite_inatividade_min=1)


# ─────────────────────────────────────────────────────────────────
# Testes
# ─────────────────────────────────────────────────────────────────


@pytest.mark.unit
def test_registrar_gravacao_atualiza_timestamp(painel: ObservabilidadeDiarios) -> None:
    """Apos registrar gravacao, ultimo_registro deve ser recente."""
    antes = datetime.datetime.now()
    painel.registrar_gravacao("MICRO_TENDENCIA")
    status = painel.obter_status("MICRO_TENDENCIA")

    assert status.ultimo_registro is not None
    assert status.ultimo_registro >= antes


@pytest.mark.unit
def test_verificar_alertas_retorna_vazio_quando_dentro_do_limite(
    painel: ObservabilidadeDiarios,
) -> None:
    """Nenhum alerta quando todos os diarios gravaram recentemente."""
    for nome in DIARIOS_MONITORADOS:
        painel.registrar_gravacao(nome)

    alertas = painel.verificar_alertas_inatividade()
    assert alertas == []


@pytest.mark.unit
def test_verificar_alertas_retorna_diario_quando_inativo(
    painel: ObservabilidadeDiarios,
) -> None:
    """Diario com ultimo_registro antigo deve aparecer nos alertas."""
    # Simula registro antigo (30 minutos atras)
    nome = "RL_5000"
    painel.registrar_gravacao(nome)
    status = painel.obter_status(nome)
    status.ultimo_registro = datetime.datetime.now() - datetime.timedelta(minutes=30)

    alertas = painel.verificar_alertas_inatividade()
    assert nome in alertas


@pytest.mark.unit
def test_exibir_painel_retorna_string_com_cabecalho(
    painel: ObservabilidadeDiarios,
) -> None:
    """Painel deve conter cabecalho identificavel."""
    saida = painel.exibir_painel_terminal()

    assert isinstance(saida, str)
    assert len(saida) > 0
    # Cabecalho deve ter algum texto identificador
    assert "DIARIOS" in saida.upper() or "PAINEL" in saida.upper() or "OBSERVABILIDADE" in saida.upper()


@pytest.mark.unit
def test_exibir_painel_inclui_todos_os_diarios(
    painel: ObservabilidadeDiarios,
) -> None:
    """Painel deve exibir linha para cada diario monitorado."""
    saida = painel.exibir_painel_terminal()

    for nome in DIARIOS_MONITORADOS:
        assert nome in saida, f"Diario '{nome}' nao encontrado no painel"


@pytest.mark.unit
def test_total_registros_incrementa_por_diario(
    painel: ObservabilidadeDiarios,
) -> None:
    """Cada chamada a registrar_gravacao deve incrementar total_registros."""
    nome = "RL_DIRETO"
    painel.registrar_gravacao(nome)
    painel.registrar_gravacao(nome)
    painel.registrar_gravacao(nome)

    status = painel.obter_status(nome)
    assert status.total_registros == 3


@pytest.mark.unit
def test_alertas_inatividade_limite_configuravel(
) -> None:
    """Limite de inatividade deve ser respeitado conforme configuracao."""
    painel_5min = ObservabilidadeDiarios(limite_inatividade_min=5)
    painel_60min = ObservabilidadeDiarios(limite_inatividade_min=60)

    nome = "DIARIOS"
    # Simula ultimo registro ha 10 minutos
    for p in [painel_5min, painel_60min]:
        p.registrar_gravacao(nome)
        status = p.obter_status(nome)
        status.ultimo_registro = datetime.datetime.now() - datetime.timedelta(minutes=10)

    alertas_5 = painel_5min.verificar_alertas_inatividade()
    alertas_60 = painel_60min.verificar_alertas_inatividade()

    # Limite 5min: 10 min atras deve alertar
    assert nome in alertas_5
    # Limite 60min: 10 min atras nao deve alertar
    assert nome not in alertas_60


@pytest.mark.unit
def test_painel_mostra_status_ok_quando_ativo(
    painel: ObservabilidadeDiarios,
) -> None:
    """Painel deve indicar status OK para diarios ativos."""
    for nome in DIARIOS_MONITORADOS:
        painel.registrar_gravacao(nome)

    saida = painel.exibir_painel_terminal()

    # Deve haver alguma indicacao de status positivo
    assert "OK" in saida or "ATIVO" in saida or "✓" in saida or "[+]" in saida


@pytest.mark.unit
def test_painel_mostra_status_alerta_quando_inativo(
    painel: ObservabilidadeDiarios,
) -> None:
    """Painel deve indicar status de alerta para diarios inativos."""
    nome = "MICRO_TENDENCIA"
    painel.registrar_gravacao(nome)
    status = painel.obter_status(nome)
    status.ultimo_registro = datetime.datetime.now() - datetime.timedelta(minutes=30)

    saida = painel.exibir_painel_terminal()

    # Deve haver alguma indicacao de alerta
    assert "ALERTA" in saida or "!" in saida or "INATIVO" in saida or "[!]" in saida


@pytest.mark.unit
def test_historico_restarts_retorna_dict(
    painel: ObservabilidadeDiarios,
) -> None:
    """historico_restarts_por_diario deve retornar dict com todos os diarios."""
    historico = painel.historico_restarts_por_diario()

    assert isinstance(historico, dict)
    for nome in DIARIOS_MONITORADOS:
        assert nome in historico
        assert isinstance(historico[nome], int)
        assert historico[nome] >= 0


@pytest.mark.unit
def test_painel_exibe_resumo_do_relatorio_latest(tmp_path) -> None:
    analysis_dir = tmp_path / "analysis"
    analysis_dir.mkdir(parents=True, exist_ok=True)
    analysis_dir.joinpath("opening_context_vs_result_latest.json").write_text(
        json.dumps(
            {
                "target_date": "2026-03-19",
                "generated_at": "2026-03-19T18:05:00",
                "total_agents": 4,
                "total_trades_closed": 7,
                "total_pnl": 123.45,
            }
        ),
        encoding="utf-8",
    )

    painel = ObservabilidadeDiarios(
        limite_inatividade_min=20,
        report_dir=analysis_dir,
    )

    saida = painel.exibir_painel_terminal()

    assert "Contexto x resultado latest" in saida
    assert "2026-03-19" in saida
    assert "123.45" in saida
