import type { Chapter, Course, Workspace } from "./types";

export const uid = () => crypto.randomUUID();
export const now = () => new Date().toISOString();
export const sourceLabels = {
  system: "系统预置",
  user: "我的上传",
  generated: "AI 生成",
  web: "网络资料",
};
export const permissionLabels = {
  manual: "完全手动",
  assisted: "部分批准",
  full: "完全访问",
};
export const templates = [
  {
    title: "Python 项目入门",
    category: "编程开发",
    icon: "code",
    color: "green",
    description: "从一个小项目开始，认识变量、函数与数据处理。",
    tags: ["项目实践", "适合入门"],
    goal: "用 Python 独立完成一个实用小工具",
  },
  {
    title: "日常英语表达",
    category: "语言学习",
    icon: "language",
    color: "blue",
    description: "围绕真实生活场景，练习更自然的英文表达。",
    tags: ["场景练习", "表达能力"],
    goal: "在日常交流中清晰、自然地表达",
  },
  {
    title: "设计入门：看懂好设计",
    category: "设计与创意",
    icon: "design",
    color: "orange",
    description: "通过观察与小练习，建立版式和配色的基础认识。",
    tags: ["视觉思维", "动手练习"],
    goal: "理解版式、颜色与视觉层级",
  },
] as const;

export function createCourse(
  title: string,
  goal: string,
  templateIndex?: number,
): Course {
  const template =
    templateIndex === undefined ? undefined : templates[templateIndex];
  const chapters: Chapter[] = template
    ? [
        {
          id: uid(),
          title: "认识学习目标",
          description: "明确我们要解决的问题，建立第一张知识地图。",
          content: `欢迎来到「${title}」。\n\n这是一份系统模板的示例章节，便于你体验课程界面。\n\n先思考两个问题：你希望用这门知识做什么？你已经接触过哪些内容？\n\n后续接入 AI 后，会根据你的目标生成具体讲解和练习。`,
          read: false,
        },
        {
          id: uid(),
          title: "基础概念与第一次练习",
          description: "从一个小例子入手，边理解边尝试。",
          content:
            "这里将承载基础讲解与示例。你可以先在路线页面编辑章节，再安排对应练习。",
          read: false,
        },
      ]
    : [];
  return {
    id: uid(),
    title,
    goal,
    category: template?.category || "自主学习",
    color: template?.color || "purple",
    icon: template?.icon || "book",
    archived: false,
    currentChapterId: chapters[0]?.id,
    chapters,
    exercises: [],
    assignments: [],
    submissions: [],
    materials: template
      ? [
          {
            id: uid(),
            title: "课程教学指导",
            source: "system",
            kind: "文本",
            description: template.description,
          },
        ]
      : [],
    messages: [
      {
        id: uid(),
        role: "assistant",
        text: `欢迎来到「${title}」！你可以先写下想解决的问题。当前是前端演示，消息回复使用本地示例，不会调用模型。`,
      },
    ],
    events: [{ id: uid(), time: now(), category: "课程", text: "创建了课程" }],
    revisions: [],
  };
}

export function seedWorkspace(): Workspace {
  const python = createCourse(
    "Python 编程：从入门到实践",
    "做一个能整理学习资料的小工具",
    0,
  );
  python.id = "python";
  python.chapters = [
    {
      id: "p1",
      title: "开始之前：认识 Python",
      description: "认识语言的用途，搭建你的第一个运行环境。",
      read: true,
      content:
        'Python 是一种通用编程语言。你可以用它整理数据、开发 Web 服务，或者编写自动化工具。\n\n这一章先完成两件事：理解代码交给谁执行，以及成功运行第一段程序。\n\n当你运行 print("Hello, world") 时，Python 解释器执行代码，并把文字输出到终端。',
    },
    {
      id: "p2",
      title: "变量与基础数据类型",
      description: "用变量保存信息，认识字符串、数字和布尔值。",
      read: true,
      content:
        '变量用于在程序中引用数据。例如 course_name = "Python 入门"，把字符串与名称关联起来。\n\n字符串适合表示文字，整数适合表示数量，布尔值适合表示是与否。\n\n理解一种类型时，可以先问：它表示什么？支持哪些操作？与其他类型怎样转换？',
    },
    {
      id: "p3",
      title: "条件判断与循环",
      description: "让程序根据条件做选择，并重复处理一组数据。",
      read: false,
      content:
        '当程序需要做选择时，可以使用 if；当同一种操作需要重复时，可以使用循环。\n\n例如整理学习资料：先遍历文件，再判断文件类型，最后放入对应文件夹。\n\nfor score in [86, 72, 95]:\n    if score >= 80:\n        print("达到目标", score)\n\n试着解释：循环负责什么？条件判断负责什么？如果分数是 80，程序会输出吗？',
    },
    {
      id: "p4",
      title: "函数：组织可复用的逻辑",
      description: "把重复的步骤组织成函数，让程序更清楚。",
      read: false,
      content:
        "函数把输入、处理步骤与返回结果组织在一起。\n\n先明确这个函数负责解决什么问题，再决定参数与返回值。你可以在作业中练习将一段重复逻辑提取为函数。",
    },
    {
      id: "p5",
      title: "文件读写与小项目",
      description: "读写本地文件，把学过的知识串起来。",
      read: false,
      content:
        "这一阶段将使用文件读取、条件判断和函数，完成一个学习资料整理工具。\n\n先从读取一个文本文件开始，再逐步增加分类与保存功能。",
    },
  ];
  python.currentChapterId = "p3";
  python.exercises = [
    {
      id: "q1",
      chapterId: "p3",
      prompt: "下面哪一个关键字用于 Python 的条件判断？",
      options: ["for", "if", "def", "return"],
      correct: "if",
      explanation:
        "if 根据条件选择执行分支；for 用于迭代，def 定义函数，return 返回函数结果。",
    },
    {
      id: "q2",
      chapterId: "p3",
      prompt: "判断：for 循环只能遍历数字，不能遍历字符串。",
      options: ["正确", "错误"],
      correct: "错误",
      explanation: "字符串也是可迭代对象，for 可以依次取得其中的字符。",
    },
    {
      id: "q3",
      chapterId: "p2",
      prompt: "用自己的话解释：变量和它所引用的数据有什么区别？",
      explanation:
        "可以从名称、数据和赋值三个角度说明，再举一个具体例子。开放题反馈目前仅为演示。",
    },
  ];
  python.assignments = [
    {
      id: "hw1",
      chapterId: "p3",
      title: "让程序做出选择",
      description:
        "用这一章的知识，解释条件判断与循环如何共同解决问题。允许多次提交，每次提交都会独立保存。",
      questions: [
        {
          id: "h1",
          prompt:
            "一个学生成绩是 80，条件为 score >= 80，是否会进入 if 分支？请说明原因。",
          explanation: "",
        },
        {
          id: "h2",
          prompt: "写出遍历 [65, 82, 91] 并输出大于 80 的分数的代码或思路。",
          explanation: "",
        },
      ],
    },
  ];
  python.materials = [
    {
      id: "m1",
      title: "Python 官方入门教程",
      source: "web",
      kind: "链接",
      description: "示例网络资料，阅读时可以对照条件语句与循环章节。",
      url: "https://docs.python.org/zh-cn/3/tutorial/",
    },
    {
      id: "m2",
      title: "课程学习指南",
      source: "system",
      kind: "文本",
      description: "先看示例，再解释执行过程，最后修改一个条件并验证结果。",
    },
    {
      id: "m3",
      title: "条件判断知识卡片",
      source: "generated",
      kind: "文本",
      description:
        "这是一份预置的 AI 生成资料展示样例，并非实时生成。\nif：条件成立时执行。\nelse：条件不成立时执行。\n比较时注意边界值。",
    },
  ];
  python.messages = [
    {
      id: "hello",
      role: "assistant",
      text: "你好！我们已经读过变量与基础类型，接下来是「条件判断与循环」。\n\n你可以先看一个例子，也可以直接做一道练习。这里的聊天与教学操作为本地演示，尚未连接模型。",
    },
  ];
  python.events = [
    {
      id: uid(),
      text: "选择「条件判断与循环」作为当前章节",
      category: "章节",
      time: now(),
    },
    {
      id: uid(),
      text: "已读「变量与基础数据类型」",
      category: "章节",
      time: now(),
    },
  ];
  const english = createCourse(
    "让英语表达更自然",
    "在日常工作中自然地进行英文交流",
    1,
  );
  english.id = "english";
  const design = createCourse(
    "从零认识视觉设计",
    "学会为自己的项目设计清晰的页面",
    2,
  );
  design.id = "design";
  return {
    version: 1,
    courses: [python, english, design],
    activeCourseId: "python",
    settings: {
      name: "学习者",
      permission: "assisted",
      compact: false,
      fontOffset: 3,
    },
  };
}
