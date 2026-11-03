/**
 * `<img>` wrapper that can load API-served assets through the authenticated
 * client. Remote URLs keep their native behaviour.
 */
import React, { useEffect, useState } from "react";
import { peekAssetUrl, resolveAssetUrl } from "../lib/authedAssets";

export type AuthedImageProps = {
  src?: string | null;
  alt?: string;
  className?: string;
  /** Rendered while loading or when the asset cannot be loaded. */
  placeholder?: React.ReactNode;
  draggable?: boolean;
  loading?: "lazy" | "eager";
};

/** Render an image whose source may require API credentials. */
export default function AuthedImage({ src, alt = "", className, placeholder = null, draggable = false, loading = "lazy" }: AuthedImageProps) {
  const fromCache = peekAssetUrl(src);
  const [url, setUrl] = useState<string | null>(() => fromCache || (src && !src.startsWith("/api/") ? src : null));
  const [failed, setFailed] = useState(false);

  useEffect(() => {
    let cancelled = false;
    setFailed(false);
    if (!src) { setUrl(null); return; }
    if (!src.startsWith("/api/")) { setUrl(src); return; }
    const ready = peekAssetUrl(src);
    setUrl(ready);
    if (ready) return;
    void resolveAssetUrl(src).then((resolved) => {
      if (cancelled) return;
      if (resolved) setUrl(resolved);
      else setFailed(true);
    });
    return () => { cancelled = true; };
  }, [src]);

  if (!url || failed) return <>{placeholder}</>;
  return <img src={url} alt={alt} className={className} draggable={draggable} loading={loading} onError={() => setFailed(true)} />;
}
