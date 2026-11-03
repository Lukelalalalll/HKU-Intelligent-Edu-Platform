/**
 * Network/error copy that is also reachable from non-React modules such as the
 * axios client. English is the canonical key shape; keep translations in sync.
 */
const en = {
  requestFailed: "Request failed. Please try again.",
  requestFailedShort: "Request failed",
  requestFailedWithStatus: "Request failed ({status})",
  eventStreamMissing: "The server did not return an event stream",
  requirementInterviewFailed: "Requirement interview failed",
  agentExecutionFailed: "Agent execution failed",
};

export type ErrorsMessages = typeof en;

const zhHans: ErrorsMessages = {
  requestFailed: "请求失败，请稍后重试",
  requestFailedShort: "请求失败",
  requestFailedWithStatus: "请求失败 ({status})",
  eventStreamMissing: "服务端未返回事件流",
  requirementInterviewFailed: "需求访谈失败",
  agentExecutionFailed: "Agent 执行失败",
};

const yue: ErrorsMessages = {
  requestFailed: "請求失敗，請再試一次",
  requestFailedShort: "請求失敗",
  requestFailedWithStatus: "請求失敗（{status}）",
  eventStreamMissing: "伺服器冇返到事件流",
  requirementInterviewFailed: "需求訪談失敗",
  agentExecutionFailed: "Agent 執行失敗",
};

/** Error copy bundle, one entry per supported locale. */
export const errors = { en, "zh-Hans": zhHans, yue };
