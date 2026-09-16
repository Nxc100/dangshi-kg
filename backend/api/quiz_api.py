# -*- coding: utf-8 -*-
"""GET /api/quiz（游客可试做）；POST /api/quiz/submit、GET /api/quiz/records[/<id>]（需登录）。"""
from flask import Blueprint, request

from backend.common.auth import current_user, login_required
from backend.common.response import ok
from backend.common.validators import parse_entities, parse_page, require_json, validate_quiz_n
from backend.services import quiz_service

bp = Blueprint("quiz_api", __name__)


@bp.get("/quiz")
def get_quiz():
    n = validate_quiz_n(request.args.get("n"))
    entities = parse_entities(request.args.get("entities"))
    return ok(quiz_service.generate(n, entities))


@bp.post("/quiz/submit")
@login_required
def submit():
    body = require_json()
    data = quiz_service.submit(
        current_user().id, body.get("questions"), body.get("answers"), body.get("duration_sec", 0))
    return ok(data, msg="成绩已保存")


@bp.get("/quiz/records")
@login_required
def records():
    page, size = parse_page()
    return ok(quiz_service.list_records(current_user().id, page, size))


@bp.get("/quiz/records/<int:record_id>")
@login_required
def record_detail(record_id):
    return ok(quiz_service.record_detail(current_user().id, record_id))
