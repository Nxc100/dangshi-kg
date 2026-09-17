# -*- coding: utf-8 -*-
"""
AI 增强模块的系统层配置管理（FR-L06，LLM-Design 2.1/4.2 的落库化）。

唯一职责：读写 `llm_config` 单行表，并把生效配置推送给 `llm.config`（依赖注入，见该模块说明）。
所有对 LLM 系统层配置的写入都必须经过本服务——它是「知识写入口」之外的又一个唯一写入点，
以保证「落库」与「推送给 llm 包」两步永远同时发生，不出现库里改了但运行时没生效的偏差。

安全：api_key 落库后任何接口只回显掩码（models.LlmConfig.to_dict）；
      本服务不提供任何返回明文 key 的方法。
"""
import logging
import time

from backend.common import llm_providers
from backend.common.errors import BadRequest
from backend.extensions import db_session
from backend.models import LlmConfig, now

log = logging.getLogger(__name__)

CONFIG_ID = 1
TIMEOUT_MIN, TIMEOUT_MAX = 1, 60
# 测试连通性用的最小问句：既验证鉴权与端点，也验证模型能正常出文本
PROBE_MESSAGES = [
    {"role": "system", "content": "你是连通性测试助手，只输出两个字：正常。"},
    {"role": "user", "content": "请回复：正常"},
]
PROBE_TIMEOUT = 12


def _row():
    """取单行配置；不存在则建一条空配置（保证后续 UPDATE 语义统一）。"""
    row = db_session.get(LlmConfig, CONFIG_ID)
    if row is None:
        row = LlmConfig(id=CONFIG_ID, enabled=0, provider="", base_url="",
                        api_key="", model="", timeout=5, updated_at=now())
        db_session.add(row)
        db_session.commit()
    return row


def _push(row):
    """把库里的配置推送给 llm 包；llm/ 被移除时静默跳过（系统层视为关闭）。"""
    try:
        from llm import config as llm_config
    except Exception:  # noqa: BLE001 —— llm/ 目录被移除即视为系统层关闭
        return False
    # 未配置齐全时推 None，等价于回落 .env，避免半截配置把原有部署方式顶掉
    if row.enabled and row.api_key and row.base_url and row.model:
        llm_config.set_override({
            "enabled": bool(row.enabled),
            "base_url": row.base_url,
            "api_key": row.api_key,
            "model": row.model,
            "timeout": row.timeout,
        })
    elif row.enabled:
        # 明确启用但配置不全：按启用态推送，available() 自会因缺项返回 False，
        # 后台由此能看到「已启用但未生效」，而不是悄悄回落到 .env 的旧配置
        llm_config.set_override({
            "enabled": True,
            "base_url": row.base_url,
            "api_key": row.api_key,
            "model": row.model,
            "timeout": row.timeout,
        })
    else:
        llm_config.set_override({"enabled": False})
    return True


def load_into_runtime():
    """应用启动时调用一次：库中有配置就接管 .env，没有则保持 .env 行为。"""
    try:
        row = db_session.get(LlmConfig, CONFIG_ID)
    except Exception as exc:  # noqa: BLE001 —— 表尚未建立（旧库未迁移）时不阻断启动
        log.warning("LLM 配置表不可用，暂按 .env 运行：%s", exc.__class__.__name__)
        return False
    if row is None:
        return False
    return _push(row)


def current():
    """后台读取：库中配置（key 掩码）+ 当前实际生效快照（区分 db / env 来源）。"""
    row = _row()
    data = row.to_dict()
    data["providers"] = llm_providers.PROVIDERS
    try:
        from llm import config as llm_config
        data["runtime"] = llm_config.snapshot()
        data["module_present"] = True
    except Exception:  # noqa: BLE001
        # llm/ 目录被物理移除：后台如实显示模块缺失，而不是假装配置有效
        data["runtime"] = {"available": False, "source": "none"}
        data["module_present"] = False
    return data


def _validate(payload, row):
    """
    校验并归一入参；返回待写入的字段字典。

    **部分更新语义**：请求体未出现的键一律保留库中原值，只覆盖显式给出的键。
    全量覆盖会让「只想改个开关」的调用把端点与模型一并清空，属易误操作的危险语义；
    api_key 另有更严的约定——传空字符串才是清空，不传则保留（见下）。
    """
    errors = {}

    provider = str(payload.get("provider", row.provider) or "").strip()
    if provider and provider not in llm_providers.PROVIDER_IDS:
        errors["provider"] = "未知的厂商标识"

    base_url = str(payload.get("base_url", row.base_url) or "").strip().rstrip("/")
    if base_url and not base_url.startswith(("http://", "https://")):
        errors["base_url"] = "端点需以 http:// 或 https:// 开头"

    model = str(payload.get("model", row.model) or "").strip()
    # custom 厂商不限制模型名；预设厂商允许自填，但给出的选项应在清单内
    if provider and provider != "custom" and model:
        allowed = llm_providers.model_ids(provider)
        if allowed and model not in allowed:
            log.info("模型 %s 不在 %s 预设清单中，按自定义模型处理", model, provider)

    try:
        timeout = int(payload.get("timeout", row.timeout) or 5)
    except (TypeError, ValueError):
        timeout = -1
    if not TIMEOUT_MIN <= timeout <= TIMEOUT_MAX:
        errors["timeout"] = "超时需在 %d–%d 秒之间" % (TIMEOUT_MIN, TIMEOUT_MAX)

    enabled = 1 if payload.get("enabled", bool(row.enabled)) else 0

    # api_key 留空表示「不修改」，便于管理员只调模型而不重填密钥；显式传空字符串才是清空
    raw_key = payload.get("api_key")
    if raw_key is None:
        api_key = row.api_key
    else:
        api_key = str(raw_key).strip()

    if enabled and not (api_key and base_url and model):
        errors["enabled"] = "启用前需填写端点、密钥与模型"

    if errors:
        raise BadRequest("配置校验未通过", errors=errors)

    return {"enabled": enabled, "provider": provider, "base_url": base_url,
            "api_key": api_key, "model": model, "timeout": timeout}


def save(payload, admin_id):
    """保存配置并即时推送到运行时；返回与 current() 同构的结果。"""
    row = _row()
    fields = _validate(payload or {}, row)
    for k, v in fields.items():
        setattr(row, k, v)
    row.updated_by = admin_id
    row.updated_at = now()
    db_session.commit()
    _push(row)
    log.info("管理员 %s 更新 AI 增强配置：enabled=%s provider=%s model=%s",
             admin_id, row.enabled, row.provider, row.model)
    return current()


def test_connection(payload):
    """
    连通性测试：用「本次表单里的配置」直接试打一次，不改动库与运行时。

    之所以不复用 llm.client：client 读的是全局生效配置，而管理员往往是在「还没保存」
    的状态下点测试，必须按表单值验证。这里只做一次最小请求，仍走 requests 直调、
    异常全部收敛为失败信息，不抛给前端。
    """
    import requests

    row = _row()
    base_url = str((payload or {}).get("base_url") or "").strip().rstrip("/")
    model = str((payload or {}).get("model") or "").strip()
    raw_key = (payload or {}).get("api_key")
    api_key = row.api_key if raw_key in (None, "") else str(raw_key).strip()

    missing = [n for n, v in (("端点", base_url), ("模型", model), ("密钥", api_key)) if not v]
    if missing:
        return {"ok": False, "message": "请先填写：%s" % "、".join(missing), "latency_ms": None}

    start = time.time()
    try:
        resp = requests.post(
            "%s/chat/completions" % base_url,
            json={"model": model, "messages": PROBE_MESSAGES, "max_tokens": 16,
                  "temperature": 0, "stream": False},
            headers={"Authorization": "Bearer %s" % api_key, "Content-Type": "application/json"},
            timeout=PROBE_TIMEOUT,
        )
    except requests.Timeout:
        return {"ok": False, "message": "连接超时（%d 秒），请检查端点是否可达" % PROBE_TIMEOUT,
                "latency_ms": int((time.time() - start) * 1000)}
    except requests.RequestException as exc:
        return {"ok": False, "message": "请求失败：%s" % exc.__class__.__name__,
                "latency_ms": int((time.time() - start) * 1000)}

    latency = int((time.time() - start) * 1000)
    if resp.status_code == 401:
        return {"ok": False, "message": "密钥无效或未授权（401）", "latency_ms": latency}
    if resp.status_code == 404:
        return {"ok": False, "message": "端点或模型不存在（404），请检查 Base URL 与模型名", "latency_ms": latency}
    if resp.status_code != 200:
        return {"ok": False, "message": "接口返回 %d" % resp.status_code, "latency_ms": latency}
    try:
        text = resp.json()["choices"][0]["message"]["content"]
    except (ValueError, KeyError, IndexError, TypeError):
        return {"ok": False, "message": "响应格式非 OpenAI 兼容，无法解析", "latency_ms": latency}

    return {"ok": True, "message": "连通正常，模型回复：%s" % (text or "").strip()[:40],
            "latency_ms": latency}
