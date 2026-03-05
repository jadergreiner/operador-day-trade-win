"""
Processador em batch de arquivos BDI PDF.

Processa todos os arquivos BDI disponíveis de uma só vez.
"""

import asyncio
import logging
import sys
from pathlib import Path
from typing import List, Dict

# Adicionar workspace ao PYTHONPATH
workspace_root = Path(__file__).parent.parent
sys.path.insert(0, str(workspace_root))

from scripts.processar_bdi_pdf import ProcessadorBDIPDF

# Configurar logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


class ProcessadorBDIBatch:
    """Processador batch de múltiplos arquivos BDI."""

    def __init__(self, workspace_root: str = None):
        """Inicializar processador batch."""
        if workspace_root is None:
            workspace_root = str(Path(__file__).parent.parent)

        self.workspace_root = Path(workspace_root)
        self.data_dir = self.workspace_root / "data"
        self.bdi_dir = self.data_dir / "BDI"
        self.processador = ProcessadorBDIPDF(workspace_root)

        logger.info(f"ProcessadorBDIBatch inicializado")

    def listar_arquivos_nao_processados(self) -> List[Path]:
        """Listar arquivos BDI que ainda não foram processados."""
        if not self.bdi_dir.exists():
            return []

        # Arquivos BDI disponíveis
        arquivos_bdi = sorted(
            self.bdi_dir.glob("BDI_*.pdf"),
            key=lambda x: x.name
        )

        # Arquivos já processados (verificar em outputs)
        output_dir = self.workspace_root / "outputs"
        processados = set()

        if output_dir.exists():
            for arquivo_json in output_dir.glob("bdi_processamento_*.json"):
                # Extrair data do nome do arquivo JSON
                data = arquivo_json.name.replace("bdi_processamento_", "").replace(".json", "")
                processados.add(data)

        # Filtrar não processados
        nao_processados = []
        for arquivo in arquivos_bdi:
            # Extrair data do nome do arquivo
            import re
            match = re.search(r"(\d{8})", arquivo.name)
            if match:
                data = match.group(1)
                if data not in processados:
                    nao_processados.append(arquivo)

        return nao_processados

    async def processar_lote(self, arquivos: List[Path] = None) -> Dict:
        """
        Processar lote de arquivos BDI.

        Args:
            arquivos: Lista de arquivos para processar (default: não processados)

        Returns:
            Sumário consolidado do processamento
        """
        if arquivos is None:
            arquivos = self.listar_arquivos_nao_processados()

        if not arquivos:
            logger.info("Nenhum arquivo novo para processar")
            return {
                "status": "info",
                "mensagem": "Nenhum arquivo novo",
                "total": 0,
                "processados": 0,
            }

        logger.info(f"🔄 Iniciando processamento de {len(arquivos)} arquivo(s) BDI")

        resultados = []
        sucessos = 0
        erros = 0

        for i, arquivo in enumerate(arquivos, 1):
            logger.info(f"\n[{i}/{len(arquivos)}] Processando {arquivo.name}")

            try:
                resultado = await self.processador.processar_arquivo(str(arquivo))
                resultados.append(resultado)

                if resultado.get("status") == "sucesso":
                    sucessos += 1
                    logger.info(f"  ✅ {arquivo.name} - OK")
                else:
                    erros += 1
                    logger.warning(f"  ⚠️ {arquivo.name} - {resultado.get('mensagem')}")

            except Exception as e:
                erros += 1
                logger.error(f"  ❌ {arquivo.name} - Erro: {e}")
                resultados.append({
                    "status": "erro",
                    "arquivo": arquivo.name,
                    "mensagem": str(e)
                })

        # Sumário
        sumario = {
            "status": "sucesso" if erros == 0 else "parcial",
            "total_arquivos": len(arquivos),
            "processados_com_sucesso": sucessos,
            "erros": erros,
            "resultados_detalhados": resultados,
        }

        logger.info(f"\n{'='*70}")
        logger.info(f"SUMÁRIO DE PROCESSAMENTO")
        logger.info(f"{'='*70}")
        logger.info(f"Total arquivos: {len(arquivos)}")
        logger.info(f"Sucessos: {sucessos}")
        logger.info(f"Erros: {erros}")
        logger.info(f"Status geral: {sumario['status'].upper()}")
        logger.info(f"{'='*70}")

        return sumario


async def main():
    """Executar processador batch via CLI."""
    processador_batch = ProcessadorBDIBatch()

    # Processar arquivos não processados
    resultado = await processador_batch.processar_lote()

    # Exibir resultado
    print("\n" + "=" * 70)
    print("RELATÓRIO FINAL DE PROCESSAMENTO")
    print("=" * 70)
    print(f"Status: {resultado['status'].upper()}")
    print(f"Total processado: {resultado['total_arquivos']} arquivo(s)")
    print(f"Sucessos: {resultado['processados_com_sucesso']}")
    print(f"Erros: {resultado['erros']}")
    print("=" * 70 + "\n")

    return resultado


if __name__ == "__main__":
    result = asyncio.run(main())
    exit(0 if result.get("status") == "sucesso" else 1)
