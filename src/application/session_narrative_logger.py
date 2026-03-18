"""
SessionNarrativeLogger - Logs Narrativos Auditáveis de Sessão.

Responsabilidades:
- Registrar narrativa estruturada de sessão do INICIAR_MICRO_TENDENCIA_AUTO_TRADE
- Captura: sinais (AC5.8), feedback (AC5.9), drift (AC6.7),
  online learning (AC6.8), baseline (AC6.9)
- Persistência: arquivo JSON diário em outputs/micro_tendencia_YYYYMMDD.json
- Rotação: não crescer indefinidamente, limpeza de logs antigos configurável

Pipeline:
    AC5.8: TradeExecutor emite sinal
    → SessionNarrativeLogger.registrar_sinal()
    → AC5.9: FeedbackValidator emite health
    → SessionNarrativeLogger.registrar_feedback()
    → AC6.7-6.9: ML engine emite alerts
    → SessionNarrativeLogger.registrar_drift/learning/baseline()
    → Gravar arquivo JSON consolidado

Status: Implementação v1.0 (18/03/2026)
Referência: docs/BACKLOG.md (ROADMAP-MICRO-01)
"""

import json
from dataclasses import asdict, dataclass, field
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional


@dataclass(frozen=True)
class NarrativeEntry:
    """
    Uma entrada individual no log narrativo.

    Campos:
        timestamp: Momento do evento (ISO 8601)
        tipo: Categoria (SINAL, FEEDBACK, DRIFT, LEARNING, BASELINE, INICIO, FIM)
        descricao: Texto legível do evento
        detalhes: Dicionário com dados estruturados

    Status: v1.0 (18/03/2026)
    """

    timestamp: datetime
    tipo: str
    descricao: str
    detalhes: Dict[str, Any] = field(default_factory=dict)

    def para_dict(self) -> Dict[str, Any]:
        """
        Converte para dicionário JSON-serializável.

        Returns:
            Dict com timestamp em ISO 8601 e demais campos

        Status: v1.0
        """
        return {
            "timestamp": self.timestamp.isoformat(),
            "tipo": self.tipo,
            "descricao": self.descricao,
            "detalhes": self.detalhes,
        }


class SessionNarrativeLogger:
    """
    Gerenciador centralizado de logs narrativos de sessão.

    Acumula entradas durante execução e persiste em arquivo JSON
    no final da sessão ou periodicamente.

    Responsabilidades:
    - Registrar sinais, feedback, drift, learning, baseline
    - Manter entradas ordenadas por timestamp
    - Gerar sumários estatísticos
    - Persistir arquivo JSON com metadados

    Status: v1.0 (18/03/2026)
    """

    def __init__(
        self,
        session_id: str,
        output_dir: str,
    ) -> None:
        """
        Inicializa logger de narrativa.

        Args:
            session_id: Identificador único da sessão
                (ex: "micro_20260318_103045")
            output_dir: Diretório onde gravar arquivos JSON
                (ex: "outputs/")

        Status: v1.0
        """
        self.session_id: str = session_id
        self.output_dir: str = output_dir
        self.data_sessao: datetime = datetime.now()
        self.entradas: List[NarrativeEntry] = []

    def registrar_sinal(
        self,
        timestamp: datetime,
        direcao: str,
        preco: float,
        confianca: float,
    ) -> None:
        """
        Registra sinal de compra/venda detectado.

        Args:
            timestamp: Momento do sinal
            direcao: "BUY", "SELL" ou "HOLD"
            preco: Preço do sinal (ex: 142500.0)
            confianca: Confiança ML (0-100)

        Status: v1.0
        """
        descricao = f"Sinal {direcao} em {preco:.0f} (confiança {confianca:.0f}%)"
        entry = NarrativeEntry(
            timestamp=timestamp,
            tipo="SINAL",
            descricao=descricao,
            detalhes={
                "direcao": direcao,
                "preco": preco,
                "confianca": confianca,
            },
        )
        self.entradas.append(entry)

    def registrar_feedback(
        self,
        timestamp: datetime,
        status: str,
        win_rate: float,
        trades_count: int,
    ) -> None:
        """
        Registra resultado de ciclo feedback (AC5.9).

        Args:
            timestamp: Momento da validação
            status: "HEALTHY", "WARNING" ou "CRITICAL"
            win_rate: Taxa de ganho (%)
            trades_count: Número de trades no período

        Status: v1.0
        """
        descricao = (
            f"Feedback AC5.9: {status} | "
            f"{trades_count} trades | "
            f"Win rate {win_rate:.1f}%"
        )
        entry = NarrativeEntry(
            timestamp=timestamp,
            tipo="FEEDBACK",
            descricao=descricao,
            detalhes={
                "status": status,
                "win_rate": win_rate,
                "trades_count": trades_count,
            },
        )
        self.entradas.append(entry)

    def registrar_drift(
        self,
        timestamp: datetime,
        metrica: str,
        valor_esperado: float,
        valor_atual: float,
        severidade: str,
    ) -> None:
        """
        Registra detecção de drift em modelo (AC6.7).

        Args:
            timestamp: Momento da detecção
            metrica: Qual métrica degradou (ex: "win_rate", "sharpe")
            valor_esperado: Valor baseline esperado
            valor_atual: Valor observado
            severidade: "ALERTA" ou "CRITICO"

        Status: v1.0
        """
        diferenca_pct = (
            ((valor_atual - valor_esperado) / valor_esperado * 100)
            if valor_esperado != 0
            else 0
        )
        descricao = (
            f"Drift AC6.7: {metrica} degradado {severidade} | "
            f"esperado {valor_esperado:.2f}, "
            f"obtido {valor_atual:.2f} "
            f"({diferenca_pct:+.1f}%)"
        )
        entry = NarrativeEntry(
            timestamp=timestamp,
            tipo="DRIFT",
            descricao=descricao,
            detalhes={
                "metrica": metrica,
                "valor_esperado": valor_esperado,
                "valor_atual": valor_atual,
                "severidade": severidade,
                "diferenca_pct": diferenca_pct,
            },
        )
        self.entradas.append(entry)

    def registrar_online_learning(
        self,
        timestamp: datetime,
        tipo_trigger: str,
        modelo_versao_anterior: str,
        modelo_versao_nova: str,
    ) -> None:
        """
        Registra acionamento de online learning (AC6.8).

        Args:
            timestamp: Momento do trigger
            tipo_trigger: "drift_detector", "manual", etc
            modelo_versao_anterior: Versão antes (ex: "v1.0.0")
            modelo_versao_nova: Versão depois (ex: "v1.0.1")

        Status: v1.0
        """
        descricao = (
            f"Online learning AC6.8 acionado ({tipo_trigger}) | "
            f"{modelo_versao_anterior} → {modelo_versao_nova}"
        )
        entry = NarrativeEntry(
            timestamp=timestamp,
            tipo="LEARNING",
            descricao=descricao,
            detalhes={
                "tipo_trigger": tipo_trigger,
                "modelo_versao_anterior": modelo_versao_anterior,
                "modelo_versao_nova": modelo_versao_nova,
            },
        )
        self.entradas.append(entry)

    def registrar_baseline_comparison(
        self,
        timestamp: datetime,
        metricas_atuais: Dict[str, float],
        metricas_baseline: Dict[str, float],
        recomendacao: str,
    ) -> None:
        """
        Registra comparação vs baseline (AC6.9).

        Args:
            timestamp: Momento da comparação
            metricas_atuais: Métricas do modelo atual
                (ex: {"win_rate": 65.0, "sharpe": 1.2})
            metricas_baseline: Métricas esperadas
                (ex: {"win_rate": 62.0, "sharpe": 1.0})
            recomendacao: "MANTER", "ROLLBACK", etc

        Status: v1.0
        """
        descricao = (
            f"Baseline AC6.9: {recomendacao} | "
            f"Atual: {metricas_atuais} vs "
            f"Baseline: {metricas_baseline}"
        )
        entry = NarrativeEntry(
            timestamp=timestamp,
            tipo="BASELINE",
            descricao=descricao,
            detalhes={
                "metricas_atuais": metricas_atuais,
                "metricas_baseline": metricas_baseline,
                "recomendacao": recomendacao,
            },
        )
        self.entradas.append(entry)

    def registrar_evento_sessao(
        self,
        timestamp: datetime,
        tipo: str,
        detalhes: Dict[str, Any],
    ) -> None:
        """
        Registra evento de sessão (INICIO, FIM, etc).

        Args:
            timestamp: Momento do evento
            tipo: "INICIO" ou "FIM"
            detalhes: Metadados do evento

        Status: v1.0
        """
        descricao = f"Sessão {tipo} em {timestamp.isoformat()}"
        entry = NarrativeEntry(
            timestamp=timestamp,
            tipo=tipo,
            descricao=descricao,
            detalhes=detalhes,
        )
        self.entradas.append(entry)

    def gerar_sumario(self) -> Dict[str, Any]:
        """
        Gera sumário consolidado da sessão.

        Retorna:
            Dict com contagem de sinais BUY/SELL/HOLD, total entradas, etc

        Status: v1.0
        """
        contagem_tipos: Dict[str, int] = {}
        sinais_by_direcao: Dict[str, int] = {"BUY": 0, "SELL": 0, "HOLD": 0}

        for entrada in self.entradas:
            contagem_tipos[entrada.tipo] = contagem_tipos.get(entrada.tipo, 0) + 1

            if entrada.tipo == "SINAL":
                direcao = entrada.detalhes.get("direcao", "HOLD")
                sinais_by_direcao[direcao] = sinais_by_direcao.get(direcao, 0) + 1

        return {
            "total_entradas": len(self.entradas),
            "sinais_buy": sinais_by_direcao["BUY"],
            "sinais_sell": sinais_by_direcao["SELL"],
            "sinais_hold": sinais_by_direcao["HOLD"],
            "contagem_tipos": contagem_tipos,
        }

    def gravar_arquivo_log(self) -> Path:
        """
        Persiste entradas em arquivo JSON.

        Nome: outputs/micro_tendencia_YYYYMMDD.json

        Returns:
            Path do arquivo gravado

        Status: v1.0
        """
        self.entradas.sort(key=lambda e: e.timestamp)

        sumario = self.gerar_sumario()

        dados = {
            "session_id": self.session_id,
            "data_sessao": self.data_sessao.date().isoformat(),
            "timestamp_inicio": self.data_sessao.isoformat(),
            "timestamp_atualizacao": datetime.now().isoformat(),
            "total_entradas": len(self.entradas),
            "entradas": [e.para_dict() for e in self.entradas],
            "sumario": sumario,
        }

        nome_arquivo = (
            f"micro_tendencia_{self.data_sessao.strftime('%Y%m%d')}.json"
        )
        arquivo = Path(self.output_dir) / nome_arquivo

        arquivo.parent.mkdir(parents=True, exist_ok=True)

        with open(arquivo, "w", encoding="utf-8") as f:
            json.dump(dados, f, ensure_ascii=False, indent=2)

        return arquivo


class DailyLogRotator:
    """
    Gerenciador de rotação diária de logs narrativos.

    Responsabilidades:
    - Não deixar arquivo crescer indefinidamente
    - Gerar novo arquivo a cada data
    - Limpar logs antigos conforme política de retenção

    Status: v1.0 (18/03/2026)
    """

    def __init__(self, output_dir: str) -> None:
        """
        Inicializa rotator de logs.

        Args:
            output_dir: Diretório onde estão os logs (ex: "outputs/")

        Status: v1.0
        """
        self.output_dir = output_dir

    def gerar_nome_arquivo(self, data: datetime) -> str:
        """
        Gera nome de arquivo de log para uma data.

        Args:
            data: Data desejada

        Returns:
            Nome do arquivo (ex: "micro_tendencia_20260318.json")

        Status: v1.0
        """
        return f"micro_tendencia_{data.strftime('%Y%m%d')}.json"

    def limpar_logs_antigos(self, dias_retencao: int = 7) -> None:
        """
        Limpa logs com mais de N dias.

        Args:
            dias_retencao: Quantos dias manter (padrão: 7 dias)

        Status: v1.0
        """
        output_path = Path(self.output_dir)
        if not output_path.exists():
            return

        data_limite = datetime.now() - timedelta(days=dias_retencao)

        for arquivo in output_path.glob("micro_tendencia_*.json"):
            try:
                # Extrair data do nome do arquivo
                nome_sem_ext = arquivo.stem.replace("micro_tendencia_", "")
                data_arquivo = datetime.strptime(nome_sem_ext, "%Y%m%d")

                if data_arquivo < data_limite:
                    arquivo.unlink()
            except (ValueError, OSError):
                pass
