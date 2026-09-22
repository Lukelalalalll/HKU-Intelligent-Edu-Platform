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
