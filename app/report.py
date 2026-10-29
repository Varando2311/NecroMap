import os
import sqlite3

import matplotlib.pyplot as plt
import pandas as pd

DB_FILE = "data/necromap.db"
REPORT_FOLDER = "reports"

conn = sqlite3.connect(DB_FILE)
plots = pd.read_sql_query("""
    SELECT pl.plot_id, c.name AS cemetery, pl.section, pl.plot_number
    FROM Plots pl
    JOIN Cemeteries c ON c.cemetery_id = pl.cemetery_id
    ORDER BY pl.plot_id
""", conn)
people = pd.read_sql_query("SELECT * FROM People ORDER BY person_id", conn)
burials = pd.read_sql_query("SELECT * FROM Burials ORDER BY burial_date", conn)
conn.close()

plots["occupied"] = plots["plot_id"].isin(burials["plot_id"])
occupancy = plots.groupby("cemetery")["occupied"].agg(["count", "sum"]).reset_index()
occupancy.columns = ["cemetery", "plots", "occupied"]
occupancy["free"] = occupancy["plots"] - occupancy["occupied"]
occupancy["load_percent"] = (occupancy["occupied"] / occupancy["plots"] * 100).round(1)

data = burials.merge(people, on="person_id")
data["burial_date"] = pd.to_datetime(data["burial_date"])
data["date_of_birth"] = pd.to_datetime(data["date_of_birth"])
data["age"] = ((data["burial_date"] - data["date_of_birth"]).dt.days / 365.25).astype(int)
data["month"] = data["burial_date"].dt.strftime("%Y-%m")

monthly = data.groupby("month").size().reset_index(name="burials")
monthly["total"] = monthly["burials"].cumsum()

first, last = data["burial_date"].min(), data["burial_date"].max()
months = (last.year - first.year) * 12 + last.month - first.month + 1
per_month = len(data) / months
free = occupancy["free"].sum()

print(occupancy.to_string(index=False))
print()
print("Месяцев:", months, "захоронений:", len(data), "в месяц:", round(per_month, 2))
print("Свободных мест хватит примерно на", round(free / per_month), "мес.")
print("Возраст: средний", round(data["age"].mean(), 1), "мин", data["age"].min(), "макс", data["age"].max())

os.makedirs(REPORT_FOLDER, exist_ok=True)

plt.figure(figsize=(6, 4))
plt.bar(occupancy["cemetery"], occupancy["occupied"], label="Занято")
plt.bar(occupancy["cemetery"], occupancy["free"], bottom=occupancy["occupied"], label="Свободно")
plt.title("Занятость участков")
plt.ylabel("Участков")
plt.ylim(0, 32)
plt.legend()
plt.savefig(f"{REPORT_FOLDER}/occupancy.png", dpi=120)
plt.close()

plt.figure(figsize=(9, 4))
plt.plot(monthly["month"], monthly["total"], marker="o")
plt.title("Захоронения нарастающим итогом")
plt.xticks(rotation=60)
plt.tight_layout()
plt.savefig(f"{REPORT_FOLDER}/burials_by_month.png", dpi=120)
plt.close()

plt.figure(figsize=(6, 4))
plt.hist(data["age"], bins=range(60, 101, 5), edgecolor="white")
plt.title("Возраст на момент захоронения")
plt.xlabel("Лет")
plt.ylabel("Человек")
plt.savefig(f"{REPORT_FOLDER}/age_distribution.png", dpi=120)
plt.close()

plots_sheet = plots[["plot_id", "cemetery", "section", "plot_number"]].copy()
plots_sheet.columns = ["Участок", "Кладбище", "Секция", "Номер"]
plots_sheet["Статус"] = [f'=IF(COUNTIF(Захоронения!A:A,A{row})>0,"Занят","Свободен")'
                         for row in range(2, len(plots_sheet) + 2)]

people_sheet = people.copy()
people_sheet["date_of_birth"] = pd.to_datetime(people_sheet["date_of_birth"]).dt.date
people_sheet.columns = ["Номер", "ФИО", "Пол", "Дата рождения"]

burials_sheet = burials.copy()
burials_sheet["burial_date"] = pd.to_datetime(burials_sheet["burial_date"]).dt.date
burials_sheet.columns = ["Участок", "Номер человека", "Дата захоронения"]
rows = range(2, len(burials_sheet) + 2)
burials_sheet["ФИО"] = [f"=VLOOKUP(B{row},Люди!A:D,2,FALSE)" for row in rows]
burials_sheet["Возраст"] = [f'=DATEDIF(VLOOKUP(B{row},Люди!A:D,4,FALSE),C{row},"Y")' for row in rows]
burials_sheet["Год"] = [f"=YEAR(C{row})" for row in rows]

analysis = [
    ["Всего участков", "=COUNT(Участки!A:A)"],
    ["Занято", '=COUNTIF(Участки!E:E,"Занят")'],
    ["Свободно", "=B2-B3"],
    ["Загрузка, %", "=ROUND(B3/B2*100,1)"],
    ["Средний возраст", "=ROUND(AVERAGE(Захоронения!E:E),1)"],
    ["Минимальный возраст", "=MIN(Захоронения!E:E)"],
    ["Максимальный возраст", "=MAX(Захоронения!E:E)"],
    ["Месяцев", '=DATEDIF(MIN(Захоронения!C:C),MAX(Захоронения!C:C),"M")+1'],
    ["Захоронений в месяц", "=ROUND(B3/B9,2)"],
    ["Свободных мест хватит, мес.", '=IF(B10=0,"нет данных",ROUND(B4/B10,0))'],
]
for name in occupancy["cemetery"]:
    analysis.append([f"Занято: {name}", f'=COUNTIFS(Участки!B:B,"{name}",Участки!E:E,"Занят")'])
for year in sorted(data["burial_date"].dt.year.unique()):
    analysis.append([f"Захоронений в {year}", f"=COUNTIF(Захоронения!F:F,{year})"])
analysis = pd.DataFrame(analysis, columns=["Показатель", "Значение"])

with pd.ExcelWriter(f"{REPORT_FOLDER}/report.xlsx", engine="openpyxl", date_format="YYYY-MM-DD") as writer:
    analysis.to_excel(writer, sheet_name="Анализ", index=False)
    plots_sheet.to_excel(writer, sheet_name="Участки", index=False)
    people_sheet.to_excel(writer, sheet_name="Люди", index=False)
    burials_sheet.to_excel(writer, sheet_name="Захоронения", index=False)
    writer.sheets["Анализ"].column_dimensions["A"].width = 30
    writer.sheets["Люди"].column_dimensions["B"].width = 35
    writer.sheets["Захоронения"].column_dimensions["D"].width = 35

print("Отчёт сохранён в папку", REPORT_FOLDER)
