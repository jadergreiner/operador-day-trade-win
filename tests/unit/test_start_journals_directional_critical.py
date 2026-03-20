from __future__ import annotations

import importlib


def test_analyze_directional_critical_reporta_bearish_sólido_sem_mascara_de_sinal() -> (
    None
):
    module = importlib.import_module("scripts.start_journals_full_display")
    reader = module.RLPerformanceReader(db_path=":memory:")

    reader.get_today_macro_items = lambda: [  # type: ignore[method-assign]
        {"category": "INDICES_BRASIL", "score": -20, "symbol": "WIN"},
        {"category": "ACOES_BRASIL", "score": -13, "symbol": "WIN"},
        {"category": "CURVA_JUROS", "score": -5, "symbol": "WIN"},
        {"category": "INDICES_GLOBAIS", "score": -3, "symbol": "WIN"},
        {"category": "PETROLEO_ENERGIA", "score": -3, "symbol": "WIN"},
        {"category": "COMMODITIES", "score": -2, "symbol": "WIN"},
        {"category": "DOLAR_CAMBIO", "score": -2, "symbol": "WIN"},
        {"category": "INDICADORES_TECNICOS", "score": -2, "symbol": "WIN"},
        {"category": "EMERGENTES", "score": -1, "symbol": "WIN"},
        {"category": "FLUXO_MICROESTRUTURA", "score": -1, "symbol": "WIN"},
    ]
    reader.get_today_episodes = lambda: [  # type: ignore[method-assign]
        {"macro_confidence": 0}
    ]
    reader.get_macro_category_history = lambda: {}  # type: ignore[method-assign]

    analysis = reader.analyze_directional_critical()

    assert analysis["veredicto"].startswith("DIRECIONAL SÓLIDO (BAIXISTA)")
    assert "Score -52" in analysis["veredicto"]
    assert analysis["confianca_ajustada"] >= 50


def test_analyze_regions_critical_usa_linguagem_neutra_para_zona_de_teste() -> None:
    module = importlib.import_module("scripts.start_journals_full_display")
    reader = module.RLPerformanceReader(db_path=":memory:")

    reader.get_today_regions = lambda: [  # type: ignore[method-assign]
        {
            "label": "OB Baixa M5 +VWAP",
            "price": 780.0,
            "tipo": "SUPORTE",
            "confluences": 2,
        }
    ]
    reader.get_today_micro_decisions = lambda: [  # type: ignore[method-assign]
        {"price_current": 1000.0, "adx": 35},
        {"price_current": 950.0, "adx": 35},
        {"price_current": 780.0, "adx": 35},
        {"price_current": 775.0, "adx": 35},
        {"price_current": 770.0, "adx": 35},
    ]
    reader.get_today_episodes = lambda: []  # type: ignore[method-assign]

    analysis = reader.analyze_regions_critical()

    assert analysis["armadilhas_possiveis"]
    assert analysis["armadilhas_possiveis"][0].startswith(
        "OB Baixa M5 +VWAP @ 780 (SUPORTE) — NÃO PRIORITÁRIO"
    )
    assert any(
        "ZONA DE TESTE" in argumento
        for argumento in analysis["regioes_analisadas"][0]["argumentos_contra"]
    )
