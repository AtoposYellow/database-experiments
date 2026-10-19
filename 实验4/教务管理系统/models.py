# -*- coding: utf-8 -*-
"""
实体层（models.py）：与数据库基本表一一对应的实体类 + 应用层校验。

职责边界：
    负责 —— 实体的字段封装、from_dict 构造、validate() 应用层校验；
    不负责 —— SQL 与业务规则（在 services.py）、HTTP（在 app.py）。

架构总览（5 个模块，一个文件一个职责，调用方向自上而下）：
    config.py     配置层：数据库连接、端口、路径等全部可配置项
    database.py   数据层：连接管理 / 事务 / 建库脚本 / MySQL错误翻译
    models.py     实体层：实体类与输入校验（双重验证第一重）          ← 本文件
    services.py   业务层：六大功能的嵌入式 SQL（双重验证第二重）
    app.py        界面层：HTTP 服务与 REST 路由、程序入口

“双重验证”的第一重在这里：
    用户提交的数据先经过 Python 的格式/范围检查（给出中文提示和合法
    范围说明），不合法的数据在这一层就被拒绝，根本不会发往数据库；
    即使个别漏网（例如并发插入重复学号），还有数据库的完整性约束
    （主码 / 唯一 / CHECK / 外键，见 schema.sql）作为第二重兜底，
    其错误由 database.py 翻译、services.py 转成友好提示。

实体类与报告 5.3 逻辑结构设计的四个关系模式一一对应：
    Student（学生）  Course（课程）
    Enrollment（选课 SC）  Prerequisite（先修 CP，在 CourseService 中处理）
"""

import re


class ValidationError(Exception):
    """应用层校验失败：message 为失败原因，hint 为合法数据范围提示。"""

    def __init__(self, message: str, hint: str = ""):
        super().__init__(message)
        self.message = message
        self.hint = hint


# ---------------------------------------------------------------------- #
# 合法数据范围说明（后端校验与前端提示共用同一份“口径”）
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
    "Sno": STUDENT_RULES["Sno"],
    "Cno": COURSE_RULES["Cno"],
    "Grade": "成绩必须是 0～100 之间的整数；留空表示“暂未录入”（NULL）",
}


# ---------------------------------------------------------------------- #
# 校验小工具
# ---------------------------------------------------------------------- #
def _clean(value) -> str:
    """把用户输入统一成去除首尾空白的字符串（None 视为空串）。"""
    return "" if value is None else str(value).strip()


def _to_int(value, field: str, rule: str, lo: int, hi: int) -> int:
    """把输入转成 [lo, hi] 内的整数，否则抛 ValidationError。"""
    s = _clean(value)
    if not re.fullmatch(r"-?\d+", s):
        raise ValidationError(f"{field}“{value}”不是整数", rule)
    n = int(s)
    if not (lo <= n <= hi):
        raise ValidationError(f"{field} {n} 超出合法范围 [{lo}, {hi}]", rule)
    return n


def _to_decimal(value, field: str, rule: str, lo: float, hi: float) -> float:
    """把输入转成 [lo, hi] 内、最多两位小数的数，否则抛 ValidationError。
    用于学分等允许小数的字段（如 2.5、5.5、0.75）。"""
    s = _clean(value)
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
        self.Sno = _clean(sno)
        self.Sname = _clean(sname)
        self.Ssex = _clean(ssex)
        self.Sage = _clean(sage)
        self.Sdept = _clean(sdept)
        self.Scholarship = _clean(scholarship) or "否"

    # ---- 构造与输出 -------------------------------------------------- #
    @classmethod
    def from_dict(cls, data: dict) -> "Student":
        """从前端 JSON 构造实体（未知字段直接丢弃）。"""
        return cls(
            sno=data.get("Sno"), sname=data.get("Sname"), ssex=data.get("Ssex"),
            sage=data.get("Sage"), sdept=data.get("Sdept"),
            scholarship=data.get("Scholarship") or "否",
        )

    def to_row(self) -> tuple:
        """按 INSERT/UPDATE 的列顺序输出参数元组。"""
        return (self.Sno, self.Sname, self.Ssex, int(self.Sage),
                self.Sdept, self.Scholarship)

    # ---- 应用层校验（双重验证第一重） -------------------------------- #
    def validate(self):
        if not re.fullmatch(r"\d{9}", self.Sno):
            raise ValidationError(f"学号“{self.Sno}”不合法", STUDENT_RULES["Sno"])
        if not (2 <= len(self.Sname) <= 20):
            raise ValidationError(f"姓名“{self.Sname}”不合法", STUDENT_RULES["Sname"])
        if self.Ssex not in ("男", "女"):
            raise ValidationError(f"性别“{self.Ssex}”不合法", STUDENT_RULES["Ssex"])
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
        self.prereqs = [_clean(p) for p in (prereqs or []) if _clean(p)]

    @classmethod
    def from_dict(cls, data: dict) -> "Course":
        return cls(cno=data.get("Cno"), cname=data.get("Cname"),
                   ccredit=data.get("Ccredit"), prereqs=data.get("prereqs") or [])

    def validate(self):
        if not re.fullmatch(r"[0-9A-Za-z]{1,4}", self.Cno):
            raise ValidationError(f"课程号“{self.Cno}”不合法", COURSE_RULES["Cno"])
        if not (1 <= len(self.Cname) <= 40):
            raise ValidationError(f"课程名“{self.Cname}”不合法", COURSE_RULES["Cname"])
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
