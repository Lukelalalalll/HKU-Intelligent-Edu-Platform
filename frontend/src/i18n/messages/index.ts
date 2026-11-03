/**
 * Message catalogs aggregated by locale.
 *
 * Every feature owns one namespace module here; this file only wires them into a
 * single typed bundle. The English bundle defines the canonical key shape and is
 * the source of truth for {@link Messages}.
 */
import { admin } from "./admin";
import { aiVideo } from "./aiVideo";
import { auth } from "./auth";
import { common } from "./common";
import { courseware } from "./courseware";
import { coursewareAgent } from "./coursewareAgent";
import { courses } from "./courses";
import { dashboard } from "./dashboard";
import { errors } from "./errors";
import { lessonPlan } from "./lessonPlan";
import { profile } from "./profile";
import { shared } from "./shared";

const en = {
  common: common.en,
  shared: shared.en,
  errors: errors.en,
  auth: auth.en,
  dashboard: dashboard.en,
  courses: courses.en,
  coursewareAgent: coursewareAgent.en,
  courseware: courseware.en,
  lessonPlan: lessonPlan.en,
  aiVideo: aiVideo.en,
  profile: profile.en,
  admin: admin.en,
};

/** Canonical message shape; every locale must match it exactly. */
export type Messages = typeof en;

/** Full message bundle for every supported locale. */
export type MessageBundle = Record<"en" | "yue" | "zh-Hans", Messages>;

const zhHans: Messages = {
  common: common["zh-Hans"],
  shared: shared["zh-Hans"],
  errors: errors["zh-Hans"],
  auth: auth["zh-Hans"],
  dashboard: dashboard["zh-Hans"],
  courses: courses["zh-Hans"],
  coursewareAgent: coursewareAgent["zh-Hans"],
  courseware: courseware["zh-Hans"],
  lessonPlan: lessonPlan["zh-Hans"],
  aiVideo: aiVideo["zh-Hans"],
  profile: profile["zh-Hans"],
  admin: admin["zh-Hans"],
};

const yue: Messages = {
  common: common.yue,
  shared: shared.yue,
  errors: errors.yue,
  auth: auth.yue,
  dashboard: dashboard.yue,
  courses: courses.yue,
  coursewareAgent: coursewareAgent.yue,
  courseware: courseware.yue,
  lessonPlan: lessonPlan.yue,
  aiVideo: aiVideo.yue,
  profile: profile.yue,
  admin: admin.yue,
};

/** Aggregated copy for every supported locale. */
export const messages: MessageBundle = { en, yue, "zh-Hans": zhHans };
