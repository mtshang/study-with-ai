"""Runs INSIDE the disposable container. Its output remains untrusted on the host."""
import base64,json,os,pathlib,stat,subprocess,sys
p=json.loads(sys.stdin.buffer.read())
root=pathlib.Path('/tmp/work');root.mkdir()
for group in ('inputs','skill','output'):(root/group).mkdir()
for group in ('inputs','skill'):
    for item in p[group]:
        path=root/group/item['path'];path.parent.mkdir(parents=True,exist_ok=True);path.write_bytes(base64.b64decode(item['content']))
if p.get('script'):script=root/'skill'/p['script'];cwd=root/'skill'
else:script=root/'main.py';script.write_text(p['code'],encoding='utf-8');cwd=root
env={'PATH':'/usr/local/bin:/usr/bin:/bin','LANG':'C.UTF-8','PYTHONIOENCODING':'utf-8','INPUT_DIR':str(root/'inputs'),'OUTPUT_DIR':str(root/'output'),'SKILL_DIR':str(root/'skill')}
with open('/tmp/stdout','wb') as out,open('/tmp/stderr','wb') as err:
    proc=subprocess.Popen([sys.executable,'-B','-u',str(script),*p['arguments']],cwd=cwd,stdin=subprocess.DEVNULL,stdout=out,stderr=err,env=env,start_new_session=True)
    try:code=proc.wait(timeout=25);status='completed' if code==0 else 'runtime_error'
    except subprocess.TimeoutExpired:
        import signal
        os.killpg(proc.pid,signal.SIGKILL);proc.wait();code=None;status='timeout'
files=[];total=0;note=''
for folder,dirs,names in os.walk(root/'output',followlinks=False):
    dirs[:]=[d for d in dirs if not (pathlib.Path(folder)/d).is_symlink()]
    for name in sorted(names):
        path=pathlib.Path(folder)/name
        try:
            fd=os.open(path,os.O_RDONLY|os.O_NOFOLLOW|os.O_NONBLOCK)
            with os.fdopen(fd,'rb') as f:
                info=os.fstat(f.fileno())
                if not stat.S_ISREG(info.st_mode):continue
                content=f.read(5*1024*1024+1)
            if len(files)>=20 or total+len(content)>5*1024*1024:note='Output file count/size limit exceeded';continue
            files.append({'path':str(path.relative_to(root/'output')),'content':base64.b64encode(content).decode()});total+=len(content)
        except OSError:continue
def read(path):
    with open(path,'rb') as f:return f.read(24000).decode('utf-8','replace')
print(json.dumps({'status':status,'stdout':read('/tmp/stdout'),'stderr':read('/tmp/stderr')+'\n'+note,'exit_code':code,'files':files,'duration_ms':0},ensure_ascii=True))
