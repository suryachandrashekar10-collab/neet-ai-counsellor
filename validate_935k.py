import pyodbc
conn = pyodbc.connect(
    "DRIVER={ODBC Driver 17 for SQL Server};"
    r"SERVER=localhost\SQLEXPRESS;"
    "DATABASE=neet_counsellor;Trusted_Connection=yes;"
)
cur = conn.cursor()

print("=== Did anyone with AIR 900K-1M get into GOVT MBBS? ===")
cur.execute("""
    SELECT a.air, a.college_code, a.college_name, a.category, a.round, a.allotted
    FROM allotments a
    JOIN seat_matrix sm ON sm.college_code = a.college_code
        AND sm.round = 'R1' AND sm.row_type = 'GEN' AND sm.year = 2025
    WHERE a.air BETWEEN 900000 AND 1000000
      AND a.allotted = 1
      AND a.category = 'OPEN'
      AND sm.section = 'GOVT_MBBS'
    ORDER BY a.air
""")
rows = cur.fetchall()
if rows:
    for r in rows:
        print(f"  AIR {r.air:,}  [{r.college_code}] {r.college_name}  {r.category}  {r.round}")
else:
    print("  NONE — no real allotments at this rank range for Govt MBBS OPEN")

print("\n=== GMC WASHIM (1270) — who actually got in? Last 10 allotments ===")
cur.execute("""
    SELECT TOP 10 air, category, round, allotted
    FROM allotments
    WHERE college_code = '1270' AND allotted = 1
    ORDER BY air DESC
""")
for r in cur.fetchall():
    print(f"  AIR {r.air:,}  {r.category}  {r.round}")

print("\n=== GMC WASHIM cutoffs OPEN — real closing ranks ===")
cur.execute("""
    SELECT round, opening_rank, closing_rank, seats_filled
    FROM cutoffs
    WHERE college_code = '1270' AND category = 'OPEN'
      AND women_quota = 0 AND year = 2025
    ORDER BY round
""")
for r in cur.fetchall():
    print(f"  {r.round}  open={r.opening_rank:,}  close={r.closing_rank:,}  filled={r.seats_filled}")

print("\n=== Max AIR that got into ANY govt MBBS in OPEN category ===")
cur.execute("""
    SELECT TOP 5 a.air, a.college_code, a.college_name, a.round
    FROM allotments a
    JOIN seat_matrix sm ON sm.college_code = a.college_code
        AND sm.round = 'R1' AND sm.row_type = 'GEN' AND sm.year = 2025
    WHERE a.allotted = 1
      AND a.category = 'OPEN'
      AND sm.section = 'GOVT_MBBS'
    ORDER BY a.air DESC
""")
for r in cur.fetchall():
    print(f"  AIR {r.air:,}  [{r.college_code}] {r.college_name}  {r.round}")

conn.close()
