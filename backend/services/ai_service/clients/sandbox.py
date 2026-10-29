import os
import httpx
from fastapi import HTTPException
from common.agent_execution_contract import AgentExecutionResult
async def request(iid,data=None):
    key=os.getenv('RUNNER_SERVICE_KEY','')
    if not key:raise HTTPException(503,'执行服务尚未配置')
    url=os.getenv('RUNNER_URL','http://127.0.0.1:8004')+'/internal/agent-executions'+('' if data is not None else '/'+iid)
    try:
        async with httpx.AsyncClient(trust_env=False,timeout=httpx.Timeout(50 if data is not None else 3,connect=3)) as client:
            async with client.stream('POST' if data is not None else 'GET',url,json=data,headers={'X-Runner-Key':key}) as response:
                if response.status_code!=200:raise HTTPException(response.status_code,'执行服务暂不可用或任务尚未存在')
                raw=bytearray()
                async for part in response.aiter_bytes():
                    raw.extend(part)
                    if len(raw)>8*1024*1024:raise ValueError('Too large')
        return AgentExecutionResult.model_validate_json(bytes(raw)).model_dump(mode='json')
    except (httpx.HTTPError,ValueError):raise HTTPException(503,'执行响应未确认，可恢复原执行记录') from None
