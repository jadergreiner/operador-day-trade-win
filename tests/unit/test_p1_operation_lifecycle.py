"""
Testes para Ciclo de Vida Operacional: 4 Etapas

Testa:
- Etapa 1: Tendência diária
- Etapa 2: Detecção de oportunidades
- Etapa 3: Monitoramento contínuo
- Etapa 4: Rastreamento de operações

Type hints: 100%
Português: 100%
Cobertura: ≥80%
"""

import pytest
import sqlite3
import tempfile
from datetime import datetime
from pathlib import Path
from src.application.p1_operation_lifecycle import (
    Tendencia,
    TendenciaDir,
    Oportunidade,
    OportunidadeStatus,
    MonitoramentoOportunidade,
    DecisaoOperacional,
    DecisaoAbertura,
    RastreamentoOperacao,
    MotorAnaliseMercado,
    MotorDecisao,
    GeradorRelatorioCicloVida,
)


@pytest.fixture
def temp_db() -> str:
    """Cria banco de dados temporário para testes."""
    with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.db') as f:
        db_path = f.name
    return db_path


@pytest.fixture
def motor_analise(temp_db: str) -> MotorAnaliseMercado:
    """Cria motor de análise com DB temporário."""
    return MotorAnaliseMercado(db_path=temp_db)


@pytest.fixture
def motor_decisao(temp_db: str) -> MotorDecisao:
    """Cria motor de decisão com DB temporário."""
    return MotorDecisao(db_path=temp_db)


class TestEtapa1Tendencia:
    """Testes para Etapa 1: Análise de Tendência Principal."""
    
    def test_criar_tendencia_altista(self) -> None:
        """Testa criação de tendência altista."""
        tendencia = Tendencia(
            timestamp=datetime.now(),
            direcao=TendenciaDir.ALTISTA,
            forca=75.5,
            contexto="BDI positivo + macro favorável",
            nivel_suporte=142000.0,
            nivel_resistencia=144000.0,
            volatilidade_esperada=1.5
        )
        
        assert tendencia.direcao == TendenciaDir.ALTISTA
        assert tendencia.forca == 75.5
        assert "BDI" in tendencia.contexto
    
    def test_criar_tendencia_baixista(self) -> None:
        """Testa criação de tendência baixista."""
        tendencia = Tendencia(
            timestamp=datetime.now(),
            direcao=TendenciaDir.BAIXISTA,
            forca=60.0,
            contexto="Notícia negativa + volume vendedor",
            nivel_suporte=140000.0,
            nivel_resistencia=142000.0,
            volatilidade_esperada=2.0
        )
        
        assert tendencia.direcao == TendenciaDir.BAIXISTA
        assert tendencia.volatilidade_esperada == 2.0
    
    def test_tendencia_para_dict(self) -> None:
        """Testa conversão de tendência para dicionário."""
        agora = datetime.now()
        tendencia = Tendencia(
            timestamp=agora,
            direcao=TendenciaDir.LATERAL,
            forca=40.0,
            contexto="Consolidação",
            nivel_suporte=141000.0,
            nivel_resistencia=143000.0,
            volatilidade_esperada=0.8
        )
        
        resultado = tendencia.para_dict()
        
        assert resultado['direcao'] == 'LATERAL'
        assert resultado['forca'] == 40.0
        assert 'timestamp' in resultado
    
    def test_registrar_tendencia(self, motor_analise: MotorAnaliseMercado) -> None:
        """Testa registro de tendência no banco."""
        tendencia = Tendencia(
            timestamp=datetime.now(),
            direcao=TendenciaDir.ALTISTA,
            forca=70.0,
            contexto="Teste",
            nivel_suporte=141500.0,
            nivel_resistencia=143500.0,
            volatilidade_esperada=1.2
        )
        
        id_tendencia = motor_analise.registrar_tendencia(tendencia)
        
        assert id_tendencia is not None
        assert isinstance(id_tendencia, str)
    
    def test_obter_tendencia_hoje(self, motor_analise: MotorAnaliseMercado) -> None:
        """Testa recuperação de tendência registrada."""
        tendencia_original = Tendencia(
            timestamp=datetime.now(),
            direcao=TendenciaDir.ALTISTA,
            forca=75.0,
            contexto="Teste recuperação",
            nivel_suporte=141000.0,
            nivel_resistencia=143000.0,
            volatilidade_esperada=1.5
        )
        
        motor_analise.registrar_tendencia(tendencia_original)
        tendencia_recuperada = motor_analise.obter_tendencia_hoje()
        
        assert tendencia_recuperada is not None
        assert tendencia_recuperada.direcao == TendenciaDir.ALTISTA
        assert tendencia_recuperada.forca == 75.0


class TestEtapa2Oportunidades:
    """Testes para Etapa 2: Detecção de Oportunidades."""
    
    def test_criar_oportunidade_valida(self) -> None:
        """Testa criação de oportunidade válida."""
        oportunidade = Oportunidade(
            id_oportunidade="opp_001",
            timestamp_deteccao=datetime.now(),
            tendencia_id="trend_001",
            preco_referencia=142500.0,
            direcao_sugerida="BUY",
            forcas_tecnicas=["pullback", "suporte_testado"],
            confianca_tecnica=82.0,
            alinhamento_tendencia=True,
            razao_desalinhamento=None,
            tamanho_potencial=1500.0,
            razao_risco_retorno=2.5
        )
        
        assert oportunidade.id_oportunidade == "opp_001"
        assert oportunidade.direcao_sugerida == "BUY"
        assert oportunidade.status == OportunidadeStatus.DETECTADA
    
    def test_oportunidade_desalinhada_com_tendencia(self) -> None:
        """Testa oportunidade desalinhada com tendência do dia."""
        oportunidade = Oportunidade(
            id_oportunidade="opp_002",
            timestamp_deteccao=datetime.now(),
            tendencia_id="trend_001",
            preco_referencia=141500.0,
            direcao_sugerida="SELL",
            forcas_tecnicas=["pullback"],
            confianca_tecnica=65.0,
            alinhamento_tendencia=False,
            razao_desalinhamento="Tendência altista, sinal contrário",
            tamanho_potencial=1000.0,
            razao_risco_retorno=1.8
        )
        
        assert not oportunidade.alinhamento_tendencia
        assert oportunidade.razao_desalinhamento is not None
    
    def test_oportunidade_para_dict(self) -> None:
        """Testa conversão de oportunidade para dicionário."""
        agora = datetime.now()
        oportunidade = Oportunidade(
            id_oportunidade="opp_003",
            timestamp_deteccao=agora,
            tendencia_id="trend_001",
            preco_referencia=142000.0,
            direcao_sugerida="BUY",
            forcas_tecnicas=["teste"],
            confianca_tecnica=70.0,
            alinhamento_tendencia=True,
            razao_desalinhamento=None,
            tamanho_potencial=1000.0,
            razao_risco_retorno=2.0
        )
        
        resultado = oportunidade.para_dict()
        
        assert resultado['id_oportunidade'] == "opp_003"
        assert resultado['status'] == 'DETECTADA'
        assert 'timestamp_deteccao' in resultado
    
    def test_registrar_oportunidade(
        self,
        motor_analise: MotorAnaliseMercado
    ) -> None:
        """Testa registro de oportunidade."""
        oportunidade = Oportunidade(
            id_oportunidade="opp_004",
            timestamp_deteccao=datetime.now(),
            tendencia_id="trend_001",
            preco_referencia=142500.0,
            direcao_sugerida="BUY",
            forcas_tecnicas=["pullback"],
            confianca_tecnica=80.0,
            alinhamento_tendencia=True,
            razao_desalinhamento=None,
            tamanho_potencial=1400.0,
            razao_risco_retorno=2.8
        )
        
        motor_analise.registrar_oportunidade(oportunidade)
        
        # Verifica que foi inserida (sem exceção)
        assert True


class TestEtapa3Monitoramento:
    """Testes para Etapa 3: Monitoramento de Oportunidades."""
    
    def test_criar_monitoramento(self) -> None:
        """Testa criação de monitoramento."""
        monitor = MonitoramentoOportunidade(
            id_oportunidade="opp_005",
            timestamp_update=datetime.now(),
            preco_atual=142600.0,
            preco_inicial=142500.0,
            movimento_pct=0.07,
            condicoes_mercado_atuais={"volatilidade": "alta", "volume": "normalizado"},
            ainda_valida=True,
            razao_invalidade=None
        )
        
        assert monitor.id_oportunidade == "opp_005"
        assert monitor.ainda_valida is True
        assert monitor.movimento_pct == 0.07
    
    def test_monitoramento_oportunidade_expirada(self) -> None:
        """Testa monitoramento de oportunidade expirada."""
        monitor = MonitoramentoOportunidade(
            id_oportunidade="opp_006",
            timestamp_update=datetime.now(),
            preco_atual=141900.0,
            preco_inicial=142500.0,
            movimento_pct=-0.42,
            condicoes_mercado_atuais={"tendencia": "revertida"},
            ainda_valida=False,
            razao_invalidade="Preço saiu da zona de interesse"
        )
        
        assert not monitor.ainda_valida
        assert monitor.razao_invalidade is not None
    
    def test_registrar_monitoramento(
        self,
        motor_analise: MotorAnaliseMercado
    ) -> None:
        """Testa registro de monitoramento."""
        monitor = MonitoramentoOportunidade(
            id_oportunidade="opp_007",
            timestamp_update=datetime.now(),
            preco_atual=142550.0,
            preco_inicial=142500.0,
            movimento_pct=0.04,
            condicoes_mercado_atuais={"status": "normal"},
            ainda_valida=True,
            razao_invalidade=None
        )
        
        motor_analise.registrar_monitoramento(monitor)
        
        assert True


class TestEtapa4DecisaoEOperacao:
    """Testes para Etapa 4: Decisão e Rastreamento de Operação."""
    
    def test_criar_decisao_abrir(self) -> None:
        """Testa criação de decisão para abrir posição."""
        decisao = DecisaoOperacional(
            id_oportunidade="opp_008",
            timestamp_decisao=datetime.now(),
            decisao=DecisaoAbertura.ABRIR,
            reasoning="Confirmação em suporte + alinhamento tendência altista",
            fatores=["suporte_testado", "volume_crescente", "RSI<30"],
            heuristica_aplicada="regra_pullback_suporte",
            motivo_negacao=None
        )
        
        assert decisao.decisao == DecisaoAbertura.ABRIR
        assert len(decisao.fatores) == 3
    
    def test_criar_decisao_negar(self) -> None:
        """Testa criação de decisão para negar posição."""
        decisao = DecisaoOperacional(
            id_oportunidade="opp_009",
            timestamp_decisao=datetime.now(),
            decisao=DecisaoAbertura.NEGAR,
            reasoning="Posição anterior em drawdown, aguardando recuperação",
            fatores=["drawdown_ativo", "capital_insuficiente"],
            heuristica_aplicada="regra_risk_management",
            motivo_negacao="Capital preservado para recuperação de DD"
        )
        
        assert decisao.decisao == DecisaoAbertura.NEGAR
        assert decisao.motivo_negacao is not None
    
    def test_registrar_decisao(
        self,
        motor_decisao: MotorDecisao
    ) -> None:
        """Testa registro de decisão."""
        decisao = DecisaoOperacional(
            id_oportunidade="opp_010",
            timestamp_decisao=datetime.now(),
            decisao=DecisaoAbertura.ABRIR,
            reasoning="Sinal válido",
            fatores=["teste"],
            heuristica_aplicada="teste",
            motivo_negacao=None
        )
        
        motor_decisao.registrar_decisao(decisao)
        
        assert True
    
    def test_criar_rastreamento_operacao(self) -> None:
        """Testa criação de rastreamento de operação."""
        operacao = RastreamentoOperacao(
            id_operacao="op_001",
            id_oportunidade="opp_011",
            timestamp_abertura=datetime.now(),
            entrada_preco=142500.0,
            stop_loss=141500.0,
            take_profit=144500.0,
            status_execucao="ABERTA",
            pnl_reais=0.0,
            pnl_pct=0.0
        )
        
        assert operacao.id_operacao == "op_001"
        assert operacao.status_execucao == "ABERTA"
    
    def test_fechar_rastreamento_com_ganho(self) -> None:
        """Testa fechamento de operação com ganho."""
        agora = datetime.now()
        operacao = RastreamentoOperacao(
            id_operacao="op_002",
            id_oportunidade="opp_012",
            timestamp_abertura=agora,
            entrada_preco=142500.0,
            stop_loss=141500.0,
            take_profit=144500.0,
            status_execucao="FECHADA",
            timestamp_fechamento=agora,
            saida_preco=144500.0,
            pnl_reais=2000.0,
            pnl_pct=1.40,
            tempo_posicao_min=45,
            motivo_fechamento="TP atingido"
        )
        
        assert operacao.pnl_reais == 2000.0
        assert operacao.pnl_pct == 1.40
        assert operacao.motivo_fechamento == "TP atingido"
    
    def test_fechar_rastreamento_com_perda(self) -> None:
        """Testa fechamento de operação com perda."""
        agora = datetime.now()
        operacao = RastreamentoOperacao(
            id_operacao="op_003",
            id_oportunidade="opp_013",
            timestamp_abertura=agora,
            entrada_preco=142500.0,
            stop_loss=141500.0,
            take_profit=144500.0,
            status_execucao="FECHADA",
            timestamp_fechamento=agora,
            saida_preco=141500.0,
            pnl_reais=-1000.0,
            pnl_pct=-0.70,
            tempo_posicao_min=30,
            motivo_fechamento="SL acionado"
        )
        
        assert operacao.pnl_reais == -1000.0
        assert operacao.motivo_fechamento == "SL acionado"
    
    def test_registrar_operacao(
        self,
        motor_decisao: MotorDecisao
    ) -> None:
        """Testa registro de operação."""
        agora = datetime.now()
        operacao = RastreamentoOperacao(
            id_operacao="op_004",
            id_oportunidade="opp_014",
            timestamp_abertura=agora,
            entrada_preco=142500.0,
            stop_loss=141500.0,
            take_profit=144500.0,
            status_execucao="ABERTA"
        )
        
        motor_decisao.registrar_operacao(operacao)
        
        assert True
    
    def test_obter_operacao(
        self,
        motor_decisao: MotorDecisao
    ) -> None:
        """Testa recuperação de operação registrada."""
        agora = datetime.now()
        operacao_original = RastreamentoOperacao(
            id_operacao="op_005",
            id_oportunidade="opp_015",
            timestamp_abertura=agora,
            entrada_preco=142500.0,
            stop_loss=141500.0,
            take_profit=144500.0,
            status_execucao="ABERTA"
        )
        
        motor_decisao.registrar_operacao(operacao_original)
        operacao_recuperada = motor_decisao.obter_operacao("op_005")
        
        assert operacao_recuperada is not None
        assert operacao_recuperada.id_operacao == "op_005"
        assert operacao_recuperada.entrada_preco == 142500.0
    
    def test_listar_operacoes_abertas(
        self,
        motor_decisao: MotorDecisao
    ) -> None:
        """Testa listagem de operações abertas."""
        agora = datetime.now()
        
        # Registra operação aberta
        op1 = RastreamentoOperacao(
            id_operacao="op_006",
            id_oportunidade="opp_016",
            timestamp_abertura=agora,
            entrada_preco=142500.0,
            stop_loss=141500.0,
            take_profit=144500.0,
            status_execucao="ABERTA"
        )
        motor_decisao.registrar_operacao(op1)
        
        # Registra operação fechada
        op2 = RastreamentoOperacao(
            id_operacao="op_007",
            id_oportunidade="opp_017",
            timestamp_abertura=agora,
            entrada_preco=142000.0,
            stop_loss=141000.0,
            take_profit=144000.0,
            status_execucao="FECHADA",
            pnl_reais=1000.0
        )
        motor_decisao.registrar_operacao(op2)
        
        abertas = motor_decisao.listar_operacoes_abertas()
        
        assert len(abertas) >= 1
        assert any(op.id_operacao == "op_006" for op in abertas)


class TestGeradorRelatorio:
    """Testes para Gerador de Relatórios."""
    
    def test_gerar_relatorio_dia_vazio(
        self,
        temp_db: str
    ) -> None:
        """Testa geração de relatório para dia sem dados."""
        gerador = GeradorRelatorioCicloVida(db_path=temp_db)
        relatorio = gerador.gerar_relatorio_dia(data="today")
        
        assert relatorio is not None
        assert 'etapa_1_tendencia' in relatorio
        assert 'etapa_2_3_oportunidades' in relatorio
        assert 'etapa_4_operacoes' in relatorio
    
    def test_relatorio_estrutura_completa(
        self,
        motor_analise: MotorAnaliseMercado,
        motor_decisao: MotorDecisao,
        temp_db: str
    ) -> None:
        """Testa estrutura completa de relatório com dados."""
        # Registra dados em todas etapas
        agora = datetime.now()
        
        tendencia = Tendencia(
            timestamp=agora,
            direcao=TendenciaDir.ALTISTA,
            forca=75.0,
            contexto="Teste",
            nivel_suporte=141000.0,
            nivel_resistencia=143000.0,
            volatilidade_esperada=1.2
        )
        tendencia_id = motor_analise.registrar_tendencia(tendencia)
        
        oportunidade = Oportunidade(
            id_oportunidade="opp_018",
            timestamp_deteccao=agora,
            tendencia_id=tendencia_id,
            preco_referencia=142500.0,
            direcao_sugerida="BUY",
            forcas_tecnicas=["teste"],
            confianca_tecnica=80.0,
            alinhamento_tendencia=True,
            razao_desalinhamento=None,
            tamanho_potencial=1400.0,
            razao_risco_retorno=2.8
        )
        motor_analise.registrar_oportunidade(oportunidade)
        
        operacao = RastreamentoOperacao(
            id_operacao="op_008",
            id_oportunidade="opp_018",
            timestamp_abertura=agora,
            entrada_preco=142500.0,
            stop_loss=141500.0,
            take_profit=144500.0,
            status_execucao="FECHADA",
            timestamp_fechamento=agora,
            saida_preco=144500.0,
            pnl_reais=2000.0,
            pnl_pct=1.40
        )
        motor_decisao.registrar_operacao(operacao)
        
        # Gera relatório
        gerador = GeradorRelatorioCicloVida(db_path=temp_db)
        relatorio = gerador.gerar_relatorio_dia(data="today")
        
        assert relatorio['etapa_1_tendencia'] is not None
        assert relatorio['etapa_1_tendencia']['direcao'] == "ALTISTA"
        assert relatorio['etapa_2_3_oportunidades']['total_detectadas'] >= 1
        assert relatorio['etapa_4_operacoes']['total_fechadas'] >= 1
        assert relatorio['etapa_4_operacoes']['pnl_total'] == 2000.0


class TestIntegracao:
    """Testes de integração completa (Etapas 1-4)."""
    
    def test_fluxo_completo_ciclo_vida(
        self,
        motor_analise: MotorAnaliseMercado,
        motor_decisao: MotorDecisao
    ) -> None:
        """Testa fluxo completo de um ciclo de vida operacional."""
        agora = datetime.now()
        
        # Etapa 1: Registra tendência
        tendencia = Tendencia(
            timestamp=agora,
            direcao=TendenciaDir.ALTISTA,
            forca=80.0,
            contexto="Momentum positivo detectado",
            nivel_suporte=141500.0,
            nivel_resistencia=144000.0,
            volatilidade_esperada=1.3
        )
        tendencia_id = motor_analise.registrar_tendencia(tendencia)
        assert tendencia_id is not None
        
        # Etapa 2: Detecta oportunidade
        oportunidade = Oportunidade(
            id_oportunidade="opp_final",
            timestamp_deteccao=agora,
            tendencia_id=tendencia_id,
            preco_referencia=142500.0,
            direcao_sugerida="BUY",
            forcas_tecnicas=["pullback", "suporte", "volume"],
            confianca_tecnica=85.0,
            alinhamento_tendencia=True,
            razao_desalinhamento=None,
            tamanho_potencial=1600.0,
            razao_risco_retorno=3.0
        )
        motor_analise.registrar_oportunidade(oportunidade)
        
        # Etapa 3: Monitora oportunidade
        monitor = MonitoramentoOportunidade(
            id_oportunidade="opp_final",
            timestamp_update=agora,
            preco_atual=142550.0,
            preco_inicial=142500.0,
            movimento_pct=0.04,
            condicoes_mercado_atuais={"volume": "crescente"},
            ainda_valida=True,
            razao_invalidade=None
        )
        motor_analise.registrar_monitoramento(monitor)
        
        # Etapa 4: Registra decisão
        decisao = DecisaoOperacional(
            id_oportunidade="opp_final",
            timestamp_decisao=agora,
            decisao=DecisaoAbertura.ABRIR,
            reasoning="Confirmação em todos fatores técnicos",
            fatores=["pullback", "suporte", "volume", "tendência"],
            heuristica_aplicada="regra_pullback_tendencia",
            motivo_negacao=None
        )
        motor_decisao.registrar_decisao(decisao)
        
        # Etapa 4: Registra operação
        operacao = RastreamentoOperacao(
            id_operacao="op_final",
            id_oportunidade="opp_final",
            timestamp_abertura=agora,
            entrada_preco=142500.0,
            stop_loss=141500.0,
            take_profit=144500.0,
            status_execucao="ABERTA"
        )
        motor_decisao.registrar_operacao(operacao)
        
        # Recupera e valida
        operacao_recuperada = motor_decisao.obter_operacao("op_final")
        assert operacao_recuperada is not None
        assert operacao_recuperada.entrada_preco == 142500.0
        assert operacao_recuperada.status_execucao == "ABERTA"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
