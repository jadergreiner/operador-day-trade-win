"""
P1-LEARNING: Etapa 7 - Learning Rule Generation

Sintetiza padroes de erro detectados nas Etapas 5 (L1) e 6 (L2) em
regras observaveis persistidas em JSON. Cada regra tem a forma:

    "Se <contexto>, evitar <acao_evitar>."

Responsabilidades:
- Agrupar episodios incorretos por contexto de erro
- Calcular frequencia e confianca por padrao
- Incorporar causa causal (L2) como regra adicional
- Persistir learning_rules_YYYYMMDD.json por sessao

Criterio de inclusao de regra:
- Frequencia >= 1 (pelo menos 1 episodio com corretude < 0.5)
- Confianca = frequencia / total_episodios_incorretos

Pipeline:
    Etapa 6 (L2 Causal)   -> p1_learning_l2_causal.py
    Etapa 7 (Learning Rules) -> p1_learning_regras.py  [este modulo]
    Relatorio              -> p1_learning_relatorio.py

Status: Implementacao v1.0 (02/04/2026)
Referencia: docs/BACKLOG.md (P1-LEARNING Etapas 5-7)
"""

from __future__ import annotations

import json
import uuid
from collections import defaultdict
from dataclasses import asdict, dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

from src.application.p1_learning_l1_analysis import ResultadoL1
from src.application.p1_learning_l2_causal import ResultadoL2


# ============================================================================
# DATACLASSES
# ============================================================================


@dataclass
class RegraAprendizado:
    """Regra de aprendizado derivada dos padroes de erro da sessao.

    Atributos:
        regra_id: UUID unico da regra
        contexto: Descricao do contexto de mercado que gerou erros
        acao_evitar: Acao a ser evitada nesse contexto
        frequencia: Quantas vezes o padrao ocorreu na sessao
        confianca: Score 0.0-1.0 (frequencia / total_incorretos)
        fonte: "L1" | "L2" | "L1+L2"
        gerado_em: Timestamp de geracao da regra
    """

    regra_id: str
    contexto: str
    acao_evitar: str
    frequencia: int
    confianca: float
    fonte: str
    gerado_em: datetime

    def para_dict(self) -> dict[str, Any]:
        """Converte para dicionario JSON-serializable."""
        d = asdict(self)
        d["gerado_em"] = self.gerado_em.isoformat()
        return d


# ============================================================================
# GERADOR DE REGRAS
# ============================================================================


class GeradorRegraAprendizado:
    """Sintetiza padroes de erro em regras observaveis de aprendizado.

    Fluxo:
    1. Filtrar ResultadoL1 com corretude < 0.5 (decisoes incorretas)
    2. Agrupar por chave de contexto (volatilidade + motivo)
    3. Calcular frequencia e confianca por grupo
    4. Adicionar regra L2 se causa dominante for DRIFT_REGIME

    Exemplo:
        gerador = GeradorRegraAprendizado()
        regras = gerador.sintetizar_padroes(resultados_l1, resultado_l2)
        caminho = gerador.persistir_regras(regras, resultado_l2, Path("data/models"))
    """

    # Score minimo de corretude para nao gerar regra
    LIMIAR_CORRETUDE: float = 0.5

    def sintetizar_padroes(
        self,
        resultados_l1: list[ResultadoL1],
        resultado_l2: ResultadoL2,
    ) -> list[RegraAprendizado]:
        """Sintetiza padroes de erro em regras de aprendizado.

        Args:
            resultados_l1: Lista de ResultadoL1 da Etapa 5
            resultado_l2: ResultadoL2 da Etapa 6

        Returns:
            Lista de RegraAprendizado (pode ser vazia se sem erros)
        """
        agora = datetime.now()
        regras: list[RegraAprendizado] = []

        # --- Regras L1: agrupamento por contexto de erro ---
        regras_l1 = self._gerar_regras_l1(resultados_l1, agora)
        regras.extend(regras_l1)

        # --- Regra L2: causa causal de regime ---
        regra_l2 = self._gerar_regra_l2(resultado_l2, len(regras_l1), agora)
        if regra_l2 is not None:
            regras.append(regra_l2)

        return regras

    def _gerar_regras_l1(
        self, resultados_l1: list[ResultadoL1], agora: datetime
    ) -> list[RegraAprendizado]:
        """Gera regras a partir dos episodios incorretos (L1).

        Args:
            resultados_l1: Resultados da analise L1
            agora: Timestamp de geracao

        Returns:
            Lista de RegraAprendizado de fonte "L1"
        """
        # Filtrar apenas episodios incorretos
        incorretos = [
            r for r in resultados_l1
            if r.corretude_decisao < self.LIMIAR_CORRETUDE
        ]

        if not incorretos:
            return []

        # Agrupar por chave de contexto
        grupos: dict[str, list[ResultadoL1]] = defaultdict(list)
        for res in incorretos:
            chave = self._chave_contexto(res)
            grupos[chave].append(res)

        total_incorretos = len(incorretos)
        regras: list[RegraAprendizado] = []

        for chave, episodios in grupos.items():
            freq = len(episodios)
            confianca = round(freq / total_incorretos, 3)
            contexto, acao = self._descrever_regra(chave, episodios[0])

            regras.append(
                RegraAprendizado(
                    regra_id=str(uuid.uuid4()),
                    contexto=contexto,
                    acao_evitar=acao,
                    frequencia=freq,
                    confianca=confianca,
                    fonte="L1",
                    gerado_em=agora,
                )
            )

        return regras

    def _gerar_regra_l2(
        self,
        resultado_l2: ResultadoL2,
        n_regras_l1: int,
        agora: datetime,
    ) -> RegraAprendizado | None:
        """Gera regra causal baseada na causa dominante do L2.

        Gera regra apenas quando causa_dominante == DRIFT_REGIME.
        Se ja ha regras L1, usa fonte "L1+L2"; senao, usa "L2".

        Args:
            resultado_l2: Resultado da analise L2
            n_regras_l1: Quantidade de regras L1 ja geradas
            agora: Timestamp de geracao

        Returns:
            RegraAprendizado ou None se nao aplicavel
        """
        if resultado_l2.causa_dominante != "DRIFT_REGIME":
            return None

        fonte = "L1+L2" if n_regras_l1 > 0 else "L2"

        return RegraAprendizado(
            regra_id=str(uuid.uuid4()),
            contexto=(
                f"Drift de regime detectado na sessao "
                f"(win_rate={resultado_l2.win_rate_sessao:.1%})"
            ),
            acao_evitar=(
                "Continuar operando sem ajuste de parametros apos "
                "detectar mudanca de regime de mercado"
            ),
            frequencia=resultado_l2.n_episodios,
            confianca=resultado_l2.confianca,
            fonte=fonte,
            gerado_em=agora,
        )

    # -----------------------------------------------------------------------
    # AUXILIARES
    # -----------------------------------------------------------------------

    def _chave_contexto(self, res: ResultadoL1) -> str:
        """Gera chave de agrupamento para o ResultadoL1.

        Args:
            res: Resultado L1 de um episodio

        Returns:
            String chave no formato "motivo__volatilidade"
        """
        vol = str(res.contexto_mercado.get("volatilidade", "desconhecida")).lower()
        return f"{res.motivo_fechamento}__{vol}"

    def _descrever_regra(
        self, chave: str, exemplo: ResultadoL1
    ) -> tuple[str, str]:
        """Gera descricoes legíveis de contexto e acao_evitar.

        Args:
            chave: Chave de agrupamento
            exemplo: Um episodio do grupo para extrair contexto

        Returns:
            Tupla (contexto: str, acao_evitar: str)
        """
        vol = str(
            exemplo.contexto_mercado.get("volatilidade", "desconhecida")
        ).lower()
        motivo = exemplo.motivo_fechamento

        contexto = f"volatilidade_{vol} AND motivo_fechamento={motivo}"
        acao = f"ENTRADA sem confirmacao adequada em regime de volatilidade_{vol}"

        return contexto, acao

    # -----------------------------------------------------------------------
    # PERSISTENCIA
    # -----------------------------------------------------------------------

    def persistir_regras(
        self,
        regras: list[RegraAprendizado],
        resultado_l2: ResultadoL2,
        output_dir: Path,
    ) -> Path:
        """Persiste regras em arquivo JSON estruturado.

        Formato:
        {
            "sessao_id": "...",
            "gerado_em": "ISO",
            "n_episodios_analisados": N,
            "causa_dominante": "...",
            "regras": [ {...}, ... ]
        }

        Args:
            regras: Lista de RegraAprendizado a persistir
            resultado_l2: ResultadoL2 para metadados
            output_dir: Diretorio de saida

        Returns:
            Path do arquivo JSON criado
        """
        output_dir.mkdir(parents=True, exist_ok=True)

        data_str = datetime.now().strftime("%Y%m%d")
        sessao_slug = resultado_l2.sessao_id.replace(" ", "_")[:20]
        nome = f"learning_rules_{data_str}_{sessao_slug}.json"
        caminho = output_dir / nome

        payload: dict[str, Any] = {
            "sessao_id": resultado_l2.sessao_id,
            "gerado_em": datetime.now().isoformat(),
            "n_episodios_analisados": resultado_l2.n_episodios,
            "causa_dominante": resultado_l2.causa_dominante,
            "regras": [r.para_dict() for r in regras],
        }

        caminho.write_text(
            json.dumps(payload, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

        return caminho
