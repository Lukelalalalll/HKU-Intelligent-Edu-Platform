import React, { useCallback, useEffect, useState } from "react";
import toast from "react-hot-toast";
import { discussionApi, type DiscussionComment } from "../../../api";
import { useAuth } from "../../../store";
import styles from "../styles/CoursesRoute.module.css";

const MAX_LENGTH = 2000;

function displayName(comment: DiscussionComment) {
  return comment.author.name || comment.author.username;
}

function avatarLabel(comment: DiscussionComment) {
  return displayName(comment).slice(0, 1).toUpperCase();
}

function timeLabel(value: string) {
  return new Intl.DateTimeFormat("zh-CN", { month: "short", day: "numeric", hour: "2-digit", minute: "2-digit" }).format(new Date(value));
}

export default function DiscussionModule({ courseId }: { courseId: string }) {
  const user = useAuth((state) => state.user);
  const [comments, setComments] = useState<DiscussionComment[]>([]);
  const [draft, setDraft] = useState("");
  const [replyTarget, setReplyTarget] = useState<string | null>(null);
  const [replyDraft, setReplyDraft] = useState("");
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState(false);

  const load = useCallback(() => {
    setLoading(true);
    setError(false);
    return discussionApi.list(courseId).then((response) => setComments(response.data)).catch(() => setError(true)).finally(() => setLoading(false));
  }, [courseId]);

  useEffect(() => { void load(); }, [load]);

  const submit = async (event: React.FormEvent) => {
    event.preventDefault();
    const content = draft.trim();
    if (!content || busy) return;
    setBusy(true);
    try {
      const response = await discussionApi.create(courseId, content);
      setComments((current) => [response.data, ...current]);
      setDraft("");
    } catch (requestError: any) {
      toast.error(requestError.response?.data?.detail || "发布评论失败");
    } finally { setBusy(false); }
  };

  const submitReply = async (event: React.FormEvent, parentId: string) => {
    event.preventDefault();
    const content = replyDraft.trim();
    if (!content || busy) return;
    setBusy(true);
    try {
      await discussionApi.reply(courseId, parentId, content);
      setReplyDraft("");
      setReplyTarget(null);
      await load();
    } catch (requestError: any) {
      toast.error(requestError.response?.data?.detail || "发布回复失败");
    } finally { setBusy(false); }
  };

  const toggleLike = async (comment: DiscussionComment) => {
    try {
      const response = comment.liked_by_me ? await discussionApi.unlike(courseId, comment.id) : await discussionApi.like(courseId, comment.id);
      setComments((current) => current.map((item) => item.id === comment.id ? { ...item, liked_by_me: response.data.liked, like_count: response.data.like_count } : {
        ...item,
        replies: item.replies.map((reply) => reply.id === comment.id ? { ...reply, liked_by_me: response.data.liked, like_count: response.data.like_count } : reply),
      }));
    } catch (requestError: any) { toast.error(requestError.response?.data?.detail || "更新点赞失败"); }
  };

  const remove = async (commentId: string) => {
    if (!window.confirm("确认删除这条评论吗？")) return;
    try {
      await discussionApi.remove(courseId, commentId);
      await load();
      toast.success("评论已删除");
    } catch (requestError: any) { toast.error(requestError.response?.data?.detail || "删除评论失败"); }
  };

  const canDelete = (comment: DiscussionComment) => user?.id === comment.author.id || user?.role === "teacher" || user?.role === "admin";
  const authorAvatar = user?.avatar_url ? <img src={user.avatar_url} alt="" className={styles.discussionAvatarImage} /> : <span className={styles.discussionAvatar}>{(user?.name || user?.username || "U").slice(0, 1).toUpperCase()}</span>;

  return <div className={styles.discussionContent}>
    <header className={styles.discussionHeading}>
      <div><p className="eyebrow">COURSE DISCUSSION</p><h2>Discussions</h2><span>围绕课程内容交流想法、问题和经验</span></div><i className="fas fa-comments" />
    </header>
    <form className={styles.discussionComposer} onSubmit={submit}>
      {authorAvatar}
      <div className={styles.discussionComposerBody}><textarea value={draft} maxLength={MAX_LENGTH} onChange={(event) => setDraft(event.target.value)} placeholder="分享一个想法或问题…" rows={3} /><div className={styles.discussionComposerFooter}><span>{draft.length}/{MAX_LENGTH}</span><button className="primary-action" type="submit" disabled={!draft.trim() || busy}>{busy ? "发布中…" : "发布评论"}</button></div></div>
    </form>
    {loading ? <div className={styles.discussionState}><i className="fas fa-circle-notch fa-spin" /><strong>正在加载讨论…</strong></div> : error ? <div className={styles.discussionState}><i className="fas fa-circle-exclamation" /><strong>暂时无法加载讨论</strong><button type="button" className="secondary-action" onClick={() => void load()}>重试</button></div> : !comments.length ? <div className={styles.discussionState}><i className="fas fa-message" /><strong>还没有讨论</strong><span>成为第一个分享想法的人吧。</span></div> : <div className={styles.discussionList}>
      {comments.map((comment) => <article className={styles.discussionThread} key={comment.id}>
        <DiscussionItem comment={comment} canDelete={canDelete(comment)} onLike={() => void toggleLike(comment)} onDelete={() => void remove(comment.id)} onReply={() => { setReplyTarget(comment.id); setReplyDraft(""); }} />
        {replyTarget === comment.id && <form className={styles.discussionReplyComposer} onSubmit={(event) => void submitReply(event, comment.id)}><span className={styles.discussionAvatar}>{(user?.name || user?.username || "U").slice(0, 1).toUpperCase()}</span><div><textarea autoFocus value={replyDraft} maxLength={MAX_LENGTH} onChange={(event) => setReplyDraft(event.target.value)} placeholder="写下你的回复…" rows={2} /><div className={styles.discussionComposerFooter}><button type="button" className="secondary-action" onClick={() => setReplyTarget(null)}>取消</button><button type="submit" className="primary-action" disabled={!replyDraft.trim() || busy}>回复</button></div></div></form>}
        {comment.replies.length > 0 && <div className={styles.discussionReplies}>{comment.replies.map((reply) => <DiscussionItem key={reply.id} comment={reply} canDelete={canDelete(reply)} onLike={() => void toggleLike(reply)} onDelete={() => void remove(reply.id)} />)}</div>}
      </article>)}
    </div>}
  </div>;
}

function DiscussionItem({ comment, canDelete, onLike, onDelete, onReply }: { comment: DiscussionComment; canDelete: boolean; onLike: () => void; onDelete: () => void; onReply?: () => void }) {
  return <div className={styles.discussionItem}>
    {comment.author.avatar_url ? <img src={comment.author.avatar_url} alt="" className={styles.discussionAvatarImage} /> : <span className={styles.discussionAvatar}>{avatarLabel(comment)}</span>}
    <div className={styles.discussionItemBody}><div className={styles.discussionMeta}><strong>{displayName(comment)}</strong><span>@{comment.author.username}</span><time dateTime={comment.created_at}>{timeLabel(comment.created_at)}</time>{canDelete && <button type="button" className={styles.discussionDelete} onClick={onDelete} aria-label="删除评论"><i className="fas fa-trash" /></button>}</div><p>{comment.content}</p><div className={styles.discussionActions}>{onReply && <button type="button" onClick={onReply}><i className="far fa-comment" /> 回复{comment.reply_count ? ` ${comment.reply_count}` : ""}</button>}<button type="button" className={comment.liked_by_me ? styles.discussionLiked : ""} onClick={onLike}><i className={comment.liked_by_me ? "fas fa-heart" : "far fa-heart"} /> {comment.like_count || "喜欢"}</button></div></div>
  </div>;
}
