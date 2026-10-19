# -*- coding: utf-8 -*-
"""
【初学者阅读指南】
    database.py 回答一个问题：“Python 程序怎么和 MySQL 打交道？”

    阅读顺序建议：
        1. 先看 DB 相关的三个方法 query() / query_one() / execute()
           —— 它们是所有 SQL 的执行入口；
        2. 再看 transaction() —— 理解“事务”为什么需要；
        3. 最后看 translate_mysql_error() —— 数据库拒绝时如何给出中文提示。

    会用到的 Python 知识点（都不难，遇到就现学）：
        class           定义“类”，把相关的函数和数据打包在一起
        __init__        构造函数：Database(DB_CONFIG) 创建对象时自动执行
        self            代表“当前这个对象自己”，通过 self.xxx 存取它的属性
        with ... as x:  上下文管理器：进入 with 块时做准备，离开时自动收尾
                        （比如自动关闭数据库连接，哪怕中间出了异常）
        yield           让一个函数变成“生成器”；配合 @contextmanager 装饰器
                        就能自定义 with 语句的行为（yield 之前的代码 = 准备，
                        之后的代码 = 收尾）
        %s              SQL 里的“参数占位符”，真正的值由 PyMySQL 安全地填入，
                        可以防止 SQL 注入攻击
        try/except      捕获异常；raise 主动抛出一个异常
        f"...{变量}..." f-string：把变量的值嵌进字符串里

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

import re                              # 正则表达式：从错误信息里“抠”出关键文字用
from contextlib import contextmanager  # 提供 @contextmanager 装饰器（配合 yield 用）

import pymysql                         # 第三方库：MySQL 的 Python 驱动（pip 安装）
from pymysql.cursors import DictCursor # 游标类型：让查询结果直接变成“字典”


class Database:
    """MySQL 数据库访问对象：持有一份连接配置，按需建立连接。

    线程安全策略：每次操作独占一条连接（用完即关），
    与 app.py 的 ThreadingHTTPServer 多线程模型天然兼容。
    （Web 服务可能同时收到多个请求，如果大家共用一条连接会互相干扰，
    所以干脆每次都新建、用完就关——实验规模下这样做最简单可靠。）
    """

    def __init__(self, config: dict):
        # 构造函数：Database(DB_CONFIG) 时被调用
        # dict(config) 复制一份配置，避免外部代码改了字典影响到这里
        self.config = dict(config)

    # ---- 连接管理 ---------------------------------------------------- #
    def _connect(self, with_db: bool = True):
        """建立一条新连接；with_db=False 时不选库（用于建库脚本）。

        方法名前面的下划线 _connect 表示“内部方法”，
        提醒使用者：一般不要直接调用它。
        """
        cfg = dict(self.config)          # 复制配置（接下来要修改它）
        if not with_db:
            # 有时需要“连上服务器但还没选库”（比如执行 CREATE DATABASE）
            cfg.pop("database", None)    # pop = 从字典里删掉这个键
        cfg["cursorclass"] = DictCursor  # 查询结果直接是 list[dict]，取列名方便
        # pymysql.connect(**cfg) 中的 ** 会把字典展开成关键字参数，
        # 等价于 pymysql.connect(host=..., port=..., user=..., ...)
        return pymysql.connect(**cfg)

    @contextmanager
    def connection(self, with_db: bool = True):
        """普通连接的上下文管理器：离开 with 块自动关闭。

        用法：
            with db.connection() as conn:
                ...使用 conn...
        yield 之前的代码（建立连接）在进入 with 时执行，
        finally 里的代码（关闭连接）在离开 with 时执行——
        哪怕中间出了异常也会关闭，不会造成连接泄漏。
        """
        conn = self._connect(with_db)
        try:
            yield conn               # 把连接“交给”with 块里的代码使用
        finally:
            conn.close()             # 无论成功还是出错，最后都关闭连接

    @contextmanager
    def transaction(self):
        """事务上下文管理器：正常退出 commit，异常退出 rollback。

        “事务”保证多条 SQL 要么全部生效、要么全部撤销。
        典型场景：删除学生时既要删他的选课记录、又要删学生本身，
        如果第二步失败而第一步已生效，数据就不一致了——
        放在同一个事务里就没有这个问题。
        """
        conn = self._connect()
        try:
            yield conn               # 把连接交给 with 块执行若干条 SQL
            conn.commit()            # with 块正常结束 → 提交（真正生效）
        except Exception:
            conn.rollback()          # 中途出错 → 回滚（全部撤销）
            raise                    # raise 重新抛出异常，让上层继续处理
        finally:
            conn.close()

    # ---- 基础操作（嵌入式 SQL 的执行入口，全部使用 %s 参数占位符）---- #
    def query(self, sql: str, args=None) -> list:
        """执行 SELECT，返回 list[dict]。

        例：db.query("SELECT * FROM Student WHERE Sdept=%s", ("CS",))
        返回 [{"Sno": "...", "Sname": "..."}, ...]
        args 是元组/列表，按顺序对应 SQL 里的每个 %s。
        """
        with self.connection() as conn, conn.cursor() as cur:
            cur.execute(sql, args)   # 执行 SQL（args 由驱动安全填充）
            return cur.fetchall()    # 取回全部结果行

    def query_one(self, sql: str, args=None):
        """执行 SELECT，只取第一行；无结果返回 None。

        常用于“判断某某存不存在”“只想要一条记录”的场景。
        """
        rows = self.query(sql, args)
        return rows[0] if rows else None

    def execute(self, sql: str, args=None) -> int:
        """执行单条 INSERT/UPDATE/DELETE，提交并返回受影响行数。

        返回值可以用来判断“到底改没改到数据”。
        """
        with self.connection() as conn, conn.cursor() as cur:
            rows = cur.execute(sql, args)
            conn.commit()            # 写操作必须 commit 才会真正存入数据库
            return rows


# ---------------------------------------------------------------------- #
# MySQL 完整性错误 → 中文提示（“双重验证”第二重的翻译表）
#
# 业务层（services.py）写库被拒时调用 translate_mysql_error()，
# 把主码/唯一/CHECK/外键错误翻译成用户能看懂的提示。
# ---------------------------------------------------------------------- #
# 键 = 约束名（schema.sql 里 CONSTRAINT 后面的名字），值 = 给用户看的说明
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

# CHECK 类约束对应的“字段中文名”，用于拼提示语
_CONSTRAINT_FIELDS = {
    "ck_student_sex": "性别", "ck_student_age": "年龄",
    "ck_sc_grade": "成绩", "ck_course_credit": "学分", "ck_cp": "先修课号",
}

# 属于“完整性约束被拒绝”的 MySQL 错误码（注意：PyMySQL 把 8.0/8.4 的
# CHECK 违规 3819 映射为 OperationalError 而非 IntegrityError，
# 因此业务层捕获范围放宽到 MySQLError，再按错误码区分）
#   1062 主码/唯一键重复   3819 违反 CHECK   1452 外键-引用不存在
#   1451 外键-仍被引用     1048 非空字段为空
INTEGRITY_CODES = {1062, 3819, 1452, 1451, 1048}


def translate_mysql_error(exc) -> tuple[str, str] | None:
    """把数据库写入异常翻译成 (用户提示, 合法范围提示)。

    - 1062 主码/唯一键重复、3819 违反 CHECK、1452/1451 外键、1048 非空；
    - 不属于完整性错误的异常返回 None，由调用方按普通数据库错误处理。
    """
    # MySQL 异常的 args 里：args[0] 是错误码，args[1] 是英文错误描述
    code = exc.args[0] if exc.args else 0
    if code not in INTEGRITY_CODES:
        return None
    text = str(exc.args[1]) if len(exc.args) > 1 else str(exc)

    if code == 1062:                                   # 主码 / 唯一键重复
        # 从英文报错里用正则抠出两样东西：
        #   重复的值（Duplicate entry 'xxx'）和约束名（for key 'yyy'）
        m_val = re.search(r"Duplicate entry '([^']*)'", text)
        m_key = re.search(r"for key '(?:.*\.)?([^'.]+)'", text)
        val = m_val.group(1) if m_val else ""
        key = m_key.group(1) if m_key else ""
        hint = _CONSTRAINT_HINTS.get(key, "数据重复，请勿重复录入")
        return f"数据“{val}”已存在：{hint}", hint

    if code == 3819:                                   # 违反 CHECK 约束
        # 报错形如：Check constraint 'ck_student_sex' is violated.
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
