# -*- coding: utf-8 -*-
"""
入参校验（开发规范 8.3；规则与前端 utils/validators.js 一致）。
校验失败抛 BadRequest(422)，errors={字段: 中文提示} 供前端逐字段红字显示。
"""
import re

from flask import request

from backend.common import ontology
from backend.common.errors import BadRequest
from backend.config import Config

_USERNAME_RE = re.compile(r"^[A-Za-z0-9_]{3,20}$")
_HAS_LETTER_RE = re.compile(r"[A-Za-z]")
_HAS_DIGIT_RE = re.compile(r"\d")
_MEANINGFUL_RE = re.compile(r"[一-鿿A-Za-z0-9]")


def require_json():
    """取 JSON 请求体（dict）；非 JSON 或非对象 → 422。"""
    body = request.get_json(silent=True)
    if not isinstance(body, dict):
        raise BadRequest("请求体必须为 JSON 对象")
    return body


def _text(value):
    return value.strip() if isinstance(value, str) else ""


# ---------------------------------------------------------------------------
# 问答
# ---------------------------------------------------------------------------
def validate_question(value):
    """问句：非空、≤100 字、非纯符号/纯空白（规范 8.3；与前端 questionError 同规则）。"""
    q = _text(value)
    if not q:
        raise BadRequest("请输入有效问题", errors={"question": "问题不能为空"})
    if len(q) > Config.QUESTION_MAX_LEN:
        raise BadRequest("问题过长", errors={"question": "问题不能超过 %d 字" % Config.QUESTION_MAX_LEN})
    if not _MEANINGFUL_RE.search(q):
        raise BadRequest("请输入有效问题", errors={"question": "问题不能为纯符号或空白"})
    return q


def validate_prev(prev_q, prev_a):
    """追问上下文：prev_q ≤100 字、prev_a ≤200 字，超出即截断（LLM-Design FR-L03）。"""
    prev_q = _text(prev_q)[:Config.QUESTION_MAX_LEN] if prev_q else ""
    prev_a = _text(prev_a)[:200] if prev_a else ""
    return prev_q, prev_a


def parse_bool(value, default=False):
    """宽松布尔解析；use_llm 等开关缺省按 False（规范 6.4：后端不信任前端）。"""
    if isinstance(value, bool):
        return value
    if value is None:
        return default
    return str(value).strip().lower() in ("1", "true", "yes", "on")


# ---------------------------------------------------------------------------
# 账号
# ---------------------------------------------------------------------------
def validate_username(value):
    """用户名：3–20 位字母、数字或下划线（规范 6.2 / 8.3）。唯一性由 auth_service 校验。"""
    u = _text(value)
    if not _USERNAME_RE.match(u):
        raise BadRequest("用户名格式不正确", errors={"username": "用户名为 3–20 位字母、数字或下划线"})
    return u


def validate_password(value, field="password"):
    """密码：8–20 位且同时含字母与数字（规范 6.2 / 8.3）。明文不落库、不写日志。"""
    p = value if isinstance(value, str) else ""
    if not (8 <= len(p) <= 20) or not _HAS_LETTER_RE.search(p) or not _HAS_DIGIT_RE.search(p):
        raise BadRequest("密码格式不正确", errors={field: "密码为 8–20 位且同时包含字母与数字"})
    return p


def validate_nickname(value):
    """昵称：1–16 个字符，过滤首尾空白（规范 6.2；默认昵称 = 用户名）。"""
    n = _text(value)
    if not (1 <= len(n) <= 16):
        raise BadRequest("昵称格式不正确", errors={"nickname": "昵称为 1–16 个字符"})
    return n


def validate_status(value):
    """user.status：1 启用 / 0 禁用（规范 8.3）。"""
    if value not in (0, 1, "0", "1"):
        raise BadRequest("状态值不合法", errors={"status": "status 只能为 0 或 1"})
    return int(value)


def validate_checked(value):
    """节点属性 checked：1 属核心校验池（测验与每日推荐只取 checked=1），0 未校验。"""
    if value not in (0, 1, "0", "1", True, False):
        raise BadRequest("校验标记不合法", errors={"checked": "checked 只能为 0 或 1"})
    return int(value)


def validate_role(value):
    """user.role：user / admin（规范 8.3）；「至少保留 1 个 admin」由 user_admin_service 兜底。"""
    if value not in ("user", "admin"):
        raise BadRequest("角色值不合法", errors={"role": "role 只能为 user 或 admin"})
    return value


# ---------------------------------------------------------------------------
# 分页 / 通用
# ---------------------------------------------------------------------------
def parse_page(args=None):
    """page ≥ 1（默认 1）、size 1–50（默认 10）；越界按默认 / 上限纠正，不报错。"""
    args = request.args if args is None else args
    try:
        page = int(args.get("page", 1))
    except (TypeError, ValueError):
        page = 1
    try:
        size = int(args.get("size", Config.PAGE_SIZE_DEFAULT))
    except (TypeError, ValueError):
        size = Config.PAGE_SIZE_DEFAULT
    page = max(page, 1)
    size = min(max(size, 1), Config.PAGE_SIZE_MAX)
    return page, size


def validate_kw(value, max_len=None, required=True):
    """搜索词：非空、≤30 字（规范 8.3 图谱项）。"""
    kw = _text(value)
    max_len = max_len or Config.KW_MAX_LEN
    if required and not kw:
        raise BadRequest("搜索词不能为空", errors={"kw": "请输入搜索词"})
    if len(kw) > max_len:
        raise BadRequest("搜索词过长", errors={"kw": "搜索词不能超过 %d 字" % max_len})
    return kw


def validate_name(value, field="name"):
    """实体主名：非空；主名是百科 URL、词典、子图 id 与收藏 ref_id 的唯一键（规范 6.5）。"""
    name = _text(value)
    if not name:
        raise BadRequest("实体名不能为空", errors={field: "实体名不能为空"})
    if len(name) > 100:
        raise BadRequest("实体名过长", errors={field: "实体名不能超过 100 字"})
    return name


# 年份范围（1921–2021）的校验按规范 8.3 由前端承担：后端接口不接收年份入参，
# 时间轴按 period 查询，年份定位是前端在已取回的事件列表内滚动。


# ---------------------------------------------------------------------------
# 图谱 / 时间轴 / 测验
# ---------------------------------------------------------------------------
def validate_hops(value):
    """子图跳数：只允许 1 或 2（规范 6.5）。"""
    try:
        hops = int(value) if value not in (None, "") else 2
    except (TypeError, ValueError):
        raise BadRequest("hops 参数不合法", errors={"hops": "hops 只能为 1 或 2"})
    if hops not in (1, 2):
        raise BadRequest("hops 参数不合法", errors={"hops": "hops 只能为 1 或 2"})
    return hops


def validate_limit(value):
    """子图节点上限：≤100，越界按上限纠正（规范 6.5：单画布节点上限 100）。"""
    try:
        limit = int(value) if value not in (None, "") else Config.SUBGRAPH_LIMIT
    except (TypeError, ValueError):
        limit = Config.SUBGRAPH_LIMIT
    return min(max(limit, 1), Config.SUBGRAPH_LIMIT)


def validate_period(value, required=False):
    """时期名：必须是本体定稿的七个历史时期之一（规范 8.3）。"""
    name = _text(value)
    if not name:
        if required:
            raise BadRequest("时期不能为空", errors={"period": "请指定历史时期"})
        return None
    if name not in ontology.PERIOD_NAMES:
        raise BadRequest("时期名称不合法", errors={"period": "period 必须是七个历史时期之一"})
    return name


def validate_quiz_n(value):
    """题量：仅 5 / 10 两档（FRS FR-G06）。"""
    try:
        n = int(value) if value not in (None, "") else 5
    except (TypeError, ValueError):
        raise BadRequest("题量不合法", errors={"n": "题量只能为 5 或 10"})
    if n not in Config.QUIZ_SIZES:
        raise BadRequest("题量不合法", errors={"n": "题量只能为 5 或 10"})
    return n


def parse_entities(value):
    """`entities=a,b,c` → 去重列表（≤ 20 个）。"""
    if not value:
        return []
    items = []
    for part in str(value).split(","):
        part = part.strip()
        if part and part not in items:
            items.append(part)
    if len(items) > 20:
        raise BadRequest("entities 参数过多", errors={"entities": "最多指定 20 个实体"})
    return items


# ---------------------------------------------------------------------------
# 后台本体校验
# ---------------------------------------------------------------------------
def validate_label(value, field="type"):
    """实体类型：必须是 ontology 七类标签之一；同时是拼入 Cypher 的白名单校验（规范 4.3）。"""
    if not ontology.is_label(value):
        raise BadRequest("实体类型不合法", errors={field: "实体类型必须是七类标签之一"})
    return value


def validate_relation(value, field="rel"):
    """关系类型：必须是 ontology 十类关系之一；同时是拼入 Cypher 的白名单校验（规范 4.3）。"""
    if not ontology.is_relation(value):
        raise BadRequest("关系类型不合法", errors={field: "关系类型必须是十类关系之一"})
    return value


def validate_entity_props(label, props):
    """按 ontology 校验必填属性与枚举值域；返回清洗后的属性字典（只保留本体定义的非派生属性）。"""
    props = props if isinstance(props, dict) else {}
    errors = {}
    cleaned = {}
    for p in ontology.form_props(label):
        raw = props.get(p["name"])
        value = raw.strip() if isinstance(raw, str) else raw
        if p["required"] and (value is None or value == ""):
            errors[p["name"]] = "%s为必填项" % p["zh"]
            continue
        if value is None or value == "":
            continue
        if p["kind"] == "enum" and value not in p.get("enum", []):
            errors[p["name"]] = "%s取值不合法" % p["zh"]
            continue
        if p["kind"] == "number":
            try:
                value = int(value)
            except (TypeError, ValueError):
                errors[p["name"]] = "%s必须为整数" % p["zh"]
                continue
        cleaned[p["name"]] = value
    if label == "Period" and "order" in cleaned and not (1 <= cleaned["order"] <= 7):
        errors["order"] = "时期序号必须在 1–7 之间"
    if errors:
        raise BadRequest("参数校验失败", errors=errors)
    return cleaned
