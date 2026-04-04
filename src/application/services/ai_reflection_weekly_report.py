"""Relatorio semanal de AI Reflection (BLID-023 / ROADMAP-DIARIOS-03).

Gera um relatorio Markdown consolidando reflexoes, perguntas e padroes
detectados ao longo da semana.

Banco alvo: data/db/trading_diarios.db (magic_number=234800, ADR-019).
"""
from __future__ import annotations

from collections import Counter
from pathlib import Path

from src.application.services.ai_reflection_persistence_service import (
    AIReflectionPersistenceService,
)


_PROMPT_MAX_LEN = 60  # comprimento maximo do prompt na tabela Markdown


class AIReflectionWeeklyReport:
    """Gerador de relatorio semanal de AI Reflection.

    Args:
        db_path: Caminho para o arquivo SQLite do banco de dados.
        output_dir: Diretorio onde os relatorios serao salvos.
    """

    def __init__(self, db_path: Path, output_dir: Path) -> None:
        self._servico = AIReflectionPersistenceService(db_path)
        self._output_dir = output_dir

    def gerar_relatorio(self, numero_semana: int) -> Path:
        """Gera o relatorio semanal de AI Reflection.

        Le dados das ultimas 7 reflexoes, perguntas e padroes detectados,
        consolida em um relatorio Markdown e salva em disco.

        Args:
            numero_semana: Numero identificador da semana (ex: 1, 42).

        Returns:
            Path do arquivo Markdown gerado.
        """
        reflexoes = self._servico.listar_reflexoes_recentes(dias=7)
        perguntas = self._servico.listar_perguntas_ativas()
        padroes = self._servico.detectar_padroes_recorrentes(janela_dias=7)

        total_reflexoes = len(reflexoes)

        # Humor predominante
        if reflexoes:
            contagem_mood = Counter(r["mood"] for r in reflexoes)
            humor_predominante = contagem_mood.most_common(1)[0][0]
        else:
            humor_predominante = "N/A"

        # Decisao mais frequente
        if reflexoes:
            contagem_decisao = Counter(r["my_decision"] for r in reflexoes)
            decisao_frequente = contagem_decisao.most_common(1)[0][0]
        else:
            decisao_frequente = "N/A"

        # Perguntas ordenadas por score (mais relevantes primeiro)
        perguntas_ordenadas = sorted(
            perguntas,
            key=lambda p: float(p.get("score_relevancia", 0.0)),
            reverse=True,
        )
        mais_relevantes = perguntas_ordenadas[:5]
        menos_relevantes = sorted(
            perguntas,
            key=lambda p: float(p.get("score_relevancia", 0.0)),
        )[:5]

        # Acoes sugeridas com base em padroes
        acoes_sugeridas: list[str] = []
        for padrao in padroes:
            if "FRUSTRADO" in padrao:
                acoes_sugeridas.append(
                    "Revisar criterios de entrada — multiplas sessoes com frustracao detectadas."
                )
            if "HOLD_TOTAL" in padrao:
                acoes_sugeridas.append(
                    "Avaliar se filtros de entrada estao muito restritivos (todas decisoes foram HOLD)."
                )
            if "DADOS_IRRELEVANTES" in padrao:
                acoes_sugeridas.append(
                    "Revisar fontes de dados — baixa correlacao com movimentos de preco detectada."
                )

        if not acoes_sugeridas:
            acoes_sugeridas.append("Nenhuma acao critica identificada. Manter monitoramento.")

        # ---------------------------------------------------------------
        # Construir conteudo Markdown
        # ---------------------------------------------------------------
        numero_formatado = f"{numero_semana:02d}"
        linhas: list[str] = [
            f"# AI Reflection — Semana {numero_formatado}",
            "",
            "## Resumo da Semana",
            f"- Total de reflexoes: {total_reflexoes}",
            f"- Humor predominante: {humor_predominante}",
            f"- Decisao mais frequente: {decisao_frequente}",
            "",
            "## Perguntas Mais Relevantes",
            "| Pergunta | Score | Categoria |",
            "|----------|-------|-----------|",
        ]
        for p in mais_relevantes:
            texto_prompt = str(p.get("prompt", ""))
            prompt = (
                texto_prompt[:_PROMPT_MAX_LEN - 3] + "..."
                if len(texto_prompt) > _PROMPT_MAX_LEN
                else texto_prompt
            )
            score = f"{float(p.get('score_relevancia', 0.0)):.2f}"
            categoria = str(p.get("category", ""))
            linhas.append(f"| {prompt} | {score} | {categoria} |")

        if not mais_relevantes:
            linhas.append("| Sem perguntas registradas | - | - |")

        linhas += [
            "",
            "## Perguntas Menos Relevantes (candidatas a obsolescencia)",
            "| Pergunta | Score | Categoria |",
            "|----------|-------|-----------|",
        ]
        for p in menos_relevantes:
            texto_prompt = str(p.get("prompt", ""))
            prompt = (
                texto_prompt[:_PROMPT_MAX_LEN - 3] + "..."
                if len(texto_prompt) > _PROMPT_MAX_LEN
                else texto_prompt
            )
            score = f"{float(p.get('score_relevancia', 0.0)):.2f}"
            categoria = str(p.get("category", ""))
            linhas.append(f"| {prompt} | {score} | {categoria} |")

        if not menos_relevantes:
            linhas.append("| Sem perguntas registradas | - | - |")

        linhas += [
            "",
            "## Padroes Detectados",
        ]
        if padroes:
            for padrao in padroes:
                linhas.append(f"- {padrao}")
        else:
            linhas.append("- Nenhum padrao recorrente detectado.")

        linhas += [
            "",
            "## Acoes Sugeridas",
        ]
        for acao in acoes_sugeridas:
            linhas.append(f"- {acao}")

        conteudo = "\n".join(linhas) + "\n"

        # ---------------------------------------------------------------
        # Salvar arquivo
        # ---------------------------------------------------------------
        self._output_dir.mkdir(parents=True, exist_ok=True)
        nome_arquivo = f"ai_reflection_semana_{numero_formatado}.md"
        caminho_saida = self._output_dir / nome_arquivo
        caminho_saida.write_text(conteudo, encoding="utf-8")

        return caminho_saida
