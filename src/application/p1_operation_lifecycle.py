"""
Ciclo de Vida Operacional: Motor de Análise de Mercado + Motor de Decisão

Este módulo implementa as 4 etapas de operação com rastreamento completo:

Etapa 1: Análise de Tendência Principal do Dia
Etapa 2: Detecção de Oportunidades (regiões de interesse)
Etapa 3: Monitoramento de Oportunidades (com ou sem decisão)
Etapa 4: Rastreamento de Operações (execução + fechamento)

A separação clara entre Motor de Análise e Motor de Decisão permite:
- Análise independente da decisão de abrir posição
- Rastreamento de oportunidades perdidas ou canceladas
- Feedback para ML/RL separado de decisões operacionais
- Auditoria completa de análises vs resultados

Type hints: 100%
Português: 100%
"""

from dataclasses import dataclass, field, asdict
from datetime import datetime
from enum import Enum
from typing import Optional, List, Dict, Any
import json
import sqlite3
from pathlib import Path


class TendenciaDir(Enum):
    """Direção da tendência principal do dia."""
    ALTISTA = "ALTISTA"
    BAIXISTA = "BAIXISTA"
    LATERAL = "LATERAL"
    INDEFINIDA = "INDEFINIDA"


class OportunidadeStatus(Enum):
    """Status de uma oportunidade detectada."""
    DETECTADA = "DETECTADA"  # Sinal detectado, aguardando decisão
    DECIDIDA = "DECIDIDA"    # Decisão tomada (abrir ou não)
    EXECUTADA = "EXECUTADA"  # Posição aberta
    CANCELADA = "CANCELADA"  # Oportunidade expirou sem decisão
    PERDIDA = "PERDIDA"      # Decidiu não abrir, teria sido lucrativo
    FECHADA = "FECHADA"      # Operação finalizada


class DecisaoAbertura(Enum):
    """Decisão sobre abertura de posição."""
    PENDENTE = "PENDENTE"      # Aguardando decisão
    ABRIR = "ABRIR"            # Decisão: abrir posição
    NEGAR = "NEGAR"            # Decisão: não abrir
    CONTINGENCIA = "CONTINGENCIA"  # Decisão: abrir com limitações (risco)


@dataclass
class Tendencia:
    """Análise de Tendência Principal do Dia (Etapa 1)."""
    
    timestamp: datetime
    direcao: TendenciaDir
    forca: float  # 0-100, força do movimento (correlação, impulso)
    contexto: str  # Descrição do contexto (BDI, macro, eventos)
    nivel_suporte: float  # Nível de suporte identificado
    nivel_resistencia: float  # Nível de resistência identificado
    volatilidade_esperada: float  # ATR ou similar
    
    def para_dict(self) -> Dict[str, Any]:
        """Converte para dicionário."""
        resultado = asdict(self)
        resultado['direcao'] = self.direcao.value
        resultado['timestamp'] = self.timestamp.isoformat()
        return resultado


@dataclass
class Oportunidade:
    """Detecção de Oportunidade (Etapa 2)."""
    
    id_oportunidade: str  # UUID ou seq único
    timestamp_deteccao: datetime
    tendencia_id: str  # Link para Etapa 1
    preco_referencia: float
    direcao_sugerida: str  # BUY ou SELL
    
    # Fatores técnicos
    forcas_tecnicas: List[str]  # ["pullback", "divergencia", "rompimento"]
    confianca_tecnica: float  # 0-100
    
    # Contexto de mercado
    alinhamento_tendencia: bool  # Alinhada com tendência do dia?
    razao_desalinhamento: Optional[str]
    
    # Características da oportunidade
    tamanho_potencial: float  # R$ estimado
    razao_risco_retorno: float  # retorno_esperado / risco_esperado
    
    status: OportunidadeStatus = OportunidadeStatus.DETECTADA
    
    def para_dict(self) -> Dict[str, Any]:
        """Converte para dicionário."""
        resultado = asdict(self)
        resultado['timestamp_deteccao'] = self.timestamp_deteccao.isoformat()
        resultado['status'] = self.status.value
        return resultado


@dataclass
class MonitoramentoOportunidade:
    """Monitoramento contínuo de Oportunidade (Etapa 3)."""
    
    id_oportunidade: str
    timestamp_update: datetime
    preco_atual: float
    preco_inicial: float
    movimento_pct: float  # % movimento desde detecção
    
    condicoes_mercado_atuais: Dict[str, Any]  # Snapshot mercado
    ainda_valida: bool  # Oportunidade ainda é viável?
    razao_invalidade: Optional[str]
    
    def para_dict(self) -> Dict[str, Any]:
        """Converte para dicionário."""
        resultado = asdict(self)
        resultado['timestamp_update'] = self.timestamp_update.isoformat()
        return resultado


@dataclass
class DecisaoOperacional:
    """Decisão sobre abertura de posição (Etapa 2-4)."""
    
    id_oportunidade: str
    timestamp_decisao: datetime
    decisao: DecisaoAbertura
    
    # Raciocínio
    reasoning: str  # Explicação da decisão
    fatores: List[str]  # Fatores que influenciaram
    heuristica_aplicada: str  # Qual regra/modelo foi usado
    
    # Se negada
    motivo_negacao: Optional[str]
    
    def para_dict(self) -> Dict[str, Any]:
        """Converte para dicionário."""
        resultado = asdict(self)
        resultado['timestamp_decisao'] = self.timestamp_decisao.isoformat()
        resultado['decisao'] = self.decisao.value
        return resultado


@dataclass
class RastreamentoOperacao:
    """Rastreamento de Operação/Posição (Etapa 4)."""
    
    id_operacao: str  # ticket MT5 ou ticket gerado
    id_oportunidade: str
    timestamp_abertura: datetime
    entrada_preco: float
    stop_loss: float
    take_profit: float
    
    # Execução
    status_execucao: str  # ABERTA, PARCIAL, FECHADA, ERRO
    timestamp_fechamento: Optional[datetime] = None
    saida_preco: Optional[float] = None
    
    # Resultado
    pnl_reais: float = 0.0
    pnl_pct: float = 0.0
    tempo_posicao_min: int = 0
    
    motivo_fechamento: Optional[str] = None
    
    def para_dict(self) -> Dict[str, Any]:
        """Converte para dicionário."""
        resultado = asdict(self)
        resultado['timestamp_abertura'] = self.timestamp_abertura.isoformat()
        if self.timestamp_fechamento:
            resultado['timestamp_fechamento'] = self.timestamp_fechamento.isoformat()
        return resultado


class MotorAnaliseMercado:
    """Motor de Análise de Mercado (Etapas 1-3)."""
    
    def __init__(self, db_path: str = "data/db/trading.db"):
        """Inicializa motor de análise."""
        self.db_path = db_path
        self._criar_tabelas()
    
    def _criar_tabelas(self) -> None:
        """Cria tabelas SQLite para análise."""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS tendencia_diaria (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    data TEXT UNIQUE,
                    timestamp TEXT,
                    direcao TEXT,
                    forca REAL,
                    contexto TEXT,
                    nivel_suporte REAL,
                    nivel_resistencia REAL,
                    volatilidade_esperada REAL
                )
            """)
            
            conn.execute("""
                CREATE TABLE IF NOT EXISTS oportunidades (
                    id TEXT PRIMARY KEY,
                    timestamp_deteccao TEXT,
                    tendencia_id TEXT,
                    preco_referencia REAL,
                    direcao_sugerida TEXT,
                    forcas_tecnicas TEXT,
                    confianca_tecnica REAL,
                    alinhamento_tendencia INTEGER,
                    tamanho_potencial REAL,
                    razao_risco_retorno REAL,
                    status TEXT,
                    FOREIGN KEY(tendencia_id) REFERENCES tendencia_diaria(id)
                )
            """)
            
            conn.execute("""
                CREATE TABLE IF NOT EXISTS monitoramento_oportunidades (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    id_oportunidade TEXT,
                    timestamp_update TEXT,
                    preco_atual REAL,
                    preco_inicial REAL,
                    movimento_pct REAL,
                    ainda_valida INTEGER,
                    razao_invalidade TEXT,
                    FOREIGN KEY(id_oportunidade) REFERENCES oportunidades(id)
                )
            """)
            
            conn.commit()
    
    def registrar_tendencia(self, tendencia: Tendencia) -> str:
        """Registra análise de tendência (Etapa 1)."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT OR REPLACE INTO tendencia_diaria
                (data, timestamp, direcao, forca, contexto, 
                 nivel_suporte, nivel_resistencia, volatilidade_esperada)
                VALUES (date('now'), ?, ?, ?, ?, ?, ?, ?)
            """, (
                tendencia.timestamp.isoformat(),
                tendencia.direcao.value,
                tendencia.forca,
                tendencia.contexto,
                tendencia.nivel_suporte,
                tendencia.nivel_resistencia,
                tendencia.volatilidade_esperada
            ))
            conn.commit()
            
            # Retorna ID da tendência registrada
            cursor.execute("SELECT id FROM tendencia_diaria WHERE data = date('now')")
            return str(cursor.fetchone()[0])
    
    def registrar_oportunidade(self, oportunidade: Oportunidade) -> None:
        """Registra detecção de oportunidade (Etapa 2)."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO oportunidades
                (id, timestamp_deteccao, tendencia_id, preco_referencia,
                 direcao_sugerida, forcas_tecnicas, confianca_tecnica,
                 alinhamento_tendencia, tamanho_potencial, razao_risco_retorno, status)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                oportunidade.id_oportunidade,
                oportunidade.timestamp_deteccao.isoformat(),
                oportunidade.tendencia_id,
                oportunidade.preco_referencia,
                oportunidade.direcao_sugerida,
                json.dumps(oportunidade.forcas_tecnicas),
                oportunidade.confianca_tecnica,
                int(oportunidade.alinhamento_tendencia),
                oportunidade.tamanho_potencial,
                oportunidade.razao_risco_retorno,
                oportunidade.status.value
            ))
            conn.commit()
    
    def registrar_monitoramento(self, monitor: MonitoramentoOportunidade) -> None:
        """Registra monitoramento contínuo (Etapa 3)."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO monitoramento_oportunidades
                (id_oportunidade, timestamp_update, preco_atual, preco_inicial,
                 movimento_pct, ainda_valida, razao_invalidade)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (
                monitor.id_oportunidade,
                monitor.timestamp_update.isoformat(),
                monitor.preco_atual,
                monitor.preco_inicial,
                monitor.movimento_pct,
                int(monitor.ainda_valida),
                monitor.razao_invalidade
            ))
            conn.commit()
    
    def obter_tendencia_hoje(self) -> Optional[Tendencia]:
        """Obtém tendência registrada para hoje."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT timestamp, direcao, forca, contexto, 
                       nivel_suporte, nivel_resistencia, volatilidade_esperada
                FROM tendencia_diaria
                WHERE data = date('now')
            """)
            row = cursor.fetchone()
            
            if not row:
                return None
            
            return Tendencia(
                timestamp=datetime.fromisoformat(row[0]),
                direcao=TendenciaDir(row[1]),
                forca=row[2],
                contexto=row[3],
                nivel_suporte=row[4],
                nivel_resistencia=row[5],
                volatilidade_esperada=row[6]
            )


class MotorDecisao:
    """Motor de Decisão de Abertura de Posição."""
    
    def __init__(self, db_path: str = "data/db/trading.db"):
        """Inicializa motor de decisão."""
        self.db_path = db_path
        self._criar_tabelas()
    
    def _criar_tabelas(self) -> None:
        """Cria tabelas SQLite para decisões e operações."""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS decisoes_operacionais (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    id_oportunidade TEXT UNIQUE,
                    timestamp_decisao TEXT,
                    decisao TEXT,
                    reasoning TEXT,
                    fatores TEXT,
                    heuristica_aplicada TEXT,
                    motivo_negacao TEXT
                )
            """)
            
            conn.execute("""
                CREATE TABLE IF NOT EXISTS rastreamento_operacoes (
                    id_operacao TEXT PRIMARY KEY,
                    id_oportunidade TEXT,
                    timestamp_abertura TEXT,
                    entrada_preco REAL,
                    stop_loss REAL,
                    take_profit REAL,
                    status_execucao TEXT,
                    timestamp_fechamento TEXT,
                    saida_preco REAL,
                    pnl_reais REAL,
                    pnl_pct REAL,
                    tempo_posicao_min INTEGER,
                    motivo_fechamento TEXT,
                    FOREIGN KEY(id_oportunidade) REFERENCES oportunidades(id)
                )
            """)
            
            conn.commit()
    
    def registrar_decisao(self, decisao: DecisaoOperacional) -> None:
        """Registra decisão sobre abertura de posição."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT OR REPLACE INTO decisoes_operacionais
                (id_oportunidade, timestamp_decisao, decisao, reasoning,
                 fatores, heuristica_aplicada, motivo_negacao)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (
                decisao.id_oportunidade,
                decisao.timestamp_decisao.isoformat(),
                decisao.decisao.value,
                decisao.reasoning,
                json.dumps(decisao.fatores),
                decisao.heuristica_aplicada,
                decisao.motivo_negacao
            ))
            conn.commit()
    
    def registrar_operacao(self, operacao: RastreamentoOperacao) -> None:
        """Registra rastreamento de operação/posição."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT OR REPLACE INTO rastreamento_operacoes
                (id_operacao, id_oportunidade, timestamp_abertura, entrada_preco,
                 stop_loss, take_profit, status_execucao, timestamp_fechamento,
                 saida_preco, pnl_reais, pnl_pct, tempo_posicao_min, motivo_fechamento)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                operacao.id_operacao,
                operacao.id_oportunidade,
                operacao.timestamp_abertura.isoformat(),
                operacao.entrada_preco,
                operacao.stop_loss,
                operacao.take_profit,
                operacao.status_execucao,
                operacao.timestamp_fechamento.isoformat() if operacao.timestamp_fechamento else None,
                operacao.saida_preco,
                operacao.pnl_reais,
                operacao.pnl_pct,
                operacao.tempo_posicao_min,
                operacao.motivo_fechamento
            ))
            conn.commit()
    
    def obter_operacao(self, id_operacao: str) -> Optional[RastreamentoOperacao]:
        """Obtém rastreamento de operação."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT id_operacao, id_oportunidade, timestamp_abertura, entrada_preco,
                       stop_loss, take_profit, status_execucao, timestamp_fechamento,
                       saida_preco, pnl_reais, pnl_pct, tempo_posicao_min, motivo_fechamento
                FROM rastreamento_operacoes
                WHERE id_operacao = ?
            """, (id_operacao,))
            
            row = cursor.fetchone()
            if not row:
                return None
            
            return RastreamentoOperacao(
                id_operacao=row[0],
                id_oportunidade=row[1],
                timestamp_abertura=datetime.fromisoformat(row[2]),
                entrada_preco=row[3],
                stop_loss=row[4],
                take_profit=row[5],
                status_execucao=row[6],
                timestamp_fechamento=datetime.fromisoformat(row[7]) if row[7] else None,
                saida_preco=row[8],
                pnl_reais=row[9],
                pnl_pct=row[10],
                tempo_posicao_min=row[11],
                motivo_fechamento=row[12]
            )
    
    def listar_operacoes_abertas(self) -> List[RastreamentoOperacao]:
        """Lista todas operações ainda abertas."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT id_operacao, id_oportunidade, timestamp_abertura, entrada_preco,
                       stop_loss, take_profit, status_execucao, timestamp_fechamento,
                       saida_preco, pnl_reais, pnl_pct, tempo_posicao_min, motivo_fechamento
                FROM rastreamento_operacoes
                WHERE status_execucao = 'ABERTA'
            """)
            
            operacoes = []
            for row in cursor.fetchall():
                operacoes.append(RastreamentoOperacao(
                    id_operacao=row[0],
                    id_oportunidade=row[1],
                    timestamp_abertura=datetime.fromisoformat(row[2]),
                    entrada_preco=row[3],
                    stop_loss=row[4],
                    take_profit=row[5],
                    status_execucao=row[6],
                    timestamp_fechamento=datetime.fromisoformat(row[7]) if row[7] else None,
                    saida_preco=row[8],
                    pnl_reais=row[9],
                    pnl_pct=row[10],
                    tempo_posicao_min=row[11],
                    motivo_fechamento=row[12]
                ))
            
            return operacoes


class GeradorRelatorioCicloVida:
    """Gerador de relatórios do ciclo de vida operacional."""
    
    def __init__(self, db_path: str = "data/db/trading.db"):
        """Inicializa gerador de relatórios."""
        self.db_path = db_path
        self._criar_tabelas()
    
    def _criar_tabelas(self) -> None:
        """Cria tabelas SQLite se não existirem."""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS tendencia_diaria (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    data TEXT UNIQUE,
                    timestamp TEXT,
                    direcao TEXT,
                    forca REAL,
                    contexto TEXT,
                    nivel_suporte REAL,
                    nivel_resistencia REAL,
                    volatilidade_esperada REAL
                )
            """)
            
            conn.execute("""
                CREATE TABLE IF NOT EXISTS oportunidades (
                    id TEXT PRIMARY KEY,
                    timestamp_deteccao TEXT,
                    tendencia_id TEXT,
                    preco_referencia REAL,
                    direcao_sugerida TEXT,
                    forcas_tecnicas TEXT,
                    confianca_tecnica REAL,
                    alinhamento_tendencia INTEGER,
                    tamanho_potencial REAL,
                    razao_risco_retorno REAL,
                    status TEXT,
                    FOREIGN KEY(tendencia_id) REFERENCES tendencia_diaria(id)
                )
            """)
            
            conn.execute("""
                CREATE TABLE IF NOT EXISTS rastreamento_operacoes (
                    id_operacao TEXT PRIMARY KEY,
                    id_oportunidade TEXT,
                    timestamp_abertura TEXT,
                    entrada_preco REAL,
                    stop_loss REAL,
                    take_profit REAL,
                    status_execucao TEXT,
                    timestamp_fechamento TEXT,
                    saida_preco REAL,
                    pnl_reais REAL,
                    pnl_pct REAL,
                    tempo_posicao_min INTEGER,
                    motivo_fechamento TEXT,
                    FOREIGN KEY(id_oportunidade) REFERENCES oportunidades(id)
                )
            """)
            
            conn.commit()
    
    def gerar_relatorio_dia(self, data: str = "today") -> Dict[str, Any]:
        """Gera relatório completo do dia (Etapas 1-4)."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            # Etapa 1
            cursor.execute("""
                SELECT direcao, forca, contexto FROM tendencia_diaria
                WHERE data = CASE WHEN ? = 'today' THEN date('now') ELSE ? END
            """, (data, data))
            tendencia_row = cursor.fetchone()
            
            # Etapas 2-3
            cursor.execute("""
                SELECT COUNT(*), 
                       SUM(CASE WHEN status = 'EXECUTADA' THEN 1 ELSE 0 END),
                       SUM(CASE WHEN status = 'CANCELADA' THEN 1 ELSE 0 END),
                       SUM(CASE WHEN status = 'PERDIDA' THEN 1 ELSE 0 END)
                FROM oportunidades
                WHERE date(timestamp_deteccao) = CASE WHEN ? = 'today' THEN date('now') ELSE ? END
            """, (data, data))
            oportunidades_row = cursor.fetchone()
            
            # Etapa 4
            cursor.execute("""
                SELECT COUNT(*),
                       SUM(CASE WHEN pnl_reais > 0 THEN 1 ELSE 0 END),
                       SUM(pnl_reais),
                       AVG(pnl_pct),
                       MAX(pnl_reais),
                       MIN(pnl_reais)
                FROM rastreamento_operacoes
                WHERE date(timestamp_abertura) = CASE WHEN ? = 'today' THEN date('now') ELSE ? END
                  AND status_execucao = 'FECHADA'
            """, (data, data))
            operacoes_row = cursor.fetchone()
            
            return {
                "data": data if data != "today" else datetime.now().strftime("%Y-%m-%d"),
                "etapa_1_tendencia": {
                    "direcao": tendencia_row[0] if tendencia_row else None,
                    "forca": tendencia_row[1] if tendencia_row else None,
                    "contexto": tendencia_row[2] if tendencia_row else None
                } if tendencia_row else None,
                "etapa_2_3_oportunidades": {
                    "total_detectadas": oportunidades_row[0] if oportunidades_row else 0,
                    "executadas": oportunidades_row[1] if oportunidades_row else 0,
                    "canceladas": oportunidades_row[2] if oportunidades_row else 0,
                    "perdidas": oportunidades_row[3] if oportunidades_row else 0
                } if oportunidades_row else None,
                "etapa_4_operacoes": {
                    "total_fechadas": operacoes_row[0] if operacoes_row else 0,
                    "vencedoras": operacoes_row[1] if operacoes_row else 0,
                    "pnl_total": operacoes_row[2] if operacoes_row else 0.0,
                    "pnl_medio_pct": operacoes_row[3] if operacoes_row else 0.0,
                    "maior_ganho": operacoes_row[4] if operacoes_row else 0.0,
                    "maior_perda": operacoes_row[5] if operacoes_row else 0.0
                } if operacoes_row else None
            }
