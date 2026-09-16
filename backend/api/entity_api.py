# -*- coding: utf-8 -*-
"""GET /api/entity/<name>（游客可用；不存在返回 404，前端跳友好词条 404 页）。"""
from flask import Blueprint

from backend.common.auth import optional_user
from backend.common.response import ok
from backend.common.validators import validate_name
from backend.services import entity_service

bp = Blueprint("entity_api", __name__)


@bp.get("/entity/<path:name>")
def detail(name):
    user = optional_user()
    return ok(entity_service.detail(validate_name(name), user_id=user.id if user else None))
