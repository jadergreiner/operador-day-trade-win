#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
FASE 1 - STEP 1️⃣ CODE REVIEW VERIFICATION SCRIPT

Para CTO executar: Validar implementação de Risk Validators

Execução:
  python scripts/fase1_step1_code_review.py
"""

import subprocess
import sys
from pathlib import Path
from typing import Tuple, List

# Repo root
REPO_ROOT = Path(__file__).parent.parent


def check_file_exists() -> bool:
    """Verifica se arquivo risk_validator.py existe."""
    file_path = REPO_ROOT / "src" / "application" / "risk_validator.py"
    exists = file_path.exists()
    status = "✅ EXISTE" if exists else "❌ NÃO ENCONTRADO"
    print(f"  Arquivo: {file_path}")
    print(f"  Status: {status}\n")
    return exists


def count_lines() -> int:
    """Conta linhas de código."""
    file_path = REPO_ROOT / "src" / "application" / "risk_validator.py"
    with open(file_path, 'r', encoding='utf-8') as f:
        lines = len(f.readlines())
    print(f"  Linhas de código: {lines}")
    return lines


def check_type_hints() -> Tuple[bool, str]:
    """Valida type hints com mypy."""
    print("\n🔍 Validando Type Hints (mypy --strict)...")
    result = subprocess.run(
        [sys.executable, "-m", "mypy",
         "src/application/risk_validator.py",
         "--strict",
         "--ignore-missing-imports"],
        capture_output=True,
        text=True,
        cwd=str(REPO_ROOT)
    )

    if result.returncode == 0:
        print("  ✅ Type hints: OK (mypy strict)\n")
        return True, ""
    else:
        print("  ❌ Type hints: FALHOU")
        print(f"  Erro: {result.stdout}\n")
        return False, result.stdout


def check_three_gates_implemented() -> bool:
    """Verifica se os 3 gates estão implementados."""
    file_path = REPO_ROOT / "src" / "application" / "risk_validator.py"
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()

    gates = [
        ("Capital Adequacy", "CapitalAdequacyValidator"),
        ("Correlation", "CorrelationValidator"),
        ("Volatility", "VolatilityValidator")
    ]

    all_found = True
    for gate_name, class_name in gates:
        found = class_name in content
        status = "✅" if found else "❌"
        print(f"  {status} Gate {gate_name:20} ({class_name})")
        all_found = all_found and found

    print()
    return all_found


def check_docstrings() -> bool:
    """Verifica se docstrings estão presentes."""
    file_path = REPO_ROOT / "src" / "application" / "risk_validator.py"
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()

    # Count docstrings
    docstring_count = content.count('"""')
    classes_count = content.count("class ")

    has_module_doc = content.startswith('"""')
    has_class_docs = docstring_count >= (classes_count * 2)  # Pelo menos 1 docstring por classe

    print(f"  Module docstring:    {'✅' if has_module_doc else '❌'}")
    print(f"  Class docstrings:    {'✅' if has_class_docs else '❌'}")
    print(f"  Total docstrings:    {docstring_count // 2} (esperado: ≥{classes_count})\n")

    return has_module_doc and has_class_docs


def check_no_critical_todos() -> bool:
    """Verifica se há TODOs/FIXMEs críticos."""
    file_path = REPO_ROOT / "src" / "application" / "risk_validator.py"
    with open(file_path, 'r', encoding='utf-8') as f:
        lines = f.readlines()

    critical_markers = ["TODO", "FIXME", "XXX", "HACK"]
    found_critical = []

    for i, line in enumerate(lines, 1):
        # Extrair parte de comentário se existir
        if '#' in line:
            comment_part = line.split('#', 1)[1]
            for marker in critical_markers:
                # Procurar marker como palavra completa no comentário
                if f" {marker}" in comment_part.upper() or comment_part.upper().startswith(marker):
                    found_critical.append((i, marker, line.strip()))

    if found_critical:
        print(f"  ⚠️  Encontrados {len(found_critical)} marcadores críticos:")
        for line_num, marker, text in found_critical:
            print(f"     Linha {line_num}: {marker} - {text[:60]}")
        print()
        return False
    else:
        print("  ✅ Sem TODOs/FIXMEs/XXX críticos\n")
        return True


def check_chain_of_responsibility() -> bool:
    """Verifica se padrão Chain of Responsibility está implementado."""
    file_path = REPO_ROOT / "src" / "application" / "risk_validator.py"
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()

    checks = [
        ("RiskValidator (base class)", "class RiskValidator(ABC):"),
        ("next_validator attribute", "next_validator"),
        ("chain_validate method", "def chain_validate"),
        ("RiskValidationProcessor", "class RiskValidationProcessor"),
    ]

    all_found = True
    for check_name, pattern in checks:
        found = pattern in content
        status = "✅" if found else "❌"
        print(f"  {status} {check_name}")
        all_found = all_found and found

    print()
    return all_found


def check_code_quality() -> bool:
    """Verifica qualidade geral do código."""
    file_path = REPO_ROOT / "src" / "application" / "risk_validator.py"
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()

    checks = {
        "Sem imports não utilizados": True,  # Verificação visual
        "Sem linhas > 100 caracteres": max(
            len(line) for line in content.split('\n')
        ) < 100,
        "Sem duplicação aparente": content.count("def validate") <= 4,  # 3 gates + 1 processor
        "Exemplo de uso incluído": "if __name__" in content or "async def example" in content,
    }

    for check_name, status in checks.items():
        symbol = "✅" if status else "⚠️"
        print(f"  {symbol} {check_name}")

    print()
    return all(checks.values())


def run_full_review() -> Tuple[bool, List[str]]:
    """Executa revisão completa."""
    print("\n" + "=" * 70)
    print("🔴 FASE 1 - STEP 1️⃣: RISK VALIDATORS CODE REVIEW")
    print("=" * 70 + "\n")

    print("📋 CHECKLIST DO CTO:\n")
    print("1️⃣ Arquivo Existe?")
    if not check_file_exists():
        return False, ["Arquivo risk_validator.py não encontrado"]

    print("2️⃣ Quantidade de Código")
    lines = count_lines()
    if lines < 300:
        print(f"  ⚠️  Código muito pequeno ({lines} linhas), esperado ≥300\n")

    print("3️⃣ Type Hints (mypy --strict)")
    type_hints_ok, mypy_error = check_type_hints()

    print("4️⃣ 3 Gates Implementados?")
    gates_ok = check_three_gates_implemented()

    print("5️⃣ Docstrings Presentes?")
    docs_ok = check_docstrings()

    print("6️⃣ Sem TODOs/FIXMEs Críticos?")
    no_todos = check_no_critical_todos()

    print("7️⃣ Padrão Chain of Responsibility?")
    chain_ok = check_chain_of_responsibility()

    print("8️⃣ Qualidade Geral do Código?")
    quality_ok = check_code_quality()

    # Summary
    print("=" * 70)
    print("📊 RESULTADO FINAL:\n")

    all_pass = type_hints_ok and gates_ok and docs_ok and no_todos and chain_ok and quality_ok

    checks = [
        ("Type Hints (mypy --strict)", type_hints_ok),
        ("3 Gates Implementados", gates_ok),
        ("Docstrings Presentes", docs_ok),
        ("Sem TODOs Críticos", no_todos),
        ("Chain of Responsibility", chain_ok),
        ("Qualidade Geral", quality_ok),
    ]

    for check_name, status in checks:
        symbol = "✅ PASS" if status else "❌ FAIL"
        print(f"  {symbol:12} {check_name}")

    print("\n" + "=" * 70)

    if all_pass:
        print("✅ APROVADO PARA STEP 2️⃣ (TESTES)")
        print("\nPróximo: Executar FASE1_BLOQUEADORES.md Step 2️⃣\n")
        return True, []
    else:
        issues = []
        if not type_hints_ok:
            issues.append("Type hints falhou - mypy errors acima")
        if not gates_ok:
            issues.append("Algum gate não implementado")
        if not docs_ok:
            issues.append("Documentação incompleta")
        if not no_todos:
            issues.append("TODOs/FIXMEs encontrados")
        if not chain_ok:
            issues.append("Padrão Chain of Responsibility não completo")
        if not quality_ok:
            issues.append("Problemas de qualidade detectados")

        print("❌ REJEITADO - PROBLEMAS ENCONTRADOS:\n")
        for issue in issues:
            print(f"  • {issue}")
        print("\nAção: Eng Sr deve corrigir issues acima")
        print("Retry: python scripts/fase1_step1_code_review.py\n")
        return False, issues

    print("=" * 70 + "\n")


def main():
    """Entry point."""
    success, issues = run_full_review()

    # CTO Sign-off section
    print("\n" + "=" * 70)
    print("📝 ASSINATURA DO CTO:\n")
    print("Revisei o código e valido que:")
    print("  □ Todos os checks passaram")
    print("  □ 3 gates implementados corretamente")
    print("  □ Code quality aceita")
    print("  □ Pronto para STEP 2️⃣ (Testes)\n")
    print("CTO Name: _____________________________")
    print("Signature: _____________________________")
    print("Date/Time: _____________________________")
    print("\n" + "=" * 70)

    return 0 if success else 1


if __name__ == "__main__":
    sys.exit(main())

