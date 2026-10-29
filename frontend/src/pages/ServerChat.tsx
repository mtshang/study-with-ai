import {RecoveryStatus} from './RecoveryStatus';
import {useEffect,useRef,useState} from 'react';
import {CourseExtensions} from './PersonalExtensions';
import {PersonaSettings} from './PersonaSettings';
import {TeachingConfirmations} from './TeachingConfirmations';
import {ArrowUp,Square,MessageSquare} from 'lucide-react';
import type {Course,UpdateCourse} from '../types';
import {ChapterProposal} from './ChapterProposal';
import {aiRequest,watchRun,type ChatRun,type AssistantState} from '../ai';

export function ServerChat({course,userId,reload,update}:{course:Course;userId:string;reload:()=>void;update:UpdateCourse}){
  const [runs,setRuns]=useState<ChatRun[]>([]),[input,setInput]=useState(''),[error,setError]=useState('');
  const [busy,setBusy]=useState(false),[loaded,setLoaded]=useState(false),[connection,setConnection]=useState(0);
  const request=useRef<{id:string;prompt:string}|null>(null),alive=useRef(true),end=useRef<HTMLDivElement>(null);
  const [agents,setAgents]=useState<AssistantState>({paused:false,teacher_run_id:null,active_assistants:0,pending_results:0,assistants:[]});
  const publishedSignature=useRef('');
  const [selected,setSelected]=useState(course.currentChapterId||''),[switching,setSwitching]=useState(false);
  const activeChapters=course.chapters.filter(c=>!c.archived);
  const current=activeChapters.find(c=>c.id===course.currentChapterId);
  const next=current?activeChapters[activeChapters.findIndex(c=>c.id===current.id)+1]:undefined;
  useEffect(()=>setSelected(course.currentChapterId||''),[course.currentChapterId]);
  async function switchChapter(){
    if(switching||busy||!selected||!activeChapters.some(c=>c.id===selected))return;
    setSwitching(true);setError('');
    try{if((await update(course.id,c=>({...c,currentChapterId:selected})))===false)setError('章节切换未保存，请重新读取课程后重试。');}
    catch(e){setError(e instanceof Error?e.message:'章节切换失败');}
    finally{if(alive.current)setSwitching(false);}
  }
  const running=runs.find(r=>r.status==='running');
  const merge=(run:ChatRun)=>setRuns(previous=>previous.some(r=>r.id===run.id)?previous.map(r=>r.id===run.id?run:r):[...previous,run]);
  async function load(signal?:AbortSignal){
    try{const data=await aiRequest<ChatRun[]>(userId,`/courses/${course.id}/runs`,undefined,undefined,signal);if(alive.current){setRuns(data);setLoaded(true);setError('');setConnection(n=>n+1);}}
    catch(e){if(alive.current&&!signal?.aborted)setError(e instanceof Error?e.message:'无法读取对话');}
  }
  useEffect(()=>{alive.current=true;const abort=new AbortController();void load(abort.signal);return()=>{alive.current=false;abort.abort();};},[userId,course.id]);
  useEffect(()=>{
    const abort=new AbortController();let timer:ReturnType<typeof setTimeout>;
    async function poll(){
      try{
        const [state,history]=await Promise.all([
          aiRequest<AssistantState>(userId,`/courses/${course.id}/agents`,undefined,undefined,abort.signal),
          aiRequest<ChatRun[]>(userId,`/courses/${course.id}/runs`,undefined,undefined,abort.signal)]);
        if(!abort.signal.aborted){
          setAgents(state);setRuns(history);setLoaded(true);
          const signature=history.flatMap(r=>r.proposals.filter(p=>p.status==='published').map(p=>p.id)).sort().join(',');
          if(signature!==publishedSignature.current){publishedSignature.current=signature;reload();}
        }
      }catch(e){if(!abort.signal.aborted)setError(e instanceof Error?e.message:'无法读取助教状态');}
      finally{if(!abort.signal.aborted)timer=setTimeout(()=>void poll(),2000);}
    }
    void poll();return()=>{abort.abort();clearTimeout(timer);};
  },[userId,course.id]);
  useEffect(()=>{if(!running)return;const abort=new AbortController();
    void watchRun(userId,running.id,abort.signal,run=>{if(!alive.current)return;merge(run);if(run.status!=='running')reload();}).catch(e=>{if(!abort.signal.aborted&&alive.current)setError(e.message);});
    return()=>abort.abort();
  },[running?.id,userId,connection]);
  useEffect(()=>{const container=end.current?.parentElement;if(container)container.scrollTo({top:container.scrollHeight,behavior:'smooth'});},[runs.at(-1)?.answer,runs.length]);
  async function send(message?:string){
    const prompt=(message??input).trim();
    if(!prompt||busy||running)return;setBusy(true);setError('');
    if(request.current?.prompt!==prompt)request.current={id:crypto.randomUUID(),prompt};
    try{const run=await aiRequest<ChatRun>(userId,`/courses/${course.id}/runs`,request.current);if(alive.current){merge(run);setInput('');request.current=null;}}
    catch(e){if(alive.current)setError(e instanceof Error?e.message:'发送失败');}finally{if(alive.current)setBusy(false);}
  }
  async function stop(){setBusy(true);try{const state=await aiRequest<AssistantState>(userId,`/courses/${course.id}/pause`,{});if(alive.current){setAgents(state);await load();}}catch(e){if(alive.current)setError(e instanceof Error?e.message:'停止失败');}finally{if(alive.current)setBusy(false);}}
  async function decide(id:string,approve:boolean){setBusy(true);setError('');try{const run=await aiRequest<ChatRun>(userId,`/proposals/${id}/decision`,{approve});if(alive.current){merge(run);reload();}}catch(e){if(alive.current){setError(e instanceof Error?e.message:'处理失败');void load();}}finally{if(alive.current)setBusy(false);}}
  return <div className="chat-layout"><section className="chat-panel panel">
    <div className="chat-header"><MessageSquare/><div><h2>AI 导师</h2><p>{course.title} · 对话独立保存</p></div><a className="text-link" href="#/settings">模型设置</a></div>
    <TeachingConfirmations key={userId+course.id} userId={userId} courseId={course.id} onDecision={()=>void load()}/>
    <div className="chat-messages" aria-label="对话消息">
      {!runs.length&&<p className="muted">可以请老师规划章节、阅读教材、讲解当前章节，或发布练习和作业。</p>}
      {runs.map(run=><div key={run.id} className="server-run">
        <article className="server-message student"><strong>{run.trigger==='assistant'?'助教结果通知':'我'}</strong><p>{run.prompt}</p></article>
        <article className="server-message teacher"><strong>AI 导师</strong><p>{run.answer||run.progress}</p>{run.status==='running'&&<small role="status">{run.progress}…</small>}{run.status==='stopped'&&<small>已停止，保留已生成内容</small>}{run.error&&<p role="alert">{run.error}</p>}</article>
        <RecoveryStatus userId={userId} id={run.id} state={run.recovery} onResume={()=>void load()}/>
        {run.proposals.filter(p=>p.payload.kind!=='memory').map(p=><section className="proposal-card" key={p.id}><h3>{p.payload.kind==='mcp'?'外部工具：':p.payload.kind==='chapters'?'章节调整：':p.payload.kind==='recycle'?'回收站操作：':p.payload.kind==='assignment'?'作业：':'练习：'}{p.payload.title}</h3>{p.payload.description&&<p>{p.payload.description}</p>}{(p.payload.kind==='chapters'||p.payload.kind==='recycle')&&<ChapterProposal payload={p.payload}/>}
          {p.payload.kind==='mcp'&&<pre className="connector-config-preview">{JSON.stringify({arguments:p.payload.arguments,result:p.payload.result},null,2)}</pre>}{p.payload.questions?.map((q,i)=><div key={i}><p>{q.prompt}</p>{q.python&&<details><summary>Python · {q.python.cases.length} 个公开测试用例</summary>{q.python.cases.map((c,n)=><div key={n}><p>输入</p><pre>{c.stdin}</pre><p>预期输出</p><pre>{c.expected_stdout}</pre></div>)}<p>只发布题目，学生提交后才运行。</p></details>}{q.options?.map((o,j)=><p key={j}>{String.fromCharCode(65+j)}. {o}</p>)}<details><summary>参考答案与讲解</summary><p>{q.correct||'开放题'}{q.explanation&&' · '+q.explanation}</p></details></div>)}
          <p>{({pending:'等待批准',reviewed:'已记录核实结论',published:p.payload.kind==='mcp'?'外部工具已返回，请查看结果':p.payload.kind==='chapters'?'章节已更新，历史已保存':p.payload.kind==='recycle'?'已移入回收站':p.payload.kind==='assignment'?'已发布到课程作业':'已发布到课程练习',rejected:'已拒绝',failed:'操作失败，请读取最新状态后重新生成',uncertain:'操作结果待核对',executing:'正在执行'} as Record<string,string>)[p.status]||p.status}</p>{p.error&&<p>{p.error}</p>}
          {(p.status==='pending'||(p.status==='uncertain'&&p.payload.kind!=='mcp'))&&<div className="button-row"><button className="button primary" disabled={busy||run.status==='running'} onClick={()=>void decide(p.id,true)}>{p.payload.kind==='mcp'?'批准调用':p.status==='uncertain'?'核对并重试操作':p.payload.kind==='chapters'||p.payload.kind==='recycle'?'批准修改':'批准发布'}</button>{p.status==='pending'&&<button className="button" disabled={busy||run.status==='running'} onClick={()=>void decide(p.id,false)}>拒绝</button>}</div>}
        </section>)}
      </div>)}<div ref={end}/>
    </div>
    <div className="server-composer">{error&&<p role="alert">{error} <button className="text-link" onClick={()=>void load()}>重新读取对话</button></p>}
      <form onSubmit={e=>{e.preventDefault();void send();}}><textarea aria-label="发送给 AI 导师" placeholder="例如：读取当前章节，给我出一道选择题" value={input} maxLength={12000} onChange={e=>setInput(e.target.value)} rows={3}/>
        {(running||agents.active_assistants>0)&&<button type="button" className="button" disabled={busy||(agents.paused&&!running)} onClick={()=>void stop()}><Square size={16}/>{agents.paused&&!running?'已暂停自动继续':'停止生成'}</button>}
        {!running&&<button className="button primary" disabled={busy||!loaded||!input.trim()}><ArrowUp size={16}/>发送</button>}
      </form><small className="muted">离开页面后任务继续；停止取消教师当前回复并暂停自动唤醒，助教继续完成。再次发送会恢复教师。</small>
    </div>
  </section><aside className="chat-context"><section className="panel learning-controls" aria-label="继续学习"><h3>当前学习</h3><p>{course.title}</p><p>{course.goal||'尚未填写学习目的'}</p>
      <p>当前章节：<strong>{current?.title||'未选择'}</strong></p>
      {current&&<p>{current.read?'已读 · 可以继续复习':'未读'}，学习掌握情况由作答与交流判断。</p>}
      <label className="field">选择学习章节<select aria-label="选择学习章节" value={selected} disabled={switching||course.archived} onChange={e=>setSelected(e.target.value)}><option value="">请选择章节</option>{activeChapters.map(c=><option key={c.id} value={c.id}>{c.title}{c.read?'（已读）':''}</option>)}</select></label>
      <div className="button-row"><button className="button" disabled={switching||busy||course.archived||!selected||selected===course.currentChapterId} onClick={()=>void switchChapter()}>确认切换章节</button>{next&&<button className="text-link" disabled={switching||course.archived} onClick={()=>setSelected(next.id)}>选择下一章</button>}</div>
      {selected!==course.currentChapterId&&selected&&<p role="status">尚未切换，请点击确认。</p>}
      <button className="button primary" disabled={busy||switching||!loaded||!!running||!current||course.archived||selected!==course.currentChapterId} onClick={()=>void send('请基于教学系统中的最新当前章节、近期作答和批改反馈，开始或继续本章教学。先衔接已有进度，再讲解一个知识点或安排适当练习。如建议下一章，请等待我自行选择；不要替我切换章节或标记已读。')}>{runs.length?'继续学习':'开始学习'}</button>
      {!activeChapters.length&&<p>还没有章节，可以在对话中请教师规划并创建章节。</p>}
      <p className="muted">教师只建议下一章。切换章节和标记已读由你操作；刷新页面不会自动开始教学。</p>
      <div className="button-row"><a className="text-link" href={`#/courses/${course.id}/chapters`}>查看章节</a><a className="text-link" href={`#/courses/${course.id}/exercises`}>练习</a><a className="text-link" href={`#/courses/${course.id}/assignments`}>作业</a><a className="text-link" href={`#/courses/${course.id}/history`}>学习记录</a></div>
    </section>
    <CourseExtensions key={userId+course.id} userId={userId} courseId={course.id}/>
    <details className="course-persona"><summary>教学人格设置</summary><PersonaSettings key={userId+course.id} userId={userId} courseId={course.id}/></details>
    <section className="panel assistant-panel" aria-label="助教任务"><h3>助教任务</h3>
      <p role="status">{agents.active_assistants} 个运行中 · {agents.pending_results} 个结果待处理</p>
      {agents.paused&&<p>已暂停自动唤醒。助教完成后会保留结果。</p>}
      {!running&&agents.pending_results>0&&<button className="button primary" disabled={busy} onClick={()=>void send('请先核对课程最新变更，再处理待办助教结果并继续教学。')}>继续处理结果</button>}
      {!agents.assistants.length&&<p className="muted">可以请教师委派一个助教准备练习，同时继续讲解。</p>}
      {agents.assistants.map(a=><details key={a.id} className="assistant-card"><summary>{a.role} · {({queued:'等待运行',running:'正在执行',completed:'已完成',failed:'失败',interrupted:'已中断',uncertain:'结果待核对'} as Record<string,string>)[a.status]||a.status}</summary>
        <RecoveryStatus userId={userId} id={a.id} state={a.recovery} onResume={()=>void load()}/><small>助教 ID：{a.id}</small><p>{a.task}</p>{a.result&&<p className="assistant-result">{a.result}</p>}{a.error&&<p role="alert">{a.error}</p>}<small>{a.consumed_by?'结果已交给教师':a.status==='completed'?'结果待教师处理':a.submission_id?'请在对应练习或作业的提交记录查看或重试批改':'独立执行，仅提交结果'}</small>
      </details>)}
    </section></aside></div>;
}
