import shutil

total, used, free = shutil.disk_usage("C:\\")
print(f"C: Total: {total/(1024**3):.1f} GB | Usado: {used/(1024**3):.1f} GB | LIVRE: {free/(1024**3):.1f} GB ({100*free/total:.1f}%)")
