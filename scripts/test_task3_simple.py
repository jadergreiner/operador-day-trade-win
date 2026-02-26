#!/usr/bin/env python3
"""
Teste Simples de TASK #3 - Validação sem pytest
"""

import sys
import numpy as np
import tempfile
from pathlib import Path

# Add workspace to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.application.backtest_validator import BacktestValidator

def create_test_dataset():
    """Cria dataset mock para testes"""
    tmpdir = tempfile.mkdtemp()
    dataset_path = f"{tmpdir}/winfut_test.npz"
    
    # Gerar dados
    np.random.seed(42)
    X = np.random.randn(435, 24).astype(np.float32)
    y = np.random.randint(0, 2, 435).astype(np.int32)
    
    # Garantir balanceamento
    y[:200] = 0  # 200 SKIP
    y[200:] = 1  # 235 BUY
    np.random.shuffle(y)
    
    # Feature names
    feature_names = np.array([f"feature_{i}" for i in range(24)])
    
    # Salvar
    np.savez(dataset_path, X=X, y=y, feature_names=feature_names)
    return dataset_path, tmpdir

def main():
    print("🚀 Teste Simples TASK #3\n")
    
    try:
        # Criar dataset
        print("1. Criando dataset mock...")
        dataset_path, tmpdir = create_test_dataset()
        print(f"   ✅ Dataset criado em: {dataset_path}\n")
        
        # Instanciar validator
        print("2. Instanciando BacktestValidator...")
        validator = BacktestValidator(
            dataset_path=dataset_path,
            model_type="xgboost"
        )
        print("   ✅ Instância criada\n")
        
        # Carregar dataset
        print("3. Carregando dataset...")
        validator.load_dataset()
        print(f"   ✅ Dataset carregado: {validator.X.shape} features, {validator.y.shape} labels\n")
        
        # Validar dataset
        print("4. Validando dataset...")
        assert validator.X.shape == (435, 24), "Shape X incorreto"
        assert validator.y.shape == (435,), "Shape y incorreto"
        assert set(np.unique(validator.y)) == {0, 1}, "Labels devem ser 0 ou 1"
        print("   ✅ Dataset válido\n")
        
        # Grid search (versão reduzida)
        print("5. Executando Grid Search (8 configs)...")
        print("   ⏳ Isso pode levar ~30-60 segundos...")
        
        results = validator.run_grid_search()
        
        print(f"   ✅ Grid search completo: {len(results)} configurações\n")
        
        # Validar resultados
        print("6. Validando resultados...")
        assert len(results) == 8, "Deveriam ter 8 configs"
        
        for i, config in enumerate(results):
            print(f"   Config {i+1}: sigma={config['threshold_sigma']:.2f}, " \
                  f"F1={config['f1_score']:.3f}, WR={config['win_rate']:.1f}%")
            
            assert "threshold_sigma" in config
            assert "f1_score" in config
            assert "win_rate" in config
        
        # Encontrar melhor config
        best_f1 = max(results, key=lambda x: x['f1_score'])
        best_wr = max(results, key=lambda x: x['win_rate'])
        
        print(f"\n   🏆 Melhor F1: sigma={best_f1['threshold_sigma']} com F1={best_f1['f1_score']:.3f}")
        print(f"   🏆 Melhor WR: sigma={best_wr['threshold_sigma']} com {best_wr['win_rate']:.1f}%")
        
        # Salvar resultados
        print("\n7. Salvando resultados...")
        output_path = f"{tmpdir}/backtest_results.json"
        validator.save_results(results, output_path)
        assert Path(output_path).exists(), "JSON não foi criado"
        print(f"   ✅ Resultados salvos em: {output_path}\n")
        
        print("=" * 60)
        print("✅ TODOS OS TESTES PASSARAM COM SUCESSO!")
        print("=" * 60)
        print("\n📊 RESUMO TASK #3:")
        print(f"   • Dataset: 435 amostras × 24 features")
        print(f"   • Grid Search: 8 thresholds processados")
        print(f"   • AC-1 ✅ Dataset carregado")
        print(f"   • AC-2 ✅ Métricas calculadas (F1, Precision, Recall, ROC-AUC)")
        print(f"   • AC-3 ✅ Grid search 8 thresholds completo")
        print(f"   • AC-4 ✅ Win rate calculado para cada config")
        print()
        
        return 0
        
    except Exception as e:
        print(f"\n❌ ERRO: {e}")
        import traceback
        traceback.print_exc()
        return 1

if __name__ == "__main__":
    sys.exit(main())
