# -*- coding: utf-8 -*-
"""
配置：从 backend/.env 读取（开发规范 4.2）。

依赖清单固定 14 个包、不引入 python-dotenv，故自实现最小 .env 解析：
KEY=VALUE 逐行读取写入 os.environ（已存在的系统环境变量优先，不覆盖）。
Neo4j 密码与 LLM key 只存 .env，不入 Git、不回显、不写日志。
"""
import os

BACKEND_DIR = os.path.dirname(os.path.abspath(__file__))
ROOT_DIR = os.path.abspath(os.path.join(BACKEND_DIR, ".."))
ENV_PATH = os.path.join(BACKEND_DIR, ".env")


def load_env(path=ENV_PATH):
    """读取 .env 到 os.environ；文件不存在时静默跳过（.env.example 为模板）。"""
    if not os.path.exists(path):
        return
    with open(path, "r", encoding="utf-8") as f:
        for raw in f:
            line = raw.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, _, value = line.partition("=")
            key, value = key.strip(), value.strip()
            if len(value) >= 2 and value[0] == value[-1] and value[0] in "\"'":
                value = value[1:-1]
            os.environ.setdefault(key, value)


load_env()


def _bool(value, default=False):
    if value is None or value == "":
        return default
    return str(value).strip().lower() in ("1", "true", "yes", "on")


def _int(value, default):
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


class Config:
    # ---- Flask / JWT ----
    SECRET_KEY = os.environ.get("SECRET_KEY") or "dev-secret-change-me"
    JWT_SECRET_KEY = os.environ.get("JWT_SECRET_KEY") or SECRET_KEY
    JWT_ACCESS_TOKEN_EXPIRES = _int(os.environ.get("JWT_ACCESS_TOKEN_EXPIRES"), 7200)  # 秒，定稿 2 小时
    JWT_TOKEN_LOCATION = ["headers"]
    JWT_HEADER_TYPE = "Bearer"
    DEBUG = _bool(os.environ.get("FLASK_DEBUG"), True)
    HOST = os.environ.get("FLASK_HOST") or "127.0.0.1"
    PORT = _int(os.environ.get("FLASK_PORT"), 5000)

    # ---- SQLite（backend/app.db，不入 Git）----
    SQLITE_PATH = os.path.join(BACKEND_DIR, "app.db")
    SQLALCHEMY_DATABASE_URI = "sqlite:///" + SQLITE_PATH.replace("\\", "/")

    # ---- Neo4j ----
    NEO4J_URI = os.environ.get("NEO4J_URI") or "bolt://localhost:7687"
    NEO4J_USER = os.environ.get("NEO4J_USER") or "neo4j"
    NEO4J_PASSWORD = os.environ.get("NEO4J_PASSWORD") or ""
    NEO4J_DATABASE = os.environ.get("NEO4J_DATABASE") or "neo4j"

    # ---- 初始管理员 ----
    ADMIN_INIT_PASSWORD = os.environ.get("ADMIN_INIT_PASSWORD") or ""

    # ---- LLM 增强（五项；llm/config.py 直接读 os.environ，此处仅作清单）----
    LLM_ENABLED = _bool(os.environ.get("LLM_ENABLED"), False)
    LLM_TIMEOUT = _int(os.environ.get("LLM_TIMEOUT"), 5)

    # ---- 资源路径 ----
    CORPUS_PATH = os.path.join(ROOT_DIR, "data", "corpus", "paragraphs.csv")
    AVATAR_DIR = os.path.join(BACKEND_DIR, "static", "avatars")
    DEFAULT_AVATAR_URL = "/static/default_avatar.png"
    MAX_CONTENT_LENGTH = 2 * 1024 * 1024 + 64 * 1024  # 头像 ≤ 2MB + multipart 余量

    # ---- 业务常量（变更须回写 V3 / FRS 对应章节，开发规范第 5 节）----
    QUESTION_MAX_LEN = 100
    KW_MAX_LEN = 30
    SUBGRAPH_LIMIT = 100
    FALLBACK_TOPK = 3
    FALLBACK_THRESHOLD = 0.05
    ANSWER_LIST_MAX = 10
    LOGIN_MAX_FAIL = 5
    LOGIN_LOCK_SECONDS = 600
    PAGE_SIZE_DEFAULT = 10
    PAGE_SIZE_MAX = 50
    HIGH_DEGREE_THRESHOLD = 20
    QUIZ_SIZES = (5, 10)
