"""Start the single-process runner with an explicitly filtered OS environment."""
import os,subprocess,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
allowed={'SYSTEMROOT','WINDIR','COMSPEC','PATH','PATHEXT','USERPROFILE','HOME','APPDATA','LOCALAPPDATA','TEMP','TMP','DOCKER_CONFIG'}
env={k:v for k,v in os.environ.items() if k.upper() in allowed}
env['PYTHONUTF8']='1'
raise SystemExit(subprocess.call([sys.executable,'-m','uvicorn','services.execution_service.main:app','--host','127.0.0.1','--port','8004','--no-proxy-headers'],cwd=ROOT,env=env))
