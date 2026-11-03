import React, { useEffect, useRef, useState } from "react";
import { useSearchParams, useParams, useNavigate } from "react-router-dom";
import toast from "react-hot-toast";
import { getApiErrorMessage, liveClassApi, type LiveClassAuthorization } from "../../../api";
import { useAuth } from "../../../store";
import { useI18n } from "../../../i18n";

/**
 * Zoom Meeting SDK view for one class occurrence.
 */
export default function LiveClassRoute() {
  const { courseId } = useParams();
  const { t } = useI18n();
  const [params] = useSearchParams();
  const navigate = useNavigate();
  const user = useAuth((state) => state.user);
  const [auth, setAuth] = useState<LiveClassAuthorization | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [sdkReady, setSdkReady] = useState(false);
  const containerRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!courseId) return;
    const action = params.get("action") === "start" && (user?.role === "teacher" || user?.role === "admin") ? "start" : "join";
    const controller = new AbortController();
    liveClassApi.authorize(courseId, action, params.get("meetingId") || undefined, { signal: controller.signal }).then((response) => setAuth(response.data)).catch((err: unknown) => { if (!controller.signal.aborted) setError(getApiErrorMessage(err, t("courses.liveRoute.enterFailed"))); });
    return () => controller.abort();
  }, [courseId, params, user?.role]);

  useEffect(() => {
    if (!auth || !containerRef.current) return;
    let cancelled = false;
    import("@zoom/meetingsdk").then(({ ZoomMtg }) => {
      if (cancelled) return;
      ZoomMtg.setZoomJSLib("https://source.zoom.us/6.2.0/lib", "/av");
      ZoomMtg.preLoadWasm();
      ZoomMtg.prepareWebSDK();
      ZoomMtg.init({ leaveUrl: `${window.location.origin}/courses/${courseId}`, patchJsMedia: true, debug: false, isSupportAV: true, isSupportChat: true, screenShare: true, success: () => {
        ZoomMtg.join({ signature: auth.sdk_jwt, meetingNumber: auth.meeting_number, userName: auth.user_name, passWord: "", zak: auth.zak || undefined, success: () => setSdkReady(true), error: (joinError: unknown) => setError(String(joinError || t("courses.liveRoute.initFailed"))) });
      }, error: (initError: unknown) => setError(String(initError || t("courses.liveRoute.initFailed"))) });
    }).catch(() => setError(t("courses.liveRoute.sdkLoadFailed")));
    return () => { cancelled = true; };
  }, [auth]);

  if (error) return <div className="placeholder-page"><i className="fas fa-triangle-exclamation placeholder-icon" /><h1>{t("courses.liveRoute.enterTitle")}</h1><p>{error}</p></div>;
  return <div className="live-class-page"><header><div><p className="eyebrow">ZOOM LIVE CLASS</p><h1>{sdkReady ? t("courses.liveRoute.inClass") : t("courses.liveRoute.connecting")}</h1></div><button className="secondary-action" type="button" onClick={() => navigate(`/courses/${courseId}`)}>{t("courses.liveRoute.leave")}</button></header><div id="zmmtg-root" ref={containerRef} className="zoom-sdk-container" aria-label={t("courses.liveRoute.ariaLabel")} /></div>;
}
