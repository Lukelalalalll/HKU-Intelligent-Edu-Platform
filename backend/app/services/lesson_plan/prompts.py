"""Prompts and deterministic fallbacks for the lesson plan agent.

The model is asked for JSON because the service persists structured state from
it.  Every prompt has a matching fallback so the workspace remains usable when
the provider is not configured or returns an unexpected shape.
"""

from __future__ import annotations

import re
from typing import Any

BUSINESS_CODE = "teacher_lesson_plan_agent"

# Page roles persisted on ``LessonPlanPage.page_role``.
PAGE_ROLES = ("objectives", "content", "activity", "exercise", "summary", "homework", "reference", "answer")

# Ordered fallback interview.  ``code`` is persisted under ``answers.__asked``
# so a teacher who skips the model is still walked through every topic once.
FALLBACK_QUESTIONS: tuple[dict[str, Any], ...] = (
    {
        "code": "grade",
        "label": "这份学案面向哪个学段或年级？",
        "options": ["初中", "高中", "大学本科", "研究生"],
    },
    {
        "code": "subject",
        "label": "学科和具体课题是什么？",
        "options": ["数学", "物理", "化学", "生物", "人文社科"],
    },
    {
        "code": "objectives",
        "label": "你希望学生下课时能掌握什么？可以列 1–3 条。",
        "options": ["理解核心概念", "会做典型练习", "能完成小组探究", "能解释真实情境问题"],
    },
    {
        "code": "duration",
        "label": "这节课多长时间？",
        "options": ["40 分钟", "45 分钟", "60 分钟", "90 分钟"],
    },
    {
        "code": "activities",
        "label": "希望安排哪些课堂活动？",
        "options": ["教师讲解 + 提问", "小组讨论", "动手实验或操作", "当堂练习讲评"],
    },
    {
        "code": "page_count",
        "label": "学案打印几页？是否需要答案区？",
        "options": ["2 页，不含答案", "3 页，含答案", "4 页，含答案", "6 页，含答案"],
    },
)

INTERVIEW_SYSTEM = """你是香港高校与中学课堂场景下的「学案 Agent」需求访谈助手。根据教师的描述、已上传资料和对话历史，逐轮帮助教师把学案需求说清楚。

只输出 JSON 对象，不要输出 JSON 之外的文字：
{
  "assistant_markdown": "给教师的回复（2-4 句，可用项目符号，简洁友好）",
  "brief_summary": "用教师口吻总结当前学案需求（1-3 句）",
  "question": {"code": "grade|subject|objectives|duration|activities|page_count|answers|other", "label": "这一轮唯一要问的问题", "options": ["短选项1", "短选项2", "短选项3"]} | null,
  "answers_patch": {"grade": "", "subject": "", "objectives": [], "duration_minutes": 45, "activities": [], "page_count": 4, "include_answers": true, "difficulty": "basic|standard|challenge", "notes": ""},
  "missing_fields": ["..."],
  "ready_to_generate": false,
  "suggested_additions": ["1-3 条教师可以补充的信息"]
}

规则：
- 先确认学段/年级、学科与课题、学习目标、课堂时长；再确认页数、练习与是否需要答案区。
- 每轮只问一个最关键的问题，给 3-5 个可直接点击的短选项，同时允许教师自由输入。
- 如果上下文中有资料摘要，先用一句话说明你从资料中读到了什么，再提问。
- 不要询问视觉风格或排版主题；不要重复教师已经确认的信息。
- 信息足够时 ready_to_generate=true，并告诉教师可以点击「生成学案」，同时列出可继续补充的内容。
- 使用与教师输入一致的语言；教师使用中文时输出简体中文。"""


def generation_system(page_count: int, include_answers: bool) -> str:
    """Return the generation system prompt for one plan request."""
    answers_rule = (
        "练习页需要给出 `> [!answer]` 参考答案块。"
        if include_answers
        else "不要输出 `> [!answer]` 参考答案块。"
    )
    return f"""你是香港高校与中学课堂场景下的「学案 Agent」设计助手。请把教师的需求和资料摘要转成可以直接打印的课堂学案。

只输出 JSON 对象，不要输出 JSON 之外的文字：
{{
  "title": "学案标题（含学科与课题，不超过 60 字）",
  "subject": "学科",
  "grade": "学段或年级",
  "duration_minutes": 45,
  "summary_markdown": "用 2-3 句话向教师说明这份学案的结构与使用建议，可用项目符号",
  "pages": [
    {{"title": "页面标题（不超过 24 字）", "page_role": "objectives|content|activity|exercise|summary|homework|reference", "markdown": "该页完整 Markdown"}}
  ]
}}

规则：
- 共 {page_count} 页，按课堂顺序排列；第一页必须是学习目标，最后一页必须是总结与作业。
- 每页内容适合 A4 单页打印，约 250-600 字，紧扣课题，避免空泛套话。
- Markdown 只允许使用：### 小标题、段落、无序列表、有序列表、表格、`> [!tip]` 提示块、`> [!answer]` 参考答案块、`---` 分隔线。不要使用图片、超链接、HTML 或代码块。
- {answers_rule}
- 练习必须与学习目标一一对应，并标注难度层级（基础 / 进阶 / 挑战）。
- 资料摘要中没有的事实不要编造；引用资料时写成「（资料：文件名，第 N 页）」，页码不确定就只写文件名。
- 使用与教师输入一致的语言；教师使用中文时输出简体中文。"""


PAGE_REWRITE_SYSTEM = """你是「学案 Agent」的单页改写助手。教师只要求重写当前这一页，请保持与整份学案一致的语气与结构。

只输出 JSON 对象：
{"title": "页面标题（不超过 24 字）", "page_role": "objectives|content|activity|exercise|summary|homework|reference", "markdown": "改写后的完整 Markdown"}

规则：
- 继续使用 ### 小标题、列表、表格、`> [!tip]`、`> [!answer]` 等既有语法。
- 保留原有学习目标与知识主线，只按教师的修改意见调整。
- 资料摘要中没有的事实不要编造；不要输出图片、链接或 HTML。
- 使用与教师输入一致的语言。"""


REFINE_SYSTEM = """你是「学案 Agent」的修改助手。教师已经有一份学案，现在提出修改意见，请判断需要修改哪些页。

只输出 JSON 对象：
{
  "assistant_markdown": "给教师的回复（1-3 句）",
  "page_updates": [{"page_id": "被修改页面的 id", "markdown": "修改后的完整 Markdown"}],
  "needs_regenerate": false
}

规则：
- 只修改教师明确提到的页面，其他页面保持不变；未提到的页面不要返回。
- page_id 只能取自输入中提供的页面列表。
- 如果教师要求整份重写、改变页数或大幅更换结构，needs_regenerate=true，并在回复中说明建议，page_updates 留空。
- 修改后的 Markdown 必须保留 ### 小标题、列表、表格、`> [!tip]`、`> [!answer]` 等原有约定。
- 使用与教师输入一致的语言。"""


def brief_summary(answers: dict[str, Any]) -> str:
    """Compose a short brief from the collected answers."""
    parts: list[str] = []
    grade, subject = answers.get("grade"), answers.get("subject")
    if grade or subject:
        parts.append(f"面向{grade or '学生'}的{subject or '课程'}")
    objectives = [str(item).strip() for item in answers.get("objectives") or [] if str(item).strip()]
    if objectives:
        parts.append("学习目标：" + "；".join(objectives[:3]))
    duration = answers.get("duration_minutes")
    if duration:
        parts.append(f"{duration} 分钟")
    page_count = answers.get("page_count")
    if page_count:
        parts.append(f"{page_count} 页")
    if answers.get("include_answers") is not None:
        parts.append("含答案区" if answers.get("include_answers") else "不含答案")
    return "，".join(parts) if parts else "正在整理学案需求。"


def interview_fallback(answers: dict[str, Any], reason: str = "") -> dict[str, Any]:
    """Return the next deterministic interview turn.

    The returned dict mirrors the model schema so the caller can apply both
    through the same path.  ``__asked_code`` tells the service which fallback
    question was consumed.
    """
    asked = {str(item) for item in answers.get("__asked") or []}
    for question in FALLBACK_QUESTIONS:
        if question["code"] in asked:
            continue
        notes = str(answers.get("notes") or "").strip()
        lead = "（当前无法调用 AI 模型，先用引导问题继续，稍后可在管理员处配置模型。）\n\n"
        return {
            "assistant_markdown": lead + question["label"],
            "brief_summary": brief_summary(answers),
            "question": {
                "code": question["code"],
                "label": question["label"],
                "options": list(question["options"]),
            },
            "answers_patch": {},
            "missing_fields": [question["code"]],
            "ready_to_generate": False,
            "suggested_additions": [],
            "__asked_code": question["code"],
            "__fallback_reason": reason,
            "__notes": notes,
        }
    return {
        "assistant_markdown": "需求已经整理完成，可以点击「生成学案」。如果还有页数、练习或案例偏好，也可以继续补充。",
        "brief_summary": brief_summary(answers),
        "question": None,
        "answers_patch": {},
        "missing_fields": [],
        "ready_to_generate": True,
        "suggested_additions": ["补充本班学生的先备知识", "指定希望引用的教材页码"],
        "__fallback_reason": reason,
    }


def template_pages(
    *,
    title: str,
    request_text: str,
    answers: dict[str, Any],
    materials: list[dict[str, Any]],
    page_count: int,
    include_answers: bool,
) -> list[dict[str, Any]]:
    """Build a deterministic lesson plan when no model is available.

    The pages are deliberately plain but structurally complete: a teacher can
    edit them in the workspace and still export a usable PDF or Markdown file.
    """
    topic = (title or request_text or "本课课题").strip().splitlines()[0][:60]
    topic = re.sub(r"(学案|教案|课件|学习单|导学案)$", "", topic).strip() or "本课课题"
    objectives = [str(item).strip() for item in answers.get("objectives") or [] if str(item).strip()]
    if not objectives:
        objectives = [
            f"理解「{topic}」的核心概念与关键术语",
            f"能够运用「{topic}」解决基础问题",
            f"能够说明「{topic}」在真实情境中的应用",
        ]
    duration = int(answers.get("duration_minutes") or 45)
    activities = [str(item).strip() for item in answers.get("activities") or [] if str(item).strip()]
    if not activities:
        activities = ["教师讲解与提问", "小组讨论", "当堂练习与讲评"]
    material_lines = []
    for material in materials[:3]:
        excerpt = str(material.get("text") or "").strip()
        if excerpt:
            material_lines.append(f"- 《{material.get('title') or '资料'}》：{excerpt[:180]}")

    pages: list[dict[str, Any]] = []
    pages.append(
        {
            "title": "学习目标",
            "page_role": "objectives",
            "markdown": "\n".join(f"- {item}" for item in objectives),
        }
    )
    content_lines = [f"本课围绕**{topic}**展开。"]
    if request_text.strip():
        content_lines += ["", *request_text.strip().splitlines()[:8]]
    if material_lines:
        content_lines += ["", "### 资料要点", "", *material_lines]
    else:
        content_lines += ["", "### 关键概念", "", f"- {topic} 的定义与适用范围", "- 典型例题与常见误区", "- 与前后课时知识的联系"]
    pages.append({"title": "核心知识", "page_role": "content", "markdown": "\n".join(content_lines)})

    activity_lines = [f"建议总时长约 {duration} 分钟。", ""]
    for index, activity in enumerate(activities, 1):
        activity_lines.append(f"{index}. **{activity}**：结合本课重点完成课堂任务，教师巡回指导。")
    pages.append({"title": "课堂活动", "page_role": "activity", "markdown": "\n".join(activity_lines)})

    exercise_lines = [
        "1. **基础**：用自己的话解释本课的核心概念，并举一个例子。",
        "2. **进阶**：完成一道与课堂例题同类型的变式题。",
        "3. **挑战**：把本课知识应用到一个真实情境中，并说明理由。",
    ]
    if include_answers:
        exercise_lines += [
            "",
            "> [!answer] 参考答案",
            "> 请结合课堂讲解与教材内容补充：概念解释应包含定义、条件与例子；变式题按课堂板书的解题步骤作答；开放题言之成理即可。",
        ]
    pages.append({"title": "课堂练习", "page_role": "exercise", "markdown": "\n".join(exercise_lines)})

    pages.append(
        {
            "title": "总结与作业",
            "page_role": "summary",
            "markdown": "### 本课小结\n\n"
            + "\n".join(f"- {item}" for item in objectives[:3])
            + "\n\n### 课后作业\n\n1. 整理本课笔记，并标出仍然不清楚的一个问题。\n2. 完成与「"
            + topic
            + "」相关的基础练习。",
        }
    )

    pages = _trim_pages(pages, page_count)
    for page in pages:
        page["markdown"] = page["markdown"].strip()
    return pages


def _trim_pages(pages: list[dict[str, Any]], page_count: int) -> list[dict[str, Any]]:
    """Keep the requested number of pages while preserving first and last.

    Exercise pages outrank the activity page when the requested count is small,
    because practice is the part of a lesson plan a teacher is least likely to
    want dropped.
    """
    target = max(1, min(int(page_count or len(pages)), len(pages)))
    if target >= len(pages):
        return pages
    if target == 1:
        return [pages[0]]
    first, last = pages[0], pages[-1]
    middle = pages[1:-1]
    priority = {"exercise": 0, "content": 1, "activity": 2}
    kept = sorted(middle, key=lambda page: priority.get(page.get("page_role", ""), 9))[: max(0, target - 2)]
    kept_ids = {id(page) for page in kept}
    ordered = [page for page in middle if id(page) in kept_ids]
    return [first, *ordered, last]


def template_plan(
    *,
    title: str,
    request_text: str,
    answers: dict[str, Any],
    materials: list[dict[str, Any]],
    page_count: int,
    include_answers: bool,
) -> dict[str, Any]:
    """Return the full fallback generation payload."""
    pages = template_pages(
        title=title,
        request_text=request_text,
        answers=answers,
        materials=materials,
        page_count=page_count,
        include_answers=include_answers,
    )
    return {
        "title": (title or "未命名学案").strip()[:60],
        "subject": str(answers.get("subject") or ""),
        "grade": str(answers.get("grade") or ""),
        "duration_minutes": int(answers.get("duration_minutes") or 45),
        "summary_markdown": f"当前无法调用 AI 模型，已按模板生成 {len(pages)} 页可编辑学案。配置模型后重新生成，可获得更贴合资料的内容。",
        "pages": pages,
        "__degraded": True,
    }


__all__ = [
    "BUSINESS_CODE",
    "FALLBACK_QUESTIONS",
    "INTERVIEW_SYSTEM",
    "PAGE_REWRITE_SYSTEM",
    "PAGE_ROLES",
    "REFINE_SYSTEM",
    "brief_summary",
    "generation_system",
    "interview_fallback",
    "template_pages",
    "template_plan",
]
