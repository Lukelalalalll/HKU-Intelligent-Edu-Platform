/**
 * Copy for the admin surface.
 *
 * English is the canonical key shape: add every key to ``en`` first, then mirror
 * it in ``zh-Hans`` (source language) and ``yue`` (written Cantonese). TypeScript
 * enforces key parity at build time.
 */
const en = {
  title: "AI configuration centre",
  subtitle: "Manage providers centrally and match models to each business role.",
  providers: {
    title: "Provider management",
    add: "Add",
    namePlaceholder: "Name",
    apiKeyPlaceholder: "API Key (optional)",
    defaultModelPlaceholder: "Default model",
    saving: "Saving…",
    saveChanges: "Save changes",
    create: "Create provider",
    edit: "Edit",
    test: "Test",
    empty: "No providers yet. Create one first.",
    keyMasked: "Key {mask}",
    keyNotConfigured: "No key configured",
  },
  businesses: {
    title: "Business model matching",
    saving: "Saving…",
    save: "Save matching",
    notConfigured: "Not configured",
    modelPlaceholder: "Business model",
  },
};

export type AdminMessages = typeof en;

const zhHans: AdminMessages = {
  title: "AI 配置中心",
  subtitle: "统一管理 Provider，并为不同角色业务匹配模型。",
  providers: {
    title: "Provider 管理",
    add: "新增",
    namePlaceholder: "名称",
    apiKeyPlaceholder: "API Key（留空保持不变）",
    defaultModelPlaceholder: "默认模型",
    saving: "保存中…",
    saveChanges: "保存修改",
    create: "创建 Provider",
    edit: "编辑",
    test: "测试",
    empty: "暂无 Provider，请先创建。",
    keyMasked: "Key {mask}",
    keyNotConfigured: "未配置 Key",
  },
  businesses: {
    title: "业务模型匹配",
    saving: "保存中…",
    save: "保存匹配",
    notConfigured: "未配置",
    modelPlaceholder: "业务模型",
  },
};

const yue: AdminMessages = {
  title: "AI 設定中心",
  subtitle: "統一管理 Provider，並為唔同角色業務配對模型。",
  providers: {
    title: "Provider 管理",
    add: "新增",
    namePlaceholder: "名稱",
    apiKeyPlaceholder: "API Key（留空即保持不變）",
    defaultModelPlaceholder: "預設模型",
    saving: "儲存緊…",
    saveChanges: "儲存修改",
    create: "建立 Provider",
    edit: "編輯",
    test: "測試",
    empty: "暫時未有 Provider，請先建立。",
    keyMasked: "Key {mask}",
    keyNotConfigured: "未配置 Key",
  },
  businesses: {
    title: "業務模型配對",
    saving: "儲存緊…",
    save: "儲存配對",
    notConfigured: "未配置",
    modelPlaceholder: "業務模型",
  },
};

export const admin = { en, "zh-Hans": zhHans, yue };
