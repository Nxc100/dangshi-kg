# -*- coding: utf-8 -*-
"""
LLM 配置（LLM-Design 4.2）。

取值优先级：**宿主应用注入的运行时配置 > backend/.env 的 LLM_* 五项**。

注入机制（依赖倒置）：后台「AI 增强」页把配置写入 SQLite 后调用 `set_override()` 推入本模块，
本模块**不反向 import backend**——`llm/` 必须保持独立可整体移除（LLM-Design 4.1 的工程保证），
若在此处直接读库，删掉 backend 或单独跑 `python -m qa.cli` 就会崩。
未注入（或注入 None）时行为与原方案逐字节一致：仍然只读 .env。

available() = enabled ∧ key ∧ base_url ∧ model；GET /api/config 只回传该布尔值，不回传任何明文。
"""
import os

DEFAULT_TIMEOUT = 5

# 宿主应用注入的运行时配置；None 表示未注入，全部回落 .env
_override = None


def set_override(cfg):
    """
    由宿主应用注入运行时配置（dict 或 None）。
    dict 键：enabled(bool) / base_url / api_key / model / timeout。
    传 None 即清除注入、回落 .env——这也是「关闭系统层开关」的物理回退路径之一。
    """
    global _override
    _override = dict(cfg) if cfg else None


def _env(key, default=""):
    return (os.environ.get(key) or default).strip()


def _pick(name, env_key, default=""):
    """先取注入值，缺失再回落 .env。"""
    if _override is not None and _override.get(name) not in (None, ""):
        return str(_override[name]).strip()
    return _env(env_key, default)


def enabled():
    if _override is not None:
        return bool(_override.get("enabled"))
    return _env("LLM_ENABLED").lower() in ("1", "true", "yes", "on")


def api_key():
    return _pick("api_key", "LLM_API_KEY")


def base_url():
    return _pick("base_url", "LLM_BASE_URL").rstrip("/")


def model():
    return _pick("model", "LLM_MODEL")


def timeout():
    try:
        return float(_pick("timeout", "LLM_TIMEOUT") or DEFAULT_TIMEOUT)
    except (TypeError, ValueError):
        return DEFAULT_TIMEOUT


def rewrite_timeout():
    """FR-L03 改写调用固定取 min(3, LLM_TIMEOUT)。"""
    return min(3.0, timeout())


def available():
    """系统层开关：enabled ∧ 端点/密钥/模型齐备；GET /api/config 只回传该布尔值。"""
    return bool(enabled() and api_key() and base_url() and model())


def snapshot():
    """当前生效配置的脱敏快照，供后台展示「实际生效值」与排错，不含明文 key。"""
    return {
        "enabled": enabled(),
        "base_url": base_url(),
        "model": model(),
        "timeout": timeout(),
        "has_key": bool(api_key()),
        "available": available(),
        "source": "db" if _override is not None else "env",
    }
