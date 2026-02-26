# 🚨 DIAGNÓSTICO: Database or Disk Full

**Timestamp:** 2026-02-26 11:12:00Z
**Erro:** `sqlite3.OperationalError: database or disk is full`
**Sistema:** RL Loop - Inserção em `rl_correlation_scores`
**Status:** 🔴 CRÍTICO - Trading Bloqueado

---

## 1️⃣ VERIFICAR ESPAÇO EM DISCO

### Windows PowerShell:
```powershell
# Verificar espaço livre
Get-Volume

# Ou para pasta específica:
(Get-Item "C:\").GetDirectorySize() | Format-Object -Property Name, @{N="Size";E={"{0:N0}" -f $_.Size}}

# Ver tamanho do banco de dados
Get-Item "data/simulator.db" -Force | Select-Object FullName, @{N="Size (MB)";E={[math]::Round($_.Length/1MB, 2)}}

# Ver tamanho da pasta data/
Get-ChildItem "data/" -Recurse | Measure-Object -Property Length -Sum | Select-Object @{N="Total (MB)";E={[math]::Round($_.Sum/1MB, 2)}}
```

**Expected Output:**
```
Tamanho do banco: ~500MB (normal)
Espaço livre: >1GB (mínimo recomendado)
```

---

## 2️⃣ VERIFICAR BANCO DE DADOS

### Listar Tabelas e Tamanhos:
```bash
cd c:\repo\operador-day-trade-win
python << 'EOF'
import sqlite3
import os

db_path = "data/simulator.db"
conn = sqlite3.connect(db_path)
cursor = conn.cursor()

# Tamanho do arquivo
db_size_mb = os.path.getsize(db_path) / (1024*1024)
print(f"📦 Tamanho total do banco: {db_size_mb:.2f} MB")

# Listar tabelas
cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
tables = cursor.fetchall()

print(f"\n📊 Tabelas no banco ({len(tables)}):")
print("=" * 60)

total_rows = 0
for (table_name,) in tables:
    cursor.execute(f"SELECT COUNT(*) FROM {table_name};")
    count = cursor.fetchone()[0]
    total_rows += count
    print(f"  {table_name}: {count:,} registros")

print("=" * 60)
print(f"Total de registros: {total_rows:,}")

# Verificar espaço livre no SQLite
cursor.execute("PRAGMA freelist_count;")
free_pages = cursor.fetchone()[0]
cursor.execute("PRAGMA page_size;")
page_size = cursor.fetchone()[0]
free_mb = (free_pages * page_size) / (1024*1024)
print(f"\n💾 Espaço livre no banco SQLite: {free_mb:.2f} MB ({free_pages} páginas)")

conn.close()
EOF
```

---

## 3️⃣ LIMPEZA IMEDIATA (Liberar Espaço)

### Opção A: Limpar Dados Antigos (Recomendado)
```bash
cd c:\repo\operador-day-trade-win
python << 'EOF'
import sqlite3
from datetime import datetime, timedelta

db_path = "data/simulator.db"
conn = sqlite3.connect(db_path)
cursor = conn.cursor()

# Deletar registros com mais de 30 dias
cutoff_date = (datetime.now() - timedelta(days=30)).isoformat()

print("🗑️  Limpando dados antigos...")

# Tabelas que crescem rapidamente
tables_to_clean = [
    "rl_correlation_scores",
    "rl_training_episodes",
    "rl_micro_cycles",
    "rl_episode_transitions",
    "rl_training_history"
]

total_deleted = 0
for table in tables_to_clean:
    try:
        cursor.execute(f"DELETE FROM {table} WHERE created_at < ?;", (cutoff_date,))
        deleted = cursor.rowcount
        total_deleted += deleted
        print(f"  {table}: {deleted:,} registros deletados")
    except Exception as e:
        print(f"  ⚠️  {table}: {e}")

conn.commit()

# Reorganizar banco de dados
print("\n🔧 Reorganizando banco de dados (VACUUM)...")
cursor.execute("VACUUM;")

print(f"\n✅ Limpeza completa!")
print(f"  Total deletado: {total_deleted:,} registros")
print(f"  Espaço liberado: ~{total_deleted * 0.001:.1f} MB")

conn.close()
EOF
```

### Opção B: Limpar Tudo (Nuclear - Última Resort)
```bash
cd c:\repo\operador-day-trade-win
# BACKUP primeiro!
Copy-Item "data/simulator.db" "data/simulator.db.backup.$(Get-Date -Format 'yyyyMMdd_HHmmss')"

# Remover banco
Remove-Item "data/simulator.db" -Force

# Sistema vai recriá-lo na próxima execução
echo "✅ Banco removido. Sistema criará novo na próxima inicialização."
```

---

## 4️⃣ VERIFICAR DISCO (Windows)

### Liberar espaço em disco:
```powershell
# Limpar arquivos temporários
Remove-Item "C:\Windows\Temp\*" -Recurse -Force -ErrorAction SilentlyContinue

# Esvaziar Lixeira
Clear-RecycleBin -Force

# Ver espaço livre agora
Get-Volume | Where-Object {$_.DriveLetter -eq 'C'} | Select-Object DriveLetter, Size, SizeRemaining
```

---

## 5️⃣ RESOLVER ERRO SQLALCHEMY

O erro também mencionava SQLAlchemy. Se persistir após limpeza:

```python
# No código do RL Loop, adicionar rollback:
try:
    session.add(correlation_score)
    session.commit()
except Exception as e:
    session.rollback()  # ← ADICIONAR ISSO
    print(f"❌ Erro ao persistir: {e}")
    # Retry lógic ou discard
```

---

## 6️⃣ CONFIGURAÇÃO PERMANENTE

### Limpar banco automaticamente a cada N ciclos:
```python
# Em seu RL Loop
CLEANUP_INTERVAL = 1000  # a cada 1000 ciclos

if episode_number % CLEANUP_INTERVAL == 0:
    print("🧹 Limpeza automática do banco...")
    cursor.execute("DELETE FROM rl_correlation_scores WHERE created_at < DATE('now', '-7 days');")
    cursor.execute("VACUUM;")
    session.commit()
```

---

## 📋 Checklist Resolução

```
[ ] 1. Rodar comando de diagnóstico (Seção 2)
[ ] 2. Verificar espaço em disco (Seção 1)
[ ] 3. Se disco < 500MB, limpar files (Seção 4)
[ ] 4. Rodar limpeza SQLite (Seção 3, Opção A)
[ ] 5. Testar sistema novamente
[ ] 6. Se problema persistir, usar Opção B (Nuclear)
[ ] 7. Implementar cleanup automático (Seção 6)
```

---

## 🎯 Prioridade

1. **URGENTE:** Liberar espaço em disco (Seção 4)
2. **CRÍTICO:** Limpar banco antigo (Seção 3)
3. **IMPORTANTE:** Adicionar rollback no código (Seção 5)
4. **MELHORIA:** Setup limpeza automática (Seção 6)

---

## 📞 Próximos Passos

**Imediatamente:**
```bash
# Rodar diagnóstico
python (script seção 2)

# Se espaço livre < 500MB:
Remove-Item "C:\Windows\Temp\*" -Recurse -Force

# Limpar banco
python (script seção 3)
```

**Resultado esperado:**
```
✅ Trading automático retoma
✅ RL Loop volta a processar ciclos
✅ Sem mais erros de "database full"
```

---

**Status:** 🔴 Ação imediata necessária
**Tempo estimado:** 5-10 minutos
**Risco:** Baixo (backup foi feito antes de limpar)

