# 基于知识图谱的党史学习智能问答系统 —— 实现方案 V2(Windows 零环境版)

> 适用前提:开发机为 **Windows 10/11(64 位)**,当前**未安装任何开发环境**,开发者从零开始。
> 本版对 V1 方案逐环节复核,凡在"Windows + 零基础环境"条件下存在安装/编译/网络风险的选型,一律替换为**免安装、有官方 Windows 安装包、或纯 pip 预编译轮子**的方案。未提及的部分(数据来源、本体设计、问答管道细节、论文建议)沿用 V1 文档,两份配合使用。

---

## 一、本版相对 V1 的修订点(复核结论先行)

| 环节 | V1 选型 | V2 修订 | 修订原因(Windows/零环境复核结论) |
|---|---|---|---|
| 用户数据库 | MySQL 8 | **默认 SQLite(Python 内置,零安装)**,MySQL 降为可选 | 少装一个服务,少一个 3306 端口/服务管理问题;SQLAlchemy 写法完全一致,若导师要求 MySQL,改一行连接串即可 |
| 图数据库 | Neo4j Community | **Neo4j Desktop(Windows 官方安装包,自带 JDK)** | 免去单独安装/配置 Java 环境这一 Windows 上最常见的卡点 |
| 意图分类对比实验 | BERT(Colab 免费 GPU) | **主线仍为规则;对比实验首选 sklearn SVM/朴素贝叶斯(纯 CPU、秒级训练);小型预训练模型(如 3 层 RoBERTa rbt3)作可选项,CPU 即可微调** | 免费云 GPU 在国内网络下不可靠,不能作为方案依赖项;小数据文本分类用轻量模型在 CPU 上完全可行 |
| 模糊匹配 | 编辑距离(python-Levenshtein) | **rapidfuzz** | rapidfuzz 提供 Windows 预编译 wheel,pip 直装,无需 C++ 编译环境 |
| RAG 向量检索 | text2vec + FAISS | **语料仅数千段落,直接用 sklearn TF-IDF / numpy 余弦相似度**;向量模型作可选项(经国内镜像下载) | 消除 FAISS 与大模型文件下载两个潜在环境风险;检索效果对本规模语料足够 |
| 动态页兜底 | Selenium | **Playwright(`playwright install` 一条命令自动装浏览器)或直接用 Edge + selenium** | 免手动匹配浏览器驱动版本;实际预计用不到(目标站为静态页) |
| Python 包源 / npm 源 / 模型源 | 未细化 | **明确配置清华 pip 镜像、npmmirror、HF 国内镜像** | 零环境 + 国内网络下,不配镜像是最常见的"装不上"原因 |

**复核总结论:V1 的技术路线(图谱 + 模板 KBQA + Flask + Vue)在 Windows 下完全成立,所有组件均有官方 Windows 支持;修订仅为"去掉每一个需要额外配置或依赖境外网络的环节",使零基础环境搭建可在 1–2 天内完成。**

---

## 二、Windows 开发环境从零搭建方案

### 2.1 硬件与系统要求

| 项 | 要求 | 说明 |
|---|---|---|
| 系统 | Windows 10/11,64 位 | — |
| 内存 | ≥ 8 GB | Neo4j 万级三元组 + Flask + 前端 dev server 同开约占 3–4 GB |
| 磁盘 | ≥ 15 GB 可用 | 各软件 + 数据 |
| 网络 | 普通家庭/校园网 | 已为国内网络配置镜像方案 |
| 其他 | 项目放在**纯英文、无空格路径**,如 `D:\graduation\dangshi-kg` | 规避中文路径导致的各类工具异常(Windows 最高频坑) |

### 2.2 安装清单与顺序(共 5 个必装 + 2 个可选,预计 0.5–1 天)

| 序 | 软件 | 版本 | 获取方式 | 必装? | 用途 |
|---|---|---|---|---|---|
| 1 | VS Code | 最新 | 官网 Windows 安装包 | 必装 | 统一开发编辑器(前后端 + 终端) |
| 2 | Python | 3.10 或 3.11(64-bit) | python.org Windows installer | 必装 | 爬虫/抽取/后端/算法 |
| 3 | Node.js | 20 LTS | nodejs.org Windows .msi | 必装 | Vue3 前端 |
| 4 | Neo4j Desktop | 最新(免费,官网填邮箱获激活码) | neo4j.com 下载中心 | 必装 | 图数据库(自带 JDK 与图形界面) |
| 5 | Git for Windows | 最新 | git-scm.com | 必装 | 版本管理(毕设强烈建议,防丢代码) |
| 6 | MySQL 8 | Windows Installer | mysql.com | 可选 | 仅当导师明确要求;默认用 SQLite |
| 7 | Playwright 浏览器 | 随 pip 包 | `pip install playwright` 后 `playwright install chromium` | 可选 | 仅当遇到动态渲染页面 |

> 全部软件均为官方 Windows 安装包,"下一步式"安装,无需手动配置环境变量(Python 安装时勾选 Add to PATH 即可)。

### 2.3 逐步安装与验证(每步给出验证命令与预期结果)

**Step 1:VS Code**
- 安装后,后续所有命令都在 VS Code 内置终端(默认 PowerShell)执行,避免 cmd/PowerShell 混用带来的困惑。
- 建议安装扩展:Python、Volar(Vue)、Chinese 语言包。

**Step 2:Python(关键勾选项)**
- 运行安装包时**务必勾选 "Add python.exe to PATH"**,其余默认。
- 验证:新开终端执行 `python --version` → 显示 `Python 3.11.x`;`pip --version` 正常输出。
- 配置国内镜像(一次性):
  ```
  pip config set global.index-url https://pypi.tuna.tsinghua.edu.cn/simple
  ```
- 创建项目虚拟环境并激活:
  ```
  cd D:\graduation\dangshi-kg
  python -m venv venv
  venv\Scripts\activate
  ```
  若 PowerShell 提示"禁止运行脚本",执行一次:
  `Set-ExecutionPolicy -Scope CurrentUser RemoteSigned`(选 Y),这是 Windows 零环境第二高频坑。
- 安装本项目全部必需包(均有 Windows 预编译轮子,不会触发本地编译):
  ```
  pip install requests beautifulsoup4 lxml jieba pandas flask flask-cors flask-jwt-extended sqlalchemy neo4j scikit-learn rapidfuzz pypinyin openpyxl
  ```
- 验证:`python -c "import requests,bs4,jieba,flask,neo4j,sklearn,rapidfuzz; print('ok')"` → 输出 `ok`。

**Step 3:Node.js**
- 默认安装(自动进 PATH)。验证:`node -v`(v20.x)、`npm -v`。
- 配置国内镜像:`npm config set registry https://registry.npmmirror.com`
- 验证前端脚手架可用:`npm create vite@latest demo -- --template vue` 能生成项目、`npm install` 无报错、`npm run dev` 能在浏览器打开 localhost:5173 默认页 → 前端链路全通。

**Step 4:Neo4j Desktop**
- 官网下载 Windows 版,安装时会要求粘贴免费激活码(下载页邮件发放)。
- 打开后 New Project → Add Local DBMS(选 5.x 版本)→ 设置密码 → Start。
- 验证:点击 Open(Neo4j Browser),执行:
  ```
  CREATE (a:Person {name:'测试'}) RETURN a
  MATCH (n) RETURN n
  ```
  能看到图形化节点即成功;再在 Python 侧验证驱动连通:
  ```python
  from neo4j import GraphDatabase
  d = GraphDatabase.driver("bolt://localhost:7687", auth=("neo4j","你的密码"))
  print(d.verify_connectivity())
  ```
- 说明:Neo4j Desktop 自带受限 JDK,**无需也不要单独安装 Java**;若个别机器上 Desktop 启动异常,备选方案为"Neo4j Community 5.x zip + Adoptium Temurin JDK17",同为免费官方 Windows 包(此为唯一备用路径,写在这里备查)。

**Step 5:Git**
- 默认安装。验证:`git --version`。项目目录 `git init`,每日提交;可再关联 Gitee(国内访问稳定)做云备份。

**Step 6(可选)MySQL:** 若导师要求,装 MySQL 8 官方 Installer(记住 root 密码),项目中把 SQLAlchemy 连接串从 `sqlite:///app.db` 改为 `mysql+pymysql://...` 并 `pip install pymysql` 即完成切换——代码零改动,这正是默认选 SQLAlchemy 的原因。

### 2.4 国内网络专项配置汇总(零环境高频卡点集中处理)

| 对象 | 配置 | 何时需要 |
|---|---|---|
| pip | 清华镜像(见上) | 必配 |
| npm | npmmirror(见上) | 必配 |
| HuggingFace 模型 | 环境变量 `HF_ENDPOINT=https://hf-mirror.com`,或改从 ModelScope(魔搭)下载 | 仅做可选的 rbt3 微调 / 向量模型时 |
| 大模型 API | 智谱/通义等国内厂商,官网注册取免费额度 key | 仅做可选 RAG 模块时 |
| GitHub 下载(OwnThink 等) | 若克隆缓慢,用其镜像加速站或改用网盘转存 | 仅补充数据时;该数据源本就是"可选补充",不构成依赖 |

### 2.5 Windows 专项避坑清单(写进论文"系统实现"更显工程完整性)

1. **路径与编码:** 项目全程英文路径;所有 Python 文件读写显式 `encoding='utf-8'`;导出给 Excel 看的 CSV 用 `utf-8-sig`,否则中文乱码。
2. **终端编码:** 若在终端打印中文乱码,统一用 VS Code 终端并确保文件为 UTF-8;必要时 `chcp 65001`。
3. **端口占用:** 本项目占用 7474/7687(Neo4j)、5000(Flask)、5173(Vite)。冲突时 `netstat -ano | findstr 5000` 查 PID 处理,或改端口。
4. **防火墙弹窗:** 首次运行 Flask/Vite,Windows 防火墙弹窗选择"允许"。
5. **杀毒软件误报:** 个别安全软件会拦截 venv 内 exe,添加项目目录为信任即可。
6. **长路径/权限:** 不要把项目放在 C:\Program Files 或桌面 OneDrive 同步目录下,避免权限与同步锁文件问题。

### 2.6 环境搭建完成的总验证(半天内应全部打勾)

- [ ] `python --version` / `pip install` 走镜像成功
- [ ] `node -v`,Vite 默认页可打开
- [ ] Neo4j Browser 可建节点、Python 驱动连通
- [ ] Flask 最小应用 `hello world` 可访问 `http://127.0.0.1:5000`
- [ ] `git commit` 成功一次

**结论:上述每一步只依赖官方 Windows 安装包与国内镜像,单人 0.5–1 天可全部完成;环境层面不存在需要编译源码、手工配环境变量或依赖境外网络的环节。**

---

## 三、系统功能再校验(逐项确保高可行)

复核原则:每个功能都必须满足 ① 只依赖第 2 节已装环境;② 有明确的"最小实现路径"(即使按最保守方式做也能完成并可演示);③ 有验证方式;④ 若含任何不可控外部依赖,必须降为"开关式可选"。按此原则,对 V1 功能表逐项复核并微调如下。

### 3.1 功能可行性总表

| 编号 | 功能 | 最小实现路径 | 依赖 | 预估工作量 | 可行性 | 验证方式 |
|---|---|---|---|---|---|---|
| F1 | 智能问答 | 词典实体链接(rapidfuzz 容错)+ 关键词规则意图分类 + 15–20 个 Cypher 模板 + 中文回答模板 | jieba、rapidfuzz、neo4j 驱动 | 10–14 人日 | **高** | 200 条测试问句端到端评测,目标 ≥ 80% |
| F2 | 图谱可视化 | 后端返回检索实体 2 跳子图 JSON,前端 ECharts graph 力导向渲染;点击节点请求邻居追加 | ECharts(npm 安装) | 4–5 人日 | **高** | 检索任一实体出图、点击可扩展、类型着色正确 |
| F3 | 大事记时间轴 | 事件实体带 `period`(时期)与 `time` 属性,按时期查询排序;前端 Element Plus Timeline 组件 | 图谱数据 | 2 人日 | **高** | 七个时期均能列出事件且按时间有序 |
| F4 | 实体百科页 | 一个接口返回实体属性 + 分组邻居;前端表格 + 标签 + 局部小图 | 同上 | 3 人日 | **高** | 抽 20 个实体页面信息完整无错 |
| F5 | 用户模块 | SQLite + SQLAlchemy 三张表(user / favorite / qa_log),JWT 登录态 | flask-jwt-extended | 3 人日 | **高** | 注册→登录→提问入日志→收藏→退出全流程走通 |
| F6 | 后台知识管理 | 三元组/实体的增删改查接口 + Element Plus 表格页;操作直接落 Neo4j | 同上 | 4 人日 | **高** | 后台改一条属性,前台问答与百科页即时生效 |
| F7 | 党史知识测验 | 出题=对高质量三元组"挖空":以(会议,时间/地点)、(事件,领导人)等模板生成题干,干扰项从**同类型实体**随机抽 3 个;答题记录入 SQLite | 纯查询逻辑,零新依赖 | 3 人日 | **高** | 连出 50 题人工检查:无病句、答案唯一、干扰项不含正确答案 |
| F8 | 每日学习 | 实现为两部分:①"今日推荐"随机推送 1 个核心实体卡片(必成);②"历史上的今天"仅对**具有精确月日**的事件启用,无匹配时自动回退到推荐卡片 | 图谱数据 | 1–2 人日 | **高**(已消除"多数事件无精确日期"的风险) | 连续换 10 个日期均有合理输出 |
| F9 | 大模型增强问答(可选开关) | 图谱未命中 → TF-IDF 检索语料 top3 段落:**无 key 时直接展示原文段落(此路径零外部依赖,恒可用)**;有 key 时把段落交国产大模型改写作答,并标注"AI 生成" | sklearn(已装);API key(可选) | 3 人日 | **高**(因为"展示原文段落"这条保底路径不依赖任何外部服务) | 断网/无 key 状态下功能仍可演示 |
| F10 | 热点统计 | 对 qa_log 表 GROUP BY 聚合,ECharts 柱图/词云 | SQLite + ECharts | 1–2 人日 | **高** | 造 100 条日志,统计图与数据一致 |

> 合计约 34–41 人日纯开发量,分布在 16 周计划的第 8–14 周,节奏宽松。**十项功能全部达到"高可行"**,其中 F8、F9 通过"内置保底路径"设计消除了 V1 中的隐性风险(日期缺失、外部 API 不可用)。

### 3.2 需要特别说明的三个设计决策

1. **F1 不承诺开放域自由问答。** 系统能力边界=意图模板库覆盖范围,超出即走 F9 兜底(检索原文段落)。在开题报告中即写明该边界,答辩不会被"问啥都要会"的期待反噬——这是问答类毕设最重要的自我保护。
2. **F7 出题只用"人工校验过的核心三元组"**(V1 中承诺 100% 校验的约 500 核心实体),从源头保证题目与答案不出错——党史领域出错题的代价远高于普通领域。
3. **F9 的保底路径(展示权威原文段落)本身就是合格的功能形态**,大模型改写只是体验增强。因此即使完全不接大模型,功能列表也不缺项。

---

## 四、技术栈修订总表(V2 · Windows 定稿)

| 环节 | 定稿选型 | 安装方式 | Windows 风险复核 |
|---|---|---|---|
| 编辑器 | VS Code | 官方安装包 | 无 |
| 语言 | Python 3.10/3.11、Node 20 LTS | 官方安装包 | 无(勾选 PATH) |
| 爬虫 | requests + BeautifulSoup4 + lxml | pip(预编译轮子) | 无 |
| 分词/匹配 | jieba + 自定义词典;rapidfuzz 模糊纠错;pypinyin | pip | 无(均纯轮子) |
| 意图分类 | 主线:关键词规则;对比实验:sklearn SVM / 朴素贝叶斯;可选:rbt3 小模型 CPU 微调 | pip(sklearn 已装;torch/transformers 仅可选时装 CPU 版) | 主线与对比实验零风险;可选项失败不影响 |
| 图数据库 | Neo4j Desktop(内置 JDK) | 官方安装包 | 无需装 Java;备选 zip+JDK17 |
| Python↔Neo4j | neo4j 官方 driver | pip | 无 |
| 用户库 | SQLite(默认)/ MySQL 8(可选) | 内置 / 官方安装包 | SQLite 零安装 |
| ORM | SQLAlchemy | pip | 无;保证 SQLite↔MySQL 无痛切换 |
| 后端 | Flask + flask-cors + flask-jwt-extended | pip | 无 |
| 前端 | Vue3 + Vite + Element Plus + ECharts + axios | npm(npmmirror) | 无 |
| RAG 检索(可选) | sklearn TF-IDF + 余弦相似度 | 已装 | 无(替代 FAISS) |
| 大模型(可选) | 国产大模型 API 免费额度 | requests 调用 | 开关式,不可用即回退 |
| 版本管理 | Git(+Gitee 远程) | 官方安装包 | 无 |

---

## 五、数据获取环节的 Windows 适配确认

V1 第四节的数据来源与采集方案**全部与操作系统无关**(requests/bs4 跨平台),仅补充三条 Windows 落地要点:

1. 采集脚本统一 `encoding='utf-8'` 读写,原始页面另存为 `data/raw/*.html` 留档(论文可展示数据处理链路,也便于解析规则调整后离线重跑,不必二次爬取);
2. 长任务(逐词条抓百科)写成断点续爬:已抓 URL 记录到本地 `done.txt`,Windows 睡眠/断网后重启脚本自动续传;
3. V1 的 4.4 试爬验证照常执行,零环境下这也是对"Python + requests + 解析"整条工具链的首次实战验证,一举两得。

---

## 六、修订后的 16 周计划(含环境搭建)

| 周次 | 任务 | 里程碑 |
|---|---|---|
| 1 | **前 2 天:按第 2 节从零搭环境并通过 2.6 总验证**;随后文献调研、试爬验证 | 环境自检清单全勾;试爬报告 |
| 2 | 需求分析、本体设计、开题 | 开题报告 |
| 3–4 | 全量采集与清洗 | 原始数据落盘 |
| 5–6 | 三元组抽取 + 别名表 + 抽样校验 | 抽取准确率达标 |
| 7 | 核心实体人工校验;Neo4j 导入建索引 | 图谱可查询 |
| 8–9 | F1 问答引擎命令行版 | **中期检查:命令行问答演示** |
| 10 | 问句数据集;SVM 对比实验(+可选 rbt3) | 分类对比表 |
| 11–12 | Flask 全部接口 + F5 用户模块(SQLite) | Postman 联调通过 |
| 12–13 | 前端五页面 + F2/F3/F4 可视化 | 系统可用 |
| 14 | F6/F7/F8/F10 + 可选 F9;端到端 200 问评测 | 实验数据齐备 |
| 15 | 测试修复、录演示视频 | 系统冻结 |
| 16 | 论文收尾、查重、答辩准备 | 提交 |

---

## 七、逐环节可行性结论汇总(V2 复核签收表)

| 环节 | Windows 零环境下的关键风险 | 消除方式 | 结论 |
|---|---|---|---|
| 环境搭建 | PATH/镜像/执行策略/中文路径 | 第 2 节逐条给出操作与验证命令 | 可行,0.5–1 天 |
| 数据采集 | 与 OS 无关;编码坑 | utf-8 规范 + 断点续爬 | 可行 |
| 图谱构建 | Java 依赖 | Neo4j Desktop 内置 JDK | 可行 |
| 问答引擎 | 深度学习环境不确定性 | 主线纯规则;对比实验用 sklearn;深模型仅可选 | 可行 |
| 前后端 | 无特有风险 | 官方安装包 + 镜像 | 可行 |
| 十项功能 | F8 日期缺失、F9 外部 API | 内置保底路径(3.1 表) | 全部高可行 |
| 演示答辩 | 单机资源 | 8G 内存实测足够;演示全部本机运行,不依赖网络(F9 走保底路径) | 可行 |

---

## 附:第 1 周落地命令速查(环境装完后 2–3 天跑通最小闭环)

```
:: 1) 项目初始化
mkdir D:\graduation\dangshi-kg && cd /d D:\graduation\dangshi-kg
python -m venv venv && venv\Scripts\activate
pip install requests beautifulsoup4 lxml jieba pandas flask flask-cors flask-jwt-extended sqlalchemy neo4j scikit-learn rapidfuzz pypinyin openpyxl

:: 2) 最小验证脚本(各写 20 行以内)
:: crawl_test.py  -> 抓 1 个大事记列表页,正则切出 时间+事件名 打印
:: baike_test.py  -> 抓 1 个人物词条,解析 infobox 为 dict 打印
:: neo4j_test.py  -> 写入 5 个节点 2 条关系,再查询打印
:: qa_min.py      -> 词典匹配实体 + 3 条意图规则 + 3 个 Cypher 模板,
::                   命令行输入"遵义会议在哪召开"返回"遵义"
```

四个脚本全部跑通,即宣告"环境 + 数据 + 图谱 + 问答"整条技术路线在你的 Windows 机器上端到端验证完毕,其后 15 周均为在已验证骨架上的扩量与完善。
