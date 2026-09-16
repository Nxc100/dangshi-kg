# -*- coding: utf-8 -*-
"""GET /api/admin/oplog（admin，只读；op_log 只增不删，无 DELETE 接口——审计属性）。"""
from flask import Blueprint, request

from backend.common.auth import admin_required
from backend.common.errors import BadRequest
from backend.common.response import ok
from backend.common.validators import parse_page
from backend.services import kg_admin_service

bp = Blueprint("admin_oplog_api", __name__)

ACTIONS = ("add", "edit", "delete")


@bp.get("/admin/oplog")
@admin_required
def list_oplog():
    page, size = parse_page()
    action = request.args.get("action") or None
    if action and action not in ACTIONS:
        raise BadRequest("动作类型不合法", errors={"action": "action 只能为 add / edit / delete"})
    return ok(kg_admin_service.list_oplog(
        action, request.args.get("from"), request.args.get("to"), page, size))
