# -*- coding: utf-8 -*-
"""
Neo4j 连通性自检（V3 附录 A）：写入 5 节点 2 关系再查询打印，随后清理。
用法（项目根目录）：python -m kg.importer.test_neo4j
"""
import os
import sys

_ROOT = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".."))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

TEST_TAG = "__selftest__"

CREATE = """
MERGE (m:Meeting {name:'自检会议'}) SET m.tag=$tag, m.time_text='1935年1月15日至17日', m.time_sort='19350115'
MERGE (l:Location {name:'自检地点'}) SET l.tag=$tag
MERGE (p:Person {name:'自检人物'}) SET p.tag=$tag
MERGE (t:Period {name:'自检时期'}) SET t.tag=$tag, t.order=99
MERGE (d:Document {name:'自检文献'}) SET d.tag=$tag
MERGE (m)-[:HELD_IN]->(l)
MERGE (p)-[:PARTICIPATED_IN]->(m)
"""
QUERY = ("MATCH (m:Meeting {name:'自检会议'})-[:HELD_IN]->(l:Location) "
         "OPTIONAL MATCH (p:Person)-[:PARTICIPATED_IN]->(m) "
         "RETURN m.name AS meeting, m.time_text AS time, l.name AS place, collect(p.name) AS people")
CLEANUP = "MATCH (n) WHERE n.tag = $tag DETACH DELETE n RETURN count(n) AS removed"


def main():
    from backend.app import create_app
    from backend.extensions import neo4j_available, neo4j_status, run_read, run_write

    app = create_app(load_resources=False)
    with app.app_context():
        if not neo4j_available():
            print("Neo4j 未连接：%s" % neo4j_status()["error"])
            print("请在 Neo4j Desktop 启动本地 DBMS，并在 backend/.env 配置 NEO4J_PASSWORD 后重试。")
            return 1
        run_write(CREATE, tag=TEST_TAG)
        rows = run_read(QUERY)
        print("查询结果：%s" % rows)
        removed = run_write(CLEANUP, tag=TEST_TAG)
        print("已清理自检数据：%s" % removed)
        counts = run_read("MATCH (n) RETURN count(n) AS nodes")
        print("当前库内节点总数：%s" % counts[0]["nodes"])
        print("Neo4j 连通性自检通过。")
        return 0


if __name__ == "__main__":
    sys.exit(main())
