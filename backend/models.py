# -*- coding: utf-8 -*-
"""
SQLite 五表（唯一可信结构来源）：user / favorite / qa_log / quiz_record / op_log。
对应 V3 7.5 + FRS 1.4（nickname / avatar_path / op_log）+ LLM-Design 4.6（answer_source / llm_latency_ms）
+ 开发规范决策 ①（llm_detail）②（must_change_pwd）。

时间字段统一 yyyy-MM-dd HH:mm:ss（to_dict 输出）。
"""
import os
from datetime import datetime

from sqlalchemy import Column, DateTime, ForeignKey, Integer, String, Text, UniqueConstraint

from backend.config import BACKEND_DIR, Config
from backend.extensions import Base

TIME_FMT = "%Y-%m-%d %H:%M:%S"


def now():
    return datetime.now().replace(microsecond=0)


def fmt_time(dt):
    return dt.strftime(TIME_FMT) if dt else None


class User(Base):
    __tablename__ = "user"

    id = Column(Integer, primary_key=True, autoincrement=True)
    username = Column(String(20), nullable=False, unique=True, index=True)
    pwd_hash = Column(String(255), nullable=False)  # werkzeug 加盐哈希，绝不存明文
    role = Column(String(10), nullable=False, default="user")  # user / admin
    status = Column(Integer, nullable=False, default=1)  # 1 启用 / 0 禁用
    nickname = Column(String(32), nullable=False, default="")  # 默认 = 用户名
    avatar_path = Column(String(255), nullable=True)  # static/avatars/{user_id}.jpg
    must_change_pwd = Column(Integer, nullable=False, default=0)  # 1：首登 admin / 被重置密码用户
    created_at = Column(DateTime, nullable=False, default=now)

    def avatar_url(self):
        """头像 URL；已上传者附文件修改时间参数破缓存，未上传返回系统默认头像。"""
        if self.avatar_path:
            rel = self.avatar_path.replace("\\", "/").lstrip("/")
            full = os.path.join(BACKEND_DIR, *rel.split("/"))
            stamp = int(os.path.getmtime(full)) if os.path.exists(full) else 0
            return "/%s?t=%d" % (rel, stamp)
        return Config.DEFAULT_AVATAR_URL

    def to_dict(self):
        return {
            "user_id": self.id,
            "username": self.username,
            "role": self.role,
            "status": self.status,
            "nickname": self.nickname,
            "avatar_url": self.avatar_url(),
            "must_change_pwd": self.must_change_pwd,
            "created_at": fmt_time(self.created_at),
        }


class Favorite(Base):
    __tablename__ = "favorite"
    __table_args__ = (UniqueConstraint("user_id", "fav_type", "ref_id", name="uq_favorite_user_type_ref"),)

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("user.id", ondelete="CASCADE"), nullable=False, index=True)
    fav_type = Column(String(10), nullable=False)  # entity / qa
    ref_id = Column(String(255), nullable=False)  # entity：实体主名；qa：qa_log.id
    created_at = Column(DateTime, nullable=False, default=now)

    def to_dict(self):
        return {
            "id": self.id,
            "fav_type": self.fav_type,
            "ref_id": self.ref_id,
            "created_at": fmt_time(self.created_at),
        }


class QaLog(Base):
    __tablename__ = "qa_log"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("user.id", ondelete="SET NULL"), nullable=True, index=True)  # 游客为空
    question = Column(Text, nullable=False)
    intent = Column(String(16), nullable=True)  # I1–I15 / UNKNOWN
    matched_entity = Column(String(255), nullable=True)  # 多实体以 | 分隔
    answer = Column(Text, nullable=True)
    fallback = Column(Integer, nullable=False, default=0)  # 0 / 1
    answer_source = Column(String(10), nullable=False, default="kg")  # kg / passage / llm
    llm_latency_ms = Column(Integer, nullable=True)  # 含失败尝试耗时；未尝试为 NULL
    llm_detail = Column(Text, nullable=True)  # JSON：{text, cited, passages, check_passed, degraded_reason}
    user_visible = Column(Integer, nullable=False, default=1)  # 提问历史逻辑删除标记（统计不受影响）
    created_at = Column(DateTime, nullable=False, default=now, index=True)

    def to_dict(self):
        return {
            "id": self.id,
            "user_id": self.user_id,
            "question": self.question,
            "intent": self.intent,
            "matched_entity": self.matched_entity,
            "answer": self.answer,
            "fallback": self.fallback,
            "answer_source": self.answer_source,
            "llm_latency_ms": self.llm_latency_ms,
            "created_at": fmt_time(self.created_at),
        }


class QuizRecord(Base):
    __tablename__ = "quiz_record"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("user.id", ondelete="CASCADE"), nullable=False, index=True)
    score = Column(Integer, nullable=False)  # 后端复算
    total = Column(Integer, nullable=False)
    detail_json = Column(Text, nullable=False)  # 逐题 {question, options, answer_key, chosen, correct, entity, template} + duration_sec
    created_at = Column(DateTime, nullable=False, default=now)

    def to_dict(self):
        return {
            "id": self.id,
            "score": self.score,
            "total": self.total,
            "created_at": fmt_time(self.created_at),
        }


class OpLog(Base):
    __tablename__ = "op_log"

    id = Column(Integer, primary_key=True, autoincrement=True)
    admin_id = Column(Integer, ForeignKey("user.id", ondelete="SET NULL"), nullable=True, index=True)
    action = Column(String(10), nullable=False)  # add / edit / delete
    object_type = Column(String(10), nullable=False)  # entity / triple
    object_label = Column(String(32), nullable=True)  # 实体标签 或 关系类型
    object_name = Column(String(255), nullable=False)  # 实体名 或 "head → tail"
    summary = Column(Text, nullable=True)  # 变更摘要 JSON
    created_at = Column(DateTime, nullable=False, default=now, index=True)

    def to_dict(self):
        return {
            "id": self.id,
            "admin_id": self.admin_id,
            "action": self.action,
            "object_type": self.object_type,
            "object_label": self.object_label,
            "object_name": self.object_name,
            "summary": self.summary,
            "created_at": fmt_time(self.created_at),
        }


# ---------------------------------------------------------------------------
# 修改记录（表结构变更须同步 FRS 1.4 / V3 7.5 / LLM-Design 4.6）
# ---------------------------------------------------------------------------
# 2026-09-07  初版五表。user 含 nickname / avatar_path（FRS 1.4）与 must_change_pwd（规范决策②）；
#             qa_log 含 answer_source / llm_latency_ms（LLM-Design 4.6）、llm_detail（规范决策①）、
#             user_visible（FR-U04 逻辑删除）；favorite 唯一索引 (user_id, fav_type, ref_id) 保证幂等；
#             op_log 只增不删（无删除接口）。
