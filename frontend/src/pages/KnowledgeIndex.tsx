import {useEffect,useState} from 'react';
import {aiRequest} from '../ai';
type Row={id:string;title:string;readable:boolean;index:null|{id:string;status:string;error:string;classification?:{format:string;category:string;notes:string[]};chunks:number;indexed_chunks:number}};
type Hit={title:string;text:string;citation:string;score:number};
const labels:Record<string,string>={queued:'排队中',running:'正在索引',completed:'可检索',stale:'资料或模型已变化',needs_attention:'需要重试',auth_required:'请重新登录后重试'};
export function KnowledgeIndex({userId,courseId}:{userId:string;courseId:string}){
 const [rows,setRows]=useState<Row[]>([]),[error,setError]=useState(''),[busy,setBusy]=useState(false);
 const [query,setQuery]=useState(''),[hits,setHits]=useState<Hit[]>([]),[notice,setNotice]=useState('');
 const path=`/courses/${courseId}/rag`;
 useEffect(()=>{const abort=new AbortController();let timer:ReturnType<typeof setTimeout>;
  async function poll(){try{const data=await aiRequest<Row[]>(userId,path,undefined,undefined,abort.signal);if(!abort.signal.aborted)setRows(data);}catch(e){if(!abort.signal.aborted)setError(e instanceof Error?e.message:'读取索引失败');}finally{if(!abort.signal.aborted)timer=setTimeout(()=>void poll(),3000);}}
  void poll();return()=>{abort.abort();clearTimeout(timer);};
 },[userId,path]);
 async function build(row:Row){setBusy(true);setError('');try{await aiRequest(userId,path+'/index',{id:crypto.randomUUID(),material_id:row.id});setRows(await aiRequest<Row[]>(userId,path));}catch(e){setError(e instanceof Error?e.message:'建立失败');}finally{setBusy(false);}}
 return <section className="panel" style={{padding:24,marginBottom:24}}>
  <h2>课程知识检索</h2><p className="muted">在设置中配置向量化模型后，为资料建立索引。教师和助教可以检索这些资料并引用原文。索引前会检测内容类型，含图片、图表或需OCR的文档暂缓处理。建立索引会将文字发送到你配置的模型供应商；关闭页面后任务继续。</p>
  {rows.map(row=><div key={row.id} className="section-heading" style={{padding:'8px 0',gap:12}}><span>{row.title} · {!row.readable?'格式暂不支持':row.index?labels[row.index.status]||row.index.status:'尚未索引'}{row.index?.classification&&` · ${row.index.classification.format.toUpperCase()} / ${{plain_text:'普通文字',structured_text:'含结构的文字',visual_deferred:'含视觉内容，暂缓'}[row.index.classification.category]||'待确认'}`}{row.index?.chunks?` ${row.index.indexed_chunks}/${row.index.chunks}`:''}{row.index?.error&&<small style={{display:'block'}}>{row.index.error}</small>}</span>
   <button className="button small" disabled={busy||!row.readable||['running','queued'].includes(row.index?.status||'')} onClick={()=>void build(row)}>{row.index?'重建 / 重试':'建立索引'}</button></div>)}
  <form onSubmit={async e=>{e.preventDefault();setBusy(true);setError('');setHits([]);setNotice('');try{const result=await aiRequest<{results:Hit[];notice:string}>(userId,path+'/search',{query,limit:5});setHits(result.results);setNotice(result.notice);}catch(e){setError(e instanceof Error?e.message:'检索失败');}finally{setBusy(false);}}}>
   <label className="field">检索测试<input value={query} maxLength={2000} onChange={e=>setQuery(e.target.value)} placeholder="例如：资料中怎样解释数据库事务？"/></label><button className="button primary" disabled={busy||!query.trim()}>检索资料</button>
  </form>
  {hits.map((hit,i)=><div key={i} className="prose"><strong>{hit.citation}</strong><p style={{whiteSpace:'pre-wrap'}}>{hit.text}</p></div>)}
  <p role="status">{error||notice}</p>
  <button className="button small" disabled={busy} onClick={async()=>{setBusy(true);setError('');try{const result=await aiRequest<{removed_generations:number}>(userId,path+'/cleanup',{});setNotice(`已清理 ${result.removed_generations} 份失效索引版本；任务记录仍保留。`);}catch(e){setError(e instanceof Error?e.message:'清理失败');}finally{setBusy(false);}}}>清理失效索引</button>
 </section>;
}
