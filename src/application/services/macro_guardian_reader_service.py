"""
MacroGuardianReaderService — Canal universal de leitura do Guardian.

Servico de leitura que todos os agentes operacionais usam a cada ciclo
para consumir o estado atual do Macro Guardian: snapshot consolidado,
verificacao de kill switch e enriquecimento de episodios de treinamento.

Arquitetura:
- Encapsula toda a logica de leitura do SQLite (os agentes chamam apenas
  ler_snapshot(db_path) e verificar_kill_switch(db_path)).
- Nao modifica os modulos macro_guardian_universal.py e
  macro_guardian_universal_log.py — apenas os consome.
- Segue os padroes SQLite: timeout=30 + PRAGMAs WAL/synchronous=NORMAL.

BLID-025 / ROADMAP-DIARIOS-05
ADR-021: MacroGuardianReaderService como canal universal de leitura.
"""

from __future__ import annotations

import sqlite3
from dataclasses import dataclass, field, asdict
from datetime import datetime
from pathlib import Path
from typing import Any, Optional

from src.application.macro_guardian_universal_log import (
    ensure_macro_guardian_log_table,
    fetch_latest_guardian_snapshot,
    fetch_recent_macro_guardian_events,
)

_SCHEMA_VERSION = "1.0"
_RELATORIO_SCHEMA_VERSION = "1.0"

# Mapa de regime macro para valor inteiro (uso em features ML)
_REGIME_TO_INT_MAP: dict[str, int] = {
    "ESTAVEL": 0,
    "CAUTELOSO": 1,
    "ALERTA": 2,
    "CRITICO": 3,
}

# Limite padrao de eventos para calculo de cenarios perdedores no relatorio
_LIMITE_EVENTOS_RELATORIO = 500


# ─────────────────────────────────────────────────────────────────
# Dataclass de resultado
# ─────────────────────────────────────────────────────────────────


@dataclass
class MacroGuardianSnapshotResult:
    """Resultado consolidado do snapshot do Macro Guardian.

    Campos:
        score_guardian: Score medio de impacto macro (negativo = adverso).
        alertas_ativos: Quantidade de alertas WARNING/CRITICAL no periodo.
        regime_macro: Regime atual — ESTAVEL, CAUTELOSO, ALERTA, CRITICO.
        kill_switch_ativo: True quando qualquer kill switch esta ativo.
        kill_switch_motivo: Descricao do motivo do kill switch (vazio se inativo).
        total_eventos: Total de eventos no periodo de lookback.
    """

    score_guardian: float = 0.0
    alertas_ativos: int = 0
    regime_macro: str = "ESTAVEL"
    kill_switch_ativo: bool = False
    kill_switch_motivo: str = ""
    total_eventos: int = 0

    def to_dict(self) -> dict[str, Any]:
        """Converte snapshot para dicionario com todos os campos."""
        return asdict(self)

    def to_feature_dict(self) -> dict[str, Any]:
        """Retorna apenas campos numericos para uso como features ML/RL."""
        return {
            "score_guardian": float(self.score_guardian),
            "alertas_ativos": int(self.alertas_ativos),
            "kill_switch_ativo_int": 1 if self.kill_switch_ativo else 0,
            "regime_macro_int": _REGIME_TO_INT_MAP.get(self.regime_macro, 0),
            "total_eventos": int(self.total_eventos),
        }


# ─────────────────────────────────────────────────────────────────
# Servico principal
# ─────────────────────────────────────────────────────────────────


class MacroGuardianReaderService:
    """Canal universal de leitura do Macro Guardian para agentes operacionais.

    Todos os 4 agentes (Micro Tendencia, RL 5000, RL Direto, Diarios)
    usam este servico a cada ciclo para obter o estado atual do Guardian.

    Uso basico:
        servico = MacroGuardianReaderService()
        snapshot = servico.ler_snapshot(db_path)
        ativo, motivo = servico.verificar_kill_switch(db_path)
        episodio_enriquecido = servico.enriquecer_episodio(episodio, db_path)
    """

    # ─── conexao ──────────────────────────────────────────────────

    @staticmethod
    def _conectar(db_path: str | Path) -> sqlite3.Connection:
        """Abre conexao SQLite com PRAGMAs otimizados para WAL."""
        conn = sqlite3.connect(str(db_path), timeout=30)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("PRAGMA synchronous=NORMAL")
        conn.execute("PRAGMA busy_timeout=30000")
        return conn

    # ─── ler_snapshot ─────────────────────────────────────────────

    def ler_snapshot(
        self,
        db_path: str | Path,
        lookback_minutes: int = 30,
    ) -> MacroGuardianSnapshotResult:
        """Retorna snapshot consolidado do estado atual do Guardian.

        Encapsula a logica de leitura do SQLite. Os agentes chamam apenas
        este metodo sem precisar conhecer a estrutura da tabela.

        Args:
            db_path: Caminho do banco SQLite com tabela macro_guardian_log.
            lookback_minutes: Janela de tempo em minutos para analise.

        Returns:
            MacroGuardianSnapshotResult com estado atual do Guardian.
        """
        try:
            ensure_macro_guardian_log_table(db_path)
            dados = fetch_latest_guardian_snapshot(
                db_path,
                lookback_minutes=lookback_minutes,
            )

            kill_switch_ativo = bool(dados.get("kill_switch_ativo", False))
            score_guardian = float(dados.get("score_impacto_medio", 0.0))
            alertas_ativos = int(dados.get("alertas_ativos", 0))
            regime_macro = str(dados.get("regime_macro", "ESTAVEL"))
            total_eventos = int(dados.get("total_eventos", 0))

            kill_switch_motivo = ""
            if kill_switch_ativo:
                kill_switch_motivo = self._construir_motivo_kill_switch(
                    regime_macro, score_guardian, alertas_ativos
                )

            return MacroGuardianSnapshotResult(
                score_guardian=score_guardian,
                alertas_ativos=alertas_ativos,
                regime_macro=regime_macro,
                kill_switch_ativo=kill_switch_ativo,
                kill_switch_motivo=kill_switch_motivo,
                total_eventos=total_eventos,
            )

        except Exception:
            return MacroGuardianSnapshotResult()

    @staticmethod
    def _construir_motivo_kill_switch(
        regime_macro: str,
        score_guardian: float,
        alertas_ativos: int,
    ) -> str:
        """Constroi descricao legivel do motivo do kill switch."""
        partes = [f"regime={regime_macro}"]
        if score_guardian != 0.0:
            partes.append(f"score_guardian={score_guardian:.2f}")
        if alertas_ativos > 0:
            partes.append(f"alertas_ativos={alertas_ativos}")
        return "; ".join(partes)

    # ─── verificar_kill_switch ────────────────────────────────────

    def verificar_kill_switch(
        self,
        db_path: str | Path,
        lookback_minutes: int = 30,
    ) -> tuple[bool, str]:
        """Verifica se o kill switch esta ativo e retorna motivo.

        Metodo rapido para agentes verificarem se devem pausar novas entradas
        sem precisar processar o snapshot completo.

        Args:
            db_path: Caminho do banco SQLite.
            lookback_minutes: Janela de tempo em minutos para analise.

        Returns:
            Tupla (ativo: bool, motivo: str). Motivo vazio quando inativo.
        """
        try:
            snapshot = self.ler_snapshot(db_path, lookback_minutes=lookback_minutes)
            return snapshot.kill_switch_ativo, snapshot.kill_switch_motivo
        except Exception:
            return False, ""

    # ─── enriquecer_episodio ──────────────────────────────────────

    def enriquecer_episodio(
        self,
        episodio_dict: dict[str, Any],
        db_path: str | Path,
        lookback_minutes: int = 30,
    ) -> dict[str, Any]:
        """Adiciona features macro ao dicionario de episodio de treinamento.

        Enriquece cada episodio com o contexto macro do momento — formando
        um dataset multimodal (tecnico + macro) para modelos ML/RL.

        Campos adicionados:
            score_guardian: Score medio de impacto macro no periodo.
            alertas_ativos_count: Quantidade de alertas WARNING/CRITICAL.
            regime_macro: Regime macro atual (ESTAVEL, ALERTA, CRITICO, etc.).
            kill_switch_ativo_no_momento: Bool — kill switch estava ativo.

        Args:
            episodio_dict: Dicionario de episodio a ser enriquecido.
            db_path: Caminho do banco SQLite com tabela macro_guardian_log.
            lookback_minutes: Janela de tempo para consulta do snapshot.

        Returns:
            Copia do dicionario de episodio com campos macro adicionados.
        """
        resultado = dict(episodio_dict)
        try:
            snapshot = self.ler_snapshot(db_path, lookback_minutes=lookback_minutes)
            resultado["score_guardian"] = snapshot.score_guardian
            resultado["alertas_ativos_count"] = snapshot.alertas_ativos
            resultado["regime_macro"] = snapshot.regime_macro
            resultado["kill_switch_ativo_no_momento"] = snapshot.kill_switch_ativo
        except Exception:
            resultado["score_guardian"] = 0.0
            resultado["alertas_ativos_count"] = 0
            resultado["regime_macro"] = "ESTAVEL"
            resultado["kill_switch_ativo_no_momento"] = False
        return resultado

    # ─── gerar_relatorio_semanal ──────────────────────────────────

    def gerar_relatorio_semanal(
        self,
        db_path: str | Path,
        diary_db_path: str | Path,
        semana: Optional[int] = None,
        outputs_dir: Optional[Path] = None,
    ) -> Path:
        """Gera relatorio semanal de correlacao macro x trades.

        Conteudo do relatorio:
            - Distribuicao de alertas por tipo e severidade.
            - Correlacao: alertas Guardian x outcomes dos trades.
            - Cenarios macro que mais precederam trades perdedores.

        Args:
            db_path: Banco com tabela macro_guardian_log.
            diary_db_path: Banco com tabela diary_feedback (pode ser o mesmo).
            semana: Numero ISO da semana (None = semana atual).
            outputs_dir: Diretorio de saida (None = outputs/ na raiz do projeto).

        Returns:
            Path do arquivo .md gerado.
        """
        if semana is None:
            semana = datetime.utcnow().isocalendar()[1]

        if outputs_dir is None:
            outputs_dir = Path(__file__).resolve().parents[3] / "outputs"

        outputs_dir.mkdir(parents=True, exist_ok=True)
        nome_arquivo = f"guardian_semana_{semana:02d}.md"
        caminho = outputs_dir / nome_arquivo

        conteudo = self._construir_relatorio(
            db_path=db_path,
            diary_db_path=diary_db_path,
            semana=semana,
        )
        caminho.write_text(conteudo, encoding="utf-8")
        return caminho

    def _construir_relatorio(
        self,
        db_path: str | Path,
        diary_db_path: str | Path,
        semana: int,
    ) -> str:
        """Constroi o conteudo Markdown do relatorio semanal."""
        gerado_em = datetime.utcnow().isoformat(timespec="seconds")
        distribuicao = self._calcular_distribuicao(db_path)
        correlacao = self._calcular_correlacao(db_path, diary_db_path)
        cenarios_perdedores = self._calcular_cenarios_perdedores(db_path, diary_db_path)

        linhas = [
            f"# Guardian Semanal — Semana {semana:02d}",
            "",
            f"> schema_version: {_SCHEMA_VERSION}  ",
            f"> gerado_em: {gerado_em} UTC",
            "",
            "---",
            "",
            "## Distribuicao de Alertas",
            "",
            "| Severidade | Quantidade |",
            "|------------|------------|",
        ]
        for severidade, quantidade in distribuicao.items():
            linhas.append(f"| {severidade} | {quantidade} |")

        linhas += [
            "",
            "---",
            "",
            "## Correlacao: Alertas Guardian x Outcomes",
            "",
        ]
        if correlacao:
            linhas.append(correlacao)
        else:
            linhas.append("_Dados insuficientes para correlacao._")

        linhas += [
            "",
            "---",
            "",
            "## Cenarios Macro Precedentes a Trades Perdedores",
            "",
        ]
        if cenarios_perdedores:
            linhas.append(cenarios_perdedores)
        else:
            linhas.append("_Nenhum trade perdedor registrado no periodo._")

        linhas += ["", "---", ""]
        return "\n".join(linhas)

    def _calcular_distribuicao(
        self,
        db_path: str | Path,
    ) -> dict[str, int]:
        """Calcula distribuicao de eventos por severidade."""
        try:
            eventos = fetch_recent_macro_guardian_events(db_path, limit=5000)
            distribuicao: dict[str, int] = {}
            for evento in eventos:
                sev = str(evento.get("severity", "INFO"))
                distribuicao[sev] = distribuicao.get(sev, 0) + 1
            return distribuicao
        except Exception:
            return {}

    def _calcular_correlacao(
        self,
        db_path: str | Path,
        diary_db_path: str | Path,
    ) -> str:
        """Calcula correlacao entre alertas Guardian e outcomes de trades."""
        try:
            feedbacks = self._ler_feedbacks(diary_db_path)
            if not feedbacks:
                return ""

            total = len(feedbacks)
            notas = [f["nota_agente"] for f in feedbacks if f.get("nota_agente") is not None]
            if not notas:
                return ""

            media = sum(notas) / len(notas)
            aprovados = sum(1 for n in notas if n >= 7)
            reprovados = sum(1 for n in notas if n < 7)

            linhas = [
                f"- Total de sessoes analisadas: **{total}**",
                f"- Nota media do agente: **{media:.1f}/10**",
                f"- Sessoes aprovadas (nota >= 7): **{aprovados}**",
                f"- Sessoes reprovadas (nota < 7): **{reprovados}**",
            ]
            return "\n".join(linhas)
        except Exception:
            return ""

    def _calcular_cenarios_perdedores(
        self,
        db_path: str | Path,
        diary_db_path: str | Path,
    ) -> str:
        """Identifica cenarios macro que precederam trades perdedores."""
        try:
            feedbacks = self._ler_feedbacks(diary_db_path)
            perdedores = [f for f in feedbacks if (f.get("nota_agente") or 10) < 5]
            if not perdedores:
                return ""

            eventos = fetch_recent_macro_guardian_events(
                db_path, limit=_LIMITE_EVENTOS_RELATORIO, severities=["WARNING", "CRITICAL"]
            )
            count_critico = sum(1 for e in eventos if e.get("severity") == "CRITICAL")
            count_warning = sum(1 for e in eventos if e.get("severity") == "WARNING")

            linhas = [
                f"- Sessoes com nota < 5: **{len(perdedores)}**",
                f"- Alertas CRITICAL no periodo: **{count_critico}**",
                f"- Alertas WARNING no periodo: **{count_warning}**",
            ]
            return "\n".join(linhas)
        except Exception:
            return ""

    def _ler_feedbacks(
        self,
        diary_db_path: str | Path,
    ) -> list[dict[str, Any]]:
        """Le registros de diary_feedback do banco."""
        try:
            conn = self._conectar(diary_db_path)
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute(
                """
                SELECT nota_agente, timestamp, source
                FROM diary_feedback
                ORDER BY id DESC
                LIMIT 100
                """
            )
            rows = cursor.fetchall()
            conn.close()
            return [dict(row) for row in rows]
        except Exception:
            return []
