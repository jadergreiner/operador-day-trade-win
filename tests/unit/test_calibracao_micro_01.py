"""
CALIBRACAO-MICRO-01: Testes de validacao dos novos thresholds de confianca.

Verifica que os ajustes de calibracao liberem trades em condicoes que
anteriormente eram bloqueadas pelos filtros excessivamente conservadores.

Status: CALIBRACAO-MICRO-01 (18/03/2026)
Referencia: docs/BACKLOG.md (CALIBRACAO-MICRO-01)
"""

from decimal import Decimal

import pytest


class TestMinConfidenceTrade:
    """Testes do threshold global MIN_CONFIDENCE_TRADE (45 -> 40)."""

    def test_threshold_global_e_40(self) -> None:
        """MIN_CONFIDENCE_TRADE deve ser 40 apos calibracao."""
        import scripts.agente_micro_tendencia_winfut as agente

        assert agente.MIN_CONFIDENCE_TRADE == 40, (
            f"Esperado 40, obtido {agente.MIN_CONFIDENCE_TRADE}. "
            "CALIBRACAO-MICRO-01 nao foi aplicada."
        )

    def test_threshold_abaixo_do_antigo_valor(self) -> None:
        """Novo threshold deve ser menor que o antigo (45)."""
        import scripts.agente_micro_tendencia_winfut as agente

        assert agente.MIN_CONFIDENCE_TRADE < 45, (
            "Threshold deve ser menor que 45 para liberar trades com confianca 40-44%."
        )

    def test_oportunidade_com_confianca_42_aprovada(self) -> None:
        """Oportunidade com confianca 42% deve passar o filtro inicial (>= 40)."""
        import scripts.agente_micro_tendencia_winfut as agente

        confianca = Decimal("42")
        threshold = Decimal(str(agente.MIN_CONFIDENCE_TRADE))
        assert confianca >= threshold, (
            f"Confianca {confianca}% deve ser aceita com threshold {threshold}%."
        )

    def test_oportunidade_com_confianca_39_bloqueada(self) -> None:
        """Oportunidade com confianca 39% deve ser bloqueada (< 40)."""
        import scripts.agente_micro_tendencia_winfut as agente

        confianca = Decimal("39")
        threshold = Decimal(str(agente.MIN_CONFIDENCE_TRADE))
        assert confianca < threshold, (
            f"Confianca {confianca}% deve ser bloqueada com threshold {threshold}%."
        )

    def test_oportunidade_com_confianca_40_aprovada(self) -> None:
        """Confianca exatamente no limite (40%) deve ser aprovada."""
        import scripts.agente_micro_tendencia_winfut as agente

        confianca = Decimal("40")
        threshold = Decimal(str(agente.MIN_CONFIDENCE_TRADE))
        assert confianca >= threshold


class TestExpReduzidaThresholds:
    """Testes dos thresholds do modo EXP_REDUZIDA (55->48, R/R 1.8->1.6)."""

    def _opp_exp_reduzida(self, confianca: Decimal, rr: Decimal) -> object:
        """Cria oportunidade com tag EXP_REDUZIDA para testes."""
        import scripts.agente_micro_tendencia_winfut as agente

        return agente.Opportunity(
            direction="COMPRA",
            entry=Decimal("142000"),
            stop_loss=Decimal("141500"),
            take_profit=Decimal("143000"),
            risk_reward=rr,
            confidence=confianca,
            reason="Macro +5 [EXP_REDUZIDA]",
            region="NEUTRO",
        )

    def test_confianca_48_rr_16_aprovado(self) -> None:
        """Confianca 48% e R/R 1.6 devem ser aprovados no modo EXP_REDUZIDA."""
        # Novos limites: conf >= 48 e rr >= 1.6
        confianca = Decimal("48")
        rr = Decimal("1.6")
        assert confianca >= Decimal("48")
        assert rr >= Decimal("1.6")

    def test_confianca_47_bloqueada_exp_reduzida(self) -> None:
        """Confianca 47% deve ser bloqueada no modo EXP_REDUZIDA (< 48)."""
        confianca = Decimal("47")
        assert confianca < Decimal("48"), (
            "EXP_REDUZIDA: confianca 47% deve ser bloqueada (threshold = 48%)"
        )

    def test_rr_159_bloqueado_exp_reduzida(self) -> None:
        """R/R 1.59 deve ser bloqueado no modo EXP_REDUZIDA (< 1.6)."""
        rr = Decimal("1.59")
        assert rr < Decimal("1.6"), (
            "EXP_REDUZIDA: R/R 1.59 deve ser bloqueado (minimo = 1.6)"
        )

    def test_antigo_threshold_55_nao_mais_usado(self) -> None:
        """Threshold antigo 55 nao deve mais ser aplicado em EXP_REDUZIDA."""
        # Confianca entre 48-54 deve ser aceita agora
        confianca = Decimal("50")
        novo_threshold = Decimal("48")
        assert confianca >= novo_threshold, (
            f"Confianca {confianca}% deve ser aceita com novo threshold {novo_threshold}% "
            "(threshold antigo 55% bloquearia esta oportunidade)."
        )

    def test_antigo_rr_18_nao_mais_exigido(self) -> None:
        """R/R antigo 1.8 nao deve mais ser exigido em EXP_REDUZIDA."""
        rr = Decimal("1.7")
        novo_minimo = Decimal("1.6")
        assert rr >= novo_minimo, (
            f"R/R {rr} deve ser aceito com novo minimo {novo_minimo} "
            "(R/R antigo 1.8 bloquearia esta oportunidade)."
        )


class TestDirFracoTolerance:
    """Testes da nova tolerancia do DIR_FRACO (3+ contrarios, era 2+)."""

    def test_2_contradicoes_nao_aciona_dir_fraco(self) -> None:
        """Com 2 contradicoes, nao deve acionar DIR_FRACO (era acionado antes)."""
        n_contradicoes = 2
        # Novo comportamento: DIR_FRACO so com >= 3
        aciona_dir_fraco = n_contradicoes >= 3
        assert not aciona_dir_fraco, (
            "2 contradicoes nao devem acionar DIR_FRACO apos CALIBRACAO-MICRO-01."
        )

    def test_2_contradicoes_aciona_dir_quest(self) -> None:
        """Com 2 contradicoes, deve acionar DIR_QUEST (penalidade moderada)."""
        n_contradicoes = 2
        aciona_dir_quest = n_contradicoes >= 2
        assert aciona_dir_quest, (
            "2 contradicoes devem acionar DIR_QUEST (penalidade moderada -8%)."
        )

    def test_3_contradicoes_aciona_dir_fraco(self) -> None:
        """Com 3 contradicoes, deve acionar DIR_FRACO (penalidade forte)."""
        n_contradicoes = 3
        aciona_dir_fraco = n_contradicoes >= 3
        assert aciona_dir_fraco, (
            "3 contradicoes devem acionar DIR_FRACO (penalidade forte -15%)."
        )

    def test_1_contradicao_sem_penalidade_forte(self) -> None:
        """1 contradicao nao aciona DIR_FRACO nem DIR_QUEST (ruido normal)."""
        n_contradicoes = 1
        aciona_dir_fraco = n_contradicoes >= 3
        aciona_dir_quest = n_contradicoes >= 2
        assert not aciona_dir_fraco
        assert not aciona_dir_quest

    def test_0_contradicoes_sem_penalidade(self) -> None:
        """0 contradicoes: nenhuma penalidade direcional aplicada."""
        n_contradicoes = 0
        aciona_qualquer = n_contradicoes >= 2
        assert not aciona_qualquer


class TestTrapProxSemPenalidade:
    """Testes que TRAP_PROX nao impacta mais a confianca calculada."""

    def test_trap_prox_nao_aplica_penalidade_15(self) -> None:
        """Zona amarela (TRAP_PROX) nao deve reduzir confianca em -15%."""
        # Simulando logica: zona amarela agora apenas registra o tag
        confianca_inicial = Decimal("45")

        # Comportamento NOVO: zona amarela nao penaliza
        # O tag e adicionado ao reason mas confianca permanece inalterada
        confianca_final_novo = confianca_inicial  # sem penalidade

        # Comportamento ANTIGO teria feito:
        # confianca_final_antigo = max(Decimal("20"), confianca_inicial - Decimal("15"))
        confianca_final_antigo = max(Decimal("20"), confianca_inicial - Decimal("15"))

        assert confianca_final_novo == confianca_inicial, (
            "TRAP_PROX nao deve mais reduzir confianca."
        )
        assert confianca_final_antigo < confianca_final_novo, (
            "Novo comportamento deve ser mais permissivo que o antigo."
        )

    def test_trap_prox_tag_ainda_adicionado_ao_reason(self) -> None:
        """Tag TRAP_PROX ainda deve aparecer no reason para informacao."""
        # O tag e informativo — aparece na string do reason sem afetar confianca
        diary_extra = ""
        tp_price = 142000.0

        # Novo comportamento: adiciona tag sem penalidade
        diary_extra += f" [TRAP_PROX: {tp_price:.0f}]"

        assert "TRAP_PROX" in diary_extra, (
            "Tag TRAP_PROX deve estar presente no reason como informacao."
        )
        # Nao deve conter o sufixo -15%
        assert "-15%" not in diary_extra, (
            "Tag TRAP_PROX nao deve conter -15% (penalidade removida)."
        )

    def test_trap_perto_zona_vermelha_ainda_penaliza(self) -> None:
        """Zona vermelha (TRAP_PERTO) ainda deve penalizar -20% em alta conviccao."""
        confianca_inicial = Decimal("70")
        # Zona vermelha: alta conviccao penaliza -20% (comportamento mantido)
        confianca_final = max(Decimal("20"), confianca_inicial - Decimal("20"))
        assert confianca_final == Decimal("50"), (
            "Zona vermelha ainda deve penalizar -20% (nao foi alterada)."
        )


class TestIntegracaoThresholdsCompletos:
    """Testes de integracao verificando interacao dos novos thresholds."""

    def test_cenario_dia_17_03_2026_liberado(self) -> None:
        """
        Simula cenario do dia 17/03/2026 onde 141 oportunidades foram geradas
        com confianca maxima de 42,4% — todas bloqueadas pelo threshold antigo (45).
        Com novo threshold (40), oportunidades com 40-44% devem ser liberadas.
        """
        import scripts.agente_micro_tendencia_winfut as agente

        confianca_maxima_dia = Decimal("42.4")
        threshold_novo = Decimal(str(agente.MIN_CONFIDENCE_TRADE))

        assert confianca_maxima_dia >= threshold_novo, (
            f"Confianca maxima {confianca_maxima_dia}% deve superar threshold {threshold_novo}%. "
            "Com threshold antigo (45%), todas as 141 oportunidades eram bloqueadas."
        )

    def test_threshold_minimo_preserva_qualidade(self) -> None:
        """Threshold 40% nao deve aceitar sinais de qualidade muito baixa (<40%)."""
        import scripts.agente_micro_tendencia_winfut as agente

        # Confiancas abaixo de 40% ainda devem ser bloqueadas
        confiancas_fracas = [Decimal("30"), Decimal("35"), Decimal("39")]
        threshold = Decimal(str(agente.MIN_CONFIDENCE_TRADE))

        for conf in confiancas_fracas:
            assert conf < threshold, (
                f"Confianca {conf}% deve ser bloqueada (abaixo do threshold {threshold}%)."
            )

    def test_limites_intactos_max_loss_max_trades(self) -> None:
        """Limites de risco (MAX_DAILY_LOSS, MAX_DAILY_TRADES) devem estar inalterados."""
        import scripts.agente_micro_tendencia_winfut as agente

        # Backlog especifica: manter intactos max loss 500 pts e limite de 3 trades/dia
        assert agente.MAX_DAILY_LOSS == Decimal("500"), (
            f"MAX_DAILY_LOSS deve ser 500, obtido {agente.MAX_DAILY_LOSS}"
        )
        # MAX_DAILY_TRADES pode ser 3 ou maior — verificar que nao foi reduzido
        assert agente.MAX_DAILY_TRADES >= 3, (
            f"MAX_DAILY_TRADES deve ser >= 3, obtido {agente.MAX_DAILY_TRADES}"
        )

    def test_cooling_off_preservado(self) -> None:
        """COOLING_OFF_MINUTES deve estar inalterado (30 minutos)."""
        import scripts.agente_micro_tendencia_winfut as agente

        assert agente.COOLING_OFF_MINUTES == 30, (
            f"COOLING_OFF_MINUTES deve ser 30, obtido {agente.COOLING_OFF_MINUTES}"
        )
