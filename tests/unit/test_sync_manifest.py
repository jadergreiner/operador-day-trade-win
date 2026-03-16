"""Testes para SYNC_MANIFEST.json - Observabilidade e Governanca Tecnica.

Valida que o manifesto de sincronizacao de documentacao:
  - Existe no caminho correto (docs/agente_autonomo/SYNC_MANIFEST.json)
  - Tem estrutura JSON valida
  - Lista todos os documentos reais do projeto
  - Define grupos de sincronizacao coerentes
  - Tem campos obrigatorios em cada documento

Pipeline:
    validate_documentation.py carrega SYNC_MANIFEST.json
    → carregar_sync_manifest() verifica existencia
    → validar_sync_manifest() cruza com arquivos reais
    → gerar_relatorio() consolida resultado

Status: Implementacao v1.0 (16/03/2026)
Referencia: docs/BACKLOG.md (P2 - Observabilidade e governanca tecnica)
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent.parent
MANIFEST_PATH = ROOT / "docs" / "agente_autonomo" / "SYNC_MANIFEST.json"
DOCS_PATH = ROOT / "docs"

sys.path.insert(0, str(ROOT))


# ============================================================================
# FIXTURES
# ============================================================================


@pytest.fixture
def manifest() -> dict:  # type: ignore[type-arg]
    """Carrega o SYNC_MANIFEST.json real do projeto."""
    assert MANIFEST_PATH.exists(), (
        f"SYNC_MANIFEST.json nao encontrado em {MANIFEST_PATH}"
    )
    with open(MANIFEST_PATH, "r", encoding="utf-8") as f:
        return json.load(f)  # type: ignore[no-any-return]


# ============================================================================
# TESTES DE EXISTENCIA E ESTRUTURA
# ============================================================================


def test_01_arquivo_existe() -> None:
    """TC-01: SYNC_MANIFEST.json existe no caminho correto."""
    assert MANIFEST_PATH.exists(), (
        f"SYNC_MANIFEST.json nao encontrado em {MANIFEST_PATH}"
    )


def test_02_json_valido() -> None:
    """TC-02: SYNC_MANIFEST.json e JSON valido."""
    with open(MANIFEST_PATH, "r", encoding="utf-8") as f:
        dados = json.load(f)
    assert isinstance(dados, dict)


def test_03_tem_campo_versao(manifest: dict) -> None:  # type: ignore[type-arg]
    """TC-03: Manifest tem campo 'versao'."""
    assert "versao" in manifest
    assert isinstance(manifest["versao"], str)
    assert len(manifest["versao"]) > 0


def test_04_tem_campo_documentos(manifest: dict) -> None:  # type: ignore[type-arg]
    """TC-04: Manifest tem campo 'documentos' como lista."""
    assert "documentos" in manifest
    assert isinstance(manifest["documentos"], list)
    assert len(manifest["documentos"]) > 0


def test_05_tem_campo_ultima_validacao(manifest: dict) -> None:  # type: ignore[type-arg]
    """TC-05: Manifest tem campo 'ultima_validacao'."""
    assert "ultima_validacao" in manifest
    assert isinstance(manifest["ultima_validacao"], str)


def test_06_tem_grupos_sincronizacao(manifest: dict) -> None:  # type: ignore[type-arg]
    """TC-06: Manifest tem campo 'grupos_sincronizacao'."""
    assert "grupos_sincronizacao" in manifest
    assert isinstance(manifest["grupos_sincronizacao"], list)
    assert len(manifest["grupos_sincronizacao"]) > 0


def test_07_tem_regras_atualizacao(manifest: dict) -> None:  # type: ignore[type-arg]
    """TC-07: Manifest tem campo 'regras_atualizacao'."""
    assert "regras_atualizacao" in manifest
    assert isinstance(manifest["regras_atualizacao"], dict)


# ============================================================================
# TESTES DE DOCUMENTOS
# ============================================================================


def test_08_cada_documento_tem_nome(manifest: dict) -> None:  # type: ignore[type-arg]
    """TC-08: Cada documento no manifest tem campo 'nome'."""
    for doc in manifest["documentos"]:
        assert "nome" in doc, f"Documento sem 'nome': {doc}"
        assert isinstance(doc["nome"], str)
        assert doc["nome"].endswith(".md"), (
            f"Nome deve terminar em .md: {doc['nome']}"
        )


def test_09_cada_documento_tem_status(manifest: dict) -> None:  # type: ignore[type-arg]
    """TC-09: Cada documento tem campo 'status'."""
    status_validos = {"PRONTO", "PENDENTE", "OBSOLETO", "REVISAO"}
    for doc in manifest["documentos"]:
        assert "status" in doc, f"Documento sem 'status': {doc['nome']}"
        assert doc["status"] in status_validos, (
            f"Status invalido '{doc['status']}' em {doc['nome']}"
        )


def test_10_cada_documento_tem_versao(manifest: dict) -> None:  # type: ignore[type-arg]
    """TC-10: Cada documento tem campo 'versao'."""
    for doc in manifest["documentos"]:
        assert "versao" in doc, f"Documento sem 'versao': {doc['nome']}"
        assert isinstance(doc["versao"], str)


def test_11_cada_documento_tem_agentes_impactados(
    manifest: dict,  # type: ignore[type-arg]
) -> None:
    """TC-11: Cada documento lista os agentes impactados."""
    agentes_validos = {
        "INICIAR_DIARIOS.bat",
        "INICIAR_MICRO_TENDENCIA_AUTO_TRADE.bat",
        "INICIAR_AGENTE_RL_5000.bat",
        "INICIAR_AGENTE_RL_DIRETO.bat",
    }
    for doc in manifest["documentos"]:
        assert "agentes_impactados" in doc, (
            f"Documento sem 'agentes_impactados': {doc['nome']}"
        )
        assert isinstance(doc["agentes_impactados"], list)
        assert len(doc["agentes_impactados"]) > 0, (
            f"'agentes_impactados' vazio em {doc['nome']}"
        )
        for agente in doc["agentes_impactados"]:
            assert agente in agentes_validos, (
                f"Agente invalido '{agente}' em {doc['nome']}"
            )


# ============================================================================
# TESTES DE CONSISTENCIA COM ARQUIVOS REAIS
# ============================================================================


def test_12_todos_docs_existem_em_disco(manifest: dict) -> None:  # type: ignore[type-arg]
    """TC-12: Todos os documentos listados existem em docs/."""
    for doc in manifest["documentos"]:
        nome = doc["nome"]
        arquivo = DOCS_PATH / nome
        assert arquivo.exists(), (
            f"Documento listado no manifest nao existe: docs/{nome}"
        )


def test_13_todos_docs_reais_estao_no_manifest(manifest: dict) -> None:  # type: ignore[type-arg]
    """TC-13: Todos os .md em docs/ estao no manifest."""
    nomes_no_manifest = {doc["nome"] for doc in manifest["documentos"]}
    for md_file in DOCS_PATH.glob("*.md"):
        assert md_file.name in nomes_no_manifest, (
            f"Arquivo docs/{md_file.name} nao esta no SYNC_MANIFEST.json"
        )


def test_14_docs_sincronizar_com_existem(manifest: dict) -> None:  # type: ignore[type-arg]
    """TC-14: Referencias em 'sincronizar_com' apontam para docs existentes."""
    todos_nomes = {doc["nome"] for doc in manifest["documentos"]}
    for doc in manifest["documentos"]:
        for ref in doc.get("sincronizar_com", []):
            assert ref in todos_nomes, (
                f"'sincronizar_com' referencia doc inexistente: "
                f"'{ref}' em {doc['nome']}"
            )


# ============================================================================
# TESTES DE GRUPOS DE SINCRONIZACAO
# ============================================================================


def test_15_grupos_tem_nome_e_documentos(manifest: dict) -> None:  # type: ignore[type-arg]
    """TC-15: Cada grupo tem 'nome' e 'documentos'."""
    for grupo in manifest["grupos_sincronizacao"]:
        assert "nome" in grupo, f"Grupo sem 'nome': {grupo}"
        assert "documentos" in grupo, f"Grupo sem 'documentos': {grupo}"
        assert len(grupo["documentos"]) >= 2, (
            f"Grupo '{grupo['nome']}' precisa de ao menos 2 documentos"
        )


def test_16_documentos_em_grupos_existem_no_manifest(
    manifest: dict,  # type: ignore[type-arg]
) -> None:
    """TC-16: Docs referenciados nos grupos existem no campo 'documentos'."""
    todos_nomes = {doc["nome"] for doc in manifest["documentos"]}
    for grupo in manifest["grupos_sincronizacao"]:
        for nome in grupo["documentos"]:
            assert nome in todos_nomes, (
                f"Grupo '{grupo['nome']}' referencia doc inexistente: {nome}"
            )


# ============================================================================
# TESTES DE REGRAS DE ATUALIZACAO
# ============================================================================


def test_17_regras_tem_ao_implementar_item(manifest: dict) -> None:  # type: ignore[type-arg]
    """TC-17: Regras de atualizacao definem o que fazer ao implementar item."""
    regras = manifest["regras_atualizacao"]
    assert "ao_implementar_item_backlog" in regras
    passos = regras["ao_implementar_item_backlog"]
    assert isinstance(passos, list)
    assert len(passos) >= 3, "Deve ter ao menos 3 passos de atualizacao"


def test_18_regras_tem_frequencia_revisao(manifest: dict) -> None:  # type: ignore[type-arg]
    """TC-18: Regras de atualizacao definem frequencia de revisao."""
    regras = manifest["regras_atualizacao"]
    assert "frequencia_revisao" in regras
    freq = regras["frequencia_revisao"]
    assert isinstance(freq, dict)
    assert len(freq) >= 2


# ============================================================================
# TESTE DE INTEGRACAO COM validate_documentation.py
# ============================================================================


def test_19_validator_carrega_manifest() -> None:
    """TC-19: DocumentValidator consegue carregar o SYNC_MANIFEST.json real."""
    from scripts.validate_documentation import DocumentValidator

    validator = DocumentValidator(docs_path=str(DOCS_PATH))
    manifest_carregado = validator.carregar_sync_manifest()

    assert manifest_carregado is not None
    assert "documentos" in manifest_carregado
    documentos = manifest_carregado["documentos"]
    assert isinstance(documentos, list)
    assert len(documentos) >= 8


def test_20_validator_sem_erros_de_sync() -> None:
    """TC-20: Validator nao encontra inconsistencias no SYNC_MANIFEST real."""
    from scripts.validate_documentation import DocumentValidator

    validator = DocumentValidator(docs_path=str(DOCS_PATH))
    erros = validator.validar_sync_manifest()

    nomes_erros = [e.mensagem for e in erros]
    assert len(erros) == 0, (
        f"SYNC_MANIFEST tem inconsistencias: {nomes_erros}"
    )
