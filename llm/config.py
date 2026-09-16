# -*- coding: utf-8 -*-
"""
LLM 配置（LLM-Design 4.2）：只读 backend/.env 的五项 LLM_*。
available() = LLM_ENABLED ∧ key 非空；GET /api/config 只回传该布尔值，不回传任何配置明文。
"""
import os

DEFAULT_TIMEOUT = 5


def _env(key, default=""):
    return (os.environ.get(key) or default).strip()


def enabled():
    return _env("LLM_ENABLED").lower() in ("1", "true", "yes", "on")


def api_key():
    return _env("LLM_API_KEY")


def base_url():
    return _env("LLM_BASE_URL").rstrip("/")


def model():
    return _env("LLM_MODEL")


def timeout():
    try:
        return float(_env("LLM_TIMEOUT") or DEFAULT_TIMEOUT)
    except ValueError:
        return DEFAULT_TIMEOUT


def rewrite_timeout():
    """FR-L03 改写调用固定取 min(3, LLM_TIMEOUT)。"""
    return min(3.0, timeout())


def available():
    """系统层开关：LLM_ENABLED ∧ 端点/密钥/模型齐备；GET /api/config 只回传该布尔值。"""
    return bool(enabled() and api_key() and base_url() and model())
