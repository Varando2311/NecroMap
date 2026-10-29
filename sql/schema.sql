PRAGMA foreign_keys = ON;

CREATE TABLE Cemeteries (
    cemetery_id INTEGER PRIMARY KEY,
    name TEXT NOT NULL UNIQUE,
    city TEXT
);

CREATE TABLE Plots (
    plot_id INTEGER PRIMARY KEY,
    cemetery_id INTEGER NOT NULL REFERENCES Cemeteries (cemetery_id),
    section TEXT NOT NULL,
    plot_number INTEGER NOT NULL,
    UNIQUE (cemetery_id, section, plot_number)
);

CREATE TABLE People (
    person_id INTEGER PRIMARY KEY,
    full_name TEXT NOT NULL,
    gender TEXT CHECK (gender IN ('М', 'Ж')),
    date_of_birth TEXT
);

CREATE TABLE Burials (
    plot_id INTEGER PRIMARY KEY REFERENCES Plots (plot_id),
    person_id INTEGER NOT NULL UNIQUE REFERENCES People (person_id),
    burial_date TEXT NOT NULL
);
