"""Initialize local runner configuration without overwriting existing credentials."""
from pathlib import Path
import os,secrets,subprocess,re
from dotenv import dotenv_values
ROOT=Path(__file__).resolve().parents[2]

def main():
    docker='C:/Program Files/Docker/Docker/resources/bin/docker.exe' if os.name=='nt' else '/usr/bin/docker'
    path=ROOT/'.env.runner';existing=dotenv_values(path,interpolate=False) if path.exists() else {}
    key=existing.get('RUNNER_SERVICE_KEY') or secrets.token_urlsafe(48)
    if existing and (not existing.get('RUNNER_SERVICE_KEY') or not re.fullmatch('sha256:[0-9a-f]{64}',existing.get('RUNNER_IMAGE',''))):raise SystemExit('Existing runner configuration is incomplete; preserved for manual review')
    configs=[p for p in [ROOT/'.env.services',ROOT/'.env.services.test'] if p.exists()]
    if not configs:raise SystemExit('Initialize service environments first')
    for p in configs:
        current=dotenv_values(p,interpolate=False).get('RUNNER_SERVICE_KEY')
        if current and current!=key:raise SystemExit('Runner key mismatch; existing settings preserved')
    if not existing:
        result=subprocess.run([docker,'image','inspect','python:3.12-slim','--format','{{.Id}}'],capture_output=True,text=True,timeout=20)
        image=result.stdout.strip()
        if result.returncode or not re.fullmatch('sha256:[0-9a-f]{64}',image):raise SystemExit('Run docker pull python:3.12-slim first')
        with path.open('x',encoding='utf-8') as f:f.write('RUNNER_SERVICE_KEY='+key+'\nRUNNER_IMAGE='+image+'\n')
    for p in configs:
        values=dotenv_values(p,interpolate=False)
        with p.open('a',encoding='utf-8') as f:
            if not values.get('RUNNER_SERVICE_KEY'):f.write('\nRUNNER_SERVICE_KEY='+key+'\n')
            if not values.get('RUNNER_URL'):f.write('RUNNER_URL=http://127.0.0.1:8004\n')
    print('Runner settings ready; existing image and credentials preserved. No secrets displayed.')
if __name__=='__main__':main()
