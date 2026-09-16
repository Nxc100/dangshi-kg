# -*- coding: utf-8 -*-
"""
唯一外呼出口（LLM-Design 4.3）：requests 直接 POST OpenAI 兼容 /chat/completions，不引入任何 SDK。
网络异常、非 200、超时、响应解析失败全部捕获返回 None 并 logging 原因；
降级判断收敛于"是否为 None"一处。requests 的 timeout 为硬限制，不允许无超时调用。
"""
import logging

import requests

from llm import config

log = logging.getLogger(__name__)


def chat(messages, timeout, max_tokens=300, temperature=0.1):
    """返回生成文本（str）或 None。"""
    if not config.available():
        return None
    url = "%s/chat/completions" % config.base_url()
    payload = {
        "model": config.model(),
        "messages": messages,
        "max_tokens": max_tokens,
        "temperature": temperature,
        "stream": False,
    }
    headers = {"Authorization": "Bearer %s" % config.api_key(), "Content-Type": "application/json"}
    try:
        resp = requests.post(url, json=payload, headers=headers, timeout=timeout)
    except requests.RequestException as exc:
        log.warning("LLM 请求异常，降级：%s", exc.__class__.__name__)
        return None
    if resp.status_code != 200:
        log.warning("LLM 返回非 200（%s），降级", resp.status_code)
        return None
    try:
        text = resp.json()["choices"][0]["message"]["content"]
    except (ValueError, KeyError, IndexError, TypeError) as exc:
        log.warning("LLM 响应解析失败，降级：%s", exc.__class__.__name__)
        return None
    text = (text or "").strip()
    return text or None
