import {useContext,useEffect,useRef,useState} from 'react';
import {ServerContext} from '../serverWorkspace';
import {accountRequest} from '../api';
import type {Course,Chapter} from '../types';
import {formatTime} from '../components/ui';
type Snapshot={chapters:Chapter[];actor?:string;historical_items?:{id:string;title:string;content?:string;questions?:{prompt:string}[]}[]};
export function RevisionViewer({course}:{course:Course}){
 const server=useContext(ServerContext),[detail,setDetail]=useState<Snapshot|null>(null),[error,setError]=useState(''),[loading,setLoading]=useState(false),[version,setVersion]=useState<number|null>(null);
 const request=useRef<AbortController|null>(null);
 useEffect(()=>()=>request.current?.abort(),[]);
 async function show(v:number){if(!server.userId)return;request.current?.abort();const abort=new AbortController();request.current=abort;setLoading(true);setDetail(null);setVersion(v);setError('');
 try{const data=await accountRequest<Snapshot>(`/courses/${course.id}/revisions/${v}`,undefined,abort.signal,{headers:{'X-Workspace-User':server.userId}});if(!abort.signal.aborted)setDetail(data);}
 catch(e){if(!abort.signal.aborted)setError(e instanceof Error?e.message:'读取失败');}finally{if(!abort.signal.aborted)setLoading(false);}}
 return <>{course.revisions.map(rev=><div className="revision" key={rev.id}><strong>版本 {rev.version} · {rev.summary}</strong><p>{formatTime(rev.time)}</p><p>{rev.titles.join(' → ')||'空路线'}</p>{server.active&&<button className="button small" onClick={()=>void show(rev.version)}>查看版本 {rev.version} 的内容</button>}</div>)}
 {loading&&<p role="status">正在读取历史内容…</p>}{error&&<p role="alert">{error}</p>}
 {detail&&<section aria-label="历史版本内容"><h3>版本 {version} · 只读历史</h3>{detail.chapters.map(ch=><details key={ch.id}><summary>{ch.title}{ch.archived?'（当时已移出）':''}{!course.chapters.some(c=>c.id===ch.id)?'（原章节已删除）':''}</summary><p>{ch.description}</p><p className="preserve-text">{ch.content}</p></details>)}{detail.historical_items?.map(item=><details key={item.id}><summary>操作前快照：{item.title}</summary><p className="preserve-text">{item.content}</p>{item.questions?.map((q,i)=><p key={i}>{q.prompt}</p>)}</details>)}</section>}
 </>;
}
