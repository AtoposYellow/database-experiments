/* ============================================================
   数据库系统原理  实验四
   六项系统功能的 SQL + 功能测试用例
   前提：库结构见 实验4\重建数据库.sql（Student / Course / SC / CP）
   ＝＝＝ 每条先在 DataGrip 里跑通，再换成程序里的 %s 占位符 ＝＝＝
   ============================================================ */

USE `CSEDB_U202510828`;

/* ---- 功能 1：新生入学信息增加、学生信息修改 ---------------- */
-- 查重：INSERT 前先查一次，便于给出友好提示
SELECT COUNT(*) FROM Student WHERE Sno = '202215126';

INSERT INTO Student (Sno, Sname, Ssex, Sage, Sdept, Scholarship)
VALUES ('202215126', '陈曦', '女', 18, 'CS', '否');

UPDATE Student
SET Sname = '陈曦', Ssex = '女', Sage = 19, Sdept = 'MA', Scholarship = '是'
WHERE Sno = '202215126';

SELECT * FROM Student WHERE Sno = '202215126';


/* ---- 功能 2：课程信息维护（增、改、删；先修课维护） -------- */
INSERT INTO Course (Cno, Cname, Ccredit) VALUES ('10', 'C语言程序设计', 4);
INSERT INTO CP (Cno, Cpno) VALUES ('10', '2'), ('10', '5');      -- 两门先修课

UPDATE Course SET Cname = 'C语言程序设计（二）', Ccredit = 3 WHERE Cno = '10';

-- 查某门课的先修课
SELECT cp.Cno, cp.Cpno, c.Cname AS 先修课名
FROM CP cp
         JOIN Course c ON c.Cno = cp.Cpno
WHERE cp.Cno = '10';

-- 删除一条先修关系
DELETE FROM CP WHERE Cno = '10' AND Cpno = '5';

-- 可删除的课程：没有任何选课记录
SELECT c.Cno, c.Cname
FROM Course c
WHERE NOT EXISTS (SELECT 1 FROM SC WHERE SC.Cno = c.Cno);

-- 删除课程（带业务校验：影响行数为 0 说明有选课记录，不允许删除）
DELETE FROM Course
WHERE Cno = '10'
  AND NOT EXISTS (SELECT 1 FROM SC WHERE SC.Cno = Course.Cno);

-- 附：还要确认它没有被别的课程当作先修课引用，否则外键会报 1451
SELECT * FROM CP WHERE Cpno = '10';


/* ---- 功能 3：录入、修改学生成绩 ---------------------------- */
INSERT INTO SC (Sno, Cno, Grade) VALUES ('202215123', '1', 91);

UPDATE SC SET Grade = 88 WHERE Sno = '202215123' AND Cno = '1';

-- 成绩暂未录入
UPDATE SC SET Grade = NULL WHERE Sno = '202215123' AND Cno = '1';

SELECT * FROM SC WHERE Sno = '202215123';


/* ---- 功能 4：按系统计（平均、最好、最差、优秀率、不及格人数） */
SELECT s.Sdept                                                        AS 系别,
       COUNT(sc.Grade)                                                AS 选课人次,
       ROUND(AVG(sc.Grade), 2)                                        AS 平均分,
       MAX(sc.Grade)                                                  AS 最好成绩,
       MIN(sc.Grade)                                                  AS 最差成绩,
       CONCAT(ROUND(SUM(sc.Grade >= 90) / COUNT(*) * 100, 2), '%')     AS 优秀率,
       SUM(sc.Grade < 60)                                             AS 不及格人数
FROM Student s
         JOIN SC sc ON sc.Sno = s.Sno
WHERE sc.Grade IS NOT NULL
GROUP BY s.Sdept
ORDER BY s.Sdept;


/* ---- 功能 5：按系对学生成绩排名（显示学生、课程、成绩） ----- */
SELECT s.Sdept,
       ROW_NUMBER() OVER (PARTITION BY s.Sdept ORDER BY sc.Grade DESC) AS 系内名次,
       s.Sname,
       c.Cname,
       sc.Grade
FROM Student s
         JOIN SC sc ON sc.Sno = s.Sno
         JOIN Course c ON c.Cno = sc.Cno
WHERE sc.Grade IS NOT NULL
ORDER BY s.Sdept, 系内名次;


/* ---- 功能 6：输入学号，显示基本信息 + 选课信息 -------------- */
SELECT Sno, Sname, Ssex, Sage, Sdept, Scholarship
FROM Student
WHERE Sno = '202215121';

SELECT c.Cno, c.Cname, sc.Grade
FROM SC sc
         JOIN Course c ON c.Cno = sc.Cno
WHERE sc.Sno = '202215121'
ORDER BY c.Cno;


/* ============================================================
   失败用例（功能测试用，执行前确认会报错，截图即测试证据）
   ============================================================ */
-- (1) 主码重复            ERROR 1062
INSERT INTO Student (Sno, Sname, Ssex, Sage, Sdept, Scholarship)
VALUES ('202215121', '张三', '男', 20, 'CS', '否');

-- (2) 姓名违反唯一约束    ERROR 1062
INSERT INTO Student (Sno, Sname, Ssex, Sage, Sdept, Scholarship)
VALUES ('202215999', '李勇', '男', 20, 'CS', '否');

-- (3) 成绩越界            ERROR 3819（ck_sc_grade）
UPDATE SC SET Grade = 120 WHERE Sno = '202215122' AND Cno = '2';

-- (4) 课程以自身为先修    ERROR 3819（ck_cp）
INSERT INTO CP (Cno, Cpno) VALUES ('2', '2');

-- (5) 删除仍被引用的课程  ERROR 1451（sc/cp 的外键）
DELETE FROM Course WHERE Cno = '1';

-- (6) 先修课不存在        ERROR 1452（fk_cp_cpno）
INSERT INTO CP (Cno, Cpno) VALUES ('10', '99');

-- (7) 操作不存在的数据：影响行数 0，程序需给出提示
DELETE FROM SC WHERE Sno = '999999999' AND Cno = '1';
UPDATE Student SET Sage = 20 WHERE Sno = '999999999';


/* ============================================================
   附：如果你决定不重建库，用下面几句把旧结构改成新结构
   （重建过库的话整段跳过）
   ============================================================ */
/*
CREATE TABLE CP
(
    Cno  CHAR(4) NOT NULL,
    Cpno CHAR(4) NOT NULL,
    PRIMARY KEY (Cno, Cpno),
    CONSTRAINT fk_cp_cno FOREIGN KEY (Cno) REFERENCES Course (Cno),
    CONSTRAINT fk_cp_cpno FOREIGN KEY (Cpno) REFERENCES Course (Cno),
    CONSTRAINT ck_cp CHECK (Cno <> Cpno)
);

INSERT INTO CP (Cno, Cpno) SELECT Cno, Cpno FROM Course WHERE Cpno IS NOT NULL;

SET @fk = (SELECT CONSTRAINT_NAME FROM information_schema.KEY_COLUMN_USAGE
           WHERE TABLE_SCHEMA = 'CSEDB_U202510828' AND TABLE_NAME = 'Course'
             AND COLUMN_NAME = 'Cpno' AND REFERENCED_TABLE_NAME = 'Course' LIMIT 1);
SET @sql = CONCAT('ALTER TABLE Course DROP FOREIGN KEY `', @fk, '`');
PREPARE s FROM @sql; EXECUTE s; DEALLOCATE PREPARE s;

ALTER TABLE Course DROP COLUMN Cpno;

ALTER TABLE SC ADD CONSTRAINT ck_sc_grade CHECK (Grade >= 0 AND Grade <= 100);
*/
