"""Run gateway, three business services, and the optional Python execution process; Ctrl+C stops all child processes."""
from pathlib import Path
import subprocess,sys,time,socket,os
ROOT=Path(__file__).resolve().parents[1]
SERVICES=[("services.identity_service.main:app",8001),("services.learning_service.main:app",8002),
          ("services.ai_service.main:app",8003),("gateway.main:app",8000),("services.execution_service.main:app",8004)]
def main():
    for _,port in SERVICES:
        with socket.socket() as probe:
            if probe.connect_ex(("127.0.0.1",port))==0: raise SystemExit(f"Port {port} is occupied; no services started")
    children=[]
    try:
        for module,port in SERVICES:
            env=None
            if port==8004:
                allowed={'SYSTEMROOT','WINDIR','COMSPEC','PATH','PATHEXT','USERPROFILE','HOME','APPDATA','LOCALAPPDATA','TEMP','TMP','DOCKER_CONFIG'}
                env={k:v for k,v in os.environ.items() if k.upper() in allowed};env['PYTHONUTF8']='1'
            children.append(subprocess.Popen([sys.executable,"-m","uvicorn",module,"--host","127.0.0.1","--port",str(port),"--no-proxy-headers"],cwd=ROOT,env=env))
        while all(proc.poll() is None for proc in children[:4]): time.sleep(.5)
        raise SystemExit("A service exited; stopping this development group")
    except KeyboardInterrupt: pass
    finally:
        for proc in reversed(children):
            if proc.poll() is None: proc.terminate()
        for proc in children:
            try: proc.wait(timeout=10)
            except subprocess.TimeoutExpired: proc.kill();proc.wait()
if __name__=="__main__": main()
