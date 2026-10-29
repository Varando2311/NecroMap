import os
import sqlite3

import pandas as pd

DB_FILE = "data/necromap.db"


def is_valid_date(text):
    if len(text) != 10:
        return False
    day = pd.to_datetime(text, format="%Y-%m-%d", errors="coerce")
    if pd.isna(day):
        return False
    return day <= pd.Timestamp.today()


def exists(conn, table, column, value):
    count = conn.execute(f"SELECT COUNT(*) FROM {table} WHERE {column} = ?", (value,)).fetchone()[0]
    return count > 0


def add_person(conn, full_name, gender, date_of_birth):
    if full_name.strip() == "":
        return "Ошибка: ФИО не может быть пустым"
    if gender not in ["М", "Ж", ""]:
        return "Ошибка: пол может быть М, Ж или пусто"
    if date_of_birth != "" and not is_valid_date(date_of_birth):
        return "Ошибка: неверная дата рождения"

    cursor = conn.execute(
        "INSERT INTO People (full_name, gender, date_of_birth) VALUES (?, ?, ?)",
        (full_name.strip(), gender or None, date_of_birth or None),
    )
    conn.commit()
    return f"Добавлен человек, номер {cursor.lastrowid}"


def delete_person(conn, person_id):
    if not exists(conn, "People", "person_id", person_id):
        return "Ошибка: человек не найден"
    if exists(conn, "Burials", "person_id", person_id):
        return "Ошибка: нельзя удалить человека, у которого есть захоронение"

    conn.execute("DELETE FROM People WHERE person_id = ?", (person_id,))
    conn.commit()
    return "Человек удалён"


def register_burial(conn, plot_id, person_id, burial_date):
    if not is_valid_date(burial_date):
        return "Ошибка: неверная дата захоронения"
    if not exists(conn, "Plots", "plot_id", plot_id):
        return "Ошибка: участок не найден"
    if not exists(conn, "People", "person_id", person_id):
        return "Ошибка: человек не найден"
    if exists(conn, "Burials", "plot_id", plot_id):
        return "Ошибка: участок уже занят"
    if exists(conn, "Burials", "person_id", person_id):
        return "Ошибка: у этого человека уже есть захоронение"

    birth = conn.execute("SELECT date_of_birth FROM People WHERE person_id = ?", (person_id,)).fetchone()[0]
    if birth is not None and burial_date < birth:
        return "Ошибка: дата захоронения раньше даты рождения"

    conn.execute("INSERT INTO Burials (plot_id, person_id, burial_date) VALUES (?, ?, ?)",
                 (plot_id, person_id, burial_date))
    conn.commit()
    return f"Захоронение зарегистрировано: участок {plot_id}, дата {burial_date}"


def find_by_name(conn, text):
    people = pd.read_sql_query("""
        SELECT p.person_id,
               p.full_name,
               COALESCE(p.date_of_birth, '') AS date_of_birth,
               COALESCE(c.name, '') AS cemetery,
               COALESCE(b.plot_id, '') AS plot_id,
               COALESCE(b.burial_date, '') AS burial_date
        FROM People p
        LEFT JOIN Burials b ON b.person_id = p.person_id
        LEFT JOIN Plots pl ON pl.plot_id = b.plot_id
        LEFT JOIN Cemeteries c ON c.cemetery_id = pl.cemetery_id
        ORDER BY p.full_name
    """, conn)
    return people[people["full_name"].str.contains(text, case=False, regex=False)]


def show_plot(conn, plot_id):
    return pd.read_sql_query("""
        SELECT pl.plot_id, c.name AS cemetery, pl.section, pl.plot_number,
               COALESCE(p.full_name, 'свободен') AS buried,
               COALESCE(b.burial_date, '') AS burial_date
        FROM Plots pl
        JOIN Cemeteries c ON c.cemetery_id = pl.cemetery_id
        LEFT JOIN Burials b ON b.plot_id = pl.plot_id
        LEFT JOIN People p ON p.person_id = b.person_id
        WHERE pl.plot_id = ?
    """, conn, params=(plot_id,))


def free_plots(conn):
    return pd.read_sql_query("""
        SELECT c.name AS cemetery, pl.plot_id, pl.section, pl.plot_number
        FROM Plots pl
        JOIN Cemeteries c ON c.cemetery_id = pl.cemetery_id
        LEFT JOIN Burials b ON b.plot_id = pl.plot_id
        WHERE b.plot_id IS NULL
        ORDER BY c.name, pl.plot_id
    """, conn)


def occupancy(conn):
    return pd.read_sql_query("""
        SELECT c.name AS cemetery,
               COUNT(pl.plot_id) AS plots,
               COUNT(b.plot_id) AS occupied,
               COUNT(pl.plot_id) - COUNT(b.plot_id) AS free
        FROM Cemeteries c
        JOIN Plots pl ON pl.cemetery_id = c.cemetery_id
        LEFT JOIN Burials b ON b.plot_id = pl.plot_id
        GROUP BY c.name
    """, conn)


def burials_by_year(conn):
    return pd.read_sql_query("""
        SELECT strftime('%Y', burial_date) AS year, COUNT(*) AS burials
        FROM Burials
        GROUP BY year
        ORDER BY year
    """, conn)


def ask_number(text):
    answer = input(text).strip()
    if answer.isdigit():
        return int(answer)
    print("Нужно ввести число")
    return None


def print_table(table):
    if table.empty:
        print("Ничего не найдено")
    else:
        print(table.to_string(index=False))


def print_menu(is_admin):
    print()
    print("1 — найти человека по ФИО")
    print("2 — показать участок")
    print("3 — свободные участки")
    print("4 — статистика")
    if is_admin:
        print("5 — добавить человека")
        print("6 — удалить человека")
        print("7 — зарегистрировать захоронение")
    print("0 — выход")


def main():
    if not os.path.exists(DB_FILE):
        print("База не найдена. Сначала запустите: python app/create_db.py")
        return

    conn = sqlite3.connect(DB_FILE)
    conn.execute("PRAGMA foreign_keys = ON")

    role = ""
    while role not in ["1", "2"]:
        role = input("Войти как: 1 — администратор, 2 — архивариус: ").strip()
    is_admin = role == "1"

    while True:
        print_menu(is_admin)
        choice = input("Выберите пункт: ").strip()

        if choice == "0":
            break
        elif choice in ["5", "6", "7"] and not is_admin:
            print("Архивариус может только просматривать данные")
        elif choice == "1":
            print_table(find_by_name(conn, input("Часть ФИО: ").strip()))
        elif choice == "2":
            plot_id = ask_number("Номер участка: ")
            if plot_id is not None:
                print_table(show_plot(conn, plot_id))
        elif choice == "3":
            print_table(free_plots(conn))
        elif choice == "4":
            print_table(occupancy(conn))
            print()
            print_table(burials_by_year(conn))
        elif choice == "5":
            name = input("ФИО: ")
            gender = input("Пол (М/Ж, Enter — неизвестен): ").strip().upper()
            birth = input("Дата рождения ГГГГ-ММ-ДД (Enter — неизвестна): ").strip()
            print(add_person(conn, name, gender, birth))
        elif choice == "6":
            person_id = ask_number("Номер человека: ")
            if person_id is not None:
                print(delete_person(conn, person_id))
        elif choice == "7":
            plot_id = ask_number("Номер участка: ")
            person_id = ask_number("Номер человека: ")
            if plot_id is not None and person_id is not None:
                burial_date = input("Дата захоронения ГГГГ-ММ-ДД: ").strip()
                print(register_burial(conn, plot_id, person_id, burial_date))
        else:
            print("Такого пункта нет")

    conn.close()


main()
