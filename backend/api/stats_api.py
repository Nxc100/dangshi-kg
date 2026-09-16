# -*- coding: utf-8 -*-
"""
GET /api/stats/overview —— 热点统计看板。
该路径不在 /api/admin 前缀下（FRS 7.12 定稿路径），故必须显式加 @admin_required，禁止只靠前缀判断。
"""
from flask import Blueprint

from backend.common.auth import admin_required
from backend.common.response import ok
from backend.services import stats_service

bp = Blueprint("stats_api", __name__)


@bp.get("/stats/overview")
@admin_required
def overview():
    return ok(stats_service.dashboard())
