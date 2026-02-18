"""
Extrator OTIMIZADO de BDI - Apenas páginas relevantes para trading WINFUT.

Extrai SOMENTE as seções do BDI relevantes para a inteligência
do operador de day trade (agente micro tendência WINFUT).

Seções extraídas (baseado no sumário do BDI):
  - Página 1: Resumo (IBOVESPA, Derivativos, Médias Diárias)
  - Páginas 1170-1174: Resumo de ações, ações resumo ops, ETFs, mercado a termo
  - Páginas 2064-2065: DI over
  - Páginas 2066-2072: Evolução dos índices
  - Páginas 2072-2073: Histórico taxas de câmbio
  - Páginas 2073-2078: Indicadores econômicos
  - Páginas 2078-2082: Participação dos investidores (primeiras páginas)
  - Páginas 2142-2144: Maiores oscilações (altas/baixas IBOVESPA, mais negociadas)
  - Páginas 2144-2160: Derivativos resumo, mark to market, operações
  - Páginas 2157-2165: Derivativos de bolsa, negócios consolidados
  - Páginas 2232-2240: Posições em aberto (primeiras páginas)

Uso:
  python scripts/extract_bdi_key_pages.py data/BDI/BDI_00_20260210.pdf
"""

from __future__ import annotations

import os
import re
import sys
from pathlib import Path

import pdfplumber

ROOT_DIR = Path(__file__).resolve().parent.parent

# Seções relevantes para trading de WINFUT/derivativos
# (nome_seção, página_início, página_fim) — páginas 1-indexed
KEY_SECTIONS = [
    ("RESUMO_GERAL", 1, 1),
    ("RESUMO_ACOES", 1170, 1175),
    ("DI_OVER", 2064, 2066),
    ("EVOLUCAO_INDICES", 2066, 2072),
    ("HISTORICO_CAMBIO", 2072, 2073),
    ("INDICADORES_ECONOMICOS", 2073, 2078),
    ("PARTICIPACAO_INVESTIDORES", 2078, 2085),
    ("MAIORES_OSCILACOES", 2142, 2144),
    ("DERIVATIVOS_RESUMO", 2144, 2160),
    ("DERIVATIVOS_BOLSA_NEGOCIOS", 2157, 2170),
    ("POSICOES_ABERTO", 2232, 2245),
]


def extract_key_pages(pdf_path: str) -> str:
    """Extrai apenas as páginas-chave do BDI para trading."""
    lines = []

    basename = os.path.basename(pdf_path)
    date_match = re.search(r'(\d{8})', basename)
    date_str = ""
    if date_match:
        d = date_match.group(1)
        date_str = f"{d[6:8]}/{d[4:6]}/{d[0:4]}"

    with pdfplumber.open(pdf_path) as pdf:
        total_pages = len(pdf.pages)

        lines.append("=" * 80)
        lines.append("BOLETIM DIÁRIO DE INFORMAÇÕES (BDI) - B3")
        lines.append(f"EXTRAÇÃO OTIMIZADA - DADOS-CHAVE PARA TRADING")
        lines.append(f"Data: {date_str}")
        lines.append(f"Total de páginas no PDF: {total_pages}")
        lines.append("=" * 80)

        for section_name, start_page, end_page in KEY_SECTIONS:
            # Ajustar para 0-indexed e limitar ao total de páginas
            start_idx = min(start_page - 1, total_pages - 1)
            end_idx = min(end_page, total_pages)

            if start_idx >= total_pages:
                lines.append(f"\n{'─' * 60}")
                lines.append(f"SEÇÃO: {section_name} (páginas {start_page}-{end_page})")
                lines.append(f"  [AVISO] Páginas fora do range do PDF ({total_pages} páginas)")
                continue

            lines.append(f"\n{'═' * 80}")
            lines.append(f"═══ SEÇÃO: {section_name} (páginas {start_page}-{end_page}) ═══")
            lines.append(f"{'═' * 80}")

            print(f"  Extraindo {section_name} (pgs {start_page}-{end_page})...")

            for p_idx in range(start_idx, end_idx):
                if p_idx < total_pages:
                    page = pdf.pages[p_idx]
                    text = page.extract_text()
                    if text:
                        lines.append(f"\n--- Página {p_idx + 1} ---")
                        lines.append(text)

    return "\n".join(lines)


def main():
    if len(sys.argv) < 2:
        print("Uso: python scripts/extract_bdi_key_pages.py <caminho_pdf>")
        sys.exit(1)

    pdf_path = sys.argv[1]
    if not os.path.isabs(pdf_path):
        pdf_path = os.path.join(ROOT_DIR, pdf_path)

    if not os.path.exists(pdf_path):
        print(f"ERRO: Arquivo não encontrado: {pdf_path}")
        sys.exit(1)

    basename = os.path.basename(pdf_path)
    date_match = re.search(r'(\d{8})', basename)
    date_code = date_match.group(1) if date_match else "unknown"

    print(f"\n╔{'═' * 60}╗")
    print(f"║  EXTRATOR BDI OTIMIZADO - DADOS-CHAVE PARA TRADING")
    print(f"╚{'═' * 60}╝\n")

    result = extract_key_pages(pdf_path)

    output_dir = os.path.dirname(pdf_path)
    output_file = os.path.join(output_dir, f"bdi_{date_code}_key_data.txt")

    with open(output_file, "w", encoding="utf-8") as f:
        f.write(result)

    rel_path = os.path.relpath(output_file, ROOT_DIR)
    print(f"\n  ✓ Dados-chave salvos em: {rel_path}")
    print(f"  ✓ Total de caracteres: {len(result):,}")


if __name__ == "__main__":
    main()
