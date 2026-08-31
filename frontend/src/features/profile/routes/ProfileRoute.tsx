import React, { useEffect, useRef, useState } from "react";
import toast from "react-hot-toast";
import { profileApi, User } from "../../../api";
import { useAuth } from "../../../store";
import styles from "../styles/ProfileRoute.module.css";

const roleLabels: Record<User["role"], string> = { student: "学生", teacher: "教师", admin: "管理员" };

function Avatar({ user, cacheKey }: { user: User; cacheKey: number }) {
  if (user.avatar_url) return <img className={styles.avatar} src={`${user.avatar_url}?v=${cacheKey}`} alt={`${user.name || user.username} 的头像`} />;
  return <div className={styles.avatarFallback} aria-hidden="true">{(user.name || user.username).slice(0, 1).toUpperCase()}</div>;
}

export default function ProfileRoute() {
  const authUser = useAuth((state) => state.user);
  const setUser = useAuth((state) => state.setUser);
  const refreshProfile = useAuth((state) => state.refreshProfile);
  const fileRef = useRef<HTMLInputElement>(null);
  const [user, setLocalUser] = useState<User | null>(authUser);
  const [name, setName] = useState(authUser?.name || "");
  const [email, setEmail] = useState(authUser?.email || "");
  const [currentPassword, setCurrentPassword] = useState("");
  const [newPassword, setNewPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [saving, setSaving] = useState(false);
  const [passwordSaving, setPasswordSaving] = useState(false);
  const [avatarSaving, setAvatarSaving] = useState(false);
  const [avatarVersion, setAvatarVersion] = useState(0);

  useEffect(() => {
    refreshProfile().then((next) => { setLocalUser(next); setName(next.name); setEmail(next.email); }).catch(() => undefined);
  }, [refreshProfile]);

  useEffect(() => { if (authUser) setLocalUser(authUser); }, [authUser]);
  if (!user) return <div className="loading-screen">正在加载个人资料…</div>;

  const updateLocal = (next: User) => { setLocalUser(next); setUser(next); setName(next.name); setEmail(next.email); };
  const errorMessage = (error: any, fallback: string) => error.response?.data?.detail || fallback;

  const saveProfile = async (event: React.FormEvent) => {
    event.preventDefault();
    if (!name.trim()) { toast.error("姓名不能为空"); return; }
    setSaving(true);
    try { const { data } = await profileApi.update({ name: name.trim(), email: email.trim() }); updateLocal(data); toast.success("个人资料已更新"); }
    catch (error: any) { toast.error(errorMessage(error, "资料更新失败，请稍后重试")); }
    finally { setSaving(false); }
  };

  const uploadAvatar = async (event: React.ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0];
    event.target.value = "";
    if (!file) return;
    setAvatarSaving(true);
    try { const { data } = await profileApi.uploadAvatar(file); updateLocal(data); setAvatarVersion((value) => value + 1); toast.success("头像已更新"); }
    catch (error: any) { toast.error(errorMessage(error, "头像上传失败，请确认格式和大小")); }
    finally { setAvatarSaving(false); }
  };

  const removeAvatar = async () => {
    setAvatarSaving(true);
    try { const { data } = await profileApi.removeAvatar(); updateLocal(data); setAvatarVersion((value) => value + 1); toast.success("头像已移除"); }
    catch (error: any) { toast.error(errorMessage(error, "头像移除失败，请稍后重试")); }
    finally { setAvatarSaving(false); }
  };

  const savePassword = async (event: React.FormEvent) => {
    event.preventDefault();
    if (newPassword.length < 6) { toast.error("新密码至少需要 6 位"); return; }
    if (newPassword !== confirmPassword) { toast.error("两次新密码不一致"); return; }
    setPasswordSaving(true);
    try { await profileApi.changePassword({ current_password: currentPassword, new_password: newPassword }); setCurrentPassword(""); setNewPassword(""); setConfirmPassword(""); toast.success("密码已更新"); }
    catch (error: any) { toast.error(errorMessage(error, "密码更新失败，请检查当前密码")); }
    finally { setPasswordSaving(false); }
  };

  return <main className={styles.page}>
    <div className="page-heading"><div><p className="eyebrow">ACCOUNT SETTINGS</p><h1>个人资料</h1><p className="muted">管理你的账户信息和登录安全设置。</p></div></div>
    <div className={styles.grid}>
      <section className={styles.card}>
        <div className={styles.identity}><div className={styles.avatarWrap}><Avatar user={user} cacheKey={avatarVersion} /><span className={styles.onlineDot} /></div><div><h2>{user.name || user.username}</h2><p>{roleLabels[user.role]} · @{user.username}</p><div className={styles.avatarActions}><button type="button" className="primary-action" onClick={() => fileRef.current?.click()} disabled={avatarSaving}>{avatarSaving ? "处理中…" : "更换头像"}</button>{user.avatar_url && <button type="button" className="secondary-action" onClick={removeAvatar} disabled={avatarSaving}>移除</button>}<input ref={fileRef} type="file" accept="image/jpeg,image/png,image/webp" onChange={uploadAvatar} hidden /></div><small>支持 JPG、PNG、WebP，最大 5MB</small></div></div>
        <form className={styles.form} onSubmit={saveProfile}><div className={styles.sectionHeading}><div><p className="eyebrow">BASIC INFORMATION</p><h2>基本信息</h2></div></div><label>姓名<input value={name} onChange={(event) => setName(event.target.value)} maxLength={120} required /></label><label>邮箱<input value={email} onChange={(event) => setEmail(event.target.value)} type="email" required /></label><label>用户名<input value={user.username} readOnly /></label><div className={styles.formFooter}><span>用户名和角色由平台管理，暂不可修改。</span><button className="primary-action" type="submit" disabled={saving}>{saving ? "保存中…" : "保存修改"}</button></div></form>
      </section>
      <section className={styles.card}><form className={styles.form} onSubmit={savePassword}><div className={styles.sectionHeading}><div><p className="eyebrow">SECURITY</p><h2>修改密码</h2></div><i className="fas fa-shield-halved" /></div><p className="muted">修改密码需要验证当前密码，当前登录会话不会中断。</p><label>当前密码<input value={currentPassword} onChange={(event) => setCurrentPassword(event.target.value)} type="password" autoComplete="current-password" required /></label><label>新密码<input value={newPassword} onChange={(event) => setNewPassword(event.target.value)} type="password" autoComplete="new-password" minLength={6} required /></label><label>确认新密码<input value={confirmPassword} onChange={(event) => setConfirmPassword(event.target.value)} type="password" autoComplete="new-password" minLength={6} required /></label><div className={styles.formFooter}><span>至少 6 位字符</span><button className="primary-action" type="submit" disabled={passwordSaving}>{passwordSaving ? "更新中…" : "更新密码"}</button></div></form></section>
    </div>
  </main>;
}
