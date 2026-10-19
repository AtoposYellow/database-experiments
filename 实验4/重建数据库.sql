/* ============================================================
   数据库系统原理  实验四
   重建数据库脚本（与第五、六章的设计结果一致：4 个基本表）
   库名沿用 CSEDB_U202510828（MySQL 的 lower_case_table_names=1，
   实际存储为小写 csedb_u202510828，SQL 里写大写同样可用）

   ⚠ 执行前先备份（PowerShell）：
     & "D:\Program Files\MySQL\MySQL Server 8.4\bin\mysqldump.exe" `
        -u root -proot --databases CSEDB_U202510828 --routines --triggers `
        > backup_csedb.sql
   ============================================================ */

DROP DATABASE IF EXISTS `CSEDB_U202510828`;
CREATE DATABASE `CSEDB_U202510828`
    DEFAULT CHARACTER SET utf8mb4
    COLLATE utf8mb4_unicode_ci;
USE `CSEDB_U202510828`;

/* ------------------------------------------------------------
   1. 学生表
   ------------------------------------------------------------ */
CREATE TABLE Student
(
    Sno         CHAR(9)  NOT NULL,
    Sname       CHAR(20) NULL,
    Ssex        CHAR(2)  NULL,
    Sage        INT      NULL,
    Sdept       CHAR(20) NULL,
    Scholarship CHAR(2)  NULL,
    CONSTRAINT pk_student PRIMARY KEY (Sno),
    CONSTRAINT uk_student_sname UNIQUE (Sname),
    CONSTRAINT ck_student_sex CHECK (Ssex IN ('男', '女')),
    CONSTRAINT ck_student_age CHECK (Sage > 0)
) ENGINE = InnoDB
  DEFAULT CHARSET = utf8mb4 COLLATE = utf8mb4_unicode_ci;

/* ------------------------------------------------------------
   2. 课程表（先修关系已移出，不再有 Cpno 列）
   ------------------------------------------------------------ */
CREATE TABLE Course
(
    Cno     CHAR(4)  NOT NULL,
    Cname   CHAR(40) NULL,
    Ccredit SMALLINT NULL,
    CONSTRAINT pk_course PRIMARY KEY (Cno)
) ENGINE = InnoDB
  DEFAULT CHARSET = utf8mb4 COLLATE = utf8mb4_unicode_ci;

/* ------------------------------------------------------------
   3. 选课表（多对多联系 SC）
   ------------------------------------------------------------ */
CREATE TABLE SC
(
    Sno   CHAR(9)  NOT NULL,
    Cno   CHAR(4)  NOT NULL,
    Grade SMALLINT NULL,
    CONSTRAINT pk_sc PRIMARY KEY (Sno, Cno),
    CONSTRAINT fk_sc_sno FOREIGN KEY (Sno) REFERENCES Student (Sno),
    CONSTRAINT fk_sc_cno FOREIGN KEY (Cno) REFERENCES Course (Cno),
    CONSTRAINT ck_sc_grade CHECK (Grade >= 0 AND Grade <= 100)
) ENGINE = InnoDB
  DEFAULT CHARSET = utf8mb4 COLLATE = utf8mb4_unicode_ci;

/* ------------------------------------------------------------
   4. 先修联系表（自反多对多联系 CP）
   ------------------------------------------------------------ */
CREATE TABLE CP
(
    Cno  CHAR(4) NOT NULL,
    Cpno CHAR(4) NOT NULL,
    CONSTRAINT pk_cp PRIMARY KEY (Cno, Cpno),
    CONSTRAINT fk_cp_cno FOREIGN KEY (Cno) REFERENCES Course (Cno),
    CONSTRAINT fk_cp_cpno FOREIGN KEY (Cpno) REFERENCES Course (Cno),
    CONSTRAINT ck_cp CHECK (Cno <> Cpno)
) ENGINE = InnoDB
  DEFAULT CHARSET = utf8mb4 COLLATE = utf8mb4_unicode_ci;

/* ------------------------------------------------------------
   5. 示例数据（实验一指导书给出的数据）
   ------------------------------------------------------------ */
INSERT INTO Student (Sno, Sname, Ssex, Sage, Sdept, Scholarship)
VALUES ('202215121', '李勇', '男', 20, 'CS', '否'),
       ('202215122', '刘晨', '女', 19, 'CS', '否'),
       ('202215123', '王敏', '女', 18, 'MA', '否'),
       ('202215125', '张立', '男', 19, 'IS', '否');

INSERT INTO Course (Cno, Cname, Ccredit)
VALUES ('1', '数据库', 4),
       ('2', '数学', 2),
       ('3', '信息系统', 4),
       ('4', '操作系统', 3),
       ('5', '数据结构', 4),
       ('6', '数据处理', 2),
       ('7', 'PASCAL语言', 4);

INSERT INTO SC (Sno, Cno, Grade)
VALUES ('202215121', '1', 92),
       ('202215121', '2', 85),
       ('202215121', '3', 88),
       ('202215122', '2', 90),
       ('202215122', '3', 80);

-- 原来的 Cpno 值搬进 CP：(课程, 先修课)
INSERT INTO CP (Cno, Cpno)
VALUES ('1', '5'),   -- 数据库   ← 数据结构
       ('3', '1'),   -- 信息系统 ← 数据库
       ('4', '6'),   -- 操作系统 ← 数据处理
       ('5', '7'),   -- 数据结构 ← PASCAL语言
       ('7', '6');   -- PASCAL语言 ← 数据处理

/* ------------------------------------------------------------
   6. 建库结果自检
   ------------------------------------------------------------ */
SHOW TABLES;
SELECT 'Student' AS 表, COUNT(*) AS 行数 FROM Student
UNION ALL SELECT 'Course', COUNT(*) FROM Course
UNION ALL SELECT 'SC',     COUNT(*) FROM SC
UNION ALL SELECT 'CP',     COUNT(*) FROM CP;
SELECT * FROM CP ORDER BY Cno, Cpno;
SHOW CREATE TABLE SC\G


/* ============================================================
   附：可选重建对象（实验三用过的，需要时再执行；不需要就整段跳过）
   ============================================================ */
-- (1) CS 系视图（报告 5.4.3 用到）
CREATE OR REPLACE VIEW CS_View AS
SELECT Sno, Sname, Ssex, Sage, Sdept, Scholarship
FROM Student
WHERE Sdept = 'CS';

-- (2) 成绩更新后自动维护奖学金的触发器（实验三定义的，末尾已被删除）
DELIMITER //
CREATE TRIGGER Update_Grade
    AFTER UPDATE
    ON SC
    FOR EACH ROW
BEGIN
    IF (NEW.Grade >= 95) THEN
        UPDATE Student SET Scholarship = '是'
        WHERE Sno = NEW.Sno AND Scholarship = '否';
    END IF;

    IF (NEW.Grade < 95) AND (OLD.Grade > 95) THEN
        IF NOT EXISTS(SELECT * FROM SC WHERE Grade >= 95 AND Sno = NEW.Sno) THEN
            UPDATE Student SET Scholarship = '否'
            WHERE Sno = NEW.Sno AND Scholarship = '是';
        END IF;
    END IF;
END//
DELIMITER ;

-- (3) 实验三创建的两个用户及其表级权限
CREATE USER IF NOT EXISTS 'U1'@'%' IDENTIFIED BY '123456';
CREATE USER IF NOT EXISTS 'U2'@'%' IDENTIFIED BY '123456';
GRANT SELECT, UPDATE ON `CSEDB_U202510828`.Student TO 'U1'@'%';
GRANT INSERT ON `CSEDB_U202510828`.SC TO 'U2'@'%';
FLUSH PRIVILEGES;

-- (4) 存储过程 / 存储函数：如需保留，直接重跑 实验3\数据库实验3.sql 中
--     Cal_grade、Lookup、LKUP 三段即可（它们不依赖 Course.Cpno）。
