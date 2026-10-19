# -*- coding: utf-8 -*-
"""
教务管理系统（学生选课管理）—— Web 服务入口。

启动方式：
    python app.py            # 启动服务（默认 http://127.0.0.1:8000）
    python app.py --port 9000

说明：建库与建表（DDL）属于逻辑设计，须先在 MySQL 端（DataGrip）执行
      schema.sql 完成；本程序只连接已有数据库并执行增删改查（DML），
      运行时不执行任何 CREATE/DROP 语句。

架构总览（前后端分离；后端 5 个模块，一个文件一个职责，
调用方向自上而下，本文件是最上层的界面层）：

    前端   static/index.html  单页交互页面（按钮 + 表单 + 表格，fetch 调 API）
    ────────────────────────────────────────────────────────────────
    后端   app.py        界面层：HTTP 服务与 REST 路由、程序入口      ← 本文件
           services.py   业务层：六大功能的嵌入式 SQL（双重验证第二重）
           models.py     实体层：实体类与输入校验（双重验证第一重）
           database.py   数据层：连接管理 / 事务 / MySQL错误翻译
           config.py     配置层：数据库连接、端口、路径等全部可配置项
    ────────────────────────────────────────────────────────────────
           schema.sql    建库脚本（四个关系模式 + 完整性约束 + 示例数据），
                         在 MySQL 端执行，不参与 Python 运行时

对应报告 5.1 需求分析的六项功能 / 页面上的七个按钮：
    1 录入新生信息            POST   /api/students
    2 学生信息修改            PUT    /api/students/{sno}
    3 课程信息维护            POST/PUT/DELETE /api/courses[/{cno}]
    4 录入修改学生成绩        POST   /api/grades
    5 统计成绩信息            GET    /api/stats?dept=网络空间安全学院&fields=avg
    6 按系排名                GET    /api/rank?dept=网络空间安全学院
    7 学生信息查询            GET    /api/students/{sno}

仅使用 Python 标准库 http.server，无需额外安装 Web 框架；
访问 MySQL 依赖 PyMySQL（见 requirements.txt，建议使用 .venv 虚拟环境）。
"""

import argparse
import json
import re
import sys
from decimal import Decimal
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse

import pymysql

from config import DB_CONFIG, HTTP_PORT, INDEX_HTML
from database import Database
from models import Student, Course, Enrollment, ValidationError
from services import (BizError, CourseService, GradeService,
                      StatService, StudentService)

# 让 Windows 控制台也能正常打印中文
try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

BASE_DIR = Path(__file__).resolve().parent

# ---------------------------------------------------------------------- #
# 服务对象：一个进程一份（Database 每次操作独立建连，线程安全）
# ---------------------------------------------------------------------- #
DB = Database(DB_CONFIG)
student_svc = StudentService(DB)
course_svc = CourseService(DB)
grade_svc = GradeService(DB)
stat_svc = StatService(DB)


class ApiRouter:
    """极简 REST 路由器：把 (方法, 路径) 映射到服务层调用。"""

    def __init__(self):
        # 每条路由：(HTTP 方法, 正则, 处理函数(query, body, *分组))
        self.routes: list[tuple[str, re.Pattern, object]] = []
        self._register()

    def add(self, method: str, pattern: str, fn):
        self.routes.append((method, re.compile("^" + pattern + "$"), fn))

    # ------------------------------------------------------------------ #
    # 全部路由
    # ------------------------------------------------------------------ #
    def _register(self):
        self.add("GET", r"/api/ping", self._ping)

        # —— 功能 1/2：学生 ——
        self.add("GET", r"/api/students", lambda q, b: student_svc.list_students())
        self.add("POST", r"/api/students",
                 lambda q, b: student_svc.add_student(Student.from_dict(b)))
        self.add("PUT", r"/api/students/([^/]+)",
                 lambda q, b, sno: student_svc.update_student(sno, Student.from_dict(b)))
        # —— 功能 7：按学号查询 ——
        self.add("GET", r"/api/students/([^/]+)",
                 lambda q, b, sno: student_svc.query_detail(sno))
        # —— 扩展功能：删除学生信息（其选课成绩一并删除）——
        self.add("DELETE", r"/api/students/([^/]+)",
                 lambda q, b, sno: {"message": student_svc.delete_student(sno)})

        # —— 功能 3：课程维护 ——
        self.add("GET", r"/api/courses", lambda q, b: course_svc.list_courses())
        self.add("POST", r"/api/courses",
                 lambda q, b: course_svc.add_course(Course.from_dict(b)))
        self.add("PUT", r"/api/courses/([^/]+)",
                 lambda q, b, cno: course_svc.update_course(cno, Course.from_dict(b)))
        self.add("DELETE", r"/api/courses/([^/]+)",
                 lambda q, b, cno: course_svc.delete_course(cno))

        # —— 功能 4：成绩 ——
        self.add("GET", r"/api/grades", lambda q, b: grade_svc.list_grades())
        self.add("POST", r"/api/grades",
                 lambda q, b: {"message": grade_svc.set_grade(Enrollment.from_dict(b))})

        # —— 功能 5：按系统计 ——
        self.add("GET", r"/api/stats", self._stats)
        # —— 功能 6：按系排名 ——
        self.add("GET", r"/api/rank",
                 lambda q, b: stat_svc.dept_rank(q.get("dept", "")))

    # ------------------------------------------------------------------ #
    # 个别需要解释请求参数的处理函数
    # ------------------------------------------------------------------ #
    @staticmethod
    def _ping(query, body):
        info = DB.query_one("SELECT VERSION() AS ver, DATABASE() AS db")
        return {"mysql": info["ver"], "database": info["db"]}

    @staticmethod
    def _stats(query, body):
        dept = query.get("dept", "")
        fields = [f for f in query.get("fields", "").split(",") if f]
        return stat_svc.dept_stats(dept, fields)

    # ------------------------------------------------------------------ #
    def dispatch(self, method: str, path: str, query: dict, body: dict):
        """按 (方法, 路径) 找路由并执行；返回 (HTTP 状态码, 响应字典)。"""
        for m, pattern, fn in self.routes:
            match = pattern.match(path)
            if match and m == method:
                data = fn(query, body, *match.groups())
                return 200, {"ok": True, "message": "操作成功",
                             "data": data if data is not None else {}}
        return 404, {"ok": False, "message": f"接口不存在：{method} {path}"}


ROUTER = ApiRouter()


class AppHandler(BaseHTTPRequestHandler):
    """HTTP 请求处理器：静态首页 + JSON API。"""

    server_version = "SMS/1.0"

    # --------------------------- 通用工具 ----------------------------- #
    def _send_json(self, status: int, payload: dict):
        # MySQL 聚合函数（AVG/ROUND 等）返回 Decimal，这里转成 float 再输出
        def _default(o):
            return float(o) if isinstance(o, Decimal) else str(o)

        body = json.dumps(payload, ensure_ascii=False, default=_default).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _send_file(self, path: Path, mime: str):
        try:
            data = path.read_bytes()
        except OSError:
            self._send_json(404, {"ok": False, "message": "文件不存在"})
            return
        self.send_response(200)
        self.send_header("Content-Type", f"{mime}; charset=utf-8")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def _read_json_body(self) -> dict:
        length = int(self.headers.get("Content-Length") or 0)
        if length == 0:
            return {}
        if length > 1_000_000:
            raise BizError("请求体过大")
        raw = self.rfile.read(length)
        try:
            data = json.loads(raw.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError):
            raise BizError("请求体不是合法的 JSON")
        if not isinstance(data, dict):
            raise BizError("请求体必须是 JSON 对象")
        return data

    def _handle(self, method: str):
        parsed = urlparse(self.path)
        path = parsed.path.rstrip("/") or "/"
        query = {k: v[0] for k, v in parse_qs(parsed.query).items()}

        # 静态首页
        if method == "GET" and path in ("/", "/index.html"):
            self._send_file(BASE_DIR / INDEX_HTML, "text/html")
            return
        if method == "GET" and path == "/favicon.ico":
            self._send_json(204, {"ok": True})
            return

        # JSON API
        try:
            body = self._read_json_body() if method in ("POST", "PUT") else {}
            status, payload = ROUTER.dispatch(method, path, query, body)
            self._send_json(status, payload)
        except ValidationError as e:                     # 第一重校验失败
            self._send_json(400, {"ok": False, "message": e.message, "hint": e.hint})
        except BizError as e:                            # 业务规则 / 约束翻译
            self._send_json(e.status, {"ok": False, "message": e.message, "hint": e.hint})
        except pymysql.err.Error as e:                   # 数据库层错误
            self._send_json(500, {"ok": False,
                                  "message": f"数据库错误：{e.args[1] if len(e.args) > 1 else e}",
                                  "hint": "请检查 MySQL 是否启动、config.py 配置是否正确"})
        except Exception as e:                           # 兜底
            self._send_json(500, {"ok": False, "message": f"服务器内部错误：{e}"})

    # HTTP 动词入口
    def do_GET(self):
        self._handle("GET")

    def do_POST(self):
        self._handle("POST")

    def do_PUT(self):
        self._handle("PUT")

    def do_DELETE(self):
        self._handle("DELETE")

    def log_message(self, fmt, *args):
        """精简访问日志。"""
        sys.stderr.write("[SMS] %s - %s\n" % (self.address_string(), fmt % args))


# ---------------------------------------------------------------------- #
# 启动
# ---------------------------------------------------------------------- #
def main():
    parser = argparse.ArgumentParser(description="教务管理系统")
    parser.add_argument("--port", type=int, default=HTTP_PORT,
                        help=f"监听端口，默认 {HTTP_PORT}")
    args = parser.parse_args()

    try:
        server = ThreadingHTTPServer(("0.0.0.0", args.port), AppHandler)
    except OSError as e:
        print(f"× 端口 {args.port} 启动失败：{e}\n  换一个端口试试：python app.py --port 9000")
        sys.exit(1)

    print("=" * 56)
    print("  教务管理系统已启动")
    print(f"  首页       http://127.0.0.1:{args.port}/")
    print(f"  数据库     MySQL @ {DB_CONFIG['host']}:{DB_CONFIG['port']}"
          f" / {DB_CONFIG['database']}")
    print("  功能按钮   1 录入新生   2 学生修改   3 课程维护")
    print("             4 成绩录入   5 成绩统计   6 按系排名   7 学生信息查询")
    print("             8 删除学生")
    print("  停止服务   Ctrl + C")
    print("=" * 56)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\n服务已停止。")


if __name__ == "__main__":
    main()
