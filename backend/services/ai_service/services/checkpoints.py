"""MySQL saver for this application's JSON-only, single-namespace graph state.
Implements LangGraph's checkpoint and pending-write contract; no pickle.
"""
import json
from sqlalchemy import select
from langgraph.checkpoint.base import BaseCheckpointSaver,CheckpointTuple,WRITES_IDX_MAP
from ..models import GraphCheckpoint,GraphWrite
from ..infrastructure.database import SessionLocal

def plain(value):
    # Do not silently deserialize executable objects from stored state.
    return json.loads(json.dumps(value,ensure_ascii=False,allow_nan=False))

class MySQLSaver(BaseCheckpointSaver):
    def __init__(self,handle):
        super().__init__();self.handle=handle
    def scope(self,config):
        if config['configurable']['thread_id']!=self.handle.id or config['configurable'].get('checkpoint_ns',''):
            raise ValueError('Checkpoint scope mismatch')
    async def aget_tuple(self,config):
        self.scope(config)
        with SessionLocal() as db:
            query=select(GraphCheckpoint).where(GraphCheckpoint.job_id==self.handle.id)
            cid=config['configurable'].get('checkpoint_id')
            if cid:query=query.where(GraphCheckpoint.checkpoint_id==cid)
            row=db.scalar(query.order_by(GraphCheckpoint.checkpoint_id.desc()).limit(1))
            if not row:return None
            data=row.data;cfg={'configurable':{'thread_id':self.handle.id,'checkpoint_ns':'','checkpoint_id':row.checkpoint_id}}
            writes=db.scalars(select(GraphWrite).where(GraphWrite.job_id==self.handle.id,GraphWrite.checkpoint_id==row.checkpoint_id).order_by(GraphWrite.task_id,GraphWrite.idx))
            parent={'configurable':{**cfg['configurable'],'checkpoint_id':data['parent']}} if data['parent'] else None
            return CheckpointTuple(cfg,data['checkpoint'],data['metadata'],parent,[(w.task_id,w.channel,w.value['value']) for w in writes])
    async def aput(self,config,checkpoint,metadata,new_versions):
        self.scope(config)
        data=plain({'checkpoint':checkpoint,'metadata':metadata,'parent':config['configurable'].get('checkpoint_id')})
        with SessionLocal.begin() as db:
            self.handle.guard(db)
            db.merge(GraphCheckpoint(job_id=self.handle.id,checkpoint_id=checkpoint['id'],data=data))
        return {'configurable':{'thread_id':self.handle.id,'checkpoint_ns':'','checkpoint_id':checkpoint['id']}}
    async def aput_writes(self,config,writes,task_id,task_path=''):
        self.scope(config)
        with SessionLocal.begin() as db:
            self.handle.guard(db)
            for i,(channel,value) in enumerate(writes):
                idx=WRITES_IDX_MAP.get(channel,i);key=(self.handle.id,config['configurable']['checkpoint_id'],task_id,idx)
                row=db.get(GraphWrite,key)
                if row and idx>=0:continue
                db.merge(GraphWrite(job_id=key[0],checkpoint_id=key[1],task_id=task_id,idx=idx,channel=channel,value=plain({'value':value})))
    async def alist(self,config,*,filter=None,before=None,limit=None):
        if config is None:raise ValueError('Explicit job scope required')
        self.scope(config)
        with SessionLocal() as db:
            q=select(GraphCheckpoint.checkpoint_id).where(GraphCheckpoint.job_id==self.handle.id)
            if before:q=q.where(GraphCheckpoint.checkpoint_id<before['configurable']['checkpoint_id'])
            ids=list(db.scalars(q.order_by(GraphCheckpoint.checkpoint_id.desc())))
        count=0
        for cid in ids:
            item=await self.aget_tuple({'configurable':{**config['configurable'],'checkpoint_id':cid}})
            if filter and any(item.metadata.get(k)!=v for k,v in filter.items()):continue
            if limit is not None and count>=limit:return
            yield item;count+=1
