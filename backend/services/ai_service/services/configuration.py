import hashlib, io, os, re, tempfile
from pathlib import Path
from urllib.parse import urlsplit
from dotenv import dotenv_values
from dotenv.parser import parse_stream
from fastapi import HTTPException
from common.storage import user_path
from ..infrastructure.config import settings
from ..repositories.chat import profile

def config_path(user):
    folder=user_path(settings.user_root,user.storage_dir)
    path=folder/'.env'
    if path.is_symlink() or path.resolve().parent!=folder: raise HTTPException(400,'配置路径不合法')
    return path

def read_file(user):
    try:
        path=config_path(user)
        if path.stat().st_size>65536: raise HTTPException(422,'模型配置文件过大')
        raw=path.read_text(encoding='utf-8-sig')
        bindings=list(parse_stream(io.StringIO(raw)))
        if any(item.error for item in bindings): raise HTTPException(422,'个人 .env 格式错误，请检查原文件')
        return raw,dict(dotenv_values(stream=io.StringIO(raw),interpolate=False))
    except (OSError,UnicodeError): raise HTTPException(503,'无法读取个人模型配置') from None

def revision(raw,permission):
    return hashlib.sha256((raw+'\0'+permission).encode()).hexdigest()

def view(user,db):
    owner=profile(db,user.id)
    raw,values=read_file(user)
    result={'revision':revision(raw,owner.permission),'permission':owner.permission}
    for channel in ['chat','vision']:
        prefix=channel.upper()
        result[channel]={'base_url':values.get(prefix+'_BASE_URL') or '', 'model':values.get(prefix+'_MODEL') or '', 'key_set':bool(values.get(prefix+'_API_KEY'))}
    db.commit()
    return result

def validate_url(value):
    try:
        parts=urlsplit(value);port=parts.port
    except ValueError: raise HTTPException(422,'接口地址格式不正确') from None
    if parts.scheme!='https' or not parts.hostname or parts.username or parts.password or parts.query or parts.fragment or port not in (None,443):
        raise HTTPException(422,'接口地址需为不带凭证、查询参数的 HTTPS 基础地址（443 端口）')
    if any(c.isspace() for c in value): raise HTTPException(422,'接口地址不合法')
    return value.rstrip('/')

def save(user,data,db):
    owner=profile(db,user.id,True)
    raw,values=read_file(user)
    if revision(raw,owner.permission)!=data.revision: raise HTTPException(409,'API 设置已变化，请重新读取后修改')
    prefix=data.channel.upper()
    base=data.base_url.strip()
    base=validate_url(base) if base else ''
    model=data.model.strip()
    key=data.api_key.get_secret_value() if data.api_key is not None else None
    if key is not None and (not key or len(key)>4096 or any(c.isspace() or ord(c)<32 for c in key)):
        raise HTTPException(422,'API Key 不能为空或包含空白字符')
    if key is not None and data.clear_key: raise HTTPException(422,'不能同时更新和清除 Key')
    if base!=(values.get(prefix+'_BASE_URL') or '').rstrip('/') and values.get(prefix+'_API_KEY') and key is None and not data.clear_key:
        raise HTTPException(422,'更换接口地址时请重新填写 Key，或明确清除原 Key')
    changes={prefix+'_BASE_URL':base,prefix+'_MODEL':model}
    if key is not None: changes[prefix+'_API_KEY']=key
    if data.clear_key: changes[prefix+'_API_KEY']=''
    # Preserve unrelated entries and comments, including other model channels.
    kept=''.join(item.original.string for item in parse_stream(io.StringIO(raw)) if item.key not in changes)
    def quote(value): return "'"+value.replace('\\','\\\\').replace("'","\\'")+"'"
    updated=kept.rstrip('\r\n')+'\n'+''.join(f'{name}={quote(value)}\n' for name,value in changes.items())
    path=config_path(user)
    temporary=None
    try:
        with tempfile.NamedTemporaryFile(mode='w',encoding='utf-8',dir=path.parent,prefix='.env-',delete=False) as file:
            temporary=Path(file.name)
            file.write(updated);file.flush();os.fsync(file.fileno())
        os.replace(temporary,path)
        if data.permission is not None: owner.permission=data.permission
        db.commit()
    except OSError: raise HTTPException(503,'保存失败，请检查用户目录权限；原配置未主动清空') from None
    finally:
        if temporary and temporary.exists(): temporary.unlink()
    return view(user,db)

def model_config(user,channel='chat'):
    _,values=read_file(user)
    prefix=channel.upper()
    key=values.get(prefix+'_API_KEY') or ''
    base=values.get(prefix+'_BASE_URL') or ''
    model=values.get(prefix+'_MODEL') or ''
    if not all([key,base,model]): raise HTTPException(422,'请先在设置中填写该模型的 API Key、接口地址和模型名称')
    return {'key':key,'base_url':validate_url(base),'model':model}
