/**
 * Copy for the dashboard surface.
 *
 * English is the canonical key shape: add every key to ``en`` first, then mirror
 * it in ``zh-Hans`` (source language) and ``yue`` (written Cantonese). TypeScript
 * enforces key parity at build time.
 */
const en = {
  greeting: "Hello, {name}",
  welcome: {
    subtitle: "This is your workspace overview.",
    title: "Your unified teaching workspace is ready",
    body: "Courses, assignments, files and AI conversations will roll out step by step in one role-aware workspace.",
  },
  dueUnset: "No due date",
  timetable: {
    previousWeek: "Previous week",
    nextWeek: "Next week",
    thisWeek: "This week",
    timeColumn: "Time",
    defaultTitle: "This week’s timetable",
    slotAria: "{course}, {start} to {end}, {room}",
  },
  today: {
    title: "Today’s classes",
    emptyTitle: "No classes today",
    emptyBody: "Enjoy some focused time.",
  },
  teacher: {
    subtitle: "Create impactful learning experiences for your students today.",
    error: "Unable to load teaching data right now. Please try again later.",
    scheduleTitle: "This week’s timetable",
    reviewTitle: "Assignments to grade",
    pendingLabel: "To grade",
    pendingCount: "{count} submission(s)",
    reviewEmptyTitle: "Nothing to grade",
    reviewEmptyBody: "All submissions have been processed.",
  },
  student: {
    subtitle: "Stay on top of every class and keep your study plan on track.",
    error: "Unable to load student data right now. Please try again later.",
    timetableTitle: "This week’s timetable",
    assignmentsTitle: "Assignment reminders",
    viewAssignment: "View assignment",
    assignmentsEmptyTitle: "No assignment reminders",
    assignmentsEmptyBody: "You have completed the assignments for your current courses.",
  },
  status: {
    notStarted: "Not started",
    submitted: "Submitted",
    graded: "Graded",
    overdue: "Overdue",
  },
  gradingPlaceholder: {
    title: "Grading workspace",
    description: "The grading interface for assignment {assignmentId} is being prepared.",
  },
};

export type DashboardMessages = typeof en;

const zhHans: DashboardMessages = {
  greeting: "你好，{name}",
  welcome: {
    subtitle: "这是你的工作空间概览。",
    title: "统一教学骨架已就绪",
    body: "课程、作业、文件和 AI 对话将在同一套角色感知的工作台中逐步展开。",
  },
  dueUnset: "未设置截止时间",
  timetable: {
    previousWeek: "上一周",
    nextWeek: "下一周",
    thisWeek: "本周",
    timeColumn: "时间",
    defaultTitle: "本周课程表",
    slotAria: "{course}，{start} 至 {end}，{room}",
  },
  today: {
    title: "今日课程",
    emptyTitle: "今天没有课程",
    emptyBody: "享受一段专注时间吧。",
  },
  teacher: {
    subtitle: "今天也为学生创造有影响力的学习体验。",
    error: "暂时无法加载教学数据，请稍后重试。",
    scheduleTitle: "本周课程表",
    reviewTitle: "待批改作业",
    pendingLabel: "待批改",
    pendingCount: "{count} 份",
    reviewEmptyTitle: "暂无待批改作业",
    reviewEmptyBody: "所有提交都已处理。",
  },
  student: {
    subtitle: "安排好每一节课，稳步完成你的学习计划。",
    error: "暂时无法加载学生数据，请稍后重试。",
    timetableTitle: "本周课表",
    assignmentsTitle: "作业提醒",
    viewAssignment: "查看作业",
    assignmentsEmptyTitle: "暂无作业提醒",
    assignmentsEmptyBody: "你已完成当前课程作业。",
  },
  status: {
    notStarted: "待完成",
    submitted: "已提交",
    graded: "已评分",
    overdue: "已逾期",
  },
  gradingPlaceholder: {
    title: "作业批改工作台",
    description: "作业 {assignmentId} 的批改界面正在准备中。",
  },
};

const yue: DashboardMessages = {
  greeting: "你好，{name}",
  welcome: {
    subtitle: "呢度係你嘅工作空間概覽。",
    title: "統一教學骨架已經準備好",
    body: "課程、作業、檔案同 AI 對話會喺同一套按角色區分嘅工作台入面逐步展開。",
  },
  dueUnset: "未設定截止時間",
  timetable: {
    previousWeek: "上一週",
    nextWeek: "下一週",
    thisWeek: "本週",
    timeColumn: "時間",
    defaultTitle: "本週課程表",
    slotAria: "{course}，{start} 至 {end}，{room}",
  },
  today: {
    title: "今日課程",
    emptyTitle: "今日冇課",
    emptyBody: "享受一段專注時間啦。",
  },
  teacher: {
    subtitle: "今日都為學生創造有影響力嘅學習體驗。",
    error: "暫時載入唔到教學資料，請遲啲再試。",
    scheduleTitle: "本週課程表",
    reviewTitle: "等批改嘅作業",
    pendingLabel: "等批改",
    pendingCount: "{count} 份",
    reviewEmptyTitle: "暫時冇作業等批改",
    reviewEmptyBody: "所有提交都已處理好。",
  },
  student: {
    subtitle: "安排好每一節課，穩步完成你嘅學習計劃。",
    error: "暫時載入唔到學生資料，請遲啲再試。",
    timetableTitle: "本週課表",
    assignmentsTitle: "作業提醒",
    viewAssignment: "睇作業",
    assignmentsEmptyTitle: "暫時冇作業提醒",
    assignmentsEmptyBody: "你已經完成咗目前課程嘅作業。",
  },
  status: {
    notStarted: "未開始",
    submitted: "已提交",
    graded: "已評分",
    overdue: "已逾期",
  },
  gradingPlaceholder: {
    title: "作業批改工作台",
    description: "作業 {assignmentId} 嘅批改介面正在準備緊。",
  },
};

export const dashboard = { en, "zh-Hans": zhHans, yue };
