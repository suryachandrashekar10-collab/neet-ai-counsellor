"""
Load parsed Maharashtra CAP data from SQLite into SQL Server Express.
Instance: localhost\SQLEXPRESS  (Windows Authentication)
"""

import sqlite3
import pyodbc

SQLITE_PATH = "data/mh_cap_2025.db"
SQL_SERVER  = r"localhost\SQLEXPRESS"
DB_NAME     = "neet_counsellor"

CONN_STR = (
    f"DRIVER={{ODBC Driver 17 for SQL Server}};"
    f"SERVER={SQL_SERVER};"
    f"DATABASE=master;"
    f"Trusted_Connection=yes;"
)

BATCH_SIZE = 1000  # rows per insert batch


def get_sql_conn(database="master"):
    conn_str = (
        f"DRIVER={{ODBC Driver 17 for SQL Server}};"
        f"SERVER={SQL_SERVER};"
        f"DATABASE={database};"
        f"Trusted_Connection=yes;"
    )
    return pyodbc.connect(conn_str, autocommit=True)


def create_database(conn):
    cur = conn.cursor()
    cur.execute(f"""
        IF NOT EXISTS (SELECT name FROM sys.databases WHERE name = '{DB_NAME}')
        CREATE DATABASE {DB_NAME}
    """)
    print(f"Database '{DB_NAME}' ready")


def create_tables(conn):
    cur = conn.cursor()
    cur.execute(f"USE {DB_NAME}")

    cur.execute("""
        IF OBJECT_ID('allotments', 'U') IS NULL
        CREATE TABLE allotments (
            id            INT IDENTITY PRIMARY KEY,
            sr_no         VARCHAR(10),
            air           INT,
            neet_roll     VARCHAR(15),
            cet_form      VARCHAR(15),
            name          NVARCHAR(100),
            gender        CHAR(1),
            category      VARCHAR(10),
            quota         VARCHAR(10),
            women_quota   BIT,
            earmark       VARCHAR(5),
            retained      BIT,
            allotted      BIT,
            college_code  VARCHAR(6),
            college_name  NVARCHAR(100),
            year          SMALLINT,
            round         VARCHAR(5)
        )
    """)

    # Indexes for fast querying
    for idx_sql in [
        "IF NOT EXISTS (SELECT * FROM sys.indexes WHERE name='idx_air') CREATE INDEX idx_air ON allotments(air)",
        "IF NOT EXISTS (SELECT * FROM sys.indexes WHERE name='idx_college') CREATE INDEX idx_college ON allotments(college_code, category, round, year)",
        "IF NOT EXISTS (SELECT * FROM sys.indexes WHERE name='idx_category') CREATE INDEX idx_category ON allotments(category, year, round)",
    ]:
        cur.execute(idx_sql)

    print("Tables and indexes ready")


def load_data(sql_conn):
    sqlite_conn = sqlite3.connect(SQLITE_PATH)
    sqlite_conn.row_factory = sqlite3.Row

    # Check existing count to avoid duplicates
    cur_sql = sql_conn.cursor()
    cur_sql.execute(f"USE {DB_NAME}")
    cur_sql.execute("SELECT COUNT(*) FROM allotments")
    existing = cur_sql.fetchone()[0]
    if existing > 0:
        print(f"  {existing:,} rows already in SQL Server — skipping load")
        print("  To reload, truncate the table first: TRUNCATE TABLE allotments")
        return

    rows = sqlite_conn.execute("SELECT * FROM allotments").fetchall()
    total = len(rows)
    print(f"  Loading {total:,} rows into SQL Server...")

    insert_sql = f"""
        INSERT INTO {DB_NAME}.dbo.allotments
          (sr_no, air, neet_roll, cet_form, name, gender, category,
           quota, women_quota, earmark, retained, allotted,
           college_code, college_name, year, round)
        VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
    """

    batch = []
    loaded = 0

    for row in rows:
        batch.append((
            row["sr_no"], row["air"], row["neet_roll"], row["cet_form"],
            row["name"], row["gender"], row["category"], row["quota"],
            bool(row["women_quota"]), row["earmark"],
            bool(row["retained"]), bool(row["allotted"]),
            row["college_code"], row["college_name"],
            row["year"], row["round"]
        ))

        if len(batch) >= BATCH_SIZE:
            cur_sql.executemany(insert_sql, batch)
            loaded += len(batch)
            batch = []
            if loaded % 10000 == 0:
                print(f"    {loaded:,}/{total:,} rows loaded...")

    if batch:
        cur_sql.executemany(insert_sql, batch)
        loaded += len(batch)

    sql_conn.commit()
    print(f"  Loaded {loaded:,} rows")
    sqlite_conn.close()


def print_summary(conn):
    cur = conn.cursor()
    cur.execute(f"USE {DB_NAME}")

    total = cur.execute("SELECT COUNT(*) FROM allotments").fetchone()[0]
    allotted = cur.execute("SELECT COUNT(*) FROM allotments WHERE allotted=1").fetchone()[0]
    colleges = cur.execute("SELECT COUNT(DISTINCT college_code) FROM allotments WHERE college_code IS NOT NULL").fetchone()[0]

    print(f"\n--- Summary ---")
    print(f"  Total rows     : {total:,}")
    print(f"  Allotted seats : {allotted:,}")
    print(f"  Unique colleges: {colleges}")

    print("\n  Category breakdown:")
    for row in cur.execute("SELECT category, COUNT(*) as n FROM allotments GROUP BY category ORDER BY n DESC"):
        print(f"    {row[0]:10s}: {row[1]:,}")

    print("\n  Per round:")
    for row in cur.execute("SELECT round, COUNT(*) as n FROM allotments GROUP BY round ORDER BY round"):
        print(f"    {row[0]:5s}: {row[1]:,}")


if __name__ == "__main__":
    print("Connecting to SQL Server Express...")
    conn = get_sql_conn()
    create_database(conn)
    conn.close()

    conn = get_sql_conn(DB_NAME)
    create_tables(conn)
    load_data(conn)
    print_summary(conn)
    conn.close()
    print("\nDone. Database: neet_counsellor on localhost\\SQLEXPRESS")
