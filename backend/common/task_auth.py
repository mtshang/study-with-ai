"""Internal, revocable task capability; never a browser login credential."""
import base64,hashlib,hmac,json,secrets,uuid
from fastapi import HTTPException,Request
from common import config
PREFIX='task-grant:'
def encode(claims):
    if not config.SERVICE_KEY:raise HTTPException(503,'服务身份未配置')
    body=base64.urlsafe_b64encode(json.dumps(claims,separators=(',',':')).encode()).decode()
    return body+'.'+hmac.new(config.SERVICE_KEY.encode(),body.encode(),hashlib.sha256).hexdigest()
def decode(token):
    try:
        if not config.SERVICE_KEY or len(token)>3000:raise ValueError()
        body,sig=token.split('.')
        expected=hmac.new(config.SERVICE_KEY.encode(),body.encode(),hashlib.sha256).hexdigest()
        if not secrets.compare_digest(expected,sig):raise ValueError()
        data=json.loads(base64.urlsafe_b64decode(body))
        if set(data)!={'session','owner','course','task','v'} or data['v']!=1:raise ValueError()
        for field in ('owner','course','task'):uuid.UUID(data[field])
        if len(data['session'])!=64 or any(c not in '0123456789abcdef' for c in data['session']):raise ValueError()
        return data
    except (ValueError,TypeError,KeyError):raise HTTPException(401,'后台任务授权无效') from None
def require_service(request:Request):
    if not config.SERVICE_KEY or not secrets.compare_digest(request.headers.get('x-service-key',''),config.SERVICE_KEY):
        raise HTTPException(403,'内部服务身份无效')
def headers(credential,owner,origin=''):
    result={'x-workspace-user':owner,'origin':origin,'cookie':''}
    if credential.startswith(PREFIX):
        result.update({'x-task-grant':credential[len(PREFIX):],'x-service-key':config.SERVICE_KEY})
    else:result['cookie']=credential
    return result


def permit_path(method,path):
    import re
    match=re.fullmatch(r'/api/courses/[0-9a-fA-F-]{36}(/.*)',path)
    tail=match.group(1) if match else ''
    reads=(r'/context',r'/changes',r'/outline',r'/chapters/[0-9a-fA-F-]{36}',r'/teaching-activities',r'/code-runs/[0-9a-fA-F-]{36}',r'/reading-materials',r'/materials/[0-9a-fA-F-]{36}/text',r'/materials/[0-9a-fA-F-]{36}/index-text',r'/materials/[0-9a-fA-F-]{36}/download',r'/submissions/[0-9a-fA-F-]{36}/grading/input')
    writes={'POST':(r'/activities',r'/chapter-changes/preview',r'/chapter-changes',r'/ai-trash-preview',r'/ai-trash-actions'),
            'PUT':(r'/submissions/[0-9a-fA-F-]{36}/grading(?:/items/[0-9a-fA-F-]{36})?',)}
    patterns=reads if method=='GET' else writes.get(method,())
    if not any(re.fullmatch(pattern,tail) for pattern in patterns):
        raise HTTPException(403,'后台授权不能访问此接口')
