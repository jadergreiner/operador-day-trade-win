"""
Manual Override Logger - S2-6

Responsavel por logar todas as intervencoes manuais do trader.
Auditoria completa + rastreabilidade.
"""

import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Optional, Dict, Any

from .config import AnalyticsConfig
from .models import ManualOverride, InterventionType


class ManualOverrideLogger:
    """Logger para intervencoes manuais do trader"""

    def __init__(self, config: Optional[AnalyticsConfig] = None) -> None:
        """
        Initializa o logger de intervencoes
        
        Args:
            config: Configuracao do modulo analytics
        """
        self.config = config or AnalyticsConfig()
        self.log_path = self.config.override_log_path
        
        # Configurar logging
        self.logger = self._setup_logger()
        
        # Validacoes
        self._overrides_count: Dict[str, int] = {}  # Contador por trader
        
    def _setup_logger(self) -> logging.Logger:
        """Configura o logger de arquivo"""
        logger = logging.getLogger("ManualOverrideLogger")
        
        # Remove handlers existentes
        for handler in logger.handlers[:]:
            logger.removeHandler(handler)
        
        logger.setLevel(logging.INFO)
        
        # Handler de arquivo
        handler = logging.FileHandler(self.log_path)
        formatter = logging.Formatter(
            "%(asctime)s | %(name)s | %(levelname)s | %(message)s"
        )
        handler.setFormatter(formatter)
        logger.addHandler(handler)
        
        return logger
    
    def log_override(
        self,
        override_id: str,
        trader_id: str,
        intervention_type: InterventionType,
        reason: str,
        signal_id: Optional[str] = None,
        previous_value: Optional[Any] = None,
        new_value: Optional[Any] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> ManualOverride:
        """
        Registra uma intervencao manual
        
        Args:
            override_id: ID unico da intervencao
            trader_id: ID do trader
            intervention_type: Tipo de intervencao
            reason: Motivo da intervencao
            signal_id: ID do sinal relacionado (se aplicavel)
            previous_value: Valor anterior (se override de parametro)
            new_value: Novo valor (se override de parametro)
            metadata: Dados adicionais
            
        Returns:
            ManualOverride com todos os dados registrados
        """
        override = ManualOverride(
            override_id=override_id,
            timestamp=datetime.now(),
            intervention_type=intervention_type,
            trader_id=trader_id,
            reason=reason,
            signal_id=signal_id,
            previous_value=previous_value,
            new_value=new_value,
            metadata=metadata or {},
        )
        
        # Validacao de limite de intervencoes consecutivas
        self._validate_intervention_limit(trader_id)
        
        # Log em arquivo (JSON)
        log_entry = {
            "override_id": override.override_id,
            "timestamp": override.timestamp.isoformat(),
            "trader_id": override.trader_id,
            "intervention_type": override.intervention_type.value,
            "reason": override.reason,
            "signal_id": override.signal_id,
            "previous_value": str(override.previous_value),
            "new_value": str(override.new_value),
            "metadata": override.metadata,
        }
        
        self.logger.info(json.dumps(log_entry))
        
        # Contador de intervencoes
        self._overrides_count[trader_id] = self._overrides_count.get(trader_id, 0) + 1
        
        return override
    
    def _validate_intervention_limit(self, trader_id: str) -> bool:
        """
        Valida se o trader nao esta excedendo limite de intervencoes
        
        Args:
            trader_id: ID do trader
            
        Returns:
            True se esta dentro do limite, False caso contrario
        """
        count = self._overrides_count.get(trader_id, 0)
        
        if count >= self.config.max_consecutive_manual_overrides:
            msg = (
                f"Trader {trader_id} excedeu limite de {self.config.max_consecutive_manual_overrides} " 
                f"intervencoes (atual: {count}). Alert gerado."
            )
            self.logger.warning(msg)
            return False
        
        return True
    
    def get_override_statistics(
        self,
        trader_id: Optional[str] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
    ) -> Dict[str, Any]:
        """
        Obtem estatisticas de intervencoes
        
        Args:
            trader_id: Filtro por trader (opcional)
            start_date: Data inicial (opcional)
            end_date: Data final (opcional)
            
        Returns:
            Dicionario com estatisticas
        """
        stats = {
            "total_overrides": 0,
            "by_trader": {},
            "by_type": {},
            "period": {
                "start": start_date.isoformat() if start_date else None,
                "end": end_date.isoformat() if end_date else None,
            },
        }
        
        # Ler arquivo de log
        if not self.log_path.exists():
            return stats
        
        with open(self.log_path, "r") as f:
            for line in f:
                try:
                    # Parse JSON do log
                    if "|" in line:  # Formato padrao de logging
                        json_part = line.split("|")[-1].strip()
                        entry = json.loads(json_part)
                    else:
                        entry = json.loads(line)
                    
                    # Aplicar filtros
                    if trader_id and entry.get("trader_id") != trader_id:
                        continue
                    
                    timestamp = datetime.fromisoformat(entry.get("timestamp", ""))
                    if start_date and timestamp < start_date:
                        continue
                    if end_date and timestamp > end_date:
                        continue
                    
                    # Contar
                    stats["total_overrides"] += 1
                    
                    # Por trader
                    tid = entry.get("trader_id", "unknown")
                    stats["by_trader"][tid] = stats["by_trader"].get(tid, 0) + 1
                    
                    # Por tipo
                    itype = entry.get("intervention_type", "unknown")
                    stats["by_type"][itype] = stats["by_type"].get(itype, 0) + 1
                    
                except (json.JSONDecodeError, ValueError):
                    continue
        
        return stats
    
    def reset_counter(self, trader_id: str) -> None:
        """
        Reseta contador de intervencoes consecutivas
        
        Args:
            trader_id: ID do trader
        """
        self._overrides_count[trader_id] = 0
        self.logger.info(f"Counter reset para trader {trader_id}")
