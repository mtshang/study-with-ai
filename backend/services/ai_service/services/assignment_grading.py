"""One bounded assistant per submission; sequential questions, durable per-question delivery."""
import asyncio,copy,json
from fastapi import HTTPException
from pydantic import ValidationError
from ..clients import grading as learning
from ..infrastructure.database import SessionLocal
from ..models import AssistantTask,utcnow
from . import assistants,recovery

def error_text(exc):
    if isinstance(exc,HTTPException): return str(exc.detail)[:300]
    if isinstance(exc,(ValidationError,ValueError,TypeError)): return '本题模型输出未通过校验，请重试'
    return '本题批改异常，请重试；已完成结果保留'

async def execute(user,cid,sid,aid,source,cookie,origin,config,cached):
    from .grading import evaluate
    outputs=copy.deepcopy((cached or {}).get('items',{}))
    failure='';interrupted=False
    async def call(payload=None,qid=None):
        return await learning.call(user,cid,sid,cookie,origin,payload,question_id=qid)
    async def failed(qid,message):
        try: await call({'input_hash':source['input_hash'],'status':'failed','error':message},qid)
        except Exception: pass
    try:
        async with asyncio.timeout(300):
            async with assistants.slots:
                with SessionLocal.begin() as db:
                    recovery.guard_current(db)
                    db.get(AssistantTask,aid).status='running'
                latest=await call()
                if latest['input_hash']!=source['input_hash']: raise HTTPException(409,'批改输入版本不匹配')
                completed={i['question_id'] for i in latest['items'] if i['status']=='completed'}
                for question in source['input']['questions']:
                    qid=question['question_id']
                    if qid in completed: continue
                    try:
                        output=outputs.get(qid)
                        if not output:
                            await call({'input_hash':source['input_hash'],'status':'running'},qid)
                            output=await evaluate(config,question,source['input_hash'])
                            outputs[qid]=output
                            with SessionLocal.begin() as db:
                                recovery.guard_current(db)
                                db.get(AssistantTask,aid).payload={'kind':'assignment','items':copy.deepcopy(outputs)}
                        await call(output,qid)
                    except Exception as exc:
                        await failed(qid,error_text(exc))
                        # Continue other questions; only unfinished ones are retried later.
                latest=await call()
                if latest['status']!='completed': raise HTTPException(503,'部分题目未完成，请重试未完成题；已完成结果保留')
        summary=json.dumps({'submission_id':sid,'assignment':source['input']['title'],
            'objective_results':source['input'].get('objective_results',[]),
            'items':[{'question_id':i['question_id'],'number':i['number'],'question':i['question'][:300],
                'mastery':i['result']['mastery'],'reason':i['result']['reason'][:300],
                'suggestions':[s[:150] for s in i['result']['suggestions'][:2]]} for i in latest['items']],
            'summary_is_abbreviated':True,'pending_attachment_count':source['input'].get('pending_attachment_count',0),
            'note':'本次作业的文字答案批改已保存。请结合客观题和开放题统一总结讲解；附件未评阅，不要宣称整份作业全部合格或自动发布新题。'},ensure_ascii=False)
        with SessionLocal.begin() as db:
            recovery.guard_current(db)
            row=db.get(AssistantTask,aid);row.status='completed';row.result=summary;row.error='';row.finished_at=utcnow()
        assistants.mirror(user,cid)
        if not assistants.closing: await assistants.wake(user,cid,cookie,origin)
        return
    except asyncio.CancelledError:
        failure='服务关闭，作业批改中断；请重试未完成题';interrupted=True
    except TimeoutError: failure='本轮批改超过五分钟，请重试未完成题；已有结果保留'
    except Exception as exc: failure=error_text(exc)
    # Completed question callbacks ignore late failure updates. No completed result is lost.
    try:
        remaining=await call()
        unfinished={i['question_id'] for i in remaining['items'] if i['status'] in ('waiting','running')}
    except Exception: unfinished={q['question_id'] for q in source['input']['questions']}
    for q in source['input']['questions']:
        if q['question_id'] in unfinished: await failed(q['question_id'],failure)
    with SessionLocal.begin() as db:
        recovery.guard_current(db)
        row=db.get(AssistantTask,aid);row.status='interrupted' if interrupted else 'uncertain' if outputs else 'failed'
        row.error=failure;row.finished_at=utcnow()
