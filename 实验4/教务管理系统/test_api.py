# -*- coding: utf-8 -*-
"""
【初学者阅读指南】
    本脚本相当于“用代码把 操作指南 里的测试步骤做一遍”：
    call() 发 HTTP 请求 → expect_ok()/expect_err() 断言结果 → check() 计数。
    用例按功能分组（功能1～8），每组都包含成功用例和失败用例；
    全部通过时打印“通过 78 项”。注意：运行会修改数据，跑完建议执行
    schema.sql 恢复初始数据。

教务管理系统 API 集成测试：成功用例 + 非法数据用例（双重验证验证）。"""
import io
import json
import sys
import urllib.request
import urllib.error
from urllib.parse import quote

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

BASE = "http://127.0.0.1:8000"
PASS, FAIL = 0, 0

NET = "网络空间安全学院"          # 示例数据中的三个系
MAT = "材料科学与工程学院"
AIA = "人工智能与自动化学院"


def call(method, path, body=None):
    """调用 API，返回 (状态码, 响应JSON)。"""
    req = urllib.request.Request(
        BASE + path, method=method,
        data=json.dumps(body).encode() if body is not None else None,
        headers={"Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req) as r:
            return r.status, json.loads(r.read().decode())
    except urllib.error.HTTPError as e:
        return e.code, json.loads(e.read().decode())


def check(name, cond, detail=""):
    global PASS, FAIL
    mark = "√" if cond else "×"
    print(f"  {mark} {name}" + ("" if cond else f"   <-- {detail}"))
    PASS, FAIL = PASS + (1 if cond else 0), FAIL + (0 if cond else 1)


def expect_ok(name, method, path, body=None):
    code, resp = call(method, path, body)
    check(name, code == 200 and resp.get("ok"), f"{code} {resp}")
    return resp.get("data")


def expect_err(name, method, path, body=None, keyword=""):
    code, resp = call(method, path, body)
    hit = keyword in (resp.get("message", "") + resp.get("hint", ""))
    check(name, code >= 400 and resp.get("ok") is False and (not keyword or hit),
          f"{code} {resp}")


print("== 0. 连通性 ==")
ping = expect_ok("GET /api/ping", "GET", "/api/ping")
print(f"     MySQL {ping['mysql']} / {ping['database']}")
html = urllib.request.urlopen(BASE + "/").read().decode("utf-8")
check("首页可访问", "教务管理系统" in html and "学号查询" in html)

print("== 功能1 录入新生 ==")
rows = expect_ok("初始学生表", "GET", "/api/students")
check("示例数据至少 15 名学生", len(rows) >= 15, f"{len(rows)} 行")
check("无 CS/MA/IS 旧系名", not any(r["Sdept"] in ("CS", "MA", "IS") for r in rows), "")
expect_ok("合法新增 202510816 陈曦", "POST", "/api/students",
          {"Sno": "202510816", "Sname": "陈曦", "Ssex": "女", "Sage": 18,
           "Sdept": NET, "Scholarship": "否"})
expect_err("学号重复（主码）", "POST", "/api/students",
           {"Sno": "202510816", "Sname": "赵新", "Ssex": "男", "Sage": 19,
            "Sdept": NET, "Scholarship": "否"}, keyword="已存在")
expect_err("姓名重复（候选码/UNIQUE）", "POST", "/api/students",
           {"Sno": "202510899", "Sname": "郑皓宇", "Ssex": "男", "Sage": 20,
            "Sdept": NET, "Scholarship": "否"}, keyword="姓名")
expect_err("性别非法（第一重 Python 拦截）", "POST", "/api/students",
           {"Sno": "202510817", "Sname": "测试", "Ssex": "未知", "Sage": 19,
            "Sdept": NET, "Scholarship": "否"}, keyword="性别")
expect_err("学号位数错误", "POST", "/api/students",
           {"Sno": "12345", "Sname": "测试", "Ssex": "男", "Sage": 19,
            "Sdept": NET, "Scholarship": "否"}, keyword="9 位")
expect_err("年龄为负", "POST", "/api/students",
           {"Sno": "202510817", "Sname": "测试", "Ssex": "男", "Sage": -3,
            "Sdept": NET, "Scholarship": "否"}, keyword="年龄")
expect_err("年龄非整数", "POST", "/api/students",
           {"Sno": "202510817", "Sname": "测试", "Ssex": "男", "Sage": "十九",
            "Sdept": NET, "Scholarship": "否"}, keyword="整数")

print("== 功能2 学生信息修改 ==")
expect_ok("修改陈曦系别/奖学金", "PUT", "/api/students/202510816",
          {"Sname": "陈曦", "Ssex": "女", "Sage": 19, "Sdept": MAT,
           "Scholarship": "是"})
d = expect_ok("查询修改结果", "GET", "/api/students/202510816")
check("修改已生效", d["student"]["Sdept"] == MAT and d["student"]["Scholarship"] == "是",
      str(d["student"]))
expect_err("修改成重复姓名", "PUT", "/api/students/202510816",
           {"Sname": "郑皓宇", "Ssex": "女", "Sage": 19, "Sdept": MAT,
            "Scholarship": "是"}, keyword="姓名")
expect_err("修改不存在的学号", "PUT", "/api/students/999999999",
           {"Sname": "幽灵", "Ssex": "男", "Sage": 20, "Sdept": NET,
            "Scholarship": "否"}, keyword="不存在")
expect_err("修改性别非法", "PUT", "/api/students/202510816",
           {"Sname": "陈曦", "Ssex": "x", "Sage": 19, "Sdept": MAT,
            "Scholarship": "是"}, keyword="性别")

print("== 功能3 课程维护 ==")
rows = expect_ok("课程列表", "GET", "/api/courses")
check("示例课程至少 21 门", len(rows) >= 21, f"{len(rows)} 行")
check("课程号 1～21 连续", [int(r["Cno"]) for r in rows if r["Cno"].isdigit()][:21]
      == list(range(1, 22)), "前 21 个不是 1～21")
check("含材料/AI 课程", {"工程化学", "电工技术", "计算机视觉"} <=
      {r["Cname"] for r in rows}, "")
expect_ok("添加课程 25（学分 2.5，先修 2、5）", "POST", "/api/courses",
          {"Cno": "25", "Cname": "软件工程与项目管理", "Ccredit": 2.5, "prereqs": ["2", "5"]})
rows = expect_ok("课程列表", "GET", "/api/courses")
c25 = next(r for r in rows if r["Cno"] == "25")
check("先修课已登记", [p["Cno"] for p in c25["prereqs"]] == ["2", "5"], str(c25))
check("小数学分已存为 2.5", c25["Ccredit"] == 2.5, str(c25))
expect_err("课程号重复", "POST", "/api/courses",
           {"Cno": "25", "Cname": "重复课", "Ccredit": 2, "prereqs": []}, keyword="已存在")
expect_err("先修课不存在（外键预检）", "POST", "/api/courses",
           {"Cno": "26", "Cname": "测试课", "Ccredit": 2, "prereqs": ["99"]}, keyword="先修课")
expect_err("以自身为先修（对应 ck_cp）", "POST", "/api/courses",
           {"Cno": "26", "Cname": "测试课", "Ccredit": 2, "prereqs": ["26"]}, keyword="自身")
expect_err("学分越界 99（合法范围 0～10）", "POST", "/api/courses",
           {"Cno": "26", "Cname": "测试课", "Ccredit": 99, "prereqs": []}, keyword="学分")
expect_ok("修改课程 25（改名/学分 3.5）", "PUT", "/api/courses/25",
          {"Cno": "25", "Cname": "软件工程与项目管理（双语）", "Ccredit": 3.5, "prereqs": ["2"]})
rows = expect_ok("课程列表", "GET", "/api/courses")
c25 = next(r for r in rows if r["Cno"] == "25")
check("修改已生效", c25["Cname"].endswith("（双语）") and c25["Ccredit"] == 3.5
      and [p["Cno"] for p in c25["prereqs"]] == ["2"], str(c25))
expect_err("删除仍被选修的课程 1（软件安全）", "DELETE", "/api/courses/1",
           keyword="选课记录")
expect_err("删除仍被引用为先修的课程 5（课程 1 的先修）", "DELETE", "/api/courses/5",
           keyword="先修课")
expect_ok("删除未被选修的课程 25", "DELETE", "/api/courses/25")
expect_err("删除不存在的课程", "DELETE", "/api/courses/88", keyword="不存在")

print("== 功能4 成绩录入修改 ==")
msg = expect_ok("录入新成绩（202510809,1,91）", "POST", "/api/grades",
                {"Sno": "202510809", "Cno": "1", "Grade": 91})
check("提示为录入成功", "录入成功" in msg["message"], str(msg))
msg = expect_ok("修改成绩为 88", "POST", "/api/grades",
                {"Sno": "202510809", "Cno": "1", "Grade": 88})
check("提示为修改成功", "修改成功" in msg["message"], str(msg))
msg = expect_ok("成绩置空（暂未录入）", "POST", "/api/grades",
                {"Sno": "202510809", "Cno": "1", "Grade": None})
rows = expect_ok("成绩列表", "GET", "/api/grades")
g = next(r for r in rows if r["Sno"] == "202510809" and r["Cno"] == "1")
check("NULL 已入库", g["Grade"] is None, str(g))
expect_ok("恢复成绩 91", "POST", "/api/grades",
          {"Sno": "202510809", "Cno": "1", "Grade": 91})
expect_err("成绩越界 101（第一重拦截）", "POST", "/api/grades",
           {"Sno": "202510809", "Cno": "1", "Grade": 101}, keyword="0～100")
expect_err("成绩为小数", "POST", "/api/grades",
           {"Sno": "202510809", "Cno": "1", "Grade": 88.5}, keyword="整数")
expect_err("学号不存在（外键预检）", "POST", "/api/grades",
           {"Sno": "999999999", "Cno": "1", "Grade": 80}, keyword="不存在")
expect_err("课程号不存在（外键预检）", "POST", "/api/grades",
           {"Sno": "202510809", "Cno": "77", "Grade": 80}, keyword="不存在")

print("== 功能5 按系统计 ==")
# 网安系此时成绩：78,85,96,91,58 → 人次5 平均81.6 最高96 最低58 优秀率40% 不及格1
q = f"dept={quote(NET)}&fields=total,avg,max,min,excellent,fail"
rows = expect_ok("网安系全部统计列", "GET", f"/api/stats?{q}")
check("网安平均分 81.6", rows and rows[0]["平均分"] == 81.6, str(rows))
check("网安优秀率 40 / 不及格 1",
      rows and rows[0]["优秀率(%)"] == 40.0 and rows[0]["不及格人数"] == 1, str(rows))
rows = expect_ok("仅勾选平均分", "GET", f"/api/stats?dept={quote(NET)}&fields=avg")
check("只输出选定列", rows and set(rows[0].keys()) == {"Sdept", "平均分"}, str(rows))
rows = expect_ok("全部系统计", "GET", "/api/stats?dept=&fields=avg")
check("含三个系", {r["Sdept"] for r in rows} == {NET, MAT, AIA}, str(rows))
rows = expect_ok("无成绩数据的系返回空", "GET", f"/api/stats?dept={quote('XX系')}&fields=avg")
check("空结果", rows == [], str(rows))
call_stats = call("GET", f"/api/stats?dept={quote(NET)}&fields=avg%3BDROP")
check("非法字段被白名单过滤", call_stats[0] == 200, str(call_stats))

print("== 功能6 按系排名 ==")
rows = expect_ok("网安系排名", "GET", f"/api/rank?dept={quote(NET)}")
check("5 条记录按名次排序",
      len(rows) == 5 and [r["rk"] for r in rows] == [1, 2, 3, 4, 5], str(rows))
check("第一名 郑皓宇 软件安全 96",
      rows[0]["Grade"] == 96 and rows[0]["Sname"] == "郑皓宇"
      and rows[0]["Cname"] == "软件安全", str(rows[0]))
rows = expect_ok("全部系排名", "GET", "/api/rank?dept=")
check("各系独立编号", {r["Sdept"] for r in rows} == {NET, MAT, AIA}, str(rows))

print("== 功能7 学号查询 ==")
d = expect_ok("查询 202510801", "GET", "/api/students/202510801")
check("基本信息正确", d["student"]["Sname"] == "周子墨", str(d["student"]))
check("选课 2 门", len(d["courses"]) == 2, str(d["courses"]))
expect_err("查询不存在的学号", "GET", "/api/students/111111111", keyword="不存在")

print("== 功能8 删除学生信息 ==")
# 202510804 韩雨桐：无选课记录，直接删除
msg = expect_ok("删除无成绩学生 202510804", "DELETE", "/api/students/202510804")
check("提示不含选课成绩", "选课成绩" not in msg["message"], str(msg))
rows = expect_ok("学生表", "GET", "/api/students")
check("学生数减 1", len(rows) == 15, f"{len(rows)} 行")
expect_err("再次查询已删除学生", "GET", "/api/students/202510804", keyword="不存在")
# 202510801 周子墨：有 2 条选课记录，级联删除
msg = expect_ok("删除有成绩学生 202510801（级联）", "DELETE", "/api/students/202510801")
check("提示同时删除 2 条选课成绩", "2 条选课成绩" in msg["message"], str(msg))
grades = expect_ok("成绩列表", "GET", "/api/grades")
check("该生成绩已清除", not any(g["Sno"] == "202510801" for g in grades), "")
expect_err("删除不存在的学生", "DELETE", "/api/students/999999999", keyword="不存在")

print()
print(f"测试结束：通过 {PASS} 项，失败 {FAIL} 项")
sys.exit(1 if FAIL else 0)
