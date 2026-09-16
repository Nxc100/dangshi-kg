# -*- coding: utf-8 -*-
"""
JWT RBAC（开发规范 6.1）：login_required / admin_required 装饰器 + token 签发 + JWT 错误回调。

- 每次请求重载用户并校验 status=1（禁用后下一次请求即被拒，无需等 token 过期）。
- must_change_pwd=1 时仅放行改密相关端点，其余返回 422 "请先修改密码"（前端守卫 + 后端双重拦截）。
- 个人数据接口一律以 JWT user_id 为准，禁止前端传 user_id 决定数据范围。
"""
from functools import wraps

from flask import g, request
from flask_jwt_extended import create_access_token, get_jwt_identity, verify_jwt_in_request

from backend.common.errors import BadRequest, Forbidden, Unauthorized
from backend.common.response import fail
from backend.extensions import db_session

# must_change_pwd=1 时仍允许访问的端点（蓝图名.函数名）。
# 只需列出带 @login_required / @admin_required 的端点：游客可用接口不经过本校验。
MUST_CHANGE_PWD_ALLOWED = {
    "user_api.get_profile",     # 改密页需要读取本人资料
    "user_api.change_password",  # 改密本身
}


def _load_current_user():
    from backend.models import User

    verify_jwt_in_request()
    identity = get_jwt_identity()
    try:
        user = db_session.get(User, int(identity))
    except (TypeError, ValueError):
        user = None
    if user is None:
        raise Unauthorized("登录已过期，请重新登录")
    if user.status != 1:
        raise Unauthorized("账号已被禁用，请联系管理员", data={"reason": "disabled"})
    if user.must_change_pwd and request.endpoint not in MUST_CHANGE_PWD_ALLOWED:
        raise BadRequest("请先修改密码", data={"reason": "must_change_pwd"})
    g.current_user = user
    return user


def login_required(fn):
    @wraps(fn)
    def wrapper(*args, **kwargs):
        _load_current_user()
        return fn(*args, **kwargs)

    return wrapper


def admin_required(fn):
    """显式 admin 校验；/api/stats/overview 不在 /api/admin 前缀下也必须使用本装饰器。"""

    @wraps(fn)
    def wrapper(*args, **kwargs):
        user = _load_current_user()
        if user.role != "admin":
            raise Forbidden("无权限访问")
        return fn(*args, **kwargs)

    return wrapper


def current_user():
    return getattr(g, "current_user", None)


def optional_user():
    """游客可用接口中尝试解析 token；无 token / token 无效一律按游客处理，不抛错。"""
    from backend.models import User

    try:
        verify_jwt_in_request(optional=True)
        identity = get_jwt_identity()
        if identity is None:
            return None
        user = db_session.get(User, int(identity))
        if user is None or user.status != 1:
            return None
        g.current_user = user
        return user
    except Exception:  # noqa: BLE001 —— 游客接口容错
        return None


def issue_token(user):
    """签发 JWT：identity=user_id（字符串），附加 role / nickname / avatar 供登录即时渲染。"""
    return create_access_token(
        identity=str(user.id),
        additional_claims={"role": user.role, "nickname": user.nickname, "avatar": user.avatar_url()},
    )


def init_jwt_handlers(jwt):
    """flask-jwt-extended 的三类失败统一 401 返回体。"""

    @jwt.unauthorized_loader
    def _missing(_reason):
        return fail(401, "未登录，请先登录")

    @jwt.invalid_token_loader
    def _invalid(_reason):
        return fail(401, "登录状态无效，请重新登录")

    @jwt.expired_token_loader
    def _expired(_header, _payload):
        return fail(401, "登录已过期，请重新登录")
