"""
CALIBRACAO-MICRO-03: Pipeline de Aprendizado com Episodios Reais.

Responsabilidades:
- Persistir cada trade do Micro Tendencia (magic AGENT_MAGIC_NUMBERS["micro_tendencia"]) nos tres destinos:
    1. rl_episodes — contexto completo da entrada (estado, acao, setup)
    2. diario_episodios — resultado final (WIN/LOSS/BREAKEVEN, pts, motivo)
    3. execution_feedback — ciclo de feedback via AC5.9
- Acionar AC6.7 (DriftDetector) a partir de 10 episodios acumulados
- Acionar AC6.8 (OnlineLearningController) a partir de 20 episodios
- Acionar AC6.9 (BaselineComparator) sob demanda (semanalmente)

Pipeline:
    trade fechado
    -> PipelineEpisodiosMicro.registrar_fechamento()
    -> rl_episodes (INSERT via SQLite direto, sem RL engine extra)
    -> diario_episodios (INSERT via EpisodioOperadorRepo)
    -> execution_feedback (UPDATE / INSERT)
    -> AC6.7 se n_episodios >= 10
    -> AC6.8 se n_episodios >= 20
    -> AC6.9 sob demanda

Status: v1.0 (18/03/2026)
Referencia: docs/BACKLOG.md (CALIBRACAO-MICRO-03)
"""

from __future__ import annotations

import logging
import sqlite3
import uuid
from datetime import datetime
from typing import Any, Optional

from config.settings import AGENT_MAGIC_NUMBERS

logger = logging.getLogger("pipeline_episodios_micro")

# Magic number canônico do Micro Tendência (importado de config/settings.py)
# Validação explícita de tipo: garante que o valor é inteiro antes de interpolar
# em strings SQL (proteção contra injeção caso a fonte do dict mude no futuro)
_MAGIC_MICRO: int = int(AGENT_MAGIC_NUMBERS["micro_tendencia"])

# Minimo de episodios para acionar cada modulo
THRESHOLD_DRIFT = 10
THRESHOLD_ONLINE_LEARNING = 20

# Metricas baseline do Micro Tendencia (LightGBM fevereiro/2026)
BASELINE_METRICAS: dict[str, float] = {
    "win_rate": 0.55,
    "f1_score": 0.57,
    "sharpe_ratio": 1.0,
    "avg_pnl": 50.0,
}


def _determinar_outcome(resultado_pts: float) -> str:
    """Converte resultado em pontos para WIN/LOSS/BREAKEVEN."""
    if resultado_pts > 0:
        return "WIN"
    if resultado_pts < 0:
        return "LOSS"
    return "BREAKEVEN"


class PipelineEpisodiosMicro:
    """Pipeline de persistencia e aprendizado para episodios do Micro Tendencia.

    Instanciado uma vez no main() do agente e reutilizado a cada fechamento
    de trade. Mantem contador de episodios em memoria para acionar os modulos
    AC6.7 e AC6.8 nos thresholds corretos.
    """

    def __init__(
        self,
        db_path: str,
        drift_detector: Any = None,
        online_learning: Any = None,
        baseline_comparator: Any = None,
    ) -> None:
        self.db_path = db_path
        self.drift_detector = drift_detector
        self.online_learning = online_learning
        self.baseline_comparator = baseline_comparator
        self._n_episodios: int = 0
        self._episodios_batch: list[dict[str, Any]] = []
        self._garantir_tabelas()

    # ──────────────────────────────────────────────────────────
    # Setup das tabelas extras necessarias
    # ──────────────────────────────────────────────────────────

    def _garantir_tabelas(self) -> None:
        """Cria tabelas se ainda nao existirem."""
        try:
            conn = sqlite3.connect(self.db_path)
            cur = conn.cursor()
            cur.execute(f"""
                CREATE TABLE IF NOT EXISTS micro_episodios (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    episode_id TEXT NOT NULL UNIQUE,
                    timestamp_entrada TEXT NOT NULL,
                    timestamp_saida TEXT NOT NULL,
                    direcao TEXT NOT NULL,
                    preco_entrada REAL,
                    preco_saida REAL,
                    sl REAL,
                    tp REAL,
                    macro_score INTEGER,
                    macro_signal TEXT,
                    macro_confidence REAL,
                    micro_score INTEGER,
                    micro_trend TEXT,
                    adx REAL,
                    rsi REAL,
                    smc_direction TEXT,
                    confianca REAL,
                    reason TEXT,
                    risk_reward REAL,
                    resultado_pts REAL,
                    motivo_saida TEXT,
                    outcome TEXT,
                    duracao_s INTEGER,
                    magic_number INTEGER DEFAULT {_MAGIC_MICRO},
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP
                )
            """)
            # Migra bancos legados antes de criar indices que dependem de colunas novas.
            self._migrar_tabelas_legado(cur)
            cur.execute("""
                CREATE INDEX IF NOT EXISTS idx_mep_ts
                    ON micro_episodios(timestamp_entrada)
            """)
            cur.execute("""
                CREATE INDEX IF NOT EXISTS idx_mep_outcome
                    ON micro_episodios(outcome)
            """)
            # Tabela execution_feedback para AC5.9
            cur.execute(f"""
                CREATE TABLE IF NOT EXISTS execution_feedback (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    episode_id TEXT NOT NULL,
                    trade_id TEXT NOT NULL,
                    timestamp TEXT NOT NULL,
                    outcome_type TEXT NOT NULL,
                    pnl REAL,
                    confianca_entrada REAL,
                    macro_score INTEGER,
                    motivo_saida TEXT,
                    motivos_entrada TEXT,
                    veredicto_pos_resultado TEXT,
                    aprendizado_extra TEXT,
                    magic_number INTEGER DEFAULT {_MAGIC_MICRO},
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP
                )
            """)
            cur.execute("""
                CREATE INDEX IF NOT EXISTS idx_efb_episode
                    ON execution_feedback(episode_id)
            """)
            conn.commit()
            conn.close()
        except Exception as e:
            logger.warning("Falha ao garantir tabelas do pipeline: %s", e)

    def _migrar_tabelas_legado(self, cur: sqlite3.Cursor) -> None:
        """Garante colunas esperadas em bancos legados."""
        tabelas = {
            "micro_trend_decisions": [
                ("exp_reduzida_ativo", "INTEGER DEFAULT 0"),
                ("macro_score_raw", "INTEGER"),
                ("directive_suspended", "INTEGER DEFAULT 0"),
                ("mima_8", "REAL"),
                ("mima_17", "REAL"),
                ("mima_34", "REAL"),
                ("mima_72", "REAL"),
                ("mima_144", "REAL"),
                ("mima_305", "REAL"),
                ("mima_610", "REAL"),
                ("mima_alignment", "TEXT"),
                ("mima_fan_score", "INTEGER"),
                ("divergence_notes", "TEXT"),
                ("aggression_ratio", "REAL"),
            ],
            "micro_episodios": [
                ("episode_id", "TEXT"),
                ("timestamp_entrada", "TEXT"),
                ("timestamp_saida", "TEXT"),
                ("direcao", "TEXT"),
                ("preco_entrada", "REAL"),
                ("preco_saida", "REAL"),
                ("sl", "REAL"),
                ("tp", "REAL"),
                ("macro_score", "INTEGER"),
                ("macro_signal", "TEXT"),
                ("macro_confidence", "REAL"),
                ("micro_score", "INTEGER"),
                ("micro_trend", "TEXT"),
                ("adx", "REAL"),
                ("rsi", "REAL"),
                ("smc_direction", "TEXT"),
                ("confianca", "REAL"),
                ("reason", "TEXT"),
                ("risk_reward", "REAL"),
                ("resultado_pts", "REAL"),
                ("motivo_saida", "TEXT"),
                ("motivos_entrada", "TEXT"),
                ("veredicto_pos_resultado", "TEXT"),
                ("aprendizado_extra", "TEXT"),
                ("outcome", "TEXT"),
                ("duracao_s", "INTEGER"),
                ("magic_number", f"INTEGER DEFAULT {_MAGIC_MICRO}"),
            ],
            "execution_feedback": [
                ("episode_id", "TEXT"),
                ("trade_id", "TEXT"),
                ("timestamp", "TEXT"),
                ("outcome_type", "TEXT"),
                ("pnl", "REAL"),
                ("confianca_entrada", "REAL"),
                ("macro_score", "INTEGER"),
                ("motivo_saida", "TEXT"),
                ("motivos_entrada", "TEXT"),
                ("veredicto_pos_resultado", "TEXT"),
                ("aprendizado_extra", "TEXT"),
                ("magic_number", f"INTEGER DEFAULT {_MAGIC_MICRO}"),
            ],
        }

        for table_name, columns in tabelas.items():
            try:
                cur.execute(f"PRAGMA table_info({table_name})")
                existing = {row[1] for row in cur.fetchall()}
            except Exception:
                continue
            for column_name, column_def in columns:
                if column_name in existing:
                    continue
                try:
                    cur.execute(
                        f"ALTER TABLE {table_name} ADD COLUMN {column_name} {column_def}"
                    )
                except Exception:
                    pass

    # ──────────────────────────────────────────────────────────
    # Persistencia principal
    # ──────────────────────────────────────────────────────────

    def registrar_fechamento(
        self,
        ticket: str,
        direction: str,
        entry_price: float,
        exit_price: float,
        stop_loss: float,
        take_profit: float,
        pnl: float,
        motivo_saida: str,
        duracao_s: int,
        context_entrada: "dict[str, Any] | None" = None,
    ) -> Optional[str]:
        """Registra fechamento de trade nos tres destinos.

        Args:
            ticket: Ticket da ordem de entrada.
            direction: "COMPRA" ou "VENDA".
            entry_price: Preco de entrada.
            exit_price: Preco de saida.
            stop_loss: Stop loss configurado.
            take_profit: Take profit configurado.
            pnl: Resultado em pontos (positivo=lucro).
            motivo_saida: "STOP_LOSS", "TAKE_PROFIT", "MANUAL", etc.
            duracao_s: Duracao da operacao em segundos.
            context_entrada: Dicionario com macro_score, adx, rsi, etc.

        Returns:
            episode_id gerado, ou None em caso de erro.
        """
        episode_id = str(uuid.uuid4())
        ts_saida = datetime.now().isoformat()
        outcome = _determinar_outcome(pnl)
        ctx = context_entrada or {}
        ts_entrada = ctx.get("timestamp_entrada", ts_saida)
        motivos_entrada = self._extrair_motivos_entrada(ctx)
        veredicto_pos_resultado = self._avaliar_veredicto_pos_resultado(
            direction=direction,
            pnl=pnl,
            ctx=ctx,
        )
        aprendizado_extra = self._gerar_aprendizado_extra(
            outcome=outcome,
            pnl=pnl,
            ctx=ctx,
            veredicto=veredicto_pos_resultado,
        )

        # 1. Destino principal: micro_episodios (tabela propria do agente)
        try:
            self._persistir_micro_episodio(
                episode_id=episode_id,
                ticket=ticket,
                direction=direction,
                entry_price=entry_price,
                exit_price=exit_price,
                stop_loss=stop_loss,
                take_profit=take_profit,
                pnl=pnl,
                motivo_saida=motivo_saida,
                duracao_s=duracao_s,
                outcome=outcome,
                ts_entrada=ts_entrada,
                ts_saida=ts_saida,
                ctx=ctx,
                motivos_entrada=motivos_entrada,
                veredicto_pos_resultado=veredicto_pos_resultado,
                aprendizado_extra=aprendizado_extra,
            )
        except Exception as e:
            logger.error("Falha ao persistir micro_episodio %s: %s", episode_id, e)

        # 2. Destino: execution_feedback (AC5.9)
        try:
            self._persistir_execution_feedback(
                episode_id=episode_id,
                ticket=ticket,
                ts_saida=ts_saida,
                outcome=outcome,
                pnl=pnl,
                ctx=ctx,
                motivo_saida=motivo_saida,
                motivos_entrada=motivos_entrada,
                veredicto_pos_resultado=veredicto_pos_resultado,
                aprendizado_extra=aprendizado_extra,
            )
        except Exception as e:
            logger.error("Falha ao persistir execution_feedback %s: %s", episode_id, e)

        # 3. Destino: diario_episodios (formato EpisodioOperador)
        try:
            self._persistir_diario_episodio(
                episode_id=episode_id,
                direction=direction,
                entry_price=entry_price,
                exit_price=exit_price,
                stop_loss=stop_loss,
                take_profit=take_profit,
                pnl=pnl,
                motivo_saida=motivo_saida,
                outcome=outcome,
                ts_entrada=ts_entrada,
                ts_saida=ts_saida,
                ctx=ctx,
                motivos_entrada=motivos_entrada,
                veredicto_pos_resultado=veredicto_pos_resultado,
                aprendizado_extra=aprendizado_extra,
            )
        except Exception as e:
            logger.warning("Falha ao persistir diario_episodio %s: %s", episode_id, e)

        # Acumula episodio no batch para modulos de aprendizado
        self._n_episodios += 1
        self._episodios_batch.append({
            "trade_id": ticket,
            "episode_id": episode_id,
            "outcome": outcome,
            "pnl": pnl,
            "timestamp": ts_saida,
            "direction": direction,
            "macro_score": ctx.get("macro_score"),
            "confianca": ctx.get("confianca"),
            "motivos_entrada": motivos_entrada,
            "veredicto_pos_resultado": veredicto_pos_resultado,
        })

        # 4. AC6.7: Drift a partir de 10 episodios
        if self._n_episodios >= THRESHOLD_DRIFT:
            self._acionar_drift_detector()

        # 5. AC6.8: Retreino a partir de 20 episodios
        if self._n_episodios >= THRESHOLD_ONLINE_LEARNING:
            self._acionar_online_learning()

        logger.info(
            "Episodio registrado: %s | outcome=%s | pnl=%.0f | n=%d",
            episode_id[:8], outcome, pnl, self._n_episodios,
        )
        return episode_id

    # ──────────────────────────────────────────────────────────
    # Persistencia por destino
    # ──────────────────────────────────────────────────────────

    def _persistir_micro_episodio(
        self,
        episode_id: str,
        ticket: str,
        direction: str,
        entry_price: float,
        exit_price: float,
        stop_loss: float,
        take_profit: float,
        pnl: float,
        motivo_saida: str,
        duracao_s: int,
        outcome: str,
        ts_entrada: str,
        ts_saida: str,
        ctx: dict[str, Any],
        motivos_entrada: str = "",
        veredicto_pos_resultado: str = "",
        aprendizado_extra: str = "",
    ) -> None:
        """Persiste na tabela micro_episodios."""
        conn = sqlite3.connect(self.db_path)
        cur = conn.cursor()
        cur.execute(
            """
            INSERT INTO micro_episodios (
                episode_id, timestamp_entrada, timestamp_saida,
                direcao, preco_entrada, preco_saida, sl, tp,
                macro_score, macro_signal, macro_confidence,
                micro_score, micro_trend,
                adx, rsi, smc_direction,
                confianca, reason, risk_reward,
                motivos_entrada, veredicto_pos_resultado, aprendizado_extra,
                resultado_pts, motivo_saida, outcome, duracao_s
            ) VALUES (
                ?, ?, ?,
                ?, ?, ?, ?, ?,
                ?, ?, ?,
                ?, ?,
                ?, ?, ?,
                ?, ?, ?, ?, ?, ?,
                ?, ?, ?, ?
            )
            """,
            (
                episode_id, ts_entrada, ts_saida,
                direction, entry_price, exit_price, stop_loss, take_profit,
                ctx.get("macro_score"), ctx.get("macro_signal"),
                ctx.get("macro_confidence"),
                ctx.get("micro_score"), ctx.get("micro_trend"),
                ctx.get("adx"), ctx.get("rsi"), ctx.get("smc_direction"),
                ctx.get("confianca"), ctx.get("reason"), ctx.get("risk_reward"),
                motivos_entrada, veredicto_pos_resultado, aprendizado_extra,
                pnl, motivo_saida, outcome, duracao_s,
            ),
        )
        conn.commit()
        conn.close()

    def _persistir_execution_feedback(
        self,
        episode_id: str,
        ticket: str,
        ts_saida: str,
        outcome: str,
        pnl: float,
        ctx: dict[str, Any],
        motivo_saida: str,
        motivos_entrada: str = "",
        veredicto_pos_resultado: str = "",
        aprendizado_extra: str = "",
    ) -> None:
        """Persiste na tabela execution_feedback para ciclo AC5.9."""
        conn = sqlite3.connect(self.db_path)
        cur = conn.cursor()
        cur.execute(
            """
            INSERT INTO execution_feedback (
                episode_id, trade_id, timestamp,
                outcome_type, pnl, confianca_entrada,
                macro_score, motivo_saida,
                motivos_entrada, veredicto_pos_resultado, aprendizado_extra
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                episode_id, ticket, ts_saida,
                outcome, pnl, ctx.get("confianca"),
                ctx.get("macro_score"), motivo_saida,
                motivos_entrada, veredicto_pos_resultado, aprendizado_extra,
            ),
        )
        conn.commit()
        conn.close()

    def _persistir_diario_episodio(
        self,
        episode_id: str,
        direction: str,
        entry_price: float,
        exit_price: float,
        stop_loss: float,
        take_profit: float,
        pnl: float,
        motivo_saida: str,
        outcome: str,
        ts_entrada: str,
        ts_saida: str,
        ctx: dict[str, Any],
        motivos_entrada: str = "",
        veredicto_pos_resultado: str = "",
        aprendizado_extra: str = "",
    ) -> None:
        """Persiste na tabela diario_episodios (formato EpisodioOperador)."""
        conn = sqlite3.connect(self.db_path)
        cur = conn.cursor()
        # Garante que a tabela existe (pode nao ter sido criada pelo agente diarios)
        cur.execute("""
            CREATE TABLE IF NOT EXISTS diario_episodios (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id TEXT NOT NULL,
                timestamp_entrada TEXT NOT NULL,
                timestamp_saida TEXT NOT NULL,
                direcao TEXT NOT NULL,
                preco_entrada REAL,
                preco_saida REAL,
                sl REAL,
                tp REAL,
                atr_entrada REAL,
                resultado_pts REAL,
                motivo_saida TEXT,
                fase_sessao TEXT,
                qualidade_movimento TEXT,
                exaustao INTEGER,
                pullback INTEGER,
                correlacao_estado TEXT,
                divergencia_critica INTEGER,
                risco_armadilha TEXT,
                preco_extremo INTEGER,
                desvio_vwap_pts REAL,
                ajuste_confianca_leitura REAL,
                confianca_entrada REAL,
                alinhamento_entrada REAL,
                momentum_entrada REAL,
                motivos_entrada TEXT,
                veredicto_pos_resultado TEXT,
                aprendizado_extra TEXT,
                foi_acerto INTEGER,
                max_ganho_pts REAL,
                eficiencia REAL
            )
        """)
        foi_acerto = 1 if pnl > 0 else 0
        confianca = float(ctx.get("confianca") or 0.0)
        # Fase da sessao derivada do horario de entrada
        try:
            hora = datetime.fromisoformat(ts_entrada).hour
            if hora < 10:
                fase = "ABERTURA"
            elif hora < 12:
                fase = "MANHA"
            elif hora < 14:
                fase = "ALMOCO"
            else:
                fase = "TARDE"
        except Exception:
            fase = "DESCONHECIDA"
        cur.execute(
            """
            INSERT INTO diario_episodios (
                session_id, timestamp_entrada, timestamp_saida,
                direcao, preco_entrada, preco_saida, sl, tp,
                atr_entrada, resultado_pts, motivo_saida,
                fase_sessao, qualidade_movimento,
                exaustao, pullback, correlacao_estado,
                divergencia_critica, risco_armadilha, preco_extremo,
                desvio_vwap_pts, ajuste_confianca_leitura,
                confianca_entrada, alinhamento_entrada, momentum_entrada,
                motivos_entrada, veredicto_pos_resultado, aprendizado_extra,
                foi_acerto, max_ganho_pts, eficiencia
            ) VALUES (
                ?, ?, ?,
                ?, ?, ?, ?, ?,
                ?, ?, ?,
                ?, ?,
                ?, ?, ?,
                ?, ?, ?,
                ?, ?,
                ?, ?, ?,
                ?, ?, ?,
                ?, ?, ?
            )
            """,
            (
                episode_id, ts_entrada, ts_saida,
                direction, entry_price, exit_price, stop_loss, take_profit,
                0.0, pnl, motivo_saida,
                fase, "MICRO_TENDENCIA",
                0, 0, "MICRO_AGENT",
                0, "BAIXO", 0,
                0.0, 0.0,
                confianca, confianca, confianca,
                motivos_entrada, veredicto_pos_resultado, aprendizado_extra,
                foi_acerto, max(pnl, 0.0),
                (pnl / max(pnl, 1.0)) if pnl > 0 else 0.0,
            ),
        )
        conn.commit()
        conn.close()

    # ──────────────────────────────────────────────────────────
    # Acionamento dos modulos AC6.7 e AC6.8
    # ──────────────────────────────────────────────────────────

    def _acionar_drift_detector(self) -> None:
        """Aciona AC6.7 com os episodios acumulados."""
        if not self.drift_detector:
            return
        try:
            alertas = self.drift_detector.detectar_drift(self._episodios_batch)
            if alertas:
                for a in alertas[:3]:
                    metric = getattr(a, "metric", None)
                    if metric is None and isinstance(a, dict):
                        metric = a.get("metric")
                    zscore = getattr(a, "zscore", None)
                    if zscore is None and isinstance(a, dict):
                        zscore = a.get("zscore")
                    severity = getattr(a, "severity", None)
                    if severity is None and isinstance(a, dict):
                        severity = a.get("severity")
                    severity_value = getattr(severity, "value", severity)
                    logger.warning(
                        "AC6.7 Drift: metric=%s z=%.2f severidade=%s",
                        metric,
                        float(zscore or 0.0),
                        severity_value,
                    )
                print(
                    f"  ⚠ AC6.7: {len(alertas)} alerta(s) de drift "
                    f"({self._n_episodios} episodios)"
                )
            else:
                logger.debug(
                    "AC6.7: Sem drift com %d episodios", self._n_episodios
                )
        except Exception as e:
            logger.warning("Falha AC6.7: %s", e)

    def _acionar_online_learning(self) -> None:
        """Aciona AC6.8 com janela dos ultimos 30 episodios."""
        if not self.online_learning:
            return
        # Janela deslizante: ultimos 30 episodios
        batch = self._episodios_batch[-30:]
        try:
            resultado = self.online_learning.train_incremental(batch)
            amostras = resultado.get("samples_trained", 0) if resultado else 0
            logger.info("AC6.8: Treino incremental com %d amostras", amostras)
            print(
                f"  📚 AC6.8: Treino incremental "
                f"({amostras} amostras | {self._n_episodios} episodios total)"
            )
        except Exception as e:
            logger.warning("Falha AC6.8: %s", e)

    def acionar_baseline_comparator(self) -> None:
        """Aciona AC6.9 manualmente (ex: semanalmente pelo loop principal).

        Calcula win_rate real dos episodios acumulados e compara com baseline
        de fevereiro. Recomenda CONTINUE / MONITOR / ROLLBACK.
        """
        if not self.baseline_comparator or not self._episodios_batch:
            return
        try:
            total = len(self._episodios_batch)
            wins = sum(1 for e in self._episodios_batch if e.get("outcome") == "WIN")
            win_rate = wins / total if total > 0 else 0.0
            metricas_atuais = {
                "win_rate": win_rate,
                "f1_score": 0.57,  # Placeholder: calculado apos retreino real
                "sharpe_ratio": 1.0,
            }
            comparacao = self.baseline_comparator.comparar_metricas(
                current_metrics=metricas_atuais
            )
            feedback = self.baseline_comparator.gerar_feedback(comparacao)
            icone = {"CONTINUE": "🟢", "MONITOR": "🟡", "ROLLBACK": "🔴"}.get(
                feedback.recommended_action, "⚪"
            )
            print(
                f"  {icone} AC6.9: {feedback.recommended_action}"
                f" | WinRate real: {win_rate:.1%}"
                f" | Episodios: {total}"
                f" | Confianca: {feedback.confidence:.0%}"
            )
            logger.info(
                "AC6.9: %s | win_rate=%.3f | n=%d",
                feedback.recommended_action, win_rate, total,
            )
        except Exception as e:
            logger.warning("Falha AC6.9: %s", e)

    def _extrair_motivos_entrada(self, ctx: dict[str, Any]) -> str:
        """Resume os motivos de entrada para aprendizagem posterior."""
        partes: list[str] = []
        for chave in (
            "reason",
            "macro_reason",
            "macro_signal",
            "micro_trend",
            "smc_direction",
            "guardian_state",
            "diary_reason",
            "market_context",
        ):
            valor = ctx.get(chave)
            if valor:
                partes.append(f"{chave}={valor}")
        return " | ".join(partes[:8])

    def _avaliar_veredicto_pos_resultado(
        self,
        direction: str,
        pnl: float,
        ctx: dict[str, Any],
    ) -> str:
        """Classifica se o resultado confirmou a tese ou pareceu casual."""
        macro_score = ctx.get("macro_score")
        try:
            macro_score = float(macro_score) if macro_score is not None else None
        except (TypeError, ValueError):
            macro_score = None

        if pnl > 0:
            if direction == "COMPRA" and macro_score is not None and macro_score > 0:
                return "MOTIVOS_CONFIRMADOS"
            if direction == "VENDA" and macro_score is not None and macro_score < 0:
                return "MOTIVOS_CONFIRMADOS"
            return "RESULTADO_POSITIVO_POSSIVEL_CASUALIDADE"

        if pnl < 0:
            if direction == "COMPRA" and macro_score is not None and macro_score < 0:
                return "MOTIVOS_CONTRARIOS_FORAM_PREVALENTES"
            if direction == "VENDA" and macro_score is not None and macro_score > 0:
                return "MOTIVOS_CONTRARIOS_FORAM_PREVALENTES"
            return "MOTIVOS_NAO_CONFIRMADOS"

        return "BREAKEVEN_EXIGE_MAIS_DADOS"

    def _gerar_aprendizado_extra(
        self,
        outcome: str,
        pnl: float,
        ctx: dict[str, Any],
        veredicto: str,
    ) -> str:
        """Gera uma frase curta de aprendizado para treino posterior."""
        macro_score = ctx.get("macro_score")
        macro_signal = ctx.get("macro_signal")
        micro_score = ctx.get("micro_score")
        return (
            f"outcome={outcome} | pnl={pnl:.0f} | macro={macro_score} "
            f"| signal={macro_signal} | micro={micro_score} | veredicto={veredicto}"
        )

    # ──────────────────────────────────────────────────────────
    # Consultas de auditoria
    # ──────────────────────────────────────────────────────────

    def contar_episodios(self) -> int:
        """Retorna total de episodios com outcome registrado no banco."""
        try:
            conn = sqlite3.connect(self.db_path)
            cur = conn.cursor()
            cur.execute(
                "SELECT COUNT(*) FROM micro_episodios WHERE outcome IS NOT NULL"
            )
            row = cur.fetchone()
            conn.close()
            return int(row[0]) if row else 0
        except Exception:
            return self._n_episodios

    def calcular_win_rate_real(self) -> float:
        """Calcula win rate real dos episodios persistidos no banco."""
        try:
            conn = sqlite3.connect(self.db_path)
            cur = conn.cursor()
            cur.execute(
                "SELECT outcome FROM micro_episodios WHERE outcome IS NOT NULL"
            )
            rows = cur.fetchall()
            conn.close()
            if not rows:
                return 0.0
            wins = sum(1 for r in rows if r[0] == "WIN")
            return wins / len(rows)
        except Exception:
            return 0.0
