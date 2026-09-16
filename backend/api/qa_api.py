# -*- coding: utf-8 -*-
"""POST /api/qa（游客可用，含 F9 兜底与 LLM 增强分支）；GET /api/config。"""
from flask import Blueprint

from backend.common.auth import optional_user
from backend.common.response import ok
from backend.common.validators import parse_bool, require_json, validate_prev, validate_question
from backend.services import qalog_service
from qa import pipeline

bp = Blueprint("qa_api", __name__)


@bp.post("/qa")
def ask():
    body = require_json()
    question = validate_question(body.get("question"))
    prev_q, prev_a = validate_prev(body.get("prev_q"), body.get("prev_a"))
    user = optional_user()  # 游客可用；登录用户自动记历史
    ctx = {
        "use_llm": parse_bool(body.get("use_llm"), False),  # 后端不信任前端，llm.config 三条件门再判一次
        "prev_q": prev_q,
        "prev_a": prev_a,
        "user_id": user.id if user else None,
    }
    resp, meta = pipeline.strip_meta(pipeline.answer(question, ctx))
    # 落库放在答案组装之后、返回之前；失败单独捕获，不影响答案返回
    resp["log_id"] = qalog_service.write_log(question, resp, meta, user_id=user.id if user else None)
    return ok(resp)


@bp.get("/config")
def get_config():
    """只返回 {llm_available}，不回传任何配置明文。"""
    try:
        from llm import config as llm_config
        available = llm_config.available()
    except Exception:  # noqa: BLE001 —— llm/ 目录被移除即视为系统层关闭
        available = False
    return ok({"llm_available": available})
