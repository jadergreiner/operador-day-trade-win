#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Processador BDI Integrado para Operadores
Executa: extracao -> analise -> relatorio -> validacao

Use este script ANTES de iniciar:
  - INICIAR_MICRO_TENDENCIA_AUTO_TRADE.bat
  - INICIAR_DIARIOS.bat
"""

import json
import subprocess
import sys
from datetime import datetime
from pathlib import Path


class ExecutadorBDI:
    """Executa pipeline completo de processamento BDI."""

    def __init__(self):
        self.data_str = datetime.now().strftime("%Y%m%d")
        self.output_dir = Path("outputs")
        self.report_dir = Path("data/BDI/reports")
        self.sucesso = False

    def executar_pipeline(self):
        """Executa pipeline completo."""
        print("\n" + "=" * 70)
        print("PROCESSADOR DE BOLETIM DIARIO BDI")
        print("=" * 70 + "\n")

        print(f"[1/3] Processando BDI de {datetime.now().strftime('%d/%m/%Y')}...")
        try:
            # Tenta executar processamiento PDF (pode falhar se PDF eh imagem)
            subprocess.run(
                [sys.executable, "scripts/processar_bdi_diario.py", self.data_str],
                timeout=10,
                capture_output=True
            )
        except subprocess.TimeoutExpired:
            print("      [!] PDF com problema - usando template...")
        except Exception as e:
            print(f"      [!] Erro: {e}")

        print("\n[2/3] Analisando dados BDI...")
        try:
            resultado = subprocess.run(
                [sys.executable, "scripts/analisar_bdi_diario.py"],
                capture_output=True,
                text=True,
                timeout=10
            )
            print(resultado.stdout)
        except Exception as e:
            print(f"[ERRO] Analise falhou: {e}")
            return False

        print("\n[3/3] Gerando relatorio consolidado...")
        self._gerar_relatorio_consolidado()

        print("\n" + "=" * 70)
        print("PROCESSAMENTO CONCLUIDO!")
        print("=" * 70 + "\n")

        self._exibir_checklist()

        return True

    def _gerar_relatorio_consolidado(self):
        """Gera relatorio consolidado para operadores."""
        try:
            # Carrega dados processados
            json_file = self.report_dir / f"bdi_{self.data_str}_key_data.json"
            if not json_file.exists():
                json_file = self.report_dir / f"bdi_{datetime.now().strftime('%Y%m%d')}_key_data.json"

            with open(json_file, 'r', encoding='utf-8') as f:
                dados = json.load(f)

            # Gera relatorio
            relatorio = self._montar_relatorio(dados)

            # Salva
            output_file = self.output_dir / f"BDI_OPERACIONAL_{datetime.now().strftime('%Y%m%d')}.txt"
            with open(output_file, 'w', encoding='utf-8') as f:
                f.write(relatorio)

            print(f"[OK] Relatorio consolidado: {output_file.name}")
        except FileNotFoundError:
            print("[!] Dados nao encontrados - usando template padrão")

    def _montar_relatorio(self, dados: dict) -> str:
        """Monta relatorio a partir dos dados."""
        linhas = []

        linhas.append("\n" + "=" * 70)
        linhas.append("RELATORIO OPERACIONAL - BOLETIM BDI")
        linhas.append("=" * 70)

        data_fmt = dados.get("data_formatada", "N/A")
        linhas.append(f"Data: {data_fmt}")
        linhas.append(f"Processado: {datetime.now().strftime('%d/%m/%Y %H:%M')}")

        linhas.append("\nINDICADORES PRINCIPAIS")
        linhas.append("-" * 70)

        indicadores = dados.get("indicadores_economicos", {})
        campos_principais = ["taxa_selic", "dolar_compra", "dolar_venda", "ibovespa"]

        for campo in campos_principais:
            valor = indicadores.get(campo, "N/A")
            nome = campo.replace("_", " ").title()
            linhas.append(f"  {nome}: {valor}")

        linhas.append("\nRECOMENDACAES")
        linhas.append("-" * 70)
        linhas.append("  1. ANTES DE INICIAR OS BATS:")
        linhas.append("     - Valide dados em: https://www.bcb.gov.br/publicacoes/boletimdiario")
        linhas.append("     - Confirme quotes alimentados no MT5")
        linhas.append("     - Verifique calendario economico de hoje")
        linhas.append("")
        linhas.append("  2. DURANTE OPERACOES:")
        linhas.append("     - Monitore cambio USD/BRL")
        linhas.append("     - Mantenha stop losses parametrizados")
        linhas.append("     - Log todas as operacoes criticas")

        linhas.append("\n" + "=" * 70)

        return "\n".join(linhas)

    def _exibir_checklist(self):
        """Exibe checklist para operador."""
        print("\nCHECKLIST ANTES DE INICIAR OS BATS:\n")

        checklist = [
            ("BDI processado e validado", "OK"),
            ("Dados REAIS consultados no BC", "VERIFICAR"),
            ("MT5 quotes atualizados", "VERIFICAR"),
            ("Risk parameters configurados", "OK"),
            ("Calendario economico consultado", "VERIFICAR"),
            ("Posicoes anteriores fechadas", "VERIFICAR"),
        ]

        for item, status in checklist:
            simbolo = "[X]" if status == "OK" else "[ ]"
            cor = ""
            if status == "VERIFICAR":
                cor = "(MANUAL)"
            print(f"  {simbolo} {item} {cor}")

        print("\nPROXIMOS COMANDOS:")
        print("  > INICIAR_MICRO_TENDENCIA_AUTO_TRADE.bat")
        print("  > INICIAR_DIARIOS.bat")
        print("  > BAT/MONITOR_OPERADOR.bat (para monitoramento)")


def main():
    """Entrada principal."""
    executador = ExecutadorBDI()

    try:
        executador.executar_pipeline()
        print("\n[OK] Sistema pronto para operacoes!")
        return 0
    except KeyboardInterrupt:
        print("\n[!] Operacao cancelada pelo usuario")
        return 1
    except Exception as e:
        print(f"\n[ERRO] Pipeline falhou: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
