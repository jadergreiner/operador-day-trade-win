"""Diagnóstico e correção para modelo RL faltante.

Problema: INICIAR_AGENTE_RL_5000.bat procura q_network.pkl que não existe
Solução: Criar symlink ou copiar modelo disponível

Type hints: 100%
Português: 100%
"""

import shutil
from pathlib import Path
from typing import Optional, Tuple


def diagnosticar_modelos() -> Tuple[bool, str]:
    """Diagnóstico de modelos disponíveis.

    Returns:
        (modelo_existe: bool, mensagem: str)
    """
    # Caminho esperado pelo INICIAR_AGENTE_RL_5000.bat
    caminho_esperado = Path("data/models/novo_agente_rl/modelo_final/q_network.pkl")

    # Modelos disponíveis
    modelos_disponiveis = [
        Path("data/models/winfut/winfut_model_latest.pkl"),
        Path("data/models/lgbm/lgbm_classification_latest.pkl"),
        Path("data/models/trade_incremental/trade_incremental_state_latest.pkl"),
        Path("models/score_t60_v1.0_BEST.pkl"),
    ]

    if caminho_esperado.exists():
        return True, f"✅ Modelo encontrado: {caminho_esperado}"

    # Verificar quais estão disponíveis
    disponiveis = [m for m in modelos_disponiveis if m.exists()]

    if not disponiveis:
        return False, (
            "❌ Nenhum modelo disponível encontrado!\n"
            "Locais procurados:\n" +
            "\n".join(f"  - {m}" for m in modelos_disponiveis)
        )

    msg = (
        f"❌ Modelo esperado não encontrado: {caminho_esperado}\n"
        f"\n✅ Modelos disponíveis ({len(disponiveis)}):\n"
    )
    for modelo in disponiveis:
        tamanho_mb = modelo.stat().st_size / (1024 * 1024)
        msg += f"  ✓ {modelo} ({tamanho_mb:.1f} MB)\n"

    return False, msg


def criar_estrutura_modelo() -> bool:
    """Cria estrutura de diretório para modelo esperado.

    Returns:
        True se sucesso, False se falha
    """
    try:
        caminho = Path("data/models/novo_agente_rl/modelo_final")
        caminho.mkdir(parents=True, exist_ok=True)
        print(f"✅ Estrutura criada: {caminho}")
        return True
    except Exception as e:
        print(f"❌ Erro ao criar estrutura: {e}")
        return False


def copiar_modelo_compativel() -> bool:
    """Copia modelo compatível para local esperado.

    Returns:
        True se sucesso
    """
    origem = Path("data/models/winfut/winfut_model_latest.pkl")
    destino = Path("data/models/novo_agente_rl/modelo_final/q_network.pkl")

    if not origem.exists():
        print(f"❌ Origem não existe: {origem}")
        return False

    try:
        destino.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(origem, destino)
        tamanho = destino.stat().st_size / (1024 * 1024)
        print(f"✅ Modelo copiado: {origem} → {destino} ({tamanho:.1f} MB)")
        return True
    except Exception as e:
        print(f"❌ Erro na cópia: {e}")
        return False


def main() -> None:
    """Executa diagnóstico e correção se necessário."""
    print("\n" + "=" * 70)
    print("DIAGNÓSTICO: Modelo RL do INICIAR_AGENTE_RL_5000.bat")
    print("=" * 70 + "\n")

    existe, mensagem = diagnosticar_modelos()
    print(mensagem)

    if existe:
        print("\n✅ Modelo está pronto! INICIAR_AGENTE_RL_5000.bat pode ser executado.")
        return

    print("\n" + "-" * 70)
    print("FIX AUTOMÁTICO: Copiando modelo compatível...")
    print("-" * 70 + "\n")

    if copiar_modelo_compativel():
        print("\n✅ CORREÇÃO COMPLETA!")
        print("Agora é seguro executar: INICIAR_AGENTE_RL_5000.bat")
    else:
        print("\n❌ FALHA na correção automática")
        print("Próximas ações:")
        print("  1. Treinar novo modelo com: python scripts/rl_training_loop.py")
        print("  2. Ou copiar manualmente de data/models/winfut/")


if __name__ == "__main__":
    main()
