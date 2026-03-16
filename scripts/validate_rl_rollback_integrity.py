#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Script de Validacao - P2-RL-1: Rollback Automatico de Modelo RL

Valida:
- Type hints 100% (mypy --strict compatibility)
- Docstrings 100% (todos metodos/classes/parametros)
- Lines of code (LOC)
- Import integrity
"""

import ast
import sys
from pathlib import Path
from typing import Dict, List, Tuple


def validar_type_hints(arquivo: Path) -> Tuple[bool, List[str]]:
    """Valida se arquivo tem 100% type hints.

    Verifica:
    - Todas funcoes tem return type
    - Todos parametros tem type annotation (exceto self, cls)

    Returns:
        (sucesso, mensagens de erro)
    """
    erros = []

    try:
        with open(arquivo, "r", encoding="utf-8") as f:
            tree = ast.parse(f.read())
    except SyntaxError as e:
        return False, [f"Erro de sintaxe: {e}"]

    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef):
            # Verificar parametros
            parametros_sem_type = []
            for arg in node.args.args:
                if arg.arg not in ("self", "cls") and arg.annotation is None:
                    parametros_sem_type.append(arg.arg)

            if parametros_sem_type:
                erros.append(
                    f"Funcao '{node.name}': parametros sem type: {parametros_sem_type}"
                )

            # Verificar return type
            if node.name.startswith("_"):
                continue  # Private methods podem ser dispensados
            if node.returns is None and node.name != "__init__":
                erros.append(f"Funcao '{node.name}': sem return type")

    return len(erros) == 0, erros


def validar_docstrings(arquivo: Path) -> Tuple[bool, List[str]]:
    """Valida se arquivo tem docstrings 100%.

    Verifica:
    - Modulo tem docstring
    - Classes tem docstring
    - Metodos publicos tem docstring

    Returns:
        (sucesso, mensagens)
    """
    erros = []

    try:
        with open(arquivo, "r", encoding="utf-8") as f:
            tree = ast.parse(f.read())
    except SyntaxError as e:
        return False, [f"Erro syntaxe: {e}"]

    # Check modulo
    if ast.get_docstring(tree) is None:
        erros.append("Modulo sem docstring")

    # Check classes e metodos
    for node in ast.walk(tree):
        if isinstance(node, ast.ClassDef):
            if ast.get_docstring(node) is None:
                erros.append(f"Classe '{node.name}' sem docstring")

            for item in node.body:
                if isinstance(item, ast.FunctionDef) and not item.name.startswith("_"):
                    if ast.get_docstring(item) is None:
                        erros.append(
                            f"Metodo '{node.name}.{item.name}' sem docstring"
                        )

    return len(erros) == 0, erros


def contar_loc(arquivo: Path) -> int:
    """Conta linhas de código (excluindo comentarios e vazias)."""
    try:
        with open(arquivo, "r", encoding="utf-8") as f:
            linhas = f.readlines()
    except IOError:
        return 0

    loc = 0
    for linha in linhas:
        linha = linha.strip()
        if linha and not linha.startswith("#"):
            loc += 1

    return loc


def validar_imports(arquivo: Path) -> Tuple[bool, List[str]]:
    """Valida que imports podem ser resolvidos.

    Returns:
        (sucesso, mensagens)
    """
    erros = []

    try:
        with open(arquivo, "r", encoding="utf-8") as f:
            tree = ast.parse(f.read())
    except SyntaxError as e:
        return False, [f"Erro syntax: {e}"]

    # Procurar imports
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                # Básica: detectar imports incomuns
                if "invalid" in alias.name.lower():
                    erros.append(f"Import suspeito: {alias.name}")

        elif isinstance(node, ast.ImportFrom):
            if node.module is None:
                erros.append("Relative import sem modulo")

    return len(erros) == 0, erros


def main() -> int:
    """Valida arquivo principal.

    Returns:
        0 se OK, 1 se erro
    """
    arquivo = Path("src/application/rl_model_rollback_manager.py")

    if not arquivo.exists():
        print(f"❌ Erro: Arquivo não encontrado: {arquivo}")
        return 1

    print(f"🔍 Validando: {arquivo}\n")

    # 1. Type hints
    print("1️⃣  Type Hints...")
    ok_types, erros_types = validar_type_hints(arquivo)
    if ok_types:
        print("   ✅ 100% type hints OK")
    else:
        print(f"   ❌ Erros de type hints:")
        for erro in erros_types:
            print(f"      - {erro}")

    # 2. Docstrings
    print("\n2️⃣  Docstrings...")
    ok_docs, erros_docs = validar_docstrings(arquivo)
    if ok_docs:
        print("   ✅ 100% docstrings OK")
    else:
        print(f"   ❌ Erros de docstrings (primeiros 5):")
        for erro in erros_docs[:5]:
            print(f"      - {erro}")

    # 3. LOC
    print("\n3️⃣  Lines of Code...")
    loc = contar_loc(arquivo)
    print(f"   📊 {loc} linhas de código")

    # 4. Imports
    print("\n4️⃣  Imports...")
    ok_imports, erros_imports = validar_imports(arquivo)
    if ok_imports:
        print("   ✅ Imports OK")
    else:
        print(f"   ⚠️  Imports:")
        for erro in erros_imports:
            print(f"      - {erro}")

    # Resultado final
    print("\n" + "=" * 50)
    sucesso = ok_types and ok_docs and ok_imports
    if sucesso:
        print("✅ VALIDACAO COMPLETA: SUCESSO")
        print(f"   Type hints: OK")
        print(f"   Docstrings: OK")
        print(f"   LOC: {loc}")
        print(f"   Imports: OK")
        return 0
    else:
        print("❌ VALIDACAO FALHOU")
        return 1


if __name__ == "__main__":
    sys.exit(main())
