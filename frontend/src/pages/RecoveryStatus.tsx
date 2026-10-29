import {useState} from 'react';
import {aiRequest,type RecoveryState} from '../ai';
export function RecoveryStatus({userId,id,state,onResume}:{userId:string;id:string;state?:RecoveryState|null;onResume:()=>void}){
 const [busy,setBusy]=useState(false),[error,setError]=useState('');
 if(!state)return null;
 const canResume=['paused','needs_attention','auth_required'].includes(state.status);
 async function resume(){setBusy(true);setError('');try{await aiRequest(userId,'/jobs/'+id+'/resume',{});onResume();}catch(e){setError(e instanceof Error?e.message:'恢复失败');}finally{setBusy(false);}}
 return <div className="recovery-status">
 {state.recoveries>0&&<small>已自动恢复 {state.recoveries} 次</small>}
 {state.error&&<p>{state.error}</p>}
 {canResume&&<button className="button" disabled={busy} onClick={()=>void resume()}>继续此任务</button>}
 {state.interrupted_drafts.length>0&&<details><summary>中断前的草稿（未完成）</summary>{state.interrupted_drafts.map((d,i)=><p key={i} style={{whiteSpace:'pre-wrap'}}>{d.text}</p>)}</details>}
 {error&&<p role="alert">{error}</p>}
 </div>;
}
