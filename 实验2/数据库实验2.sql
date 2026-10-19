USE `CSEDB_U202510828`;
/* 1. 查询每门课程及其被选情况（输出所有课程中每门课的课程号、课程名称、选修该课程的学生学号及成绩
      如果没有学生选择该课，则相应的学生学号及成绩为空值）*/
SELECT Course.Cno, Course.Cname, SC.Sno, SC.Grade
FROM Course
         LEFT JOIN SC ON Course.Cno = SC.Cno;

-- 2. 查询与“张立”同岁的学生的学号、姓名和年龄。（要求使用至少3种方法求解）
-- 法 1
SELECT Sno, Sname, Sage
FROM Student
WHERE Sage IN (SELECT Sage
               FROM Student
               WHERE Sname = '张立');
-- 法 2
SELECT Sno, Sname, Sage
FROM Student x
WHERE EXISTS(SELECT *
             FROM Student y
             WHERE x.Sage = y.Sage
               AND y.Sname = '张立');
-- 法 3
SELECT X.Sno, X.Sname, X.Sage
FROM Student X,
     Student Y
WHERE X.Sage = Y.Sage
  AND Y.Sname = '张立';

-- 3. 查询选修了3号课程而且成绩为良好（80~89分）的所有学生的学号和姓名
SELECT DISTINCT SC.Sno, Student.Sname
FROM SC,
     student
WHERE SC.Grade BETWEEN 80 AND 89
  AND SC.Cno = '3'
  AND SC.Sno = Student.Sno;

-- 4. 查询学生202215122选修的课程号、课程名
SELECT SC.Cno, Cname
FROM SC,
     Course
WHERE SC.Cno = Course.Cno
  AND Sno = '202215122';
-- 思考：如何查询学生202215122选修的课程号、课程名及成绩
SELECT SC.Cno, Cname, Grade
FROM Course,
     SC
WHERE SC.Cno = Course.Cno
  AND SC.Sno = '202215122';

-- 5. 找出每个学生低于他所选修课程平均成绩5分以上的课程号。（输出学号和课程号）
SELECT Sno, Cno
FROM SC X
WHERE Grade < (SELECT AVG(Grade) - 5
               FROM SC Y
               WHERE X.Sno = Y.Sno);
-- 6. 查询比所有男生年龄都小的女生的学号、姓名和年龄
SELECT Sno, Sname, Sage
FROM Student
WHERE Sage < ALL (SELECT Sage
                  FROM Student
                  WHERE Ssex = '男')
  AND Ssex = '女';

-- 7。 查询所有选修了2号课程的学生姓名及所在系
SELECT Sname, Sdept
FROM SC,
     Student
WHERE SC.Sno = Student.Sno
  AND SC.Cno = '2';

-- 8. 使用update语句把平均成绩为良的学生的年龄增加2岁，并查询出来
UPDATE Student
SET Sage = Sage + 2
WHERE Sno IN (SELECT Sno
              FROM SC
              GROUP BY Sno
              HAVING AVG(Grade) BETWEEN 80 AND 89);

SELECT DISTINCT Sage, Sname
FROM Student
WHERE Sno IN (SELECT Sno
              FROM SC
              GROUP BY Sno
              HAVING AVG(Grade) BETWEEN 80 AND 89);

-- 9. 使用insert语句增加两门课程：C语言和人工智能，并查询出来
INSERT INTO Course(Cno, Cname, Cpno, Ccredit)
VALUES ('8', 'C语言', '2', 4),
       ('9', '人工智能', '5', 4);
SELECT *
FROM Course
WHERE Cno = '8'
   OR Cno = '9';

-- 10. 使用delete语句把人工智能课程删除，并查询出来
DELETE
FROM Course
WHERE Cname = '人工智能';
SELECT *
FROM Course
WHERE Cname = '人工智能';