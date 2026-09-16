# -*- coding: utf-8 -*-
"""GET /api/admin/overview —— 后台总览四数字卡。"""
from flask import Blueprint

from backend.common.auth import admin_required
from backend.common.response import ok
from backend.services import stats_service

bp = Blueprint("admin_overview_api", __name__)


@bp.get("/admin/overview")
@admin_required
def overview():
    return ok(stats_service.overview())
