"""Teste estático para garantir observabilidade do monitor no HTML."""

from pathlib import Path


def test_monitor_quantico_html_contem_blocos_promocao_e_fechamentos() -> None:
    html_path = Path("outputs/monitor_quantico.html")
    html = html_path.read_text(encoding="utf-8")
    assert "id=\"promocao-card\"" in html
    assert "renderizarPromocaoScheduler" in html
    assert "scheduler_symbol_promotion" in html
    assert "PRE-OPEN TOLERADO" in html
    assert "BLOQUEIO_ESTRITO" in html
    assert "id=\"fechamentos-card\"" in html
    assert "renderizarFechamentosOperacionais" in html
    assert "fechamentos_por_origem" in html
    assert "anomalia_fechamentos" in html
    assert "fechamentos-anomalia-badge" in html
    assert "id=\"dashboard-operacional-card\"" in html
    assert "renderizarDashboardOperacional" in html
    assert "dashboard_operacional" in html
    assert "Proteção Operacional" in html
    assert "id=\"saude-operacional-card\"" in html
    assert "renderizarSaudeOperacional" in html
    assert "saude_operacional" in html
    assert "Saúde Operacional Geral" in html
