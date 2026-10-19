# -*- coding: utf-8 -*-
"""SMS 库的连接与常用操作封装（Python 3.15 + PyMySQL）

用法：
    import db
    db.query("SELECT * FROM student")                 # 查询，返回 list[dict]
    db.execute("UPDATE sc SET Grade=%s WHERE Sno=%s", (88, "202215121"))
"""

import pymysql
from pymysql.cursors import DictCursor

# ---- 连接参数：只改这里 ----------------------------------------------
CONFIG = {
    "host": "127.0.0.1",
    "port": 3306,
    "user": "root",
    "password": "root",      # 你的 root 密码
    "database": "sms",       # 新建的库（MySQL 里存为小写 sms）
    "charset": "utf8mb4",    # 中文必须 utf8mb4，否则会乱码
    "cursorclass": DictCursor,   # 查询结果直接是字典，取字段方便
    "connect_timeout": 5,
    "autocommit": False,     # 显式提交，便于回滚
}


def get_conn():
    """建立一条新连接（用完要 close；每次操作新建连接最省心）"""
    return pymysql.connect(**CONFIG)


def query(sql, args=None):
    """执行 SELECT，返回 list[dict]"""
    conn = get_conn()
    try:
        with conn.cursor() as cur:
            cur.execute(sql, args)
            return cur.fetchall()
    finally:
        conn.close()


def query_one(sql, args=None):
    """执行 SELECT，只取第一行（没有则返回 None）"""
    rows = query(sql, args)
    return rows[0] if rows else None


def execute(sql, args=None):
    """执行 INSERT / UPDATE / DELETE，返回受影响行数；出错回滚并抛出"""
    conn = get_conn()
    try:
        with conn.cursor() as cur:
            rows = cur.execute(sql, args)
        conn.commit()
        return rows
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


if __name__ == "__main__":
    info = query_one("SELECT VERSION() AS ver, DATABASE() AS db, "
                     "@@character_set_client AS cs")
    print("连接成功：MySQL %s，当前库 %s，客户端字符集 %s"
          % (info["ver"], info["db"], info["cs"]))

    print("表：", [list(r.values())[0] for r in query("SHOW TABLES")])
    for t in ("student", "course", "sc", "cp"):
        n = query_one("SELECT COUNT(*) AS n FROM %s" % t)["n"]
        print("  %-8s %d 行" % (t, n))
