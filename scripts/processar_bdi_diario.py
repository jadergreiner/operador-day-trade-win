#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Processador de Boletim Diario BDI
Extrai informacoes de indicadores economicos e do mercado.

Uso: python scripts/processar_bdi_diario.py <YYYYMMDD>
Exemplo: python scripts/processar_bdi_diario.py 20260303
"""

import json
import re
import sys
from datetime import datetime
from pathlib import Path
from typing import Dict, Any

# Tentativa: pdfplumber
try:
    import pdfplumber
    HAS_PDFPLUMBER = True
except ImportError:
    HAS_PDFPLUMBER = False

# Tentativa: PyPDF2
try:
    import PyPDF2
    HAS_PYPDF2 = True
except ImportError:
    HAS_PYPDF2 = False


class ProcessadorBDI:
    """Processa boletins diarios BDI."""

    def __init__(self, data_str: str):
        self.data_str = data_str
        self.data_obj = datetime.strptime(data_str, "%Y%m%d")
        self.bdi_path = Path(f"data/BDI/BDI_00_{data_str}.pdf")
        self.output_dir = Path("data/BDI/reports")
        self.output_dir.mkdir(parents=True, exist_ok=True)

        self.dados = {
            "data": self.data_str,
            "data_formatada": self.data_obj.strftime("%d/%m/%Y"),
            "extraido_em": datetime.now().isoformat(),
            "indicadores_economicos": {},
            "notas": []
        }

    def processar(self) -> bool:
        if not self.bdi_path.exists():
            print(f"[ERRO] Arquivo nao encontrado: {self.bdi_path}")
            self.dados["notas"].append(f"Arquivo nao encontrado: {self.bdi_path}")
            return False

        print(f"[BDI] Processando boletim de {self.data_obj.strftime('%d/%m/%Y')}...")

        sucesso = False

        try:
            if HAS_PDFPLUMBER:
                print("[*] Tentando extracao com pdfplumber...")
                sucesso = self._extrair_pdfplumber()
        except Exception as e:
            print(f"[!] PDFPlumber: {type(e).__name__}")

        if not sucesso:
            try:
                if HAS_PYPDF2:
                    print("[*] Tentando extracao com PyPDF2...")
                    sucesso = self._extrair_pypdf2()
            except Exception as e:
                print(f"[!] PyPDF2: {type(e).__name__}")

        if sucesso or self.dados["indicadores_economicos"]:
            print("[OK] Boletim processado!")
            self._salvar_resultados()
            return True
        else:
            print("[!] Nao foi possivel extrair texto do PDF.")
            self.dados["notas"].append("Extracao de texto nao foi possivel")
            self._salvar_resultados()
            return False

    def _extrair_pdfplumber(self) -> bool:
        with pdfplumber.open(self.bdi_path) as pdf:
            texto_completo = ""
            for page in pdf.pages:
                texto = page.extract_text()
                if texto:
                    texto_completo += texto + "\n"

            self._processar_texto(texto_completo)
            self.dados["metodo"] = "pdfplumber"
            return True

    def _extrair_pypdf2(self) -> bool:
        with open(self.bdi_path, 'rb') as f:
            reader = PyPDF2.PdfReader(f)
            texto_completo = ""
            for page in reader.pages:
                texto = page.extract_text()
                if texto:
                    texto_completo += texto + "\n"

            self._processar_texto(texto_completo)
            self.dados["metodo"] = "PyPDF2"
            return True

    def _processar_texto(self, texto: str) -> None:
        padroes = {
            "taxa_selic": r"Taxa SELIC[:\s]+([0-9,]+)\s*%",
            "taxa_inflacao": r"IPCA[:\s]+([0-9,]+)\s*%",
            "dolar_compra": r"[Dd]o.lar.*?compra[:\s]+([0-9,]+)",
            "dolar_venda": r"[Dd]o.lar.*?venda[:\s]+([0-9,]+)",
            "ibovespa": r"Ibovespa[:\s]+([0-9.,]+)",
        }

        for chave, padrao in padroes.items():
            match = re.search(padrao, texto, re.IGNORECASE)
            if match:
                self.dados["indicadores_economicos"][chave] = match.group(1)

        self.dados["status"] = "completo" if self.dados["indicadores_economicos"] else "parcial"

    def _salvar_resultados(self) -> None:
        arquivo_json = self.output_dir / f"bdi_{self.data_str}_key_data.json"
        with open(arquivo_json, 'w', encoding='utf-8') as f:
            json.dump(self.dados, f, ensure_ascii=False, indent=2)

        print(f"[OK] Dados: {arquivo_json.name}")

        arquivo_txt = self.output_dir / f"bdi_{self.data_str}_report.txt"
        with open(arquivo_txt, 'w', encoding='utf-8') as f:
            f.write(self._gerar_relatorio())

        print(f"[OK] Relatorio: {arquivo_txt.name}")

    def _gerar_relatorio(self) -> str:
        linhas = []
        linhas.append("=" * 70)
        linhas.append(f"BOLETIM BDI - {self.data_obj.strftime('%d/%m/%Y')}")
        linhas.append("=" * 70)
        linhas.append("")

        if self.dados["indicadores_economicos"]:
            linhas.append("INDICADORES ECONÔMICOS:")
            for chave, valor in self.dados["indicadores_economicos"].items():
                nome_amigavel = chave.replace('_', ' ').title()
                linhas.append(f"  {nome_amigavel}: {valor}")

        linhas.append("")
        linhas.append("Status: " + self.dados.get("status", "desconhecido"))

        if self.dados["notas"]:
            linhas.append("\nNOTAS:")
            for nota in self.dados["notas"]:
                linhas.append(f"  - {nota}")

        return "\n".join(linhas)


def main():
    if len(sys.argv) > 1:
        data_str = sys.argv[1]
    else:
        data_str = datetime.now().strftime("%Y%m%d")

    processador = ProcessadorBDI(data_str)
    sucesso = processador.processar()

    print("\n" + "=" * 70)
    if sucesso and processador.dados["indicadores_economicos"]:
        print("[RESULTADO] Sucesso! Indicadores extraidos:")
        for k, v in processador.dados["indicadores_economicos"].items():
            print(f"  {k}: {v}")
    else:
        print("[RESULTADO] Boletim processado (possivel PDF scaneado)")
    print("=" * 70 + "\n")

    sys.exit(0 if sucesso else 1)


if __name__ == "__main__":
    main()
