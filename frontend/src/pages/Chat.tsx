import { useEffect, useRef, useState } from "react";
import {
  ArrowUp,
  BookOpen,
  Check,
  ChevronRight,
  Lightbulb,
  MessageSquare,
  NotebookPen,
  PencilLine,
  ShieldCheck,
  Sparkles,
  Square,
} from "lucide-react";
import type { Course, Permission, UpdateCourse } from "../types";
import { now, permissionLabels, uid } from "../data";
import { Badge, DemoNote, Modal } from "../components/ui";

type Action = "exercise" | "assignment" | "chapter";
const actionLabels = { exercise: "练习", assignment: "作业", chapter: "章节" };
export function Chat({
  course,
  update,
  permission,
  toast,
}: {
  course: Course;
  update: UpdateCourse;
  permission: Permission;
  toast: (text: string) => void;
}) {
  const [input, setInput] = useState("");
  const [running, setRunning] = useState(false);
  const [approval, setApproval] = useState<Action | null>(null);
  const timer = useRef<ReturnType<typeof setTimeout> | null>(null);
  const end = useRef<HTMLDivElement>(null);
  useEffect(
    () => () => {
      if (timer.current) clearTimeout(timer.current);
    },
    [],
  );
  useEffect(() => {
    end.current?.scrollIntoView({ block: "nearest", behavior: "smooth" });
  }, [course.messages.length, running]);
  const current = course.chapters.find(
    (ch) => ch.id === course.currentChapterId && !ch.archived,
  );
  const publish = (action: Action) => {
    const id = uid();
    const title =
      action === "exercise"
        ? "用自己的话解释一个概念"
        : action === "assignment"
          ? "把所学知识应用一次"
          : "新的探索：把概念连接起来";
    update(
      course.id,
      (c) => {
        let next = c;
        if (action === "exercise")
          next = {
            ...c,
            exercises: [
              ...c.exercises,
              {
                id,
                prompt: `结合「${c.title}」，选一个刚学到的概念，用自己的话解释并举例。`,
                explanation: "开放题示例，等待接入真实 AI 评估。",
                chapterId: c.currentChapterId,
              },
            ],
          };
        if (action === "assignment")
          next = {
            ...c,
            assignments: [
              ...c.assignments,
              {
                id,
                title,
                description:
                  "这是一份演示发布的作业。请先解释概念，再描述一个应用场景。",
                chapterId: c.currentChapterId,
                questions: [
                  {
                    id: uid(),
                    prompt: "选择一个本课程中的概念，解释它解决什么问题。",
                    explanation: "",
                  },
                  {
                    id: uid(),
                    prompt: "描述一个你会使用这个概念的具体场景。",
                    explanation: "",
                  },
                ],
              },
            ],
          };
        if (action === "chapter") {
          const chapters = [
            ...c.chapters,
            {
              id,
              title,
              description: "示例章节：整理概念之间的关系。",
              content:
                "这是通过前端演示工具发布的章节。\n\n先列出三个已学习的概念，说明它们之间的关系，再找一个实际例子。\n\n此内容为固定示例，尚未调用模型。",
              read: false,
            },
          ];
          next = {
            ...c,
            chapters,
            revisions: [
              {
                id: uid(),
                version: c.revisions.length + 1,
                time: now(),
                summary: "演示 AI 发布章节",
                titles: chapters
                  .filter((ch) => !ch.archived)
                  .map((ch) => ch.title),
              },
              ...c.revisions,
            ],
          };
        }
        return {
          ...next,
          messages: [
            ...next.messages,
            {
              id: uid(),
              role: "assistant",
              text: `【演示操作已完成】已在当前课程发布一${action === "chapter" ? "个章节" : action === "assignment" ? "份作业" : "道练习"}。你可以前往${actionLabels[action]}页面查看、作答或修改。\n\n这是本地固定示例，不是模型生成。`,
            },
          ],
        };
      },
      {
        category: "AI",
        text: `演示 AI 发布${actionLabels[action]}「${title}」`,
      },
    );
    setApproval(null);
    toast(`${actionLabels[action]}已发布到当前课程`);
  };
  const request = (action: Action) => {
    if (
      permission === "manual" ||
      (permission === "assisted" && action === "chapter")
    )
      setApproval(action);
    else publish(action);
  };
  const send = () => {
    if (!input.trim() || running) return;
    const question = input.trim();
    setInput("");
    update(course.id, (c) => ({
      ...c,
      messages: [...c.messages, { id: uid(), role: "user", text: question }],
    }));
    setRunning(true);
    timer.current = setTimeout(() => {
      update(
        course.id,
        (c) => ({
          ...c,
          messages: [
            ...c.messages,
            {
              id: uid(),
              role: "assistant",
              text: `【本地示例回复】我收到了你的问题。当前课程是「${c.title}」，${c.currentChapterId ? "已经记录当前学习章节。" : "还没有选择当前章节。"}\n\n真实 AI 接入后，会结合课程目标、资料和最新路线回答。现在可以点击右侧的“演示发布”按钮，体验章节、练习和作业怎样进入课程。`,
            },
          ],
        }),
        { category: "AI", text: "完成一次演示对话" },
      );
      setRunning(false);
      timer.current = null;
    }, 1100);
  };
  return (
    <div className="chat-layout">
      <section className="chat-panel panel">
        <div className="chat-header">
          <div className="tutor-avatar">
            <Sparkles size={23} />
          </div>
          <div>
            <h1>AI 导师</h1>
            <span>
              <span className="status-dot" />
              当前课程专属对话
            </span>
          </div>
          <Badge>本地演示</Badge>
        </div>
        <div className="chat-messages" aria-label="对话消息">
          {course.messages.map((message) => (
            <div className={`message ${message.role}`} key={message.id}>
              <span className="message-avatar">
                {message.role === "assistant" ? <Sparkles size={16} /> : "我"}
              </span>
              <div>
                <div className="message-author">
                  {message.role === "assistant" ? "AI 导师 · 演示" : "你"}
                </div>
                <div className="message-bubble">{message.text}</div>
              </div>
            </div>
          ))}
          {running && (
            <div className="message assistant" role="status">
              <span className="message-avatar">
                <Sparkles size={16} />
              </span>
              <div className="typing">
                正在准备示例回复
                <span />
                <span />
                <span />
              </div>
            </div>
          )}
          <div ref={end} />
        </div>
        <div className="composer-area">
          <div className="prompt-chips">
            <button
              onClick={() => setInput("能用一个具体例子讲解当前章节吗？")}
            >
              <Lightbulb size={14} />
              换个例子讲讲
            </button>
            <button onClick={() => request("exercise")}>
              <PencilLine size={14} />
              演示发布练习
            </button>
          </div>
          <form
            className="composer"
            onSubmit={(e) => {
              e.preventDefault();
              send();
            }}
          >
            <textarea
              aria-label="发送给 AI 导师的消息"
              placeholder="写下你的问题，或者告诉我你想换个方向……"
              value={input}
              maxLength={5000}
              onChange={(e) => setInput(e.target.value)}
              onKeyDown={(e) => {
                if (
                  e.key === "Enter" &&
                  !e.shiftKey &&
                  !e.nativeEvent.isComposing
                ) {
                  e.preventDefault();
                  send();
                }
              }}
            />
            <div className="composer-bottom">
              <span>Enter 发送 · Shift + Enter 换行</span>
              {running ? (
                <button
                  type="button"
                  className="button small"
                  onClick={() => {
                    if (timer.current) clearTimeout(timer.current);
                    timer.current = null;
                    setRunning(false);
                    update(course.id, (c) => ({
                      ...c,
                      messages: [
                        ...c.messages,
                        {
                          id: uid(),
                          role: "assistant",
                          text: "示例回复已停止。你的消息已保留。",
                        },
                      ],
                    }));
                    toast("已停止本次演示回复");
                  }}
                >
                  <Square size={13} />
                  停止生成
                </button>
              ) : (
                <button
                  className="send-button"
                  aria-label="发送消息"
                  disabled={!input.trim()}
                >
                  <ArrowUp size={19} />
                </button>
              )}
            </div>
          </form>
          <p className="composer-note">
            当前使用固定示例回复，不调用模型。演示等待会在离开此页面时结束。
          </p>
        </div>
      </section>
      <aside className="chat-context">
        <section className="panel">
          <div className="eyebrow">LEARNING CONTEXT</div>
          <h3>我们的学习上下文</h3>
          <div className="context-item">
            <span>学习目的</span>
            <p>{course.goal || "尚未填写"}</p>
          </div>
          <div className="context-item">
            <span>当前章节</span>
            <p>{current?.title || "尚未选择"}</p>
          </div>
          <div className="context-item">
            <span>路线版本</span>
            <p>v{course.revisions.length} · 按当前页面数据读取</p>
          </div>
          <a className="text-link" href={`#/courses/${course.id}/roadmap`}>
            查看学习路线
            <ChevronRight size={15} />
          </a>
        </section>
        <section className="panel">
          <div className="section-heading">
            <h3>教学操作</h3>
            <Badge>演示</Badge>
          </div>
          <p className="muted text-small">
            体验 AI 将内容发布到课程，而不只是发送一段聊天文字。
          </p>
          {(
            [
              ["chapter", BookOpen],
              ["exercise", PencilLine],
              ["assignment", NotebookPen],
            ] as const
          ).map(([action, Icon]) => (
            <button
              className="tool-action"
              key={action}
              onClick={() => request(action)}
            >
              <span>
                <Icon size={18} />
              </span>
              <strong>演示发布{actionLabels[action]}</strong>
              <ChevronRight size={16} />
            </button>
          ))}
        </section>
        <div className="permission-note">
          <ShieldCheck size={19} />
          <div>
            <strong>{permissionLabels[permission]}</strong>
            <p>权限可在设置中修改</p>
          </div>
          <a href="#/settings" aria-label="修改 AI 权限">
            <ChevronRight size={17} />
          </a>
        </div>
        <DemoNote>资料搜索、代码执行和视频生成将在后续接入。</DemoNote>
      </aside>
      {approval && (
        <Modal title="确认 AI 教学操作" onClose={() => setApproval(null)}>
          <div className="approval-icon">
            <MessageSquare size={25} />
          </div>
          <h3>
            在「{course.title}」发布{actionLabels[approval]}
          </h3>
          <p className="muted">
            根据当前权限设置，此操作需要你批准。它只会新增演示内容，不会删除过去的章节与提交记录。
          </p>
          <div className="modal-actions">
            <button className="button" onClick={() => setApproval(null)}>
              拒绝
            </button>
            <button
              className="button primary"
              onClick={() => publish(approval)}
            >
              <Check size={16} />
              批准并发布
            </button>
          </div>
        </Modal>
      )}
    </div>
  );
}
