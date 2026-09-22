import React from "react";
import { Navigate, useParams } from "react-router-dom";
import { useAuth } from "../../store";

export default function GradingPlaceholder() {
  const { assignmentId } = useParams();
  const { user } = useAuth();
  if (user?.role !== "teacher") return <Navigate to="/courses" replace />;
  return <div className="placeholder-page"><i className="fas fa-file-pen placeholder-icon" /><p className="eyebrow">GRADING WORKSPACE</p><h1>作业批改工作台</h1><p>作业 {assignmentId} 的批改界面正在准备中。</p></div>;
}

