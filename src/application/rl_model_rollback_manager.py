"""
P2-RL-1: Gerenciador de Rollback Automático de Modelo RL

Módulo responsável pela detecção automática de degradação do modelo RL
e execução de rollback para checkpoint anterior quando necessário.

Componentes:
- RollbackReason: Enum das razões para rollback
- RollbackDecision: Dataclass com decisão de rollback
- ModelRollbackManager: Gerenciador principal de rollback

Funcionalidades:
- Detecção de degradação usando BaselineComparator
- Decisão automática de rollback baseada em thresholds
- Execução atômica de rollback com validação
- Persistência de auditoria em JSON
- Histórico de rollbacks para análise
- Proteção contra rollback excessivo (max 1/dia)

Exemplo:
    manager = ModelRollbackManager(
        checkpoint_dir="data/models/novo_agente_rl/modelo_final",
        config_path="config/rl_rollback_config.json"
    )

    decision = manager.check_degradation(
        current_metrics={"win_rate": 60.0, "sharpe": 0.8},
        baseline_metrics={"win_rate": 65.0, "sharpe": 1.2}
    )

    if decision.deve_fazer_rollback:
        sucesso = manager.executar_rollback("checkpoint_best")
        if sucesso:
            print("Rollback executado com sucesso!")
"""

import json
import shutil
from dataclasses import dataclass, asdict
from datetime import datetime, timedelta
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional


# ============================================================================
# ENUMS
# ============================================================================


class RollbackReason(str, Enum):
    """Razões para triggering de rollback."""

    DEGRADACAO_WIN_RATE = "degradacao_win_rate"
    SHARPE_NEGATIVO = "sharpe_negativo"
    F1_DEGRADACAO = "f1_degradacao"
    ERRO_CARREGAMENTO = "erro_carregamento"
    OK = "ok"


# ============================================================================
# DATACLASSES
# ============================================================================


@dataclass
class RollbackDecision:
    """Decisão de rollback baseada em análise de degradação.

    Atributos:
        deve_fazer_rollback: Se rollback é recomendado
        razao: Enum da razão para rollback (RollbackReason)
        versao_rollback: Nome do checkpoint para rollback (ex: "checkpoint_best")
        metricas_atuais: Métricas atuais de performance
        metricas_baseline: Métricas de baseline para comparação
        timestamp: Timestamp ISO 8601 da decisão
        recomendacao: Texto descritivo da recomendação
        delta_win_rate: Delta de win_rate (% negativo = degradação)
        confidence: Confiança da decisão (0.0 a 1.0)
    """

    deve_fazer_rollback: bool
    razao: str
    versao_rollback: Optional[str]
    metricas_atuais: Dict[str, float]
    metricas_baseline: Dict[str, float]
    timestamp: str
    recomendacao: str
    delta_win_rate: float
    confidence: float = 1.0

    def para_dict(self) -> Dict[str, Any]:
        """Converte para dicionário para persistência."""
        return asdict(self)


# ============================================================================
# GERENCIADOR DE ROLLBACK
# ============================================================================


class ModelRollbackManager:
    """Gerenciador de rollback automático de modelo RL.

    Responsabilidades:
    - Detectar degradação de métricas via check_degradation()
    - Decidir se rollback é necessário
    - Executar rollback atômico com validação
    - Manter histórico de rollbacks
    - Persistir auditoria em JSON
    - Bloquear rollbacks excessivos (max 1 por dia)

    Exemplo:
        manager = ModelRollbackManager(
            checkpoint_dir="data/models/novo_agente_rl/modelo_final",
            config_path="config/rl_rollback_config.json"
        )
        decision = manager.check_degradation(current, baseline)
        if decision.deve_fazer_rollback:
            manager.executar_rollback("checkpoint_best")
    """

    def __init__(
        self, checkpoint_dir: str, config_path: str = "config/rl_rollback_config.json"
    ) -> None:
        """Inicializa o gerenciador de rollback.

        Args:
            checkpoint_dir: Diretório com checkpoints do modelo
            config_path: Caminho para arquivo de configuração JSON

        Raises:
            FileNotFoundError: Se diretório de checkpoint não existir
            ValueError: Se configuração inválida
        """
        self.checkpoint_dir = Path(checkpoint_dir)
        self.config_path = Path(config_path)

        if not self.checkpoint_dir.exists():
            raise FileNotFoundError(
                f"Diretório de checkpoint não existe: {self.checkpoint_dir}"
            )

        # Carregar configuração
        self.config = self._carregar_config()

        # Histórico de rollbacks
        self.historico_rollbacks: List[RollbackDecision] = []
        self.ultimo_rollback_timestamp: Optional[str] = None

        # Diretório de logs
        self.log_dir = Path("data/logs")
        self.log_dir.mkdir(parents=True, exist_ok=True)

        # Carregar histórico anterior
        self._carregar_historico()

    def _carregar_config(self) -> Dict[str, Any]:
        """Carrega configuração do arquivo ou usa padrões.

        Returns:
            Dict com configuração

        Raises:
            ValueError: Se arquivo de config inválido
        """
        padroes = {
            "win_rate_threshold_pct": 5.0,
            "sharpe_threshold": -0.5,
            "f1_threshold": 0.05,
            "rolling_window_trades": 50,
            "max_rollback_frequency_hours": 24,
            "notification_slack": False,
            "log_file": "data/logs/rl_rollback.log",
        }

        # Se arquivo existe, carregar
        if self.config_path.exists():
            try:
                with open(self.config_path, "r", encoding="utf-8") as f:
                    config_arquivo = json.load(f)
                # Mesclar com padrões
                return {**padroes, **config_arquivo}
            except (json.JSONDecodeError, IOError) as e:
                raise ValueError(f"Erro ao carregar config: {e}")

        return padroes

    def _carregar_historico(self) -> None:
        """Carrega histórico anterior de rollbacks de arquivo JSON."""
        historico_file = self.log_dir / "rl_rollback_history.json"

        if not historico_file.exists():
            self.historico_rollbacks = []
            return

        try:
            with open(historico_file, "r", encoding="utf-8") as f:
                historico_dict = json.load(f)

            self.historico_rollbacks = [
                RollbackDecision(
                    deve_fazer_rollback=item["deve_fazer_rollback"],
                    razao=item["razao"],
                    versao_rollback=item["versao_rollback"],
                    metricas_atuais=item["metricas_atuais"],
                    metricas_baseline=item["metricas_baseline"],
                    timestamp=item["timestamp"],
                    recomendacao=item["recomendacao"],
                    delta_win_rate=item["delta_win_rate"],
                    confidence=item.get("confidence", 1.0),
                )
                for item in historico_dict
            ]

            # Carregar timestamp do último rollback
            rollbacks_executados = [
                r for r in self.historico_rollbacks if r.deve_fazer_rollback
            ]
            if rollbacks_executados:
                self.ultimo_rollback_timestamp = rollbacks_executados[-1].timestamp
        except (json.JSONDecodeError, IOError, KeyError):
            self.historico_rollbacks = []

    def check_degradation(
        self,
        current_metrics: Dict[str, float],
        baseline_metrics: Dict[str, float],
    ) -> RollbackDecision:
        """Verifica degradação de métricas e retorna decisão de rollback.

        Aplica thresholds configurados para detectar:
        - Queda em win_rate > threshold
        - Sharpe negativo
        - F1 score degradado

        Args:
            current_metrics: Métricas atuais {win_rate, sharpe, f1}
            baseline_metrics: Métricas de baseline para comparação

        Returns:
            RollbackDecision com recomendação

        Raises:
            ValueError: Se métricas inválidas
        """
        # Validar entrada
        if not isinstance(current_metrics, dict) or not isinstance(
            baseline_metrics, dict
        ):
            raise ValueError("Métricas devem ser dicionários")

        # Extrair métricas
        win_rate_atual = current_metrics.get("win_rate", 0.0)
        win_rate_baseline = baseline_metrics.get("win_rate", 0.0)
        sharpe_atual = current_metrics.get("sharpe", 0.0)
        f1_atual = current_metrics.get("f1", 0.0)
        f1_baseline = baseline_metrics.get("f1", 0.0)

        # Calcular deltas
        delta_win_rate = win_rate_atual - win_rate_baseline

        # Análise de degradação (3 critérios)
        win_rate_degradado = (
            delta_win_rate <= -self.config["win_rate_threshold_pct"]
        )
        sharpe_degradado = sharpe_atual < self.config["sharpe_threshold"]
        f1_degradado = f1_baseline > 0 and (
            (f1_baseline - f1_atual) >= self.config["f1_threshold"]
        )

        # Determinar razão e ação
        deve_fazer_rollback = win_rate_degradado or sharpe_degradado or f1_degradado

        if win_rate_degradado:
            razao = RollbackReason.DEGRADACAO_WIN_RATE.value
        elif sharpe_degradado:
            razao = RollbackReason.SHARPE_NEGATIVO.value
        elif f1_degradado:
            razao = RollbackReason.F1_DEGRADACAO.value
        else:
            razao = RollbackReason.OK.value

        # Versão para rollback
        versao_rollback = "checkpoint_best" if deve_fazer_rollback else None

        # Recomendação
        if deve_fazer_rollback:
            recomendacao = (
                f"ROLLBACK RECOMENDADO: {razao.upper()} "
                f"(delta_wr={delta_win_rate:.2f}%, sharpe={sharpe_atual:.2f})"
            )
            confidence = 0.95
        else:
            recomendacao = "CONTINUAR OPERACAO NORMAL"
            confidence = 0.95

        # Criar decisão
        decision = RollbackDecision(
            deve_fazer_rollback=deve_fazer_rollback,
            razao=razao,
            versao_rollback=versao_rollback,
            metricas_atuais=current_metrics,
            metricas_baseline=baseline_metrics,
            timestamp=datetime.utcnow().isoformat(),
            recomendacao=recomendacao,
            delta_win_rate=delta_win_rate,
            confidence=confidence,
        )

        # Registrar no histórico
        self.historico_rollbacks.append(decision)

        return decision

    def executar_rollback(self, alvo: str) -> bool:
        """Executa rollback para checkpoint especificado.

        Passos:
        1. Validar checkpoint existe
        2. Validar integridade (tamanho > 0)
        3. Backup do modelo atual
        4. Carregar novo modelo
        5. Persistir auditoria
        6. Log de sucesso

        Args:
            alvo: Nome do checkpoint (ex: "checkpoint_best")

        Returns:
            True se rollback bem-sucedido, False caso contrário

        Raises:
            FileNotFoundError: Se checkpoint não existe
            IOError: Se erro ao copiar/carregar arquivo
        """
        # Verificar proteção contra rollback excessivo
        if not self._pode_fazer_rollback():
            print(
                f"Rollback bloqueado: máximo 1 por {self.config['max_rollback_frequency_hours']}h"
            )
            return False

        # Construir caminhos
        checkpoint_source = self.checkpoint_dir / f"{alvo}.pkl"
        checkpoint_current = self.checkpoint_dir / "checkpoint_current.pkl"
        checkpoint_backup = self.checkpoint_dir / "checkpoint_backup.pkl"

        # Validar checkpoint existe
        if not checkpoint_source.exists():
            print(f"Erro: Checkpoint não encontrado: {checkpoint_source}")
            return False

        # Validar tamanho (deve ter pelo menos 1KB)
        if checkpoint_source.stat().st_size < 1024:
            print(f"Erro: Checkpoint inválido (tamanho < 1KB): {checkpoint_source}")
            return False

        try:
            # Fazer backup do checkpoint atual
            if checkpoint_current.exists():
                shutil.copy2(checkpoint_current, checkpoint_backup)
                print(f"Backup criado: {checkpoint_backup}")

            # Copiar novo checkpoint
            shutil.copy2(checkpoint_source, checkpoint_current)
            print(f"Rollback executado: {alvo} → {checkpoint_current}")

            # Atualizar timestamp
            self.ultimo_rollback_timestamp = datetime.utcnow().isoformat()

            # Persistir auditoria
            self._persistir_auditoria(alvo, sucesso=True)

            return True

        except (IOError, OSError) as e:
            print(f"Erro ao executar rollback: {e}")
            self._persistir_auditoria(alvo, sucesso=False, erro=str(e))
            return False

    def _pode_fazer_rollback(self) -> bool:
        """Verifica se é permitido fazer rollback agora.

        Bloqueia se houver rollback dentro das últimas N horas.

        Returns:
            True se permitido, False se muito recente
        """
        if not self.ultimo_rollback_timestamp:
            return True

        ultima_vez = datetime.fromisoformat(self.ultimo_rollback_timestamp)
        horas_decorridas = (datetime.utcnow() - ultima_vez).total_seconds() / 3600
        max_frequencia = self.config["max_rollback_frequency_hours"]

        return horas_decorridas >= max_frequencia

    def _persistir_auditoria(
        self, alvo: str, sucesso: bool, erro: Optional[str] = None
    ) -> None:
        """Persiste auditoria de rollback em arquivo JSON.

        Args:
            alvo: Nome do checkpoint de destino
            sucesso: Se rollback foi bem-sucedido
            erro: Mensagem de erro (se houver)
        """
        auditoria = {
            "timestamp": datetime.utcnow().isoformat(),
            "alvo": alvo,
            "sucesso": sucesso,
            "erro": erro,
        }

        auditoria_file = self.log_dir / "rl_rollback_audit.jsonl"

        try:
            with open(auditoria_file, "a", encoding="utf-8") as f:
                f.write(json.dumps(auditoria, ensure_ascii=False) + "\n")
        except IOError as e:
            print(f"Aviso: Não foi possível salvar auditoria: {e}")

    def obter_historico_rollbacks(self, limite: int = 10) -> List[RollbackDecision]:
        """Retorna histórico de últimos N rollbacks.

        Args:
            limite: Número máximo de rollbacks a retornar (padrão 10)

        Returns:
            Lista de RollbackDecision ordenada por timestamp (mais recente primeiro)
        """
        return sorted(
            self.historico_rollbacks,
            key=lambda d: d.timestamp,
            reverse=True,
        )[:limite]

    def gerar_relatorio(self, formato: str = "json") -> str:
        """Gera relatório do status e histórico de rollbacks.

        Args:
            formato: "json" ou "markdown"

        Returns:
            String com relatório formatado

        Raises:
            ValueError: Se formato inválido
        """
        if formato not in ("json", "markdown"):
            raise ValueError(f"Formato inválido: {formato}")

        if formato == "json":
            return self._gerar_relatorio_json()
        else:
            return self._gerar_relatorio_markdown()

    def _gerar_relatorio_json(self) -> str:
        """Gera relatório em formato JSON."""
        relatorio = {
            "timestamp": datetime.utcnow().isoformat(),
            "total_rollbacks": len(
                [r for r in self.historico_rollbacks if r.deve_fazer_rollback]
            ),
            "ultimo_rollback": self.ultimo_rollback_timestamp,
            "pode_fazer_rollback_agora": self._pode_fazer_rollback(),
            "historico_ultimos_10": [
                r.para_dict() for r in self.obter_historico_rollbacks(10)
            ],
        }
        return json.dumps(relatorio, indent=2, ensure_ascii=False)

    def _gerar_relatorio_markdown(self) -> str:
        """Gera relatório em formato Markdown."""
        ultimosAcoes = self.obter_historico_rollbacks(5)

        md = "# Relatorio de Rollback de Modelo RL\n\n"
        md += f"**Timestamp:** {datetime.utcnow().isoformat()}\n\n"
        md += f"**Total de Rollbacks:** {len([r for r in self.historico_rollbacks if r.deve_fazer_rollback])}\n\n"
        md += f"**Ultimo Rollback:** {self.ultimo_rollback_timestamp or 'Nenhum'}\n\n"
        md += f"**Pode fazer rollback agora:** {'Sim' if self._pode_fazer_rollback() else 'Nao'}\n\n"

        md += "## Ultimos Eventos\n\n"
        md += "| Timestamp | Razao | Acao | Win Rate Delta |\n"
        md += "|-----------|-------|------|----------------|\n"

        for decision in ultimosAcoes:
            acao = "ROLLBACK" if decision.deve_fazer_rollback else "CONTINUA"
            md += (
                f"| {decision.timestamp[:19]} | {decision.razao} | "
                f"{acao} | {decision.delta_win_rate:+.2f}% |\n"
            )

        return md

    def salvar_historico(self) -> None:
        """Salva histórico de rollbacks em arquivo JSON."""
        historico_file = self.log_dir / "rl_rollback_history.json"

        try:
            historico_data = [d.para_dict() for d in self.historico_rollbacks]
            with open(historico_file, "w", encoding="utf-8") as f:
                json.dump(historico_data, f, indent=2, ensure_ascii=False)
        except IOError as e:
            print(f"Aviso: Não foi possível salvar histórico: {e}")
