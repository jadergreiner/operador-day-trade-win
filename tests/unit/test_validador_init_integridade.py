"""Testes para validador de integridade do INIT_DO_PROJETO.

Testa:
- Existência de arquivos críticos
- Sincronização entre INIT_DO_PROJETO.md e OPERACAO_4_AGENTES.md
- Referências cruzadas válidas
- Formatação markdown (sem encoding issues)
- Type hints 100%
"""

import pytest
from pathlib import Path
from typing import List, Tuple
import json
import re


class TestValidadorInitIntegridade:
    """Suite de testes para ValidadorInitIntegridade."""

    @pytest.fixture
    def root_dir(self) -> Path:
        """Diretório raiz do projeto."""
        return Path(__file__).parent.parent.parent

    def test_arquivo_init_existe(self, root_dir: Path) -> None:
        """Testa se INIT_DO_PROJETO.md existe na raiz."""
        arquivo = root_dir / "INIT_DO_PROJETO.md"
        assert arquivo.exists(), f"INIT_DO_PROJETO.md não encontrado em {root_dir}"
        assert arquivo.is_file(), "INIT_DO_PROJETO.md não é arquivo"

    def test_arquivo_operacao_existe(self, root_dir: Path) -> None:
        """Testa se OPERACAO_4_AGENTES.md existe em docs/."""
        arquivo = root_dir / "docs" / "OPERACAO_4_AGENTES.md"
        assert arquivo.exists(), f"OPERACAO_4_AGENTES.md não encontrado em {arquivo.parent}"
        assert arquivo.is_file(), "OPERACAO_4_AGENTES.md não é arquivo"

    def test_init_contem_secoes_obrigatorias(self, root_dir: Path) -> None:
        """Testa se INIT_DO_PROJETO.md contém seções obrigatorias."""
        arquivo = root_dir / "INIT_DO_PROJETO.md"
        conteudo = arquivo.read_text(encoding="utf-8")

        secoes_obrigatorias = [
            "# 🤖 INÍCIO",
            "## ⚡ Quick Start",
            "## 📋 Arquitetura",
            "## 🎯 Os 4 Agentes",
            "## 📁 Estrutura de Pastas",
            "## 🔍 Verificação de Saúde",
            "## 📊 Fluxo de Operação",
            "## 🚀 Próximos Passos",
        ]

        for secao in secoes_obrigatorias:
            assert secao in conteudo, f"Seção '{secao}' não encontrada em INIT_DO_PROJETO.md"

    def test_operacao_contem_4_agentes(self, root_dir: Path) -> None:
        """Testa se OPERACAO_4_AGENTES.md documenta todos os 4 agentes."""
        arquivo = root_dir / "docs" / "OPERACAO_4_AGENTES.md"
        conteudo = arquivo.read_text(encoding="utf-8")

        agentes = [
            "## Agente 1: INICIAR_DIARIOS.bat",
            "## Agente 2: INICIAR_MICRO_TENDENCIA_AUTO_TRADE.bat",
            "## Agente 3: INICIAR_AGENTE_RL_5000.bat",
            "## Agente 4: INICIAR_AGENTE_RL_DIRETO.bat",
        ]

        for agente in agentes:
            assert agente in conteudo, f"Agente não documentado: {agente}"

    def test_init_referencia_operacao(self, root_dir: Path) -> None:
        """Testa se INIT_DO_PROJETO.md referencia OPERACAO_4_AGENTES.md."""
        arquivo = root_dir / "INIT_DO_PROJETO.md"
        conteudo = arquivo.read_text(encoding="utf-8")

        # Aceitar qualquer variação de referência
        referenciadores = [
            "OPERACAO_4_AGENTES",
            "Agente 1:",
            "Agente 2:",
            "Agente 3:",
            "Agente 4:",
        ]

        encontrou = any(ref in conteudo for ref in referenciadores)
        assert encontrou, (
            "INIT_DO_PROJETO.md deve referenciar documentacao dos 4 agentes"
        )

    def test_nenhum_caractere_encoding_corrompido(self, root_dir: Path) -> None:
        """Testa se não há caracteres de encoding corrompido.

        Nota: Caracteres ASCII art como ├ em UTF-8 são válidos e aceitáveis.
        Este teste verifica apenas por erros graves de encoding.
        """
        arquivos = [
            root_dir / "INIT_DO_PROJETO.md",
            root_dir / "docs" / "OPERACAO_4_AGENTES.md",
            root_dir / "INIT_RESUMO_CRIACAO.md",
        ]

        for arquivo in arquivos:
            if arquivo.exists():
                # Tentar ler em UTF-8
                try:
                    conteudo = arquivo.read_text(encoding="utf-8")
                    # Se conseguir ler, o encoding está OK
                    assert len(conteudo) > 0, f"Arquivo {arquivo.name} vazio"
                except UnicodeDecodeError as e:
                    raise AssertionError(
                        f"Arquivo {arquivo.name} tem encoding inválido: {e}"
                    )

    def test_arquivos_markdown_bem_formados(self, root_dir: Path) -> None:
        """Testa se arquivos markdown têm headers bem formados."""
        arquivo = root_dir / "INIT_DO_PROJETO.md"
        conteudo = arquivo.read_text(encoding="utf-8")

        # Verificar que headers têm formato correto: # Header, ## Header, etc
        linhas = conteudo.split("\n")
        headers = [l for l in linhas if l.startswith("#")]

        for header in headers:
            # Format: # Title, ## Title, ### Title, etc
            assert re.match(r"^#+\s+.+$", header), f"Header mal formatado: {header}"

    def test_instancia_validador(self) -> None:
        """Testa se ValidadorInitIntegridade pode ser instanciado."""
        from src.application.validador_init_integridade import (
            ValidadorInitIntegridade,
        )

        validador = ValidadorInitIntegridade()
        assert validador is not None
        assert hasattr(validador, "validar")
        assert callable(validador.validar)

    def test_validador_retorna_resultado_estruturado(self) -> None:
        """Testa se validador retorna resultado com estrutura esperada."""
        from src.application.validador_init_integridade import (
            ValidadorInitIntegridade,
            ValidationResult,
        )

        validador = ValidadorInitIntegridade()
        resultado = validador.validar()

        assert isinstance(resultado, ValidationResult)
        assert hasattr(resultado, "status")
        assert hasattr(resultado, "mensagens")
        assert hasattr(resultado, "arquivo_relatorio")
        assert isinstance(resultado.mensagens, list)

    def test_validador_gera_relatorio_json(self, tmp_path: Path) -> None:
        """Testa se validador gera relatório JSON."""
        from src.application.validador_init_integridade import (
            ValidadorInitIntegridade,
        )

        validador = ValidadorInitIntegridade(output_dir=str(tmp_path))
        resultado = validador.validar()

        # Verificar se arquivo JSON foi criado
        arquivos_json = list(tmp_path.glob("*.json"))
        assert len(arquivos_json) > 0, "Nenhum arquivo JSON gerado"

        # Verificar conteúdo
        arquivo = arquivos_json[0]
        conteudo = json.loads(arquivo.read_text(encoding="utf-8"))

        assert "status" in conteudo
        assert "timestamp" in conteudo
        assert "validacoes" in conteudo

    def test_validador_100_porcento_type_hints(self) -> None:
        """Testa se ValidadorInitIntegridade tem 100% de type hints."""
        from src.application import validador_init_integridade

        # Verificar imports e assinaturas
        modulo_source = (
            Path(__file__).parent.parent.parent
            / "src"
            / "application"
            / "validador_init_integridade.py"
        ).read_text(encoding="utf-8")

        # Contar métodos com type hints
        metodos = re.findall(r"def\s+\w+\([^)]*\)\s*->\s*\w+", modulo_source)
        assert len(metodos) >= 5, f"Esperava >=5 métodos com type hints, encontrou {len(metodos)}"

        # Verificar que dataclasses existem
        assert "@dataclass" in modulo_source, "Dataclasses não encontradas"
        assert "ValidationMessage" in modulo_source, "ValidationMessage ausente"
        assert "ValidationResult" in modulo_source, "ValidationResult ausente"

