# -*- coding: utf-8 -*-
"""GET /api/admin/logs、/logs/export（admin）—— 导出与当前筛选条件一致，utf-8-sig CSV。"""
from flask import Blueprint, Response, request

from backend.common.auth import admin_required
from backend.common.errors import BadRequest
from backend.common.response import ok
from backend.common.validators import parse_page
from backend.services import qalog_service

bp = Blueprint("admin_qalog_api", __name__)

SOURCES = ("kg", "passage", "llm")


def _filters():
    fallback = request.args.get("fallback")
    if fallback not in (None, "", "0", "1"):
        raise BadRequest("兜底筛选值不合法", errors={"fallback": "fallback 只能为 0 或 1"})
    source = request.args.get("source") or None
    if source and source not in SOURCES:
        raise BadRequest("回答来源不合法", errors={"source": "source 只能为 kg / passage / llm"})
    return {
        "fallback": int(fallback) if fallback in ("0", "1") else None,
        "source": source,
        "date_from": request.args.get("from") or None,
        "date_to": request.args.get("to") or None,
        "kw": (request.args.get("kw") or "").strip() or None,
    }


@bp.get("/admin/logs")
@admin_required
def list_logs():
    page, size = parse_page()
    return ok(qalog_service.list_logs(page, size, **_filters()))


@bp.get("/admin/logs/export")
@admin_required
def export_logs():
    content = qalog_service.export_csv(**_filters())
    return Response(content, mimetype="text/csv; charset=utf-8", headers={
        "Content-Disposition": "attachment; filename=qa_logs.csv",
        "Content-Length": str(len(content)),
    })
