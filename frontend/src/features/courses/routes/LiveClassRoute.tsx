import React, { useEffect, useRef, useState } from "react";
import { Link, useSearchParams, useParams, useNavigate } from "react-router-dom";
import toast from "react-hot-toast";
import { liveClassApi, type LiveClassAuthorization } from "../../../api";
import { useAuth } from "../../../store";

export default function LiveClassRoute() {
  const { courseId } = useParams();
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
    liveClassApi.authorize(courseId, action, params.get("meetingId") || undefined).then((response) => setAuth(response.data)).catch((err) => setError(err.response?.data?.detail || "无法进入 Zoom 课堂"));
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
        ZoomMtg.join({ signature: auth.sdk_jwt, meetingNumber: auth.meeting_number, userName: auth.user_name, passWord: "", zak: auth.zak || undefined, success: () => setSdkReady(true), error: (joinError: unknown) => setError(String(joinError || "Zoom 课堂初始化失败")) });
      }, error: (initError: unknown) => setError(String(initError || "Zoom 课堂初始化失败")) });
    }).catch(() => setError("Zoom Meeting SDK 未加载，请检查前端依赖和网络"));
    return () => { cancelled = true; };
  }, [auth]);

  if (error) return <div className="placeholder-page"><i className="fas fa-triangle-exclamation placeholder-icon" /><h1>无法进入课堂</h1><p>{error}</p><Link className="primary-action" to={`/courses/${courseId}`}>返回课程</Link></div>;
  return <div className="live-class-page"><header><div><p className="eyebrow">ZOOM LIVE CLASS</p><h1>{sdkReady ? "课堂进行中" : "正在连接课堂…"}</h1></div><button className="secondary-action" type="button" onClick={() => navigate(`/courses/${courseId}`)}>退出课堂</button></header><div id="zmmtg-root" ref={containerRef} className="zoom-sdk-container" aria-label="Zoom 实时课堂" /></div>;
}
