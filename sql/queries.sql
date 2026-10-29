-- 1. Кто похоронен на участке 3
SELECT p.full_name, c.name AS cemetery, pl.section, pl.plot_number, b.burial_date
FROM Burials b
JOIN People p ON p.person_id = b.person_id
JOIN Plots pl ON pl.plot_id = b.plot_id
JOIN Cemeteries c ON c.cemetery_id = pl.cemetery_id
WHERE b.plot_id = 3;


-- 2. Занятость участков по кладбищам
SELECT c.name AS cemetery,
       COUNT(pl.plot_id) AS plots,
       COUNT(b.plot_id) AS occupied,
       COUNT(pl.plot_id) - COUNT(b.plot_id) AS free
FROM Cemeteries c
JOIN Plots pl ON pl.cemetery_id = c.cemetery_id
LEFT JOIN Burials b ON b.plot_id = pl.plot_id
GROUP BY c.name;


-- 3. Кладбища, где занято больше 15 участков
SELECT c.name AS cemetery, COUNT(b.plot_id) AS occupied
FROM Cemeteries c
JOIN Plots pl ON pl.cemetery_id = c.cemetery_id
JOIN Burials b ON b.plot_id = pl.plot_id
GROUP BY c.name
HAVING COUNT(b.plot_id) > 15;


-- 4. Свободные участки
SELECT c.name AS cemetery, pl.section, pl.plot_number
FROM Plots pl
JOIN Cemeteries c ON c.cemetery_id = pl.cemetery_id
LEFT JOIN Burials b ON b.plot_id = pl.plot_id
WHERE b.plot_id IS NULL
ORDER BY c.name, pl.section, pl.plot_number;


-- 5. Люди без захоронения
SELECT person_id,
       full_name,
       COALESCE(gender, 'не указан') AS gender,
       COALESCE(date_of_birth, 'неизвестна') AS date_of_birth
FROM People
WHERE person_id NOT IN (SELECT person_id FROM Burials);


-- 6. Сколько в базе мужчин и женщин
SELECT CASE
           WHEN gender = 'М' THEN 'мужчины'
           WHEN gender = 'Ж' THEN 'женщины'
           ELSE 'не указан'
       END AS gender_group,
       COUNT(*) AS people
FROM People
GROUP BY gender_group;


-- 7. Захоронения по месяцам с нарастающим итогом
WITH monthly AS (
    SELECT strftime('%Y-%m', burial_date) AS month, COUNT(*) AS burials
    FROM Burials
    GROUP BY month
)
SELECT month, burials, SUM(burials) OVER (ORDER BY month) AS total
FROM monthly
ORDER BY month;


-- 8. Порядковый номер захоронения на каждом кладбище
SELECT c.name AS cemetery,
       b.burial_date,
       p.full_name,
       ROW_NUMBER() OVER (PARTITION BY c.name ORDER BY b.burial_date) AS number
FROM Burials b
JOIN People p ON p.person_id = b.person_id
JOIN Plots pl ON pl.plot_id = b.plot_id
JOIN Cemeteries c ON c.cemetery_id = pl.cemetery_id
ORDER BY c.name, number;
