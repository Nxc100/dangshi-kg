# 基于知识图谱的党史学习智能问答系统

限定领域模板式 KBQA：Neo4j 知识图谱 + jieba 规则问答管道 + Flask 接口 + Vue 3 前端。
需求与规范以 `doc/` 下四份文档为唯一来源（FRS V1.0 / 实施方案 V3 / LLM 接入方案 / 开发规范）。

## 目录

| 目录 | 内容 |
|---|---|
| `backend/` | Flask 应用：蓝图 `api/`、业务 `services/`、公共 `common/`（本体常量 `ontology.py` 为唯一来源） |
| `qa/` | 问答引擎八步管道（独立包，`python -m qa.cli` 命令行版） |
| `llm/` | AI 增强模块（可整体删除，`qa/` 以 try-import 引用） |
| `kg/` | 采集 `crawler/`、清洗抽取 `extract/`、导入 `importer/`（`schema.cypher` 为约束索引唯一来源） |
| `data/` | `raw/`（不入 Git）、`clean/`、`excel/`、`corpus/`、`sources.md` |
| `eval/` | 评测集与实验脚本 |
| `frontend/` | Vue 3 + Vite + Element Plus + ECharts 工程 |

## 启动

```powershell
# 0. 依赖（首次）
venv\Scripts\activate
pip install -r requirements.txt
cd frontend; npm install; cd ..

# 1. 后端（http://127.0.0.1:5000）——SQLite 已建表，直接启动
python -m backend.app

# 2. 前端（http://localhost:5173）
cd frontend; npm run dev

# 命令行问答（中期检查材料，与 POST /api/qa 共用 qa.pipeline.answer）
python -m qa.cli
python -m qa.cli "遵义会议在哪里召开"      # 非交互单次提问

# 本体常量变更后重新生成前端镜像文件（不得手改 frontend/src/utils/ontology.js）
python -m backend.common.export_ontology
```

### 自检脚本（合并代码前跑一遍，对应开发规范第 3 节回归清单）

```powershell
python -m eval.selfcheck_qa    # 离线：15 类意图 / 实体链接三级降级 / 槽位澄清 / 注入防护 / 答案模板
python -m eval.selfcheck_api   # 在线：需先启动后端；鉴权三档、问答边界、账号闭环、本体约束、导出编码
```

`selfcheck_api` 的管理员断言需要空白库才能完整验证首登强制改密，可先删除 `backend/app.db`
再执行 `python -m backend.init_db`。图谱相关断言在 Neo4j 未连接时自动计入 SKIP，不判为失败。

固定端口：Neo4j 7474/7687、Flask 5000、Vite 5173（5173 被占用时 Vite 自动顺延）。

### 账号

初始管理员 `admin`，密码取 `backend/.env` 的 `ADMIN_INIT_PASSWORD`，`must_change_pwd=1`，
首次登录只能进入"账号安全"页改密，改密后方可使用后台。重建账号：删除 `backend/app.db` 后
`python -m backend.init_db`（未配置 `ADMIN_INIT_PASSWORD` 时生成随机密码并在终端打印一次）。

### 接入 Neo4j（图谱相关功能的前置条件）

未连接 Neo4j 时系统可正常启动：首页、时间轴降级为空态与七个时期页签，问答走 F9 兜底分支，
账号 / 后台用户与日志功能不受影响；实体百科、图谱可视化、测验返回"图数据库未连接"。

```powershell
# 1) Neo4j Desktop 启动本地 DBMS，把密码填入 backend/.env 的 NEO4J_PASSWORD
# 2) 建约束与索引（Neo4j Browser 中执行 kg/importer/schema.cypher，或随导入脚本自动执行）
python -m kg.importer.test_neo4j                 # 连通自检：写 5 节点 2 关系再查询并清理
python -m kg.importer.import_all --schema        # 建约束索引 + 导入 data/excel/ 七张表（幂等可重跑）
python -m kg.importer.verify                     # 对照 V3 3.7 / 5.3 验收线核对计数与溯源覆盖
```

### AI 增强模块（可选，P1）

`backend/.env` 配置 `LLM_ENABLED / LLM_BASE_URL / LLM_API_KEY / LLM_MODEL / LLM_TIMEOUT` 后，
`GET /api/config` 返回 `llm_available=true`，问答页右上角才出现开关。未配置时界面与原方案一致。
删除 `llm/` 目录并还原 `.env` 即物理回退，`qa/` 的 try-import 失败视为系统层关闭。
