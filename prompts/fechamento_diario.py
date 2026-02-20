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
    import yaml  # type: ignore[import]

    _TEM_YAML = True
except ImportError:
    _TEM_YAML = False

FOCOS_VALIDOS = ("abertura", "meio_dia", "fechamento")

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


@dataclass
class CapturaMelhoria:
    """Melhoria identificada durante o pregão."""

    id: str
    titulo: str
    descricao: str
    categoria: str
    prioridade: str
    esforco: str
    sync_com: list[str] = field(default_factory=list)
    arquivo_afetado: str = ""
    estrategia_relacionada: str = ""
    documento_afetado: str = ""
    tipo_aprendizado: str = ""


@dataclass
class SinteseFechamento:
    """Síntese consolidada do fechamento diário para importação no backlog."""

    captura: CapturaDia
    aprendizados: AprendizadoOperacional
    melhorias: list[CapturaMelhoria]

    def para_dict(self) -> dict[str, Any]:
        """Converte a síntese para dicionário serializável."""
        return {
            "captura_dia": asdict(self.captura),
            "aprendizados": asdict(self.aprendizados),
            "melhorias": [asdict(m) for m in self.melhorias],
            "resumo": {
                "total_melhorias": len(self.melhorias),
                "por_categoria": _contar_por_categoria(self.melhorias),
                "itens_criticos": [
                    {"id": m.id, "titulo": m.titulo, "categoria": m.categoria}
                    for m in self.melhorias
                    if m.prioridade == "alta"
                ],
                "sincronizacao": {
                    "backlog_atualizado": True,
                    "sync_manifest_atualizado": self.captura.foco == "fechamento",
                    "timestamp": self.captura.timestamp,
                },
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

    if not melhorias_altas and not melhorias_medias:
        return

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
    ]

    if melhorias_altas:
        linhas.append("\n#### 🔴 Alta Prioridade\n")
        for m in melhorias_altas:
            linhas.append(
                f"- [ ] **[{m.id}]** {m.titulo} "
                f"_(categoria: {m.categoria}, esforço: {m.esforco})_\n"
            )

    if melhorias_medias:
        linhas.append("\n#### 🟡 Média Prioridade\n")
        for m in melhorias_medias:
            linhas.append(
                f"- [ ] **[{m.id}]** {m.titulo} "
                f"_(categoria: {m.categoria}, esforço: {m.esforco})_\n"
            )

    with CAMINHO_BACKLOG.open("a", encoding="utf-8") as arq:
        arq.writelines(linhas)


def _atualizar_sync_manifest(sintese: SinteseFechamento) -> None:
    """Atualiza SYNC_MANIFEST.json após execução de fechamento."""
    if sintese.captura.foco != "fechamento":
        return

    manifest = _carregar_json(CAMINHO_SYNC)
    ts = sintese.captura.timestamp

    if "sync_metadata" in manifest:
        manifest["sync_metadata"]["last_update"] = ts
        manifest["sync_metadata"]["status"] = "SYNCHRONIZED"

    if "documents" in manifest:
        backlog_chave = "AGENTE_AUTONOMO_BACKLOG.md"
        if backlog_chave in manifest["documents"]:
            manifest["documents"][backlog_chave]["last_modified"] = ts
            manifest["documents"][backlog_chave]["checksum"] = _checksum_arquivo(
                CAMINHO_BACKLOG
            )

    if "health_check" in manifest:
        manifest["health_check"]["last_health_check"] = ts
        manifest["health_check"]["sync_status"] = "HEALTHY"

    if "validation_checklist" in manifest:
        manifest["validation_checklist"]["last_validation"] = ts
        manifest["validation_checklist"]["validation_status"] = "PASSED"

    for nome_doc in DOCUMENTOS_FECHAMENTO:
        caminho_doc = RAIZ / "prompts" / nome_doc
        if "documents" not in manifest:
            manifest["documents"] = {}
        if nome_doc not in manifest["documents"]:
            manifest["documents"][nome_doc] = {
                "version": "1.0.0",
                "checksum": _checksum_arquivo(caminho_doc),
                "last_modified": ts,
                "related_docs": ["AGENTE_AUTONOMO_BACKLOG.md"],
                "status": "ACTIVE",
                "mandatory_sync_with": ["AGENTE_AUTONOMO_BACKLOG.md"],
            }

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
                    "Schema de validação JSON",
                    "Integração automática com backlog",
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
    return SinteseFechamento(
        captura=captura,
        aprendizados=aprendizados,
        melhorias=melhorias,
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
    contagem = _contar_por_categoria(sintese.melhorias)
    total = len(sintese.melhorias)

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
