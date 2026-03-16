#!/usr/bin/env python3
"""Regenera o modelo RL no formato correto (MLPRegressor sklearn)."""

import json
import sys
from pathlib import Path

import joblib
import numpy as np
from sklearn.neural_network import MLPRegressor

# Setup path
ROOT_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT_DIR))

# Configuração do modelo
N_FEATURES = 15  # Estado: 15 dimensões
N_ACTIONS = 3    # Ações: HOLD, BUY, SELL

def regenerar_modelo_rl() -> bool:
    """Regenera modelo RL no formato esperado (MLPRegressor)."""
    
    print("[INFO] Regenerando modelo RL...")
    
    # Criar MLPRegressor (conforme agente_q_learning.py)
    modelo = MLPRegressor(
        hidden_layer_sizes=(128, 64, 32),
        activation='relu',
        solver='adam',
        alpha=0.0001,
        batch_size=64,
        learning_rate='adaptive',
        learning_rate_init=0.001,
        max_iter=10000,
        random_state=42,
        early_stopping=False,
        verbose=False,
    )
    
    # Fazer um fit dummy para inicializar o modelo
    # (MLPRegressor precisa de fit antes de usar)
    X_dummy = np.random.randn(100, N_FEATURES)
    y_dummy = np.random.randn(100, N_ACTIONS)
    
    print("   [*] Inicializando modelo com dados dummy...")
    modelo.fit(X_dummy, y_dummy)
    
    # Definir diretórios
    model_dir_1 = ROOT_DIR / "data" / "models" / "novo_agente_rl" / "modelo_final"
    model_dir_2 = Path("C:") / "repo" / "data" / "models" / "novo_agente_rl" / "modelo_final"
    
    # Salvar no primeiro local
    print(f"\n   [*] Salvando modelo em: {model_dir_1}")
    model_dir_1.mkdir(parents=True, exist_ok=True)
    
    try:
        joblib.dump(modelo, model_dir_1 / "q_network.pkl")
        print(f"       ✅ Modelo salvo com sucesso")
        
        arquivo_size = (model_dir_1 / "q_network.pkl").stat().st_size
        print(f"       📦 Tamanho: {arquivo_size / 1024:.1f} KB")
    except Exception as e:
        print(f"       ❌ Erro ao salvar: {e}")
        return False
    
    # Salvar metadados
    print(f"   [*] Salvando metadados...")
    metadados = {
        "tamanho_estado": N_FEATURES,
        "n_acoes": N_ACTIONS,
        "epsilon": 0.1,
        "n_passos": 0,
        "n_episodios": 5000,
        "modelo_inicializado": True,
        "config": {
            "taxa_aprendizado": 0.001,
            "fator_desconto": 0.95,
            "epsilon_inicial": 1.0,
            "epsilon_minimo": 0.05,
            "taxa_decaimento_epsilon": 0.995,
        },
    }
    
    try:
        with open(model_dir_1 / "metadados.json", "w", encoding="utf-8") as f:
            json.dump(metadados, f, indent=2, ensure_ascii=False)
        print(f"       ✅ Metadados salvos")
    except Exception as e:
        print(f"       ❌ Erro ao salvar metadados: {e}")
        return False
    
    # Tentar copiar para segunda localização (C:\repo\data\...)
    if model_dir_2 != model_dir_1:
        print(f"\n   [*] Copiando para segundo local: {model_dir_2}")
        try:
            model_dir_2.mkdir(parents=True, exist_ok=True)
            joblib.dump(modelo, model_dir_2 / "q_network.pkl")
            with open(model_dir_2 / "metadados.json", "w", encoding="utf-8") as f:
                json.dump(metadados, f, indent=2, ensure_ascii=False)
            print(f"       ✅ Modelo copiado para segundo local")
        except Exception as e:
            print(f"       ⚠️  Aviso: Não foi possível copiar para segundo local: {e}")
    
    # Validar modelo carregando
    print(f"\n   [*] Validando modelo carregado...")
    try:
        modelo_teste = joblib.load(model_dir_1 / "q_network.pkl")
        print(f"       ✅ Modelo carregado com sucesso")
        print(f"       🧠 Tipo: {type(modelo_teste).__name__}")
        print(f"       📊 Inputs: {modelo_teste.n_features_in_}")
        print(f"       📤 Outputs: {modelo_teste.n_outputs_}")
    except Exception as e:
        print(f"       ❌ Erro ao validar: {e}")
        return False
    
    print(f"\n✅ Regeneracao de modelo RL concluída com sucesso!")
    print(f"\n   Modelo localizações:")
    print(f"   1. {model_dir_1}")
    print(f"   2. {model_dir_2}")
    print(f"\n   Próximo passo: Execute INICIAR_AGENTE_RL_5000.bat")
    
    return True

if __name__ == "__main__":
    sucesso = regenerar_modelo_rl()
    sys.exit(0 if sucesso else 1)
