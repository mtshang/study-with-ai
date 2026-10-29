"""User-only irreversible removal; original learning evidence lives in immutable snapshots."""
from sqlalchemy import select
from common.errors import BusinessError
from ..models import ChapterRecord,ActivityRecord,CourseRevision,utcnow
from .courses import owned,chapters_for,snapshot
from .activities import fingerprint
from .changes import record_change

def detach(db,cid,chapter_id):
    for activity in db.scalars(select(ActivityRecord).where(ActivityRecord.course_id==cid,ActivityRecord.chapter_id==chapter_id).with_for_update()):
        activity.chapter_id=None

def listing(db,user,cid,kind):
    course=owned(db,cid,user.id)
    if kind=='chapter':
        rows=db.scalars(select(ChapterRecord).where(ChapterRecord.course_id==course.id,ChapterRecord.archived==True,ChapterRecord.deleted==False).order_by(ChapterRecord.position))
        items=[{'id':c.id,'title':c.title,'description':c.description,'content':c.content,'read':c.read} for c in rows]
    else:
        rows=db.scalars(select(ActivityRecord).where(ActivityRecord.course_id==course.id,ActivityRecord.kind==kind,ActivityRecord.trash_state=='trash').order_by(ActivityRecord.created_at))
        items=[{'id':a.id,'title':a.title,'description':a.description,'questions':[{'prompt':q['prompt']} for q in a.questions]} for a in rows]
    return {'version':course.version,'items':items}

def activity_catalog(db,user,cid):
    course=owned(db,cid,user.id)
    rows=db.scalars(select(ActivityRecord).where(ActivityRecord.course_id==course.id,ActivityRecord.trash_state=='active').order_by(ActivityRecord.created_at))
    return {'course_version':course.version,'activities':[{'id':a.id,'kind':a.kind,'title':a.title,'chapter_id':a.chapter_id} for a in rows]}

def validate(db,course,data,actor):
    if actor=='ai' and data.action!='archive': raise BusinessError(403,'AI只能移入回收站，不能恢复或永久删除')
    if course.version!=data.expected_version: raise BusinessError(409,'课程已变化，请重新读取回收站或重新生成方案')
    if actor=='ai' and course.archived: raise BusinessError(409,'课程已归档')
    model=ChapterRecord if data.kind=='chapter' else ActivityRecord
    rows=list(db.scalars(select(model).where(model.course_id==course.id,model.id.in_([str(i) for i in data.target_ids])).with_for_update()))
    if len(rows)!=len(data.target_ids): raise BusinessError(404,'对象不存在或不属于本课程')
    for row in rows:
        state=('deleted' if row.deleted else 'trash' if row.archived else 'active') if data.kind=='chapter' else row.trash_state
        if data.kind!='chapter' and row.kind!=data.kind: raise BusinessError(422,'对象类型不匹配')
        if state!=('active' if data.action=='archive' else 'trash'): raise BusinessError(409,'对象状态已经变化，请重新读取')
        if actor=='ai' and data.kind=='chapter' and row.read: raise BusinessError(422,'AI不能移出已完成章节')
    return rows

def preview(db,user,cid,data):
    course=owned(db,cid,user.id,lock=True);rows=validate(db,course,data,'ai')
    return {'titles':[r.title for r in rows],'expected_version':course.version}

def apply(db,user,cid,data,actor='user'):
    course=owned(db,cid,user.id,lock=True)
    if actor=='ai' and data.action!='archive': raise BusinessError(403,'AI没有永久删除权限')
    signature=fingerprint({'actor':actor,**data.model_dump(mode='json')})
    existing=db.get(CourseRevision,str(data.id))
    if existing:
        if existing.course_id!=course.id or existing.snapshot.get('operation',{}).get('hash')!=signature: raise BusinessError(409,'操作标识已使用')
        db.commit();return {'id':str(data.id),'version':course.version,'applied_version':existing.version}
    rows=validate(db,course,data,actor);evidence=[]
    for row in rows:
        if data.kind=='chapter':
            evidence.append({'kind':'chapter','id':row.id,'title':row.title,'description':row.description,'content':row.content,'read':row.read})
            if data.action=='restore': row.archived=False
            else:
                detach(db,course.id,row.id);row.archived=True
                if course.current_chapter_id==row.id: course.current_chapter_id=None
                if data.action in ('delete','clear'):
                    row.deleted=True;row.title='已删除章节';row.description='';row.content=''
        else:
            evidence.append({'kind':row.kind,'id':row.id,'title':row.title,'description':row.description,'questions':row.questions})
            row.trash_state='trash' if data.action=='archive' else 'active' if data.action=='restore' else 'deleted'
            if data.action in ('delete','clear'):
                row.title='已删除'+('练习' if row.kind=='exercise' else '作业');row.description='';row.questions=[];row.chapter_id=None
    db.flush()
    course.version+=1;course.updated_at=utcnow()
    action={'archive':'移入回收站','restore':'恢复','delete':'永久删除','clear':'清空回收站'}[data.action]
    summary=('AI' if actor=='ai' else '用户')+action+f'（{len(rows)}项）'
    saved=snapshot(course,chapters_for(db,course))
    saved.update(actor=actor,operation={'hash':signature,'kind':data.kind,'action':data.action,'targets':[str(i) for i in data.target_ids]},historical_items=evidence)
    db.add(CourseRevision(id=str(data.id),course_id=course.id,version=course.version,summary=summary,snapshot=saved))
    record_change(db,course,'recycle.'+data.action,data.id,summary)
    db.commit();return {'id':str(data.id),'version':course.version,'applied_version':course.version}
