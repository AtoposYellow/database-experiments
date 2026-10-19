CREATE DATABASE IF NOT EXISTS `sms`
    DEFAULT CHARACTER SET utf8mb4
    COLLATE utf8mb4_unicode_ci;
USE `sms`;

-- 删除旧表（顺序：先子表再父表）
DROP TABLE IF EXISTS CP;
DROP TABLE IF EXISTS SC;
DROP TABLE IF EXISTS Course;
DROP TABLE IF EXISTS Student;

-- 1. 学生表 Student（学号，姓名，性别，年龄，所在系，奖学金）
CREATE TABLE Student
(
    Sno         CHAR(9)  NOT NULL,
    Sname       CHAR(20) NOT NULL,
    Ssex        CHAR(2)  NULL,
    Sage        SMALLINT NULL,
    Sdept       CHAR(20) NULL,
    Scholarship CHAR(2)  NULL,
    CONSTRAINT pk_student      PRIMARY KEY (Sno),
    CONSTRAINT uk_student_sname UNIQUE (Sname),
    CONSTRAINT ck_student_sex  CHECK (Ssex IN ('男', '女')),
    CONSTRAINT ck_student_age  CHECK (Sage > 0)
) ENGINE = InnoDB
  DEFAULT CHARSET = utf8mb4
  COLLATE = utf8mb4_unicode_ci;

CREATE TABLE Course
(
    Cno     CHAR(4)      NOT NULL,
    Cname   CHAR(40)     NULL,
    Ccredit DECIMAL(4,2) NULL,
    CONSTRAINT pk_course PRIMARY KEY (Cno),
    CONSTRAINT ck_course_credit CHECK (Ccredit >= 0 AND Ccredit <= 10)
) ENGINE = InnoDB
  DEFAULT CHARSET = utf8mb4
  COLLATE = utf8mb4_unicode_ci;

-- ------------------------------------------------------------
-- 3. 选课表 SC（学号，课程号，成绩）—— m:n 联系
--    主码：(Sno, Cno)；外键：参照 Student / Course；
--    CHECK：成绩 0～100（Grade 允许 NULL = 暂未录入）
-- ------------------------------------------------------------
CREATE TABLE SC
(
    Sno   CHAR(9)  NOT NULL,
    Cno   CHAR(4)  NOT NULL,
    Grade SMALLINT NULL,
    CONSTRAINT pk_sc      PRIMARY KEY (Sno, Cno),
    CONSTRAINT fk_sc_sno  FOREIGN KEY (Sno) REFERENCES Student (Sno),
    CONSTRAINT fk_sc_cno  FOREIGN KEY (Cno) REFERENCES Course (Cno),
    CONSTRAINT ck_sc_grade CHECK (Grade BETWEEN 0 AND 100)
) ENGINE = InnoDB
  DEFAULT CHARSET = utf8mb4
  COLLATE = utf8mb4_unicode_ci;

-- ------------------------------------------------------------
-- 4. 先修表 CP（课程号，先修课程号）—— 课程实体内部的自反 m:n 联系
--    两列都是外键，参照 Course(Cno)；CHECK：不能以自身为先修
-- ------------------------------------------------------------
CREATE TABLE CP
(
    Cno  CHAR(4) NOT NULL,
    Cpno CHAR(4) NOT NULL,
    CONSTRAINT pk_cp     PRIMARY KEY (Cno, Cpno),
    CONSTRAINT fk_cp_cno  FOREIGN KEY (Cno)  REFERENCES Course (Cno),
    CONSTRAINT fk_cp_cpno FOREIGN KEY (Cpno) REFERENCES Course (Cno),
    CONSTRAINT ck_cp CHECK (Cno <> Cpno)
) ENGINE = InnoDB
  DEFAULT CHARSET = utf8mb4
  COLLATE = utf8mb4_unicode_ci;

-- 5. 添加数据

INSERT INTO Student (Sno, Sname, Ssex, Sage, Sdept, Scholarship)
VALUES ('202510801', '周子墨', '男', 19, '网络空间安全学院', '否'),
       ('202510802', '林诗涵', '女', 18, '网络空间安全学院', '否'),
       ('202510803', '郑皓宇', '男', 19, '网络空间安全学院', '是'),
       ('202510804', '韩雨桐', '女', 18, '网络空间安全学院', '否'),
       ('202510805', '冯思远', '男', 20, '网络空间安全学院', '否'),
       ('202510806', '沈乐怡', '女', 19, '材料科学与工程学院', '否'),
       ('202510807', '许博文', '男', 18, '材料科学与工程学院', '否'),
       ('202510808', '苏念慈', '女', 19, '材料科学与工程学院', '是'),
       ('202510809', '曹俊杰', '男', 20, '材料科学与工程学院', '否'),
       ('202510810', '严语嫣', '女', 18, '材料科学与工程学院', '否'),
       ('202510811', '罗天翊', '男', 19, '人工智能与自动化学院', '否'),
       ('202510812', '高清雅', '女', 18, '人工智能与自动化学院', '否'),
       ('202510813', '石景行', '男', 19, '人工智能与自动化学院', '否'),
       ('202510814', '邵一诺', '女', 20, '人工智能与自动化学院', '是'),
       ('202510815', '钟昊然', '男', 18, '人工智能与自动化学院', '否');

INSERT INTO Course (Cno, Cname, Ccredit)
VALUES ('1',  '软件安全', 3),
       ('2',  '数据库系统原理', 3),
       ('3',  '网络安全程序设计', 2),
       ('4',  '编译原理', 2),
       ('5',  '汇编语言与逆向技术基础', 2),
       ('6',  '计算机基础', 2),
       ('7',  'C语言程序设计', 2),
       ('8',  '微积分（B）（上）', 5.5),
       ('9',  '高级密码学', 2),
       ('10', '工程化学', 2),
       ('11', '电工技术', 2),
       ('12', '材料科学基础（上）', 3),
       ('13', '热处理原理与工艺', 3),
       ('14', '计算材料学', 3),
       ('15', '半导体物理与器件', 3),
       ('17', '电路理论', 4),
       ('18', '最优化理论与方法', 3),
       ('19', '智能机器人', 2),
       ('20', '计算机视觉', 2),
       ('21', '智能芯片设计', 2);

INSERT INTO SC (Sno, Cno, Grade)
VALUES ('202510801', '1', 78),
       ('202510801', '2', 85),
       ('202510803', '1', 96),
       ('202510803', '2', 91),
       ('202510805', '2', 58),
       ('202510806', '10', 88),
       ('202510806', '12', 92),
       ('202510808', '12', 96),
       ('202510808', '13', 74),
       ('202510810', '10', 55),
       ('202510811', '16', 90),
       ('202510812', '17', 82),
       ('202510814', '18', 98),
       ('202510814', '20', 87),
       ('202510815', '16', 45);

-- 先修关系 (Cno, Cpno)：修 Cno 之前应先修 Cpno
INSERT INTO CP (Cno, Cpno)
VALUES ('1',  '5'),  -- 软件安全              ← 汇编语言与逆向技术基础
       ('3',  '1'),  -- 网络安全程序设计       ← 软件安全
       ('4',  '7'),  -- 编译原理              ← C语言程序设计
       ('5',  '7'),  -- 汇编语言与逆向技术基础 ← C语言程序设计
       ('7',  '6'),  -- C语言程序设计          ← 计算机基础
       ('12', '10'), -- 材料科学基础（上）     ← 工程化学
       ('13', '12'), -- 热处理原理与工艺       ← 材料科学基础（上）
       ('14', '12'), -- 计算材料学            ← 材料科学基础（上）
       ('15', '12'), -- 半导体物理与器件       ← 材料科学基础（上）
       ('18', '8'),  -- 最优化理论与方法       ← 微积分（B）（上）
       ('19', '17'), -- 智能机器人            ← 电路理论
       ('20', '18'), -- 计算机视觉            ← 最优化理论与方法
       ('21', '17'); -- 智能芯片设计          ← 电路理论
