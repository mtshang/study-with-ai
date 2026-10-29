import { useContext, useRef, useState } from "react";
import { ArrowRight, Download, FileText, Link2, Search, Upload } from "lucide-react";
import type { Course, Material } from "../types";
import { sourceLabels, uid } from "../data";
import { saveDownloadedFile } from "../download";
import { ServerContext } from "../serverWorkspace";
import { Badge, Empty, Modal, PageTitle } from "../components/ui";

export function ServerMaterials({course,toast}:{course:Course;toast:(text:string)=>void}) {
  const server=useContext(ServerContext);
  const [search,setSearch]=useState("");
  const [source,setSource]=useState("all");
  const [managing,setManaging]=useState<{material:Material;action:"edit"|"delete";version:number}|null>(null);
  const [preview,setPreview]=useState<Material|null>(null);
  const [editor,setEditor]=useState<{id:string;kind:"note"|"file"}|null>(null);
  const items=course.materials.filter(m=>(source==="all"||m.source===source)&&m.title.toLowerCase().includes(search.toLowerCase()));
  const download=async(material:Material)=>{
    const blob=await server.downloadMaterial(course.id,material.id);
    if(!blob)return;
    saveDownloadedFile(blob,material.filename||material.title);
  };
  return <>
    <PageTitle eyebrow="YOUR KNOWLEDGE SHELF" title="课程资料" description="保存教材、网页链接和自己的笔记。"
      action={<div className="button-row"><button className="button" disabled={server.busy} onClick={()=>setEditor({id:uid(),kind:"note"})}><Link2 size={16}/>添加链接或笔记</button>
        <button className="button primary" disabled={server.busy} onClick={()=>setEditor({id:uid(),kind:"file"})}><Upload size={16}/>上传资料</button></div>}/>
    <div className="toolbar"><div className="tab-row" role="group" aria-label="资料来源筛选">
      {[["all","全部资料"],...Object.entries(sourceLabels)].map(([key,label])=><button key={key} className={source===key?"selected":""} onClick={()=>setSource(key)}>{label}</button>)}
    </div><div className="search-field"><Search size={16}/><input aria-label="搜索资料" placeholder="搜索资料名称" value={search} onChange={e=>setSearch(e.target.value)}/></div></div>
    <div className="material-grid">{items.map(m=><button className="panel material-card" key={m.id} onClick={()=>setPreview(m)}>
      <div className="section-heading"><span className={`material-icon ${m.source}`}>{m.kind==="链接"?<Link2 size={23}/>:<FileText size={23}/>}</span><Badge>{sourceLabels[m.source]}</Badge></div>
      <h3>{m.title}</h3><p>{m.description}</p><div className="material-footer"><span>{m.kind}</span><span>查看详情 →</span></div>
    </button>)}</div>
    {!items.length&&<Empty title="这里还没有资料" description="上传一份教材，添加一个链接，或者记录自己的想法。"/>}
    <p className="fine-print">文件每份最多 10 MiB，可保存和下载。支持在 AI 聊天中要求阅读笔记、UTF-8 TXT/Markdown、文字 PDF、DOCX 和 PPTX。网页链接只保存地址；扫描件暂不支持。</p>
    {preview&&<Modal title={preview.title} wide onClose={()=>setPreview(null)}>
      <Badge>{sourceLabels[preview.source]}</Badge><div className="prose material-description">{preview.description}</div>
      {preview.url&&/^https?:\/\//i.test(preview.url)&&<a className="button primary" href={preview.url} target="_blank" rel="noopener noreferrer">打开来源网页<ArrowRight size={16}/></a>}
      {preview.downloadable&&<button className="button primary" disabled={server.busy} onClick={()=>void download(preview)}><Download size={16}/>下载原文件</button>}
      <div className="modal-actions"><button className="button" disabled={server.busy} onClick={()=>{setManaging({material:preview,action:"edit",version:course.version||1});setPreview(null);}}>编辑资料</button><button className="button" disabled={server.busy} onClick={()=>{setManaging({material:preview,action:"delete",version:course.version||1});setPreview(null);}}>删除资料</button></div>
    </Modal>}
    {managing&&<ManageMaterial courseId={course.id} {...managing} onClose={()=>setManaging(null)} onSaved={()=>{toast(managing.action==="delete"?"资料已删除，历史附件仅保留名称":"资料已更新");setManaging(null);}}/>}
    {editor&&<MaterialEditor key={editor.id} courseId={course.id} id={editor.id} kind={editor.kind} onClose={()=>setEditor(null)} onSaved={()=>{setEditor(null);toast("资料已保存");}}/>}
  </>;
}

function MaterialEditor({courseId,id,kind,onClose,onSaved}:{courseId:string;id:string;kind:"note"|"file";onClose:()=>void;onSaved:()=>void}) {
  const server=useContext(ServerContext);
  const [title,setTitle]=useState("");
  const [url,setUrl]=useState("");
  const [description,setDescription]=useState("");
  const [file,setFile]=useState<File|null>(null);
  const [error,setError]=useState("");
  return <Modal title={kind==="file"?"上传资料":"添加资料"} onClose={onClose}>
    <form onSubmit={async e=>{
      e.preventDefault();setError("");
      if(kind==="file") {
        if(!file)return;
        if(file.size>10*1024*1024){setError("每份文件最多 10 MiB，请选择较小的文件。");return;}
        if(await server.uploadMaterial(courseId,id,file))onSaved();
      }else{
        if(!title.trim())return;
        if(await server.addMaterial(courseId,{id,title:title.trim(),description:description.trim(),url:url.trim()||undefined}))onSaved();
      }
    }}>
      {kind==="file"?<label className="field">选择文件<input aria-label="选择文件" type="file" required onChange={e=>{setFile(e.target.files?.[0]||null);setError("");}}/><small>每次上传一份，最多 10 MiB。上传后保留原文件，不自动执行或解析。</small></label>:<>
        <label className="field">标题<input data-autofocus required maxLength={200} value={title} onChange={e=>setTitle(e.target.value)}/></label>
        <label className="field">来源网址 <small>选填</small><input type="url" maxLength={2048} placeholder="https://" value={url} onChange={e=>setUrl(e.target.value)}/></label>
        <label className="field">内容或说明<textarea rows={5} maxLength={10000} value={description} onChange={e=>setDescription(e.target.value)}/></label>
      </>}
      {error&&<p role="alert" className="account-error">{error}</p>}
      <div className="modal-actions"><button type="button" className="button" onClick={onClose}>取消</button><button className="button primary" disabled={server.busy||(kind==="file"?!file:!title.trim())}>{kind==="file"?"保存文件":"保存资料"}</button></div>
    </form>
  </Modal>;
}


function ManageMaterial({courseId,material,action,version,onClose,onSaved}:{courseId:string;material:Material;action:"edit"|"delete";version:number;onClose:()=>void;onSaved:()=>void}){
  const server=useContext(ServerContext);
  const [title,setTitle]=useState(material.title),[description,setDescription]=useState(material.description),[url,setUrl]=useState(material.url||'');
  const operation=useRef<{signature:string;id:string}|null>(null);
  async function save(){
    const body=action==='delete'?{expected_version:version}:{expected_version:version,title:title.trim(),description:description.trim(),url:url.trim()||null};
    const signature=JSON.stringify(body);
    if(operation.current?.signature!==signature)operation.current={signature,id:crypto.randomUUID()};
    if(await server.manageMaterial(courseId,material.id,action,{...body,id:operation.current.id}))onSaved();
  }
  return <Modal title={action==='delete'?'永久删除资料？':'编辑资料'} onClose={onClose}>
    <form onSubmit={e=>{e.preventDefault();void save();}}>
      {action==='delete'?<><p>删除「{material.title}」及其原文件，无法恢复，不进入回收站。</p><p>历史作业提交仅保留当时的附件名称，原文件将无法下载；已有答案和批改结果不删除。</p></>:<>
        <label className="field">资料标题<input data-autofocus required maxLength={200} value={title} onChange={e=>setTitle(e.target.value)}/></label>
        {material.kind!=='文件'&&<label className="field">来源网址<input type="url" maxLength={2048} value={url} onChange={e=>setUrl(e.target.value)}/></label>}
        <label className="field">内容或说明<textarea aria-label="内容或说明" rows={6} maxLength={10000} value={description} onChange={e=>setDescription(e.target.value)}/></label>
        {material.kind==='文件'&&<p className="fine-print">修改展示标题和说明，不替换原文件或历史附件名称。更换文件请另外上传。</p>}
      </>}
      <p className="fine-print">若提示版本冲突，请重新载入后关闭此窗口，再打开资料核对；不会覆盖其他页面的修改。</p>
      <div className="modal-actions"><button className="button" type="button" onClick={onClose}>取消</button><button className="button primary" disabled={server.busy||(action==='edit'&&!title.trim())}>{action==='delete'?'确认永久删除':'保存修改'}</button></div>
    </form>
  </Modal>;
}
