# -*- coding: utf-8 -*-
"""5.5.1 数据库连接测试：连上 sms 库，确认四张表已就绪。"""

import pymysql

from config import DB_CONFIG

conn = pymysql.connect(**DB_CONFIG)
try:
    with conn.cursor() as cur:
        cur.execute("SELECT VERSION(), DATABASE()")
        version, db = cur.fetchone()
        print(f"连接成功：MySQL {version}，当前库 {db}，客户端字符集 {DB_CONFIG['charset']}")

        cur.execute("SHOW TABLES")
        tables = "、".join(sorted(row[0] for row in cur.fetchall()))
        print(f"sms 库中的表：{tables}")

        for t in ("student", "course", "sc", "cp"):
            cur.execute(f"SELECT COUNT(*) FROM `{t}`")
            print(f"  {t:<8}{cur.fetchone()[0]:>4} 行")
finally:
    conn.close()
