/**
 * Shared axios client and SSE helpers for every API module.
 *
 * Requests always send credentials and, in development, mark themselves as an
 * isolated session so a tab keeps its token in sessionStorage instead of the
 * shared cookies.  Failures are normalized to ``ApiError``.
 */
import axios, { AxiosError, type AxiosRequestConfig } from "axios";
import { translate } from "../i18n/translate";

/**
 * sessionStorage key of the per-tab development access token.
 */
export const DEV_SESSION_STORAGE_KEY = "hku-dev-access-token";
const isDevelopment = import.meta.env.DEV;

/**
 * Normalized API failure with a retry hint derived from the status.
 */
export type ApiError = {
  status?: number;
  code?: string;
  message: string;
  retryable: boolean;
  cause?: unknown;
};

/**
 * Narrow an unknown thrown value to ``ApiError``.
 */
export function isApiError(error: unknown): error is ApiError {
  return Boolean(error && typeof error === "object" && "message" in error && "retryable" in error);
}

/**
 * Return a user-facing message, falling back to the backend detail.
 */
export function getApiErrorMessage(error: unknown, fallback = translate("errors.requestFailed")): string {
  if (isApiError(error)) return error.message || fallback;
  if (axios.isAxiosError(error)) {
    const detail = error.response?.data?.detail;
    return typeof detail === "string" ? detail : error.message || fallback;
  }
  if (error instanceof Error && error.message) return error.message;
  return fallback;
}

/**
 * Read the per-tab development token; null outside development.
 */
export function getDevAccessToken(): string | null {
  if (!isDevelopment || typeof window === "undefined") return null;
  return window.sessionStorage.getItem(DEV_SESSION_STORAGE_KEY);
}

/**
 * Persist or clear the per-tab development token.
 */
export function setDevAccessToken(token: string | null): void {
  if (!isDevelopment || typeof window === "undefined") return;
  if (token) window.sessionStorage.setItem(DEV_SESSION_STORAGE_KEY, token);
  else window.sessionStorage.removeItem(DEV_SESSION_STORAGE_KEY);
}

/**
 * Normalize axios and generic errors into ``ApiError``.
 *
 * Network failures, 5xx and 429 are marked retryable; other 4xx are not,
 * because repeating the same request cannot succeed.
 */
export function toApiError(error: unknown): ApiError {
  if (isApiError(error)) return error;
  if (axios.isAxiosError(error)) {
    const response = error.response;
    const detail = response?.data?.detail;
    const message = typeof detail === "string" ? detail : error.message || translate("errors.requestFailedShort");
    const status = response?.status;
    return { status, code: response?.data?.code, message, retryable: !status || status >= 500 || status === 429, cause: error };
  }
  if (error instanceof Error) return { message: error.message, retryable: true, cause: error };
  return { message: translate("errors.requestFailed"), retryable: true, cause: error };
}

/**
 * Axios instance mounted at ``/api`` with cookie credentials.
 */
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

/**
 * Execute one request and resolve with the response body.
 */
export async function request<T>(config: AxiosRequestConfig): Promise<T> {
  const response = await api.request<T>(config);
  return response.data;
}

/**
 * JSON payload of one server-sent event frame.
 */
export type SseEvent = Record<string, unknown>;

/** Consume an SSE response safely. The callback is invoked only for valid JSON data frames. */
export async function consumeSse<T extends SseEvent>(
  response: Response,
  onEvent: (event: T) => void,
  signal?: AbortSignal,
): Promise<void> {
  if (!response.ok) {
    const body = await response.text().catch(() => "");
    throw toApiError(new Error(body || translate("errors.requestFailedWithStatus", { status: response.status })));
  }
  if (!response.body) throw toApiError(new Error(translate("errors.eventStreamMissing")));
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

/**
 * Build fetch headers for an SSE request, including the dev token.
 */
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
