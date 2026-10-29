import { useContext } from "react";
import { ServerContext } from "../serverWorkspace";
import { useEffect, useRef, type ReactNode } from "react";
import {
  X,
  ArrowRight,
  BookOpen,
  Code2,
  Languages,
  Palette,
  Sparkles,
  Inbox,
} from "lucide-react";
import type { Course } from "../types";

export function CourseIcon({
  course,
  size = 25,
}: {
  course: Pick<Course, "icon" | "color">;
  size?: number;
}) {
  const Icon = {
    code: Code2,
    language: Languages,
    design: Palette,
    book: BookOpen,
  }[course.icon];
  return (
    <span className={`course-icon ${course.color}`}>
      <Icon size={size} strokeWidth={1.6} />
    </span>
  );
}
export function Badge({
  children,
  tone = "",
}: {
  children: ReactNode;
  tone?: string;
}) {
  return <span className={`badge ${tone}`}>{children}</span>;
}
export function Empty({
  title,
  description,
  action,
}: {
  title: string;
  description: string;
  action?: ReactNode;
}) {
  return (
    <div className="empty">
      <div className="empty-icon">
        <Inbox size={28} />
      </div>
      <h3>{title}</h3>
      <p>{description}</p>
      {action}
    </div>
  );
}
export function PageTitle({
  eyebrow,
  title,
  description,
  action,
}: {
  eyebrow?: string;
  title: string;
  description?: string;
  action?: ReactNode;
}) {
  return (
    <div className="page-title">
      <div>
        {eyebrow && <div className="eyebrow">{eyebrow}</div>}
        <h1>{title}</h1>
        {description && <p>{description}</p>}
      </div>
      {action}
    </div>
  );
}
export function Modal({
  title,
  children,
  onClose,
  wide = false,
}: {
  title: string;
  children: ReactNode;
  onClose: () => void;
  wide?: boolean;
}) {
  const server = useContext(ServerContext);
  const ref = useRef<HTMLDivElement>(null);
  const closeRef = useRef(onClose);
  closeRef.current = onClose;
  useEffect(() => {
    const previous = document.activeElement as HTMLElement | null;
    const original = document.body.style.overflow;
    document.body.style.overflow = "hidden";
    const focusable = () =>
      Array.from(
        ref.current?.querySelectorAll<HTMLElement>(
          'button:not(:disabled), input, select, textarea, a[href], [tabindex="0"]',
        ) || [],
      ).filter((el) => el.offsetParent !== null);
    (
      ref.current?.querySelector<HTMLElement>("[data-autofocus]") ||
      focusable()[0]
    )?.focus();
    const keydown = (event: KeyboardEvent) => {
      if (event.key === "Escape") closeRef.current();
      if (event.key === "Tab") {
        const items = focusable();
        const first = items[0];
        const last = items.at(-1);
        if (event.shiftKey && document.activeElement === first) {
          event.preventDefault();
          last?.focus();
        } else if (!event.shiftKey && document.activeElement === last) {
          event.preventDefault();
          first?.focus();
        }
      }
    };
    document.addEventListener("keydown", keydown);
    return () => {
      document.body.style.overflow = original;
      document.removeEventListener("keydown", keydown);
      previous?.focus();
    };
  }, []);
  return (
    <div
      className="modal-backdrop"
      onMouseDown={(event) => {
        if (event.target === event.currentTarget) onClose();
      }}
    >
      <div
        ref={ref}
        role="dialog"
        aria-modal="true"
        aria-labelledby="modal-title"
        className={`modal ${wide ? "wide" : ""}`}
      >
        <div className="modal-head">
          <h2 id="modal-title">{title}</h2>
          <button
            className="icon-button"
            aria-label="关闭对话框"
            onClick={onClose}
          >
            <X size={20} />
          </button>
        </div>
        {server.active && server.error && <div className="account-error" role="alert">{server.error}<button className="button small" type="button" disabled={server.busy} onClick={server.reload}>重新载入服务器版本</button><p>表单内容仍保留，请核对后再保存。</p></div>}
        <fieldset className="dialog-fields" disabled={server.active && server.busy}>{children}</fieldset>
      </div>
    </div>
  );
}
export function DemoNote({ children }: { children?: ReactNode }) {
  const server=useContext(ServerContext);
  return (
    <div className="demo-note">
      <Sparkles size={16} />
      <span>
        {server.active ? "课程、章节与作答记录已接入账号；客观题由后端核对，开放练习与作业文字答案支持 AI 批改，附件仍待评阅。" : (children || "本地演示 · 示例数据保存在当前浏览器，尚未连接模型。")}
      </span>
    </div>
  );
}
export function TextLink({
  children,
  onClick,
}: {
  children: ReactNode;
  onClick: () => void;
}) {
  return (
    <button className="text-link" onClick={onClick}>
      {children}
      <ArrowRight size={15} />
    </button>
  );
}
export function formatTime(time: string) {
  return new Intl.DateTimeFormat("zh-CN", {
    month: "2-digit",
    day: "2-digit",
    hour: "2-digit",
    minute: "2-digit",
  }).format(new Date(time));
}
