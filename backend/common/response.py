# -*- coding: utf-8 -*-
"""统一返回体（开发规范 8.2）：{code, msg, data}；HTTP 状态码与 code 同步（成功 200）。"""
from flask import jsonify


def ok(data=None, msg="ok"):
    return jsonify({"code": 0, "msg": msg, "data": data}), 200


def fail(code, msg, data=None):
    """code ∈ {401, 403, 404, 422, 500}，不另设四位业务码（FRS 1.5）。"""
    return jsonify({"code": code, "msg": msg, "data": data}), code


def page_data(items, page, size, total):
    """分页统一结构：{list, page, size, total}。"""
    return {"list": items, "page": page, "size": size, "total": total}
