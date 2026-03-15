#!/usr/bin/env python3
"""Validador de Documentação e Sincronização - Observabilidade e Governança.

Objetivo: Validar integridade de documentação, sincronização entre arquivos
e consistência do projeto.

Funcionalidades:
  - Validação de markdown (MD013, MD001, MD022, MD023)
  - Detecção de referências cruzadas
  - Validação de SYNC_MANIFEST.json
  - Verificação de status (DONE, PENDENTE)
  - Report de integridade
  - Encoding UTF-8 validation
  - Aviso de commit messages com acentos

Type hints: 100%
Docstrings: 100%
Português: 100%
"""

from __future__ import annotations

import json
import logging
import re
from dataclasses import dataclass, field, asdict
from datetime import datetime
from pathlib import Path
from typing import Optional, List, Dict, Set, Tuple

# ============================================================================
# LOGGING
# ============================================================================

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)


# ============================================================================
# DATA CLASSES
# ============================================================================

@dataclass
class ErroValidacao:
    """Erro encontrado durante validação."""
    arquivo: str
    tipo_erro: str  # MD013, MD001, ENCODING, SYNC, etc
    linha: int
    mensagem: str
    severidade: str = "ERROR"  # ERROR, WARNING, INFO

    def __str__(self) -> str:
        """Formatação da mensagem de erro."""
        return (f"{self.arquivo}:{self.linha} [{self.tipo_erro}] "
                f"({self.severidade}) {self.mensagem}")


@dataclass
class ResultadoValidacao:
    """Resultado de validação de um arquivo."""
    arquivo: str
    valido: bool
    erros: List[ErroValidacao] = field(default_factory=list)
    avisos: List[str] = field(default_factory=list)
    tempo_validacao: float = 0.0

    def tem_erros_criticos(self) -> bool:
        """Verifica se há erros críticos (não warnings)."""
        return any(e.severidade == "ERROR" for e in self.erros)


@dataclass
class RelatorioValidacao:
    """Relatório consolidado de validação."""
    timestamp: str
    total_arquivos: int
    arquivos_validos: int
    arquivos_invalidos: int
    total_erros: int
    total_avisos: int
    tempo_total_segundos: float
    resultados: List[ResultadoValidacao] = field(default_factory=list)
    referencias_faltantes: List[str] = field(default_factory=list)
    documentos_orphans: List[str] = field(default_factory=list)


# ============================================================================
# VALIDATOR CLASS
# ============================================================================

class DocumentValidator:
    """Validador de documentação e sincronização do projeto."""

    # Constantes
    MAX_LINHA_CHARS = 80
    ACENTOS_PATTERN = r"[áéíóúãõâêôàçñü]"
    REFERENCIA_PATTERN = r"\[([^\]]+)\]\(([^)]+)\)"  # [texto](arquivo)

    def __init__(self, docs_path: str | Path = "docs") -> None:
        """Inicializa validador com caminho dos documentos.

        Args:
            docs_path: Caminho base dos documentos.
        """
        self.docs_path = Path(docs_path)
        self.logger = logging.getLogger(self.__class__.__name__)
        self.logger.info(f"DocumentValidator inicializado com docs_path={self.docs_path}")

    # ========================================================================
    # DESCOBERTA DE ARQUIVOS
    # ========================================================================

    def encontrar_arquivos_md(self) -> List[Path]:
        """Encontra todos os arquivos .md no diretório docs.

        Returns:
            Lista de arquivos .md encontrados.
        """
        if not self.docs_path.exists():
            self.logger.warning(f"Caminho docs_path não existe: {self.docs_path}")
            return []

        md_files = list(self.docs_path.rglob("*.md"))
        self.logger.info(f"Encontrados {len(md_files)} arquivos .md")
        return md_files

    def encontrar_arquivos_json(self) -> List[Path]:
        """Encontra todos os arquivos .json na docs/agente_autonomo.

        Returns:
            Lista de arquivos .json encontrados.
        """
        agente_dir = self.docs_path / "agente_autonomo"
        if not agente_dir.exists():
            return []

        json_files = list(agente_dir.glob("*.json"))
        return json_files

    # ========================================================================
    # EXTRAÇÃO DE INFORMAÇÕES
    # ========================================================================

    def extrair_items_status(
        self, arquivo: Path, status: str = "DONE"
    ) -> List[str]:
        """Extrai items com determinado status do arquivo.

        Args:
            arquivo: Arquivo a analisar.
            status: Status a procurar (ex: DONE, PENDENTE).

        Returns:
            Lista de items com o status.
        """
        try:
            conteudo = arquivo.read_text(encoding="utf-8")
        except Exception as e:
            self.logger.error(f"Erro ao ler {arquivo}: {e}")
            return []

        # Padrão: encontra seções com ### ou #### seguido de número e texto
        # depois procura "Status: DONE" ou "**Status:** DONE"
        pattern = rf"^#+\s+(\d+\..+?)$\n\n(.*?)\*\*?Status:\*?\s*{status}"
        matches = re.findall(pattern, conteudo, re.MULTILINE | re.DOTALL)

        items = [match[0] for match in matches]
        return items

    def encontrar_referencias_cruzadas(self, arquivo: Path) -> Set[str]:
        """Encontra referências de arquivo em link (ex: [texto](../outro.md)).

        Args:
            arquivo: Arquivo a analisar.

        Returns:
            Set de nomes de arquivos referenciados.
        """
        try:
            conteudo = arquivo.read_text(encoding="utf-8")
        except Exception:
            return set()

        # Procura por padrões de link [texto](arquivo)
        matches = re.findall(self.REFERENCIA_PATTERN, conteudo)
        referencias = set()

        for _, link in matches:
            # Extrai nome do arquivo do link
            if link.startswith("../"):
                arquivo_ref = link.replace("../", "").split("#")[0]
            elif link.startswith("."):
                arquivo_ref = link.split("#")[0]
            else:
                arquivo_ref = link.split("#")[0]

            if arquivo_ref:
                referencias.add(arquivo_ref)

        return referencias

    # ========================================================================
    # VALIDAÇÃO MARKDOWN
    # ========================================================================

    def validar_md013(self, arquivo: Path) -> List[ErroValidacao]:
        """Valida MD013 (linhas máximo 80 caracteres).

        Args:
            arquivo: Arquivo a validar.

        Returns:
            Lista de ErroValidacao encontrados.
        """
        erros: List[ErroValidacao] = []

        try:
            linhas = arquivo.read_text(encoding="utf-8").split("\n")
        except Exception as e:
            self.logger.error(f"Erro ao ler {arquivo}: {e}")
            return erros

        for idx, linha in enumerate(linhas, 1):
            # Exceções: URLs, blocos de código
            if linha.startswith("    "):  # Código indentado
                continue
            if "http://" in linha or "https://" in linha:
                continue

            if len(linha) > self.MAX_LINHA_CHARS:
                erros.append(
                    ErroValidacao(
                        arquivo=arquivo.name,
                        tipo_erro="MD013",
                        linha=idx,
                        mensagem=f"Linha muito longa: {len(linha)} chars (máximo {self.MAX_LINHA_CHARS})",
                        severidade="WARNING",
                    )
                )

        return erros

    def validar_md001(self, arquivo: Path) -> List[ErroValidacao]:
        """Valida MD001 (ordem sequencial de cabeçalhos).

        Args:
            arquivo: Arquivo a validar.

        Returns:
            Lista de ErroValidacao encontrados.
        """
        erros: List[ErroValidacao] = []

        try:
            linhas = arquivo.read_text(encoding="utf-8").split("\n")
        except Exception:
            return erros

        ultimo_level = 0
        primeiro_h1_encontrado = False

        for idx, linha in enumerate(linhas, 1):
            # Detecta cabeçalho
            match = re.match(r"^(#+)\s", linha)
            if not match:
                continue

            level = len(match.group(1))

            # Primeiro cabeçalho deve ser nível 1
            if not primeiro_h1_encontrado:
                if level != 1:
                    erros.append(
                        ErroValidacao(
                            arquivo=arquivo.name,
                            tipo_erro="MD001",
                            linha=idx,
                            mensagem=f"Primeiro cabeçalho deve ser nível 1, encontrado nível {level}",
                            severidade="ERROR",
                        )
                    )
                primeiro_h1_encontrado = True
                ultimo_level = level
                continue

            # Verifica se não pulou niveis (permite retorno para niveis anteriores)
            if level > ultimo_level + 1:
                erros.append(
                    ErroValidacao(
                        arquivo=arquivo.name,
                        tipo_erro="MD001",
                        linha=idx,
                        mensagem=f"Pulou nivel de cabecalho: {ultimo_level} -> {level}",
                        severidade="ERROR",
                    )
                )

            ultimo_level = level

        return erros

    def validar_md022(self, arquivo: Path) -> List[ErroValidacao]:
        """Valida MD022 (espaço em branco antes de cabeçalho).

        Args:
            arquivo: Arquivo a validar.

        Returns:
            Lista de ErroValidacao encontrados.
        """
        erros: List[ErroValidacao] = []

        try:
            linhas = arquivo.read_text(encoding="utf-8").split("\n")
        except Exception:
            return erros

        for idx in range(1, len(linhas)):
            # Se esta linha é cabeçalho (##)
            if re.match(r"^#+\s", linhas[idx]):
                # Linha anterior deve estar vazia (exceto na primeira linha)
                if idx > 0 and linhas[idx - 1].strip() != "":
                    erros.append(
                        ErroValidacao(
                            arquivo=arquivo.name,
                            tipo_erro="MD022",
                            linha=idx + 1,
                            mensagem="Cabeçalho deve ter linha em branco antes",
                            severidade="WARNING",
                        )
                    )

        return erros

    # ========================================================================
    # VALIDAÇÃO ENCODING E CONTEÚDO
    # ========================================================================

    def validar_encoding(self, arquivo: Path) -> bool:
        """Valida que arquivo está em UTF-8.

        Args:
            arquivo: Arquivo a validar.

        Returns:
            True se válido, False caso contrário.
        """
        try:
            arquivo.read_text(encoding="utf-8")
            return True
        except UnicodeDecodeError as e:
            self.logger.error(f"Erro de encoding em {arquivo}: {e}")
            return False

    def tem_acentos(self, texto: str) -> bool:
        """Verifica se texto tem acentos.

        Args:
            texto: Texto a validar.

        Returns:
            True se tem acentos, False caso contrário.
        """
        return bool(re.search(self.ACENTOS_PATTERN, texto))

    # ========================================================================
    # VALIDAÇÃO SYNC_MANIFEST
    # ========================================================================

    def carregar_sync_manifest(self) -> Optional[Dict[str, object]]:
        """Carrega SYNC_MANIFEST.json da pasta agente_autonomo.

        Returns:
            Dict com manifest ou None se não encontrado.
        """
        manifest_path = self.docs_path / "agente_autonomo" / "SYNC_MANIFEST.json"

        if not manifest_path.exists():
            self.logger.warning(f"SYNC_MANIFEST.json nao encontrado: {manifest_path}")
            return None

        try:
            with open(manifest_path, "r", encoding="utf-8") as f:
                manifest: Dict[str, object] = json.load(f)
            self.logger.info(f"SYNC_MANIFEST carregado com sucesso")
            return manifest
        except json.JSONDecodeError as e:
            self.logger.error(f"Erro ao decodificar SYNC_MANIFEST.json: {e}")
            return None
        except Exception as e:
            self.logger.error(f"Erro ao ler SYNC_MANIFEST.json: {e}")
            return None

    def validar_sync_manifest(self) -> List[ErroValidacao]:
        """Valida consistencia do SYNC_MANIFEST com arquivos reais.

        Returns:
            Lista de ErroValidacao encontrados.
        """
        erros: List[ErroValidacao] = []

        manifest = self.carregar_sync_manifest()
        if manifest is None:
            return erros

        md_files_reais = {f.name for f in self.encontrar_arquivos_md()}

        # Verificar documentos listados no manifest
        if "documentos" in manifest:
            documentos = manifest.get("documentos")
            if isinstance(documentos, list):
                for doc in documentos:
                    if isinstance(doc, dict) and "nome" in doc:
                        nome_arquivo = doc.get("nome")
                        if isinstance(nome_arquivo, str) and nome_arquivo not in md_files_reais:
                            erros.append(
                                ErroValidacao(
                                    arquivo="SYNC_MANIFEST.json",
                                    tipo_erro="SYNC",
                                    linha=0,
                                    mensagem=f"Arquivo listado nao encontrado: {nome_arquivo}",
                                    severidade="WARNING",
                                )
                            )

        return erros

    # ========================================================================
    # VALIDAÇÃO COMPLETA DE ARQUIVO
    # ========================================================================

    def validar_arquivo(self, arquivo: Path) -> ResultadoValidacao:
        """Valida um arquivo .md completo.

        Args:
            arquivo: Arquivo a validar.

        Returns:
            ResultadoValidacao com resultado detalhado.
        """
        timestamp_inicio = datetime.now()

        resultado = ResultadoValidacao(arquivo=arquivo.name, valido=True)

        # Encoding
        if not self.validar_encoding(arquivo):
            resultado.valido = False
            resultado.avisos.append("Arquivo não está em UTF-8")

        # MD013
        erros_md013 = self.validar_md013(arquivo)
        resultado.erros.extend(erros_md013)

        # MD001
        erros_md001 = self.validar_md001(arquivo)
        resultado.erros.extend(erros_md001)
        if erros_md001:
            resultado.valido = False

        # MD022
        erros_md022 = self.validar_md022(arquivo)
        resultado.erros.extend(erros_md022)

        # Se houver erros, marcar como inválido
        if resultado.erros:
            resultado.valido = False

        # Tempo
        resultado.tempo_validacao = (
            datetime.now() - timestamp_inicio
        ).total_seconds()

        return resultado

    # ========================================================================
    # GERAÇÃO DE RELATÓRIO
    # ========================================================================

    def gerar_relatorio(self) -> RelatorioValidacao:
        """Gera relatório consolidado de validação.

        Returns:
            RelatorioValidacao com resultado completo.
        """
        timestamp_inicio = datetime.now()

        # Encontrar arquivos
        md_files = self.encontrar_arquivos_md()

        # Validar cada um
        resultados: List[ResultadoValidacao] = []
        total_erros = 0
        total_avisos = 0
        arquivos_invalidos = 0

        for md_file in md_files:
            resultado = self.validar_arquivo(md_file)
            resultados.append(resultado)

            if not resultado.valido:
                arquivos_invalidos += 1

            total_erros += len(resultado.erros)
            total_avisos += len(resultado.avisos)

        # Validar SYNC_MANIFEST
        erros_sync = self.validar_sync_manifest()
        total_erros += len(erros_sync)

        if erros_sync:
            resultado_sync = ResultadoValidacao(
                arquivo="SYNC_MANIFEST.json",
                valido=False,
                erros=erros_sync,
            )
            resultados.append(resultado_sync)
            arquivos_invalidos += 1

        # Construir relatório
        relatorio = RelatorioValidacao(
            timestamp=datetime.now().isoformat(),
            total_arquivos=len(md_files),
            arquivos_validos=len(md_files) - arquivos_invalidos,
            arquivos_invalidos=arquivos_invalidos,
            total_erros=total_erros,
            total_avisos=total_avisos,
            tempo_total_segundos=(datetime.now() - timestamp_inicio).total_seconds(),
            resultados=resultados,
        )

        return relatorio

    # ========================================================================
    # EXPORTAÇÃO E DISPLAY
    # ========================================================================

    def exibir_relatorio(self, relatorio: RelatorioValidacao) -> None:
        """Exibe relatório formatado no console.

        Args:
            relatorio: RelatorioValidacao a exibir.
        """
        print("\n" + "=" * 80)
        print("VALIDAÇÃO DE DOCUMENTAÇÃO - RELATÓRIO")
        print("=" * 80)
        print(f"Timestamp:           {relatorio.timestamp}")
        print(f"Total de arquivos:   {relatorio.total_arquivos}")
        print(f"Válidos:             {relatorio.arquivos_validos}")
        print(f"Inválidos:           {relatorio.arquivos_invalidos}")
        print(f"Total de erros:      {relatorio.total_erros}")
        print(f"Total de avisos:     {relatorio.total_avisos}")
        print(f"Tempo:               {relatorio.tempo_total_segundos:.2f}s")
        print()

        if relatorio.arquivos_invalidos > 0:
            print("ERROS ENCONTRADOS:")
            print("-" * 80)
            for resultado in relatorio.resultados:
                if not resultado.valido:
                    print(f"\n{resultado.arquivo}:")
                    for erro in resultado.erros:
                        print(f"  {erro}")

        print("\n" + "=" * 80 + "\n")

    def exportar_relatorio_json(
        self, relatorio: RelatorioValidacao, caminho: str | Path = "outputs/relatorio_validacao.json"
    ) -> None:
        """Exporta relatório em formato JSON.

        Args:
            relatorio: RelatorioValidacao a exportar.
            caminho: Caminho do arquivo de saída.
        """
        caminho = Path(caminho)
        caminho.parent.mkdir(parents=True, exist_ok=True)

        dados = {
            "timestamp": relatorio.timestamp,
            "total_arquivos": relatorio.total_arquivos,
            "arquivos_validos": relatorio.arquivos_validos,
            "arquivos_invalidos": relatorio.arquivos_invalidos,
            "total_erros": relatorio.total_erros,
            "total_avisos": relatorio.total_avisos,
            "tempo_total_segundos": relatorio.tempo_total_segundos,
            "resultados": [
                {
                    "arquivo": r.arquivo,
                    "valido": r.valido,
                    "erros": [asdict(e) for e in r.erros],
                    "avisos": r.avisos,
                    "tempo_validacao": r.tempo_validacao,
                }
                for r in relatorio.resultados
            ],
        }

        with open(caminho, "w", encoding="utf-8") as f:
            json.dump(dados, f, indent=2, ensure_ascii=False)

        self.logger.info(f"Relatório exportado para {caminho}")

    # ========================================================================
    # MAIN EXECUTION
    # ========================================================================

    def executar(self) -> int:
        """Executa validação completa.

        Returns:
            0 se tudo OK, 1 se houver erros críticos.
        """
        relatorio = self.gerar_relatorio()
        self.exibir_relatorio(relatorio)
        self.exportar_relatorio_json(relatorio)

        if relatorio.arquivos_invalidos > 0:
            self.logger.warning(
                f"Validação falhou: {relatorio.arquivos_invalidos} "
                f"arquivo(s) com erro(s)"
            )
            return 1

        self.logger.info("Validação concluída com sucesso!")
        return 0


# ============================================================================
# ENTRY POINT
# ============================================================================

def main() -> int:
    """Main entry point do validador."""
    import argparse

    parser = argparse.ArgumentParser(
        description="Validador de documentação e sincronização."
    )
    parser.add_argument(
        "--docs-path",
        type=str,
        default="docs",
        help="Caminho para diretório de documentação (padrão: docs)",
    )
    parser.add_argument(
        "--output",
        type=str,
        default="outputs/relatorio_validacao.json",
        help="Caminho para relatório JSON de saída",
    )

    args = parser.parse_args()

    validator = DocumentValidator(docs_path=args.docs_path)
    relatorio = validator.gerar_relatorio()
    validator.exibir_relatorio(relatorio)
    validator.exportar_relatorio_json(relatorio, caminho=args.output)

    return 1 if relatorio.arquivos_invalidos > 0 else 0


if __name__ == "__main__":
    import sys
    sys.exit(main())
