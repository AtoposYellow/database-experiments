CREATE SCHEMA `CSEDB_U202510828`;

USE `CSEDB_U202510828`;

CREATE TABLE Student
(
    Sno         CHAR(9) PRIMARY KEY,
    Sname       CHAR(20) UNIQUE,
    Ssex        CHAR(2),
    Sage        INT,
    Sdept       CHAR(20),
    Scholarship CHAR(2)
);

CREATE TABLE Course
(
    Cno     CHAR(4) PRIMARY KEY,
    Cname   CHAR(40),
    Cpno    CHAR(4),
    Ccredit SMALLINT,
    FOREIGN KEY (Cpno) REFERENCES Course (Cno)
);

CREATE TABLE SC
(
    Sno   CHAR(9),
    Cno   CHAR(4),
    Grade SMALLINT,
    Primary key (Sno, Cno),
    FOREIGN KEY (Sno) REFERENCES Student (Sno),
    FOREIGN KEY (Cno) REFERENCES Course (Cno)
);

DROP TABLE Course;

INSERT INTO Student (Sno, Sname, Ssex, Sage, Sdept, Scholarship)
VALUES ('202215121', '李勇', '男', 20, 'CS', '否'),
       ('202215122', '刘晨', '女', 19, 'CS', '否'),
       ('202215123', '王敏', '女', 18, 'MA', '否'),
       ('202215125', '张立', '男', 19, 'IS', '否');
SET FOREIGN_KEY_CHECKS = 0;

INSERT INTO Course (Cno, Cname, Cpno, Ccredit)
VALUES (1, '数据库', 5, 4),
       (2, '数学', NULL, 2),
       (3, '信息系统', 1, 4),
       (4, '操作系统', 6, 3),
       (5, '数据结构', 7, 4),
       (6, '数据处理', NULL, 2),
       (7, 'PASCAL语言', 6, 4);
SET FOREIGN_KEY_CHECKS = 1;

INSERT INTO SC (Sno, Cno, Grade)
VALUES ('202215121', 1, 92),
       ('202215121', 2, 85),
       ('202215121', 3, 88),
       ('202215122', 2, 90),
       ('202215122', 3, 80);

-- 扩展练习
-- 1. 查询全体学生的学号、姓名和年龄
SELECT Sno, Sname, Sage
FROM Student;

-- 2. 查询所有计算机系学生的详细记录
SELECT *
FROM Student
WHERE Sdept = 'CS';

-- 3. 找出考试成绩为优秀（90分及以上）或不及格的学生的学号、课程号及成绩
SELECT Student.Sno, SC.Cno, SC.Grade
FROM SC,
     Student
WHERE SC.Sno = Student.Sno
  AND (SC.Grade >= 90 OR SC.Grade < 60);

-- 4. 查询年龄不在19~20岁之间的学生姓名、性别和年龄
SELECT Sname, Ssex, Sage
FROM Student
WHERE Sage NOT BETWEEN 19 AND 20;

-- 5. 查询数学系（MA）、信息系（IS)的学生的姓名和所在系
SELECT Sname, Sdept
FROM Student
WHERE Sdept IN ('MA', 'IS');

-- 6. 查询名称中包含“数据”的所有课程的课程号、课程名及其学分
SELECT Cno, Cname, Ccredit
FROM Course
WHERE Cname LIKE '%数据%';

-- 7. 找出所有没有选修课成绩的学生学号和课程号
SELECT Sno, Cno
FROM SC
WHERE Grade IS NULL;

-- 8. 查询学生202215121选修课的最高分、最低分以及平均成绩
SELECT MAX(Grade), MIN(Grade), AVG(Grade)
FROM SC
WHERE Sno = '202215121';

-- 9. 查询选修了2号课程的学生的学号及其成绩，查询结果按成绩升序排列
SELECT Sno, Grade
FROM SC
WHERE Cno = '2'
ORDER BY Grade;

-- 10. 查询每个系名及其学生的平均年龄
SELECT Sdept,AVG(Sage)
FROM Student
GROUP BY Sdept;

-- 思考：查询学生平均年龄在19岁以下（含19岁）的系别及其学生的平均年龄
SELECT Sdept, AVG(Sage)
FROM Student
GROUP BY Sdept
HAVING AVG(Sage) <= 19;
