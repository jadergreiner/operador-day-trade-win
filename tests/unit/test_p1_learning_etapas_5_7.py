"""
Testes unitarios para P1-LEARNING Etapas 5-7:
  - Etapa 5: L1 Decision Correctness Analysis (p1_learning_l1_analysis.py)
  - Etapa 6: L2 Causal Drift Detection (p1_learning_l2_causal.py)
  - Etapa 7: Learning Rule Generation (p1_learning_regras.py)
  - Relatorio de Sessao (p1_learning_relatorio.py)

Criterios de aceite (PO):
  1. l1_analysis_YYYYMMDD.jsonl gerado com >= 1 entrada por sessao
  2. learning_rules_YYYYMMDD.json com campos contexto/acao_evitar/frequencia/confianca
  3. p1_learning_report_YYYYMMDD.md gerado sem stack traces
  4. pytest >= 85% cobertura nos novos modulos
  5. mypy --strict: zero erros novos
"""

from __future__ import annotations

import json
import tempfile
from datetime import datetime
from pathlib import Path
from typing import Any
from unittest.mock import MagicMock, patch

import pytest

from src.application.p1_learning_closure import (
    ClosureRecord,
    MotivoFechamento,
    OutcomeType,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _closure(
    outcome: OutcomeType = OutcomeType.LOSS,
    motivo: MotivoFechamento = MotivoFechamento.SL_ATINGIDO,
    pnl_pct: float = -1.0,
    pnl: float = -500.0,
    market_conditions: dict[str, Any] | None = None,
    episode_id: str = "EP_001",
) -> ClosureRecord:
    return ClosureRecord(
        closure_id="CLO_001",
        episode_id=episode_id,
        trade_id="TRD_001",
        timestamp_fechamento=datetime(2026, 4, 2, 10, 30, 0),
        preco_entrada=128000.0,
        preco_saida=127500.0,
        outcome=outcome,
        motivo_fechamento=motivo,
        pnl_realizado=pnl,
        pnl_realizado_pct=pnl_pct,
        duracao_total_segundos=300.0,
        market_conditions=market_conditions or {},
    )


# ---------------------------------------------------------------------------
# ETAPA 5 — L1 Decision Correctness Analysis
# ---------------------------------------------------------------------------

class TestL1Analysis:
    """Testes para AnalisadorDecisaoL1 (p1_learning_l1_analysis.py)."""

    def _analisador(self, registros: list[ClosureRecord]) -> Any:
        from src.application.p1_learning_l1_analysis import AnalisadorDecisaoL1

        analisador = AnalisadorDecisaoL1.__new__(AnalisadorDecisaoL1)
        analisador._registros = registros
        analisador._sessao_id = "SESSAO_TEST_001"
        return analisador

    def test_win_tp_condicoes_favoraveis_score_alto(self) -> None:
        """WIN por TP com condicoes favoraveis → corretude >= 0.9."""
        from src.application.p1_learning_l1_analysis import AnalisadorDecisaoL1

        rec = _closure(
            outcome=OutcomeType.WIN,
            motivo=MotivoFechamento.TP_ATINGIDO,
            pnl_pct=1.5,
            pnl=750.0,
            market_conditions={"volatilidade": "baixa", "tendencia": "UP"},
        )
        analisador = self._analisador([rec])
        resultado = analisador.avaliar_corretude_decisao(rec)
        assert resultado.corretude_decisao >= 0.9

    def test_loss_sl_volatilidade_alta_score_aceitavel(self) -> None:
        """LOSS por SL com volatilidade alta → corretude >= 0.5."""
        from src.application.p1_learning_l1_analysis import AnalisadorDecisaoL1

        rec = _closure(
            outcome=OutcomeType.LOSS,
            motivo=MotivoFechamento.SL_ATINGIDO,
            pnl_pct=-1.2,
            market_conditions={"volatilidade": "alta"},
        )
        analisador = self._analisador([rec])
        resultado = analisador.avaliar_corretude_decisao(rec)
        assert resultado.corretude_decisao >= 0.5

    def test_loss_sl_volatilidade_baixa_score_baixo(self) -> None:
        """LOSS por SL com volatilidade baixa → corretude < 0.5."""
        from src.application.p1_learning_l1_analysis import AnalisadorDecisaoL1

        rec = _closure(
            outcome=OutcomeType.LOSS,
            motivo=MotivoFechamento.SL_ATINGIDO,
            pnl_pct=-1.5,
            market_conditions={"volatilidade": "baixa"},
        )
        analisador = self._analisador([rec])
        resultado = analisador.avaliar_corretude_decisao(rec)
        assert resultado.corretude_decisao < 0.5

    def test_breakeven_score_medio(self) -> None:
        """BREAKEVEN → corretude == 0.5."""
        from src.application.p1_learning_l1_analysis import AnalisadorDecisaoL1

        rec = _closure(
            outcome=OutcomeType.BREAKEVEN,
            motivo=MotivoFechamento.FECHAMENTO_MANUAL,
            pnl_pct=0.0,
        )
        analisador = self._analisador([rec])
        resultado = analisador.avaliar_corretude_decisao(rec)
        assert resultado.corretude_decisao == pytest.approx(0.5, abs=0.01)

    def test_resultado_l1_tem_todos_campos(self) -> None:
        """ResultadoL1 deve ter todos os campos obrigatorios."""
        from src.application.p1_learning_l1_analysis import (
            AnalisadorDecisaoL1,
            ResultadoL1,
        )

        rec = _closure()
        analisador = self._analisador([rec])
        resultado = analisador.avaliar_corretude_decisao(rec)
        assert isinstance(resultado, ResultadoL1)
        assert resultado.closure_id
        assert resultado.episode_id
        assert resultado.outcome
        assert resultado.diagnostico
        assert resultado.sessao_id == "SESSAO_TEST_001"
        assert isinstance(resultado.timestamp_analise, datetime)

    def test_analisar_sessao_retorna_lista(self) -> None:
        """analisar_sessao() retorna lista com 1 ResultadoL1 por registro."""
        from src.application.p1_learning_l1_analysis import AnalisadorDecisaoL1

        registros = [_closure() for _ in range(3)]
        analisador = self._analisador(registros)
        resultados = analisador.analisar_sessao()
        assert len(resultados) == 3

    def test_analisar_sessao_vazia_retorna_lista_vazia(self) -> None:
        """analisar_sessao() com 0 registros ja carregados retorna lista vazia."""
        from src.application.p1_learning_l1_analysis import AnalisadorDecisaoL1
        import tempfile

        with tempfile.TemporaryDirectory() as tmp:
            analisador = AnalisadorDecisaoL1(
                db_path=Path(tmp) / "vazio.db",
                sessao_id="SESSAO_VAZIA",
            )
            # _registros vazio + banco nao existente → lista vazia
            resultados = analisador.analisar_sessao()
            assert resultados == []

    def test_persistir_analise_cria_jsonl(self) -> None:
        """persistir_analise() cria arquivo .jsonl com 1 linha por resultado."""
        from src.application.p1_learning_l1_analysis import AnalisadorDecisaoL1

        registros = [_closure()]
        analisador = self._analisador(registros)
        resultados = analisador.analisar_sessao()

        with tempfile.TemporaryDirectory() as tmp:
            caminho = analisador.persistir_analise(resultados, Path(tmp))
            assert caminho.suffix == ".jsonl"
            linhas = caminho.read_text(encoding="utf-8").strip().splitlines()
            assert len(linhas) == 1
            dado = json.loads(linhas[0])
            assert "closure_id" in dado
            assert "corretude_decisao" in dado

    def test_persistir_analise_multiplos_registros(self) -> None:
        """persistir_analise() com N registros gera N linhas no .jsonl."""
        from src.application.p1_learning_l1_analysis import AnalisadorDecisaoL1

        registros = [
            _closure(episode_id=f"EP_{i:03d}") for i in range(5)
        ]
        analisador = self._analisador(registros)
        resultados = analisador.analisar_sessao()

        with tempfile.TemporaryDirectory() as tmp:
            caminho = analisador.persistir_analise(resultados, Path(tmp))
            linhas = caminho.read_text(encoding="utf-8").strip().splitlines()
            assert len(linhas) == 5

    def test_timeout_loss_score_especifico(self) -> None:
        """LOSS por TIMEOUT → corretude == 0.4."""
        from src.application.p1_learning_l1_analysis import AnalisadorDecisaoL1

        rec = _closure(
            outcome=OutcomeType.LOSS,
            motivo=MotivoFechamento.TIMEOUT,
            pnl_pct=-0.3,
        )
        analisador = self._analisador([rec])
        resultado = analisador.avaliar_corretude_decisao(rec)
        assert resultado.corretude_decisao == pytest.approx(0.4, abs=0.01)


# ---------------------------------------------------------------------------
# ETAPA 6 — L2 Causal Drift Detection
# ---------------------------------------------------------------------------

class TestL2Causal:
    """Testes para DetectorCausalL2 (p1_learning_l2_causal.py)."""

    def _detector(self, **kwargs: Any) -> Any:
        from src.application.ac6_7_drift_detector import DriftDetector
        from src.application.p1_learning_l2_causal import DetectorCausalL2

        det = DriftDetector(
            baseline_win_rate=kwargs.get("baseline_win_rate", 0.59),
            baseline_sharpe=kwargs.get("baseline_sharpe", 1.0),
        )
        return DetectorCausalL2(
            detector=det,
            min_episodios=kwargs.get("min_episodios", 3),
            sessao_id="SESSAO_TEST_001",
        )

    def _closures_win(self, n: int) -> list[ClosureRecord]:
        return [
            _closure(
                outcome=OutcomeType.WIN,
                motivo=MotivoFechamento.TP_ATINGIDO,
                pnl_pct=1.0,
                pnl=500.0,
                episode_id=f"EP_{i:03d}",
            )
            for i in range(n)
        ]

    def _closures_loss(self, n: int) -> list[ClosureRecord]:
        return [
            _closure(
                outcome=OutcomeType.LOSS,
                motivo=MotivoFechamento.SL_ATINGIDO,
                pnl_pct=-1.0,
                pnl=-500.0,
                episode_id=f"EP_L{i:03d}",
            )
            for i in range(n)
        ]

    def test_adaptar_registros_mapeia_outcome_e_pnl(self) -> None:
        """adaptar_registros() deve produzir objetos com .outcome e .pnl."""
        detector = self._detector()
        rec = _closure(
            outcome=OutcomeType.WIN,
            pnl=750.0,
        )
        adaptados = detector.adaptar_registros([rec])
        assert len(adaptados) == 1
        assert adaptados[0].outcome == "WIN"
        assert adaptados[0].pnl == pytest.approx(750.0)

    def test_resultado_l2_tem_campos_obrigatorios(self) -> None:
        """ResultadoL2 deve ter todos os campos definidos no contrato."""
        from src.application.p1_learning_l2_causal import ResultadoL2

        detector = self._detector()
        registros = self._closures_win(5)
        resultado = detector.detectar(registros)
        assert isinstance(resultado, ResultadoL2)
        assert resultado.sessao_id
        assert resultado.n_episodios == 5
        assert isinstance(resultado.win_rate_sessao, float)
        assert isinstance(resultado.drift_detectado, bool)
        assert resultado.causa_dominante in (
            "DRIFT_REGIME", "ERRO_DECISAO", "AMOSTRA_INSUFICIENTE", "OK"
        )
        assert 0.0 <= resultado.confianca <= 1.0

    def test_amostra_insuficiente_retorna_flag(self) -> None:
        """Menos de min_episodios → causa_dominante = AMOSTRA_INSUFICIENTE."""
        detector = self._detector(min_episodios=5)
        registros = self._closures_loss(2)
        resultado = detector.detectar(registros)
        assert resultado.causa_dominante == "AMOSTRA_INSUFICIENTE"

    def test_sessao_100_pct_loss_detecta_erro_decisao(self) -> None:
        """Sessao com 100% LOSS sem drift de regime → ERRO_DECISAO."""
        detector = self._detector(min_episodios=3)
        registros = self._closures_loss(8)
        resultado = detector.detectar(registros)
        assert resultado.win_rate_sessao == pytest.approx(0.0)
        # Com win_rate=0 e baseline=0.59, deve detectar drift ou ERRO_DECISAO
        assert resultado.causa_dominante in ("DRIFT_REGIME", "ERRO_DECISAO")

    def test_sessao_normal_retorna_ok(self) -> None:
        """Sessao com win_rate proximo ao baseline retorna causa OK."""
        # Usa baseline_win_rate=0.0 para nao detectar drift
        from src.application.ac6_7_drift_detector import DriftDetector
        from src.application.p1_learning_l2_causal import DetectorCausalL2

        det = DriftDetector(
            baseline_win_rate=0.0,
            baseline_sharpe=0.0,
            baseline_f1=0.0,
        )
        detector = DetectorCausalL2(
            detector=det,
            min_episodios=3,
            sessao_id="SESSAO_OK",
        )
        registros = self._closures_win(5)
        resultado = detector.detectar(registros)
        assert resultado.causa_dominante == "OK"

    def test_alertas_drift_serializaveis(self) -> None:
        """alertas_drift deve ser serializavel para JSON."""
        detector = self._detector()
        registros = self._closures_loss(10)
        resultado = detector.detectar(registros)
        # Deve serializar sem erro
        serializado = json.dumps(resultado.alertas_drift)
        assert isinstance(serializado, str)

    def test_resultado_l2_win_rate_calculado_corretamente(self) -> None:
        """win_rate_sessao deve refletir proporcao correta de wins."""
        detector = self._detector(min_episodios=1)
        registros = self._closures_win(3) + self._closures_loss(7)
        resultado = detector.detectar(registros)
        assert resultado.win_rate_sessao == pytest.approx(0.3)
        assert resultado.n_episodios == 10


# ---------------------------------------------------------------------------
# ETAPA 7 — Learning Rule Generation
# ---------------------------------------------------------------------------

class TestGeradorRegras:
    """Testes para GeradorRegraAprendizado (p1_learning_regras.py)."""

    def _fazer_resultados_l1(self, n_incorretos: int = 3) -> Any:
        from src.application.p1_learning_l1_analysis import (
            AnalisadorDecisaoL1,
            ResultadoL1,
        )

        resultados = []
        for i in range(n_incorretos):
            resultados.append(
                ResultadoL1(
                    closure_id=f"CLO_{i:03d}",
                    episode_id=f"EP_{i:03d}",
                    outcome="LOSS",
                    motivo_fechamento="SL_ATINGIDO",
                    corretude_decisao=0.2,
                    contexto_mercado={"volatilidade": "baixa"},
                    diagnostico="LOSS por SL com volatilidade baixa",
                    sessao_id="SESSAO_TEST",
                    timestamp_analise=datetime(2026, 4, 2, 17, 0, 0),
                )
            )
        return resultados

    def _fazer_resultado_l2(self, causa: str = "ERRO_DECISAO") -> Any:
        from src.application.p1_learning_l2_causal import ResultadoL2

        return ResultadoL2(
            sessao_id="SESSAO_TEST",
            timestamp_analise=datetime(2026, 4, 2, 17, 0, 0),
            n_episodios=5,
            win_rate_sessao=0.2,
            sharpe_sessao=-0.5,
            drift_detectado=False,
            alertas_drift=[],
            causa_dominante=causa,
            confianca=0.75,
        )

    def test_regras_geradas_para_padroes_de_erro(self) -> None:
        """sintetizar_padroes() retorna pelo menos 1 regra quando ha erros."""
        from src.application.p1_learning_regras import GeradorRegraAprendizado

        gerador = GeradorRegraAprendizado()
        r_l1 = self._fazer_resultados_l1(n_incorretos=3)
        r_l2 = self._fazer_resultado_l2()
        regras = gerador.sintetizar_padroes(r_l1, r_l2)
        assert len(regras) >= 1

    def test_regra_tem_campos_obrigatorios(self) -> None:
        """Cada RegraAprendizado deve ter os 7 campos do contrato."""
        from src.application.p1_learning_regras import (
            GeradorRegraAprendizado,
            RegraAprendizado,
        )

        gerador = GeradorRegraAprendizado()
        r_l1 = self._fazer_resultados_l1()
        r_l2 = self._fazer_resultado_l2()
        regras = gerador.sintetizar_padroes(r_l1, r_l2)
        for regra in regras:
            assert isinstance(regra, RegraAprendizado)
            assert regra.regra_id
            assert regra.contexto
            assert regra.acao_evitar
            assert isinstance(regra.frequencia, int) and regra.frequencia >= 1
            assert 0.0 <= regra.confianca <= 1.0
            assert regra.fonte in ("L1", "L2", "L1+L2")
            assert isinstance(regra.gerado_em, datetime)

    def test_sem_erros_nao_gera_regras(self) -> None:
        """Com todos os resultados L1 corretos (corretude >= 0.5), regras minimas."""
        from src.application.p1_learning_l1_analysis import ResultadoL1
        from src.application.p1_learning_regras import GeradorRegraAprendizado

        gerador = GeradorRegraAprendizado()
        r_l1 = [
            ResultadoL1(
                closure_id="CLO_OK",
                episode_id="EP_OK",
                outcome="WIN",
                motivo_fechamento="TP_ATINGIDO",
                corretude_decisao=0.95,
                contexto_mercado={},
                diagnostico="WIN OK",
                sessao_id="SESSAO_TEST",
                timestamp_analise=datetime(2026, 4, 2, 17, 0, 0),
            )
        ]
        r_l2 = self._fazer_resultado_l2(causa="OK")
        regras = gerador.sintetizar_padroes(r_l1, r_l2)
        # Nenhum erro → nenhuma regra de correcao necessaria
        assert len(regras) == 0

    def test_persistir_regras_cria_json_valido(self) -> None:
        """persistir_regras() cria JSON com campos sessao_id e regras."""
        from src.application.p1_learning_regras import GeradorRegraAprendizado

        gerador = GeradorRegraAprendizado()
        r_l1 = self._fazer_resultados_l1()
        r_l2 = self._fazer_resultado_l2()
        regras = gerador.sintetizar_padroes(r_l1, r_l2)

        with tempfile.TemporaryDirectory() as tmp:
            caminho = gerador.persistir_regras(
                regras, r_l2, Path(tmp)
            )
            assert caminho.suffix == ".json"
            dado = json.loads(caminho.read_text(encoding="utf-8"))
            assert "sessao_id" in dado
            assert "regras" in dado
            assert "gerado_em" in dado
            assert "n_episodios_analisados" in dado
            assert "causa_dominante" in dado

    def test_persistir_regras_estrutura_cada_regra(self) -> None:
        """Cada regra no JSON tem os 6 campos do contrato."""
        from src.application.p1_learning_regras import GeradorRegraAprendizado

        gerador = GeradorRegraAprendizado()
        r_l1 = self._fazer_resultados_l1()
        r_l2 = self._fazer_resultado_l2()
        regras = gerador.sintetizar_padroes(r_l1, r_l2)

        with tempfile.TemporaryDirectory() as tmp:
            caminho = gerador.persistir_regras(regras, r_l2, Path(tmp))
            dado = json.loads(caminho.read_text(encoding="utf-8"))
            for r in dado["regras"]:
                assert "regra_id" in r
                assert "contexto" in r
                assert "acao_evitar" in r
                assert "frequencia" in r
                assert "confianca" in r
                assert "fonte" in r

    def test_drift_regime_gera_regra_fonte_l2(self) -> None:
        """Quando causa=DRIFT_REGIME, ao menos uma regra deve ter fonte L2."""
        from src.application.p1_learning_l1_analysis import ResultadoL1
        from src.application.p1_learning_regras import GeradorRegraAprendizado

        gerador = GeradorRegraAprendizado()
        r_l1 = self._fazer_resultados_l1(n_incorretos=2)
        r_l2 = self._fazer_resultado_l2(causa="DRIFT_REGIME")
        regras = gerador.sintetizar_padroes(r_l1, r_l2)
        fontes = {r.fonte for r in regras}
        assert "L2" in fontes or "L1+L2" in fontes

    def test_regras_frequencia_agregada_corretamente(self) -> None:
        """Multiplos episodios com mesmo contexto de erro devem ser agrupados."""
        from src.application.p1_learning_l1_analysis import ResultadoL1
        from src.application.p1_learning_regras import GeradorRegraAprendizado

        gerador = GeradorRegraAprendizado()
        # 5 erros identicos de volatilidade baixa
        r_l1 = self._fazer_resultados_l1(n_incorretos=5)
        r_l2 = self._fazer_resultado_l2()
        regras = gerador.sintetizar_padroes(r_l1, r_l2)
        # A regra agrupada deve ter frequencia >= 2 (varios episodios)
        assert any(r.frequencia >= 2 for r in regras)


# ---------------------------------------------------------------------------
# RELATORIO DE SESSAO
# ---------------------------------------------------------------------------

class TestRelatorioSessao:
    """Testes para RelatorioSessao (p1_learning_relatorio.py)."""

    def _dados_relatorio(self) -> tuple[Any, Any, Any]:
        from src.application.p1_learning_l1_analysis import ResultadoL1
        from src.application.p1_learning_l2_causal import ResultadoL2
        from src.application.p1_learning_regras import GeradorRegraAprendizado

        r_l1 = [
            ResultadoL1(
                closure_id="CLO_001",
                episode_id="EP_001",
                outcome="LOSS",
                motivo_fechamento="SL_ATINGIDO",
                corretude_decisao=0.2,
                contexto_mercado={"volatilidade": "baixa"},
                diagnostico="LOSS por SL com volatilidade baixa",
                sessao_id="SESSAO_TEST",
                timestamp_analise=datetime(2026, 4, 2, 17, 0, 0),
            )
        ]
        r_l2 = ResultadoL2(
            sessao_id="SESSAO_TEST",
            timestamp_analise=datetime(2026, 4, 2, 17, 0, 0),
            n_episodios=1,
            win_rate_sessao=0.0,
            sharpe_sessao=-0.5,
            drift_detectado=False,
            alertas_drift=[],
            causa_dominante="ERRO_DECISAO",
            confianca=0.7,
        )
        gerador = GeradorRegraAprendizado()
        from src.application.p1_learning_l1_analysis import ResultadoL1 as _R1

        regras = gerador.sintetizar_padroes(r_l1, r_l2)
        return r_l1, r_l2, regras

    def test_relatorio_cria_arquivo_md(self) -> None:
        """gerar_relatorio_md() deve criar arquivo .md no diretorio alvo."""
        from src.application.p1_learning_relatorio import RelatorioSessao

        r_l1, r_l2, regras = self._dados_relatorio()
        with tempfile.TemporaryDirectory() as tmp:
            caminho = RelatorioSessao().gerar_relatorio_md(
                r_l1, r_l2, regras, Path(tmp)
            )
            assert caminho.exists()
            assert caminho.suffix == ".md"

    def test_relatorio_contem_secoes_obrigatorias(self) -> None:
        """Relatorio deve ter secoes Resumo, L1, L2 e Regras."""
        from src.application.p1_learning_relatorio import RelatorioSessao

        r_l1, r_l2, regras = self._dados_relatorio()
        with tempfile.TemporaryDirectory() as tmp:
            caminho = RelatorioSessao().gerar_relatorio_md(
                r_l1, r_l2, regras, Path(tmp)
            )
            conteudo = caminho.read_text(encoding="utf-8")
            assert "Resumo" in conteudo
            assert "L1" in conteudo
            assert "L2" in conteudo
            assert "Regras" in conteudo

    def test_relatorio_sem_stack_trace(self) -> None:
        """Relatorio nao deve conter Traceback ou linhas de excecao."""
        from src.application.p1_learning_relatorio import RelatorioSessao

        r_l1, r_l2, regras = self._dados_relatorio()
        with tempfile.TemporaryDirectory() as tmp:
            caminho = RelatorioSessao().gerar_relatorio_md(
                r_l1, r_l2, regras, Path(tmp)
            )
            conteudo = caminho.read_text(encoding="utf-8")
            assert "Traceback" not in conteudo
            assert "Exception" not in conteudo

    def test_relatorio_nome_contem_data(self) -> None:
        """Nome do arquivo deve conter data no formato YYYYMMDD."""
        from src.application.p1_learning_relatorio import RelatorioSessao

        r_l1, r_l2, regras = self._dados_relatorio()
        with tempfile.TemporaryDirectory() as tmp:
            caminho = RelatorioSessao().gerar_relatorio_md(
                r_l1, r_l2, regras, Path(tmp)
            )
            nome = caminho.name
            data_hoje = datetime.now().strftime("%Y%m%d")
            assert data_hoje in nome
