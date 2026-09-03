import React, { useCallback, useEffect, useRef } from "react";
import { Link, Navigate, NavLink, Outlet, Route, Routes, useLocation, useNavigate, useParams } from "react-router-dom";
import toast from "react-hot-toast";
import { AgentConversation, AgentMessage, api, Assignment, Course, Role, setDevAccessToken, TeacherDashboardData } from "./api";
import { useAuth } from "./store";
import logoImg from "./assets/hku_logo.png";
import PptCoursewareAgent from "./ppt/CoursewareAgent";
import CoursesRoute from "./features/courses/routes/CoursesRoute";
import CourseDetailRoute from "./features/courses/routes/CourseDetailRoute";
import LiveClassRoute from "./features/courses/routes/LiveClassRoute";
import ProfileRoute from "./features/profile/routes/ProfileRoute";
import WorkspaceSidebar, { readSidebarCollapsed, SidebarItem, writeSidebarCollapsed } from "./shared/components/WorkspaceSidebar";
import Breadcrumbs from "./shared/components/Breadcrumbs";

const demoAccounts = [
  { label: "学生演示", username: "demo_student" },
  { label: "教师演示", username: "demo_teacher" },
  { label: "管理员演示", username: "demo_admin" },
];

function SiteHeader() {
  const { user, logout } = useAuth();
  const navigate = useNavigate();

  const handleLogout = async () => {
    await logout();
    navigate("/login");
  };

  return (
    <header className="site-header">
      <div className="site-header-inner">
        <div className="site-header-leading">
          <Link className="site-logo" to={user ? (user.role === "teacher" ? "/teacher" : "/") : "/login"} aria-label="HKU Intelligent Education Platform">
            <img src={logoImg} alt="The University of Hong Kong" />
          </Link>
          {user && <Breadcrumbs />}
        </div>

        <nav className="site-nav" aria-label="主导航">
          {user ? (
            <div className="user-profile">
              <span className="role-pill">{user.role}</span>
              {user.avatar_url ? <img className="avatar avatar-image" src={user.avatar_url} alt="" /> : <span className="avatar" aria-hidden="true">{(user.name || user.username).slice(0, 1).toUpperCase()}</span>}
              <span className="user-name">{user.name || user.username}</span>
              <button className="nav-logout" onClick={handleLogout} type="button">
                <i className="fas fa-sign-out-alt" aria-hidden="true" />
                退出
              </button>
            </div>
          ) : (
            <>
              <Link className="nav-login" to="/login">
                <i className="fas fa-sign-in-alt" aria-hidden="true" />
                登录
              </Link>
              <Link className="nav-register" to="/register">
                <i className="fas fa-user-plus" aria-hidden="true" />
                注册
              </Link>
            </>
          )}
        </nav>
      </div>
    </header>
  );
}

function AuthPage({ mode }: { mode: "login" | "register" }) {
  const navigate = useNavigate();
  const { user, login } = useAuth();
  const cardRef = useRef<HTMLElement>(null);
  const sheenRef = useRef<HTMLDivElement>(null);
  const rafRef = useRef<number | null>(null);

  const [username, setUsername] = React.useState("");
  const [email, setEmail] = React.useState("");
  const [name, setName] = React.useState("");
  const [password, setPassword] = React.useState("");
  const [confirm, setConfirm] = React.useState("");
  const [showPassword, setShowPassword] = React.useState(false);
  const [showConfirm, setShowConfirm] = React.useState(false);
  const [loading, setLoading] = React.useState(false);
  const [allowPointerMotion, setAllowPointerMotion] = React.useState(false);

  useEffect(() => {
    if (typeof window === "undefined" || typeof window.matchMedia !== "function") return undefined;

    const pointerQuery = window.matchMedia("(pointer: fine)");
    const reducedMotionQuery = window.matchMedia("(prefers-reduced-motion: reduce)");
    const sync = () => setAllowPointerMotion(pointerQuery.matches && !reducedMotionQuery.matches);
    sync();
    pointerQuery.addEventListener("change", sync);
    reducedMotionQuery.addEventListener("change", sync);
    return () => {
      pointerQuery.removeEventListener("change", sync);
      reducedMotionQuery.removeEventListener("change", sync);
    };
  }, []);

  const resetCardPose = useCallback(() => {
    if (rafRef.current !== null) {
      cancelAnimationFrame(rafRef.current);
      rafRef.current = null;
    }
    if (!cardRef.current || !sheenRef.current) return;
    cardRef.current.style.transform = "translate3d(0, 0, 0)";
    cardRef.current.style.willChange = "auto";
    sheenRef.current.style.opacity = "0";
    sheenRef.current.style.willChange = "auto";
  }, []);

  useEffect(() => () => resetCardPose(), [resetCardPose]);

  const handleCardMouseMove = useCallback(
    (event: React.MouseEvent<HTMLElement>) => {
      if (!allowPointerMotion || !cardRef.current || !sheenRef.current || rafRef.current !== null) return;
      const { clientX, clientY } = event;
      rafRef.current = requestAnimationFrame(() => {
        rafRef.current = null;
        if (!cardRef.current || !sheenRef.current) return;
        const rect = cardRef.current.getBoundingClientRect();
        const offsetX = clientX - rect.left;
        const offsetY = clientY - rect.top;
        const rotateX = ((offsetY / rect.height) - 0.5) * -7;
        const rotateY = ((offsetX / rect.width) - 0.5) * 7;
        cardRef.current.style.transform = `perspective(1000px) rotateX(${rotateX}deg) rotateY(${rotateY}deg) translate3d(0, -2px, 0)`;
        sheenRef.current.style.background = `radial-gradient(circle at ${offsetX}px ${offsetY}px, rgba(255,255,255,0.24), transparent 58%)`;
        sheenRef.current.style.opacity = "1";
      });
    },
    [allowPointerMotion],
  );

  const handleInputChange = (setter: React.Dispatch<React.SetStateAction<string>>) => (
    event: React.ChangeEvent<HTMLInputElement>,
  ) => setter(event.target.value);

  if (user) return <Navigate to="/" replace />;

  const submit = async (event: React.FormEvent) => {
    event.preventDefault();
    if (mode === "register" && password !== confirm) {
      toast.error("两次密码不一致");
      return;
    }

    setLoading(true);
    try {
      if (mode === "login") {
        const next = await login(username, password);
        navigate(next.role === "student" ? "/student" : next.role === "teacher" ? "/teacher" : "/admin");
      } else {
        const { data } = await api.post("/auth/register", { username, email, password, name });
        setDevAccessToken(data.access_token || null);
        useAuth.getState().setUser(data.user);
        navigate("/");
        toast.success("注册成功");
      }
    } catch (error: any) {
      toast.error(error.response?.data?.detail || "操作失败，请稍后重试");
    } finally {
      setLoading(false);
    }
  };

  const fillDemo = (account: (typeof demoAccounts)[number]) => {
    setUsername(account.username);
    setPassword("123456");
  };

  const isLogin = mode === "login";
  return (
    <>
      <SiteHeader />
      <main className={`auth-page ${isLogin ? "auth-page-login" : "auth-page-register"}`}>
        <div className="auth-orb auth-orb-primary" aria-hidden="true" />
        <div className="auth-orb auth-orb-secondary" aria-hidden="true" />

        {isLogin && (
          <section className="auth-hero" aria-label="平台介绍">
            <p className="eyebrow">HKU · INTELLIGENT EDU</p>
            <h1>
              <span className="hero-line">欢迎来到</span>
              <span className="hero-line hero-line-glow">HKU Intelligent</span>
              <span className="hero-line">Education Platform</span>
            </h1>
            <p className="auth-hero-subtitle">
              以 AI 驱动学习体验，连接教师、学生与管理者。
              <br />登录后继续你的智能学习旅程。
            </p>
          </section>
        )}

        <section className="auth-container">
          <article
            className="auth-card"
            ref={cardRef}
            onMouseMove={handleCardMouseMove}
            onMouseLeave={() => {
              if (cardRef.current) cardRef.current.style.transition = "transform 220ms cubic-bezier(0.22, 1, 0.36, 1)";
              resetCardPose();
            }}
            onMouseEnter={() => {
              if (allowPointerMotion && cardRef.current) {
                cardRef.current.style.transition = "transform 120ms ease-out";
                cardRef.current.style.willChange = "transform";
              }
            }}
          >
            <div className="auth-card-sheen" ref={sheenRef} aria-hidden="true" />
            <div className="auth-header">
              <div className="auth-header-icon" aria-hidden="true">
                <i className={`fas ${isLogin ? "fa-user-circle" : "fa-user-plus"}`} />
              </div>
              <h2>{isLogin ? "欢迎回来" : "加入 HKU 平台"}</h2>
              <p>{isLogin ? "登录你的校园教学空间" : "开启你的智能学习旅程"}</p>
            </div>

            <form className="auth-form" onSubmit={submit}>
              {!isLogin && (
                <div className="auth-input-group">
                  <div className="auth-input-icon"><i className="fas fa-id-card" aria-hidden="true" /></div>
                  <input id="name" type="text" placeholder=" " value={name} onChange={handleInputChange(setName)} />
                  <label htmlFor="name">姓名</label>
                </div>
              )}

              {!isLogin && (
                <div className="auth-input-group">
                  <div className="auth-input-icon"><i className="fas fa-envelope" aria-hidden="true" /></div>
                  <input id="email" type="email" required placeholder=" " value={email} onChange={handleInputChange(setEmail)} />
                  <label htmlFor="email">邮箱</label>
                </div>
              )}

              <div className="auth-input-group">
                <div className="auth-input-icon"><i className="fas fa-user" aria-hidden="true" /></div>
                <input id="username" type="text" required placeholder=" " autoComplete="username" value={username} onChange={handleInputChange(setUsername)} />
                <label htmlFor="username">用户名或邮箱</label>
              </div>

              <div className="auth-input-group">
                <div className="auth-input-icon"><i className="fas fa-lock" aria-hidden="true" /></div>
                <input id="password" type={showPassword ? "text" : "password"} required placeholder=" " autoComplete={isLogin ? "current-password" : "new-password"} value={password} onChange={handleInputChange(setPassword)} />
                <button className="toggle-password" type="button" onClick={() => setShowPassword((value) => !value)} aria-label={showPassword ? "隐藏密码" : "显示密码"}>
                  <i className={`fas ${showPassword ? "fa-eye-slash" : "fa-eye"}`} aria-hidden="true" />
                </button>
                <label htmlFor="password">密码</label>
              </div>

              {!isLogin && (
                <div className="auth-input-group">
                  <div className="auth-input-icon"><i className="fas fa-shield-alt" aria-hidden="true" /></div>
                  <input id="confirm-password" type={showConfirm ? "text" : "password"} required placeholder=" " autoComplete="new-password" value={confirm} onChange={handleInputChange(setConfirm)} />
                  <button className="toggle-password" type="button" onClick={() => setShowConfirm((value) => !value)} aria-label={showConfirm ? "隐藏确认密码" : "显示确认密码"}>
                    <i className={`fas ${showConfirm ? "fa-eye-slash" : "fa-eye"}`} aria-hidden="true" />
                  </button>
                  <label htmlFor="confirm-password">确认密码</label>
                </div>
              )}

              {isLogin && <div className="form-options"><span>安全登录 · HKU 校园空间</span></div>}

              <button className={`auth-submit ${loading ? "is-loading" : ""}`} disabled={loading} type="submit">
                {loading ? <><i className="fas fa-circle-notch fa-spin" aria-hidden="true" />处理中…</> : <><span>{isLogin ? "登录" : "创建账户"}</span><i className="fas fa-arrow-right" aria-hidden="true" /></>}
              </button>
            </form>

            {isLogin && import.meta.env.DEV && (
              <div className="demo-box">
                <strong>本地演示账户</strong>
                <div className="demo-buttons">
                  {demoAccounts.map((account) => <button key={account.username} onClick={() => fillDemo(account)} type="button">{account.label}</button>)}
                </div>
                <small>密码统一为 123456</small>
              </div>
            )}

            <p className="auth-footer">
              {isLogin ? "还没有账户？" : "已有账户？"}
              <Link to={isLogin ? "/register" : "/login"}>{isLogin ? "注册" : "登录"}</Link>
            </p>
          </article>
        </section>
      </main>
    </>
  );
}

function Shell() {
  const { user } = useAuth();
  const [sidebarCollapsed, setSidebarCollapsed] = React.useState(readSidebarCollapsed);
  const toggleSidebar = () => setSidebarCollapsed((collapsed) => {
    const next = !collapsed;
    writeSidebarCollapsed(next);
    return next;
  });
  const links: SidebarItem[] = [
    { to: user?.role === "teacher" ? "/teacher" : "/", label: "总览", roles: ["teacher", "student", "admin"], icon: "overview" },
    { to: "/courses", label: user?.role === "teacher" ? "我的课程" : "课程", roles: ["teacher", "student", "admin"], icon: "courses" },
    { to: "/assignments", label: "作业", roles: ["teacher", "student"], icon: "assignments" },
    { to: "/teacher/courseware-agent", label: "课件 Agent", roles: ["teacher"], icon: "courseware" },
    { to: "/admin", label: "管理后台", roles: ["admin"], icon: "admin" },
  ];

  return (
    <div className={`app-shell ${sidebarCollapsed ? "sidebar-collapsed" : ""}`}>
      <SiteHeader />
      <WorkspaceSidebar userRole={user?.role} links={links} collapsed={sidebarCollapsed} onToggle={toggleSidebar} />
      <div className="content"><Outlet /></div>
    </div>
  );
}

function Protected() {
  const { user, loading } = useAuth();
  const location = useLocation();
  if (loading) return <div className="loading-screen">正在恢复登录状态…</div>;
  return user ? <Shell /> : <Navigate to={`/login?next=${encodeURIComponent(location.pathname)}`} replace />;
}

const weekdays = ["周一", "周二", "周三", "周四", "周五", "周六", "周日"];
const formatDue = (value: string | null) => value ? new Intl.DateTimeFormat("zh-CN", { month: "short", day: "numeric", hour: "2-digit", minute: "2-digit" }).format(new Date(value)) : "未设置截止时间";
const SCHEDULE_START_MINUTES = 8 * 60;
const SCHEDULE_DAYTIME_END = 20 * 60;
const SCHEDULE_END_MINUTES = 24 * 60;
const SCHEDULE_DAYTIME_PIXELS_PER_MINUTE = 1;
const SCHEDULE_EVENING_PIXELS_PER_MINUTE = 0.5;
const SCHEDULE_AXIS_HEIGHT = (SCHEDULE_DAYTIME_END - SCHEDULE_START_MINUTES) * SCHEDULE_DAYTIME_PIXELS_PER_MINUTE
  + (SCHEDULE_END_MINUTES - SCHEDULE_DAYTIME_END) * SCHEDULE_EVENING_PIXELS_PER_MINUTE;
const scheduleTicks = [8, 10, 12, 14, 16, 18, 20, 22, 24].map((hour) => hour * 60);
const minutesOf = (value: string) => {
  const [hours = 0, minutes = 0] = value.split(":").map(Number);
  const total = Number.isFinite(hours) && Number.isFinite(minutes) ? hours * 60 + minutes : 0;
  return Math.max(0, Math.min(SCHEDULE_END_MINUTES, total));
};
const scheduleAxisOffset = (minutes: number) => {
  const safeMinutes = Math.max(SCHEDULE_START_MINUTES, Math.min(SCHEDULE_END_MINUTES, minutes));
  if (safeMinutes <= SCHEDULE_DAYTIME_END) return (safeMinutes - SCHEDULE_START_MINUTES) * SCHEDULE_DAYTIME_PIXELS_PER_MINUTE;
  return (SCHEDULE_DAYTIME_END - SCHEDULE_START_MINUTES) * SCHEDULE_DAYTIME_PIXELS_PER_MINUTE
    + (safeMinutes - SCHEDULE_DAYTIME_END) * SCHEDULE_EVENING_PIXELS_PER_MINUTE;
};

function Dashboard() {
  const { user } = useAuth();
  const navigate = useNavigate();
  const [data, setData] = React.useState<TeacherDashboardData | null>(null);
  const [weekOffset, setWeekOffset] = React.useState(0);
  const [error, setError] = React.useState(false);
  useEffect(() => { if (user?.role === "teacher") api.get<TeacherDashboardData>("/teacher/dashboard").then((r) => setData(r.data)).catch(() => setError(true)); }, [user]);
  if (user?.role !== "teacher") return <div><div className="page-heading"><div><p className="eyebrow">{user?.role?.toUpperCase()} WORKSPACE</p><h1>你好，{user?.name}</h1><p className="muted">这是你的工作空间概览。</p></div></div><div className="welcome-panel"><h2>统一教学骨架已就绪</h2><p>课程、作业、文件和 AI 对话将在同一套角色感知的工作台中逐步展开。</p></div></div>;
  const base = new Date(); base.setDate(base.getDate() - ((base.getDay() + 6) % 7) + weekOffset * 7); base.setHours(0, 0, 0, 0);
  const weekLabel = `${base.toLocaleDateString("zh-CN", { month: "short", day: "numeric" })} – ${new Date(base.getTime() + 6 * 86400000).toLocaleDateString("zh-CN", { month: "short", day: "numeric" })}`;
  const schedule = data?.schedule ?? [];
  return <div className="teacher-dashboard">
    <div className="page-heading teacher-heading"><div><p className="eyebrow"><i className="fas fa-sparkles" /> TEACHER WORKSPACE</p><h1>你好，{user.name || user.username}</h1><p className="muted">今天也为学生创造有影响力的学习体验。</p></div><div className="date-chip"><i className="fas fa-calendar-day" /> {new Date().toLocaleDateString("zh-CN", { weekday: "long", month: "long", day: "numeric" })}</div></div>
    {error ? <div className="error-panel">暂时无法加载教学数据，请稍后重试。</div> : <div className="dashboard-grid">
      <section className="schedule-panel panel-card"><div className="panel-title"><div><p className="eyebrow">TIME SCHEDULE</p><h2>本周课程表</h2></div><div className="week-controls"><button onClick={() => setWeekOffset((v) => v - 1)} aria-label="上一周"><i className="fas fa-chevron-left" /></button><span>{weekLabel}</span><button onClick={() => setWeekOffset((v) => v + 1)} aria-label="下一周"><i className="fas fa-chevron-right" /></button><button className="today-button" onClick={() => setWeekOffset(0)}>本周</button></div></div><div className="timetable" style={{ "--schedule-axis-height": `${SCHEDULE_AXIS_HEIGHT}px` } as React.CSSProperties}><div className="time-column"><span className="time-title">时间</span>{scheduleTicks.map((minutes) => <span className={`time-tick ${minutes === SCHEDULE_START_MINUTES ? "time-tick-start" : ""}`} style={{ top: 48 + scheduleAxisOffset(minutes) }} key={minutes}>{minutes === SCHEDULE_END_MINUTES ? "24:00" : `${String(Math.floor(minutes / 60)).padStart(2, "0")}:00`}</span>)}</div>{weekdays.map((day, i) => <div className="day-column" key={day}><header><span>{day}</span><strong>{new Date(base.getTime() + i * 86400000).getDate()}</strong></header><div className="day-track">{scheduleTicks.slice(1).map((minutes) => <span className="schedule-grid-line" style={{ top: scheduleAxisOffset(minutes) }} aria-hidden="true" key={minutes} />)}{schedule.filter((s) => s.weekday === i + 1).map((item) => { const start = minutesOf(item.start_time); const end = Math.max(start, minutesOf(item.end_time)); const top = scheduleAxisOffset(start); const height = Math.max(52, scheduleAxisOffset(end) - top - 7); const compact = end - start <= 90 || height < 104; return <button className={`schedule-block ${compact ? "schedule-block-compact" : ""}`} style={{ top, height }} key={`${item.course_id}-${item.start_time}-${item.weekday}`} onClick={() => navigate(`/courses/${item.course_id}`)} aria-label={`${item.course_name}，${item.start_time} 至 ${item.end_time}，${item.room || "待定教室"}`}><strong>{item.course_code}</strong>{compact ? <small className="schedule-compact-details">{item.start_time} – {item.end_time} · {item.room || "待定教室"}</small> : <><span>{item.course_name}</span><small>{item.start_time} – {item.end_time}</small><small><i className="fas fa-location-dot" /> {item.room || "待定教室"}</small></>}</button>; })}{!schedule.some((s) => s.weekday === i + 1) && <span className="day-empty">—</span>}</div></div>)}</div></section>
      <aside className="dashboard-side"><section className="panel-card side-panel"><div className="panel-title"><div><p className="eyebrow">TODAY</p><h2>今日课程</h2></div><i className="fas fa-clock panel-icon" /></div>{schedule.filter((s) => s.weekday === ((new Date().getDay() + 6) % 7) + 1).map((item) => <button className="today-course" key={`${item.course_id}-${item.start_time}`} onClick={() => navigate(`/courses/${item.course_id}`)}><span className="time-label">{item.start_time}</span><div><strong>{item.course_name}</strong><span>{item.course_code} · {item.room || "待定教室"}</span></div><i className="fas fa-arrow-right" /></button>)}{!schedule.some((s) => s.weekday === ((new Date().getDay() + 6) % 7) + 1) && <div className="empty-state"><i className="fas fa-mug-hot" /><strong>今天没有课程</strong><span>享受一段专注时间吧。</span></div>}</section><section className="panel-card side-panel"><div className="panel-title"><div><p className="eyebrow">REVIEW QUEUE</p><h2>待批改作业</h2></div><i className="fas fa-file-pen panel-icon" /></div>{(data?.pending_assignments ?? []).map((item) => <button className="review-card" key={item.id} onClick={() => navigate(`/assignments/${item.id}/grading`)}><span className="review-due">{formatDue(item.due_at)}</span><strong>{item.title}</strong><span>{item.course_name}</span><footer><small>待批改</small><b>{item.pending_count} 份</b></footer></button>)}{!data?.pending_assignments?.length && <div className="empty-state"><i className="fas fa-check-circle" /><strong>暂无待批改作业</strong><span>所有提交都已处理。</span></div>}</section></aside>
    </div>}
  </div>;
}

function GradingPlaceholder() {
  const { assignmentId } = useParams();
  const { user } = useAuth();
  if (user?.role !== "teacher") return <Navigate to="/assignments" replace />;
  return <div className="placeholder-page"><i className="fas fa-file-pen placeholder-icon" /><p className="eyebrow">GRADING WORKSPACE</p><h1>作业批改工作台</h1><p>作业 {assignmentId} 的批改界面正在准备中。</p></div>;
}

function CoursewareAgent() {
  const [conversations, setConversations] = React.useState<AgentConversation[]>([]); const [activeId, setActiveId] = React.useState<string | null>(null); const [messages, setMessages] = React.useState<AgentMessage[]>([]); const [draft, setDraft] = React.useState(""); const [streaming, setStreaming] = React.useState(false); const [deleteId, setDeleteId] = React.useState<string | null>(null);
  const loadConversations = React.useCallback(() => api.get<AgentConversation[]>("/agent/conversations").then((r) => { setConversations(r.data); if (!activeId && r.data[0]) setActiveId(r.data[0].id); }).catch(() => undefined), [activeId]);
  useEffect(() => { loadConversations(); }, [loadConversations]);
  useEffect(() => { if (activeId) api.get<AgentConversation>(`/agent/conversations/${activeId}`).then((r) => setMessages(r.data.messages || [])).catch(() => setMessages([])); }, [activeId]);
  const createConversation = async () => { const { data } = await api.post<AgentConversation>("/agent/conversations", { title: "新对话" }); setConversations((c) => [data, ...c]); setActiveId(data.id); setMessages([]); };
  const send = async (event: React.FormEvent) => { event.preventDefault(); const text = draft.trim(); if (!text || streaming) return; let id = activeId; setStreaming(true); try { if (!id) { const { data } = await api.post<AgentConversation>("/agent/conversations", { title: text.slice(0, 24) }); setConversations((c) => [data, ...c]); id = data.id; setActiveId(id); } setDraft(""); const userMessage = await api.post<AgentMessage>(`/agent/conversations/${id}/messages`, { role: "user", content: text }); setMessages((m) => [...m, userMessage.data]); const reply = `收到你的问题：“${text}”。这是课件 Agent 的演示回复：我可以帮助你梳理课程重点、设计课堂活动，并根据教学目标组织课件结构。真实课件生成能力将在后续版本接入。`; const tempId = `stream-${Date.now()}`; setMessages((m) => [...m, { id: tempId, conversation_id: id!, role: "assistant", content: "", citations: [], model: "demo", created_at: new Date().toISOString() }]); for (let i = 1; i <= reply.length; i += 1) { await new Promise((resolve) => window.setTimeout(resolve, 18)); setMessages((m) => m.map((item) => item.id === tempId ? { ...item, content: reply.slice(0, i) } : item)); } const saved = await api.post<AgentMessage>(`/agent/conversations/${id}/messages`, { role: "assistant", content: reply, model: "demo" }); setMessages((m) => m.map((item) => item.id === tempId ? saved.data : item)); } catch { toast.error("消息发送失败，请稍后重试"); } finally { setStreaming(false); } };
  const remove = async () => { if (!deleteId) return; await api.delete(`/agent/conversations/${deleteId}`); const next = conversations.filter((c) => c.id !== deleteId); setConversations(next); setDeleteId(null); setActiveId(next[0]?.id || null); setMessages([]); };
  return <div className="agent-page"><div className="agent-history"><div className="agent-history-head"><div><p className="eyebrow">COURSEWARE</p><h2>课件 Agent</h2></div><button className="icon-button" onClick={createConversation} aria-label="新建会话"><i className="fas fa-plus" /></button></div><button className="new-conversation" onClick={createConversation}><i className="fas fa-pen-to-square" /> 新建对话</button><div className="conversation-list">{conversations.map((c) => <div className={`conversation-row ${c.id === activeId ? "active" : ""}`} key={c.id}><button onClick={() => setActiveId(c.id)}><strong>{c.title}</strong><small>{new Date(c.created_at).toLocaleDateString("zh-CN")}</small></button><button className="delete-conversation" onClick={() => setDeleteId(c.id)} aria-label="删除会话"><i className="fas fa-trash" /></button></div>)}{!conversations.length && <span className="history-empty">还没有对话记录</span>}</div></div><section className="agent-chat"><header className="agent-chat-head"><div><p className="eyebrow">INTELLIGENT TEACHING</p><h1>和你的课件助手聊聊</h1></div><span className="agent-status"><i className="fas fa-circle" /> Demo 模式</span></header><div className="agent-messages">{!messages.length ? <div className="agent-empty"><i className="fas fa-robot" /><h2>从一个教学想法开始</h2><p>试试询问课程结构、课堂活动或课件大纲。</p><div className="suggestions">{["帮我设计一节 50 分钟的课堂", "总结这门课的核心知识点", "给出一个小组讨论活动"].map((s) => <button key={s} onClick={() => setDraft(s)}>{s}</button>)}</div></div> : messages.map((m) => <div className={`agent-message ${m.role}`} key={m.id}><span className="message-avatar"><i className={`fas ${m.role === "assistant" ? "fa-robot" : "fa-user"}`} /></span><div><small>{m.role === "assistant" ? "课件 Agent" : "你"}</small><p>{m.content}{streaming && m.id.startsWith("stream-") && <span className="cursor" />}</p></div></div>)}</div><form className="agent-composer" onSubmit={send}><textarea value={draft} onChange={(e) => setDraft(e.target.value)} placeholder="输入你的教学问题…" rows={1} disabled={streaming} /><button type="submit" disabled={!draft.trim() || streaming}><i className="fas fa-arrow-up" /></button></form></section>{deleteId && <div className="modal-backdrop"><div className="confirm-modal"><h3>删除这段对话？</h3><p>删除后将无法恢复对话记录。</p><div><button onClick={() => setDeleteId(null)}>取消</button><button className="danger" onClick={remove}>确认删除</button></div></div></div>}</div>;
}

function Assignments() { return <div><div className="page-heading"><div><p className="eyebrow">COURSEWORK</p><h1>作业</h1><p className="muted">Phase 1 作业列表与提交入口。</p></div></div><div className="welcome-panel"><h2>作业工作台</h2><p>教师发布、学生提交、评分反馈的数据链路已在后端准备完成。</p></div></div>; }
function Admin() { return <div><div className="page-heading"><div><p className="eyebrow">ADMINISTRATION</p><h1>管理后台</h1><p className="muted">管理账户、课程和审计能力将在这里扩展。</p></div></div><div className="welcome-panel"><h2>管理员空间</h2><p>当前登录账户具备 admin 权限，后续可接入用户、课程与系统配置管理。</p></div></div>; }

export default function App() {
  const bootstrap = useAuth((state) => state.bootstrap);
  useEffect(() => { bootstrap(); }, [bootstrap]);
  return <Routes><Route path="/login" element={<AuthPage mode="login" />} /><Route path="/register" element={<AuthPage mode="register" />} /><Route element={<Protected />}><Route path="/" element={<Dashboard />} /><Route path="/student" element={<Dashboard />} /><Route path="/teacher" element={<Dashboard />} /><Route path="/teacher/courseware-agent" element={<PptCoursewareAgent />} /><Route path="/teacher/courseware-agent/:projectId" element={<PptCoursewareAgent />} /><Route path="/admin" element={<Admin />} /><Route path="/courses" element={<CoursesRoute />} /><Route path="/courses/:courseId" element={<CourseDetailRoute />} /><Route path="/courses/:courseId/live" element={<LiveClassRoute />} /><Route path="/assignments" element={<Assignments />} /><Route path="/assignments/:assignmentId/grading" element={<GradingPlaceholder />} /><Route path="/profile" element={<ProfileRoute />} /></Route><Route path="*" element={<Navigate to="/" replace />} /></Routes>;
}
