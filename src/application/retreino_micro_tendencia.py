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

logger = logging.getLogger("retreino_micro_tendencia")

# ─────────────────────────────────────────────
# Constantes de threshold
# ─────────────────────────────────────────────
THRESHOLD_REWARDS_NOVO_TREINO: int = 200
JANELA_EPISODIOS: int = 500
ROLLBACK_DELTA_MAX_PP: float = 5.0  # porcentagem
WIN_RATE_MINIMO_VALIDACAO: float = 0.40


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
        """Retorna n_rewards_no_treino do ultimo registro em rl_training_metrics.

        Returns:
            n_rewards do ultimo treino, ou 0 se nunca treinou.
        """
        try:
            conn = sqlite3.connect(self.db_path)
            cur = conn.cursor()
            cur.execute(
                "SELECT n_rewards_no_treino FROM rl_training_metrics "
                "ORDER BY id DESC LIMIT 1"
            )
            row = cur.fetchone()
            conn.close()
            return int(row[0]) if row else 0
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

    def deve_retreinar(self) -> bool:
        """Verifica se threshold foi atingido para disparar retreino.

        Returns:
            True se novos_rewards >= threshold.
        """
        return self.novos_rewards_desde_ultimo_treino() >= self.threshold


# ─────────────────────────────────────────────
# Carregador de episodios
# ─────────────────────────────────────────────


class CarregadorEpisodios:
    """Carrega episodios de micro_episodios com janela deslizante.

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
        """Carrega os ultimos N episodios de micro_episodios.

        Returns:
            Lista de dicts com outcome, pnl, timestamp, confianca,
            macro_score, direction, peso.
        """
        try:
            conn = sqlite3.connect(self.db_path)
            cur = conn.cursor()
            cur.execute(
                """
                SELECT outcome, resultado_pts, timestamp_saida,
                       confianca, macro_score, direcao
                FROM micro_episodios
                WHERE outcome IS NOT NULL
                ORDER BY timestamp_entrada DESC
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
            episodios.append(
                {
                    "outcome": row[0] or "BREAKEVEN",
                    "pnl": float(row[1] or 0.0),
                    "timestamp": row[2] or "",
                    "confianca": float(row[3] or 0.0),
                    "macro_score": int(row[4] or 0),
                    "direction": row[5] or "",
                    "peso": round(peso, 4),
                }
            )
        return episodios

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
            cur.execute(
                "SELECT win_rate_validacao FROM model_metadata "
                "WHERE ativo = 1 ORDER BY id DESC LIMIT 1"
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

            # Inserir em rl_training_metrics
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

            # Desativar versoes anteriores
            cur.execute(
                "UPDATE model_metadata SET ativo = 0"
            )

            # Inserir nova versao em model_metadata
            cur.execute(
                """
                INSERT INTO model_metadata (
                    versao, data_treino, modelo_path,
                    win_rate_validacao, n_episodios, ativo, notas
                ) VALUES (?, ?, ?, ?, ?, 1, ?)
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

            conn.commit()
            conn.close()
        except Exception as exc:
            logger.error("Falha ao registrar treino no banco: %s", exc)
