export type Permission = "manual" | "assisted" | "full";
export type Source = "system" | "user" | "generated" | "web";
export type Chapter = {
  id: string;
  title: string;
  description: string;
  content: string;
  read: boolean;
  archived?: boolean;
};
export type PythonExercise={language:'python';starter_code:string;cases:{stdin:string;expected_stdout:string}[]};
export type CodeRun={status:string;total:number;passed:number;error:string;cases:{number:number;stdin:string;expected_stdout:string;stdout:string;stderr:string;status:string;exit_code:number|null;duration_ms:number;passed:boolean;output_truncated:boolean}[]};
export type Question = {
  python?:PythonExercise;
  id: string;
  prompt: string;
  options?: string[];
  correct?: string;
  explanation: string;
  chapterId?: string;
};
export type Assignment = {
  id: string;
  title: string;
  description: string;
  chapterId?: string;
  questions: Question[];
};
export type SubmissionAttachment = { deleted?:boolean; id:string; filename:string; size:number };
export type GradeResult={mastery:'mastered'|'partial'|'needs_practice';reason:string;evidence:string[];suggestions:string[];sample_answer:string};
export type AIGrade = {
  kind?:'assignment'; pending_attachment_count?:number;
  items?:{question_id:string;number:number;question:string;status:'waiting'|'running'|'failed'|'completed';result:GradeResult|null;error:string;model:string}[];
  objective_results?:{questionId:string;number:number;question:string;answer:string;verdict:string;correct:string;explanation:string}[];
  id:string; submission_id:string; status:'waiting'|'running'|'failed'|'completed'; error:string; model:string; updated_at:string;
  result:null|GradeResult;
};
export type Submission = {
  id: string;
  targetId: string;
  targetTitle?:string;
  targetDeleted?:boolean;
  targetTrashed?:boolean;
  kind: "exercise" | "assignment";
  answers: Record<string, string>;
  createdAt: string;
  feedback: string;
  verdict: "correct" | "incorrect" | "demo" | "pending" | "reviewed";
  aiGrade?:AIGrade;
  codeRun?:CodeRun;
  questions?: Question[];
  correctCount?: number;
  objectiveCount?: number;
  pendingCount?: number;
  attachments?: SubmissionAttachment[];
  pendingAttachmentCount?: number;
};
export type Material = {
  id: string;
  title: string;
  source: Source;
  kind: string;
  description: string;
  url?: string;
  filename?: string;
  size?: number;
  downloadable?: boolean;
};
export type Message = { id: string; role: "user" | "assistant"; text: string };
export type Event = {
  id: string;
  text: string;
  time: string;
  category: string;
};
export type Revision = {
  id: string;
  version: number;
  time: string;
  summary: string;
  titles: string[];
};
export type Course = {
  version?: number;
  source?: Source;
  id: string;
  title: string;
  goal: string;
  category: string;
  color: "green" | "blue" | "orange" | "purple";
  icon: "code" | "language" | "design" | "book";
  archived: boolean;
  currentChapterId?: string;
  chapters: Chapter[];
  exercises: Question[];
  assignments: Assignment[];
  submissions: Submission[];
  materials: Material[];
  messages: Message[];
  events: Event[];
  revisions: Revision[];
};
export type DisplayPreferences = { version:number; fontOffset:number; compact:boolean };
export type Settings = {
  name: string;
  permission: Permission;
  compact: boolean;
  fontOffset: number;
};
export type Workspace = {
  version: 1;
  courses: Course[];
  activeCourseId: string;
  settings: Settings;
};
export type UpdateCourse = (
  courseId: string,
  update: (course: Course) => Course,
  event?: { text: string; category: string },
) => void | Promise<boolean>;
