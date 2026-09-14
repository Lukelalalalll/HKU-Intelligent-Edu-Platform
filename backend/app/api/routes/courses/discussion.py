from .common import *  # noqa: F401,F403

@router.get("/{course_id}/discussion", response_model=list[DiscussionCommentOut])
def list_discussion(course_id: str, user: User = Depends(current_user), db: Session = Depends(get_db)):
    _course_for_user(course_id, user, db)
    comments = db.scalars(
        select(DiscussionComment)
        .where(DiscussionComment.course_id == course_id, DiscussionComment.parent_id.is_(None))
        .options(
            selectinload(DiscussionComment.author),
            selectinload(DiscussionComment.likes),
            selectinload(DiscussionComment.replies).selectinload(DiscussionComment.author),
            selectinload(DiscussionComment.replies).selectinload(DiscussionComment.likes),
        )
    ).all()
    comments.sort(key=lambda item: (_discussion_activity(item), item.id), reverse=True)
    return [_discussion_comment_out(comment, user.id) for comment in comments]


@router.post("/{course_id}/discussion", response_model=DiscussionCommentOut, status_code=201)
def create_discussion_comment(course_id: str, payload: DiscussionCommentCreate, user: User = Depends(current_user), db: Session = Depends(get_db)):
    _course_for_user(course_id, user, db)
    comment = DiscussionComment(course_id=course_id, author_id=user.id, content=payload.content)
    db.add(comment)
    db.commit()
    db.refresh(comment)
    comment.author = user
    return _discussion_comment_out(comment, user.id)


@router.post("/{course_id}/discussion/{comment_id}/replies", response_model=DiscussionCommentOut, status_code=201)
def create_discussion_reply(course_id: str, comment_id: str, payload: DiscussionCommentCreate, user: User = Depends(current_user), db: Session = Depends(get_db)):
    _course_for_user(course_id, user, db)
    parent = _discussion_comment_or_404(course_id, comment_id, db)
    if parent.parent_id is not None:
        raise HTTPException(400, "Replies can only target top-level comments")
    reply = DiscussionComment(course_id=course_id, author_id=user.id, parent_id=parent.id, content=payload.content)
    db.add(reply)
    db.commit()
    db.refresh(reply)
    reply.author = user
    return _discussion_comment_out(reply, user.id)


@router.put("/{course_id}/discussion/{comment_id}/like", response_model=DiscussionLikeOut)
def like_discussion_comment(course_id: str, comment_id: str, user: User = Depends(current_user), db: Session = Depends(get_db)):
    _course_for_user(course_id, user, db)
    comment = _discussion_comment_or_404(course_id, comment_id, db)
    like = db.scalar(select(DiscussionLike).where(DiscussionLike.comment_id == comment.id, DiscussionLike.user_id == user.id))
    if not like:
        db.add(DiscussionLike(comment_id=comment.id, user_id=user.id))
        db.commit()
    count = db.scalar(select(func.count(DiscussionLike.id)).where(DiscussionLike.comment_id == comment.id)) or 0
    return DiscussionLikeOut(liked=True, like_count=count)


@router.delete("/{course_id}/discussion/{comment_id}/like", response_model=DiscussionLikeOut)
def unlike_discussion_comment(course_id: str, comment_id: str, user: User = Depends(current_user), db: Session = Depends(get_db)):
    _course_for_user(course_id, user, db)
    comment = _discussion_comment_or_404(course_id, comment_id, db)
    like = db.scalar(select(DiscussionLike).where(DiscussionLike.comment_id == comment.id, DiscussionLike.user_id == user.id))
    if like:
        db.delete(like)
        db.commit()
    count = db.scalar(select(func.count(DiscussionLike.id)).where(DiscussionLike.comment_id == comment.id)) or 0
    return DiscussionLikeOut(liked=False, like_count=count)


@router.delete("/{course_id}/discussion/{comment_id}", status_code=204)
def delete_discussion_comment(course_id: str, comment_id: str, user: User = Depends(current_user), db: Session = Depends(get_db)):
    course = _course_for_user(course_id, user, db)
    comment = _discussion_comment_or_404(course_id, comment_id, db)
    if comment.author_id != user.id and user.role not in {UserRole.admin} and course.teacher_id != user.id:
        raise HTTPException(403, "You cannot delete this comment")
    db.delete(comment)
    db.commit()


