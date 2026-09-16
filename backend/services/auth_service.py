# -*- coding: utf-8 -*-
"""
注册 / 登录 / 内存锁定 / JWT 签发（开发规范 6.2）。

- 注册：用户名唯一，密码 werkzeug 加盐哈希，成功后自动登录（签发 JWT），默认昵称 = 用户名；
- 登录：错误统一提示"用户名或密码错误"（不区分具体项）；禁用 → "账号已被禁用，请联系管理员"；
- 锁定：连续 5 次密码错误锁定 10 分钟，内存字典 {username: (fail_count, lock_until)}，单进程、重启即清，成功登录清零。
"""
import threading
import time

from werkzeug.security import check_password_hash, generate_password_hash

from backend.common.auth import issue_token
from backend.common.errors import BadRequest, Unauthorized
from backend.config import Config
from backend.extensions import db_session
from backend.models import User

_lock = threading.Lock()
_fails = {}  # username -> (fail_count, lock_until_ts)


def _check_lock(username):
    with _lock:
        count, until = _fails.get(username, (0, 0))
        if until and time.time() < until:
            raise BadRequest("尝试次数过多，请稍后再试", data={"reason": "locked"})
        if until and time.time() >= until:
            _fails.pop(username, None)


def _record_fail(username):
    with _lock:
        count, _until = _fails.get(username, (0, 0))
        count += 1
        until = time.time() + Config.LOGIN_LOCK_SECONDS if count >= Config.LOGIN_MAX_FAIL else 0
        _fails[username] = (count, until)


def _clear_fail(username):
    with _lock:
        _fails.pop(username, None)


def username_available(username):
    """用户名唯一性预检（FR-G07：注册页失焦异步校验）。"""
    return db_session.query(User).filter_by(username=username).first() is None


def register(username, password, confirm_password):
    """注册并自动登录：密码加盐哈希入库，默认昵称 = 用户名，返回 {token, user}（FR-G07）。"""
    if password != confirm_password:
        raise BadRequest("两次输入的密码不一致", errors={"confirm_password": "两次输入的密码不一致"})
    if not username_available(username):
        raise BadRequest("该用户名已被占用", errors={"username": "该用户名已被占用"})
    user = User(
        username=username,
        pwd_hash=generate_password_hash(password),
        role="user",
        status=1,
        nickname=username,
        must_change_pwd=0,
    )
    db_session.add(user)
    db_session.commit()
    return {"token": issue_token(user), "user": user.to_dict()}


def login(username, password):
    """登录：错误统一提示「用户名或密码错误」；禁用账号单独提示；连续 5 次错误锁定 10 分钟（规范 6.2）。"""
    _check_lock(username)
    user = db_session.query(User).filter_by(username=username).first()
    if user is None or not check_password_hash(user.pwd_hash, password):
        _record_fail(username)
        raise Unauthorized("用户名或密码错误")
    if user.status != 1:
        raise Unauthorized("账号已被禁用，请联系管理员", data={"reason": "disabled"})
    _clear_fail(username)
    return {"token": issue_token(user), "user": user.to_dict()}
