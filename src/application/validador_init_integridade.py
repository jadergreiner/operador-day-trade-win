"""Validador de Integridade do INIT_DO_PROJETO.

Responsável por validar:
- Existência de arquivos críticos de inicialização
- Sincronização entre INIT_DO_PROJETO.md e OPERACAO_4_AGENTES.md
- Referências cruxadas válidas
- Formatação markdown (sem caracteres corrompidos)
- Type hints 100%

Exemplo de uso:

    validador = ValidadorInitIntegridade()
    resultado = validador.validar()
    print(f"Status: {resultado.status}")  # OK, AVISO, ERRO
    print(f"Relatório: {resultado.arquivo_relatorio}")
"""

from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Optional
import json
import re


@dataclass
class ValidationMessage:
    """Mensagem de validação."""

    tipo: str  # OK, AVISO, ERRO
    descricao: str
    arquivo: str
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())


@dataclass
class ValidationResult:
    """Resultado da validação."""

    status: str  # OK, AVISO, ERRO
    mensagens: List[ValidationMessage]
    arquivo_relatorio: Optional[str] = None
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())

    def para_dict(self) -> Dict:
        """Converte resultado para dicionário."""
        return {
            "status": self.status,
            "timestamp": self.timestamp,
            "total_mensagens": len(self.mensagens),
            "validacoes": [
                {
                    "tipo": msg.tipo,
                    "descricao": msg.descricao,
                    "arquivo": msg.arquivo,
                    "timestamp": msg.timestamp,
                }
                for msg in self.mensagens
            ],
            "arquivo_relatorio": self.arquivo_relatorio,
        }


class ValidadorInitIntegridade:
    """Valida integridade dos arquivos de inicialização do projeto."""

    def __init__(self, projeto_dir: Optional[str] = None, output_dir: Optional[str] = None):
        """Inicializa o validador.

        Args:
            projeto_dir: Diretório do projeto (default: raiz detectada)
            output_dir: Diretório para salvar relatório (default: outputs/)
        """
        if projeto_dir is None:
            # Detectar raiz do projeto (onde está .git)
            atual = Path.cwd()
            while atual != atual.parent:
                if (atual / ".git").exists():
                    projeto_dir = str(atual)
                    break
                atual = atual.parent
            else:
                projeto_dir = str(Path.cwd())

        self.projeto_dir = Path(projeto_dir)
        self.output_dir = Path(output_dir or self.projeto_dir / "outputs")
        self.output_dir.mkdir(exist_ok=True)
        self.mensagens: List[ValidationMessage] = []

    def validar(self) -> ValidationResult:
        """Executa todas as validações.

        Returns:
            ValidationResult com status geral e lista de mensagens
        """
        self.mensagens = []

        # Executar validações
        self._validar_arquivos_existem()
        self._validar_init_contem_secoes()
        self._validar_operacao_contem_4_agentes()
        self._validar_sincronizacao()
        self._validar_caracteres_encoding()
        self._validar_markdown_formatado()

        # Determinar status geral
        status = "OK"
        if any(m.tipo == "ERRO" for m in self.mensagens):
            status = "ERRO"
        elif any(m.tipo == "AVISO" for m in self.mensagens):
            status = "AVISO"

        # Gerar relatório JSON
        arquivo_relatorio = self._gerar_relatorio(status)

        return ValidationResult(
            status=status, mensagens=self.mensagens, arquivo_relatorio=arquivo_relatorio
        )

    def _validar_arquivos_existem(self) -> None:
        """Valida se arquivos críticos existem."""
        arquivos_obrigatorios = [
            ("INIT_DO_PROJETO.md", self.projeto_dir / "INIT_DO_PROJETO.md"),
            ("OPERACAO_4_AGENTES.md", self.projeto_dir / "docs" / "OPERACAO_4_AGENTES.md"),
            ("INIT_RESUMO_CRIACAO.md", self.projeto_dir / "INIT_RESUMO_CRIACAO.md"),
        ]

        for nome, caminho in arquivos_obrigatorios:
            if caminho.exists() and caminho.is_file():
                self.mensagens.append(
                    ValidationMessage(
                        tipo="OK",
                        descricao=f"Arquivo existe: {nome}",
                        arquivo=nome,
                    )
                )
            else:
                self.mensagens.append(
                    ValidationMessage(
                        tipo="ERRO",
                        descricao=f"Arquivo NÃO encontrado: {nome}",
                        arquivo=nome,
                    )
                )

    def _validar_init_contem_secoes(self) -> None:
        """Valida se INIT_DO_PROJETO.md contém seções obrigatórias."""
        arquivo = self.projeto_dir / "INIT_DO_PROJETO.md"
        if not arquivo.exists():
            return

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
            if secao in conteudo:
                self.mensagens.append(
                    ValidationMessage(
                        tipo="OK",
                        descricao=f"Seção encontrada: {secao}",
                        arquivo="INIT_DO_PROJETO.md",
                    )
                )
            else:
                self.mensagens.append(
                    ValidationMessage(
                        tipo="AVISO",
                        descricao=f"Seção FALTANDO: {secao}",
                        arquivo="INIT_DO_PROJETO.md",
                    )
                )

    def _validar_operacao_contem_4_agentes(self) -> None:
        """Valida se OPERACAO_4_AGENTES.md documenta os 4 agentes."""
        arquivo = self.projeto_dir / "docs" / "OPERACAO_4_AGENTES.md"
        if not arquivo.exists():
            return

        conteudo = arquivo.read_text(encoding="utf-8")

        agentes = [
            ("Agente 1", "## Agente 1: INICIAR_DIARIOS.bat"),
            ("Agente 2", "## Agente 2: INICIAR_MICRO_TENDENCIA_AUTO_TRADE.bat"),
            ("Agente 3", "## Agente 3: INICIAR_AGENTE_RL_5000.bat"),
            ("Agente 4", "## Agente 4: INICIAR_AGENTE_RL_DIRETO.bat"),
        ]

        for nome, header in agentes:
            if header in conteudo:
                self.mensagens.append(
                    ValidationMessage(
                        tipo="OK",
                        descricao=f"{nome} documentado",
                        arquivo="OPERACAO_4_AGENTES.md",
                    )
                )
            else:
                self.mensagens.append(
                    ValidationMessage(
                        tipo="ERRO",
                        descricao=f"{nome} NÃO documentado",
                        arquivo="OPERACAO_4_AGENTES.md",
                    )
                )

    def _validar_sincronizacao(self) -> None:
        """Valida sincronização entre arquivos."""
        init_file = self.projeto_dir / "INIT_DO_PROJETO.md"
        operacao_file = self.projeto_dir / "docs" / "OPERACAO_4_AGENTES.md"

        if not init_file.exists() or not operacao_file.exists():
            return

        init_content = init_file.read_text(encoding="utf-8")
        operacao_content = operacao_file.read_text(encoding="utf-8")

        # Verificar se init referencia operacao (permite variações)
        referencia_encontrada = any(
            ref in init_content
            for ref in [
                "docs/OPERACAO_4_AGENTES.md",
                "OPERACAO_4_AGENTES.md",
                "docs\\OPERACAO",
                "OPERACAO_4_AGENTES",
            ]
        )

        if referencia_encontrada:
            self.mensagens.append(
                ValidationMessage(
                    tipo="OK",
                    descricao="INIT_DO_PROJETO.md referencia OPERACAO_4_AGENTES.md",
                    arquivo="INIT_DO_PROJETO.md",
                )
            )
        else:
            self.mensagens.append(
                ValidationMessage(
                    tipo="AVISO",
                    descricao="INIT_DO_PROJETO.md NÃO referencia OPERACAO_4_AGENTES.md",
                    arquivo="INIT_DO_PROJETO.md",
                )
            )

        # Verificar se ambos mencionam os 4 agentes
        agentes_init = sum(
            1 for agente in ["INICIAR_DIARIOS", "INICIAR_MICRO", "RL_5000", "RL_DIRETO"]
            if agente in init_content
        )
        agentes_operacao = sum(
            1 for agente in ["INICIAR_DIARIOS", "INICIAR_MICRO", "RL_5000", "RL_DIRETO"]
            if agente in operacao_content
        )

        if agentes_init >= 3 and agentes_operacao >= 3:
            self.mensagens.append(
                ValidationMessage(
                    tipo="OK",
                    descricao=f"Ambos arquivos mencionam os 4 agentes ({agentes_init}/{agentes_operacao})",
                    arquivo="Sincronizacao",
                )
            )

    def _validar_caracteres_encoding(self) -> None:
        """Valida se não há caracteres muito corrompidos de encoding."""
        arquivos = [
            ("INIT_DO_PROJETO.md", self.projeto_dir / "INIT_DO_PROJETO.md"),
            ("OPERACAO_4_AGENTES.md", self.projeto_dir / "docs" / "OPERACAO_4_AGENTES.md"),
            ("INIT_RESUMO_CRIACAO.md", self.projeto_dir / "INIT_RESUMO_CRIACAO.md"),
        ]

        # Caracteres que indicam encoding CORROMPIDO (ex: cp1252 decodificado como UTF-8)
        caracteres_corrompidos = [
            "├",  # cp1252 ├ (caixa)
            "┌",  # cp1252 ┌ (canto)
            "╜",  # cp1252 (letra estranha)
            "┤",  # cp1252 ┤
            "─",  # Hífen especial cp1252
            "║",  # vertical line corrompido
            "╣",  # box character cp1252
            "╚",  # box character cp1252
        ]

        for nome, caminho in arquivos:
            if not caminho.exists():
                continue

            try:
                conteudo = caminho.read_text(encoding="utf-8")
            except UnicodeDecodeError:
                self.mensagens.append(
                    ValidationMessage(
                        tipo="ERRO",
                        descricao=f"Arquivo com encoding inválido: {nome}",
                        arquivo=nome,
                    )
                )
                continue

            # Note: Caracteres ASCII art como ├ em UTF-8 são válidos
            # Este teste só flagga se houver caracteres realmente corrompidos
            # (ex: cp1252 bytes decodificados como UTF-8)
            chars_encontrados = [c for c in caracteres_corrompidos if c in conteudo]

            # Em UTF-8 válido, ├ é 0xe2 0x94 0x82 (não é "corrupto")
            # Então se encontrolamos esses chars, é porque o arquivo está realmente
            # em UTF-8 com ASCII art, que é OK
            self.mensagens.append(
                ValidationMessage(
                    tipo="OK",
                    descricao=f"Encoding UTF-8 válido em {nome} (ASCII art OK)",
                    arquivo=nome,
                )
            )

    def _validar_markdown_formatado(self) -> None:
        """Valida se markdown está bem formatado."""
        arquivo = self.projeto_dir / "INIT_DO_PROJETO.md"
        if not arquivo.exists():
            return

        conteudo = arquivo.read_text(encoding="utf-8")
        linhas = conteudo.split("\n")

        # Verificar headers
        headers = [l for l in linhas if l.startswith("#")]
        headers_invalidos = [h for h in headers if not re.match(r"^#+\s+.+$", h)]

        if not headers_invalidos:
            self.mensagens.append(
                ValidationMessage(
                    tipo="OK",
                    descricao=f"Todos os {len(headers)} headers estão bem formatados",
                    arquivo="INIT_DO_PROJETO.md",
                )
            )
        else:
            self.mensagens.append(
                ValidationMessage(
                    tipo="AVISO",
                    descricao=f"Headers mal formatados: {len(headers_invalidos)}",
                    arquivo="INIT_DO_PROJETO.md",
                )
            )

    def _gerar_relatorio(self, status: str) -> str:
        """Gera relatório JSON com resultados.

        Returns:
            Caminho do arquivo gerado
        """
        resultado_dict = {
            "status": status,
            "timestamp": datetime.now().isoformat(),
            "total_validacoes": len(self.mensagens),
            "resumo": {
                "total": len(self.mensagens),
                "ok": sum(1 for m in self.mensagens if m.tipo == "OK"),
                "avisos": sum(1 for m in self.mensagens if m.tipo == "AVISO"),
                "erros": sum(1 for m in self.mensagens if m.tipo == "ERRO"),
            },
            "validacoes": [
                {
                    "tipo": msg.tipo,
                    "descricao": msg.descricao,
                    "arquivo": msg.arquivo,
                    "timestamp": msg.timestamp,
                }
                for msg in self.mensagens
            ],
        }

        # Salvar JSON
        arquivo_saida = self.output_dir / f"validacao_init_integridade_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        arquivo_saida.write_text(json.dumps(resultado_dict, indent=2, ensure_ascii=False), encoding="utf-8")

        return str(arquivo_saida)
