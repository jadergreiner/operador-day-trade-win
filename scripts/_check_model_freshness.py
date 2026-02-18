"""Verifica se o modelo atual contem os aprendizados de hoje."""
import joblib
import json
from pathlib import Path
import sqlite3

# 1) Dados no modelo
lgbm_path = Path("data/models/lgbm/lgbm_classification_latest.pkl")
if lgbm_path.exists():
    model = joblib.load(lgbm_path)
    print("=== MODELO LGBM (arquivo) ===")
    print(f"  Modificado: {lgbm_path.stat().st_mtime}")
    from datetime import datetime
    mod_time = datetime.fromtimestamp(lgbm_path.stat().st_mtime)
    print(f"  Data arquivo: {mod_time}")
    print(f"  Tipo: {type(model).__name__}")
    if hasattr(model, "classes_"):
        print(f"  Classes: {model.classes_}")
    if hasattr(model, "n_features_in_"):
        print(f"  Features: {model.n_features_in_}")

# 2) Modelo WINFUT
winfut_path = Path("data/models/winfut/winfut_model_latest.pkl")
if winfut_path.exists():
    payload = joblib.load(winfut_path)
    print()
    print("=== MODELO WINFUT (arquivo) ===")
    mod_time = datetime.fromtimestamp(winfut_path.stat().st_mtime)
    print(f"  Data arquivo: {mod_time}")
    print(f"  Keys: {list(payload.keys())}")
    for k, v in payload.items():
        if isinstance(v, str) or isinstance(v, (int, float)):
            print(f"  {k}: {v}")
        elif isinstance(v, dict):
            print(f"  {k}: {v}")

# 3) Dados de treino vs dados novos
report_path = Path("data/ml/reports/training_report_20260211_191940.json")
if report_path.exists():
    rpt = json.loads(report_path.read_text())
    print()
    print("=== ULTIMO TREINO: 11/02/2026 19:19 ===")
    print(f"  Accuracy: {rpt['avg_metrics']['accuracy_mean']:.1%}")
    print(f"  F1 macro: {rpt['avg_metrics']['f1_macro_mean']:.1%}")
    for fold in rpt["fold_results"]:
        print(f"    Fold {fold['fold']}: train={fold['train_size']} test={fold['test_size']}")
    total_samples = sum(f["train_size"] + f["test_size"] for f in rpt["fold_results"])
    # Ultimo fold tem o total real
    last_fold = rpt["fold_results"][-1]
    real_total = last_fold["train_size"] + last_fold["test_size"]
    print(f"  Total amostras no treino: {real_total}")

# 4) Dados atuais no DB (incluindo hoje)
con = sqlite3.connect("data/db/trading.db")
print()
print("=== DADOS DISPONIVEIS AGORA ===")
rows = con.execute("""
    SELECT DATE(timestamp) as dia, COUNT(*)
    FROM rl_episodes
    GROUP BY DATE(timestamp)
    ORDER BY dia
""").fetchall()
total_now = 0
for r in rows:
    print(f"  {r[0]}: {r[1]} episodios")
    total_now += r[1]
print(f"  TOTAL ATUAL: {total_now}")

# Rewards avaliados
evaluated = con.execute("SELECT COUNT(*) FROM rl_rewards WHERE was_correct IS NOT NULL").fetchone()[0]
pending = con.execute("SELECT COUNT(*) FROM rl_rewards WHERE was_correct IS NULL").fetchone()[0]
print(f"  Rewards avaliados: {evaluated} | Pendentes: {pending}")

# 5) Quanto dado novo
print()
print("=== GAP ===")
new_episodes = con.execute("""
    SELECT COUNT(*) FROM rl_episodes
    WHERE DATE(timestamp) = '2026-02-12'
""").fetchone()[0]
new_rewards = con.execute("""
    SELECT COUNT(*) FROM rl_rewards r
    JOIN rl_episodes e ON r.episode_id = e.episode_id
    WHERE DATE(e.timestamp) = '2026-02-12'
    AND r.was_correct IS NOT NULL
""").fetchone()[0]
print(f"  Episodios de HOJE nao vistos pelo modelo: {new_episodes}")
print(f"  Rewards de HOJE nao vistos pelo modelo: {new_rewards}")
print(f"  O modelo foi treinado ANTES do pregao de 12/02")
print(f"  NENHUM aprendizado de hoje esta no modelo!")

con.close()
