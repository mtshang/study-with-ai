"""Single-process, disk receipts for isolated Agent runs. No database/model keys."""
import hashlib,json,os,subprocess,threading,time,uuid
from pathlib import Path
from fastapi import HTTPException
from common.agent_execution_contract import AgentExecutionResult
from . import runner,config

ROOT=config.ROOT/'runner_data'/'agent_runs'
BOOTSTRAP=(Path(__file__).with_name('agent_bootstrap.py')).read_text(encoding='utf-8')
lock=threading.Lock();active=set()
def location(iid):return ROOT/str(uuid.UUID(str(iid)))
def save(path,data):
    path.parent.mkdir(parents=True,exist_ok=True);tmp=path.with_name('pending-'+uuid.uuid4().hex)
    try:
        with open(tmp,'w',encoding='utf-8') as f:json.dump(data,f);f.flush();os.fsync(f.fileno())
        os.replace(tmp,path)
    finally:tmp.unlink(missing_ok=True)
def read(path):return json.loads(path.read_text(encoding='utf-8'))
def status(iid):
    base=location(iid)
    with lock:
        if (base/'result.json').is_file():return read(base/'result.json')
        if str(iid) in active:return {'status':'running'}
        if (base/'request.json').is_file():return {'status':'interrupted'}
    raise HTTPException(404,'执行记录不存在')

def execute(data):
    iid=str(data.id);base=location(iid);request=data.model_dump(mode='json');digest=hashlib.sha256(json.dumps(request,sort_keys=True).encode()).hexdigest()
    with lock:
        if (base/'request.json').is_file() and read(base/'request.json')['sha256']!=digest:raise HTTPException(409,'执行ID已经用于不同输入')
        if (base/'result.json').is_file():return read(base/'result.json')
        if iid in active:return {'status':'running'}
        if not runner.ready():return {'status':'unavailable','stderr':'执行环境未就绪'}
        save(base/'request.json',{'sha256':digest});active.add(iid)
    result=None
    try:
        result=run_container(request)
        if result['status'] in ('completed','runtime_error','timeout'):
            result=AgentExecutionResult.model_validate(result).model_dump(mode='json');save(base/'result.json',result)
        return result
    finally:
        with lock:active.discard(iid)

def run_container(request):
    start=time.monotonic();name='study-agent-'+uuid.uuid4().hex;proc=None;created=False
    result={'status':'unavailable','stderr':'执行未完成，可以使用原执行ID恢复'}
    try:
        args=['create','--name',name,'--label',config.LABEL,'--pull','never','--network','none','--user','65534:65534','--read-only','--cap-drop','ALL','--security-opt','no-new-privileges','--memory','256m','--memory-swap','256m','--cpus','1','--pids-limit','32','--ulimit','nofile=128:128','--ulimit','fsize=5242880:5242880','--ulimit','cpu=25:25','--tmpfs','/tmp:rw,noexec,nosuid,nodev,size=48m,mode=1777','--workdir','/tmp','--log-driver','none','--env','PYTHONIOENCODING=utf-8','-i',config.IMAGE,'python','-I','-B','-u','-c',BOOTSTRAP]
        created=True
        if runner.cli(args).returncode:return result
        proc=subprocess.Popen([config.DOCKER,'start','-a','-i',name],stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=subprocess.PIPE,env=runner.environment())
        buffers=[bytearray(),bytearray()];overflow=threading.Event();guard=threading.Lock()
        def drain(stream,index):
            while chunk:=stream.read(65536):
                with guard:
                    available=8*1024*1024-sum(map(len,buffers));buffers[index].extend(chunk[:max(0,available)])
                    if len(chunk)>available:overflow.set()
        readers=[threading.Thread(target=drain,args=(stream,i),daemon=True) for i,stream in enumerate((proc.stdout,proc.stderr))]
        for t in readers:t.start()
        payload=json.dumps(request).encode()
        def feed():
            try:proc.stdin.write(payload);proc.stdin.close()
            except (OSError,ValueError):pass
        threading.Thread(target=feed,daemon=True).start();deadline=time.monotonic()+35
        while proc.poll() is None:
            if overflow.is_set() or time.monotonic()>deadline:runner.cli(['kill',name],5);break
            time.sleep(.03)
        try:proc.wait(timeout=3)
        except subprocess.TimeoutExpired:proc.kill();proc.wait(timeout=3)
        for t in readers:t.join(timeout=2)
        if overflow.is_set():
            result={'status':'runtime_error','stderr':'执行输出超出限制','files':[]};return result
        try:
            result=AgentExecutionResult.model_validate_json(bytes(buffers[0])).model_dump(mode='json')
            if result['status'] not in ('completed','runtime_error','timeout'):raise ValueError('Untrusted execution state')
        except ValueError:result={'status':'runtime_error','stderr':'执行中断或输出格式无效；未接收任何产物','files':[]}
        result['duration_ms']=int((time.monotonic()-start)*1000)
        return result
    except (OSError,ValueError,subprocess.TimeoutExpired):return result
    finally:
        if created and not runner.remove(name):
            runner.cleanup_failed.set();result.clear();result.update(status='unavailable',stderr='容器清理未确认，执行服务已停止接收新任务')
        if proc and proc.poll() is None:proc.kill()
