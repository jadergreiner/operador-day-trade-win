import pytest
from src.application.reconciliadores.unknown_result_detector import UnknownResultDetector

@pytest.mark.asyncio
async def test_detectar_lacunas_identifica_ordens_faltantes():
    detector = UnknownResultDetector()
    ordens_locais = [{"order_id": "101", "result": 10.5}]
    ordens_mt5 = [{"ticket": "101"}, {"ticket": "102"}]

    lacunas = await detector.detectar_lacunas(ordens_locais, ordens_mt5)

    assert "102" in lacunas
    assert len(lacunas) == 1

@pytest.mark.asyncio
async def test_detectar_lacunas_ignora_identificadores_vazios():
    detector = UnknownResultDetector()
    ordens_locais = [{"order_id": "", "result": 10.5}, {"order_id": None, "result": 5.0}]
    ordens_mt5 = [{"ticket": ""}, {"ticket": "102"}, {"ticket": "101"}]

    lacunas = await detector.detectar_lacunas(ordens_locais, ordens_mt5)

    assert lacunas == ["101", "102"]

def test_validar_integridade_resultado_sucesso():
    detector = UnknownResultDetector()
    resultado_valido = {"price": 120500, "volume": 1, "profit": 50.0}

    assert detector.validar_integridade_resultado(resultado_valido) is True

def test_validar_integridade_resultado_sucesso_com_valores_texto():
    detector = UnknownResultDetector()
    resultado_valido = {"price": "120500", "volume": "1", "profit": "50.0"}

    assert detector.validar_integridade_resultado(resultado_valido) is True

def test_validar_integridade_resultado_falha_campo_ausente():
    detector = UnknownResultDetector()
    resultado_invalido = {"price": 120500} # Faltam volume e profit

    assert detector.validar_integridade_resultado(resultado_invalido) is False

def test_validar_integridade_resultado_falha_valor_nulo():
    detector = UnknownResultDetector()
    resultado_invalido = {"price": 120500, "volume": None, "profit": 50.0}

    assert detector.validar_integridade_resultado(resultado_invalido) is False
