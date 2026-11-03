/**
 * Copy for the profile surface.
 *
 * English is the canonical key shape: add every key to ``en`` first, then mirror
 * it in ``zh-Hans`` (source language) and ``yue`` (written Cantonese). TypeScript
 * enforces key parity at build time.
 */
const en = {
  loading: "Loading your profile…",
  heading: "Profile",
  subtitle: "Manage your account details and login security settings.",
  avatarAlt: "{name}’s avatar",
  avatar: {
    change: "Change avatar",
    remove: "Remove",
    processing: "Processing…",
    hint: "Supports JPG, PNG and WebP, up to 5MB",
    updated: "Avatar updated",
    uploadFailed: "Avatar upload failed. Check the format and size.",
    removed: "Avatar removed",
    removeFailed: "Could not remove the avatar. Please try again later.",
  },
  basic: {
    title: "Basic information",
    name: "Name",
    email: "Email",
    username: "Username",
    managedHint: "Your username and role are managed by the platform and cannot be changed.",
    save: "Save changes",
    saving: "Saving…",
    nameRequired: "Name cannot be empty",
    updated: "Profile updated",
    updateFailed: "Could not update your profile. Please try again later.",
  },
  security: {
    title: "Change password",
    description: "Changing your password requires your current password. Your current session stays signed in.",
    currentPassword: "Current password",
    newPassword: "New password",
    confirmPassword: "Confirm new password",
    minLengthHint: "At least 6 characters",
    submit: "Update password",
    updating: "Updating…",
    minLength: "The new password must be at least 6 characters",
    mismatch: "The new passwords do not match",
    updated: "Password updated",
    updateFailed: "Could not update the password. Please check your current password.",
  },
};

export type ProfileMessages = typeof en;

const zhHans: ProfileMessages = {
  loading: "正在加载个人资料…",
  heading: "个人资料",
  subtitle: "管理你的账户信息和登录安全设置。",
  avatarAlt: "{name} 的头像",
  avatar: {
    change: "更换头像",
    remove: "移除",
    processing: "处理中…",
    hint: "支持 JPG、PNG、WebP，最大 5MB",
    updated: "头像已更新",
    uploadFailed: "头像上传失败，请确认格式和大小",
    removed: "头像已移除",
    removeFailed: "头像移除失败，请稍后重试",
  },
  basic: {
    title: "基本信息",
    name: "姓名",
    email: "邮箱",
    username: "用户名",
    managedHint: "用户名和角色由平台管理，暂不可修改。",
    save: "保存修改",
    saving: "保存中…",
    nameRequired: "姓名不能为空",
    updated: "个人资料已更新",
    updateFailed: "资料更新失败，请稍后重试",
  },
  security: {
    title: "修改密码",
    description: "修改密码需要验证当前密码，当前登录会话不会中断。",
    currentPassword: "当前密码",
    newPassword: "新密码",
    confirmPassword: "确认新密码",
    minLengthHint: "至少 6 位字符",
    submit: "更新密码",
    updating: "更新中…",
    minLength: "新密码至少需要 6 位",
    mismatch: "两次新密码不一致",
    updated: "密码已更新",
    updateFailed: "密码更新失败，请检查当前密码",
  },
};

const yue: ProfileMessages = {
  loading: "正在載入個人資料…",
  heading: "個人資料",
  subtitle: "管理你嘅帳戶資料同登入安全設定。",
  avatarAlt: "{name} 嘅頭像",
  avatar: {
    change: "更換頭像",
    remove: "移除",
    processing: "處理緊…",
    hint: "支援 JPG、PNG、WebP，最大 5MB",
    updated: "頭像已更新",
    uploadFailed: "頭像上傳失敗，請確認格式同大細",
    removed: "頭像已移除",
    removeFailed: "頭像移除失敗，請遲啲再試",
  },
  basic: {
    title: "基本資料",
    name: "姓名",
    email: "電郵",
    username: "用戶名",
    managedHint: "用戶名同角色由平台管理，暫時唔可以改。",
    save: "儲存修改",
    saving: "儲存緊…",
    nameRequired: "姓名唔可以留空",
    updated: "個人資料已更新",
    updateFailed: "資料更新失敗，請遲啲再試",
  },
  security: {
    title: "修改密碼",
    description: "改密碼要先驗證目前密碼，而家嘅登入狀態唔會中斷。",
    currentPassword: "目前密碼",
    newPassword: "新密碼",
    confirmPassword: "確認新密碼",
    minLengthHint: "最少 6 個字元",
    submit: "更新密碼",
    updating: "更新緊…",
    minLength: "新密碼最少要 6 位",
    mismatch: "兩次新密碼唔一致",
    updated: "密碼已更新",
    updateFailed: "密碼更新失敗，請檢查目前密碼",
  },
};

export const profile = { en, "zh-Hans": zhHans, yue };
