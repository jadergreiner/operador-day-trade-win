"""Consolidador de Fechamento de Pipeline dos Diarios.

BLID-027 / ROADMAP-DIARIOS-07
Executor: INICIAR_DIARIOS.bat

Agrega as saidas dos 5 servicos de diarios (BLID-022 a 026) num unico
relatorio de fechamento de pregao, oferecendo visibilidade operacional
consolidada ao operador.

Pipeline:
    consolidar_fechamento_pregao(data, db_path)
    -> leitura de metricas por secao (Journal, AI Reflection, RL Diary,
       Macro Guardian, Order Manager)
    -> retorna dict consolidado com todas as metricas

    gerar_relatorio_markdown(data, db_path)
    -> chama consolidar_fechamento_pregao
    -> serializa em Markdown estruturado
    -> persiste em outputs/diarios/fechamento_diario_YYYYMMDD.md

    obter_resumo_estatisticas(data, db_path)
    -> subconjunto de metricas numericas para dashboards

Banco alvo: data/db/trading_diarios.db (ADR-019, magic_number=234800).
"""
from __future__ import annotations

import logging
import sqlite3
from datetime import date, datetime
from pathlib import Path
from typing import Any, Optional

logger = logging.getLogger("pipeline_diarios_consolidator")

# ---------------------------------------------------------------------------
# Constantes
# ---------------------------------------------------------------------------

_MAGIC_NUMBER_DIARIOS: int = 234800
_SQLITE_TIMEOUT: int = 30
_TABELAS_OBRIGATORIAS: tuple[str, ...] = (
    "trading_journal_logs",
    "journal_trade_correlation",
    "ai_reflection_logs",
    "reflection_questions",
    "diary_feedback",
)


# ---------------------------------------------------------------------------
# Helpers internos de conexao
# ---------------------------------------------------------------------------


def _conectar(db_path: Path) -> sqlite3.Connection:
    """Abre conexao SQLite com PRAGMAs otimizados para WAL.

    Args:
        db_path: Caminho para o arquivo SQLite.

    Returns:
        Conexao configurada com timeout=30, WAL e busy_timeout=30000.
    """
    conn = sqlite3.connect(str(db_path), timeout=_SQLITE_TIMEOUT)
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA synchronous=NORMAL")
    conn.execute("PRAGMA busy_timeout=30000")
    conn.row_factory = sqlite3.Row
    return conn


def _tabela_existe(conn: sqlite3.Connection, nome: str) -> bool:
    """Verifica se uma tabela existe no banco conectado.

    Args:
        conn: Conexao SQLite ativa.
        nome: Nome da tabela.

    Returns:
        True se a tabela existir, False caso contrario.
    """
    row = conn.execute(
        "SELECT 1 FROM sqlite_master WHERE type='table' AND name=?",
        (nome,),
    ).fetchone()
    return row is not None


# ---------------------------------------------------------------------------
# Secao 1 — Journal Correlacoes
# ---------------------------------------------------------------------------


def _coletar_metricas_journal(
    conn: sqlite3.Connection,
    data: str,
) -> dict[str, Any]:
    """Coleta metricas de trading_journal_logs e journal_trade_correlation.

    Args:
        conn: Conexao SQLite.
        data: Data no formato YYYY-MM-DD.

    Returns:
        Dicionario com metricas do journal da data informada.
    """
    metricas: dict[str, Any] = {
        "total_entradas": 0,
        "total_correlacoes": 0,
        "win": 0,
        "loss": 0,
        "breakeven": 0,
        "sem_trade": 0,
        "win_rate": 0.0,
        "pnl_total": 0.0,
        "narrativas_alinhadas": 0,
    }

    if not _tabela_existe(conn, "trading_journal_logs"):
        return metricas

    # Total de entradas do dia
    row_entradas = conn.execute(
        "SELECT COUNT(*) FROM trading_journal_logs WHERE DATE(timestamp) = ?",
        (data,),
    ).fetchone()
    metricas["total_entradas"] = row_entradas[0] if row_entradas else 0

    if not _tabela_existe(conn, "journal_trade_correlation"):
        return metricas

    # Correlacoes do dia
    rows_corr = conn.execute(
        """
        SELECT c.outcome, c.pnl_reais, c.narrativa_estava_alinhada
        FROM journal_trade_correlation c
        JOIN trading_journal_logs j ON j.entry_id = c.journal_entry_id
        WHERE DATE(j.timestamp) = ?
        """,
        (data,),
    ).fetchall()

    metricas["total_correlacoes"] = len(rows_corr)
    contagem_com_trade = 0
    soma_pnl = 0.0
    alinhadas = 0

    for row in rows_corr:
        outcome = row["outcome"]
        if outcome == "WIN":
            metricas["win"] += 1
        elif outcome == "LOSS":
            metricas["loss"] += 1
        elif outcome == "BREAKEVEN":
            metricas["breakeven"] += 1
        else:
            metricas["sem_trade"] += 1

        if outcome != "SEM_TRADE":
            contagem_com_trade += 1
            soma_pnl += float(row["pnl_reais"] or 0.0)

        if row["narrativa_estava_alinhada"] == 1:
            alinhadas += 1

    metricas["pnl_total"] = round(soma_pnl, 2)
    metricas["narrativas_alinhadas"] = alinhadas
    if contagem_com_trade > 0:
        metricas["win_rate"] = round(metricas["win"] / contagem_com_trade, 4)

    return metricas


# ---------------------------------------------------------------------------
# Secao 2 — AI Reflection
# ---------------------------------------------------------------------------


def _coletar_metricas_ai_reflection(
    conn: sqlite3.Connection,
    data: str,
) -> dict[str, Any]:
    """Coleta metricas de ai_reflection_logs e reflection_questions.

    Args:
        conn: Conexao SQLite.
        data: Data no formato YYYY-MM-DD.

    Returns:
        Dicionario com metricas de reflexao da IA para a data.
    """
    metricas: dict[str, Any] = {
        "total_reflexoes": 0,
        "confianca_media": 0.0,
        "alinhamento_medio": 0.0,
        "moods": {},
        "decisoes": {},
        "perguntas_ativas": 0,
        "perguntas_obsoletas": 0,
    }

    if not _tabela_existe(conn, "ai_reflection_logs"):
        return metricas

    rows = conn.execute(
        """
        SELECT mood, my_decision, my_confidence, my_alignment
        FROM ai_reflection_logs
        WHERE DATE(timestamp) = ?
        """,
        (data,),
    ).fetchall()

    metricas["total_reflexoes"] = len(rows)
    if rows:
        soma_conf = sum(float(r["my_confidence"] or 0.0) for r in rows)
        soma_ali = sum(float(r["my_alignment"] or 0.0) for r in rows)
        metricas["confianca_media"] = round(soma_conf / len(rows), 4)
        metricas["alinhamento_medio"] = round(soma_ali / len(rows), 4)

        moods: dict[str, int] = {}
        decisoes: dict[str, int] = {}
        for r in rows:
            mood = str(r["mood"] or "DESCONHECIDO")
            decisao = str(r["my_decision"] or "DESCONHECIDA")
            moods[mood] = moods.get(mood, 0) + 1
            decisoes[decisao] = decisoes.get(decisao, 0) + 1
        metricas["moods"] = moods
        metricas["decisoes"] = decisoes

    if _tabela_existe(conn, "reflection_questions"):
        row_ativas = conn.execute(
            "SELECT COUNT(*) FROM reflection_questions WHERE ativa=1 AND obsoleta=0"
        ).fetchone()
        row_obsoletas = conn.execute(
            "SELECT COUNT(*) FROM reflection_questions WHERE obsoleta=1"
        ).fetchone()
        metricas["perguntas_ativas"] = row_ativas[0] if row_ativas else 0
        metricas["perguntas_obsoletas"] = row_obsoletas[0] if row_obsoletas else 0

    return metricas


# ---------------------------------------------------------------------------
# Secao 3 — RL Diary
# ---------------------------------------------------------------------------


def _coletar_metricas_rl_diary(
    conn: sqlite3.Connection,
    data: str,
) -> dict[str, Any]:
    """Coleta metricas de diary_feedback com source='rl_diary'.

    Args:
        conn: Conexao SQLite.
        data: Data no formato YYYY-MM-DD.

    Returns:
        Dicionario com metricas de aprendizado RL para a data.
    """
    metricas: dict[str, Any] = {
        "ciclos_registrados": 0,
        "nota_media": 0.0,
        "market_range_pts": 0.0,
        "eficiencia_pct": 0.0,
        "n_episodes": 0,
        "retreinamentos": 0,
    }

    if not _tabela_existe(conn, "diary_feedback"):
        return metricas

    rows = conn.execute(
        """
        SELECT nota_agente, market_range_pts, eficiencia_pct,
               n_episodes, retreinamento_necessario
        FROM diary_feedback
        WHERE source = 'rl_diary' AND date = ?
        """,
        (data,),
    ).fetchall()

    metricas["ciclos_registrados"] = len(rows)
    if rows:
        notas = [float(r["nota_agente"] or 0.0) for r in rows]
        metricas["nota_media"] = round(sum(notas) / len(notas), 2)

        ultimo = rows[-1]
        metricas["market_range_pts"] = float(
            ultimo["market_range_pts"] or 0.0
        )
        metricas["eficiencia_pct"] = float(
            ultimo["eficiencia_pct"] or 0.0
        )
        metricas["n_episodes"] = int(ultimo["n_episodes"] or 0)
        metricas["retreinamentos"] = sum(
            1 for r in rows if r["retreinamento_necessario"]
        )

    return metricas


# ---------------------------------------------------------------------------
# Secao 4 — Macro Guardian
# ---------------------------------------------------------------------------


def _coletar_metricas_macro_guardian(
    conn: sqlite3.Connection,
    data: str,
) -> dict[str, Any]:
    """Coleta metricas do Macro Guardian para a data de pregao.

    Usa a tabela macro_guardian_log se disponivel. Retorna metricas
    vazias graciosamente se a tabela nao existir.

    Args:
        conn: Conexao SQLite.
        data: Data no formato YYYY-MM-DD.

    Returns:
        Dicionario com metricas macro para a data.
    """
    metricas: dict[str, Any] = {
        "total_eventos": 0,
        "alertas_warning": 0,
        "alertas_critical": 0,
        "kill_switch_ativo": False,
        "regime_macro": "N/A",
        "score_medio": 0.0,
    }

    # Tentar ler de tabelas macro disponiveis
    for tabela in ("macro_guardian_log", "macro_guardian_events"):
        if _tabela_existe(conn, tabela):
            try:
                rows = conn.execute(
                    f"""
                    SELECT nivel, score_impacto, kill_switch_ativo, regime_macro
                    FROM {tabela}
                    WHERE DATE(timestamp) = ?
                    """,
                    (data,),
                ).fetchall()

                metricas["total_eventos"] = len(rows)
                if rows:
                    metricas["alertas_warning"] = sum(
                        1 for r in rows if str(r["nivel"] or "").upper() == "WARNING"
                    )
                    metricas["alertas_critical"] = sum(
                        1 for r in rows if str(r["nivel"] or "").upper() == "CRITICAL"
                    )
                    kill_ativo = any(r["kill_switch_ativo"] for r in rows)
                    metricas["kill_switch_ativo"] = bool(kill_ativo)

                    regimes = [str(r["regime_macro"] or "") for r in rows if r["regime_macro"]]
                    if regimes:
                        metricas["regime_macro"] = regimes[-1]

                    scores = [float(r["score_impacto"] or 0.0) for r in rows]
                    if scores:
                        metricas["score_medio"] = round(
                            sum(scores) / len(scores), 4
                        )
            except sqlite3.OperationalError as exc:
                logger.debug("Erro ao ler tabela %s: %s", tabela, exc)
            break

    return metricas


# ---------------------------------------------------------------------------
# Secao 5 — Order Manager Regime
# ---------------------------------------------------------------------------


def _coletar_metricas_order_manager(
    conn: sqlite3.Connection,
    data: str,
) -> dict[str, Any]:
    """Coleta metricas do Order Manager para a data de pregao.

    Usa diary_feedback com source='order_manager' e a tabela
    diario_episodios quando disponivel.

    Args:
        conn: Conexao SQLite.
        data: Data no formato YYYY-MM-DD.

    Returns:
        Dicionario com metricas de gestao de ordens para a data.
    """
    metricas: dict[str, Any] = {
        "n_episodios": 0,
        "win_rate": 0.0,
        "eficiencia_media": 0.0,
        "vies_detectado": False,
        "retreinamentos_acionados": 0,
    }

    if _tabela_existe(conn, "diario_episodios"):
        try:
            rows_ep = conn.execute(
                """
                SELECT foi_acerto, eficiencia
                FROM diario_episodios
                WHERE DATE(timestamp_entrada) = ?
                """,
                (data,),
            ).fetchall()

            metricas["n_episodios"] = len(rows_ep)
            if rows_ep:
                n_acertos = sum(1 for r in rows_ep if r["foi_acerto"])
                metricas["win_rate"] = round(n_acertos / len(rows_ep), 4)
                efi = [float(r["eficiencia"] or 0.0) for r in rows_ep]
                metricas["eficiencia_media"] = round(
                    sum(efi) / len(efi), 4
                )
        except sqlite3.OperationalError as exc:
            logger.debug("Erro ao ler diario_episodios: %s", exc)

    if _tabela_existe(conn, "diary_feedback"):
        try:
            rows_fb = conn.execute(
                """
                SELECT acao_sugerida, retreinamento_necessario
                FROM diary_feedback
                WHERE source = 'order_manager' AND date = ?
                """,
                (data,),
            ).fetchall()

            metricas["retreinamentos_acionados"] = sum(
                1 for r in rows_fb if r["retreinamento_necessario"]
            )
            metricas["vies_detectado"] = any(
                "vies" in str(r["acao_sugerida"] or "").lower()
                for r in rows_fb
            )
        except sqlite3.OperationalError as exc:
            logger.debug("Erro ao ler diary_feedback order_manager: %s", exc)

    return metricas


# ---------------------------------------------------------------------------
# Classe principal
# ---------------------------------------------------------------------------


class PipelineDiariosConsolidator:
    """Consolida o fechamento do pipeline de diarios do pregao.

    Agrega metricas dos 5 servicos de diarios (BLID-022 a 026) num unico
    relatorio estruturado. Todas as leituras sao somente-leitura (SELECT),
    sem modificar os bancos de origem.

    Banco alvo: data/db/trading_diarios.db (ADR-019, magic_number=234800).
    """

    # ------------------------------------------------------------------
    # Interface publica principal
    # ------------------------------------------------------------------

    def consolidar_fechamento_pregao(
        self,
        data: str,
        db_path: Path,
    ) -> dict[str, Any]:
        """Agrega dados dos 5 diarios para uma data de pregao.

        Realiza leituras somente-leitura em cada secao (journal, ai_reflection,
        rl_diary, macro_guardian, order_manager) e retorna o resultado
        consolidado como dicionario estruturado.

        Args:
            data: Data no formato YYYY-MM-DD.
            db_path: Caminho para o banco SQLite (data/db/trading_diarios.db).

        Returns:
            Dicionario com secoes: journal, ai_reflection, rl_diary,
            macro_guardian, order_manager, resumo.

        Raises:
            FileNotFoundError: Se db_path nao existir.
        """
        if not db_path.exists():
            raise FileNotFoundError(
                f"Banco nao encontrado: {db_path}"
            )

        conn = _conectar(db_path)
        try:
            journal = _coletar_metricas_journal(conn, data)
            ai_reflection = _coletar_metricas_ai_reflection(conn, data)
            rl_diary = _coletar_metricas_rl_diary(conn, data)
            macro_guardian = _coletar_metricas_macro_guardian(conn, data)
            order_manager = _coletar_metricas_order_manager(conn, data)
        finally:
            conn.close()

        resumo = self._calcular_resumo(
            journal, ai_reflection, rl_diary, macro_guardian, order_manager
        )

        return {
            "data": data,
            "gerado_em": datetime.now().isoformat(),
            "journal": journal,
            "ai_reflection": ai_reflection,
            "rl_diary": rl_diary,
            "macro_guardian": macro_guardian,
            "order_manager": order_manager,
            "resumo": resumo,
        }

    def gerar_relatorio_markdown(
        self,
        data: str,
        db_path: Path,
        diretorio_saida: Optional[Path] = None,
    ) -> Path:
        """Gera relatorio de fechamento do pregao em Markdown.

        Consolida os dados via consolidar_fechamento_pregao() e serializa
        o resultado em um arquivo Markdown estruturado.

        Args:
            data: Data no formato YYYY-MM-DD.
            db_path: Caminho para o banco SQLite.
            diretorio_saida: Diretorio de saida (padrao: outputs/diarios).

        Returns:
            Path do arquivo .md gerado.
        """
        if diretorio_saida is None:
            diretorio_saida = Path("outputs") / "diarios"

        diretorio_saida.mkdir(parents=True, exist_ok=True)

        dados = self.consolidar_fechamento_pregao(data, db_path)
        data_fmt = data.replace("-", "")
        arquivo_saida = diretorio_saida / f"fechamento_diario_{data_fmt}.md"

        conteudo = self._serializar_markdown(dados)
        arquivo_saida.write_text(conteudo, encoding="utf-8")

        logger.info("Relatorio de fechamento gerado: %s", arquivo_saida)
        return arquivo_saida

    def obter_resumo_estatisticas(
        self,
        data: str,
        db_path: Path,
    ) -> dict[str, Any]:
        """Retorna metricas consolidadas numericas para dashboards.

        Subconjunto das metricas de consolidar_fechamento_pregao(),
        focado em indicadores quantitativos de facil consumo.

        Args:
            data: Data no formato YYYY-MM-DD.
            db_path: Caminho para o banco SQLite.

        Returns:
            Dicionario com metricas numericas consolidadas.
        """
        dados = self.consolidar_fechamento_pregao(data, db_path)
        resumo: dict[str, Any] = dados["resumo"]
        return resumo

    # ------------------------------------------------------------------
    # Metodos privados — calculo e serializacao
    # ------------------------------------------------------------------

    def _calcular_resumo(
        self,
        journal: dict[str, Any],
        ai_reflection: dict[str, Any],
        rl_diary: dict[str, Any],
        macro_guardian: dict[str, Any],
        order_manager: dict[str, Any],
    ) -> dict[str, Any]:
        """Calcula metricas resumidas de todas as secoes.

        Args:
            journal: Metricas do journal de correlacoes.
            ai_reflection: Metricas de reflexao da IA.
            rl_diary: Metricas do diario RL.
            macro_guardian: Metricas do guardian macro.
            order_manager: Metricas do gestor de ordens.

        Returns:
            Dicionario com metricas numericas consolidadas.
        """
        total_trades = (
            journal["win"] + journal["loss"] + journal["breakeven"]
        )

        return {
            "total_entradas_journal": journal["total_entradas"],
            "total_trades_correlacionados": total_trades,
            "win_rate_journal": journal["win_rate"],
            "pnl_total_reais": journal["pnl_total"],
            "narrativas_alinhadas": journal["narrativas_alinhadas"],
            "total_reflexoes_ia": ai_reflection["total_reflexoes"],
            "confianca_media_ia": ai_reflection["confianca_media"],
            "alinhamento_medio_ia": ai_reflection["alinhamento_medio"],
            "ciclos_rl_registrados": rl_diary["ciclos_registrados"],
            "nota_media_rl": rl_diary["nota_media"],
            "eficiencia_rl_pct": rl_diary["eficiencia_pct"],
            "alertas_macro_warning": macro_guardian["alertas_warning"],
            "alertas_macro_critical": macro_guardian["alertas_critical"],
            "kill_switch_ativo": macro_guardian["kill_switch_ativo"],
            "n_episodios_order_manager": order_manager["n_episodios"],
            "win_rate_order_manager": order_manager["win_rate"],
            "vies_detectado": order_manager["vies_detectado"],
        }

    def _serializar_markdown(self, dados: dict[str, Any]) -> str:
        """Serializa o dicionario consolidado em Markdown estruturado.

        Args:
            dados: Resultado de consolidar_fechamento_pregao().

        Returns:
            String com conteudo Markdown do relatorio.
        """
        data = dados["data"]
        gerado_em = dados["gerado_em"]
        journal = dados["journal"]
        ai_ref = dados["ai_reflection"]
        rl = dados["rl_diary"]
        macro = dados["macro_guardian"]
        ordem = dados["order_manager"]
        resumo = dados["resumo"]

        linhas: list[str] = [
            f"# Fechamento Diario do Pipeline de Diarios — {data}",
            f"",
            f"> Gerado em: {gerado_em}",
            f"",
            "---",
            "",
            "## Resumo Executivo",
            "",
            f"| Metrica | Valor |",
            f"|---------|-------|",
            f"| Total entradas journal | {resumo['total_entradas_journal']} |",
            f"| Trades correlacionados | {resumo['total_trades_correlacionados']} |",
            f"| Win rate journal | {resumo['win_rate_journal']:.1%} |",
            f"| P&L total (R$) | {resumo['pnl_total_reais']:.2f} |",
            f"| Narrativas alinhadas | {resumo['narrativas_alinhadas']} |",
            f"| Reflexoes IA | {resumo['total_reflexoes_ia']} |",
            f"| Confianca media IA | {resumo['confianca_media_ia']:.2f} |",
            f"| Ciclos RL registrados | {resumo['ciclos_rl_registrados']} |",
            f"| Nota media RL | {resumo['nota_media_rl']:.1f} |",
            f"| Alertas macro (WARNING) | {resumo['alertas_macro_warning']} |",
            f"| Alertas macro (CRITICAL) | {resumo['alertas_macro_critical']} |",
            f"| Kill switch ativo | {'SIM' if resumo['kill_switch_ativo'] else 'NAO'} |",
            f"| Episodios order manager | {resumo['n_episodios_order_manager']} |",
            f"| Vies direcional detectado | {'SIM' if resumo['vies_detectado'] else 'NAO'} |",
            "",
            "---",
            "",
            "## 1. Journal Correlacoes",
            "",
            f"- **Entradas registradas:** {journal['total_entradas']}",
            f"- **Correlacoes processadas:** {journal['total_correlacoes']}",
            f"- **WIN:** {journal['win']}",
            f"- **LOSS:** {journal['loss']}",
            f"- **BREAKEVEN:** {journal['breakeven']}",
            f"- **SEM_TRADE:** {journal['sem_trade']}",
            f"- **Win Rate:** {journal['win_rate']:.1%}",
            f"- **P&L Total:** R$ {journal['pnl_total']:.2f}",
            f"- **Narrativas alinhadas:** {journal['narrativas_alinhadas']}",
            "",
            "---",
            "",
            "## 2. AI Reflection",
            "",
            f"- **Reflexoes registradas:** {ai_ref['total_reflexoes']}",
            f"- **Confianca media:** {ai_ref['confianca_media']:.4f}",
            f"- **Alinhamento medio:** {ai_ref['alinhamento_medio']:.4f}",
            f"- **Perguntas ativas:** {ai_ref['perguntas_ativas']}",
            f"- **Perguntas obsoletas:** {ai_ref['perguntas_obsoletas']}",
        ]

        if ai_ref["moods"]:
            linhas.append("- **Distribuicao de moods:**")
            for mood, qtd in sorted(ai_ref["moods"].items()):
                linhas.append(f"  - {mood}: {qtd}")

        if ai_ref["decisoes"]:
            linhas.append("- **Distribuicao de decisoes:**")
            for decisao, qtd in sorted(ai_ref["decisoes"].items()):
                linhas.append(f"  - {decisao}: {qtd}")

        linhas += [
            "",
            "---",
            "",
            "## 3. RL Diary",
            "",
            f"- **Ciclos registrados:** {rl['ciclos_registrados']}",
            f"- **Nota media do agente:** {rl['nota_media']:.1f}",
            f"- **Range de mercado (pts):** {rl['market_range_pts']:.1f}",
            f"- **Eficiencia (%):** {rl['eficiencia_pct']:.2f}",
            f"- **Episodios:** {rl['n_episodes']}",
            f"- **Retreinamentos acionados:** {rl['retreinamentos']}",
            "",
            "---",
            "",
            "## 4. Macro Guardian",
            "",
            f"- **Total de eventos:** {macro['total_eventos']}",
            f"- **Alertas WARNING:** {macro['alertas_warning']}",
            f"- **Alertas CRITICAL:** {macro['alertas_critical']}",
            f"- **Kill switch ativo:** {'SIM' if macro['kill_switch_ativo'] else 'NAO'}",
            f"- **Regime macro:** {macro['regime_macro']}",
            f"- **Score medio:** {macro['score_medio']:.4f}",
            "",
            "---",
            "",
            "## 5. Order Manager Regime",
            "",
            f"- **Episodios do dia:** {ordem['n_episodios']}",
            f"- **Win Rate:** {ordem['win_rate']:.1%}",
            f"- **Eficiencia media:** {ordem['eficiencia_media']:.4f}",
            f"- **Vies direcional detectado:** {'SIM' if ordem['vies_detectado'] else 'NAO'}",
            f"- **Retreinamentos acionados:** {ordem['retreinamentos_acionados']}",
            "",
            "---",
            "",
            f"*Relatorio gerado pelo PipelineDiariosConsolidator (BLID-027)*",
        ]

        return "\n".join(linhas) + "\n"
