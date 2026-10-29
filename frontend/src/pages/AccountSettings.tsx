import {PersonaSettings} from './PersonaSettings';
import {ApiSettings} from "./ApiSettings";
import {useState} from "react";
import type {DisplayPreferences} from "../types";
import {PageTitle} from "../components/ui";

export function AccountSettings({userId,username,preferences,busy,save,reload,toast}:{
  userId:string;username:string;preferences:DisplayPreferences|null;busy:boolean;
  save:(data:DisplayPreferences)=>Promise<DisplayPreferences|null>;
  reload:()=>Promise<DisplayPreferences|null>;toast:(message:string)=>void;
}) {
  // Keep the draft and its original version on errors or unrelated workspace reloads.
  const [draft,setDraft]=useState<DisplayPreferences|null>(null);
  const value=draft||preferences;
  const dirty=!!draft&&(draft.fontOffset!==preferences?.fontOffset||draft.compact!==preferences?.compact);
  return <>
    <PageTitle eyebrow="MAKE IT YOURS" title="设置" description="管理个人模型、AI 操作权限与显示偏好。"/>
    <div className="settings-layout">
      <ApiSettings userId={userId}/>
      <PersonaSettings key={userId} userId={userId}/>
      <section className="panel settings-panel">
        <h2>当前账号</h2><p>{username}</p><a className="text-link" href="#/account">前往账号与登录</a>
      </section>
      <section className="panel settings-panel">
        <h2>显示偏好</h2><p className="muted">保存后应用到当前账号；换浏览器登录也可恢复。</p>
        {value?<form onSubmit={async e=>{e.preventDefault();const result=await save(value);if(result){setDraft(null);toast("显示设置已保存");}}}>
          <fieldset disabled={busy} className="settings-fields">
            <div className="setting-row font-setting"><div><strong>整体字号增量</strong><p>默认增加 3px，保存后应用。</p></div>
              <label className="font-control">字号<select aria-label="整体字号增量" value={value.fontOffset} onChange={e=>setDraft({...value,fontOffset:Number(e.target.value)})}>
                {[0,1,2,3,4,5,6].map(n=><option key={n} value={n}>+{n} px</option>)}
              </select></label>
            </div>
            <div className="setting-row"><div><strong>紧凑布局</strong><p>缩小页面留白，在一屏内展示更多内容。</p></div>
              <button type="button" role="switch" aria-label="紧凑布局" aria-checked={value.compact} className={`switch ${value.compact?"on":""}`} onClick={()=>setDraft({...value,compact:!value.compact})}><span/></button>
            </div>
            <div className="button-row"><button className="button primary" disabled={!dirty}>保存显示设置</button>
              <button type="button" className="button" onClick={async()=>{const result=await reload();if(result){setDraft(null);toast("已读取保存的设置");}}}>重新读取已保存设置</button>
            </div>
            <p className="fine-print">重新读取会放弃这里未保存的调整；保存失败时保留当前选择。</p>
          </fieldset>
        </form>:<><p className="muted">显示设置尚未载入，暂用默认显示。</p><button className="button" disabled={busy} onClick={()=>void reload()}>重新读取已保存设置</button></>}
      </section>

    </div>
  </>;
}
