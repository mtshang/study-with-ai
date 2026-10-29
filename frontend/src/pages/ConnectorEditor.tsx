import {useRef,useState,type InputHTMLAttributes} from "react";
import {FolderUp,Upload,FileArchive,Braces} from "lucide-react";
import {Modal} from "../components/ui";

// Streamable HTTP endpoint configuration; this example is not a real service.
const defaultConfig=JSON.stringify({mcpServers:{server:{url:"https://mcp.example.com/mcp",headers:{}}}},null,2);
export type Draft={name:string;description:string;configuration?:string;files?:File[]};
const isObject=(value:unknown):value is Record<string,unknown>=>!!value&&typeof value==="object"&&!Array.isArray(value);
function configError(text:string):string {
  let parsed:unknown;try{parsed=JSON.parse(text);}catch{return "JSON 格式不正确，请检查引号、逗号和括号。";}
  if(!isObject(parsed)||!isObject(parsed.mcpServers)||!Object.keys(parsed.mcpServers).length)return "需要非空的 mcpServers 对象。";
  if(Object.keys(parsed.mcpServers).length!==1)return "每个连接器配置一个服务。";
  for(const server of Object.values(parsed.mcpServers)){
    if(!isObject(server)||typeof server.url!=="string"||!server.url.startsWith("https://"))return "请填写 HTTPS 服务地址 url。";
    if(Object.keys(server).some(k=>!['url','headers'].includes(k)))return "本轮仅支持 url 和 headers，不支持本地命令。";
    if(server.headers!==undefined&&(!isObject(server.headers)||!Object.values(server.headers).every(v=>typeof v==='string')))return "headers 必须是字符串键值对象。";
  }
  return "";
}

export function ConnectorEditor({kind,onClose,onSave,live=false,initial}:{kind:"skill"|"MCP";onClose:()=>void;onSave:(entry:Draft)=>void|Promise<void>;live?:boolean;initial?:{name:string;configuration:string}}) {
  const skill=kind==="skill";
  const [name,setName]=useState(initial?.name||"");
  const [saving,setSaving]=useState(false);
  const [files,setFiles]=useState<File[]>([]);
  const [error,setError]=useState("");
  const [dragging,setDragging]=useState(false);
  const [config,setConfig]=useState(initial?.configuration||defaultConfig);
  const picker=useRef<HTMLInputElement>(null),directory=useRef<HTMLInputElement>(null),zip=useRef<HTMLInputElement>(null);
  const gutter=useRef<HTMLDivElement>(null);
  const directoryAttributes={webkitdirectory:""} as InputHTMLAttributes<HTMLInputElement>;
  const selectFiles=(selection:File[])=>{
    setError("");setFiles([]);
    if(!selection.length)return;
    const folder=selection.some(f=>f.webkitRelativePath);
    if(folder){
      if(!selection.some(f=>f.name==="SKILL.md")){setError("文件夹中需要包含 SKILL.md。");return;}
    }else if(selection.length!==1||! /\.(md|zip)$/i.test(selection[0].name)){
      setError("请选择一个 .md 或 .zip 文件；文件夹请使用“选择文件夹”。");return;
    }
    setFiles(selection);
  };
  const check=configError(config);
  return <Modal title={skill?"导入技能":"添加 MCP 连接器"} wide onClose={onClose}>
    <form className="connector-editor" onSubmit={async e=>{
      e.preventDefault();if(!name.trim()||saving)return;
      if(skill&&!files.length)return;if(!skill&&check){setError(check);return;}
      setSaving(true);setError('');try{await onSave({name:name.trim(),description:skill?`技能包 · ${files.length} 个文件`:'MCP 配置',files:skill?files:undefined,configuration:skill?undefined:JSON.stringify(JSON.parse(config),null,2)});}catch(e){setError(e instanceof Error?e.message:'保存失败');}finally{setSaving(false);}
    }}>
      <label className="field">{skill?"技能名称":"连接器名称"}<input required data-autofocus maxLength={60} value={name} onChange={e=>setName(e.target.value)} placeholder={skill?"例如：循序渐进讲解":"例如：课程工具"}/></label>
      {skill?<>
        <button type="button" className={`skill-dropzone ${dragging?"dragging":""}`} onClick={()=>picker.current?.click()}
          onDragOver={e=>{e.preventDefault();setDragging(true);}} onDragLeave={()=>setDragging(false)}
          onDrop={e=>{e.preventDefault();setDragging(false);selectFiles(Array.from(e.dataTransfer.files));}}>
          <FolderUp size={38}/><strong>拖拽文件或点击上传</strong><span>{files.length?`已选择：${files.length===1?files[0].name:`${files.length} 个文件`}`:"支持 .md、.zip；文件夹请使用下方按钮"}</span>
        </button>
        <input hidden ref={picker} aria-label="选择技能文件" type="file" accept=".md,.zip" onChange={e=>{selectFiles(Array.from(e.target.files||[]));e.target.value="";}}/>
        <input hidden ref={zip} aria-label="选择技能 ZIP 文件" type="file" accept=".zip" onChange={e=>{selectFiles(Array.from(e.target.files||[]));e.target.value="";}}/>
        <input hidden ref={directory} aria-label="选择技能文件夹" type="file" {...directoryAttributes} onChange={e=>{selectFiles(Array.from(e.target.files||[]));e.target.value="";}}/>
        <div className="skill-requirements"><h3>文件要求</h3><ul>
          <li>文件夹或 ZIP 包中需要包含 SKILL.md 文件。</li>
          <li>SKILL.md 开头需包含 YAML 格式的 name 和 description。</li>
        </ul><p className="fine-print">上方技能名称用于页面展示，可以使用中文；文件内部的 name 按技能规范填写。导入时检查包内路径和 YAML。脚本仅保存，不执行。</p></div>
        <div className="button-row"><button type="button" className="text-link" onClick={()=>zip.current?.click()}><FileArchive size={16}/>选择 ZIP 文件</button><button type="button" className="text-link" onClick={()=>directory.current?.click()}><Upload size={16}/>选择文件夹</button></div>
      </>:<>
        <div className="choice-heading"><strong>MCP 配置（JSON）</strong><button type="button" className="text-link" onClick={()=>{if(check){setError(check);return;}setConfig(JSON.stringify(JSON.parse(config),null,2));setError("");}}><Braces size={16}/>格式化</button></div>
        <div className="mcp-code-editor"><div className="mcp-line-numbers" aria-hidden="true" ref={gutter}>{config.split("\n").map((_,i)=><div key={i}>{i+1}</div>)}</div>
          <textarea aria-label="MCP 配置（JSON）" spellCheck={false} maxLength={20000} wrap="off" value={config} onChange={e=>{setConfig(e.target.value);setError("");}} onScroll={e=>{if(gutter.current)gutter.current.scrollTop=e.currentTarget.scrollTop;}}/>
        </div>
        <p className="fine-print">请替换示例地址为公网 HTTPS Streamable HTTP 服务。可用 headers 配置 Authorization 或 X-API-Key；编辑时省略 headers 保留原凭据，填写 {} 清空。更换地址需重填或清空凭据。</p>
        <a className="text-link" href="https://modelcontextprotocol.io/specification/2025-11-25/basic/transports" target="_blank" rel="noopener noreferrer">查看官方传输协议</a>
      </>}
      {error&&<p role="alert" className="account-error">{error}</p>}
      <p className="fine-print">{live?"保存到个人库；课程中需单独启用。MCP 保存后需发现工具并确认权限。":"当前为演示草稿，刷新后重置，不上传或执行。"}</p>
      <div className="modal-actions"><button type="button" className="button" onClick={onClose}>取消</button><button className="button primary" disabled={saving||!name.trim()||(skill&&!files.length)}>{saving?"保存中…":live?"保存":"保存草稿"}</button></div>
    </form>
  </Modal>;
}
