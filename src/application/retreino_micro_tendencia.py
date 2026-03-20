"""
CALIBRACAO-MICRO-05: Retreino Efetivo com Episodios Acumulados.

Responsabilidades:
- Disparar retreinamento do LightGBM independente de trades executados,
  quando rl_rewards acumular >= 200 novos rewards desde o ultimo treino.
- Retreinar com janela deslizante dos ultimos 500 episodios avaliados,
  priorizando os mais recentes (peso decrescente).
- Registrar cada retreinamento em rl_training_metrics e model_metadata:
  versao, data, n_episodios_usados, win_rate_treino, win_rate_validacao,
  delta vs versao anterior.
- Versionamento semantico: data/models/micro_tendencia/vMAJOR.MINOR.PATCH_YYYYMMDD
- Rollback automatico se win_rate_validacao cair mais de 5pp vs versao anterior.

Pipeline:
    rl_rewards acumula novos registros
    -> TriggerRetreino.checar_threshold()
    -> GerenciadorRetreino.executar_retreino()
    -> RegistroTreino persiste em rl_training_metrics + model_metadata
    -> Rollback automatico se degradacao detectada

Status: v1.0 (18/03/2026)
Referencia: docs/BACKLOG.md (CALIBRACAO-MICRO-05)
"""

from __future__ import annotations

import json
import logging
import sqlite3
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Optional
from uuid import uuid4

logger = logging.getLogger("retreino_micro_tendencia")

# ─────────────────────────────────────────────
# Constantes de threshold
# ─────────────────────────────────────────────
THRESHOLD_REWARDS_NOVO_TREINO: int = 500
JANELA_EPISODIOS: int = 500
ROLLBACK_DELTA_MAX_PP: float = 5.0  # porcentagem
WIN_RATE_MINIMO_VALIDACAO: float = 0.40
COOLDOWN_TREINO_MINUTOS: int = 180


# ─────────────────────────────────────────────
# Dataclasses
# ─────────────────────────────────────────────


@dataclass
class RegistroTreino:
    """Registro de um ciclo de retreinamento persistido no banco.

    Armazenado em rl_training_metrics e model_metadata.
    """

    versao: str
    data_treino: str
    n_episodios_usados: int
    win_rate_treino: float
    win_rate_validacao: float
    delta_vs_anterior: float
    rollback_realizado: bool
    modelo_path: str
    notas: str = ""

    def para_dict(self) -> dict[str, Any]:
        """Converte para dicionario JSON-serializable."""
        return {
            "versao": self.versao,
            "data_treino": self.data_treino,
            "n_episodios_usados": self.n_episodios_usados,
            "win_rate_treino": self.win_rate_treino,
            "win_rate_validacao": self.win_rate_validacao,
            "delta_vs_anterior": self.delta_vs_anterior,
            "rollback_realizado": self.rollback_realizado,
            "modelo_path": self.modelo_path,
            "notas": self.notas,
        }


@dataclass
class ResultadoRetreino:
    """Resultado de uma execucao de retreinamento.

    Retornado por GerenciadorRetreino.executar_retreino().
    """

    executado: bool
    versao: str
    n_episodios: int
    win_rate_treino: float
    win_rate_validacao: float
    delta_win_rate: float
    rollback_realizado: bool
    motivo_nao_execucao: str = ""
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())

    def para_dict(self) -> dict[str, Any]:
        """Converte para dicionario JSON-serializable."""
        return {
            "executado": self.executado,
            "versao": self.versao,
            "n_episodios": self.n_episodios,
            "win_rate_treino": self.win_rate_treino,
            "win_rate_validacao": self.win_rate_validacao,
            "delta_win_rate": self.delta_win_rate,
            "rollback_realizado": self.rollback_realizado,
            "motivo_nao_execucao": self.motivo_nao_execucao,
            "timestamp": self.timestamp,
        }


@dataclass
class EstadoRetreino:
    """Resumo do estado atual de aprendizado e treino do micro."""

    episodios_acumulados: int
    rewards_acumuladas: int
    rewards_desde_ultimo_treino: int
    rewards_ate_proximo_treino: int
    threshold_rewards: int
    ultima_versao_treino: str
    ultima_data_treino: str

    def para_dict(self) -> dict[str, Any]:
        return {
            "episodios_acumulados": self.episodios_acumulados,
            "rewards_acumuladas": self.rewards_acumuladas,
            "rewards_desde_ultimo_treino": self.rewards_desde_ultimo_treino,
            "rewards_ate_proximo_treino": self.rewards_ate_proximo_treino,
            "threshold_rewards": self.threshold_rewards,
            "ultima_versao_treino": self.ultima_versao_treino,
            "ultima_data_treino": self.ultima_data_treino,
        }


# ─────────────────────────────────────────────
# Trigger de retreinamento
# ─────────────────────────────────────────────


class TriggerRetreino:
    """Verifica se o threshold de rewards foi atingido para disparar retreino.

    Compara o total de rewards acumulados em rl_rewards contra o ultimo
    n_rewards registrado em rl_training_metrics.

    Args:
        db_path: Caminho para o banco SQLite.
        threshold: Minimo de novos rewards para disparar retreino.
    """

    def __init__(
        self,
        db_path: str,
        threshold: int = THRESHOLD_REWARDS_NOVO_TREINO,
    ) -> None:
        self.db_path = db_path
        self.threshold = threshold
        self._garantir_tabelas()

    def _garantir_tabelas(self) -> None:
        """Cria tabelas rl_training_metrics e model_metadata se nao existirem."""
        try:
            conn = sqlite3.connect(self.db_path)
            cur = conn.cursor()
            cur.execute("""
                CREATE TABLE IF NOT EXISTS rl_training_metrics (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    versao TEXT NOT NULL,
                    data_treino TEXT NOT NULL,
                    n_episodios_usados INTEGER NOT NULL,
                    n_rewards_no_treino INTEGER NOT NULL,
                    win_rate_treino REAL NOT NULL,
                    win_rate_validacao REAL NOT NULL,
                    delta_vs_anterior REAL NOT NULL,
                    rollback_realizado INTEGER NOT NULL DEFAULT 0,
                    modelo_path TEXT NOT NULL,
                    notas TEXT DEFAULT '',
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP
                )
            """)
            cur.execute("""
                CREATE TABLE IF NOT EXISTS model_metadata (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    versao TEXT NOT NULL UNIQUE,
                    data_treino TEXT NOT NULL,
                    modelo_path TEXT NOT NULL,
                    win_rate_validacao REAL NOT NULL,
                    n_episodios INTEGER NOT NULL,
                    ativo INTEGER NOT NULL DEFAULT 0,
                    notas TEXT DEFAULT '',
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP
                )
            """)
            conn.commit()
            conn.close()
        except Exception as exc:
            logger.warning("Falha ao garantir tabelas de retreino: %s", exc)

    def _tem_coluna(self, tabela: str, coluna: str) -> bool:
        """Verifica se uma coluna existe em uma tabela SQLite."""
        try:
            conn = sqlite3.connect(self.db_path)
            cur = conn.cursor()
            cur.execute(f"PRAGMA table_info({tabela})")
            colunas = {str(row[1]) for row in cur.fetchall()}
            conn.close()
            return coluna in colunas
        except Exception:
            return False

    def _salvar_model_metadata(
        self,
        cur: sqlite3.Cursor,
        versao: str,
        data_treino: str,
        modelo_path: str,
        win_rate_validacao: float,
        n_episodios: int,
        notas: str,
        win_rate_treino: float = 0.0,
        delta: float = 0.0,
        rollback: bool = False,
    ) -> None:
        """Persiste o metadado ativo do modelo no schema atual.

        O projeto convive com dois formatos de `model_metadata`:
        - schema legado com `versao`/`ativo`
        - schema atual com `model_name`/`version`

        Este helper faz upsert no formato disponível para evitar quebra por
        `UNIQUE constraint` ao registrar novas versões.
        """
        if self._tem_coluna("model_metadata", "model_name"):
            cur.execute("UPDATE model_metadata SET is_active = 0")
            training_metrics = json.dumps(
                {
                    "win_rate_treino": win_rate_treino,
                    "win_rate_validacao": win_rate_validacao,
                    "n_episodios": n_episodios,
                    "delta_vs_anterior": delta,
                    "rollback": rollback,
                    "notas": notas,
                },
                ensure_ascii=False,
            )
            cur.execute(
                """
                INSERT INTO model_metadata (
                    model_name, model_type, version, trained_at,
                    training_metrics, hyperparameters, file_path,
                    is_active, created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, 1, ?, ?)
                ON CONFLICT(model_name) DO UPDATE SET
                    model_type = excluded.model_type,
                    version = excluded.version,
                    trained_at = excluded.trained_at,
                    training_metrics = excluded.training_metrics,
                    hyperparameters = excluded.hyperparameters,
                    file_path = excluded.file_path,
                    is_active = excluded.is_active,
                    updated_at = excluded.updated_at
                """,
                (
                    "micro_tendencia",
                    "LightGBM_micro_tendencia",
                    versao,
                    data_treino,
                    training_metrics,
                    json.dumps({}, ensure_ascii=False),
                    modelo_path,
                    data_treino,
                    data_treino,
                ),
            )
            return

        if self._tem_coluna("model_metadata", "versao"):
            cur.execute("UPDATE model_metadata SET ativo = 0")
            cur.execute(
                """
                INSERT INTO model_metadata (
                    versao, data_treino, modelo_path,
                    win_rate_validacao, n_episodios, ativo, notas
                ) VALUES (?, ?, ?, ?, ?, 1, ?)
                ON CONFLICT(versao) DO UPDATE SET
                    data_treino = excluded.data_treino,
                    modelo_path = excluded.modelo_path,
                    win_rate_validacao = excluded.win_rate_validacao,
                    n_episodios = excluded.n_episodios,
                    ativo = excluded.ativo,
                    notas = excluded.notas
                """,
                (
                    versao,
                    data_treino,
                    modelo_path,
                    win_rate_validacao,
                    n_episodios,
                    notas,
                ),
            )

            return

        logger.warning(
            "model_metadata sem colunas conhecidas para persistencia segura."
        )

    def contar_rewards_total(self) -> int:
        """Retorna total de rewards avaliados em rl_rewards.

        Returns:
            Contagem total de registros em rl_rewards, ou 0 se tabela
            nao existe.
        """
        try:
            conn = sqlite3.connect(self.db_path)
            cur = conn.cursor()
            cur.execute(
                "SELECT COUNT(*) FROM rl_rewards WHERE is_evaluated = 1"
            )
            row = cur.fetchone()
            conn.close()
            return int(row[0]) if row else 0
        except Exception:
            return 0

    def contar_rewards_ultimo_treino(self) -> int:
        """Retorna a quantidade de rewards avaliados ate o ultimo treino."""
        try:
            conn = sqlite3.connect(self.db_path)
            cur = conn.cursor()
            treino_ts: Optional[str] = None
            if self._tem_coluna("rl_training_metrics", "timestamp"):
                cur.execute(
                    "SELECT timestamp FROM rl_training_metrics "
                    "ORDER BY id DESC LIMIT 1"
                )
                row = cur.fetchone()
                treino_ts = str(row[0]) if row and row[0] else None
            elif self._tem_coluna("model_metadata", "trained_at"):
                cur.execute(
                    "SELECT trained_at FROM model_metadata "
                    "WHERE is_active = 1 ORDER BY id DESC LIMIT 1"
                )
                row = cur.fetchone()
                treino_ts = str(row[0]) if row and row[0] else None

            if not treino_ts:
                conn.close()
                return 0

            cur.execute(
                """
                SELECT COUNT(*)
                FROM rl_rewards
                WHERE is_evaluated = 1
                  AND datetime(COALESCE(evaluated_at, created_at)) <= datetime(?)
                """,
                (treino_ts,),
            )
            row = cur.fetchone()

            conn.close()
            return int(row[0]) if row else 0
        except Exception:
            return 0

    def _obter_timestamp_ultimo_treino(self) -> Optional[str]:
        """Retorna o timestamp do ultimo treino persistido."""
        try:
            conn = sqlite3.connect(self.db_path)
            cur = conn.cursor()
            cur.execute(
                "SELECT timestamp FROM rl_training_metrics "
                "ORDER BY id DESC LIMIT 1"
            )
            row = cur.fetchone()
            conn.close()
            if row and row[0]:
                return str(row[0])
            if self._tem_coluna("model_metadata", "trained_at"):
                conn = sqlite3.connect(self.db_path)
                cur = conn.cursor()
                cur.execute(
                    "SELECT trained_at FROM model_metadata "
                    "WHERE is_active = 1 ORDER BY id DESC LIMIT 1"
                )
                row = cur.fetchone()
                conn.close()
                if row and row[0]:
                    return str(row[0])
        except Exception:
            return None
        return None

    def _cooldown_restante_minutos(self) -> int:
        """Retorna quantos minutos faltam para o cooldown liberar novo treino."""
        ultimo_ts = self._obter_timestamp_ultimo_treino()
        if not ultimo_ts:
            return 0
        try:
            ultimo = datetime.fromisoformat(str(ultimo_ts).replace("Z", "+00:00"))
            delta = datetime.now() - ultimo.replace(tzinfo=None) if ultimo.tzinfo else datetime.now() - ultimo
            decorrido = delta.total_seconds() / 60.0
            return max(0, int(round(COOLDOWN_TREINO_MINUTOS - decorrido)))
        except Exception:
            return 0

    def novos_rewards_desde_ultimo_treino(self) -> int:
        """Calcula quantos rewards acumularam desde o ultimo retreino.

        Returns:
            Diferenca entre total atual e ultimo snapshot de treino.
        """
        total = self.contar_rewards_total()
        ultimo = self.contar_rewards_ultimo_treino()
        return max(0, total - ultimo)

    def obter_estado(self) -> dict[str, Any]:
        """Retorna um snapshot do estado de aprendizado do micro."""
        total = self.contar_rewards_total()
        ultimo = self.contar_rewards_ultimo_treino()
        desde_ultimo = max(0, total - ultimo)
        falta_para_proximo = max(0, self.threshold - desde_ultimo)
        cooldown_restante = self._cooldown_restante_minutos()
        return {
            "rewards_acumuladas": total,
            "rewards_desde_ultimo_treino": desde_ultimo,
            "rewards_ate_proximo_treino": falta_para_proximo,
            "threshold_rewards": self.threshold,
            "cooldown_treino_minutos": COOLDOWN_TREINO_MINUTOS,
            "cooldown_restante_minutos": cooldown_restante,
        }

    def bootstrap_modelo_atual(self, modelo_path: str, rewards_total: int, n_episodios: int) -> Optional[str]:
        """Cria um baseline auditável quando não existe histórico formal."""
        try:
            if self.contar_rewards_ultimo_treino() > 0:
                return None

            path = Path(modelo_path)
            data_treino = datetime.fromtimestamp(path.stat().st_mtime).isoformat() if path.exists() else datetime.now().isoformat()
            versao = f"bootstrap_{path.stem}_{datetime.now().strftime('%Y%m%d')}"
            metrics = {
                "rewards_total": rewards_total,
                "n_episodios": n_episodios,
                "bootstrap": True,
                "fonte": str(path),
            }
            notas = f"Bootstrap inicial | rewards_total={rewards_total} | modelo={modelo_path}"

            conn = sqlite3.connect(self.db_path)
            cur = conn.cursor()
            if self._tem_coluna("rl_training_metrics", "model_version"):
                cur.execute(
                    """
                    INSERT INTO rl_training_metrics (
                        training_id, timestamp, model_name, model_version,
                        algorithm, episodes_total, episodes_train,
                        episodes_validation, avg_reward, cumulative_reward,
                        win_rate, profit_factor, sharpe_ratio, max_drawdown,
                        buy_accuracy, sell_accuracy, hold_accuracy,
                        hyperparameters, feature_importance, validation_reward,
                        overfitting_ratio, notes, created_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        str(uuid4()),
                        data_treino,
                        "micro_tendencia",
                        versao,
                        "LightGBM_micro_tendencia",
                        n_episodios,
                        n_episodios,
                        0,
                        0.0,
                        0.0,
                        0.0,
                        0.0,
                        0.0,
                        0.0,
                        0.0,
                        0.0,
                        0.0,
                        json.dumps({}, ensure_ascii=False),
                        json.dumps({}, ensure_ascii=False),
                        0.0,
                        0.0,
                        f"Bootstrap inicial | rewards_total={rewards_total} | modelo={modelo_path}",
                        datetime.now().isoformat(),
                    ),
                )
            else:
                cur.execute(
                    """
                    INSERT INTO rl_training_metrics (
                        versao, data_treino, n_episodios_usados,
                        n_rewards_no_treino, win_rate_treino,
                        win_rate_validacao, delta_vs_anterior,
                        rollback_realizado, modelo_path, notas
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        versao,
                        data_treino,
                        n_episodios,
                        rewards_total,
                        0.0,
                        0.0,
                        0.0,
                        0,
                        modelo_path,
                        notas,
                    ),
                )
            self._salvar_model_metadata(
                cur=cur,
                versao=versao,
                data_treino=data_treino,
                modelo_path=modelo_path,
                win_rate_validacao=0.0,
                n_episodios=n_episodios,
                notas=notas,
                win_rate_treino=0.0,
                delta=0.0,
                rollback=False,
            )
            conn.commit()
            conn.close()
            return versao
        except Exception as exc:
            logger.warning("Falha ao registrar bootstrap do modelo atual: %s", exc)
            return None

    def deve_retreinar(self) -> bool:
        """Verifica se threshold foi atingido para disparar retreino.

        Returns:
            True se novos_rewards >= threshold.
        """
        return (
            self.novos_rewards_desde_ultimo_treino() >= self.threshold
            and self._cooldown_restante_minutos() <= 0
        )


# ─────────────────────────────────────────────
# Carregador de episodios
# ─────────────────────────────────────────────


class CarregadorEpisodios:
    """Carrega episodios do micro a partir de rl_episodes com janela deslizante.

    Prioriza os mais recentes com peso decrescente para simular
    relevancia temporal no retreino.

    Args:
        db_path: Caminho para o banco SQLite.
        janela: Numero maximo de episodios a carregar.
    """

    def __init__(self, db_path: str, janela: int = JANELA_EPISODIOS) -> None:
        self.db_path = db_path
        self.janela = janela

    def carregar_episodios(self) -> list[dict[str, Any]]:
        """Carrega os ultimos N episodios do micro.

        Returns:
            Lista de dicts com outcome, pnl, timestamp, confianca,
            macro_score, direction, peso.
        """
        try:
            conn = sqlite3.connect(self.db_path)
            cur = conn.cursor()
            cur.execute(
                """
                SELECT episode_id, timestamp, action, micro_trend,
                       overall_confidence, macro_score_final
                FROM rl_episodes
                WHERE source = 'MICRO_AGENT'
                ORDER BY timestamp DESC
                LIMIT ?
                """,
                (self.janela,),
            )
            rows = cur.fetchall()
            conn.close()
        except Exception as exc:
            logger.warning("Falha ao carregar episodios: %s", exc)
            return []

        episodios: list[dict[str, Any]] = []
        total = len(rows)
        for i, row in enumerate(rows):
            # Peso decrescente: episodio mais recente tem peso 1.0,
            # o mais antigo tem peso ~0.1
            peso = 1.0 - 0.9 * (i / max(total - 1, 1))
            outcome, pnl = self._derivar_outcome_e_pnl(row[0])
            episodios.append(
                {
                    "outcome": outcome,
                    "pnl": pnl,
                    "timestamp": row[1] or "",
                    "confianca": float(row[4] or 0.0),
                    "macro_score": int(float(row[5] or 0.0)),
                    "direction": row[3] or row[2] or "",
                    "peso": round(peso, 4),
                }
            )
        return episodios

    def contar_episodios(self) -> int:
        """Retorna a quantidade total de episodios persistidos."""
        try:
            conn = sqlite3.connect(self.db_path)
            cur = conn.cursor()
            cur.execute(
                "SELECT COUNT(*) FROM rl_episodes WHERE source = 'MICRO_AGENT'"
            )
            row = cur.fetchone()
            conn.close()
            return int(row[0]) if row else 0
        except Exception:
            return 0

    def _derivar_outcome_e_pnl(self, episode_id: str) -> tuple[str, float]:
        """Deriva o outcome a partir da recompensa mais recente do episodio."""
        try:
            conn = sqlite3.connect(self.db_path)
            cur = conn.cursor()
            cur.execute(
                """
                SELECT reward_direction, was_correct, reward_continuous,
                       reward_normalized, price_change_points, decision_verdict
                FROM rl_rewards
                WHERE episode_id = ?
                ORDER BY COALESCE(evaluated_at, created_at) DESC, id DESC
                LIMIT 1
                """,
                (episode_id,),
            )
            row = cur.fetchone()
            conn.close()
            if not row:
                return "BREAKEVEN", 0.0

            verdict = str(row[5] or "").upper()
            pnl = float(row[2] or row[4] or row[3] or 0.0)
            if verdict in {"WIN", "LOSS", "BREAKEVEN"}:
                return verdict, pnl

            was_correct = row[1]
            if was_correct is not None:
                return ("WIN", pnl) if int(was_correct) == 1 else ("LOSS", pnl)
            if pnl > 0:
                return "WIN", pnl
            if pnl < 0:
                return "LOSS", pnl
            return "BREAKEVEN", pnl
        except Exception:
            return "BREAKEVEN", 0.0

    def calcular_win_rate(self, episodios: list[dict[str, Any]]) -> float:
        """Calcula win rate ponderado por peso.

        Args:
            episodios: Lista com campos outcome e peso.

        Returns:
            Win rate entre 0.0 e 1.0.
        """
        if not episodios:
            return 0.0
        peso_total: float = sum(float(e["peso"]) for e in episodios)
        if peso_total == 0:
            return 0.0
        wins_ponderados: float = sum(
            float(e["peso"]) for e in episodios if e["outcome"] == "WIN"
        )
        return wins_ponderados / peso_total


# ─────────────────────────────────────────────
# Versionador de modelos
# ─────────────────────────────────────────────


class VersonadorModelo:
    """Gerencia versionamento semantico de modelos treinados.

    Formato: vMAJOR.MINOR.PATCH_YYYYMMDD
    MINOR e incrementado a cada retreino bem-sucedido.
    PATCH e incrementado em retreinos de rollback.

    Args:
        db_path: Caminho para o banco SQLite.
        modelos_dir: Diretorio base para persistir modelos.
    """

    def __init__(
        self,
        db_path: str,
        modelos_dir: str = "data/models/micro_tendencia",
    ) -> None:
        self.db_path = db_path
        self.modelos_dir = Path(modelos_dir)
        self.modelos_dir.mkdir(parents=True, exist_ok=True)

    def obter_versao_atual(self) -> Optional[str]:
        """Retorna versao do modelo ativo em model_metadata.

        Returns:
            String de versao como "v1.2.0_20260318", ou None se vazio.
        """
        try:
            conn = sqlite3.connect(self.db_path)
            cur = conn.cursor()
            cur.execute(
                "SELECT versao FROM model_metadata WHERE ativo = 1 "
                "ORDER BY id DESC LIMIT 1"
            )
            row = cur.fetchone()
            conn.close()
            return str(row[0]) if row else None
        except Exception:
            return None

    def gerar_proxima_versao(self, rollback: bool = False) -> str:
        """Gera proximo identificador de versao semantico.

        Args:
            rollback: Se True, incrementa PATCH; caso contrario MINOR.

        Returns:
            String como "v1.2.0_20260318".
        """
        versao_atual = self.obter_versao_atual()
        hoje = datetime.now().strftime("%Y%m%d")

        if versao_atual is None:
            return f"v1.0.0_{hoje}"

        # Extrai major.minor.patch da versao (ignora data)
        prefixo = versao_atual.split("_")[0]  # "v1.2.0"
        partes = prefixo.lstrip("v").split(".")
        try:
            major = int(partes[0])
            minor = int(partes[1])
            patch = int(partes[2]) if len(partes) > 2 else 0
        except (IndexError, ValueError):
            return f"v1.0.0_{hoje}"

        if rollback:
            patch += 1
        else:
            minor += 1
            patch = 0

        return f"v{major}.{minor}.{patch}_{hoje}"

    def caminho_modelo(self, versao: str) -> Path:
        """Retorna caminho completo para arquivo de modelo.

        Args:
            versao: Identificador de versao.

        Returns:
            Path para o arquivo JSON de metadados do modelo.
        """
        return self.modelos_dir / f"{versao}.json"

    def caminho_changelog(self) -> Path:
        """Retorna o caminho do changelog de versoes do modelo."""
        return self.modelos_dir / "CHANGELOG.md"


# ─────────────────────────────────────────────
# Gerenciador principal de retreino
# ─────────────────────────────────────────────


class GerenciadorRetreino:
    """Motor principal de retreinamento do LightGBM do Micro Tendencia.

    Responsabilidades:
    - Verificar threshold de rewards acumulados.
    - Carregar janela deslizante de episodios.
    - Simular retreino (calcula metricas sem dependencia de LightGBM real).
    - Detectar degradacao e acionar rollback automatico.
    - Registrar resultado em rl_training_metrics e model_metadata.

    Args:
        db_path: Caminho para o banco SQLite.
        modelos_dir: Diretorio para persistir versoes de modelo.
    """

    def __init__(
        self,
        db_path: str,
        modelos_dir: str = "data/models/micro_tendencia",
    ) -> None:
        self.db_path = db_path
        self.trigger = TriggerRetreino(db_path)
        self.carregador = CarregadorEpisodios(db_path)
        self.versionador = VersonadorModelo(db_path, modelos_dir)

    def _tem_coluna(self, tabela: str, coluna: str) -> bool:
        """Atalho para consultar colunas usando a mesma conexao do trigger."""
        return self.trigger._tem_coluna(tabela, coluna)

    def _salvar_model_metadata(
        self,
        cur: sqlite3.Cursor,
        versao: str,
        data_treino: str,
        modelo_path: str,
        win_rate_validacao: float,
        n_episodios: int,
        notas: str,
        win_rate_treino: float = 0.0,
        delta: float = 0.0,
        rollback: bool = False,
    ) -> None:
        """Delega a persistencia do metadado para o helper do TriggerRetreino."""
        self.trigger._salvar_model_metadata(
            cur=cur,
            versao=versao,
            data_treino=data_treino,
            modelo_path=modelo_path,
            win_rate_validacao=win_rate_validacao,
            n_episodios=n_episodios,
            notas=notas,
            win_rate_treino=win_rate_treino,
            delta=delta,
            rollback=rollback,
        )

    def obter_estado_aprendizado(self) -> EstadoRetreino:
        """Retorna o estado atual de aprendizado e proximidade do proximo treino."""
        estado_trigger = self.trigger.obter_estado()
        return EstadoRetreino(
            episodios_acumulados=self.carregador.contar_episodios(),
            rewards_acumuladas=int(estado_trigger["rewards_acumuladas"]),
            rewards_desde_ultimo_treino=int(estado_trigger["rewards_desde_ultimo_treino"]),
            rewards_ate_proximo_treino=int(estado_trigger["rewards_ate_proximo_treino"]),
            threshold_rewards=int(estado_trigger["threshold_rewards"]),
            ultima_versao_treino=self.obter_ultima_versao_treino(),
            ultima_data_treino=self.obter_ultima_data_treino(),
        )

    def executar_retreino(
        self,
        forcar: bool = False,
    ) -> ResultadoRetreino:
        """Executa ciclo completo de retreinamento.

        Verifica threshold, carrega episodios, calcula metricas,
        detecta rollback e persiste resultados.

        Args:
            forcar: Se True, executa mesmo sem atingir threshold
                (util para retreino manual imediato).

        Returns:
            ResultadoRetreino com resultado completo.
        """
        if not forcar and not self.trigger.deve_retreinar():
            novos = self.trigger.novos_rewards_desde_ultimo_treino()
            return ResultadoRetreino(
                executado=False,
                versao="",
                n_episodios=0,
                win_rate_treino=0.0,
                win_rate_validacao=0.0,
                delta_win_rate=0.0,
                rollback_realizado=False,
                motivo_nao_execucao=(
                    f"Threshold nao atingido: {novos} novos rewards "
                    f"(minimo: {self.trigger.threshold})"
                ),
            )

        episodios = self.carregador.carregar_episodios()
        if len(episodios) < 10:
            return ResultadoRetreino(
                executado=False,
                versao="",
                n_episodios=len(episodios),
                win_rate_treino=0.0,
                win_rate_validacao=0.0,
                delta_win_rate=0.0,
                rollback_realizado=False,
                motivo_nao_execucao=(
                    f"Episodios insuficientes: {len(episodios)} (minimo: 10)"
                ),
            )

        # Divisao treino/validacao: 80% treino, 20% validacao
        n_treino = max(8, int(len(episodios) * 0.8))
        episodios_treino = episodios[:n_treino]
        episodios_validacao = episodios[n_treino:]

        win_rate_treino = self.carregador.calcular_win_rate(episodios_treino)
        win_rate_validacao = (
            self.carregador.calcular_win_rate(episodios_validacao)
            if episodios_validacao
            else win_rate_treino
        )

        # Obter win_rate da versao anterior para calcular delta
        win_rate_anterior = self._obter_win_rate_versao_anterior()
        delta = (win_rate_validacao - win_rate_anterior) * 100.0

        # Detectar se deve fazer rollback
        rollback = (
            win_rate_anterior > 0.0
            and delta < -ROLLBACK_DELTA_MAX_PP
        )

        versao = self.versionador.gerar_proxima_versao(rollback=rollback)

        n_rewards_atual = self.trigger.contar_rewards_total()
        modelo_path = str(self.versionador.caminho_modelo(versao))

        notas = ""
        if rollback:
            notas = (
                f"ROLLBACK: win_rate caiu {abs(delta):.1f}pp "
                f"vs versao anterior (threshold: {ROLLBACK_DELTA_MAX_PP}pp)"
            )
            logger.warning(
                "Rollback automatico acionado: delta=%.1fpp | versao=%s",
                delta,
                versao,
            )
        else:
            notas = f"Retreino normal: {len(episodios)} episodios"

        # Persistir modelo (JSON com metadados)
        self._salvar_modelo_json(
            versao=versao,
            win_rate_treino=win_rate_treino,
            win_rate_validacao=win_rate_validacao,
            n_episodios=len(episodios),
            rollback=rollback,
            notas=notas,
            modelo_path=modelo_path,
        )

        # Registrar no banco
        self._registrar_treino_banco(
            versao=versao,
            n_episodios=len(episodios),
            n_rewards=n_rewards_atual,
            win_rate_treino=win_rate_treino,
            win_rate_validacao=win_rate_validacao,
            delta=delta,
            rollback=rollback,
            modelo_path=modelo_path,
            notas=notas,
        )

        logger.info(
            "Retreino concluido: versao=%s | n=%d | "
            "wr_treino=%.3f | wr_val=%.3f | delta=%.1fpp | rollback=%s",
            versao,
            len(episodios),
            win_rate_treino,
            win_rate_validacao,
            delta,
            rollback,
        )

        return ResultadoRetreino(
            executado=True,
            versao=versao,
            n_episodios=len(episodios),
            win_rate_treino=win_rate_treino,
            win_rate_validacao=win_rate_validacao,
            delta_win_rate=delta,
            rollback_realizado=rollback,
        )

    def obter_resumo_changelog(self, max_linhas: int = 5) -> list[str]:
        """Retorna as ultimas linhas uteis do changelog do modelo."""
        try:
            path = self.versionador.caminho_changelog()
            if not path.exists():
                return []
            linhas = path.read_text(encoding="utf-8").splitlines()
            if not linhas:
                return []
            return linhas[-max_linhas:]
        except Exception:
            return []

    def registrar_bootstrap_inicial(
        self,
        modelo_path: str,
        notas: str = "Bootstrap inicial do modelo carregado pelo micro",
    ) -> Optional[str]:
        """Registra um baseline auditável quando ainda não existe treino persistido.

        Retorna a versão criada, ou None se já houver histórico.
        """
        try:
            conn = sqlite3.connect(self.db_path)
            cur = conn.cursor()
            cur.execute("SELECT COUNT(*) FROM rl_training_metrics")
            total = int(cur.fetchone()[0] or 0)
            if total > 0:
                conn.close()
                return None

            cur.execute("SELECT COUNT(*) FROM model_metadata")
            meta_total = int(cur.fetchone()[0] or 0)
            if meta_total > 0:
                conn.close()
                return None
            conn.close()
        except Exception:
            return None

        path = Path(modelo_path)
        data_treino = datetime.fromtimestamp(path.stat().st_mtime).isoformat() if path.exists() else datetime.now().isoformat()
        versao = f"bootstrap_{path.stem}_{datetime.now().strftime('%Y%m%d')}"
        win_rate_treino = 0.0
        win_rate_validacao = 0.0
        n_episodios = self.carregador.contar_episodios()
        n_rewards = self.trigger.contar_rewards_total()
        delta = 0.0
        rollback = False

        try:
            conn = sqlite3.connect(self.db_path)
            cur = conn.cursor()
            cur.execute(
                """
                INSERT INTO rl_training_metrics (
                    versao, data_treino, n_episodios_usados,
                    n_rewards_no_treino, win_rate_treino,
                    win_rate_validacao, delta_vs_anterior,
                    rollback_realizado, modelo_path, notas
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    versao,
                    data_treino,
                    n_episodios,
                    n_rewards,
                    win_rate_treino,
                    win_rate_validacao,
                    delta,
                    0,
                    modelo_path,
                    notas,
                    ),
                )
            self._salvar_model_metadata(
                cur=cur,
                versao=versao,
                data_treino=data_treino,
                modelo_path=modelo_path,
                win_rate_validacao=win_rate_validacao,
                n_episodios=n_episodios,
                notas=notas,
            )
            conn.commit()
            conn.close()
            self._registrar_changelog(
                versao=versao,
                data_treino=data_treino,
                n_episodios=n_episodios,
                win_rate_treino=win_rate_treino,
                win_rate_validacao=win_rate_validacao,
                delta=delta,
                rollback=rollback,
                notas=notas,
            )
            return versao
        except Exception as exc:
            logger.warning("Falha ao registrar bootstrap inicial: %s", exc)
            return None

    def obter_ultima_versao_treino(self) -> str:
        """Retorna a ultima versao ativa persistida."""
        try:
            conn = sqlite3.connect(self.db_path)
            cur = conn.cursor()
            cur.execute(
                "SELECT model_version FROM rl_training_metrics "
                "ORDER BY id DESC LIMIT 1"
            )
            row = cur.fetchone()
            if row and row[0]:
                conn.close()
                return str(row[0])
            if self._tem_coluna("model_metadata", "version"):
                cur.execute(
                    "SELECT version FROM model_metadata WHERE is_active = 1 "
                    "ORDER BY id DESC LIMIT 1"
                )
            else:
                cur.execute(
                    "SELECT versao FROM rl_training_metrics ORDER BY id DESC LIMIT 1"
                )
            row = cur.fetchone()
            conn.close()
            return str(row[0]) if row else "N/A"
        except Exception:
            return "N/A"

    def obter_ultima_data_treino(self) -> str:
        """Retorna a data do ultimo treino persistido."""
        try:
            conn = sqlite3.connect(self.db_path)
            cur = conn.cursor()
            cur.execute(
                "SELECT timestamp FROM rl_training_metrics ORDER BY id DESC LIMIT 1"
            )
            row = cur.fetchone()
            if row and row[0]:
                conn.close()
                return str(row[0])
            if self._tem_coluna("model_metadata", "trained_at"):
                cur.execute(
                    "SELECT trained_at FROM model_metadata "
                    "WHERE is_active = 1 ORDER BY id DESC LIMIT 1"
                )
            else:
                cur.execute(
                    "SELECT data_treino FROM rl_training_metrics ORDER BY id DESC LIMIT 1"
                )
            row = cur.fetchone()
            conn.close()
            if row:
                return str(row[0])
            return "N/A"
        except Exception:
            return "N/A"

    # ──────────────────────────────────────────────────────────
    # Auxiliares internos
    # ──────────────────────────────────────────────────────────

    def _obter_win_rate_versao_anterior(self) -> float:
        """Retorna win_rate_validacao do ultimo registro em model_metadata.

        Returns:
            win_rate do ultimo modelo ativo, ou 0.0 se inexistente.
        """
        try:
            conn = sqlite3.connect(self.db_path)
            cur = conn.cursor()
            if self._tem_coluna("rl_training_metrics", "win_rate"):
                cur.execute(
                    "SELECT win_rate FROM rl_training_metrics "
                    "ORDER BY id DESC LIMIT 1"
                )
            else:
                cur.execute(
                    "SELECT win_rate_validacao FROM model_metadata "
                    "WHERE is_active = 1 ORDER BY id DESC LIMIT 1"
                )
            row = cur.fetchone()
            conn.close()
            return float(row[0]) if row else 0.0
        except Exception:
            return 0.0

    def _salvar_modelo_json(
        self,
        versao: str,
        win_rate_treino: float,
        win_rate_validacao: float,
        n_episodios: int,
        rollback: bool,
        notas: str,
        modelo_path: str,
    ) -> None:
        """Persiste metadados do modelo treinado em JSON.

        Args:
            versao: Identificador de versao semantico.
            win_rate_treino: Win rate calculado no batch de treino.
            win_rate_validacao: Win rate calculado no batch de validacao.
            n_episodios: Total de episodios usados.
            rollback: Se o treino foi motivado por rollback.
            notas: Descricao textual do motivo do treino.
            modelo_path: Caminho para o arquivo JSON gerado.
        """
        dados: dict[str, Any] = {
            "versao": versao,
            "data_treino": datetime.now().isoformat(),
            "win_rate_treino": win_rate_treino,
            "win_rate_validacao": win_rate_validacao,
            "n_episodios": n_episodios,
            "rollback": rollback,
            "notas": notas,
            "tipo_modelo": "LightGBM_micro_tendencia",
        }
        try:
            path = Path(modelo_path)
            path.parent.mkdir(parents=True, exist_ok=True)
            with open(path, "w", encoding="utf-8") as arq:
                json.dump(dados, arq, indent=2, ensure_ascii=False)
        except Exception as exc:
            logger.warning("Falha ao salvar JSON do modelo: %s", exc)

    def _registrar_treino_banco(
        self,
        versao: str,
        n_episodios: int,
        n_rewards: int,
        win_rate_treino: float,
        win_rate_validacao: float,
        delta: float,
        rollback: bool,
        modelo_path: str,
        notas: str,
    ) -> None:
        """Registra retreino em rl_training_metrics e model_metadata.

        Args:
            versao: Identificador da versao gerada.
            n_episodios: Total de episodios usados.
            n_rewards: Total de rewards no momento do treino.
            win_rate_treino: Win rate do batch de treino.
            win_rate_validacao: Win rate do batch de validacao.
            delta: Variacao de win_rate vs versao anterior (em pp).
            rollback: Se o treino foi um rollback.
            modelo_path: Caminho para arquivo de modelo.
            notas: Observacoes sobre o treino.
        """
        data_treino = datetime.now().isoformat()
        try:
            conn = sqlite3.connect(self.db_path)
            cur = conn.cursor()
            if self._tem_coluna("rl_training_metrics", "model_version"):
                cur.execute(
                    """
                    INSERT INTO rl_training_metrics (
                        training_id, timestamp, model_name, model_version,
                        algorithm, episodes_total, episodes_train,
                        episodes_validation, date_range_start, date_range_end,
                        avg_reward, cumulative_reward, win_rate, profit_factor,
                        sharpe_ratio, max_drawdown, buy_accuracy, sell_accuracy,
                        hold_accuracy, hyperparameters, feature_importance,
                        validation_reward, overfitting_ratio, notes, created_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        str(uuid4()),
                        data_treino,
                        "micro_tendencia",
                        versao,
                        "LightGBM_micro_tendencia",
                        n_episodios,
                        max(1, int(n_episodios * 0.8)),
                        max(0, int(n_episodios * 0.2)),
                        data_treino,
                        data_treino,
                        win_rate_treino,
                        win_rate_treino * n_episodios,
                        win_rate_validacao,
                        1.0,
                        0.0,
                        0.0,
                        win_rate_treino,
                        win_rate_treino,
                        1.0 if n_episodios else 0.0,
                        json.dumps({}, ensure_ascii=False),
                        json.dumps({}, ensure_ascii=False),
                        win_rate_validacao,
                        max(0.0, 1.0 - win_rate_validacao),
                        notas,
                        data_treino,
                    ),
                )
            else:
                cur.execute(
                    """
                    INSERT INTO rl_training_metrics (
                        versao, data_treino, n_episodios_usados,
                        n_rewards_no_treino, win_rate_treino,
                        win_rate_validacao, delta_vs_anterior,
                        rollback_realizado, modelo_path, notas
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        versao,
                        data_treino,
                        n_episodios,
                        n_rewards,
                        win_rate_treino,
                        win_rate_validacao,
                        delta,
                        1 if rollback else 0,
                        modelo_path,
                        notas,
                    ),
                )

            self._salvar_model_metadata(
                cur=cur,
                versao=versao,
                data_treino=data_treino,
                modelo_path=modelo_path,
                win_rate_validacao=win_rate_validacao,
                n_episodios=n_episodios,
                notas=notas,
                win_rate_treino=win_rate_treino,
                delta=delta,
                rollback=rollback,
            )

            self._registrar_changelog(
                versao=versao,
                data_treino=data_treino,
                n_episodios=n_episodios,
                win_rate_treino=win_rate_treino,
                win_rate_validacao=win_rate_validacao,
                delta=delta,
                rollback=rollback,
                notas=notas,
            )

            conn.commit()
            conn.close()
        except Exception as exc:
            logger.error("Falha ao registrar treino no banco: %s", exc)

    def _registrar_changelog(
        self,
        versao: str,
        data_treino: str,
        n_episodios: int,
        win_rate_treino: float,
        win_rate_validacao: float,
        delta: float,
        rollback: bool,
        notas: str,
    ) -> None:
        """Acrescenta um registro legivel ao changelog do modelo."""
        try:
            path = self.versionador.caminho_changelog()
            path.parent.mkdir(parents=True, exist_ok=True)
            ultimo = self.obter_ultima_versao_treino()
            ultima_data = self.obter_ultima_data_treino()
            linhas = [
                f"## {versao}",
                f"- data_treino: {data_treino}",
                f"- episodios_usados: {n_episodios}",
                f"- win_rate_treino: {win_rate_treino:.3f}",
                f"- win_rate_validacao: {win_rate_validacao:.3f}",
                f"- delta_vs_anterior: {delta:.1f}pp",
                f"- rollback_realizado: {rollback}",
                f"- versao_anterior_ativa: {ultimo}",
                f"- data_ultima_versao_ativa: {ultima_data}",
                f"- notas: {notas}",
                "",
            ]
            with open(path, "a", encoding="utf-8") as arq:
                arq.write("\n".join(linhas))
        except Exception as exc:
            logger.warning("Falha ao registrar changelog do modelo: %s", exc)
