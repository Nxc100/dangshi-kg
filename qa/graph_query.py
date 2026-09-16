# -*- coding: utf-8 -*-
"""⑦ 图谱只读查询：driver session 读事务执行第⑥步产出的参数化 Cypher。"""
from backend.extensions import run_read


def query(cypher, params):
    """返回 list[dict]；图数据库未连接时抛 backend.extensions.Neo4jUnavailable。"""
    return run_read(cypher, **(params or {}))
