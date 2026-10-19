# -*- coding: utf-8 -*-
"""
【初学者阅读指南】
    models.py 存放“实体类”——就是把数据库里的一行数据包装成 Python 对象。
    比如 Student 类的一个对象 = Student 表里的一行。

    这个文件回答两个问题：
        1. 一条学生/课程/成绩记录，在 Python 里长什么样？（实体类）
        2. 用户填的数据合不合法？谁来检查？（validate() 校验方法）

    “双重验证”的第一重在这里：
        用户提交的数据先经过 Python 的格式/范围检查（给出中文提示和合法
        范围说明），不合法的数据在这一层就被拒绝，根本不会发往数据库；
        即使个别漏网（例如并发插入重复学号），还有数据库的完整性约束
        （主码 / 唯一 / CHECK / 外键，见 schema.sql）作为第二重兜底，
        其错误由 database.py 翻译、services.py 转成友好提示。

    会用到的 Python 知识点：
        class / __init__ / self    类、构造函数、对象自己（见 database.py）
        @classmethod               “类方法”，不用先创建对象就能调用，
                                   常用来“根据一段数据造出一个对象”
        Exception / raise          自定义异常 + 主动抛出：
                                   校验不通过时 raise ValidationError(...)
                                   上层（app.py）会捕获它并返回给用户
        re.fullmatch               正则表达式“整串匹配”，检查字符串格式
                                   例：代码里写着“9 个数字”这样的格式规则
        字典.get(键)               取字典里的值；键不存在返回 None 而不报错

    实体类与报告 5.3 逻辑结构设计的四个关系模式一一对应：
        Student（学生）  Course（课程）
        Enrollment（选课 SC）  Prerequisite（先修 CP，在 CourseService 中处理）
"""

import re   # 正则表达式模块，用来检查“字符串长得对不对”


# 自定义异常类：继承 Python 内置的 Exception
# “继承”的意思是它拥有 Exception 的一切能力，只是多了两个自定义属性
class ValidationError(Exception):
    """应用层校验失败：message 为失败原因，hint 为合法数据范围提示。"""

    def __init__(self, message: str, hint: str = ""):
        super().__init__(message)   # 把 message 交给父类 Exception 保存
        self.message = message      # 失败原因（大字提示）
        self.hint = hint            # 合法数据范围说明（小字提示）


# ---------------------------------------------------------------------- #
# 合法数据范围说明（后端校验与前端提示共用同一份“口径”）
# 校验函数抛异常时会引用这里的文字，保证提示语统一、不用到处复制
# ---------------------------------------------------------------------- #
STUDENT_RULES = {
    "Sno": "学号必须是 9 位数字（例如 202215121）",
    "Sname": "姓名必填，长度 2～20 个字符，且不能与已有学生重名",
    "Ssex": "性别只能是「男」或「女」",
    "Sage": "年龄必须是 1～150 之间的整数",
    "Sdept": "系名必填，长度 2～20 个字符（例如 CS / MA / IS）",
    "Scholarship": "奖学金只能是「是」或「否」",
}

COURSE_RULES = {
    "Cno": "课程号必须是 1～4 位数字或字母（例如 1、10、C1）",
    "Cname": "课程名必填，长度不超过 40 个字符",
    "Ccredit": "学分必须是 0～10 之间的数（最多两位小数，如 2.5、5.5、0.75）",
    "Cpno": "先修课号必须是已存在的课程号，且不能是课程自身",
}

GRADE_RULES = {
    "Sno": STUDENT_RULES["Sno"],      # 直接复用学生规则里写好的那句话
    "Cno": COURSE_RULES["Cno"],
    "Grade": "成绩必须是 0～100 之间的整数；留空表示“暂未录入”（NULL）",
}


# ---------------------------------------------------------------------- #
# 校验小工具（下面的实体类都会用到）
# ---------------------------------------------------------------------- #
def _clean(value) -> str:
    """把用户输入统一成去除首尾空白的字符串（None 视为空串）。

    例：_clean("  张三 ") → "张三"；_clean(None) → ""
    “x if 条件 else y”是三元表达式：条件成立取 x，否则取 y。
    """
    return "" if value is None else str(value).strip()


def _to_int(value, field: str, rule: str, lo: int, hi: int) -> int:
    """把输入转成 [lo, hi] 内的整数，否则抛 ValidationError。

    参数含义：value=用户输入，field=字段中文名（用于提示），
    rule=合法范围说明文字，lo/hi=允许的最小/最大值。
    """
    s = _clean(value)
    # 正则 \d 表示数字，{1,} 表示一个或多个 → 整串必须是纯数字（允许负号）
    if not re.fullmatch(r"-?\d+", s):
        raise ValidationError(f"{field}“{value}”不是整数", rule)
    n = int(s)                       # 字符串转成整数
    if not (lo <= n <= hi):          # Python 允许连写：lo <= n <= hi
        raise ValidationError(f"{field} {n} 超出合法范围 [{lo}, {hi}]", rule)
    return n


def _to_decimal(value, field: str, rule: str, lo: float, hi: float) -> float:
    """把输入转成 [lo, hi] 内、最多两位小数的数，否则抛 ValidationError。
    用于学分等允许小数的字段（如 2.5、5.5、0.75）。"""
    s = _clean(value)
    # 正则含义：整数部分 + 可选的“小数点 + 1~2 位小数”（如 2.5、0.75）
    if not re.fullmatch(r"-?\d+(?:\.\d{1,2})?", s):
        raise ValidationError(f"{field}“{value}”不是数字（最多两位小数）", rule)
    n = float(s)
    if not (lo <= n <= hi):
        raise ValidationError(f"{field} {n} 超出合法范围 [{lo:g}, {hi:g}]", rule)
    return n


# ---------------------------------------------------------------------- #
# 实体类
# ---------------------------------------------------------------------- #
class Student:
    """学生实体：对应关系模式 学生（学号，姓名，性别，年龄，所在系，奖学金）。"""

    # 允许前端传上来的字段白名单（多余字段一律忽略，防止越权写入）
    FIELDS = ("Sno", "Sname", "Ssex", "Sage", "Sdept", "Scholarship")

    def __init__(self, sno="", sname="", ssex="", sage=None, sdept="", scholarship="否"):
        # __init__ 在创建对象时执行，把传入的值清洗后存到对象属性上
        self.Sno = _clean(sno)                       # 学号
        self.Sname = _clean(sname)                   # 姓名
        self.Ssex = _clean(ssex)                     # 性别
        self.Sage = _clean(sage)                     # 年龄（此刻还是字符串）
        self.Sdept = _clean(sdept)                   # 所在系
        # “xxx or 默认值”：xxx 为空时取默认值 → 奖学金不填就按“否”处理
        self.Scholarship = _clean(scholarship) or "否"

    # ---- 构造与输出 -------------------------------------------------- #
    @classmethod
    def from_dict(cls, data: dict) -> "Student":
        """从前端 JSON 构造实体（未知字段直接丢弃）。

        data.get("Sno") 表示“从字典里取键 Sno 的值，没有就返回 None”。
        cls(...) 等价于 Student(...)，即调用下面的构造函数。
        """
        return cls(
            sno=data.get("Sno"), sname=data.get("Sname"), ssex=data.get("Ssex"),
            sage=data.get("Sage"), sdept=data.get("Sdept"),
            scholarship=data.get("Scholarship") or "否",
        )

    def to_row(self) -> tuple:
        """按 INSERT 语句的列顺序输出参数元组。

        元组 (a, b, c) 会对应 SQL 里 VALUES (%s, %s, %s) 的三个占位符。
        注意：到这里年龄一定已经通过 validate() 转成了整数。
        """
        return (self.Sno, self.Sname, self.Ssex, int(self.Sage),
                self.Sdept, self.Scholarship)

    # ---- 应用层校验（双重验证第一重） -------------------------------- #
    def validate(self):
        """逐个字段检查格式与范围；发现第一个不合法的就抛出异常。

        raise 会立刻中断本方法——后面的检查不再执行，
        异常会被 app.py 捕获并转成返回给前端的错误提示。
        """
        # \d{9} = 恰好 9 个数字
        if not re.fullmatch(r"\d{9}", self.Sno):
            raise ValidationError(f"学号“{self.Sno}”不合法", STUDENT_RULES["Sno"])
        # len() 取字符串长度；Python 支持连续比较 2 <= x <= 20
        if not (2 <= len(self.Sname) <= 20):
            raise ValidationError(f"姓名“{self.Sname}”不合法", STUDENT_RULES["Sname"])
        # in 用于判断“是否在候选集合里”
        if self.Ssex not in ("男", "女"):
            raise ValidationError(f"性别“{self.Ssex}”不合法", STUDENT_RULES["Ssex"])
        # 年龄比较特殊：既要转整数、又限范围，交给工具函数处理
        self.Sage = _to_int(self.Sage, "年龄", STUDENT_RULES["Sage"], 1, 150)
        if not (2 <= len(self.Sdept) <= 20):
            raise ValidationError(f"系名“{self.Sdept}”不合法", STUDENT_RULES["Sdept"])
        if self.Scholarship not in ("是", "否"):
            raise ValidationError(f"奖学金“{self.Scholarship}”不合法",
                                  STUDENT_RULES["Scholarship"])


class Course:
    """课程实体：对应关系模式 课程（课程号，课程名，学分）。
    先修课不在课程表里（已按概念设计拆成独立的 CP 联系表），
    这里用 self.prereqs 保存先修课号列表，由服务层负责落库。"""

    FIELDS = ("Cno", "Cname", "Ccredit", "prereqs")

    def __init__(self, cno="", cname="", ccredit=None, prereqs=None):
        self.Cno = _clean(cno)
        self.Cname = _clean(cname)
        self.Ccredit = _clean(ccredit)
        # 这一行是“列表推导式”：对 prereqs 里每个元素清洗、去掉空值
        # 等价于：先建空列表，再 for 循环逐个 append
        self.prereqs = [_clean(p) for p in (prereqs or []) if _clean(p)]

    @classmethod
    def from_dict(cls, data: dict) -> "Course":
        return cls(cno=data.get("Cno"), cname=data.get("Cname"),
                   ccredit=data.get("Ccredit"), prereqs=data.get("prereqs") or [])

    def validate(self):
        # {1,4} 表示 1～4 个字符，且只能是数字或字母
        if not re.fullmatch(r"[0-9A-Za-z]{1,4}", self.Cno):
            raise ValidationError(f"课程号“{self.Cno}”不合法", COURSE_RULES["Cno"])
        if not (1 <= len(self.Cname) <= 40):
            raise ValidationError(f"课程名“{self.Cname}”不合法", COURSE_RULES["Cname"])
        # 学分允许小数（0～10，最多两位小数），用小数版校验函数
        self.Ccredit = _to_decimal(self.Ccredit, "学分",
                                   COURSE_RULES["Ccredit"], 0, 10)
        # 先修课号格式 + 不能以自身为先修（对应数据库 ck_cp 约束）
        for p in self.prereqs:
            if not re.fullmatch(r"[0-9A-Za-z]{1,4}", p):
                raise ValidationError(f"先修课号“{p}”不合法", COURSE_RULES["Cno"])
            if p == self.Cno:
                raise ValidationError("课程不能以自身为先修课", COURSE_RULES["Cpno"])


class Enrollment:
    """选课实体：对应关系模式 选课（学号，课程号，成绩）。
    grade 允许为 None —— 表示“暂未录入”（SC.Grade 可为空）。"""

    def __init__(self, sno="", cno="", grade=None):
        self.Sno = _clean(sno)
        self.Cno = _clean(cno)
        self.grade = _clean(grade)

    @classmethod
    def from_dict(cls, data: dict) -> "Enrollment":
        return cls(sno=data.get("Sno"), cno=data.get("Cno"),
                   grade=data.get("Grade"))

    def validate(self):
        if not re.fullmatch(r"\d{9}", self.Sno):
            raise ValidationError(f"学号“{self.Sno}”不合法", GRADE_RULES["Sno"])
        if not re.fullmatch(r"[0-9A-Za-z]{1,4}", self.Cno):
            raise ValidationError(f"课程号“{self.Cno}”不合法", GRADE_RULES["Cno"])
        # 成绩：空 → None（未录入）；非空则必须是 0～100 的整数
        if self.grade == "":
            self.grade = None
        else:
            self.grade = _to_int(self.grade, "成绩", GRADE_RULES["Grade"], 0, 100)
