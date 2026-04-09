"""
Testes para Motor de Decisão Isolado por Agent ID

Validação de:
- Isolamento completo entre agentes
- Registro de posições, decisões e histórico
- Persistência em JSON por agent_id
- Cálculo correto de P&L
- Estatísticas de performance
"""

import json
import pytest
import tempfile
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional

from src.application.motor_decisao_isolado import (
    MotorDecisaoIsolado,
    PosicaoAberta,
    DecisaoRegistrada,
    HistoricoFechamento,
    DecisaoOperacional,
    TipoPosicao,
    MotivoFechamento,
)


@pytest.fixture
def temp_data_dir():
    """Cria diretório temporário para testes."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir)


@pytest.fixture
def motor_agente_5000(temp_data_dir):
    """Cria motor isolado para agente_5000."""
    return MotorDecisaoIsolado(agent_id='agente_5000', data_dir=temp_data_dir)


@pytest.fixture
def motor_agente_direto(temp_data_dir):
    """Cria motor isolado para agente_direto."""
    return MotorDecisaoIsolado(agent_id='agente_direto_20260316', data_dir=temp_data_dir)


class TestDataClasses:
    """Testes das dataclasses."""

    def test_posicao_aberta_criacao_valida(self):
        """Testa criação de PosicaoAberta."""
        pos = PosicaoAberta(
            ticket=123456,
            agent_id='agente_5000',
            tipo=TipoPosicao.COMPRADA,
            preco_entrada=100.0,
            volume=1.0,
            stop_loss=99.0,
            take_profit=102.0,
            timestamp_abertura=datetime.now().isoformat(),
        )
        assert pos.ticket == 123456
        assert pos.agent_id == 'agente_5000'
        assert pos.tipo == TipoPosicao.COMPRADA

    def test_posicao_para_dict(self):
        """Testa conversão de PosicaoAberta para dict."""
        pos = PosicaoAberta(
            ticket=123456,
            agent_id='agente_5000',
            tipo=TipoPosicao.VENDIDA,
            preco_entrada=100.0,
            volume=1.0,
            stop_loss=101.0,
            take_profit=98.0,
            timestamp_abertura=datetime.now().isoformat(),
        )
        d = pos.para_dict()
        assert d['ticket'] == 123456
        assert d['agent_id'] == 'agente_5000'
        assert d['tipo'] == 'SELL'

    def test_decisao_registrada_criacao(self):
        """Testa criação de DecisaoRegistrada."""
        dec = DecisaoRegistrada(
            agent_id='agente_5000',
            timestamp=datetime.now().isoformat(),
            decisao=DecisaoOperacional.ABRIR,
            ticket=123456,
            reasoning='Sinal RL confirmado',
            confianca=0.85,
            fatores=['rsi_baixo', 'volume_crescente'],
        )
        assert dec.agent_id == 'agente_5000'
        assert dec.decisao == DecisaoOperacional.ABRIR
        assert dec.confianca == 0.85

    def test_historico_fechamento_criacao(self):
        """Testa criação de HistoricoFechamento."""
        hist = HistoricoFechamento(
            ticket=123456,
            agent_id='agente_5000',
            tipo=TipoPosicao.COMPRADA,
            preco_entrada=100.0,
            preco_saida=102.0,
            volume=1.0,
            pnl_reais=200.0,
            pnl_pct=2.0,
            motivo=MotivoFechamento.TP_ATINGIDO,
            duracao_minutos=15.5,
            timestamp_abertura=datetime.now().isoformat(),
            timestamp_fechamento=datetime.now().isoformat(),
        )
        assert hist.pnl_reais == 200.0
        assert hist.motivo == MotivoFechamento.TP_ATINGIDO

    def test_historico_fechamento_resultado_none_por_padrao(self):
        """Resultado deve ser None por padrao (campo nao obrigatorio)."""
        hist = HistoricoFechamento(
            ticket=1001,
            agent_id='agente_5000',
            tipo=TipoPosicao.COMPRADA,
            preco_entrada=120000.0,
            preco_saida=120500.0,
            volume=1.0,
            pnl_reais=25.0,
            pnl_pct=0.42,
            motivo=MotivoFechamento.TP_ATINGIDO,
            duracao_minutos=12.0,
            timestamp_abertura='2026-04-02T09:00:00',
            timestamp_fechamento='2026-04-02T09:12:00',
        )
        assert hist.resultado is None

    def test_historico_fechamento_aceita_resultado_win(self):
        """Resultado aceita literal WIN."""
        hist = HistoricoFechamento(
            ticket=1002,
            agent_id='agente_5000',
            tipo=TipoPosicao.COMPRADA,
            preco_entrada=120000.0,
            preco_saida=120600.0,
            volume=1.0,
            pnl_reais=60.0,
            pnl_pct=0.50,
            motivo=MotivoFechamento.TP_ATINGIDO,
            duracao_minutos=10.0,
            timestamp_abertura='2026-04-02T09:00:00',
            timestamp_fechamento='2026-04-02T09:10:00',
            resultado='WIN',
        )
        assert hist.resultado == 'WIN'

    def test_historico_fechamento_aceita_resultado_loss(self):
        """Resultado aceita literal LOSS."""
        hist = HistoricoFechamento(
            ticket=1003,
            agent_id='agente_5000',
            tipo=TipoPosicao.COMPRADA,
            preco_entrada=120000.0,
            preco_saida=119700.0,
            volume=1.0,
            pnl_reais=-30.0,
            pnl_pct=-0.25,
            motivo=MotivoFechamento.SL_ATINGIDO,
            duracao_minutos=5.0,
            timestamp_abertura='2026-04-02T09:00:00',
            timestamp_fechamento='2026-04-02T09:05:00',
            resultado='LOSS',
        )
        assert hist.resultado == 'LOSS'

    def test_historico_fechamento_aceita_resultado_breakeven(self):
        """Resultado aceita literal BREAKEVEN."""
        hist = HistoricoFechamento(
            ticket=1004,
            agent_id='agente_5000',
            tipo=TipoPosicao.COMPRADA,
            preco_entrada=120000.0,
            preco_saida=120040.0,
            volume=1.0,
            pnl_reais=4.0,
            pnl_pct=0.03,
            motivo=MotivoFechamento.MANUAL,
            duracao_minutos=8.0,
            timestamp_abertura='2026-04-02T09:00:00',
            timestamp_fechamento='2026-04-02T09:08:00',
            resultado='BREAKEVEN',
        )
        assert hist.resultado == 'BREAKEVEN'


class TestMotorIsolamento:
    """Testes de isolamento entre agentes."""

    def test_arquivos_isolados_por_agent_id(self, motor_agente_5000, motor_agente_direto, temp_data_dir):
        """Verifica que cada agente tem arquivos separados."""
        assert motor_agente_5000.posicoes_ativas_file.name == 'posicoes_ativas_agente_5000.json'
        assert motor_agente_direto.posicoes_ativas_file.name == 'posicoes_ativas_agente_direto_20260316.json'
        assert motor_agente_5000.posicoes_ativas_file != motor_agente_direto.posicoes_ativas_file

    def test_posicoes_nao_variam_entre_agentes(self, motor_agente_5000, motor_agente_direto):
        """Testa que posição aberta em agente_5000 não afeta agente_direto."""
        # Abrir posição no agente_5000
        motor_agente_5000.abrir_posicao(
            ticket=100001,
            tipo=TipoPosicao.COMPRADA,
            preco_entrada=100.0,
            volume=1.0,
            stop_loss=99.0,
            take_profit=102.0,
        )

        # Verificar que agente_direto não vê essa posição
        assert motor_agente_5000.tem_posicao_aberta() == True
        assert motor_agente_direto.tem_posicao_aberta() == False

    def test_historico_isolado_por_agent(self, motor_agente_5000, motor_agente_direto):
        """Testa que histórico de um agente não aparece no outro."""
        # Abrir e fechar em agente_5000
        motor_agente_5000.abrir_posicao(
            ticket=100001,
            tipo=TipoPosicao.COMPRADA,
            preco_entrada=100.0,
            volume=1.0,
            stop_loss=99.0,
            take_profit=102.0,
        )
        motor_agente_5000.fechar_posicao(100001, 102.0, MotivoFechamento.TP_ATINGIDO)

        # Verificar isolamento
        assert len(motor_agente_5000.historico) == 1
        assert len(motor_agente_direto.historico) == 0


class TestAbrirPosicao:
    """Testes de abertura de posição."""

    def test_abrir_posicao_comprada(self, motor_agente_5000):
        """Testa abertura de posição COMPRADA."""
        sucesso = motor_agente_5000.abrir_posicao(
            ticket=123456,
            tipo=TipoPosicao.COMPRADA,
            preco_entrada=100.0,
            volume=1.0,
            stop_loss=99.0,
            take_profit=102.0,
        )
        assert sucesso == True
        assert motor_agente_5000.tem_posicao_aberta() == True
        assert len(motor_agente_5000.posicoes_ativas) == 1

    def test_abrir_posicao_vendida(self, motor_agente_5000):
        """Testa abertura de posição VENDIDA."""
        sucesso = motor_agente_5000.abrir_posicao(
            ticket=654321,
            tipo=TipoPosicao.VENDIDA,
            preco_entrada=100.0,
            volume=1.0,
            stop_loss=101.0,
            take_profit=98.0,
        )
        assert sucesso == True
        posicao = motor_agente_5000.obter_posicao(654321)
        assert posicao.tipo == TipoPosicao.VENDIDA

    def test_nao_abrir_posicao_duplicada(self, motor_agente_5000):
        """Testa que não permite abrir mesma posição 2x."""
        motor_agente_5000.abrir_posicao(
            ticket=123456,
            tipo=TipoPosicao.COMPRADA,
            preco_entrada=100.0,
            volume=1.0,
            stop_loss=99.0,
            take_profit=102.0,
        )

        sucesso = motor_agente_5000.abrir_posicao(
            ticket=123456,  # Mesmo ticket
            tipo=TipoPosicao.COMPRADA,
            preco_entrada=100.0,
            volume=1.0,
            stop_loss=99.0,
            take_profit=102.0,
        )
        assert sucesso == False

    def test_nao_abrir_segunda_posicao_simultanea(self, motor_agente_5000):
        """Testa que só permite 1 posição aberta por agente."""
        motor_agente_5000.abrir_posicao(
            ticket=111111,
            tipo=TipoPosicao.COMPRADA,
            preco_entrada=100.0,
            volume=1.0,
            stop_loss=99.0,
            take_profit=102.0,
        )

        sucesso = motor_agente_5000.abrir_posicao(
            ticket=222222,  # Ticket diferente
            tipo=TipoPosicao.COMPRADA,
            preco_entrada=100.0,
            volume=1.0,
            stop_loss=99.0,
            take_profit=102.0,
        )
        assert sucesso == False


class TestAtualizarPosicao:
    """Testes de atualização de P&L."""

    def test_atualizar_pnl_posicao_comprada_com_ganho(self, motor_agente_5000):
        """Testa cálculo de P&L para posição comprada com ganho."""
        motor_agente_5000.abrir_posicao(
            ticket=123456,
            tipo=TipoPosicao.COMPRADA,
            preco_entrada=100.0,
            volume=1.0,
            stop_loss=99.0,
            take_profit=102.0,
        )

        # Atualizar para preço com ganho
        sucesso = motor_agente_5000.atualizar_posicao(123456, 102.0)
        assert sucesso == True

        posicao = motor_agente_5000.obter_posicao(123456)
        assert posicao.preco_atual == 102.0
        assert posicao.pnl_reais == pytest.approx(0.40)  # (102.0 - 100.0) * 1.0 * R$0.20/pt
        assert posicao.pnl_pct == 2.0  # 2%

    def test_atualizar_pnl_posicao_vendida_com_ganho(self, motor_agente_5000):
        """Testa cálculo de P&L para posição vendida com ganho."""
        motor_agente_5000.abrir_posicao(
            ticket=654321,
            tipo=TipoPosicao.VENDIDA,
            preco_entrada=100.0,
            volume=1.0,
            stop_loss=101.0,
            take_profit=98.0,
        )

        # Atualizar para preço com ganho (desceu)
        sucesso = motor_agente_5000.atualizar_posicao(654321, 98.0)
        assert sucesso == True

        posicao = motor_agente_5000.obter_posicao(654321)
        assert posicao.pnl_reais == pytest.approx(0.40)  # (100.0 - 98.0) * 1.0 * R$0.20/pt
        assert posicao.pnl_pct == 2.0


class TestFecharPosicao:
    """Testes de fechamento de posição."""

    def test_fechar_posicao_rejeita_preco_saida_zero(self, motor_agente_5000):
        """TECH-001: nunca persistir fechamento com preco_saida <= 0."""
        motor_agente_5000.abrir_posicao(
            ticket=999001,
            tipo=TipoPosicao.COMPRADA,
            preco_entrada=100.0,
            volume=1.0,
            stop_loss=99.0,
            take_profit=102.0,
        )

        with pytest.raises(ValueError, match="preco_saida"):
            motor_agente_5000.fechar_posicao(
                999001,
                preco_saida=0.0,
                motivo=MotivoFechamento.MANUAL,
            )

        assert motor_agente_5000.tem_posicao_aberta() is True


    def test_fechar_posicao_com_ganho_tp(self, motor_agente_5000):
        """Testa fechamento de posição com ganho (TP atingido)."""
        motor_agente_5000.abrir_posicao(
            ticket=123456,
            tipo=TipoPosicao.COMPRADA,
            preco_entrada=100.0,
            volume=1.0,
            stop_loss=99.0,
            take_profit=102.0,
        )

        historico = motor_agente_5000.fechar_posicao(
            123456,
            preco_saida=102.0,
            motivo=MotivoFechamento.TP_ATINGIDO,
        )

        assert historico is not None
        assert historico.pnl_reais == pytest.approx(0.40)  # (102.0 - 100.0) * 1.0 * R$0.20/pt
        assert historico.motivo == MotivoFechamento.TP_ATINGIDO
        assert motor_agente_5000.tem_posicao_aberta() == False

    def test_fechar_posicao_com_perda_sl(self, motor_agente_5000):
        """Testa fechamento de posição com perda (SL atingido)."""
        motor_agente_5000.abrir_posicao(
            ticket=123456,
            tipo=TipoPosicao.COMPRADA,
            preco_entrada=100.0,
            volume=1.0,
            stop_loss=99.0,
            take_profit=102.0,
        )

        historico = motor_agente_5000.fechar_posicao(
            123456,
            preco_saida=99.0,
            motivo=MotivoFechamento.SL_ATINGIDO,
        )

        assert historico.pnl_reais == pytest.approx(-0.20)  # (99.0 - 100.0) * 1.0 * R$0.20/pt
        assert historico.motivo == MotivoFechamento.SL_ATINGIDO

    def test_nao_fechar_posicao_inexistente(self, motor_agente_5000):
        """Testa que não fecha posição que não existe."""
        historico = motor_agente_5000.fechar_posicao(
            999999,  # Ticket que não existe
            preco_saida=100.0,
            motivo=MotivoFechamento.MANUAL,
        )
        assert historico is None


class TestEstatisticas:
    """Testes de cálculo de estatísticas."""

    def test_estatisticas_vazio(self, motor_agente_5000):
        """Testa estatísticas quando sem histórico."""
        stats = motor_agente_5000.obter_estatisticas()
        assert stats['total_trades'] == 0
        assert stats['win_rate'] == 0.0
        assert stats['total_pnl'] == 0.0

    def test_estatisticas_com_ganhos(self, motor_agente_5000):
        """Testa calculo de estatisticas com operacoes lucrativas."""
        # Trade 1: +2 pontos * 1 contrato * R$0,20 = R$0,40
        motor_agente_5000.abrir_posicao(111, TipoPosicao.COMPRADA, 100.0, 1.0, 99.0, 102.0)
        motor_agente_5000.fechar_posicao(111, 102.0, MotivoFechamento.TP_ATINGIDO)

        # Trade 2: +3 pontos * 1 contrato * R$0,20 = R$0,60
        motor_agente_5000.abrir_posicao(222, TipoPosicao.COMPRADA, 100.0, 1.0, 99.0, 103.0)
        motor_agente_5000.fechar_posicao(222, 103.0, MotivoFechamento.TP_ATINGIDO)

        stats = motor_agente_5000.obter_estatisticas()
        assert stats['total_trades'] == 2
        assert stats['wins'] == 2
        assert stats['win_rate'] == 100.0
        assert stats['total_pnl'] == pytest.approx(1.00)  # R$0,40 + R$0,60

    def test_estatisticas_com_perdas(self, motor_agente_5000):
        """Testa calculo de estatisticas com operacoes com perda."""
        # Trade 1: -1 ponto * 1 contrato * R$0,20 = R$-0,20
        motor_agente_5000.abrir_posicao(111, TipoPosicao.COMPRADA, 100.0, 1.0, 99.0, 102.0)
        motor_agente_5000.fechar_posicao(111, 99.0, MotivoFechamento.SL_ATINGIDO)

        # Trade 2: +2 pontos * 1 contrato * R$0,20 = R$0,40
        motor_agente_5000.abrir_posicao(222, TipoPosicao.COMPRADA, 100.0, 1.0, 99.0, 102.0)
        motor_agente_5000.fechar_posicao(222, 102.0, MotivoFechamento.TP_ATINGIDO)

        stats = motor_agente_5000.obter_estatisticas()
        assert stats['total_trades'] == 2
        assert stats['wins'] == 1
        assert stats['losses'] == 1
        assert stats['win_rate'] == 50.0
        assert stats['total_pnl'] == pytest.approx(0.20)  # R$-0,20 + R$0,40


class TestPersistencia:
    """Testes de persistência em JSON."""

    def test_salvar_e_carregar_posicoes(self, temp_data_dir):
        """Testa salvar e recarregar posições do arquivo."""
        # Criar motor e abrir posição
        motor1 = MotorDecisaoIsolado('agente_teste', temp_data_dir)
        motor1.abrir_posicao(111, TipoPosicao.COMPRADA, 100.0, 1.0, 99.0, 102.0)
        assert len(motor1.posicoes_ativas) == 1

        # Criar novo motor com mesmo agent_id (deve carregar do arquivo)
        motor2 = MotorDecisaoIsolado('agente_teste', temp_data_dir)
        assert len(motor2.posicoes_ativas) == 1
        posicao = motor2.obter_posicao(111)
        assert posicao is not None
        assert posicao.tipo == TipoPosicao.COMPRADA

    def test_salvar_e_carregar_decisoes(self, temp_data_dir):
        """Testa salvar e recarregar decisões do arquivo."""
        motor1 = MotorDecisaoIsolado('agente_teste', temp_data_dir)
        motor1.registrar_decisao(DecisaoOperacional.ABRIR, ticket=111, reasoning='Teste')
        assert len(motor1.decisoes) == 1

        motor2 = MotorDecisaoIsolado('agente_teste', temp_data_dir)
        assert len(motor2.decisoes) == 1
        assert motor2.decisoes[0].decisao == DecisaoOperacional.ABRIR

    def test_persistir_contexto_operacional_na_decisao(self, temp_data_dir):
        """Decisões devem reter flags estruturadas do contexto de abertura."""
        contexto = {
            'regime_macro': 'CAUTELOSO',
            'vies_intraday': 'NEUTRO_LEVEMENTE_BAIXISTA',
            'watchlist': ['PETR4', 'VALE3', 'DOL'],
            'acao_normalizada': 'BUY',
        }
        motor1 = MotorDecisaoIsolado('agente_teste', temp_data_dir)
        motor1.registrar_decisao(
            DecisaoOperacional.CANCELAR,
            ticket=111,
            reasoning='Bloqueada por contexto',
            contexto_operacional=contexto,
        )

        motor2 = MotorDecisaoIsolado('agente_teste', temp_data_dir)
        assert motor2.decisoes[0].contexto_operacional['vies_intraday'] == (
            'NEUTRO_LEVEMENTE_BAIXISTA'
        )
        assert motor2.decisoes[0].contexto_operacional['acao_normalizada'] == 'BUY'

    def test_salvar_e_carregar_historico(self, temp_data_dir):
        """Testa salvar e recarregar histórico do arquivo."""
        motor1 = MotorDecisaoIsolado('agente_teste', temp_data_dir)
        motor1.abrir_posicao(111, TipoPosicao.COMPRADA, 100.0, 1.0, 99.0, 102.0)
        motor1.fechar_posicao(111, 102.0, MotivoFechamento.TP_ATINGIDO)
        assert len(motor1.historico) == 1

        motor2 = MotorDecisaoIsolado('agente_teste', temp_data_dir)
        assert len(motor2.historico) == 1
        assert motor2.historico[0].pnl_reais == pytest.approx(0.40)  # (102.0-100.0)*1.0*R$0.20/pt


class TestIntegracaoCompleta:
    """Testes de integração completa com múltiplos agentes."""

    def test_fluxo_completo_agente_5000(self, motor_agente_5000):
        """Testa fluxo completo: abrir → atualizar → fechar."""
        # Etapa 1: Abrir posição
        motor_agente_5000.abrir_posicao(
            ticket=123456,
            tipo=TipoPosicao.COMPRADA,
            preco_entrada=100.0,
            volume=1.0,
            stop_loss=99.0,
            take_profit=102.0,
        )
        assert motor_agente_5000.tem_posicao_aberta() == True

        # Etapa 2: Atualizar P&L conforme preço sobe
        motor_agente_5000.atualizar_posicao(123456, 101.0)
        posicao = motor_agente_5000.obter_posicao(123456)
        assert posicao.pnl_reais == pytest.approx(0.20)  # (101.0-100.0)*1.0*R$0.20/pt

        # Etapa 3: Fechar na meta
        historico = motor_agente_5000.fechar_posicao(123456, 102.0, MotivoFechamento.TP_ATINGIDO)
        assert motor_agente_5000.tem_posicao_aberta() == False
        assert historico.pnl_reais == pytest.approx(0.40)  # (102.0-100.0)*1.0*R$0.20/pt

    def test_multiplos_agentes_nao_interferem(self, motor_agente_5000, motor_agente_direto):
        """Testa múltiplos agentes operando simultaneamente."""
        # Agente 5000 abre posição
        motor_agente_5000.abrir_posicao(
            ticket=111111,
            tipo=TipoPosicao.COMPRADA,
            preco_entrada=100.0,
            volume=1.0,
            stop_loss=99.0,
            take_profit=102.0,
        )

        # Agente direto abre posição diferente
        motor_agente_direto.abrir_posicao(
            ticket=222222,
            tipo=TipoPosicao.VENDIDA,
            preco_entrada=100.0,
            volume=1.0,
            stop_loss=101.0,
            take_profit=98.0,
        )

        # Verificar isolamento
        assert motor_agente_5000.tem_posicao_aberta() == True
        assert motor_agente_direto.tem_posicao_aberta() == True
        assert motor_agente_5000.obter_posicao(111111) is not None
        assert motor_agente_5000.obter_posicao(222222) is None  # Não vê posição do outro
        assert motor_agente_direto.obter_posicao(222222) is not None
        assert motor_agente_direto.obter_posicao(111111) is None  # Não vê posição do outro
