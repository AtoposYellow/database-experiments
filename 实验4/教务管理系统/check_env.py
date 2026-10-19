# -*- coding: utf-8 -*-
"""
环境自检脚本：检查能否正常运行 / 测试教务管理系统。

检查项（按顺序）：
  1. Python 版本 >= 3.10
  2. PyMySQL 已安装
  3. MySQL 服务器可连接（账号密码见 config.py）
  4. sms 库与 Student/Course/SC/CP 四张表存在且有数据
  5. Web 服务是否已在 8000 端口运行（软检查，仅提示）

用法：
  python check_env.py        任一硬检查失败时退出码为 1
"""

import sys

try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

BASE = "http://127.0.0.1:8000"
HARD_FAIL = False


def item(ok: bool, text: str, hint: str = ""):
    """打印一项检查结果；硬失败置全局标记。"""
    global HARD_FAIL
    mark = "√" if ok else "×"
    print(f"  {mark} {text}")
    if not ok:
        HARD_FAIL = True
        if hint:
            print(f"     → 解决办法：{hint}")


def soft(ok: bool, text: str, hint: str = ""):
    """软检查：不通过不算失败，只给提示。"""
    print(f"  {'√' if ok else '！'} {text}")
    if not ok and hint:
        print(f"     → 提示：{hint}")


print("=" * 52)
print("教务管理系统 环境自检")
print("=" * 52)

# ---- 1. Python 版本 -------------------------------------------------- #
v = sys.version_info
item(v >= (3, 10), f"Python 版本 {v.major}.{v.minor}.{v.micro}",
     "需 Python 3.10 及以上（当前 " + sys.executable + "）")

# ---- 2. PyMySQL ------------------------------------------------------ #
try:
    import pymysql
    item(True, f"PyMySQL 已安装（{pymysql.__version__}）")
except Exception as e:
    item(False, "PyMySQL 未安装", f"pip install pymysql  （报错：{e}）")

# ---- 3. MySQL 连接 --------------------------------------------------- #
from config import DB_CONFIG

conn = None
if not HARD_FAIL:
    try:
        conn = pymysql.connect(host=DB_CONFIG["host"], port=DB_CONFIG["port"],
                               user=DB_CONFIG["user"],
                               password=DB_CONFIG["password"],
                               charset="utf8mb4", connect_timeout=5)
        item(True, f"MySQL 可连接（{DB_CONFIG['host']}:{DB_CONFIG['port']}，"
                   f"服务器版本 {conn.get_server_info()}）")
    except Exception as e:
        item(False, f"MySQL 连接失败：{e}",
             "确认 MySQL 服务已启动、config.py 里的 user/password 正确")

# ---- 4. sms 库与四张表 ----------------------------------------------- #
if conn is not None:
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT COUNT(*) FROM information_schema.SCHEMATA "
                        "WHERE SCHEMA_NAME = %s", (DB_CONFIG["database"],))
            has_db = cur.fetchone()[0] == 1
            if not has_db:
                item(False, f"数据库 {DB_CONFIG['database']} 不存在",
                     "在 DataGrip 中执行 schema.sql 建库（建表属逻辑设计，不在 Python 中）")
            else:
                counts = {}
                for t in ("student", "course", "sc", "cp"):
                    cur.execute(f"SELECT COUNT(*) FROM `{DB_CONFIG['database']}`.`{t}`")
                    counts[t] = cur.fetchone()[0]
                ok = all(n > 0 for n in counts.values())
                item(ok,
                     f"sms 库四张表就绪（student {counts['student']} / course "
                     f"{counts['course']} / sc {counts['sc']} / cp {counts['cp']} 行）",
                     "表为空：在 DataGrip 中重新执行 schema.sql 灌入示例数据")
    except Exception as e:
        item(False, f"表检查失败：{e}", "在 DataGrip 中重新执行 schema.sql")
    finally:
        conn.close()

# ---- 5. Web 服务（软检查） -------------------------------------------- #
try:
    import urllib.request
    with urllib.request.urlopen(BASE + "/api/ping", timeout=2) as r:
        info = r.json() if hasattr(r, "json") else None
    soft(True, "Web 服务已在 http://127.0.0.1:8000 运行")
except Exception:
    soft(False, "Web 服务未启动（跑 test_api.py 前需要启动）",
         "python app.py  （或双击 启动系统.bat）")

print("-" * 52)
if HARD_FAIL:
    print("结论：环境未就绪，请按上面的解决办法处理后重试。")
    sys.exit(1)
print("结论：环境就绪，可以正常测试。")
