# -*- coding: utf-8 -*-
"""
【初学者阅读指南】
    services.py 是“干活最多”的文件：六大功能的具体实现都在这里。
    每个功能 = 一个方法；每个方法里都有可直接阅读的 SQL 语句
    （这就是“嵌入式 SQL”——宿主语言 Python 中嵌入 SQL）。

    每个写库方法的套路完全一样，看懂第一个就全懂了：
        ① stu.validate()            → 第一重校验（models.py）
        ② 若干 query_one() 查重/预检 → 提前给出友好错误
        ③ db.execute(SQL, 参数)      → 真正读写数据库
        ④ except MySQLError          → 数据库约束拒绝时翻译成中文（第二重）

    会用到的 Python 知识点：
        类的继承    class StudentService(_ServiceBase):
                    括号里写父类，子类自动拥有父类的 __init__ 等方法
        异常链      raise _biz(e) from e
                    “from e”表示新异常是由 e 引起的，便于调试追溯
        元组/列表   (a, b) 元组不可变，按位置对应 SQL 的 %s；
                    [x for x in 列表 if 条件] 是列表推导式
        字典合并    {**字典1, **字典2} 把两个字典拼成一个新字典
        三元表达式  "A" if 条件 else "B"

业务层（services.py）：实现报告“5.1 需求分析”中的六项系统功能。

职责边界：
    负责 —— 业务规则（如“只允许删除未被选修的课程”）、嵌入式 SQL、
             把数据库完整性错误转成用户提示（双重验证第二重）；
    不负责 —— HTTP/路由（在 app.py）、连接管理（在 database.py）、
               字段格式校验（在 models.py）。

架构总览（5 个模块，一个文件一个职责，调用方向自上而下）：
    config.py     配置层：数据库连接、端口、路径等全部可配置项
    database.py   数据层：连接管理 / 事务 / MySQL错误翻译
    models.py     实体层：实体类与输入校验（双重验证第一重）
    services.py   业务层：六大功能的嵌入式 SQL（双重验证第二重）      ← 本文件
    app.py        界面层：HTTP 服务与 REST 路由、程序入口

组织方式（面向对象，按功能划分服务类）：
    StudentService  功能 1/2/7：学生信息维护（录入、修改）与按学号查询
    CourseService   功能 3  ：课程信息维护（增、改、删，含先修课）
    GradeService    功能 4  ：成绩的录入与修改
    StatService     功能 5/6：按系统计成绩、按系排名

嵌入式 SQL 说明：
    所有 SQL 都以 %s 占位符的形式内嵌在 Python 方法中，参数由 PyMySQL
    绑定后发给 MySQL，从机制上杜绝 SQL 注入——这正是“宿主语言 + 嵌入
    式 SQL”的开发方式。

双重验证的第二重：
    第一重（models.py）拦截绝大多数非法输入；这里再把 MySQL 完整性
    约束（主码 1062、CHECK 3819、外键 1452/1451、非空 1048）抛出的
    错误经 database.translate_mysql_error() 翻译成中文提示，作为最后防线。
"""

import pymysql   # 只为捕获它的异常类型；SQL 执行都通过 database.py

from database import translate_mysql_error   # 数据层提供的“错误翻译器”
from models import Student, Course, Enrollment, ValidationError


class BizError(Exception):
    """业务规则不满足（数据不存在、违反约束等），信息可直接展示给用户。

    与 ValidationError 的区别：
        ValidationError —— 第一重校验（格式/范围）不通过时抛出；
        BizError        —— 第二重：业务规则或数据库约束不通过时抛出。
    两者都会被 app.py 捕获并转成 JSON 返回给前端。
    """

    def __init__(self, message: str, hint: str = "", status: int = 400):
        super().__init__(message)
        self.message = message    # 给用户看的失败原因
        self.hint = hint          # 合法数据范围说明
        self.status = status      # HTTP 状态码（默认 400 = 请求有问题）


def _biz(exc):
    """数据库写入异常 → BizError（可展示给用户）；
    不属于完整性约束的错误原样抛出，交给 app.py 的全局 500 处理。"""
    t = translate_mysql_error(exc)   # 尝试翻译（database.py 的函数）
    if t is None:                    # 返回 None 说明不是完整性错误
        raise exc                    # 原样抛出（比如连接断开之类的错误）
    return BizError(*t)              # *t 把 (消息, 提示) 元组拆开传入


class _ServiceBase:
    """服务类的公共基类：持有 Database 对象。

    四个服务类都继承它（括号里写 _ServiceBase），
    这样每个服务里都能直接用 self.db 访问数据库。
    """

    def __init__(self, db):
        self.db = db


# 功能 1 / 2：学生信息维护 + 功能 6：按学号查询
class StudentService(_ServiceBase):

    def list_students(self) -> list:
        """全部学生列表（添加成功后回显、修改功能的表格都用它）。"""
        # —— 嵌入式 SQL：功能 1/2 展示全部学生 ——
        # 相邻的字符串会被 Python 自动拼接成一条完整 SQL
        return self.db.query(
            "SELECT Sno, Sname, Ssex, Sage, Sdept, Scholarship "
            "FROM Student ORDER BY Sno")

    def get_student(self, sno: str):
        # WHERE Sno = %s 里的 %s 由第二个参数 (sno,) 填入
        # 注意 (sno,) 是“只有一个元素的元组”，逗号不能省
        return self.db.query_one(
            "SELECT Sno, Sname, Ssex, Sage, Sdept, Scholarship "
            "FROM Student WHERE Sno = %s", (sno,))

    def add_student(self, stu: Student):
        """功能 1：增加新生入学信息。"""
        stu.validate()                                  # 第一重：应用层校验

        # 预先检查
        # 先 SELECT 再 INSERT，能给出比数据库报错更友好的提示
        if self.get_student(stu.Sno):
            raise BizError(f"学号 {stu.Sno} 已存在",
                           "学号是 9 位数字且不能与已有学生重复")
        if self.db.query_one("SELECT Sno FROM Student WHERE Sname = %s",
                             (stu.Sname,)):
            raise BizError(f"姓名“{stu.Sname}”已存在",
                           "姓名是候选码（UNIQUE），不能与其他学生重名")

        # 功能 1：插入新生记录
        # SQL 里写 6 个 %s；stu.to_row() 返回的 6 个值按顺序填入
        sql = ("INSERT INTO Student (Sno, Sname, Ssex, Sage, Sdept, Scholarship) "
               "VALUES (%s, %s, %s, %s, %s, %s)")
        try:
            self.db.execute(sql, stu.to_row())
        except pymysql.err.MySQLError as e:             # 第二重：完整性约束
            # 万一两条 SELECT 和 INSERT 之间别人抢先插入了相同学号
            # （并发情况），这里的数据库约束还能兜底拒绝
            raise _biz(e) from e

    def update_student(self, sno: str, stu: Student):
        """功能 2：修改学生信息"""
        if not self.get_student(sno):
            raise BizError(f"学号 {sno} 不存在，无法修改", "请刷新表格后重试")
        stu.Sno = sno                     # 学号以 URL 路径参数为准（主码不可改）
        stu.validate()                    # 修改后的数据同样要过第一重校验

       # 检查姓名唯一性
        if self.db.query_one(
                "SELECT Sno FROM Student WHERE Sname = %s AND Sno <> %s",
                (stu.Sname, sno)):
            raise BizError(f"姓名“{stu.Sname}”已被其他学生使用，修改失败",
                           "姓名是候选码（UNIQUE），不能与其他学生重名")

        # —— 嵌入式 SQL：功能 2 按主码定位并更新 ——
        # WHERE Sno = %s 保证只改这一行（主码唯一）
        sql = ("UPDATE Student SET Sname = %s, Ssex = %s, Sage = %s, "
               "Sdept = %s, Scholarship = %s WHERE Sno = %s")
        try:
            self.db.execute(sql, (stu.Sname, stu.Ssex, int(stu.Sage),
                                  stu.Sdept, stu.Scholarship, sno))
        except pymysql.err.MySQLError as e:
            raise _biz(e) from e

    def query_detail(self, sno: str) -> dict:
        """功能 6：输入学号 → 基本信息 + 全部选课信息。"""
        stu = self.get_student(sno)
        if not stu:
            raise BizError(f"学号 {sno} 不存在", "请输入 9 位数字学号，例如 202215121")
        # 嵌入式 SQL：功能 6 查询该生的选课明细
        courses = self.db.query(
            "SELECT c.Cno, c.Cname, c.Ccredit, sc.Grade "
            "FROM SC sc JOIN Course c ON c.Cno = sc.Cno "
            "WHERE sc.Sno = %s ORDER BY c.Cno", (sno,))
        return {"student": stu, "courses": courses}   # 打包成字典返回给前端

    def delete_student(self, sno: str) -> str:
        """扩展功能：删除学生信息"""
        stu = self.get_student(sno)
        if not stu:
            raise BizError(f"学号 {sno} 不存在，无法删除", "请刷新学生列表后重试")
        # 先数一数这名学生有几条选课成绩（用于提示语）
        n = self.db.query_one(
            "SELECT COUNT(*) AS n FROM SC WHERE Sno = %s", (sno,))["n"]
        try:
            # 两句 DELETE 必须同生共死：只删了成绩没删学生 = 数据不一致
            with self.db.transaction() as conn, conn.cursor() as cur:
                # —— 嵌入式 SQL：先删选课记录，再删学生（同一事务）——
                cur.execute("DELETE FROM SC WHERE Sno = %s", (sno,))
                cur.execute("DELETE FROM Student WHERE Sno = %s", (sno,))
        except pymysql.err.MySQLError as e:
            raise _biz(e) from e
        # 三元表达式：有成绩才追加“同时删除 …”字样
        extra = f"，同时删除其 {n} 条选课成绩" if n else ""
        return f"学生 {sno}（{stu['Sname']}）已删除{extra}"

# 功能 2：课程信息维护（增、改、删，含先修课 CP）
class CourseService(_ServiceBase):

    def list_courses(self) -> list:
        """课程列表：附带选课人数和先修课"""
        # 嵌入式 SQL：课程 + 先修课 + 选课人数（相关子查询）——
        # 两个 (SELECT ...) 是“相关子查询”：对每一门课 c 分别计算
        #   chosen     = 有多少人选了这门课
        #   prereq_ids = 这门课所有先修课号，GROUP_CONCAT 拼成 "12,10" 这样的串
        # Cno 是 CHAR(4)，纯字符串排序会得到 1,12,...,19,2,...；
        # 先 CAST 成数值再排序，即可按课程号数值升序（1,2,...,9,10,...）
        rows = self.db.query(
            "SELECT c.Cno, c.Cname, c.Ccredit, "
            "  (SELECT COUNT(*) FROM SC WHERE SC.Cno = c.Cno) AS chosen, "
            "  (SELECT GROUP_CONCAT(cp.Cpno ORDER BY cp.Cpno) FROM CP cp "
            "   WHERE cp.Cno = c.Cno) AS prereq_ids "
            "FROM Course c ORDER BY CAST(c.Cno AS UNSIGNED), c.Cno")
        # 下面几行把 prereq_ids（"12,10" 字符串）翻译成
        # [{"Cno":"12","Cname":"材料科学基础（上）"}, ...] 这样的列表
        # 字典推导式 {r["Cno"]: r["Cname"]} 先建好“课号→课名”对照表
        names = {r["Cno"]: r["Cname"] for r in rows}
        for r in rows:
            # split(",") 按逗号切开；空字符串会产生空元素，用 if p 过滤掉
            ids = [p for p in (r["prereq_ids"] or "").split(",") if p]
            r["prereqs"] = [{"Cno": p, "Cname": names.get(p, p)} for p in ids]
            del r["prereq_ids"]          # 删掉临时的中间字段，不返给前端
        return rows

    def _check_prereqs_exist(self, prereqs: list):
        """先修课号必须已存在于 Course 表（外键 fk_cp_cpno 的友好预检）。"""
        for p in prereqs:
            if not self.db.query_one(
                    "SELECT Cno FROM Course WHERE Cno = %s", (p,)):
                raise BizError(f"先修课 {p} 不存在，保存失败",
                               "先修课号必须对应一门已存在的课程（外键约束）")

    def add_course(self, course: Course):
        """增加课程（可同时登记若干门先修课）。"""
        course.validate()
        if self.db.query_one("SELECT Cno FROM Course WHERE Cno = %s",
                             (course.Cno,)):
            raise BizError(f"课程号 {course.Cno} 已存在",
                           "课程号是 1～4 位数字或字母且不能重复")
        self._check_prereqs_exist(course.prereqs)

        # 一个事务里写 Course 与 CP 两张表：要么全成功，要么全回滚
        # （如果只插了课程、先修课插入失败，就会出现“半成品”数据）
        try:
            with self.db.transaction() as conn, conn.cursor() as cur:
                # 功能 2:插入课程
                cur.execute("INSERT INTO Course (Cno, Cname, Ccredit) "
                            "VALUES (%s, %s, %s)",
                            (course.Cno, course.Cname, float(course.Ccredit)))
                # 登记先修联系 CP
                # 几门先修课就插几行 CP 记录
                for p in course.prereqs:
                    cur.execute("INSERT INTO CP (Cno, Cpno) VALUES (%s, %s)",
                                (course.Cno, p))
        except pymysql.err.MySQLError as e:
            raise _biz(e) from e

    def update_course(self, cno: str, course: Course):
        """修改课程信息与先修课（课程号为主码不可改）。"""
        if not self.db.query_one("SELECT Cno FROM Course WHERE Cno = %s", (cno,)):
            raise BizError(f"课程号 {cno} 不存在，无法修改", "请刷新课程列表后重试")
        course.Cno = cno
        course.validate()
        self._check_prereqs_exist(course.prereqs)

        try:
            with self.db.transaction() as conn, conn.cursor() as cur:
                # 功能 2: 更新课程
                cur.execute("UPDATE Course SET Cname = %s, Ccredit = %s "
                            "WHERE Cno = %s",
                            (course.Cname, float(course.Ccredit), cno))
                # 先修关系整表重建：先删旧的，再插新的（同一事务）
                # 这是处理“多对多联系整体替换”的常用做法
                cur.execute("DELETE FROM CP WHERE Cno = %s", (cno,))
                for p in course.prereqs:
                    cur.execute("INSERT INTO CP (Cno, Cpno) VALUES (%s, %s)",
                                (cno, p))
        except pymysql.err.MySQLError as e:
            raise _biz(e) from e

    def delete_course(self, cno: str):
        """删除课程。业务规则（报告 5.1）：
        删除前检查是否还有选课记录，只允许删除未被选修的课程。"""
        row = self.db.query_one("SELECT Cno, Cname FROM Course WHERE Cno = %s",
                                (cno,))
        if not row:
            raise BizError(f"课程号 {cno} 不存在，无法删除", "请刷新课程列表后重试")

        # 业务校验 1：仍被选修的课程不允许删除
        # （对应指导书要求：“删除没有选课的课程信息”）
        n_sc = self.db.query_one(
            "SELECT COUNT(*) AS n FROM SC WHERE Cno = %s", (cno,))["n"]
        if n_sc:
            raise BizError(f"课程 {cno}（{row['Cname']}）仍有 {n_sc} 条选课记录，不允许删除",
                           "功能规则：只允许删除未被选修的课程；请先删除相关选课成绩")

        # 业务校验 2：仍被其他课程当作先修课时不允许删除（外键 fk_cp_cpno）
        n_cp = self.db.query_one(
            "SELECT COUNT(*) AS n FROM CP WHERE Cpno = %s", (cno,))["n"]
        if n_cp:
            raise BizError(f"课程 {cno}（{row['Cname']}）仍被 {n_cp} 门课程列为先修课，不允许删除",
                           "请先在那些课程的先修课列表中去掉本课程，再删除")

        with self.db.transaction() as conn, conn.cursor() as cur:
            # 该课程自身的先修关系一并清理，再删除课程本体
            cur.execute("DELETE FROM CP WHERE Cno = %s", (cno,))
            cur.execute("DELETE FROM Course WHERE Cno = %s", (cno,))

# 功能 3：成绩的录入与修改
class GradeService(_ServiceBase):

    def list_grades(self) -> list:
        """全部选课成绩（含学生姓名、课程名），供录入后回显。"""
        # —— 嵌入式 SQL：三表连接展示成绩 ——
        # SC 表只存学号和课程号，JOIN 一下才能显示出姓名和课名
        return self.db.query(
            "SELECT sc.Sno, s.Sname, sc.Cno, c.Cname, sc.Grade "
            "FROM SC sc "
            "JOIN Student s ON s.Sno = sc.Sno "
            "JOIN Course  c ON c.Cno = sc.Cno "
            "ORDER BY sc.Sno, sc.Cno")

    def set_grade(self, enr: Enrollment) -> str:
        """录入或修改一条成绩：记录已存在则 UPDATE，否则 INSERT。
        返回给前端的提示文字（区分“录入成功 / 修改成功”）。"""
        enr.validate()                                   # 第一重校验（0~100 等）

        # 外键友好预检查：学号、课程号必须存在
        if not self.db.query_one("SELECT Sno FROM Student WHERE Sno = %s",
                                 (enr.Sno,)):
            raise BizError(f"学号 {enr.Sno} 不存在，保存失败", "请先在“学生管理”中录入该学生")
        if not self.db.query_one("SELECT Cno FROM Course WHERE Cno = %s",
                                 (enr.Cno,)):
            raise BizError(f"课程号 {enr.Cno} 不存在，保存失败", "请先在“课程维护”中添加该课程")

        # 先查这条选课记录是否已存在，决定走“修改”还是“录入”
        existing = self.db.query_one(
            "SELECT Grade FROM SC WHERE Sno = %s AND Cno = %s",
            (enr.Sno, enr.Cno))

        try:
            if existing is not None:
                # 功能 3：修改成绩
                self.db.execute("UPDATE SC SET Grade = %s "
                                "WHERE Sno = %s AND Cno = %s",
                                (enr.grade, enr.Sno, enr.Cno))
                action = "修改成功"
            else:
                # 功能 3：录入成绩
                # enr.grade 为 None 时，PyMySQL 会写入 SQL 的 NULL（暂未录入）
                self.db.execute("INSERT INTO SC (Sno, Cno, Grade) "
                                "VALUES (%s, %s, %s)",
                                (enr.Sno, enr.Cno, enr.grade))
                action = "录入成功"
        except pymysql.err.MySQLError as e:          # 第二重：ck_sc_grade 等
            raise _biz(e) from e

        # 组装返回给前端的提示文字
        grade_text = "暂未录入（NULL）" if enr.grade is None else f"{enr.grade} 分"
        return f"成绩{action}：{enr.Sno} / 课程 {enr.Cno} = {grade_text}"

# 功能 4 / 5：按系统计成绩、按系排名
class StatService(_ServiceBase):

    # 允许输出的统计列（白名单，防止把任意字符串拼进 SQL）
    ALL_FIELDS = ["total", "avg", "max", "min", "excellent", "fail"]
    FIELD_LABELS = {
        "total": "选课人次", "avg": "平均分", "max": "最高分",
        "min": "最低分", "excellent": "优秀率(%)", "fail": "不及格人数",
    }

    def dept_stats(self, dept: str, fields=None) -> list:
        """功能 4：按系别统计成绩。dept 为空表示统计全部系；
        fields 从白名单中选择要输出的列（SQL 固定计算全部统计值，
        输出列在 Python 侧按白名单过滤，安全又不失灵活）。"""
        # —— 嵌入式 SQL：功能 4 分组统计 ——
        # GROUP BY s.Sdept 表示“按系分组”，每组算出一行统计值；
        # SUM(sc.Grade >= 90) 利用了“条件成立=1、不成立=0”的技巧来数人数
        sql = ("SELECT s.Sdept AS dept, "
               "       COUNT(sc.Grade) AS total, "
               "       ROUND(AVG(sc.Grade), 2) AS avg, "
               "       MAX(sc.Grade) AS max, "
               "       MIN(sc.Grade) AS min, "
               "       ROUND(SUM(sc.Grade >= 90) / COUNT(*) * 100, 2) AS excellent, "
               "       SUM(sc.Grade < 60) AS fail "
               "FROM Student s JOIN SC sc ON sc.Sno = s.Sno "
               "WHERE sc.Grade IS NOT NULL")
        args = []
        if dept:                         # 指定了系名就追加过滤条件
            sql += " AND s.Sdept = %s"
            args.append(dept)
        sql += " GROUP BY s.Sdept ORDER BY s.Sdept"

        # fields 白名单过滤：不在 ALL_FIELDS 里的请求列直接忽略
        wanted = [f for f in (fields or []) if f in self.ALL_FIELDS]
        rows = self.db.query(sql, tuple(args))
        # 组装输出：每行 = 系别 + 用户勾选的那些统计列
        # {**字典A, **字典B} 表示两个字典合并
        return [{**{"Sdept": r["dept"]},
                 **{self.FIELD_LABELS[f]: r[f] for f in wanted}}
                for r in rows]

    def dept_rank(self, dept: str) -> list:
        """功能 5：按系对学生成绩排名（系内名次 + 姓名、课程、成绩）。"""
        # 功能 5：窗口函数 ROW_NUMBER() 系内排名
        sql = ("SELECT s.Sdept AS Sdept, "
               "       ROW_NUMBER() OVER (PARTITION BY s.Sdept "
               "                          ORDER BY sc.Grade DESC, s.Sno, sc.Cno) AS rk, "
               "       s.Sno, s.Sname, c.Cno, c.Cname, sc.Grade "
               "FROM Student s "
               "JOIN SC sc ON sc.Sno = s.Sno "
               "JOIN Course c ON c.Cno = sc.Cno "
               "WHERE sc.Grade IS NOT NULL")
        args = []
        if dept:
            sql += " AND s.Sdept = %s"
            args.append(dept)
        sql += " ORDER BY s.Sdept, rk"
        return self.db.query(sql, tuple(args))
