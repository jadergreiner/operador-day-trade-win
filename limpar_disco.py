#!/usr/bin/env python
# -*- coding: utf-8 -*-
import os
import shutil
import glob

print("=" * 70)
print("LIMPEZA AGRESSIVA DE ESPACO EM DISCO")
print("=" * 70)

removed_mb = 0

# 1. Remover arquivos de cache Python
print("\n1. Removendo cache Python...")
patterns = [
    r"c:\repo\operador-day-trade-win\**\__pycache__",
    r"c:\repo\operador-day-trade-win\**\*.pyc",
    r"c:\repo\operador-day-trade-win\**\*.pyo",
]

for pattern in patterns:
    for path in glob.glob(pattern, recursive=True):
        try:
            if os.path.isdir(path):
                size_before = sum(os.path.getsize(os.path.join(dirpath, filename))
                                 for dirpath, dirnames, filenames in os.walk(path)
                                 for filename in filenames) / (1024*1024)
                shutil.rmtree(path, ignore_errors=True)
                print(f"   Removido: {path} (-{size_before:.1f} MB)")
                removed_mb += size_before
        except:
            pass

# 2. Remover .log files antigos
print("\n2. Removendo arquivos .log antigos...")
for root, dirs, files in os.walk(r"c:\repo\operador-day-trade-win"):
    for file in files:
        if file.endswith('.log'):
            filepath = os.path.join(root, file)
            try:
                size_mb = os.path.getsize(filepath) / (1024*1024)
                os.remove(filepath)
                print(f"   Removido: {file} (-{size_mb:.1f} MB)")
                removed_mb += size_mb
            except:
                pass

# 3. Remover Windows temp files
print("\n3. Limpando temp do Windows...")
try:
    temp_dir = r"C:\Windows\Temp"
    if os.path.exists(temp_dir):
        for file in os.listdir(temp_dir):
            try:
                filepath = os.path.join(temp_dir, file)
                if os.path.isfile(filepath):
                    size_mb = os.path.getsize(filepath) / (1024*1024)
                    os.remove(filepath)
                    if size_mb > 0.1:
                        print(f"   Removido: {file} (-{size_mb:.1f} MB)")
                    removed_mb += size_mb
            except:
                pass
except:
    print("   (Sem permissao para limpeza de Windows\\Temp)")

# 4. Remover .tmp files
print("\n4. Removendo .tmp files...")
for root, dirs, files in os.walk(r"c:\repo\operador-day-trade-win"):
    for file in files:
        if file.endswith('.tmp'):
            filepath = os.path.join(root, file)
            try:
                size_mb = os.path.getsize(filepath) / (1024*1024)
                os.remove(filepath)
                print(f"   Removido {file} (-{size_mb:.1f} MB)")
                removed_mb += size_mb
            except:
                pass

# 5. Verificar espaco depois
print(f"\n5. RESULTADO DA LIMPEZA")
total, used, free = shutil.disk_usage("C:\\")
free_gb = free / (1024**3)
print(f"   Total liberado: ~{removed_mb:.1f} MB")
print(f"   Espaco LIVRE agora: {free_gb:.2f} GB")

if free_gb > 1:
    print(f"   [OK] Espaco suficiente liberado!")
else:
    print(f"   [AVISO] Ainda falta mais limpeza")

print("\n" + "=" * 70)
