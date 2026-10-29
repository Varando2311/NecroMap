import os
from datetime import datetime

import pandas as pd

PEOPLE_FILE = "source/кладбища_с_людьми_и_адресами.xlsx"
RELATIONS_FILE = "source/кладбища_с_пересечениями_и_участками.xlsx"
OUTPUT_FOLDER = "output"

problems = []


def log(sheet, rows, column, problem):
    for index, row in rows.iterrows():
        problems.append({
            "лист": sheet,
            "строка в Excel": row["excel_row"],
            "поле": column,
            "проблема": problem,
            "исходное значение": row[column],
        })


def is_date(value):
    return isinstance(value, datetime)


def check_people(people):
    inn = people["inn"].astype(str).str.strip()
    log("People", people[inn == ""], "inn", "пустой ИНН")
    log("People", people[(inn != "") & (inn.str.len() != 12)], "inn", "ИНН не из 12 цифр")
    log("People", people[people["gender"].isna()], "gender", "не указан пол")

    birth = pd.to_datetime(people["date_of_birth"], errors="coerce")
    log("People", people[people["date_of_birth"].notna() & birth.isna()], "date_of_birth",
        "вместо даты рождения текст")

    patronymic = people["full_name"].str.upper().str.split().str[-1]
    female_wrong = (people["gender"] == "Female") & patronymic.str.endswith(("ВИЧ", "ЬИЧ"))
    male_wrong = (people["gender"] == "Male") & patronymic.str.endswith(("ВНА", "ЧНА"))
    log("People", people[female_wrong | male_wrong], "gender", "пол не совпадает с отчеством")

    print("Записей без ИНН и без пола одновременно:", ((inn == "") & people["gender"].isna()).sum())

    clean = people.drop(columns=["excel_row", "year_of_birth"])
    clean["inn"] = inn.where(inn != "")
    clean["date_of_birth"] = birth.dt.strftime("%Y-%m-%d")
    return clean


def check_addresses(addresses):
    house_is_date = addresses["house_number"].apply(is_date)
    log("Addresses", addresses[house_is_date], "house_number", "номер дома превратился в дату")

    code = addresses["postal_code"].fillna(0).astype(int).astype(str)
    bad_code = addresses["postal_code"].isna() | (code.str.len() != 6)
    log("Addresses", addresses[bad_code], "postal_code", "индекс пустой или не из 6 цифр")

    clean = addresses.drop(columns=["excel_row"])
    clean.loc[house_is_date, "house_number"] = None
    clean["postal_code"] = code.where(~bad_code)
    return clean


def check_relations(assignments, participants):
    dates_per_event = participants.groupby("event_id")["date_of_burial"].nunique()
    bad_events = dates_per_event[dates_per_event > 1].index
    log("People_in_Events", participants[participants["event_id"].isin(bad_events)], "event_id",
        "у одного события разные даты")

    merged = participants.merge(assignments[["person_id", "date_of_burial"]], on="person_id",
                                suffixes=("_event", "_own"))
    after_burial = merged[(merged["role_code"] != "The Deceased")
                          & (merged["date_of_burial_event"] >= merged["date_of_burial_own"])]
    log("People_in_Events", after_burial, "person_id", "участвует в событии после своего захоронения")

    deceased = participants[participants["role_code"] == "The Deceased"]
    log("Plot_Assignments", assignments[~assignments["person_id"].isin(deceased["person_id"])],
        "person_id", "захоронен, но нет события, где он The Deceased")
    log("People_in_Events", deceased[~deceased["person_id"].isin(assignments["person_id"])],
        "person_id", "The Deceased, но нет участка")


def main():
    if not os.path.exists(PEOPLE_FILE) or not os.path.exists(RELATIONS_FILE):
        print("Положите исходные Excel-файлы в папку source/")
        return

    people = pd.read_excel(PEOPLE_FILE, sheet_name="People")
    addresses = pd.read_excel(PEOPLE_FILE, sheet_name="Addresses")
    assignments = pd.read_excel(RELATIONS_FILE, sheet_name="Plot_Assignments")
    participants = pd.read_excel(RELATIONS_FILE, sheet_name="People_in_Events")

    for table in [people, addresses, assignments, participants]:
        table["excel_row"] = table.index + 2

    print("Людей:", len(people), "адресов:", len(addresses))

    people_clean = check_people(people)
    addresses_clean = check_addresses(addresses)
    check_relations(assignments, participants)

    os.makedirs(OUTPUT_FOLDER, exist_ok=True)
    journal = pd.DataFrame(problems)
    journal.to_csv(f"{OUTPUT_FOLDER}/problems.csv", index=False, encoding="utf-8-sig")
    people_clean.to_csv(f"{OUTPUT_FOLDER}/people_clean.csv", index=False, encoding="utf-8-sig")
    addresses_clean.to_csv(f"{OUTPUT_FOLDER}/addresses_clean.csv", index=False, encoding="utf-8-sig")

    print("Найдено проблем:", len(journal))
    print(journal.groupby(["лист", "проблема"]).size().to_string())


main()
