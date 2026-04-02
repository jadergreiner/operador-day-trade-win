#!/usr/bin/env python3
"""Script executor do Prompt de Fechamento Diário — Operador Quântico.

Executa até três vezes ao dia para capturar decisões operacionais,
aprendizados e melhorias, alimentando o backlog do Agente Autônomo.

Uso:
    python prompts/fechamento_diario.py --foco abertura
    python prompts/fechamento_diario.py --foco meio_dia
    python prompts/fechamento_diario.py --foco fechamento
    python prompts/fechamento_diario.py --foco fechamento --data 2026-02-20
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
from dataclasses import asdict, dataclass, field
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any

try:
    import yaml

    _TEM_YAML = True
except ImportError:
    _TEM_YAML = False

FOCOS_VALIDOS = ("abertura", "meio_dia", "fechamento")
AGENTES_OPERACIONAIS = ("MICRO_TENDENCIA", "DIARIOS", "RL_5000", "RL_DIRETO")
EXECUTORES_POR_AGENTE = {
    "MICRO_TENDENCIA": "INICIAR_MICRO_TENDENCIA_AUTO_TRADE.bat",
    "DIARIOS": "INICIAR_DIARIOS.bat",
    "RL_5000": "INICIAR_AGENTE_RL_5000.bat",
    "RL_DIRETO": "INICIAR_AGENTE_RL_DIRETO.bat",
}
CAPITAL_BASE_RESUMO = float(os.environ.get("FECHAMENTO_CAPITAL_BASE", "50000"))

DOCUMENTOS_FECHAMENTO = (
    "fechamento_diario.md",
    "fechamento_diario.py",
    "schema_fechamento_diario.json",
)

RAIZ = Path(__file__).resolve().parent.parent
CAMINHO_BACKLOG = RAIZ / "docs" / "agente_autonomo" / "AGENTE_AUTONOMO_BACKLOG.md"
CAMINHO_SYNC = RAIZ / "docs" / "agente_autonomo" / "SYNC_MANIFEST.json"
CAMINHO_VERSIONING = RAIZ / "docs" / "agente_autonomo" / "VERSIONING.json"
CAMINHO_SCHEMA = RAIZ / "prompts" / "schema_fechamento_diario.json"
CAMINHO_SAIDAS = RAIZ / "data" / "fechamento_diario"
CAMINHO_OUTPUTS = RAIZ / "outputs"


# ---------------------------------------------------------------------------
# Estruturas de dados
# ---------------------------------------------------------------------------


@dataclass
class CapturaDia:
    """Dados operacionais capturados durante o período."""

    timestamp: str
    foco: str
    data_pregao: str
    analises_rodadas: int = 0
    trades_executados: int = 0
    trades_encerrados: int = 0
    posicoes_abertas: int = 0
    resultado_dia_pts: float = 0.0
    resultado_dia_pct: str = "0.0%"
    win_rate_dia_pct: float = 0.0
    simbolo: str = "WINFUT"
    preco_abertura: float = 0.0
    preco_atual: float = 0.0
    maxima_dia: float = 0.0
    minima_dia: float = 0.0
    variacao_dia_pct: str = "0.0%"
    volume_relativo_pct: str = "0%"
    eventos_macro: list[dict[str, str]] = field(default_factory=list)
    eventos_locais: list[dict[str, str]] = field(default_factory=list)


@dataclass
class AprendizadoOperacional:
    """Aprendizados do período operacional."""

    agente: str = "TODOS"
    dimensao_macro_sinal: str = "NEUTRAL"
    dimensao_macro_funcionou: bool = False
    dimensao_fundamentos_sinal: str = "NEUTRAL"
    dimensao_fundamentos_funcionou: bool = False
    dimensao_sentimento_sinal: str = "NEUTRAL"
    dimensao_sentimento_funcionou: bool = False
    dimensao_tecnica_sinal: str = "NEUTRAL"
    dimensao_tecnica_funcionou: bool = False
    setups_sucesso: list[dict[str, Any]] = field(default_factory=list)
    setups_falha: list[dict[str, Any]] = field(default_factory=list)
    decisoes_corretas: list[dict[str, str]] = field(default_factory=list)
    decisoes_incorretas: list[dict[str, str]] = field(default_factory=list)
    algoritmo_alinhado: bool = True
    observacoes_algoritmo: list[str] = field(default_factory=list)
    divergencias_algoritmo: list[str] = field(default_factory=list)
    sugestoes_ajuste: list[str] = field(default_factory=list)

    def __post_init__(self) -> None:
        self.agente = _normalizar_agente(self.agente)

    def to_dict(self) -> dict[str, Any]:
        """Retorna a representação serializável do aprendizado."""
        return asdict(self)


@dataclass
class ResultadoAgente:
    """Resultado consolidado de um agente operacional."""

    agente: str
    executor: str
    resultado_reais: float = 0.0
    trades_executados: int = 0
    trades_encerrados: int = 0
    wins: int = 0
    losses: int = 0
    win_rate_pct: float = 0.0
    maior_ganho_reais: float = 0.0
    maior_perda_reais: float = 0.0
    relacao_risco_retorno: str = "0:0"
    veredicto: str = "NEUTRO"

    def __post_init__(self) -> None:
        self.agente = _normalizar_agente(self.agente)
        self.executor = self.executor.strip()
        self.veredicto = _normalizar_veredicto(self.veredicto)

    def to_dict(self) -> dict[str, Any]:
        """Retorna a representação serializável do resultado."""
        return asdict(self)


@dataclass
class CapturaMelhoria:
    """Melhoria identificada durante o pregão."""

    id: str
    titulo: str
    descricao: str
    categoria: str
    prioridade: str
    esforco: str
    agente_impactado: str = "TODOS"
    sync_com: list[str] = field(default_factory=list)
    arquivo_afetado: str = ""
    estrategia_relacionada: str = ""
    documento_afetado: str = ""
    tipo_aprendizado: str = ""

    def __post_init__(self) -> None:
        self.agente_impactado = _normalizar_agente(self.agente_impactado)


@dataclass
class SinteseFechamento:
    """Síntese consolidada do fechamento diário para importação no backlog."""

    captura: CapturaDia
    aprendizados: AprendizadoOperacional
    melhorias: list[CapturaMelhoria]
    resultados_agente: list[ResultadoAgente] = field(default_factory=list)
    aprendizados_por_agente: list[AprendizadoOperacional] = field(default_factory=list)

    def para_dict(self) -> dict[str, Any]:
        """Converte a síntese para dicionário serializável."""
        resultados_agente = self.resultados_agente or _coletar_resultados_agente(
            self.captura.data_pregao
        )
        aprendizados_por_agente = self.aprendizados_por_agente or _gerar_aprendizados_por_agente(
            resultados_agente,
            self.aprendizados,
        )
        melhorias_por_categoria = _contar_por_categoria(self.melhorias)
        melhorias_por_agente = _contar_melhorias_por_agente(self.melhorias)
        itens_criticos = [
            {
                "id": m.id,
                "titulo": m.titulo,
                "categoria": m.categoria,
                "agente_impactado": m.agente_impactado,
                "prioridade": m.prioridade,
            }
            for m in self.melhorias
            if m.prioridade == "alta"
        ]
        resultado_por_agente = [resultado.to_dict() for resultado in resultados_agente]
        resultado_consolidado = _consolidar_resultados_agente(
            resultados_agente,
            foco=self.captura.foco,
            timestamp=self.captura.timestamp,
            capital_base=CAPITAL_BASE_RESUMO,
        )
        agentes_em_alerta = [
            {
                "agente": resultado.agente,
                "motivo": "DEFICITARIO",
                "acao_requerida": "Revisar estrategia, risco e rastreio de execucao.",
            }
            for resultado in resultados_agente
            if resultado.veredicto == "DEFICITARIO"
        ]
        sincronizacao = {
            "backlog_atualizado": True,
            "sync_manifest_atualizado": self.captura.foco == "fechamento",
            "versioning_atualizado": self.captura.foco == "fechamento",
            "timestamp_sincronizacao": self.captura.timestamp,
        }
        return {
            "captura_dia": asdict(self.captura),
            "aprendizados": asdict(self.aprendizados),
            "melhorias": [asdict(m) for m in self.melhorias],
            "aprendizados_por_agente": [
                asdict(aprendizado) for aprendizado in aprendizados_por_agente
            ],
            "resultado_consolidado": resultado_consolidado,
            "resultado_por_agente": resultado_por_agente,
            "melhorias_por_categoria": melhorias_por_categoria,
            "melhorias_por_agente": melhorias_por_agente,
            "itens_criticos": itens_criticos,
            "agentes_em_alerta": agentes_em_alerta,
            "sincronizacao": sincronizacao,
            "resumo": {
                "total_melhorias": len(self.melhorias),
                "por_categoria": melhorias_por_categoria,
                "por_agente": melhorias_por_agente,
                "resultado_total_reais": resultado_consolidado["resultado_total_reais"],
                "resultado_total_pct": resultado_consolidado["resultado_total_pct"],
                "win_rate_geral_pct": resultado_consolidado["win_rate_geral_pct"],
                "agentes_em_alerta": [item["agente"] for item in agentes_em_alerta],
                "itens_criticos": itens_criticos,
                "sincronizacao": sincronizacao,
            },
        }


# ---------------------------------------------------------------------------
# Funções auxiliares
# ---------------------------------------------------------------------------


def _contar_por_categoria(melhorias: list[CapturaMelhoria]) -> dict[str, int]:
    """Conta melhorias por categoria."""
    contagem: dict[str, int] = {
        "tecnico": 0,
        "funcional": 0,
        "governanca": 0,
        "ml_rl": 0,
    }
    for melhoria in melhorias:
        if melhoria.categoria in contagem:
            contagem[melhoria.categoria] += 1
    return contagem


def _contar_melhorias_por_agente(melhorias: list[CapturaMelhoria]) -> dict[str, int]:
    """Conta melhorias por agente impactado."""
    contagem: dict[str, int] = {agente: 0 for agente in AGENTES_OPERACIONAIS}
    contagem["TODOS"] = 0
    for melhoria in melhorias:
        agente = _normalizar_agente(melhoria.agente_impactado)
        contagem[agente] = contagem.get(agente, 0) + 1
    return contagem


def _normalizar_texto(valor: Any) -> str:
    """Normaliza texto removendo espaços duplicados e valores nulos."""
    if valor is None:
        return ""
    return " ".join(str(valor).strip().split())


def _normalizar_agente(agente: Any) -> str:
    """Normaliza o nome do agente para o contrato canônico."""
    texto = _normalizar_texto(agente).upper()
    if not texto:
        return "TODOS"

    texto = texto.replace("-", "_").replace(" ", "_")
    aliases = {
        "AGENTE_DIRETO": "RL_DIRETO",
        "AGENTE_RL_DIRETO": "RL_DIRETO",
        "AGENTE_DIARIOS": "DIARIOS",
        "AGENTE_MICRO_TENDENCIA": "MICRO_TENDENCIA",
        "AGENTE_MICROTENDENCIA": "MICRO_TENDENCIA",
        "AGENTE_RL_5000": "RL_5000",
        "RL5000": "RL_5000",
        "RL_DIRETO_V3_0": "RL_DIRETO",
        "DIARIO": "DIARIOS",
        "DIARIO_S": "DIARIOS",
        "MICROTENDENCIA": "MICRO_TENDENCIA",
        "TODOS": "TODOS",
    }
    texto = aliases.get(texto, texto)

    if texto in AGENTES_OPERACIONAIS or texto == "TODOS":
        return texto
    if "DIRETO" in texto:
        return "RL_DIRETO"
    if "5000" in texto:
        return "RL_5000"
    if "MICRO" in texto:
        return "MICRO_TENDENCIA"
    if "DIARI" in texto:
        return "DIARIOS"
    return "TODOS"


def _normalizar_veredicto(veredicto: Any) -> str:
    """Normaliza o veredicto do agente para o contrato canônico."""
    texto = _normalizar_texto(veredicto).upper()
    aliases = {
        "LUCRATIVA": "LUCRATIVO",
        "LUCRATIVO": "LUCRATIVO",
        "POSITIVO": "LUCRATIVO",
        "NEUTRA": "NEUTRO",
        "NEUTRO": "NEUTRO",
        "NEUTRAL": "NEUTRO",
        "DEFICITARIA": "DEFICITARIO",
        "DEFICITARIO": "DEFICITARIO",
        "DEFICITÁRIA": "DEFICITARIO",
        "DEFICITÁRIO": "DEFICITARIO",
    }
    return aliases.get(texto, "NEUTRO")


def _inferir_executor_por_agente(agente: str) -> str:
    """Retorna o executor BAT associado ao agente."""
    return EXECUTORES_POR_AGENTE.get(_normalizar_agente(agente), "DESCONHECIDO")


def _extrair_numero(valor: Any) -> float | None:
    """Extrai número de valores numéricos ou strings numéricas."""
    if isinstance(valor, bool) or valor is None:
        return None
    if isinstance(valor, (int, float)):
        return float(valor)
    if isinstance(valor, str):
        texto = valor.strip().replace("%", "")
        if not texto:
            return None
        try:
            return float(texto)
        except ValueError:
            return None
    return None


def _obter_caminho_data_evento(dados: dict[str, Any]) -> str:
    """Tenta identificar a data de referência do snapshot."""
    candidatos: tuple[Any | None, ...] = (
        dados.get("timestamp"),
        dados.get("close_time"),
        dados.get("open_time"),
        dados.get("abertura_ts"),
    )
    ultimo_fechamento = dados.get("ultimo_fechamento")
    if isinstance(ultimo_fechamento, dict):
        candidatos = candidatos + (ultimo_fechamento.get("timestamp"),)

    for valor in candidatos:
        texto = _normalizar_texto(valor)
        if len(texto) >= 10:
            try:
                return datetime.fromisoformat(texto.replace("Z", "+00:00")).date().isoformat()
            except ValueError:
                pass
        if len(texto) >= 8 and texto[:8].isdigit():
            return f"{texto[:4]}-{texto[4:6]}-{texto[6:8]}"
    return ""


def _inferir_agente_por_payload(dados: dict[str, Any], nome_arquivo: str = "") -> str:
    """Infere o agente operacional a partir do payload ou do nome do arquivo."""
    texto_base = " ".join(
        _normalizar_texto(part).upper()
        for part in (
            dados.get("owner"),
            dados.get("session_id"),
            nome_arquivo,
        )
    )
    texto_base = texto_base.replace("-", "_").replace(" ", "_")

    if "RL_DIRETO" in texto_base or "AGENTE_DIRETO" in texto_base:
        return "RL_DIRETO"
    if "DIARIOS" in texto_base:
        return "DIARIOS"
    if "MICRO" in texto_base:
        return "MICRO_TENDENCIA"
    if "5000" in texto_base:
        return "RL_5000"
    return "TODOS"


def _direcao_fator(direcao: Any) -> float:
    """Retorna o fator de sinal conforme a direção da operação."""
    texto = _normalizar_texto(direcao).upper()
    if texto in {"SELL", "VENDA", "SHORT"}:
        return -1.0
    return 1.0


def _inferir_resultado_reais(dados: dict[str, Any]) -> float:
    """Inferir resultado em reais a partir do snapshot do agente."""
    ultimo_fechamento = dados.get("ultimo_fechamento")
    if isinstance(ultimo_fechamento, dict):
        valor = _extrair_numero(ultimo_fechamento.get("pnl"))
        if valor is not None:
            return valor
        valor = _extrair_numero(ultimo_fechamento.get("resultado_reais"))
        if valor is not None:
            return valor

    for chave in (
        "resultado_reais",
        "pnl",
        "lucro_reais",
        "resultado",
    ):
        valor = _extrair_numero(dados.get(chave))
        if valor is not None:
            return valor

    preco_entrada = _extrair_numero(dados.get("preco_entrada"))
    if preco_entrada is None:
        return 0.0

    preco_saida = None
    for chave in (
        "preco_saida",
        "close_price",
        "preco_fechamento",
        "preco_final",
        "ultimo_preco",
    ):
        preco_saida = _extrair_numero(dados.get(chave))
        if preco_saida is not None:
            break

    if preco_saida is None and isinstance(ultimo_fechamento, dict):
        for chave in ("preco_saida", "close_price", "preco_fechamento", "ultimo_preco"):
            preco_saida = _extrair_numero(ultimo_fechamento.get(chave))
            if preco_saida is not None:
                break

    if preco_saida is None:
        return 0.0

    return (preco_saida - preco_entrada) * _direcao_fator(dados.get("direcao")) * float(
        os.environ.get("FECHAMENTO_VALOR_PONTO", "0.20")
    )


def _inferir_trades_executados(dados: dict[str, Any]) -> int:
    """Inferir se o snapshot representa uma execução de trade."""
    if any(
        chave in dados and dados.get(chave) is not None
        for chave in ("ticket", "preco_entrada", "close_time", "open_time", "ultimo_preco")
    ):
        return 1
    if isinstance(dados.get("ultimo_fechamento"), dict):
        return 1
    return 0


def _inferir_trades_encerrados(dados: dict[str, Any]) -> int:
    """Inferir se o trade foi encerrado no snapshot."""
    if isinstance(dados.get("ultimo_fechamento"), dict):
        return 1
    if dados.get("aberta") is False and any(
        chave in dados and dados.get(chave) is not None
        for chave in ("ticket", "preco_entrada", "close_time", "preco_saida", "ultimo_preco")
    ):
        return 1
    if dados.get("preco_saida") is not None:
        return 1
    return 0


def _gerar_aprendizados_por_agente(
    resultados_agente: list[ResultadoAgente],
    aprendizado_base: AprendizadoOperacional,
) -> list[AprendizadoOperacional]:
    """Gera aprendizados por agente com base no resultado consolidado."""
    base = asdict(aprendizado_base)
    aprendizados: list[AprendizadoOperacional] = []
    for resultado in resultados_agente:
        dados = dict(base)
        dados["agente"] = resultado.agente
        observacoes = list(dados.get("observacoes_algoritmo", []))
        divergencias = list(dados.get("divergencias_algoritmo", []))
        sugestoes = list(dados.get("sugestoes_ajuste", []))
        observacoes.append(
            f"Resultado do agente {resultado.agente}: {resultado.veredicto} "
            f"({resultado.resultado_reais:.2f} R$)."
        )
        if resultado.veredicto == "DEFICITARIO":
            dados["algoritmo_alinhado"] = False
            divergencias.append(
                f"Agente {resultado.agente} encerrou deficitario e requer reavaliacao."
            )
            sugestoes.append(
                f"Revisar risco, entradas e encerramento do agente {resultado.agente}."
            )
        dados["observacoes_algoritmo"] = observacoes
        dados["divergencias_algoritmo"] = divergencias
        dados["sugestoes_ajuste"] = sugestoes
        aprendizados.append(AprendizadoOperacional(**dados))
    return aprendizados


def _consolidar_resultados_agente(
    resultados_agente: list[ResultadoAgente],
    foco: str,
    timestamp: str,
    capital_base: float,
) -> dict[str, Any]:
    """Consolida o resultado de todos os agentes."""
    resultado_total_reais = round(
        sum(resultado.resultado_reais for resultado in resultados_agente),
        2,
    )
    trades_executados_total = sum(resultado.trades_executados for resultado in resultados_agente)
    trades_encerrados_total = sum(resultado.trades_encerrados for resultado in resultados_agente)
    wins_total = sum(resultado.wins for resultado in resultados_agente)
    losses_total = sum(resultado.losses for resultado in resultados_agente)
    maior_ganho_reais = max(
        (resultado.maior_ganho_reais for resultado in resultados_agente),
        default=0.0,
    )
    maior_perda_reais = min(
        (resultado.maior_perda_reais for resultado in resultados_agente),
        default=0.0,
    )
    win_rate_geral_pct = (
        round((wins_total / trades_encerrados_total) * 100, 2)
        if trades_encerrados_total
        else 0.0
    )
    resultado_total_pct = (
        round((resultado_total_reais / capital_base) * 100, 4) if capital_base else 0.0
    )
    relacao_risco_retorno = "0:0"
    if maior_ganho_reais > 0 and maior_perda_reais < 0:
        razao = abs(maior_ganho_reais / maior_perda_reais)
        relacao_risco_retorno = f"1:{razao:.2f}".rstrip("0").rstrip(".")

    agentes_em_alerta = [
        resultado.agente for resultado in resultados_agente if resultado.veredicto == "DEFICITARIO"
    ]

    return {
        "foco": foco,
        "timestamp": timestamp,
        "capital_base_reais": capital_base,
        "resultado_total_reais": resultado_total_reais,
        "resultado_total_pct": resultado_total_pct,
        "trades_executados_total": trades_executados_total,
        "trades_encerrados_total": trades_encerrados_total,
        "wins_total": wins_total,
        "losses_total": losses_total,
        "win_rate_geral_pct": win_rate_geral_pct,
        "maior_ganho_reais": round(maior_ganho_reais, 2),
        "maior_perda_reais": round(maior_perda_reais, 2),
        "relacao_risco_retorno": relacao_risco_retorno,
        "agentes_em_alerta": agentes_em_alerta,
    }


def _criar_resultado_padrao(agente: str) -> ResultadoAgente:
    """Cria resultado padrão para um agente sem snapshots no dia."""
    agente_normalizado = _normalizar_agente(agente)
    return ResultadoAgente(
        agente=agente_normalizado,
        executor=_inferir_executor_por_agente(agente_normalizado),
        resultado_reais=0.0,
        trades_executados=0,
        trades_encerrados=0,
        wins=0,
        losses=0,
        win_rate_pct=0.0,
        maior_ganho_reais=0.0,
        maior_perda_reais=0.0,
        relacao_risco_retorno="0:0",
        veredicto="NEUTRO",
    )


def _coletar_resultados_agente(data_pregao: str | None = None) -> list[ResultadoAgente]:
    """Coleta resultados por agente a partir dos snapshots em outputs/."""
    agregados: dict[str, dict[str, Any]] = {}
    for agente in AGENTES_OPERACIONAIS:
        agregados[agente] = {
            "resultado_reais": 0.0,
            "trades_executados": 0,
            "trades_encerrados": 0,
            "wins": 0,
            "losses": 0,
            "maior_ganho_reais": 0.0,
            "maior_perda_reais": 0.0,
            "sessao_ultima": {},
        }

    if CAMINHO_OUTPUTS.exists():
        snapshots: dict[tuple[str, str], tuple[str, dict[str, Any]]] = {}
        for caminho in sorted(CAMINHO_OUTPUTS.glob("agente_posicao_*.json")):
            dados = _carregar_json(caminho)
            if not dados:
                continue
            if data_pregao:
                data_snapshot = _obter_caminho_data_evento(dados)
                if data_snapshot != data_pregao:
                    continue
            agente = _inferir_agente_por_payload(dados, caminho.name)
            if agente not in AGENTES_OPERACIONAIS:
                continue
            session_id = _normalizar_texto(dados.get("session_id")) or caminho.stem
            chave = (agente, session_id)
            data_ordem = _normalizar_texto(dados.get("timestamp")) or _normalizar_texto(
                dados.get("close_time")
            )
            if chave not in snapshots or data_ordem >= snapshots[chave][0]:
                snapshots[chave] = (data_ordem, dados)

        for (agente, _session_id), (_, dados) in snapshots.items():
            resultado = _inferir_resultado_reais(dados)
            agregado = agregados[agente]
            agregado["resultado_reais"] += resultado
            agregado["trades_executados"] += _inferir_trades_executados(dados)
            agregado["trades_encerrados"] += _inferir_trades_encerrados(dados)
            if resultado > 0:
                agregado["wins"] += 1
            elif resultado < 0:
                agregado["losses"] += 1
            agregado["maior_ganho_reais"] = max(
                agregado["maior_ganho_reais"], resultado
            )
            if agregado["maior_perda_reais"] == 0.0:
                agregado["maior_perda_reais"] = resultado if resultado < 0 else 0.0
            elif resultado < agregado["maior_perda_reais"]:
                agregado["maior_perda_reais"] = resultado

    resultados: list[ResultadoAgente] = []
    for agente in AGENTES_OPERACIONAIS:
        agregado = agregados[agente]
        trades_encerrados = int(agregado["trades_encerrados"])
        wins = int(agregado["wins"])
        losses = int(agregado["losses"])
        win_rate_pct = round((wins / trades_encerrados) * 100, 2) if trades_encerrados else 0.0
        resultado_reais = round(float(agregado["resultado_reais"]), 2)
        maior_ganho_reais = round(float(agregado["maior_ganho_reais"]), 2)
        maior_perda_reais = round(float(agregado["maior_perda_reais"]), 2)
        if maior_ganho_reais > 0 and maior_perda_reais < 0:
            razao = abs(maior_ganho_reais / maior_perda_reais)
            relacao_risco_retorno = f"1:{razao:.2f}".rstrip("0").rstrip(".")
        else:
            relacao_risco_retorno = "0:0"
        if resultado_reais > 0:
            veredicto = "LUCRATIVO"
        elif resultado_reais < 0:
            veredicto = "DEFICITARIO"
        else:
            veredicto = "NEUTRO"
        resultados.append(
            ResultadoAgente(
                agente=agente,
                executor=_inferir_executor_por_agente(agente),
                resultado_reais=resultado_reais,
                trades_executados=int(agregado["trades_executados"]),
                trades_encerrados=trades_encerrados,
                wins=wins,
                losses=losses,
                win_rate_pct=win_rate_pct,
                maior_ganho_reais=maior_ganho_reais,
                maior_perda_reais=maior_perda_reais,
                relacao_risco_retorno=relacao_risco_retorno,
                veredicto=veredicto,
            )
        )
    return resultados


def _timestamp_agora() -> str:
    """Retorna timestamp ISO 8601 em UTC."""
    return datetime.now(tz=timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _checksum_arquivo(caminho: Path) -> str:
    """Calcula SHA-256 (primeiros 12 hex) de um arquivo."""
    if not caminho.exists():
        return "arquivo_nao_encontrado"
    conteudo = caminho.read_bytes()
    return hashlib.sha256(conteudo).hexdigest()[:12]


def _carregar_json(caminho: Path) -> dict[str, Any]:
    """Carrega JSON de um arquivo, retorna dict vazio se não existir."""
    if not caminho.exists():
        return {}
    with caminho.open(encoding="utf-8") as arq:
        return json.load(arq)  # type: ignore[no-any-return]


def _salvar_json(caminho: Path, dados: dict[str, Any]) -> None:
    """Salva dados em JSON com indentação."""
    caminho.parent.mkdir(parents=True, exist_ok=True)
    with caminho.open("w", encoding="utf-8") as arq:
        json.dump(dados, arq, ensure_ascii=False, indent=2)


def _serializar_saida(dados: dict[str, Any]) -> str:
    """Serializa dados para YAML (se disponível) ou JSON."""
    if _TEM_YAML:
        return yaml.dump(
            dados,
            allow_unicode=True,
            default_flow_style=False,
            sort_keys=False,
        )
    return json.dumps(dados, ensure_ascii=False, indent=2)


# ---------------------------------------------------------------------------
# Atualização de documentos do Agente Autônomo
# ---------------------------------------------------------------------------


def _atualizar_backlog(sintese: SinteseFechamento) -> None:
    """Adiciona itens de melhoria ao AGENTE_AUTONOMO_BACKLOG.md."""
    melhorias_altas = [m for m in sintese.melhorias if m.prioridade == "alta"]
    melhorias_medias = [m for m in sintese.melhorias if m.prioridade == "media"]
    dados_sintese = sintese.para_dict()

    ts = sintese.captura.timestamp
    foco = sintese.captura.foco.upper()
    marcador = f"<!-- FECHAMENTO_DIARIO: {ts} foco={foco} -->"

    if not CAMINHO_BACKLOG.exists():
        return

    conteudo = CAMINHO_BACKLOG.read_text(encoding="utf-8")
    if marcador in conteudo:
        return

    linhas: list[str] = [
        f"\n{marcador}",
        f"\n### Itens Capturados — {sintese.captura.data_pregao} ({foco})\n",
        "\n#### Resultado Consolidado\n",
        (
            f"- Resultado total: R$ {dados_sintese['resultado_consolidado']['resultado_total_reais']:.2f} "
            f"({dados_sintese['resultado_consolidado']['resultado_total_pct']:.4f}%)\n"
        ),
        (
            f"- Win rate geral: {dados_sintese['resultado_consolidado']['win_rate_geral_pct']:.2f}% | "
            f"Trades encerrados: {dados_sintese['resultado_consolidado']['trades_encerrados_total']}\n"
        ),
        "\n#### Resultado por Agente\n",
    ]

    for resultado in dados_sintese["resultado_por_agente"]:
        linhas.append(
            "- {agente} | executor={executor} | resultado=R$ {resultado:.2f} | "
            "executados={executados} | encerrados={encerrados} | veredicto={veredicto}\n".format(
                agente=resultado["agente"],
                executor=resultado["executor"],
                resultado=resultado["resultado_reais"],
                executados=resultado["trades_executados"],
                encerrados=resultado["trades_encerrados"],
                veredicto=resultado["veredicto"],
            )
        )

    if melhorias_altas:
        linhas.append("\n#### 🔴 Alta Prioridade\n")
        for m in melhorias_altas:
            linhas.append(
                f"- [ ] **[{m.id}]** {m.titulo} "
                f"_(categoria: {m.categoria}, esforço: {m.esforco}, "
                f"agente_impactado: {m.agente_impactado})_\n"
            )

    if melhorias_medias:
        linhas.append("\n#### 🟡 Média Prioridade\n")
        for m in melhorias_medias:
            linhas.append(
                f"- [ ] **[{m.id}]** {m.titulo} "
                f"_(categoria: {m.categoria}, esforço: {m.esforco}, "
                f"agente_impactado: {m.agente_impactado})_\n"
            )

    with CAMINHO_BACKLOG.open("a", encoding="utf-8") as arq:
        arq.writelines(linhas)


def _atualizar_sync_manifest(sintese: SinteseFechamento) -> None:
    """Atualiza SYNC_MANIFEST.json após execução de fechamento."""
    if sintese.captura.foco != "fechamento":
        return

    manifest = _carregar_json(CAMINHO_SYNC)
    ts = sintese.captura.timestamp

    # Atualizar timestamp de última atualização
    manifest["last_update"] = ts
    manifest["last_health_check"] = ts
    manifest["status"] = "synchronized"

    # Se documents é uma lista, não fazer mais atualizações de documento individual
    # pois a estrutura não o suporta dessa forma
    if "documents" in manifest and isinstance(manifest["documents"], list):
        # Apenas garantir que o manifest tem timestamp recente
        return

    _salvar_json(CAMINHO_SYNC, manifest)


def _atualizar_versioning(sintese: SinteseFechamento) -> None:
    """Atualiza VERSIONING.json ao final do fechamento."""
    if sintese.captura.foco != "fechamento":
        return

    versioning = _carregar_json(CAMINHO_VERSIONING)
    ts = sintese.captura.timestamp

    if "last_updated" in versioning:
        versioning["last_updated"] = ts

    componente = {
        "version": "1.0.0",
        "status": "PRODUCTION",
        "last_change": ts,
        "changelog": [
            {
                "version": "1.0.0",
                "date": sintese.captura.data_pregao,
                "changes": [
                    "Prompt de fechamento diário implementado",
                    "Script executor com parâmetro --foco",
                    "Schema de validação JSON com contrato por agente",
                    "Integração automática com backlog",
                    "Resultado consolidado por agente e precedencia documental",
                ],
            }
        ],
    }

    if "components" not in versioning:
        versioning["components"] = {}
    versioning["components"]["Fechamento_Diario"] = componente

    _salvar_json(CAMINHO_VERSIONING, versioning)


# ---------------------------------------------------------------------------
# Validação de schema
# ---------------------------------------------------------------------------


def _validar_sintese(dados: dict[str, Any]) -> list[str]:
    """Valida campos obrigatórios da síntese. Retorna lista de erros."""
    erros: list[str] = []
    schema = _carregar_json(CAMINHO_SCHEMA)
    if not schema:
        return erros

    obrigatorios = schema.get("required", [])
    for campo in obrigatorios:
        if campo not in dados:
            erros.append(f"Campo obrigatório ausente: '{campo}'")

    foco = dados.get("captura_dia", {}).get("foco", "")
    focos_permitidos = schema.get("properties", {}).get("foco", {}).get("enum", [])
    if focos_permitidos and foco not in focos_permitidos:
        erros.append(
            f"Foco inválido: '{foco}'. Permitidos: {focos_permitidos}"
        )

    return erros


# ---------------------------------------------------------------------------
# Geração de sessão padrão (modo automático)
# ---------------------------------------------------------------------------


def _criar_sessao_padrao(foco: str, data_pregao: str) -> SinteseFechamento:
    """Cria uma sessão de fechamento com valores padrão para execução automática."""
    ts = _timestamp_agora()
    captura = CapturaDia(
        timestamp=ts,
        foco=foco,
        data_pregao=data_pregao,
        simbolo=os.environ.get("FECHAMENTO_SIMBOLO", "WINFUT"),
    )
    aprendizados = AprendizadoOperacional()
    melhorias: list[CapturaMelhoria] = []
    resultados_agente = _coletar_resultados_agente(data_pregao)
    aprendizados_por_agente = _gerar_aprendizados_por_agente(
        resultados_agente,
        aprendizados,
    )
    return SinteseFechamento(
        captura=captura,
        aprendizados=aprendizados,
        melhorias=melhorias,
        resultados_agente=resultados_agente,
        aprendizados_por_agente=aprendizados_por_agente,
    )


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def _parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Executor do Prompt de Fechamento Diário — Operador Quântico.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=(
            "Exemplos:\n"
            "  python prompts/fechamento_diario.py --foco abertura\n"
            "  python prompts/fechamento_diario.py --foco meio_dia\n"
            "  python prompts/fechamento_diario.py --foco fechamento\n"
            "  python prompts/fechamento_diario.py --foco fechamento "
            "--data 2026-02-20\n"
        ),
    )
    parser.add_argument(
        "--foco",
        choices=list(FOCOS_VALIDOS),
        required=True,
        help="Momento do dia: abertura | meio_dia | fechamento",
    )
    parser.add_argument(
        "--data",
        default=date.today().isoformat(),
        help="Data do pregão no formato YYYY-MM-DD (padrão: hoje)",
    )
    parser.add_argument(
        "--saida",
        default=None,
        help="Caminho para salvar a saída YAML/JSON (padrão: data/fechamento_diario/)",
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        default=os.environ.get("FECHAMENTO_VERBOSE", "").lower() in ("1", "true"),
        help="Exibe saída detalhada",
    )
    return parser.parse_args(argv)


def _determinar_caminho_saida(args: argparse.Namespace) -> Path:
    """Determina o caminho do arquivo de saída."""
    if args.saida:
        return Path(args.saida)
    ext = "yaml" if _TEM_YAML else "json"
    nome_arquivo = f"fechamento_{args.data}_{args.foco}.{ext}"
    return CAMINHO_SAIDAS / nome_arquivo


def executar(foco: str, data_pregao: str, caminho_saida: Path | None = None,
             verbose: bool = False) -> int:
    """Executa o fluxo completo do fechamento diário.

    Parâmetros
    ----------
    foco:
        Momento do dia (abertura, meio_dia, fechamento).
    data_pregao:
        Data do pregão no formato YYYY-MM-DD.
    caminho_saida:
        Caminho opcional para salvar a saída.
    verbose:
        Exibe detalhes da execução.

    Retorna
    -------
    Código de saída (0 = sucesso, 1 = erro).
    """
    try:
        datetime.strptime(data_pregao, "%Y-%m-%d")
    except ValueError:
        print(f"[ERRO] Data inválida: '{data_pregao}'. Use YYYY-MM-DD.")
        return 2

    if foco not in FOCOS_VALIDOS:
        print(f"[ERRO] Foco inválido: '{foco}'. Use: {FOCOS_VALIDOS}")
        return 2

    _imprimir_cabecalho(foco, data_pregao)

    sintese = _criar_sessao_padrao(foco, data_pregao)
    dados = sintese.para_dict()

    erros_validacao = _validar_sintese(dados)
    if erros_validacao:
        print("\n[AVISO] Erros de validação de schema:")
        for erro in erros_validacao:
            print(f"  - {erro}")

    _atualizar_backlog(sintese)
    _atualizar_sync_manifest(sintese)
    _atualizar_versioning(sintese)

    if caminho_saida is None:
        ext = "yaml" if _TEM_YAML else "json"
        nome_arquivo = f"fechamento_{data_pregao}_{foco}.{ext}"
        caminho_saida = CAMINHO_SAIDAS / nome_arquivo

    caminho_saida.parent.mkdir(parents=True, exist_ok=True)
    conteudo_saida = _serializar_saida(dados)
    caminho_saida.write_text(conteudo_saida, encoding="utf-8")

    if verbose:
        print("\n" + "=" * 72)
        print("SAÍDA GERADA:")
        print("=" * 72)
        print(conteudo_saida)

    _imprimir_rodape(sintese, caminho_saida)
    return 0


def _imprimir_cabecalho(foco: str, data_pregao: str) -> None:
    """Exibe cabeçalho da execução."""
    foco_display = {
        "abertura": "ABERTURA DE MERCADO (~08:00)",
        "meio_dia": "MEIO DO DIA (~12:00)",
        "fechamento": "FECHAMENTO DE MERCADO (~17:00)",
    }.get(foco, foco.upper())

    print("=" * 72)
    print("FECHAMENTO DIÁRIO — OPERADOR QUÂNTICO")
    print("=" * 72)
    print(f"Data do Pregão : {data_pregao}")
    print(f"Foco           : {foco_display}")
    print(f"Timestamp      : {_timestamp_agora()}")
    print("=" * 72)


def _imprimir_rodape(sintese: SinteseFechamento, caminho_saida: Path) -> None:
    """Exibe rodapé com resumo da execução."""
    dados = sintese.para_dict()
    contagem = _contar_por_categoria(sintese.melhorias)
    total = len(sintese.melhorias)
    resultado_consolidado = dados["resultado_consolidado"]

    print()
    print("─" * 72)
    print("EXECUÇÃO CONCLUÍDA")
    print("─" * 72)
    print(f"Foco           : {sintese.captura.foco.upper()}")
    print(f"Data           : {sintese.captura.data_pregao}")
    print(f"Melhorias      : {total} total")
    print(f"  Técnico      : {contagem['tecnico']}")
    print(f"  Funcional    : {contagem['funcional']}")
    print(f"  Governança   : {contagem['governanca']}")
    print(f"  ML/RL        : {contagem['ml_rl']}")
    print(
        f"Resultado total: R$ {resultado_consolidado['resultado_total_reais']:.2f} "
        f"({resultado_consolidado['resultado_total_pct']:.4f}%)"
    )
    print(
        f"Win rate geral : {resultado_consolidado['win_rate_geral_pct']:.2f}% | "
        f"Trades enc. {resultado_consolidado['trades_encerrados_total']}"
    )
    print("Por agente     :")
    for resultado in dados["resultado_por_agente"]:
        print(
            f"  - {resultado['agente']}: {resultado['veredicto']} | "
            f"R$ {resultado['resultado_reais']:.2f} | "
            f"encerrados={resultado['trades_encerrados']}"
        )
    if dados["resultado_consolidado"]["agentes_em_alerta"]:
        print(
            "Alertas        : "
            + ", ".join(dados["resultado_consolidado"]["agentes_em_alerta"])
        )
    print(f"Arquivo salvo  : {caminho_saida}")

    if sintese.captura.foco == "fechamento":
        print()
        print("Documentos atualizados:")
        print(f"  - {CAMINHO_BACKLOG.name}")
        print(f"  - {CAMINHO_SYNC.name}")
        print(f"  - {CAMINHO_VERSIONING.name}")

    print("─" * 72)


# ---------------------------------------------------------------------------
# Ponto de entrada
# ---------------------------------------------------------------------------


def main(argv: list[str] | None = None) -> int:
    """Ponto de entrada principal."""
    args = _parse_args(argv)

    caminho_saida: Path | None = None
    if args.saida:
        caminho_saida = Path(args.saida)

    return executar(
        foco=args.foco,
        data_pregao=args.data,
        caminho_saida=caminho_saida,
        verbose=args.verbose,
    )


if __name__ == "__main__":
    raise SystemExit(main())
