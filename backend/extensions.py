# -*- coding: utf-8 -*-
"""
扩展单例：SQLAlchemy 引擎 / 会话、JWT、Neo4j driver（开发规范 4.2 / 7.2 / 7.4）。

- SQLite：每请求一个 scoped_session，请求结束 remove；写操作在 service 内显式 commit / rollback。
- Neo4j：driver 单例，session 每次创建关闭；读用 execute_read、写用 execute_write。
  driver 不可用（未配置密码 / 未启动）只告警不阻断启动，访问图谱的接口返回 500 "图数据库未连接"。
"""
import logging

from flask_jwt_extended import JWTManager
from sqlalchemy import create_engine, event
from sqlalchemy.orm import declarative_base, scoped_session, sessionmaker

from backend.common.errors import ServiceError

log = logging.getLogger(__name__)

Base = declarative_base()
engine = None
db_session = scoped_session(sessionmaker(autoflush=False, expire_on_commit=False))
jwt = JWTManager()

_neo4j_driver = None
_neo4j_database = "neo4j"
_neo4j_error = "尚未初始化"


class Neo4jUnavailable(ServiceError):
    """图数据库未连接时由 neo4j_session() / run_read() / run_write() 抛出。"""

    def __init__(self):
        super().__init__("图数据库未连接，请先启动 Neo4j 并在 backend/.env 配置 NEO4J_PASSWORD")


# ---------------------------------------------------------------------------
# SQLite
# ---------------------------------------------------------------------------
def init_db(app):
    global engine
    engine = create_engine(
        app.config["SQLALCHEMY_DATABASE_URI"],
        connect_args={"check_same_thread": False},
        future=True,
    )

    @event.listens_for(engine, "connect")
    def _enable_fk(dbapi_conn, _record):
        dbapi_conn.execute("PRAGMA foreign_keys=ON")

    db_session.configure(bind=engine)

    @app.teardown_appcontext
    def _remove_session(_exc=None):
        db_session.remove()


# ---------------------------------------------------------------------------
# Neo4j
# ---------------------------------------------------------------------------
def init_neo4j(app):
    """创建 driver 单例并验证连通；失败只记录告警（空白项目 / Neo4j 未启动时系统仍可运行）。"""
    global _neo4j_driver, _neo4j_database, _neo4j_error
    from neo4j import GraphDatabase

    uri = app.config["NEO4J_URI"]
    user = app.config["NEO4J_USER"]
    password = app.config["NEO4J_PASSWORD"]
    _neo4j_database = app.config.get("NEO4J_DATABASE") or "neo4j"
    if not password:
        _neo4j_driver = None
        _neo4j_error = "NEO4J_PASSWORD 未配置（backend/.env）"
        log.warning("Neo4j 未连接：%s", _neo4j_error)
        return
    try:
        driver = GraphDatabase.driver(uri, auth=(user, password), connection_timeout=5)
        driver.verify_connectivity()
        _neo4j_driver = driver
        _neo4j_error = None
        log.info("Neo4j 已连接：%s（database=%s）", uri, _neo4j_database)
    except Exception as exc:  # noqa: BLE001 —— 启动期容错
        _neo4j_driver = None
        _neo4j_error = str(exc)
        log.warning("Neo4j 连接失败（%s）：%s", uri, exc)


def close_neo4j():
    global _neo4j_driver
    if _neo4j_driver is not None:
        try:
            _neo4j_driver.close()
        finally:
            _neo4j_driver = None


def get_driver():
    return _neo4j_driver


def neo4j_available():
    return _neo4j_driver is not None


def neo4j_status():
    return {"connected": _neo4j_driver is not None, "error": _neo4j_error}


def neo4j_session():
    """返回 driver.session()（调用方负责 with 关闭）；driver 不可用抛 Neo4jUnavailable。"""
    if _neo4j_driver is None:
        raise Neo4jUnavailable()
    return _neo4j_driver.session(database=_neo4j_database)


def run_read(cypher, **params):
    """只读事务执行参数化 Cypher，返回 list[dict]。标签 / 关系名只能来自 ontology 白名单拼入。"""
    with neo4j_session() as session:
        return session.execute_read(lambda tx: tx.run(cypher, **params).data())


def run_write(cypher, **params):
    """写事务执行参数化 Cypher，返回 list[dict]；只允许 kg_admin_service 与导入脚本调用。"""
    with neo4j_session() as session:
        return session.execute_write(lambda tx: tx.run(cypher, **params).data())
