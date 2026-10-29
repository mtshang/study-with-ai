import {GeneratedArtifacts} from './GeneratedArtifacts';
import {SubmittedFiles} from './Activities';
import { useContext, useRef, useState } from "react";
import {
  ArrowDown,
  ArrowUp,
  ArrowRight,
  BookOpen,
  Check,
  CheckCircle2,
  ChevronRight,
  Clock3,
  FileText,
  History,
  Link2,
  MessageSquare,
  NotebookPen,
  Pencil,
  Plus,
  Search,
  Upload,
  Archive,
  RotateCcw,
} from "lucide-react";
import type {
  Chapter,
  Course,
  Material,
  Permission,
  UpdateCourse,
} from "../types";
import { now, sourceLabels, uid } from "../data";
import {
  Badge,
  CourseIcon,
  DemoNote,
  Empty,
  formatTime,
  Modal,
  PageTitle,
  TextLink,
} from "../components/ui";
import {TrashPage} from './TrashPage';
import {RevisionViewer} from './RevisionViewer';
import {CodeFeedback} from './CodeExercise';
import {GradeFeedback} from './GradeFeedback';
import {accountRequest} from '../api';
import { ServerChat } from "./ServerChat";
import { Chat } from "./Chat";
import { Activities } from "./Activities";
import { ServerMaterials } from "./ServerMaterials";
import { ServerContext } from "../serverWorkspace";

type Props = {
  course: Course;
  tab: string;
  update: UpdateCourse;
  permission: Permission;
  toast: (text: string) => void;
};
const go = (id: string, tab: string) => {
  location.hash = `/courses/${id}/${tab}`;
};
const revise = (
  course: Course,
  chapters: Chapter[],
  summary: string,
): Course => ({
  ...course,
  chapters,
  revisions: [
    {
      id: uid(),
      time: now(),
      version: course.revisions.length + 1,
      summary,
      titles: chapters.filter((ch) => !ch.archived).map((ch) => ch.title),
    },
    ...course.revisions,
  ],
});

export function CoursePage(props: Props) {
  const server=useContext(ServerContext);
  switch (props.tab) {
    case "chat":
      return server.active&&server.userId ? <ServerChat key={server.userId+props.course.id} course={props.course} userId={server.userId} reload={server.reload} update={props.update}/> : <Chat {...props} />;
    case "chapter-trash":
    case "exercise-trash":
    case "assignment-trash":
      return <TrashPage key={(server.userId||'demo')+props.course.id+props.tab} course={props.course} kind={props.tab==='chapter-trash'?'chapter':props.tab==='exercise-trash'?'exercise':'assignment'}/>;
    case "chapters":
      return <Chapters {...props} />;
    case "roadmap":
      return <Roadmap {...props} />;
    case "exercises":
    case "assignments":
      return (
        <Activities
          {...props}
          kind={props.tab === "exercises" ? "exercise" : "assignment"}
        />
      );
    case "materials":
      return <Materials {...props} />;
    case "artifacts":
      return <GeneratedArtifacts key={(server.userId||"demo")+props.course.id} courseId={props.course.id} userId={server.active?(server.userId??null):null}/>;
    case "history":
      return <LearningHistory course={props.course} />;
    default:
      return <Overview {...props} />;
  }
}

function Overview({ course, update, toast }: Props) {
  const [edit, setEdit] = useState(false);
  const [title, setTitle] = useState(course.title);
  const [goal, setGoal] = useState(course.goal);
  const visible = course.chapters.filter((ch) => !ch.archived);
  const read = visible.filter((ch) => ch.read).length;
  const current = visible.find((ch) => ch.id === course.currentChapterId);
  const pending = course.assignments.filter(
    (a) => !course.submissions.some((s) => s.targetId === a.id),
  );
  return (
    <>
      <PageTitle
        eyebrow="COURSE SPACE"
        title={course.title}
        description={course.goal || "按你的节奏，探索这门课程。"}
        action={
          <button
            className="button"
            onClick={async () => {
              setTitle(course.title);
              setGoal(course.goal);
              setEdit(true);
            }}
          >
            <Pencil size={15} />
            编辑课程
          </button>
        }
      />
      <div className="overview-grid">
        <section className="panel current-chapter">
          <div className="section-heading">
            <Badge tone="green">当前学习</Badge>
            <CourseIcon course={course} />
          </div>
          <span className="muted text-small">
            CHAPTER{" "}
            {current
              ? String(visible.indexOf(current) + 1).padStart(2, "0")
              : "—"}
          </span>
          <h2>{current?.title || (visible.length ? "请选择学习章节" : "准备好第一章了吗？")}</h2>
          <p>
            {current?.description ||
              "在章节页面创建内容，或前往 AI 导师体验发布流程。"}
          </p>
          <div className="button-row">
            <button
              className="button primary"
              onClick={() => go(course.id, "chapters")}
            >
              {current ? "进入章节" : "管理章节"}
              <ArrowRight size={17} />
            </button>
            <button className="button" onClick={() => go(course.id, "chat")}>
              <MessageSquare size={16} />
              问问 AI 导师
            </button>
          </div>
        </section>
        <section className="panel progress-panel">
          <h3>一点一点，积累起来</h3>
          <div className="reading-number">
            {read}
            <span>/ {visible.length} 章已读</span>
          </div>
          <div className="progress-track">
            <i
              style={{
                width: `${visible.length ? (read / visible.length) * 100 : 0}%`,
              }}
            />
          </div>
          <div className="mini-stats">
            <div>
              <strong>
                {course.submissions.filter((s) => s.kind === "exercise").length}
              </strong>
              <span>练习提交</span>
            </div>
            <div>
              <strong>
                {
                  course.submissions.filter((s) => s.kind === "assignment")
                    .length
                }
              </strong>
              <span>作业提交</span>
            </div>
            <div>
              <strong>{course.materials.length}</strong>
              <span>学习资料</span>
            </div>
          </div>
          <p className="fine-print">阅读进度只表示已读章节，不代表掌握程度。</p>
        </section>
      </div>
      <div className="two-columns">
        <section className="panel">
          <div className="section-heading">
            <h2>接下来的章节</h2>
            <TextLink onClick={() => go(course.id, "roadmap")}>
              查看路线
            </TextLink>
          </div>
          {visible.length ? (
            visible.slice(0, 5).map((ch, i) => (
              <button
                className="chapter-row"
                key={ch.id}
                onClick={async () => {
                  if ((await update(course.id, (c) => ({ ...c, currentChapterId: ch.id }))) === false) return;
                  go(course.id, "chapters");
                }}
              >
                <span className={`chapter-index ${ch.read ? "done" : ""}`}>
                  {ch.read ? (
                    <Check size={15} />
                  ) : (
                    String(i + 1).padStart(2, "0")
                  )}
                </span>
                <span>
                  <strong>{ch.title}</strong>
                  <small>
                    {ch.read
                      ? "已读"
                      : ch.id === current?.id
                        ? "正在学习"
                        : "待探索"}
                  </small>
                </span>
                <ChevronRight size={16} />
              </button>
            ))
          ) : (
            <Empty
              title="还没有章节"
              description="先写下第一个想了解的问题吧。"
            />
          )}
        </section>
        <section className="panel">
          <div className="section-heading">
            <h2>待完成的作业</h2>
            <Badge tone="orange">{pending.length} 份</Badge>
          </div>
          {pending.length ? (
            pending.map((a) => (
              <button
                className="assignment-preview"
                key={a.id}
                onClick={() => go(course.id, "assignments")}
              >
                <span className="stat-icon orange">
                  <NotebookPen size={20} />
                </span>
                <div>
                  <strong>{a.title}</strong>
                  <p>{a.questions.length} 道题 · 尚未提交</p>
                </div>
                <ArrowRight size={17} />
              </button>
            ))
          ) : (
            <Empty
              title="暂时没有待提交作业"
              description="你可以先学习章节，或做一道小练习。"
            />
          )}
          <div className="soft-callout">
            <BookOpen size={22} />
            <div>
              <strong>不确定哪里没懂？</strong>
              <p>试着用自己的话解释一次，再让 AI 帮你梳理。</p>
            </div>
          </div>
        </section>
      </div>
      <DemoNote />
      {edit && (
        <Modal title="编辑课程" onClose={() => setEdit(false)}>
          <form
            onSubmit={async (e) => {
              e.preventDefault();
              if (!title.trim()) return;
              if ((await update(
                course.id,
                (c) => ({ ...c, title: title.trim(), goal: goal.trim() }),
                { category: "课程", text: "更新了课程名称或学习目的" },
              )) === false) return;
              setEdit(false);
              toast("课程已更新");
            }}
          >
            <label className="field">
              课程名
              <input
                required
                maxLength={80}
                value={title}
                onChange={(e) => setTitle(e.target.value)}
              />
            </label>
            <label className="field">
              学习目的
              <textarea
                rows={3}
                maxLength={1000}
                value={goal}
                onChange={(e) => setGoal(e.target.value)}
              />
            </label>
            <div className="modal-actions">
              <button
                type="button"
                className="button"
                onClick={() => setEdit(false)}
              >
                取消
              </button>
              <button className="button primary" disabled={!title.trim()}>
                保存修改
              </button>
            </div>
          </form>
        </Modal>
      )}
    </>
  );
}

function ChapterEditor({
  chapter,
  onSave,
  onClose,
}: {
  chapter?: Chapter;
  onSave: (title: string, description: string, content: string) => void;
  onClose: () => void;
}) {
  const [title, setTitle] = useState(chapter?.title || "");
  const [description, setDescription] = useState(chapter?.description || "");
  const [content, setContent] = useState(chapter?.content || "");
  return (
    <Modal title={chapter ? "编辑章节" : "新增章节"} onClose={onClose} wide>
      <form
        onSubmit={async (e) => {
          e.preventDefault();
          if (title.trim())
            onSave(title.trim(), description.trim(), content.trim());
        }}
      >
        <label className="field">
          章节名称
          <input
            data-autofocus
            required
            maxLength={100}
            value={title}
            onChange={(e) => setTitle(e.target.value)}
            placeholder="这一章想学什么？"
          />
        </label>
        <label className="field">
          简要说明
          <input
            maxLength={200}
            value={description}
            onChange={(e) => setDescription(e.target.value)}
          />
        </label>
        <label className="field">
          章节内容
          <textarea
            rows={9}
            maxLength={20000}
            value={content}
            onChange={(e) => setContent(e.target.value)}
            placeholder="可以先写下讲解、例子和需要探索的问题。"
          />
        </label>
        <div className="modal-actions">
          <button type="button" className="button" onClick={onClose}>
            取消
          </button>
          <button className="button primary" disabled={!title.trim()}>
            保存章节
          </button>
        </div>
      </form>
    </Modal>
  );
}

function Chapters({ course, update, toast }: Props) {
  const visible = course.chapters.filter((ch) => !ch.archived);
  const [selected, setSelected] = useState(
    course.currentChapterId || visible[0]?.id,
  );
  const [editor, setEditor] = useState<{ chapter?: Chapter } | null>(null);
  const chapter = visible.find((ch) => ch.id === selected) || visible[0];
  const save = async (title: string, description: string, content: string) => {
    const target = editor?.chapter;
    const id = target?.id || uid();
    if ((await update(
      course.id,
      (c) =>
        revise(
          c,
          target
            ? c.chapters.map((ch) =>
                ch.id === id ? { ...ch, title, description, content } : ch,
              )
            : [...c.chapters, { id, title, description, content, read: false }],
          target ? "编辑章节内容" : "新增章节",
        ),
      { category: "章节", text: `${target ? "修改" : "新增"}「${title}」` },
    )) === false) return;
    setSelected(id);
    setEditor(null);
    toast("章节已保存");
  };
  return (
    <>
      <PageTitle
        eyebrow="ONE CHAPTER AT A TIME"
        title="章节"
        description="读一点，试一点。你的学习节奏，由你决定。"
        action={
          <button className="button primary" onClick={() => setEditor({})}>
            <Plus size={16} />
            新增章节
          </button>
        }
      />
      {!chapter ? (
        <Empty
          title="第一章，从这里开始"
          description="手动添加章节，或在 AI 导师中体验发布示例章节。"
          action={
            <button className="button" onClick={() => go(course.id, "chat")}>
              前往 AI 导师
              <ArrowRight size={16} />
            </button>
          }
        />
      ) : (
        <div className="chapter-layout">
          <aside className="panel chapter-list">
            <div className="section-heading">
              <h3>章节目录</h3>
              <span className="muted text-small">{visible.length} 章</span>
            </div>
            {visible.map((ch, i) => (
              <button
                key={ch.id}
                className={`chapter-selector ${chapter.id === ch.id ? "selected" : ""}`}
                onClick={() => setSelected(ch.id)}
              >
                <span>
                  {ch.read ? (
                    <CheckCircle2 size={18} />
                  ) : (
                    String(i + 1).padStart(2, "0")
                  )}
                </span>
                <div>
                  <strong>{ch.title}</strong>
                  <small>
                    {ch.id === course.currentChapterId
                      ? "当前章节"
                      : ch.read
                        ? "已读"
                        : "未读"}
                  </small>
                </div>
              </button>
            ))}
          </aside>
          <article className="panel chapter-content">
            <div className="section-heading">
              <Badge tone={chapter.read ? "green" : ""}>
                {chapter.read ? "已读" : "未读"}
              </Badge>
              <button
                className="button small"
                onClick={() => setEditor({ chapter })}
              >
                <Pencil size={14} />
                编辑
              </button>
            </div>
            <div className="eyebrow">
              CHAPTER {String(visible.indexOf(chapter) + 1).padStart(2, "0")}
            </div>
            <h2>{chapter.title}</h2>
            <p className="chapter-description">{chapter.description}</p>
            <div className="prose chapter-prose">
              {chapter.content || "这一章还没有正文，你可以点击编辑补充。"}
            </div>
            <div className="chapter-content-actions">
              <button
                className={`button ${chapter.read ? "" : "primary"}`}
                onClick={async () => {
                  if ((await update(
                    course.id,
                    (c) => ({
                      ...c,
                      chapters: c.chapters.map((ch) =>
                        ch.id === chapter.id ? { ...ch, read: !ch.read } : ch,
                      ),
                    }),
                    {
                      category: "章节",
                      text: `${chapter.read ? "标记未读" : "已读"}「${chapter.title}」`,
                    },
                  )) === false) return;
                  toast(chapter.read ? "已标记为未读" : "已记录章节阅读状态");
                }}
              >
                <Check size={16} />
                {chapter.read ? "标记为未读" : "标记为已读"}
              </button>
              <button
                className="button"
                disabled={chapter.id === course.currentChapterId}
                onClick={async () => {
                  if ((await update(
                    course.id,
                    (c) => ({ ...c, currentChapterId: chapter.id }),
                    {
                      category: "章节",
                      text: `选择「${chapter.title}」作为当前章节`,
                    },
                  )) === false) return;
                  toast("当前章节已更新");
                }}
              >
                {chapter.id === course.currentChapterId
                  ? "当前学习章节"
                  : "设为当前章节"}
              </button>
            </div>
            <div className="related">
              <strong>学完后，试试看</strong>
              <div className="button-row">
                <button
                  className="text-link"
                  onClick={() => go(course.id, "exercises")}
                >
                  章节练习 ·{" "}
                  {
                    course.exercises.filter((q) => q.chapterId === chapter.id)
                      .length
                  }{" "}
                  道<ArrowRight size={15} />
                </button>
                <button
                  className="text-link"
                  onClick={() => go(course.id, "assignments")}
                >
                  查看课程作业
                  <ArrowRight size={15} />
                </button>
              </div>
            </div>
          </article>
        </div>
      )}
      {editor && (
        <ChapterEditor
          chapter={editor.chapter}
          onSave={save}
          onClose={() => setEditor(null)}
        />
      )}
    </>
  );
}

function Roadmap({ course, update, toast }: Props) {
  const server=useContext(ServerContext);
  const visible = course.chapters.filter((ch) => !ch.archived);
  const [editor, setEditor] = useState<{ chapter?: Chapter } | null>(null);
  const [archiving, setArchiving] = useState<Chapter | null>(null);
  const [showHistory, setShowHistory] = useState(false);
  const move = async (id: string, direction: number) => {
    const index = visible.findIndex((ch) => ch.id === id);
    const reordered = [...visible];
    [reordered[index], reordered[index + direction]] = [
      reordered[index + direction],
      reordered[index],
    ];
    if ((await update(
      course.id,
      (c) =>
        revise(
          c,
          [...reordered, ...c.chapters.filter((ch) => ch.archived)],
          "调整章节顺序",
        ),
      { category: "路线", text: "调整了章节顺序" },
    )) === false) return;
  };
  return (
    <>
      <PageTitle
        eyebrow="YOUR PATH, YOUR PACE"
        title="学习路线"
        description="保留走过的路，也给新的方向留一点空间。"
        action={
          <div className="button-row">
            <button className="button" onClick={() => setShowHistory(true)}>
              <History size={16} />
              版本记录 <Badge>{course.revisions.length}</Badge>
            </button>
            <button className="button primary" onClick={() => setEditor({})}>
              <Plus size={16} />
              添加章节
            </button>
          </div>
        }
      />
      <div className="route-goal">
        <span className="stat-icon green">
          <BookOpen size={22} />
        </span>
        <div>
          <span className="eyebrow">学习目的</span>
          <h3>{course.goal || "还没有填写，可以在课程概览中补充。"}</h3>
        </div>
      </div>
      <div className="route-list">
        {visible.map((ch, index) => (
          <article
            className={`route-card ${ch.read ? "done" : ""}`}
            key={ch.id}
          >
            <div className="route-node">
              {ch.read ? (
                <Check size={18} />
              ) : (
                String(index + 1).padStart(2, "0")
              )}
            </div>
            <div className="route-info">
              <div className="button-row">
                <h3>{ch.title}</h3>
                {ch.read && <Badge tone="green">已读 · 保留</Badge>}
                {ch.id === course.currentChapterId && (
                  <Badge tone="blue">当前章节</Badge>
                )}
              </div>
              <p>{ch.description || "还没有章节说明"}</p>
            </div>
            <div className="route-actions">
              <button
                className="icon-button"
                aria-label={`上移${ch.title}`}
                disabled={index === 0}
                onClick={() => move(ch.id, -1)}
              >
                <ArrowUp size={16} />
              </button>
              <button
                className="icon-button"
                aria-label={`下移${ch.title}`}
                disabled={index === visible.length - 1}
                onClick={() => move(ch.id, 1)}
              >
                <ArrowDown size={16} />
              </button>
              <button
                className="icon-button"
                aria-label={`编辑${ch.title}`}
                onClick={() => setEditor({ chapter: ch })}
              >
                <Pencil size={16} />
              </button>
              <button
                className="icon-button"
                aria-label={`移出${ch.title}`}
                disabled={ch.read && !server.active}
                title="由你确认移入章节回收站，保留历史"
                onClick={() => setArchiving(ch)}
              >
                <Archive size={16} />
              </button>
            </div>
          </article>
        ))}
      </div>
      {!visible.length && (
        <Empty
          title="路线还在等待你的第一个想法"
          description="先添加一个章节，之后可以继续扩展或调整。"
        />
      )}
      {course.chapters.some((ch) => ch.archived) && (
        <section className="panel archived-chapters">
          <h3>已移出的章节</h3>
          <p className="muted">原内容和关联的作业、提交仍然保留。</p>
          {course.chapters
            .filter((ch) => ch.archived)
            .map((ch) => (
              <div className="file-row" key={ch.id}>
                <BookOpen size={18} />
                <strong>{ch.title}</strong>
                <button
                  className="button small"
                  onClick={async () => {
                    if ((await update(
                      course.id,
                      (c) =>
                        revise(
                          c,
                          c.chapters.map((item) =>
                            item.id === ch.id
                              ? { ...item, archived: false }
                              : item,
                          ),
                          "恢复章节",
                        ),
                      { category: "路线", text: `恢复「${ch.title}」` },
                    )) === false) return;
                    toast("已恢复到学习路线");
                  }}
                >
                  <RotateCcw size={14} />
                  恢复
                </button>
              </div>
            ))}
        </section>
      )}
      <DemoNote>
        路线修改会记录版本。AI 修改前会核对版本，已完成章节只能由你手动移出。
      </DemoNote>
      {editor && (
        <ChapterEditor
          chapter={editor.chapter}
          onClose={() => setEditor(null)}
          onSave={async (title, description, content) => {
            const old = editor.chapter;
            if ((await update(
              course.id,
              (c) =>
                revise(
                  c,
                  old
                    ? c.chapters.map((ch) =>
                        ch.id === old.id
                          ? { ...ch, title, description, content }
                          : ch,
                      )
                    : [
                        ...c.chapters,
                        { id: uid(), title, description, content, read: false },
                      ],
                  old ? "编辑章节" : "添加章节",
                ),
              {
                category: "路线",
                text: `${old ? "编辑" : "添加"}「${title}」`,
              },
            )) === false) return;
            setEditor(null);
            toast("路线已更新");
          }}
        />
      )}
      {archiving && (
        <Modal title="移出当前路线？" onClose={() => setArchiving(null)}>
          <p className="muted">
            「{archiving.title}
            」将移入章节回收站。章节正文保留，关联作业和练习转为未分类，恢复时不会重新关联。提交和批改记录保留。
          </p>
          <div className="modal-actions">
            <button className="button" onClick={() => setArchiving(null)}>
              取消
            </button>
            <button
              className="button primary"
              onClick={async () => {
                if(server.active&&server.userId){
                  try { await accountRequest(`/courses/${course.id}/trash-actions`,{id:crypto.randomUUID(),expected_version:course.version,kind:'chapter',action:'archive',target_ids:[archiving.id]},AbortSignal.timeout(20000),{headers:{'X-Workspace-User':server.userId}});setArchiving(null);server.reload();toast('已移入章节回收站，关联作业和练习转为未分类'); }
                  catch(e){toast(e instanceof Error?e.message:'移入回收站失败');}return;
                }
                if ((await update(
                  course.id,
                  (c) => {
                    const next = revise(
                      c,
                      c.chapters.map((ch) =>
                        ch.id === archiving.id ? { ...ch, archived: true } : ch,
                      ),
                      "移出未完成章节",
                    );
                    return {
                      ...next,
                      currentChapterId:
                        c.currentChapterId === archiving.id
                          ? next.chapters.find((ch) => !ch.archived && !ch.read)
                              ?.id
                          : c.currentChapterId,
                    };
                  },
                  { category: "路线", text: `移出「${archiving.title}」` },
                )) === false) return;
                setArchiving(null);
                toast("已移出，历史记录已保留");
              }}
            >
              确认移出
            </button>
          </div>
        </Modal>
      )}
      {showHistory && (
        <Modal title="路线版本记录" wide onClose={() => setShowHistory(false)}>
          <RevisionViewer key={server.userId+course.id} course={course}/>
        </Modal>
      )}
    </>
  );
}

function Materials({ course, update, toast }: Props) {
  const server=useContext(ServerContext);
  const [search, setSearch] = useState("");
  const [source, setSource] = useState("all");
  const [preview, setPreview] = useState<Material | null>(null);
  const [add, setAdd] = useState(false);
  const [title, setTitle] = useState("");
  const [url, setUrl] = useState("");
  const [description, setDescription] = useState("");
  const input = useRef<HTMLInputElement>(null);
  const materials = course.materials.filter(
    (m) =>
      (source === "all" || m.source === source) &&
      m.title.toLowerCase().includes(search.toLowerCase()),
  );
  const addRecord = (material: Material) =>
    update(
      course.id,
      (c) => ({ ...c, materials: [material, ...c.materials] }),
      { category: "资料", text: `添加资料「${material.title}」` },
    );
  if(server.active)return <ServerMaterials course={course} toast={toast}/>;
  return (
    <>
      <PageTitle
        eyebrow="YOUR KNOWLEDGE SHELF"
        title="课程资料"
        description="把有价值的内容留在这里，每份资料都有自己的来源。"
        action={
          <div className="button-row">
            <button
              className="button"
              onClick={() => {
                setAdd(true);
                setTitle("");
                setUrl("");
                setDescription("");
              }}
            >
              <Link2 size={16} />
              添加链接或笔记
            </button>
            <button
              className="button primary"
              onClick={() => input.current?.click()}
            >
              <Upload size={16} />
              上传资料
            </button>
          </div>
        }
      />
      <input
        className="visually-hidden"
        type="file"
        ref={input}
        multiple
        onChange={(e) => {
          const files = Array.from(e.target.files || []);
          files.forEach((file) =>
            addRecord({
              id: uid(),
              title: file.name,
              filename: file.name,
              source: "user",
              kind: "文件",
              description: `文件大小 ${(file.size / 1024).toFixed(1)} KB。当前仅保存文件信息，未读取或上传文件本体。刷新后如需处理内容，请重新选择原文件。`,
            }),
          );
          if (files.length)
            toast(`已记录 ${files.length} 个文件的信息，尚未上传文件内容`);
          e.target.value = "";
        }}
      />
      <div className="toolbar">
        <div className="tab-row" role="group" aria-label="资料来源筛选">
          {[["all", "全部资料"], ...Object.entries(sourceLabels)].map(
            ([key, label]) => (
              <button
                className={source === key ? "selected" : ""}
                key={key}
                onClick={() => setSource(key)}
              >
                {label}
              </button>
            ),
          )}
        </div>
        <div className="search-field">
          <Search size={16} />
          <input
            aria-label="搜索资料"
            placeholder="搜索资料名称"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
          />
        </div>
      </div>
      <div className="material-grid">
        {materials.map((m) => (
          <button
            className="panel material-card"
            key={m.id}
            onClick={() => setPreview(m)}
          >
            <div className="section-heading">
              <span className={`material-icon ${m.source}`}>
                {m.kind === "链接" ? (
                  <Link2 size={23} />
                ) : (
                  <FileText size={23} />
                )}
              </span>
              <Badge tone={m.source === "system" ? "green" : ""}>
                {sourceLabels[m.source]}
              </Badge>
            </div>
            <h3>{m.title}</h3>
            <p>{m.description}</p>
            <div className="material-footer">
              <span>{m.kind}</span>
              <span>
                查看详情 <ChevronRight size={14} />
              </span>
            </div>
          </button>
        ))}
      </div>
      {!materials.length && (
        <Empty
          title="这里还没有资料"
          description="上传一份教材，添加一个链接，或者记录自己的想法。"
        />
      )}
      <DemoNote>
        文件上传目前只保存文件名与大小，不会读取、上传或持久化文件本体。
      </DemoNote>
      {preview && (
        <Modal title={preview.title} wide onClose={() => setPreview(null)}>
          <Badge>{sourceLabels[preview.source]}</Badge>
          <div className="prose material-description">
            {preview.description}
          </div>
          {preview.url && /^https?:\/\//i.test(preview.url) && (
            <a
              className="button primary"
              href={preview.url}
              target="_blank"
              rel="noopener noreferrer"
            >
              打开来源网页
              <ArrowRight size={16} />
            </a>
          )}
        </Modal>
      )}
      {add && (
        <Modal title="添加资料" onClose={() => setAdd(false)}>
          <form
            onSubmit={(e) => {
              e.preventDefault();
              if (!title.trim()) return;
              if (url && !/^https?:\/\//i.test(url)) {
                toast("请使用 http 或 https 链接");
                return;
              }
              addRecord({
                id: uid(),
                title: title.trim(),
                source: url ? "web" : "user",
                kind: url ? "链接" : "笔记",
                url: url || undefined,
                description: description.trim() || "暂无说明",
              });
              setAdd(false);
              toast("资料已保存");
            }}
          >
            <label className="field">
              标题
              <input
                required
                data-autofocus
                maxLength={120}
                value={title}
                onChange={(e) => setTitle(e.target.value)}
              />
            </label>
            <label className="field">
              来源网址 <small>选填</small>
              <input
                type="url"
                placeholder="https://"
                value={url}
                onChange={(e) => setUrl(e.target.value)}
              />
            </label>
            <label className="field">
              内容或说明
              <textarea
                rows={5}
                maxLength={10000}
                value={description}
                onChange={(e) => setDescription(e.target.value)}
              />
            </label>
            <div className="modal-actions">
              <button
                type="button"
                className="button"
                onClick={() => setAdd(false)}
              >
                取消
              </button>
              <button className="button primary" disabled={!title.trim()}>
                保存资料
              </button>
            </div>
          </form>
        </Modal>
      )}
    </>
  );
}

function LearningHistory({ course }: { course: Course }) {
  const [filter, setFilter] = useState("全部");
  const categories = [
    "全部",
    "课程",
    "章节",
    "路线",
    "练习",
    "作业",
    "资料",
    "AI",
  ];
  const events = course.events.filter(
    (e) => filter === "全部" || e.category === filter,
  );
  return (
    <>
      <PageTitle
        eyebrow="EVERY STEP COUNTS"
        title="学习记录"
        description="看过的章节、做过的练习和改变的方向，都值得被记住。"
      />
      <div className="tab-row">
        {categories.map((c) => (
          <button
            key={c}
            className={filter === c ? "selected" : ""}
            onClick={() => setFilter(c)}
          >
            {c}
          </button>
        ))}
      </div>
      {course.submissions.some(s=>s.targetDeleted||s.targetTrashed)&&<section className="panel" aria-label="保留的提交历史"><h2>已移出或删除内容的学习历史</h2>{course.submissions.filter(s=>s.targetDeleted||s.targetTrashed).map(s=><details key={s.id}><summary>{s.targetTitle||'历史提交'} · {s.targetDeleted?'原对象已删除':'原对象在回收站'} · {formatTime(s.createdAt)}</summary>{s.questions?.map(q=><div key={q.id}><strong>{q.prompt}</strong><p className="preserve-text">{s.answers[q.id]}</p></div>)}<SubmittedFiles courseId={course.id} attachments={s.attachments||[]}/><p>{s.feedback}</p>{s.codeRun&&<CodeFeedback value={s.codeRun}/ >}{s.aiGrade&&<GradeFeedback courseId={course.id} initial={s.aiGrade}/>}</details>)}</section>}
      {course.submissions.some(s=>s.codeRun&&!s.targetDeleted&&!s.targetTrashed)&&<section className="panel" aria-label="代码学习历史"><h2>Python 运行记录</h2>{course.submissions.filter(s=>s.codeRun&&!s.targetDeleted&&!s.targetTrashed).map(s=><details key={s.id}><summary>{s.targetTitle||'Python练习'} · {formatTime(s.createdAt)}</summary><pre className="preserve-text">{Object.values(s.answers)[0]}</pre>{s.codeRun&&<CodeFeedback value={s.codeRun}/>}</details>)}</section>}
      <section className="panel history-panel">
        {events.length ? (
          events.map((event) => (
            <div className="timeline-item" key={event.id}>
              <span className="timeline-dot">
                <Clock3 size={16} />
              </span>
              <div>
                <strong>{event.text}</strong>
                <div className="timeline-meta">
                  <Badge>{event.category}</Badge>
                  <time>{formatTime(event.time)}</time>
                </div>
              </div>
            </div>
          ))
        ) : (
          <Empty
            title="还没有这类记录"
            description="你的学习操作会陆续出现在这里。"
          />
        )}
      </section>
    </>
  );
}
