# -*- coding: utf-8 -*-
"""
/api/user/*（需登录）：资料 / 头像 / 改密 / 提问历史 / 收藏夹。
所有个人数据接口后端强制以 JWT user_id 过滤，禁止前端传 user_id 决定数据范围。
"""
from flask import Blueprint, request

from backend.common.auth import current_user, login_required
from backend.common.errors import BadRequest
from backend.common.response import ok
from backend.common.validators import (parse_page, require_json, validate_nickname, validate_password)
from backend.services import favorite_service, history_service, user_service

bp = Blueprint("user_api", __name__)


# ---- 资料 ----
@bp.get("/user/profile")
@login_required
def get_profile():
    return ok(user_service.profile(current_user()))


@bp.put("/user/profile")
@login_required
def update_profile():
    body = require_json()
    nickname = validate_nickname(body.get("nickname"))
    return ok(user_service.update_nickname(current_user(), nickname), msg="已保存")


@bp.post("/user/avatar")
@login_required
def upload_avatar():
    file = request.files.get("file")
    return ok(user_service.save_avatar(current_user(), file), msg="头像已更新")


@bp.put("/user/password")
@login_required
def change_password():
    body = require_json()
    old_password = body.get("old_password") or ""
    if not old_password:
        raise BadRequest("请输入原密码", errors={"old_password": "请输入原密码"})
    new_password = validate_password(body.get("new_password"), field="new_password")
    user_service.change_password(current_user(), old_password, new_password, body.get("confirm_password"))
    return ok(None, msg="密码已修改，请重新登录")


# ---- 提问历史 ----
@bp.get("/user/history")
@login_required
def history():
    page, size = parse_page()
    return ok(history_service.list_history(current_user().id, page, size))


@bp.delete("/user/history/<int:log_id>")
@login_required
def delete_history(log_id):
    history_service.delete_one(current_user().id, log_id)
    return ok(None, msg="已删除")


@bp.delete("/user/history")
@login_required
def clear_history():
    return ok({"cleared": history_service.clear_all(current_user().id)}, msg="已清空")


# ---- 收藏夹 ----
@bp.get("/user/favorite")
@login_required
def list_favorite():
    page, size = parse_page()
    fav_type = request.args.get("fav_type") or "entity"
    return ok(favorite_service.list_favorites(current_user().id, fav_type, page, size))


@bp.post("/user/favorite")
@login_required
def add_favorite():
    body = require_json()
    data = favorite_service.add(current_user().id, body.get("fav_type"), body.get("ref_id"))
    return ok(data, msg="已收藏")


@bp.delete("/user/favorite")
@login_required
def remove_favorite():
    body = require_json()
    favorite_service.remove(current_user().id, body.get("fav_type"), body.get("ref_id"))
    return ok(None, msg="已取消收藏")
