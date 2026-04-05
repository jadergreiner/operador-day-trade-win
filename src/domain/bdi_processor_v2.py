"""
BDI Processor v2 — Dominio

Define a logica de filtragem por confianca, audit logging e metricas
da pipeline BDI.

Responsabilidades (ENG-202 / BLID-037):
- AC-2: Filtro de confianca com limiar configuravel (padrao: 0.75)
- AC-6: Registro de auditoria para cada decisao de filtro
- AC-7: Calculo e exportacao de precision, recall e F1-score

Pipeline:
    ProcessadorBDI gera AlertaOportunidade
    -> FiltroConfiancaBDI.avaliar(alerta)
    -> Se APROVADO: FilaAlertas.enfileirar() -> WebSocket
    -> Se REJEITADO: apenas audit log, sem enfileiramento

Status: Implementacao v1.0 (05/04/2026)
Referencia: docs/BACKLOG.md BLID-037, ADR-030
"""

import logging
import time
from dataclasses import dataclass, field
from datetime import datetime
from decimal import Decimal
from typing import List, Protocol, runtime_checkable

logger = logging.getLogger(__name__)

# Limiar de confianca padrao — apenas alertas com confianca ACIMA deste
# valor sao aprovados e enfileirados para o WebSocket (AC-2)
LIMIAR_CONFIANCA_PADRAO: Decimal = Decimal("0.75")


@runtime_checkable
class AlertaProtocol(Protocol):
    """
    Protocolo tipado para AlertaOportunidade.

    Define os atributos minimos que FiltroConfiancaBDI utiliza para
    avaliacao de confianca, eliminando a necessidade de type: ignore
    e permitindo type checking estrito.
    """

    confianca: Decimal
    ativo: object   # Symbol (possui __str__)
    padrao: object  # PatraoAlerta (possui .value: str)


@dataclass
class RegistroAuditFiltro:
    """
    Registro de auditoria de uma decisao de filtro de confianca.

    Criado para cada AlertaOportunidade avaliado, independente de
    ser aprovado ou rejeitado. Garante rastreabilidade completa (AC-6).
    """

    timestamp: datetime
    ativo: str
    padrao: str
    confianca: Decimal
    decisao: str        # "APROVADO" ou "REJEITADO"
    motivo: str         # descricao legivel da comparacao confianca vs limiar
    latencia_ms: float  # tempo de avaliacao em ms (meta: < 100ms total pipeline)


@dataclass
class MetricasPipelineBDI:
    """
    Metricas de qualidade acumuladas da pipeline BDI (AC-7).

    Contadores:
    - total_processados: todos os alertas avaliados pelo filtro
    - aprovados:         alertas que passaram (confianca > limiar)
    - rejeitados:        alertas bloqueados (confianca <= limiar)

    Feedback de resultados reais (alimentado externamente):
    - verdadeiros_positivos: aprovados que geraram trade lucrativo
    - falsos_positivos:      aprovados que geraram trade com perda
    - falsos_negativos:      rejeitados que teriam sido lucrativos

    Enquanto nenhum feedback real for registrado, precision e recall
    sao calculados como aproximacao baseada nos contadores de filtro.
    """

    total_processados: int = 0
    aprovados: int = 0
    rejeitados: int = 0
    verdadeiros_positivos: int = 0
    falsos_positivos: int = 0
    falsos_negativos: int = 0

    @property
    def precision(self) -> float:
        """
        Precision = TP / (TP + FP).

        Sem feedback real, usa razao de aprovacao como aproximacao:
        precision_aprox = aprovados / total_processados.
        """
        denom = self.verdadeiros_positivos + self.falsos_positivos
        if denom == 0:
            if self.total_processados == 0:
                return 0.0
            return round(self.aprovados / self.total_processados, 4)
        return round(self.verdadeiros_positivos / denom, 4)

    @property
    def recall(self) -> float:
        """
        Recall = TP / (TP + FN).

        Sem feedback real, retorna 1.0 se ha aprovados (todos capturados).
        """
        denom = self.verdadeiros_positivos + self.falsos_negativos
        if denom == 0:
            return 1.0 if self.aprovados > 0 else 0.0
        return round(self.verdadeiros_positivos / denom, 4)

    @property
    def f1_score(self) -> float:
        """F1 = 2 * precision * recall / (precision + recall)."""
        p = self.precision
        r = self.recall
        return round(2 * p * r / (p + r), 4) if (p + r) > 0 else 0.0

    def exportar(self) -> dict:
        """
        Exporta metricas para dict (AC-7).

        Returns:
            Dict com chaves: total_processados, aprovados, rejeitados,
            taxa_aprovacao, precision, recall, f1_score.
        """
        taxa = (
            round(self.aprovados / self.total_processados, 4)
            if self.total_processados > 0
            else 0.0
        )
        return {
            "total_processados": self.total_processados,
            "aprovados": self.aprovados,
            "rejeitados": self.rejeitados,
            "taxa_aprovacao": taxa,
            "precision": self.precision,
            "recall": self.recall,
            "f1_score": self.f1_score,
        }


class FiltroConfiancaBDI:
    """
    Filtro de confianca para alertas da pipeline BDI.

    AC-2: Filtra AlertaOportunidade com confianca > limiar (padrao: 0.75).
    AC-6: Registra audit log para cada decisao de filtro.
    AC-7: Acumula metricas exportaveis (precision, recall, F1).

    Uso:
        filtro = FiltroConfiancaBDI()
        if filtro.avaliar(alerta):
            await fila.enfileirar(alerta)
        metricas = filtro.exportar_metricas()
    """

    def __init__(self, limiar: Decimal = LIMIAR_CONFIANCA_PADRAO) -> None:
        """
        Inicializa filtro.

        Args:
            limiar: Threshold de confianca (padrao 0.75 conforme AC-2).
        """
        self.limiar = limiar
        self.historico_audit: List[RegistroAuditFiltro] = []
        self.metricas = MetricasPipelineBDI()

    def avaliar(self, alerta: AlertaProtocol) -> bool:
        """
        Avalia se alerta passa o filtro de confianca.

        AC-2: aprovado apenas se confianca > limiar (estritamente maior).
        AC-6: registra RegistroAuditFiltro independente da decisao.

        Args:
            alerta: objeto que implementa AlertaProtocol
                    (confianca, ativo, padrao).

        Returns:
            True se aprovado, False se rejeitado.
        """
        inicio = time.perf_counter()

        confianca: Decimal = alerta.confianca
        aprovado = confianca > self.limiar

        latencia_ms = (time.perf_counter() - inicio) * 1000

        decisao = "APROVADO" if aprovado else "REJEITADO"
        motivo = (
            f"confianca={float(confianca):.3f} > limiar={float(self.limiar):.2f}"
            if aprovado
            else (
                f"confianca={float(confianca):.3f} "
                f"<= limiar={float(self.limiar):.2f}"
            )
        )

        registro = RegistroAuditFiltro(
            timestamp=datetime.now(),
            ativo=str(alerta.ativo),
            padrao=alerta.padrao.value,
            confianca=confianca,
            decisao=decisao,
            motivo=motivo,
            latencia_ms=latencia_ms,
        )
        self.historico_audit.append(registro)

        self.metricas.total_processados += 1
        if aprovado:
            self.metricas.aprovados += 1
        else:
            self.metricas.rejeitados += 1

        logger.info(
            "[AUDIT-FILTRO] %s | %s | confianca=%.3f | %s | %.3fms",
            registro.ativo,
            registro.padrao,
            float(confianca),
            decisao,
            latencia_ms,
        )

        return aprovado

    def exportar_metricas(self) -> dict:
        """
        AC-7: Exporta metricas de qualidade da pipeline.

        Returns:
            Dict com precision, recall, f1_score e contadores.
        """
        return self.metricas.exportar()

    def registrar_resultado_real(
        self,
        foi_aprovado: bool,
        foi_correto: bool,
    ) -> None:
        """
        Alimenta feedback de resultado real para calculo de precision/recall.

        Deve ser chamado apos resultado do trade associado ao alerta.

        Args:
            foi_aprovado: True se o filtro aprovou o alerta.
            foi_correto:  True se a decisao foi correta (trade lucrativo
                          se aprovado, ou operacao perdedora evitada se
                          rejeitado).
        """
        if foi_aprovado and foi_correto:
            self.metricas.verdadeiros_positivos += 1
        elif foi_aprovado and not foi_correto:
            self.metricas.falsos_positivos += 1
        elif not foi_aprovado and not foi_correto:
            # Rejeitado, mas deveria ter sido aprovado
            self.metricas.falsos_negativos += 1
        # Verdadeiro negativo (rejeitado corretamente): nao impacta F1
