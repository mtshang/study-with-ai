import {useEffect,useState} from 'react';
import {aiRequest,type ModelSettings} from '../ai';

export function ApiSettings({userId}:{userId?:string}){
  const [tab,setTab]=useState<'chat'|'vision'|'embedding'>('chat');
  const [saved,setSaved]=useState<ModelSettings|null>(null);
  const [base,setBase]=useState(''),[model,setModel]=useState(''),[key,setKey]=useState('');
  const [permission,setPermission]=useState<ModelSettings['permission']>('manual');
  const [clear,setClear]=useState(false),[busy,setBusy]=useState(false),[message,setMessage]=useState('');
  const fill=(data:ModelSettings,channel=tab)=>{setBase(data[channel].base_url);setModel(data[channel].model);setKey('');setClear(false);setPermission(data.permission);};
  useEffect(()=>{if(!userId)return;const abort=new AbortController();
    aiRequest<ModelSettings>(userId,'/config',undefined,undefined,abort.signal).then(data=>{setSaved(data);fill(data,'chat');}).catch(e=>{if(!abort.signal.aborted)setMessage(e.message);});
    return()=>abort.abort();
  },[userId]);
  const dirty=!!saved&&(base!==saved[tab].base_url||model!==saved[tab].model||!!key||clear||permission!==saved.permission);
  async function action(kind:'save'|'test'|'reload'){
    if(!userId)return;setBusy(true);setMessage('');
    try{
      if(kind==='test'){
        const result=await aiRequest<{message:string}>(userId,`/config/${tab}/test`,{});setMessage(result.message);return;
      }
      const data=kind==='reload'?await aiRequest<ModelSettings>(userId,'/config'):await aiRequest<ModelSettings>(userId,'/config',{
        revision:saved!.revision,channel:tab,base_url:base,model,api_key:key||null,clear_key:clear,permission
      },'PUT');
      setSaved(data);fill(data);setMessage(kind==='save'?'API 设置已保存':'已重新读取配置');
    }catch(e){setMessage(e instanceof Error?e.message:'设置操作失败');}finally{setBusy(false);}
  }
  return <section className="panel settings-panel api-settings">
    <h2>API 设置</h2>
    <div role="tablist" aria-label="模型类型" className="api-tabs">{(['chat','vision','embedding'] as const).map(channel=><button key={channel} type="button" role="tab" aria-selected={tab===channel} disabled={busy} className={tab===channel?'selected':''} onClick={()=>{setTab(channel);if(saved)fill(saved,channel);setMessage('');}}>{channel==='chat'?'聊天模型':channel==='vision'?'视觉模型':'向量化模型'}</button>)}</div>
    {!userId?<p>登录后可设置个人模型。<a href="#/account">前往账号与登录</a></p>:<>
      <p className="muted">{tab==='embedding'?'用于资料索引与语义检索。请填写兼容 /embeddings 的 HTTPS 基础地址（通常以 /v1 结尾）；建立索引会把资料文字发送给该供应商。更换模型或地址后需要重建索引。':tab==='chat'?'用于课程内聊天和练习生成。':'用于视觉模型配置与图片连接测试；课程内图片上传对话尚未开放。'}</p>
      {saved&&<form onSubmit={e=>{e.preventDefault();void action('save');}}>
        <fieldset className="settings-fields" disabled={busy}>
          <label>接口基础地址<input aria-label="接口基础地址" type="url" placeholder="https://api.deepseek.com" value={base} onChange={e=>setBase(e.target.value)}/></label>
          <label>模型名称<input aria-label="模型名称" value={model} onChange={e=>setModel(e.target.value)} placeholder="填写供应商提供的模型标识"/></label>
          <label>API Key<input aria-label="API Key" type="password" autoComplete="new-password" value={key} disabled={clear} placeholder={saved[tab].key_set?'已设置；留空保留原 Key':'尚未设置'} onChange={e=>setKey(e.target.value)}/></label>
          <label className="inline-check"><input type="checkbox" checked={clear} onChange={e=>{setClear(e.target.checked);setKey('');}}/>清除当前模型的 Key</label>
          {tab==='chat'&&<label>AI 操作权限<select aria-label="AI 操作权限" value={permission} onChange={e=>setPermission(e.target.value as ModelSettings['permission'])}>
            <option value="manual">完全手动：修改和发布前由我批准</option><option value="assisted">部分帮我批准：允许教学操作与无冲突记忆记录</option><option value="full">完全访问：在已开放工具范围内执行</option>
          </select></label>}
          <div className="button-row"><button className="button primary" disabled={!dirty}>保存 API 设置</button><button type="button" className="button" disabled={dirty||!saved[tab].key_set} onClick={()=>void action('test')}>测试连接</button><button type="button" className="button" onClick={()=>void action('reload')}>重新读取 API 设置</button></div>
          <p className="fine-print">Key 不会回显；测试连接会发起一次小请求。切换分页会放弃当前未保存的编辑。</p>
        </fieldset>
      </form>}
      {!saved&&<button className="button" disabled={busy} onClick={()=>void action('reload')}>重新读取 API 设置</button>}
      <p role="status">{busy?'正在处理…':message}</p>
    </>}
  </section>;
}
