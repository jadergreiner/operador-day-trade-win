"""
Extrator de BDI (Boletim Diário de Informações) da B3.

Extrai dados relevantes do PDF do BDI para uso na inteligência
do operador de day trade (agente micro tendência WINFUT).

Uso:
  python scripts/extract_bdi_pdf.py data/BDI/BDI_00_20260210.pdf
"""

from __future__ import annotations

import os
import re
import sys
from pathlib import Path

import pdfplumber

ROOT_DIR = Path(__file__).resolve().parent.parent


def extract_bdi_full(pdf_path: str) -> str:
    """Extrai todo o conteúdo textual do PDF BDI, página por página."""
    lines = []
    with pdfplumber.open(pdf_path) as pdf:
        total_pages = len(pdf.pages)
        lines.append("BOLETIM DIÁRIO DE INFORMAÇÕES (BDI) - B3")

        # Extrair data do nome do arquivo
        basename = os.path.basename(pdf_path)
        date_match = re.search(r'(\d{8})', basename)
        if date_match:
            d = date_match.group(1)
            date_str = f"{d[6:8]}/{d[4:6]}/{d[0:4]}"
            lines.append(f"Data: {date_str}")

        lines.append(f"Total de páginas: {total_pages}")
        lines.append("=" * 80)

        for i, page in enumerate(pdf.pages):
            lines.append("")
            lines.append("=" * 80)
            lines.append(f"=== PÁGINA {i + 1} ===")
            lines.append("=" * 80)

            text = page.extract_text()
            if text:
                lines.append(text)

            # Progresso
            if (i + 1) % 100 == 0 or i == 0:
                print(f"  Processando página {i + 1}/{total_pages}...")

    return "\n".join(lines)


def extract_bdi_key_data(pdf_path: str) -> dict:
    """Extrai dados-chave do BDI relevantes para trading de futuros.

    Foca em:
    - IBOVESPA fechamento e variação
    - Derivativos: volumes, contratos, negócios
    - Indicadores econômicos (DI, câmbio, etc.)
    - Resumo de ações
    - Maiores altas/baixas do IBOVESPA
    - Posições em aberto de derivativos
    """
    data = {
        "ibovespa": {},
        "derivativos_resumo": {},
        "medias_diarias": {},
        "indicadores_economicos": [],
        "maiores_altas_ibov": [],
        "maiores_baixas_ibov": [],
        "acoes_mais_negociadas": [],
        "derivativos_bolsa": [],
        "posicoes_aberto": [],
        "di_over": {},
        "cambio": {},
        "evolucao_indices": [],
        "participacao_investidores": {},
    }

    with pdfplumber.open(pdf_path) as pdf:
        total_pages = len(pdf.pages)
        print(f"  PDF com {total_pages} páginas. Extraindo dados-chave...")

        # Página 1 - Resumo principal
        if total_pages >= 1:
            text = pdf.pages[0].extract_text() or ""

            # IBOVESPA
            ibov_match = re.search(
                r'(?:IBOVESPA|Ibovespa)[:\s]+([0-9.,]+)\s+([-+]?[0-9.,]+%?)',
                text, re.IGNORECASE
            )
            if ibov_match:
                data["ibovespa"]["fechamento"] = ibov_match.group(1).strip()
                data["ibovespa"]["variacao"] = ibov_match.group(2).strip()

            # Derivativos - volumes
            total_minis = re.search(
                r'Total com minis[:\s]+([0-9.,]+)', text, re.IGNORECASE
            )
            if total_minis:
                data["derivativos_resumo"]["total_com_minis"] = total_minis.group(1)

            total_sem = re.search(
                r'Total sem minis[:\s]+([0-9.,]+)', text, re.IGNORECASE
            )
            if total_sem:
                data["derivativos_resumo"]["total_sem_minis"] = total_sem.group(1)

            vol_neg = re.search(
                r'Volume negociado[:\s]+([0-9.,]+)', text, re.IGNORECASE
            )
            if vol_neg:
                data["derivativos_resumo"]["volume_negociado"] = vol_neg.group(1)

            qtd_neg = re.search(
                r'Quantidade de neg[óo]cios[:\s]+([0-9.,]+)', text, re.IGNORECASE
            )
            if qtd_neg:
                data["derivativos_resumo"]["qtd_negocios"] = qtd_neg.group(1)

        # Varrer páginas relevantes (sumário indica as seções)
        # Focar nas seções: Indicadores econômicos (~p2073), DI over (~p2064),
        # Evolução dos índices (~p2066), Maiores oscilações (~p2142),
        # Derivativos resumo (~p2144), Posições em aberto (~p2232)

        # Seções de interesse baseadas no sumário do BDI
        sections_of_interest = {
            "indicadores_economicos": (2072, 2078),
            "evolucao_indices": (2065, 2072),
            "maiores_oscilacoes": (2141, 2144),
            "derivativos_resumo_ops": (2143, 2158),
            "participacao_investidores": (2077, 2142),
        }

        # Extrair texto das seções relevantes
        for section_name, (start_page, end_page) in sections_of_interest.items():
            start_idx = min(start_page - 1, total_pages - 1)
            end_idx = min(end_page, total_pages)

            section_text = ""
            for p_idx in range(start_idx, end_idx):
                if p_idx < total_pages:
                    page_text = pdf.pages[p_idx].extract_text() or ""
                    section_text += page_text + "\n"

            if section_text.strip():
                data[section_name + "_raw"] = section_text

    return data


def format_key_data_report(data: dict, date_str: str = "") -> str:
    """Formata os dados-chave extraídos num relatório estruturado."""
    lines = []
    lines.append("=" * 80)
    lines.append("BOLETIM DIÁRIO DE INFORMAÇÕES (BDI) - B3")
    lines.append(f"EXTRAÇÃO DE DADOS-CHAVE PARA TRADING")
    if date_str:
        lines.append(f"Data: {date_str}")
    lines.append("=" * 80)

    # IBOVESPA
    if data.get("ibovespa"):
        lines.append("")
        lines.append("─── IBOVESPA ───")
        ibov = data["ibovespa"]
        if ibov.get("fechamento"):
            lines.append(f"  Fechamento: {ibov['fechamento']}")
        if ibov.get("variacao"):
            lines.append(f"  Variação: {ibov['variacao']}")

    # Derivativos Resumo
    if data.get("derivativos_resumo"):
        lines.append("")
        lines.append("─── DERIVATIVOS - RESUMO ───")
        deriv = data["derivativos_resumo"]
        for k, v in deriv.items():
            label = k.replace("_", " ").title()
            lines.append(f"  {label}: {v}")

    # Seções raw extraídas
    for key in sorted(data.keys()):
        if key.endswith("_raw") and data[key].strip():
            section_name = key.replace("_raw", "").replace("_", " ").upper()
            lines.append("")
            lines.append(f"─── {section_name} ───")
            # Limitar a 200 linhas por seção
            raw_lines = data[key].strip().split("\n")
            for rl in raw_lines[:200]:
                lines.append(f"  {rl}")
            if len(raw_lines) > 200:
                lines.append(f"  ... ({len(raw_lines) - 200} linhas adicionais)")

    return "\n".join(lines)


def main():
    if len(sys.argv) < 2:
        print("Uso: python scripts/extract_bdi_pdf.py <caminho_pdf>")
        print("Exemplo: python scripts/extract_bdi_pdf.py data/BDI/BDI_00_20260210.pdf")
        sys.exit(1)

    pdf_path = sys.argv[1]
    if not os.path.isabs(pdf_path):
        pdf_path = os.path.join(ROOT_DIR, pdf_path)

    if not os.path.exists(pdf_path):
        print(f"ERRO: Arquivo não encontrado: {pdf_path}")
        sys.exit(1)

    basename = os.path.basename(pdf_path)
    date_match = re.search(r'(\d{8})', basename)
    date_str = ""
    date_code = ""
    if date_match:
        d = date_match.group(1)
        date_str = f"{d[6:8]}/{d[4:6]}/{d[0:4]}"
        date_code = d

    print(f"\n╔{'═' * 60}╗")
    print(f"║  EXTRATOR BDI - B3 ({date_str})")
    print(f"╚{'═' * 60}╝\n")
    print(f"  Arquivo: {basename}")

    # 1) Extrair dados-chave
    print(f"\n  [1/3] Extraindo dados-chave do PDF...")
    key_data = extract_bdi_key_data(pdf_path)

    # 2) Extração completa (texto de todas as páginas)
    print(f"\n  [2/3] Extraindo texto completo do PDF...")
    full_text = extract_bdi_full(pdf_path)

    # 3) Salvar arquivos
    print(f"\n  [3/3] Salvando arquivos...")

    output_dir = os.path.dirname(pdf_path)

    # Arquivo completo (mesmo padrão do bdi_20260210_extracted.txt)
    full_output = os.path.join(output_dir, f"bdi_{date_code}_extracted.txt")
    with open(full_output, "w", encoding="utf-8") as f:
        f.write(full_text)
    print(f"  ✓ Extração completa: {os.path.relpath(full_output, ROOT_DIR)}")

    # Relatório de dados-chave
    key_report = format_key_data_report(key_data, date_str)
    key_output = os.path.join(output_dir, f"bdi_{date_code}_key_data.txt")
    with open(key_output, "w", encoding="utf-8") as f:
        f.write(key_report)
    print(f"  ✓ Dados-chave: {os.path.relpath(key_output, ROOT_DIR)}")

    # Resumo
    print(f"\n  ── RESUMO ──")
    print(f"  IBOVESPA: {key_data.get('ibovespa', {}).get('fechamento', 'N/A')} "
          f"{key_data.get('ibovespa', {}).get('variacao', '')}")
    deriv = key_data.get("derivativos_resumo", {})
    if deriv:
        print(f"  Contratos (c/ minis): {deriv.get('total_com_minis', 'N/A')}")
        print(f"  Volume negociado: {deriv.get('volume_negociado', 'N/A')}")

    print(f"\n  ✓ Extração concluída com sucesso!")
    return key_data


if __name__ == "__main__":
    main()
