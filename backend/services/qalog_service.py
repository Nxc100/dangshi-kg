# -*- coding: utf-8 -*-
"""
qa_log 落库 / 查询 / CSV 导出（开发规范 6.8）——问答日志、提问历史、热点统计、LLM 审计的唯一数据源。

- 每次问答必写（游客 user_id 为空）；写入失败单独捕获并 logging，不影响答案返回；
- 后台日志与统计不看 user_visible；导出 utf-8-sig CSV，与当前筛选条件一致。
"""
import csv
import io
import json
import logging
from datetime import datetime, timedelta

from sqlalchemy import or_

from backend.common.errors import BadRequest
from backend.common.response import page_data
from backend.extensions import db_session
from backend.models import QaLog, User

log = logging.getLogger(__name__)

EXPORT_HEADER = ["时间", "用户", "问句", "意图", "命中实体", "是否兜底", "回答来源", "LLM时延(ms)", "答案"]
PASSAGE_BRIEF = 60  # 兜底记录落库时保留的段落摘要长度


def day_start(day, plus_days=0):
    """'YYYY-MM-DD' → 当日零点的 datetime（plus_days 用于取次日零点，作右开区间上界）。"""
    try:
        return datetime.strptime(str(day), "%Y-%m-%d") + timedelta(days=plus_days)
    except (TypeError, ValueError):
        raise BadRequest("日期格式不正确", errors={"date": "日期格式应为 YYYY-MM-DD"})


def _answer_for_log(resp):
    """
    面向用户的答案文本（供提问历史摘要与日志关键词检索）。
    兜底命中段落时 answer_text 为空，改存首段摘要并标注来源，避免历史与检索出现空白记录。
    """
    llm_text = (resp.get("llm") or {}).get("text")
    if llm_text:
        return llm_text
    if resp.get("answer_text"):
        return resp["answer_text"]
    passages = resp.get("fallback_passages") or []
    if passages:
        head = passages[0]
        return "【权威资料原文节选】%s%s" % (
            head["text"][:PASSAGE_BRIEF],
            "（出处：%s）" % head["chapter"] if head.get("chapter") else "")
    return ""


def write_log(question, resp, meta, user_id=None):
    """
    写入 qa_log 并返回 log_id；写入失败记录 ERROR 并返回 None，不影响答案返回（规范 6.3）。
    matched_entity 取第③步实体链接结果（_meta.linked_entities），不含溯源子图邻居。
    """
    try:
        linked = (meta or {}).get("linked_entities") or []
        row = QaLog(
            user_id=user_id,
            question=question,
            intent=resp.get("intent"),
            matched_entity="|".join(linked) or None,
            answer=_answer_for_log(resp),
            fallback=1 if resp.get("fallback") else 0,
            answer_source=resp.get("answer_source") or "kg",
            llm_latency_ms=(meta or {}).get("llm_latency_ms"),
            llm_detail=json.dumps((meta or {}).get("llm_detail"), ensure_ascii=False)
            if (meta or {}).get("llm_detail") else None,
            user_visible=1,
        )
        db_session.add(row)
        db_session.commit()
        return row.id
    except Exception as exc:  # noqa: BLE001 —— 落库失败不得影响答案返回
        log.error("qa_log 落库失败：%s", exc)
        db_session.rollback()
        return None


def _filtered_query(fallback=None, source=None, date_from=None, date_to=None, kw=None):
    """按筛选条件构造查询；日志与统计不看 user_visible（规范 6.8）。"""
    q = db_session.query(QaLog, User.username).outerjoin(User, QaLog.user_id == User.id)
    if fallback in (0, 1):
        q = q.filter(QaLog.fallback == fallback)
    if source:
        q = q.filter(QaLog.answer_source == source)
    if date_from:
        q = q.filter(QaLog.created_at >= day_start(date_from))
    if date_to:
        # 用「次日零点之前」而非「当日 23:59:59」，避免带微秒的记录被漏掉
        q = q.filter(QaLog.created_at < day_start(date_to, plus_days=1))
    if kw:
        like = "%%%s%%" % kw
        q = q.filter(or_(QaLog.question.like(like), QaLog.answer.like(like)))
    return q.order_by(QaLog.id.desc())


def _row_dict(row, username):
    data = row.to_dict()
    data["user_name"] = username or "游客"
    data["llm_detail"] = row.llm_detail
    return data


def list_logs(page, size, **filters):
    """问答日志分页：游客用户列显示「游客」，llm 来源记录附 llm_detail 供展开审计（FR-A06 / FR-L04）。"""
    q = _filtered_query(**filters)
    total = q.count()
    rows = q.offset((page - 1) * size).limit(size).all()
    return page_data([_row_dict(r, u) for r, u in rows], page, size, total)


def export_csv(**filters):
    """utf-8-sig 编码，Excel 直接打开无乱码；行数与筛选一致。"""
    buf = io.StringIO(newline="")
    writer = csv.writer(buf)
    writer.writerow(EXPORT_HEADER)
    for row, username in _filtered_query(**filters).all():
        writer.writerow([
            row.to_dict()["created_at"], username or "游客", row.question, row.intent or "",
            row.matched_entity or "", "是" if row.fallback else "否", row.answer_source,
            row.llm_latency_ms if row.llm_latency_ms is not None else "", row.answer or "",
        ])
    return buf.getvalue().encode("utf-8-sig")
