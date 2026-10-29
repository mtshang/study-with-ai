"""Fixed Docker invocation. Student input never becomes a host command or mount path."""
import json,os,subprocess,threading,time,uuid
from . import config

LIMIT=32768
cleanup_failed=threading.Event()
BOOTSTRAP="import sys,json,io; p=json.loads(sys.stdin.buffer.read()); sys.stdin=io.TextIOWrapper(io.BytesIO(p['stdin'].encode('utf-8')),encoding='utf-8'); exec(compile(p['code'],'<student>','exec'),{'__name__':'__main__'})"

def environment():
    # CLI needs only Windows/Linux system locations and Docker local configuration.
    allowed=('SYSTEMROOT','WINDIR','COMSPEC','PATH','PATHEXT','USERPROFILE','HOME','APPDATA','LOCALAPPDATA','TEMP','TMP','DOCKER_CONFIG')
    return {k:v for k,v in os.environ.items() if k.upper() in allowed}

def cli(args,timeout=10):
    return subprocess.run([config.DOCKER,*args],capture_output=True,timeout=timeout,env=environment(),check=False)

def ready():
    if cleanup_failed.is_set() or not config.KEY or not config.IMAGE.startswith('sha256:'):return False
    try:
        result=cli(['image','inspect',config.IMAGE,'--format','{{.Os}}'],5)
        return result.returncode==0 and result.stdout.strip()==b'linux'
    except (OSError,subprocess.TimeoutExpired):return False

def remove(name):
    # Names are generated here, never accepted from a user.
    try:return cli(['rm','-f',name]).returncode==0
    except (OSError,subprocess.TimeoutExpired):return False

def recover():
    # This service has a single process. Reclaim only containers with our exact label.
    try:
        found=cli(['ps','-aq','--filter','label='+config.LABEL])
        if found.returncode:return False
        for cid in found.stdout.decode().split():
            if len(cid)!=12 or any(c not in '0123456789abcdef' for c in cid):return False
            if not remove(cid):return False
        cleanup_failed.clear()
        return True
    except (OSError,subprocess.TimeoutExpired):return False

def execute(data):
    started=time.monotonic();name='study-python-'+uuid.uuid4().hex
    result={'status':'unavailable','stdout':'','stderr':'执行环境暂不可用，请稍后新建运行。','exit_code':None,'duration_ms':0,'output_truncated':False}
    proc=None;readers=[];created=False
    try:
        if not ready():return result
        # No bind mounts, Docker socket, ports, host environment or runtime package installs.
        args=['create','--name',name,'--label',config.LABEL,'--pull','never','--network','none',
            '--user','65534:65534','--read-only','--cap-drop','ALL','--security-opt','no-new-privileges',
            '--memory','128m','--memory-swap','128m','--cpus','0.5','--pids-limit','32',
            '--ulimit','nofile=64:64','--ulimit','fsize=1048576:1048576','--ulimit','cpu=3:3',
            '--tmpfs','/tmp:rw,noexec,nosuid,nodev,size=16m,mode=1777','--workdir','/tmp',
            '--log-driver','none','--env','PYTHONIOENCODING=utf-8','-i',config.IMAGE,
            'python','-I','-B','-u','-c',BOOTSTRAP]
        created=True # Even a CLI timeout can leave a server-side container.
        if cli(args).returncode:return result
        proc=subprocess.Popen([config.DOCKER,'start','-a','-i',name],stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=subprocess.PIPE,env=environment())
        buffers=[bytearray(),bytearray()];overflow=threading.Event();lock=threading.Lock()
        def drain(stream,index):
            while True:
                chunk=stream.read(4096)
                if not chunk:break
                with lock:
                    available=LIMIT-sum(len(b) for b in buffers)
                    buffers[index].extend(chunk[:max(0,available)])
                    if len(chunk)>available:overflow.set()
        for index,stream in enumerate((proc.stdout,proc.stderr)):
            reader=threading.Thread(target=drain,args=(stream,index),daemon=True);reader.start();readers.append(reader)
        payload=json.dumps({'code':data.code,'stdin':data.stdin},ensure_ascii=False).encode()
        def feed():
            try:proc.stdin.write(payload);proc.stdin.close()
            except (OSError,ValueError):pass
        writer=threading.Thread(target=feed,daemon=True);writer.start()
        deadline=time.monotonic()+5;status=None
        while proc.poll() is None:
            if overflow.is_set():status='output_limit';break
            if time.monotonic()>deadline:status='timeout';break
            time.sleep(.02)
        if status:cli(['kill',name],5)
        try:proc.wait(timeout=3)
        except subprocess.TimeoutExpired:proc.kill();proc.wait(timeout=3)
        for reader in readers:reader.join(timeout=2)
        info=cli(['inspect',name,'--format','{{json .State}}'],5)
        state=json.loads(info.stdout) if info.returncode==0 else {}
        if not state and not status:return result
        code=state.get('ExitCode')
        if overflow.is_set():status='output_limit'
        status=status or ('completed' if code==0 else 'runtime_error')
        result.update(status=status,stdout=buffers[0].decode('utf-8','replace'),stderr=buffers[1].decode('utf-8','replace'),exit_code=code,output_truncated=overflow.is_set())
        return result
    except (OSError,subprocess.TimeoutExpired,ValueError):return result
    finally:
        if created and not remove(name):
            cleanup_failed.set()
            result.update(status='unavailable',stderr='运行清理未确认，请联系维护者检查执行环境。')
        if proc and proc.poll() is None:proc.kill()
        result['duration_ms']=int((time.monotonic()-started)*1000)
