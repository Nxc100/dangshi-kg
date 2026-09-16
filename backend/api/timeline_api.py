# -*- coding: utf-8 -*-
"""GET /api/timeline?period=（游客可用；无参返回时期列表 + 首个时期事件）。"""
from flask import Blueprint, request

from backend.common.response import ok
from backend.common.validators import validate_period
from backend.services import timeline_service

bp = Blueprint("timeline_api", __name__)


@bp.get("/timeline")
def timeline():
    period = validate_period(request.args.get("period"))
    return ok(timeline_service.timeline(period))
