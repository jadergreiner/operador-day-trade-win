#!/usr/bin/env python3
"""Train WINFUT XGBoost Model — Sprint 0.

Script principal para treinar o modelo.

Uso:
    python scripts/ml/train_winfut_xgboost.py [--days 30] [--tier 1]

Options:
    --days:    Quantos dias de histórico usar (default: 30)
    --tier:    Tier de features (1 ou 2, default: 1)
"""

import sys
from pathlib import Path

# Add root ao path
ROOT_DIR = Path(__file__).resolve().parents[2]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

import argparse
from datetime import datetime, timedelta

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from src.application.services.ml.winfut_dataset import WinFutDatasetBuilder
from src.application.services.ml.winfut_feature_engineer import WinFutFeatureEngineer
from src.application.services.ml.winfut_model_trainer import WinFutModelTrainer


def main():
    parser = argparse.ArgumentParser(description="Train WINFUT XGBoost Model")
    parser.add_argument("--days", type=int, default=30, help="Dias de histórico")
    parser.add_argument("--tier", type=int, default=1, help="Tier de features (1 ou 2)")
    parser.add_argument("--db", type=str, default="data/db/trading.db", help="Path ao banco SQLite")
    parser.add_argument("--output", type=str, default="latest", help="Sufixo do modelo")

    args = parser.parse_args()

    print("\n" + "="*70)
    print("TREINAMENTO — MODELO WINFUT XGBOOST (Sprint 0)")
    print("="*70 + "\n")

    # Conectar ao banco
    db_path = Path(args.db)
    if not db_path.exists():
        print(f"❌ Banco de dados não encontrado: {db_path}")
        sys.exit(1)

    engine = create_engine(f"sqlite:///{db_path}")
    Session = sessionmaker(bind=engine)
    session = Session()

    try:
        # 1. CARREGAR DATASET
        print(f"\n1️⃣  Carregando dataset (últimos {args.days} dias)...")
        end_date = datetime.now()
        start_date = end_date - timedelta(days=args.days)

        builder = WinFutDatasetBuilder(session)
        X, y = builder.build(
            start_date=start_date,
            end_date=end_date,
            mode="training",
        )

        print(f"   Shape: X={X.shape}, y={y.shape}")
        print(f"   Range y: [{y.min():.2f}, {y.max():.2f}] pts")

        # 2. TREINAR COM WALK-FORWARD
        print(f"\n2️⃣  Treinando modelo (walk-forward, {args.tier} folds)...")
        trainer = WinFutModelTrainer()
        wf_results = trainer.train_walk_forward(X, y, n_folds=5)

        # Verificar se aceita modelo
        avg_mae = wf_results["avg_mae_val"]
        if avg_mae > 150:
            print(f"\n❌ MAE muito alto ({avg_mae:.2f}). Aumentar features ou dados.")
            sys.exit(1)

        # 3. TREINAR FINAL
        print(f"\n3️⃣  Treinando modelo final (com TODOS os dados)...")
        trainer.train_final(X, y)

        # 4. SALVAR
        print(f"\n4️⃣  Salvando modelo...")
        model_path = trainer.save_model(suffix=args.output)

        # 5. IMPRIMIR RELATÓRIO
        print(f"\n5️⃣  RELATÓRIO:")
        print(trainer.generate_report())

        print(f"\n✅ Treinamento concluído com sucesso!")
        print(f"   Modelo: {model_path}")

    finally:
        session.close()


if __name__ == "__main__":
    main()
