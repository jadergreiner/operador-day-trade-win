#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Analisador de Boletim BDI para operacoes do dia
Valida indicadores e gera recomendacoes para os operadores.
"""

import json
from datetime import datetime
from pathlib import Path


class AnalisadorBDI:
    """Analisa dados BDI para decisoes operacionais."""

    def __init__(self, data_str: str):
        self.data_str = data_str
        self.data_obj = datetime.strptime(data_str, "%Y%m%d")
        self.report_dir = Path("data/BDI/reports")
        self.bdi_file = self.report_dir / f"bdi_{data_str}_key_data.json"
        self.dados = {}
        self.analise = {}

    def carregar_dados(self) -> bool:
        """Carrega dados processados do BDI."""
        if not self.bdi_file.exists():
            print(f"[!] Arquivo de dados nao encontrado: {self.bdi_file}")
            print("[*] Usando template padrão...")
            return self._usar_template()

        try:
            with open(self.bdi_file, 'r', encoding='utf-8') as f:
                self.dados = json.load(f)
            print(f"[OK] Dados carregados: {self.bdi_file.name}")
            return True
        except Exception as e:
            print(f"[ERRO] Nao conseguiu ler dados: {e}")
            return False

    def _usar_template(self) -> bool:
        """Carrega template padrão."""
        template_file = Path("data/BDI/bdi_template_manual.json")
        if template_file.exists():
            try:
                with open(template_file, 'r', encoding='utf-8') as f:
                    self.dados = json.load(f)
                self.dados["data"] = self.data_str
                self.dados["data_formatada"] = self.data_obj.strftime("%d/%m/%Y")
                print("[*] Template carregado como base")
                return True
            except Exception as e:
                print(f"[ERRO] Nao conseguiu carregar template: {e}")
                return False
        return False

    def analisar(self) -> bool:
        """Analisa indicadores para decisoes operacionais."""
        if not self.dados:
            print("[!] Nenhum dado disponivel para analise")
            return False

        print("\n" + "=" * 70)
        print(f"ANALISE BDI - {self.data_obj.strftime('%d/%m/%Y')}")
        print("=" * 70)

        self._analisar_taxa_selic()
        self._analisar_cambio()
        self._analisar_bolsa()
        self._gerar_recomendacoes()

        return True

    def _analisar_taxa_selic(self):
        """Analisa impacto de taxa SELIC."""
        selic = self.dados.get("indicadores_economicos", {}).get("taxa_selic", "13.75")
        try:
            selic_valor = float(selic.replace(",", "."))

            print("\nTAXA SELIC")
            print(f"  Valor: {selic}%")

            if selic_valor >= 14.0:
                print("  STATUS: ALTA - Impacto negativo para operacoes com alavancagem")
                self.analise["selic_impacto"] = "alto_negativo"
            elif selic_valor >= 13.0:
                print("  STATUS: MODERADA - Custo de capital elevado")
                self.analise["selic_impacto"] = "moderado"
            else:
                print("  STATUS: BAIXA - Condicoes mais favoraveis")
                self.analise["selic_impacto"] = "positivo"
        except:
            print("  [!] Nao conseguiu processar valor de SELIC")

    def _analisar_cambio(self):
        """Analisa situacao do cambio."""
        pars = self.dados.get("indicadores_economicos", {})
        compra = pars.get("dolar_compra", "5.12")
        venda = pars.get("dolar_venda", "5.13")

        print("\nCAMBIO (USD/BRL)")
        print(f"  Compra: {compra}")
        print(f"  Venda: {venda}")

        try:
            spread = float(venda.replace(",", ".")) - float(compra.replace(",", "."))
            print(f"  Spread: R${spread:.2f}")

            if spread > 0.02:
                print("  STATUS: Volatilidade elevada - cuidado com entradas/saidas")
                self.analise["cambio_condicao"] = "volatilidade_alta"
            else:
                print("  STATUS: Condicoes normais")
                self.analise["cambio_condicao"] = "normal"
        except:
            pass

    def _analisar_bolsa(self):
        """Analisa situacao de bolsa."""
        ibov = self.dados.get("indicadores_economicos", {}).get("ibovespa", "120450.50")

        print("\nBOLSA (IBOVESPA)")
        print(f"  Nivel: {ibov}")
        print("  STATUS: Consulte trending atual no MT5")
        self.analise["bolsa_status"] = "verificar_mt5"

    def _gerar_recomendacoes(self):
        """Gera recomendacoes para operadores."""
        print("\nRECOMENDACAES OPERACIONAIS")
        print("-" * 70)

        recomendacoes = []

        # Baseado em SELIC
        if self.analise.get("selic_impacto") == "alto_negativo":
            recomendacoes.append("SELIC: Reduza alavancagem - considere operacoes menores")
        elif self.analise.get("selic_impacto") == "positivo":
            recomendacoes.append("SELIC: Condicoes mais favoraveis para operacoes")

        # Baseado em cambio
        if self.analise.get("cambio_condicao") == "volatilidade_alta":
            recomendacoes.append("CAMBIO: Aumente stop loss - mercado mais volatil")

        # Recomendacoes gerais
        recomendacoes.extend([
            "Valide dados BDI em: https://www.bcb.gov.br/publicacoes/boletimdiario",
            "Sincronize horario operacional com calendario economico",
            "Confirme quotes MT5 antes de operacoes criticas"
        ])

        for i, rec in enumerate(recomendacoes, 1):
            print(f"  {i}. {rec}")

        self.analise["recomendacoes"] = recomendacoes

    def gerar_relatorio_operador(self) -> str:
        """Gera arquivo de relatorio para operadores."""
        linhas = []

        linhas.append("=" * 70)
        linhas.append(f"BOLETIM OPERACIONAL - {self.data_obj.strftime('%d/%m/%Y')}")
        linhas.append("=" * 70)
        linhas.append(f"Processado: {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}")
        linhas.append("")

        linhas.append("INDICADORES PRINCIPAIS")
        linhas.append("-" * 70)
        indicadores = self.dados.get("indicadores_economicos", {})
        for chave in ["taxa_selic", "dolar_compra", "dolar_venda", "ibovespa"]:
            valor = indicadores.get(chave, "N/A")
            nome = chave.replace("_", " ").title()
            linhas.append(f"  {nome}: {valor}")

        linhas.append("")
        linhas.append("SINTESE DE ANALISE")
        linhas.append("-" * 70)
        for chave, valor in self.analise.items():
            if chave != "recomendacoes":
                nome = chave.replace("_", " ").title()
                linhas.append(f"  {nome}: {valor}")

        linhas.append("")
        linhas.append("RECOMENDACOES")
        linhas.append("-" * 70)
        for rec in self.analise.get("recomendacoes", []):
            linhas.append(f"  - {rec}")

        linhas.append("")
        linhas.append("[FIM DO RELATORIO]")

        return "\n".join(linhas)

    def salvar_relatorio_operador(self) -> bool:
        """Salva relatorio em arquivo para operadores."""
        try:
            output_file = self.report_dir / f"bdi_{self.data_str}_operador.txt"
            with open(output_file, 'w', encoding='utf-8') as f:
                f.write(self.gerar_relatorio_operador())

            print(f"\n[OK] Relatorio operador: {output_file.name}")
            return True
        except Exception as e:
            print(f"[ERRO] Nao conseguiu salvar relatorio: {e}")
            return False


def main():
    """Entrada principal."""
    from datetime import datetime

    # Data de hoje
    data_str = datetime.now().strftime("%Y%m%d")

    # Processa
    analisador = AnalisadorBDI(data_str)

    if analisador.carregar_dados():
        analisador.analisar()
        analisador.salvar_relatorio_operador()
        print("\n" + "=" * 70)
        print("[OK] Analise concluida!")
        print("=" * 70)
    else:
        print("[!] Operacao abortada - dados indisponiveis")


if __name__ == "__main__":
    main()
