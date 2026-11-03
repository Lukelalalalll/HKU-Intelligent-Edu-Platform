import React, { useEffect, useRef, useState } from "react";
import toast from "react-hot-toast";
import { getApiErrorMessage, profileApi, User } from "../../../api";
import { useI18n, type TranslationKey } from "../../../i18n";
import { useAuth } from "../../../store";
import styles from "../styles/ProfileRoute.module.css";

const roleLabelKeys: Record<User["role"], TranslationKey> = { student: "common.header.roles.student", teacher: "common.header.roles.teacher", admin: "common.header.roles.admin" };

function Avatar({ user, cacheKey }: { user: User; cacheKey: number }) {
  const { t } = useI18n();
  if (user.avatar_url) return <img className={styles.avatar} src={`${user.avatar_url}?v=${cacheKey}`} alt={t("profile.avatarAlt", { name: user.name || user.username })} />;
  return <div className={styles.avatarFallback} aria-hidden="true">{(user.name || user.username).slice(0, 1).toUpperCase()}</div>;
}

/**
 * Profile page: account fields, avatar upload and password change.
 */
export default function ProfileRoute() {
  const authUser = useAuth((state) => state.user);
  const setUser = useAuth((state) => state.setUser);
  const refreshProfile = useAuth((state) => state.refreshProfile);
  const { t } = useI18n();
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
  if (!user) return <div className="loading-screen">{t("profile.loading")}</div>;

  const updateLocal = (next: User) => { setLocalUser(next); setUser(next); setName(next.name); setEmail(next.email); };

  const saveProfile = async (event: React.FormEvent) => {
    event.preventDefault();
    if (!name.trim()) { toast.error(t("profile.basic.nameRequired")); return; }
    setSaving(true);
    try { const { data } = await profileApi.update({ name: name.trim(), email: email.trim() }); updateLocal(data); toast.success(t("profile.basic.updated")); }
    catch (error: unknown) { toast.error(getApiErrorMessage(error, t("profile.basic.updateFailed"))); }
    finally { setSaving(false); }
  };

  const uploadAvatar = async (event: React.ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0];
    event.target.value = "";
    if (!file) return;
    setAvatarSaving(true);
    try { const { data } = await profileApi.uploadAvatar(file); updateLocal(data); setAvatarVersion((value) => value + 1); toast.success(t("profile.avatar.updated")); }
    catch (error: unknown) { toast.error(getApiErrorMessage(error, t("profile.avatar.uploadFailed"))); }
    finally { setAvatarSaving(false); }
  };

  const removeAvatar = async () => {
    setAvatarSaving(true);
    try { const { data } = await profileApi.removeAvatar(); updateLocal(data); setAvatarVersion((value) => value + 1); toast.success(t("profile.avatar.removed")); }
    catch (error: unknown) { toast.error(getApiErrorMessage(error, t("profile.avatar.removeFailed"))); }
    finally { setAvatarSaving(false); }
  };

  const savePassword = async (event: React.FormEvent) => {
    event.preventDefault();
    if (newPassword.length < 6) { toast.error(t("profile.security.minLength")); return; }
    if (newPassword !== confirmPassword) { toast.error(t("profile.security.mismatch")); return; }
    setPasswordSaving(true);
    try { await profileApi.changePassword({ current_password: currentPassword, new_password: newPassword }); setCurrentPassword(""); setNewPassword(""); setConfirmPassword(""); toast.success(t("profile.security.updated")); }
    catch (error: unknown) { toast.error(getApiErrorMessage(error, t("profile.security.updateFailed"))); }
    finally { setPasswordSaving(false); }
  };

  return <main className={styles.page}>
    <div className="page-heading"><div><p className="eyebrow">ACCOUNT SETTINGS</p><h1>{t("profile.heading")}</h1><p className="muted">{t("profile.subtitle")}</p></div></div>
    <div className={styles.grid}>
      <section className={styles.card}>
        <div className={styles.identity}><div className={styles.avatarWrap}><Avatar user={user} cacheKey={avatarVersion} /><span className={styles.onlineDot} /></div><div><h2>{user.name || user.username}</h2><p>{t(roleLabelKeys[user.role])} · @{user.username}</p><div className={styles.avatarActions}><button type="button" className="primary-action" onClick={() => fileRef.current?.click()} disabled={avatarSaving}>{avatarSaving ? t("profile.avatar.processing") : t("profile.avatar.change")}</button>{user.avatar_url && <button type="button" className="secondary-action" onClick={removeAvatar} disabled={avatarSaving}>{t("profile.avatar.remove")}</button>}<input ref={fileRef} type="file" accept="image/jpeg,image/png,image/webp" onChange={uploadAvatar} hidden /></div><small>{t("profile.avatar.hint")}</small></div></div>
        <form className={styles.form} onSubmit={saveProfile}><div className={styles.sectionHeading}><div><p className="eyebrow">BASIC INFORMATION</p><h2>{t("profile.basic.title")}</h2></div></div><label>{t("profile.basic.name")}<input value={name} onChange={(event) => setName(event.target.value)} maxLength={120} required /></label><label>{t("profile.basic.email")}<input value={email} onChange={(event) => setEmail(event.target.value)} type="email" required /></label><label>{t("profile.basic.username")}<input value={user.username} readOnly /></label><div className={styles.formFooter}><span>{t("profile.basic.managedHint")}</span><button className="primary-action" type="submit" disabled={saving}>{saving ? t("profile.basic.saving") : t("profile.basic.save")}</button></div></form>
      </section>
      <section className={styles.card}><form className={styles.form} onSubmit={savePassword}><div className={styles.sectionHeading}><div><p className="eyebrow">SECURITY</p><h2>{t("profile.security.title")}</h2></div><i className="fas fa-shield-halved" /></div><p className="muted">{t("profile.security.description")}</p><label>{t("profile.security.currentPassword")}<input value={currentPassword} onChange={(event) => setCurrentPassword(event.target.value)} type="password" autoComplete="current-password" required /></label><label>{t("profile.security.newPassword")}<input value={newPassword} onChange={(event) => setNewPassword(event.target.value)} type="password" autoComplete="new-password" minLength={6} required /></label><label>{t("profile.security.confirmPassword")}<input value={confirmPassword} onChange={(event) => setConfirmPassword(event.target.value)} type="password" autoComplete="new-password" minLength={6} required /></label><div className={styles.formFooter}><span>{t("profile.security.minLengthHint")}</span><button className="primary-action" type="submit" disabled={passwordSaving}>{passwordSaving ? t("profile.security.updating") : t("profile.security.submit")}</button></div></form></section>
    </div>
  </main>;
}
