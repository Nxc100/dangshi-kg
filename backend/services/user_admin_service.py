# -*- coding: utf-8 -*-
"""
后台用户管理（FR-A05，开发规范 6.1）——全项目唯一从请求路径接收目标 user_id 的写接口族，
集中隔离于此，不污染 user_service"操作对象一律是当前登录人"的契约。

每个写方法服务端重载目标用户并逐条校验：
  目标存在（404）→ 不能操作当前登录账号（422，前端按钮同步置灰）→ 取消管理员时系统至少保留 1 个 admin（422）
重置密码：secrets 生成 8 位含字母数字随机密码，仅在响应中返回一次，库中只存哈希，置 must_change_pwd=1。
角色授予不进 op_log（op_log 仅记知识操作），以应用日志留痕。
"""
import logging
import secrets
import string

from sqlalchemy import func, or_
from werkzeug.security import generate_password_hash

from backend.common.errors import BadRequest, NotFound
from backend.common.response import page_data
from backend.extensions import db_session
from backend.models import User

log = logging.getLogger(__name__)


def _target(user_id, current_user):
    user = db_session.get(User, int(user_id))
    if user is None:
        raise NotFound("用户不存在")
    if current_user is not None and user.id == current_user.id:
        raise BadRequest("不能对当前登录账号执行该操作")
    return user


def _random_password(length=8):
    alphabet = string.ascii_letters + string.digits
    while True:
        pwd = "".join(secrets.choice(alphabet) for _ in range(length))
        if any(c.isalpha() for c in pwd) and any(c.isdigit() for c in pwd):
            return pwd


def list_users(kw="", page=1, size=10):
    """用户列表，支持用户名 / 昵称关键词检索（FR-A05）。"""
    q = db_session.query(User)
    if kw:
        like = "%%%s%%" % kw
        q = q.filter(or_(User.username.like(like), User.nickname.like(like)))
    q = q.order_by(User.id.asc())
    total = q.count()
    rows = q.offset((page - 1) * size).limit(size).all()
    return page_data([r.to_dict() for r in rows], page, size, total)


def set_status(current_user, user_id, status):
    """禁用 / 启用：禁用后该用户下一次请求即被拒，无需等 token 过期（规范 6.2）。"""
    user = _target(user_id, current_user)
    user.status = int(status)
    db_session.commit()
    log.info("管理员 %s 将用户 %s 状态改为 %s", current_user.username, user.username, status)
    return user.to_dict()


def reset_password(current_user, user_id):
    """随机密码仅返回一次（前端 ElNotification 显示并提示复制），关闭后不可再查。"""
    user = _target(user_id, current_user)
    password = _random_password()
    user.pwd_hash = generate_password_hash(password)
    user.must_change_pwd = 1
    db_session.commit()
    log.info("管理员 %s 重置了用户 %s 的密码", current_user.username, user.username)
    return {"user": user.to_dict(), "password": password}


def set_role(current_user, user_id, role):
    """授予 / 取消管理员：不能改自己，且系统至少保留 1 个 admin（规范 6.1）。"""
    user = _target(user_id, current_user)
    if user.role == "admin" and role == "user":
        admin_count = db_session.query(func.count(User.id)).filter(User.role == "admin").scalar() or 0
        if admin_count <= 1:
            raise BadRequest("系统至少保留 1 个管理员")
    user.role = role
    db_session.commit()
    log.info("管理员 %s 将用户 %s 角色改为 %s", current_user.username, user.username, role)
    return user.to_dict()
