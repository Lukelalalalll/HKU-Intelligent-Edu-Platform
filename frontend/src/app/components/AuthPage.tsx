import React, { useCallback, useEffect, useRef } from "react";
import { Link, Navigate, useNavigate } from "react-router-dom";
import toast from "react-hot-toast";
import { api, getApiErrorMessage, setDevAccessToken } from "../../api";
import { useAuth } from "../../store";
import SiteHeader from "./SiteHeader";

const demoAccounts = [
  { label: "学生演示", username: "demo_student" },
  { label: "教师演示", username: "demo_teacher" },
  { label: "管理员演示", username: "demo_admin" },
];

export default function AuthPage({ mode }: { mode: "login" | "register" }) {
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
        navigate(data.user.role === "student" ? "/student" : data.user.role === "teacher" ? "/teacher" : "/admin");
        toast.success("注册成功");
      }
    } catch (error: unknown) {
      toast.error(getApiErrorMessage(error, "操作失败，请稍后重试"));
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
