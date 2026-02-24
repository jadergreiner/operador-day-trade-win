"""Integração de feedback ao loop principal do agente.

Este módulo mostra como integrar FeedbackCollector ao
agente_micro_tendencia_winfut.py de forma não-intrusiva.
"""

import logging
from typing import Optional, Dict
from datetime import datetime
from src.application.feedback_collector import (
    FeedbackCollector,
    FeedbackIntervencaoManual,
)

logger = logging.getLogger(__name__)


class FeedbackIntegrationManager:
    """Gerenciador de integração de feedback ao loop principal.

    Responsabilidades:
    - Capturar contexto de mercado durante operação
    - Solicitar feedback ao trader quando posição encerrada manualmente
    - Persistir feedback com mínimo overhead
    """

    def __init__(self, feedback_db_path: str):
        """Inicializa gerenciador de feedback.

        Args:
            feedback_db_path: Caminho para BD de feedback SQLite.
        """
        self.collector = FeedbackCollector(feedback_db_path)
        self.current_trade_context: Optional[Dict] = None
        logger.info("FeedbackIntegrationManager inicializado")

    def capture_trade_context(
        self,
        trade_id: str,
        score_ia: float,
        volatilidade_atr: float,
        win_rate_sessao: float,
        p_and_l_sessao: float,
    ) -> None:
        """Captura contexto da operação antes de sua conclusão.

        Esta função deve ser chamada APÓS uma ordem ser executada
        e a posição estar aberta.

        Args:
            trade_id: ID único da operação em execução.
            score_ia: Score da IA para este trade (0-1).
            volatilidade_atr: ATR atual do instrumento.
            win_rate_sessao: Win rate acumulado da sessão.
            p_and_l_sessao: P&L acumulado da sessão.

        Examples:
            >>> manager.capture_trade_context(
            ...     trade_id="WINFUT-2026-02-24-14-30",
            ...     score_ia=0.85,
            ...     volatilidade_atr=1.2,
            ...     win_rate_sessao=0.62,
            ...     p_and_l_sessao=1234.56
            ... )
        """
        self.current_trade_context = {
            "trade_id": trade_id,
            "score": float(score_ia),
            "volatilidade": float(volatilidade_atr),
            "win_rate": float(win_rate_sessao),
            "p_and_l": float(p_and_l_sessao),
            "timestamp_captura": datetime.now().isoformat(),
        }
        logger.debug(f"Contexto capturado para {trade_id}")

    def handle_manual_intervention(
        self,
        trade_outcome: str,
    ) -> Optional[Dict]:
        """Solicita feedback ao trader quando intervenção manual detecta.

        Deve ser chamado quando:
        - Trader encerra posição manualmente via interface
        - Sistema detecta encerramento externo (MT5)
        - Posição atinge timeout e trader a encerra manualmente

        Args:
            trade_outcome: Resultado da operação ('win', 'loss', 'closed').

        Returns:
            Dicionário com dados de feedback registrados ou None se cancelado.

        Examples:
            >>> resultado = manager.handle_manual_intervention("win")
            >>> if resultado:
            ...     print(f"Feedback registrado: {resultado['id_intervencao']}")
        """
        if not self.current_trade_context:
            logger.warning("Não há contexto de trade para feedback")
            return None

        try:
            # Solicitar feedback (menu interativo)
            feedback = self.collector.solicitar_feedback(
                operacao_id=self.current_trade_context["trade_id"],
                contexto=self.current_trade_context,
            )

            # Registrar no BD
            id_intervencao = self.collector.registrar_intervencao(
                feedback,
                trade_outcome,
            )

            logger.info(
                f"Feedback registrado com sucesso: "
                f"id={id_intervencao}, "
                f"código={feedback.codigo_intervencao}"
            )

            # Limpar contexto
            self.current_trade_context = None

            return {
                "id_intervencao": id_intervencao,
                "codigo": feedback.codigo_intervencao,
                "descricao": (
                    FeedbackCollector.CODIGOS_INTERVENCAO[
                        feedback.codigo_intervencao
                    ]
                ),
            }

        except Exception as e:
            logger.error(f"Erro ao solicitar feedback: {e}")
            return None

    def get_feedback_status_badge(self) -> str:
        """Retorna badge com status agregado de feedback.

        Útil para exibir no dashboard MONITOR_OPERADOR.bat

        Returns:
            String com status e estatísticas.

        Examples:
            >>> badge = manager.get_feedback_status_badge()
            >>> print(badge)
            "🔵 FEEDBACK: 247 ops | #3 dominante (36%)"
        """
        try:
            relatorio = self.collector.gerar_relatorio_agregado()
            total = relatorio["total"]

            if total == 0:
                return "🔵 FEEDBACK: Sem dados"

            # Encontrar código dominante
            dominante_código = None
            max_count = 0
            for cod, dados in relatorio["por_codigo"].items():
                if dados["count"] > max_count:
                    max_count = dados["count"]
                    dominante_código = cod

            if dominante_código:
                percentual = (
                    relatorio["por_codigo"][str(dominante_código)]["percentual"]
                )
                return (
                    f"🔵 FEEDBACK: {total} ops | "
                    f"#{dominante_código} dominante ({percentual:.0f}%)"
                )
            else:
                return f"🔵 FEEDBACK: {total} ops"

        except Exception as e:
            logger.error(f"Erro ao gerar status badge: {e}")
            return "🔴 FEEDBACK: Erro ao recuperar status"


# ============================================================================
# EXEMPLO DE INTEGRAÇÃO NO LOOP PRINCIPAL
# ============================================================================

"""
Para integrar no agente_micro_tendencia_winfut.py, adicionar o seguinte:

# No início do arquivo:
from src.application.integration.feedback_integration import (
    FeedbackIntegrationManager,
)

# No setup do agente (função main):
def main():
    ...
    # Inicializar FeedbackIntegrationManager
    feedback_manager = FeedbackIntegrationManager(
        feedback_db_path="data/feedback/analytics_intervencao_manual.db"
    )
    ...

# No loop principal (loop While):
while True:
    try:
        # Lógica existente: BDI, SMC, ML
        ordem_executada = executar_ordem_se_sinal_valido(...)

        if ordem_executada:
            trade_id = gerar_trade_id()  # Ex: "WINFUT-2026-02-24-14-30"

            # NOVO: Capturar contexto IMEDIATAMENTE após execução
            feedback_manager.capture_trade_context(
                trade_id=trade_id,
                score_ia=score_final,
                volatilidade_atr=atr_15m,
                win_rate_sessao=stats.win_rate,
                p_and_l_sessao=stats.p_and_l_resultado,
            )

            # Aguardar resultado (pode ser automático ou manual)
            resultado = aguardar_resultado_posicao(
                trade_id=trade_id,
                timeout=3600,  # 1 hora
            )

            # NOVO: Se encerramento manual
            if resultado.tipo == "intervencao_manual":
                feedback_response = feedback_manager.handle_manual_intervention(
                    trade_outcome=resultado.outcome,
                )

                if feedback_response:
                    logger.info(
                        f"Feedback coletado. "
                        f"Código: {feedback_response['codigo']} "
                        f"({feedback_response['descricao']})"
                    )

        # NOVO: Atualizar status badge no MONITOR_OPERADOR.bat
        status_badge = feedback_manager.get_feedback_status_badge()
        print(f"\\n{status_badge}\\n")

    except Exception as e:
        logger.error(f"Erro no loop: {e}")
        time.sleep(5)
"""

