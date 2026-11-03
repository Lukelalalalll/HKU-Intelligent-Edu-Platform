# Translation glossary

Shared terminology for the English / 粵語 / 简体中文 UI. Follow this table before
inventing a new label; add rows when a new cross-page concept appears.

| Concept | en | zh-Hans | yue |
| --- | --- | --- | --- |
| Language | Language | 语言 | 語言 |
| Login | Login | 登录 | 登入 |
| Register | Register | 注册 | 註冊 |
| Log out | Log out | 退出 | 登出 |
| Overview | Overview | 总览 | 總覽 |
| Courses | Courses | 课程 | 課程 |
| My courses | My courses | 我的课程 | 我的課程 |
| Course details | Course details | 课程详情 | 課程詳情 |
| Live class | Live class | 直播课堂 | 直播課堂 |
| Assignments | Assignments | 作业 | 作業 |
| Grading | Grading | 作业批改 | 作業批改 |
| Announcements | Announcements | 公告 | 公告 |
| Materials | Materials | 课程资料 | 課程資料 |
| Discussions | Discussions | 讨论 | 討論 |
| Comment | Comment | 评论 | 留言 |
| Post comment | Post comment | 发布评论 | 發佈留言 |
| Grades | Grades | 成绩 | 成績 |
| Participants | Participants | 参与者 | 參與者 |
| Semester 1 | Semester 1 | 第一学期 | 第一學期 |
| Semester 2 | Semester 2 | 第二学期 | 第二學期 |
| Summer Semester | Summer Semester | 夏季学期 | 夏季學期 |
| Academic year | Academic year | 学年 | 學年 |
| Teacher | Teacher | 教师 | 教師 |
| Student | Student | 学生 | 學生 |
| Administrator | Administrator | 管理员 | 管理員 |
| Dashboard | Dashboard | 工作台 | 工作台 |
| Workspace | Workspace | 工作区 | 工作區 |
| Profile | Profile | 个人资料 | 個人資料 |
| Admin Console | Admin Console | 管理后台 | 管理後台 |
| PPT Agent | PPT Agent | PPT Agent | PPT Agent |
| Lesson plan | Lesson plan | 学案 | 學案 |
| Teaching video | Teaching video | 教学视频 | 教學影片 |
| AI Lecturer | AI Lecturer | AI 讲师 | AI 講師 |
| Room TBA | Room TBA | 待定教室 | 待定課室 |
| This week | This week | 本周 | 本週 |
| Today | Today | 今天 | 今日 |
| Due | Due | 截止 | 截止 |
| Submit | Submit | 提交 | 提交 |
| Upload | Upload | 上传 | 上傳 |
| Download | Download | 下载 | 下載 |
| Save | Save | 保存 | 儲存 |
| Cancel | Cancel | 取消 | 取消 |
| Confirm | Confirm | 确认 | 確認 |
| Delete | Delete | 删除 | 刪除 |
| Edit | Edit | 编辑 | 編輯 |
| Retry | Retry | 重试 | 重試 |
| Loading | Loading… | 加载中… | 載入緊… |
| Search | Search | 搜索 | 搜尋 |
| Settings | Settings | 设置 | 設定 |
| Notification | Notification | 通知 | 通知 |
| Failed | Failed | 失败 | 失敗 |
| Completed | Completed | 已完成 | 已完成 |
| Processing | Processing… | 处理中… | 處理緊… |
| Empty list | No items yet | 暂无内容 | 暫時未有內容 |

## Style rules

### English

- Sentence case for buttons, labels and help text: `Save changes`, `Post comment`.
- Keep product/brand names as-is: `HKU`, `PPT Agent`, `AI`, `Zoom`, `Panopto`.
- Use `{count}` interpolation; when grammar changes, add `one`/`other` key pairs
  and choose by count (`count === 1 ? "…one" : "…other"`).

### 简体中文 (zh-Hans)

- Preserve existing copy exactly where it exists — this is a localization
  refactor, not a rewrite.
- Full-width punctuation: `，。；：（）「」`.
- Latin terms keep a single space: `AI 讲师`, `PPT Agent`, `Base URL`.

### 粵語 (yue)

- Traditional characters with written Cantonese grammar and vocabulary.
- Prefer HK usage: `課室` (not 教室), `檔案` (文件), `影片` (视频), `登入` (登录),
  `儲存` (保存), `搜尋` (搜索), `留言` (评论), `發佈` (发布), `學期` (学期),
  `揀` (选择), `睇` (查看), `攞` (获取), `俾` (给).
- Common particles: `係`, `唔`, `嘅`, `咗`, `喺`, `啲`, `冇`, `緊`, `返`, `咁`.
- Do not produce Mandarin word-for-word transliterations; write natural 粵文.
- Keep the same brand/technical tokens untranslated.

## Do not translate

- Backend data: course names, course codes, teacher/student names, assignment
  titles, file names, room identifiers, provider `display_name`/`description`.
- Identifiers: route paths, query parameter values, API roles (`teacher`).
- Design-token eyebrows that are already English in the current UI:
  `TEACHER WORKSPACE`, `STUDENT WORKSPACE`, `TODAY`, `REVIEW QUEUE`,
  `COURSE DISCUSSION`, `LESSON PLAN AGENT`, `PPT AGENT`, `COURSEWARE RAG`,
  `PROVIDERS`, `BUSINESS MAPPING`, `ADMINISTRATION · AI CONTROL`.
