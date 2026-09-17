# 基于知识图谱的党史学习智能问答系统

限定领域模板式 KBQA：Neo4j 知识图谱 + jieba 规则问答管道 + Flask 接口 + Vue 3 前端。
需求与规范以 `doc/` 下四份文档为唯一来源（FRS V1.1 / 实施方案 V3 / LLM 接入方案 / 开发规范）；
`doc/Neo4j-Desktop-2-使用指南.md` 是操作手册，只讲怎么用，不参与需求与规范的定义。

## 目录

| 目录 | 内容 |
|---|---|
| `backend/` | Flask 应用：蓝图 `api/`、业务 `services/`、公共 `common/`（本体常量 `ontology.py` 为唯一来源） |
| `qa/` | 问答引擎八步管道（独立包，`python -m qa.cli` 命令行版） |
| `llm/` | AI 增强模块（可整体删除，`qa/` 以 try-import 引用） |
| `kg/` | 采集 `crawler/`、清洗抽取 `extract/`、导入 `importer/`（`schema.cypher` 为约束索引唯一来源） |
| `db/` | 种子与核心池数据 `seed_data/`、四层合并 `merge_sources.py`、Excel 生成 `build_seed.py`、一键初始化 `init_all.py` |
| `data/` | `excel/`（**图谱初始化数据，随仓库提交**）、`clean/`、`corpus/`、`sources.md`；`raw/` 为原始网页留档，不入 Git |
| `eval/` | 功能验收、数据核查、两个实验数据集与实验脚本 |
| `frontend/` | Vue 3 + Vite + Element Plus + ECharts 工程 |

---

## 在一台新机器上跑起来

**前置软件：** Python 3.12、Node.js 18+、Neo4j Desktop（本地 DBMS，Bolt 端口 7687）。

```powershell
# 1. 取代码并建虚拟环境（venv/ 不入 Git，必须本地建）
git clone <仓库地址> dangshi-kg
cd dangshi-kg
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt

# 2. 配置（.env 含密码，不入 Git，必须本地建）
copy backend\.env.example backend\.env
#    编辑 backend\.env，至少填两项：
#      NEO4J_PASSWORD=<Neo4j Desktop 里该 DBMS 的密码>
#      ADMIN_INIT_PASSWORD=<初始管理员口令，留空则建库时生成随机密码并打印一次>

# 3. 启动 Neo4j Desktop 的本地 DBMS，确认 bolt://127.0.0.1:7687 已监听
#    没用过 Desktop 2 看 doc/Neo4j-Desktop-2-使用指南.md（启停、查图谱、看日志、排错）

# 4. 一键初始化：建 SQLite → 建约束索引 → 导入图谱 → 数据验收核对
python -m db.init_all

# 5. 起服务
python -m backend.app                    # 后端 http://127.0.0.1:5000
cd frontend; npm install; npm run dev    # 前端 http://localhost:5173
```

第 4 步的图谱数据来自随仓库提交的 `data/excel/` 七张表 + `alias.xlsx`，**不需要联网重新采集**；
跑完会打印 V3 3.7 的七项验收结果，全部「达标」即初始化成功。

固定端口：Neo4j 7474/7687、Flask 5000（`FLASK_PORT` 可改）、Vite 5173（被占用时自动顺延）。

### 没连 Neo4j 时会怎样

系统仍可启动：首页与时间轴降级为空态与七个时期页签，问答走 F9 兜底分支，账号与后台
用户/日志功能不受影响；实体百科、图谱可视化、测验返回「图数据库未连接」。

### 初始账号

管理员 `admin`，密码取 `backend/.env` 的 `ADMIN_INIT_PASSWORD`，`must_change_pwd=1`，
首次登录只能进「账号安全」页改密，改密后方可使用后台。
重建账号：删除 `backend/app.db` 后 `python -m backend.init_db`。

---

## 日常命令

```powershell
python -m qa.cli                          # 命令行问答（与 POST /api/qa 共用 qa.pipeline.answer）
python -m qa.cli "遵义会议在哪里召开"       # 非交互单次提问
python -m backend.common.export_ontology  # 本体常量变更后重生成前端镜像（不得手改 ontology.js）
```

### 数据链路（改了数据才需要重跑）

```powershell
python -m db.build_seed                       # db/seed_data → data/excel 七表（按本体逐条校验）
python -m eval.core_check --emit              # V3 3.6 交叉复核；--emit 生成待补源名单
python -m db.build_seed                       # 据名单把无原文佐证的条目降为 checked=0
python -m kg.importer.import_all --prune      # 导入并使图谱与 Excel 完全一致
python -m kg.importer.verify                  # V3 3.7 七项指标核对
```

重新采集与抽取（需联网，原始留档会重建到 `data/raw/`）：

```powershell
python -m kg.crawler.ttd_crawler              # DR-12 天天读，366 个日页，间隔 ≥2 秒
python -m kg.extract.parse_ttd                # 解析编年条目
python -m kg.extract.build_corpus             # F9 语料
python -m kg.extract.build_entities           # DR-13 自动实体
python -m kg.extract.build_relations          # DR-14 自动关系
```

### 验收与实验

```powershell
python -m eval.selfcheck_qa           # 离线：15 类意图 / 实体链接三级降级 / 槽位澄清 / 注入防护
python -m eval.selfcheck_api          # 在线：需先启动后端；鉴权三档、问答边界、账号闭环
python -m eval.selfcheck_frs          # FRS 第四章 22 条功能需求 + 第五章 12 条闭环
python -m eval.data_capability        # 数据对功能的支撑度：15 类意图 / 6 个题型各有多少数据
python -m eval.intent_experiment      # 意图分类对比实验（规则 / 朴素贝叶斯 / 线性 SVM）
python -m eval.run_qa200              # 200 条端到端评测
python -m eval.extraction_accuracy    # 自动抽取准确率抽样评估
```

`selfcheck_api` 与 `selfcheck_frs` 的管理员断言需要空白库才能完整验证首登强制改密：
先删 `backend/app.db` 再 `python -m backend.init_db`，否则该条计入 SKIP。

---

## AI 增强模块（可选，P1）

`backend/.env` 配置 `LLM_ENABLED / LLM_BASE_URL / LLM_API_KEY / LLM_MODEL / LLM_TIMEOUT` 后，
`GET /api/config` 返回 `llm_available=true`，问答页右上角才出现开关。未配置时界面与原方案一致。
删除 `llm/` 目录并还原 `.env` 即物理回退，`qa/` 的 try-import 失败视为系统层关闭。
