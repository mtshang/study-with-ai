import { createContext, useCallback, useEffect, useRef, useState } from "react";
import { accountRequest, ApiError, type Account } from "./api";
import type { Assignment, Submission, Course, UpdateCourse, DisplayPreferences } from "./types";

type ServerActions = {
  userId?:string; active:boolean; busy:boolean; error:string; reload:()=>void;
  manageMaterial:(courseId:string,materialId:string,action:"edit"|"delete",data:unknown)=>Promise<boolean>;
  addMaterial:(courseId:string,data:{id:string;title:string;description:string;url?:string})=>Promise<boolean>;
  uploadMaterial:(courseId:string,id:string,file:File)=>Promise<boolean>;
  downloadMaterial:(courseId:string,id:string)=>Promise<Blob|null>;
  publish:(courseId:string,entry:Assignment,kind:"exercise"|"assignment")=>Promise<boolean>;
  submit:(courseId:string,activityId:string,answers:Record<string,string>,requestId:string,attachments:string[])=>Promise<Submission|null>;
};
export const ServerContext = createContext<ServerActions>({ active:false, busy:false, error:"", reload:()=>{},manageMaterial:async()=>false,addMaterial:async()=>false,uploadMaterial:async()=>false,downloadMaterial:async()=>null,publish:async()=>false,submit:async()=>null });
export function announceAuthChange() {
  window.dispatchEvent(new Event("study-auth-changed"));
  try { localStorage.setItem("study-with-ai:auth-change", crypto.randomUUID()); } catch { /* notification only */ }
}
export function useServerWorkspace() {
  const [account,setAccount]=useState<Account|null>(null);
  const [preferences,setPreferences]=useState<DisplayPreferences|null>(null);
  const [courses,setCourses]=useState<Course[]>([]);
  const [loading,setLoading]=useState(true);
  const [saving,setSaving]=useState(false);
  const [error,setError]=useState("");
  const [activeCourseId,setActive]=useState("");
  const owner=useRef<string|null>(null);
  const sequence=useRef(0);
  const busy=useRef(false);
  const current=useRef(courses); current.current=courses;
  const request = useCallback(<T,>(id:string,path:string,data?:unknown,method?:string) =>
    accountRequest<T>(path,data,AbortSignal.timeout(path.endsWith("/materials/upload")?120000:15000),{method,headers:{"X-Workspace-User":id}}),[]);
  const load = useCallback(async () => {
    // Reload and write share one operation boundary. An old read must not replace a newer save.
    if(busy.current)return;
    busy.current=true;setSaving(true);
    const token=++sequence.current;
    try {
      const user=await accountRequest<Account>("/auth/me",undefined,AbortSignal.timeout(10000));
      if(token!==sequence.current) return;
      if(owner.current!==user.id) { setCourses([]); setActive(""); setPreferences(null); }
      owner.current=user.id; setAccount(user);
      const list=await request<Course[]>(user.id,"/courses");
      if(token!==sequence.current) return;
      setCourses(list); setError("");
      let selected="";
      try { selected=localStorage.getItem(`study-with-ai:current-course:${user.id}`)||""; } catch { /* optional preference */ }
      setActive(list.some(c=>c.id===selected)?selected:(list.find(c=>!c.archived)?.id||""));
      const display=await request<DisplayPreferences>(user.id,"/preferences/display");
      if(token!==sequence.current)return;
      setPreferences(display);
    } catch(e) {
      if(token!==sequence.current) return;
      if(e instanceof ApiError && e.status===401) {
        owner.current=null; setAccount(null);setPreferences(null);setCourses([]);setActive("");setError("");
      } else setError(e instanceof Error?e.message:"载入课程失败，请重试");
    } finally {
      if(token===sequence.current) {busy.current=false;setSaving(false);setLoading(false);}
    }
  },[request]);
  useEffect(()=>{
    void load();
    const changed=()=>{
      // Invalidate outstanding reads/writes before loading the new identity.
      sequence.current++;busy.current=false;setSaving(false);setError("");
      owner.current=null;setAccount(null);setPreferences(null);setCourses([]);setLoading(true);
      void load();
    };
    const storage=(e:StorageEvent)=>{ if(e.key==="study-with-ai:auth-change") changed(); };
    window.addEventListener("study-auth-changed",changed);
    window.addEventListener("storage",storage);
    return ()=>{sequence.current++; busy.current=false; window.removeEventListener("study-auth-changed",changed);window.removeEventListener("storage",storage);};
  },[load]);
  const selectCourse=(id:string)=>{
    setActive(id);
    try { if(owner.current) localStorage.setItem(`study-with-ai:current-course:${owner.current}`,id); } catch { /* optional preference */ }
  };
  const perform=async(action:(id:string)=>Promise<Course>):Promise<Course|null>=>{
    if(busy.current || !owner.current) return null;
    const id=owner.current, token=sequence.current;
    busy.current=true;setSaving(true);setError("");
    try {
      const result=await action(id);
      if(token!==sequence.current || owner.current!==id) return null;
      setCourses(previous=>[result,...previous.filter(c=>c.id!==result.id)]);
      return result;
    } catch(e) {
      if(token===sequence.current) setError(e instanceof Error?e.message:"保存失败，请重试");
      return null;
    } finally {if(token===sequence.current){busy.current=false;setSaving(false);}}
  };
  const displayRequest=async(data?:DisplayPreferences):Promise<DisplayPreferences|null>=>{
    if(busy.current||!owner.current)return null;
    const userId=owner.current,token=sequence.current;
    busy.current=true;setSaving(true);setError("");
    try {
      const result=await request<DisplayPreferences>(userId,"/preferences/display",data,data?"PUT":undefined);
      if(token!==sequence.current||owner.current!==userId)return null;
      setPreferences(result);return result;
    }catch(e){
      if(token===sequence.current)setError(e instanceof Error?e.message:"设置操作失败，请重试");
      return null;
    }finally{if(token===sequence.current){busy.current=false;setSaving(false);}}
  };
  const create=(title:string,goal:string,template:number|undefined,creationId:string)=>perform(id=>request<Course>(id,"/courses",{id:creationId,title,goal,template_id:template??null},"POST"));
  const update:UpdateCourse=async(id,change)=>{
    const old=current.current.find(c=>c.id===id); if(!old) return false;
    const next=change(old);
    const result=await perform(ownerId=>request<Course>(ownerId,`/courses/${id}`,{
      version:old.version,title:next.title,goal:next.goal,archived:next.archived,
      currentChapterId:next.currentChapterId||null,
      chapters:next.chapters.map(ch=>({id:ch.id,title:ch.title,description:ch.description,content:ch.content,read:ch.read,archived:ch.archived??false}))
    },"PUT"));
    return result!==null;
  };
  const publish:ServerActions["publish"]=async(courseId,entry,kind)=>{
    const result=await perform(ownerId=>request<Course>(ownerId,`/courses/${courseId}/activities`,{
      id:entry.id,kind,title:entry.title,description:entry.description,chapter_id:entry.chapterId||null,
      questions:entry.questions.map(q=>({prompt:q.prompt,options:q.options||null,correct:q.correct??null,explanation:q.explanation,...(q.python?{python:q.python}:{})}))
    },"POST"));
    return result!==null;
  };
  const submit:ServerActions["submit"]=async(courseId,activityId,answers,requestId,attachments)=>{
    let saved:Submission|null=null;
    const result=await perform(async ownerId=>{
      const data=await request<{course:Course;submission:Submission}>(ownerId,`/courses/${courseId}/activities/${activityId}/submissions`,{request_id:requestId,answers,attachments},"POST");
      saved=data.submission;return data.course;
    });
    return result?saved:null;
  };
  const manageMaterial:ServerActions["manageMaterial"]=async(courseId,materialId,action,data)=>
    !!await perform(ownerId=>request<Course>(ownerId,`/courses/${courseId}/materials/${materialId}${action==="delete"?"/delete":""}`,data,action==="delete"?"POST":"PUT"));
  const addMaterial:ServerActions["addMaterial"]=async(courseId,data)=>
    !!await perform(ownerId=>request<Course>(ownerId,`/courses/${courseId}/materials`,data,"POST"));
  const uploadMaterial:ServerActions["uploadMaterial"]=async(courseId,id,file)=>{
    const form=new FormData();form.set("material_id",id);form.set("file",file);
    return !!await perform(ownerId=>request<Course>(ownerId,`/courses/${courseId}/materials/upload`,form,"POST"));
  };
  const downloadMaterial:ServerActions["downloadMaterial"]=async(courseId,id)=>{
    if(busy.current||!owner.current)return null;
    const userId=owner.current,token=sequence.current;
    busy.current=true;setSaving(true);setError("");
    try {
      const blob=await accountRequest<Blob>(`/courses/${courseId}/materials/${id}/download`,undefined,AbortSignal.timeout(120000),
        {responseType:"blob",headers:{"X-Workspace-User":userId}});
      return token===sequence.current&&owner.current===userId?blob:null;
    } catch(e) {
      if(token===sequence.current)setError(e instanceof Error?e.message:"下载失败，请重试");
      return null;
    } finally {if(token===sequence.current){busy.current=false;setSaving(false);}}
  };
  return {account,preferences,savePreferences:displayRequest,reloadPreferences:()=>displayRequest(),courses,loading,saving,error,activeCourseId,selectCourse,create,update,publish,submit,manageMaterial,addMaterial,uploadMaterial,downloadMaterial,reload:()=>{void load();}};
}
