/**
 * Authenticated asset URLs for the browser image loader.
 *
 * API-served assets (`/api/...`) need the same credentials as the axios
 * client, but `<img src>` and Fabric's image loader cannot attach headers.
 * Resolving those paths to short-lived object URLs keeps them visible in
 * isolated development sessions and gives every consumer a shared cache.
 */
import { api } from "../../lib/apiClient";

/** Cached resolution per source path; `null` means the asset is unavailable. */
const resolved = new Map<string, Promise<string | null>>();
/** Already-resolved object URLs, so remounts can paint without a placeholder. */
const readyUrls = new Map<string, string>();
/** Object URLs created for this session, revoked by ``clearAssetCache``. */
const objectUrls = new Set<string>();

/** True when the path is served by the authenticated API. */
export function isApiAsset(src?: string | null): boolean {
  if (!src) return false;
  return src.startsWith("/api/") || src.startsWith("api/");
}

/** True when object URLs can be created in the current environment. */
function canCreateObjectUrl(): boolean {
  return typeof URL !== "undefined" && typeof URL.createObjectURL === "function";
}

/**
 * Resolve an asset path to something `<img>` can load.
 *
 * Remote URLs pass through untouched. API paths are fetched with the shared
 * axios client (cookie or development bearer token) and cached for the tab.
 */
export function resolveAssetUrl(src?: string | null): Promise<string | null> {
  if (!src) return Promise.resolve(null);
  if (!isApiAsset(src) || !canCreateObjectUrl()) return Promise.resolve(src || null);
  const cached = resolved.get(src);
  if (cached) return cached;
  const task = api
    .get<Blob>(src.replace(/^\/api/, ""), { responseType: "blob" })
    .then(({ data }) => {
      const url = URL.createObjectURL(data);
      objectUrls.add(url);
      readyUrls.set(src, url);
      return url;
    })
    .catch(() => null);
  resolved.set(src, task);
  return task;
}

/** Return an already-resolved URL without starting a request. */
export function peekAssetUrl(src?: string | null): string | null {
  if (!src) return null;
  return readyUrls.get(src) ?? null;
}

/** Forget one cached asset so the next consumer retries it. */
export function invalidateAsset(src?: string | null): void {
  if (!src) return;
  resolved.delete(src);
  readyUrls.delete(src);
}

/** Drop every cached object URL. Used by tests and on explicit retry. */
export function clearAssetCache(): void {
  resolved.clear();
  readyUrls.clear();
  if (typeof URL !== "undefined" && typeof URL.revokeObjectURL === "function") {
    objectUrls.forEach((url) => URL.revokeObjectURL(url));
  }
  objectUrls.clear();
}
