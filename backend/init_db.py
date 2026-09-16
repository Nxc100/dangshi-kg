# -*- coding: utf-8 -*-
"""
建表 + 预置管理员（可重复执行）。用法（项目根目录）：python -m backend.init_db

- 预置 1 个 role=admin 账号（用户名 admin），must_change_pwd=1，首登仅可访问改密页；
- 初始密码取环境变量 ADMIN_INIT_PASSWORD（backend/.env）；未设置则生成随机密码打印终端一次；
- 页面不作任何初始密码提示；密码只存 werkzeug 加盐哈希。
"""
import os
import secrets
import string
import sys

_ROOT = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

from werkzeug.security import generate_password_hash  # noqa: E402

ADMIN_USERNAME = "admin"


def ensure_schema():
    """create_all 幂等建表（五表）。"""
    from backend import models  # noqa: F401 —— 注册模型
    from backend.extensions import Base, engine

    Base.metadata.create_all(engine)


def _random_password(length=12):
    alphabet = string.ascii_letters + string.digits
    while True:
        pwd = "".join(secrets.choice(alphabet) for _ in range(length))
        if any(c.isalpha() for c in pwd) and any(c.isdigit() for c in pwd):
            return pwd


def seed_admin(init_password=None):
    """不存在 admin 时创建；返回明文初始密码（仅用于终端打印一次），已存在返回 None。"""
    from backend.extensions import db_session
    from backend.models import User

    if db_session.query(User).filter_by(username=ADMIN_USERNAME).first() is not None:
        return None
    password = init_password or _random_password()
    user = User(
        username=ADMIN_USERNAME,
        pwd_hash=generate_password_hash(password),
        role="admin",
        status=1,
        nickname=ADMIN_USERNAME,
        must_change_pwd=1,
    )
    db_session.add(user)
    db_session.commit()
    return password


def main():
    from backend.app import create_app

    app = create_app(load_resources=False)
    with app.app_context():
        ensure_schema()
        print("SQLite 建表完成：%s" % app.config["SQLITE_PATH"])
        password = seed_admin(app.config["ADMIN_INIT_PASSWORD"] or None)
        if password is None:
            print("管理员 admin 已存在，跳过预置。")
        elif app.config["ADMIN_INIT_PASSWORD"]:
            print("已预置管理员 admin（密码来自 ADMIN_INIT_PASSWORD），首次登录须修改密码。")
        else:
            print("已预置管理员 admin，初始随机密码（仅显示一次，请立即记录）：%s" % password)


if __name__ == "__main__":
    main()
