import axios, { AxiosError, type AxiosRequestConfig } from "axios";

export const DEV_SESSION_STORAGE_KEY = "hku-dev-access-token";
const isDevelopment = import.meta.env.DEV;

export type ApiError = {
  status?: number;
  code?: string;
  message: string;
  retryable: boolean;
  cause?: unknown;
};

export function isApiError(error: unknown): error is ApiError {
  return Boolean(error && typeof error === "object" && "message" in error && "retryable" in error);
}

export function getApiErrorMessage(error: unknown, fallback = "请求失败，请稍后重试"): string {
  if (isApiError(error)) return error.message || fallback;
  if (axios.isAxiosError(error)) {
    const detail = error.response?.data?.detail;
    return typeof detail === "string" ? detail : error.message || fallback;
  }
  if (error instanceof Error && error.message) return error.message;
  return fallback;
}

export function getDevAccessToken(): string | null {
  if (!isDevelopment || typeof window === "undefined") return null;
  return window.sessionStorage.getItem(DEV_SESSION_STORAGE_KEY);
}

export function setDevAccessToken(token: string | null): void {
  if (!isDevelopment || typeof window === "undefined") return;
  if (token) window.sessionStorage.setItem(DEV_SESSION_STORAGE_KEY, token);
  else window.sessionStorage.removeItem(DEV_SESSION_STORAGE_KEY);
}

export function toApiError(error: unknown): ApiError {
  if (isApiError(error)) return error;
  if (axios.isAxiosError(error)) {
    const response = error.response;
    const detail = response?.data?.detail;
    const message = typeof detail === "string" ? detail : error.message || "请求失败";
    const status = response?.status;
    return { status, code: response?.data?.code, message, retryable: !status || status >= 500 || status === 429, cause: error };
  }
  if (error instanceof Error) return { message: error.message, retryable: true, cause: error };
  return { message: "请求失败，请稍后重试", retryable: true, cause: error };
}

export const api = axios.create({ baseURL: "/api", withCredentials: true, timeout: 30_000 });
api.interceptors.request.use((config) => {
  if (isDevelopment) {
    config.headers.set("X-HKU-Session-Mode", "isolated");
    const token = getDevAccessToken();
    if (token) config.headers.set("Authorization", `Bearer ${token}`);
  }
  return config;
});
api.interceptors.response.use(undefined, (error: AxiosError) => Promise.reject(toApiError(error)));

export async function request<T>(config: AxiosRequestConfig): Promise<T> {
  const response = await api.request<T>(config);
  return response.data;
}

export type SseEvent = Record<string, unknown>;

/** Consume an SSE response safely. The callback is invoked only for valid JSON data frames. */
export async function consumeSse<T extends SseEvent>(
  response: Response,
  onEvent: (event: T) => void,
  signal?: AbortSignal,
): Promise<void> {
  if (!response.ok) {
    const body = await response.text().catch(() => "");
    throw toApiError(new Error(body || `请求失败 (${response.status})`));
  }
  if (!response.body) throw toApiError(new Error("服务端未返回事件流"));
  const reader = response.body.getReader();
  const decoder = new TextDecoder();
  let buffer = "";
  const consumeFrame = (frame: string) => {
    const data = frame
      .split(/\r?\n/)
      .filter((line) => line.startsWith("data:"))
      .map((line) => line.slice(5).trim())
      .join("\n");
    if (!data) return;
    try {
      onEvent(JSON.parse(data) as T);
    } catch (error) {
      if (error instanceof SyntaxError) return;
      throw error;
    }
  };
  try {
    while (true) {
      if (signal?.aborted) throw new DOMException("The operation was aborted.", "AbortError");
      const { done, value } = await reader.read();
      if (done) break;
      buffer += decoder.decode(value, { stream: true });
      let split = buffer.indexOf("\n\n");
      while (split >= 0) {
        consumeFrame(buffer.slice(0, split));
        buffer = buffer.slice(split + 2);
        split = buffer.indexOf("\n\n");
      }
    }
    buffer += decoder.decode();
    if (buffer.trim()) consumeFrame(buffer);
  } finally {
    reader.releaseLock();
  }
}

export function createStreamHeaders(contentType?: string): Headers {
  const headers = new Headers(contentType ? { "Content-Type": contentType } : undefined);
  headers.set("Accept", "text/event-stream");
  if (isDevelopment) {
    headers.set("X-HKU-Session-Mode", "isolated");
    const token = getDevAccessToken();
    if (token) headers.set("Authorization", `Bearer ${token}`);
  }
  return headers;
}
