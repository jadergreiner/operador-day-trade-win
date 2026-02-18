"""Migration: criar tabelas do modelo colunar RL.

Uso:
    python scripts/migrate_rl_tables.py [--db-path data/db/trading.db]

Cria todas as tabelas do modelo de Aprendizagem por Reforço:
    - dim_correlation_items (cadastro dos 85 itens)
    - dim_technical_indicators (referência de indicadores)
    - rl_episodes (episódios de decisão)
    - rl_correlation_scores (scores por item por episódio)
    - rl_indicator_values (indicadores por episódio)
    - rl_rewards (recompensas multi-horizonte)
    - rl_training_metrics (métricas de treinamento)

E popula as tabelas de dimensão com dados de referência.
"""

import argparse
import sys
from pathlib import Path

# Adiciona raiz ao path
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from src.infrastructure.database.rl_schema import create_rl_tables
from src.infrastructure.repositories.rl_repository import SqliteRLRepository


def main():
    parser = argparse.ArgumentParser(description="Migration: tabelas RL")
    parser.add_argument(
        "--db-path",
        default="data/db/trading.db",
        help="Caminho do banco SQLite (padrão: data/db/trading.db)",
    )
    args = parser.parse_args()

    db_path = Path(args.db_path)
    db_path.parent.mkdir(parents=True, exist_ok=True)

    print(f"📦 Criando tabelas RL em: {db_path}")
    print()

    # Cria engine
    engine = create_engine(f"sqlite:///{db_path}", echo=False)

    # Cria tabelas
    create_rl_tables(engine)
    print("✅ Tabelas criadas:")
    print("   - dim_correlation_items")
    print("   - dim_technical_indicators")
    print("   - rl_episodes")
    print("   - rl_correlation_scores")
    print("   - rl_indicator_values")
    print("   - rl_rewards")
    print("   - rl_training_metrics")
    print()

    # Popula dimensões
    print("📊 Populando tabelas de dimensão...")
    SessionLocal = sessionmaker(bind=engine)
    session = SessionLocal()

    repo = SqliteRLRepository(session)
    repo.seed_dimension_tables()

    # Conta registros
    from src.infrastructure.database.rl_schema import (
        DimCorrelationItemModel,
        DimTechnicalIndicatorModel,
    )

    n_items = session.query(DimCorrelationItemModel).count()
    n_indicators = session.query(DimTechnicalIndicatorModel).count()

    print(f"   ✅ {n_items} itens de correlação cadastrados")
    print(f"   ✅ {n_indicators} indicadores técnicos cadastrados")
    print()

    session.close()

    print("🎯 Migration concluída com sucesso!")
    print()
    print("Modelo RL (Aprendizagem por Reforço):")
    print("  Episódio = par (estado, ação)")
    print("  Estado   = vetor de scores + cotações + indicadores")
    print("  Ação     = decisão (BUY/SELL/HOLD)")
    print("  Reward   = variação preço WIN em 5/15/30/60/120 min")


if __name__ == "__main__":
    main()
