# -*- coding: utf-8 -*-
"""
一键初始化：换一台机器克隆下来后，跑这一条命令即可把库建好、数据导好。

用法（项目根目录，已激活虚拟环境）：
    python -m db.init_all              # 建 SQLite + 建图谱约束索引 + 导入图谱 + 验收核对
    python -m db.init_all --rebuild    # 另加：先由 db/seed_data 重新生成 data/excel 七表

顺序是有讲究的，写成脚本就是为了不让人记错：
  ① backend/init_db.py   —— 建 SQLite 五张表并预置初始管理员（app.db 不入 Git，必须本地建）
  ② db/build_seed.py     —— 仅 --rebuild 时执行。data/excel 已随仓库提交，正常无需重跑；
                            只有改了 db/seed_data 下的数据才需要重新生成
  ③ import_all --schema --prune —— 先建约束索引再导入；--prune 让图谱与 Excel 完全一致
                            （MERGE 只增不减，不 prune 会残留上一版已删除的实体）
  ④ kg/importer/verify.py —— 对照 V3 3.7 验收线核对，不达标时退出码非 0

前置：Neo4j Desktop 的本地 DBMS 已启动，且 backend/.env 里 NEO4J_PASSWORD 已填。
未配置 .env 时本脚本会直接提示并退出，不会留下半成品。
"""
import argparse
import os
import subprocess
import sys

_ROOT = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

ENV_PATH = os.path.join(_ROOT, "backend", ".env")
ENV_EXAMPLE = os.path.join(_ROOT, "backend", ".env.example")


def precheck():
    """缺 .env 或缺 Neo4j 密码时给出可照做的提示，而不是让后续步骤报连接失败。"""
    if not os.path.exists(ENV_PATH):
        print("缺少 backend/.env。先复制模板再填密码：")
        print("    copy backend\\.env.example backend\\.env")
        print("然后把 Neo4j Desktop 里该 DBMS 的密码填到 NEO4J_PASSWORD=")
        return False
    from backend.config import Config

    if not Config.NEO4J_PASSWORD:
        print("backend/.env 的 NEO4J_PASSWORD 为空，填好后重跑本脚本。")
        return False
    return True


def run(step, module, *args):
    """逐步执行子命令；任一步失败即中止，保证不产生半成品状态。"""
    print("\n=== %s：python -m %s %s ===" % (step, module, " ".join(args)))
    code = subprocess.call([sys.executable, "-m", module] + list(args), cwd=_ROOT)
    if code != 0:
        print("\n%s 失败（退出码 %d），已中止。" % (step, code))
    return code == 0


def main():
    parser = argparse.ArgumentParser(description="一键初始化 SQLite 与 Neo4j 图谱")
    parser.add_argument("--rebuild", action="store_true",
                        help="先由 db/seed_data 重新生成 data/excel 七表（改过种子数据时才需要）")
    args = parser.parse_args()

    if not precheck():
        return 1
    steps = [("① 建 SQLite 并预置管理员", "backend.init_db")]
    if args.rebuild:
        steps.append(("② 重新生成 data/excel 七表", "db.build_seed"))
    steps.append(("③ 建约束索引并导入图谱", "kg.importer.import_all", "--schema", "--prune"))
    steps.append(("④ 数据验收核对", "kg.importer.verify"))

    for step in steps:
        if not run(*step):
            return 1
    print("\n初始化完成。接着启动服务：")
    print("    python -m backend.app          # 后端 http://127.0.0.1:5000")
    print("    cd frontend && npm run dev     # 前端 http://localhost:5173")
    return 0


if __name__ == "__main__":
    sys.exit(main())
