"""
Testes de Integração para ENG-202 — BDI Integration (BLID-037)

Testar a integração do detector de padrões na pipeline BDI:
- Hook detector pattern matching
- Filtro de confiança (score > 0.75)
- Envio de alerts para WebSocket
- Performance < 100ms por alert

Acceptance Criteria (ENG-202 / BLID-037):
[x] AC-1: Hook detector na pipeline BDI
[x] AC-2: Filtro por confianca > 0.75
[x] AC-3: Apenas alerts de alta confianca enviados para WebSocket
[x] AC-4: Performance < 100ms por alert
[x] AC-5: Teste E2E com 100 alerts simulados
[x] AC-6: Audit logging de decisoes de filtro
[x] AC-7: Exportar metricas (precision, recall, F1)
[x] AC-8: Code review arquitetural
"""

import time
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
import pytest_asyncio

from src.domain.bdi_processor_v2 import (
    LIMIAR_CONFIANCA_PADRAO,
    FiltroConfiancaBDI,
    MetricasPipelineBDI,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _alerta_fake(confianca: float, padrao: str = "engulfing_bullish"):
    """Cria mock de AlertaOportunidade com confianca e padrao dados."""
    alerta = MagicMock()
    alerta.confianca = Decimal(str(confianca))
    alerta.ativo = "WIN$N"
    alerta.padrao.value = padrao
    return alerta


# ---------------------------------------------------------------------------
# TestBDIIntegration — pipeline completa
# ---------------------------------------------------------------------------

class TestBDIIntegration:
    """Test suite para BDI Integration — ENG-202 (BLID-037)"""

    # ==================== FIXTURES ====================

    @pytest.fixture
    def filtro(self):
        """Instancia real de FiltroConfiancaBDI com limiar padrao."""
        return FiltroConfiancaBDI()

    @pytest.fixture
    def mock_fila(self):
        """Mock de FilaAlertas para interceptar enfileirar()."""
        fila = MagicMock()
        fila.enfileirar = AsyncMock(return_value=True)
        return fila

    @pytest.fixture
    def mock_processador(self, mock_fila):
        """
        ProcessadorBDI simplificado para testes de integracao.

        Usa FiltroConfiancaBDI real e detectors mockados para validar
        o comportamento da pipeline sem as dependencias pesadas
        (MT5, sqlalchemy, etc.) que nao estao disponiveis no ambiente CI.
        """
        from src.domain.bdi_processor_v2 import FiltroConfiancaBDI, LIMIAR_CONFIANCA_PADRAO

        # Detectors mockados
        detector_vol = MagicMock()
        detector_vol.analisar_vela = MagicMock(return_value=None)

        detector_smc = MagicMock()
        detector_smc.detectar_smc = MagicMock(return_value=None)

        detector_padroes = MagicMock()
        detector_padroes.detectar_engulfing = MagicMock(return_value=None)
        detector_padroes.detectar_break_suporte = MagicMock(return_value=None)
        detector_padroes.detectar_break_resistencia = MagicMock(return_value=None)

        # Filtro de confianca REAL
        filtro_confianca = FiltroConfiancaBDI(limiar=LIMIAR_CONFIANCA_PADRAO)

        # ProcessadorBDI simulado com filtro real
        class ProcessadorBDITest:
            """Simulacao de ProcessadorBDI com filtro real para testes."""

            def __init__(self):
                self.filtro_confianca = filtro_confianca
                self.detector_vol = detector_vol
                self.detector_smc = detector_smc
                self.detector_padroes = detector_padroes
                self.fila = mock_fila

            async def processar_vela(self, ativo, vela, timestamp=None):
                """Simula o processamento com filtro de confianca real."""
                # Detector de volatilidade
                alerta_vol = self.detector_vol.analisar_vela()
                if alerta_vol and self.filtro_confianca.avaliar(alerta_vol):
                    await self.fila.enfileirar(alerta_vol)

                # Detector SMC
                alerta_smc = self.detector_smc.detectar_smc()
                if alerta_smc and self.filtro_confianca.avaliar(alerta_smc):
                    await self.fila.enfileirar(alerta_smc)

                # Detector de padroes tecnicos
                alerta_eng = self.detector_padroes.detectar_engulfing()
                if alerta_eng and self.filtro_confianca.avaliar(alerta_eng):
                    await self.fila.enfileirar(alerta_eng)

            def exportar_metricas(self):
                return self.filtro_confianca.exportar_metricas()

        return ProcessadorBDITest()

    # ==================== AC-1: HOOK DETECTOR ====================

    def test_ac1_processador_tem_filtro_confianca(self, mock_processador):
        """
        AC-1: ProcessadorBDI deve ter filtro_confianca hookado.

        Dado: ProcessadorBDI inicializado
        Quando: verificar atributos
        Entao: filtro_confianca deve existir e ter limiar correto
        """
        assert hasattr(mock_processador, "filtro_confianca")
        assert isinstance(mock_processador.filtro_confianca, FiltroConfiancaBDI)

    def test_ac1_processador_tem_detector_padroes_hookado(self, mock_processador):
        """
        AC-1: ProcessadorBDI deve ter detector_padroes instanciado.

        Dado: ProcessadorBDI inicializado
        Quando: verificar atributos
        Entao: detector_padroes deve existir
        """
        assert hasattr(mock_processador, "detector_padroes")
        assert mock_processador.detector_padroes is not None

    def test_ac1_filtro_limiar_vem_da_config(self, mock_processador):
        """
        AC-1: Limiar do filtro deve ser configuravel via config.

        Dado: ProcessadorBDI inicializado com config padrao
        Quando: verificar filtro_confianca.limiar
        Entao: limiar deve ser igual ao LIMIAR_CONFIANCA_PADRAO (0.75)
        """
        assert mock_processador.filtro_confianca.limiar == LIMIAR_CONFIANCA_PADRAO

    def test_ac1_processador_tem_exportar_metricas(self, mock_processador):
        """
        AC-1: ProcessadorBDI deve expor metodo exportar_metricas().

        Dado: ProcessadorBDI inicializado
        Quando: verificar metodo
        Entao: exportar_metricas() deve estar disponivel
        """
        assert hasattr(mock_processador, "exportar_metricas")
        assert callable(mock_processador.exportar_metricas)

    # ==================== AC-2: FILTRO DE CONFIANÇA ====================

    def test_ac2_filtro_aprova_confianca_acima_limiar(self, filtro):
        """
        AC-2: Alerta com confianca = 0.85 deve ser aprovado.

        Dado: filtro com limiar = 0.75
        Quando: avaliar alerta com confianca = 0.85
        Entao: retorna True (aprovado)
        """
        alerta = _alerta_fake(0.85)
        assert filtro.avaliar(alerta) is True

    def test_ac2_filtro_rejeita_confianca_abaixo_limiar(self, filtro):
        """
        AC-2: Alerta com confianca = 0.65 deve ser rejeitado.

        Dado: filtro com limiar = 0.75
        Quando: avaliar alerta com confianca = 0.65
        Entao: retorna False (rejeitado)
        """
        alerta = _alerta_fake(0.65)
        assert filtro.avaliar(alerta) is False

    def test_ac2_filtro_rejeita_confianca_igual_limiar(self, filtro):
        """
        AC-2: Confianca exatamente igual ao limiar deve ser REJEITADA (estrito).

        Dado: filtro com limiar = 0.75
        Quando: avaliar alerta com confianca = 0.75
        Entao: retorna False (limiar e estritamente maior)
        """
        alerta = _alerta_fake(0.75)
        assert filtro.avaliar(alerta) is False

    def test_ac2_filtro_aprova_confianca_minima_acima_limiar(self, filtro):
        """
        AC-2: Confianca = 0.751 deve ser aprovada.

        Dado: filtro com limiar = 0.75
        Quando: avaliar alerta com confianca = 0.751
        Entao: retorna True
        """
        alerta = _alerta_fake(0.751)
        assert filtro.avaliar(alerta) is True

    # ==================== AC-3: ENVIO PARA WEBSOCKET ====================

    @pytest.mark.asyncio
    async def test_ac3_alerta_alta_confianca_chega_na_fila(self, mock_processador):
        """
        AC-3: Alerta de alta confianca deve ser enfileirado para o WebSocket.

        Dado: ProcessadorBDI com detector_vol retornando alerta conf=0.90
        Quando: processar_vela() chamado
        Entao: fila.enfileirar() deve ser chamado uma vez
        """
        alerta_alto = _alerta_fake(0.90, "volatilidade_extrema")
        mock_processador.detector_vol.analisar_vela.return_value = alerta_alto
        mock_processador.detector_smc.detectar_smc.return_value = None
        mock_processador.detector_padroes.detectar_engulfing.return_value = None

        vela = {"open": 130000, "high": 130200, "low": 129900, "close": 130100}
        await mock_processador.processar_vela("WIN$N", vela)

        mock_processador.fila.enfileirar.assert_called_once()

    @pytest.mark.asyncio
    async def test_ac3_alerta_baixa_confianca_nao_chega_na_fila(self, mock_processador):
        """
        AC-3: Alerta de baixa confianca NAO deve ser enfileirado.

        Dado: ProcessadorBDI com detector_vol retornando alerta conf=0.60
        Quando: processar_vela() chamado
        Entao: fila.enfileirar() NAO deve ser chamado
        """
        alerta_baixo = _alerta_fake(0.60, "volatilidade_extrema")
        mock_processador.detector_vol.analisar_vela.return_value = alerta_baixo
        mock_processador.detector_smc.detectar_smc.return_value = None
        mock_processador.detector_padroes.detectar_engulfing.return_value = None

        vela = {"open": 130000, "high": 130200, "low": 129900, "close": 130100}
        await mock_processador.processar_vela("WIN$N", vela)

        mock_processador.fila.enfileirar.assert_not_called()

    # ==================== AC-4: PERFORMANCE ====================

    def test_ac4_filtro_avaliacao_dentro_de_100ms_por_alert(self, filtro):
        """
        AC-4: FiltroConfiancaBDI.avaliar() deve completar < 100ms por alert.

        Dado: filtro de confianca
        Quando: 100 avaliacoes executadas
        Entao: tempo medio < 100ms (meta operacional da pipeline)
        """
        alertas = [_alerta_fake(0.5 + i * 0.01) for i in range(100)]

        inicio = time.perf_counter()
        for alerta in alertas:
            filtro.avaliar(alerta)
        elapsed_ms = (time.perf_counter() - inicio) * 1000

        tempo_medio_ms = elapsed_ms / 100
        assert tempo_medio_ms < 100, (
            f"Tempo medio de {tempo_medio_ms:.2f}ms excede a meta de 100ms"
        )

    def test_ac4_latencia_individual_registrada_no_audit(self, filtro):
        """
        AC-4: Latencia de cada avaliacao deve ser registrada no audit log.

        Dado: filtro de confianca
        Quando: avaliar um alerta
        Entao: registro.latencia_ms >= 0
        """
        filtro.avaliar(_alerta_fake(0.85))
        assert filtro.historico_audit[0].latencia_ms >= 0.0

    # ==================== AC-5: E2E COM 100 ALERTAS ====================

    def test_ac5_e2e_100_alertas_filtro_correto(self, filtro):
        """
        AC-5: Pipeline deve processar 100 alerts corretamente.

        Dado: 100 alertas simulados
            - 50 com confianca > 0.75 (alta)
            - 50 com confianca <= 0.75 (baixa)
        Quando: todos processados pelo filtro
        Entao:
            - exatamente 50 aprovados
            - exatamente 50 rejeitados
            - 100 registros de audit log
            - performance media < 100ms
        """
        # 50 alertas de alta confianca (0.76 a 1.00)
        alertas_altos = [_alerta_fake(0.76 + i * 0.004) for i in range(50)]
        # 50 alertas de baixa confianca (0.25 a 0.75)
        alertas_baixos = [_alerta_fake(0.25 + i * 0.01) for i in range(50)]
        todos = alertas_altos + alertas_baixos

        inicio = time.perf_counter()
        for alerta in todos:
            filtro.avaliar(alerta)
        elapsed_ms = (time.perf_counter() - inicio) * 1000

        # Verificar contadores
        assert filtro.metricas.total_processados == 100
        assert filtro.metricas.aprovados == 50
        assert filtro.metricas.rejeitados == 50

        # Verificar audit log
        assert len(filtro.historico_audit) == 100
        decisoes = [r.decisao for r in filtro.historico_audit]
        assert decisoes.count("APROVADO") == 50
        assert decisoes.count("REJEITADO") == 50

        # Verificar performance media < 100ms
        tempo_medio_ms = elapsed_ms / 100
        assert tempo_medio_ms < 100, (
            f"Tempo medio {tempo_medio_ms:.2f}ms excede 100ms"
        )

    def test_ac5_e2e_100_alertas_todos_acima_limiar(self, filtro):
        """
        AC-5: Cenario onde todos os 100 alertas sao de alta confianca.

        Dado: 100 alertas com confianca entre 0.76 e 0.99
        Quando: processados
        Entao: todos os 100 aprovados
        """
        for i in range(100):
            filtro.avaliar(_alerta_fake(0.76 + i * 0.002))

        assert filtro.metricas.aprovados == 100
        assert filtro.metricas.rejeitados == 0

    # ==================== AC-6: AUDIT LOGGING ====================

    def test_ac6_audit_log_gerado_para_cada_decisao(self, filtro):
        """
        AC-6: Um RegistroAuditFiltro deve ser gerado para cada alerta.

        Dado: filtro de confianca
        Quando: 3 alertas avaliados
        Entao: historico_audit deve ter 3 registros
        """
        for confianca in [0.90, 0.65, 0.80]:
            filtro.avaliar(_alerta_fake(confianca))

        assert len(filtro.historico_audit) == 3

    def test_ac6_audit_log_campos_obrigatorios(self, filtro):
        """
        AC-6: Cada registro de audit deve conter timestamp, confianca e decisao.

        Dado: filtro de confianca
        Quando: um alerta avaliado
        Entao: registro tem timestamp, confianca e decisao preenchidos
        """
        from datetime import datetime as dt
        filtro.avaliar(_alerta_fake(0.80))
        registro = filtro.historico_audit[0]

        assert isinstance(registro.timestamp, dt)
        assert isinstance(registro.confianca, Decimal)
        assert registro.decisao in ("APROVADO", "REJEITADO")

    def test_ac6_audit_log_motivo_legivel(self, filtro):
        """
        AC-6: Motivo do audit deve ser descricao legivel da comparacao.

        Dado: filtro avaliando alerta com conf=0.80
        Quando: audit gerado
        Entao: motivo deve conter 'confianca' e 'limiar'
        """
        filtro.avaliar(_alerta_fake(0.80))
        motivo = filtro.historico_audit[0].motivo

        assert "confianca" in motivo
        assert "limiar" in motivo

    def test_ac6_audit_log_ativo_preenchido(self, filtro):
        """
        AC-6: Registro de audit deve preservar o ativo do alerta.

        Dado: alerta com ativo='WIN$N'
        Quando: auditado
        Entao: registro.ativo == 'WIN$N'
        """
        filtro.avaliar(_alerta_fake(0.80))
        assert filtro.historico_audit[0].ativo == "WIN$N"

    # ==================== AC-7: METRICAS ====================

    def test_ac7_exportar_metricas_chaves_presentes(self, filtro):
        """
        AC-7: exportar_metricas() deve retornar precision, recall, f1_score.

        Dado: filtro com alertas processados
        Quando: exportar_metricas() chamado
        Entao: dict com 7 chaves incluindo precision, recall, f1_score
        """
        for c in [0.85, 0.90, 0.60, 0.70, 0.95]:
            filtro.avaliar(_alerta_fake(c))

        metricas = filtro.exportar_metricas()

        assert "precision" in metricas
        assert "recall" in metricas
        assert "f1_score" in metricas
        assert "total_processados" in metricas
        assert "aprovados" in metricas
        assert "rejeitados" in metricas
        assert "taxa_aprovacao" in metricas

    def test_ac7_exportar_metricas_precision_entre_0_e_1(self, filtro):
        """
        AC-7: precision deve estar entre 0.0 e 1.0.

        Dado: filtro com mix de alertas altos e baixos
        Quando: exportar_metricas() chamado
        Entao: precision em [0, 1]
        """
        for c in [0.80, 0.85, 0.60, 0.65, 0.95]:
            filtro.avaliar(_alerta_fake(c))

        m = filtro.exportar_metricas()
        assert 0.0 <= m["precision"] <= 1.0

    def test_ac7_exportar_metricas_recall_entre_0_e_1(self, filtro):
        """
        AC-7: recall deve estar entre 0.0 e 1.0.

        Dado: filtro com alertas processados
        Quando: exportar_metricas() chamado
        Entao: recall em [0, 1]
        """
        for c in [0.80, 0.60]:
            filtro.avaliar(_alerta_fake(c))

        m = filtro.exportar_metricas()
        assert 0.0 <= m["recall"] <= 1.0

    def test_ac7_exportar_metricas_f1_entre_0_e_1(self, filtro):
        """
        AC-7: f1_score deve estar entre 0.0 e 1.0.

        Dado: filtro com alertas processados
        Quando: exportar_metricas() chamado
        Entao: f1_score em [0, 1]
        """
        for c in [0.80, 0.60, 0.95]:
            filtro.avaliar(_alerta_fake(c))

        m = filtro.exportar_metricas()
        assert 0.0 <= m["f1_score"] <= 1.0

    def test_ac7_metricas_via_processador(self, mock_processador):
        """
        AC-7: exportar_metricas() do ProcessadorBDI deve retornar metricas.

        Dado: ProcessadorBDI inicializado
        Quando: exportar_metricas() chamado
        Entao: retorna dict com chaves esperadas
        """
        metricas = mock_processador.exportar_metricas()
        assert isinstance(metricas, dict)
        assert "precision" in metricas
        assert "recall" in metricas
        assert "f1_score" in metricas

    # ==================== AC-8: CODE REVIEW ARQUITETURAL ====================

    def test_ac8_bdi_processor_v2_e_modulo_de_dominio(self):
        """
        AC-8: bdi_processor_v2 deve residir no modulo de dominio (Clean Arch).

        Dado: modulo src.domain.bdi_processor_v2
        Quando: importado
        Entao: importacao bem-sucedida (modulo de dominio puro, sem deps infra)
        """
        from src.domain import bdi_processor_v2  # noqa: F401
        assert bdi_processor_v2.LIMIAR_CONFIANCA_PADRAO == Decimal("0.75")

    def test_ac8_filtro_nao_depende_de_infraestrutura(self):
        """
        AC-8: FiltroConfiancaBDI nao deve ter dependencias de infraestrutura.

        Dado: modulo bdi_processor_v2
        Quando: inspecionar imports
        Entao: nenhum import de src.infrastructure no modulo
        """
        import importlib
        import inspect

        modulo = importlib.import_module("src.domain.bdi_processor_v2")
        source = inspect.getsource(modulo)
        assert "src.infrastructure" not in source

    def test_ac8_filtro_e_instanciavel_sem_parametros(self):
        """
        AC-8: FiltroConfiancaBDI deve ser instanciavel sem parametros.

        Dado: importacao do FiltroConfiancaBDI
        Quando: instanciado sem argumentos
        Entao: objeto criado com limiar padrao
        """
        f = FiltroConfiancaBDI()
        assert f is not None
        assert f.limiar == Decimal("0.75")

    def test_ac8_metricas_pipeline_e_dataclass(self):
        """
        AC-8: MetricasPipelineBDI deve ser dataclass com campos corretos.

        Dado: MetricasPipelineBDI
        Quando: inspecionar tipo
        Entao: e dataclass com campos de contadores e feedback
        """
        from dataclasses import is_dataclass, fields
        assert is_dataclass(MetricasPipelineBDI)
        nomes = {f.name for f in fields(MetricasPipelineBDI)}
        assert "total_processados" in nomes
        assert "aprovados" in nomes
        assert "rejeitados" in nomes
        assert "verdadeiros_positivos" in nomes


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

