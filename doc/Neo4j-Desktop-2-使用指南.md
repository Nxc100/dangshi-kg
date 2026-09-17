# Neo4j Desktop 2 使用指南（查看本项目图谱）

> **这份文档是什么：** 面向没用过 Neo4j Desktop 2 的人，说明怎么用它查看、启停、排查本项目的图数据库。
> **这份文档不是什么：** 不是需求或方案文档。需求以 FRS 为准、技术选型与本体以 V3 为准、
> 编码与数据纪律以开发规范为准；本文只讲**操作**，不重复那三份的任何结论。
>
> 文中所有数字与路径均为 2026-09-17 在本机实测所得。

---

## 一、先记住本机的几个坐标

| 项 | 值 |
|---|---|
| Desktop 2 程序 | `D:\aNeoj\Neo4j Desktop 2\Neo4j Desktop 2.exe` |
| Desktop 数据根目录 | `%USERPROFILE%\.Neo4jDesktop2\Data\` |
| 当前实例 ID | `dbms-ce5875b5-cc0f-4e0a-a5bb-cd5bed1b1e56` |
| 实例目录 | `%USERPROFILE%\.Neo4jDesktop2\Data\dbmss\<实例ID>\` |
| Neo4j 版本 | 2026.07.1 |
| 数据库名 | `neo4j`（业务数据都在这里）、`system`（系统库，不要动） |
| Bolt 端口 | `bolt://127.0.0.1:7687` ← 后端 `backend\.env` 连的就是它 |
| HTTP / Browser | `http://localhost:7474` |
| 账号 | 用户 `neo4j`，密码见 `backend\.env` 的 `NEO4J_PASSWORD`（不写在本文里） |

**为什么连接串写 `127.0.0.1` 而不是 `localhost`：** Neo4j 默认只监听 IPv4 回环，
而 Windows 上 `localhost` 会优先解析成 IPv6 的 `::1`，驱动先试 `::1` 被拒再回退，
机器忙的时候这个回退可能超时，表现为「时好时坏的连接失败」。项目里已统一用 `127.0.0.1`。

---

## 二、Desktop 2 界面怎么用

### 2.1 打开与总体布局

双击 `Neo4j Desktop 2.exe`。主界面左侧是**实例（Instance）列表**，本机只有一个，
就是上表那个 `dbms-ce5875b5…`。点它进入详情，能看到：

- **状态标签**：`Running`（绿）/ `Stopped`（灰）
- **版本号**与**连接信息**（Bolt / HTTP 端口）
- **Start / Stop** 按钮
- **Open** 按钮 → 打开查询界面
- **Logs**、**Settings / 配置**等入口

> Desktop 1.x 的「Project → Graph → Manage」那套结构在 2 里没有了，
> 2 是扁平的「实例列表 + 详情页」。网上搜到的 Desktop 1 教程对不上，别照着找。

### 2.2 启动与停止

- **启动**：详情页点 `Start`，等状态变 `Running`（首次启动要十几秒，日志在滚）。
- **停止**：点 `Stop`。停掉后本项目的图谱相关功能会立刻不可用——
  问答降级到 F9 兜底，百科页、图谱可视化、测验会返回「图数据库未连接」。
  后端和账号功能不受影响，这是设计好的降级行为，不是故障。

### 2.3 ⚠️ 一个必然会撞上的坑：store lock

**如果这个实例是在命令行里用 `neo4j.bat console` 起的（不是从 Desktop 点的启动），
Desktop 界面会显示它「已停止」，而它其实正跑着、端口也占着。** 这时候点 `Start` 会报
**store lock / 存储锁**错误——同一个数据目录不允许两个进程同时打开。

怎么判断到底跑没跑（PowerShell）：

```powershell
# 有输出就说明在跑，PID 就是那个 java 进程
netstat -ano | findstr "127.0.0.1:7687"

# 看是哪个进程占着
Get-CimInstance Win32_Process -Filter "Name='java.exe'" |
  Where-Object { $_.CommandLine -like '*Neo4jDesktop2*' } |
  Select-Object ProcessId, @{n='cmd';e={$_.CommandLine.Substring(0,80)}}
```

**处理办法**：先把命令行起的那个进程停掉（`Stop-Process -Id <PID>`，或关掉那个终端窗口），
确认 7687 不再监听，再从 Desktop 点 `Start`。反过来也一样——Desktop 起着的时候别去命令行起。

---

## 三、查本项目的图谱

### 3.1 打开查询界面

两条路，效果一样：

- **Desktop 里**：实例详情页点 `Open`（会打开内置的 Query 界面）
- **浏览器里**：直接开 `http://localhost:7474`，用 `neo4j` + `.env` 里的密码登录

查询框里贴 Cypher，`Ctrl + Enter` 执行。

### 3.2 总览：看数据到底有多少

```cypher
// 各类实体的数量
MATCH (n) RETURN labels(n)[0] AS 类型, count(*) AS 数量 ORDER BY 数量 DESC;

// 各类关系的数量
MATCH ()-[r]->() RETURN type(r) AS 关系, count(*) AS 数量 ORDER BY 数量 DESC;

// 一个数字看总量
MATCH (n) RETURN count(n) AS 节点总数;
MATCH ()-[r]->() RETURN count(r) AS 关系总数;
```

2026-09-17 实测应得：**节点 4406、关系 3526**。对不上说明导入没跑完或跑了别的数据。

### 3.3 核心池：测验与每日推荐只从这里取数

```cypher
// 核心池规模（checked=1 表示经过人工校验）
MATCH (n) WHERE n.checked = 1
RETURN labels(n)[0] AS 类型, count(*) AS 已校验 ORDER BY 已校验 DESC;

// 核心池总数（应为 570）
MATCH (n) WHERE n.checked = 1 RETURN count(n) AS 核心池;
```

### 3.4 七个历史时期：时间轴页的数据来源

```cypher
// 每个时期挂了多少事件，按时期顺序排
MATCH (p:Period)
OPTIONAL MATCH (e)-[:BELONGS_TO]->(p)
RETURN p.order AS 序, p.name AS 时期, count(e) AS 事件数
ORDER BY p.order;
```

七个时期任意一个为 0 都是异常——时间轴那个页签会空掉。

### 3.5 可视化：看一个实体的关系网

Query 界面返回节点和关系时会自动画图，**要看图就把节点和关系都 RETURN 出来**，
只返回属性是画不出来的：

```cypher
// 遵义会议的邻居（这个会看得最清楚）
MATCH (m:Meeting {name:'遵义会议'})-[r]-(n) RETURN m, r, n;

// 毛泽东的两跳关系网，限制 60 条免得糊成一团
MATCH path = (p:Person {name:'毛泽东'})-[*1..2]-() RETURN path LIMIT 60;

// 某个时期下的事件（抽 25 个看看）
MATCH (e)-[r:BELONGS_TO]->(p:Period {name:'土地革命战争时期'})
RETURN e, r, p LIMIT 25;
```

画出来后：滚轮缩放、拖拽移动、**点节点**看它全部属性、双击节点展开它的邻居。

### 3.6 按名字找一条具体知识

```cypher
// 精确找
MATCH (n {name:'南昌起义'}) RETURN labels(n)[0] AS 类型, properties(n) AS 全部属性;

// 模糊找（名字里包含"会议"的会议，取 20 个）
MATCH (m:Meeting) WHERE m.name CONTAINS '会议' RETURN m.name, m.time_text LIMIT 20;

// 看某人的任职
MATCH (p:Person {name:'周恩来'})-[r:HELD_POSITION]->(o:Organization)
RETURN o.name AS 组织, r.position AS 职务;
```

### 3.7 约束与索引：导入前必须先建好

```cypher
SHOW CONSTRAINTS;   // 应有 7 条（七类实体的 name 唯一约束）
SHOW INDEXES;       // 应有 18 条
SHOW DATABASES;     // 看 neo4j / system 两个库的状态，都该是 online
```

这些由 `kg/importer/schema.cypher` 定义，`import_all --schema` 会自动执行，不要手改。

---

## 四、看日志

日志文件在 **`%USERPROFILE%\.Neo4jDesktop2\Data\dbmss\<实例ID>\logs\`**，
Desktop 详情页的 `Logs` 入口看的也是它们：

| 文件 | 看什么 |
|---|---|
| `neo4j.log` | 启动/停止过程、端口绑定、启动失败原因 —— **起不来先看这个** |
| `debug.log` | 详细运行日志，查疑难问题用 |
| `query.log` | 执行过的查询与耗时，排查慢查询 |
| `security.log` | 认证成功/失败 —— **密码错了看这个**，会写 `unauthorized due to authentication failure` |
| `http.log` | HTTP 接口访问记录 |

PowerShell 实时跟踪（相当于 Linux 的 `tail -f`）：

```powershell
Get-Content "$env:USERPROFILE\.Neo4jDesktop2\Data\dbmss\dbms-ce5875b5-cc0f-4e0a-a5bb-cd5bed1b1e56\logs\neo4j.log" -Wait -Tail 30
```

---

## 五、看与改配置

配置文件：`%USERPROFILE%\.Neo4jDesktop2\Data\dbmss\<实例ID>\conf\neo4j.conf`
（Desktop 详情页的设置入口改的也是它）。本机当前的关键值：

| 配置项 | 当前值 | 说明 |
|---|---|---|
| `server.memory.heap.max_size` | `1G` | 堆内存。本项目 4406 节点用不满，不用调 |
| `server.memory.pagecache.size` | `512m` | 页缓存，同上 |
| `server.bolt.enabled` | `true` | 驱动走 Bolt，**必须开**，关了后端就连不上 |
| `server.http.enabled` | `true` | Browser 走 HTTP，关了 7474 打不开 |
| `dbms.security.auth_enabled` | `true` | 认证开关，**别关**，关了等于裸奔 |

**改配置必须重启实例才生效。** 没把握就别动——本项目的数据量对默认配置来说很轻松。

---

## 六、常见问题

**连不上 / 后端报 `Couldn't connect to 127.0.0.1:7687`**
1. `netstat -ano | findstr "7687"` 看端口在不在监听；不在就是实例没起
2. 起了还连不上，看 `neo4j.log` 末尾有没有启动失败
3. 确认 `backend\.env` 里是 `bolt://127.0.0.1:7687` 而不是 `localhost`（见第一节的 IPv6 说明）

**报 `The client is unauthorized due to authentication failure`**
`backend\.env` 里的 `NEO4J_PASSWORD` 和实例的密码对不上。注意 Neo4j 2026.x
**强制密码至少 8 位**，所以短密码根本设不上去——如果你以为自己设了个 6 位的，那它没生效。

**Desktop 显示「已停止」但端口被占**
见 2.3 的 store lock，是命令行起的进程还在。

**端口 7687 / 7474 被别的程序占了**
改 `neo4j.conf` 的 `server.bolt.listen_address` / `server.http.listen_address`，
改完 `backend\.env` 的 `NEO4J_URI` 要跟着改。

**忘记密码**
Desktop 实例详情页有重置密码的入口；改完**记得同步改 `backend\.env`**，否则后端连不上。

**想把图谱清空重来**
```cypher
MATCH (n) DETACH DELETE n;   // ⚠ 删除全部节点与关系，不可撤销
```
然后在项目根目录重新导入：`python -m kg.importer.import_all --schema --prune`。
数据源是随仓库提交的 `data\excel\` 七张表，不需要联网重新采集。

---

## 七、不想开界面？项目自带等价命令

```powershell
python -m kg.importer.test_neo4j    # 连通自检：写 5 节点 2 关系，查询后清理
python -m kg.importer.verify        # 完整体检：七类实体/十类关系计数、溯源覆盖、约束索引、验收结论
python -m eval.data_capability      # 数据对功能的支撑度：15 类意图 / 6 个题型各有多少数据可用
```

`verify` 的输出就是对照 V3 3.7 验收线的那张表，比在界面上一条条敲 Cypher 快得多。

---

## 八、两条别踩的红线

1. **不要手改 `data\excel\` 里的 xlsx**。它是 `python -m db.build_seed` 从 `db\seed_data\`
   生成的，手改会在下次重新生成时被覆盖。要改数据就改 `db\seed_data\` 下的源文件，
   或者走后台的知识管理页（F6），那条路会写操作日志。
2. **不要在 Browser 里直接改业务数据**。后台写操作会同步刷新实体词典并留痕，
   在 Browser 里手写 `SET` / `DELETE` 绕过了这两件事，词典不刷新会让问答链接不到新实体。
   临时试验可以，正式改数据请走 F6 或重新导入。
