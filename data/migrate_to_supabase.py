"""
Migrate neet_counsellor data from SQL Server → Supabase (PostgreSQL).
Fill in your Supabase password before running.
"""

import pyodbc
import psycopg2
import psycopg2.extras

# ── FILL THIS IN ──────────────────────────────────────────────────────────────
SUPABASE_URL = "postgresql://postgres:fUojvnciuyvraziVJGIDZkATzyCybGsA@acela.proxy.rlwy.net:53271/railway"
# ─────────────────────────────────────────────────────────────────────────────

BATCH = 1000

def get_sql_conn():
    return pyodbc.connect(
        "DRIVER={ODBC Driver 17 for SQL Server};"
        r"SERVER=localhost\SQLEXPRESS;"
        "DATABASE=neet_counsellor;Trusted_Connection=yes;"
    )

def get_pg_conn():
    return psycopg2.connect(SUPABASE_URL, connect_timeout=30)

# ── Create tables ─────────────────────────────────────────────────────────────

CREATE_ALLOTMENTS = """
CREATE TABLE IF NOT EXISTS allotments (
    id           SERIAL PRIMARY KEY,
    sr_no        VARCHAR(20),
    air          INTEGER,
    neet_roll    VARCHAR(15),
    cet_form     VARCHAR(12),
    name         TEXT,
    gender       VARCHAR(2),
    category     VARCHAR(20),
    quota        VARCHAR(20),
    women_quota  BOOLEAN,
    earmark      VARCHAR(20),
    retained     BOOLEAN,
    allotted     BOOLEAN,
    college_code VARCHAR(8),
    college_name TEXT,
    year         SMALLINT,
    round        VARCHAR(5)
);
CREATE INDEX IF NOT EXISTS idx_allotments_air      ON allotments(air);
CREATE INDEX IF NOT EXISTS idx_allotments_neet     ON allotments(neet_roll);
CREATE INDEX IF NOT EXISTS idx_allotments_college  ON allotments(college_code, category, round, year);
"""

CREATE_CUTOFFS = """
CREATE TABLE IF NOT EXISTS cutoffs (
    id           SERIAL PRIMARY KEY,
    college_code VARCHAR(8),
    college_name TEXT,
    category     VARCHAR(20),
    quota        VARCHAR(20),
    women_quota  BOOLEAN,
    year         SMALLINT,
    round        VARCHAR(5),
    opening_rank INTEGER,
    closing_rank INTEGER,
    seats_filled INTEGER
);
CREATE INDEX IF NOT EXISTS idx_cutoffs_lookup ON cutoffs(college_code, category, women_quota, year, round);
CREATE INDEX IF NOT EXISTS idx_cutoffs_rank   ON cutoffs(closing_rank, category, women_quota);
"""

CREATE_SEAT_MATRIX = """
CREATE TABLE IF NOT EXISTS seat_matrix (
    id           SERIAL PRIMARY KEY,
    college_code VARCHAR(8),
    college_name TEXT,
    intake       INTEGER,
    aiq          INTEGER,
    goi          INTEGER,
    state_pool   INTEGER,
    section      VARCHAR(20),
    row_type     VARCHAR(5),
    sc_seats     INTEGER, st_seats   INTEGER, vja_seats  INTEGER,
    ntb_seats    INTEGER, ntc_seats  INTEGER, ntd_seats  INTEGER,
    obc_seats    INTEGER, sebc_seats INTEGER, ews_seats  INTEGER,
    open_seats   INTEGER, state_total INTEGER,
    round        VARCHAR(5),
    year         SMALLINT
);
CREATE INDEX IF NOT EXISTS idx_sm_lookup ON seat_matrix(college_code, row_type, round, year);
"""


def migrate_table(name: str, sql_query: str, pg_insert: str, transform=None):
    print(f"\n── Migrating {name} ──")
    src = get_sql_conn()
    dst = get_pg_conn()
    src_cur = src.cursor()
    dst_cur = dst.cursor()

    src_cur.execute(sql_query)
    total = 0
    while True:
        rows = src_cur.fetchmany(BATCH)
        if not rows:
            break
        data = [transform(r) for r in rows] if transform else [tuple(r) for r in rows]
        psycopg2.extras.execute_batch(dst_cur, pg_insert, data, page_size=BATCH)
        dst.commit()
        total += len(rows)
        print(f"  {total:,} rows", end="\r")

    print(f"  {total:,} rows done")
    src.close()
    dst.close()


def main():
    # Test connection
    print("Testing Supabase connection...")
    pg = get_pg_conn()
    cur = pg.cursor()
    cur.execute("SELECT version()")
    print(f"  Connected: {cur.fetchone()[0][:50]}")

    # Create tables
    print("\nCreating tables...")
    cur.execute(CREATE_ALLOTMENTS)
    cur.execute(CREATE_CUTOFFS)
    cur.execute(CREATE_SEAT_MATRIX)
    pg.commit()

    # Check existing counts (skip if already migrated)
    cur.execute("SELECT COUNT(*) FROM allotments")
    existing = cur.fetchone()[0]
    pg.close()

    if existing > 0:
        print(f"\n  allotments already has {existing:,} rows — skipping allotments migration.")
        print("  Delete tables and re-run if you want a fresh migration.")
    else:
        migrate_table(
            "allotments",
            "SELECT sr_no, air, neet_roll, cet_form, name, gender, category, quota, women_quota, earmark, retained, allotted, college_code, college_name, year, round FROM allotments",
            "INSERT INTO allotments (sr_no, air, neet_roll, cet_form, name, gender, category, quota, women_quota, earmark, retained, allotted, college_code, college_name, year, round) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)",
        )

    migrate_table(
        "cutoffs",
        "SELECT college_code, college_name, category, quota, women_quota, year, round, opening_rank, closing_rank, seats_filled FROM cutoffs",
        "INSERT INTO cutoffs (college_code, college_name, category, quota, women_quota, year, round, opening_rank, closing_rank, seats_filled) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)",
        transform=lambda r: (r[0], r[1], r[2], r[3], bool(r[4]), r[5], r[6], r[7], r[8], r[9])
    )

    migrate_table(
        "seat_matrix",
        "SELECT college_code, college_name, intake, aiq, goi, state_pool, section, row_type, sc_seats, st_seats, vja_seats, ntb_seats, ntc_seats, ntd_seats, obc_seats, sebc_seats, ews_seats, open_seats, state_total, round, year FROM seat_matrix",
        "INSERT INTO seat_matrix (college_code, college_name, intake, aiq, goi, state_pool, section, row_type, sc_seats, st_seats, vja_seats, ntb_seats, ntc_seats, ntd_seats, obc_seats, sebc_seats, ews_seats, open_seats, state_total, round, year) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)",
    )

    print("\nMigration complete. Verifying row counts...")
    pg = get_pg_conn()
    cur = pg.cursor()
    for table in ["allotments", "cutoffs", "seat_matrix"]:
        cur.execute(f"SELECT COUNT(*) FROM {table}")
        print(f"  {table}: {cur.fetchone()[0]:,} rows")
    pg.close()
    print("\nDone! Supabase is ready.")

if __name__ == "__main__":
    main()
