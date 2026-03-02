#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
🚀 S2-5 FINALIZATION MASTER SCRIPT - EXECUTE TUDO AQUI

Master script que orquestra TODAS as 5 ACs do blocker S2-5:
  AC-1: Grid search fine-tuning (45 min)
  AC-2: Cross-validation final (30 min)
  AC-3: Model serialization (10 min)
  AC-4: Production inference test (20 min)
  AC-5: Final validation report (10 min)

Total estimated: 2-3 horas

Uso:
  python scripts/s2_5_finalization_master.py

Resultado:
  Todos os ACs devem estar PASSED, pronto para git commit com tag v1.3.0-s2-5-final

Deadline: 28/02/2026 23:59 BRT (IMMOVABLE)
"""

import subprocess
import sys
import json
from pathlib import Path
from datetime import datetime
from typing import List, Tuple, Dict


class S2_5_Master:
    """Orquestrador de execução do S2-5 Finalization."""

    def __init__(self):
        self.scripts = [
            ("AC-1", "scripts/s2_5_fine_tuning_gridsearch.py", 45),
            ("AC-2", "scripts/s2_5_cross_validation_final.py", 30),
            ("AC-3", "scripts/s2_5_model_serialization.py", 10),
            ("AC-4", "scripts/s2_5_production_inference_test.py", 20),
            ("AC-5", "scripts/s2_5_final_validation_report.py", 10),
        ]
        self.results = {}
        self.start_time = None
        self.end_time = None

    def print_header(self):
        """Imprime header do master script."""
        print("\n")
        print("=" * 100)
        print(" " * 30 + "🚀 S2-5 FINALIZATION MASTER SCRIPT")
        print("=" * 100)
        print()
        print("Objetivo: Finalizar S2-5 (Probabilidade T+60) para Gate 2")
        print()
        print("Cronograma:")
        total_time = 0
        for ac_nome, script_path, est_time in self.scripts:
            total_time += est_time
            print(f"  {ac_nome}: {script_path:<50} ({est_time} min)")
        print()
        print(f"Total Estimado: {total_time} minutos (~{total_time/60:.1f} horas)")
        print(f"Deadline: 28/02/2026 23:59 BRT")
        print()
        print("=" * 100)
        print()

    def executar_ac(self, ac_nome: str, script_path: str, est_time: int) -> Tuple[bool, str]:
        """
        Executa uma AC individual.

        Retorna:
            (sucesso: bool, output: str)
        """
        print(f"\n{'='*100}")
        print(f"▶️  Executando {ac_nome}")
        print(f"Script: {script_path}")
        print(f"Tempo estimado: {est_time} minutos")
        print(f"Timestamp: {datetime.now().isoformat()}")
        print(f"{'='*100}\n")

        try:
            # Executar script
            resultado = subprocess.run(
                [sys.executable, script_path],
                capture_output=False,
                text=True,
                check=False,
                timeout=est_time * 120,  # Timeout em segundos (2x estimate)
            )

            sucesso = resultado.returncode == 0

            if sucesso:
                print(f"\n✅ {ac_nome} COMPLETADO COM SUCESSO")
            else:
                print(f"\n❌ {ac_nome} FALHOU (exit code: {resultado.returncode})")

            return sucesso, f"Exit code: {resultado.returncode}"

        except subprocess.TimeoutExpired:
            print(f"\n❌ {ac_nome} TIMEOUT (excedeu {est_time*2} minutos)")
            return False, "Timeout"
        except Exception as e:
            print(f"\n❌ {ac_nome} ERRO: {str(e)}")
            return False, str(e)

    def validar_arquivos_saida(self) -> Dict[str, bool]:
        """
        Valida que todos os arquivos de saída foram gerados.

        Retorna:
            Dict com status de cada arquivo
        """
        arquivos_esperados = {
            "AC-1": Path("scripts/s2_5_fine_tuning_results.json"),
            "AC-2": Path("scripts/s2_5_cross_validation_results.json"),
            "AC-3": Path("scripts/s2_5_serialization_validation.json"),
            "AC-4": Path("scripts/s2_5_production_inference_test.json"),
            "AC-5": Path("scripts/s2_5_final_validation_report.json"),
        }

        arquivos_status = {}
        for ac, arquivo in arquivos_esperados.items():
            existe = arquivo.exists()
            arquivos_status[ac] = existe

            icon = "✅" if existe else "❌"
            print(f"  {icon} {ac}: {arquivo.name}")

        return arquivos_status

    def rodar(self) -> bool:
        """
        Executa todas as ACs em sequência.

        Retorna:
            True se todas passaram, False caso contrário
        """
        self.print_header()
        self.start_time = datetime.now()

        # Executar cada AC
        for ac_nome, script_path, est_time in self.scripts:
            sucesso, output = self.executar_ac(ac_nome, script_path, est_time)
            self.results[ac_nome] = {
                "passed": sucesso,
                "output": output,
                "timestamp": datetime.now().isoformat(),
            }

            if not sucesso:
                print(f"\n⚠️  {ac_nome} falhou. Continuando com próximas ACs...")

        self.end_time = datetime.now()

        # Validar arquivos
        print(f"\n{'='*100}")
        print("✓ Validando arquivos de saída gerados...")
        print(f"{'='*100}\n")

        arquivos_status = self.validar_arquivos_saida()

        # Gerar relatório final
        return self._gerar_relatorio_final(arquivos_status)

    def _gerar_relatorio_final(self, arquivos_status: Dict[str, bool]) -> bool:
        """
        Gera relatório final e determina se tudo está pronto para git commit.
        """
        print(f"\n{'='*100}")
        print("📊 RELATÓRIO FINAL")
        print(f"{'='*100}\n")

        # Resumo de execução
        print("Status das ACs:")
        todos_passaram = True
        for ac_nome, resultado in self.results.items():
            passou = resultado["passed"]
            icon = "✅" if passou else "❌"
            print(f"  {icon} {ac_nome}: {'PASSED' if passou else 'FAILED'}")
            if not passou:
                todos_passaram = False

        print()
        print("Arquivos Gerados:")
        todos_arquivos_ok = all(arquivos_status.values())
        for ac, existe in arquivos_status.items():
            icon = "✅" if existe else "❌"
            print(f"  {icon} {ac} output file: {'EXISTS' if existe else 'MISSING'}")

        print()

        # Duração total
        duracao = (self.end_time - self.start_time).total_seconds() / 60
        print(f"Duração total: {duracao:.1f} minutos")
        print()

        # Status final
        pronto_para_commit = todos_passaram and todos_arquivos_ok

        if pronto_para_commit:
            print("=" * 100)
            print("✅ SUCESSO! S2-5 ESTÁ 100% PRONTO PARA COMMIT!")
            print("=" * 100)
            print()
            print("Próxima ação (AC-5): GIT COMMIT & TAG")
            print()
            print("Executar:")
            print("  cd c:\\repo\\operador-day-trade-win")
            print("  git add models/ scripts/")
            print("  git commit -m \"feat: S2-5 final - modelo serializado e testado em producao\"")
            print("  git tag v1.3.0-s2-5-final")
            print("  git tag -m \"S2-5 Finalization - pronto para Gate 2\" -a v1.3.0-s2-5-final")
            print("  git push origin main --tags")
            print()
        else:
            print("=" * 100)
            print("❌ ERRO! Algunsó elemento falhou. Revisar acima.")
            print("=" * 100)
            print()

            # Recomendações
            if not todos_passaram:
                print("ACs que falharam:")
                for ac_nome, resultado in self.results.items():
                    if not resultado["passed"]:
                        print(f"  - {ac_nome}: {resultado['output']}")
                        print(f"    Re-executar: python {[s[1] for s in self.scripts if s[0] == ac_nome][0]}")

            if not todos_arquivos_ok:
                print("\nArquivos faltando:")
                for ac, existe in arquivos_status.items():
                    if not existe:
                        print(f"  - {ac}: Arquivo não foi gerado")

        print()
        print("=" * 100)
        print()

        return pronto_para_commit


def main():
    """Entry point."""
    master = S2_5_Master()
    sucesso = master.rodar()
    return 0 if sucesso else 1


if __name__ == "__main__":
    try:
        exit_code = main()
        sys.exit(exit_code)
    except KeyboardInterrupt:
        print("\n\n⚠️  Execução interrompida pelo usuário")
        sys.exit(130)
    except Exception as e:
        print(f"\n\n❌ Erro não tratado: {str(e)}")
        sys.exit(1)
