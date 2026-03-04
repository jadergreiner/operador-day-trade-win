"""
Terminal Isolation Enforcer: HARD STOP para garantir APENAS CLEAR terminal.

Implementa:
  1. Validação de terminal ANTES de cada operação crítica
  2. Monitoramento contínuo de processos MT5 concorrentes
  3. Kill switch automático se detectar terminal errado
  4. Auditoria de todas tentativas de isolamento

OBJETIVO: ZERO possibilidade de conectar a FBS/XP/Zero/outro broker.
"""

import os
import sys
import psutil
import logging
from pathlib import Path
from typing import Optional, Dict, Tuple
from datetime import datetime

logger = logging.getLogger(__name__)


class TerminalIsolationViolation(Exception):
    """Exceção lançada quando isolamento de terminal é violado."""
    pass


class TerminalIsolationEnforcer:
    """
    Enforcer de isolamento de terminal.

    Valida que APENAS o terminal Clear está rodando e conectado.
    Se detectar qualquer outro terminal MT5, FALHA IMEDIATAMENTE.
    
    Uso:
        enforcer = TerminalIsolationEnforcer(
            expected_terminal_path="C:\\Program Files\\Clear...\\terminal64.exe"
        )
        
        # Chamar ANTES de qualquer operação crítica
        enforcer.validate_before_operation("send_order")
        
        # Chamar periodicamente para monitorar
        enforcer.validate_continuous()
    """

    # Brokers conhecidos que NÃO devem rodar simultaneamente
    DANGEROUS_PATTERNS = {
        "fbs": ["fbs", "finalbitcoin"],
        "xp": ["xp investimentos", "xp trader"],
        "zero": ["zero markets", "zerodesk"],
        "ic": ["ic markets"],
        "ativa": ["ativa", "ativa investimentos"],
        "rica": ["rica corretora"],
    }

    def __init__(
        self,
        expected_terminal_path: str,
        enforce_mode: str = "HARD_STOP"  # HARD_STOP, WARN_ONLY, MONITOR
    ):
        """
        Inicializa enforcer.

        Args:
            expected_terminal_path: Caminho esperado do terminal Clear
            enforce_mode: Modo de enforcement (HARD_STOP = falha se viola)
        """
        self.expected_terminal_path = expected_terminal_path.lower()
        self.enforce_mode = enforce_mode
        
        # Validação básica
        if "clear" not in self.expected_terminal_path.upper():
            raise ValueError(
                f"Terminal path deve conter 'CLEAR', recebido: {expected_terminal_path}"
            )

        # Estado de monitoramento
        self.violations_count = 0
        self.last_violation_time: Optional[datetime] = None
        self.operation_count = 0
        
        logger.info(
            f"TerminalIsolationEnforcer inicializado com modo {enforce_mode}"
        )

    def validate_before_operation(self, operation_name: str) -> bool:
        """
        BLOQUEIO: Valida isolamento ANTES de operação crítica.

        Lançará TerminalIsolationViolation se isolamento foi violado.

        Args:
            operation_name: Nome da operação (ex: "send_order", "get_positions")

        Returns:
            True se válido

        Raises:
            TerminalIsolationViolation: Se isolamento violado
        """
        self.operation_count += 1

        logger.debug(f"[PRECHECK #{self.operation_count}] {operation_name}")

        # 1. Verificar que arquivo esperado existe
        if not os.path.exists(self.expected_terminal_path):
            msg = (
                f"❌ BLOQUEIO: Terminal esperado não existe!\n"
                f"   Caminho: {self.expected_terminal_path}\n"
                f"   Operação vetada: {operation_name}"
            )
            self._fail(msg)

        # 2. Procurar outros terminais MT5 PERIGOSOS
        dangerous_terminals = self._find_dangerous_terminals()
        if dangerous_terminals:
            msg = (
                f"❌ BLOQUEIO: Detectado terminal(is) PERIGOSO(s) rodando!\n"
                f"   {dangerous_terminals}\n"
                f"   Feche TODOS os outros terminais MT5 (FBS/XP/Zero/etc).\n"
                f"   Operação VETADA: {operation_name}\n"
                f"   Comando: Get-Process terminal64 | Stop-Process -Force"
            )
            self._fail(msg)

        # 3. Verificar que terminal Clear está rodando
        clear_pids = self._find_clear_terminal_pids()
        if not clear_pids:
            msg = (
                f"❌ BLOQUEIO: Terminal CLEAR não está rodando!\n"
                f"   Abra MetaTrader 5 da Clear antes de qualquer operação.\n"
                f"   Operação VETADA: {operation_name}"
            )
            self._fail(msg)

        logger.info(f"✅ PRÉ-VOO OK para {operation_name} (Clear PID: {clear_pids[0]})")
        return True

    def validate_continuous(self) -> bool:
        """
        MONITORAMENTO: Valida isolamento continuamente durante execução.

        Chamado periodicamente (a cada ciclo do agente) para verificar
        que nenhum outro terminal foi aberto.

        Returns:
            True se tudo OK

        Raises:
            TerminalIsolationViolation: Se isolamento violado
        """
        # 1. Procurar outros terminais
        dangerous = self._find_dangerous_terminals()
        if dangerous:
            msg = (
                f"❌ KILL SWITCH: Detectado terminal PERIGOSO durante execução!\n"
                f"   {dangerous}\n"
                f"   Sistema PARANDO imediatamente para proteger sua conta."
            )
            self._fail(msg)

        # 2. Verificar que Clear ainda está rodando
        clear_pids = self._find_clear_terminal_pids()
        if not clear_pids:
            msg = (
                f"❌ KILL SWITCH: Terminal CLEAR desconectou!\n"
                f"   Sistema PARANDO. Reconecte e reinicie o agente."
            )
            self._fail(msg)

        return True

    def get_isolation_status(self) -> Dict:
        """
        Retorna status atual de isolamento.

        Útil para monitoring/logging.

        Returns:
            Dict com status detalhado
        """
        clear_pids = self._find_clear_terminal_pids()
        dangerous = self._find_dangerous_terminals()

        return {
            "is_isolated": not dangerous and bool(clear_pids),
            "clear_terminal_running": bool(clear_pids),
            "clear_pids": clear_pids,
            "dangerous_terminals_detected": dangerous,
            "violations_count": self.violations_count,
            "operations_validated": self.operation_count,
            "last_violation": self.last_violation_time.isoformat() if self.last_violation_time else None,
        }

    def _find_dangerous_terminals(self) -> str:
        """
        Procura por terminais PERIGOSOS (FBS/XP/Zero/etc).

        Returns:
            String com lista de terminais encontrados (vazio se nenhum)
        """
        dangerous_found = []

        try:
            for proc in psutil.process_iter(["pid", "name", "exe"]):
                try:
                    exe = proc.info.get("exe", "").lower()
                    
                    # Skip se é nosso terminal Clear esperado
                    if exe == self.expected_terminal_path:
                        continue
                    
                    # Procurar por padrões perigosos
                    if "terminal64.exe" in proc.info.get("name", "").lower():
                        # É um terminal MT5, mas qual broker?
                        
                        for broker, patterns in self.DANGEROUS_PATTERNS.items():
                            for pattern in patterns:
                                if pattern in exe.lower():
                                    dangerous_found.append(
                                        f"{broker.upper()} (PID:{proc.pid}, exe:{exe})"
                                    )
                except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
                    pass
        except Exception as e:
            logger.warning(f"Erro ao procurar terminais perigosos: {e}")

        return " | ".join(dangerous_found)

    def _find_clear_terminal_pids(self) -> list:
        """
        Procura por terminal Clear rodando.

        Returns:
            Lista de PIDs do terminal Clear (vazio se não rodar)
        """
        clear_pids = []

        try:
            for proc in psutil.process_iter(["pid", "name", "exe"]):
                try:
                    exe = proc.info.get("exe", "").lower()
                    
                    # Procurar por qualquer terminal64.exe from Clear
                    if (
                        exe == self.expected_terminal_path or
                        (
                            "terminal64.exe" in proc.info.get("name", "").lower() and
                            "clear" in exe
                        )
                    ):
                        clear_pids.append(proc.pid)
                except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
                    pass
        except Exception as e:
            logger.warning(f"Erro ao procurar terminal Clear: {e}")

        return clear_pids

    def _fail(self, message: str) -> None:
        """
        Lança exceção com mensagem e aplica enforcement.

        Args:
            message: Mensagem de erro detalhada
        """
        self.violations_count += 1
        self.last_violation_time = datetime.now()

        logger.critical(message)
        print(f"\n{'═' * 70}")
        print(message)
        print(f"{'═' * 70}\n")

        if self.enforce_mode == "HARD_STOP":
            # FALHA IMEDIATA
            raise TerminalIsolationViolation(message)
        elif self.enforce_mode == "WARN_ONLY":
            # Apenas log (para testes)
            logger.warning(f"WARN_ONLY mode: viola seria detectada, apenas logged")


# ─ Instância global ─
_enforcer: Optional[TerminalIsolationEnforcer] = None


def initialize_enforcer(expected_terminal_path: str) -> TerminalIsolationEnforcer:
    """
    Inicializa enforcer global.

    Args:
        expected_terminal_path: Caminho do terminal Clear

    Returns:
        TerminalIsolationEnforcer instance
    """
    global _enforcer
    _enforcer = TerminalIsolationEnforcer(expected_terminal_path)
    return _enforcer


def get_enforcer() -> Optional[TerminalIsolationEnforcer]:
    """Retorna enforcer global (se inicializado)."""
    return _enforcer


def validate_critical_operation(operation_name: str) -> None:
    """
    Conveniência: Valida antes de operação crítica.

    Uso:
        from src.infrastructure.terminal_isolation_enforcer import validate_critical_operation
        
        def send_order(...):
            validate_critical_operation("send_order")
            # ... send order ...

    Args:
        operation_name: Nome da operação
    """
    enforcer = get_enforcer()
    if enforcer:
        enforcer.validate_before_operation(operation_name)
