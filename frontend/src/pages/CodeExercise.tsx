import {useContext,useEffect,useRef,useState} from 'react';
import {ServerContext} from '../serverWorkspace';
import {accountRequest} from '../api';
import type {Question,Submission,CodeRun} from '../types';
import {Modal,formatTime} from '../components/ui';

export function CodeFeedback({value}:{value:CodeRun}){
 const labels:Record<string,string>={running:'运行中',completed:'运行完成',unavailable:'环境不可用或结果未确认',interrupted:'运行中断',runtime_error:'运行错误或资源限制',timeout:'运行超时',output_limit:'输出超限'};
 return <section className="code-feedback" aria-label="代码运行结果"><strong>{labels[value.status]||value.status} · {value.passed} / {value.total} 个用例通过</strong>{value.error&&<p role="alert">{value.error}</p>}{value.cases.map(c=><details key={c.number} open><summary>用例 {c.number} · {c.passed?'通过':labels[c.status]||'输出不匹配'}{!c.passed&&c.status==='completed'?' · 输出不匹配':''}</summary><p>输入</p><pre>{c.stdin||'（空输入）'}</pre><p>预期输出</p><pre>{c.expected_stdout||'（空输出）'}</pre><p>实际输出</p><pre>{c.stdout||'（空输出）'}</pre>{c.stderr&&<><p>错误输出</p><pre>{c.stderr}</pre></>}<small>{c.duration_ms} 毫秒 · 退出码 {c.exit_code??'未确认'}{c.output_truncated?' · 输出已截断':''}</small></details>)}<p className="fine-print">只统一换行并忽略末尾换行，空格参与比较。通过公开用例不等于对所有输入都正确。</p></section>;
}

export function CodeExercise({courseId,activityId,question,onClose}:{courseId:string;activityId:string;question:Question;onClose:()=>void}){
 const server=useContext(ServerContext),[code,setCode]=useState(question.python?.starter_code||''),[records,setRecords]=useState<Submission[]>([]),[busy,setBusy]=useState(false),[error,setError]=useState(''),[loaded,setLoaded]=useState(false);
 const attempt=useRef<{id:string;code:string}|null>(null),alive=useRef(true),lastResult=useRef('');
 const path=`/courses/${courseId}/activities/${activityId}/code-runs`;
 const headers={'X-Workspace-User':server.userId||''};
 useEffect(()=>{
  const abort=new AbortController();alive.current=true;let timer:ReturnType<typeof setTimeout>;
  async function poll(){try{const data=await accountRequest<Submission[]>(path,undefined,abort.signal,{headers});if(!abort.signal.aborted){setRecords(data);setLoaded(true);const signature=data.map(s=>s.id+s.codeRun?.status).join();if(signature!==lastResult.current){lastResult.current=signature;server.reload();}}}
   catch(e){if(!abort.signal.aborted)setError(e instanceof Error?e.message:'读取运行记录失败');}
   finally{if(!abort.signal.aborted)timer=setTimeout(()=>void poll(),2000);}}
  if(server.userId)void poll();return()=>{alive.current=false;abort.abort();clearTimeout(timer);};
 },[courseId,activityId,server.userId]);
 const running=records.some(s=>s.codeRun?.status==='running');
 async function submit(){
  if(busy||running||!loaded||!server.userId||!code.trim())return;
  setBusy(true);setError('');if(attempt.current?.code!==code)attempt.current={id:crypto.randomUUID(),code};
  try{const result=await accountRequest<Submission>(path,attempt.current,AbortSignal.timeout(15000),{headers});if(alive.current){setRecords(previous=>[result,...previous.filter(s=>s.id!==result.id)]);attempt.current=null;server.reload();}}
  catch(e){if(alive.current)setError(e instanceof Error?e.message:'提交失败，请核对运行记录后重试');}finally{if(alive.current)setBusy(false);}
 }
 return <Modal title="Python 练习与运行记录" wide onClose={onClose}><h3>{question.prompt}</h3><p>Python 标准库 · 禁网 · 每个用例使用新临时容器。点击提交会保存本次代码与结果。</p>
 <details><summary>公开测试用例（{question.python?.cases.length}）</summary>{question.python?.cases.map((c,i)=><div key={i}><strong>用例 {i+1}</strong><p>输入</p><pre>{c.stdin||'（空输入）'}</pre><p>预期输出</p><pre>{c.expected_stdout||'（空输出）'}</pre></div>)}</details>
 <label className="field">Python 代码<textarea className="python-code" aria-label="Python 代码" rows={10} maxLength={10000} spellCheck={false} value={code} onChange={e=>setCode(e.target.value)}/></label>
 {error&&<p role="alert">{error}</p>}<div className="button-row"><button className="button primary" disabled={!server.active||!loaded||busy||running||!code.trim()} onClick={()=>void submit()}>{busy?'正在提交…':running?'正在运行…':'提交并运行'}</button><a className="text-link" href={`#/courses/${courseId}/chat`}>请教师讲解结果</a></div>
 {!server.active&&<p>请登录后运行，演示空间不执行代码。</p>}<p className="fine-print">关闭窗口不取消已接受的运行。环境故障不判为答案错误；可以查看旧记录后重新提交。教师不会自行执行代码。</p>
 <section aria-label="代码提交历史"><h3>最近运行记录</h3>{records.map(s=><article className="submission-history" key={s.id}><strong>{formatTime(s.createdAt)}</strong><details><summary>查看本次代码</summary><pre>{s.answers[question.id]||Object.values(s.answers)[0]}</pre></details>{s.codeRun&&<CodeFeedback value={s.codeRun}/>}</article>)}{loaded&&!records.length&&<p>暂无运行记录。</p>}</section></Modal>;
}
