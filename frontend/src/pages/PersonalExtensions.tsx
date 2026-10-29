import {useEffect,useState} from 'react';
import {aiRequest} from '../ai';
import {PageTitle,Modal} from '../components/ui';
import {ConnectorEditor,type Draft} from './ConnectorEditor';

export type ExtensionEntry={id:string;kind:'skill'|'mcp';name:string;revision:number;data:{description?:string;url?:string;credential_set?:boolean;discovered?:boolean;files?:{path:string;size:number;script:boolean}[];tools?:{name:string;description:string;inputSchema:unknown;effect:'disabled'|'read'|'write'}[]}};
const labels=['我的技能（skill）','我的连接器（MCP）','系统内置技能（skill）','系统内置连接器（MCP）'];
const message=(e:unknown)=>e instanceof Error?e.message:'操作失败，请重试';
export function PersonalExtensions({userId}:{userId:string}){
 const [tab,setTab]=useState(0),[rows,setRows]=useState<ExtensionEntry[]>([]),[error,setError]=useState(''),[busy,setBusy]=useState(false);
 const [editor,setEditor]=useState<{kind:'skill'|'MCP';id:string;entry?:ExtensionEntry}|null>(null),[detail,setDetail]=useState<ExtensionEntry|null>(null);
 const [policies,setPolicies]=useState<Record<string,string>>({});
 const [builtin,setBuiltin]=useState<{id:string;name:string;description:string;upstream:string;license:string}[]>([]);
 async function load(){setRows(await aiRequest<ExtensionEntry[]>(userId,'/extensions'));}
 useEffect(()=>{let alive=true;aiRequest<ExtensionEntry[]>(userId,'/extensions').then(r=>{if(alive)setRows(r);}).catch(e=>{if(alive)setError(message(e));});fetch('/api/ai/reading-skills').then(r=>{if(!r.ok)throw Error('内置技能读取失败');return r.json();}).then(r=>{if(alive)setBuiltin(r);}).catch(e=>{if(alive)setError(message(e));});return()=>{alive=false;};},[userId]);
 function show(row:ExtensionEntry){setDetail(row);setPolicies(Object.fromEntries((row.data.tools||[]).map(t=>[t.name,t.effect])));}
 async function action(fn:()=>Promise<void>){setBusy(true);setError('');try{await fn();}catch(e){setError(message(e));}finally{setBusy(false);}}
 async function save(draft:Draft){
  if(!editor)return;
  if(editor.kind==='skill'){
   const form=new FormData();form.set('id',editor.id);form.set('name',draft.name);for(const file of draft.files||[])form.append('files',file,file.webkitRelativePath||file.name);
   await aiRequest(userId,'/extensions/skills',form);
  }else{
   const config=Object.values(JSON.parse(draft.configuration!).mcpServers)[0] as {url:string;headers?:Record<string,string>};
   await aiRequest(userId,'/extensions/mcp',{id:editor.id,revision:editor.entry?.revision||0,name:draft.name,url:config.url,headers:config.headers},'PUT');
  }
  setEditor(null);setDetail(null);await load();
 }
 return <><PageTitle eyebrow="EXTEND YOUR LEARNING" title="技能·连接器" description="保存到个人库，再到课程聊天中选择启用。" action={tab<2?<button className="button primary" onClick={()=>setEditor({kind:tab===0?'skill':'MCP',id:crypto.randomUUID()})}>新建{labels[tab]}</button>:undefined}/>
 <div className="tab-row connector-tabs" role="group" aria-label="技能与连接器分类">{labels.map((l,i)=><button key={l} aria-pressed={tab===i} className={tab===i?'selected':''} onClick={()=>setTab(i)}>{l}</button>)}</div>
 {error&&<p role="alert" className="account-error">{error}</p>}
 <div className="connector-cards">{tab<2?rows.filter(r=>r.kind===(tab===0?'skill':'mcp')).map(r=><button className="connector-card" key={r.id} onClick={()=>show(r)}><span className="connector-badge">{r.kind==='skill'?'已导入':r.data.discovered?'已发现工具':'待连接'}</span><h2>{r.name}</h2><p>{r.data.description||r.data.url}</p><small>{r.kind==='skill'?`${r.data.files?.length||0} 个文件`:`${r.data.tools?.filter(t=>t.effect!=='disabled').length||0} 个已授权工具`}</small></button>):tab===2?builtin.map(r=><article className="connector-card" key={r.id}><h2>{r.name}</h2><p>{r.description}</p><small>{r.license}</small><p><a href={r.upstream} target="_blank" rel="noreferrer">开源来源</a></p></article>):null}</div>
 {tab<2&&!rows.some(r=>r.kind===(tab===0?'skill':'mcp'))&&<p className="muted">尚未添加，点击右上角新建。</p>}
 {tab===2&&<p className="fine-print">系统随项目提供的资料读取技能，继续用于课程内的受控文档读取。个人导入的技能需逐课程启用。</p>}
 {tab===3&&<p className="muted">暂无系统内置连接器。请在“我的连接器”中配置自己的服务。</p>}
 {editor&&<ConnectorEditor key={editor.entry?.id||editor.kind} kind={editor.kind} initial={editor.entry?{name:editor.entry.name,configuration:JSON.stringify({mcpServers:{server:{url:editor.entry.data.url}}},null,2)}:undefined} live onClose={()=>setEditor(null)} onSave={save}/>}
 {detail&&<Modal title={detail.name} wide onClose={()=>{if(!busy)setDetail(null);}}><div className="prose">
 {error&&<p role="alert">{error}</p>}
 {detail.kind==='skill'?<><p>{detail.data.description}</p><p>按需加载指令与参考文本。Python 脚本可在禁网沙箱执行，仅有标准库，不安装依赖。</p><ul>{detail.data.files?.map(f=><li key={f.path}>{f.path} · {f.size} 字节{f.script?' · 脚本':''}</li>)}</ul></>:<><p>{detail.data.url}</p><p>{detail.data.credential_set?'已保存凭据（不回显）':'未设置凭据'}</p><div className="button-row"><button className="button" disabled={busy} onClick={()=>{setEditor({kind:'MCP',id:detail.id,entry:detail});setDetail(null);}}>编辑配置</button><button className="button" disabled={busy} onClick={()=>void action(async()=>{show(await aiRequest<ExtensionEntry>(userId,`/extensions/${detail.id}/discover`,{revision:detail.revision}));await load();})}>连接并发现工具</button></div><p className="fine-print">每次重新发现或修改配置都会重置权限。只读必须由你确认，服务的自我声明不作为批准。</p>
 {detail.data.tools?.map(t=><section className="panel" key={t.name}><strong>{t.name}</strong><p>{t.description}</p><label className="field">工具用途<select aria-label={`${t.name} 权限`} value={policies[t.name]||'disabled'} disabled={busy} onChange={e=>setPolicies({...policies,[t.name]:e.target.value})}><option value="disabled">禁用（默认）</option><option value="read">我确认：只读</option><option value="write">有副作用</option></select></label><details><summary>参数格式</summary><pre className="connector-config-preview">{JSON.stringify(t.inputSchema,null,2)}</pre></details></section>)}
 {!!detail.data.tools?.length&&<button className="button primary" disabled={busy} onClick={()=>void action(async()=>{show(await aiRequest<ExtensionEntry>(userId,`/extensions/${detail.id}/tools`,{revision:detail.revision,tools:policies},'PUT'));await load();})}>保存工具权限</button>}
 <p>助教仅能调用确认过的只读工具。教师调用有副作用工具时，手动／部分批准会逐次征求批准；完全访问可直接调用。</p></>}
 <div className="modal-actions"><button className="button" disabled={busy} onClick={()=>{if(window.confirm('删除此扩展？课程将无法继续使用，历史调用记录保留。'))void action(async()=>{await aiRequest(userId,`/extensions/${detail.id}/delete`,{revision:detail.revision});setDetail(null);await load();});}}>删除</button><button className="button" disabled={busy} onClick={()=>setDetail(null)}>关闭</button></div></div></Modal>}
 </>;
}

type Call={id:string;tool:string;status:string;effect:string;arguments:unknown;result:unknown;error:string};
export function CourseExtensions({userId,courseId}:{userId:string;courseId:string}){
 const [rows,setRows]=useState<ExtensionEntry[]>([]),[binding,setBinding]=useState({revision:0,enabled:[] as string[]}),[calls,setCalls]=useState<Call[]>([]),[error,setError]=useState(''),[busy,setBusy]=useState(false),[loaded,setLoaded]=useState(false);
 const base=`/courses/${courseId}`;
 async function load(){const [r,b,c]=await Promise.all([aiRequest<ExtensionEntry[]>(userId,'/extensions'),aiRequest<typeof binding>(userId,base+'/extensions'),aiRequest<Call[]>(userId,base+'/mcp-calls')]);setRows(r);setBinding({...b,enabled:b.enabled.filter(id=>r.some(e=>e.id===id))});setCalls(c);setLoaded(true);}
 async function action(fn:()=>Promise<void>){setBusy(true);setError('');try{await fn();}catch(e){setError(message(e));}finally{setBusy(false);}}
 return <details className="course-persona" onToggle={e=>{if(e.currentTarget.open&&!loaded)void action(load);}}><summary>本课程技能与连接器</summary><p>仅启用此处勾选的个人扩展。</p>{error&&<p role="alert">{error}</p>}{rows.map(r=><label className="field" key={r.id}><span><input type="checkbox" disabled={busy} checked={binding.enabled.includes(r.id)} onChange={e=>setBinding({...binding,enabled:e.target.checked?[...binding.enabled,r.id]:binding.enabled.filter(id=>id!==r.id)})}/> {r.name} · {r.kind.toUpperCase()}</span></label>)}
 <div className="button-row"><button className="button primary" disabled={busy||!loaded} onClick={()=>void action(async()=>{setBinding(await aiRequest(userId,base+'/extensions',binding,'PUT'));})}>保存课程启用项</button><button className="button" disabled={busy} onClick={()=>void action(load)}>刷新</button></div><a href="#/connectors" className="text-link">管理个人库</a>
 <h4>最近工具调用</h4>{calls.map(c=><details key={c.id}><summary>{c.tool} · {({completed:'已返回',pending:'待批准',ready:'等待执行',executing:'执行中／待核实',uncertain:'结果未知',reviewed:'用户已核实',rejected:'已拒绝'} as Record<string,string>)[c.status]||c.status}</summary><small>{c.id}</small><pre className="connector-config-preview">{JSON.stringify({arguments:c.arguments,result:c.result},null,2)}</pre>{c.error&&<p>{c.error}</p>}{['uncertain','executing','ready'].includes(c.status)&&<button className="button" disabled={busy} onClick={()=>{const note=window.prompt('请先检查外部服务的实际结果，再填写核实结论。这不会重新执行工具。');if(note?.trim())void action(async()=>{await aiRequest(userId,base+`/mcp-calls/${c.id}/review`,{note});await load();});}}>记录核实结论（不重发）</button>}</details>)}</details>;
}
