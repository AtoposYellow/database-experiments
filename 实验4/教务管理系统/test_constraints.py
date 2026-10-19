# -*- coding: utf-8 -*-
"""
【初学者阅读指南】
    这个脚本故意“绕过 Python 校验”，直接用 SQL 往数据库里塞非法数据，
    用来证明双重验证的第二重（数据库完整性约束）真实有效：
    每条非法 SQL 都应被 MySQL 拒绝并抛出对应错误码，然后打印
    translate_mysql_error() 翻译出的中文提示。所有操作都会被拒绝，
    因此不会改动任何数据，可放心反复运行。

验证双重验证的第二重：绕过 Python 校验，直接向数据库提交非法数据，
确认完整性约束（主码/UNIQUE/CHECK/外键）会拒绝，且错误能被翻译成中文提示。"""
import io
import sys

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
sys.path.insert(0, r"C:\Users\Atopos Yellow\Desktop\大学\大二上学期\数据库实验\实验4\教务管理系统")

import pymysql
from config import DB_CONFIG
from database import Database, INTEGRITY_CODES, translate_mysql_error

db = Database(DB_CONFIG)

CASES = [
    # 注意：这里引用的学号（202510802/202510803）在 test_api.py 中不会被删除，
    # 保证两套测试按"先 API 后约束"的顺序连续执行也能稳定复现。
    ("主码重复（1062）",
     "INSERT INTO Student (Sno, Sname, Ssex, Sage, Sdept, Scholarship) "
     "VALUES ('202510802', '新同学', '男', 20, '网络空间安全学院', '否')"),
    ("姓名违反 UNIQUE（1062）",
     "INSERT INTO Student (Sno, Sname, Ssex, Sage, Sdept, Scholarship) "
     "VALUES ('202510899', '郑皓宇', '男', 20, '网络空间安全学院', '否')"),
    ("性别违反 CHECK（3819）",
     "INSERT INTO Student (Sno, Sname, Ssex, Sage, Sdept, Scholarship) "
     "VALUES ('202510831', '测试者', '未知', 20, '网络空间安全学院', '否')"),
    ("年龄违反 CHECK（3819）",
     "INSERT INTO Student (Sno, Sname, Ssex, Sage, Sdept, Scholarship) "
     "VALUES ('202510832', '测试者2', '男', -5, '网络空间安全学院', '否')"),
    ("成绩越界违反 CHECK（3819）",
     "UPDATE SC SET Grade = 120 WHERE Sno = '202510803' AND Cno = '1'"),
    ("选课引用不存在学生（1452）",
     "INSERT INTO SC (Sno, Cno, Grade) VALUES ('999999999', '1', 80)"),
    ("先修课不存在（1452）",
     "INSERT INTO CP (Cno, Cpno) VALUES ('2', '99')"),
    ("删除仍被选修的课程（1451）",
     "DELETE FROM Course WHERE Cno = '1'"),
    ("以自身为先修违反 CHECK（3819）",
     "INSERT INTO CP (Cno, Cpno) VALUES ('2', '2')"),
]

ok = 0
for name, sql in CASES:
    try:
        with db.connection() as conn, conn.cursor() as cur:
            cur.execute(sql)
        print(f"  × {name}：居然成功了！约束未生效！")
    except pymysql.err.MySQLError as e:
        if e.args[0] not in INTEGRITY_CODES:
            raise
        msg, hint = translate_mysql_error(e)
        code = e.args[0]
        print(f"  √ {name} [MySQL {code}] 被拒绝 -> “{msg}”（{hint}）")
        ok += 1

print(f"\n结论：{ok}/{len(CASES)} 项非法数据全部被数据库完整性约束拦截。")
sys.exit(0 if ok == len(CASES) else 1)
