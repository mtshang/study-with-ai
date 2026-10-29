import {useEffect,useState} from 'react';
import {aiRequest} from '../ai';
type Persona={version:number;prompt:string;source_revision?:number};
export function PersonaSettings({userId,courseId}:{userId:string;courseId?:string}){
 const path=courseId?'/courses/'+courseId+'/persona':'/persona';
 const [saved,setSaved]=useState<Persona|null>(null),[draft,setDraft]=useState(''),[busy,setBusy]=useState(false),[message,setMessage]=useState('');
 useEffect(()=>{const abort=new AbortController();setSaved(null);setDraft('');setMessage('');
  aiRequest<Persona>(userId,path,undefined,undefined,abort.signal).then(v=>{if(!abort.signal.aborted){setSaved(v);setDraft(v.prompt);}}).catch(e=>{if(!abort.signal.aborted)setMessage(e.message);});
  return()=>abort.abort();
 },[userId,path]);
 async function action(kind:'save'|'reload'|'default'){
  setBusy(true);setMessage('');
  try{
   if(kind==='default'){const v=await aiRequest<Persona>(userId,'/persona');setDraft(v.prompt);setMessage('已填入全局默认，保存后应用于本课程。');return;}
   const v=kind==='save'?await aiRequest<Persona>(userId,path,{version:saved!.version,prompt:draft},'PUT'):await aiRequest<Persona>(userId,path);
   setSaved(v);setDraft(v.prompt);setMessage(kind==='save'?'人格提示词已保存，下一次模型调用时生效。':'已重新读取。');
  }catch(e){setMessage(e instanceof Error?e.message:'操作失败');}finally{setBusy(false);}
 }
 return <section className="panel settings-panel persona-settings" aria-label={courseId?'课程人格':'默认人格'}>
  <h3>{courseId?'课程人格提示词':'默认人格提示词'}</h3>
  <p className="muted">{courseId?'只影响本课程，可独立设置教学语气和风格。':'新课程继承创建时的默认版本，修改这里不会覆盖已有课程。'}</p>
  {saved&&<form onSubmit={e=>{e.preventDefault();void action('save');}}><fieldset disabled={busy} className="settings-fields">
   <label>{courseId?'课程人格内容':'默认人格内容'}<textarea aria-label={courseId?'课程人格内容':'默认人格内容'} value={draft} onChange={e=>setDraft(e.target.value)} maxLength={3000} rows={5}/></label>
   <div className="button-row"><button className="button primary" disabled={!draft.trim()||draft===saved.prompt}>保存人格</button>
   {courseId&&<button className="button" type="button" onClick={()=>void action('default')}>采用当前全局默认</button>}</div>
  </fieldset></form>}
  <button type="button" className="text-link" disabled={busy} onClick={()=>void action('reload')}>重新读取人格</button>
  <p className="fine-print">人格不改变操作权限。课程记忆由 AI 内部维护。</p><p role="status">{busy?'正在处理…':message}</p>
 </section>;
}
