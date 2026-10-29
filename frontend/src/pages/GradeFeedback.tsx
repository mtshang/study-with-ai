import {useContext,useEffect,useRef,useState} from 'react';
import {ServerContext} from '../serverWorkspace';
import {accountRequest} from '../api';
import {aiRequest} from '../ai';
import type {AIGrade,GradeResult} from '../types';

function ResultDetails({result}:{result:GradeResult}){
  return <><strong className="grade-mastery">{{mastered:'基本掌握',partial:'部分掌握',needs_practice:'需要再练'}[result.mastery]}</strong>
    <p>{result.reason}</p><h4>本次答案中的依据</h4>{result.evidence.map((text,i)=><blockquote key={i}>{text}</blockquote>)}
    <h4>改进建议</h4><ul>{result.suggestions.map((text,i)=><li key={i}>{text}</li>)}</ul>
    <details><summary>参考解释</summary><p>{result.sample_answer}</p></details></>;
}

export function GradeFeedback({courseId,initial}:{courseId:string;initial:AIGrade}){
  const server=useContext(ServerContext),[grade,setGrade]=useState(initial),[error,setError]=useState(''),[busy,setBusy]=useState(false),[refresh,setRefresh]=useState(0);
  const alive=useRef(true),reloaded=useRef('');
  useEffect(()=>{
    alive.current=true;setGrade(initial);setError('');const abort=new AbortController();let timer:ReturnType<typeof setTimeout>;
    async function poll(){
      if(!server.userId)return;
      let again=true;
      try{
        const data=await accountRequest<AIGrade>(`/courses/${courseId}/submissions/${initial.submission_id}/grading`,undefined,abort.signal,{headers:{'X-Workspace-User':server.userId}});
        if(abort.signal.aborted)return;
        setGrade(data);setError('');again=data.status==='waiting'||data.status==='running';
        if(data.status==='completed'&&reloaded.current!==data.id){reloaded.current=data.id;server.reload();}
      }catch(e){if(!abort.signal.aborted){setError(e instanceof Error?e.message:'无法读取批改状态');again=false;}}
      if(again&&!abort.signal.aborted)timer=setTimeout(()=>void poll(),2000);
    }
    void poll();return()=>{alive.current=false;abort.abort();clearTimeout(timer);};
  },[initial.id,courseId,server.userId,refresh]);
  async function retry(){
    if(!server.userId||busy)return;
    setBusy(true);setError('');
    try{await aiRequest(server.userId,`/courses/${courseId}/submissions/${initial.submission_id}/grade`,{});if(alive.current)setRefresh(n=>n+1);}
    catch(e){if(alive.current)setError(e instanceof Error?e.message:'重试批改失败');}
    finally{if(alive.current)setBusy(false);}
  }
  const result=grade.result;
  return <section className="grade-feedback" aria-label="本次提交的 AI 批改">
    <h3>AI 批改</h3>
    {grade.kind==='assignment'?<>
      <p role="status">开放题已批改 {grade.items?.filter(i=>i.status==='completed').length||0} / {grade.items?.length||0} 题</p>
      {!!grade.objective_results?.length&&<p>客观题已核对：{grade.objective_results.filter(i=>i.verdict==='correct').length} / {grade.objective_results.length} 题正确</p>}
      {(grade.objective_results||[]).map(item=><article className="assignment-grade-item" key={item.questionId}>
        <h4>第 {item.number} 题 · {item.verdict==='correct'?'回答正确':'回答错误'}</h4><p>{item.question}</p>
        <p>参考答案：{item.correct}</p><p>{item.explanation}</p></article>)}
      {(grade.items||[]).map(item=><article className="assignment-grade-item" key={item.question_id}>
        <h4>第 {item.number} 题 · {{waiting:'等待批改',running:'正在批改',failed:'批改未完成',completed:'已批改'}[item.status]}</h4>
        <p>{item.question}</p>{item.result?<ResultDetails result={item.result}/>:item.error&&<p>{item.error}</p>}
      </article>)}
      {!!grade.pending_attachment_count&&<p>另有 {grade.pending_attachment_count} 份附件待评阅，AI 尚未读取或批改附件。</p>}
      {grade.status!=='completed'?<><p>{grade.error}</p><button type="button" className="button" disabled={busy} onClick={()=>void retry()}>{busy?'正在请求…':'继续批改未完成题'}</button>
        <p className="fine-print">逐题保存进度；已完成题目不会再次调用模型批改。</p></>:<><p>文字答案批改已完成，教师将统一总结；课程暂停时结果保留。</p><a className="text-link" href={`#/courses/${courseId}/chat`}>去 AI 导师查看讲解</a></>}
    </>:grade.status==='completed'&&result?<>
      <ResultDetails result={result}/>
      <p className="fine-print">仅评价本次作答，不代表课程完成。可重新作答；原答案与评价保留。</p>
      <a className="text-link" href={`#/courses/${courseId}/chat`}>去 AI 导师查看讲解</a>
    </>:<>
      <p role="status">{{waiting:'答案已保存，等待启动 AI 批改。',running:'批改助教正在分析本次答案，离开页面后会继续。',failed:'本次批改未完成，答案已保留。',completed:'批改结果需重新核对。'}[grade.status]||'正在核对批改状态。'}</p>
      {grade.error&&<p>{grade.error}</p>}
      <button type="button" className="button" disabled={busy} onClick={()=>void retry()}>{busy?'正在请求…':grade.status==='running'?'检查并继续批改':'重试批改'}</button>
      <p className="fine-print">服务重启后可点此继续。已有模型结果会优先补存，不重复生成。</p>
    </>}
    {error&&<p role="alert">{error} <button type="button" className="text-link" onClick={()=>setRefresh(n=>n+1)}>重新读取</button></p>}
  </section>;
}
