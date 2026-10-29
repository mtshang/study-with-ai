import { useContext, useEffect, useState } from "react";
import { Plus, Sparkles, Plug, ArrowUpRight } from "lucide-react";
import { ConnectorEditor } from "./ConnectorEditor";
import { PageTitle, Modal } from "../components/ui";

const categories = [
  { id: "my-skill", label: "我的技能（skill）", kind: "skill", system: false },
  { id: "my-mcp", label: "我的连接器（MCP）", kind: "MCP", system: false },
  {
    id: "system-skill",
    label: "系统内置技能（skill）",
    kind: "skill",
    system: true,
  },
  {
    id: "system-mcp",
    label: "系统内置连接器（MCP）",
    kind: "MCP",
    system: true,
  },
] as const;
type Category = (typeof categories)[number];
type Entry = {
  id: string;
  category: Category["id"];
  name: string;
  description: string;
  example: boolean;
  configuration?:string;
  builtin?: { license: string; upstream: string; commit: string };
};
const skillSamples = [
  ["概念拆解", "从日常例子开始，逐步解释抽象概念。"],
  ["练习出题", "围绕当前章节组织练习与参考答案。"],
  ["作业讲评", "结合提交内容梳理思路与改进方向。"],
  ["学习路线", "按学习目标拆分章节与学习步骤。"],
  ["错题复习", "归纳易错点，安排有针对性的复习。"],
];
const mcpSamples = [
  ["网页搜索", "寻找课程相关的公开资料与参考来源。"],
  ["文档读取", "读取教材文档，辅助资料整理。"],
  ["浏览器工具", "打开网页并读取页面中的学习内容。"],
  ["代码运行", "连接独立执行环境，查看代码运行结果。"],
  ["知识库检索", "从课程资料中检索相关内容。"],
];
const samples: Entry[] = categories.filter(c => c.id !== "system-skill").flatMap((c) =>
  (c.kind === "skill" ? skillSamples : mcpSamples).map(
    ([name, description], i) => ({
      id: `${c.id}-${i}`,
      category: c.id,
      name,
      description,
      example: true,
    }),
  ),
);

import {ServerContext} from '../serverWorkspace';
import {PersonalExtensions} from './PersonalExtensions';
export function Connectors(){const server=useContext(ServerContext);return server.active&&server.userId?<PersonalExtensions key={server.userId} userId={server.userId}/>:<DemoConnectors/>;}
function DemoConnectors() {
  const [categoryId, setCategoryId] = useState<Category["id"]>("my-skill");
  const [entries, setEntries] = useState(samples);
  const [builtin, setBuiltin] = useState<Entry[]>([]);
  const [catalogError, setCatalogError] = useState("");
  const [loading, setLoading] = useState(true);
  useEffect(() => {
    const controller = new AbortController();
    fetch('/api/ai/reading-skills', {signal: controller.signal})
      .then(async response => {
        if (!response.ok) throw new Error('内置技能暂不可用，请检查后端后刷新页面。');
        const rows: {id:string;name:string;description:string;license:string;upstream:string;commit:string}[] = await response.json();
        setBuiltin(rows.map(row => ({id:row.id,category:'system-skill',name:row.name,description:row.description,example:false,builtin:row})));
      }).catch(error => {if (!controller.signal.aborted) setCatalogError(error.message);})
      .finally(() => {if (!controller.signal.aborted) setLoading(false);});
    return () => controller.abort();
  }, []);
  const [creating, setCreating] = useState<Category | null>(null);
  const [detail, setDetail] = useState<Entry | null>(null);

  const category = categories.find((c) => c.id === categoryId)!;
  const Icon = category.kind === "skill" ? Sparkles : Plug;
  const visible = [...entries, ...builtin].filter((e) => e.category === categoryId);
  return (
    <>
      <PageTitle
        eyebrow="EXTEND YOUR LEARNING"
        title="技能·连接器"
        description="管理教学技能与工具连接器，为 AI 导师扩展能力。"
        action={
          <button
            className="button primary connector-create"
            onClick={() => {
              setCreating(category);

            }}
          >
            <Plus size={18} />
            新建{category.label}
          </button>
        }
      />
      <div
        className="tab-row connector-tabs"
        role="group"
        aria-label="技能与连接器分类"
      >
        {categories.map((c) => (
          <button
            key={c.id}
            className={categoryId === c.id ? "selected" : ""}
            aria-pressed={categoryId === c.id}
            onClick={() => setCategoryId(c.id)}
          >
            {c.label}
          </button>
        ))}
      </div>
      <div className="connector-summary">
        <span>
          {category.system ? "系统内置" : "个人空间"} ·{" "}
          {category.kind === "skill" ? "教学技能" : "工具连接器"}
        </span>
        <span>{visible.length} 项</span>
      </div>
      {categoryId === 'system-skill' && <p className="fine-print" role="status">{loading ? '正在读取内置技能…' : catalogError || '同一开源 MarkItDown Skill 的三个格式适配：教师可在课程聊天中读取已上传资料。'}</p>}
      <div className="connector-cards">
        {visible.map((entry) => (
          <button
            className="connector-card"
            key={entry.id}
            onClick={() => setDetail(entry)}
            aria-label={`查看${entry.name}`}
          >
            <div className="connector-card-top">
              <span className="connector-card-icon">
                <Icon size={22} />
              </span>
              <span className="connector-badge">
                {entry.builtin ? "已内置" : entry.example ? "示例" : "草稿"}
              </span>
            </div>
            <h2>{entry.name}</h2>
            <p>{entry.description || "还没有添加说明。"}</p>
            <div className="connector-card-footer">
              <span>{category.kind === "skill" ? "SKILL" : "MCP"}</span>
              <ArrowUpRight size={16} />
            </div>
          </button>
        ))}
      </div>
      <p className="fine-print connector-boundary">内置资料技能已接入教师的受控读取工具；不执行技能脚本。其他示例仅用于预览。导入和配置目前保留为本页草稿，刷新或离开页面后重置；尚未上传至服务器或实际连接 MCP。</p>
      {creating && <ConnectorEditor kind={creating.kind} onClose={()=>setCreating(null)} onSave={draft=>{
        setEntries(items=>[...items,{id:crypto.randomUUID(),category:creating.id,...draft,example:false}]);setCreating(null);
      }}/>}
      {detail && (
        <Modal title={detail.name} onClose={() => setDetail(null)}>
          <div className="prose">
            <p>{detail.description || "还没有添加说明。"}</p>
            {detail.configuration&&<pre className="connector-config-preview">{detail.configuration}</pre>}
            {detail.builtin && <><p>许可证：{detail.builtin.license} · 基于 K-Dense MarkItDown Skill 适配</p><p><a href={detail.builtin.upstream} target="_blank" rel="noreferrer">查看固定版本来源</a></p><p>在课程资料中上传对应文件，再在 AI 聊天中要求阅读、讲解或出题。当前不支持扫描件 OCR、网页抓取或任意代码执行。</p></>}
            <p className="muted">
              {detail.builtin ? "仅可读取当前账号当前课程的资料。原文作为参考内容，不授予操作权限。" : detail.example
                ? "这是布局示例，尚未接入真实技能或 MCP 服务。"
                : "这是本次页面中的演示草稿，尚未保存到文件或接入工具。"}
            </p>
          </div>
          <div className="modal-actions">
            <button className="button primary" onClick={() => setDetail(null)}>
              关闭
            </button>
          </div>
        </Modal>
      )}
    </>
  );
}
