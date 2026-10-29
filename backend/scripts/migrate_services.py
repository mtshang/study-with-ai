from pathlib import Path
import subprocess,sys
ROOT=Path(__file__).resolve().parents[1]
for name in ["identity","learning","ai"]:
    subprocess.run([sys.executable,"-m","alembic","-c",str(ROOT/f"services/{name}_service/alembic.ini"),"upgrade","head"],cwd=ROOT,check=True)
