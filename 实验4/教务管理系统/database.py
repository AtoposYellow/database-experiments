# -*- coding: utf-8 -*-
"""
数据层（database.py）：一切与 MySQL 本身打交道的代码。

职责边界：
    负责 —— 连接管理、查询/事务执行、把 MySQL 完整性约束错误
             翻译成中文提示（供业务层使用）；
    不负责 —— 建库建表（DDL 在 MySQL 端的 schema.sql 中执行）、
               业务规则与输入校验（在 services.py / models.py）。

架构总览（5 个模块，一个文件一个职责，调用方向自上而下）：
    config.py     配置层：数据库连接、端口、路径等全部可配置项
    database.py   数据层：连接管理 / 事务 / MySQL错误翻译            ← 本文件
    models.py     实体层：实体类与输入校验（双重验证第一重）
    services.py   业务层：六大功能的嵌入式 SQL（双重验证第二重）
    app.py        界面层：HTTP 服务与 REST 路由、程序入口
"""

import re
from contextlib import contextmanager

import pymysql
from pymysql.cursors import DictCursor


class Database:
    """MySQL 数据库访问对象：持有一份连接配置，按需建立连接。

    线程安全策略：每次操作独占一条连接（用完即关），
    与 app.py 的 ThreadingHTTPServer 多线程模型天然兼容。
    """

    def __init__(self, config: dict):
        self.config = dict(config)

    # ---- 连接管理 ---------------------------------------------------- #
    def _connect(self, with_db: bool = True):
        """建立一条新连接；with_db=False 时不选库（用于建库脚本）。"""
        cfg = dict(self.config)
        if not with_db:
            cfg.pop("database", None)
        cfg["cursorclass"] = DictCursor   # 查询结果直接是 list[dict]
        return pymysql.connect(**cfg)

    @contextmanager
    def connection(self, with_db: bool = True):
        """普通连接的上下文管理器：离开 with 块自动关闭。"""
        conn = self._connect(with_db)
        try:
            yield conn
        finally:
            conn.close()

    @contextmanager
    def transaction(self):
        """事务上下文管理器：正常退出 commit，异常退出 rollback。
        课程维护里“改课程 + 重建先修关系”这类组合操作必须放在一个事务里。"""
        conn = self._connect()
        try:
            yield conn
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()

    # ---- 基础操作（嵌入式 SQL 的执行入口，全部使用 %s 参数占位符）---- #
    def query(self, sql: str, args=None) -> list:
        """执行 SELECT，返回 list[dict]。"""
        with self.connection() as conn, conn.cursor() as cur:
            cur.execute(sql, args)
            return cur.fetchall()

    def query_one(self, sql: str, args=None):
        """执行 SELECT，只取第一行；无结果返回 None。"""
        rows = self.query(sql, args)
        return rows[0] if rows else None

    def execute(self, sql: str, args=None) -> int:
        """执行单条 INSERT/UPDATE/DELETE，提交并返回受影响行数。"""
        with self.connection() as conn, conn.cursor() as cur:
            rows = cur.execute(sql, args)
            conn.commit()
            return rows


# ---------------------------------------------------------------------- #
# MySQL 完整性错误 → 中文提示（“双重验证”第二重的翻译表）
#
# 业务层（services.py）写库被拒时调用 translate_mysql_error()，
# 把主码/唯一/CHECK/外键错误翻译成用户能看懂的提示。
# ---------------------------------------------------------------------- #
_CONSTRAINT_HINTS = {
    "pk_student":       "学号不能重复",
    "uk_student_sname": "姓名是候选码（UNIQUE 约束），不能与其他学生重名",
    "ck_student_sex":   "性别只能是「男」或「女」",
    "ck_student_age":   "年龄必须是大于 0 的整数",
    "pk_course":        "课程号不能重复",
    "pk_sc":            "同一学生同一课程只能有一条选课记录",
    "ck_sc_grade":      "成绩必须在 0～100 之间（空值表示暂未录入）",
    "ck_course_credit": "学分必须在 0～10 之间",
    "ck_cp":            "课程不能以自身为先修课",
}

_CONSTRAINT_FIELDS = {
    "ck_student_sex": "性别", "ck_student_age": "年龄",
    "ck_sc_grade": "成绩", "ck_course_credit": "学分", "ck_cp": "先修课号",
}

# 属于“完整性约束被拒绝”的 MySQL 错误码（注意：PyMySQL 把 8.0/8.4 的
# CHECK 违规 3819 映射为 OperationalError 而非 IntegrityError，
# 因此业务层捕获范围放宽到 MySQLError，再按错误码区分）
INTEGRITY_CODES = {1062, 3819, 1452, 1451, 1048}


def translate_mysql_error(exc) -> tuple[str, str] | None:
    """把数据库写入异常翻译成 (用户提示, 合法范围提示)。

    - 1062 主码/唯一键重复、3819 违反 CHECK、1452/1451 外键、1048 非空；
    - 不属于完整性错误的异常返回 None，由调用方按普通数据库错误处理。
    """
    code = exc.args[0] if exc.args else 0
    if code not in INTEGRITY_CODES:
        return None
    text = str(exc.args[1]) if len(exc.args) > 1 else str(exc)

    if code == 1062:                                   # 主码 / 唯一键重复
        m_val = re.search(r"Duplicate entry '([^']*)'", text)
        m_key = re.search(r"for key '(?:.*\.)?([^'.]+)'", text)
        val = m_val.group(1) if m_val else ""
        key = m_key.group(1) if m_key else ""
        hint = _CONSTRAINT_HINTS.get(key, "数据重复，请勿重复录入")
        return f"数据“{val}”已存在：{hint}", hint

    if code == 3819:                                   # 违反 CHECK 约束
        m = re.search(r"constraint '([^']+)'", text)
        name = m.group(1) if m else ""
        hint = _CONSTRAINT_HINTS.get(name, "违反检查(CHECK)约束")
        field = _CONSTRAINT_FIELDS.get(name, "该字段")
        return f"{field}取值非法：{hint}", hint

    if code == 1452:                                   # 外键：引用不存在
        return ("引用的记录不存在（违反外键约束）",
                "请先确认学号 / 课程号 / 先修课号已经存在于对应表中")
    if code == 1451:                                   # 外键：仍被引用
        return ("该记录仍被其他数据引用，不能删除或修改（违反外键约束）",
                "请先删除引用它的选课记录或先修关系")
    # 1048：非空约束
    return ("必填字段为空（NOT NULL 约束）", "请补全所有必填项")
