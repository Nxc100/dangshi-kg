# 数据源入口登记表（data/sources.md）

> 第 1 周试爬（DR-06）时逐一复核可达性并填写；URL 属易变信息，以本表为准，不写死在方案与代码中。
> 采集纪律：只采权威官方公开静态页；请求间隔 ≥ 2 秒；常规浏览器 UA；原始 HTML 全量留档 `data/raw/`；断点续爬 `done.txt`。

## 一、五个数据源（FRS 第三章，2026-09-04 已联网验证存在）

| 编号 | 数据源 | 入口 URL | 可达性 | 编码 | 页面结构备注 | 复核日期 |
|---|---|---|---|---|---|---|
| DR-01 | 《中国共产党一百年大事记》全文页（人民网） | https://cpc.people.com.cn/n1/2021/0628/c64387-32142446.html | 待复核 | GBK（须 `resp.encoding='gbk'`） | 年份加粗标题 + 逐条"日期 + 事件描述"；备用镜像：求是网 https://www.qstheory.cn/yaowen/2021-06/28/c_1127603704.htm | |
| DR-02 | 历次党代会数据库（人民网 / 共产党员网） | http://cpc.people.com.cn/GB/64162/64168/index.html ；https://www.12371.cn/special/lcddh/ | 待复核 | GBK | 老页面含全角数字（如"１９２１年"），须全角→半角归一 | |
| DR-03 | 党史人物纪念馆 / 党史资料库人物栏（人民网） | http://cpc.people.com.cn/GB/69112/index.html ；http://dangshi.people.com.cn/GB/234123/index.html | 待复核 | GBK | 人物专题页含生平、年谱、著作子栏 | |
| DR-04 | 《中国共产党简史》分章全文（中联部党史学习平台） | https://www.idcpc.gov.cn/ztwy/tbtj/jdbnghlc/xxzl/jianshi/ | 待复核 | 待确认 | 第一章至第十章逐章在线正文 | |
| DR-05 | 人民网党史频道"党史大事记"栏目及党代会报告/公报/党章全文子页 | http://cpc.people.com.cn/GB/64162/64164/index.html | 待复核 | GBK | 随 DR-02 一并采集 | |

## 二、LLM 厂商实测记录（第 14 周登记；换厂商只改 backend/.env 三行）

| 厂商 | OpenAI 兼容端点 | 模型名 | 免费额度 | P95 时延 | 内容稳定性 | 结论 | 测试日期 |
|---|---|---|---|---|---|---|---|
| | | | | | | | |
