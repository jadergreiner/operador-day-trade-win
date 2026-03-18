"""
CALIBRACAO-MICRO-06: Autoavaliacao de Inatividade em Mercado Direcional.

Responsabilidades:
- Detectar dias sem trade em mercado favoravel (ADX >= 30, macro >= 15,
  range >= 500 pts) — inatividade injusta
- Gerar episodios HOLD_FORCADO penalizados em rl_rewards para cada
  oportunidade detectada mas nao executada
- Calcular penalidade proporcional ao movimento nao capturado
  (formula: -0.5 por cada 100 pts perdidos)
- Gerar relatorio diario outputs/micro_autoavaliacao_YYYYMMDD.md com
  condicoes do mercado, oportunidades e recomendacao
- Integrar penalidades no ciclo de retreinamento (CALIBRACAO-MICRO-05)

Pipeline:
    Encerramento do pregao / a cada 3h sem trade
    -> AutoavaliacaoInatividade.avaliar_dia()
    -> coletar_condicoes_do_dia()       -- consulta SQLite
    -> _e_inatividade_injusta()         -- verifica condicoes
    -> gerar_episodios_hold_penalizados() -- gera episodios
    -> persistir_episodios()            -- grava em rl_rewards
    -> gerar_relatorio_markdown()       -- relatorio legivel
    -> salvar_relatorio()               -- outputs/

Status: Implementacao v1.0 (18/03/2026)
Referencia: docs/BACKLOG.md (CALIBRACAO-MICRO-06)
"""

import logging
import sqlite3
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Optional

logger = logging.getLogger(__name__)

# ────────────────────────────────────────────────────────────────
# Limiares de deteccao de inatividade injusta
# ────────────────────────────────────────────────────────────────

LIMIAR_MACRO_SCORE = 15.0       # macro_score_medio >= 15 no dia
LIMIAR_ADX = 30.0               # adx_medio >= 30 no dia
LIMIAR_MARKET_RANGE_PTS = 500.0  # market_range_pts >= 500 no dia

# Penalidade por movimento nao capturado
# Formula: movimento_pts / 100 * PENALIDADE_POR_100_PTS
PENALIDADE_POR_100_PTS = -0.5   # -0.5 reward por cada 100 pts perdidos
PENALIDADE_TETO = -5.0          # teto maximo de penalidade por episodio


# ────────────────────────────────────────────────────────────────
# Enums
# ────────────────────────────────────────────────────────────────


class StatusAutoavaliacao(str, Enum):
    """Status do resultado da autoavaliacao diaria."""

    INATIVIDADE_INJUSTA = "INATIVIDADE_INJUSTA"
    """Agente ficou parado em mercado favoravel — penalidades geradas."""

    MERCADO_FRACO = "MERCADO_FRACO"
    """Mercado sem direcao — inatividade justificada, sem penalidade."""

    SEM_DADOS = "SEM_DADOS"
    """Banco sem dados suficientes para avaliar o dia."""

    TRADES_EXECUTADOS = "TRADES_EXECUTADOS"
    """Agente operou no dia — sem avaliacao de inatividade."""


# ────────────────────────────────────────────────────────────────
# Dataclasses
# ────────────────────────────────────────────────────────────────


@dataclass
class CondicoesInatividade:
    """Condicoes de mercado do dia para avaliar se inatividade foi injusta.

    Campos:
        data: Data do pregao (YYYY-MM-DD).
        n_trades_executados: Numero de trades realizados no dia.
        macro_score_medio: Media do macro_score ao longo do pregao.
        adx_medio: Media do ADX ao longo do pregao.
        market_range_pts: Range total do mercado no dia (max - min) em pontos.
        n_oportunidades_detectadas: Total de oportunidades geradas pelo agente.
        n_oportunidades_executadas: Total de oportunidades efetivamente abertas.
    """

    data: str
    n_trades_executados: int
    macro_score_medio: float
    adx_medio: float
    market_range_pts: float
    n_oportunidades_detectadas: int
    n_oportunidades_executadas: int

    def para_dict(self) -> dict[str, object]:
        """Serializa para dicionario JSON-compativel.

        Returns:
            dict: Campos da dataclass como dicionario.
        """
        return {
            "data": self.data,
            "n_trades_executados": self.n_trades_executados,
            "macro_score_medio": self.macro_score_medio,
            "adx_medio": self.adx_medio,
            "market_range_pts": self.market_range_pts,
            "n_oportunidades_detectadas": self.n_oportunidades_detectadas,
            "n_oportunidades_executadas": self.n_oportunidades_executadas,
        }


@dataclass
class EpisodioHoldPenalizado:
    """Episodio de HOLD que deveria ter sido trade — penalidade para rl_rewards.

    Cada oportunidade detectada mas nao executada em dia de inatividade injusta
    gera um registro com penalidade proporcional ao movimento perdido.

    Campos:
        opportunity_id: ID da oportunidade em micro_trend_opportunities.
        timestamp: Timestamp da oportunidade original.
        direction: Direcao sugerida (COMPRA ou VENDA).
        movimento_pts: Movimento real do mercado apos o timestamp (estimado).
        penalidade_normalizada: Reward normalizado negativo (proporcional ao movimento).
        was_correct: 0 — ficar fora foi incorreto.
        action_at_decision: Sempre "HOLD_FORCADO".
    """

    opportunity_id: int
    timestamp: str
    direction: str
    movimento_pts: float
    penalidade_normalizada: float
    was_correct: int
    action_at_decision: str = "HOLD_FORCADO"

    def para_dict(self) -> dict[str, object]:
        """Serializa para dicionario JSON-compativel.

        Returns:
            dict: Campos do episodio como dicionario.
        """
        return {
            "opportunity_id": self.opportunity_id,
            "timestamp": self.timestamp,
            "direction": self.direction,
            "movimento_pts": self.movimento_pts,
            "penalidade_normalizada": self.penalidade_normalizada,
            "was_correct": self.was_correct,
            "action_at_decision": self.action_at_decision,
        }


@dataclass
class ResultadoAutoavaliacao:
    """Resultado completo da autoavaliacao diaria de inatividade.

    Campos:
        status: Status da avaliacao (INATIVIDADE_INJUSTA, MERCADO_FRACO, etc).
        data: Data avaliada (YYYY-MM-DD).
        condicoes: Condicoes de mercado do dia.
        episodios_penalizados: Lista de episodios HOLD_FORCADO gerados.
        movimento_total_perdido_pts: Soma dos movimentos nao capturados.
        penalidade_total: Soma absoluta das penalidades geradas.
        recomendacao: Texto com recomendacao para o operador.
        arquivo_relatorio: Caminho do arquivo Markdown salvo (ou None).
    """

    status: StatusAutoavaliacao
    data: str
    condicoes: CondicoesInatividade
    episodios_penalizados: list[EpisodioHoldPenalizado]
    movimento_total_perdido_pts: float
    penalidade_total: float
    recomendacao: str
    arquivo_relatorio: Optional[str] = None

    def para_dict(self) -> dict[str, object]:
        """Serializa resultado completo para dicionario JSON-compativel.

        Returns:
            dict: Estrutura completa do resultado.
        """
        return {
            "status": self.status.value,
            "data": self.data,
            "condicoes": self.condicoes.para_dict(),
            "n_episodios_penalizados": len(self.episodios_penalizados),
            "episodios_penalizados": [e.para_dict() for e in self.episodios_penalizados],
            "movimento_total_perdido_pts": self.movimento_total_perdido_pts,
            "penalidade_total": self.penalidade_total,
            "recomendacao": self.recomendacao,
            "arquivo_relatorio": self.arquivo_relatorio,
        }


# ────────────────────────────────────────────────────────────────
# Motor principal
# ────────────────────────────────────────────────────────────────


class AutoavaliacaoInatividade:
    """Motor de autoavaliacao de inatividade em mercado direcional.

    Detecta quando o agente ficou parado em um pregao com mercado favoravel
    e gera episodios de penalidade para alimentar o retreinamento do LightGBM.

    O objetivo e ensinar ao modelo que HOLD em mercado direcional tem custo
    real — tao penalizavel quanto um trade perdedor.

    Uso tipico:
        avaliador = AutoavaliacaoInatividade(db_path="data/db/trading.db")
        resultado = avaliador.avaliar_dia(
            n_trades_executados=0,
            diretorio_outputs="outputs/"
        )
    """

    def __init__(self, db_path: str) -> None:
        """Inicializa o motor de autoavaliacao.

        Args:
            db_path: Caminho para o banco SQLite do agente.
        """
        self.db_path = db_path

    # ──────────────────────────────────────────────────────────
    # API publica
    # ──────────────────────────────────────────────────────────

    def avaliar_dia(
        self,
        n_trades_executados: int,
        diretorio_outputs: str = "outputs",
    ) -> ResultadoAutoavaliacao:
        """Executa avaliacao completa do dia.

        Fluxo:
          1. Coleta condicoes do mercado no banco
          2. Verifica se inatividade foi injusta
          3. Gera episodios HOLD penalizados (se injusta)
          4. Persiste episodios em rl_rewards
          5. Gera relatorio Markdown
          6. Salva relatorio em outputs/

        Args:
            n_trades_executados: Numero de trades abertos no dia.
            diretorio_outputs: Diretorio para salvar relatorio.

        Returns:
            ResultadoAutoavaliacao: Resultado completo com episodios e relatorio.
        """
        data_hoje = datetime.now().date().isoformat()

        # Passo 1: Coleta condicoes do mercado
        condicoes = self.coletar_condicoes_do_dia()
        if condicoes is None:
            return ResultadoAutoavaliacao(
                status=StatusAutoavaliacao.SEM_DADOS,
                data=data_hoje,
                condicoes=CondicoesInatividade(
                    data=data_hoje,
                    n_trades_executados=n_trades_executados,
                    macro_score_medio=0.0,
                    adx_medio=0.0,
                    market_range_pts=0.0,
                    n_oportunidades_detectadas=0,
                    n_oportunidades_executadas=0,
                ),
                episodios_penalizados=[],
                movimento_total_perdido_pts=0.0,
                penalidade_total=0.0,
                recomendacao="Sem dados suficientes para avaliar o dia.",
                arquivo_relatorio=None,
            )

        # Sobrescreve n_trades com o valor passado diretamente
        condicoes_atualizadas = CondicoesInatividade(
            data=condicoes.data,
            n_trades_executados=n_trades_executados,
            macro_score_medio=condicoes.macro_score_medio,
            adx_medio=condicoes.adx_medio,
            market_range_pts=condicoes.market_range_pts,
            n_oportunidades_detectadas=condicoes.n_oportunidades_detectadas,
            n_oportunidades_executadas=n_trades_executados,
        )

        # Passo 2: Verifica inatividade injusta
        if n_trades_executados > 0:
            return ResultadoAutoavaliacao(
                status=StatusAutoavaliacao.TRADES_EXECUTADOS,
                data=data_hoje,
                condicoes=condicoes_atualizadas,
                episodios_penalizados=[],
                movimento_total_perdido_pts=0.0,
                penalidade_total=0.0,
                recomendacao="Agente operou no dia — sem avaliacao de inatividade.",
                arquivo_relatorio=None,
            )

        if not self._e_inatividade_injusta(condicoes_atualizadas):
            return ResultadoAutoavaliacao(
                status=StatusAutoavaliacao.MERCADO_FRACO,
                data=data_hoje,
                condicoes=condicoes_atualizadas,
                episodios_penalizados=[],
                movimento_total_perdido_pts=0.0,
                penalidade_total=0.0,
                recomendacao=(
                    "Mercado sem direcao clara — inatividade justificada. "
                    "Nenhuma penalidade gerada."
                ),
                arquivo_relatorio=None,
            )

        # Passo 3: Gera episodios penalizados
        episodios = self.gerar_episodios_hold_penalizados()

        # Passo 4: Persiste em rl_rewards
        n_persistidos = self.persistir_episodios(episodios)
        logger.info(
            "CALIBRACAO-MICRO-06: %d episodios HOLD_FORCADO persistidos em rl_rewards",
            n_persistidos,
        )

        # Calcula metricas agregadas
        movimento_total = sum(e.movimento_pts for e in episodios)
        penalidade_total = abs(sum(e.penalidade_normalizada for e in episodios))

        recomendacao = (
            f"Calibracao necessaria — agente excessivamente conservador. "
            f"{len(episodios)} oportunidades perdidas com {movimento_total:.0f} pts "
            f"de movimento disponivel."
        )

        resultado = ResultadoAutoavaliacao(
            status=StatusAutoavaliacao.INATIVIDADE_INJUSTA,
            data=data_hoje,
            condicoes=condicoes_atualizadas,
            episodios_penalizados=episodios,
            movimento_total_perdido_pts=movimento_total,
            penalidade_total=penalidade_total,
            recomendacao=recomendacao,
            arquivo_relatorio=None,
        )

        # Passo 5: Gera relatorio
        conteudo = self.gerar_relatorio_markdown(resultado)

        # Passo 6: Salva relatorio
        try:
            caminho = self.salvar_relatorio(
                conteudo=conteudo,
                data=data_hoje,
                diretorio_outputs=diretorio_outputs,
            )
            resultado.arquivo_relatorio = caminho
            logger.info("CALIBRACAO-MICRO-06: Relatorio salvo em %s", caminho)
        except Exception as exc:
            logger.warning("CALIBRACAO-MICRO-06: Falha ao salvar relatorio: %s", exc)

        return resultado

    def coletar_condicoes_do_dia(self) -> Optional[CondicoesInatividade]:
        """Coleta condicoes do mercado para o dia de hoje do banco SQLite.

        Consulta as tabelas micro_trend_decisions e micro_trend_opportunities
        para calcular macro_score_medio, adx_medio, market_range_pts e
        numero de oportunidades detectadas.

        Returns:
            CondicoesInatividade com dados do dia, ou None se sem dados.
        """
        data_hoje = datetime.now().date().isoformat()
        try:
            conn = sqlite3.connect(self.db_path)
            cur = conn.cursor()

            # Macro score e ADX medios do dia
            cur.execute("""
                SELECT AVG(CAST(macro_score AS REAL)), AVG(adx)
                FROM micro_trend_decisions
                WHERE DATE(timestamp) = ?
            """, (data_hoje,))
            row_dec = cur.fetchone()
            macro_score_medio = float(row_dec[0] or 0.0)
            adx_medio = float(row_dec[1] or 0.0)

            # Range do mercado no dia (max - min do preco)
            cur.execute("""
                SELECT MAX(price_current), MIN(price_current)
                FROM micro_trend_decisions
                WHERE DATE(timestamp) = ?
                  AND price_current IS NOT NULL
                  AND price_current > 0
            """, (data_hoje,))
            row_range = cur.fetchone()
            if row_range and row_range[0] and row_range[1]:
                market_range_pts = float(row_range[0]) - float(row_range[1])
            else:
                market_range_pts = 0.0

            # Numero de oportunidades detectadas no dia
            cur.execute("""
                SELECT COUNT(*)
                FROM micro_trend_opportunities
                WHERE DATE(timestamp) = ?
            """, (data_hoje,))
            n_oportunidades = int(cur.fetchone()[0] or 0)

            conn.close()

            if macro_score_medio == 0.0 and adx_medio == 0.0 and n_oportunidades == 0:
                return None

            return CondicoesInatividade(
                data=data_hoje,
                n_trades_executados=0,
                macro_score_medio=macro_score_medio,
                adx_medio=adx_medio,
                market_range_pts=market_range_pts,
                n_oportunidades_detectadas=n_oportunidades,
                n_oportunidades_executadas=0,
            )

        except Exception as exc:
            logger.warning("Falha ao coletar condicoes do dia: %s", exc)
            return None

    def gerar_episodios_hold_penalizados(self) -> list[EpisodioHoldPenalizado]:
        """Gera lista de episodios HOLD penalizados para oportunidades nao executadas.

        Para cada oportunidade detectada hoje que nao foi executada,
        estima o movimento real que ocorreu apos o timestamp da oportunidade
        e calcula a penalidade proporcional.

        Returns:
            Lista de EpisodioHoldPenalizado para persistir em rl_rewards.
        """
        data_hoje = datetime.now().date().isoformat()
        episodios: list[EpisodioHoldPenalizado] = []
        try:
            conn = sqlite3.connect(self.db_path)
            cur = conn.cursor()

            # Busca oportunidades nao executadas do dia
            cur.execute("""
                SELECT id, timestamp, direction, entry, take_profit
                FROM micro_trend_opportunities
                WHERE DATE(timestamp) = ?
                ORDER BY timestamp ASC
            """, (data_hoje,))
            oportunidades = cur.fetchall()

            for opp_row in oportunidades:
                opp_id = int(opp_row[0])
                ts_opp = str(opp_row[1])
                direction = str(opp_row[2])
                entry = float(opp_row[3] or 0.0)
                take_profit = float(opp_row[4] or 0.0)

                # Estima movimento apos o timestamp da oportunidade
                movimento_pts = self._estimar_movimento_pos_oportunidade(
                    cur=cur,
                    ts_oportunidade=ts_opp,
                    direction=direction,
                    preco_entrada=entry,
                    take_profit=take_profit,
                )

                if movimento_pts <= 0.0:
                    # Sem movimento mensuravel — pula (mercado nao confirmou)
                    continue

                penalidade = self._calcular_penalidade(movimento_pts)

                episodios.append(
                    EpisodioHoldPenalizado(
                        opportunity_id=opp_id,
                        timestamp=ts_opp,
                        direction=direction,
                        movimento_pts=movimento_pts,
                        penalidade_normalizada=penalidade,
                        was_correct=0,
                        action_at_decision="HOLD_FORCADO",
                    )
                )

            conn.close()

        except Exception as exc:
            logger.warning("Falha ao gerar episodios HOLD: %s", exc)

        return episodios

    def persistir_episodios(
        self, episodios: list[EpisodioHoldPenalizado]
    ) -> int:
        """Persiste episodios HOLD penalizados na tabela rl_rewards.

        Cada episodio e inserido com:
          - action_at_decision = "HOLD_FORCADO"
          - price_change_points = movimento_pts
          - was_correct = 0
          - reward_normalized = penalidade_normalizada
          - is_evaluated = 1
          - agent_id = "micro_tendencia"

        Args:
            episodios: Lista de episodios a persistir.

        Returns:
            int: Numero de episodios persistidos com sucesso.
        """
        if not episodios:
            return 0

        n_persistidos = 0
        try:
            conn = sqlite3.connect(self.db_path)
            cur = conn.cursor()

            for ep in episodios:
                episode_id = str(uuid.uuid4())
                cur.execute("""
                    INSERT INTO rl_rewards (
                        episode_id, action_at_decision, price_change_points,
                        was_correct, reward_normalized, is_evaluated,
                        timestamp, agent_id
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    episode_id,
                    ep.action_at_decision,
                    ep.movimento_pts,
                    ep.was_correct,
                    ep.penalidade_normalizada,
                    1,
                    ep.timestamp,
                    "micro_tendencia",
                ))
                n_persistidos += 1

            conn.commit()
            conn.close()

        except Exception as exc:
            logger.warning("Falha ao persistir episodios HOLD: %s", exc)

        return n_persistidos

    def gerar_relatorio_markdown(
        self, resultado: ResultadoAutoavaliacao
    ) -> str:
        """Gera relatorio Markdown estruturado da autoavaliacao.

        Estrutura do relatorio:
          - Cabecalho com data e status
          - Condicoes do mercado no dia (macro score, ADX, range)
          - Numero de oportunidades detectadas vs executadas
          - Movimento nao capturado estimado
          - Lista de episodios penalizados
          - Recomendacao

        Args:
            resultado: Resultado completo da autoavaliacao.

        Returns:
            str: Conteudo Markdown do relatorio.
        """
        c = resultado.condicoes
        linhas = [
            f"# Autoavaliacao de Inatividade — {resultado.data}",
            "",
            f"**Status:** {resultado.status.value}",
            f"**Data:** {resultado.data}",
            "",
            "## Condicoes do Mercado no Dia",
            "",
            f"| Metrica | Valor | Limiar | Status |",
            f"|---------|-------|--------|--------|",
            (
                f"| Macro Score Medio | {c.macro_score_medio:.1f} "
                f"| >= {LIMIAR_MACRO_SCORE:.0f} "
                f"| {'OK' if c.macro_score_medio >= LIMIAR_MACRO_SCORE else 'ABAIXO'} |"
            ),
            (
                f"| ADX Medio | {c.adx_medio:.1f} "
                f"| >= {LIMIAR_ADX:.0f} "
                f"| {'OK' if c.adx_medio >= LIMIAR_ADX else 'ABAIXO'} |"
            ),
            (
                f"| Range de Mercado | {c.market_range_pts:.0f} pts "
                f"| >= {LIMIAR_MARKET_RANGE_PTS:.0f} pts "
                f"| {'OK' if c.market_range_pts >= LIMIAR_MARKET_RANGE_PTS else 'ABAIXO'} |"
            ),
            "",
            "## Oportunidades do Dia",
            "",
            f"- **Detectadas:** {c.n_oportunidades_detectadas}",
            f"- **Executadas:** {c.n_oportunidades_executadas}",
            f"- **Nao executadas:** "
            f"{c.n_oportunidades_detectadas - c.n_oportunidades_executadas}",
            "",
            "## Movimento Nao Capturado",
            "",
            f"- **Total estimado:** {resultado.movimento_total_perdido_pts:.0f} pts",
            f"- **Penalidade total gerada:** -{resultado.penalidade_total:.2f} rewards",
            f"- **Episodios HOLD persistidos:** {len(resultado.episodios_penalizados)}",
            "",
        ]

        if resultado.episodios_penalizados:
            linhas += [
                "## Episodios HOLD Penalizados",
                "",
                "| # | Timestamp | Direcao | Movimento (pts) | Penalidade |",
                "|---|-----------|---------|-----------------|------------|",
            ]
            for i, ep in enumerate(resultado.episodios_penalizados, 1):
                ts_curto = ep.timestamp[:16] if len(ep.timestamp) > 16 else ep.timestamp
                linhas.append(
                    f"| {i} | {ts_curto} | {ep.direction} "
                    f"| {ep.movimento_pts:.0f} | {ep.penalidade_normalizada:.3f} |"
                )
            linhas.append("")

        linhas += [
            "## Recomendacao",
            "",
            f"> {resultado.recomendacao}",
            "",
        ]

        return "\n".join(linhas)

    def salvar_relatorio(
        self,
        conteudo: str,
        data: str,
        diretorio_outputs: str = "outputs",
    ) -> str:
        """Salva relatorio Markdown em outputs/micro_autoavaliacao_YYYYMMDD.md.

        Args:
            conteudo: Conteudo Markdown do relatorio.
            data: Data do relatorio (YYYY-MM-DD).
            diretorio_outputs: Diretorio de saida.

        Returns:
            str: Caminho completo do arquivo salvo.

        Raises:
            OSError: Se falhar ao criar diretorio ou escrever arquivo.
        """
        import os

        os.makedirs(diretorio_outputs, exist_ok=True)
        nome_arquivo = f"micro_autoavaliacao_{data}.md"
        caminho = os.path.join(diretorio_outputs, nome_arquivo)
        with open(caminho, "w", encoding="utf-8") as f:
            f.write(conteudo)
        return caminho

    # ──────────────────────────────────────────────────────────
    # Metodos auxiliares (internos)
    # ──────────────────────────────────────────────────────────

    def _e_inatividade_injusta(
        self, condicoes: CondicoesInatividade
    ) -> bool:
        """Verifica se as condicoes configuram inatividade injusta.

        Retorna True quando TODAS as condicoes sao verdadeiras:
          - n_trades_executados == 0
          - macro_score_medio >= LIMIAR_MACRO_SCORE (15)
          - adx_medio >= LIMIAR_ADX (30)
          - market_range_pts >= LIMIAR_MARKET_RANGE_PTS (500)

        Args:
            condicoes: Condicoes de mercado do dia.

        Returns:
            bool: True se inatividade injusta, False caso contrario.
        """
        if condicoes.n_trades_executados > 0:
            return False
        if condicoes.macro_score_medio < LIMIAR_MACRO_SCORE:
            return False
        if condicoes.adx_medio < LIMIAR_ADX:
            return False
        if condicoes.market_range_pts < LIMIAR_MARKET_RANGE_PTS:
            return False
        return True

    def _calcular_penalidade(self, movimento_pts: float) -> float:
        """Calcula penalidade normalizada para o movimento nao capturado.

        Formula: (movimento_pts / 100) * PENALIDADE_POR_100_PTS
        com teto em PENALIDADE_TETO para evitar penalidades extremas.

        Args:
            movimento_pts: Movimento do mercado nao capturado em pontos.

        Returns:
            float: Penalidade normalizada (<= 0.0).
        """
        if movimento_pts <= 0.0:
            return 0.0
        penalidade = (movimento_pts / 100.0) * PENALIDADE_POR_100_PTS
        # Aplica teto (PENALIDADE_TETO e negativo)
        return max(penalidade, PENALIDADE_TETO)

    def _estimar_movimento_pos_oportunidade(
        self,
        cur: sqlite3.Cursor,
        ts_oportunidade: str,
        direction: str,
        preco_entrada: float,
        take_profit: float,
    ) -> float:
        """Estima movimento real apos o timestamp da oportunidade.

        Consulta micro_trend_decisions para obter o preco maximo (COMPRA)
        ou minimo (VENDA) nos 30 minutos apos a oportunidade.

        Args:
            cur: Cursor SQLite ativo.
            ts_oportunidade: Timestamp ISO da oportunidade.
            direction: "COMPRA" ou "VENDA".
            preco_entrada: Preco de entrada sugerido.
            take_profit: Take profit sugerido (referencia).

        Returns:
            float: Movimento estimado em pontos (>= 0).
        """
        try:
            if direction == "COMPRA":
                cur.execute("""
                    SELECT MAX(price_current)
                    FROM micro_trend_decisions
                    WHERE timestamp > ?
                      AND datetime(timestamp) <= datetime(?, '+30 minutes')
                      AND price_current IS NOT NULL
                """, (ts_oportunidade, ts_oportunidade))
                row = cur.fetchone()
                if row and row[0] and preco_entrada > 0:
                    movimento = float(row[0]) - preco_entrada
                    return max(0.0, movimento)
            else:  # VENDA
                cur.execute("""
                    SELECT MIN(price_current)
                    FROM micro_trend_decisions
                    WHERE timestamp > ?
                      AND datetime(timestamp) <= datetime(?, '+30 minutes')
                      AND price_current IS NOT NULL
                """, (ts_oportunidade, ts_oportunidade))
                row = cur.fetchone()
                if row and row[0] and preco_entrada > 0:
                    movimento = preco_entrada - float(row[0])
                    return max(0.0, movimento)
        except Exception as exc:
            logger.debug("Falha ao estimar movimento: %s", exc)

        return 0.0
