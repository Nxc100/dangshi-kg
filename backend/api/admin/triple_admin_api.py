# -*- coding: utf-8 -*-
"""/api/admin/triple GET / POST / DELETE（admin）—— 头尾类型约束由 ontology 复校（不允许仅前端过滤）。"""
from flask import Blueprint, request

from backend.common.auth import admin_required, current_user
from backend.common.response import ok
from backend.common.validators import (parse_page, require_json, validate_label, validate_name,
                                       validate_relation)
from backend.services import kg_admin_service

bp = Blueprint("admin_triple_api", __name__)


def _triple_args(body):
    return (
        validate_name(body.get("head"), field="head"),
        validate_label(body.get("head_type"), field="head_type"),
        validate_relation(body.get("rel")),
        validate_name(body.get("tail"), field="tail"),
        validate_label(body.get("tail_type"), field="tail_type"),
    )


@bp.get("/admin/triple")
@admin_required
def list_triples():
    page, size = parse_page()
    rel = request.args.get("rel")
    if rel:
        validate_relation(rel)
    return ok(kg_admin_service.list_triples(
        request.args.get("head", ""), request.args.get("tail", ""), rel, page, size))


@bp.post("/admin/triple")
@admin_required
def create_triple():
    body = require_json()
    head, head_type, rel, tail, tail_type = _triple_args(body)
    data = kg_admin_service.create_triple(
        current_user().id, head, head_type, rel, tail, tail_type, body.get("props"))
    return ok(data, msg="已新增")


@bp.delete("/admin/triple")
@admin_required
def delete_triple():
    body = require_json()
    head, head_type, rel, tail, tail_type = _triple_args(body)
    data = kg_admin_service.delete_triple(current_user().id, head, head_type, rel, tail, tail_type)
    return ok(data, msg="已删除")
