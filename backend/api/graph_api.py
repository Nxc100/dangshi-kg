# -*- coding: utf-8 -*-
"""GET /api/graph/search | /subgraph | /neighbors（游客可用）。"""
from flask import Blueprint, request

from backend.common.response import ok
from backend.common.validators import validate_hops, validate_kw, validate_limit, validate_name
from backend.services import graph_service

bp = Blueprint("graph_api", __name__)


@bp.get("/graph/search")
def search():
    kw = validate_kw(request.args.get("kw"))
    return ok(graph_service.search(kw))


@bp.get("/graph/subgraph")
def subgraph():
    name = validate_name(request.args.get("name"))
    hops = validate_hops(request.args.get("hops"))
    limit = validate_limit(request.args.get("limit"))
    return ok(graph_service.subgraph(name, hops=hops, limit=limit))


@bp.get("/graph/neighbors")
def neighbors():
    name = validate_name(request.args.get("name"))
    return ok(graph_service.neighbors(name, limit=validate_limit(request.args.get("limit"))))
