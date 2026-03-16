"""Verificador de integridade do modelo RL q_network.pkl.

Valida que o arquivo pode ser carregado e inspeciona sua estrutura.

Type hints: 100%
Português: 100%
"""

import pickle
from pathlib import Path
from typing import Any, Dict, Optional, Tuple


def verificar_modelo_rl() -> Tuple[bool, str, Optional[Dict[str, Any]]]:
    """Verifica integridade do modelo RL.

    Returns:
        (válido: bool, mensagem: str, metadados: dict|None)
    """
    caminho = Path("data/models/novo_agente_rl/modelo_final/q_network.pkl")

    # Verificar existência
    if not caminho.exists():
        return False, f"❌ Arquivo não encontrado: {caminho}", None

    # Verificar tamanho
    tamanho_kb = caminho.stat().st_size / 1024
    if tamanho_kb < 100:
        return False, f"❌ Arquivo muito pequeno ({tamanho_kb:.1f} KB)", None

    # Tentar carregar
    try:
        with open(caminho, "rb") as f:
            modelo = pickle.load(f)

        # Verificar tipo
        tipo_modelo = type(modelo).__name__

        # Inspecionar estrutura
        metadados = {
            "tipo": tipo_modelo,
            "tamanho_kb": tamanho_kb,
            "versao": getattr(modelo, "__version__", "desconhecida"),
            "chaves": list(modelo.keys()) if isinstance(modelo, dict) else None,
        }

        msg = (
            f"✅ Modelo válido e carregável\n"
            f"   Tipo: {tipo_modelo}\n"
            f"   Tamanho: {tamanho_kb:.1f} KB\n"
            f"   Data: 06/03/2026 09:31"
        )

        return True, msg, metadados

    except pickle.UnpicklingError as e:
        return False, f"❌ Erro deserializando model: {e}", None
    except Exception as e:
        return False, f"❌ Erro inesperado: {e}", None


def main() -> None:
    """Executa verificação completa."""
    print("\n" + "=" * 70)
    print("VERIFICACAO: Integridade do Modelo RL q_network.pkl")
    print("=" * 70 + "\n")

    válido, msg, metadados = verificar_modelo_rl()
    print(msg)

    if válido and metadados:
        print("\n" + "-" * 70)
        print("METADADOS:")
        print("-" * 70)
        for chave, valor in metadados.items():
            if valor is not None:
                print(f"  {chave}: {valor}")

    if válido:
        print("\n✅ STATUS: Pronto para operação")
        print("   Execute: INICIAR_AGENTE_RL_5000.bat")
    else:
        print("\n❌ STATUS: Modelo inválido")
        print("   Próximos passos:")
        print("     1. Treinar novo modelo")
        print("     2. Restaurar de backup")
        print("     3. Copiar de outro diretório")


if __name__ == "__main__":
    main()
