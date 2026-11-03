import React from "react";
import { Navigate, useParams } from "react-router-dom";
import { useI18n } from "../../i18n";
import { useAuth } from "../../store";

/**
 * Placeholder grading workspace for the assignment route.
 */
export default function GradingPlaceholder() {
  const { assignmentId } = useParams();
  const { user } = useAuth();
  const { t } = useI18n();
  if (user?.role !== "teacher") return <Navigate to="/courses" replace />;
  return <div className="placeholder-page"><i className="fas fa-file-pen placeholder-icon" /><p className="eyebrow">GRADING WORKSPACE</p><h1>{t("dashboard.gradingPlaceholder.title")}</h1><p>{t("dashboard.gradingPlaceholder.description", { assignmentId: assignmentId ?? "" })}</p></div>;
}

