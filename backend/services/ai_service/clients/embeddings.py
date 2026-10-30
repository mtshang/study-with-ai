"""Bounded OpenAI-compatible embeddings; credentials never enter task receipts."""
import json,math
from urllib.parse import urlsplit
import httpx
from fastapi import HTTPException
from ..services.configuration import validate_url

from .model_network import ModelTransport as PublicTransport

def validate_vectors(body,count):
    rows=body['data']
    if len(rows)!=count or sorted(r['index'] for r in rows)!=list(range(count)):raise ValueError('Invalid indices')
    vectors=[r['embedding'] for r in sorted(rows,key=lambda r:r['index'])]
    size=len(vectors[0])
    if not 1<=size<=8192:raise ValueError('Invalid dimension')
    for vector in vectors:
        if len(vector)!=size or any(isinstance(x,bool) or not isinstance(x,(int,float)) or not math.isfinite(x) for x in vector):raise ValueError('Invalid vector')
        if not any(x!=0 for x in vector):raise ValueError('Zero vector')
    return vectors

def protocol(endpoint):
    url=urlsplit(endpoint)
    return 'ark_multimodal' if url.hostname=='ark.cn-beijing.volces.com' and url.path=='/api/v3/embeddings/multimodal' else 'standard'

async def embed(config,texts):
    if not 1<=len(texts)<=16 or any(not t.strip() or len(t)>3000 for t in texts):
        raise HTTPException(422,'向量化每批最多16段，每段最多3000字符')
    endpoint=validate_url(config['base_url'])
    mode=protocol(endpoint)
    # Ark combines input items into ONE embedding; send each text independently.
    batches=[[text] for text in texts] if mode=='ark_multimodal' else [texts]
    vectors=[]
    try:
        async with httpx.AsyncClient(transport=PublicTransport(endpoint,base_url=endpoint,trusted_url=config.get('trusted_url','')),trust_env=False,follow_redirects=False,timeout=60) as client:
            for batch in batches:
                inputs=[{'type':'text','text':batch[0]}] if mode=='ark_multimodal' else batch
                async with client.stream('POST',endpoint,headers={'Authorization':'Bearer '+config['key'],'Accept-Encoding':'identity'},
                    json={'model':config['model'],'input':inputs,'encoding_format':'float'}) as response:
                    if response.status_code!=200:raise HTTPException(502,f'Embedding 接口返回 HTTP {response.status_code}，请检查完整URL、模型、Key和额度')
                    body=bytearray()
                    async for part in response.aiter_bytes():
                        body.extend(part)
                        if len(body)>4*1024*1024:raise ValueError('Response too large')
                result=json.loads(body)
                if mode=='ark_multimodal':result={'data':[{'index':0,'embedding':result['data']['embedding']}]}
                vectors.extend(validate_vectors(result,len(batch)))
        return validate_vectors({'data':[{'index':i,'embedding':v} for i,v in enumerate(vectors)]},len(texts))
    except (httpx.HTTPError,OSError,ValueError,KeyError,TypeError,IndexError,OverflowError):
        raise HTTPException(502,'Embedding 连接失败或返回向量格式不正确') from None
