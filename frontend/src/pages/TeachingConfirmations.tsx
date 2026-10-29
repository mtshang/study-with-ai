import {useEffect,useState} from 'react';
import {aiRequest} from '../ai';
type Confirmation={id:string;payload:{title:string;description:string}};
export function TeachingConfirmations({userId,courseId,onDecision}:{userId:string;courseId:string;onDecision:()=>void}){
 const [items,setItems]=useState<Confirmation[]>([]),[busy,setBusy]=useState(false),[error,setError]=useState('');
 const path='/courses/'+courseId+'/confirmations';
 useEffect(()=>{const abort=new AbortController();
  const load=()=>aiRequest<Confirmation[]>(userId,path,undefined,undefined,abort.signal).then(v=>{if(!abort.signal.aborted)setItems(v);}).catch(e=>{if(!abort.signal.aborted)setError(e.message);});
  void load();const timer=setInterval(()=>void load(),3000);return()=>{abort.abort();clearInterval(timer);};
 },[userId,path]);
 async function decide(id:string,approve:boolean){
  setBusy(true);setError('');
  try{await aiRequest(userId,'/proposals/'+id+'/decision',{approve});setItems(rows=>rows.filter(r=>r.id!==id));onDecision();}
  catch(e){setError(e instanceof Error?e.message:'确认失败');}finally{setBusy(false);}
 }
 if(!items.length&&!error)return null;
 return <section className="panel teaching-confirmations" aria-label="教学确认"><h3>需要你的确认</h3>
  <p>仅暂停与此调整有关的操作，其他学习可以继续。决定后可发送消息继续教学。</p>
  {items.map(p=><article key={p.id}><h4>{p.payload.title}</h4><p>{p.payload.description}</p><div className="button-row">
   <button className="button primary" disabled={busy} onClick={()=>void decide(p.id,true)}>确认</button><button className="button" disabled={busy} onClick={()=>void decide(p.id,false)}>不采用</button>
  </div></article>)}{error&&<p role="alert">{error}</p>}
 </section>;
}
