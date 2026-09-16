# -*- coding: utf-8 -*-
"""POST /api/auth/register | /login；GET /api/auth/check?username=。"""
from flask import Blueprint, request

from backend.common.response import ok
from backend.common.validators import require_json, validate_password, validate_username
from backend.services import auth_service

bp = Blueprint("auth_api", __name__)


@bp.post("/auth/register")
def register():
    body = require_json()
    username = validate_username(body.get("username"))
    password = validate_password(body.get("password"))
    data = auth_service.register(username, password, body.get("confirm_password"))
    return ok(data, msg="注册成功")


@bp.post("/auth/login")
def login():
    body = require_json()
    username = (body.get("username") or "").strip()
    password = body.get("password") or ""
    if not username or not password:
        from backend.common.errors import BadRequest
        raise BadRequest("请输入用户名与密码")
    return ok(auth_service.login(username, password), msg="登录成功")


@bp.get("/auth/check")
def check_username():
    username = (request.args.get("username") or "").strip()
    return ok({"available": bool(username) and auth_service.username_available(username)})
