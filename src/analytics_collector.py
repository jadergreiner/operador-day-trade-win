"""
AnalyticsCollector - Coletor de Eventos de Intervenção Manual

Responsável por:
- Registrar intervenções (OVERRIDE, PAUSE, CANCEL, EXECUTE)
- Atualizar resultados (WIN, LOSS, PARTIAL)
- Gerar estatísticas de performance

Integração: FastAPI WebSocket Server (src/interfaces/websocket_server.py)
"""

import sqlite3
from datetime import datetime
from typing import Optional, Dict, List
from dataclasses import dataclass, field


@dataclass
class InterventionEvent:
    """Evento de intervenção manual."""
    timestamp: datetime
    symbol: str
    action: str  # OVERRIDE, PAUSE, CANCEL, EXECUTE
    ml_signal: float
    trader_decision: str
    reason: Optional[str] = None
    notes: Optional[str] = None


class AnalyticsCollector:
    """
    Coletor centralizado de eventos de intervenção manual.
    
    Responsabilidades:
    1. Persistência em SQLite
    2. Query de histórico
    3. Cálculo de estatísticas
    4. Validação de constraints
    
    Example:
        >>> collector = AnalyticsCollector("data/analytics.db")
        >>> collector.connect()
        >>> 
        >>> # Registrar intervenção
        >>> event_id = collector.log_intervention(
        ...     symbol="WINFUT",
        ...     action="OVERRIDE",
        ...     reason="Padrão SMC com confluência",
        ...     ml_signal=0.75,
        ...     trader_decision="Aumentar ticket 20%"
        ... )
        >>> 
        >>> # Atualizar resultado após operação
        >>> collector.update_intervention_result(
        ...     intervention_id=event_id,
        ...     result="WIN",
        ...     p_and_l=450.50
        ... )
        >>> 
        >>> # Estatísticas
        >>> stats = collector.get_intervention_stats(symbol="WINFUT")
        >>> print(f"Win rate: {stats['win_rate']}%")
    """
    
    def __init__(self, db_path: str):
        """
        Inicializa o collector com path do database.
        
        Args:
            db_path: Caminho para arquivo SQLite (ex: data/analytics.db)
        """
        self.db_path = db_path
        self.conn = None
    
    def connect(self) -> bool:
        """
        Conecta ao database SQLite.
        
        Returns:
            True se conexão bem-sucedida, False caso contrário.
        """
        try:
            self.conn = sqlite3.connect(self.db_path)
            self.conn.row_factory = sqlite3.Row
            return True
        except Exception as e:
            print(f"❌ Erro ao conectar database: {e}")
            return False
    
    def log_intervention(
        self,
        symbol: str,
        action: str,
        ml_signal: float,
        trader_decision: str,
        reason: Optional[str] = None,
        notes: Optional[str] = None
    ) -> Optional[int]:
        """
        Registra uma nova intervenção manual.
        
        Args:
            symbol: Símbolo do contrato (ex: 'WINFUT')
            action: Tipo de ação - 'OVERRIDE', 'PAUSE', 'CANCEL', 'EXECUTE'
            ml_signal: Score ML original [0.0, 1.0]
            trader_decision: Descrição da decisão do trader
            reason: Razão da intervenção
            notes: Notas adicionais
        
        Returns:
            ID da intervenção registrada, ou None se erro
        
        Raises:
            ValueError: Se action não é válido
        """
        if not self.conn:
            print("❌ Database não conectado")
            return None
        
        # Validar action
        valid_actions = {"OVERRIDE", "PAUSE", "CANCEL", "EXECUTE"}
        if action not in valid_actions:
            raise ValueError(
                f"action '{action}' inválido. "
                f"Use: {', '.join(valid_actions)}"
            )
        
        # Validar ml_signal
        if not (0.0 <= ml_signal <= 1.0):
            raise ValueError(f"ml_signal {ml_signal} deve estar em [0.0, 1.0]")
        
        try:
            cursor = self.conn.cursor()
            cursor.execute("""
                INSERT INTO trader_interventions (
                    timestamp, symbol, action, reason, 
                    ml_signal, trader_decision, created_at, notes
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                datetime.now(),
                symbol,
                action,
                reason,
                ml_signal,
                trader_decision,
                datetime.now(),
                notes
            ))
            self.conn.commit()
            intervention_id = cursor.lastrowid
            
            return intervention_id
            
        except Exception as e:
            print(f"❌ Erro ao registrar intervenção: {e}")
            return None
    
    def update_intervention_result(
        self,
        intervention_id: int,
        result: str,
        p_and_l: float,
        notes: Optional[str] = None
    ) -> bool:
        """
        Atualiza resultado de uma intervenção.
        
        Args:
            intervention_id: ID da intervenção (retornado por log_intervention)
            result: Resultado - 'WIN', 'LOSS', 'PARTIAL'
            p_and_l: P&L em pontos (ex: 450.50)
            notes: Notas adicionais
        
        Returns:
            True se update bem-sucedido, False caso contrário
        
        Raises:
            ValueError: Se result inválido ou intervention_id não existe
        """
        if not self.conn:
            print("❌ Database não conectado")
            return False
        
        # Validar result
        valid_results = {"WIN", "LOSS", "PARTIAL"}
        if result not in valid_results:
            raise ValueError(
                f"result '{result}' inválido. "
                f"Use: {', '.join(valid_results)}"
            )
        
        try:
            cursor = self.conn.cursor()
            
            # Verificar se intervenção existe
            cursor.execute(
                "SELECT id FROM trader_interventions WHERE id = ?",
                (intervention_id,)
            )
            if not cursor.fetchone():
                raise ValueError(
                    f"Intervenção {intervention_id} não encontrada"
                )
            
            cursor.execute("""
                UPDATE trader_interventions
                SET result = ?, p_and_l = ?, updated_at = ?
                WHERE id = ?
            """, (result, p_and_l, datetime.now(), intervention_id))
            
            self.conn.commit()
            return True
            
        except Exception as e:
            print(f"❌ Erro ao atualizar intervenção: {e}")
            return False
    
    def get_intervention_stats(
        self, 
        symbol: Optional[str] = None
    ) -> Dict:
        """
        Retorna estatísticas de intervenções.
        
        Args:
            symbol: Filtrar por símbolo (ex: 'WINFUT'). 
                   Se None, retorna estatísticas globais.
        
        Returns:
            Dict com:
            - total_interventions: Total de intervenções
            - wins: Quantidade de WINs
            - losses: Quantidade de LOSSes
            - partials: Quantidade de PARTIALs
            - win_rate: Percentual de WINs
            - avg_pnl: P&L médio
            - total_pnl: P&L total
        """
        if not self.conn:
            print("❌ Database não conectado")
            return {}
        
        try:
            cursor = self.conn.cursor()
            
            if symbol:
                cursor.execute("""
                    SELECT 
                        COUNT(*) as total_interventions,
                        SUM(CASE WHEN result = 'WIN' THEN 1 ELSE 0 END) as wins,
                        SUM(CASE WHEN result = 'LOSS' THEN 1 ELSE 0 END) as losses,
                        SUM(CASE WHEN result = 'PARTIAL' THEN 1 ELSE 0 END) as partials,
                        AVG(p_and_l) as avg_pnl,
                        SUM(p_and_l) as total_pnl
                    FROM trader_interventions
                    WHERE symbol = ?
                """, (symbol,))
            else:
                cursor.execute("""
                    SELECT 
                        COUNT(*) as total_interventions,
                        SUM(CASE WHEN result = 'WIN' THEN 1 ELSE 0 END) as wins,
                        SUM(CASE WHEN result = 'LOSS' THEN 1 ELSE 0 END) as losses,
                        SUM(CASE WHEN result = 'PARTIAL' THEN 1 ELSE 0 END) as partials,
                        AVG(p_and_l) as avg_pnl,
                        SUM(p_and_l) as total_pnl
                    FROM trader_interventions
                """)
            
            row = cursor.fetchone()
            
            if not row:
                return {
                    "total_interventions": 0,
                    "wins": 0,
                    "losses": 0,
                    "partials": 0,
                    "win_rate": 0.0,
                    "avg_pnl": 0.0,
                    "total_pnl": 0.0
                }
            
            total = row["total_interventions"] or 0
            wins = row["wins"] or 0
            
            return {
                "total_interventions": total,
                "wins": wins,
                "losses": row["losses"] or 0,
                "partials": row["partials"] or 0,
                "win_rate": (wins / total * 100) if total > 0 else 0.0,
                "avg_pnl": row["avg_pnl"] or 0.0,
                "total_pnl": row["total_pnl"] or 0.0
            }
            
        except Exception as e:
            print(f"❌ Erro ao calcular estatísticas: {e}")
            return {}
    
    def get_interventions_by_action(
        self,
        action: str,
        limit: int = 10
    ) -> List[Dict]:
        """
        Retorna últimas intervenções de um tipo específico.
        
        Args:
            action: Tipo de ação ('OVERRIDE', 'PAUSE', 'CANCEL', 'EXECUTE')
            limit: Quantidade máxima de registros
        
        Returns:
            Lista de dicts com histórico
        """
        if not self.conn:
            return []
        
        try:
            cursor = self.conn.cursor()
            cursor.execute("""
                SELECT * FROM trader_interventions
                WHERE action = ?
                ORDER BY timestamp DESC
                LIMIT ?
            """, (action, limit))
            
            rows = cursor.fetchall()
            return [dict(row) for row in rows]
            
        except Exception as e:
            print(f"❌ Erro ao buscar intervenções: {e}")
            return []
    
    def close(self):
        """Fecha conexão com database."""
        if self.conn:
            self.conn.close()
            self.conn = None
    
    def __enter__(self):
        """Context manager entry."""
        self.connect()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.close()


if __name__ == "__main__":
    # Exemplo de uso
    print("=" * 70)
    print("AnalyticsCollector - Example")
    print("=" * 70)
    
    with AnalyticsCollector("data/analytics.db") as collector:
        print("\n✅ Conectado ao database analytics\n")
        
        # Registrar uma intervenção
        print("1. Registrando intervenção OVERRIDE...")
        event_id = collector.log_intervention(
            symbol="WINFUT",
            action="OVERRIDE",
            reason="Divergência SMC + confluência",
            ml_signal=0.72,
            trader_decision="Aumentar 25% do ticket"
        )
        
        if event_id:
            print(f"   ✅ Intervenção registrada com ID: {event_id}\n")
            
            # Simular resultado
            print("2. Atualizando resultado...")
            success = collector.update_intervention_result(
                intervention_id=event_id,
                result="WIN",
                p_and_l=475.50,
                notes="Setup perfeito, saiu no topo"
            )
            print(f"   {'✅' if success else '❌'} Resultado atualizado\n")
        
        # Estatísticas
        print("3. Estatísticas gerais:")
        stats = collector.get_intervention_stats()
        print(f"   Total intervenções: {stats['total_interventions']}")
        print(f"   Wins: {stats['wins']}")
        print(f"   Win rate: {stats['win_rate']:.1f}%")
        print(f"   Total P&L: {stats['total_pnl']:.2f}\n")
    
    print("=" * 70)
    print("✅ Status: AnalyticsCollector pronto para integração\n")
