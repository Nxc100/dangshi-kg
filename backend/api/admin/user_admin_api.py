# -*- coding: utf-8 -*-
"""/api/admin/users*（admin）—— 全项目唯一从请求路径接收目标 user_id 的写接口族。"""
from flask import Blueprint, request

from backend.common.auth import admin_required, current_user
from backend.common.response import ok
from backend.common.validators import parse_page, require_json, validate_role, validate_status
from backend.services import user_admin_service

bp = Blueprint("admin_user_api", __name__)


@bp.get("/admin/users")
@admin_required
def list_users():
    page, size = parse_page()
    return ok(user_admin_service.list_users(request.args.get("kw", ""), page, size))


@bp.post("/admin/users/<int:user_id>/status")
@admin_required
def set_status(user_id):
    status = validate_status(require_json().get("status"))
    data = user_admin_service.set_status(current_user(), user_id, status)
    return ok(data, msg="已启用" if status == 1 else "已禁用")


@bp.post("/admin/users/<int:user_id>/reset-password")
@admin_required
def reset_password(user_id):
    """随机密码仅在本响应中返回一次，库中只存哈希。"""
    return ok(user_admin_service.reset_password(current_user(), user_id), msg="密码已重置")


@bp.post("/admin/users/<int:user_id>/role")
@admin_required
def set_role(user_id):
    role = validate_role(require_json().get("role"))
    data = user_admin_service.set_role(current_user(), user_id, role)
    return ok(data, msg="已设为管理员" if role == "admin" else "已取消管理员")
