import { useContext, useEffect, useLayoutEffect, useRef, useState } from "react";
import {
  ArrowRight,
  CheckCircle2,
  FileText,
  Download,
  History,
  MessageSquare,
  NotebookPen,
  PencilLine,
  Plus,
  Send,
  Upload,
  Trash2,
} from "lucide-react";
import type {
  Assignment,
  Course,
  Submission,
  SubmissionAttachment,
  UpdateCourse,
} from "../types";
import { now, uid } from "../data";
import { saveDownloadedFile } from "../download";
import { ServerContext } from "../serverWorkspace";
import {CodeExercise} from './CodeExercise';
import {GradeFeedback} from "./GradeFeedback";
import {
  Badge,
  DemoNote,
  Empty,
  formatTime,
  Modal,
  PageTitle,
} from "../components/ui";

export function Activities({
  course,
  kind,
  update,
  toast,
}: {
  course: Course;
  kind: "exercise" | "assignment";
  update: UpdateCourse;
  toast: (text: string) => void;
}) {
  const server = useContext(ServerContext);
  const attempt = useRef<{ signature:string; id:string } | null>(null);
  const [selected, setSelected] = useState<string | null>(null);
  const [filter, setFilter] = useState("all");
  const [chapterFilter, setChapterFilter] = useState("all");
  const [creating, setCreating] = useState(false);
  const [answers, setAnswers] = useState<Record<string, string>>({});
  const [attachments,setAttachments]=useState<string[]>([]);
  const files=course.materials.filter(m=>m.kind==="文件"&&m.downloadable);
  const [feedback, setFeedback] = useState<Submission | null>(null);
  const [history, setHistory] = useState(false);
  useEffect(()=>{
    if(!feedback||!server.active)return;
    const latest=course.submissions.find(s=>s.id===feedback.id);
    if(latest&&latest!==feedback)setFeedback(latest);
  },[course.submissions,feedback?.id,server.active]);
  const isExercise = kind === "exercise";
  const label = isExercise ? "练习" : "作业";
  const entries = isExercise
    ? course.exercises.map((q) => ({
        id: q.id,
        title: q.prompt,
        description: q.python ? "Python 标准输入／输出 · 提交后在临时容器运行公开用例。" : q.options
          ? "选择最合适的答案，提交后查看解析。"
          : (server.active ? "用自己的话解释，提交后由 AI 批改，保留每次答案与评价。" : "试着用自己的话解释，提交后查看示例反馈。"),
        chapterId: q.chapterId,
        questions: [q],
      }))
    : course.assignments;
  const filtered = entries.filter(
    (item) =>
      (filter === "all" ||
        (filter === "pending"
          ? !course.submissions.some((s) => s.targetId === item.id)
          : course.submissions.some((s) => s.targetId === item.id))) &&
      (chapterFilter === "all" ||
        (chapterFilter === "none"
          ? !item.chapterId
          : item.chapterId === chapterFilter)),
  );
  const item = entries.find((entry) => entry.id === selected);
  const submissions = course.submissions.filter(
    (s) => s.targetId === selected && s.kind === kind,
  );
  const submit = async () => {
    if (!item || item.questions.some((q) => !answers[q.id]?.trim())) return;
    if(server.active) {
      const signature=JSON.stringify({activity:item.id,answers,attachments:[...attachments].sort()});
      if(attempt.current?.signature!==signature) attempt.current={signature,id:uid()};
      const result=await server.submit(course.id,item.id,answers,attempt.current.id,attachments);
      if(!result) return;
      setFeedback(result);toast(result.aiGrade?"提交已保存，可在下方查看 AI 批改进度":result.verdict==="pending"?"提交已保存，含待评阅内容":"提交已保存，客观题已核对");return;
    }
    const objective = item.questions.filter((q) => q.correct !== undefined);
    const correct = objective.filter((q) => answers[q.id] === q.correct).length;
    const allObjective = objective.length === item.questions.length;
    const explanations = objective
      .map(
        (q) =>
          `${answers[q.id] === q.correct ? "回答正确" : "需要再想一想"}：${q.prompt}\n参考答案：${q.correct}\n${q.explanation}`,
      )
      .join("\n\n");
    const response: Submission = {
      id: uid(),
      kind,
      targetId: item.id,
      answers: { ...answers },
      createdAt: now(),
      verdict: allObjective
        ? correct === objective.length
          ? "correct"
          : "incorrect"
        : "demo",
      feedback: allObjective
        ? `本次 ${correct} / ${objective.length} 题回答正确。\n\n${explanations}`
        : `提交已保存。当前没有连接 AI，下面仅展示反馈样式，不代表对答案正确性的评估。\n\n示例反馈：可以先说清概念，再用一个具体例子解释你的思路。接入模型后，这里会显示针对本次提交的批改与讲解。${explanations ? "\n\n客观题核对：\n" + explanations : ""}`,
    };
    update(
      course.id,
      (c) => ({ ...c, submissions: [response, ...c.submissions] }),
      { category: label, text: `提交${label}「${item.title}」` },
    );
    setFeedback(response);
    toast(
      allObjective
        ? "答案已保存，已按预置答案核对"
        : "提交已保存；开放题展示的是示例反馈",
    );
  };
  return (
    <>
      <PageTitle
        eyebrow={isExercise ? "A LITTLE PRACTICE" : "PUT IDEAS INTO ACTION"}
        title={label}
        description={
          isExercise
            ? "一道题，一点新理解。不怕答错，试过才知道。"
            : "把学过的知识串起来，留下自己的思考过程。"
        }
        action={
          <button className="button primary" onClick={() => setCreating(true)}>
            <Plus size={16} />
            {`创建${label}`}
          </button>
        }
      />
      <div className="toolbar">
        <div className="tab-row" role="group" aria-label={`${label}筛选`}>
          {[
            ["all", `全部${label}`],
            ["pending", "未提交"],
            ["submitted", "已提交"],
          ].map(([key, text]) => (
            <button
              className={filter === key ? "selected" : ""}
              key={key}
              onClick={() => setFilter(key)}
            >
              {text}
            </button>
          ))}
        </div>
        <select
          aria-label="按章节筛选"
          value={chapterFilter}
          onChange={(e) => setChapterFilter(e.target.value)}
        >
          <option value="all">全部章节</option>
          <option value="none">未分类</option>
          {course.chapters.map((ch) => (
            <option value={ch.id} key={ch.id}>
              {ch.title}
              {ch.archived ? "（已移出）" : ""}
            </option>
          ))}
        </select>
      </div>
      <div className={isExercise ? "exercise-list" : "assignment-grid"}>
        {filtered.map((entry, index) => {
          const previous = course.submissions.filter(
            (s) => s.targetId === entry.id && s.kind === kind,
          );
          const chapter = course.chapters.find(
            (ch) => ch.id === entry.chapterId,
          );
          return (
            <article
              className={`panel activity-card ${isExercise ? "exercise-card" : ""}`}
              key={entry.id}
            >
              <span
                className={`activity-symbol ${isExercise ? "blue" : "orange"}`}
              >
                {isExercise ? (
                  <PencilLine size={22} />
                ) : (
                  <NotebookPen size={25} />
                )}
              </span>
              <div className="activity-body">
                <div className="activity-labels">
                  <span className="eyebrow">
                    {isExercise
                      ? `练习 ${String(index + 1).padStart(2, "0")}`
                      : "课程作业"}
                  </span>
                  <Badge tone={previous.length ? "green" : "orange"}>
                    {previous.length ? "已提交" : "未提交"}
                  </Badge>
                  {isExercise && (
                    <Badge>
                      {entry.questions[0].options ? "客观题" : "开放题"}
                    </Badge>
                  )}
                </div>
                <h3>{entry.title}</h3>
                <p>
                  {isExercise
                    ? chapter?.title || "未分类练习"
                    : entry.description}
                </p>
                {!isExercise && (
                  <div className="assignment-meta">
                    <span>
                      <FileText size={14} />
                      {entry.questions.length} 道题
                    </span>
                    <span>{chapter?.title || "未分类作业"}</span>
                  </div>
                )}
                <div className="activity-footer">
                  <span>
                    {previous.length
                      ? `${previous.length} 次提交 · 保留历史记录`
                      : isExercise
                        ? "提交后查看反馈"
                        : "按自己的节奏完成"}
                  </span>
                  <button
                    className={`button ${isExercise ? "" : "primary"}`}
                    onClick={() => {
                      setSelected(entry.id);
                      setAnswers({});
                      setAttachments([]);
                      attempt.current=null;
                      setFeedback(null);
                      setHistory(false);
                    }}
                  >
                    {previous.length
                      ? "再次作答"
                      : isExercise
                        ? "开始练习"
                        : "查看作业"}
                    <ArrowRight size={16} />
                  </button>
                </div>
              </div>
            </article>
          );
        })}
      </div>
      {!filtered.length && (
        <Empty
          title={`还没有${filter === "submitted" ? "已提交的" : filter === "pending" ? "未提交的" : ""}${label}`}
          description={`可以手动创建，或到 AI 导师页面体验发布${label}。`}
          action={
            <button
              className="button"
              onClick={() => {
                location.hash = `/courses/${course.id}/chat`;
              }}
            >
              <MessageSquare size={16} />
              前往 AI 导师
            </button>
          }
        />
      )}
      <DemoNote>
        {server.active?"Python练习由临时容器运行公开用例；选择题由后端核对；开放问答与作业文字答案由 AI 批改；附件仍待评阅。":"客观题按预置答案核对；开放题只展示示例反馈，尚未执行真实 AI 批改。"}
      </DemoNote>
      {item?.questions[0].python&&<CodeExercise key={item.id} courseId={course.id} activityId={item.id} question={item.questions[0]} onClose={()=>setSelected(null)}/>}
      {item && !item.questions[0].python && (
        <Modal
          title={isExercise ? "练习与反馈" : item.title}
          wide
          onClose={() => setSelected(null)}
        >
          <div className="activity-modal-header">
            <Badge>{label}</Badge>
            <button className="text-link" onClick={() => setHistory(!history)}>
              <History size={15} />
              {history ? "返回作答" : `提交历史（${submissions.length}）`}
            </button>
          </div>
          {history ? (
            <div>
              {submissions.length ? (
                submissions.map((s) => (
                  <div className="submission-history" key={s.id}>
                    <div className="section-heading">
                      <strong>{formatTime(s.createdAt)}</strong>
                      <Badge>
                        {s.verdict === "reviewed" ? "AI 已批改" : s.verdict === "pending" ? "待批改" : s.verdict === "demo" ? "示例反馈" : "客观题核对"}
                      </Badge>
                    </div>
                    {(s.questions || item.questions).map((q) => (
                      <div className="past-answer" key={q.id}>
                        <strong>{q.prompt}</strong>
                        <p>{s.answers[q.id] || "未作答"}</p>
                      </div>
                    ))}
                    {s.answers.__attachment && (
                      <p className="fine-print">
                        附件记录：{s.answers.__attachment}
                      </p>
                    )}
                    {server.active&&<SubmittedFiles courseId={course.id} attachments={s.attachments||[]}/>}
                    {!s.aiGrade&&<div className="feedback-text">{s.feedback}</div>}
                    {server.active&&s.aiGrade&&<GradeFeedback courseId={course.id} initial={s.aiGrade}/>}
                  </div>
                ))
              ) : (
                <Empty
                  title="尚未提交"
                  description="完成本次作答后，记录会保存在这里。"
                />
              )}
            </div>
          ) : (
            <>
              <p className="muted">{item.description}</p>
              <form
                onSubmit={(e) => {
                  e.preventDefault();
                  submit();
                }}
              >
                {item.questions.map((question, index) => (
                  <fieldset className="question-field" key={question.id}>
                    <legend>
                      <span>{String(index + 1).padStart(2, "0")}</span>
                      {question.prompt}
                    </legend>
                    {question.options ? (
                      <div className="answer-options">
                        {question.options.map((option, i) => (
                          <label
                            className={
                              answers[question.id] === option ? "selected" : ""
                            }
                            key={option}
                          >
                            <input
                              type="radio"
                              required
                              name={question.id}
                              value={option}
                              checked={answers[question.id] === option}
                              onChange={() => {
                                setAnswers((previous) => ({
                                  ...previous,
                                  [question.id]: option,
                                }));
                                setFeedback(null);
                              }}
                            />
                            <span className="option-letter">
                              {String.fromCharCode(65 + i)}
                            </span>
                            <span>{option}</span>
                            {answers[question.id] === option && (
                              <CheckCircle2 size={17} />
                            )}
                          </label>
                        ))}
                      </div>
                    ) : (
                      <textarea
                        aria-label={`第${index + 1}题答案`}
                        required
                        rows={5}
                        maxLength={10000}
                        placeholder="写下你的思路，不用担心是否完美。"
                        value={answers[question.id] || ""}
                        onChange={(e) => {
                          setAnswers((previous) => ({
                            ...previous,
                            [question.id]: e.target.value,
                          }));
                          setFeedback(null);
                        }}
                      />
                    )}
                  </fieldset>
                ))}
                {!isExercise && server.active && (
                  <fieldset className="question-field assignment-attachments">
                    <legend>作业附件（可选，最多 5 份）</legend>
                    <p className="fine-print">从本课程资料中选择已上传的文件。提交只引用附件名称；删除原资料后不能下载，暂不自动评阅。</p>
                    {files.length ? <div className="attachment-options">{files.map(file=><label key={file.id}>
                      <input type="checkbox" checked={attachments.includes(file.id)}
                        disabled={!attachments.includes(file.id)&&attachments.length>=5}
                        onChange={e=>{setAttachments(previous=>e.target.checked?[...previous,file.id]:previous.filter(id=>id!==file.id));setFeedback(null);}}/>
                      <span>{file.filename||file.title}<small>{file.size??0} 字节 · 文件 {file.id.slice(0,8)}</small></span>
                    </label>)}</div> : <p className="fine-print">暂无可选文件。可以先在课程资料页上传文件，再回来作答。</p>}
                  </fieldset>
                )}
                {!isExercise && !server.active && (
                  <label className="attachment-field">
                    <Upload size={17} />
                    添加附件记录（演示，不上传文件）
                    <input
                      type="file"
                      onChange={(e) =>
                        setAnswers((previous) => ({
                          ...previous,
                          __attachment: e.target.files?.[0]?.name || "",
                        }))
                      }
                    />
                    {answers.__attachment && (
                      <small>{answers.__attachment}</small>
                    )}
                  </label>
                )}
                <div className="modal-actions">
                  <button
                    type="button"
                    className="button"
                    onClick={() => setSelected(null)}
                  >
                    稍后再做
                  </button>
                  <button
                    className="button primary"
                    disabled={
                      !!feedback || server.busy ||
                      item.questions.some((q) => !answers[q.id]?.trim())
                    }
                  >
                    <Send size={16} />
                    {feedback
                      ? "本次答案已保存"
                      : isExercise
                        ? "提交答案"
                        : "提交作业"}
                  </button>
                </div>
              </form>
              {feedback && (
                <div
                  className={`feedback-box ${feedback.verdict}`}
                  role="status"
                >
                  <div className="section-heading">
                    <h3>
                      {feedback.verdict === "reviewed" ? "AI 批改已保存" : feedback.verdict === "correct"
                        ? "回答正确"
                        : feedback.verdict === "incorrect"
                          ? "再想一想，也是在进步"
                          : "提交已保存"}
                    </h3>
                    <Badge>
                      {feedback.verdict === "reviewed" ? "AI 已批改" : feedback.verdict === "pending" ? "待批改" : feedback.verdict === "demo" ? "演示反馈" : "参考答案核对"}
                    </Badge>
                  </div>
                  {server.active&&<SubmittedFiles courseId={course.id} attachments={feedback.attachments||[]}/>}
                  {!feedback.aiGrade&&<div className="feedback-text">{feedback.feedback}</div>}
                  {server.active&&feedback.aiGrade&&<GradeFeedback courseId={course.id} initial={feedback.aiGrade}/>}
                </div>
              )}
            </>
          )}
        </Modal>
      )}
      {creating && (
        <ActivityEditor
          course={course}
          kind={kind}
          onClose={() => setCreating(false)}
          onSave={async (entry) => {
            if(server.active) {
              if(!await server.publish(course.id,entry,kind)) return;
              setCreating(false);toast(`${label}已发布并保存`);return;
            }
            if (isExercise) {
              const q = entry.questions[0];
              update(
                course.id,
                (c) => ({
                  ...c,
                  exercises: [
                    ...c.exercises,
                    { ...q, id: entry.id, chapterId: entry.chapterId },
                  ],
                }),
                { category: "练习", text: `创建练习「${entry.title}」` },
              );
            } else
              update(
                course.id,
                (c) => ({ ...c, assignments: [...c.assignments, entry] }),
                { category: "作业", text: `创建作业「${entry.title}」` },
              );
            setCreating(false);
            toast(`${label}已创建`);
          }}
        />
      )}
    </>
  );
}

export function SubmittedFiles({courseId,attachments}:{courseId:string;attachments:SubmissionAttachment[]}) {
  const server=useContext(ServerContext);
  if(!attachments.length)return null;
  return <div className="submitted-files" aria-label="本次提交附件">
    <strong>本次提交附件</strong>
    {attachments.map(file=><div className="submitted-file" key={file.id}>
      <span>{file.filename}<small>{file.size} 字节 · 文件 {file.id.slice(0,8)}</small></span>
      <button type="button" className="button" disabled={server.busy||file.deleted} aria-label={`下载附件 ${file.filename}`} onClick={async()=>{
        const blob=await server.downloadMaterial(courseId,file.id);
        if(blob)saveDownloadedFile(blob,file.filename);
      }}><Download size={15}/>{file.deleted?"原资料已删除":"下载"}</button>
    </div>)}
  </div>;
}

type OptionDraft = { id:string; text:string };
type QuestionDraft = {prompt:string; type:"open"|"judge"|"choice"|"python"; starter:string; cases:{stdin:string;expected_stdout:string}[]; options:OptionDraft[]; correctId:string|null; correct:string; explanation:string};
const emptyQuestion=():QuestionDraft=>({prompt:"",type:"open",starter:"",cases:[{stdin:"",expected_stdout:""}],options:[],correctId:null,correct:"正确",explanation:""});
const letter=(index:number)=>String.fromCharCode(65+index);

function OptionInput({value,label,onChange}:{value:string;label:string;onChange:(text:string)=>void}) {
  const ref=useRef<HTMLTextAreaElement>(null);
  useLayoutEffect(()=>{
    const input=ref.current;if(!input)return;
    const resize=()=>{input.style.height="auto";input.style.height=`${input.scrollHeight}px`;};
    resize();
    const observer=new ResizeObserver(()=>{if(input.clientWidth!==width){width=input.clientWidth;resize();}});
    let width=input.clientWidth;observer.observe(input);
    return ()=>observer.disconnect();
  },[value]);
  return <textarea ref={ref} className="choice-text" aria-label={label} required rows={1} maxLength={200} value={value} placeholder="填写选项内容" onChange={e=>onChange(e.target.value)}/>;
}

function ActivityEditor({course,kind,onClose,onSave}:{course:Course;kind:"exercise"|"assignment";onClose:()=>void;onSave:(entry:Assignment)=>void}) {
  const [id]=useState(uid);
  const [title,setTitle]=useState("");
  const [description,setDescription]=useState("");
  const [chapterId,setChapterId]=useState(course.currentChapterId||"");
  const exercise=kind==="exercise";
  const [drafts,setDrafts]=useState<QuestionDraft[]>(()=>Array.from({length:exercise?1:2},emptyQuestion));
  const change=(index:number,fields:Partial<QuestionDraft>)=>setDrafts(previous=>previous.map((q,i)=>i===index?{...q,...fields}:q));
  const options=(q:QuestionDraft)=>q.type==="judge"?["正确","错误"]:q.options.map(option=>option.text.trim());
  const correct=(q:QuestionDraft)=>q.type==="judge"?q.correct:q.options.find(option=>option.id===q.correctId)?.text.trim();
  const invalid=!title.trim() || drafts.some(q=>(!exercise&&!q.prompt.trim()) || (q.type!=="open" && q.type!=="python" && (options(q).length<2||options(q).length>10||options(q).some(s=>!s||s.length>200)||new Set(options(q)).size!==options(q).length||!options(q).includes(correct(q)||""))));
  return <Modal title={exercise?"创建一道练习":"创建一份作业"} wide onClose={onClose}>
    <form onSubmit={e=>{e.preventDefault();if(invalid)return;onSave({id,title:title.trim(),description:description.trim(),chapterId:chapterId||undefined,
      questions:drafts.map(q=>({id:uid(),prompt:exercise?title.trim():q.prompt.trim(),explanation:q.explanation.trim(),...(q.type==="python"?{python:{language:"python" as const,starter_code:q.starter,cases:q.cases}}:q.type==="open"?{}:{options:options(q),correct:correct(q)} )}))});}}>
      <label className="field">{exercise?"题目":"作业名称"}<input data-autofocus required maxLength={200} value={title} onChange={e=>setTitle(e.target.value)}/></label>
      <label className="field">所属章节<select value={chapterId} onChange={e=>setChapterId(e.target.value)}><option value="">未分类</option>{course.chapters.filter(ch=>!ch.archived).map(ch=><option key={ch.id} value={ch.id}>{ch.title}</option>)}</select></label>
      {!exercise&&<label className="field">作业说明<textarea rows={2} maxLength={2000} value={description} onChange={e=>setDescription(e.target.value)}/></label>}
      {drafts.map((q,index)=><fieldset className="question-field" key={index}>
        <legend>{exercise?"题目设置":`第 ${index+1} 题`}</legend>
        {!exercise&&<label className="field">{`第 ${index+1} 题题目`}<textarea required rows={2} maxLength={3000} value={q.prompt} onChange={e=>change(index,{prompt:e.target.value})}/></label>}
        <label className="field">{exercise?"题型":`第 ${index+1} 题题型`}<select aria-label={exercise?"题型":`第 ${index+1} 题题型`} value={q.type} onChange={e=>change(index,{type:e.target.value as QuestionDraft["type"]})}><option value="open">开放问答</option>{exercise&&<option value="python">Python 输入／输出</option>}<option value="judge">判断题</option><option value="choice">单选题</option></select></label>
        {q.type==="python"&&<div><label className="field">初始代码（可选）<textarea aria-label="初始代码" rows={4} maxLength={10000} value={q.starter} onChange={e=>change(index,{starter:e.target.value})}/></label>{q.cases.map((c,i)=><fieldset key={i}><legend>测试用例 {i+1}</legend><label className="field">输入<textarea aria-label={`用例 ${i+1} 输入`} rows={2} maxLength={4000} value={c.stdin} onChange={e=>change(index,{cases:q.cases.map((x,j)=>j===i?{...x,stdin:e.target.value}:x)})}/></label><label className="field">预期输出<textarea aria-label={`用例 ${i+1} 预期输出`} rows={2} maxLength={4000} value={c.expected_stdout} onChange={e=>change(index,{cases:q.cases.map((x,j)=>j===i?{...x,expected_stdout:e.target.value}:x)})}/></label><button className="text-link" type="button" disabled={q.cases.length===1} onClick={()=>change(index,{cases:q.cases.filter((_,j)=>j!==i)})}>删除用例 {i+1}</button></fieldset>)}<button className="button" type="button" disabled={q.cases.length>=3} onClick={()=>change(index,{cases:[...q.cases,{stdin:'',expected_stdout:''}]})}>添加测试用例</button><p>1～3个公开用例；仅统一换行和忽略末尾换行，空格参与比较。</p></div>}
        {q.type==="choice"&&<div className="choice-editor">
          <div className="choice-heading"><strong>选项</strong><button type="button" className="button small" aria-label={exercise?"创建选项":`第 ${index+1} 题创建选项`} disabled={q.options.length>=10} onClick={()=>change(index,{options:[...q.options,{id:uid(),text:""}]})}><Plus size={16}/>创建选项</button></div>
          {!q.options.length&&<p className="fine-print">点击创建选项，从 A 开始添加。</p>}
          {q.options.map((option,i)=><div className="choice-edit-row" key={option.id}>
            <span className="choice-letter">{letter(i)}</span>
            <OptionInput value={option.text} label={exercise?`选项 ${letter(i)}`:`第 ${index+1} 题选项 ${letter(i)}`} onChange={text=>change(index,{options:q.options.map(o=>o.id===option.id?{...o,text}:o)})}/>
            <button type="button" className="icon-button choice-delete" aria-label={exercise?`删除选项 ${letter(i)}`:`第 ${index+1} 题删除选项 ${letter(i)}`} onClick={()=>change(index,{options:q.options.filter(o=>o.id!==option.id),correctId:q.correctId===option.id?null:q.correctId})}><Trash2 size={18}/></button>
          </div>)}
          <p className="fine-print">2–10 个不重复选项，每项最多 200 字。删除后字母自动顺延。</p>
          <div className="field"><strong>参考答案</strong><div className="choice-answer-buttons" role="group" aria-label={exercise?"参考答案":`第 ${index+1} 题参考答案`}>
            {q.options.map((option,i)=><button type="button" key={option.id} className={`choice-answer ${q.correctId===option.id?"selected":""}`} aria-label={letter(i)} aria-pressed={q.correctId===option.id} onClick={()=>change(index,{correctId:option.id})}>{letter(i)}</button>)}
          </div><small>{!q.options.length?"创建选项后选择对应字母。":q.correctId?`已选择 ${letter(q.options.findIndex(o=>o.id===q.correctId))}`:"请选择参考答案；删除已选项后需要重新选择。"}</small></div>
        </div>}
        {q.type==="judge"&&<label className="field">{exercise?"参考答案":`第 ${index+1} 题参考答案`}<select aria-label={exercise?"参考答案":`第 ${index+1} 题参考答案`} value={q.correct} onChange={e=>change(index,{correct:e.target.value})}><option>正确</option><option>错误</option></select></label>}
        <label className="field">{exercise?"参考解析":`第 ${index+1} 题参考解析`}<textarea rows={2} maxLength={3000} value={q.explanation} onChange={e=>change(index,{explanation:e.target.value})}/></label>
      </fieldset>)}
      {!exercise&&<button type="button" className="text-link" disabled={drafts.length>=10} onClick={()=>setDrafts(q=>[...q,emptyQuestion()])}><Plus size={15}/>再加一道题（最多 10 题）</button>}
      <p className="fine-print">发布后保留原题；需要调整时创建新题，避免改变历史作答依据。账号空间的新提交开放练习与作业文字答案支持 AI 批改；附件仍待评阅。</p>
      <div className="modal-actions"><button type="button" className="button" onClick={onClose}>取消</button><button className="button primary" disabled={invalid}>确认创建</button></div>
    </form>
  </Modal>;
}
