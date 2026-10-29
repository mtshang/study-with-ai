import { useEffect, useState } from "react";
import {
  BookOpen,
  LayoutGrid,
  Settings as SettingsIcon,
  Plus,
  Plug,
  ArrowLeft,
  MessageSquare,
  ListTree,
  NotebookPen,
  PencilLine,
  FolderOpen,
  Trash2,
  History,
  PanelLeftClose,
  PanelLeftOpen,
  Sparkles,
  ShieldCheck,
  GraduationCap,
  UserRound,
} from "lucide-react";
import { createCourse, templates, uid } from "./data";
import { useWorkspace } from "./store";
import { ServerContext, useServerWorkspace } from "./serverWorkspace";
import { CourseIcon, Modal } from "./components/ui";
import { Home, Templates, Settings } from "./pages/WorkspacePages";
import { Connectors } from "./pages/Connectors";
import { AccountSettings } from "./pages/AccountSettings";
import { AccountPage } from "./pages/AccountPage";
import { CoursePage } from "./pages/CoursePages";

export const navigate = (path: string) => {
  window.location.hash = path;
};
const courseNavigation = [
  ["overview", "课程概览", LayoutGrid],
  ["chat", "AI 导师", MessageSquare],
  ["chapters", "章节", BookOpen],
  ["chapter-trash", "章节回收站", Trash2],
  ["roadmap", "学习路线", ListTree],
  ["exercises", "练习", PencilLine],
  ["exercise-trash", "练习回收站", Trash2],
  ["assignments", "作业", NotebookPen],
  ["assignment-trash", "作业回收站", Trash2],
  ["materials", "资料", FolderOpen],
  ["artifacts", "生成产物", FolderOpen],
  ["history", "学习记录", History],
] as const;

export default function App() {
  const { state: demoState, setState, updateCourse: demoUpdate, storageError } = useWorkspace();
  const server = useServerWorkspace();
  const [showDemo,setShowDemo] = useState(false);
  const personal = !!server.account && !showDemo;
  const state = personal ? { ...demoState, courses:server.courses, activeCourseId:server.activeCourseId, settings:{...demoState.settings,name:server.account!.username,fontOffset:server.preferences?.fontOffset??3,compact:server.preferences?.compact??false} } : demoState;
  const updateCourse = personal ? server.update : demoUpdate;

  const [route, setRoute] = useState(location.hash.slice(1) || "/");
  const [mobileOpen, setMobileOpen] = useState(false);
  const [toast, setToast] = useState("");
  const [create, setCreate] = useState<{ template?: number; id:string } | null>(null);
  const [title, setTitle] = useState("");
  const [goal, setGoal] = useState("");
  useEffect(()=>{
    setShowDemo(false);
    // Personal drafts must not cross account boundaries or become demo content after logout.
    setCreate(null);setTitle("");setGoal("");setToast("");
  },[server.account?.id]);
  useEffect(() => {
    const change = () => {
      setRoute(location.hash.slice(1) || "/");
      setMobileOpen(false);
      window.scrollTo(0, 0);
    };
    window.addEventListener("hashchange", change);
    return () => window.removeEventListener("hashchange", change);
  }, []);
  useEffect(() => {
    if (!toast) return;
    const timer = setTimeout(() => setToast(""), 3800);
    return () => clearTimeout(timer);
  }, [toast]);
  const parts = route.split("/").filter(Boolean);
  const course =
    parts[0] === "courses"
      ? state.courses.find((item) => item.id === parts[1])
      : undefined;
  const tab = parts[2] || "overview";
  const globalPage = parts[0] || "home";
  const currentLabel = course
    ? courseNavigation.find((item) => item[0] === tab)?.[1] || "课程概览"
    : globalPage === "account"
      ? "账号与登录"
      : globalPage === "settings"
        ? "设置"
        : globalPage === "templates"
          ? "课程模板"
          : globalPage === "connectors"
            ? "技能·连接器"
            : "我的课程";
  useEffect(() => {
    document.title = `${currentLabel} · Study with AI`;
  }, [currentLabel]);
  useEffect(() => {
    document.documentElement.style.setProperty(
      "--font-offset",
      `${state.settings.fontOffset}px`,
    );
  }, [state.settings.fontOffset]);
  const openCreate = (template?: number) => {
    setCreate({ template, id:uid() });
    setTitle(template === undefined ? "" : templates[template].title);
    setGoal(template === undefined ? "" : templates[template].goal);
  };
  const openCourse = (id: string, target = "overview") => {
    if(personal) server.selectCourse(id);
    else setState((previous) => ({ ...previous, activeCourseId: id }));
    navigate(`/courses/${id}/${target}`);
  };
  return (
    <ServerContext.Provider value={{active:personal,userId:personal?server.account!.id:undefined,busy:personal && server.saving,error:personal?server.error:"",reload:server.reload,publish:server.publish,submit:server.submit,manageMaterial:server.manageMaterial,addMaterial:server.addMaterial,uploadMaterial:server.uploadMaterial,downloadMaterial:server.downloadMaterial}}>
    <div className={`app-shell ${state.settings.compact ? "compact" : ""}`}>
      <header className="global-header">
        <button
          className="icon-button mobile-toggle"
          aria-label="切换导航"
          aria-expanded={mobileOpen}
          onClick={() => setMobileOpen(!mobileOpen)}
        >
          {mobileOpen ? (
            <PanelLeftClose size={20} />
          ) : (
            <PanelLeftOpen size={20} />
          )}
        </button>
        <a className="brand" href="#/">
          <span className="brand-mark">
            <BookOpen size={23} />
          </span>
          <span>
            Study with AI<small>让好奇心，有迹可循</small>
          </span>
        </a>
        <nav className="global-nav" aria-label="主导航">
          <a
            href="#/"
            className={course || globalPage === "home" ? "active" : ""}
          >
            <LayoutGrid size={19} />
            我的课程
          </a>
          <a
            href="#/templates"
            className={globalPage === "templates" ? "active" : ""}
          >
            <Sparkles size={19} />
            课程模板
          </a>
          <a
            href="#/connectors"
            className={globalPage === "connectors" ? "active" : ""}
          >
            <Plug size={19} />
            技能·连接器
          </a>
        </nav>
        <div className="workspace-label header-workspace">
          <span className="workspace-name">个人学习空间</span>
          <span>{personal ? "账号空间" : "DEMO"}</span>
          {server.account && <button className="text-link" onClick={()=>{setShowDemo(!showDemo);navigate("/");}}>{personal?"查看演示":"回到个人课程"}</button>}
        </div>
      </header>
      {mobileOpen && (
        <button
          className="sidebar-scrim"
          aria-label="关闭导航"
          onClick={() => setMobileOpen(false)}
        />
      )}
      <aside className={`sidebar ${mobileOpen ? "open" : ""}`}>
        <div className="sidebar-scroll">
          {course ? (
            <>
              <button className="back-link" onClick={() => navigate("/")}>
                <ArrowLeft size={14} />
                全部课程
              </button>
              <div className="sidebar-course">
                <CourseIcon course={course} size={18} />
                <span>{course.title}</span>
              </div>
              <nav aria-label="课程导航">
                {courseNavigation.map(([key, label, Icon]) => (
                  <a
                    key={key}
                    href={`#/courses/${course.id}/${key}`}
                    className={tab === key ? "active" : ""}
                  >
                    <Icon size={18} />
                    {label}
                    {key === "assignments" && (
                      <span className="nav-count">
                        {course.assignments.length}
                      </span>
                    )}
                  </a>
                ))}
              </nav>
            </>
          ) : (
            <>
              <div className="nav-section-title">最近学习</div>
              <nav>
                {state.courses
                  .filter((c) => !c.archived)
                  .slice(0, 3)
                  .map((c) => (
                    <button
                      className="recent-link"
                      key={c.id}
                      onClick={() => openCourse(c.id)}
                    >
                      <span className={`dot ${c.color}`} />
                      <span>{c.title}</span>
                    </button>
                  ))}
              </nav>
              <button className="sidebar-new" onClick={() => openCreate()}>
                <Plus size={16} />
                创建一门新课程
              </button>
            </>
          )}
          <div className="sidebar-tip">
            <GraduationCap size={23} />
            <strong>按你的节奏，学你想学。</strong>
            <p>每门课程都是一个独立的探索空间。</p>
          </div>
        </div>
        <div className="sidebar-bottom">
          <nav>
            <a
              href="#/account"
              className={globalPage === "account" ? "active" : ""}
            >
              <UserRound size={18} />
              账号与登录
            </a>
            <a
              className={globalPage === "settings" ? "active" : ""}
              href="#/settings"
            >
              <SettingsIcon size={18} />
              设置
            </a>

          </nav>
          <div className="profile">
            <span className="avatar">
              {state.settings.name.slice(0, 1) || "学"}
            </span>
            <div>
              <strong>{state.settings.name}</strong>
              <small>{personal ? "个人账号空间" : "本地演示空间"}</small>
            </div>
            <ShieldCheck size={17} />
          </div>
        </div>
      </aside>
      <div className="main-shell">
        {storageError && (
          <div role="alert" className="storage-warning">
            浏览器存储空间不足或不可用，当前修改可能无法保留。请到设置导出数据。
          </div>
        )}
        {server.error && <div role="alert" className="storage-warning">{server.error} <button className="button small" disabled={server.saving || server.loading} onClick={server.reload}>重新载入</button></div>}
        {personal && <div role="status" className="server-status">{server.saving ? "正在处理服务器请求…" : "课程、章节与作答记录保存在服务器；单道开放练习支持 AI 批改。"}</div>}
        <main
          id="main-content"
          className={
            course && tab === "chat" ? "main-content chat-main" : "main-content"
          }
          key={course?.id || globalPage}
        >
          {server.loading && globalPage !== "account" ? <p role="status">正在载入学习空间…</p> : course && personal && !["overview","chapters","roadmap","history","exercises","assignments","materials","artifacts","chat","chapter-trash","exercise-trash","assignment-trash"].includes(tab) ? <div className="empty"><h1>这项功能正在接入</h1><p>当前个人空间已支持课程、章节、练习、作业和资料。此页面尚未开放。</p><button className="button" onClick={()=>{setShowDemo(true);navigate("/");}}>查看本地演示</button></div> : course ? (
            <CoursePage
              course={course}
              tab={tab}
              update={updateCourse}
              permission={state.settings.permission}
              toast={setToast}
            />
          ) : parts[0] === "courses" ? (
            <div className="empty">
              <h1>没有找到这门课程</h1>
              <p>它可能已被删除，或当前浏览器还没有这份数据。</p>
              <button className="button primary" onClick={() => navigate("/")}>
                返回我的课程
              </button>
            </div>
          ) : globalPage === "templates" ? (
            <Templates onCreate={openCreate} />
          ) : globalPage === "connectors" ? (
            <Connectors />
          ) : globalPage === "account" ? (
            <AccountPage />
          ) : globalPage === "settings" ? (
            personal ? <AccountSettings key={server.account!.id} userId={server.account!.id} username={server.account!.username} preferences={server.preferences} busy={server.saving} save={server.savePreferences} reload={server.reloadPreferences} toast={setToast}/>
              : <Settings state={demoState} setState={setState} toast={setToast} />
          ) : (
            <Home
              state={state}
              openCreate={openCreate}
              openCourse={openCourse}
              update={updateCourse}
            />
          )}
        </main>
        <footer className="app-footer">
          <span>STUDY WITH AI</span>
          <span>一点好奇，一次进步。</span>
          <span>{personal ? "账号与课程服务 v0.2" : "本地演示 v0.1"}</span>
        </footer>
      </div>
      {toast && (
        <div className="toast" role="status">
          <ShieldCheck size={18} />
          {toast}
          <button aria-label="关闭提示" onClick={() => setToast("")}>
            ×
          </button>
        </div>
      )}
      {create && (
        <Modal title="开启一段新的学习" onClose={() => setCreate(null)}>
          <form
            onSubmit={async (event) => {
              event.preventDefault();
              if (!title.trim()) return;
              if(personal) {
                const c=await server.create(title.trim(),goal.trim(),create.template,create.id);
                if(!c) return;
                server.selectCourse(c.id);setCreate(null);navigate(`/courses/${c.id}/overview`);setToast("课程已保存到账号");return;
              }
              const c = createCourse(
                title.trim(),
                goal.trim(),
                create.template,
              );
              setState((previous) => ({
                ...previous,
                courses: [...previous.courses, c],
                activeCourseId: c.id,
              }));
              setCreate(null);
              navigate(`/courses/${c.id}/overview`);
              setToast("课程已创建，开始探索吧");
            }}
          >
            <p className="muted">
              从一个课程名开始，也可以告诉 AI 你希望学会什么。
            </p>
            {create.template !== undefined && (
              <div className="callout">
                使用系统模板：{templates[create.template].title}
              </div>
            )}
            <label className="field">
              课程名称 <span className="required">*</span>
              <input
                data-autofocus
                required
                maxLength={80}
                placeholder="例如：从零理解经济学"
                value={title}
                onChange={(e) => setTitle(e.target.value)}
              />
            </label>
            <label className="field">
              学习目的 <small>选填</small>
              <textarea
                maxLength={1000}
                rows={3}
                placeholder="我想用这些知识做什么？"
                value={goal}
                onChange={(e) => setGoal(e.target.value)}
              />
            </label>
            <div className="form-note">
              课程的章节、对话、练习与资料将独立管理。
            </div>
            <div className="modal-actions">
              <button
                type="button"
                className="button"
                onClick={() => setCreate(null)}
              >
                取消
              </button>
              <button className="button primary" disabled={!title.trim() || (personal && server.saving)}>
                <Plus size={16} />
                创建课程
              </button>
            </div>
          </form>
        </Modal>
      )}

    </div>
    </ServerContext.Provider>
  );
}
