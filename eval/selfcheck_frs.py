# -*- coding: utf-8 -*-
"""
FRS 功能验收自检：逐条核对《功能需求文档 FRS V1.0》第四章 22 条功能需求的验收标准。

覆盖 FR-G01~G08（游客）、FR-U01~U07（注册用户）、FR-A01~A07（管理员）。
断言按需求编号分组，失败时直接给出「FR 编号 + 验收项」，可对回文档条目。

前置：后端已启动（python -m backend.app）；建议先重置为空白库以完整验证
admin 首登强制改密链路：删除 backend/app.db 后 python -m backend.init_db。
图谱未导入数据时，依赖图谱的断言自动计入 SKIP，不判为失败。

用法（项目根目录）：python -m eval.selfcheck_frs [admin 初始口令]
退出码 0 表示全部验收项达标。
"""
import os
import sys

import requests

_ROOT = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

from backend.config import Config  # noqa: E402
from eval.frs import admin, guest, loops, user  # noqa: E402
from eval.frs.harness import Checker, graph_ready  # noqa: E402

BASE = os.environ.get("API_BASE") or "http://127.0.0.1:%d/api" % Config.PORT
ADMIN_NEW_PWD = "Frsadmin2026"


def main():
    init_pwd = sys.argv[1] if len(sys.argv) > 1 else (Config.ADMIN_INIT_PASSWORD or "")
    c = Checker(BASE)
    try:
        c.get("/health")
    except requests.RequestException:
        print("后端未启动：%s 不可达。请先运行 python -m backend.app" % BASE)
        return 2

    kg = graph_ready(c)
    print("=" * 96)
    print("FRS 功能验收自检  目标 %s" % BASE)
    print("图谱：%s" % ("已导入数据" if kg else "无数据（图谱相关断言跳过）"))
    print("=" * 96)

    guest_ctx = guest.run(c, kg)
    user_ctx = user.run(c, kg, guest_ctx)
    # 用改密后的口令重新取一份普通用户请求头，供管理员越权用例使用
    body = c.post("/auth/login", json={"username": user_ctx["username"],
                                       "password": user_ctx["password"]}).json()
    user_h = c.auth(body["data"]["token"]) if body.get("code") == 0 else {}
    admin_h = admin.run(c, kg, init_pwd, ADMIN_NEW_PWD, user_h, user_ctx["username"])

    print()
    print("=" * 96)
    print("FRS 第五章 功能闭环校验表（整体验收必测）")
    print("=" * 96)
    loops.run(c, kg, admin_h)
    return c.summary()


if __name__ == "__main__":
    sys.exit(main())
