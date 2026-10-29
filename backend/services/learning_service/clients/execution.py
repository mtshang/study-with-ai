import os,httpx
from common import config
from common.execution_contract import ExecutionResult

def execute(code,stdin,request_id):
    key=os.getenv('RUNNER_SERVICE_KEY','')
    if not key:raise RuntimeError('Runner unconfigured')
    with httpx.Client(timeout=httpx.Timeout(45,connect=3),trust_env=False) as client:
        response=client.post(os.getenv('RUNNER_URL','http://127.0.0.1:8004')+'/internal/execute',
            headers={'X-Runner-Key':key},json={'id':request_id,'code':code,'stdin':stdin})
        response.raise_for_status()
        return ExecutionResult.model_validate(response.json()).model_dump()
