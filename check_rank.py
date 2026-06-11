import pyodbc
conn = pyodbc.connect(
    "DRIVER={ODBC Driver 17 for SQL Server};"
    r"SERVER=localhost\SQLEXPRESS;"
    "DATABASE=neet_counsellor;Trusted_Connection=yes;"
)
cur = conn.cursor()

AIR = 725639

print(f"=== Real allotments at AIR ~{AIR} (OPEN, any round) ===")
cur.execute("""
    SELECT air, college_code, college_name, category, round, year
    FROM allotments
    WHERE air BETWEEN ? - 5000 AND ? + 5000
      AND category = 'OPEN'
      AND allotted = 1
    ORDER BY air
""", (AIR, AIR))
rows = cur.fetchall()
if rows:
    for r in rows:
        print(f"  AIR {r.air:,}  {r.college_code}  {r.college_name}  {r.category}  {r.round}")
else:
    print("  No allotments found near this rank!")

print(f"\n=== Cutoffs for OPEN category — what actually closed near {AIR} ===")
cur.execute("""
    SELECT college_code, college_name, round, opening_rank, closing_rank, seats_filled
    FROM cutoffs
    WHERE category = 'OPEN' AND women_quota = 0 AND year = 2025
      AND closing_rank BETWEEN ? - 100000 AND ? + 100000
    ORDER BY closing_rank
""", (AIR, AIR))
rows = cur.fetchall()
for r in rows:
    print(f"  {r.college_code}  {r.college_name:<35}  {r.round}  "
          f"open={r.opening_rank:,}  close={r.closing_rank:,}  filled={r.seats_filled}")

print(f"\n=== Max closing rank for OPEN category (last college to accept someone) ===")
cur.execute("""
    SELECT TOP 10 college_code, college_name, round, closing_rank
    FROM cutoffs
    WHERE category = 'OPEN' AND women_quota = 0 AND year = 2025
    ORDER BY closing_rank DESC
""")
for r in cur.fetchall():
    print(f"  {r.college_code}  {r.college_name:<35}  {r.round}  close={r.closing_rank:,}")

conn.close()
