"""Teste estático para garantir observabilidade da promoção no HTML do monitor."""

from pathlib import Path


def test_monitor_quantico_html_contem_bloco_promocao_scheduler() -> None:
    html_path = Path("outputs/monitor_quantico.html")
    html = html_path.read_text(encoding="utf-8")
    assert "id=\"promocao-card\"" in html
    assert "renderizarPromocaoScheduler" in html
    assert "scheduler_symbol_promotion" in html
