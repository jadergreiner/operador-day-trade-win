"""
P1-LEARNING: Relatorio de Sessao

Gera relatorio Markdown legivel pelo operador com o resultado das
analises L1, L2 e das regras de aprendizado geradas na sessao.

Responsabilidades:
- Formatar ResultadoL1, ResultadoL2 e RegraAprendizado em Markdown
- Persistir outputs/p1_learning_report_YYYYMMDD_<sessao>.md
- Nao propagar excecoes (erros viram notas no relatorio)

Estrutura do relatorio:
    # Relatorio P1-LEARNING — YYYY-MM-DD
    ## Resumo da Sessao
    ## L1 — Analise de Decisoes
    ## L2 — Analise Causal
    ## Regras Geradas

Pipeline:
    Etapa 7 (Learning Rules) -> p1_learning_regras.py
    Relatorio               -> p1_learning_relatorio.py  [este modulo]
    Integracao              -> agente_rl_direto_independente.py

Status: Implementacao v1.0 (02/04/2026)
Referencia: docs/BACKLOG.md (P1-LEARNING Etapas 5-7)
"""

from __future__ import annotations

from datetime import datetime
from pathlib import Path

from src.application.p1_learning_l1_analysis import ResultadoL1
from src.application.p1_learning_l2_causal import ResultadoL2
from src.application.p1_learning_regras import RegraAprendizado


class RelatorioSessao:
    """Gera relatorio Markdown de encerramento de sessao P1-LEARNING.

    Consolida os resultados das Etapas 5, 6 e 7 em um documento
    legivel pelo operador.

    Exemplo:
        RelatorioSessao().gerar_relatorio_md(
            resultados_l1, resultado_l2, regras,
            output_dir=Path("outputs"),
        )
    """

    def gerar_relatorio_md(
        self,
        resultados_l1: list[ResultadoL1],
        resultado_l2: ResultadoL2,
        regras: list[RegraAprendizado],
        output_dir: Path,
    ) -> Path:
        """Gera e salva relatorio Markdown da sessao.

        Args:
            resultados_l1: Lista de ResultadoL1 da Etapa 5
            resultado_l2: ResultadoL2 da Etapa 6
            regras: Lista de RegraAprendizado da Etapa 7
            output_dir: Diretorio onde salvar o relatorio

        Returns:
            Path do arquivo .md criado
        """
        output_dir.mkdir(parents=True, exist_ok=True)

        data_str = datetime.now().strftime("%Y%m%d")
        sessao_slug = resultado_l2.sessao_id.replace(" ", "_")[:20]
        nome = f"p1_learning_report_{data_str}_{sessao_slug}.md"
        caminho = output_dir / nome

        conteudo = self._gerar_conteudo(resultados_l1, resultado_l2, regras)
        caminho.write_text(conteudo, encoding="utf-8")

        return caminho

    def _gerar_conteudo(
        self,
        resultados_l1: list[ResultadoL1],
        resultado_l2: ResultadoL2,
        regras: list[RegraAprendizado],
    ) -> str:
        """Monta o conteudo Markdown completo.

        Args:
            resultados_l1: Resultados L1
            resultado_l2: Resultado L2
            regras: Regras geradas

        Returns:
            String Markdown do relatorio
        """
        linhas: list[str] = []
        data_fmt = datetime.now().strftime("%Y-%m-%d %H:%M")

        linhas.append(f"# Relatorio P1-LEARNING — {data_fmt}")
        linhas.append("")
        linhas.append(f"**Sessao:** {resultado_l2.sessao_id}")
        linhas.append("")

        # Resumo
        linhas.extend(self._secao_resumo(resultados_l1, resultado_l2, regras))
        linhas.append("")

        # L1 — Analise de Decisoes
        linhas.extend(self._secao_l1(resultados_l1))
        linhas.append("")

        # L2 — Analise Causal
        linhas.extend(self._secao_l2(resultado_l2))
        linhas.append("")

        # Regras Geradas
        linhas.extend(self._secao_regras(regras))
        linhas.append("")

        return "\n".join(linhas)

    # -----------------------------------------------------------------------
    # SECOES
    # -----------------------------------------------------------------------

    def _secao_resumo(
        self,
        resultados_l1: list[ResultadoL1],
        resultado_l2: ResultadoL2,
        regras: list[RegraAprendizado],
    ) -> list[str]:
        """Monta secao de Resumo da Sessao."""
        n = len(resultados_l1)
        n_incorretos = sum(
            1 for r in resultados_l1 if r.corretude_decisao < 0.5
        )
        wr_pct = resultado_l2.win_rate_sessao * 100

        linhas = ["## Resumo da Sessao", ""]
        linhas.append(f"- **Episodios analisados:** {n}")
        linhas.append(f"- **Win Rate sessao:** {wr_pct:.1f}%")
        linhas.append(
            f"- **Decisoes questionaveis (L1 < 0.5):** {n_incorretos}"
        )
        linhas.append(
            f"- **Causa dominante:** {resultado_l2.causa_dominante} "
            f"(confianca: {resultado_l2.confianca:.0%})"
        )
        linhas.append(f"- **Regras geradas:** {len(regras)}")
        linhas.append(
            f"- **Drift de regime detectado:** "
            f"{'Sim' if resultado_l2.drift_detectado else 'Nao'}"
        )
        return linhas

    def _secao_l1(self, resultados_l1: list[ResultadoL1]) -> list[str]:
        """Monta secao L1 — Analise de Decisoes."""
        linhas = ["## L1 — Analise de Decisoes", ""]

        if not resultados_l1:
            linhas.append("_Nenhum episodio disponivel para analise._")
            return linhas

        # Tabela de episodios
        linhas.append(
            "| episode_id | outcome | corretude | motivo | diagnostico |"
        )
        linhas.append("|------------|---------|-----------|--------|-------------|")

        for r in resultados_l1:
            corr = f"{r.corretude_decisao:.2f}"
            diag = r.diagnostico[:60].replace("|", "/")
            linhas.append(
                f"| {r.episode_id[:12]} | {r.outcome} | {corr} "
                f"| {r.motivo_fechamento} | {diag} |"
            )

        # Sumario de incorretos
        incorretos = [r for r in resultados_l1 if r.corretude_decisao < 0.5]
        if incorretos:
            linhas.append("")
            linhas.append(
                f"> **{len(incorretos)} decisao(oes) abaixo do limiar 0.5** "
                "— candidatas a regras de aprendizado."
            )

        return linhas

    def _secao_l2(self, resultado_l2: ResultadoL2) -> list[str]:
        """Monta secao L2 — Analise Causal."""
        linhas = ["## L2 — Analise Causal", ""]

        linhas.append(
            f"- **Drift detectado:** "
            f"{'Sim' if resultado_l2.drift_detectado else 'Nao'}"
        )
        linhas.append(
            f"- **Win rate sessao:** "
            f"{resultado_l2.win_rate_sessao:.1%}"
        )
        linhas.append(
            f"- **Sharpe sessao:** {resultado_l2.sharpe_sessao:.2f}"
        )
        linhas.append(
            f"- **Causa dominante:** {resultado_l2.causa_dominante}"
        )
        linhas.append(
            f"- **Confianca classificacao:** {resultado_l2.confianca:.0%}"
        )

        if resultado_l2.alertas_drift:
            linhas.append("")
            linhas.append("### Alertas de Drift")
            for alerta in resultado_l2.alertas_drift:
                metrica = alerta.get("metric", "?")
                severidade = alerta.get("severity", "?")
                mensagem = alerta.get("message", "")
                linhas.append(f"- **[{severidade}]** {metrica}: {mensagem}")

        return linhas

    def _secao_regras(self, regras: list[RegraAprendizado]) -> list[str]:
        """Monta secao de Regras Geradas."""
        linhas = [f"## Regras Geradas ({len(regras)})", ""]

        if not regras:
            linhas.append(
                "_Nenhuma regra gerada. "
                "Performance dentro do esperado para a sessao._"
            )
            return linhas

        for i, regra in enumerate(regras, start=1):
            confianca_pct = f"{regra.confianca:.0%}"
            linhas.append(
                f"### {i}. [{regra.fonte}] confianca: {confianca_pct}"
            )
            linhas.append("")
            linhas.append(f"**Contexto:** {regra.contexto}")
            linhas.append("")
            linhas.append(f"**Evitar:** {regra.acao_evitar}")
            linhas.append("")
            linhas.append(
                f"_Frequencia: {regra.frequencia} vez(es) | "
                f"ID: {regra.regra_id[:8]}..._"
            )
            linhas.append("")

        return linhas
