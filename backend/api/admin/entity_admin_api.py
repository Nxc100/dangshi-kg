# -*- coding: utf-8 -*-
"""/api/admin/entity GET / POST / PUT / DELETE（admin）—— 蓝图层只做入参校验与鉴权，Cypher 全在 kg_admin_service。"""
from flask import Blueprint, request

from backend.common.auth import admin_required, current_user
from backend.common.response import ok
from backend.common.validators import (parse_page, require_json, validate_checked, validate_entity_props,
                                       validate_label, validate_name)
from backend.services import kg_admin_service

bp = Blueprint("admin_entity_api", __name__)


@bp.get("/admin/entity")
@admin_required
def list_entities():
    page, size = parse_page()
    label = request.args.get("type")
    if label:
        validate_label(label)
    return ok(kg_admin_service.list_entities(request.args.get("kw", ""), label, page, size))


@bp.post("/admin/entity")
@admin_required
def create_entity():
    body = require_json()
    label = validate_label(body.get("type"))
    props = validate_entity_props(label, body.get("props") or {})
    name = validate_name(props.get("name") or body.get("name"))
    props["name"] = name
    data = kg_admin_service.create_entity(current_user().id, label, name, props)
    return ok(data, msg="已新增")


@bp.put("/admin/entity")
@admin_required
def update_entity():
    body = require_json()
    label = validate_label(body.get("type"))
    name = validate_name(body.get("name"))
    props = validate_entity_props(label, body.get("props") or {})
    new_name = props.get("name") or body.get("new_name")
    new_name = validate_name(new_name, field="new_name") if new_name and new_name != name else None
    checked = body.get("checked")  # 规范决策⑦：编辑表单勾选"已校验"置 1
    if checked is not None:
        checked = validate_checked(checked)
    data = kg_admin_service.update_entity(current_user().id, label, name, props, new_name, checked)
    return ok(data, msg="已保存")


@bp.delete("/admin/entity")
@admin_required
def delete_entity():
    body = require_json()
    label = validate_label(body.get("type"))
    name = validate_name(body.get("name"))
    data = kg_admin_service.delete_entity(current_user().id, label, name, body.get("confirm_name"))
    return ok(data, msg="已删除")
