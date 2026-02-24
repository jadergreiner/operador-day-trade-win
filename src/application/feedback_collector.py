"""Coletor de feedback de intervenção manual.

Este módulo implementa o sistema de coleta de feedback estruturado
quando o trader encerra uma posição manualmente, alimentando o ciclo
de aprendizado contínuo da IA.
"""

import sqlite3
import json
from datetime import datetime
from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass, asdict
import logging

# Configurar logging
logger = logging.getLogger(__name__)


@dataclass
class FeedbackIntervencaoManual:
    """Feedback de intervenção manual do trader.

    Attributes:
        codigo_intervencao: Código de 1-8 indicando motivo da intervenção.
        timestamp: ISO 8601 timestamp da intervenção.
        contexto: Dict com informações de mercado no momento.
        descricao: Descrição livre (opcional, usada para código 8).
        resultado_operacao: Resultado final ('win', 'loss', 'closed').
    """

    codigo_intervencao: int
    timestamp: str
    contexto: Dict
    descricao: str = ""
    resultado_operacao: str = ""

    def __post_init__(self):
        """Valida código de intervenção."""
        if not 1 <= self.codigo_intervencao <= 8:
            raise ValueError(
                f"Código deve estar entre 1 e 8, "
                f"recebido: {self.codigo_intervencao}"
            )

    def to_dict(self) -> Dict:
        """Converte para dicionário."""
        return asdict(self)


class FeedbackCollector:
    """Coletor de feedback de intervenção manual.

    Responsibilidades:
    - Inicializar e gerenciar BD SQLite
    - Solicitar feedback ao trader via console
    - Persistir feedback estruturado
    - Gerar análises agregadas
    """

    # Códigos de intervenção predefinidos
    CODIGOS_INTERVENCAO = {
        1: "Falha Técnica",
        2: "Risco Externo",
        3: "Lucro Satisfatório",
        4: "Stop Hit + Reentrada",
        5: "Volatilidade Extrema",
        6: "Falta de Confiança IA",
        7: "Pausa Operacional",
        8: "Outro / Livre",
    }

    def __init__(self, db_path: str):
        """Inicializa o coletor de feedback.

        Args:
            db_path: Caminho para arquivo SQLite de feedback.
        """
        self.db_path = db_path
        self._init_db()
        logger.info(f"FeedbackCollector inicializado: {db_path}")

    def _init_db(self) -> None:
        """Inicializa tabela intervencoes_manuais se não existir."""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            cursor.execute("""
                CREATE TABLE IF NOT EXISTS intervencoes_manuais (
                    id_intervencao INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp TEXT NOT NULL,
                    codigo_intervencao INTEGER
                        CHECK (codigo_intervencao BETWEEN 1 AND 8),
                    descricao_codigo TEXT,
                    contexto_json TEXT,
                    resultado_operacao TEXT,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
                )
            """)

            # Criar índices
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS
                    idx_timestamp_intervencoes
                ON intervencoes_manuais(timestamp DESC)
            """)
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS
                    idx_codigo_intervencoes
                ON intervencoes_manuais(codigo_intervencao)
            """)

            conn.commit()
            conn.close()
            logger.info("Tabela intervencoes_manuais verificada/criada")

        except sqlite3.Error as e:
            logger.error(f"Erro ao inicializar BD: {e}")
            raise

    def solicitar_feedback(
        self,
        operacao_id: str,
        contexto: Dict,
    ) -> FeedbackIntervencaoManual:
        """Exibe menu e coleta feedback do trader.

        Args:
            operacao_id: ID da operação sendo encerrada.
            contexto: Dict com contexto de mercado.

        Returns:
            FeedbackIntervencaoManual com código e dados.

        Raises:
            ValueError: Se código inválido ou entrada inválida.
        """
        print("\n" + "=" * 60)
        print("FEEDBACK DE INTERVENÇÃO MANUAL")
        print("=" * 60)
        print(f"Operação: {operacao_id}")
        print(f"Score IA: {contexto.get('score', 'N/A'):.2f}")
        print(f"Volatilidade: {contexto.get('volatilidade', 'N/A'):.2f}")
        print(f"Win Rate Sessão: {contexto.get('win_rate', 'N/A'):.1%}")
        print("=" * 60)
        print("\nSelecione o motivo da intervenção (1-8):\n")

        for cod, desc in self.CODIGOS_INTERVENCAO.items():
            print(f"  {cod}. {desc}")

        print("\n" + "-" * 60)

        while True:
            try:
                entrada = input("Código? > ").strip()
                codigo = int(entrada)

                if 1 <= codigo <= 8:
                    break
                else:
                    print(f"❌ Código inválido. Digite entre 1-8.")

            except ValueError:
                print("❌ Entrada inválida. Digite um número.")

        descricao = ""
        if codigo == 8:  # Código "Outro"
            print("\nDescreva brevemente (máx 200 caracteres):")
            descricao = input("> ").strip()[:200]

        feedback = FeedbackIntervencaoManual(
            codigo_intervencao=codigo,
            timestamp=datetime.now().isoformat(),
            contexto=contexto,
            descricao=descricao,
        )

        print(f"✅ Feedback registrado: {self.CODIGOS_INTERVENCAO[codigo]}")
        print("=" * 60 + "\n")

        return feedback

    def registrar_intervencao(
        self,
        feedback: FeedbackIntervencaoManual,
        resultado: str,
    ) -> int:
        """Persiste feedback em intervencoes_manuais.

        Args:
            feedback: Objeto FeedbackIntervencaoManual.
            resultado: Resultado final ('win', 'loss', 'closed').

        Returns:
            id_intervencao: ID da linha inserida (PK).

        Raises:
            sqlite3.Error: Se erro ao escrever BD.
        """
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            contexto_json = json.dumps(feedback.contexto)

            cursor.execute("""
                INSERT INTO intervencoes_manuais
                (
                    timestamp,
                    codigo_intervencao,
                    descricao_codigo,
                    contexto_json,
                    resultado_operacao
                )
                VALUES (?, ?, ?, ?, ?)
            """, (
                feedback.timestamp,
                feedback.codigo_intervencao,
                self.CODIGOS_INTERVENCAO[feedback.codigo_intervencao],
                contexto_json,
                resultado,
            ))

            conn.commit()
            id_new = cursor.lastrowid
            conn.close()

            logger.info(
                f"Intervenção registrada: "
                f"id={id_new}, "
                f"codigo={feedback.codigo_intervencao}"
            )

            return id_new

        except sqlite3.Error as e:
            logger.error(f"Erro ao registrar intervenção: {e}")
            raise

    def obter_historico(
        self,
        filtro_data: Optional[Tuple[str, str]] = None,
    ) -> List[Dict]:
        """Retorna histórico de intervenções com filtro opcional.

        Args:
            filtro_data: Tuple (data_inicio, data_fim) em ISO format.
                        Se None, retorna últimas 100 linhas.

        Returns:
            Lista de dicts com dados das intervenções.
        """
        try:
            conn = sqlite3.connect(self.db_path)
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()

            if filtro_data:
                data_inicio, data_fim = filtro_data
                cursor.execute("""
                    SELECT * FROM intervencoes_manuais
                    WHERE timestamp BETWEEN ? AND ?
                    ORDER BY timestamp DESC
                """, (data_inicio, data_fim))
            else:
                cursor.execute("""
                    SELECT * FROM intervencoes_manuais
                    ORDER BY timestamp DESC
                    LIMIT 100
                """)

            rows = cursor.fetchall()
            conn.close()

            return [dict(row) for row in rows]

        except sqlite3.Error as e:
            logger.error(f"Erro ao obter histórico: {e}")
            return []

    def gerar_relatorio_agregado(
        self,
        filtro_data: Optional[Tuple[str, str]] = None,
    ) -> Dict:
        """Retorna análise agregada por código de intervenção.

        Args:
            filtro_data: Tuple (data_inicio, data_fim) em ISO format.

        Returns:
            Dict com estatísticas por código.

        Examples:
            >>> relatorio = collector.gerar_relatorio_agregado()
            >>> print(relatorio['total'])
            >>> print(relatorio['por_codigo']['3'])
            {'count': 89, 'percentual': 36.0, 'descricao': '...'}
        """
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            # Total geral
            if filtro_data:
                data_inicio, data_fim = filtro_data
                cursor.execute("""
                    SELECT COUNT(*) as total
                    FROM intervencoes_manuais
                    WHERE timestamp BETWEEN ? AND ?
                """, (data_inicio, data_fim))
            else:
                cursor.execute("""
                    SELECT COUNT(*) as total
                    FROM intervencoes_manuais
                """)

            total = cursor.fetchone()[0]

            # Por código
            if filtro_data:
                cursor.execute("""
                    SELECT
                        codigo_intervencao,
                        COUNT(*) as contagem
                    FROM intervencoes_manuais
                    WHERE timestamp BETWEEN ? AND ?
                    GROUP BY codigo_intervencao
                    ORDER BY contagem DESC
                """, (data_inicio, data_fim))
            else:
                cursor.execute("""
                    SELECT
                        codigo_intervencao,
                        COUNT(*) as contagem
                    FROM intervencoes_manuais
                    GROUP BY codigo_intervencao
                    ORDER BY contagem DESC
                """)

            rows = cursor.fetchall()
            conn.close()

            resultado = {
                "total": total,
                "por_codigo": {},
            }

            for codigo, contagem in rows:
                percentual = (contagem / total * 100) if total > 0 else 0
                resultado["por_codigo"][str(codigo)] = {
                    "count": contagem,
                    "percentual": round(percentual, 1),
                    "descricao": self.CODIGOS_INTERVENCAO[codigo],
                }

            logger.info(f"Relatório agregado gerado: {total} intervencoes")

            return resultado

        except sqlite3.Error as e:
            logger.error(f"Erro ao gerar relatório agregado: {e}")
            return {"total": 0, "por_codigo": {}}
