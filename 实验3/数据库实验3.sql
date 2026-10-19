USE `CSEDB_U202510828`;
-- 1
CREATE OR REPLACE VIEW CS_View AS
SELECT Sno, Sname, Ssex, Sage, Sdept, Scholarship
FROM Student
WHERE Sdept = 'CS';

-- 2
SELECT *
FROM CS_View
WHERE Sno IN (SELECT Sno
              FROM SC
              WHERE Cno = '1');
-- 3
CREATE VIEW IS_View AS
SELECT Student.Sno,
       Student.Sname,
       Student.Ssex,
       Student.Sage,
       Student.Sdept,
       SC.Cno,
       SC.Grade
FROM Student,
     SC
WHERE Student.Sdept = 'IS'
  AND Student.Sno = SC.Sno
  AND SC.Grade > 80;

-- 4
SELECT *
FROM IS_View;
-- 5
DROP VIEW IS_View;

-- 创建用户 U1、U2
CREATE USER 'U1'@'%' IDENTIFIED BY '123456';
CREATE USER 'U2'@'%' IDENTIFIED BY '123456';
-- 授权
GRANT SELECT, UPDATE
    ON `CSEDB_U202510828`.Student
    TO 'U1'@'%';

GRANT INSERT
    ON `CSEDB_U202510828`.SC
    TO 'U2'@'%';

SHOW GRANTS FOR 'U1';
SHOW GRANTS FOR 'U2';

SELECT CURRENT_USER(), USER();

REVOKE SELECT, UPDATE
    ON TABLE `CSEDB_U202510828`.Student
    FROM U1;
SHOW GRANTS FOR 'U1';

DELIMITER //

CREATE TRIGGER Update_Grade
    AFTER UPDATE
    ON SC
    FOR EACH ROW
BEGIN
    IF (NEW.Grade >= 95) THEN
        UPDATE Student
        SET Scholarship = '是'
        WHERE Sno = NEW.Sno
          AND Scholarship = '否';
    END IF;

    IF (NEW.Grade < 95) AND (OLD.Grade > 95) THEN
        IF NOT EXISTS(SELECT *
                      FROM SC
                      WHERE Grade >= 95
                        AND Sno = NEW.Sno)
        THEN
            UPDATE Student
            SET Scholarship = '否'
            WHERE Sno = NEW.Sno
              AND Scholarship = '是';
        END IF;
    END IF;
END//

DELIMITER ;

SHOW TRIGGERS FROM `CSEDB_U202510828`;

DROP TRIGGER Update_Grade;

UPDATE SC
SET Grade=80
WHERE Sno = '202215122'
  AND Cno = '1';

SELECT Sno, Scholarship
FROM Student
WHERE Sno = '202215122';

DROP TRIGGER Update_Grade;
SHOW TRIGGERS FROM `CSEDB_U202510828`;

DELIMITER //

CREATE PROCEDURE Cal_grade(
    OUT outAvg_grade NUMERIC(5, 2),
    OUT outMax_grade NUMERIC(5, 2)
)
BEGIN
    DECLARE avg_grade NUMERIC(5, 2);
    DECLARE max_grade NUMERIC(5, 2);
    SELECT AVG(SC.Grade)
    INTO avg_grade
    FROM SC,
         Student
    WHERE SC.Sno = Student.Sno
      AND Student.Sdept = 'CS';

    SELECT MAX(SC.Grade)
    INTO max_grade
    FROM SC,
         Student
    WHERE SC.Sno = Student.Sno
      AND Student.Sdept = 'CS';

    SET outAvg_grade = Round(avg_grade,2);
    SET outMax_grade = Round(max_grade,2);

END//

DELIMITER ;

CALL Cal_grade(@outAvg_grade, @outMax_grade);
SELECT FORMAT(@outAvg_grade, 2) AS 平均成绩, FORMAT(@outMax_grade, 2) AS 最高成绩;

CREATE PROCEDURE Lookup(
    IN inSno CHAR(9)
)
BEGIN
    SELECT Student.Sno,
           Student.Sname,
           Course.Cname,
           SC.Grade
    FROM Student,
         SC,
         Course
    WHERE Student.Sno = SC.Sno
      AND SC.Cno = Course.Cno
      AND Student.Sno = inSno
    ORDER BY Course.Cno;

END;

CALL Lookup('202215122');

-- 14.存储函数
CREATE FUNCTION LKUP(
    inSno CHAR(9)
)
    RETURNS JSON
    READS SQL DATA
BEGIN
    DECLARE result JSON;
    SELECT JSON_ARRAYAGG(obj1)
    INTO result
    FROM (SELECT JSON_OBJECT(
                         'Sno', Student.Sno,
                         'Sname', Student.Sname,
                         'Cname', Course.Cname,
                         'Grade', SC.Grade
                 ) AS obj1
          FROM Student,
               SC,
               Course
          WHERE Student.Sno = SC.Sno
            AND SC.Cno = Course.Cno
            AND Student.Sno = inSno
          ORDER BY Course.Cno) AS obj2;

    RETURN result;

END;

SELECT LKUP('202215122');

-- 15
UPDATE SC
SET Grade = 120
WHERE Sno = '202215122'
  AND Cno = '1';

SELECT *
FROM SC
WHERE Sno = '202215122'
  AND Cno = '1';

UPDATE SC
SET Grade = 75
WHERE Sno = '202215122'
  AND Cno = '1';

ALTER TABLE SC
    ADD CONSTRAINT CK_Grade CHECK (Grade >= 0 AND Grade <= 100);
UPDATE SC
SET Grade = 120
WHERE Sno = '202215122'
  AND Cno = '1';

SELECT *
FROM SC
WHERE Sno = '202215122'
  AND Cno = '1';