export type RecoveryState={status:string;recoveries:number;error:string;interrupted_drafts:{text:string;at:string}[]};
import {accountRequest} from './api';
export type ModelChannel={base_url:string;model:string;key_set:boolean};
export type ModelSettings={revision:string;permission:'manual'|'assisted'|'full';chat:ModelChannel;vision:ModelChannel;embedding:ModelChannel};
type ChapterPreview={title:string;description:string;content:string};
export type Proposal={id:string;status:string;error:string;payload:{kind?:'exercise'|'assignment'|'chapters'|'recycle'|'memory'|'mcp';arguments?:unknown;result?:unknown;description?:string;title:string;questions?:{python?:import('./types').PythonExercise;prompt:string;options?:string[]|null;correct?:string|null;explanation:string}[];command?:{expected_version:number};preview?:{titles?:string[];route_titles?:string[];changes?:{action:string;title:string;before:ChapterPreview|null;after:ChapterPreview;after_title:string|null}[]}}};
export type AssistantState={paused:boolean;teacher_run_id:string|null;active_assistants:number;pending_results:number;assistants:{recovery?:RecoveryState|null;id:string;run_id:string|null;submission_id?:string|null;purpose?:string;role:string;task:string;status:string;result:string;error:string;consumed_by:string|null}[]};
export type ChatRun={recovery?:RecoveryState|null;id:string;trigger?:'user'|'assistant';course_id:string;prompt:string;answer:string;status:string;progress:string;error:string;proposals:Proposal[]};
export function aiRequest<T>(userId:string,path:string,data?:unknown,method?:string,signal?:AbortSignal){
  return accountRequest<T>('/ai'+path,data,signal??AbortSignal.timeout(45000),{method,headers:{'X-Workspace-User':userId}});
}
export async function watchRun(userId:string,id:string,signal:AbortSignal,onUpdate:(run:ChatRun)=>void){
  const response=await fetch(`/api/ai/runs/${id}/events`,{credentials:'same-origin',headers:{'X-Workspace-User':userId},signal});
  if(!response.ok||!response.body)throw new Error('无法连接回复进度，请重新读取');
  const reader=response.body.getReader(),decoder=new TextDecoder();let buffer='';
  try{while(true){
    const {value,done}=await reader.read();if(done)break;
    buffer+=decoder.decode(value,{stream:true});let end;
    while((end=buffer.indexOf('\n\n'))!==-1){const block=buffer.slice(0,end);buffer=buffer.slice(end+2);
      if(block.startsWith('event: auth_error'))throw new Error('登录已失效，请重新登录');
      const data=block.split('\n').find(line=>line.startsWith('data: '));if(data)onUpdate(JSON.parse(data.slice(6)) as ChatRun);
    }
  }}finally{reader.releaseLock();}
}
