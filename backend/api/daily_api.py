# -*- coding: utf-8 -*-
"""GET /api/daily（游客可用）：今日推荐 + 历史上的今天。"""
from flask import Blueprint

from backend.common.response import ok
from backend.services import daily_service

bp = Blueprint("daily_api", __name__)


@bp.get("/daily")
def daily():
    return ok(daily_service.daily())
