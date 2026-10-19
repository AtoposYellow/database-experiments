/* ============================================================
   数据库系统原理  实验四  ——  SMS 库建库脚本（约束全部写在建表语句里）
   MySQL 8.4.11 / utf8mb4 / InnoDB
   ⚠ 会先 DROP 掉已有的 SMS 库
   ============================================================ */

DROP DATABASE IF EXISTS `SMS`;
CREATE DATABASE `SMS`
    DEFAULT CHARACTER SET utf8mb4
    COLLATE utf8mb4_unicode_ci;
USE `SMS`;

/* ------------------------------------------------------------
   1. 学生表
      pk  主码：Sno
      uk  候选码：Sname（实验一就是唯一约束）
      ck  用户定义完整性：性别、年龄
   ------------------------------------------------------------ */
CREATE TABLE Student
(
    Sno         CHAR(9)  NOT NULL,
    Sname       CHAR(20) NOT NULL,
    Ssex        CHAR(2)  NULL,
    Sage        SMALLINT NULL,
    Sdept       CHAR(20) NULL,
    Scholarship CHAR(2)  NULL,

    CONSTRAINT pk_student PRIMARY KEY (Sno),
    CONSTRAINT uk_student_sname UNIQUE (Sname),
    CONSTRAINT ck_student_sex CHECK (Ssex IN ('男', '女')),
    CONSTRAINT ck_student_age CHECK (Sage > 0)
) ENGINE = InnoDB
  DEFAULT CHARSET = utf8mb4
  COLLATE = utf8mb4_unicode_ci;

/* ------------------------------------------------------------
   2. 课程表（先修关系已拆到 CP，这里没有 Cpno）
   ------------------------------------------------------------ */
CREATE TABLE Course
(
    Cno     CHAR(4)  NOT NULL,
    Cname   CHAR(40) NULL,
    Ccredit SMALLINT NULL,

    CONSTRAINT pk_course PRIMARY KEY (Cno)
) ENGINE = InnoDB
  DEFAULT CHARSET = utf8mb4
  COLLATE = utf8mb4_unicode_ci;

/* ------------------------------------------------------------
   3. 选课表（m:n 联系 SC）
      fk  参照完整性：Sno → Student，Cno → Course
      ck  用户定义完整性：成绩 0～100（Grade 允许为空，空值不受 CHECK 限制）
   ------------------------------------------------------------ */
CREATE TABLE SC
(
    Sno   CHAR(9)  NOT NULL,
    Cno   CHAR(4)  NOT NULL,
    Grade SMALLINT NULL,

    CONSTRAINT pk_sc PRIMARY KEY (Sno, Cno),
    CONSTRAINT fk_sc_sno FOREIGN KEY (Sno) REFERENCES Student (Sno),
    CONSTRAINT fk_sc_cno FOREIGN KEY (Cno) REFERENCES Course (Cno),
    CONSTRAINT ck_sc_grade CHECK (Grade BETWEEN 0 AND 100)
) ENGINE = InnoDB
  DEFAULT CHARSET = utf8mb4
  COLLATE = utf8mb4_unicode_ci;

/* ------------------------------------------------------------
   4. 先修联系表（自反 m:n 联系 CP）
      两列都引用 Course(Cno)；不写 ON DELETE CASCADE，
      这样删除仍被引用的课程会报 1451，正好当外键测试用例
   ------------------------------------------------------------ */
CREATE TABLE CP
(
    Cno  CHAR(4) NOT NULL,
    Cpno CHAR(4) NOT NULL,

    CONSTRAINT pk_cp PRIMARY KEY (Cno, Cpno),
    CONSTRAINT fk_cp_cno FOREIGN KEY (Cno) REFERENCES Course (Cno),
    CONSTRAINT fk_cp_cpno FOREIGN KEY (Cpno) REFERENCES Course (Cno),
    CONSTRAINT ck_cp CHECK (Cno != Cpno)
) ENGINE = InnoDB
  DEFAULT CHARSET = utf8mb4
  COLLATE = utf8mb4_unicode_ci;

/* ------------------------------------------------------------
   5. 示例数据（实验一指导书的数据）
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

INSERT INTO CP (Cno, Cpno)
VALUES ('1', '5'),
       ('3', '1'),
       ('4', '6'),
       ('5', '7'),
       ('7', '6');

/* ------------------------------------------------------------
   6. 自检：约束是否真的建上了
   ------------------------------------------------------------ */
SHOW TABLES;
SELECT TABLE_NAME AS 表, CONSTRAINT_NAME AS 约束名, CONSTRAINT_TYPE AS 类型
FROM information_schema.TABLE_CONSTRAINTS
WHERE CONSTRAINT_SCHEMA = 'SMS'
ORDER BY TABLE_NAME, CONSTRAINT_TYPE;
SELECT CONSTRAINT_NAME AS 检查约束, CHECK_CLAUSE AS 表达式
FROM information_schema.CHECK_CONSTRAINTS
WHERE CONSTRAINT_SCHEMA = 'SMS';

/* ============================================================
   附：不想重建库、只给现有 SMS 补约束（二选一，按需执行）
   ============================================================ */
/*
USE `SMS`;

-- (1) 学分的列名与报告统一
ALTER TABLE Course RENAME COLUMN Credit TO Ccredit;

-- (2) 补唯一约束（姓名为候选码）
ALTER TABLE Student ADD CONSTRAINT uk_student_sname UNIQUE (Sname);

-- (3) 补用户定义完整性
ALTER TABLE Student ADD CONSTRAINT ck_student_sex CHECK (Ssex IN ('男', '女'));
ALTER TABLE Student ADD CONSTRAINT ck_student_age CHECK (Sage > 0);
ALTER TABLE SC      ADD CONSTRAINT ck_sc_grade   CHECK (Grade BETWEEN 0 AND 100);
ALTER TABLE CP      ADD CONSTRAINT ck_cp         CHECK (Cno <> Cpno);
*/
