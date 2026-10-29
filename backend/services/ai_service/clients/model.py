"""OpenAI-compatible Chat Completions transport; credentials never enter errors/logs."""
import asyncio, base64, ipaddress, json, socket, struct, zlib
from urllib.parse import urlsplit
import httpx
from fastapi import HTTPException

async def check_destination(base):
    host=urlsplit(base).hostname
    try:
        addresses=await asyncio.get_running_loop().getaddrinfo(host,443,type=socket.SOCK_STREAM)
        def permitted(address):
            ip=ipaddress.ip_address(address)
            # Proxy Fake-IP for this explicit provider only; TLS verifies the original hostname.
            return ip.is_global or (host=='api.deepseek.com' and ((ip.version==4 and ip in ipaddress.ip_network('198.18.0.0/15')) or (ip.version==6 and ip in ipaddress.ip_network('2001:2::/48'))))
        if not addresses or any(not permitted(row[4][0]) for row in addresses):
            raise HTTPException(422,'模型接口不能指向本机、内网或保留地址')
    except socket.gaierror: raise HTTPException(502,'模型接口域名无法解析') from None

def request_body(config,messages,tools=None,stream=True,max_tokens=1600):
    body={'model':config['model'],'messages':messages,'stream':stream,'max_tokens':max_tokens}
    if urlsplit(config['base_url']).hostname=='api.deepseek.com': body['thinking']={'type':'disabled'}
    if tools: body['tools']=tools
    return body

def red_image():
    def chunk(tag,data): return struct.pack('!I',len(data))+tag+data+struct.pack('!I',zlib.crc32(tag+data)&0xffffffff)
    data=b'\x89PNG\r\n\x1a\n'+chunk(b'IHDR',struct.pack('!2I5B',32,32,8,2,0,0,0))+chunk(b'IDAT',zlib.compress((b'\0'+b'\xff\0\0'*32)*32))+chunk(b'IEND',b'')
    return 'data:image/png;base64,'+base64.b64encode(data).decode()

async def stream_reply(config,messages,tools,on_text):
    await check_destination(config['base_url'])
    payload=request_body(config,messages,tools)
    content='';calls={};total=0;finished=False
    try:
        async with httpx.AsyncClient(timeout=httpx.Timeout(45,connect=10),trust_env=False,follow_redirects=False) as client:
            async with client.stream('POST',config['base_url'].rstrip('/')+'/chat/completions',
                headers={'Authorization':'Bearer '+config['key']},json=payload) as response:
                if response.status_code!=200: raise HTTPException(502,f'模型接口返回 HTTP {response.status_code}，请检查 Key、模型名称、余额和接口地址')
                async for line in response.aiter_lines():
                    total+=len(line)
                    if total>2_000_000: raise HTTPException(502,'模型响应超出本轮限制')
                    if not line.startswith('data:'): continue
                    raw=line[5:].strip()
                    if raw=='[DONE]': break
                    item=json.loads(raw)
                    if item.get('error'): raise HTTPException(502,'模型返回流式错误，请核对配置后重试')
                    choices=item.get('choices') or []
                    if not choices: continue
                    choice=choices[0];delta=choice.get('delta') or {}
                    text=delta.get('content') or ''
                    if text:
                        content+=text
                        await on_text(content)
                    for part in delta.get('tool_calls') or []:
                        index=part['index']
                        if not isinstance(index,int) or index<0 or index>=4: raise HTTPException(502,'单轮工具调用过多')
                        call=calls.setdefault(index,{'id':'','type':'function','function':{'name':'','arguments':''}})
                        call['id']+=part.get('id') or ''
                        fn=part.get('function') or {}
                        call['function']['name']+=fn.get('name') or ''
                        call['function']['arguments']+=fn.get('arguments') or ''
                        if len(call['function']['arguments'])>20000: raise HTTPException(502,'工具参数过长')
                    if choice.get('finish_reason'):
                        if choice['finish_reason'] not in ('stop','tool_calls'): raise HTTPException(502,'模型输出未完整结束，请缩小本次请求')
                        finished=True
        if not finished: raise HTTPException(502,'模型连接中断，已收到的内容会保留')
        if not content and not calls: raise HTTPException(502,'模型未返回可用内容')
        message={'role':'assistant','content':content or None}
        if calls: message['tool_calls']=[calls[i] for i in sorted(calls)]
        return message
    except (httpx.HTTPError,json.JSONDecodeError,KeyError,TypeError,ValueError):
        raise HTTPException(502,'模型连接失败或返回格式异常，已收到的内容会保留') from None

async def test_connection(config,channel):
    await check_destination(config['base_url'])
    content='Reply only OK.' if channel=='chat' else [{'type':'text','text':'What is the main color? Reply in one word.'},{'type':'image_url','image_url':{'url':red_image()}}]
    try:
        async with httpx.AsyncClient(timeout=30,trust_env=False,follow_redirects=False) as client:
            response=await client.post(config['base_url'].rstrip('/')+'/chat/completions',headers={'Authorization':'Bearer '+config['key']},json=request_body(config,[{'role':'user','content':content}],stream=False,max_tokens=32))
        if response.status_code!=200: raise HTTPException(502,f'连接测试返回 HTTP {response.status_code}；请检查 Key、模型名称、能力与余额')
        text=response.json()['choices'][0]['message'].get('content')
        if not isinstance(text,str) or not text.strip(): raise ValueError()
        return {'ok':True,'channel':channel,'message':'模型已正常返回文字' if channel=='chat' else '模型已接收测试图片并返回文字'}
    except (httpx.HTTPError,ValueError,KeyError,IndexError,TypeError): raise HTTPException(502,'连接测试失败，未收到有效模型响应') from None
