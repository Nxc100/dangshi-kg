# -*- coding: utf-8 -*-
"""
LLM 厂商与模型预设（唯一来源，LLM-Design 4.2/4.3）。

只登记「OpenAI 兼容端点 + 可选模型」这类公开信息，**绝不包含任何 API Key**——
密钥由管理员在后台填写并落库（见 models.LlmConfig），文件与接口均不回显明文。

新增厂商只改本文件：端点须为 OpenAI 兼容的 /chat/completions 前缀（client.py 会补该后缀），
换厂商不需要改任何调用代码（LLM-Design 4.3「更换厂商只改配置，不改代码」）。
"""

PROVIDERS = [
    {
        "id": "qwen",
        "name": "通义千问（阿里云百炼）",
        "base_url": "https://dashscope.aliyuncs.com/compatible-mode/v1",
        "doc": "https://help.aliyun.com/zh/model-studio/",
        "models": [
            {"id": "qwen-plus", "name": "通义千问 Plus"},
            {"id": "qwen-turbo", "name": "通义千问 Turbo"},
            {"id": "qwen-max", "name": "通义千问 Max"},
        ],
    },
    {
        "id": "zhipu",
        "name": "智谱 GLM",
        "base_url": "https://open.bigmodel.cn/api/paas/v4",
        "doc": "https://open.bigmodel.cn/dev/api",
        "models": [
            {"id": "glm-4-flash", "name": "GLM-4-Flash（免费）"},
            {"id": "glm-4-air", "name": "GLM-4-Air"},
            {"id": "glm-4-plus", "name": "GLM-4-Plus"},
        ],
    },
    {
        "id": "deepseek",
        "name": "DeepSeek",
        "base_url": "https://api.deepseek.com/v1",
        "doc": "https://platform.deepseek.com/api-docs/",
        "models": [
            {"id": "deepseek-chat", "name": "DeepSeek Chat"},
        ],
    },
    {
        "id": "moonshot",
        "name": "月之暗面 Kimi",
        "base_url": "https://api.moonshot.cn/v1",
        "doc": "https://platform.moonshot.cn/docs",
        "models": [
            {"id": "moonshot-v1-8k", "name": "Moonshot v1 8K"},
            {"id": "moonshot-v1-32k", "name": "Moonshot v1 32K"},
        ],
    },
    {
        "id": "custom",
        "name": "自定义（其他 OpenAI 兼容端点）",
        "base_url": "",
        "doc": "",
        "models": [],
    },
]

PROVIDER_IDS = [p["id"] for p in PROVIDERS]


def get(provider_id):
    """按 id 取厂商预设；未知 id 返回 None。"""
    for p in PROVIDERS:
        if p["id"] == provider_id:
            return p
    return None


def model_ids(provider_id):
    """该厂商的预设模型 id 列表；custom 返回空表示不限制。"""
    p = get(provider_id)
    return [m["id"] for m in (p or {}).get("models", [])]
