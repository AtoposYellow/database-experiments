# -*- coding: utf-8 -*-
"""
配置层（config.py）：全项目所有可配置项集中在此，
其他模块一律从这里读取，改环境只改这一个文件。

架构总览（5 个模块，一个文件一个职责，调用方向自上而下）：
    config.py     配置层：数据库连接、端口、路径等全部可配置项        ← 本文件
    database.py   数据层：连接管理 / 事务 / MySQL错误翻译
    models.py     实体层：实体类与输入校验（双重验证第一重）
    services.py   业务层：六大功能的嵌入式 SQL（双重验证第二重）
    app.py        界面层：HTTP 服务与 REST 路由、程序入口

字段含义与 实验4/db.py 保持一致：
    host/port     MySQL 服务器地址与端口
    user/password 数据库账号（本机 root）
    database      数据库名（本实验使用 sms，建表由 MySQL 端执行 schema.sql 完成）
    charset       中文必须使用 utf8mb4，否则会乱码
"""

DB_CONFIG = {
    "host": "127.0.0.1",
    "port": 3306,
    "user": "root",
    "password": "root",        # ← 改成你自己的 root 密码
    "database": "sms",
    "charset": "utf8mb4",
    "connect_timeout": 5,
}

# Web 服务监听端口（命令行 --port 可覆盖）
HTTP_PORT = 8000

# 前端页面文件位置（相对本文件所在目录）
INDEX_HTML = "static/index.html"
