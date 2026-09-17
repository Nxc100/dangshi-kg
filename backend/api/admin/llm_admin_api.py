# -*- coding: utf-8 -*-
"""
AI 增强模块配置管理（FR-L06，admin 专属）。

GET  /api/admin/llm        读配置（api_key 只回显掩码）+ 当前生效快照 + 厂商预设
PUT  /api/admin/llm        保存配置并即时生效（api_key 留空表示不修改）
POST /api/admin/llm/test   按表单值测试连通性，不落库、不改运行时

蓝图层只做鉴权与入参透传，配置读写与外呼一律在 llm_admin_service（规范 6.7「蓝图层不得出现业务实现」）。
"""
from flask import Blueprint

from backend.common.auth import admin_required, current_user
from backend.common.response import ok
from backend.common.validators import require_json
from backend.services import llm_admin_service

bp = Blueprint("llm_admin_api", __name__)


@bp.get("/admin/llm")
@admin_required
def get_llm_config():
    return ok(llm_admin_service.current())


@bp.put("/admin/llm")
@admin_required
def save_llm_config():
    body = require_json()
    return ok(llm_admin_service.save(body, current_user().id))


@bp.post("/admin/llm/test")
@admin_required
def test_llm_config():
    body = require_json()
    return ok(llm_admin_service.test_connection(body))
