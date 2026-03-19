"""
Testes para MT5SyncValidator.

Cobertura de cenários:
1. Dados sincronizados com tolerância ✓
2. Divergência crítica detectada ✓
3. Status divergente ✓
4. Faltam dados ✓
5. Validação em lote ✓
6. Relatório de auditoria ✓
7. Divergência percentual ✓
"""

import pytest
from src.application.reconciliadores.mt5_sync_validator import (
    MT5SyncValidator,
    SyncStatus
)

@pytest.mark.asyncio
async def test_validar_sincronizacao_dados_sincronizados():
    validator = MT5SyncValidator(tolerance_percent=1.0)
    dados_local = {"profit": 100.0, "status": "closed"}
    dados_mt5 = {"profit": 100.5, "status": "closed"}

    report = await validator.validar_sincronizacao("101", dados_local, dados_mt5)

    assert report.status == SyncStatus.SINCRONIZADO
    assert report.tolerance_percent == 1.0

@pytest.mark.asyncio
async def test_validar_sincronizacao_divergencia_critica():
    validator = MT5SyncValidator(tolerance_percent=0.5)
    dados_local = {"profit": 100.0, "status": "closed"}
    dados_mt5 = {"profit": 110.0, "status": "closed"}  # 9.09% divergência

    report = await validator.validar_sincronizacao("102", dados_local, dados_mt5)

    assert report.status == SyncStatus.DIVERGENCIA_CRITICA
    assert "divergência" in report.observations.lower()

@pytest.mark.asyncio
async def test_validar_sincronizacao_status_divergente():
    validator = MT5SyncValidator()
    dados_local = {"profit": 100.0, "status": "open"}
    dados_mt5 = {"profit": 100.0, "status": "closed"}

    report = await validator.validar_sincronizacao("103", dados_local, dados_mt5)

    assert report.status == SyncStatus.DESINCRONIZADO
    assert "status" in report.observations.lower()

@pytest.mark.asyncio
async def test_validar_sincronizacao_faltam_dados():
    validator = MT5SyncValidator()

    report = await validator.validar_sincronizacao("104", {}, None)

    assert report.status == SyncStatus.AUDITORIA_NECESSARIA
    assert "faltando" in report.observations.lower()

@pytest.mark.asyncio
async def test_validar_sincronizacao_profit_em_texto():
    validator = MT5SyncValidator(tolerance_percent=1.0)
    dados_local = {"profit": "100.0", "status": "closed"}
    dados_mt5 = {"profit": 100.0, "status": "closed"}

    report = await validator.validar_sincronizacao("104a", dados_local, dados_mt5)

    assert report.status == SyncStatus.SINCRONIZADO
    assert "sincronizado" in report.observations.lower()

@pytest.mark.asyncio
async def test_validar_sincronizacao_profit_invalido_marca_auditoria():
    validator = MT5SyncValidator()
    dados_local = {"profit": "abc", "status": "closed"}
    dados_mt5 = {"profit": 100.0, "status": "closed"}

    report = await validator.validar_sincronizacao("104b", dados_local, dados_mt5)

    assert report.status == SyncStatus.AUDITORIA_NECESSARIA
    assert "invalido" in report.observations.lower()

@pytest.mark.asyncio
async def test_validar_lote():
    validator = MT5SyncValidator(tolerance_percent=1.0)

    ordens = [
        ("201", {"profit": 100.0, "status": "closed"}, {"profit": 100.5, "status": "closed"}),
        ("202", {"profit": 100.0}, {"profit": 110.0}),  # Divergência crítica
        ("203", {}, None),  # Faltam dados
    ]

    reports = await validator.validar_lote(ordens)

    assert len(reports) == 3
    assert reports[0].status == SyncStatus.SINCRONIZADO
    assert reports[1].status == SyncStatus.DIVERGENCIA_CRITICA
    assert reports[2].status == SyncStatus.AUDITORIA_NECESSARIA

def test_obter_relatorio_auditoria():
    validator = MT5SyncValidator(tolerance_percent=1.0)

    # Simular validações prévias
    from src.application.reconciliadores.mt5_sync_validator import ValidationReport
    from datetime import datetime

    validator.validation_reports = [
        ValidationReport(
            order_id="301",
            status=SyncStatus.SINCRONIZADO,
            local_data={"profit": 100.0},
            mt5_data={"profit": 100.5},
            timestamp=datetime.now(),
            tolerance_percent=1.0,
            observations="Sincronizado"
        ),
        ValidationReport(
            order_id="302",
            status=SyncStatus.DIVERGENCIA_CRITICA,
            local_data={"profit": 100.0},
            mt5_data={"profit": 120.0},
            timestamp=datetime.now(),
            tolerance_percent=1.0,
            observations="Divergência crítica"
        ),
    ]

    relatorio = validator.obter_relatorio_auditoria()

    assert relatorio["total_validacoes"] == 2
    assert relatorio["sincronizados"] == 1
    assert relatorio["divergencias_criticas"] == 1
    assert relatorio["taxa_sincronizacao"] == 50.0

def test_calcular_divergencia_percentual():
    validator = MT5SyncValidator()

    # 10% diferença
    divergencia = validator._calcular_divergencia_percentual(110.0, 100.0)
    assert abs(divergencia - 10.0) < 0.01

    # 0% diferença
    divergencia = validator._calcular_divergencia_percentual(100.0, 100.0)
    assert divergencia == 0.0

    # Lidar com zero
    divergencia = validator._calcular_divergencia_percentual(0.0, 0.0)
    assert divergencia == 0.0

    divergencia = validator._calcular_divergencia_percentual(100.0, 0.0)
    assert divergencia == 100.0

def test_tolerance_negative_is_normalized():
    validator = MT5SyncValidator(tolerance_percent=-3.0)

    assert validator.tolerance_percent == 0.0

def test_limpar_relatorios():
    validator = MT5SyncValidator()

    from src.application.reconciliadores.mt5_sync_validator import ValidationReport
    from datetime import datetime

    validator.validation_reports = [
        ValidationReport(
            order_id="401",
            status=SyncStatus.SINCRONIZADO,
            local_data={},
            mt5_data={},
            timestamp=datetime.now(),
            tolerance_percent=1.0,
            observations="Teste"
        )
    ]

    assert len(validator.validation_reports) == 1

    validator.limpar_relatorios()

    assert len(validator.validation_reports) == 0

def test_obter_relatorio_auditoria_vazio():
    validator = MT5SyncValidator()

    relatorio = validator.obter_relatorio_auditoria()

    assert relatorio["total_validacoes"] == 0
    assert relatorio["taxa_sincronizacao"] == 0
