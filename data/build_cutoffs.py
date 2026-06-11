"""
Derive cutoff table from allotments.
opening_rank = best (lowest) AIR admitted
closing_rank = worst (highest) AIR admitted
Only looks at allotted=1 rows.
"""

import pyodbc

SQL_SERVER = r"localhost\SQLEXPRESS"
DB_NAME    = "neet_counsellor"


def get_conn():
    return pyodbc.connect(
        f"DRIVER={{ODBC Driver 17 for SQL Server}};"
        f"SERVER={SQL_SERVER};"
        f"DATABASE={DB_NAME};"
        f"Trusted_Connection=yes;",
        autocommit=True
    )


def build_cutoffs(conn):
    cur = conn.cursor()

    # Create cutoffs table
    cur.execute("""
        IF OBJECT_ID('cutoffs', 'U') IS NOT NULL DROP TABLE cutoffs
    """)

    cur.execute("""
        CREATE TABLE cutoffs (
            id            INT IDENTITY PRIMARY KEY,
            college_code  VARCHAR(6)    NOT NULL,
            college_name  NVARCHAR(100),
            category      VARCHAR(10)   NOT NULL,
            quota         VARCHAR(10),
            women_quota   BIT           NOT NULL DEFAULT 0,
            year          SMALLINT      NOT NULL,
            round         VARCHAR(5)    NOT NULL,
            opening_rank  INT,
            closing_rank  INT,
            seats_filled  INT
        )
    """)

    cur.execute("""
        CREATE INDEX idx_cutoffs_lookup
        ON cutoffs(college_code, category, women_quota, year, round)
    """)

    cur.execute("""
        CREATE INDEX idx_cutoffs_rank
        ON cutoffs(closing_rank, category, women_quota)
    """)

    print("cutoffs table created")

    # Populate from allotments
    cur.execute("""
        INSERT INTO cutoffs
          (college_code, college_name, category, quota, women_quota,
           year, round, opening_rank, closing_rank, seats_filled)
        SELECT
            college_code,
            MAX(college_name)   AS college_name,
            category,
            quota,
            women_quota,
            year,
            round,
            MIN(air)            AS opening_rank,
            MAX(air)            AS closing_rank,
            COUNT(*)            AS seats_filled
        FROM allotments
        WHERE allotted = 1
          AND college_code IS NOT NULL
        GROUP BY
            college_code, category, quota, women_quota, year, round
    """)

    count = cur.execute("SELECT COUNT(*) FROM cutoffs").fetchone()[0]
    print(f"Inserted {count:,} cutoff rows")
    return count


def print_sample(conn):
    cur = conn.cursor()

    print("\n--- Sample cutoffs (GSMC Mumbai, R1) ---")
    for row in cur.execute("""
        SELECT college_code, college_name, category, women_quota,
               opening_rank, closing_rank, seats_filled
        FROM cutoffs
        WHERE college_code = '1103' AND round = 'R1'
        ORDER BY category, women_quota
    """):
        w = "(W)" if row.women_quota else "   "
        print(f"  {row.college_code} {row.category:6s}{w}  "
              f"open={row.opening_rank:7,}  close={row.closing_rank:7,}  "
              f"seats={row.seats_filled}")

    print("\n--- Top 10 colleges by seats filled (R1, OPEN category) ---")
    for row in cur.execute("""
        SELECT TOP 10 college_code, college_name, closing_rank, seats_filled
        FROM cutoffs
        WHERE round = 'R1' AND category = 'OPEN' AND women_quota = 0
        ORDER BY seats_filled DESC
    """):
        print(f"  {row.college_code}  {row.college_name:35s}  "
              f"closing={row.closing_rank:7,}  seats={row.seats_filled}")

    print("\n--- Closing ranks for OBC category, R1 (top 15 by rank) ---")
    for row in cur.execute("""
        SELECT TOP 15 college_code, college_name, closing_rank, seats_filled
        FROM cutoffs
        WHERE round = 'R1' AND category = 'OBC' AND women_quota = 0
        ORDER BY closing_rank ASC
    """):
        print(f"  {row.college_code}  {row.college_name:35s}  closing={row.closing_rank:7,}")


if __name__ == "__main__":
    conn = get_conn()
    build_cutoffs(conn)
    print_sample(conn)
    conn.close()
    print("\nDone. Query the cutoffs table to power the prediction engine.")
