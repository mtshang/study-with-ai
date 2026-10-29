import {useContext,useEffect,useRef,useState} from 'react';
import {ServerContext} from '../serverWorkspace';
import {accountRequest} from '../api';
import type {Course} from '../types';
import {Modal,PageTitle,Empty} from '../components/ui';
export type TrashKind='chapter'|'exercise'|'assignment';
type Item={id:string;title:string;description?:string;content?:string;read?:boolean;questions?:{prompt:string}[]};
type Data={version:number;items:Item[]};
type Action='archive'|'restore'|'delete'|'clear';
export function TrashPage({course,kind}:{course:Course;kind:TrashKind}){
  const server=useContext(ServerContext),[data,setData]=useState<Data|null>(null),[error,setError]=useState(''),[busy,setBusy]=useState(false);
  const [confirm,setConfirm]=useState<{id:string;action:Action;items:Item[];version:number}|null>(null),[select,setSelect]=useState('');
  const alive=useRef(true),sequence=useRef(0);
  const label={chapter:'章节',exercise:'练习',assignment:'作业'}[kind];
  const available:Item[]=kind==='chapter'?course.chapters.filter(c=>!c.archived):kind==='exercise'?course.exercises.map(q=>({id:q.id,title:q.prompt})):course.assignments;
  async function load(){
    if(!server.userId)return;const token=++sequence.current;
    try{const next=await accountRequest<Data>(`/courses/${course.id}/trash/${kind}`,undefined,AbortSignal.timeout(15000),{headers:{'X-Workspace-User':server.userId}});if(alive.current&&token===sequence.current){setData(next);setError('');}}
    catch(e){if(alive.current&&token===sequence.current)setError(e instanceof Error?e.message:'读取失败');}
  }
  useEffect(()=>{alive.current=true;void load();return()=>{alive.current=false;sequence.current++;};},[server.userId,course.id,kind,course.version]);
  function propose(action:Action,items:Item[]){if(!data||busy)return;setConfirm({id:crypto.randomUUID(),action,items,version:data.version});}
  async function execute(){
    if(!confirm||!server.userId||busy)return;setBusy(true);setError('');
    try{await accountRequest(`/courses/${course.id}/trash-actions`,{id:confirm.id,expected_version:confirm.version,kind,action:confirm.action,target_ids:confirm.items.map(i=>i.id)},AbortSignal.timeout(20000),{headers:{'X-Workspace-User':server.userId}});
      if(alive.current){setConfirm(null);setSelect('');await load();server.reload();}}
    catch(e){if(alive.current)setError(e instanceof Error?e.message:'操作失败');}
    finally{if(alive.current)setBusy(false);}
  }
  if(!server.active)return <Empty title="请先登录使用回收站" description="回收站操作保存到账号，不作用于本地演示数据。"/>;
  return <><PageTitle title={`${label}回收站`} eyebrow="RECYCLE BIN" description="移入后可以恢复；永久删除或清空只由你操作，已有学习历史继续保留。" action={<button className="button" disabled={busy||!data?.items.length} onClick={()=>propose('clear',data!.items)}>一键清空</button>}/>
    {error&&<p role="alert">{error} <button className="text-link" disabled={busy} onClick={()=>{setConfirm(null);void load();server.reload();}}>重新读取</button></p>}
    <section className="panel"><label className="field">选择要移入回收站的{label}<select aria-label={`选择${label}`} value={select} onChange={e=>setSelect(e.target.value)}><option value="">请选择</option>{available.map(i=><option key={i.id} value={i.id}>{i.title}{i.read?'（已完成，仅你可移出）':''}</option>)}</select></label><button className="button" disabled={!select||!data||busy} onClick={()=>{const item=available.find(i=>i.id===select);if(item)propose('archive',[item]);}}>移入回收站</button></section>
    {!data?<p role="status">正在读取回收站…</p>:!data.items.length?<Empty title="回收站为空" description="已移出的内容会显示在这里。"/>:<div className="recycle-list">{data.items.map(item=><section className="panel" key={item.id}><h2>{item.title}</h2>{item.read&&<p>已完成章节 · AI不能修改或移出</p>}<p>{item.description}</p><details><summary>查看内容</summary><p className="preserve-text">{item.content}</p>{item.questions?.map((q,i)=><p key={i}>{i+1}. {q.prompt}</p>)}</details><div className="button-row"><button className="button" disabled={busy} onClick={()=>propose('restore',[item])}>恢复</button><button className="button" disabled={busy} onClick={()=>propose('delete',[item])}>永久删除</button></div></section>)}</div>}
    {confirm&&<Modal title={confirm.action==='clear'?'确认清空回收站？':confirm.action==='delete'?'确认永久删除？':confirm.action==='archive'?'确认移入回收站？':'确认恢复？'} onClose={()=>{if(!busy)setConfirm(null);}}>
      <p>本次处理 {confirm.items.length} 项：{confirm.items.map(i=>i.title).join('、')}</p>
      <p>{confirm.action==='delete'||confirm.action==='clear'?'当前内容将无法从回收站恢复；历史版本、已提交答案和批改结果仍保留，并标记原对象已删除。':kind==='chapter'?'章节正文随章节保存，关联作业和练习转为未分类；恢复时不自动重新关联。':'已有提交和批改记录保留。'}</p>
      {error&&<p role="alert">{error}</p>}
      <div className="modal-actions"><button className="button" disabled={busy} onClick={()=>setConfirm(null)}>取消</button><button className="button primary" disabled={busy} onClick={()=>void execute()}>{busy?'处理中…':'确认操作'}</button></div>
    </Modal>}
  </>;
}
