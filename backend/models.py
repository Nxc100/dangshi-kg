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


class LlmConfig(Base):
    """
    AI 增强模块的系统层配置（LLM-Design 2.1 系统层开关 / 4.2 配置项）。

    **单行表**：固定 id=1，由 `llm_admin_service` 读写，后台「AI 增强」页维护。
    原方案把这五项放在 `.env`（需改文件 + 重启），改为落库后管理员可在线切换厂商与模型、
    即时生效；`.env` 仍作为首次启动的默认值，二者关系见 `llm_admin_service.current()`。

    api_key 以明文存储：与 `.env` 的存储强度一致（app.db 同样不入 Git），
    但**任何接口一律只回显掩码**（见 to_dict），满足 LLM-Design 5.1「后台与任何接口不回显」。
    """

    __tablename__ = "llm_config"

    id = Column(Integer, primary_key=True, autoincrement=True)
    enabled = Column(Integer, nullable=False, default=0)  # 系统层开关 0/1
    provider = Column(String(32), nullable=False, default="")  # llm_providers.PROVIDER_IDS
    base_url = Column(String(255), nullable=False, default="")  # OpenAI 兼容端点
    api_key = Column(String(255), nullable=False, default="")  # 不回显明文
    model = Column(String(64), nullable=False, default="")
    timeout = Column(Integer, nullable=False, default=5)  # 秒；改写调用取 min(3, timeout)
    updated_by = Column(Integer, ForeignKey("user.id", ondelete="SET NULL"), nullable=True)
    updated_at = Column(DateTime, nullable=False, default=now)

    def masked_key(self):
        """掩码：保留前 6 位与后 4 位，中间以 * 代替；过短则全掩。"""
        key = self.api_key or ""
        if not key:
            return ""
        if len(key) <= 12:
            return "*" * len(key)
        return "%s%s%s" % (key[:6], "*" * 8, key[-4:])

    def to_dict(self):
        """对外结构：只给掩码 key 与「是否已配置」标记，绝不下发明文。"""
        return {
            "enabled": self.enabled,
            "provider": self.provider,
            "base_url": self.base_url,
            "model": self.model,
            "timeout": self.timeout,
            "api_key_masked": self.masked_key(),
            "has_key": bool(self.api_key),
            "updated_by": self.updated_by,
            "updated_at": fmt_time(self.updated_at),
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
# 2026-09-17  新增第 6 张表 llm_config（单行，id=1），承载 AI 增强模块的系统层配置
#             （enabled / provider / base_url / api_key / model / timeout）。
#             原 LLM-Design 4.2 把这五项放在 .env，需改文件并重启；改为落库后管理员可在后台
#             在线切换厂商与模型、即时生效，.env 退化为首次启动的默认值（llm_admin_service.current()）。
#             api_key 明文存储，与 .env 同等强度（app.db 不入 Git），但接口一律只回显掩码。
#             迁移：新表由 init_db.create_all() 自动创建，旧库直接跑 python -m backend.init_db 即可，
#             不触碰既有五表的任何列。已同步 FRS 1.4 / LLM-Design 4.2、4.6。
# 2026-09-07  初版五表。user 含 nickname / avatar_path（FRS 1.4）与 must_change_pwd（规范决策②）；
#             qa_log 含 answer_source / llm_latency_ms（LLM-Design 4.6）、llm_detail（规范决策①）、
#             user_visible（FR-U04 逻辑删除）；favorite 唯一索引 (user_id, fav_type, ref_id) 保证幂等；
#             op_log 只增不删（无删除接口）。
