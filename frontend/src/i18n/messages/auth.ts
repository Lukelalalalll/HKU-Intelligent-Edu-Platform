/**
 * Copy for the auth surface.
 *
 * English is the canonical key shape: add every key to ``en`` first, then mirror
 * it in ``zh-Hans`` (source language) and ``yue`` (written Cantonese). TypeScript
 * enforces key parity at build time.
 */
const en = {
  hero: {
    ariaLabel: "About the platform",
    welcome: "Welcome to",
    subtitle: "AI-powered learning that connects teachers, students and administrators.",
    continueHint: "Log in to continue your intelligent learning journey.",
  },
  login: {
    title: "Welcome back",
    subtitle: "Log in to your campus teaching space",
  },
  register: {
    title: "Join the HKU platform",
    subtitle: "Start your intelligent learning journey",
  },
  form: {
    name: "Name",
    email: "Email",
    username: "Username or email",
    password: "Password",
    confirmPassword: "Confirm password",
    showPassword: "Show password",
    hidePassword: "Hide password",
    showConfirmPassword: "Show confirm password",
    hideConfirmPassword: "Hide confirm password",
    secureLogin: "Secure login · HKU campus space",
    submitting: "Processing…",
    submitLogin: "Login",
    submitRegister: "Create account",
  },
  demo: {
    heading: "Local demo accounts",
    passwordHint: "All accounts use the password 123456",
    student: "Student demo",
    teacher: "Teacher demo",
    admin: "Admin demo",
  },
  footer: {
    noAccount: "Don’t have an account? ",
    haveAccount: "Already have an account? ",
    register: "Register",
    login: "Login",
  },
  errors: {
    passwordMismatch: "The two passwords do not match",
    actionFailed: "Something went wrong. Please try again later.",
    registerSuccess: "Account created",
  },
};

export type AuthMessages = typeof en;

const zhHans: AuthMessages = {
  hero: {
    ariaLabel: "平台介绍",
    welcome: "欢迎来到",
    subtitle: "以 AI 驱动学习体验，连接教师、学生与管理者。",
    continueHint: "登录后继续你的智能学习旅程。",
  },
  login: {
    title: "欢迎回来",
    subtitle: "登录你的校园教学空间",
  },
  register: {
    title: "加入 HKU 平台",
    subtitle: "开启你的智能学习旅程",
  },
  form: {
    name: "姓名",
    email: "邮箱",
    username: "用户名或邮箱",
    password: "密码",
    confirmPassword: "确认密码",
    showPassword: "显示密码",
    hidePassword: "隐藏密码",
    showConfirmPassword: "显示确认密码",
    hideConfirmPassword: "隐藏确认密码",
    secureLogin: "安全登录 · HKU 校园空间",
    submitting: "处理中…",
    submitLogin: "登录",
    submitRegister: "创建账户",
  },
  demo: {
    heading: "本地演示账户",
    passwordHint: "密码统一为 123456",
    student: "学生演示",
    teacher: "教师演示",
    admin: "管理员演示",
  },
  footer: {
    noAccount: "还没有账户？",
    haveAccount: "已有账户？",
    register: "注册",
    login: "登录",
  },
  errors: {
    passwordMismatch: "两次密码不一致",
    actionFailed: "操作失败，请稍后重试",
    registerSuccess: "注册成功",
  },
};

const yue: AuthMessages = {
  hero: {
    ariaLabel: "平台介紹",
    welcome: "歡迎嚟到",
    subtitle: "以 AI 驅動學習體驗，連結教師、學生同管理者。",
    continueHint: "登入之後繼續你嘅智能學習旅程。",
  },
  login: {
    title: "歡迎返嚟",
    subtitle: "登入你嘅校園教學空間",
  },
  register: {
    title: "加入 HKU 平台",
    subtitle: "開展你嘅智能學習旅程",
  },
  form: {
    name: "姓名",
    email: "電郵",
    username: "用戶名或電郵",
    password: "密碼",
    confirmPassword: "確認密碼",
    showPassword: "顯示密碼",
    hidePassword: "隱藏密碼",
    showConfirmPassword: "顯示確認密碼",
    hideConfirmPassword: "隱藏確認密碼",
    secureLogin: "安全登入 · HKU 校園空間",
    submitting: "處理緊…",
    submitLogin: "登入",
    submitRegister: "建立帳戶",
  },
  demo: {
    heading: "本地示範帳戶",
    passwordHint: "所有帳戶密碼都係 123456",
    student: "學生示範",
    teacher: "教師示範",
    admin: "管理員示範",
  },
  footer: {
    noAccount: "仲未有帳戶？",
    haveAccount: "已有帳戶？",
    register: "註冊",
    login: "登入",
  },
  errors: {
    passwordMismatch: "兩次密碼唔一致",
    actionFailed: "操作失敗，請遲啲再試",
    registerSuccess: "註冊成功",
  },
};

export const auth = { en, "zh-Hans": zhHans, yue };
