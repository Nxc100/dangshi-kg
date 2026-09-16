// ============================================================================
// Neo4j 唯一约束与索引（唯一可信来源，V3 5.1）
// 执行方式：Neo4j Browser 中整段粘贴执行，或 python -m kg.importer.import_all（导入前自动执行）
// 变更纪律：本文件与 backend/common/ontology.py、V3 第四章 必须同步修改
// 验证：SHOW CONSTRAINTS / SHOW INDEXES 与下表一致
// ============================================================================

// ---- 七类实体主名唯一约束（自动附带索引，保证 name 点查毫秒级）----
CREATE CONSTRAINT person_name IF NOT EXISTS FOR (n:Person) REQUIRE n.name IS UNIQUE;
CREATE CONSTRAINT org_name IF NOT EXISTS FOR (n:Organization) REQUIRE n.name IS UNIQUE;
CREATE CONSTRAINT event_name IF NOT EXISTS FOR (n:Event) REQUIRE n.name IS UNIQUE;
CREATE CONSTRAINT meeting_name IF NOT EXISTS FOR (n:Meeting) REQUIRE n.name IS UNIQUE;
CREATE CONSTRAINT location_name IF NOT EXISTS FOR (n:Location) REQUIRE n.name IS UNIQUE;
CREATE CONSTRAINT document_name IF NOT EXISTS FOR (n:Document) REQUIRE n.name IS UNIQUE;
CREATE CONSTRAINT period_name IF NOT EXISTS FOR (n:Period) REQUIRE n.name IS UNIQUE;

// ---- 时间排序索引（时间轴按 time_sort 升序、每日学习按 MMDD 筛选）----
CREATE INDEX event_time IF NOT EXISTS FOR (n:Event) ON (n.time_sort);
CREATE INDEX meeting_time IF NOT EXISTS FOR (n:Meeting) ON (n.time_sort);

// ---- 核心池标记索引（测验出题与每日推荐一律 WHERE n.checked = 1）----
CREATE INDEX event_checked IF NOT EXISTS FOR (n:Event) ON (n.checked);
CREATE INDEX meeting_checked IF NOT EXISTS FOR (n:Meeting) ON (n.checked);
CREATE INDEX person_checked IF NOT EXISTS FOR (n:Person) ON (n.checked);
CREATE INDEX org_checked IF NOT EXISTS FOR (n:Organization) ON (n.checked);
CREATE INDEX document_checked IF NOT EXISTS FOR (n:Document) ON (n.checked);
CREATE INDEX location_checked IF NOT EXISTS FOR (n:Location) ON (n.checked);
CREATE INDEX period_checked IF NOT EXISTS FOR (n:Period) ON (n.checked);
