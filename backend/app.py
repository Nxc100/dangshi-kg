# -*- coding: utf-8 -*-
"""
Flask 应用工厂（开发规范 4.2）：create_app() 注册蓝图 / CORS / JWT / 全局错误处理 / 静态资源，
并在启动时一次性加载常驻对象（实体词典 + jieba 词典 + TF-IDF 矩阵），禁止每请求重建。

启动：python -m backend.app（http://127.0.0.1:5000）
"""
import logging
import os
import sys

_ROOT = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

from flask import Flask  # noqa: E402
from flask_cors import CORS  # noqa: E402

from backend.common.auth import init_jwt_handlers  # noqa: E402
from backend.common.errors import register_error_handlers  # noqa: E402
from backend.common.response import ok  # noqa: E402
from backend.config import BACKEND_DIR, Config  # noqa: E402
from backend.extensions import init_db, init_neo4j, jwt, neo4j_status  # noqa: E402

log = logging.getLogger(__name__)

BLUEPRINTS = (
    "backend.api.qa_api",
    "backend.api.graph_api",
    "backend.api.timeline_api",
    "backend.api.entity_api",
    "backend.api.daily_api",
    "backend.api.quiz_api",
    "backend.api.auth_api",
    "backend.api.user_api",
    "backend.api.stats_api",
    "backend.api.admin.overview_api",
    "backend.api.admin.entity_admin_api",
    "backend.api.admin.triple_admin_api",
    "backend.api.admin.oplog_api",
    "backend.api.admin.user_admin_api",
    "backend.api.admin.qalog_api",
)


# 这些库在 DEBUG 级别会逐条打印协议握手与连接池细节，淹没应用日志，固定压到 INFO
_NOISY_LOGGERS = ("neo4j", "neo4j.pool", "neo4j.io", "urllib3", "werkzeug")


def _configure_logging(debug):
    logging.basicConfig(
        level=logging.DEBUG if debug else logging.INFO,
        format="%(asctime)s %(levelname)s [%(name)s] %(message)s",
    )
    for name in _NOISY_LOGGERS:
        logging.getLogger(name).setLevel(logging.INFO)


def _register_blueprints(app):
    from importlib import import_module

    for module_path in BLUEPRINTS:
        app.register_blueprint(import_module(module_path).bp, url_prefix="/api")


def _load_resources(app):
    """常驻对象：实体词典（含 jieba userdict）与 F9 兜底 TF-IDF 矩阵，各加载一次（规范 6.3 性能项）。"""
    from qa import dictionary, fallback

    with app.app_context():
        dict_stats = dictionary.load()
        fallback.build(app.config["CORPUS_PATH"])
    return {"dictionary": dict_stats, "corpus_paragraphs": fallback.size()}


def create_app(load_resources=True):
    """
    应用工厂。load_resources=False 供建表 / 导入 / 验收等脚本使用：
    只装配蓝图与数据库连接，跳过词典与 TF-IDF 的加载，避免脚本启动时做无谓的重活。
    """
    app = Flask(__name__, static_folder=os.path.join(BACKEND_DIR, "static"), static_url_path="/static")
    app.config.from_object(Config)
    _configure_logging(app.config["DEBUG"])

    CORS(app, resources={r"/api/*": {"origins": "*"}, r"/static/*": {"origins": "*"}},
         supports_credentials=True)
    jwt.init_app(app)
    init_jwt_handlers(jwt)
    init_db(app)
    init_neo4j(app)
    register_error_handlers(app)
    _register_blueprints(app)

    @app.get("/api/health")
    def health():
        """自检：Neo4j 连通性、词典规模、语料段数（空白项目启动测试用）。"""
        from qa import dictionary, fallback

        return ok({
            "status": "ok",
            "neo4j": neo4j_status(),
            "dictionary_entities": dictionary.get().size(),
            "corpus_paragraphs": fallback.size(),
            "sqlite": os.path.exists(app.config["SQLITE_PATH"]),
        })

    if load_resources:
        log.info("常驻资源加载完成：%s", _load_resources(app))
    return app


def main():
    app = create_app()
    log.info("Flask 启动：http://%s:%d", app.config["HOST"], app.config["PORT"])
    app.run(host=app.config["HOST"], port=app.config["PORT"], debug=app.config["DEBUG"], use_reloader=False)


if __name__ == "__main__":
    main()
