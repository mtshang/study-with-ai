import {useEffect, useRef, useState} from 'react';
import {accountRequest} from '../api';
import {PageTitle, Empty, formatTime} from '../components/ui';

type Artifact={id:string;name:string;size:number;sha256:string};
type Run={id:string;task_id:string|null;role:string;title:string;status:string;created_at:string;error:string;
  request:{code:string;script:string|null;arguments:string[]};
  sources:{kind:string;name:string;sha256:string;script_preview?:string}[];
  result:{stdout?:string;stderr?:string;duration_ms?:number;exit_code?:number|null;files?:Artifact[]}};
const labels:Record<string,string>={pending:'待批准',ready:'等待执行',running:'执行中',completed:'已完成',runtime_error:'运行失败',timeout:'运行超时',interrupted:'执行中断',rejected:'已拒绝'};

export function GeneratedArtifacts({courseId,userId}:{courseId:string;userId:string|null}){
 const [rows,setRows]=useState<Run[]>([]),[error,setError]=useState(''),[loading,setLoading]=useState(true),[busy,setBusy]=useState('');
 const alive=useRef(true),fetching=useRef(false);
 const base=`/ai/courses/${courseId}`;
 const headers={'X-Workspace-User':userId||''};
 async function load(){
  if(!userId||fetching.current)return;
  fetching.current=true;
  try{const data=await accountRequest<Run[]>(base+'/sandbox-runs',undefined,undefined,{headers});if(alive.current){setRows(data);setError('');}}
  catch(e){if(alive.current)setError((e as Error).message);}
  finally{fetching.current=false;if(alive.current)setLoading(false);}
 }
 useEffect(()=>{alive.current=true;void load();const timer=setInterval(()=>void load(),4000);return()=>{alive.current=false;clearInterval(timer);};},[courseId,userId]);
 async function act(id:string,action:string,approve?:boolean){
  setBusy(id);setError('');
  try{await accountRequest(base+`/sandbox-runs/${id}/${action}`,action==='decision'?{approve}:{},undefined,{headers});await load();}
  catch(e){if(alive.current)setError((e as Error).message);}
  finally{if(alive.current)setBusy('');}
 }
 async function download(file:Artifact){
  setBusy(file.id);
  try{const blob=await accountRequest<Blob>(base+`/artifacts/${file.id}/download`,undefined,undefined,{headers,responseType:'blob'});if(!alive.current)return;
   const url=URL.createObjectURL(blob),link=document.createElement('a');link.href=url;link.download=file.name.split('/').pop()||'artifact';link.click();setTimeout(()=>URL.revokeObjectURL(url),1000);
  }catch(e){if(alive.current)setError((e as Error).message);}finally{if(alive.current)setBusy('');}
 }
 return <section className="artifacts-page"><PageTitle title="生成产物" description="教师与助教生成的文件，按执行任务保存。"/>
 {!userId?<Empty title="登录后查看生成产物" description="产物保存在各自课程内，与其他课程隔离。"/>:<>
 <div className="button-row"><button className="button" disabled={!!busy} onClick={()=>void load()}>刷新记录</button><span className="fine-print">文件不会自动发布为章节、资料或作业。</span></div>
 {error&&<p role="alert" className="error-message">{error}</p>}
 {loading?<p role="status">正在读取执行记录…</p>:!rows.length?<Empty title="还没有生成产物" description="可请 AI 导师计算、生成文件，或执行已启用技能的 Python 脚本。"/>:rows.map(row=><article className="artifact-run" key={row.id}>
  <header><div><span className="eyebrow">{row.role==='assistant'?'助教':'教师'} · {labels[row.status]||row.status}</span><h3>{row.title}</h3></div><time>{formatTime(row.created_at)}</time></header>
  <p className="fine-print">执行 {row.id}{row.task_id&&<> · 所属任务 {row.task_id}</>}</p>
  {row.status==='pending'&&<p>此执行需要你批准。请先查看代码、输入文件和参数。</p>}
  <details open={row.status==='pending'}><summary>执行内容与输入文件</summary>
   <p>Python 标准库 · 禁网 · 临时环境 · 不安装依赖</p>
   {row.request.script?<p>技能脚本：<code>{row.request.script}</code>　参数：<code>{JSON.stringify(row.request.arguments)}</code></p>:<pre>{row.request.code}</pre>}
   {row.sources.length?<ul>{row.sources.map((s,i)=><li key={i}>{s.kind==='skill'?'技能':s.kind==='material'?'课程资料':'已有产物'}：{s.name}<small> SHA-256 {s.sha256}</small>{s.script_preview&&<pre>{s.script_preview}</pre>}</li>)}</ul>:<p>无输入文件。</p>}
  </details>
  {row.error&&<p role="status">{row.error}</p>}
  {(row.result.stdout||row.result.stderr)&&<details><summary>运行输出</summary><pre>{row.result.stdout||'（无标准输出）'}{row.result.stderr&&'\n'+row.result.stderr}</pre></details>}
  {!!row.result.files?.length&&<ul className="artifact-files">{row.result.files.map(file=><li key={file.id}><span><span>{file.name}</span><small>{(file.size/1024).toFixed(1)} KB</small></span><button className="button" disabled={!!busy} onClick={()=>void download(file)}>下载</button></li>)}</ul>}
  {row.status==='completed'&&!row.result.files?.length&&<p>执行已完成，没有生成文件。</p>}
  <div className="button-row">{row.status==='pending'&&<><button className="button primary" disabled={!!busy} onClick={()=>void act(row.id,'decision',true)}>批准本次执行</button><button className="button" disabled={!!busy} onClick={()=>void act(row.id,'decision',false)}>拒绝</button></>}
  {['interrupted','ready'].includes(row.status)&&<button className="button" disabled={!!busy} onClick={()=>void act(row.id,'continue')}>继续原执行</button>}</div>
 </article>)}
 {rows.length===100&&<p className="fine-print">当前展示最近 100 次执行。</p>}
 </>}
 </section>;
}
