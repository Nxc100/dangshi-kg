# -*- coding: utf-8 -*-
"""
提问历史（FR-U04，开发规范 6.8）：本人且 user_visible=1；删除 / 清空为逻辑删除（user_visible=0），
管理员日志与看板计数不受影响。
"""
from backend.common.errors import NotFound
from backend.common.response import page_data
from backend.extensions import db_session
from backend.models import QaLog

ANSWER_BRIEF = 40


def list_history(user_id, page, size):
    """提问历史：本人且 user_visible=1，倒序分页（FR-U04）。"""
    q = (db_session.query(QaLog)
         .filter(QaLog.user_id == user_id, QaLog.user_visible == 1)
         .order_by(QaLog.id.desc()))
    total = q.count()
    rows = q.offset((page - 1) * size).limit(size).all()
    items = []
    for r in rows:
        answer = r.answer or ""
        items.append({
            "id": r.id,
            "question": r.question,
            "answer_brief": answer[:ANSWER_BRIEF] + ("…" if len(answer) > ANSWER_BRIEF else ""),
            "fallback": r.fallback,
            "answer_source": r.answer_source,
            "created_at": r.to_dict()["created_at"],
        })
    return page_data(items, page, size, total)


def delete_one(user_id, log_id):
    """删除单条历史：逻辑删除并校验归属，管理员日志与统计计数不受影响（规范 6.8）。"""
    row = db_session.query(QaLog).filter(QaLog.id == log_id, QaLog.user_id == user_id).first()
    if row is None:
        raise NotFound("记录不存在")
    row.user_visible = 0
    db_session.commit()
    return True


def clear_all(user_id):
    """清空本人历史：同为逻辑删除，返回受影响条数（FR-U04）。"""
    count = (db_session.query(QaLog)
             .filter(QaLog.user_id == user_id, QaLog.user_visible == 1)
             .update({QaLog.user_visible: 0}, synchronize_session=False))
    db_session.commit()
    return count
