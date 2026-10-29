"""Atomic chapter commands, revision snapshots and retry receipts in the same transaction."""
import copy,uuid
from common.errors import BusinessError
from ..models import ChapterRecord,CourseRevision,utcnow
from ..repositories import courses as repository
from .courses import owned,chapters_for,snapshot,public
from .changes import record_change
from .activities import fingerprint

def outline(db,user,cid):
    course=owned(db,cid,user.id)
    chapters=chapters_for(db,course)
    return {'course_version':course.version,'chapters':[{'id':c.id,'title':c.title,'description':c.description,'read':c.read,'archived':c.archived} for c in chapters]}

def read_chapter(db,user,cid,chapter_id):
    course=owned(db,cid,user.id)
    chapter=next((c for c in chapters_for(db,course) if c.id==str(chapter_id)),None)
    if not chapter: raise BusinessError(404,'章节不存在或不属于本课程')
    return {'course_version':course.version,'chapter':{'id':chapter.id,'title':chapter.title,'description':chapter.description,'content':chapter.content,'read':chapter.read,'archived':chapter.archived}}

def plan(course,rows,data):
    if course.archived: raise BusinessError(409,'课程已归档，不能由AI修改章节')
    if course.version!=data.expected_version: raise BusinessError(409,'课程已经变化，请重新读取后生成修改方案')
    before=snapshot(course,rows);after=copy.deepcopy(before);items=after['chapters'];details=[]
    for index,op in enumerate(data.operations):
        old=copy.deepcopy(items)
        ch=next((c for c in items if c['id']==str(op.chapter_id)),None)
        if op.action!='add':
            if not ch: raise BusinessError(422,'只能修改本课程现有章节')
            if ch['read']: raise BusinessError(422,'AI不能修改或移出已完成章节，请由用户手动操作')
        if op.action=='add':
            if len(items)>=100: raise BusinessError(422,'本课程章节已达100个上限（含已移出章节）')
            ch={'id':str(uuid.uuid5(data.id,str(index))),'title':op.title.strip(),'description':op.description or '',
                'content':op.content or '', 'read':False,'archived':False,'source':'ai'}
            items.append(ch)
        elif op.action=='update':
            if ch['archived']: raise BusinessError(422,'请先恢复章节再编辑')
            for key in ('title','description','content'):
                value=getattr(op,key)
                if value is not None: ch[key]=value.strip() if key=='title' else value
        elif op.action=='archive': ch['archived']=True
        elif op.action=='restore': ch['archived']=False
        if op.action=='move' or (op.action=='add' and 'after_id' in op.model_fields_set):
            if ch['archived']: raise BusinessError(422,'不能移动已移出章节')
            anchor=next((c for c in items if c['id']==str(op.after_id) and not c['archived']),None) if op.after_id else None
            if op.after_id and (not anchor or anchor is ch): raise BusinessError(422,'移动位置必须是本课程其他有效章节')
            items.remove(ch);items.insert(items.index(anchor)+1 if anchor else 0,ch)
        if old!=items:
            previous=next((c for c in old if c['id']==ch['id']),None)
            details.append({'action':op.action,'title':ch['title'],'before':previous,'after':copy.deepcopy(ch),
                'after_title': next((c['title'] for c in items if c['id']==str(op.after_id)),None) if op.after_id else None})
    if before['chapters']==items: raise BusinessError(422,'修改方案没有改变章节')
    if after['currentChapterId'] and not any(c['id']==after['currentChapterId'] and not c['archived'] for c in items):
        after['currentChapterId']=None
    return after,details

def preview(db,user,cid,data):
    course=owned(db,cid,user.id)
    after,details=plan(course,chapters_for(db,course),data)
    return {'expected_version':course.version,'changes':details,'route_titles':[c['title'] for c in after['chapters'] if not c['archived']]}

def apply(db,user,cid,data):
    course=owned(db,cid,user.id,lock=True)
    signature=fingerprint(data.model_dump(mode='json',exclude_unset=True))
    # Revision ID is also the operation receipt. Retry before version check because a successful write increments it.
    existing=db.get(CourseRevision,str(data.id))
    if existing:
        receipt=existing.snapshot.get('operation',{})
        if existing.course_id!=course.id or receipt.get('hash')!=signature: raise BusinessError(409,'修改标识已使用')
        db.commit();return {'id':str(data.id),'applied_version':existing.version,'course_version':course.version}
    rows=chapters_for(db,course,lock=True)
    after,details=plan(course,rows,data);old={c.id:c for c in rows};updated=[]
    for position,ch in enumerate(after['chapters']):
        item=old.get(ch['id'])
        if item is None:
            if repository.find_existing_chapter_id(db,[ch['id']]): raise BusinessError(409,'新增章节标识冲突')
            item=ChapterRecord(id=ch['id'],course_id=course.id);repository.add(db,item)
        if ch['archived'] and not item.archived:
            from .recycle import detach
            detach(db,course.id,item.id)
        for key in ('title','description','content','read','archived','source'): setattr(item,key,ch[key])
        item.position=position;updated.append(item)
    course.current_chapter_id=after['currentChapterId'];course.version+=1;course.updated_at=utcnow()
    revision=snapshot(course,updated)
    revision.update(actor='ai',operation={'hash':signature,'summary':data.summary,'changes':details})
    summary='AI调整章节：'+data.summary
    record_change(db,course,'chapters.ai_updated',data.id,summary)
    repository.add(db,CourseRevision(id=str(data.id),course_id=course.id,version=course.version,summary=summary,snapshot=revision))
    db.commit()
    return {'id':str(data.id),'applied_version':course.version,'course_version':course.version}
