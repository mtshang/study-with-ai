import {ApiSettings} from "./ApiSettings";
import { useState, type Dispatch, type SetStateAction } from "react";
import {
  ArrowRight,
  Plus,
  Search,
  BookOpen,
  CheckCheck,
  NotebookPen,
  Sparkles,
  Archive,
  MoreHorizontal,
  Download,
  RotateCcw,
  ShieldCheck,
  MousePointer2,
  Wand2,
  Zap,
  Check,
} from "lucide-react";
import { templates, seedWorkspace } from "../data";
import type { Workspace, UpdateCourse, Permission } from "../types";
import {
  Badge,
  CourseIcon,
  DemoNote,
  Empty,
  Modal,
  PageTitle,
} from "../components/ui";

export function Home({
  state,
  openCreate,
  openCourse,
  update,
}: {
  state: Workspace;
  openCreate: (template?: number) => void;
  openCourse: (id: string, tab?: string) => void;
  update: UpdateCourse;
}) {
  const [search, setSearch] = useState("");
  const [filter, setFilter] = useState("all");
  const [menu, setMenu] = useState("");
  const active =
    state.courses.find((c) => c.id === state.activeCourseId && !c.archived) ||
    state.courses.find((c) => !c.archived);
  const current =
    active?.chapters.find(
      (c) => c.id === active.currentChapterId && !c.archived,
    );
  const courses = state.courses.filter(
    (c) =>
      (filter === "archived" ? c.archived : !c.archived) &&
      (filter !== "active" || c.id === active?.id) &&
      `${c.title} ${c.goal}`.toLowerCase().includes(search.toLowerCase()),
  );
  const pending = state.courses
    .filter((c) => !c.archived)
    .reduce(
      (sum, c) =>
        sum +
        c.assignments.filter(
          (a) => !c.submissions.some((s) => s.targetId === a.id),
        ).length,
      0,
    );
  const read = state.courses.reduce(
    (sum, c) => sum + c.chapters.filter((ch) => ch.read).length,
    0,
  );
  return (
    <>
      <PageTitle
        eyebrow="YOUR LEARNING SPACE"
        title={`你好，${state.settings.name}。今天想探索什么？`}
        description="让 AI 成为你的导师，把每一个问题变成前进的一步。"
        action={
          <button className="button primary" onClick={() => openCreate()}>
            <Plus size={18} />
            新建课程
          </button>
        }
      />
      <div className="home-hero">
        <div className="hero-copy">
          <div className="eyebrow light">
            <span className="live-dot" />
            继续你的学习旅程
          </div>
          <h2>{active ? active.title : "每一段探索，都从好奇开始。"}</h2>
          <p>
            {active
              ? `当前章节 · ${current?.title || "还没有选择章节"}`
              : "创建一门属于自己的课程，让想法慢慢成为能力。"}
          </p>
          <button
            className="button hero-button"
            onClick={() =>
              active
                ? openCourse(active.id, current ? "chapters" : "overview")
                : openCreate()
            }
          >
            {active ? "继续学习" : "创建第一门课程"}
            <ArrowRight size={18} />
          </button>
          <span className="hero-footnote">不必一次学会，重要的是开始。</span>
        </div>
        <div className="hero-art" aria-hidden="true">
          <div className="orbit orbit-one" />
          <div className="orbit orbit-two" />
          <div className="art-card back">
            <span />
            <span />
            <span />
          </div>
          <div className="art-card front">
            <BookOpen size={34} strokeWidth={1.2} />
            <div className="art-lines">
              <span />
              <span />
            </div>
            <div className="art-progress">
              <i />
            </div>
          </div>
          <div className="art-spark">
            <Sparkles size={24} />
          </div>
          <div className="art-check">
            <Check size={23} />
          </div>
          <span className="art-caption">A LITTLE EVERY DAY</span>
        </div>
      </div>
      <div className="stat-grid">
        <div>
          <span className="stat-icon green">
            <BookOpen size={21} />
          </span>
          <div>
            <strong>
              {state.courses.filter((c) => !c.archived).length}
              <small>门</small>
            </strong>
            <p>学习中的课程</p>
          </div>
        </div>
        <div>
          <span className="stat-icon blue">
            <CheckCheck size={21} />
          </span>
          <div>
            <strong>
              {read}
              <small>个</small>
            </strong>
            <p>已读章节</p>
          </div>
        </div>
        <div>
          <span className="stat-icon orange">
            <NotebookPen size={21} />
          </span>
          <div>
            <strong>
              {pending}
              <small>份</small>
            </strong>
            <p>待提交作业</p>
          </div>
        </div>
      </div>
      <div className="section-heading">
        <h2>
          我的课程 <span>{courses.length}</span>
        </h2>
        <div className="search-field">
          <Search size={16} />
          <input
            aria-label="搜索课程"
            placeholder="搜索课程或学习目标"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
          />
        </div>
      </div>
      <div className="tab-row" role="group" aria-label="课程筛选">
        {[
          ["all", "全部课程"],
          ["active", "正在学习"],
          ["archived", "已归档"],
        ].map(([key, label]) => (
          <button
            key={key}
            className={filter === key ? "selected" : ""}
            onClick={() => setFilter(key)}
          >
            {label}
          </button>
        ))}
      </div>
      <div className="course-grid">
        {courses.map((c) => {
          const chapters = c.chapters.filter((ch) => !ch.archived);
          const done = chapters.filter((ch) => ch.read).length;
          return (
            <article className={`course-card ${c.color}`} key={c.id}>
              <div className="course-card-top">
                <CourseIcon course={c} />
                <div className="card-actions">
                  <Badge>{c.category}</Badge>
                  <button
                    className="icon-button"
                    aria-label={`${c.title}的操作`}
                    onClick={() => setMenu(menu === c.id ? "" : c.id)}
                  >
                    <MoreHorizontal size={18} />
                  </button>
                  {menu === c.id && (
                    <div className="popover">
                      <button
                        onClick={() => {
                          update(
                            c.id,
                            (item) => ({ ...item, archived: !item.archived }),
                            {
                              category: "课程",
                              text: c.archived ? "恢复了课程" : "归档了课程",
                            },
                          );
                          setMenu("");
                        }}
                      >
                        <Archive size={15} />
                        {c.archived ? "恢复课程" : "归档课程"}
                      </button>
                    </div>
                  )}
                </div>
              </div>
              <button
                className="course-title-button"
                onClick={() => openCourse(c.id)}
              >
                <h3>{c.title}</h3>
              </button>
              <p className="course-goal">
                {c.goal || "从一个问题开始，慢慢找到自己的方向。"}
              </p>
              <div className="course-progress-label">
                <span>章节阅读进度</span>
                <span>
                  {done} / {chapters.length}
                </span>
              </div>
              <div className="progress-track">
                <i
                  style={{
                    width: `${chapters.length ? (done / chapters.length) * 100 : 0}%`,
                  }}
                />
              </div>
              <div className="course-card-bottom">
                <span>
                  {c.id === active?.id ? (
                    <>
                      <span className="status-dot" />
                      正在学习
                    </>
                  ) : (
                    `${c.exercises.length} 道练习 · ${c.assignments.length} 份作业`
                  )}
                </span>
                <button
                  aria-label={`进入${c.title}`}
                  className="round-button"
                  onClick={() => openCourse(c.id)}
                >
                  <ArrowRight size={18} />
                </button>
              </div>
            </article>
          );
        })}
        {filter === "all" && !search && (
          <button className="new-course-card" onClick={() => openCreate()}>
            <span>
              <Plus size={25} />
            </span>
            <h3>下一份好奇，是什么？</h3>
            <p>创建课程，开启新的学习旅程</p>
          </button>
        )}
      </div>
      {courses.length === 0 && (filter !== "all" || !!search) && (
        <Empty
          title="这里还没有课程"
          description={
            search ? "换一个关键词试试。" : "归档课程会保留全部学习记录。"
          }
        />
      )}
      <div className="home-bottom">
        <div>
          <Sparkles size={21} />
          <div>
            <strong>不知道从哪里开始？</strong>
            <p>从预置课程获得一点灵感，再按照自己的目标调整。</p>
          </div>
        </div>
        <a className="text-link" href="#/templates">
          浏览课程模板 <ArrowRight size={16} />
        </a>
      </div>
      <DemoNote />
    </>
  );
}

export function Templates({
  onCreate,
}: {
  onCreate: (template?: number) => void;
}) {
  return (
    <>
      <PageTitle
        eyebrow="A PLACE TO START"
        title="每一种好奇，都值得开始。"
        description="选一份教学模板，建立属于自己的课程。路线可以随你调整。"
      />
      <div className="template-banner">
        <Sparkles size={28} />
        <div>
          <h2>模板是起点，你的目标才是方向。</h2>
          <p>创建后生成独立课程和示例章节，可自行编辑；目前不包含完整教材或预设题库。</p>
        </div>
      </div>
      <div className="template-grid">
        {templates.map((template, index) => (
          <article className="panel template-card" key={template.title}>
            <CourseIcon course={template} size={34} />
            <Badge>{template.category}</Badge>
            <h2>{template.title}</h2>
            <p>{template.description}</p>
            <div className="tags">
              {template.tags.map((tag) => (
                <span key={tag}>{tag}</span>
              ))}
            </div>
            <div className="template-includes">内含：可自行编辑的示例章节</div>
            <button className="button primary" onClick={() => onCreate(index)}>
              用此模板创建
              <ArrowRight size={17} />
            </button>
          </article>
        ))}
      </div>
      <DemoNote>
        模板内容用于体验页面，不代表已内置完整教材或自动教学能力。
      </DemoNote>
    </>
  );
}

export function Settings({
  state,
  setState,
  toast,
}: {
  state: Workspace;
  setState: Dispatch<SetStateAction<Workspace>>;
  toast: (text: string) => void;
}) {
  const [name, setName] = useState(state.settings.name);
  const [reset, setReset] = useState(false);
  const choices: {
    value: Permission;
    title: string;
    text: string;
    icon: typeof ShieldCheck;
  }[] = [
    {
      value: "manual",
      title: "完全手动",
      text: "AI 提出操作建议，每次发布章节、作业或练习前都由你确认。",
      icon: MousePointer2,
    },
    {
      value: "assisted",
      title: "部分批准",
      text: "账号模式允许直接调整未完成章节、发布及回收作业与练习；永久删除仅限用户。",
      icon: Wand2,
    },
    {
      value: "full",
      title: "完全访问",
      text: "允许当前课程内的演示教学操作直接执行；不代表系统或电脑权限。",
      icon: Zap,
    },
  ];
  return (
    <>
      <PageTitle
        eyebrow="MAKE IT YOURS"
        title="设置"
        description="让学习空间按照你的方式工作。"
      />
      <div className="settings-layout">
        <ApiSettings/>
        <section className="panel settings-panel">
          <h2>个人资料</h2>
          <p className="muted">仅用于当前浏览器中的显示，不是真实登录账号。</p>
          <form
            onSubmit={(e) => {
              e.preventDefault();
              if (!name.trim()) return;
              setState((s) => ({
                ...s,
                settings: { ...s.settings, name: name.trim() },
              }));
              toast("显示名称已更新");
            }}
          >
            <label className="field">
              显示名称
              <input
                maxLength={24}
                required
                value={name}
                onChange={(e) => setName(e.target.value)}
              />
            </label>
            <button className="button primary">保存资料</button>
          </form>
        </section>
        <section className="panel settings-panel">
          <div className="section-heading">
            <h2>AI 操作权限</h2>
            <Badge tone="green">课程范围</Badge>
          </div>
          <p className="muted">在 AI 导师页面体验不同模式下的发布确认流程。</p>
          <div className="permission-grid">
            {choices.map((choice) => (
              <button
                key={choice.value}
                className={`permission-card ${state.settings.permission === choice.value ? "selected" : ""}`}
                onClick={() => {
                  setState((s) => ({
                    ...s,
                    settings: { ...s.settings, permission: choice.value },
                  }));
                  toast(`已切换为${choice.title}`);
                }}
              >
                <choice.icon size={22} />
                <strong>{choice.title}</strong>
                <p>{choice.text}</p>
                <span className="radio-indicator">
                  {state.settings.permission === choice.value && <span />}
                </span>
              </button>
            ))}
          </div>
          <DemoNote>
            当前权限只控制前端演示；真正的授权与数据隔离需要后端执行。
          </DemoNote>
        </section>
        <section className="panel settings-panel">
          <h2>显示偏好</h2>
          <div className="setting-row font-setting">
            <div>
              <strong>整体字号增量</strong>
              <p>在原始字号上统一放大，默认增加 3px。</p>
            </div>
            <label className="font-control">
              字号
              <select
                aria-label="整体字号增量"
                value={state.settings.fontOffset}
                onChange={(e) =>
                  setState((s) => ({
                    ...s,
                    settings: {
                      ...s.settings,
                      fontOffset: Number(e.target.value),
                    },
                  }))
                }
              >
                {[0, 1, 2, 3, 4, 5, 6].map((n) => (
                  <option key={n} value={n}>
                    +{n} px
                  </option>
                ))}
              </select>
            </label>
          </div>
          <div className="setting-row">
            <div>
              <strong>紧凑布局</strong>
              <p>缩小页面留白，在一屏内展示更多内容。</p>
            </div>
            <button
              role="switch"
              aria-checked={state.settings.compact}
              aria-label="紧凑布局"
              className={`switch ${state.settings.compact ? "on" : ""}`}
              onClick={() =>
                setState((s) => ({
                  ...s,
                  settings: { ...s.settings, compact: !s.settings.compact },
                }))
              }
            >
              <span />
            </button>
          </div>
        </section>
        <section className="panel settings-panel">
          <h2>演示数据</h2>
          <p className="muted">
            数据仅保存在当前浏览器。清除浏览器数据会丢失修改；导出文件可能包含你输入的个人内容，请自行保管。
          </p>
          <div className="button-row">
            <button
              className="button"
              onClick={() => {
                const url = URL.createObjectURL(
                  new Blob([JSON.stringify(state, null, 2)], {
                    type: "application/json",
                  }),
                );
                const a = document.createElement("a");
                a.href = url;
                a.download = "study-with-ai-demo.json";
                a.click();
                setTimeout(() => URL.revokeObjectURL(url), 1000);
                toast("演示数据已导出");
              }}
            >
              <Download size={16} />
              导出演示数据
            </button>
            <button
              className="button danger-ghost"
              onClick={() => setReset(true)}
            >
              <RotateCcw size={16} />
              恢复初始演示
            </button>
          </div>
        </section>
      </div>
      {reset && (
        <Modal title="恢复初始演示？" onClose={() => setReset(false)}>
          <p className="muted">
            这会清除当前浏览器中新建的课程、提交和修改。建议先导出数据。
          </p>
          <div className="modal-actions">
            <button className="button" onClick={() => setReset(false)}>
              取消
            </button>
            <button
              className="button danger"
              onClick={() => {
                setState(seedWorkspace());
                setName("学习者");
                setReset(false);
                toast("已恢复初始演示数据");
              }}
            >
              确认恢复
            </button>
          </div>
        </Modal>
      )}
    </>
  );
}
